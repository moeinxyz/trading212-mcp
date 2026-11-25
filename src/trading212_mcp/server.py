"""Personal Trading 212 MCP over stdio. Credentials come from the launching process."""

import asyncio
import logging
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from .broker import EQUITY, Trading212
from .config import CONFIG_KEYS, configured_accounts

SKILLS = {
    "analyze_stock": (
        "analyze-stock",
        "Research a listed company from public filings or supplied reports.",
    ),
    "analyze_portfolio_risk": (
        "analyze-portfolio-risk",
        "Review concentration, exposures and portfolio data gaps.",
    ),
}
READ = types.ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, openWorldHint=True
)
WRITE = types.ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True
)
ACCOUNT = {
    "type": "string",
    "pattern": "^[a-z][a-z0-9_-]*$",
    "default": "primary",
    "description": "Choose a label returned by trading_status.",
}
TEXT = {"type": "string", "minLength": 1}
DECIMAL = {
    "type": "string",
    "pattern": r"^(0|[1-9][0-9]*)(\.[0-9]+)?$",
    "maxLength": 32,
}
PAGE_SIZE = {"type": "integer", "minimum": 1, "maximum": 50}


def tool(
    name: str,
    description: str,
    properties: dict,
    required: tuple[str, ...] = (),
    *,
    write: bool = False,
) -> types.Tool:
    return types.Tool(
        name=name,
        description=description,
        annotations=WRITE if write else READ,
        inputSchema={
            "type": "object",
            "properties": properties,
            "required": list(required),
            "additionalProperties": False,
        },
        outputSchema={"type": "object"},
    )


READ_TOOLS = [
    tool(
        "trading_status",
        "Show local account labels, environment and credential presence. This does not contact the broker.",
        {},
    ),
    tool(
        "get_account_summary",
        "Return the broker's account value, cash and investment results in its primary currency.",
        {"account": ACCOUNT},
    ),
    tool(
        "list_positions",
        "Get current positions, optionally by exact Trading 212 ticker. walletImpact uses its own currency.",
        {"account": ACCOUNT, "ticker": TEXT},
    ),
    tool(
        "list_pending_orders",
        "Return active pending orders for the selected account.",
        {"account": ACCOUNT},
    ),
    tool(
        "trading_history",
        "Read one page of order, dividend or cash history. Reuse a returned next_page_path only with the same account and kind.",
        {
            "account": ACCOUNT,
            "kind": {"type": "string", "enum": ["orders", "dividends", "transactions"]},
            "next_page_path": {"type": ["string", "null"], "maxLength": 4096},
            "limit": {**PAGE_SIZE, "default": 50},
        },
        ("kind",),
    ),
    tool(
        "search_instruments",
        "Search the broker's instrument catalogue by part of a name, ticker or ISIN.",
        {"account": ACCOUNT, "query": TEXT, "limit": {**PAGE_SIZE, "default": 20}},
        ("query",),
    ),
]
ORDER_TOOLS = [
    tool(
        "preview_limit_order",
        "Prepare a primary-account DAY limit order. Provide positive decimal strings. Preview expires in five minutes.",
        {
            "ticker": TEXT,
            "side": {"type": "string", "enum": ["buy", "sell"]},
            "quantity": DECIMAL,
            "limit_price": DECIMAL,
        },
        ("ticker", "side", "quantity", "limit_price"),
    ),
    tool(
        "submit_limit_order",
        "Request interactive user approval and submit the exact primary-account preview once.",
        {"preview_id": TEXT},
        ("preview_id",),
        write=True,
    ),
]


def skill_text(prompt_name: str) -> str:
    if prompt_name not in SKILLS:
        raise ValueError("Unknown portfolio research prompt.")
    relative = Path("skills") / SKILLS[prompt_name][0] / "SKILL.md"
    path = Path(__file__).parent / relative
    if not path.is_file():
        # Editable installs and source distributions retain the top-level skills layout.
        path = Path(__file__).resolve().parents[2] / relative
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        raise ValueError(
            "This installation is missing a bundled analysis skill."
        ) from None
    if text.startswith("---\n") and "\n---\n" in text[4:]:
        text = text.split("\n---\n", 1)[1]
    return text.strip()


