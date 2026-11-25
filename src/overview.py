"""Compare selected Trading 212 account summaries in their reported currencies."""

import asyncio
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from typing import Any

from .broker import EQUITY, Trading212

METRICS = ("available_cash", "investments_value", "total_value")
MAX_ACCOUNTS = 50
DECIMAL_BOUND = (
    100  # Keep malformed payloads from expanding to enormous decimal strings.
)
NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", re.ASCII)
Row = dict[str, Any]
Identity = tuple[str, int]


def amount(value: object) -> str | None:
    # The client decodes broker JSON numbers as int or exact decimal strings.
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return None
    text = str(value)
    if len(text) > DECIMAL_BOUND or not NUMBER.fullmatch(text):
        return None
    try:
        number = Decimal(text)
    except ArithmeticError:
        return None
    if (
        not number.is_finite()
        or abs(number.adjusted()) > DECIMAL_BOUND
        or abs(number.as_tuple().exponent) > DECIMAL_BOUND
    ):
        return None
    return format(number, "f")


async def read_account(
    label: str, api: Trading212, limit: asyncio.Semaphore
) -> tuple[Identity | None, Row]:
    row = {
        "account_label": label,
        "environment": api.env,
        "currency": None,
        **dict.fromkeys(METRICS),
    }
    if not api.credentials_configured:
        return None, {**row, "status": "unconfigured"}

    try:
        async with limit:
            summary = await api.request(f"{EQUITY}/account/summary")
    except Exception:
        # An individual broker request can fail independently. Keep errors, URLs and IDs private.
        return None, {
            **row,
            "status": "error",
            "message": "Summary request failed. Check this label with get_account_summary.",
        }
    if not isinstance(summary, dict):
        return None, {
            **row,
            "status": "incomplete",
            "message": "The broker returned an unreadable account summary.",
        }

    account_id = summary.get("id")
    identity = (
        (api.env, account_id)
        if type(account_id) is int and 0 <= account_id < 2**63
        else None
    )
    currency = summary.get("currency")
    if isinstance(currency, str) and re.fullmatch(r"[A-Z]{3}", currency):
        row["currency"] = currency
    cash, investments = summary.get("cash"), summary.get("investments")
    if isinstance(cash, dict):
        row["available_cash"] = amount(cash.get("availableToTrade"))
    if isinstance(investments, dict):
        row["investments_value"] = amount(investments.get("currentValue"))
    row["total_value"] = amount(summary.get("totalValue"))
    missing = [key for key in ("currency", *METRICS) if row[key] is None]
    if identity is None:
        missing.append("account identity")
    if missing:
        return identity, {**row, "status": "incomplete", "missing_or_invalid": missing}
    return identity, {**row, "status": "included"}


def mark_aliases(observations: list[tuple[Identity | None, Row]]) -> None:
    by_identity: dict[Identity, list[Row]] = {}
    for identity, row in observations:
        if identity is not None:
            by_identity.setdefault(identity, []).append(row)

    for aliases in by_identity.values():
        if len(aliases) < 2:
            continue
        currencies = {row["currency"] for row in aliases if row["currency"] is not None}
        if len(currencies) > 1:
            for row in aliases:
                row.update(
                    status="conflict",
                    message="The same broker account reported different primary currencies.",
                )
            continue
        representative = next(
            (row for row in aliases if row["status"] == "included"), aliases[0]
        )
        for row in aliases:
            if row is not representative:
                row.update(
                    status="duplicate", duplicate_of=representative["account_label"]
                )
                row.update(dict.fromkeys(METRICS))


def grouped_totals(rows: list[Row]) -> list[Row]:
    groups: dict[tuple[str, str], list[Row]] = {}
    for row in rows:
        if row["status"] == "included":
            groups.setdefault((row["environment"], row["currency"]), []).append(row)

    totals = []
    with localcontext() as ctx:
        # Enough places for both the largest integer and smallest fraction from all 50 accounts.
        ctx.prec = 2 * DECIMAL_BOUND + len(str(MAX_ACCOUNTS)) + 2
        for (environment, currency), members in groups.items():
            sums = {
                key: format(sum(Decimal(row[key]) for row in members), "f")
                for key in METRICS
            }
            totals.append(
                {
                    "environment": environment,
                    "currency": currency,
                    "account_labels": [row["account_label"] for row in members],
                    **sums,
                }
            )
    return totals


async def portfolio_overview(
    configured: Mapping[str, Trading212], accounts: list[str] | None = None
) -> Row:
    """Read one summary per selected label. Aggregate verified accounts once per environment and currency."""
    unconfigured = [
        label for label, api in configured.items() if not api.credentials_configured
    ]
    if accounts is None:
        selected = [
            label for label, api in configured.items() if api.credentials_configured
        ]
    else:
        if not accounts or any(label not in configured for label in accounts):
            raise ValueError(
                "Select at least one existing account label from trading_status."
            )
        if len(set(accounts)) != len(accounts):
            raise ValueError("Each selected account label must occur only once.")
        selected = list(accounts)
    if len(selected) > MAX_ACCOUNTS:
        raise ValueError(f"Select {MAX_ACCOUNTS} account labels or fewer per overview.")

    limit = asyncio.Semaphore(4)
    observed = list(
        await asyncio.gather(
            *(read_account(label, configured[label], limit) for label in selected)
        )
    )
    mark_aliases(observed)
    rows = [row for _, row in observed]
    complete = bool(rows) and all(
        row["status"] in {"included", "duplicate"} for row in rows
    )
    has_data = any(row[key] is not None for row in rows for key in METRICS)
    status = "complete" if complete else "partial" if has_data else "unavailable"
    return {
        "status": status,
        "selection": "all_configured" if accounts is None else "explicit",
        "selected_accounts": selected,
        "unconfigured_accounts": unconfigured,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "accounts": rows,
        "grouped_totals": grouped_totals(rows) if complete else None,
    }
