"""
yfinance-based scraper: price history, company metadata, and news events.

News credibility
----------------
Google News / yfinance aggregates sources of wildly varying reliability.
We assign a credibility_score (0–1) per domain and filter out low-quality
sources.  Only items from TRUSTED_DOMAINS (0.7+) are stored.

SEC EDGAR 8-K filings (edgar.py) always score 1.0 and bypass this file.

Source tiers
  1.0  sec.gov, businesswire.com, prnewswire.com, globenewswire.com (official filings / press releases)
  0.9  reuters.com, bloomberg.com, wsj.com, ft.com, apnews.com
  0.8  cnbc.com, fortune.com, barrons.com, marketwatch.com, axios.com, nytimes.com
  0.7  techcrunch.com, businessinsider.com, theverge.com, venturebeat.com
  skip anything else
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse
from typing import Dict, List, Optional, Tuple

try:
    import yfinance as yf
    _HAS_YFINANCE = True
except ImportError:
    yf = None
    _HAS_YFINANCE = False

from .companies import COMPANY_REGISTRY
from .database import Database

DEFAULT_HISTORY_YEARS = 5
PRE_WINDOWS = [1, 3, 5]
POST_WINDOWS = [1, 3, 5, 10, 30]

# Domain → credibility score.  Anything not listed is skipped.
_SOURCE_SCORES: Dict[str, float] = {
    # Official wires / filings
    "sec.gov": 1.0,
    "businesswire.com": 1.0,
    "prnewswire.com": 1.0,
    "globenewswire.com": 1.0,
    "accesswire.com": 0.95,
    # Tier-1 financial press
    "reuters.com": 0.9,
    "bloomberg.com": 0.9,
    "wsj.com": 0.9,
    "ft.com": 0.9,
    "apnews.com": 0.9,
    "bbc.com": 0.85,
    # Tier-2 financial press
    "cnbc.com": 0.8,
    "fortune.com": 0.8,
    "barrons.com": 0.8,
    "marketwatch.com": 0.8,
    "axios.com": 0.8,
    "nytimes.com": 0.8,
    "economist.com": 0.8,
    "theguardian.com": 0.75,
    "washingtonpost.com": 0.75,
    # Tech press (good for startups / tech companies)
    "techcrunch.com": 0.7,
    "businessinsider.com": 0.7,
    "theverge.com": 0.7,
    "venturebeat.com": 0.7,
    "wired.com": 0.7,
    "theinformation.com": 0.7,
    "protocol.com": 0.7,
}

_MIN_CREDIBILITY = 0.7  # discard anything below this


def _score_url(url: str) -> Tuple[float, str]:
    """Return (credibility_score, domain) for a URL. (0, '') means skip."""
    if not url:
        return 0.0, ""
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return 0.0, ""
    # Match on suffix (e.g. 'news.wsj.com' → 'wsj.com')
    for domain, score in _SOURCE_SCORES.items():
        if host == domain or host.endswith("." + domain):
            return score, domain
    return 0.0, host  # unlisted — will be filtered


# Keyword → event_type classification (first match wins)
_EVENT_PATTERNS: List[Tuple[str, str]] = [
    (r"acqui|merger|takeover|buyout|deal|combine|merge", "acquisition"),
    (r"\bearning|revenue|profit|loss|quarter|fiscal|Q[1-4]\b|EPS|beat|miss", "earnings"),
    (r"CEO|CFO|CTO|COO|president|appoint|resign|retire|step.?down|hire|fire|leadership|execut", "leadership"),
    (r"launch|release|unveil|introduc|new product|new service|debut|announce product", "product"),
    (r"layoff|restructur|cut.*job|downsize|workforce|redundan|reorg", "restructuring"),
    (r"regulat|fine|sued|lawsuit|antitrust|SEC |FTC |FDA |penalty|investig|probe", "regulatory"),
    (r"dividend|split|distribution|payout", "dividend"),
    (r"buyback|repurchase|share.*program", "buyback"),
    (r"partner|collaborat|joint venture|alliance|license", "partnership"),
    (r"guidance|outlook|forecast|raise.*target|lower.*target", "guidance"),
]


def _classify_event(title: str) -> str:
    for pattern, etype in _EVENT_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return etype
    return "other"


def _unix_to_date(ts: int) -> str:
    return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")


class MarketScraper:
    def __init__(self, db: Database, throttle_seconds: float = 1.0) -> None:
        self.db = db
        self.throttle = throttle_seconds

    def _require_yfinance(self) -> bool:
        if _HAS_YFINANCE:
            return True
        print("  [warn] 'yfinance' not installed — skipping market-data scrape")
        return False

    # ── Public entry points ────────────────────────────────────────────────

    def fetch_company(self, ticker: str) -> bool:
        """Pull company metadata from yfinance and upsert into DB."""
        if not self._require_yfinance():
            return False
        try:
            info = yf.Ticker(ticker).info
            if not info or info.get("quoteType") is None:
                print(f"  [warn] {ticker}: no metadata returned")
                return False
            self.db.upsert_company(
                ticker=ticker,
                name=info.get("longName") or info.get("shortName") or ticker,
                sector=info.get("sector"),
                industry=info.get("industry"),
                exchange=info.get("exchange"),
                country=info.get("country"),
                market_cap=info.get("marketCap"),
                description=(info.get("longBusinessSummary") or "")[:500],
            )
            return True
        except Exception as exc:
            print(f"  [error] {ticker} metadata: {exc}")
            return False

    def fetch_prices(
        self,
        ticker: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> int:
        """Download OHLCV history and insert new rows. Returns rows inserted."""
        if not self._require_yfinance():
            return 0
        if start is None:
            latest = self.db.latest_price_date(ticker)
            if latest:
                # resume from the day after the last stored date
                dt = datetime.strptime(latest, "%Y-%m-%d") + timedelta(days=1)
                start = dt.strftime("%Y-%m-%d")
            else:
                dt = datetime.utcnow() - timedelta(days=365 * DEFAULT_HISTORY_YEARS)
                start = dt.strftime("%Y-%m-%d")

        if end is None:
            end = datetime.utcnow().strftime("%Y-%m-%d")

        if start >= end:
            return 0

        try:
            df = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)
        except Exception as exc:
            print(f"  [error] {ticker} prices: {exc}")
            return 0

        if df is None or df.empty:
            return 0

        rows = []
        for date_idx, row in df.iterrows():
            date_str = date_idx.strftime("%Y-%m-%d") if hasattr(date_idx, "strftime") else str(date_idx)[:10]
            rows.append({
                "ticker": ticker,
                "date": date_str,
                "open": _safe(row.get("Open")),
                "high": _safe(row.get("High")),
                "low": _safe(row.get("Low")),
                "close": _safe(row.get("Close")),
                "adj_close": _safe(row.get("Adj Close")),
                "volume": _safe_int(row.get("Volume")),
            })
        return self.db.insert_prices(rows)

    def fetch_events(self, ticker: str, max_items: Optional[int] = None) -> int:
        """
        Pull recent news from yfinance, filter by source credibility, classify,
        and store.  Returns number of events stored.
        """
        if not self._require_yfinance():
            return 0
        try:
            t = yf.Ticker(ticker)
            news_items = t.news or []
        except Exception as exc:
            print(f"  [error] {ticker} news: {exc}")
            return 0

        if max_items is not None:
            news_items = news_items[:max_items]

        stored = 0
        for item in news_items:
            title = item.get("title") or ""
            if not title:
                continue
            ts = item.get("providerPublishTime") or item.get("publishedAt")
            if not ts:
                continue

            url = item.get("link") or item.get("url") or ""
            credibility, domain = _score_url(url)

            # yfinance sometimes has a publisher key — use it as fallback domain
            if not domain:
                pub = (item.get("publisher") or "").lower()
                for d, sc in _SOURCE_SCORES.items():
                    if d.split(".")[0] in pub:
                        credibility, domain = sc, d
                        break

            if credibility < _MIN_CREDIBILITY:
                continue  # discard low-quality / unknown sources

            date = _unix_to_date(int(ts))
            event_type = _classify_event(title)
            self.db.insert_event(
                ticker=ticker,
                date=date,
                event_type=event_type,
                title=title,
                source_url=url,
                credibility_score=credibility,
                source_domain=domain,
            )
            stored += 1
        return stored

    def fetch_earnings_events(self, ticker: str) -> int:
        """Store earnings dates as explicit earnings events (more reliable than news)."""
        if not self._require_yfinance():
            return 0
        try:
            t = yf.Ticker(ticker)
            cal = t.earnings_dates
        except Exception:
            return 0

        if cal is None or cal.empty:
            return 0

        stored = 0
        for date_idx, row in cal.iterrows():
            date_str = date_idx.strftime("%Y-%m-%d") if hasattr(date_idx, "strftime") else str(date_idx)[:10]
            eps_est = row.get("EPS Estimate")
            eps_act = row.get("Reported EPS")
            surprise = row.get("Surprise(%)")
            if eps_act is None:
                description = f"Earnings date (estimated EPS: {eps_est})"
            else:
                direction = "beat" if (surprise or 0) > 0 else "missed"
                description = f"EPS: {eps_act} vs est {eps_est} — {direction} by {surprise:.1f}%" if surprise else f"EPS: {eps_act}"
            title = f"{ticker} Q earnings announcement"
            self.db.insert_event(
                ticker=ticker,
                date=date_str,
                event_type="earnings",
                title=title,
                description=description,
            )
            stored += 1
        return stored

    # ── Bulk helpers ───────────────────────────────────────────────────────

    def fetch_all(
        self,
        tickers: Optional[List[str]] = None,
        include_events: bool = True,
        include_earnings: bool = True,
    ) -> Dict[str, Dict[str, int]]:
        """Fetch metadata + prices + events for every ticker. Returns counts."""
        tickers = tickers or list(COMPANY_REGISTRY.keys())
        results = {}

        for i, ticker in enumerate(tickers, 1):
            print(f"[{i}/{len(tickers)}] {ticker}")
            ok = self.fetch_company(ticker)
            if not ok:
                # Seed minimal metadata from the registry if yfinance fails
                info = COMPANY_REGISTRY.get(ticker, {})
                self.db.upsert_company(
                    ticker=ticker,
                    name=info.get("name", ticker),
                    sector=info.get("sector"),
                    industry=info.get("industry"),
                    exchange=info.get("exchange"),
                )

            price_rows = self.fetch_prices(ticker)
            event_rows = self.fetch_events(ticker) if include_events else 0
            earn_rows = self.fetch_earnings_events(ticker) if include_earnings else 0

            results[ticker] = {
                "prices": price_rows,
                "news_events": event_rows,
                "earnings_events": earn_rows,
            }
            print(f"       prices={price_rows}, news={event_rows}, earnings={earn_rows}")

            time.sleep(self.throttle)

        return results


# ── Helpers ────────────────────────────────────────────────────────────────

def _safe(v) -> Optional[float]:
    try:
        f = float(v)
        return None if f != f else f  # NaN guard
    except (TypeError, ValueError):
        return None


def _safe_int(v) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
