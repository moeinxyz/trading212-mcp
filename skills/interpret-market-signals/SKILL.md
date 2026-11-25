---
name: interpret-market-signals
description: Explain published analyst ratings, price targets, earnings revisions and market positioning for a stock or portfolio as of a given date. Use when a reader asks what a WSJ ratings table means, whether analysts changed their minds, or what a market signal actually measures.
---

# Interpret published market signals

Start with the user's ticker, exchange, share class and cutoff time. For a portfolio request, use the selected account's read-only positions if available. Use only public instrument identifiers in external searches. An ETF can have positioning data of its own. Company earnings estimates apply to the underlying companies.

## Find the underlying observation

- **Ratings and targets.** Find the issue's Research & Ratings page in WSJ Market Data. The Apple example shows rating counts across dates, target summaries, and quarterly and annual earnings estimates. WSJ credits FactSet for analyst estimates. Attribute the panel to its contributors and provider. For a specific upgrade, look for a dated statement identifying the research firm, previous and new ratings, and its definition and horizon. “Overweight” can mean expected outperformance against the firm's chosen benchmark. [WSJ example](https://www.wsj.com/market-data/quotes/AAPL/research-ratings) · [FINRA rating definitions, section (c)(2)](https://www.finra.org/rules-guidance/rulebooks/finra-rules/2241)
- **Forecasts and results.** Consensus combines forecasts from contributing analysts. Record which statistic the source reports, the contributor count if shown, fiscal period, currency, and reported or adjusted earnings basis. Some companies publish analyst surveys through investor relations. Identify management's own guidance and reported results from dated releases or filings. Where the WSJ view or historical data requires a subscription, use an accessible issuer compilation or user-supplied excerpt and state which fields remain unavailable. [Issuer-hosted example](https://www.shell.com/investors/results-and-reporting/consensus-estimates.html) · [FactSet estimates methodology](https://insight.factset.com/resources/factset-consensus-estimates-datafeed) · [SEC filing search](https://www.sec.gov/edgar/search/)
- **Positioning and sentiment.** If relevant to the question, FINRA publishes U.S. equity short interest twice monthly. Cite settlement and publication dates. Open short positions can include hedges. Daily short-sale volume counts trades and answers a different question. CFTC positions describe trader groups in a particular derivatives contract. AAII surveys members about the U.S. market over the next six months. Use these last two as market context and give the ticker's specific exposure if known. [FINRA short interest](https://www.finra.org/finra-data/browse-catalog/equity-short-interest/data) · [CFTC release calendar](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm) · [AAII survey](https://www.aaii.com/sentimentsurvey)

## Work out what changed

1. Establish the observation date and when it became public. A historical answer needs a dated document or point-in-time snapshot available by the cutoff. A page retrieved today may reflect backfilled estimates or amended filings. A quote timestamp dates the price only. If the analyst data has no update time, say when you viewed it and leave its age unknown.
2. Compare the same fiscal period, share class, units and accounting basis. Show estimate changes per share, and percentages when the old value is positive and material. Use the absolute change for a figure near zero or crossing between profit and loss. A changed consensus can reflect analysts joining or leaving. Show the Buy count over the number of ratings and interpret that percentage as a share of opinions. Attribute a particular analyst’s change only with evidence for both observations.
3. For a positive price, calculate the target gap as `100 × (target / reference price − 1)`. Identify whether the target is the mean, median or an individual forecast. Match currency, units, split basis and quote session. State the horizon if known and any delay in that price. The high and low targets show how far apart contributors' forecasts are. The gap measures distance to a forecast. Dividends, fees and the chance of reaching that price are separate questions.

## Explain the evidence

Lead with the most material change. Give each observation a dated source link, plain-language meaning and the evidence that would resolve the main uncertainty. For a requested historical success check, evaluate the subsequent realised outcome separately against the original forecast and horizon. Keep the conclusion descriptive and leave trading decisions with the reader.

For example, these **fictional** figures compare 30 January and 27 February 2026 for the same share. In a live answer, replace the example dates and sources with the actual ones.

| Signal and source | What changed by 27 February | Meaning for the reader |
| --- | --- | --- |
| FY2026 adjusted earnings per share, analyst panel | £2.00 → £1.90, down 10p or 5% | The panel expects lower profit per share. The company has yet to report that result. |
| Median target and closing share price, same currency | Target £60 on both dates. Close £50 → £48. Gap 20% → 25%. | The price fell. An unchanged target now stands further above the market. |
| Buy ratings, analyst panel | 8 of 10 → 9 of 12. Share of Buy ratings fell from 80% to 75%. | More contributors rated the shares Buy, but their share of the larger panel fell. The counts alone cannot identify an individual upgrade. |
