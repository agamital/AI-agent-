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

# Popular ETFs (not always in SEC list, or to recognise instantly)
_KNOWN_ETFS = {
    "SPY", "QQQ", "VOO", "VTI", "IVV", "DIA", "IWM", "VEA", "VWO", "EFA",
    "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB", "XLRE",
    "VYM", "SCHD", "VIG", "DGRO", "GLD", "SLV", "TLT", "BND", "AGG", "LQD",
    "ARKK", "SOXX", "SMH", "VGT", "VUG", "VTV", "VNQ", "EEM", "GDX", "USO",
    "HYG", "EMB", "MUB", "VXUS", "BNDX", "VT", "ITOT", "SCHB", "SCHX", "RSP",
}

# Common company-name → ticker (covers names that aren't literal tickers)
_NAME_TO_TICKER = {
    "apple": "AAPL", "אפל": "AAPL",
    "microsoft": "MSFT", "מיקרוסופט": "MSFT",
    "google": "GOOGL", "alphabet": "GOOGL", "גוגל": "GOOGL",
    "amazon": "AMZN", "אמזון": "AMZN",
    "meta": "META", "facebook": "META", "פייסבוק": "META", "מטא": "META",
    "tesla": "TSLA", "טסלה": "TSLA",
    "nvidia": "NVDA", "אנבידיה": "NVDA",
    "netflix": "NFLX", "נטפליקס": "NFLX",
    "teva": "TEVA", "טבע": "TEVA",
    "ford": "F", "פורד": "F",
    "pfizer": "PFE", "פייזר": "PFE",
    "amd": "AMD", "intel": "INTC",
    "disney": "DIS", "boeing": "BA", "nike": "NKE",
    "coca cola": "KO", "cocacola": "KO", "pepsi": "PEP",
    "walmart": "WMT", "visa": "V", "mastercard": "MA",
    "jpmorgan": "JPM", "jp morgan": "JPM",
    "s&p": "SPY", "sp500": "SPY", "אס אנד פי": "SPY", "מדד 500": "SPY",
    "nasdaq": "QQQ", "נאסדק": "QQQ", "dow": "DIA",
}


def _data_fallback(user_message: str, current_ticker: str = None) -> dict:
    """Recognise tickers WITHOUT the LLM, using the SEC ticker map + known ETFs.
    Used when the LLM fails (rate limit) or returns nothing useful."""
    from investment_agent.tools.sec_tool import _load_ticker_map
    msg = user_message.strip()
    lower = msg.lower()

    # Build the universe of valid symbols
    try:
        sec_map = _load_ticker_map()
        valid_symbols = set(sec_map.keys()) | _KNOWN_ETFS
    except Exception:
        valid_symbols = _KNOWN_ETFS

    # Words that ARE valid SEC tickers but are almost always English/Hebrew words
    _STOP = {"VS", "WITH", "AND", "THE", "FOR", "ARE", "A", "AN", "TO", "OR",
             "IS", "IT", "ON", "IN", "OF", "BE", "E", "AT", "AS", "SO", "BY",
             "DO", "GO", "ME", "MY", "WE", "ALL", "ANY", "CAN", "HOW", "NOW",
             "SEE", "GET", "BIG", "NEW", "OLD", "TOP", "LOW", "BUY"}

    # 1. Find explicit ticker tokens (uppercase or matching a known symbol)
    tokens = re.findall(r"[A-Za-z][A-Za-z.\-]{0,5}", msg)
    found = []
    for tok in tokens:
        up = tok.upper()
        if up in _STOP:
            continue
        # Only accept lowercase tokens if they're a known ETF or a 2-5 letter match
        if up in valid_symbols and up not in found:
            found.append(up)

    # 2. Also scan for company names — keep them in order of appearance in the text
    name_hits = []
    for name, tk in _NAME_TO_TICKER.items():
        pos = lower.find(name)
        if pos >= 0 and tk not in found:
            name_hits.append((pos, tk))
    # Sort by position so the first-mentioned company comes first
    for pos, tk in sorted(name_hits):
        if tk not in found:
            found.append(tk)

    # 3. Decide intent from keywords
    is_compare = any(w in lower for w in
                     ["vs", "versus", "compare", "תשווה", "השווה", "מול", "ביחס", "לעומת"])

    if not found:
        return {"intent": "off_topic", "ticker": None, "peers": [],
                "original_language": "he"}

    if is_compare and len(found) >= 2:
        return {"intent": "compare", "ticker": found[0], "peers": found[1:],
                "original_language": "he"}
    if is_compare and len(found) == 1 and current_ticker:
        return {"intent": "compare", "ticker": current_ticker, "peers": found,
                "original_language": "he"}
    return {"intent": "analyze", "ticker": found[0], "peers": found[1:],
            "original_language": "he"}


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
        # LLM call failed — try the data-based fallback first (recognises tickers offline)
        fb = _data_fallback(user_message, current_ticker)
        if fb["ticker"]:
            return fb
        # No ticker found — if it was a rate limit, say so
        from investment_agent.llm.client import LAST_ERROR
        if LAST_ERROR.get("rate_limited"):
            return {"intent": "rate_limited", "ticker": None, "peers": [],
                    "original_language": "he", "message": LAST_ERROR.get("message", "")}
        return fb

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
