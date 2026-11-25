---
name: analyze-stock
description: Evaluate a listed operating company's business, financial performance and valuation from public filings or supplied reports. Use for a single-stock thesis, earnings review or price-sensitivity question.
---

# Analyse a listed company

Answer the investor's question in the first paragraph. Name the issuer, security and evidence date. Identify the business result that would most change the conclusion. Match the depth to the question. An earnings update may need only one segment, one cash-flow check and the change in expectations.

## Establish the evidence

- Confirm the legal issuer, exchange, share class, quote unit and reporting currency. An ADR can represent several ordinary shares or a fraction of one. Resolve material ticker ambiguities before calculating a price multiple.
- Use the most recent annual report available by the requested research date, the subsequent interim filing if available, and material updates since that filing. For a historical analysis, use only information published by the cutoff. US domestic issuers generally use 10-K and 10-Q filings. Foreign private issuers may use 20-F and furnish interim information on 6-K. For a UK issuer, start with its investor-relations reports and regulatory announcements. Cite the specific filing, publication date, fiscal period and statement, note or page behind a figure. [SEC EDGAR](https://www.sec.gov/edgar/search/) · [FCA National Storage Mechanism](https://www.fca.org.uk/markets/primary-markets/regulatory-disclosures/national-storage-mechanism)
- If the user asks about a Trading 212 holding and the personal connector is available, use `list_positions(ticker=..., account=...)` for the selected holding. Use `search_instruments(query=...)` to resolve the exact broker ticker and ISIN when needed. For general company research, start with the public issuer identity. Keep position size, value, cost basis and account identifiers out of external searches. A holding’s `currentPrice` is per share in `instrument.currency`. Report the retrieval time if a separate quote timestamp is unavailable. Use an independently dated price for historical comparisons.
- The user's supplied filings or excerpts can support the same analysis offline. Identify which periods and statements they cover. Use a dated, publicly available exchange close or a supplied price for valuation, and label it with its date, currency and units. When a price or filing is missing, calculate the measures supported by the available evidence and name what would resolve the gap. A public issuer lookup needs only its public identity.

## Trace the business result to cash

Choose measures that explain how this company earns money. Start with a concrete driver such as units and price, retention and customer spend, or a regulated asset base. Connect it to segment revenue, reported profitability and cash generation. Distinguish disclosures, management guidance and your own assumptions.

| Question | Calculation or check |
| --- | --- |
| Did growth improve? | Compare equivalent fiscal periods. Revenue growth is current revenue divided by prior revenue minus one when the prior figure is positive. Inspect acquisitions, currency and business disposals before attributing a change to demand. |
| Did margins improve? | Divide reported operating profit by revenue in each period. Report the difference in percentage points. Reconcile material adjustments when using management's adjusted operating profit. |
| Did earnings convert to cash? | For an operating company, a useful free-cash-flow measure is cash from operations less cash purchases of property and equipment. Express capex as a positive cash outlay and identify other material capitalised investment. Explain major working-capital swings and share-based compensation or dilution. |
| Can the balance sheet support the thesis? | Inspect unrestricted cash, debt maturities, interest cost and material lease obligations. Specify the balances included in net debt. For a bank or insurer, use sector-appropriate evidence such as regulatory capital and credit losses or underwriting results. |

For trailing-twelve-month revenue or operating cash flow, use the latest full year plus current year-to-date minus comparable prior year-to-date. Match period lengths, accounting basis, restatements and reporting units. Balance sheet values are point-in-time figures. Per-share ratios and margins need consistent denominators and generally cannot be added across periods.

## Explain the price being paid

Use a valuation measure suited to the firm's economics. With positive attributable earnings, calculate price divided by diluted EPS for the same share unit and currency. For enterprise measures, start with the market value of all relevant equity classes, add debt, preferred equity and non-controlling interests as applicable, then deduct unrestricted cash. State lease treatment. Match the resulting enterprise value to operating metrics covering the same consolidated businesses. With a loss or near-zero earnings, choose a meaningful alternative and explain its limitation.

When the question concerns future value, show what the price requires. For example, multiply a clearly assumed future diluted EPS by a stated P/E multiple to give an illustrative price at that future date. Vary the operating assumption and the multiple independently. Include the horizon, dilution and currency assumptions so a reader can reproduce the numbers. Discuss which observable business evidence would move the assessment. For peer comparisons, align sector, fiscal period, growth profile and accounting definitions, and cite the sources for the comparison.

In the answer, put dated reported figures beside their comparison period, separate scenarios from observed results, and link the primary sources beside the claims they support. If a missing fact prevents a valuation, give the strongest business conclusion the available data supports.
