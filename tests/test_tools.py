"""Unit tests for the pure-Python tools and the data validator.

Network tools (SEC EDGAR, yfinance) are mocked so the suite runs offline and
fast. The deterministic calculators and the validator need no mocking.
"""

import pytest

from investment_agent.schemas import FinancialData, MarketData
from investment_agent.tools.metrics_tool import _safe_divide, calculate_metrics
from investment_agent.tools.technical_tool import (
    _ema,
    _rsi,
    _sma,
    calculate_technical_indicators,
)
from investment_agent.validation.data_validator import validate_financial_data


# --------------------------------------------------------------------------- #
# Data validator
# --------------------------------------------------------------------------- #


def test_validator_reports_missing_fields():
    """A model with only one field set should warn about every other field."""
    data = FinancialData(ticker="XYZ", revenue=100.0)
    warnings = validate_financial_data(data)

    # revenue is present, so it must NOT be reported...
    assert not any("Revenue" in w for w in warnings)
    # ...but the other tracked fields are missing and must be reported.
    assert any("Net income" in w for w in warnings)
    assert any("Total equity" in w for w in warnings)
    # every warning is scoped to the ticker for traceability
    assert all(w.startswith("[XYZ]") for w in warnings)


def test_validator_passes_when_complete():
    """A fully-populated model produces no warnings."""
    data = FinancialData(
        ticker="AAPL",
        fiscal_year=2024,
        period_end_date="2024-09-28",
        revenue=391_035_000_000.0,
        net_income=93_736_000_000.0,
        operating_income=123_216_000_000.0,
        total_assets=364_980_000_000.0,
        total_liabilities=308_030_000_000.0,
        total_equity=56_950_000_000.0,
        cash_and_equivalents=29_943_000_000.0,
        eps_basic=6.11,
        eps_diluted=6.08,
        shares_outstanding=15_115_823_000.0,
    )
    assert validate_financial_data(data) == []


def test_validator_handles_none():
    """Passing None returns a single explanatory warning, not a crash."""
    warnings = validate_financial_data(None)
    assert len(warnings) == 1
    assert "None" in warnings[0]


def test_validator_unknown_model(caplog):
    """An unrecognized model type returns [] and logs a warning."""
    from pydantic import BaseModel

    class Mystery(BaseModel):
        ticker: str = "ZZZ"

    assert validate_financial_data(Mystery()) == []
    assert "no field labels defined" in caplog.text


# --------------------------------------------------------------------------- #
# metrics_tool: _safe_divide
# --------------------------------------------------------------------------- #


def test_safe_divide_normal():
    assert _safe_divide(10, 4) == 2.5
    assert _safe_divide(1, 3) == 0.3333  # rounded to 4 dp


def test_safe_divide_guards():
    assert _safe_divide(10, 0) is None  # zero denominator
    assert _safe_divide(None, 4) is None  # missing numerator
    assert _safe_divide(10, None) is None  # missing denominator


# --------------------------------------------------------------------------- #
# metrics_tool: calculate_metrics
# --------------------------------------------------------------------------- #


def test_calculate_metrics_known_values():
    """Ratios are computed correctly from known inputs."""
    financial = FinancialData(
        ticker="TST",
        revenue=500.0,
        net_income=100.0,
        operating_income=150.0,
        total_assets=400.0,
        total_liabilities=300.0,
        total_equity=200.0,
    )
    market = MarketData(ticker="TST", market_cap=1000.0)

    m = calculate_metrics(financial, market)
    assert m.pe_ratio == 10.0  # 1000 / 100
    assert m.pb_ratio == 5.0  # 1000 / 200
    assert m.ps_ratio == 2.0  # 1000 / 500
    assert m.roe == 0.5  # 100 / 200
    assert m.roa == 0.25  # 100 / 400
    assert m.debt_to_equity == 1.5  # 300 / 200
    assert m.net_profit_margin == 0.2  # 100 / 500
    assert m.operating_margin == 0.3  # 150 / 500


def test_calculate_metrics_missing_input_yields_none_ratio():
    """A missing numerator/denominator makes only that ratio None, not a crash."""
    financial = FinancialData(ticker="TST", net_income=None, total_equity=200.0)
    market = MarketData(ticker="TST", market_cap=1000.0)

    m = calculate_metrics(financial, market)
    assert m.pe_ratio is None  # net_income missing
    assert m.pb_ratio == 5.0  # still computable


def test_calculate_metrics_both_none_returns_none():
    assert calculate_metrics(None, None) is None


# --------------------------------------------------------------------------- #
# technical_tool: _sma / _ema / _rsi
# --------------------------------------------------------------------------- #


def test_sma():
    assert _sma([1, 2, 3, 4, 5], 5) == 3.0
    assert _sma([2, 4, 6, 8], 2) == 7.0  # mean of last two
    assert _sma([1, 2, 3], 5) is None  # too few prices


def test_ema():
    # period=3 over [1,2,3,4,5]: seed=2.0, then 3.0, then 4.0
    assert _ema([1, 2, 3, 4, 5], 3) == pytest.approx(4.0)
    assert _ema([1, 2], 3) is None  # too few prices


def test_rsi_known_value():
    # period=2 over [1,2,1,2,1,2]: Wilder's smoothing -> rs=2.2 -> RSI 68.75
    assert _rsi([1, 2, 1, 2, 1, 2], period=2) == pytest.approx(68.75, abs=0.01)


