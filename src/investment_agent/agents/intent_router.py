"""
Intent Router — understands free-text requests (Hebrew or English)
and extracts intent: analyze, compare, followup, or off-topic.
Maps company names to current U.S. ticker symbols.
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
   Examples: "תנתח את אפל", "analyze Tesla", "תראה לי את אנבידיה"
2. "compare" — user wants to compare one stock against others, OR compare the
   CURRENT stock to something. Set "ticker" to the MAIN stock, "peers" to the rest.
   Examples: "תשווה בין Google ל-Meta", "איך אפל ביחס ל-QQQ", "compare with SPY"
   If comparing the current stock to something, use CURRENT_TICKER as ticker.
3. "followup" — a question about the current stock needing NO new data.
   Examples: "מה ה-RSI אומר?", "למה זה מסוכן?", "what about the risks?"
4. "off_topic" — unrelated to investing.

Map company NAMES to CURRENT U.S. ticker symbols:
- אפל/Apple→AAPL, מיקרוסופט/Microsoft→MSFT, טבע/Teva→TEVA
- גוגל/Google→GOOGL (always GOOGL, never GOOG)
- אנבידיה/Nvidia→NVDA, טסלה/Tesla→TSLA, אמזון/Amazon→AMZN
- מטא/פייסבוק/facebook/Facebook→META (NOT the old FB symbol)
- נטפליקס/Netflix→NFLX, פייזר/Pfizer→PFE, פורד/Ford→F
- "אס אנד פי"/"S&P"/"מדד 500"→SPY, "נאסדק"/QQQ→QQQ, AMD→AMD
Use only CURRENT symbols. Never use delisted tickers like FB.
If a company name has no clear U.S. ticker, set ticker to null.

Respond with ONLY a JSON object, no other text:
{
  "intent": "analyze" | "compare" | "followup" | "off_topic",
  "ticker": "AAPL" or null,
  "peers": ["MSFT"] or [],
  "original_language": "he" or "en"
}

Examples (CURRENT_TICKER shown before each):
[none] "תנתח את מניית פייסבוק"
{"intent":"analyze","ticker":"META","peers":[],"original_language":"he"}

[none] "תשווה בין Google ל-Meta"
{"intent":"compare","ticker":"GOOGL","peers":["META"],"original_language":"he"}

[AAPL] "איך זה ביחס לאס אנד פי"
{"intent":"compare","ticker":"AAPL","peers":["SPY"],"original_language":"he"}

[AAPL] "מה ה-RSI אומר?"
{"intent":"followup","ticker":null,"peers":[],"original_language":"he"}

[none] "מה מתכון לפיצה?"
{"intent":"off_topic","ticker":null,"peers":[],"original_language":"he"}
"""


def parse_intent(client: LLMClient, user_message: str, current_ticker: str = None) -> dict:
    """Parse a free-text message into a structured intent dict."""
    context = f"CURRENT_TICKER: {current_ticker}\n" if current_ticker else "CURRENT_TICKER: none\n"

    response = client.chat([
        Message(role="system", content=_ROUTER_PROMPT),
        Message(role="user", content=context + user_message),
    ], temperature=0.0, max_tokens=200)

    if not response:
        # LLM call failed — check if it was a rate limit
        from investment_agent.llm.client import LAST_ERROR
        if LAST_ERROR.get("rate_limited"):
            return {"intent": "rate_limited", "ticker": None, "peers": [],
                    "original_language": "he", "message": LAST_ERROR.get("message", "")}
        # Otherwise try a simple ticker regex fallback
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
        parsed.setdefault("ticker", None)
        parsed.setdefault("peers", [])
        parsed.setdefault("original_language", "he")
        # Normalise tickers
        if parsed["ticker"]:
            parsed["ticker"] = parsed["ticker"].upper().strip()
        parsed["peers"] = [p.upper().strip() for p in parsed.get("peers", [])]
        return parsed
    except json.JSONDecodeError:
        logger.warning("Router returned non-JSON: %s", response)
        return {"intent": "off_topic", "ticker": None, "peers": [], "original_language": "he"}
