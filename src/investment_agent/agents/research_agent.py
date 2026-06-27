"""
Investment Research Agent — the main brain.
"""

import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

sys.path.insert(0, '/content/investment_research_agent/src')

from investment_agent.llm.client import LLMClient, Message
from investment_agent.tools.sec_tool import get_cik_for_ticker, get_company_facts, extract_annual_financials
from investment_agent.tools.market_tool import get_market_data
from investment_agent.tools.metrics_tool import calculate_metrics
from investment_agent.tools.technical_tool import calculate_technical_indicators
from investment_agent.tools.peer_tool import get_peer_comparison
from investment_agent.tools.news_tool import get_news_sentiment
from investment_agent.validation.data_validator import validate_financial_data
from investment_agent.validation.ticker_validator import validate_ticker

logger = logging.getLogger(__name__)


@dataclass
class ConversationMemory:
    messages: list[Message] = field(default_factory=list)
    analysed_tickers: dict = field(default_factory=dict)

    def add(self, role: str, content: str):
        self.messages.append(Message(role=role, content=content))

    def get_history(self) -> list[Message]:
        return self.messages.copy()

    def cache_ticker(self, ticker: str, data: dict):
        self.analysed_tickers[ticker.upper()] = data

    def get_cached(self, ticker: str) -> Optional[dict]:
        return self.analysed_tickers.get(ticker.upper())

    def clear(self):
        self.messages.clear()
        self.analysed_tickers.clear()


