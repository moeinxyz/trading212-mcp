# Configure Trading 212 MCP

## Connect a client

Run `trading212-mcp setup` in your terminal. Choose `live` for a real account or `demo` for a practice account, and enter a key pair generated in that same environment. Setup creates an owner-only file on Unix and prints its location. On Windows it uses your user's application-data directory. Running setup again preserves the existing file. Edit it locally to change accounts or rotate keys. [Broker key setup and revocation](https://helpcentre.trading212.com/hc/en-us/articles/14584770928157-Trading-212-API-key)

The default file is `~/.config/trading212-mcp/accounts.toml` on macOS and Linux (or under `XDG_CONFIG_HOME`) and `%APPDATA%\trading212-mcp\accounts.toml` on Windows. If the installed command is missing from your terminal, run `uv tool update-shell` and reopen the terminal.

For Codex, run `codex mcp add trading212 -- trading212-mcp`. For another stdio client that accepts JSON configuration, add this entry to its server settings.

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

Your first key can belong to Invest or Stocks ISA. The default account label is `primary`. To add an ISA or another account, switch accounts in Trading 212, generate a separate pair, and add a section to the private file.

```toml
[trading_accounts.isa]
T212_ENV = "live"
T212_API_KEY = "<second account key>"
T212_API_SECRET = "<second account secret>"
```

Use `account="isa"` when requesting that account. Labels come from your configuration. Before combining portfolios, compare each broker-returned account ID with **Menu → My account → Account details**. Two different keys can point to the same portfolio. [Finding your account number](https://helpcentre.trading212.com/hc/en-us/articles/360008823837-Where-can-I-find-my-account-reference-number)

To reuse an existing settings file, pass its absolute path in the client environment as `T212_CONFIG_FILE`. The file uses `[trading]` for primary and `[trading_accounts.<label>]` for other accounts. On Unix the owner must be the current user and the file must be private (`chmod 600`). For environment-only setups, pass `T212_ENV`, `T212_API_KEY` and `T212_API_SECRET` through a private launcher. Optional `T212_ISA_API_KEY` and `T212_ISA_API_SECRET` add an ISA in the same environment. Explicit server settings take precedence over automatic file discovery. An environment override for credentials must supply the key and secret together.

## Tools and permissions

| Tool | Key permission |
| --- | --- |
| `trading_status` | Local |
| `get_account_summary` | `account` |
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

## Privacy and terms

Credentials go to Trading 212 over HTTPS. Tool results can contain identifiers, balances, positions and transactions. Your MCP client controls which results reach its model provider. Keep keys and account exports out of prompts, issues and Git. You can revoke keys in Trading 212 at any time.

This is an independent personal project. Trading 212 describes personal access for testing in §6.2 and requires prior written consent for uses covered by §6.3, including developing an API application intended for other end users. The code’s MIT licence and the broker's API access terms govern different things. Financial losses are possible. Verify figures and orders in the broker app. The software is provided as-is under the warranty and liability terms of the MIT licence. [API terms](https://www.trading212.com/legal-documentation/API-Terms_EN.pdf#page=7) · [MIT licence](../LICENSE)
