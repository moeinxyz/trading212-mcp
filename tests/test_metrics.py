from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from trading212_mcp.metrics import FinancialPeriod, Valuation, calculate_stock_metrics


def period(year=2025, **figures):
    inputs = {
        "period_start": date(year, 1, 1),
        "period_end": date(year, 12, 31),
        "period_kind": "year",
        "source": "Fictional annual report, consolidated statements",
    }
    return FinancialPeriod(**(inputs | figures))


def valuation(**fields):
    inputs = {
        "share_price": "12",
        "price_date": "2026-02-03",
        "price_source": "Fictional closing price",
        "trailing_diluted_eps": "1",
        "eps_period_end": "2025-12-31",
        "eps_available_on": "2026-02-02",
        "eps_source": "Fictional annual report, EPS note",
    }
    return Valuation(**(inputs | fields))


def by_metric(output):
    return {row["metric"]: row for row in output["rows"]}


def test_fictional_filing_scorecard_preserves_period_source_and_per_share_units():
    current = period(
        revenue=120,
        operating_profit="16.8",
        diluted_eps=1,
        operating_cash_flow=14,
        capex_outflow=9,
        total_debt=45,
        unrestricted_cash=25,
    )
    prior = period(
        2024,
        revenue=100,
        operating_profit=15,
        diluted_eps=1,
        operating_cash_flow=14,
        capex_outflow=6,
        total_debt=50,
        unrestricted_cash=20,
    )
    result = calculate_stock_metrics(current, "GBP", "millions", prior, valuation())
    assert result["current_period"]["source"] == current.source
    assert result["prior_period"]["period_end"] == "2024-12-31"
    assert result["valuation"]["price_source"] == "Fictional closing price"
    rows = by_metric(result)
    assert [
        (row["current"], row["prior"], row["change"], row["unit"], row["change_unit"])
        for row in rows.values()
    ] == [
        ("120", "100", "20", "GBP millions", "%"),
        ("1", "1", "0", "GBP/share", "%"),
        ("14", "15", "-1", "%", "percentage points"),
        ("5", "8", "-3", "GBP millions", "GBP millions"),
        ("20", "30", "-10", "GBP millions", "GBP millions"),
        ("12", None, None, "multiple", "multiple"),
    ]


def test_missing_values_stay_unknown_but_explicit_zero_is_used():
    current = period(revenue=0, operating_profit=-2, diluted_eps="0.25", total_debt=1)
    result = by_metric(calculate_stock_metrics(current, "USD", "units"))
    assert result["revenue"]["current"] == "0"
    assert result["operating_margin"]["current"] is None
    assert result["net_debt"]["current"] is None
    assert result["free_cash_flow"]["current"] is None
    # The period EPS is never implicitly used for a trailing valuation.
    assert result["trailing_pe"]["current"] is None
    assert all(
        row["prior"] is None and row["change"] is None for row in result.values()
    )
    current = period(
        operating_cash_flow="-0.000001234567",
        capex_outflow=0,
        total_debt=0,
        unrestricted_cash="0.000000000099",
    )
    rows = by_metric(calculate_stock_metrics(current, "JPY", "billions"))
    assert rows["free_cash_flow"]["current"] == "-0.000001234567"
    assert rows["net_debt"]["current"] == "-0.000000000099"


@pytest.mark.parametrize(
    ("old", "new", "change"),
    [("-0.8", "-0.3", "0.5"), ("0", "0.2", "0.2"), ("0.3", "-0.1", "-0.4")],
)
def test_sign_changes_zero_and_losses_have_absolute_eps_changes(old, new, change):
    result = calculate_stock_metrics(
        period(diluted_eps=new),
        "GBP",
        "units",
        period(2024, diluted_eps=old),
        valuation(trailing_diluted_eps=new),
    )
    eps = by_metric(result)["diluted_eps"]
    assert (eps["change"], eps["change_unit"]) == (change, "GBP/share")
    if Decimal(new) < 0:
        assert by_metric(result)["trailing_pe"]["current"] is None
        assert any("P/E" in note for note in result["notes"])


@pytest.mark.parametrize(
    "fields",
    [
        {"capex_outflow": "-2"},
        {"source": " "},
        {"revenue": "Infinity"},
        {"operating_profit": "NaN"},
        {"period_end": "2024-01-01"},
        {"purchases": 1},
        {"total_debt": -20},
    ],
)
def test_reject_ambiguous_signs_invalid_numbers_missing_sources_and_unknown_fields(
    fields,
):
    with pytest.raises(ValidationError):
        period(**fields)


@pytest.mark.parametrize(
    "prior",
    [
        period(2024, period_kind="quarter", period_start="2024-10-01"),
        period(2024, period_start="2024-06-01"),
        period(2025, period_start="2024-12-01", period_end="2025-11-30"),
    ],
)
def test_incomparable_or_overlapping_periods_are_rejected(prior):
    with pytest.raises(ValueError, match="comparable"):
        calculate_stock_metrics(period(), "GBP", "millions", prior)


def test_rolling_matched_trailing_years_can_overlap():
    prior = period(
        2024,
        period_kind="trailing_year",
        period_start="2024-07-01",
        period_end="2025-06-30",
        revenue=90,
    )
    result = calculate_stock_metrics(
        period(period_kind="trailing_year", revenue=100), "GBP", "millions", prior
    )
    assert by_metric(result)["revenue"]["change"] == "11.111111"


@pytest.mark.parametrize(
    "fields",
    [
        {"trailing_diluted_eps": None},
        {"share_price": 0},
        {"eps_available_on": "2026-02-04"},
        {"eps_period_end": "2026-02-04"},
        {"eps_available_on": "2026-02-03"},
        {"eps_known_by_close": False},
    ],
)
def test_price_cannot_use_unpublished_or_ambiguous_same_day_eps(fields):
    with pytest.raises(ValidationError):
        valuation(**fields)


def test_same_day_publication_confirmed_before_close_and_old_loss():
    report = valuation(
        eps_available_on="2026-02-03", eps_known_by_close=True, trailing_diluted_eps=0
    )
    result = calculate_stock_metrics(
        period(diluted_eps="1"), "GBP", "units", valuation=report
    )
    assert by_metric(result)["trailing_pe"]["current"] is None
    assert result["valuation"]["eps_available_on"] == "2026-02-03"
