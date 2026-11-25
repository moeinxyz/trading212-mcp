import asyncio
import base64
import json
import sys
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path

import httpx
import pytest
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.shared.memory import create_connected_server_and_client_session

from trading212_mcp.broker import EQUITY, Trading212
from trading212_mcp.config import configured_accounts
from trading212_mcp.server import create_server


def broker(handler, *, write=False):
    return Trading212(
        {
            "T212_ENV": "demo",
            "T212_ENABLE_WRITES": str(write),
            "T212_API_KEY": "test-key",
            "T212_API_SECRET": "test-secret",
        },
        httpx.MockTransport(handler),
    )


def test_read_only_tool_list_and_unconfigured_guidance():
    async def check():
        async with create_connected_server_and_client_session(
            create_server(configured_accounts({}))
        ) as client:
            tools = (await client.list_tools()).tools
            assert all(tool.annotations.readOnlyHint for tool in tools)
            assert {tool.name for tool in tools} == {
                "trading_status",
                "get_portfolio_overview",
                "calculate_stock_metrics",
                "get_account_summary",
                "list_positions",
                "list_pending_orders",
                "trading_history",
                "search_instruments",
            }
            status = await client.call_tool("trading_status", {})
            assert status.structuredContent["environment"] == "demo"
            assert not status.structuredContent["credentials_configured"]
            missing = await client.call_tool("get_account_summary", {})
            assert missing.isError and "T212_API_SECRET" in missing.content[0].text

    asyncio.run(check())


def test_isa_reads_use_the_second_key_and_never_fall_back_to_primary():
    calls = []

    def respond(request):
        account_id = {
            b"test-key:test-secret": 100,
            b"isa-key:isa-secret": 200,
        }[base64.b64decode(request.headers["authorization"].removeprefix("Basic "))]
        assert request.method == "GET"
        assert request.url.host == "demo.trading212.com"
        calls.append((account_id, request.url.path))
        data = (
            {"id": account_id}
            if request.url.path.endswith("/summary")
            else [{"ticker": "EXAMPLE_EQ"}]
        )
        return httpx.Response(200, json=data)

    accounts = configured_accounts(
        {
            "T212_API_KEY": "test-key",
            "T212_API_SECRET": "test-secret",
            "T212_ISA_API_KEY": "isa-key",
            "T212_ISA_API_SECRET": "isa-secret",
        },
        httpx.MockTransport(respond),
    )
    assert not accounts["isa"].writes

    async def check():
        async with create_connected_server_and_client_session(
            create_server(accounts)
        ) as client:
            status = (await client.call_tool("trading_status", {})).structuredContent
            assert status["accounts"]["isa"] == {
                "environment": "demo",
                "credentials_configured": True,
                "writes_enabled": False,
            }
            assert (
                await client.call_tool("get_account_summary", {"account": "typo"})
            ).isError
            primary = await client.call_tool("get_account_summary", {})
            isa = await client.call_tool("get_account_summary", {"account": "isa"})
            assert primary.structuredContent["account"]["id"] == 100
            assert isa.structuredContent["account"]["id"] == 200
            positions = await client.call_tool("list_positions", {"account": "isa"})
            assert positions.structuredContent["account_label"] == "isa"
            assert positions.structuredContent["positions"] == [
                {"ticker": "EXAMPLE_EQ"}
            ]

    asyncio.run(check())
    assert calls == [
        (100, EQUITY + "/account/summary"),
        (200, EQUITY + "/account/summary"),
        (200, EQUITY + "/positions"),
    ]


@pytest.mark.parametrize(
    "config", [{"T212_ENV": "sandbox"}, {"T212_ENABLE_WRITES": "yes"}]
)
def test_invalid_config_fails_closed(config):
    with pytest.raises(ValueError):
        Trading212(config)


