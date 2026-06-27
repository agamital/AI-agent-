"""
Intent Router — understands free-text requests (Hebrew or English)
and extracts intent: analyze, compare-with, followup, or off-topic.
"""

import json
import logging
import re

from investment_agent.llm.client import LLMClient, Message

logger = logging.getLogger(__name__)

_ROUTER_PROMPT = """You are an intent parser for an investment research agent.
The user writes in Hebrew or English. Extract their intent into JSON.

CONTEXT: The user may already be discussing a stock (given as CURRENT_TICKER).
Use that context to resolve references like "it", "this", "זה", "המניה".

Possible intents:
1. "analyze" — user wants a NEW full research report on a stock/ETF.
2. "compare" — user wants to compare the CURRENT stock against other tickers.
3. "followup" — a question about the current stock that needs NO new data.
4. "off_topic" — unrelated to investing.

Respond with ONLY a JSON object:
{
  "intent": "analyze" | "compare" | "followup" | "off_topic",
  "ticker": "AAPL" or null,
  "peers": ["MSFT"] or [],
  "original_language": "he" or "en"
}
"""

def parse_intent(client: LLMClient, user_message: str, current_ticker: str = None) -> dict:
    context = f"CURRENT_TICKER: {current_ticker}\n" if current_ticker else "CURRENT_TICKER: none\n"
    response = client.chat([
        Message(role="system", content=_ROUTER_PROMPT),
        Message(role="user", content=context + user_message),
    ], temperature=0.0)

    if not response:
        match = re.search(r'\b[A-Z]{1,5}\b', user_message)
        return {
            "intent": "analyze" if match else "off_topic",
            "ticker": match.group(0) if match else None,
            "peers": [], "original_language": "he",
        }

    cleaned = re.sub(r'^```(?:json)?\s*', '', response.strip())
    cleaned = re.sub(r'\s*```$', '', cleaned)

    try:
        parsed = json.loads(cleaned)
        parsed.setdefault("intent", "off_topic")
        return parsed
    except json.JSONDecodeError:
        return {"intent": "off_topic", "ticker": None, "peers": [], "original_language": "he"}
