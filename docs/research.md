# Reading your portfolio report

Ask the assistant to “give me a report card across my Invest and ISA accounts.” It can read the account figures and explain them. For current earnings or analyst views, it needs a web-enabled research client or dated sources you supply. An honest “unknown” is a useful result when the data cannot answer a question.

## An example report card

The figures below are fictional. The two GBP accounts have distinct broker identifiers. The example covers one year, and its only contribution arrived at the beginning, before any market movement.

| Question | Result | What it means | Evidence or next check |
| --- | --- | --- | --- |
| What do I have? | £6,000 Invest + £4,000 ISA = **£10,000** | Together the accounts hold £10,000, including their cash. | Two account summaries on the same day. |
| How much cash is available? | **£1,000**, or 10% | The accounts have £400 and £600 immediately available to trade. | Cash reserved for orders is a separate balance. |
| How did I do? | **+£200**, or **+2.04%** | I started with £8,800, added £1,000 at the start and finished with £10,000. The contribution gave me £9,800 invested for the full year. | Against a comparable GBP total-return benchmark at +3.00%, the gap is **−0.96 percentage points**. |
| Where is the risk? | At least **£1,600** in one issuer | £1,400 held directly plus 8% of a £2,500 fund. A 15% fall on that known exposure would cost **£240**, with everything else flat. | Check the fund's dated holdings and any other funds that might own the issuer. |

Without the opening valuation and cash flows, the first two rows still work and the annual return is **unknown**. An unrealised profit on today's holdings cannot recover returns from shares already sold.

## Earnings and external signals

Diluted earnings per share (EPS) measures the profit attributable to each common share after applicable potential dilution. If comparable diluted EPS rises from £1.20 to £1.44, earnings per share rose 20%. To interpret that, check what happened to profit, the share count and cash flow. At a £28.80 share price, **20× earnings** is a valid trailing P/E only if £1.44 is trailing twelve-month diluted EPS for that same share, known at the price date. [IAS 33 on earnings per share](https://www.ifrs.org/issued-standards/list-of-standards/ias-33-earnings-per-share/)

WSJ Research & Ratings displays analyst estimates, rating counts and price targets. Identify the contributor or consensus provider, fiscal period and observation date. A rising target gap can come from a falling share price even if analysts never changed their targets. Coverage varies. When public evidence is unavailable, the workflow can use a dated excerpt you provide or an issuer's published consensus. There is no WSJ feed or subscription bundled with this server. [WSJ example](https://www.wsj.com/market-data/quotes/AAPL/research-ratings) · [Shell’s issuer-published consensus](https://www.shell.com/investors/results-and-reporting/consensus-estimates.html)

## Workflows reviewed

| Source | What informed this project |
| --- | --- |
| [Anthropic earnings analysis](https://github.com/anthropics/financial-services/blob/main/plugins/vertical-plugins/equity-research/skills/earnings-analysis/SKILL.md) and [comparable-company analysis](https://github.com/anthropics/financial-services/blob/main/plugins/agent-plugins/market-researcher/skills/comps-analysis/SKILL.md) | Compare actual results with expectations available before the release. Choose comparable periods, accounting definitions and peers. |
| [TraderMonty US stock analysis](https://github.com/tradermonty/claude-trading-skills/blob/main/skills/us-stock-analysis/SKILL.md) | Read financial statements alongside sector and valuation context. The beginner matrix explains each selected ratio in everyday language. |
| [Anthropic idea generation](https://github.com/anthropics/financial-services/blob/main/plugins/vertical-plugins/equity-research/skills/idea-generation/SKILL.md) and [thesis tracker](https://github.com/anthropics/financial-services/blob/main/plugins/vertical-plugins/equity-research/skills/thesis-tracker/SKILL.md) | For each opportunity, identify its comparator, costs, evidence, and the observation that would weaken it. |
| [OpenAI public-equity investing](https://github.com/openai/plugins/blob/main/plugins/public-equity-investing/skills/public-equity-investing/SKILL.md) | Connect financial statements and valuation to the investment question. Keep facts, assumptions and scenarios visible to the reader. |
| [FactSet consensus methodology](https://insight.factset.com/resources/factset-consensus-estimates-datafeed) and [FINRA’s equity research rule](https://www.finra.org/rules-guidance/rulebooks/finra-rules/2241) | Differentiate estimates from actual results. Attribute analyst opinions and check the rating scale and horizon. |

The workflows in this repository are independently written. The calculator runs locally on sourced figures. Market research runs on demand using public material or sources you supply.