def test_broker_read_pagination_exact_decimals_and_auth():
    next_page = (
        EQUITY + "/history/transactions?cursor=12%2F34&time=2026-01-01T12%3A00Z&limit=1"
    )
    seen = []

    def respond(request):
        assert request.url.host == "demo.trading212.com"
        assert (
            request.headers["authorization"]
            == "Basic " + base64.b64encode(b"test-key:test-secret").decode()
        )
        assert request.method == "GET"
        seen.append(request.url.raw_path.decode())
        if len(seen) == 1:
            data = b'{"items":[{"amount":11.1234567890123456789,"currency":"GBP"}],"nextPagePath":'
            return httpx.Response(
                200, content=data + json.dumps(next_page).encode() + b"}"
            )
        return httpx.Response(200, json={"items": [], "nextPagePath": None})

    async def check():
        api = broker(respond)
        first = await api.history("transactions", 1, None)
        assert first["items"][0]["amount"] == "11.1234567890123456789"
        second = await api.history("transactions", 1, first["next_page_path"])
        assert second["next_page_path"] is None
        assert seen == [EQUITY + "/history/transactions?limit=1", next_page]

    asyncio.run(check())


@pytest.mark.parametrize(
    "path",
    [
        "https://elsewhere.invalid/path",
        "//elsewhere.invalid/path",
        EQUITY + "/orders",
        EQUITY + "/history/orders?cursor=1",
        EQUITY + "/history/transactions?cursor=1#fragment",
        "/limit=5&cursor=abc",
        "cursor=1&redirect=https://elsewhere.invalid",
        "cursor=1&cursor=2",
        "limit=5&time=2026-09-10",
    ],
)
def test_history_only_accepts_cursor_on_same_feed(path):
    api = broker(lambda _: pytest.fail("Unexpected HTTP request"))
    with pytest.raises(ValueError, match="next_page_path"):
        asyncio.run(api.history("transactions", 50, path))


@pytest.mark.parametrize("prefix", ["", "?"])
def test_cash_query_only_continuation_preserves_provider_encoding(prefix):
    endpoint = EQUITY + "/history/transactions"
    query = "limit=5&cursor=abc%2Fdef&time=2026-01-12T11:12:31.337Z"
    seen = []

    def respond(request):
        seen.append(request.url.raw_path.decode())
        return httpx.Response(
            200,
            json={
                "items": [{"amount": 1}],
                "nextPagePath": prefix + query if len(seen) == 1 else None,
            },
        )

    async def check():
        api = broker(respond)
        first = await api.history("transactions", 5, None)
        assert first["next_page_path"] == endpoint + "?" + query
        second = await api.history("transactions", 5, first["next_page_path"])
        assert second["next_page_path"] is None
        assert seen == [endpoint + "?limit=5", endpoint + "?" + query]

    asyncio.run(check())


@pytest.mark.parametrize(
    "provider_cursor",
    ["https://elsewhere.invalid", EQUITY + "/history/orders?cursor=2", "cursor=abc"],
)
def test_unusable_or_repeated_broker_cursor_retains_current_page(provider_cursor):
    item = {"amount": "1.05"}
    api = broker(
        lambda _: httpx.Response(
            200, json={"items": [item], "nextPagePath": provider_cursor}
        )
    )
    page = asyncio.run(
        api.history("transactions", 1, EQUITY + "/history/transactions?cursor=abc")
    )
    assert page["items"] == [item]
    assert page["next_page_path"] is None
    assert "incomplete" in page["coverage_warning"]


def test_rate_limit_and_sanitized_rejection():
    api = broker(
        lambda _: httpx.Response(
            429, headers={"retry-after": "12"}, text="private provider detail"
        )
    )
    with pytest.raises(ValueError, match="12 seconds") as caught:
        asyncio.run(api.request(EQUITY + "/positions"))
    assert "private provider detail" not in str(caught.value)


