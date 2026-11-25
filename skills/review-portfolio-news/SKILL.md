---
name: review-portfolio-news
description: Identify recent news that materially affects specified holdings. Verify what happened, distinguish direct and indirect exposure, and explain the financial mechanism and limits of any price attribution.
---

# Review news affecting a portfolio

Answer “What happened that matters to what I own?” Give the most consequential verified development first, the exposed holding and the reason the development matters. A routine news review is a point-in-time report.

## Define what was checked

Use the requested dates, time zone and research cutoff. For “recently” without a window, use the past seven calendar days and print the dates. Use supplied holdings or, with the Trading 212 MCP, call `trading_status`, `list_positions` and `get_account_summary` for the selected accounts. Check for duplicate accounts and separate demo from live. Record when the positions were observed. Today's holdings can identify which businesses to research. Establish quantities held at the time before attributing a historical portfolio gain or loss.

Identify issuers and fund share classes using name, ticker, ISIN and listing. External queries need only the public identity of one issuer or fund at a time. Keep account numbers, holdings lists, sizes, values and cost bases out of queries. If full coverage is impractical, say which issuers or percentage of value you checked, which you omitted and why. Without web access use dated documents the user supplied and bound the conclusion to them.

## Verify and connect the event

- Start with issuer investor relations, filed announcements, regulator decisions and fund-manager notices. Use reporting to discover a story, then open the underlying document. For a central bank or government decision, use its actual announcement and effective date. Record the event date, earliest verified publication time and source link. An article updated this week may describe a decision made months earlier. Group syndicated versions, amendments and company responses into one event, distinguishing what changed. [SEC EDGAR](https://www.sec.gov/edgar/search/) · [FCA National Storage Mechanism](https://www.fca.org.uk/markets/primary-markets/regulatory-disclosures/national-storage-mechanism)
- Explain the path to revenue, costs, financing, dilution, cash flow or a fund's mandate. Label management forecasts and proposed measures. A supplier, customer or competitor relationship needs evidence of the link. State the uncertainty if exposure size or the direction of impact is unknown.
- Use whole-position `walletImpact.currentValue` in `walletImpact.currency` for current invested value. For an underlying issuer, add direct exposure and each fund value times the disclosed constituent weight on its stated date. Count each holding once, include the unknown fraction separately and use one currency or per-currency subtotals. Affected exposure measures how much is invested in the issuer. To estimate a loss, supply a separate explicit shock and its assumptions.
- If asked whether the news moved a price, use dated, comparable prices around publication and the relevant market session. Check a benchmark, concurrent announcements, splits, dividends and FX. Label an observed move and any explanation separately. A measured move immediately after a release supports a timing observation. It cannot establish how much the event caused on its own.

For each material item, give the date, source, confirmed change, affected holdings, impact mechanism and one uncertainty that could change the interpretation. If nothing material was found, identify the window and sources checked so the reader understands the coverage.
