import asyncio
import json

import httpx
import pytest

from trading212_mcp.broker import EQUITY, Trading212
from trading212_mcp.overview import MAX_ACCOUNTS, portfolio_overview


def summary(
    account_id=24601234, currency="GBP", cash="10.11", current="20.22", total="33.33"
):
    return {
        "id": account_id,
        "currency": currency,
        "cash": {"availableToTrade": cash, "reservedForOrders": "3", "inPies": "0"},
        "investments": {"currentValue": current, "totalCost": "15.75"},
        "totalValue": total,
    }


def broker(response, calls, *, env="live", configured=True):
    def handler(request):
        assert (
            request.method == "GET" and request.url.path == EQUITY + "/account/summary"
        )
        assert request.url.query == b"" and request.url.host == f"{env}.trading212.com"
        calls.append(request.url.path)
        return (
            response
            if isinstance(response, httpx.Response)
            else httpx.Response(200, json=response)
        )

    return Trading212(
        {
            "T212_ENV": env,
            "T212_API_KEY": "test-key" if configured else "",
            "T212_API_SECRET": "test-secret" if configured else "",
        },
        httpx.MockTransport(handler),
    )


def test_one_or_both_return_exact_values_from_summary_only():
    calls = []
    configured = {
        "invest": broker(summary(), calls),
        "isa": broker(
            summary(
                24601235,
                cash="0.0000000000000000001",
                current="1000.00",
                total="1000.0000000000000000001",
            ),
            calls,
        ),
    }
    result = asyncio.run(portfolio_overview(configured, ["isa"]))
    assert result["status"] == "complete" and result["selected_accounts"] == ["isa"]
    assert len(calls) == 1 and result["accounts"][0]["investments_value"] == "1000.00"

    result = asyncio.run(portfolio_overview(configured))
    assert result["selection"] == "all_configured" and result["status"] == "complete"
    assert len(calls) == 3
    assert result["grouped_totals"] == [
        {
            "environment": "live",
            "currency": "GBP",
            "account_labels": ["invest", "isa"],
            "available_cash": "10.1100000000000000001",
            "investments_value": "1020.22",
            "total_value": "1033.3300000000000000001",
        }
    ]
    assert "24601234" not in json.dumps(result) and "24601235" not in json.dumps(result)


def test_duplicate_aliases_deduplicate_by_identity_within_environment():
    calls = []
    configured = {
        "demo": broker(summary(), calls, env="demo"),
        "a": broker(summary(), calls),
        "b": broker(summary(), calls),
        "usd": broker(summary(5432, "USD"), calls),
    }
    result = asyncio.run(portfolio_overview(configured, ["b", "a", "usd", "demo"]))
    assert result["status"] == "complete" and len(calls) == 4
    assert [
        (r["environment"], r["currency"], r["account_labels"])
        for r in result["grouped_totals"]
    ] == [
        ("live", "GBP", ["b"]),
        ("live", "USD", ["usd"]),
        ("demo", "GBP", ["demo"]),
    ]
    assert (
        result["accounts"][1]["status"] == "duplicate"
        and result["accounts"][1]["duplicate_of"] == "b"
    )
    assert result["accounts"][1]["total_value"] is None
    assert all(r["total_value"] == "33.33" for r in result["grouped_totals"])


@pytest.mark.parametrize("selected", [[], ["other"], ["a", "other"], ["a", "a"]])
def test_invalid_selection_rejected_before_any_request(selected):
    calls = []
    with pytest.raises(ValueError):
        asyncio.run(portfolio_overview({"a": broker(summary(), calls)}, selected))
    assert calls == []


def test_selection_bound_before_network():
    calls = []
    profiles = {f"a{n}": broker(summary(n), calls) for n in range(MAX_ACCOUNTS + 1)}
    with pytest.raises(ValueError, match="or fewer"):
        asyncio.run(portfolio_overview(profiles))
    assert calls == []


def test_unconfigured_and_failed_profiles_never_turn_partial_data_into_total():
    calls = []
    profiles = {
        "demo": broker(summary(), calls, env="demo"),
        "isa": broker(summary(), calls, configured=False),
        "failed": broker(httpx.Response(403, text="do not echo 919191"), calls),
    }
    result = asyncio.run(portfolio_overview(profiles, ["isa", "demo", "failed"]))
    assert (
        result["status"] == "partial"
        and result["grouped_totals"] is None
        and len(calls) == 2
    )
    assert [r["status"] for r in result["accounts"]] == [
        "unconfigured",
        "included",
        "error",
    ]
    assert result["accounts"][1]["available_cash"] == "10.11" and "919191" not in str(
        result
    )

    result = asyncio.run(
        portfolio_overview({"demo": profiles["demo"], "isa": profiles["isa"]})
    )
    assert (
        result["status"] == "complete"
        and result["selected_accounts"] == ["demo"]
        and result["unconfigured_accounts"] == ["isa"]
    )
    result = asyncio.run(portfolio_overview({"isa": profiles["isa"]}))
    assert (
        result["status"] == "unavailable"
        and result["accounts"] == []
        and result["grouped_totals"] is None
    )


