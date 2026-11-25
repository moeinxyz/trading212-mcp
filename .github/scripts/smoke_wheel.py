"""Verify the installed CLI and its bundled prompts from outside the checkout."""

import asyncio
import sysconfig
from importlib.metadata import distribution
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    checkout = Path(__file__).resolve().parents[2]
    assert not Path.cwd().resolve().is_relative_to(checkout)
    source_skills = {p.parent.name for p in (checkout / "skills").glob("*/SKILL.md")}
    wheel_files = distribution("moein-trading212-mcp").files or []
    wheel_skills = {p.parent.name for p in wheel_files if p.name == "SKILL.md"}
    assert source_skills and wheel_skills == source_skills, "Wheel is missing skills"

    entrypoint = Path(sysconfig.get_path("scripts")) / "trading212-mcp"
    # An explicit demo environment also bypasses the CLI's default account file.
    server = StdioServerParameters(command=str(entrypoint), env={"T212_ENV": "demo"})
    async with (
        stdio_client(server) as (reader, writer),
        ClientSession(reader, writer) as client,
    ):
        await client.initialize()
        tools = (await client.list_tools()).tools
        assert {t.name for t in tools} == {
            "trading_status",
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

        prompts = {prompt.name for prompt in (await client.list_prompts()).prompts}
        assert prompts == {name.replace("-", "_") for name in wheel_skills}
        for name in sorted(prompts):
            result = await client.get_prompt(name)
            assert result.messages and result.messages[0].content.text.strip(), name
    print(f"Installed CLI passed stdio checks with {len(prompts)} bundled prompts.")


if __name__ == "__main__":
    asyncio.run(main())
