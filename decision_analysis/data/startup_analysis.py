"""
Startup valuation reaction analysis.

Because startups don't have daily prices, the "price signal" is the
post-money valuation disclosed at each funding round.

Logic
-----
For each startup_event we find:
  - prev_round : the most recent funding round BEFORE the event date
  - next_round : the first funding round AFTER the event date

Then we compute:
  - valuation_change_pct  : (next_val - prev_val) / prev_val * 100
  - amount_change_pct     : (next_amount - prev_amount) / prev_amount * 100
  - months_to_next_round  : calendar months between event date and next round

This captures "did company raise more (or less) money at a higher (or lower)
valuation after this event, and how quickly?"
"""

from __future__ import annotations

from datetime import datetime
from statistics import mean, stdev
from typing import Dict, List, Optional

from .database import Database


def _months_between(d1: str, d2: str) -> float:
    try:
        a = datetime.strptime(d1[:10], "%Y-%m-%d")
        b = datetime.strptime(d2[:10], "%Y-%m-%d")
        delta = b - a
        return round(delta.days / 30.44, 2)
    except ValueError:
        return 0.0


def _pct(base, new) -> Optional[float]:
    try:
        b, n = float(base), float(new)
        if b == 0:
            return None
        return round((n - b) / b * 100, 2)
    except (TypeError, ValueError):
        return None


