# Trading 212 MCP

[![CI](https://github.com/moeinxyz/trading212-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/moeinxyz/trading212-mcp/actions/workflows/ci.yml)

I built this for my own portfolio. Ask your AI about holdings and cash in your Trading 212 Invest and Stocks ISA accounts. **Use it at your own risk.** Figures and AI analysis can be wrong. Check them in Trading 212 before making investment decisions.

## Connect your AI

Use an AI app that supports local MCP servers and can run `uvx`. Your app starts the server when needed. On the first run, uv downloads the Python package and dependencies into its cache. [How uvx works](https://docs.astral.sh/uv/guides/tools/)

**1. Connect your account once.** In Trading 212, choose **Menu → Settings → API (Beta) → Generate API key** and select **Account data** and **Portfolio**. Run the command below in a terminal and enter the key and secret at the hidden prompts. For an ISA, use `--account isa`. [Trading 212’s key guide](https://helpcentre.trading212.com/hc/en-us/articles/14584770928157-Trading-212-API-key)

```sh
uvx --from https://github.com/moeinxyz/trading212-mcp/archive/refs/tags/v0.4.0.tar.gz trading212-mcp setup --account invest
```

**2. Add Trading 212 to your AI app.** Choose your client below and review the connection. The links contain only the launch command. Orders are disabled by default.

[Add to LM Studio](https://lmstudio.ai/install-mcp?name=trading212&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyItLWZyb20iLCJodHRwczovL2dpdGh1Yi5jb20vbW9laW54eXovdHJhZGluZzIxMi1tY3AvYXJjaGl2ZS9yZWZzL3RhZ3MvdjAuNC4wLnRhci5neiIsInRyYWRpbmcyMTItbWNwIl19) · [Add to Cursor](https://cursor.com/en/install-mcp?name=trading212&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyItLWZyb20iLCJodHRwczovL2dpdGh1Yi5jb20vbW9laW54eXovdHJhZGluZzIxMi1tY3AvYXJjaGl2ZS9yZWZzL3RhZ3MvdjAuNC4wLnRhci5neiIsInRyYWRpbmcyMTItbWNwIl19) · [Claude Desktop, ChatGPT Desktop, Codex and other clients](docs/configuration.md#connect-a-client)

Open a chat and ask **“Show my holdings and available cash.”**

## Ask about your portfolio

| Ask | Workflow |
| --- | --- |
| “How am I doing across Invest and ISA? Give me one simple table.” | [Portfolio report card](skills/portfolio-report-card/SKILL.md) · [Worked example](docs/research.md#an-example-report-card) |
| “What does diluted EPS tell me? Are earnings turning into cash?” | [Company metrics](skills/explain-stock-metrics/SKILL.md) · [Stock fundamentals](skills/analyze-stock/SKILL.md) |
| “Which opportunities am I overlooking, and what would they cost?” | [Opportunity review](skills/find-portfolio-opportunities/SKILL.md) · [Allocation drift](skills/check-allocation-drift/SKILL.md) |
| “Did analysts change their estimates? What news affects my holdings?” | [Published signals](skills/interpret-market-signals/SKILL.md) · [Portfolio news](skills/review-portfolio-news/SKILL.md) |

All ten workflows ship as MCP prompts and Agent Skills, including [portfolio risk](skills/analyze-portfolio-risk/SKILL.md), [performance](skills/analyze-portfolio-performance/SKILL.md) and [upcoming events](skills/preview-portfolio-events/SKILL.md). Market research uses your assistant’s web access or dated sources you supply. [Using the skills](docs/configuration.md#research-skills)

An independent project by Moein under the [MIT licence](LICENSE). Your MCP client can share results with its model provider. Broker access is subject to [Trading 212’s API terms](https://www.trading212.com/legal-documentation/API-Terms_EN.pdf).
