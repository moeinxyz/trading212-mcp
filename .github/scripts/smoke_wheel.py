"""Verify the installed CLI and its bundled prompts from outside the checkout."""

import asyncio
import sys
import sysconfig
from importlib.metadata import distribution
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main(command: list[str]) -> None:
    checkout = Path(__file__).resolve().parents[2]
    assert not Path.cwd().resolve().is_relative_to(checkout)
    source_skills = {p.parent.name for p in (checkout / "skills").glob("*/SKILL.md")}
    wheel_files = distribution("moein-trading212-mcp").files or []
    wheel_skills = {p.parent.name for p in wheel_files if p.name == "SKILL.md"}
    assert source_skills and wheel_skills == source_skills, "Wheel is missing skills"

    # An explicit demo environment also bypasses the CLI's default account file.
    server = StdioServerParameters(
        command=command[0], args=command[1:], env={"T212_ENV": "demo"}
    )
    async with (
        stdio_client(server) as (reader, writer),
        ClientSession(reader, writer) as client,
    ):
        await client.initialize()
        tools = (await client.list_tools()).tools
        assert {t.name for t in tools} == {
            "trading_status",
            "get_portfolio_overview",
            "calculate_stock_metrics",
            "get_account_summary",
            "list_positions",
            "list_pending_orders",
            "trading_history",
            "search_instruments",
        }
        assert all(t.annotations and t.annotations.readOnlyHint for t in tools)
        status = await client.call_tool("trading_status", {})
        assert not status.isError and status.structuredContent
        assert status.structuredContent["credentials_configured"] is False
        assert status.structuredContent["writes_enabled"] is False

        overview = await client.call_tool("get_portfolio_overview", {})
        assert (
            not overview.isError
            and overview.structuredContent["status"] == "unavailable"
        )
        metrics = await client.call_tool(
            "calculate_stock_metrics",
            {
                "currency": "GBP",
                "amount_scale": "millions",
                "current": {
                    "period_kind": "year",
                    "period_start": "2025-01-01",
                    "period_end": "2025-12-31",
                    "source": "Fictional annual report, income statement",
                    "revenue": "100",
                    "operating_profit": "15",
                },
            },
        )
        assert not metrics.isError
        margin = next(
            row
            for row in metrics.structuredContent["rows"]
            if row["metric"] == "operating_margin"
        )
        assert (margin["current"], margin["unit"]) == ("15", "%")

        prompts = {prompt.name for prompt in (await client.list_prompts()).prompts}
        assert prompts == {name.replace("-", "_") for name in wheel_skills}
        for name in sorted(prompts):
            result = await client.get_prompt(name)
            assert result.messages and result.messages[0].content.text.strip(), name
    print(
        f"{Path(command[0]).name} passed stdio checks with {len(prompts)} bundled prompts."
    )


if __name__ == "__main__":
    entrypoint = Path(sysconfig.get_path("scripts")) / "trading212-mcp"
    asyncio.run(main(sys.argv[1:] or [str(entrypoint)]))
