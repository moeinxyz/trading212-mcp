# Trading 212 MCP

[![CI](https://github.com/moeinxyz/trading212-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/moeinxyz/trading212-mcp/actions/workflows/ci.yml)

I built this for my own portfolio. It lets an assistant read Trading 212 Invest and Stocks ISA accounts locally and explain the numbers. **Use it at your own risk.** Figures and AI analysis can be wrong. I don’t provide investment advice through this project. You make your own investment decisions. Check figures and orders in Trading 212 before acting.

## Get started

In each account, open **Menu → Settings → API (Beta) → Generate API key**. Select **Account data** and **Portfolio** for holdings and cash. With Git and [uv](https://docs.astral.sh/uv/getting-started/installation/) installed, set up the first account. Keys are entered privately and orders are disabled by default.

```sh
uv tool install git+https://github.com/moeinxyz/trading212-mcp@v0.3.0
trading212-mcp setup
```

Have a second account? Switch to it in Trading 212, generate its own key, and run `trading212-mcp setup --account isa`. For Codex, register the server with `codex mcp add trading212 -- trading212-mcp`. Restart the client and ask for Invest, ISA or both. [Client setup and account labels](docs/configuration.md#accounts-and-credentials)

## Ask about your portfolio

| Ask | Workflow |
| --- | --- |
| “How am I doing across Invest and ISA? Give me one simple table.” | [Portfolio report card](skills/portfolio-report-card/SKILL.md) · [Worked example](docs/research.md#an-example-report-card) |
| “What does diluted EPS tell me? Are earnings turning into cash?” | [Company metrics](skills/explain-stock-metrics/SKILL.md) · [Stock fundamentals](skills/analyze-stock/SKILL.md) |
| “Which opportunities am I overlooking, and what would they cost?” | [Opportunity review](skills/find-portfolio-opportunities/SKILL.md) · [Allocation drift](skills/check-allocation-drift/SKILL.md) |
| “Did analysts change their estimates? What news affects my holdings?” | [Published signals](skills/interpret-market-signals/SKILL.md) · [Portfolio news](skills/review-portfolio-news/SKILL.md) |

All ten workflows ship as MCP prompts and Agent Skills, including [portfolio risk](skills/analyze-portfolio-risk/SKILL.md), [performance](skills/analyze-portfolio-performance/SKILL.md) and [upcoming events](skills/preview-portfolio-events/SKILL.md). Market research uses your assistant’s web access or dated sources you supply. [Using the skills](docs/configuration.md#research-skills)

An independent project by Moein under the [MIT licence](LICENSE). Your MCP client can share results with its model provider. Broker access is subject to [Trading 212’s API terms](https://www.trading212.com/legal-documentation/API-Terms_EN.pdf).
