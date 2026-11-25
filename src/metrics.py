"""Local, source-labelled arithmetic for comparable public-company financials."""

from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Amount = Annotated[
    Decimal, Field(max_digits=30, decimal_places=12, allow_inf_nan=False)
]
Nonnegative = Annotated[Amount, Field(ge=0)]
Source = Annotated[str, Field(min_length=1, max_length=1000)]
Currency = Annotated[
    str,
    Field(
        pattern=r"^[A-Z]{3}$",
        description="Three-letter reporting currency. Use major units for all per-share figures.",
    ),
]
Scale = Literal["units", "thousands", "millions", "billions"]
PeriodKind = Literal["quarter", "half_year", "nine_months", "year", "trailing_year"]
HUNDRED = Decimal(100)


class FinancialPeriod(BaseModel):
    """One reporting period. Use the same issuer, share class and accounting basis for both periods."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    period_kind: PeriodKind
    period_start: date
    period_end: date
    source: Source = Field(
        description="Filing URL or supplied document title and page or note."
    )
    revenue: Amount | None = None
    operating_profit: Amount | None = None
    diluted_eps: Amount | None = Field(
        default=None,
        description="Reported (GAAP/IFRS) diluted EPS in major currency units per share, without amount scaling.",
    )
    operating_cash_flow: Amount | None = None
    capex_outflow: Nonnegative | None = Field(
        default=None,
        description="Cash spent on capital expenditure, entered as a nonnegative outflow magnitude.",
    )
    total_debt: Nonnegative | None = Field(
        default=None,
        description="Interest-bearing debt. Apply the same lease treatment in both periods.",
    )
    unrestricted_cash: Nonnegative | None = None

    @model_validator(mode="after")
    def check_dates(self):
        if self.period_start >= self.period_end:
            raise ValueError("A reporting period must start before it ends.")
        return self


class Valuation(BaseModel):
    """Closing price and reported trailing-year diluted EPS for the same security and currency."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    share_price: Annotated[Amount, Field(gt=0)]
    price_date: date
    price_source: Source
    trailing_diluted_eps: Amount = Field(
        description="Full trailing-year reported diluted EPS known at the price observation, in the same share unit and currency as the closing price."
    )
    eps_period_end: date
    eps_available_on: date = Field(
        description="Date this trailing EPS was published. For a same-day release verify that EPS was known by the price observation."
    )
    eps_source: Source
    eps_known_by_close: Annotated[bool, Field(strict=True)] | None = Field(
        default=None,
        description="For earnings published on the price date, confirm from the release and exchange times that the EPS was public by the close.",
    )

    @model_validator(mode="after")
    def check_dates(self):
        if not self.eps_period_end <= self.eps_available_on <= self.price_date:
            raise ValueError(
                "Trailing EPS must have been published after or on period end and known by the price date."
            )
        if self.eps_known_by_close is False or (
            self.price_date == self.eps_available_on
            and self.eps_known_by_close is not True
        ):
            raise ValueError(
                "Verify that trailing EPS was public by the observed close. For a same-day release set eps_known_by_close=true after checking times, or use a later close."
            )
        return self


def _subtract(a: Decimal | None, b: Decimal | None) -> Decimal | None:
    return None if a is None or b is None else a - b


def _number(value: Decimal | None, *, ratio: bool = False) -> str | None:
    if value is None:
        return None
    if ratio:
        value = value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)
    if value.is_zero():
        return "0"
    return format(value.normalize(), "f")


def _values(period: FinancialPeriod) -> dict[str, Decimal | None]:
    margin = None
    if (
        period.operating_profit is not None
        and period.revenue is not None
        and period.revenue > 0
    ):
        margin = HUNDRED * period.operating_profit / period.revenue
    return {
        "revenue": period.revenue,
        "diluted_eps": period.diluted_eps,
        "operating_margin": margin,
        "free_cash_flow": _subtract(period.operating_cash_flow, period.capex_outflow),
        "net_debt": _subtract(period.total_debt, period.unrestricted_cash),
    }


def _source(period: FinancialPeriod) -> dict:
    return period.model_dump(
        mode="json", include={"period_kind", "period_start", "period_end", "source"}
    )


def calculate_stock_metrics(
    current: FinancialPeriod,
    currency: Currency,
    amount_scale: Scale,
    prior: FinancialPeriod | None = None,
    valuation: Valuation | None = None,
) -> dict[str, Any]:
    """Calculate a local scorecard from supplied filing inputs. Currency and scale apply to both periods. EPS and price always use major currency units per share. An optional P/E requires explicitly supplied trailing-year diluted EPS and a dated close. Returns decimal strings and nulls for unavailable measures."""
    current_days = (current.period_end - current.period_start).days
    if prior is not None:
        prior_days = (prior.period_end - prior.period_start).days
        if (
            prior.period_kind != current.period_kind
            or prior.period_end >= current.period_end
            or abs(prior_days - current_days) > 7
            or (
                current.period_kind != "trailing_year"
                and prior.period_end >= current.period_start
            )
        ):
            raise ValueError(
                "Use earlier comparable periods of the same kind and similar length (within seven days). Only rolling trailing years may overlap. Otherwise run each period separately."
            )

    amount_unit = currency if amount_scale == "units" else f"{currency} {amount_scale}"
    units = {
        "revenue": amount_unit,
        "diluted_eps": f"{currency}/share",
        "operating_margin": "%",
        "free_cash_flow": amount_unit,
        "net_debt": amount_unit,
        "trailing_pe": "multiple",
    }
    notes: list[str] = []
    rows = []
    with localcontext() as ctx:
        ctx.prec = 80
        latest = _values(current)
        previous = _values(prior) if prior else {}
        latest["trailing_pe"] = None
        if valuation is not None:
            if valuation.trailing_diluted_eps > 0:
                latest["trailing_pe"] = (
                    valuation.share_price / valuation.trailing_diluted_eps
                )
            else:
                notes.append(
                    "Trailing P/E is unavailable with zero or negative trailing diluted EPS."
                )

        for metric, now in latest.items():
            then = previous.get(metric)
            unit = units[metric]
            change = _subtract(now, then)
            change_unit = "percentage points" if metric == "operating_margin" else unit
            if (
                metric in ("revenue", "diluted_eps")
                and now is not None
                and then is not None
            ):
                if then > 0 and now >= 0:
                    change = HUNDRED * (now - then) / then
                    change_unit = "%"
                else:
                    notes.append(
                        f"{metric} change is in absolute units because the prior value was nonpositive or the current value is negative."
                    )
            rows.append(
                {
                    "metric": metric,
                    "current": _number(now, ratio=unit in ("%", "multiple")),
                    "prior": _number(then, ratio=unit in ("%", "multiple")),
                    "unit": unit,
                    "change": _number(
                        change, ratio=change_unit in ("%", "percentage points")
                    ),
                    "change_unit": change_unit,
                }
            )

    return {
        "currency": currency,
        "amount_scale": amount_scale,
        "current_period": _source(current),
        "prior_period": _source(prior) if prior else None,
        "valuation": valuation.model_dump(mode="json") if valuation else None,
        "rows": rows,
        "notes": notes,
    }
