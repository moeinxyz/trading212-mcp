# Configure Trading 212 MCP

## Connect a client

For Codex on macOS, use the [one-command installer](../README.md#connect-to-codex-on-a-mac) in Terminal. For Windows, Linux or another MCP client, install [uv](https://docs.astral.sh/uv/getting-started/installation/) and run this command in a terminal.

```sh
uv tool install --python 3.13 https://github.com/moeinxyz/trading212-mcp/archive/refs/tags/v0.4.0.tar.gz
```

With Codex, run `trading212-mcp connect` and follow the prompts. For another client, run `trading212-mcp setup`. Choose `live` for a real account or `demo` for a practice account, then enter a key pair generated in that environment. Setup prints the location of the private account file. [Broker key setup and revocation](https://helpcentre.trading212.com/hc/en-us/articles/14584770928157-Trading-212-API-key)

The default file is `~/.config/trading212-mcp/accounts.toml` on macOS and Linux (or under `XDG_CONFIG_HOME`) and `%APPDATA%\trading212-mcp\accounts.toml` on Windows. If your terminal cannot find `trading212-mcp` after a manual installation with uv, run `uv tool update-shell` and reopen the terminal.

The Mac installer keeps its launcher and runtime in `~/.local/share/trading212-mcp` (or under `XDG_DATA_HOME`). A new Codex registration uses the full launcher path. If Codex already uses this server, the connector can reuse that registration and its account file. Update that original installation to change the version Codex runs. To disconnect a server added by the installer, run `codex mcp remove trading212`. To revoke a key, open the API settings in Trading 212.

For another stdio client that accepts JSON configuration, add this entry to its server settings.

```json
{
  "mcpServers": {
    "trading212": {
      "command": "trading212-mcp"
    }
  }
}
```

If a desktop client cannot find the command, set `command` to its full path from `command -v trading212-mcp` (macOS/Linux) or `(Get-Command trading212-mcp).Source` (PowerShell). Restart the client. `trading_status` reports the configured environment and labels locally. `get_account_summary` tests the key against the broker.

## Accounts and credentials

Your first key can belong to Invest or Stocks ISA and is labelled `primary`. To add an ISA, switch to it in Trading 212 and generate its own read-only key pair. With the Mac installer, run the same command with an account label.

```sh
curl -fsSL https://raw.githubusercontent.com/moeinxyz/trading212-mcp/v0.4.0/install.sh | sh -s -- --account isa
```

With the manual installation, run `trading212-mcp setup --account isa`. If your first account was ISA and the second is Invest, use `--account invest` instead. Restart the MCP client, then ask for Invest, ISA or both.

Ask “Show only my ISA” to select the appropriate label. Ask “Show both accounts and combine the GBP balances” to use `get_portfolio_overview(accounts=["primary", "isa"])`. Without a selection, the overview tries all configured profiles and identifies unconfigured ones. It shows each account's available cash, investments and total value. It groups values by live/practice and currency and counts each broker account ID once. A failed requested account makes the combined total unavailable. The separate account results show what was actually retrieved.

Labels describe your configuration. Check each broker ID in `get_account_summary` against **Menu → My account → Account details** to confirm which account is which. Two different keys can refer to the same account. [Finding your account number](https://helpcentre.trading212.com/hc/en-us/articles/360008823837-Where-can-I-find-my-account-reference-number)

To reuse an existing settings file, pass its absolute path in the client environment as `T212_CONFIG_FILE`. The file uses `[trading]` for primary and `[trading_accounts.<label>]` for other accounts. On Unix the owner must be the current user and the file must be private (`chmod 600`). For environment-only setups, pass `T212_ENV`, `T212_API_KEY` and `T212_API_SECRET` through a private launcher. Optional `T212_ISA_API_KEY` and `T212_ISA_API_SECRET` add an ISA in the same environment. Explicit server settings take precedence over automatic file discovery. An environment override for credentials must supply the key and secret together.

## Tools and permissions

| Tool | Key permission |
| --- | --- |
| `trading_status` | Local |
| `get_account_summary`, `get_portfolio_overview` | `account` for each account selected |
| `calculate_stock_metrics` | Local arithmetic on supplied financial statements |
| `list_positions` | `portfolio` |
| `list_pending_orders` | `orders:read` |
| `trading_history` | `history:orders`, `history:dividends` or `history:transactions` for the requested feed |
| `search_instruments` | `metadata` |

`walletImpact.currentValue` is the value of a whole position in `walletImpact.currency`. `currentPrice` is a per-share price in the instrument's currency. Use `cash.availableToTrade` for available cash. History returns up to 50 records per page. Follow `next_page_path` with the same feed and account until the period is covered. The server reports unusable cursors and rate limits. [Trading 212 API reference](https://docs.trading212.com/api)

### Optional limit orders

For the primary account only, both the broker key's `orders:execute` permission and `T212_ENABLE_WRITES = true` in `[trading]` are required. The preview also uses `account` and `metadata`. Test in `demo` first. A submission in `live` can trade real money.

`preview_limit_order` prepares a five-minute, single-use DAY limit order. `submit_limit_order` asks your MCP client for approval of that exact order. Use a trusted client configured to show elicitation forms to you and disable automatic approval. Check the environment, account ending, side, quantity and per-share limit before accepting. After a timeout, check pending orders and history before preparing another order. An order ID acknowledges submission, while its broker status tells you whether it filled. [Limit order reference](https://docs.trading212.com/api/orders/placelimitorder)

## Research skills

In a client with MCP prompt support, open its prompt picker and choose a Trading 212 workflow. Each Markdown skill is also installable in an Agent Skills client. For example, run `npx skills add moeinxyz/trading212-mcp --agent codex` in the project where you want to use them and select the workflows you want. [Skills CLI](https://github.com/vercel-labs/skills)

News and event research uses the host's web access or dated source documents. Allocation drift needs a target or an earlier allocation. Period returns need dated valuations and external cash flows. The portfolio tools expose current holdings and history, and the workflows identify missing inputs when the available data cannot answer the question.

For a beginner overview, use `portfolio_report_card`. Ask for a specific account, both accounts, or all configured accounts. For a single issuer, `explain_stock_metrics` can use `calculate_stock_metrics` for consistent arithmetic on sourced filing figures. `find_portfolio_opportunities` and `interpret_market_signals` distinguish possible follow-ups from verified outcomes. [Example report and research sources](research.md)

## Privacy and terms

Credentials go to Trading 212 over HTTPS. Tool results can contain identifiers, balances, positions and transactions. Your MCP client controls which results reach its model provider. Keep keys and account exports out of prompts, issues and Git. You can revoke keys in Trading 212 at any time.

I built this for my own use. If you choose to use it, you do so at your own risk. This is an independent personal project. Trading 212 describes personal access for testing in §6.2 and requires prior written consent for uses covered by §6.3, including developing an API application intended for other end users. The code’s MIT licence and the broker's API access terms govern different things. Financial losses are possible. Verify figures and orders in the broker app. The software is provided as-is under the warranty and liability terms of the MIT licence. [API terms](https://www.trading212.com/legal-documentation/API-Terms_EN.pdf#page=7) · [MIT licence](../LICENSE)
