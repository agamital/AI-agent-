"""
News & Sentiment Tool — fetches recent headlines via NewsAPI
and returns a structured sentiment summary.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

_NEWSAPI_URL = "https://newsapi.org/v2/everything"

@dataclass
class NewsSentiment:
    ticker: str
    overall_sentiment: str
    positive_count: int
    neutral_count: int
    negative_count: int
    total_articles: int
    key_themes: list[str] = field(default_factory=list)
    recent_headlines: list[str] = field(default_factory=list)
    summary: str = ""

_POSITIVE_WORDS = {
    "beat", "record", "growth", "profit", "surge", "rally", "upgrade",
    "strong", "outperform", "exceed", "gain", "rose", "climbed", "jumped",
    "wins", "expands", "launches", "innovative", "bullish", "buyback"
}

_NEGATIVE_WORDS = {
    "miss", "loss", "decline", "fall", "drop", "downgrade", "lawsuit",
    "investigation", "recall", "layoff", "cut", "weak", "bearish", "risk",
    "concern", "warning", "slump", "tumble", "plunge", "debt", "fraud"
}

# מיפוי ticker → שם חברה לחיפוש מדויק יותר
_TICKER_TO_COMPANY = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Google",
    "AMZN": "Amazon",
    "META": "Meta",
    "NVDA": "NVIDIA",
    "TSLA": "Tesla",
    "NFLX": "Netflix",
    "INTU": "Intuit",
    "ADBE": "Adobe",
    "CRM": "Salesforce",
    "NOW": "ServiceNow",
}


def _score_headline(headline: str) -> str:
    words = headline.lower().split()
    pos = sum(1 for w in words if w.strip(".,!?") in _POSITIVE_WORDS)
    neg = sum(1 for w in words if w.strip(".,!?") in _NEGATIVE_WORDS)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def _is_relevant(headline: str, ticker: str, company_name: str) -> bool:
    """פילטר כותרות שלא קשורות לחברה."""
    headline_lower = headline.lower()
    ticker_lower = ticker.lower()
    company_lower = company_name.lower() if company_name else ""

    return (
        ticker_lower in headline_lower or
        (company_lower and company_lower in headline_lower)
    )


def _extract_themes(headlines: list[str]) -> list[str]:
    theme_keywords = {
        "Earnings & Revenue":      {"earnings", "revenue", "profit", "eps", "quarter", "beat", "miss"},
        "Legal & Regulatory":      {"lawsuit", "investigation", "sec", "ftc", "regulation", "fine", "court"},
        "Product & Innovation":    {"launch", "product", "ai", "innovation", "patent", "release", "new"},
        "Leadership & Strategy":   {"ceo", "cfo", "executive", "strategy", "acquisition", "merger", "deal"},
        "Macro & Market":          {"inflation", "rates", "fed", "macro", "recession", "market", "economy"},
        "Layoffs & Restructuring": {"layoff", "cut", "restructur", "workforce", "job"},
        "Pricing & Tariffs":       {"price", "pricing", "tariff", "tariffs", "cost", "raise", "increase"},
    }
    theme_counts = {theme: 0 for theme in theme_keywords}
    for headline in headlines:
        words = set(headline.lower().split())
        for theme, keywords in theme_keywords.items():
            if words & keywords:
                theme_counts[theme] += 1

    active = [(t, c) for t, c in theme_counts.items() if c > 0]
    active.sort(key=lambda x: x[1], reverse=True)
    return [t for t, _ in active[:5]]


def get_news_sentiment(ticker: str, company_name: str = "") -> NewsSentiment | None:
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        logger.error("NEWS_API_KEY not set.")
        return None

    # שם חברה — מה-mapping או מהפרמטר
    company = company_name or _TICKER_TO_COMPANY.get(ticker.upper(), "")

    # תאריך 30 יום אחורה
    from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    # query מדויק יותר
    if company:
        query = f'"{company}" stock OR "{ticker}" stock'
    else:
        query = f'"{ticker}" stock'

    try:
        response = requests.get(
            _NEWSAPI_URL,
            params={
                "q":        query,
                "language": "en",
                "sortBy":   "publishedAt",
                "pageSize": 30,
                "from":     from_date,
                "apiKey":   api_key,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.error("NewsAPI request failed for %s: %s", ticker, exc)
        return None

    articles = data.get("articles", [])

    # פלטר כותרות לא רלוונטיות
    headlines = [
        a["title"] for a in articles
        if a.get("title")
        and a["title"] != "[Removed]"
        and _is_relevant(a["title"], ticker, company)
    ]

    if not headlines:
        logger.warning("No relevant articles found for %s.", ticker)
        return NewsSentiment(
            ticker=ticker,
            overall_sentiment="neutral",
            positive_count=0,
            neutral_count=0,
            negative_count=0,
            total_articles=0,
            summary="No relevant recent news found.",
        )

    scores = [_score_headline(h) for h in headlines]
    pos = scores.count("positive")
    neg = scores.count("negative")
    neu = scores.count("neutral")

    if pos > neg + neu * 0.5:
        overall = "positive"
    elif neg > pos + neu * 0.5:
        overall = "negative"
    else:
        overall = "neutral"

    themes = _extract_themes(headlines)
    recent = headlines[:5]

    summary = (
        f"Out of {len(headlines)} relevant articles: "
        f"{pos} positive, {neg} negative, {neu} neutral. "
        f"Overall sentiment: {overall}."
    )

    return NewsSentiment(
        ticker=ticker,
        overall_sentiment=overall,
        positive_count=pos,
        neutral_count=neu,
        negative_count=neg,
        total_articles=len(headlines),
        key_themes=themes,
        recent_headlines=recent,
        summary=summary,
    )
