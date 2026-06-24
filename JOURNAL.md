# Project Journal

Decisions made, problems encountered, and how they were solved.
Update this as you go — don't leave it for the end.

---

## Format

### [Date] — Title
**Context:** What were you working on?
**Problem / Decision:** What happened or what choice did you face?
**Solution / Outcome:** How did you solve it or what did you decide?
**Lesson:** What would you do differently, or what should you remember?

### Function Card (write one in the `## Function Reference` section after each function)

Every function gets a card with these fixed fields plus a data-flow tree:

```
### 🔧 `function_name(args) -> ReturnType`
**Inputs:** each argument, its type, what it means
**Output:** the return type and what it represents (including the None / failure case)
**What it does:** 1–2 sentences on the mechanism
**Why it exists:** why it's a separate function / what need it serves
**Data flow:** an ASCII call tree (see below)
```

**Reading the data-flow tree:** `└─►` = "calls and sends down"; `returns:` on a line = "what comes back up"; indentation depth = call depth. The tree shows *where each piece of data is collected, what is passed between functions, and what each transformation produces.*

---

## Entries

### 2026-06-21 — Project Planning

**Context:** Initial project planning session before any code was written.

**Decisions made:**
- LLM provider: Groq (Llama/Mixtral) — fast, free tier, good for academic project
- Agent framework: LangGraph — supervisor + ReAct agent pattern
- Data sources: SEC EDGAR + yfinance (free only, no paid APIs)
- Architecture: Orchestrator supervises agents; agents call tools autonomously as needed. LLM never calculates or invents numbers.
- Conversational memory: using LangGraph MessagesState so follow-up questions retain context
- MCP: optional/bonus only — too risky for 2-week deadline
- Notebook submission: waived by teacher — submitting as Python package

**Lesson:** The assignment requires 6 specific system prompt components (Persona, Goal, Tools, Process, Constraints, Output Format). These must be explicit in prompts.yaml — not just implied by the code.

---

### 2026-06-21 — Schema Design (company.py + report.py)

**Context:** First coding session. Built all Pydantic data models before touching any tools or agents.

**Why schemas first?**
Every other part of the system — tools, agents, the report — needs to agree on what data looks like. Defining the shapes first means all future code references a shared contract instead of raw dicts that can have typos, wrong types, or missing fields. If schemas change later, Python will immediately tell you everywhere they're used.

**Why Pydantic `BaseModel` and not plain Python dataclasses or dicts?**
- Plain dicts: no type enforcement, typos silently pass through
- Python `dataclass`: no automatic validation, no JSON serialization
- Pydantic `BaseModel`: validates types on creation, raises a clear error immediately if something is wrong, and serializes to/from JSON for free. For a data pipeline where bad values silently cause wrong analysis, immediate validation is essential.

**Why `Optional[field] = None` for almost every field?**
APIs don't always return every field. SEC EDGAR may have revenue but not operating income for a given company. Making fields Optional means a single missing API response field doesn't crash the whole pipeline. The data validator (built later) will catch and report the gaps explicitly — this is better than crashing and better than silently passing `None` through undetected.

**Why are `FinancialData` and `MarketData` two separate models?**
They come from different sources (SEC EDGAR vs. yfinance), have different update frequencies (annual filings vs. live prices), and serve different agents (fundamental vs. technical). Mixing them would couple two independent data streams — if the SEC API fails, you'd lose the market data too. Separation makes each fetchable, testable, and cacheable independently.

**Why `price_history` and `price_dates` as two parallel lists instead of a dict?**
The technical indicators calculator uses `pandas` Series and `numpy` arrays, both of which work directly with plain lists. A dict would need to be unpacked into two lists on every use. Keeping them as parallel lists (same index = same day) removes a conversion step in every downstream function.

**Why `float` for financial values and not `int`?**
SEC EDGAR returns raw dollar amounts as floats (e.g. `391035000000.0`). EPS values like `6.43` also require decimals. Using `float` for all financial values avoids any integer-division bugs and handles both large whole numbers and decimals with one type.

