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

## Planned Tools

- SEC or company facts retrieval tool
- Market data retrieval tool
- Financial metrics calculator
- Technical indicators calculator
- Peer comparison tool

## Planned Agents

- Investment Research Orchestrator
- Fundamental Analysis Agent
- Technical Analysis Agent
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

## Planned Commands

Run one analysis:

poetry run python scripts/run_agent.py --ticker INTU --peers ADBE CRM NOW

Run Streamlit UI:

poetry run streamlit run src/investment_agent/app/streamlit_app.py

Run tests:

poetry run pytest -q

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

Initial architecture setup in progress.
