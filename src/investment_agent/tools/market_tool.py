import logging
import yfinance as yf
from investment_agent.schemas.company import MarketData

logger = logging.getLogger(__name__)


def get_market_data(ticker: str) -> MarketData | None:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        hist = stock.history(period="6mo")

        if not hist.empty:
            raw_prices = hist["Close"].round(2).tolist()
            price_history = [p for p in raw_prices if p == p]
            price_dates = [
                d.strftime("%Y-%m-%d")
                for d, p in zip(hist.index, raw_prices)
                if p == p
            ]
        else:
            price_history = None
            price_dates = None

        # market_cap / beta — try multiple field names (ETFs use different keys)
        market_cap = (
            info.get("marketCap")
            or info.get("totalAssets")  # ETFs report AUM here
        )
        beta = info.get("beta") or info.get("beta3Year")

        return MarketData(
            ticker=ticker,
            current_price=info.get("currentPrice") or info.get("regularMarketPrice"),
            previous_close=info.get("previousClose") or info.get("regularMarketPreviousClose"),
            week_52_high=info.get("fiftyTwoWeekHigh"),
            week_52_low=info.get("fiftyTwoWeekLow"),
            market_cap=market_cap,
            average_volume=info.get("averageVolume"),
            beta=beta,
            price_history=price_history,
            price_dates=price_dates,
        )
    except Exception as exc:
        logger.error("Failed to fetch market data for %s: %s", ticker, exc)
        return None