**Why is `disclaimer` in `ResearchReport` a hardcoded string default and not `Optional`?**
The assignment and README both require the system to "clearly state limitations." Making `disclaimer` Optional would allow a report to be created without it — which defeats the rule. A hardcoded default means every `ResearchReport` instance always carries the disclaimer automatically, with no extra code needed.

**Why `__all__` in `schemas/__init__.py`?**
Two reasons: (1) it defines the package's public interface — other developers can see at a glance what the schemas package exports; (2) it controls wildcard imports (`from schemas import *`), preventing internal helpers from leaking into the caller's namespace. Without `__all__`, a wildcard import would pull in everything including things that weren't meant to be public.

**Why `schemas/__init__.py` at all?**
Without it, importing `CompanyInfo` anywhere in the project would require the full path: `from investment_agent.schemas.company import CompanyInfo`. With it, every file can write `from investment_agent.schemas import CompanyInfo` — shorter, cleaner, and if we ever move the class to a different file we only update one place (the `__init__.py`), not every importer.

---

### 2026-06-23 — All 5 Tools Built

**Context:** Second coding session. Built all tools in `tools/` from scratch, tested each against AAPL.

**Decision: Disk cache for `company_tickers.json` instead of fetching every session**
The SEC publishes a single static JSON file mapping every public company's ticker to its CIK. This file rarely changes and is the same for all tickers. Fetching it once and saving to `data/company_tickers.json` means every session after the first reads from disk instantly with no HTTP call. In-memory caching (module-level variable) would still re-fetch on every new Python process. The only risk is staleness — new IPOs won't appear until the file is deleted and re-fetched — which is acceptable for this project.

**Decision: `_GAAP_TAGS` priority list for extracting financials**
Different companies use different GAAP tag names for the same concept. For example, revenue is filed as `RevenueFromContractWithCustomerExcludingAssessedTax` by some companies and `Revenues` or `SalesRevenueNet` by others. Rather than hardcoding one tag and silently getting `None` for many companies, `_GAAP_TAGS` defines an ordered priority list per field. The extractor tries each tag in order and takes the first hit. This makes the tool work correctly across a wide range of companies without special-casing each one.

**Decision: SEC requires a `User-Agent` header**
SEC EDGAR blocks requests without a `User-Agent` header identifying the caller. The required format is `app-name email@domain.com`. Without this, all SEC requests return 403 Forbidden. Centralized in `_HEADERS` constant so both functions in `sec_tool.py` use it consistently.

**Decision: 6 months of price history instead of 3**
Initially fetched 3 months (`period="3mo"`, ~64 trading days). SMA 50 requires at least 50 data points — 64 days is only 14 days of margin. A stock with a few data gaps or a recent IPO would silently return `None` for SMA 50. Changed to `period="6mo"` (~124 trading days) to give every indicator a safe margin. Cost is negligible.

**Decision: `_safe_divide` helper in `metrics_tool.py`**
Every ratio calculation (P/E, ROE, etc.) divides two numbers that could each independently be `None` (data not found) or `0` (e.g. a company with zero equity). Without a helper, every ratio would need a 3-line guard. `_safe_divide` centralizes this: returns `None` if either input is `None` or denominator is `0`, otherwise divides and rounds. Keeps `calculate_metrics` readable.

**Decision: `_fetch_metrics_for_ticker` private helper in `peer_tool.py`**
The full pipeline for one ticker (CIK lookup → SEC facts → financial data → market data → metrics) is 5 sequential function calls. Extracting this into a private helper keeps `get_peer_comparison` as a clean loop with one line per ticker. It also means the error handling (skip and log on any failure) is isolated in one place rather than repeated inside the loop.

**Decision: Wilder's smoothing for RSI**
RSI uses Wilder's smoothing method: after the initial 14-period average, each subsequent average is `(prev_avg * 13 + today_value) / 14` rather than recalculating from scratch. This makes the RSI value more stable and less sensitive to a single outlier day. It is the standard implementation used by trading platforms.

---

### 2026-06-24 — Data Validator + Unit Tests (Days 1–2 complete)

**Context:** Third coding session. Verified and tested the data validator, then wrote the full unit test suite for all tools.

