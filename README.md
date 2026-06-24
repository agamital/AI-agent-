# Investment Research Agent

Python-based AI agent for investment research on publicly traded U.S. companies.

The system receives a stock ticker and optional peer tickers, retrieves financial and market data, calculates financial and technical metrics, and generates a structured investment research report.

This project is an educational AI Agents project. It is designed as a decision-support tool only. It does not provide personalized financial advice, automatic buy or sell recommendations, or trading execution.

## Project Goal

Build a modular investment research agent that can:

- Receive a stock ticker from the user
- Retrieve structured company and financial data
- Retrieve historical market price data
- Calculate financial metrics
- Calculate basic technical indicators
- Compare the company with selected peers
- Generate a structured research report
- Clearly state assumptions, missing data, and limitations

## Architecture Principle

Python tools retrieve data and calculate metrics.

LLM agents interpret the results and generate structured explanations.

The LLM should not invent financial numbers or calculate financial metrics by itself.

## Tools (implemented)

All five tools are built, are pure Python (no LLM calls), and handle their own
errors — returning `None` and logging on failure rather than crashing.

- **SEC EDGAR tool** (`tools/sec_tool.py`) — ticker → CIK lookup (disk-cached),
  company-facts retrieval, and extraction of the latest annual financials.
- **Market data tool** (`tools/market_tool.py`) — current price, 52-week range,
  market cap, beta, and 6 months of price history via yfinance.
- **Financial metrics calculator** (`tools/metrics_tool.py`) — valuation and
  profitability ratios (P/E, P/B, P/S, ROE, ROA, D/E, margins).
- **Technical indicators calculator** (`tools/technical_tool.py`) — SMA, EMA,
  RSI (Wilder's smoothing), and MACD.
- **Peer comparison tool** (`tools/peer_tool.py`) — runs the full data pipeline
  for a company and its peers and returns side-by-side metrics.

## Data Validation (implemented)

`validation/data_validator.py` inspects a data model for missing (`None`) fields
and returns plain-English warnings, so an agent can disclose data gaps instead of
letting the LLM invent values.

## Planned Agents (not yet built)

- Investment Research Orchestrator
- Fundamental Analysis Agent
- Technical Analysis Agent
- Peer Comparison Agent
- Report Generation Agent

## Main Project Structure

investment_research_agent/
  configs/
  data/
  src/
    investment_agent/
      llm/
      agents/
      tools/
      memory/
      schemas/
      validation/
      reporting/
      app/
  scripts/
  reports/
  tests/

## Installation

This project uses Poetry.

Install dependencies:

poetry install

Add main dependencies if needed:

poetry add openai python-dotenv pydantic pyyaml requests pandas numpy yfinance streamlit

Add development dependencies:

poetry add --group dev pytest ruff black

Optional, if using Groq:

poetry add groq

## Environment Variables

Create a local .env file based on .env.example.

Never commit the real .env file to GitHub.

## Testing (implemented)

The tools and data validator are covered by 22 unit tests. The pure-math tools
(metrics, technical indicators, validator) are tested directly; the network tools
(SEC EDGAR, yfinance) are tested with mocked responses, so the whole suite runs
offline in under one second.

Run tests:

poetry run pytest -q

## Planned Commands (not yet built)

Run one analysis:

poetry run python scripts/run_agent.py --ticker INTU --peers ADBE CRM NOW

Run Streamlit UI:

poetry run streamlit run src/investment_agent/app/streamlit_app.py

## Team Workflow

1. Pull latest main.
2. Create a feature branch.
3. Work only on the assigned task.
4. Run tests before pushing.
5. Commit with a clear message.
6. Push the branch.
7. Open a Pull Request.

## Important Rules

- Do not commit API keys.
- Do not commit .env.
- Do not work directly on main after initial setup.
- Keep Python calculations inside tools.
- Keep LLM usage inside agents.
- Every important tool should have tests.
- If data is missing, report it clearly instead of inventing values.

## Project Status

**Days 1–2 complete (Foundation).** Done so far:

- All Pydantic data schemas
- All 5 data/calculation tools, with error handling
- Data validator for missing-field detection
- 22 passing unit tests (pure-math direct, network tools mocked)

Next: Groq LLM client + the 6-component system prompt (Day 3), then conversational
memory and the LangGraph agents/orchestrator.
