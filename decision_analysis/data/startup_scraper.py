"""
Startup event scraper.

Two data sources:
  1. Hardcoded funding rounds from startups.py (loaded into DB on demand).
  2. Google News RSS — no API key required — for live event headlines per company.

Event classification reuses the same keyword patterns as the public-market scraper.
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

from .startups import STARTUP_REGISTRY
from .database import Database

# Google News RSS endpoint — no key, ~100 results per query
_GNEWS_URL = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; decision-analysis-bot/1.0; "
        "+https://github.com/example/decision-analysis)"
    )
}

_EVENT_PATTERNS: List[Tuple[str, str]] = [
    (r"acqui|merger|takeover|buyout|deal|combine|merge",                           "acquisition"),
    (r"fund|raise|series [a-h]|seed round|valuation|investor|VC|venture",          "funding"),
    (r"CEO|CFO|CTO|COO|president|appoint|resign|retire|step.?down|hire|fire",      "leadership"),
    (r"launch|release|unveil|introduc|new product|new service|debut",               "product"),
    (r"layoff|restructur|cut.*job|downsize|workforce|redundan|reorg",               "restructuring"),
    (r"regulat|fine|sued|lawsuit|antitrust|SEC |FTC |FDA |penalty|investig|probe", "regulatory"),
    (r"IPO|going public|direct listing|SPAC",                                       "ipo"),
    (r"partner|collaborat|joint venture|alliance|license",                          "partnership"),
    (r"pivot|rebrand|strategy|shift|expand",                                        "strategic"),
    (r"bankrupt|shut.?down|clos|wind.?down|liqui",                                  "failure"),
]


def _classify(title: str) -> str:
    for pattern, etype in _EVENT_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return etype
    return "other"


def _parse_rfc2822(date_str: str) -> Optional[str]:
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None


class StartupScraper:
    def __init__(self, db: Database, throttle_seconds: float = 2.0) -> None:
        self.db = db
        self.throttle = throttle_seconds

    # ── Load static funding data ───────────────────────────────────────────

    def load_registry(self, company_keys: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Seed the database from STARTUP_REGISTRY (no network calls).
        Returns {company_key: rounds_inserted}.
        """
        keys = company_keys or list(STARTUP_REGISTRY.keys())
        result = {}
        for key in keys:
            info = STARTUP_REGISTRY.get(key)
            if not info:
                continue

            rounds = info.get("funding_rounds", [])
            valuations = [r["valuation_usd"] for r in rounds if r.get("valuation_usd")]
            amounts = [r["amount_usd"] for r in rounds if r.get("amount_usd")]
            latest = max(rounds, key=lambda r: r["date"]) if rounds else {}

            self.db.upsert_startup(
                company_key=key,
                name=info["name"],
                sector=info.get("sector"),
                industry=info.get("industry"),
                founded=info.get("founded"),
                country=info.get("country"),
                hq_city=info.get("hq_city"),
                description=info.get("description", "")[:500],
                total_funding_usd=sum(amounts) if amounts else None,
                latest_valuation_usd=valuations[-1] if valuations else None,
                latest_round_type=latest.get("type"),
                latest_round_date=latest.get("date"),
            )

            inserted = 0
            for r in rounds:
                self.db.upsert_funding_round(
                    company_key=key,
                    date=r["date"],
                    round_type=r["type"],
                    amount_usd=r.get("amount_usd"),
                    valuation_usd=r.get("valuation_usd"),
                    lead_investor=r.get("lead", ""),
                )
                inserted += 1

            result[key] = inserted
        return result

    # ── Scrape news via Google News RSS ────────────────────────────────────

    def fetch_news_events(self, company_key: str, max_items: int = 30) -> int:
        """
        Query Google News RSS for the company name and store matched headlines.
        Returns the number of events stored.
        """
        if not _HAS_REQUESTS:
            print("  [warn] 'requests' not installed — skipping news scrape")
            return 0

        info = STARTUP_REGISTRY.get(company_key, {})
        company_name = info.get("name", company_key)
        query = quote_plus(f'"{company_name}" startup funding OR launch OR layoff OR CEO OR acquisition')
        url = _GNEWS_URL.format(query=query)

        try:
            resp = requests.get(url, headers=_HEADERS, timeout=15)
            resp.raise_for_status()
        except Exception as exc:
            print(f"  [error] {company_key} news fetch: {exc}")
            return 0

        stored = 0
        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as exc:
            print(f"  [error] {company_key} XML parse: {exc}")
            return 0

        items = root.findall(".//item")[:max_items]
        for item in items:
            title_el = item.find("title")
            pub_el = item.find("pubDate")
            link_el = item.find("link")
            if title_el is None or pub_el is None:
                continue
            title = (title_el.text or "").strip()
            date = _parse_rfc2822(pub_el.text or "")
            if not title or not date:
                continue
            url_str = (link_el.text or "") if link_el is not None else ""
            event_type = _classify(title)
            self.db.insert_startup_event(
                company_key=company_key,
                date=date,
                event_type=event_type,
                title=title,
                source_url=url_str,
            )
            stored += 1

        return stored

    # ── Funding milestones as events ───────────────────────────────────────

    def load_funding_as_events(self, company_keys: Optional[List[str]] = None) -> int:
        """
        Convert every funding round in the DB into a startup_event of type 'funding'.
        This allows the analysis layer to measure what happened after each round.
        """
        keys = company_keys or [r["company_key"] for r in self.db.list_startups()]
        total = 0
        for key in keys:
            for rnd in self.db.get_funding_rounds(key):
                company_name = STARTUP_REGISTRY.get(key, {}).get("name", key)
                val_str = f"${rnd['valuation_usd']/1e9:.1f}B" if rnd["valuation_usd"] else "undisclosed valuation"
                amt_str = f"${rnd['amount_usd']/1e6:.0f}M" if rnd["amount_usd"] else "undisclosed amount"
                title = f"{company_name} raises {amt_str} at {val_str} ({rnd['round_type']})"
                self.db.insert_startup_event(
                    company_key=key,
                    date=rnd["date"],
                    event_type="funding",
                    title=title,
                    description=f"Lead: {rnd['lead_investor']}",
                )
                total += 1
        return total

    # ── Bulk fetch ─────────────────────────────────────────────────────────

    def fetch_all(
        self,
        company_keys: Optional[List[str]] = None,
        include_news: bool = True,
    ) -> Dict[str, Dict[str, int]]:
        """Load registry data + scrape news for every company. Returns counts."""
        keys = company_keys or list(STARTUP_REGISTRY.keys())

        print(f"Loading registry for {len(keys)} companies…")
        round_counts = self.load_registry(keys)

        print("Converting funding rounds to events…")
        self.load_funding_as_events(keys)

        results = {}
        for i, key in enumerate(keys, 1):
            news = 0
            if include_news:
                print(f"[{i}/{len(keys)}] {key} — scraping news…")
                news = self.fetch_news_events(key)
                print(f"       news_events={news}")
                time.sleep(self.throttle)
            results[key] = {
                "funding_rounds": round_counts.get(key, 0),
                "news_events": news,
            }

        return results