**Decision: validate_financial_data already existed — verified before moving on**
The function was found in `validation/data_validator.py` as an untracked file. Rather than rewriting, we ran a smoke test to confirm it correctly returns human-readable warnings for missing fields. It passed, so we moved straight to tests.

**Decision: mocked network tests over live calls**
Tests for SEC EDGAR and yfinance use `monkeypatch` to replace the real network calls with fake objects. Reason: live calls are slow (3+ seconds), can fail if APIs are down or rate-limit, and make the test suite unreliable during a demo. Mocked tests run in 0.08 seconds and never fail due to external factors.

**Decision: `_FakeTicker` class instead of a simple dict for yfinance mock**
`yf.Ticker()` returns an object with `.info` (a dict) and `.history()` (a method returning a pandas DataFrame). A plain dict cannot represent this. A small fake class `_FakeTicker` with both attributes stands in cleanly without any third-party mocking library.

**Decision: hand-computed RSI = 68.75 as the known-value anchor**
For the RSI test, I computed the expected value manually (period=2, prices [1,2,1,2,1,2]) using the Wilder's smoothing formula. The test asserts against that hand-computed value within a tolerance of 0.01. This approach means the test is an independent check — it would catch a bug where the code produces a plausible-looking but wrong number.

**Decision: `pytest.approx` for all floating-point assertions**
Floating-point arithmetic can produce tiny rounding differences (e.g. 3.9999999998 instead of 4.0). `pytest.approx` checks "close enough" rather than exact equality, preventing false test failures from meaningless decimal dust while still catching real math bugs.

---

## Function Reference

Per-function cards documenting inputs, outputs, and the data flow between functions.
See the **Function Card** spec under `## Format` for the field meanings and how to read the trees.

---

### `tools/sec_tool.py`

#### 🔧 `_load_ticker_map() -> dict[str, str]`
**Inputs:** none
**Output:** a `{TICKER: CIK}` dict — every public ticker (uppercased) mapped to its zero-padded 10-digit SEC CIK string.
**What it does:** Reads the cached `data/company_tickers.json` if it exists; otherwise fetches the file once from SEC, saves it to disk, then builds the mapping.
**Why it exists:** SEC identifies companies by CIK, not ticker. This is the lookup table that bridges the two. Caching to disk avoids re-fetching the same static file every session.

**Data flow:**
```
_load_ticker_map()
│   if data/company_tickers.json exists → json.load it
│   else → requests.get(_TICKERS_URL, _HEADERS) → save raw JSON to disk
│   transforms raw SEC list into:  {entry.ticker.upper(): entry.cik_str zero-padded to 10}
└─► returns: {TICKER: CIK} dict   (consumed by get_cik_for_ticker)
```

#### 🔧 `get_cik_for_ticker(ticker) -> str | None`
**Inputs:** `ticker: str` — a stock symbol (case-insensitive).
**Output:** the zero-padded 10-digit CIK string, or `None` if the ticker is unknown or the lookup fails.
**What it does:** Loads the ticker→CIK map and looks the ticker up; logs a warning on miss, logs an error on exception.
**Why it exists:** The public, error-handled entry point that other tools call to turn a ticker into a CIK. It is the first step of every per-ticker pipeline.

**Data flow:**
```
get_cik_for_ticker(ticker)          receives: ticker string
└─► _load_ticker_map()              returns: {TICKER: CIK} dict
        look up ticker.upper() in the dict
    returns: CIK string | None      (consumed by get_company_facts)
```

#### 🔧 `get_company_facts(cik) -> dict | None`
**Inputs:** `cik: str` — the 10-digit CIK from `get_cik_for_ticker`.
**Output:** the raw SEC EDGAR company-facts dict (all reported XBRL facts), or `None` if the HTTP request fails.
**What it does:** Builds the company-facts URL from the CIK and GETs it with the required `User-Agent` header.
**Why it exists:** Isolates the network call to SEC so the raw payload can be fetched, error-handled, and later parsed independently.

**Data flow:**
```
get_company_facts(cik)              receives: CIK string (from get_cik_for_ticker)
    requests.get(_COMPANY_FACTS_URL.format(cik), _HEADERS)
└─► returns: raw facts dict | None  (consumed by extract_annual_financials)
```

