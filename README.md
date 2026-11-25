# Trading 212 MCP

Ask your assistant “What do I hold in my ISA?” or “How much of my portfolio would a 10% fall in my largest position cost me?” This free, self-hosted Model Context Protocol (MCP) server runs on your computer and reads your own Trading 212 account using your API Key and API Secret. It starts in practice mode with order placement disabled. Trading 212 provides the API for Invest and Stocks & Shares ISA accounts. [Trading 212 API overview](https://docs.trading212.com/api)

## Install from source

With Git and uv installed, run these commands in a terminal. The project uses Python 3.11 or later and a lockfile for its dependencies. [Install uv](https://docs.astral.sh/uv/getting-started/installation/)

```sh
git clone https://github.com/moeinxyz/trading212-mcp.git
cd trading212-mcp
uv sync --locked --no-dev
```

## Connect your account

1. In Trading 212, select the account you want to read and switch to **Practice** or **Real money**. Open **Menu → Settings → API (Beta) → Generate API key**. Review the broker’s risk notice, name the key and choose permissions. **Account data** and **Portfolio** cover cash and holdings. Add the other read permissions below if you want those tools. Keep order execution off for a read-only key. You can restrict the key to trusted IP addresses. [Trading 212 key guide](https://helpcentre.trading212.com/hc/en-us/articles/14584770928157-Trading-212-API-key)
2. Save the **API Key** and the **API Secret Key** in your password manager. Trading 212 shows the secret only once. The pair belongs to the selected account and environment.
3. Create a private settings file outside the checkout. On macOS or Linux the following commands create the file with owner-only permissions before you edit it.

```sh
mkdir -p "$HOME/.config/trading212-mcp"
chmod 700 "$HOME/.config/trading212-mcp"
(umask 077 && touch "$HOME/.config/trading212-mcp/broker.env")
chmod 600 "$HOME/.config/trading212-mcp/broker.env"
```

Open `broker.env` in a local editor. Start with the following contents and replace the placeholders with your practice key pair. For real holdings, change `T212_ENV` to `live` and enter the corresponding real-account pair. Keep credentials out of chat, shell history and Git.

```dotenv
T212_ENV=demo
T212_API_KEY=replace-with-your-api-key
T212_API_SECRET=replace-with-your-api-secret
T212_ENABLE_WRITES=false
```

### Start the server from your MCP client

Add this entry to your client's local **stdio** MCP configuration. Replace the three absolute paths with the output of `command -v uv`, the checkout’s `pwd -P`, and the full path of your private file. Use an env-file path without spaces with this uv command. This works for desktop clients launched outside your terminal. uv loads the file into the server process. The server reads its environment at startup. [uv command reference](https://docs.astral.sh/uv/reference/cli/#uv-run--env-file)

```json
{
  "mcpServers": {
    "trading212": {
      "command": "/absolute/path/to/uv",
      "args": [
        "--directory", "/absolute/path/to/trading212-mcp",
        "run", "--locked", "--no-dev",
        "--env-file", "/absolute/path/to/private/broker.env",
        "trading212-mcp"
      ]
    }
  }
}
```

Restart the client. Ask “Which Trading 212 environment and accounts are configured?” This runs `trading_status` locally. Then ask “Show available cash and my three largest holdings in my account currency.” That second question tests the credentials and account permissions with the broker.

### Add a separate ISA

If your primary key belongs to Invest, switch to your ISA in the **same environment**, generate a second read-only key pair and add these lines to the same file. Restart the client and ask for the `isa` account. If your only account is an ISA, use its pair as `primary`. [Trading 212 key guide](https://helpcentre.trading212.com/hc/en-us/articles/14584770928157-Trading-212-API-key)

```dotenv
T212_ISA_API_KEY=replace-with-your-isa-api-key
T212_ISA_API_SECRET=replace-with-your-isa-api-secret
```

Labels describe your configuration. Before combining balances, privately compare `account.id` from `get_account_summary` for each label with the number in Trading 212 under **Menu → My account → Account details**. If the numbers match each other, both pairs point to the same account. [Account reference numbers](https://helpcentre.trading212.com/hc/en-us/articles/360008823837-Where-can-I-find-my-account-reference-number)

### Named accounts in a private TOML file

For more than two accounts or separately configured demo and live accounts, use a private TOML file. Create it with the same owner-only permissions as `broker.env` before entering keys. Keep just `T212_CONFIG_FILE=/absolute/path/to/private/accounts.toml` in `broker.env` for this setup. Existing credential pairs in the process environment take precedence over the corresponding file credentials.

```toml
[trading]
T212_ENV = "demo"
T212_API_KEY = "replace-with-your-primary-key"
T212_API_SECRET = "replace-with-your-primary-secret"
T212_ENABLE_WRITES = false

[trading_accounts.invest]
T212_ENV = "live"
T212_API_KEY = "replace-with-your-invest-key"
T212_API_SECRET = "replace-with-your-invest-secret"
```

For paths containing spaces, the client can launch the installed `/absolute/path/to/trading212-mcp/.venv/bin/trading212-mcp` directly with `"args": []` and `"env": {"T212_CONFIG_FILE": "/absolute/path/to/private/accounts.toml"}`. On Windows the installed command is in `.venv\Scripts\trading212-mcp.exe`.

The `[trading]` section defines `primary`. Each `[trading_accounts.<label>]` section adds a read-only account you can request by label. Set the environment explicitly for each pair. Use `trading_status` to check the configuration after restarting the client.

## Read tools

| Tool | Broker permission | What you can ask |
| --- | --- | --- |
| `trading_status` | Local, no key required | Which environment, account labels and order settings are configured? |
| `get_account_summary` | `account` | What are my total account value, available cash and invested value? |
| `list_positions` | `portfolio` | How much is each holding worth, and how much have I gained or lost on it? |
| `list_pending_orders` | `orders:read` | Which orders are still open? |
| `trading_history` | `history:orders`, `history:dividends` or `history:transactions` for the chosen feed | Which dividends did I receive last quarter, and which dates were checked? |
| `search_instruments` | `metadata` | Which broker ticker and ISIN correspond to this share class? |

The five broker read tools accept an `account` argument that defaults to `primary`. Positions carry a per-share `currentPrice` in `instrument.currency` and a whole-position `walletImpact.currentValue` in `walletImpact.currency`. Use the latter to rank holdings in a common currency. The account summary separates `cash.availableToTrade`, cash in Pies and cash reserved for orders. Broker JSON fractions are returned as strings to preserve precision. [Position fields](https://docs.trading212.com/api/positions/getpositions) · [Account summary fields](https://docs.trading212.com/api/accounts/getaccountsummary)

History returns up to 50 records per call. To cover a period, follow each returned `next_page_path` on the same feed and account until you cover the requested dates or reach the end. Report any `coverage_warning` alongside the result. On a rate limit, wait for the broker's stated interval. [Trading 212 pagination and rate limits](https://docs.trading212.com/api/section/pagination)

## Optional order placement

For primary-account **DAY limit orders**, give that account’s key the `account`, `metadata` and `orders:execute` scopes, set `T212_ENABLE_WRITES=true`, and restart the server. Try this flow in `demo` with practice funds. In `live` an approved submission can trade real money. Every additional account is read-only. [Trading 212 limit orders](https://docs.trading212.com/api/orders/placelimitorder)

1. `preview_limit_order` takes an exact broker ticker, `buy` or `sell`, a positive share quantity and a positive per-share limit price, both supplied as decimal strings. The preview shows the account ending, environment, quote currency, quantity and value at the limit before fees or FX. It expires after five minutes.
2. `submit_limit_order` takes the preview ID and requests approval through an MCP **elicitation form**. Use a trusted client that displays forms to you and has automatic approval disabled. Check the environment, account, ticker, direction, quantity, price and currency before approving. A client without form support cannot complete a submission.
3. Each preview allows one submission attempt. An order ID acknowledges submission. Check its status in Trading 212 to confirm fills or cancel an open order. If the connection fails during submission, check pending orders and history before creating another preview. Sending another order could duplicate the first.

## Stock and portfolio analysis

Clients that support MCP prompts can retrieve `analyze_stock` and `analyze_portfolio_risk`. Each is also a standalone Agent Skill in the checkout.

- **Single stock.** “Using the latest annual and interim filings, how much of this company’s reported operating profit turned into cash?” The skill identifies the share class, dates its sources and distinguishes reported results from valuation assumptions. [Stock analysis skill](skills/analyze-stock/SKILL.md)
- **Portfolio risk.** “Across Invest and ISA, how exposed am I to my largest issuer, including any holdings inside funds? Show the effect of a 15% fall and quantify the unknown part.” The skill reconciles broker values, checks for overlap and shows its calculation. [Portfolio risk skill](skills/analyze-portfolio-risk/SKILL.md)

Public company filings and fund holdings can be read by a client with web access or supplied directly. The research workflow can use free sources. A public issuer lookup needs only a company name, ticker or ISIN.

## Privacy, risk and licence

The client starts this server locally over stdio. The server sends authenticated requests to Trading 212 over HTTPS. Its results can include account numbers, balances, holdings and trades. A cloud-backed MCP client may send those results to its model provider. Choose a client and data policy appropriate for your financial information. To revoke a key pair, delete it under **Settings → API (Beta)** in Trading 212. [Trading 212 key guide](https://helpcentre.trading212.com/hc/en-us/articles/14584770928157-Trading-212-API-key)

Moein (moeinxyz) shares this independent personal project as-is under the MIT licence. Trading 212's API terms apply separately. Section 6.2 describes personal use for testing, and section 6.3 requires Trading 212's prior written consent for other uses, including developing an API application intended for other end users. Running a local copy with personal keys does not itself grant that consent. [Trading 212 API terms, §§6.2–6.3](https://www.trading212.com/legal-documentation/API-Terms_EN.pdf#page=6) · [MIT licence](LICENSE)

This software and its analysis prompts are for information only and do not provide investment advice. Figures and model interpretations can be wrong or out of date. You make your own investment decisions and can lose money, including when an order behaves differently from what you expect. The MIT licence disclaims warranties and limits the author’s liability. [MIT licence](LICENSE)
