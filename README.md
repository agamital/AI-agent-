# 📈 Investment Research Agent

An AI-powered investment research agent for U.S. publicly traded stocks and ETFs.
The user chats with it in **Hebrew or English** ("תנתח את אפל", "compare Google with Meta",
"איך אפל ביחס ל-QQQ?"), and the agent retrieves **real data** from SEC filings,
market feeds and news, then produces a **structured visual research report** —
charts, valuation/technical cards, peer comparisons, and an LLM-written Bull/Bear case.

🔗 **Live app:** [ai-stock-agent-ziv-tal.streamlit.app](https://ai-stock-agent-ziv-tal.streamlit.app)

> ⚠️ Educational project only. Not financial advice, not a buy/sell recommendation,
> and not a trading tool.

---

## ✨ What it does

- **Free-text chat interface** (Hebrew + English) — no forms. Type naturally and the
  agent understands intent: analyze a stock, compare against peers, ask a follow-up.
- **Real data, no hallucinated numbers** — all financials, prices and metrics come
  from live tools. The LLM only *interprets*; it never invents figures.
- **Visual reports** — interactive Plotly charts (price history, RSI gauge, peer bars),
  snapshot tiles, and colour-coded badges (Premium / Strong / Bullish / Overbought).
- **Smart routing** — maps company names to tickers (פייסבוק → META, אפל → AAPL),
  resolves context ("how does *it* compare to QQQ?" after analysing AAPL).
- **ETF / crypto awareness** — detects ETFs (SPY, QQQ) and runs technical-only analysis;
  blocks unsupported assets (crypto, forex, non-US) with a clear message.
- **Live API quota meter** — sidebar shows remaining Groq tokens and reset time.
- **Graceful degradation** — when the API quota runs out, charts still render from data
  and the user gets a clear "quota exhausted, retry in X" message instead of a crash.

---

## 🏗️ Architecture

The core principle: **Python tools fetch & compute data; the LLM interprets it.**
The LLM never calculates a financial metric or invents a number.

```
User (Hebrew/English chat)
        │
        ▼
  Intent Router  ──►  {analyze | compare | followup | off_topic} + ticker + peers
        │
        ▼
 Research Agent  ──►  orchestrates tools + memory
        │
        ├─ Tools (data, no LLM):
        │    • sec_tool       — SEC EDGAR 10-K financials
        │    • market_tool    — yfinance price / market cap / beta / history
        │    • metrics_tool   — P/E, P/B, P/S, ROE, ROA, margins, D/E
        │    • technical_tool — SMA, EMA, RSI, MACD
        │    • peer_tool      — side-by-side peer comparison
        │    • news_tool      — headlines → sentiment + themes
        │
        ├─ Validation:
        │    • ticker_validator — asset type, ETF/crypto detection
        │    • data_validator   — missing-field warnings
        │
        ├─ Charts (data → Plotly, no LLM tokens):
        │    • price_chart, rsi_gauge, metrics_bar, snapshot_metrics
        │    • usage_bar + colour badges
        │
        └─ LLM (Groq Llama-3.3-70B, Gemini fallback):
             • narrative only — Bull / Bear / Bottom-line + follow-ups
        │
        ▼
   Streamlit UI  ──►  chat + visual report cards
```

### LLM setup
- **Primary:** Groq `llama-3.3-70b-versatile` (fast, free tier)
- **Fallback:** Google `gemini-2.5-flash`
- Automatic retry with exponential backoff; rate-limit detection with friendly messaging.

---

## 📂 Project structure

```
streamlit_app.py              # Main UI: chat + visual report rendering
src/investment_agent/
├── agents/
│   ├── research_agent.py      # Orchestrator: tools + memory + 6-part system prompt
│   ├── intent_router.py       # Hebrew/English → structured intent
│   └── structured_output.py   # Runs pipeline, returns data + short LLM narrative
├── tools/
│   ├── sec_tool.py            # SEC EDGAR financials
│   ├── market_tool.py         # yfinance market data
│   ├── metrics_tool.py        # Valuation & profitability ratios
│   ├── technical_tool.py      # SMA / EMA / RSI / MACD
│   ├── peer_tool.py           # Peer comparison
│   └── news_tool.py           # News sentiment
├── validation/
│   ├── ticker_validator.py    # Asset-type detection, ETF/crypto handling
│   └── data_validator.py      # Data-quality warnings
├── reporting/
│   └── charts.py              # Plotly figures + badges (no LLM)
├── llm/
│   └── client.py              # Groq + Gemini client, retry, usage tracking
└── schemas/                   # Pydantic models (company, report)
```

---

## 🧠 System prompt design

The agent's system prompt is structured into six components:
**Persona** (senior equity analyst), **Goal**, **Constraints** (never invent numbers,
never recommend buy/sell), **Asset-type awareness** (ETF vs company), **Technical
interpretation rules** (consistent bullish/bearish logic), and a fixed **Output format**
(8 sections from Company Snapshot to Bull/Bear case).

---

## 🚀 Running locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API keys (create a .env file — see .env.example)
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key     # optional fallback
NEWS_API_KEY=your_newsapi_key      # optional, for news sentiment

# 3. Run
streamlit run streamlit_app.py
```

### Deployment
The app is deployed on **Streamlit Cloud**, auto-deploying from the `main` branch.
API keys are stored in Streamlit Secrets (not in the repo).

---

## 💬 Example queries

| You type | The agent does |
|---|---|
| `תנתח את מניית פייסבוק` | Full report on **META** (maps the name correctly) |
| `compare Google with Meta` | Side-by-side **GOOGL vs META** comparison |
| `איך אפל ביחס ל-QQQ?` | Adds **QQQ** as a peer to the current **AAPL** analysis |
| `מה ה-RSI אומר?` | Answers from memory about the current stock |
| `analyze SPY` | ETF-aware technical-only report |

---

## ⚙️ Token efficiency

To stay within the free-tier API limits, the architecture is deliberately
token-light: **charts and tables are built from raw data** (zero LLM tokens),
and the LLM is called only for the short qualitative narrative. Each call also
requests a right-sized `max_tokens` (router: 200, narrative: 900, follow-up: 700)
instead of a fixed 4096 — cutting token usage by roughly 70%.

---

## 📋 Tech stack

**Python** · **Streamlit** · **Plotly** · **Groq (Llama 3.3 70B)** · **Google Gemini** ·
**yfinance** · **SEC EDGAR API** · **NewsAPI** · **Pydantic**

---

*Built as an educational AI Agents project.*
