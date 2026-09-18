"""
SEC EDGAR 8-K scraper — official, legally-mandated corporate event filings.

Why EDGAR instead of news
--------------------------
Every US public company must file an 8-K within 4 business days of any
"material" event.  The items field in each filing is machine-readable and
maps directly to event types.  No headline bias, no paywall, no rate-limited
API key needed.

Rate limits
-----------
SEC policy: ≤10 requests/second.  We default to 0.15s throttle.
User-Agent must identify the application (SEC requirement, not enforced as
auth but logged).  Set EDGAR_USER_AGENT env var or pass user_agent= to override.

8-K item → event_type mapping
-------------------------------
1.01/1.02  deal          Entry / termination of material agreement
1.03       bankruptcy    Bankruptcy or receivership
2.01       acquisition   Completion of acquisition or disposition
2.02       earnings      Results of operations / earnings release
2.05       restructuring Exit costs / workforce reduction
2.06       restructuring Material impairment
3.01       regulatory    Notice of delisting or failure to satisfy listing rule
4.01/4.02  regulatory    Change in / non-reliance on auditor
5.01       leadership    Change in control of registrant
5.02       leadership    Departure / appointment of executives or directors
5.03       governance    Amendments to charter or bylaws
5.07       governance    Submission to vote of security holders
7.01/7.02  guidance      Regulation FD / forward guidance disclosure
8.01       other         Other events (catch-all)
9.01       <skip>        Financial exhibits — always accompanies others
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

from .database import Database

# ── EDGAR endpoints ────────────────────────────────────────────────────────
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
_SUBMISSIONS_EXTRA = "https://data.sec.gov/submissions/{filename}"
_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/{document}"

_DEFAULT_UA = "DecisionAnalysis/1.0 research tool (github.com/example/decision-analysis)"

# ── Item code mappings ─────────────────────────────────────────────────────
_ITEM_TO_TYPE: Dict[str, str] = {
    "1.01": "deal",
    "1.02": "deal",
    "1.03": "bankruptcy",
    "2.01": "acquisition",
    "2.02": "earnings",
    "2.03": "deal",
    "2.04": "deal",
    "2.05": "restructuring",
    "2.06": "restructuring",
    "3.01": "regulatory",
    "3.02": "regulatory",
    "3.03": "regulatory",
    "4.01": "regulatory",
    "4.02": "regulatory",
    "5.01": "leadership",
    "5.02": "leadership",
    "5.03": "governance",
    "5.04": "governance",
    "5.05": "governance",
    "5.06": "governance",
    "5.07": "governance",
    "5.08": "governance",
    "6.01": "dividend",
    "7.01": "guidance",
    "7.02": "guidance",
    "8.01": "other",
    "9.01": None,  # financial exhibits — skip
}

_ITEM_TITLES: Dict[str, str] = {
    "1.01": "Entered material definitive agreement",
    "1.02": "Terminated material definitive agreement",
    "1.03": "Bankruptcy or receivership",
    "2.01": "Acquisition or disposition of assets completed",
    "2.02": "Earnings release / results of operations",
    "2.05": "Exit costs or workforce reduction announced",
    "2.06": "Material impairment charge",
    "3.01": "Delisting notice or listing-rule failure",
    "4.01": "Change in independent auditor",
    "4.02": "Non-reliance on prior financial statements",
    "5.01": "Change in control of registrant",
    "5.02": "Executive or director departure / appointment",
    "5.03": "Charter or bylaws amendment",
    "5.07": "Shareholder vote results",
    "6.01": "Dividend or distribution announced",
    "7.01": "Regulation FD / forward guidance disclosure",
    "8.01": "Other material event",
}

# leadership-sub-patterns extracted from 8-K body text
_APPOINT_RE = re.compile(
    r"(?:appoint(?:ed|ment)|named|elected|hired)\s+(?:as\s+)?"
    r"([A-Z][a-zA-Z\-\'\.]+(?:\s+[A-Z][a-zA-Z\-\'\.]+){1,4})"
    r"\s+(?:as|to serve as|to the position of)\s+"
    r"((?:[A-Z][a-zA-Z\s\-,]+?)"
    r"(?:Officer|President|CEO|CFO|CTO|COO|Vice President|VP|Chairman|Director|Secretary|Treasurer))",
    re.IGNORECASE,
)
_DEPART_RE = re.compile(
    r"([A-Z][a-zA-Z\-\'\.]+(?:\s+[A-Z][a-zA-Z\-\'\.]+){1,4})"
    r"[,\s]+(?:has\s+)?(?:resigned|retired|stepped\s+down|departed|notified.*intention to resign)"
    r"(?:\s+(?:as|from))?\s*"
    r"((?:[A-Z][a-zA-Z\s\-,]+?)"
    r"(?:Officer|President|CEO|CFO|CTO|COO|Vice President|VP|Chairman|Director|Secretary|Treasurer))?",
    re.IGNORECASE,
)


class EDGARScraper:
    """
    Pull 8-K filing history from EDGAR for any US public company.

    Parameters
    ----------
    db          : Database instance to write events into
    user_agent  : Free-text UA string for SEC (name + contact)
    throttle    : Seconds between requests (SEC limit ~10/s; default 0.2)
    """

    def __init__(
        self,
        db: Database,
        user_agent: str = "",
        throttle: float = 0.2,
    ) -> None:
        self.db = db
        self.ua = user_agent or os.getenv("EDGAR_USER_AGENT", _DEFAULT_UA)
        self.throttle = throttle
        self._ticker_map: Optional[Dict[str, str]] = None  # ticker → cik

    # ── CIK resolution ─────────────────────────────────────────────────────

    def get_cik(self, ticker: str) -> Optional[str]:
        """Return zero-padded 10-digit CIK for ticker. Uses DB cache."""
        ticker = ticker.upper()
        cached = self.db.get_cik(ticker)
        if cached:
            return cached

        if self._ticker_map is None:
            self._ticker_map = self._load_ticker_map()

        cik = self._ticker_map.get(ticker)
        if cik:
            self.db.cache_cik(ticker, cik)
        return cik

    def _load_ticker_map(self) -> Dict[str, str]:
        data = self._get_json(_TICKERS_URL)
        mapping: Dict[str, str] = {}
        for entry in data.values():
            t = entry.get("ticker", "").upper()
            cik_raw = str(entry.get("cik_str", ""))
            if t and cik_raw:
                mapping[t] = cik_raw.zfill(10)
        return mapping

    # ── Filing history ─────────────────────────────────────────────────────

    def fetch_8k_events(
        self,
        ticker: str,
        start: str = "2015-01-01",
        end: Optional[str] = None,
    ) -> int:
        """
        Download all 8-K filings for a ticker in the date range, classify
        them, and store in the events table.  Returns number of events stored.
        """
        if end is None:
            end = datetime.utcnow().strftime("%Y-%m-%d")

        cik = self.get_cik(ticker)
        if not cik:
            print(f"  [warn] {ticker}: CIK not found in EDGAR")
            return 0

        company = self.db.get_company(ticker)
        company_name = company["name"] if company else ticker

        filings = self._fetch_all_8k(cik, start, end)
        if not filings:
            return 0

        stored = 0
        for filing in filings:
            items_str = filing.get("items", "")
            if not items_str:
                continue
            event_type, title = self._classify_filing(items_str, company_name)
            if event_type is None:
                continue

            accession = filing["accessionNumber"]
            primary_doc = filing.get("primaryDocument", "")
            sec_url = _filing_url(cik, accession, primary_doc) if primary_doc else ""

            # For leadership events, try to extract executive details
            description = ""
            if event_type == "leadership" and primary_doc:
                description = self._extract_leadership_detail(cik, accession, primary_doc)

            event_id = self.db.insert_event(
                ticker=ticker,
                date=filing["filingDate"],
                event_type=event_type,
                title=title,
                description=description,
                source_url=sec_url,
                credibility_score=1.0,
                source_domain="sec.gov",
            )

            # Store structured leadership changes separately
            if event_type == "leadership" and description:
                self._store_leadership_changes(ticker, filing["filingDate"], description)

            stored += 1

        return stored

    def _fetch_all_8k(
        self, cik: str, start: str, end: str
    ) -> List[Dict]:
        """Fetch the submissions JSON and extract 8-K rows within date range."""
        url = _SUBMISSIONS_URL.format(cik10=cik)
        try:
            data = self._get_json(url)
        except Exception as exc:
            print(f"  [error] EDGAR submissions fetch: {exc}")
            return []

        all_filings = self._extract_8k_rows(data.get("filings", {}).get("recent", {}))

        # Paginate through additional submission files
        for extra_file in data.get("filings", {}).get("files", []):
            filename = extra_file.get("name", "")
            if not filename:
                continue
            try:
                extra_data = self._get_json(_SUBMISSIONS_EXTRA.format(filename=filename))
                all_filings.extend(self._extract_8k_rows(extra_data))
            except Exception:
                pass

        # Filter by date range and remove 8-K/A amendments if you only want originals
        return [
            f for f in all_filings
            if start <= f["filingDate"] <= end
            and f.get("form") in ("8-K", "8-K/A")
        ]

    @staticmethod
    def _extract_8k_rows(recent: dict) -> List[Dict]:
        """Zip the parallel arrays in submissions recent into a list of dicts."""
        if not recent:
            return []
        keys = ["accessionNumber", "filingDate", "form", "primaryDocument", "items"]
        arrays = {k: recent.get(k, []) for k in keys}
        length = len(arrays["filingDate"])
        rows = []
        for i in range(length):
            rows.append({k: (arrays[k][i] if i < len(arrays[k]) else "") for k in keys})
        return rows

    # ── Event classification ───────────────────────────────────────────────

    @staticmethod
    def _classify_filing(
        items_str: str, company_name: str
    ) -> Tuple[Optional[str], str]:
        """
        Return (event_type, human_title) from an 8-K items string like "5.02,9.01".
        Returns (None, "") if the only item is 9.01 (exhibits only).
        """
        items = [i.strip() for i in items_str.split(",") if i.strip()]
        # Remove exhibit-only item
        meaningful = [i for i in items if i != "9.01"]
        if not meaningful:
            return None, ""

        # Priority: pick the most specific item type
        priority_order = [
            "1.03", "5.01", "5.02", "2.01", "2.05", "2.02",
            "1.01", "1.02", "3.01", "4.01", "7.01", "5.03", "8.01",
        ]
        chosen = meaningful[0]
        for p in priority_order:
            if p in meaningful:
                chosen = p
                break

        event_type = _ITEM_TO_TYPE.get(chosen, "other")
        title_base = _ITEM_TITLES.get(chosen, f"8-K item {chosen} filed")
        title = f"{company_name} — {title_base}"

        # Append secondary items for context
        others = [i for i in meaningful if i != chosen]
        if others:
            title += f" (also: {', '.join(others)})"

        return event_type, title

    # ── Leadership detail extraction ────────────────────────────────────────

    def _extract_leadership_detail(
        self, cik: str, accession: str, primary_doc: str
    ) -> str:
        """
        Best-effort: download 8-K HTML and regex-scan for executive names.
        Returns a description string (empty on failure).
        """
        url = _filing_url(cik, accession, primary_doc)
        try:
            html = self._get_raw(url)
        except Exception:
            return ""

        # Strip tags
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)[:8000]  # cap to first 8k chars

        parts = []
        for m in _APPOINT_RE.finditer(text):
            name, title = m.group(1).strip(), m.group(2).strip()
            parts.append(f"Appointed: {name} as {title}")
        for m in _DEPART_RE.finditer(text):
            name = m.group(1).strip()
            title = (m.group(2) or "").strip()
            parts.append(f"Departed: {name}" + (f" ({title})" if title else ""))

        return "; ".join(parts[:4])  # cap at 4 changes per filing

    def _store_leadership_changes(
        self, ticker: str, date: str, description: str
    ) -> None:
        """Parse 'Appointed: X as Y; Departed: Z' and write to executives table."""
        for part in description.split(";"):
            part = part.strip()
            if part.startswith("Appointed:"):
                rest = part[len("Appointed:"):].strip()
                if " as " in rest:
                    name, title = rest.split(" as ", 1)
                    self.db.upsert_executive(
                        ticker=ticker,
                        name=name.strip(),
                        title=title.strip(),
                        start_date=date,
                        end_date=None,
                        source="8-K/5.02",
                    )
            elif part.startswith("Departed:"):
                rest = part[len("Departed:"):].strip()
                name = re.sub(r"\s*\(.*?\)", "", rest).strip()
                if name:
                    self.db.close_executive_tenure(ticker=ticker, name=name, end_date=date)

    # ── Current officers from yfinance ─────────────────────────────────────

    def fetch_current_officers(self, ticker: str) -> int:
        """
        Pull current executives from yfinance companyOfficers and store in
        the executives table.  Returns number of records written.
        """
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
        except Exception as exc:
            print(f"  [error] {ticker} officers: {exc}")
            return 0

        officers = info.get("companyOfficers") or []
        today = datetime.utcnow().strftime("%Y-%m-%d")
        stored = 0
        for o in officers:
            name = (o.get("name") or "").strip()
            title = (o.get("title") or "").strip()
            if not name or not title:
                continue
            self.db.upsert_executive(
                ticker=ticker,
                name=name,
                title=title,
                start_date=None,
                end_date=None,
                is_current=True,
                total_pay=o.get("totalPay"),
                source="yfinance",
            )
            stored += 1
        return stored

    # ── Bulk pipeline ──────────────────────────────────────────────────────

    def fetch_all(
        self,
        tickers: List[str],
        start: str = "2015-01-01",
        include_officers: bool = True,
    ) -> Dict[str, Dict[str, int]]:
        results = {}
        for i, ticker in enumerate(tickers, 1):
            print(f"[{i}/{len(tickers)}] {ticker} — EDGAR 8-K…")
            events = self.fetch_8k_events(ticker, start=start)
            officers = self.fetch_current_officers(ticker) if include_officers else 0
            print(f"       8-K events={events}  officers={officers}")
            results[ticker] = {"8k_events": events, "officers": officers}
            time.sleep(self.throttle)
        return results

    # ── HTTP helpers ───────────────────────────────────────────────────────

    def _get_json(self, url: str) -> dict:
        time.sleep(self.throttle)
        req = Request(url, headers={"User-Agent": self.ua, "Accept": "application/json"})
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get_raw(self, url: str) -> str:
        time.sleep(self.throttle)
        req = Request(url, headers={"User-Agent": self.ua, "Accept": "text/html"})
        with urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8", errors="replace")


# ── Utility ────────────────────────────────────────────────────────────────

def _filing_url(cik: str, accession: str, document: str) -> str:
    accession_nodash = accession.replace("-", "")
    return _ARCHIVES_URL.format(
        cik=cik.lstrip("0"),
        accession_nodash=accession_nodash,
        document=document,
    )
