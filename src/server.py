"""Serve Trading 212 tools and bundled research prompts over standard input/output."""

import asyncio
import logging
import os
from collections.abc import Mapping
from functools import partial
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlencode

from mcp import types
from mcp.server.elicitation import elicit_with_validation
from mcp.server.fastmcp.tools import ToolManager
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError
from pydantic import BaseModel, Field

from .broker import EQUITY, History, Side, Trading212
from .config import CONFIG_KEYS, configured_accounts
from .metrics import calculate_stock_metrics
from .overview import portfolio_overview

JsonObject = dict[str, Any]
AccountLabel = Annotated[
    str,
    Field(
        pattern=r"^[a-z][a-z0-9_-]*$", description="Account label from trading_status."
    ),
]
Text = Annotated[str, Field(min_length=1)]
PageSize = Annotated[int, Field(ge=1, le=50)]
DecimalText = Annotated[
    str, Field(pattern=r"^(0|[1-9][0-9]*)(\.[0-9]+)?$", max_length=32)
]
Cursor = Annotated[str, Field(max_length=4096)]
READ = types.ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, openWorldHint=True
)
WRITE = types.ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True
)


class ConfirmOrder(BaseModel):
    approve: bool = Field(
        description="Place this exact limit order?", default=False, strict=True
    )


def load_prompts(directory: Path) -> dict[str, types.GetPromptResult]:
    """Expose each installed SKILL.md as an MCP prompt, using its Markdown title."""
    prompts = {}
    for file in sorted(directory.glob("*/SKILL.md")):
        name = file.parent.name.replace("-", "_")
        if name in prompts:
            raise ValueError(f"Duplicate research prompt name: {name}")
        text = file.read_text(encoding="utf-8")
        if text.startswith("---\n"):
            _, separator, body = text[4:].partition("\n---\n")
            if not separator:
                raise ValueError(f"Invalid skill front matter: {name}")
            text = body
        title = next(
            (line[2:].strip() for line in text.splitlines() if line.startswith("# ")),
            name,
        )
        message = types.PromptMessage(
            role="user", content=types.TextContent(type="text", text=text.strip())
        )
        prompts[name] = types.GetPromptResult(description=title, messages=[message])
    if not prompts:
        raise ValueError("This installation is missing its research skills.")
    return prompts