def test_rsi_no_losses_branch():
    # strictly increasing -> no losses -> RSI caps at 100.0
    assert _rsi([1, 2, 3, 4, 5], period=2) == 100.0


def test_rsi_too_few_prices():
    assert _rsi([1, 2], period=14) is None


# --------------------------------------------------------------------------- #
# technical_tool: calculate_technical_indicators
# --------------------------------------------------------------------------- #


def test_technical_indicators_missing_history_returns_none():
    assert calculate_technical_indicators(None) is None
    assert calculate_technical_indicators(MarketData(ticker="TST", price_history=None)) is None
    assert calculate_technical_indicators(MarketData(ticker="TST", price_history=[])) is None


def test_technical_indicators_computes_available():
    """With a short series, SMA-20/50 are None but the model still builds."""
    market = MarketData(ticker="TST", price_history=[float(i) for i in range(1, 11)])
    ti = calculate_technical_indicators(market)
    assert ti is not None
    assert ti.ticker == "TST"
    assert ti.sma_20 is None  # only 10 prices, need 20
    assert ti.sma_50 is None


# --------------------------------------------------------------------------- #
# sec_tool: get_cik_for_ticker
# --------------------------------------------------------------------------- #


def test_get_cik_for_ticker_hit(monkeypatch):
    """A known ticker returns the correct zero-padded CIK."""
    from investment_agent.tools import sec_tool

    monkeypatch.setattr(sec_tool, "_load_ticker_map", lambda: {"AAPL": "0000320193"})

    from investment_agent.tools.sec_tool import get_cik_for_ticker

    assert get_cik_for_ticker("AAPL") == "0000320193"
    assert get_cik_for_ticker("aapl") == "0000320193"  # case-insensitive


def test_get_cik_for_ticker_miss(monkeypatch):
    """An unknown ticker returns None instead of crashing."""
    from investment_agent.tools import sec_tool

    monkeypatch.setattr(sec_tool, "_load_ticker_map", lambda: {"AAPL": "0000320193"})

    from investment_agent.tools.sec_tool import get_cik_for_ticker

    assert get_cik_for_ticker("FAKE") is None


# --------------------------------------------------------------------------- #
# sec_tool: extract_annual_financials
# --------------------------------------------------------------------------- #


def _make_fake_facts(revenue: float, net_income: float) -> dict:
    """Build the minimum SEC facts structure that extract_annual_financials reads."""
    def entry(val):
        return {"units": {"USD": [{"val": val, "form": "10-K", "fp": "FY", "end": "2024-09-28", "fy": 2024}]}}

    return {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": entry(revenue),
                "NetIncomeLoss": entry(net_income),
            }
        }
    }


def test_extract_annual_financials_known_values():
    """Revenue and net income are extracted correctly from a minimal fake facts dict."""
    from investment_agent.tools.sec_tool import extract_annual_financials

    facts = _make_fake_facts(revenue=391_035_000_000.0, net_income=93_736_000_000.0)
    result = extract_annual_financials(facts, "AAPL")

    assert result is not None
    assert result.ticker == "AAPL"
    assert result.revenue == 391_035_000_000.0
    assert result.net_income == 93_736_000_000.0
    assert result.fiscal_year == 2024
    assert result.period_end_date == "2024-09-28"


def test_extract_annual_financials_missing_gaap_returns_none():
    """A facts dict with no us-gaap key returns None instead of crashing."""
    from investment_agent.tools.sec_tool import extract_annual_financials

    bad_facts = {"facts": {}}
    assert extract_annual_financials(bad_facts, "XYZ") is None


# --------------------------------------------------------------------------- #
# market_tool: get_market_data
# --------------------------------------------------------------------------- #


import pandas as pd


class _FakeTicker:
    """Stands in for yfinance.Ticker during tests — no network call made."""

    def __init__(self):
        self.info = {
            "currentPrice": 189.50,
            "previousClose": 188.00,
            "fiftyTwoWeekHigh": 220.00,
            "fiftyTwoWeekLow": 155.00,
            "marketCap": 2_950_000_000_000,
            "averageVolume": 55_000_000,
            "beta": 1.24,
        }

    def history(self, period=None):  # noqa: ARG002
        closes = [150.0, 155.0, 160.0, 158.0, 162.0]
        dates = pd.to_datetime(
            ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]
        )
        return pd.DataFrame({"Close": closes}, index=dates)


def test_get_market_data_fields(monkeypatch):
    """Fields from yfinance .info and .history() land correctly in MarketData."""
    import investment_agent.tools.market_tool as market_tool

    def _fake_ticker(_ticker):
        return _FakeTicker()

    monkeypatch.setattr(market_tool.yf, "Ticker", _fake_ticker)

    from investment_agent.tools.market_tool import get_market_data

    result = get_market_data("AAPL")

    assert result is not None
    assert result.ticker == "AAPL"
    assert result.current_price == 189.50
    assert result.week_52_high == 220.00
    assert result.market_cap == 2_950_000_000_000
    assert result.beta == 1.24
    assert result.price_history == [150.0, 155.0, 160.0, 158.0, 162.0]
    assert result.price_dates == [
        "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"
    ]


def test_get_market_data_failure_returns_none(monkeypatch):
    """If yfinance raises an exception, the function returns None instead of crashing."""
    import investment_agent.tools.market_tool as market_tool

    def _explode(ticker):
        raise ConnectionError("network is down")

    monkeypatch.setattr(market_tool.yf, "Ticker", _explode)

    from investment_agent.tools.market_tool import get_market_data

    assert get_market_data("AAPL") is None