@pytest.mark.parametrize(
    "approval", ["accept", "decline", "cancel", "unchecked", "unsupported", "timeout"]
)
def test_single_use_approval_over_mcp(approval):
    sent = []
    ticker = "EXAMPLE_US_EQ"

    def respond(request):
        if request.url.path.endswith("/metadata/instruments"):
            return httpx.Response(
                200, json=[{"ticker": ticker, "currencyCode": "USD", "name": "Example"}]
            )
        if request.url.path.endswith("/account/summary"):
            return httpx.Response(200, json={"currency": "GBP", "id": 110022})
        assert request.url.path == EQUITY + "/orders/limit"
        assert request.method == "POST"
        sent.append(json.loads(request.content, parse_float=Decimal))
        if approval == "timeout":
            raise httpx.ReadTimeout("no reply")
        return httpx.Response(200, json={"id": 123, "status": "NEW"})

    async def elicit(context, params):
        assert (
            "DEMO" in params.message
            and "SELL" in params.message
            and "0022" in params.message
        )
        assert ticker in params.message and "1.000000000000000001 USD" in params.message
        if approval in ("decline", "cancel"):
            return types.ElicitResult(action=approval)
        return types.ElicitResult(
            action="accept", content={"approve": approval != "unchecked"}
        )

    async def check():
        api = broker(respond, write=True)
        async with create_connected_server_and_client_session(
            create_server({"primary": api}),
            elicitation_callback=elicit if approval != "unsupported" else None,
        ) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
            assert tools["submit_limit_order"].annotations.destructiveHint
            assert set(tools["submit_limit_order"].inputSchema["properties"]) == {
                "preview_id"
            }
            preview = (
                await client.call_tool(
                    "preview_limit_order",
                    {
                        "ticker": ticker,
                        "side": "sell",
                        "quantity": "0.010000000000000001",
                        "limit_price": "1.000000000000000001",
                    },
                )
            ).structuredContent
            assert (
                preview["value_at_limit_before_fees_or_fx"]
                == "0.010000000000000001010000000000000001"
            )
            assert not sent
            args = {"preview_id": preview["preview_id"]}
            result = await client.call_tool("submit_limit_order", args)
            if approval == "timeout":
                assert result.isError and "outcome is unknown" in result.content[0].text
            elif approval == "unsupported":
                assert result.isError and "interactive form" in result.content[0].text
            else:
                assert not result.isError
                assert result.structuredContent["submitted"] == (approval == "accept")
            replay = await client.call_tool("submit_limit_order", args)
            assert replay.isError and "unavailable" in replay.content[0].text

    asyncio.run(check())
    if approval in ("accept", "timeout"):
        assert sent == [
            {
                "ticker": ticker,
                "quantity": Decimal("-0.010000000000000001"),
                "limitPrice": Decimal("1.000000000000000001"),
                "timeValidity": "DAY",
            }
        ]
    else:
        assert sent == []


@pytest.mark.parametrize(
    "settings",
    [
        {"T212_API_KEY": "partial"},
        {"T212_ISA_API_SECRET": "partial"},
        {
            "T212_API_KEY": "same",
            "T212_API_SECRET": "one",
            "T212_ISA_API_KEY": "same",
            "T212_ISA_API_SECRET": "two",
        },
    ],
)
def test_incomplete_or_duplicated_account_pairs(settings):
    with pytest.raises(ValueError):
        configured_accounts(settings)


def test_disabled_or_missing_account_never_calls_the_broker():
    async def check():
        accounts = configured_accounts(
            {
                "T212_API_KEY": "partial-fixture-id",
                "T212_API_SECRET": "fixture-password",
            },
            httpx.MockTransport(lambda _: pytest.fail("Unexpected brokerage request")),
        )
        async with create_connected_server_and_client_session(
            create_server(accounts)
        ) as client:
            status = (await client.call_tool("trading_status", {})).structuredContent
            assert "partial-fixture-id" not in str(
                status
            ) and "fixture-password" not in str(status)
            assert (
                await client.call_tool("get_account_summary", {"account": "isa"})
            ).isError
            assert (
                await client.call_tool("submit_limit_order", {"preview_id": "absent"})
            ).isError

    asyncio.run(check())


