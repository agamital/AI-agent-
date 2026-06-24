import logging

from investment_agent.schemas.company import FinancialData, MarketData, MetricsResult

logger = logging.getLogger(__name__)


def _safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    """Divide two numbers, returning None if either is None or denominator is zero."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return round(numerator / denominator, 4)


def calculate_metrics(financial: FinancialData, market: MarketData) -> MetricsResult | None:
    """Compute valuation and profitability ratios from SEC and market data.

    Returns a MetricsResult model, or None if both inputs are missing.
    """
    if financial is None and market is None:
        logger.error("Cannot calculate metrics: both financial and market data are None.")
        return None

    mc = market.market_cap if market else None

    return MetricsResult(
        ticker=financial.ticker if financial else market.ticker,
        pe_ratio=_safe_divide(mc, financial.net_income if financial else None),
        pb_ratio=_safe_divide(mc, financial.total_equity if financial else None),
        ps_ratio=_safe_divide(mc, financial.revenue if financial else None),
        roe=_safe_divide(financial.net_income, financial.total_equity) if financial else None,
        roa=_safe_divide(financial.net_income, financial.total_assets) if financial else None,
        debt_to_equity=_safe_divide(financial.total_liabilities, financial.total_equity) if financial else None,
        net_profit_margin=_safe_divide(financial.net_income, financial.revenue) if financial else None,
        operating_margin=_safe_divide(financial.operating_income, financial.revenue) if financial else None,
    )
