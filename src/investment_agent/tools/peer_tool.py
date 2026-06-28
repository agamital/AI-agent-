import logging

from investment_agent.schemas.company import MetricsResult
from investment_agent.tools.market_tool import get_market_data
from investment_agent.tools.metrics_tool import calculate_metrics
from investment_agent.tools.sec_tool import get_cik_for_ticker, get_company_facts, extract_annual_financials

logger = logging.getLogger(__name__)


def _fetch_metrics_for_ticker(ticker: str) -> MetricsResult | None:
    """Run the full SEC + market pipeline for a single ticker and return its metrics.

    For ETFs (no SEC CIK), build metrics from the ETF's own fund data instead
    of company financials — using the fund-level P/E where available.
    """
    market = get_market_data(ticker)

    # ETF path: no SEC filings, use fund-level metrics
    if market is not None and getattr(market, "is_etf", False):
        return MetricsResult(
            ticker=ticker,
            pe_ratio=market.etf_pe,          # weighted P/E of holdings
            pb_ratio=None,                   # not meaningful for a fund
            ps_ratio=None,
            roe=None,
            roa=None,
            net_profit_margin=None,
            operating_margin=None,
            debt_to_equity=None,
        )

    # Regular company path: requires SEC data
    cik = get_cik_for_ticker(ticker)
    if cik is None:
        return None

    facts = get_company_facts(cik)
    financial = extract_annual_financials(facts, ticker) if facts else None

    if financial is None and market is None:
        logger.warning("No data available for ticker %s — skipping.", ticker)
        return None

    return calculate_metrics(financial, market)


def get_peer_comparison(ticker: str, peers: list[str]) -> list[MetricsResult]:
    """Fetch and return metrics for a ticker and its peers, for side-by-side comparison.

    Tickers that fail to fetch are skipped and logged. Always returns at least an empty list.
    """
    all_tickers = [ticker] + peers
    results = []

    for t in all_tickers:
        metrics = _fetch_metrics_for_ticker(t)
        if metrics is not None:
            results.append(metrics)

    return results