def test_read_tools_filter_and_cache():
    calls = []

    def respond(request):
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("/positions"):
            assert request.url.params["ticker"] == "A/B"
            return httpx.Response(
                200, json=[{"ticker": "A/B", "walletImpact": {"currency": "GBP"}}]
            )
        if request.url.path.endswith("/orders"):
            return httpx.Response(200, json=[])
        return httpx.Response(
            200,
            json=[
                {
                    "ticker": "SHARE_X",
                    "isin": "XXTEST",
                    "name": "Example Plc",
                    "currencyCode": "GBP",
                }
            ],
        )

    async def check():
        async with create_connected_server_and_client_session(
            create_server({"primary": broker(respond)})
        ) as client:
            for query in ("share_", "xxtest"):
                res = await client.call_tool("search_instruments", {"query": query})
                assert res.structuredContent["total_matches"] == 1
            assert (
                await client.call_tool("list_pending_orders", {})
            ).structuredContent["orders"] == []
            assert (
                await client.call_tool("list_positions", {"ticker": "A/B"})
            ).structuredContent["positions"][0]["ticker"] == "A/B"

    asyncio.run(check())
    assert calls == [
        ("GET", EQUITY + "/metadata/instruments"),
        ("GET", EQUITY + "/orders"),
        ("GET", EQUITY + "/positions"),
    ]


def test_stdio_starts_without_credentials_or_dotenv(tmp_path):
    bootstrap = """
import os, sys
def audit(event, args):
    if event == 'socket.connect':
        # Windows asyncio can create its wakeup socketpair using a TCP loopback connection.
        address = args[1]
        if sys.platform != 'win32' or not isinstance(address, tuple) or address[0] not in ('127.0.0.1', '::1'):
            raise RuntimeError('status or prompts initiated an external connection')
    if event == 'open' and isinstance(args[0], str) and os.path.basename(args[0]) == '.env':
        raise RuntimeError('unexpected dotenv access')
sys.addaudithook(audit)
from trading212_mcp.server import main
main()
"""
    (tmp_path / ".env").write_text("T212_API_KEY=synthetic-file-value")
    params = StdioServerParameters(
        command=sys.executable,
        args=["-c", bootstrap],
        cwd=tmp_path,
        env={},
    )

    async def check():
        async with stdio_client(params) as (rd, wr), ClientSession(rd, wr) as client:
            assert (await client.initialize()).serverInfo.version == version(
                "moein-trading212-mcp"
            )
            result = (await client.call_tool("trading_status", {})).structuredContent
            assert (
                result["environment"] == "demo"
                and not result["credentials_configured"]
                and not result["writes_enabled"]
            )
            assert set(result["accounts"]) == {"primary"}
            prompts = {item.name for item in (await client.list_prompts()).prompts}
            source_skills = Path(__file__).resolve().parents[1] / "skills"
            assert prompts == {
                file.parent.name.replace("-", "_")
                for file in source_skills.glob("*/SKILL.md")
            }
            for name in prompts:
                assert (
                    len((await client.get_prompt(name)).messages[0].content.text) > 200
                )

    asyncio.run(check())


def private_toml(tmp_path, contents):
    path = tmp_path / "synthetic-profile.toml"
    path.write_text(contents, encoding="utf-8")
    path.chmod(0o600)
    return str(path)


