import json
import logging
from pathlib import Path

import requests

from investment_agent.schemas.company import FinancialData

logger = logging.getLogger(__name__)

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_CACHE_PATH = Path(__file__).parents[4] / "data" / "company_tickers.json"
_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
_HEADERS = {"User-Agent": "investment-research-agent zivdi2273@gmail.com"}


def _load_ticker_map() -> dict[str, str]:
    """Return {ticker: zero-padded CIK} mapping, using disk cache when available."""
    if _CACHE_PATH.exists():
        with _CACHE_PATH.open() as f:
            raw = json.load(f)
    else:
        response = requests.get(_TICKERS_URL, headers=_HEADERS)
        response.raise_for_status()
        raw = response.json()
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _CACHE_PATH.open("w") as f:
            json.dump(raw, f)

    return {
        entry["ticker"].upper(): str(entry["cik_str"]).zfill(10)
        for entry in raw.values()
    }


_GAAP_TAGS: dict[str, tuple[list[str], str]] = {
    "revenue":              (["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"], "USD"),
    "net_income":           (["NetIncomeLoss", "ProfitLoss"], "USD"),
    "operating_income":     (["OperatingIncomeLoss"], "USD"),
    "total_assets":         (["Assets"], "USD"),
    "total_liabilities":    (["Liabilities"], "USD"),
    "total_equity":         (["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"], "USD"),
    "cash_and_equivalents": (["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsAndShortTermInvestments"], "USD"),
    "eps_basic":            (["EarningsPerShareBasic"], "USD/shares"),
    "eps_diluted":          (["EarningsPerShareDiluted"], "USD/shares"),
    "shares_outstanding":   (["CommonStockSharesOutstanding", "WeightedAverageNumberOfSharesOutstandingBasic"], "shares"),
}


def _get_latest_10k_value(gaap: dict, tag: str, units: str) -> tuple[float, str, int] | tuple[None, None, None]:
    """Return (value, period_end_date, fiscal_year) for the most recent 10-K filing of a GAAP tag."""
    try:
        entries = gaap[tag]["units"][units]
        annual = [e for e in entries if e.get("form") == "10-K" and e.get("fp") == "FY"]
        if not annual:
            return None, None, None
        latest = max(annual, key=lambda e: e["end"])
        return float(latest["val"]), latest["end"], int(latest.get("fy", latest["end"][:4]))
    except (KeyError, ValueError, TypeError):
        return None, None, None


def extract_annual_financials(facts: dict, ticker: str) -> FinancialData | None:
    """Extract key annual financial metrics from a raw SEC EDGAR company facts dict.

    Returns a FinancialData model with None for any field not found in the filing.
    """
    try:
        gaap = facts["facts"]["us-gaap"]
    except KeyError:
        logger.error("No us-gaap facts found for %s.", ticker)
        return None

    fields: dict = {}
    period_end: str | None = None
    fiscal_year: int | None = None

    for field_name, (tags, units) in _GAAP_TAGS.items():
        for tag in tags:
            val, end, fy = _get_latest_10k_value(gaap, tag, units)
            if val is not None:
                fields[field_name] = val
                if period_end is None:
                    period_end = end
                    fiscal_year = fy
                break

    return FinancialData(ticker=ticker, fiscal_year=fiscal_year, period_end_date=period_end, **fields)


def get_company_facts(cik: str) -> dict | None:
    """Fetch all reported financial facts for a company from SEC EDGAR.

    Returns the raw facts dict, or None if the request fails.
    """
    try:
        url = _COMPANY_FACTS_URL.format(cik=cik)
        response = requests.get(url, headers=_HEADERS)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.error("Failed to fetch company facts for CIK %s: %s", cik, exc)
        return None


def get_cik_for_ticker(ticker: str) -> str | None:
    """Convert a ticker symbol to a zero-padded 10-digit SEC CIK string.

    Returns None if the ticker is not found or the request fails.
    """
    try:
        ticker_map = _load_ticker_map()
        cik = ticker_map.get(ticker.upper())
        if cik is None:
            logger.warning("Ticker %s not found in SEC company tickers.", ticker)
        return cik
    except Exception as exc:
        logger.error("Failed to resolve CIK for ticker %s: %s", ticker, exc)
        return None
