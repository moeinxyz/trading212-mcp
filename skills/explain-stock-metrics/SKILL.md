---
name: explain-stock-metrics
description: Explain EPS and other company metrics to a beginner in a plain-English earnings scorecard. Use for a side-by-side assessment of business results, cash, debt, expectations and share valuation.
---

# Explain a company's earnings scorecard

Answer two questions up front. Is the business improving, and what price are shareholders paying for those results? Give one piece of evidence for each and name the biggest uncertainty. When asked about just one metric, explain it with the company’s own numbers. For an overall review, build the matrix below and add measures that matter for that business.

## Find the right numbers

Confirm issuer, share class, reporting currency, fiscal period and cutoff date. Start with the issuer's filed statements, EPS note and earnings release. Compare the same quarter last year for seasonal businesses, or two comparable full years. Use restated comparatives when available. Label quarter, year-to-date and trailing year explicitly. State amounts in thousands or millions and prices in their quote currency and unit. The broker's current position price can help identify a holding. It supplies neither a historical earnings estimate nor company accounts. Public searches need only the issuer or security identity. With supplied documents alone, say what they cover. [SEC guide to reading filings](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/how-read)

If available, use `calculate_stock_metrics` for the arithmetic. Supply the current and, if available, comparable prior figures from the same financial statements, plus trailing diluted EPS and a dated share price when applicable. Align currencies, units, time periods, share class and EPS basis first. The tool can compute revenue and EPS growth, operating margin, free cash flow, net debt and trailing P/E. Add sector measures and interpret material changes from the filed notes. The tool can calculate a ratio from supplied numbers without establishing that those numbers are comparable.

## Start with this matrix

Replace the fictional numbers with sourced figures. The example compares two full years for an industrial company. Amounts are in £ millions except pounds per share, percentages and multiples. In a real scorecard, cite the filing page or note beside the figures and date each valuation price. Use specific interpretations such as “improving”, “mixed” or “insufficient data” and explain them. Avoid averaging unrelated metrics into a numerical grade.

| Question and measure | Prior year | Latest year | What changed in plain English |
| --- | ---: | ---: | --- |
| Are sales growing? Revenue | 100 | 120 | Customers generated 20% more revenue. Check prices, volume and acquisitions to learn why. |
| Does each sale earn more? Operating margin | 15% | 14% | Operating profit rose from 15 to 16.8, but each £1 of sales generated 1p less operating profit. |
| What did one share earn? Basic / diluted EPS | £1.05 / £1.00 | £1.09 / £1.00 | Profit available to ordinary holders grew from 10 to 12. The diluted share count also grew 20%, leaving diluted EPS flat. |
| Is cash generation keeping up? Free cash flow | 8 | 5 | Operating cash stayed at 14. Cash spent on equipment rose from 6 to 9. |
| How much debt is left after cash? Net debt | 30 | 20 | Borrowings less unrestricted cash fell by 10. Check when the debt is due. |
| What does the price assume? Trailing price/earnings | 10× | 12× | At the two observation dates, the price rose from £10 to £12 for the same £1 of annual diluted earnings. |

Here revenue grew and net debt fell. The benefit to each diluted share stalled, investment absorbed more cash, and the market price rose. Whether the equipment spending will increase future operating profit is the next question to check.

## Explain EPS and earnings surprises accurately

- **Basic earnings per share (EPS)** is profit available to ordinary shareholders divided by the weighted-average ordinary shares outstanding during the period. It measures accounting profit per share. It does not tell the shareholder how much cash they receive. Look for preference dividends or multiple classes when the numerator differs from consolidated net profit.
- **Diluted EPS** includes the effects of potential shares that reduce EPS or increase loss per share under the applicable standard. Use the issuer’s diluted numerator and denominator. Convertible debt can require adjusting earnings as well as shares. Loss periods often show the same basic and diluted figure because potential shares would reduce the reported loss per share. Check the EPS note for excluded instruments. Buybacks, issuance or dilution can change EPS even if the business earns the same profit. [IAS 33, Earnings per Share](https://www.ifrs.org/issued-standards/list-of-standards/ias-33-earnings-per-share/)
- Lead with reported GAAP or IFRS earnings. If management highlights adjusted EPS, show the closest reported measure alongside it and explain the largest reconciled adjustments. Repeated exclusions warrant attention. Losses narrowing from £0.80 to £0.30 per share are a £0.50 improvement. For a negative, zero or tiny prior base, use the absolute movement and explain the sign. [SEC guidance on non-GAAP measures](https://www.sec.gov/rules-regulations/staff-guidance/corporation-finance-interpretations/non-gaap-financial-measures)
- **Surprise** asks how results compared with expectations at the time. Find a consensus published **before** the release. Match the period, currency, share unit, GAAP/adjusted basis and basic/diluted basis. Give both dated sources. Subtract estimate from actual for the per-share gap. With a meaningful positive estimate, divide the gap by that estimate for a percentage. A result of £1.08 against £1.10 is a £0.02 miss, about 1.8%. For a near-zero or negative estimate, use the per-share gap. If only prior guidance is available, compare with the guidance separately and mark consensus surprise unavailable.

## Choose the remaining measures

- **Profitability and cash.** Gross margin measures what remains after cost of sales. Operating margin uses reported operating profit. Net margin uses the specified net profit. Divide each by revenue and describe margin changes in percentage points. For many operating companies, free cash flow is operating cash flow less cash purchases of property and equipment. State the capex definition, material capitalised software, working capital and unusual cash items. Strong cash collection and delayed supplier payments have different implications. [SEC beginners’ guide to financial statements](https://www.sec.gov/about/reports-publications/investorpubsbegfinstmtguide)
- **Financial resilience.** Define the interest-bearing debt and unrestricted cash included in net debt, including lease treatment. Interest coverage can use operating profit divided by interest expense when the denominator is meaningful. Read maturities and liquidity alongside a debt ratio. For capital-intensive companies consider return on invested capital using after-tax operating profit and average invested capital, with a stated tax and capital basis.
- **Price versus business quality.** Trailing P/E is price per share divided by positive diluted EPS for the trailing year on the same share and currency basis. Match any ADR ratio and quote subunits. Forward P/E uses a dated forecast. Negative or near-zero earnings make P/E uninformative. Use a suitable alternative such as enterprise value to revenue, with margin and growth context. Compare with close business peers after aligning period, accounting treatment, leverage and growth. Cost basis and the investor's personal gain belong to a different question.
- **Sector fit.** For a bank, consider net interest margin, credit losses, return on equity and regulatory capital. For a property trust, examine the trust's reconciled funds-from-operations measure, occupancy and debt. For a pre-revenue company, use cash burn and available funding with explicit assumptions. An ETF needs fund-level measures such as fees, index tracking and holdings. Use issuer-specific definitions and mark inapplicable metrics clearly.

Finish with the strongest improvement, the most consequential weakness, the valuation context, and one figure to watch in the next report. Separate confirmed accounting results, management guidance and analyst estimates. Give sources for peer or market figures. Missing evidence belongs in the relevant matrix cell.