@pytest.mark.parametrize(
    "bad",
    [None, "NaN", "-Infinity", True, "£42", "1e9999999999999999999999", " 5", "1_000"],
)
def test_missing_or_invalid_numbers_are_unknown_not_zero(bad):
    calls = []
    result = asyncio.run(
        portfolio_overview({"only": broker(summary(current=bad), calls)})
    )
    row = result["accounts"][0]
    assert result["status"] == "partial" and result["grouped_totals"] is None
    assert row["investments_value"] is None and row["available_cash"] == "10.11"
    assert row["missing_or_invalid"] == ["investments_value"]


@pytest.mark.parametrize("wrong_id", [None, True, "1234", -1])
def test_missing_identity_prevents_consolidation(wrong_id):
    responses = {"a": broker(summary(), []), "other": broker(summary(wrong_id), [])}
    result = asyncio.run(portfolio_overview(responses))
    assert result["grouped_totals"] is None and result["status"] == "partial"
    assert result["accounts"][1]["missing_or_invalid"] == ["account identity"]


def test_valid_alias_can_provide_value_but_currency_conflict_blocks_totals():
    profiles = {
        "missing": broker(summary(cash=None), []),
        "complete": broker(summary(), []),
    }
    result = asyncio.run(portfolio_overview(profiles))
    assert result["status"] == "complete" and result["grouped_totals"][0][
        "account_labels"
    ] == ["complete"]
    assert result["accounts"][0]["duplicate_of"] == "complete"
    profiles["different"] = broker(summary(currency="USD"), [])
    result = asyncio.run(portfolio_overview(profiles))
    assert result["grouped_totals"] is None and {
        r["status"] for r in result["accounts"]
    } == {"conflict"}


def test_numeric_broker_json_exponents_and_missing_currency():
    data = b'{"id":7621,"currency":"USD","cash":{"availableToTrade":-2E-4},"investments":{"currentValue":0},"totalValue":1.23456789012345678901234567890123456789}'
    result = asyncio.run(
        portfolio_overview({"a": broker(httpx.Response(200, content=data), [])})
    )
    totals = result["grouped_totals"][0]
    assert totals["available_cash"] == "-0.0002" and totals["investments_value"] == "0"
    assert totals["total_value"] == "1.23456789012345678901234567890123456789"
    result = asyncio.run(portfolio_overview({"a": broker(summary(currency=None), [])}))
    assert result["grouped_totals"] is None and result["accounts"][0][
        "missing_or_invalid"
    ] == ["currency"]


def test_mcp_selection_returns_only_requested_profile():
    from mcp.shared.memory import create_connected_server_and_client_session

    from trading212_mcp.server import create_server

    calls = []
    server = create_server(
        {"primary": broker(summary(), calls), "isa": broker(summary(32), calls)}
    )

    async def check():
        async with create_connected_server_and_client_session(server) as client:
            single = await client.call_tool(
                "get_portfolio_overview", {"accounts": ["isa"]}
            )
            assert (
                single.structuredContent["selected_accounts"] == ["isa"]
                and len(calls) == 1
            )
            invalid = await client.call_tool(
                "get_portfolio_overview", {"accounts": ["isa", "isa"]}
            )
            assert invalid.isError and len(calls) == 1
            both = await client.call_tool("get_portfolio_overview", {})
            assert both.structuredContent["grouped_totals"][0]["account_labels"] == [
                "primary",
                "isa",
            ]
            assert len(calls) == 3

    asyncio.run(check())


def test_profile_requests_have_bounded_concurrency():
    async def check():
        active = 0
        peak = 0

        def connection(account_id):
            async def handler(request):
                nonlocal active, peak
                active += 1
                peak = max(peak, active)
                await asyncio.sleep(0)
                active -= 1
                return httpx.Response(200, json=summary(account_id))

            return Trading212(
                {"T212_API_KEY": "fixture-id", "T212_API_SECRET": "fixture-secret"},
                httpx.MockTransport(handler),
            )

        profiles = {f"alias{idx}": connection(idx) for idx in range(12)}
        result = await portfolio_overview(profiles)
        assert result["status"] == "complete" and 1 < peak <= 4
        assert len(result["grouped_totals"][0]["account_labels"]) == 12

    asyncio.run(check())
