# Configure Trading 212 MCP

## Connect a client

Your client needs access to `uvx` (included with uv) on the computer that runs it. If you already have uv, use the configuration below. On first launch, `uvx` downloads the tagged release and any needed dependencies. It can also download a compatible Python if one is missing. The server runs locally in a cached, isolated environment. Complete the private account setup below, then give your client this local **stdio** server. [Install uv](https://docs.astral.sh/uv/getting-started/installation/) · [How uvx runs tools](https://docs.astral.sh/uv/guides/tools/) · [Accounts and credentials](#accounts-and-credentials)

```json
{
  "mcpServers": {
    "trading212": {
      "command": "uvx",
      "args": [
        "--from",
        "https://github.com/moeinxyz/trading212-mcp/archive/refs/tags/v0.4.0.tar.gz",
        "trading212-mcp"
      ]
    }
  }
}
```

Merge the `trading212` entry into your existing server list. For clients with a form, use `trading212` as the name, `uvx` as the command and the three array items as separate arguments. If a desktop app cannot find `uvx`, use its full path from `command -v uvx` on macOS/Linux or `(Get-Command uvx).Source` in PowerShell. Leave `setup` out of the server arguments so the client starts the MCP session.

| Client | Where to add it |
| --- | --- |
| Claude Desktop | Open **Settings → Developer → Edit Config**, merge the entry into `claude_desktop_config.json`, then fully quit and reopen Claude. [Local server guide](https://modelcontextprotocol.io/docs/develop/connect-local-servers) |
| LM Studio | Open **Program → Install → Edit mcp.json**, then merge the entry and save. [LM Studio MCP guide](https://lmstudio.ai/docs/app/mcp) |
| Cursor | Add the entry to `~/.cursor/mcp.json` for your local editor across projects. [Cursor MCP guide](https://cursor.com/docs/mcp) |
| ChatGPT Desktop or Codex | In the desktop app, open **Settings → MCP servers → Add server**, choose **STDIO**, enter the command and arguments above, save and select **Restart**. Codex CLI and its IDE extension share this configuration. [OpenAI local MCP guide](https://learn.chatgpt.com/docs/extend/mcp) |

Ask **“Which account labels are configured?”** `trading_status` answers locally. Then ask **“Show the available cash and my three largest holdings in the invest account.”** Substitute `isa` or `primary` for a different label. The second question uses the broker API.

ChatGPT web uses remote MCP connections. Eligible workspaces can connect a private stdio server through OpenAI’s separately configured secure tunnel. Consumer Meta Muse runs on its own cloud computer. We could not verify a consumer setting to launch this local command there. For a regular hosted chat, you can share a summary you have reviewed from a supported local client. Keep the credentials private. [OpenAI custom MCP guide](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt) · [OpenAI secure tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) · [How Meta Muse runs](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/)

## Accounts and credentials

1. Switch to the **Invest** or **Stocks & Shares ISA** account you want in Trading 212. Open **Menu → Settings → API (Beta) → Generate API key**. Choose **Account data** for cash and account totals, and **Portfolio** for individual holdings. Leave order execution disabled for a read-only key. Add other read permissions only for tools you want. Save the API Key and its one-time API Secret Key privately. [Trading 212 key creation and revocation](https://helpcentre.trading212.com/hc/en-us/articles/14584770928157-Trading-212-API-key)
2. Run the matching one-time command below in your terminal. Enter `live` for your real account or `demo` for practice, then enter the key and secret at the hidden prompts. For both accounts, switch accounts in Trading 212 and generate a separate pair before running the other command.

**Invest**

```sh
uvx --from https://github.com/moeinxyz/trading212-mcp/archive/refs/tags/v0.4.0.tar.gz trading212-mcp setup --account invest
```

**Stocks & Shares ISA**

```sh
uvx --from https://github.com/moeinxyz/trading212-mcp/archive/refs/tags/v0.4.0.tar.gz trading212-mcp setup --account isa
```

The saved labels are `invest` and `isa`. Omitting `--account` creates the legacy/default `primary` label for either account type. Existing `primary` profiles still work. Keep that label if you already use it. The labels are local names. Check `account.id` from `get_account_summary(account="invest")` against **Menu → My account → Account details** in Trading 212 to verify the underlying account. [Finding your account number](https://helpcentre.trading212.com/hc/en-us/articles/360008823837-Where-can-I-find-my-account-reference-number)

Setup saves new profiles as read-only and preserves existing key pairs. The key and secret are stored in a local, unencrypted TOML file protected by your user account. On macOS/Linux it defaults to `~/.config/trading212-mcp/accounts.toml` (or under `XDG_CONFIG_HOME`). On Windows it defaults to `%APPDATA%\trading212-mcp\accounts.toml`. To use another private file, set `T212_CONFIG_FILE` to the same absolute path in the setup environment and the host's server environment. On Unix use an owner-only file such as mode `600`. To rotate credentials, update the pair in its existing private account section, restart the client and revoke the old key in Trading 212.

Ask “Show both accounts and combine the GBP balances” to use `get_portfolio_overview(accounts=["invest", "isa"])`. With no account selection the overview tries the configured profiles, groups results by live/practice and currency, and counts each broker account ID once. If a requested account fails, the response shows the available account results and marks the combined total unavailable. For a single-account tool such as `list_positions`, pass the saved label explicitly. Its default is `primary`.

Existing file-based settings use `[trading]` for `primary` and `[trading_accounts.<label>]` for additional accounts. A host that provides private environment variables can supply a primary pair with `T212_ENV`, `T212_API_KEY` and `T212_API_SECRET`. An optional `T212_ISA_API_KEY` and `T212_ISA_API_SECRET` pair adds an ISA. Specifying any server settings in the environment disables automatic file discovery, so also set `T212_CONFIG_FILE` if you want to include file profiles. Override both parts of a key pair together.

### VS Code masked credential prompts

If uv is already available, VS Code’s **editor-managed** server configuration can prompt privately for one account without the terminal setup step. In a local VS Code window, run **MCP: Open User Configuration** from the Command Palette and merge the following. Start the server and enter each value in its masked prompt. This example connects a read-only real account labelled `primary`. For practice keys, set `T212_ENV` to `demo`. [VS Code MCP input variables](https://code.visualstudio.com/docs/copilot/reference/mcp-configuration)

```json
{
  "inputs": [
    {"id": "t212Key", "type": "promptString", "description": "Trading 212 API Key", "password": true},
    {"id": "t212Secret", "type": "promptString", "description": "Trading 212 API Secret", "password": true}
  ],
  "servers": {
    "trading212": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "https://github.com/moeinxyz/trading212-mcp/archive/refs/tags/v0.4.0.tar.gz", "trading212-mcp"],
      "env": {
        "T212_ENV": "live",
        "T212_API_KEY": "${input:t212Key}",
        "T212_API_SECRET": "${input:t212Secret}",
        "T212_ENABLE_WRITES": "false"
      }
    }
  }
}
```

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