#### 🔧 `_get_latest_10k_value(gaap, tag, units) -> (float, str, int) | (None, None, None)`
**Inputs:** `gaap: dict` (the `facts.us-gaap` sub-dict), `tag: str` (a single GAAP concept name), `units: str` (e.g. `"USD"`).
**Output:** a tuple `(value, period_end_date, fiscal_year)` for the most recent annual 10-K filing of that tag, or `(None, None, None)` if the tag/units are absent or unparseable.
**What it does:** Filters the tag's entries to `form == "10-K"` and `fp == "FY"`, picks the one with the latest `end` date, and returns its value plus dating info.
**Why it exists:** One GAAP tag can appear in many filings (quarterly, restated, multiple years). This isolates the "give me the single latest annual number" logic so `extract_annual_financials` stays readable.

**Data flow:**
```
_get_latest_10k_value(gaap, tag, units)   receives: gaap sub-dict + one tag + units
    entries = gaap[tag]["units"][units]
    keep only 10-K / FY entries → take max by "end" date
└─► returns: (value, end_date, fiscal_year) | (None, None, None)
                                          (consumed by extract_annual_financials)
```

#### 🔧 `extract_annual_financials(facts, ticker) -> FinancialData | None`
**Inputs:** `facts: dict` (raw payload from `get_company_facts`), `ticker: str`.
**Output:** a `FinancialData` model with the latest annual revenue, net income, assets, equity, EPS, etc. — `None` for any field not found; whole function returns `None` if there are no `us-gaap` facts at all.
**What it does:** Iterates `_GAAP_TAGS` (a priority list of tag aliases per field), calls `_get_latest_10k_value` for each candidate tag, and takes the first hit per field. Records `period_end_date` / `fiscal_year` from the first field found.
**Why it exists:** Turns SEC's huge, inconsistent raw payload into the clean, typed `FinancialData` contract the rest of the system relies on. The priority list handles companies that file the same concept under different tag names.

**Data flow:**
```
extract_annual_financials(facts, ticker)  receives: raw facts dict + ticker
│   gaap = facts["facts"]["us-gaap"]
│   for each field in _GAAP_TAGS, for each candidate tag:
│      └─► _get_latest_10k_value(gaap, tag, units)
│             returns: (value, end, fy)  → first non-None wins, fills the field
└─► returns: FinancialData(ticker, fiscal_year, period_end_date, **fields) | None
                                          (consumed by calculate_metrics)
```

---

### `tools/market_tool.py`

#### 🔧 `get_market_data(ticker) -> MarketData | None`
**Inputs:** `ticker: str`.
**Output:** a `MarketData` model — current/previous price, 52-week high/low, market cap, average volume, beta, plus 6 months of closing prices (`price_history`) and matching `price_dates`. `None` on failure; individual fields may be `None` if yfinance omits them.
**What it does:** Uses `yfinance` to pull `.info` (point-in-time fields) and `.history(period="6mo")` (the daily close series), rounding prices to 2 decimals.
**Why it exists:** The single source of live market data, kept separate from SEC data so a yfinance outage doesn't take down fundamentals (and vice versa). The 6-month history feeds the technical indicators.

**Data flow:**
```
get_market_data(ticker)             receives: ticker string
    yf.Ticker(ticker).info          → current_price, 52wk range, market_cap, beta, ...
    yf.Ticker(ticker).history("6mo")→ price_history (closes) + price_dates
└─► returns: MarketData | None
       consumed by: calculate_metrics (market_cap) and
                    calculate_technical_indicators (price_history)
```

---

### `tools/metrics_tool.py`

#### 🔧 `_safe_divide(numerator, denominator) -> float | None`
**Inputs:** `numerator: float | None`, `denominator: float | None`.
**Output:** `numerator / denominator` rounded to 4 decimals, or `None` if either input is `None` or the denominator is `0`.
**What it does:** Guards every ratio against missing data and division-by-zero in one place.
**Why it exists:** Each ratio divides two values that can independently be missing or zero. Centralizing the guard keeps `calculate_metrics` to one clean line per ratio instead of a 3-line check each.