class StartupAnalyzer:
    def __init__(self, db: Database) -> None:
        self.db = db

    def compute_reactions(
        self,
        company_keys: Optional[List[str]] = None,
        event_types: Optional[List[str]] = None,
    ) -> int:
        """
        For each startup_event, find bracketing funding rounds and store
        a valuation_reaction record.  Returns total records written.
        """
        events = self.db.get_startup_events(
            company_key=company_keys[0] if company_keys and len(company_keys) == 1 else None,
            event_type=event_types[0] if event_types and len(event_types) == 1 else None,
        )
        if company_keys:
            events = [e for e in events if e["company_key"] in company_keys]
        if event_types:
            events = [e for e in events if e["event_type"] in event_types]

        computed = 0
        for event in events:
            key = event["company_key"]
            event_date = event["date"]
            event_id = event["id"]

            rounds = self.db.get_funding_rounds(key)
            if not rounds:
                continue

            prev = _last_before(rounds, event_date)
            nxt = _first_after(rounds, event_date)

            if nxt is None:
                continue

            val_chg = _pct(
                prev["valuation_usd"] if prev else None,
                nxt["valuation_usd"],
            )
            amt_chg = _pct(
                prev["amount_usd"] if prev else None,
                nxt["amount_usd"],
            )
            months = _months_between(event_date, nxt["date"])

            self.db.upsert_valuation_reaction(
                event_id=event_id,
                company_key=key,
                prev_round_id=prev["id"] if prev else None,
                next_round_id=nxt["id"],
                months_to_next_round=months,
                valuation_change_pct=val_chg,
                amount_change_pct=amt_chg,
                round_type_after=nxt["round_type"],
            )
            computed += 1

        return computed

    # ── Aggregated views ───────────────────────────────────────────────────

    def impact_by_event_type(
        self, company_key: Optional[str] = None
    ) -> Dict[str, Dict]:
        """
        Mean valuation change and time-to-next-round grouped by event type.
        Only includes events where valuation_change_pct is known.
        """
        rows = self.db.get_valuation_reactions(company_key=company_key)
        grouped: Dict[str, List] = {}
        for r in rows:
            if r["valuation_change_pct"] is None:
                continue
            grouped.setdefault(r["event_type"], []).append({
                "val_chg": r["valuation_change_pct"],
                "months": r["months_to_next_round"] or 0,
            })

        result = {}
        for etype, items in grouped.items():
            vals = [x["val_chg"] for x in items]
            months = [x["months"] for x in items]
            result[etype] = {
                "mean_valuation_change_pct": round(mean(vals), 2),
                "stdev_valuation_change_pct": round(stdev(vals), 2) if len(vals) > 1 else 0.0,
                "mean_months_to_next_round": round(mean(months), 1),
                "count": len(vals),
                "positive_rate": round(sum(1 for v in vals if v > 0) / len(vals), 3),
            }
        return dict(sorted(result.items(), key=lambda x: x[1]["mean_valuation_change_pct"], reverse=True))

    def company_timeline(self, company_key: str) -> List[Dict]:
        """Chronological events + valuation reactions for one company."""
        rows = self.db.get_valuation_reactions(company_key=company_key)
        out = []
        for r in rows:
            out.append({
                "date": r["event_date"],
                "event_type": r["event_type"],
                "title": r["title"][:80],
                "valuation_change_pct": r["valuation_change_pct"],
                "amount_change_pct": r["amount_change_pct"],
                "months_to_next_round": r["months_to_next_round"],
                "round_type_after": r["round_type_after"],
            })
        return sorted(out, key=lambda x: x["date"])

    def funding_trajectory(self, company_key: str) -> List[Dict]:
        """Funding rounds ordered chronologically with cumulative total."""
        rounds = self.db.get_funding_rounds(company_key)
        cumulative = 0.0
        out = []
        for r in rounds:
            amt = r["amount_usd"] or 0
            cumulative += amt
            out.append({
                "date": r["date"],
                "round_type": r["round_type"],
                "amount_usd": r["amount_usd"],
                "valuation_usd": r["valuation_usd"],
                "cumulative_raised_usd": cumulative,
                "lead_investor": r["lead_investor"],
            })
        return out

    def cross_company_comparison(
        self,
        event_type: str = "funding",
        metric: str = "valuation_change_pct",
    ) -> List[Dict]:
        """
        Rank all companies by average metric value for a given event type.
        metric: 'valuation_change_pct' | 'amount_change_pct' | 'months_to_next_round'
        """
        rows = self.db.get_valuation_reactions(event_type=event_type)
        grouped: Dict[str, List[float]] = {}
        for r in rows:
            v = r[metric]
            if v is not None:
                grouped.setdefault(r["company_key"], []).append(float(v))

        result = []
        for key, vals in grouped.items():
            startup = self.db.get_startup(key)
            result.append({
                "company_key": key,
                "name": startup["name"] if startup else key,
                "sector": startup["sector"] if startup else "",
                f"mean_{metric}": round(mean(vals), 2),
                "count": len(vals),
            })
        return sorted(result, key=lambda x: x[f"mean_{metric}"], reverse=True)

    def biggest_valuation_jumps(self, top_n: int = 15) -> List[Dict]:
        """Events associated with the largest positive valuation changes."""
        rows = self.db.get_valuation_reactions()
        candidates = [
            {
                "company_key": r["company_key"],
                "event_date": r["event_date"],
                "event_type": r["event_type"],
                "title": r["title"][:80],
                "valuation_change_pct": r["valuation_change_pct"],
                "months_to_next_round": r["months_to_next_round"],
                "round_type_after": r["round_type_after"],
            }
            for r in rows
            if r["valuation_change_pct"] is not None
        ]
        return sorted(
            candidates, key=lambda x: x["valuation_change_pct"], reverse=True
        )[:top_n]

    def biggest_valuation_drops(self, top_n: int = 15) -> List[Dict]:
        """Events associated with the largest negative valuation changes (down rounds)."""
        rows = self.db.get_valuation_reactions()
        candidates = [
            {
                "company_key": r["company_key"],
                "event_date": r["event_date"],
                "event_type": r["event_type"],
                "title": r["title"][:80],
                "valuation_change_pct": r["valuation_change_pct"],
                "months_to_next_round": r["months_to_next_round"],
            }
            for r in rows
            if r["valuation_change_pct"] is not None
        ]
        return sorted(candidates, key=lambda x: x["valuation_change_pct"])[:top_n]


# ── Helpers ────────────────────────────────────────────────────────────────

def _last_before(rounds, date: str):
    candidates = [r for r in rounds if r["date"] < date]
    return max(candidates, key=lambda r: r["date"]) if candidates else None


def _first_after(rounds, date: str):
    candidates = [r for r in rounds if r["date"] > date]
    return min(candidates, key=lambda r: r["date"]) if candidates else None
