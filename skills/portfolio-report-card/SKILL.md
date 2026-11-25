---
name: portfolio-report-card
description: Give a beginner a plain-English portfolio scorecard across the Invest and ISA accounts they choose. Use for an overall review that connects returns, concentration, company earnings, opportunities and dated analyst signals.
---

# Explain how my portfolio is doing

Start with the strongest conclusion supported by the data. Name the accounts, date, reporting currency and the time period used for returns. Give the matrix four columns named **Question**, **Result**, **What it means** and **Evidence or next check**. Lead with what changed in the user's money. Use ordinary language and define unfamiliar terms where they first appear.

## Build the matrix

1. **What do I have?** Discover account labels with `trading_status`. Use `get_portfolio_overview` for the requested labels, or all configured accounts when the user wants everything. Report coverage, omissions and duplicate labels. Keep practice money and different currencies in separate groups. Use the overview's `available_cash` or the account's `cash.availableToTrade` for cash available to trade. Other cash can be reserved for orders or held in Pies.
2. **How did my investments perform?** For an explicit period, look for opening and ending valuations and external cash flows. Use the performance skill's method to separate investment gain from contributions. Compare with a suitable total-return benchmark on the same dates, currency and income basis. If the only evidence is current holdings, give current value and label the period return **Unknown**. Say which missing observation would settle it.
3. **What could hurt me most?** Fetch current positions for each distinct included account. State the largest evidenced issuer exposure, including identified holdings inside funds. Illustrate one clear price or FX shock in cash terms. State what fraction you could look through. A listing currency is insufficient evidence for a business's economic currency exposure.
4. **What do the companies' results say?** Select one or two material operating-company exposures. Use the company metrics skill and cite the filing. Explain EPS as profit attributable to common shareholders per share. Diluted EPS also reflects applicable potential shares. Compare the same accounting basis and fiscal period. Company EPS does not measure the user's personal return. For an ETF or cash-only portfolio, use fund exposure or yield information as appropriate.
5. **What is worth checking next?** Use the opportunities skill to pick one material, testable idea with a comparator, costs and a counterargument. Use the market-signals skill when a verified, dated change in analyst expectations or another published indicator bears on the question. Attribute the opinion and show what could disprove it. Where sources are unavailable, record the gap.

Choose rows that help answer the actual question. Label facts, estimates and scenarios visibly. Use percentage points for gaps between percentages. Keep knowledge gaps in words rather than turning them into a zero, grade or invented overall score. Close with one question the user can act on or one document that would improve the answer. Use public identifiers alone in external searches. This review never requests an order.