**Data flow:**
```
_safe_divide(numerator, denominator)   receives: two numbers (or None)
    if either None or denominator == 0 → None
    else → round(numerator / denominator, 4)
└─► returns: float | None              (used throughout calculate_metrics)
```

#### 🔧 `calculate_metrics(financial, market) -> MetricsResult | None`
**Inputs:** `financial: FinancialData` (from `extract_annual_financials`), `market: MarketData` (from `get_market_data`).
**Output:** a `MetricsResult` with valuation ratios (P/E, P/B, P/S) and profitability ratios (ROE, ROA, D/E, net & operating margin). `None` only if **both** inputs are missing; individual ratios are `None` when their inputs are absent.
**What it does:** Combines the market cap (market side) with the income/balance-sheet figures (financial side) through `_safe_divide` to produce each ratio.
**Why it exists:** This is where the two independent data streams (SEC + market) finally meet. It is the only place raw figures become the comparable ratios the agents reason about.

**Data flow:**
```
calculate_metrics(financial, market)   receives: FinancialData + MarketData
│   mc = market.market_cap
│   pe = _safe_divide(mc, financial.net_income)
│   pb = _safe_divide(mc, financial.total_equity)
│   roe = _safe_divide(financial.net_income, financial.total_equity)
│   ... (each ratio via _safe_divide)
└─► returns: MetricsResult | None
       consumed by: _fetch_metrics_for_ticker → get_peer_comparison
```

---

### `tools/technical_tool.py`

#### 🔧 `_sma(prices, period) -> float | None`
**Inputs:** `prices: list[float]` (closing prices, oldest→newest), `period: int`.
**Output:** the simple average of the last `period` prices (4 decimals), or `None` if fewer than `period` prices exist.
**What it does:** Averages the trailing `period` closes.
**Why it exists:** Reusable building block for the 20- and 50-day moving averages.

**Data flow:**
```
_sma(prices, period)    receives: price list + window size
    guard: len(prices) < period → None
    else → mean of prices[-period:]
└─► returns: float | None   (called by calculate_technical_indicators for sma_20, sma_50)
```

#### 🔧 `_ema(prices, period) -> float | None`
**Inputs:** `prices: list[float]`, `period: int`.
**Output:** the exponential moving average (4 decimals), or `None` if fewer than `period` prices.
**What it does:** Seeds the EMA with the simple average of the first `period` prices, then applies the smoothing factor `k = 2/(period+1)` across the rest.
**Why it exists:** Reusable building block for EMA-20 and for the MACD line/signal (which are themselves EMAs).

**Data flow:**
```
_ema(prices, period)    receives: price list + window size
    seed = mean(prices[:period]); iterate k-smoothing over the remainder
└─► returns: float | None   (called for ema_20 and repeatedly inside MACD)
```

#### 🔧 `_rsi(prices, period=14) -> float | None`
**Inputs:** `prices: list[float]`, `period: int` (default 14).
**Output:** the Relative Strength Index 0–100 (4 decimals), `100.0` if there are no losses, or `None` if fewer than `period + 1` prices.
**What it does:** Computes day-over-day gains/losses, seeds average gain/loss over the first `period`, then applies Wilder's smoothing across the rest and converts to the RSI scale.
**Why it exists:** Encapsulates the momentum-oscillator math so the orchestrating function just asks for `rsi_14`.

**Data flow:**
```
_rsi(prices, period=14)   receives: price list
    changes → gains/losses → seed averages → Wilder smoothing → 100 - 100/(1+rs)
└─► returns: float | None   (called by calculate_technical_indicators for rsi_14)
```

#### 🔧 `calculate_technical_indicators(market) -> TechnicalIndicators | None`
**Inputs:** `market: MarketData` — specifically uses its `price_history` list.
**Output:** a `TechnicalIndicators` model (SMA-20, SMA-50, EMA-20, RSI-14, MACD line/signal/histogram). `None` if `market` or its price history is missing.
**What it does:** Pulls `price_history` out of `MarketData`, then feeds it to the `_sma` / `_ema` / `_rsi` helpers; builds MACD from EMA-12 minus EMA-26 with a 9-period signal line.
**Why it exists:** The single orchestrator the technical agent calls — it converts one price series into the full indicator set, so the agent never touches raw prices.