def create_server(accounts: Mapping[str, Trading212]) -> Server:
    profiles = accounts
    primary = profiles["primary"]
    server = Server(
        "Trading 212 MCP",
        version=version("moein-trading212-mcp"),
        instructions=(
            "Use trading_status to find configured labels and demo/live environments. Select the requested label "
            "explicitly, including when primary has no key. A label is user-defined. Verify it with the account "
            "owner when its meaning is unclear. Compare broker account IDs "
            "before combining portfolios, or use get_portfolio_overview for several accounts. This is a personal "
            "research project. Verify figures before making investment decisions. Use the currency on each broker "
            "field. A next_page_path means the same "
            "account and history feed has more pages. Optional DAY limit orders apply only to the primary account."
        ),
    )
    # ToolManager generates schemas from signatures. Constructing only the manager
    # preserves explicit profile selection without FastMCP's automatic .env lookup.
    tools = ToolManager()
    read_tool = partial(tools.add_tool, annotations=READ)
    tools.add_tool(
        calculate_stock_metrics,
        annotations=types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )

    def select(label: str) -> Trading212:
        if label not in profiles:
            raise ValueError(
                "Account unavailable. Choose a label returned by trading_status."
            )
        api = profiles[label]
        if label != "primary" and not api.credentials_configured:
            raise ValueError("This named account has no configured credential pair.")
        return api

    async def read(label: str, path: str, field: str) -> JsonObject:
        api = select(label)
        return {
            "environment": api.env,
            "account_label": label,
            field: await api.request(path),
        }

    @read_tool
    def trading_status() -> JsonObject:
        """Show account labels, environments and credential presence without contacting the broker."""
        return {
            "provider": "Trading 212",
            **primary.status(),
            "accounts": {name: api.status() for name, api in profiles.items()},
        }

    @read_tool
    async def get_account_summary(account: AccountLabel = "primary") -> JsonObject:
        """Get the account's cash, investments and portfolio value in its primary currency."""
        return await read(account, f"{EQUITY}/account/summary", "account")

    @read_tool
    async def get_portfolio_overview(
        accounts: Annotated[list[AccountLabel], Field(min_length=1, max_length=50)]
        | None = None,
    ) -> JsonObject:
        """Read selected account summaries, or all configured accounts. Group totals by environment and currency."""
        return await portfolio_overview(profiles, accounts)

    @read_tool
    async def list_positions(
        account: AccountLabel = "primary", ticker: Text | None = None
    ) -> JsonObject:
        """Get current holdings, optionally by exact Trading 212 ticker. walletImpact has its own currency."""
        query = "?" + urlencode({"ticker": ticker}) if ticker else ""
        return await read(account, f"{EQUITY}/positions{query}", "positions")

    @read_tool
    async def list_pending_orders(account: AccountLabel = "primary") -> JsonObject:
        """List orders that are still open for the selected account."""
        return await read(account, f"{EQUITY}/orders", "orders")

    @read_tool
    async def trading_history(
        kind: History,
        next_page_path: Cursor | None = None,
        limit: PageSize = 50,
        account: AccountLabel = "primary",
    ) -> JsonObject:
        """Get one history page. Reuse its next_page_path with the same account and kind until null."""
        return {
            "account_label": account,
            **await select(account).history(kind, limit, next_page_path),
        }

    @read_tool
    async def search_instruments(
        query: Text, limit: PageSize = 20, account: AccountLabel = "primary"
    ) -> JsonObject:
        """Search the broker's instrument catalogue by name, ticker or ISIN."""
        api = select(account)
        matches = await api.search_instruments(query)
        return {
            "environment": api.env,
            "account_label": account,
            "matches": matches[:limit],
            "total_matches": len(matches),
        }

    if primary.writes:

        @read_tool
        async def preview_limit_order(
            ticker: Text, side: Side, quantity: DecimalText, limit_price: DecimalText
        ) -> JsonObject:
            """Prepare a primary-account DAY limit order. Previews expire after five minutes."""
            return await primary.preview(ticker, side, quantity, limit_price)

        async def confirm_order(message: str) -> bool:
            ctx = server.request_context
            try:
                response = await elicit_with_validation(
                    ctx.session,
                    message,
                    ConfirmOrder,
                    related_request_id=ctx.request_id,
                )
            except (McpError, ValueError):
                raise ValueError(
                    "Order was not sent. Use an MCP client with interactive form elicitation for order approval."
                ) from None
            return (
                response.action == "accept"
                and response.data is not None
                and response.data.approve
            )

        @partial(tools.add_tool, annotations=WRITE)
        async def submit_limit_order(preview_id: Text) -> JsonObject:
            """Request interactive approval and submit the exact primary-account preview once."""
            return await primary.submit(preview_id, confirm_order)

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name=tool.name,
                description=tool.description,
                annotations=tool.annotations,
                inputSchema={**tool.parameters, "additionalProperties": False},
                outputSchema=tool.output_schema,
            )
            for tool in tools.list_tools()
        ]

    server.call_tool()(tools.call_tool)

    module_dir = Path(__file__).resolve().parent
    skill_dir = module_dir / "skills"
    if module_dir.name == "src" and not skill_dir.is_dir():
        skill_dir = module_dir.parent / "skills"
    prompts = load_prompts(skill_dir)

    @server.list_prompts()
    async def list_prompts() -> list[types.Prompt]:
        return [
            types.Prompt(name=name, description=result.description)
            for name, result in prompts.items()
        ]

    @server.get_prompt()
    async def get_prompt(
        name: str, arguments: dict[str, str] | None
    ) -> types.GetPromptResult:
        if name not in prompts:
            raise ValueError("Unknown portfolio research prompt.")
        if arguments:
            raise ValueError("Portfolio research prompts take no arguments.")
        return prompts[name]

    return server


async def run(settings: Mapping[str, str]) -> None:
    server = create_server(configured_accounts(settings))
    async with stdio_server() as (inputs, outputs):
        await server.run(inputs, outputs, server.create_initialization_options())


def main(settings: Mapping[str, str] | None = None) -> None:
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
    try:
        if settings is None:
            settings = {
                name: os.environ[name] for name in CONFIG_KEYS if name in os.environ
            }
        asyncio.run(run(settings))
    except ValueError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
