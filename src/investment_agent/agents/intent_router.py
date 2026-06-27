"""
Intent Router — understands free-text requests (Hebrew or English)
and extracts the user's intent: which ticker, which peers, or a follow-up.
Uses the LLM to parse, then returns a structured dict.
"""

import json
import logging
import re

from investment_agent.llm.client import LLMClient, Message

logger = logging.getLogger(__name__)

_ROUTER_PROMPT = """You are an intent parser for an investment research agent.
The user writes in Hebrew or English. Extract their intent into JSON.

Possible intents:
1. "analyze" — user wants a full research report on a stock/ETF.
   Extract the ticker symbol and any peer tickers mentioned.
2. "followup" — user asks a question about a stock already discussed
   (e.g. "what about its RSI?", "מה לגבי הסיכונים?").
3. "off_topic" — user asks something unrelated to investing.

You must map company NAMES to their U.S. ticker symbols. Examples:
- "אפל" / "Apple" → AAPL
- "מיקרוסופט" / "Microsoft" → MSFT
- "טבע" / "Teva" → TEVA
- "גוגל" / "Google" → GOOGL
- "אנבידיה" / "Nvidia" → NVDA
- "טסלה" / "Tesla" → TSLA
- "אמזון" / "Amazon" → AMZN
- "מטא" / "פייסבוק" → META
- "נטפליקס" → NFLX
If a company name has no clear U.S. ticker, set ticker to null.

Respond with ONLY a JSON object, no other text:
{
  "intent": "analyze" | "followup" | "off_topic",
  "ticker": "AAPL" or null,
  "peers": ["MSFT", "GOOGL"] or [],
  "original_language": "he" or "en"
}

Examples:
User: "תנתח לי את אפל"
{"intent":"analyze","ticker":"AAPL","peers":[],"original_language":"he"}

User: "compare Teva with Pfizer and Moderna"
{"intent":"analyze","ticker":"TEVA","peers":["PFE","MRNA"],"original_language":"en"}

User: "מה ה-RSI אומר?"
{"intent":"followup","ticker":null,"peers":[],"original_language":"he"}

User: "מה מתכון לפיצה?"
{"intent":"off_topic","ticker":null,"peers":[],"original_language":"he"}
"""


def parse_intent(client: LLMClient, user_message: str) -> dict:
    """Parse a free-text message into a structured intent dict."""
    response = client.chat([
        Message(role="system", content=_ROUTER_PROMPT),
        Message(role="user", content=user_message),
    ], temperature=0.0)

    if not response:
        # Fallback: try to grab an uppercase ticker-like token
        match = re.search(r'\b[A-Z]{1,5}\b', user_message)
        return {
            "intent": "analyze" if match else "off_topic",
            "ticker": match.group(0) if match else None,
            "peers": [],
            "original_language": "he",
        }

    # Strip markdown code fences if present
    cleaned = response.strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)

    try:
        parsed = json.loads(cleaned)
        # Normalise
        parsed.setdefault("intent", "off_topic")
        parsed.setdefault("ticker", None)
        parsed.setdefault("peers", [])
        parsed.setdefault("original_language", "he")
        if parsed["ticker"]:
            parsed["ticker"] = parsed["ticker"].upper().strip()
        parsed["peers"] = [p.upper().strip() for p in parsed.get("peers", [])]
        return parsed
    except json.JSONDecodeError:
        logger.warning("Router returned non-JSON: %s", response)
        return {
            "intent": "off_topic",
            "ticker": None,
            "peers": [],
            "original_language": "he",
        }