**Data flow:**
```
calculate_technical_indicators(market)   receives: MarketData
│   prices = market.price_history
│   ├─► _sma(prices, 20) / _sma(prices, 50)      → sma_20 / sma_50
│   ├─► _ema(prices, 20)                         → ema_20
│   ├─► _ema(prices, 12) & _ema(prices, 26)      → macd_line = ema12 - ema26
│   │      _ema(macd_prices, 9)                  → macd_signal → macd_histogram
│   └─► _rsi(prices)                             → rsi_14
└─► returns: TechnicalIndicators | None          (consumed by the technical agent)
```

---

### `tools/peer_tool.py`

#### 🔧 `_fetch_metrics_for_ticker(ticker) -> MetricsResult | None`
**Inputs:** `ticker: str`.
**Output:** the `MetricsResult` for one ticker, or `None` if the CIK can't be resolved or no data (financial **and** market) is available.
**What it does:** Runs the full single-ticker pipeline — CIK → SEC facts → financials, plus market data — then combines them via `calculate_metrics`.
**Why it exists:** Isolates the 4-call pipeline and its skip-on-failure handling so `get_peer_comparison` stays a clean one-line-per-ticker loop.

**Data flow:**
```
_fetch_metrics_for_ticker(ticker)        receives: one ticker string
├─► get_cik_for_ticker(ticker)           → CIK | None  (None ⇒ return None)
├─► get_company_facts(cik)               → raw facts dict | None
├─► extract_annual_financials(facts, t)  → FinancialData | None
├─► get_market_data(ticker)              → MarketData | None
│      (both None ⇒ log + return None)
└─► calculate_metrics(financial, market) → MetricsResult | None
    returns: MetricsResult | None        (consumed by get_peer_comparison)
```

#### 🔧 `get_peer_comparison(ticker, peers) -> list[MetricsResult]`
**Inputs:** `ticker: str` (main company), `peers: list[str]` (companies to compare against).
**Output:** a `list[MetricsResult]` — one entry per ticker that fetched successfully. Failed tickers are skipped and logged; the list is never `None` and may be empty.
**What it does:** Builds `[ticker] + peers`, runs each through `_fetch_metrics_for_ticker`, and collects the non-`None` results.
**Why it exists:** The single entry point the peer agent calls for side-by-side comparison — a core deliverable.

**Data flow:**
```
get_peer_comparison(ticker, peers)       receives: main ticker + peer list
│   all_tickers = [ticker] + peers
│   for each t:
│   └─► _fetch_metrics_for_ticker(t)     → MetricsResult | None
│          (full CIK→facts→financials + market→metrics pipeline, see card above)
│       append result if not None
└─► returns: list[MetricsResult]         (consumed by the peer agent)
```

---

### `validation/data_validator.py`

#### 🔧 `validate_financial_data(data) -> list[str]`
**Inputs:** `data: BaseModel | None` — any Pydantic model (expected: `FinancialData`, `MarketData`, or `MetricsResult`).
**Output:** a list of human-readable warning strings, one per `None` field. Empty list means all tracked fields are present. Single-item list if `data` is `None` itself.
**What it does:** Looks up the model's class name in `_FIELD_LABELS` to get the fields worth checking, then walks each field and collects a warning string for every one that is `None`.
**Why it exists:** Agents call this before generating analysis so the LLM is never silently working with gaps. It converts invisible `None` values into explicit, readable disclosures.

**Data flow:**
```
validate_financial_data(data)            receives: any Pydantic model (or None)
    if data is None → return ["No data object provided..."]
    model_name = type(data).__name__
    labels = _FIELD_LABELS.get(model_name)
    if labels is None → log warning, return []
    for field, label in labels.items():
        if getattr(data, field) is None → append "[TICKER] Missing {label}."
└─► returns: list[str]                   (consumed by agents before LLM analysis)
```

---
