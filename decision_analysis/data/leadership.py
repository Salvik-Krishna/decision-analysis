"""
Executive roster tracker.

Answers questions like:
  - Who was in the C-suite at time T?
  - When did CEO X take over, and what happened to stock price afterwards?
  - Which companies had the most executive turnover over a period?

Data sources (in reliability order):
  1. SEC 8-K Item 5.02  — official, dated, mandatory (edgar.py writes these)
  2. yfinance officers   — current snapshot (edgar.py writes these)
  3. Manual / proxy      — for historical backfill
"""

from __future__ import annotations

from datetime import datetime
from statistics import mean
from typing import Dict, List, Optional

from .database import Database


# Titles that constitute "C-suite" for reporting purposes
_CSUITE_KEYWORDS = {
    "chief executive", "ceo",
    "chief financial", "cfo",
    "chief operating", "coo",
    "chief technology", "cto",
    "chief product", "cpo",
    "chief marketing", "cmo",
    "chief revenue", "cro",
    "chairman",
    "president",
    "executive vice president",
}


def _is_csuite(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in _CSUITE_KEYWORDS)


class LeadershipTracker:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ── Roster queries ─────────────────────────────────────────────────────

    def current_roster(self, ticker: str) -> List[Dict]:
        """All active executives currently tracked for a company."""
        rows = self.db.get_executives(ticker=ticker, current_only=True)
        return [_row_to_dict(r) for r in rows]

    def roster_at_date(self, ticker: str, date: str) -> List[Dict]:
        """
        Best-effort reconstruction of the executive roster at a given date.
        Returns executives whose start_date <= date and (end_date IS NULL or end_date > date).
        Falls back to current roster when history is sparse.
        """
        rows = self.db.get_executives_at_date(ticker=ticker, date=date)
        if not rows:
            # Sparse data: return current roster with a caveat
            rows = self.db.get_executives(ticker=ticker, current_only=True)
        return [_row_to_dict(r) for r in rows]

    def csuite_at_date(self, ticker: str, date: str) -> List[Dict]:
        """C-suite only subset of roster_at_date."""
        return [e for e in self.roster_at_date(ticker, date) if _is_csuite(e["title"])]

    def ceo_at_date(self, ticker: str, date: str) -> Optional[Dict]:
        """Return the CEO record active at the given date (best-effort)."""
        for e in self.roster_at_date(ticker, date):
            if "ceo" in e["title"].lower() or "chief executive" in e["title"].lower():
                return e
        return None

    # ── Tenure and turnover ────────────────────────────────────────────────

    def executive_tenure(self, ticker: str) -> List[Dict]:
        """All executive records ordered by start_date, with tenure_days computed."""
        rows = self.db.get_executives(ticker=ticker, current_only=False)
        out = []
        today = datetime.utcnow().strftime("%Y-%m-%d")
        for r in rows:
            d = _row_to_dict(r)
            start = d.get("start_date") or ""
            end = d.get("end_date") or today
            try:
                s = datetime.strptime(start[:10], "%Y-%m-%d")
                e = datetime.strptime(end[:10], "%Y-%m-%d")
                d["tenure_days"] = (e - s).days
            except ValueError:
                d["tenure_days"] = None
            out.append(d)
        return sorted(out, key=lambda x: x.get("start_date") or "")

    def turnover_events(self, ticker: str) -> List[Dict]:
        """
        C-suite changes (departures + appointments) ordered chronologically.
        Sourced from the leadership events in the events table.
        """
        events = self.db.get_events(ticker=ticker, event_type="leadership")
        return [
            {
                "date": e["date"],
                "title": e["title"],
                "description": e["description"],
                "source": e["source_domain"],
                "credibility": e["credibility_score"],
                "sec_url": e["source_url"],
            }
            for e in events
        ]

    def turnover_rate(self, ticker: str, start: str, end: str) -> Dict:
        """
        Count executive changes (5.02 events) between start and end.
        Returns count, annualised rate, and list of changes.
        """
        events = self.db.get_events(ticker=ticker, event_type="leadership",
                                    start=start, end=end)
        n = len(events)
        try:
            s = datetime.strptime(start[:10], "%Y-%m-%d")
            e = datetime.strptime(end[:10], "%Y-%m-%d")
            years = max((e - s).days / 365.25, 0.01)
        except ValueError:
            years = 1.0
        return {
            "ticker": ticker,
            "start": start,
            "end": end,
            "change_count": n,
            "annualised_rate": round(n / years, 2),
            "events": [{"date": ev["date"], "title": ev["title"][:60]} for ev in events],
        }

    # ── Cross-company views ────────────────────────────────────────────────

    def high_turnover_companies(
        self,
        tickers: List[str],
        start: str = "2018-01-01",
        end: Optional[str] = None,
    ) -> List[Dict]:
        """Rank companies by annualised C-suite turnover rate, highest first."""
        if end is None:
            end = datetime.utcnow().strftime("%Y-%m-%d")
        results = [self.turnover_rate(t, start, end) for t in tickers]
        return sorted(results, key=lambda x: x["annualised_rate"], reverse=True)

    def post_leadership_change_returns(
        self,
        ticker: str,
        window_days: int = 30,
    ) -> List[Dict]:
        """
        For each leadership event, look up the stock price reaction in the
        price_reactions table (populated by EventAnalyzer).
        """
        from .analysis import EventAnalyzer
        ea = EventAnalyzer(self.db)
        return ea.company_event_summary(
            ticker, direction="post", window_days=window_days
        )

    def ceo_change_market_impact(self, tickers: List[str]) -> List[Dict]:
        """
        Aggregate average post-event return after CEO changes across companies.
        Requires price reactions to be pre-computed.
        """
        rows = self.db.get_reactions(event_type="leadership")
        by_ticker: Dict[str, List[float]] = {}
        for r in rows:
            if r["direction"] == "post" and r["window_days"] == 5:
                if r["price_change_pct"] is not None and r["ticker"] in tickers:
                    by_ticker.setdefault(r["ticker"], []).append(r["price_change_pct"])

        out = []
        for ticker, vals in by_ticker.items():
            company = self.db.get_company(ticker)
            out.append({
                "ticker": ticker,
                "name": company["name"] if company else ticker,
                "mean_5d_return_pct": round(mean(vals), 3),
                "event_count": len(vals),
            })
        return sorted(out, key=lambda x: x["mean_5d_return_pct"], reverse=True)

    # ── DEF 14A proxy snapshot ────────────────────────────────────────────
    # (Minimal implementation — full proxy parsing requires document download)

    def proxy_exec_count_from_events(self, ticker: str, year: int) -> int:
        """
        Proxy for 'how many executives were on record in YEAR'.
        Uses the executives table filtered by tenure active during that year.
        """
        start = f"{year}-01-01"
        end = f"{year}-12-31"
        rows = self.db.get_executives_at_date(ticker=ticker, date=end)
        # Filter to those active during the year
        active = [
            r for r in rows
            if (r["start_date"] or "0000") <= end
            and (r["end_date"] is None or r["end_date"] >= start)
        ]
        return len(active)

    # ── Pretty summaries ───────────────────────────────────────────────────

    def company_leadership_report(self, ticker: str) -> Dict:
        """Full leadership summary for one company."""
        company = self.db.get_company(ticker)
        return {
            "ticker": ticker,
            "company": company["name"] if company else ticker,
            "current_roster": self.current_roster(ticker),
            "turnover_since_2018": self.turnover_rate(ticker, "2018-01-01",
                                                       datetime.utcnow().strftime("%Y-%m-%d")),
            "tenure_records": self.executive_tenure(ticker),
        }


# ── Helper ─────────────────────────────────────────────────────────────────

def _row_to_dict(row) -> Dict:
    return dict(zip(row.keys(), tuple(row)))