def test_named_profiles_isolate_accounts_and_allow_an_empty_isa(tmp_path):
    filename = private_toml(
        tmp_path,
        """
[unrelated]
irrelevant = "private-fixture-value"
[trading]
T212_ENV = "demo"
T212_API_KEY = "file-key"
T212_API_SECRET = "file-secret"
[trading_accounts.isa]
T212_API_KEY = ""
T212_API_SECRET = ""
[trading_accounts.long_hold]
T212_ENV = "live"
T212_API_KEY = "hold-key"
T212_API_SECRET = "hold-secret"
T212_ENABLE_WRITES = true
""",
    )
    calls = []

    def respond(request):
        user = base64.b64decode(request.headers["Authorization"].split()[1])
        calls.append((user, request.url.host))
        return httpx.Response(200, json={"id": 12345})

    accounts = configured_accounts(
        {
            "T212_CONFIG_FILE": filename,
            "T212_API_KEY": "env-key",
            "T212_API_SECRET": "env-secret",
        },
        httpx.MockTransport(respond),
    )

    async def check():
        async with create_connected_server_and_client_session(
            create_server(accounts)
        ) as client:
            status = (await client.call_tool("trading_status", {})).structuredContent
            assert set(status["accounts"]) == {"primary", "isa", "long_hold"}
            assert (
                "hold-key" not in str(status)
                and "private-fixture-value" not in str(status)
                and filename not in str(status)
            )
            assert (
                status["accounts"]["isa"]["environment"] == "live"
                and not status["accounts"]["isa"]["credentials_configured"]
            )
            assert not status["accounts"]["long_hold"]["writes_enabled"]
            assert not (await client.call_tool("get_account_summary", {})).isError
            assert not (
                await client.call_tool("get_account_summary", {"account": "long_hold"})
            ).isError
            assert (
                await client.call_tool("get_account_summary", {"account": "isa"})
            ).isError
            assert (
                await client.call_tool("get_account_summary", {"account": "unknown"})
            ).isError

    asyncio.run(check())
    assert calls == [
        (b"env-key:env-secret", "demo.trading212.com"),
        (b"hold-key:hold-secret", "live.trading212.com"),
    ]


def test_file_and_env_credentials_are_overridden_as_pairs(tmp_path):
    filename = private_toml(
        tmp_path,
        """
[trading]
T212_ENV = "demo"
T212_ENABLE_WRITES = true
T212_API_KEY = "file-a"
T212_API_SECRET = "file-b"
[trading_accounts.isa]
T212_ENV = "live"
T212_API_KEY = "file-c"
T212_API_SECRET = "file-d"
T212_ENABLE_WRITES = true
""",
    )
    for single in (
        "T212_API_KEY",
        "T212_API_SECRET",
        "T212_ISA_API_KEY",
        "T212_ISA_API_SECRET",
    ):
        with pytest.raises(ValueError, match="both"):
            configured_accounts({"T212_CONFIG_FILE": filename, single: "new-field"})
    opts = configured_accounts(
        {
            "T212_CONFIG_FILE": filename,
            "T212_ISA_API_KEY": "new-a",
            "T212_ISA_API_SECRET": "new-b",
            "T212_ENABLE_WRITES": "false",
        }
    )
    assert (
        opts["isa"].env == "live"
        and opts["isa"].key == "new-a"
        and opts["isa"].secret == "new-b"
    )
    assert not opts["primary"].writes and not opts["isa"].writes


@pytest.mark.parametrize(
    "text",
    [
        "malformed TOML string not a document",
        "[trading_accounts.primary]",
        "[trading_accounts.'Capital Label']",
        "[trading]\nT212_API_KEY = 123",
        "trading_accounts = []",
        "[trading_accounts.one]\nT212_API_KEY='dup'\nT212_API_SECRET='a'\n[trading_accounts.two]\nT212_API_KEY='dup'\nT212_API_SECRET='b'",
    ],
)
def test_bad_selected_settings_do_not_echo_the_file(tmp_path, text):
    filename = private_toml(tmp_path, text)
    with pytest.raises(ValueError) as err:
        configured_accounts({"T212_CONFIG_FILE": filename})
    assert filename not in str(err.value) and text not in str(err.value)


def test_file_must_be_explicit_private_regular(tmp_path):
    import os

    with pytest.raises(ValueError, match="absolute"):
        configured_accounts({"T212_CONFIG_FILE": "relative.toml"})
    with pytest.raises(ValueError, match="regular"):
        configured_accounts({"T212_CONFIG_FILE": str(tmp_path)})
    if os.name == "posix":
        filename = private_toml(tmp_path, "[trading]")
        os.chmod(filename, 0o644)
        with pytest.raises(ValueError, match="owner-only"):
            configured_accounts({"T212_CONFIG_FILE": filename})


def test_redirect_is_not_followed_and_body_is_not_echoed():
    calls = []

    def respond(request):
        calls.append(request.url.host)
        return httpx.Response(
            302,
            headers={"location": "https://elsewhere.invalid"},
            text="private-response",
        )

    with pytest.raises(ValueError, match="302") as err:
        asyncio.run(broker(respond).request(EQUITY + "/positions"))
    assert calls == ["demo.trading212.com"] and "private-response" not in str(err.value)


