"""Trading 212 HTTP client, portfolio data and single-use limit order previews."""

import asyncio
import json
import math
import re
import secrets
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Any, Literal

import httpx

EQUITY = "/api/v0/equity"
HOSTS = {env: f"https://{env}.trading212.com" for env in ("demo", "live")}
READ_PATHS = {
    f"{EQUITY}/{suffix}"
    for suffix in (
        "account/summary",
        "positions",
        "orders",
        "metadata/instruments",
        "history/orders",
        "history/dividends",
        "history/transactions",
    )
}
History = Literal["orders", "dividends", "transactions"]
Side = Literal["buy", "sell"]
UNCERTAIN = "Order outcome is unknown. Check pending orders and order history before placing another order."


@dataclass(frozen=True)
class OrderPreview:
    expires: float
    ticker: str
    side: Side
    quantity: str
    limit_price: str
    quote_currency: str
    account_currency: str
    account_suffix: str

    def details(self) -> dict[str, Any]:
        with localcontext() as ctx:
            ctx.prec = 70
            at_limit = format(Decimal(self.quantity) * Decimal(self.limit_price), "f")
        return {
            "account_ending": self.account_suffix,
            "ticker": self.ticker,
            "side": self.side,
            "quantity": self.quantity,
            "limit_price": self.limit_price,
            "quote_currency": self.quote_currency,
            "value_at_limit_before_fees_or_fx": at_limit,
            "account_currency": self.account_currency,
            "time_validity": "DAY",
        }

    def payload(self) -> bytes:
        # The broker requires JSON numbers. The validated decimal strings preserve
        # their exact numeric value, including fractional shares, on the wire.
        quantity = ("-" if self.side == "sell" else "") + self.quantity
        return (
            f'{{"ticker":{json.dumps(self.ticker)},"quantity":{quantity},'
            f'"limitPrice":{self.limit_price},"timeValidity":"DAY"}}'
        ).encode("ascii")


def check_page(path: str, endpoint: str) -> str:
    """Confine the continuation to its original feed, preserving the broker's encoded cursor."""
    if (
        not isinstance(path, str)
        or not path
        or len(path) > 4096
        or not path.isascii()
        or not path.isprintable()
        or any(char in path for char in (" ", "#", "\\"))
    ):
        raise ValueError("Invalid next_page_path for this Trading 212 history feed.")

    prefix = endpoint + "?"
    bare = not path.startswith(prefix)
    if bare and endpoint != f"{EQUITY}/history/transactions":
        raise ValueError("Invalid next_page_path for this Trading 212 history feed.")
    # The cash feed sometimes returns just the query, with or without a leading '?'.
    query = path.removeprefix("?") if bare else path.removeprefix(prefix)
    params = {}
    for part in query.split("&"):
        key, separator, value = part.partition("=")
        if (
            not separator
            or not value
            or key in params
            or not re.fullmatch(r"[a-zA-Z0-9_]+", key)
        ):
            raise ValueError("Invalid parameters in next_page_path.")
        if bare and (
            key not in {"limit", "time", "cursor"} or "/" in value or "?" in value
        ):
            raise ValueError("Invalid parameters in next_page_path.")
        params[key] = value
    if "cursor" not in params or (
        "limit" in params and not re.fullmatch(r"[1-9]|[1-4][0-9]|50", params["limit"])
    ):
        raise ValueError("Invalid cursor or limit in next_page_path.")
    return prefix + query


def rate_limit_message(headers: httpx.Headers) -> str:
    retry = headers.get("retry-after", "")
    reset = headers.get("x-ratelimit-reset", "")
    if re.fullmatch(r"[0-9]{1,10}", retry):
        when = f"in {retry} seconds"
    elif re.fullmatch(r"[0-9]{1,12}", reset):
        when = f"in {max(1, math.ceil(int(reset) - time.time()))} seconds"
    else:
        when = "after the broker's rate window resets"
    return f"Trading 212 rate limit reached. Try again {when}."


