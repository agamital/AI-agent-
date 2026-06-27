"""
Ticker validator — checks if a ticker is supported and identifies asset type
before running analysis.
"""

import logging
import yfinance as yf
from investment_agent.tools.sec_tool import get_cik_for_ticker

logger = logging.getLogger(__name__)

# Asset types we explicitly do NOT support
_BLOCKED_TYPES = {"CRYPTOCURRENCY", "CURRENCY", "FUTURE", "OPTION"}


def validate_ticker(ticker: str) -> dict:
    """
    Check what data is available for a ticker and identify its asset type.
    Returns a dict with availability flags, asset type, and a user-friendly message.
    """
    ticker = ticker.upper().strip()
    result = {
        "ticker": ticker,
        "asset_type": "UNKNOWN",
        "has_sec_data": False,
        "has_market_data": False,
        "is_supported": False,
        "is_etf": False,
        "message": "",
        "warning": "",
    }

    # SEC check
    cik = get_cik_for_ticker(ticker)
    result["has_sec_data"] = cik is not None

    # Market data + asset type check
    asset_type = "UNKNOWN"
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        result["has_market_data"] = price is not None
        asset_type = (info.get("quoteType") or "UNKNOWN").upper()
        result["asset_type"] = asset_type
    except Exception:
        result["has_market_data"] = False

    # ── Decision logic ──────────────────────────────────────────────

    # 1. Blocked asset types (crypto, forex, futures, options)
    if asset_type in _BLOCKED_TYPES:
        result["is_supported"] = False
        result["message"] = (
            f"❌ '{ticker}' is a {asset_type.lower()}, not a stock. "
            f"This agent specialises in equity research for U.S.-listed companies. "
            f"It does not analyse cryptocurrencies, forex, futures, or options."
        )
        return result

    # 2. Nothing found at all
    if not result["has_sec_data"] and not result["has_market_data"]:
        result["is_supported"] = False
        result["message"] = (
            f"❌ '{ticker}' was not found in U.S. markets (SEC EDGAR + yfinance). "
            f"This agent supports U.S.-listed stocks only (NYSE, NASDAQ, etc.). "
            f"Non-U.S. stocks like Israeli (TASE), European, or Asian listed companies "
            f"are not supported. If this is a U.S. stock, please check the ticker symbol."
        )
        return result

    # 3. ETF / fund — supported but technical-only
    if asset_type in {"ETF", "MUTUALFUND", "INDEX"}:
        result["is_supported"] = True
        result["is_etf"] = True
        result["warning"] = (
            f"⚠️ '{ticker}' is an {asset_type}, not an individual company. "
            f"ETFs and funds don't file company financials, so valuation ratios "
            f"(P/E, ROE, margins) and the Bull/Bear fundamental case won't apply. "
            f"The report will focus on price/technical analysis and market data only."
        )
        result["message"] = f"✅ '{ticker}' supported as an {asset_type} (technical analysis only)."
        return result

    # 4. Equity with market data but no SEC filing (foreign ADR, etc.)
    if not result["has_sec_data"] and result["has_market_data"]:
        result["is_supported"] = True
        result["warning"] = (
            f"⚠️ '{ticker}' has market data but no SEC EDGAR filing. "
            f"The report will include technical analysis and market metrics only. "
            f"Fundamental financial data (revenue, earnings) will not be available."
        )
        result["message"] = f"✅ '{ticker}' supported with partial data (market only)."
        return result

    # 5. Full support — equity with both SEC and market data
    result["is_supported"] = True
    result["message"] = f"✅ '{ticker}' fully supported."
    return result
