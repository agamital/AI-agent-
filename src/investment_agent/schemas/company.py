from pydantic import BaseModel
from typing import Optional


class CompanyInfo(BaseModel):
    ticker: str
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    exchange: Optional[str] = None
    country: Optional[str] = None


class FinancialData(BaseModel):
    ticker: str
    fiscal_year: Optional[int] = None
    period_end_date: Optional[str] = None
    currency: str = "USD"
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    operating_income: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    eps_basic: Optional[float] = None
    eps_diluted: Optional[float] = None
    shares_outstanding: Optional[float] = None


class MarketData(BaseModel):
    ticker: str
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    market_cap: Optional[float] = None
    average_volume: Optional[float] = None
    beta: Optional[float] = None
    price_history: Optional[list[float]] = None
    price_dates: Optional[list[str]] = None


class MetricsResult(BaseModel):
    ticker: str
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    debt_to_equity: Optional[float] = None
    net_profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None


class TechnicalIndicators(BaseModel):
    ticker: str
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_20: Optional[float] = None
    rsi_14: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
