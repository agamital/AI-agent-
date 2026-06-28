"""
Comparison engine — builds a dynamic head-to-head comparison that adapts
to what is being compared:

  • stock vs stock   → valuation + profitability metrics (P/E, P/B, ROE, margins…)
  • any ETF involved → shared metrics that exist for both (P/E, yield, 3Y return,
                       beta, 52-week position, size)

Returns a structured dict the UI renders into a table — no LLM tokens used.
"""

import logging

from investment_agent.tools.market_tool import get_market_data
from investment_agent.tools.metrics_tool import calculate_metrics
from investment_agent.tools.sec_tool import (
    get_cik_for_ticker, get_company_facts, extract_annual_financials,
)

logger = logging.getLogger(__name__)


def _collect_entity(ticker: str) -> dict:
    """Gather everything needed for one ticker (stock or ETF) into a flat dict."""
    market = get_market_data(ticker)
    is_etf = bool(market and getattr(market, "is_etf", False))

    entity = {
        "ticker": ticker,
        "is_etf": is_etf,
        "price": market.current_price if market else None,
        "beta": market.beta if market else None,
        "market_cap": market.market_cap if market else None,
        "week_52_high": market.week_52_high if market else None,
        "week_52_low": market.week_52_low if market else None,
        "price_history": market.price_history if market else None,
        "price_dates": market.price_dates if market else None,
        # filled below
        "pe": None, "pb": None, "ps": None, "roe": None,
        "net_margin": None, "debt_equity": None,
        "yield": None, "ret_3y": None, "total_assets": None, "category": None,
    }

    # 52-week position (0–100%): where price sits in the yearly range
    if market and market.current_price and market.week_52_high and market.week_52_low:
        rng = market.week_52_high - market.week_52_low
        if rng > 0:
            entity["week_52_pos"] = (market.current_price - market.week_52_low) / rng * 100
        else:
            entity["week_52_pos"] = None
    else:
        entity["week_52_pos"] = None

    if is_etf:
        # ETF: fund-level data
        entity["pe"] = market.etf_pe
        entity["yield"] = market.etf_yield
        entity["ret_3y"] = market.etf_3y_return
        entity["total_assets"] = market.etf_total_assets
        entity["category"] = market.etf_category
    else:
        # Stock: SEC financials + computed ratios
        cik = get_cik_for_ticker(ticker)
        financial = None
        if cik:
            facts = get_company_facts(cik)
            financial = extract_annual_financials(facts, ticker) if facts else None
        metrics = calculate_metrics(financial, market)
        if metrics:
            entity["pe"] = metrics.pe_ratio
            entity["pb"] = metrics.pb_ratio
            entity["ps"] = metrics.ps_ratio
            entity["roe"] = metrics.roe
            entity["net_margin"] = metrics.net_profit_margin
            entity["debt_equity"] = metrics.debt_to_equity

    return entity


# Metric definitions: (label, key, lower_is_better, formatter)
def _fmt_ratio(v):  return f"{v:.2f}" if v is not None else None
def _fmt_pct(v):    return f"{v*100:.1f}%" if v is not None else None
def _fmt_pct_raw(v):return f"{v:.0f}%" if v is not None else None
def _fmt_money(v):
    if v is None: return None
    if v >= 1e12: return f"${v/1e12:.2f}T"
    if v >= 1e9:  return f"${v/1e9:.1f}B"
    if v >= 1e6:  return f"${v/1e6:.0f}M"
    return f"${v:.0f}"

_STOCK_METRICS = [
    ("P/E Ratio",    "pe",          True,  _fmt_ratio),
    ("P/B Ratio",    "pb",          True,  _fmt_ratio),
    ("P/S Ratio",    "ps",          True,  _fmt_ratio),
    ("ROE",          "roe",         False, _fmt_pct),
    ("Net Margin",   "net_margin",  False, _fmt_pct),
    ("Debt/Equity",  "debt_equity", True,  _fmt_ratio),
]

_ETF_METRICS = [
    ("P/E Ratio",       "pe",          True,  _fmt_ratio),
    ("Dividend Yield",  "yield",       False, _fmt_pct),
    ("3-Year Return",   "ret_3y",      False, _fmt_pct),
    ("Beta",            "beta",        None,  _fmt_ratio),
    ("52-Wk Position",  "week_52_pos", None,  _fmt_pct_raw),
    ("Size (Cap/AUM)",  "_size",       False, _fmt_money),
]


def build_comparison(ticker: str, peers: list[str]) -> dict:
    """
    Returns:
    {
      "mode": "stock" | "etf",
      "entities": [entity dicts],
      "rows": [ {label, values:[(display, is_winner)], } ],
    }
    """
    all_tickers = [ticker] + [p for p in peers if p != ticker]
    entities = []
    for t in all_tickers:
        try:
            entities.append(_collect_entity(t))
        except Exception as e:
            logger.warning("comparison: failed for %s: %s", t, e)

    if len(entities) < 2:
        return {"mode": "stock", "entities": entities, "rows": []}

    # Choose mode: if ANY entity is an ETF, use the ETF metric set
    has_etf = any(e["is_etf"] for e in entities)
    metric_set = _ETF_METRICS if has_etf else _STOCK_METRICS
    mode = "etf" if has_etf else "stock"

    rows = []
    for label, key, lower_better, fmt in metric_set:
        # special "_size" key: market_cap for stocks, total_assets for ETFs
        if key == "_size":
            raw = [e["total_assets"] if e["is_etf"] else e["market_cap"] for e in entities]
        else:
            raw = [e.get(key) for e in entities]

        present = [(i, v) for i, v in enumerate(raw) if v is not None]
        winner_idx = None
        if present and lower_better is not None:
            winner_idx = (min if lower_better else max)(present, key=lambda x: x[1])[0]

        values = []
        for i, v in enumerate(raw):
            disp = fmt(v) if v is not None else "N/A"
            values.append((disp, i == winner_idx))
        rows.append({"label": label, "values": values})

    return {"mode": mode, "entities": entities, "rows": rows}
