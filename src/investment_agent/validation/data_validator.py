import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# Human-readable labels for the fields we care about, keyed by model class name.
# Identity / metadata fields (ticker, currency, price_dates) are intentionally
# excluded — their absence is not a "data gap" an analyst needs warned about.
# The financial and market *numbers* are what matter for analysis.
_FIELD_LABELS: dict[str, dict[str, str]] = {
    "FinancialData": {
        "fiscal_year": "Fiscal year",
        "period_end_date": "Reporting period end date",
        "revenue": "Revenue",
        "net_income": "Net income",
        "operating_income": "Operating income",
        "total_assets": "Total assets",
        "total_liabilities": "Total liabilities",
        "total_equity": "Total equity",
        "cash_and_equivalents": "Cash and equivalents",
        "eps_basic": "Basic EPS",
        "eps_diluted": "Diluted EPS",
        "shares_outstanding": "Shares outstanding",
    },
    "MarketData": {
        "current_price": "Current price",
        "previous_close": "Previous close",
        "week_52_high": "52-week high",
        "week_52_low": "52-week low",
        "market_cap": "Market capitalization",
        "average_volume": "Average volume",
        "beta": "Beta",
        "price_history": "Price history",
    },
    "MetricsResult": {
        "pe_ratio": "P/E ratio",
        "pb_ratio": "P/B ratio",
        "ps_ratio": "P/S ratio",
        "roe": "Return on equity (ROE)",
        "roa": "Return on assets (ROA)",
        "debt_to_equity": "Debt-to-equity",
        "net_profit_margin": "Net profit margin",
        "operating_margin": "Operating margin",
    },
}


def validate_financial_data(data: BaseModel | None) -> list[str]:
    """Scan a data model for missing (None) fields and report them in plain English.

    Accepts a FinancialData, MarketData, or MetricsResult object. Returns one
    human-readable warning string per field that is None, so an agent can disclose
    the gap instead of letting the LLM invent a value. The list is empty when every
    tracked field is present.
    """
    if data is None:
        return ["No data object was provided to validate (received None)."]

    model_name = type(data).__name__
    labels = _FIELD_LABELS.get(model_name)
    if labels is None:
        logger.warning("validate_financial_data: no field labels defined for '%s'.", model_name)
        return []

    ticker = getattr(data, "ticker", "unknown")
    warnings: list[str] = []
    for field, label in labels.items():
        if getattr(data, field, None) is None:
            warnings.append(f"[{ticker}] Missing {label}.")

    return warnings