def create_server(accounts: Mapping[str, Trading212]) -> Server:
    primary = accounts["primary"]
    entries = READ_TOOLS + (ORDER_TOOLS if primary.writes else [])
    available = {entry.name: entry for entry in entries}
    server = Server(
        "Trading 212 MCP",
        version="0.1.0",
        instructions=(
            "Use trading_status first to identify the environment and configured accounts. The default primary "
            "account uses the first key. Specify a configured label to read another account. Compare broker account IDs "
            "before combining portfolios. Use the currency on each broker field. A next_page_path means that "
            "the history feed has more pages. Optional DAY limit orders apply only to the primary account."
        ),
    )

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return entries

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in available:
            raise ValueError("Unknown or disabled Trading 212 tool.")
        if name == "trading_status":
            return {
                "environment": primary.env,
                "credentials_configured": bool(primary.key and primary.secret),
                "writes_enabled": primary.writes,
                "provider": "Trading 212",
                "accounts": {
                    label: {
                        "environment": api.env,
                        "credentials_configured": bool(api.key and api.secret),
                        "writes_enabled": api.writes,
                    }
                    for label, api in accounts.items()
                },
            }
        if name == "preview_limit_order":
            return await primary.preview(**arguments)
        if name == "submit_limit_order":
            ctx = server.request_context
            return await primary.submit(
                arguments["preview_id"], ctx.session, ctx.request_id
            )

        label = arguments.get("account", "primary")
        if label not in accounts:
            raise ValueError(
                "Account unavailable. Choose a label returned by trading_status."
            )
        selected = accounts[label]
        if label != "primary" and not (selected.key and selected.secret):
            raise ValueError("This named account has no configured credential pair.")
        meta = {"environment": selected.env, "account_label": label}
        if name == "get_account_summary":
            return {
                **meta,
                "account": await selected.request(f"{EQUITY}/account/summary"),
            }
        if name == "list_positions":
            ticker = arguments.get("ticker")
            query = "?" + urlencode({"ticker": ticker}) if ticker else ""
            return {
                **meta,
                "positions": await selected.request(f"{EQUITY}/positions{query}"),
            }
        if name == "list_pending_orders":
            return {**meta, "orders": await selected.request(f"{EQUITY}/orders")}
        if name == "trading_history":
            page = await selected.history(
                arguments["kind"],
                arguments.get("limit", 50),
                arguments.get("next_page_path"),
            )
            return {**meta, **page}

        query = arguments["query"].strip().casefold()
        if not query:
            raise ValueError("Enter part of an instrument name, ticker or ISIN.")
        rows = [
            row
            for row in await selected.instruments()
            if any(
                query in str(row.get(field, "")).casefold()
                for field in ("name", "shortName", "ticker", "isin")
            )
        ]
        return {
            **meta,
            "matches": rows[: arguments.get("limit", 20)],
            "total_matches": len(rows),
        }

    @server.list_prompts()
    async def list_prompts() -> list[types.Prompt]:
        return [
            types.Prompt(name=name, description=desc)
            for name, (_, desc) in SKILLS.items()
        ]

    @server.get_prompt()
    async def get_prompt(
        name: str, arguments: dict[str, str] | None
    ) -> types.GetPromptResult:
        if arguments:
            raise ValueError("The portfolio research prompts take no arguments.")
        content = types.TextContent(type="text", text=skill_text(name))
        return types.GetPromptResult(
            messages=[types.PromptMessage(role="user", content=content)]
        )

    return server


async def run(settings: Mapping[str, str]) -> None:
    server = create_server(configured_accounts(settings))
    async with stdio_server() as (inputs, outputs):
        await server.run(inputs, outputs, server.create_initialization_options())


def main() -> None:
    for logger in ("httpx", "httpcore"):
        logging.getLogger(logger).setLevel(logging.WARNING)
    try:
        asyncio.run(
            run({name: os.environ[name] for name in CONFIG_KEYS if name in os.environ})
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