class Trading212:
    def __init__(
        self,
        settings: Mapping[str, str],
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.env = settings.get("T212_ENV", "demo").strip().lower()
        if self.env not in HOSTS:
            raise ValueError("T212_ENV must be demo or live.")
        writes = settings.get("T212_ENABLE_WRITES", "false").strip().lower()
        if writes not in ("true", "false"):
            raise ValueError("T212_ENABLE_WRITES must be true or false.")
        self.writes = writes == "true"
        self.key = settings.get("T212_API_KEY", "").strip()
        self.secret = settings.get("T212_API_SECRET", "").strip()
        self.transport = transport
        self.previews: dict[str, OrderPreview] = {}
        self.catalog: list[dict] = []
        self.catalog_expires = 0.0
        self.catalog_lock = asyncio.Lock()

    @property
    def credentials_configured(self) -> bool:
        return bool(self.key and self.secret)

    def status(self) -> dict[str, Any]:
        return {
            "environment": self.env,
            "credentials_configured": self.credentials_configured,
            "writes_enabled": self.writes,
        }

    async def request(self, path: str, *, order: OrderPreview | None = None) -> Any:
        if not self.credentials_configured:
            raise ValueError(
                "Set T212_API_KEY and T212_API_SECRET for the selected T212_ENV, then restart."
            )
        if order and (not self.writes or path != f"{EQUITY}/orders/limit"):
            raise ValueError("Order placement is disabled.")
        if order is None and path.partition("?")[0] not in READ_PATHS:
            raise ValueError("Unknown read endpoint.")
        try:
            async with httpx.AsyncClient(
                auth=(self.key, self.secret),
                trust_env=False,
                follow_redirects=False,
                timeout=15,
                transport=self.transport,
            ) as client:
                url = HOSTS[self.env] + path
                if order:
                    response = await client.post(
                        url,
                        content=order.payload(),
                        headers={"Content-Type": "application/json"},
                    )
                else:
                    response = await client.get(url)
        except httpx.RequestError:
            raise ValueError(
                UNCERTAIN
                if order
                else "Could not reach Trading 212. Try the read again."
            ) from None
        if response.status_code == 429:
            raise ValueError(rate_limit_message(response.headers))
        if response.status_code == 401:
            raise ValueError(
                f"Trading 212 rejected the key pair for {self.env}. Check the account and environment."
            )
        if response.status_code == 403:
            raise ValueError(
                "Trading 212 denied access. Check the key's scopes and IP restrictions."
            )
        if not response.is_success:
            if order and (response.status_code >= 500 or response.status_code == 408):
                raise ValueError(UNCERTAIN)
            raise ValueError(
                f"Trading 212 returned HTTP {response.status_code}. Check the request in the broker app."
            )
        try:
            # Decimal-valued JSON numbers become strings for lossless transport to MCP clients.
            data = response.json(parse_float=str)
        except (ValueError, UnicodeDecodeError):
            raise ValueError(
                UNCERTAIN if order else "Trading 212 returned an unreadable response."
            ) from None
        if order and (not isinstance(data, dict) or not data.get("id")):
            raise ValueError(UNCERTAIN)
        return data

    async def instruments(self) -> list[dict]:
        async with self.catalog_lock:
            if time.monotonic() >= self.catalog_expires:
                data = await self.request(f"{EQUITY}/metadata/instruments")
                if not isinstance(data, list) or not all(
                    isinstance(item, dict) for item in data
                ):
                    raise ValueError(
                        "Trading 212 returned an unreadable instrument list."
                    )
                self.catalog = data
                self.catalog_expires = time.monotonic() + 600
            return self.catalog

    async def search_instruments(self, query: str) -> list[dict]:
        needle = query.strip().casefold()
        if not needle:
            raise ValueError("Enter part of an instrument name, ticker or ISIN.")
        return [
            item
            for item in await self.instruments()
            if any(
                needle in str(item.get(field, "")).casefold()
                for field in ("name", "shortName", "ticker", "isin")
            )
        ]

    async def history(
        self, kind: History, limit: int, next_page_path: str | None
    ) -> dict[str, Any]:
        endpoint = f"{EQUITY}/history/{kind}"
        path = (
            check_page(next_page_path, endpoint)
            if next_page_path is not None
            else f"{endpoint}?limit={limit}"
        )
        page = await self.request(path)
        if not isinstance(page, dict) or not isinstance(page.get("items"), list):
            raise TypeError("Trading 212 returned an unreadable history page.")
        result = {
            "environment": self.env,
            "items": page["items"],
            "next_page_path": None,
        }
        if "nextPagePath" in page and page["nextPagePath"] is None:
            return result
        try:
            next_path = check_page(page.get("nextPagePath"), endpoint)
        except ValueError:
            result["coverage_warning"] = (
                "Trading 212 returned an unusable cursor. History coverage is incomplete."
            )
        else:
            if next_path == path:
                result["coverage_warning"] = (
                    "Trading 212 repeated its cursor. History coverage is incomplete."
                )
            else:
                result["next_page_path"] = next_path
        return result

    async def preview(
        self, ticker: str, side: Side, quantity: str, limit_price: str
    ) -> dict[str, Any]:
        if not self.writes:
            raise ValueError("Order placement is disabled.")
        if side not in ("buy", "sell"):
            raise ValueError("Choose buy or sell.")
        for value in (quantity, limit_price):
            if (
                not re.fullmatch(r"(0|[1-9][0-9]*)(\.[0-9]+)?", value)
                or len(value) > 32
                or Decimal(value) <= 0
            ):
                raise ValueError(
                    "Provide positive decimal strings for quantity and limit price."
                )
        instrument = next(
            (i for i in await self.instruments() if i.get("ticker") == ticker), None
        )
        if not instrument or not instrument.get("currencyCode"):
            raise ValueError(
                "Unknown ticker or quote currency. Use search_instruments for the exact Trading 212 ticker."
            )
        account = await self.request(f"{EQUITY}/account/summary")
        if (
            not isinstance(account, dict)
            or not account.get("currency")
            or not account.get("id")
        ):
            raise ValueError("Could not verify the trading account and its currency.")
        now = time.monotonic()
        self.previews = {
            key: value for key, value in self.previews.items() if value.expires > now
        }
        preview = OrderPreview(
            now + 300,
            ticker,
            side,
            quantity,
            limit_price,
            instrument["currencyCode"],
            account["currency"],
            str(account["id"])[-4:],
        )
        preview_id = secrets.token_urlsafe(18)
        self.previews[preview_id] = preview
        return {
            "environment": self.env,
            "account_label": "primary",
            "preview_id": preview_id,
            "expires_in_seconds": 300,
            **preview.details(),
        }

    async def submit(
        self, preview_id: str, confirm: Callable[[str], Awaitable[bool]]
    ) -> dict[str, Any]:
        # Pop before any await so concurrent submissions cannot both submit the same order.
        preview = self.previews.pop(preview_id, None)
        if not self.writes or not preview or time.monotonic() >= preview.expires:
            raise ValueError(
                "Order preview is unavailable or expired. Create a new preview."
            )
        environment = (
            "LIVE — REAL MONEY" if self.env == "live" else "DEMO — PAPER TRADING"
        )
        note = (
            f"{environment}, primary account ending {preview.account_suffix}. "
            f"{preview.side.upper()} {preview.quantity} shares of {preview.ticker} "
            f"at a DAY limit of {preview.limit_price} {preview.quote_currency} per share. "
            f"Value at the limit is {preview.details()['value_at_limit_before_fees_or_fx']} {preview.quote_currency} "
            f"before fees or FX. Account currency is {preview.account_currency}."
        )
        if await confirm(note) is not True:
            return {
                "environment": self.env,
                "account_label": "primary",
                "submitted": False,
                "reason": "Approval was declined or cancelled.",
            }
        if time.monotonic() >= preview.expires:
            raise ValueError("Preview expired during approval. Order was not sent.")
        receipt = await self.request(f"{EQUITY}/orders/limit", order=preview)
        return {
            "environment": self.env,
            "account_label": "primary",
            "submitted": True,
            "order": receipt,
        }
