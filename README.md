# Trading 212 MCP

[![CI](https://github.com/moeinxyz/trading212-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/moeinxyz/trading212-mcp/actions/workflows/ci.yml)

I built this for my own portfolio. It lets an assistant read Trading 212 Invest and Stocks ISA accounts locally and explain the numbers. **Use it at your own risk.** Figures and AI analysis can be wrong. I don’t provide investment advice through this project. You make your own investment decisions. Check figures and orders in Trading 212 before acting.

## Connect to Codex on a Mac

In your Trading 212 account, open **Menu → Settings → API (Beta) → Generate API key**. Choose **Account data** and **Portfolio** to read holdings and cash. Keep the key and secret handy for the Terminal prompts. [Trading 212’s key guide](https://helpcentre.trading212.com/hc/en-us/articles/14584770928157-Trading-212-API-key)

With Codex installed, paste this command into Terminal.

```sh
curl -fsSL https://raw.githubusercontent.com/moeinxyz/trading212-mcp/v0.4.0/install.sh | sh
```

The installer handles Python, saves your keys locally and connects the server to Codex. Restart Codex and ask **“Show my holdings and available cash.”** Orders are disabled by default. [Inspect the installer](install.sh) · [Add an ISA](docs/configuration.md#accounts-and-credentials) · [Windows, Linux and other clients](docs/configuration.md#connect-a-client)

## Ask about your portfolio

| Ask | Workflow |
| --- | --- |
| “How am I doing across Invest and ISA? Give me one simple table.” | [Portfolio report card](skills/portfolio-report-card/SKILL.md) · [Worked example](docs/research.md#an-example-report-card) |
| “What does diluted EPS tell me? Are earnings turning into cash?” | [Company metrics](skills/explain-stock-metrics/SKILL.md) · [Stock fundamentals](skills/analyze-stock/SKILL.md) |
| “Which opportunities am I overlooking, and what would they cost?” | [Opportunity review](skills/find-portfolio-opportunities/SKILL.md) · [Allocation drift](skills/check-allocation-drift/SKILL.md) |
| “Did analysts change their estimates? What news affects my holdings?” | [Published signals](skills/interpret-market-signals/SKILL.md) · [Portfolio news](skills/review-portfolio-news/SKILL.md) |

All ten workflows ship as MCP prompts and Agent Skills, including [portfolio risk](skills/analyze-portfolio-risk/SKILL.md), [performance](skills/analyze-portfolio-performance/SKILL.md) and [upcoming events](skills/preview-portfolio-events/SKILL.md). Market research uses your assistant’s web access or dated sources you supply. [Using the skills](docs/configuration.md#research-skills)

An independent project by Moein under the [MIT licence](LICENSE). Your MCP client can share results with its model provider. Broker access is subject to [Trading 212’s API terms](https://www.trading212.com/legal-documentation/API-Terms_EN.pdf).
