---
name: analyze-portfolio-performance
description: Measure portfolio return, benchmark divergence and historical drawdown with dated valuations and external cash flows. Use for how an account performed over a period or why its result differs from a benchmark.
---

# Measure portfolio performance over time

Specify the accounts, period, reporting currency and whether the question is about investment performance or the investor's cash-flow experience. Establish the beginning and ending total values, the timing of external flows, the frequency of valuations and the fee and income treatment. Current exposure and unrealised P&L alone cannot establish past performance.

## Establish the series

- Trading 212's `get_account_summary` and `list_positions` provide current values. `trading_history` provides pages of orders, dividends or account transactions. Follow returned cursors on the same account and feed, preserve coverage warnings and check that the period is covered. These tools do not supply a historical total-account valuation series. Use dated statements or valuations the user has provided when needed.
- Include cash and accrued or paid income consistently in opening and ending values. Treat deposits, withdrawals and in-kind transfers crossing the measured account boundary as external flows. Trades, FX exchanges within the account, and dividends or interest retained within it are internal. For consolidated accounts, reconcile transfers between included accounts and count each account once. Preserve fees and taxes reflected in a net return. Record how distributions paid out were handled.
- Convert valuations and flows using the FX rate at each observation or flow time and state the reporting currency. Mixing opening and closing FX rates indiscriminately distorts performance. Keep quantities, account IDs and private values out of public benchmark or FX lookups. Missing cash, unidentified transactions and gaps in valuations can invalidate a return.

## Choose a measure supported by the inputs

| User's question | Method |
| --- | --- |
| How much did the portfolio gain in currency? | End value minus start value minus signed net external inflows. Deposits are positive, withdrawals negative. This amount is distinct from the broker's realised gains on sold positions and covers the period specified. |
| What was the investment return? | With boundary valuations immediately before and after all external flows, calculate each no-flow segment as ending value divided by starting value minus one. Chain the factors by multiplication and subtract one. Divide by positive, meaningful capital. For a period with no flows, beginning and ending values suffice. |
| What if I only have endpoints and dated flows? | If requested, estimate Modified Dietz as `(end − start − ΣF) / (start + Σ(w × F))`, with `w` the fraction of the period remaining after a signed flow. State the day/timing convention and label this an estimate, especially with large flows or volatile prices. If the denominator is zero or unreliable, show the currency gain and missing inputs. |
| How did my own contributions perform? | Use a money-weighted return for dated investor flows when appropriate. From the investor's perspective, opening value and deposits are outflows, withdrawals and final value are inflows. State the annualisation basis. Sign changes can yield multiple or no meaningful IRRs. Distinguish an annualised IRR from a short-period cumulative return. |

## Compare like with like

Match dates, currency, income reinvestment, gross or net treatment and benchmark identity. Use the benchmark provider or fund manager for a dated total-return series, or use data the user supplied. If only a price index is available, label the missing dividends and qualify the comparison. Give the portfolio and benchmark cumulative returns and their difference in **percentage points**. A relative wealth ratio, if requested, is `(1 + portfolio return) / (1 + benchmark return) − 1`. Do not attribute a gap to asset selection, FX or fees without data that separates those effects.

For drawdown, build a positive wealth index from the flow-adjusted return series. At each observation compute wealth divided by its running peak minus one. Report the largest fall as a magnitude with peak and trough dates, recovery if observed, and sampling frequency. Month-end observations can miss deeper intra-month losses. A hypothetical reconstruction from today's holdings assumes those same holdings throughout and needs its own label. If evidence supports only a currency gain or an estimate, report that result and name the valuation or flow needed for a more precise answer. [CFA Institute performance calculation guidance](https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/)