def test_typed_tools_reject_unexpected_order_fields():
    async def check():
        api = broker(lambda _: pytest.fail("Unexpected brokerage request"), write=True)
        async with create_connected_server_and_client_session(
            create_server({"primary": api})
        ) as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
            for tool in tools.values():
                assert tool.inputSchema["additionalProperties"] is False
            # Account selection on an order must never be silently stripped by the argument validator.
            result = await client.call_tool(
                "preview_limit_order",
                {
                    "account": "isa",
                    "ticker": "EXAMPLE",
                    "side": "buy",
                    "quantity": "1",
                    "limit_price": "5",
                },
            )
            assert result.isError and "account" in result.content[0].text

    asyncio.run(check())


def test_concurrent_catalogue_requests_share_one_fetch():
    async def check():
        started, release = asyncio.Event(), asyncio.Event()
        calls = []

        async def respond(request):
            calls.append(request.url.path)
            started.set()
            await release.wait()
            return httpx.Response(
                200, json=[{"ticker": "EXAMPLE", "name": "Example Corporation"}]
            )

        api = broker(respond)
        first = asyncio.create_task(api.search_instruments("corp"))
        await asyncio.wait_for(started.wait(), timeout=2)
        second = asyncio.create_task(api.search_instruments("example"))
        release.set()
        a, b = await asyncio.gather(first, second)
        assert a == b == [{"ticker": "EXAMPLE", "name": "Example Corporation"}]
        assert calls == [EQUITY + "/metadata/instruments"]

    asyncio.run(check())


@pytest.mark.parametrize("expire_during_approval", [False, True])
def test_preview_consumed_before_approval_and_checked_again_before_post(
    monkeypatch, expire_during_approval
):
    from types import SimpleNamespace

    from trading212_mcp import broker as module

    async def check():
        entered, release = asyncio.Event(), asyncio.Event()
        clock = [1.0]
        monkeypatch.setattr(module, "time", SimpleNamespace(monotonic=lambda: clock[0]))

        async def confirm(message: str) -> bool:
            assert "primary account" in message
            entered.set()
            await release.wait()
            return True

        posts = []

        def respond(request):
            if request.url.path.endswith("/metadata/instruments"):
                return httpx.Response(
                    200, json=[{"ticker": "EXAMPLE", "currencyCode": "GBP"}]
                )
            if request.url.path.endswith("/account/summary"):
                return httpx.Response(200, json={"id": 12345, "currency": "GBP"})
            posts.append(request.method)
            return httpx.Response(200, json={"id": 7})

        api = broker(respond, write=True)
        preview = await api.preview("EXAMPLE", "buy", "1", "5")
        token = preview["preview_id"]
        first = asyncio.create_task(api.submit(token, confirm))
        await asyncio.wait_for(entered.wait(), timeout=2)
        with pytest.raises(ValueError, match="unavailable"):
            await api.submit(token, confirm)
        assert posts == []
        if expire_during_approval:
            clock[0] += 301
        release.set()
        if expire_during_approval:
            with pytest.raises(ValueError, match="expired during approval"):
                await first
            assert posts == []
        else:
            assert (await first)["submitted"] and posts == ["POST"]

    asyncio.run(check())


def test_skill_discovery_uses_skill_files_and_ignores_unrelated_files(tmp_path):
    from trading212_mcp.server import load_prompts

    folder = tmp_path / "review-example"
    folder.mkdir()
    (folder / "SKILL.md").write_text(
        "---\nname: review-example\n---\n\n# Review an example\n\nUse fictional observations.",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("This file is not a skill.", encoding="utf-8")
    prompts = load_prompts(tmp_path)
    assert list(prompts) == ["review_example"]
    result = prompts["review_example"]
    assert result.description == "Review an example"
    assert (
        result.messages[0].content.text
        == "# Review an example\n\nUse fictional observations."
    )