class InvestmentResearchAgent:

    SYSTEM_PROMPT = """You are a senior equity research analyst with 15 years of experience
covering U.S. publicly traded companies across all major sectors.
You are rigorous, data-driven, and intellectually honest.
You never speculate beyond the data and always disclose uncertainty.

## GOAL
Produce a complete, structured investment research report based ONLY on the data provided.
Never invent financial numbers. If a metric is missing, say "data not available".

## CONSTRAINTS
1. Never invent financial numbers — use only the data given.
2. Never make a buy, sell, or hold recommendation.
3. Never guarantee future performance.
4. Always include Bull Case and Bear Case sections.
5. Always list data gaps at the end.
6. Do not answer questions unrelated to investment research.
7. If only partial data is available, write the report with what you have
   and clearly note what sections are missing and why.

## ASSET TYPE AWARENESS
If the data indicates the asset is an ETF or fund (not an individual company):
- Do NOT invent or imply company fundamentals (revenue, ROE, margins don't exist for funds).
- Focus the Bull/Bear case on the ETF's underlying index exposure, price trend,
  and technical indicators — NOT on company-specific reasoning.
- State clearly at the top: "Note: This is an ETF/fund, so company-level
  fundamental analysis does not apply."

## TECHNICAL INDICATOR INTERPRETATION (read carefully — do not contradict yourself)
- Compare CURRENT PRICE to the moving averages:
  * If current price is ABOVE SMA-20 and SMA-50 → bullish / uptrend.
  * If current price is BELOW SMA-20 and SMA-50 → bearish / downtrend.
- RSI above 70 → overbought. RSI below 30 → oversold. Between 30-70 → neutral.
- MACD: if MACD line is ABOVE the signal line → bullish. If BELOW → bearish.
- Be consistent: do not give a bullish reason and a bearish reason that
  use the same indicator in contradictory ways.

## OUTPUT FORMAT
# Investment Research Report: {TICKER} — {COMPANY NAME}
*Generated: {DATE}*

---

## 1. Company Snapshot
## 2. Valuation Analysis (table)
## 3. Profitability & Financial Health (table)
## 4. Technical Analysis (table + interpretation)
## 5. Peer Comparison (if peers provided)
## 6. News & Sentiment
## 7. Bull Case 🟢 (3-5 points)
## 8. Bear Case 🔴 (3-5 points)
## 9. Data Gaps & Limitations

---
*Disclaimer: This report is for educational purposes only and does not constitute
financial advice or a recommendation to buy, sell, or hold any security.*"""

    def __init__(self):
        self.client = LLMClient()
        self.memory = ConversationMemory()
        print(f"✅ Agent initialised — provider: {self.client.active_provider}")

    def _collect_data(self, ticker: str, asset_type: str = "EQUITY") -> dict:
        cached = self.memory.get_cached(ticker)
        if cached:
            print(f"  📦 Using cached data for {ticker}")
            return cached

        print(f"  🔍 Fetching data for {ticker}...")
        data = {"ticker": ticker, "asset_type": asset_type}

        cik = get_cik_for_ticker(ticker)
        if cik:
            facts = get_company_facts(cik)
            data["financial"] = extract_annual_financials(facts, ticker) if facts else None
        else:
            data["financial"] = None

        data["market"] = get_market_data(ticker)

        if data["financial"] or data["market"]:
            data["metrics"] = calculate_metrics(data["financial"], data["market"])
        else:
            data["metrics"] = None

        if data["market"] and data["market"].price_history:
            data["technical"] = calculate_technical_indicators(data["market"])
        else:
            data["technical"] = None

        data["news"] = get_news_sentiment(ticker)

        warnings = []
        for key in ["financial", "market", "metrics"]:
            if data.get(key):
                warnings.extend(validate_financial_data(data[key]))
        data["warnings"] = warnings

        self.memory.cache_ticker(ticker, data)
        return data

    def _build_data_summary(self, ticker: str, data: dict, peers_data: list = None) -> str:
        lines = [f"=== DATA FOR {ticker} ===\n"]

        # Asset type header — so the LLM knows what it's analysing
        asset_type = data.get("asset_type", "EQUITY")
        lines.append(f"ASSET TYPE: {asset_type}")
        if asset_type in {"ETF", "MUTUALFUND", "INDEX"}:
            lines.append("(This is a fund/ETF — company fundamentals do NOT apply.)")
        lines.append("")

        m = data.get("market")
        if m:
            lines.append("## MARKET DATA")
            lines.append(f"Current Price: ${m.current_price}")
            lines.append(f"Previous Close: ${m.previous_close}")
            lines.append(f"52-Week High: ${m.week_52_high}")
            lines.append(f"52-Week Low: ${m.week_52_low}")
            lines.append(f"Market Cap: ${m.market_cap:,.0f}" if m.market_cap else "Market Cap: N/A")
            lines.append(f"Beta: {m.beta}" if m.beta else "Beta: N/A")
            lines.append(f"Avg Volume: {m.average_volume:,.0f}" if m.average_volume else "Avg Volume: N/A")

        f = data.get("financial")
        if f:
            lines.append("\n## FINANCIAL DATA (Annual)")
            lines.append(f"Fiscal Year: {f.fiscal_year}")
            lines.append(f"Revenue: ${f.revenue:,.0f}" if f.revenue else "Revenue: N/A")
            lines.append(f"Net Income: ${f.net_income:,.0f}" if f.net_income else "Net Income: N/A")
            lines.append(f"Operating Income: ${f.operating_income:,.0f}" if f.operating_income else "Operating Income: N/A")
            lines.append(f"Total Assets: ${f.total_assets:,.0f}" if f.total_assets else "Total Assets: N/A")
            lines.append(f"Total Equity: ${f.total_equity:,.0f}" if f.total_equity else "Total Equity: N/A")
            lines.append(f"EPS Diluted: ${f.eps_diluted}" if f.eps_diluted else "EPS Diluted: N/A")
        else:
            lines.append("\n## FINANCIAL DATA: Not available (no SEC company filing — normal for ETFs/funds)")

        met = data.get("metrics")
        if met:
            lines.append("\n## VALUATION & PROFITABILITY METRICS")
            lines.append(f"P/E Ratio: {met.pe_ratio}")
            lines.append(f"P/B Ratio: {met.pb_ratio}")
            lines.append(f"P/S Ratio: {met.ps_ratio}")
            lines.append(f"ROE: {met.roe}")
            lines.append(f"ROA: {met.roa}")
            lines.append(f"Debt/Equity: {met.debt_to_equity}")
            lines.append(f"Net Margin: {met.net_profit_margin}")
            lines.append(f"Operating Margin: {met.operating_margin}")

        t = data.get("technical")
        if t:
            lines.append("\n## TECHNICAL INDICATORS")
            lines.append(f"Current Price: ${m.current_price if m else 'N/A'}")
            lines.append(f"SMA-20: {t.sma_20}")
            lines.append(f"SMA-50: {t.sma_50}")
            lines.append(f"EMA-20: {t.ema_20}")
            lines.append(f"RSI-14: {t.rsi_14}")
            lines.append(f"MACD Line: {t.macd_line}")
            lines.append(f"MACD Signal: {t.macd_signal}")
            lines.append(f"MACD Histogram: {t.macd_histogram}")

        n = data.get("news")
        if n:
            lines.append("\n## NEWS & SENTIMENT")
            lines.append(f"Overall Sentiment: {n.overall_sentiment}")
            lines.append(f"Articles Analysed: {n.total_articles}")
            lines.append(f"Positive: {n.positive_count} | Negative: {n.negative_count} | Neutral: {n.neutral_count}")
            if n.key_themes:
                lines.append(f"Key Themes: {', '.join(n.key_themes)}")
            if n.recent_headlines:
                lines.append("Recent Headlines:")
                for h in n.recent_headlines:
                    lines.append(f"  - {h}")

        if peers_data:
            lines.append("\n## PEER COMPARISON")
            lines.append("Ticker | P/E | P/B | P/S | ROE | Net Margin")
            lines.append("--- | --- | --- | --- | --- | ---")
            for p in peers_data:
                row = [
                    p.ticker,
                    str(p.pe_ratio) if p.pe_ratio else "N/A",
                    str(p.pb_ratio) if p.pb_ratio else "N/A",
                    str(p.ps_ratio) if p.ps_ratio else "N/A",
                    str(p.roe) if p.roe else "N/A",
                    str(p.net_profit_margin) if p.net_profit_margin else "N/A",
                ]
                lines.append(" | ".join(row))

        warnings = data.get("warnings", [])
        if warnings:
            lines.append(f"\n## DATA GAPS ({len(warnings)} missing fields)")
            for w in warnings:
                lines.append(f"  - {w}")

        return "\n".join(lines)

    def analyse(self, ticker: str, peers: list[str] = None) -> str:
        ticker = ticker.upper().strip()
        peers = [p.upper().strip() for p in peers] if peers else []

        # Validate ticker + identify asset type
        validation = validate_ticker(ticker)
        if not validation["is_supported"]:
            return validation["message"]

        warning_banner = ""
        if validation.get("warning"):
            warning_banner = f"> {validation['warning']}\n\n"
            print(validation["warning"])

        print(f"\n📊 Starting analysis for {ticker}" + (f" + peers: {peers}" if peers else ""))

        data = self._collect_data(ticker, asset_type=validation["asset_type"])

        peers_data = None
        if peers:
            print(f"  🔍 Fetching peer data...")
            peers_data = get_peer_comparison(ticker, peers)

        data_summary = self._build_data_summary(ticker, data, peers_data)

        today = datetime.now().strftime("%Y-%m-%d")
        peers_str = f" Compare with peers: {', '.join(peers)}." if peers else ""
        user_prompt = (
            f"Generate a complete investment research report for {ticker} as of {today}.{peers_str}\n\n"
            f"Use ONLY the following data:\n\n{data_summary}"
        )

        self.memory.add("user", user_prompt)
        print("  🤖 Generating report...")

        messages = [Message(role="system", content=self.SYSTEM_PROMPT)]
        messages.extend(self.memory.get_history())

        report = self.client.chat(messages, temperature=0.2)

        if report:
            self.memory.add("assistant", report)
            print("  ✅ Report generated!")
            # Prepend the warning banner so the user sees it
            return warning_banner + report
        else:
            return "❌ Failed to generate report. Please try again."

    def follow_up(self, question: str) -> str:
        self.memory.add("user", question)
        messages = [Message(role="system", content=self.SYSTEM_PROMPT)]
        messages.extend(self.memory.get_history())
        answer = self.client.chat(messages, temperature=0.3, max_tokens=700)
        if answer:
            self.memory.add("assistant", answer)
        else:
            answer = "❌ Failed to generate response."
        return answer

    def reset(self):
        self.memory.clear()
        print("🔄 Memory cleared.")
