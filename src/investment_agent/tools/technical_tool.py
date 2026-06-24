import logging

from investment_agent.schemas.company import MarketData, TechnicalIndicators

logger = logging.getLogger(__name__)


def _sma(prices: list[float], period: int) -> float | None:
    if len(prices) < period:
        return None
    return round(sum(prices[-period:]) / period, 4)


def _ema(prices: list[float], period: int) -> float | None:
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = price * k + ema * (1 - k)
    return round(ema, 4)


def _rsi(prices: list[float], period: int = 14) -> float | None:
    if len(prices) < period + 1:
        return None
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [c if c > 0 else 0.0 for c in changes]
    losses = [abs(c) if c < 0 else 0.0 for c in changes]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 4)


def calculate_technical_indicators(market: MarketData) -> TechnicalIndicators | None:
    """Compute technical indicators from the price history inside a MarketData object.

    Returns a TechnicalIndicators model, or None if price history is missing.
    """
    if market is None or not market.price_history:
        logger.error("Cannot calculate technical indicators: price history is missing.")
        return None

    prices = market.price_history

    ema12 = _ema(prices, 12)
    ema26 = _ema(prices, 26)

    if ema12 is not None and ema26 is not None:
        macd_line = round(ema12 - ema26, 4)
        macd_prices = [_ema(prices[:i], 12) - _ema(prices[:i], 26)
                       for i in range(26, len(prices) + 1)
                       if _ema(prices[:i], 12) is not None and _ema(prices[:i], 26) is not None]
        macd_signal = _ema(macd_prices, 9) if len(macd_prices) >= 9 else None
        macd_histogram = round(macd_line - macd_signal, 4) if macd_signal is not None else None
    else:
        macd_line = macd_signal = macd_histogram = None

    return TechnicalIndicators(
        ticker=market.ticker,
        sma_20=_sma(prices, 20),
        sma_50=_sma(prices, 50),
        ema_20=_ema(prices, 20),
        rsi_14=_rsi(prices),
        macd_line=macd_line,
        macd_signal=macd_signal,
        macd_histogram=macd_histogram,
    )
