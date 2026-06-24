import logging

import yfinance as yf

from investment_agent.schemas.company import MarketData

logger = logging.getLogger(__name__)


def get_market_data(ticker: str) -> MarketData | None:
    """Fetch current market data and 90-day price history for a ticker via yfinance.

    Returns a MarketData model, or None if the request fails.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        hist = stock.history(period="6mo")
        price_history = hist["Close"].round(2).tolist() if not hist.empty else None
        price_dates = [d.strftime("%Y-%m-%d") for d in hist.index] if not hist.empty else None

        return MarketData(
            ticker=ticker,
            current_price=info.get("currentPrice") or info.get("regularMarketPrice"),
            previous_close=info.get("previousClose") or info.get("regularMarketPreviousClose"),
            week_52_high=info.get("fiftyTwoWeekHigh"),
            week_52_low=info.get("fiftyTwoWeekLow"),
            market_cap=info.get("marketCap"),
            average_volume=info.get("averageVolume"),
            beta=info.get("beta"),
            price_history=price_history,
            price_dates=price_dates,
        )
    except Exception as exc:
        logger.error("Failed to fetch market data for %s: %s", ticker, exc)
        return None
