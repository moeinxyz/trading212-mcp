# Trading 212 MCP

[![CI](https://github.com/moeinxyz/trading212-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/moeinxyz/trading212-mcp/actions/workflows/ci.yml)

Ask your assistant about your Trading 212 Invest or Stocks ISA account. The server runs locally with your own API key and starts read-only.

## Get started

In Trading 212, switch to the account you want, then open **Menu → Settings → API (Beta) → Generate API key**. Select **Account data** and **Portfolio** for holdings and cash. Install with Git and [uv](https://docs.astral.sh/uv/getting-started/installation/), then run setup.

```sh
uv tool install git+https://github.com/moeinxyz/trading212-mcp@v0.2.0
trading212-mcp setup
```

Setup asks for your key and one-time secret in the terminal. For Codex, register the server with `codex mcp add trading212 -- trading212-mcp`. Restart your client and ask **“What do I hold, and how much cash is available?”** [Other clients, multiple accounts and optional orders](docs/configuration.md)

## Research with your holdings

| Ask | Skill |
| --- | --- |
| Which news this week actually affects my holdings? | [Portfolio news](skills/review-portfolio-news/SKILL.md) |
| How far have I moved from my target allocation? | [Allocation drift](skills/check-allocation-drift/SKILL.md) |
| Where do my ETFs overlap, and what would a 15% drop cost me? | [Portfolio risk](skills/analyze-portfolio-risk/SKILL.md) |
| Which earnings dates or corporate actions are coming up? | [Upcoming events](skills/preview-portfolio-events/SKILL.md) |
| How did I do against my benchmark after accounting for deposits? | [Portfolio performance](skills/analyze-portfolio-performance/SKILL.md) |
| Does the company’s cash generation support its valuation? | [Stock fundamentals](skills/analyze-stock/SKILL.md) |

All six ship as MCP prompts and Agent Skills. News and event reviews run on demand using your assistant’s web access or sources you supply. [Using the skills](docs/configuration.md#research-skills)

Independent software by Moein, distributed under the [MIT licence](LICENSE). Analysis is informational and can be wrong. Your MCP client can share tool results with its model provider. Use of the broker API is subject to [Trading 212’s API terms](https://www.trading212.com/legal-documentation/API-Terms_EN.pdf).
