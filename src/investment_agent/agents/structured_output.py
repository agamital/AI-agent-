"""
Helper that runs the agent's data pipeline and returns BOTH the raw data
(for charts) and a SHORT LLM-generated narrative (Bull/Bear + summary only).

This keeps token usage low: charts/tables come from data, the LLM only
writes the qualitative analysis.
"""

import logging
from datetime import datetime

from investment_agent.llm.client import Message
from investment_agent.validation.ticker_validator import validate_ticker

logger = logging.getLogger(__name__)


_NARRATIVE_PROMPT = """You are a senior equity research analyst.
Based ONLY on the data provided, write a CONCISE qualitative analysis.
Do NOT repeat the raw numbers in tables — those are shown separately as charts.

Output EXACTLY these sections in Markdown, nothing else:

## 🟢 Bull Case
3-4 short bullet points — data-backed reasons the stock could outperform.

## 🔴 Bear Case
3-4 short bullet points — data-backed risks.

## 📌 Bottom Line
2-3 sentences summarising the picture. Never give a buy/sell recommendation.

Keep it tight. No preamble, no disclaimer (added separately)."""


def analyse_structured(agent, ticker: str, peers: list = None) -> dict:
    """
    Run the full pipeline and return a dict:
    {
      "ok": bool,
      "ticker": str,
      "asset_type": str,
      "warning": str,
      "error": str,
      "market": MarketData,
      "financial": FinancialData,
      "metrics": MetricsResult,
      "technical": TechnicalIndicators,
      "news": NewsSentiment,
      "peers_data": list,
      "narrative": str,   # short LLM markdown (Bull/Bear/Bottom line)
      "warnings": list,
    }
    """
    ticker = ticker.upper().strip()
    peers = [p.upper().strip() for p in peers] if peers else []

    # Validate
    validation = validate_ticker(ticker)
    if not validation["is_supported"]:
        return {"ok": False, "ticker": ticker, "error": validation["message"]}

    # Collect data (reuses the agent's pipeline + cache)
    data = agent._collect_data(ticker, asset_type=validation["asset_type"])

    # Peers
    peers_data = None
    if peers:
        from investment_agent.tools.peer_tool import get_peer_comparison
        peers_data = get_peer_comparison(ticker, peers)

    # Build a compact data summary for the narrative LLM call
    summary = agent._build_data_summary(ticker, data, peers_data)

    narrative = agent.client.chat([
        Message(role="system", content=_NARRATIVE_PROMPT),
        Message(role="user", content=f"Data for {ticker}:\n\n{summary}"),
    ], temperature=0.3, max_tokens=900)

    if not narrative:
        narrative = "_⚠️ ניתוח איכותי לא זמין כרגע (מכסת API נוצלה). הגרפים והנתונים למטה עדיין תקפים._"

    # Store narrative in memory so follow-ups have context
    agent.memory.add("user", f"Analysis request for {ticker}")
    agent.memory.add("assistant", narrative)

    return {
        "ok": True,
        "ticker": ticker,
        "asset_type": validation["asset_type"],
        "warning": validation.get("warning", ""),
        "error": "",
        "market": data.get("market"),
        "financial": data.get("financial"),
        "metrics": data.get("metrics"),
        "technical": data.get("technical"),
        "news": data.get("news"),
        "peers_data": peers_data,
        "narrative": narrative,
        "warnings": data.get("warnings", []),
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
