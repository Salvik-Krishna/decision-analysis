"""Price reaction analysis: measure how stock prices respond around corporate events."""

from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean, stdev
from typing import Dict, List, Optional

from .database import Database

PRE_WINDOWS = [1, 3, 5]
POST_WINDOWS = [1, 3, 5, 10, 30]


class EventAnalyzer:
    def __init__(self, db: Database) -> None:
        self.db = db

    def compute_reactions(
        self,
        tickers: Optional[List[str]] = None,
        event_types: Optional[List[str]] = None,
    ) -> int:
        """
        For every event in the DB, look up closing prices in the surrounding
        windows and compute percentage changes.  Stores results in price_reactions.
        Returns total reactions computed.
        """
        events = self.db.get_events(
            ticker=tickers[0] if tickers and len(tickers) == 1 else None,
            event_type=event_types[0] if event_types and len(event_types) == 1 else None,
        )

        # Filter to requested tickers / event_types when multiple were given
        if tickers:
            events = [e for e in events if e["ticker"] in tickers]
        if event_types:
            events = [e for e in events if e["event_type"] in event_types]

        computed = 0
        for event in events:
            ticker = event["ticker"]
            event_date = event["date"]
            event_id = event["id"]

            price_map = self._price_map(ticker)
            if not price_map:
                continue

            anchor = _find_nearest_trading_day(event_date, price_map, direction="on_or_after")
            if anchor is None:
                continue
            anchor_close = price_map[anchor]["close"]
            anchor_vol = price_map[anchor]["volume"]

            for days in POST_WINDOWS:
                target = _offset_trading_day(anchor, price_map, days, forward=True)
                if target:
                    p_chg = _pct_change(anchor_close, price_map[target]["close"])
                    v_chg = _pct_change(anchor_vol, price_map[target]["volume"])
                    self.db.upsert_reaction(event_id, ticker, days, "post", p_chg, v_chg)
                    computed += 1

            for days in PRE_WINDOWS:
                target = _offset_trading_day(anchor, price_map, days, forward=False)
                if target:
                    p_chg = _pct_change(price_map[target]["close"], anchor_close)
                    v_chg = _pct_change(price_map[target]["volume"], anchor_vol)
                    self.db.upsert_reaction(event_id, ticker, days, "pre", p_chg, v_chg)
                    computed += 1

        return computed

    def _price_map(self, ticker: str) -> Dict[str, dict]:
        rows = self.db.get_prices(ticker)
        return {r["date"]: {"close": r["adj_close"] or r["close"], "volume": r["volume"] or 0}
                for r in rows
                if (r["adj_close"] or r["close"])}

    # ── Aggregated views ───────────────────────────────────────────────────

    def impact_by_event_type(
        self,
        direction: str = "post",
        window_days: int = 5,
        ticker: Optional[str] = None,
    ) -> Dict[str, Dict[str, float]]:
        """
        Returns mean and stdev of price_change_pct grouped by event_type.
        direction: 'post' or 'pre'
        """
        rows = self.db.get_reactions(ticker=ticker)
        grouped: Dict[str, List[float]] = {}
        for r in rows:
            if r["direction"] != direction or r["window_days"] != window_days:
                continue
            if r["price_change_pct"] is None:
                continue
            grouped.setdefault(r["event_type"], []).append(r["price_change_pct"])

        result = {}
        for etype, vals in grouped.items():
            result[etype] = {
                "mean_pct": round(mean(vals), 4),
                "stdev_pct": round(stdev(vals), 4) if len(vals) > 1 else 0.0,
                "count": len(vals),
                "positive_rate": round(sum(1 for v in vals if v > 0) / len(vals), 4),
            }
        return dict(sorted(result.items(), key=lambda x: x[1]["mean_pct"], reverse=True))

    def company_event_summary(
        self,
        ticker: str,
        direction: str = "post",
        window_days: int = 5,
    ) -> List[Dict]:
        """Per-event table for a single ticker: date, type, price reaction."""
        rows = self.db.get_reactions(ticker=ticker)
        out = []
        for r in rows:
            if r["direction"] != direction or r["window_days"] != window_days:
                continue
            out.append({
                "date": r["event_date"],
                "event_type": r["event_type"],
                "title": r["title"][:80],
                "price_change_pct": r["price_change_pct"],
                "volume_change_pct": r["volume_change_pct"],
            })
        return sorted(out, key=lambda x: x["date"])

    def top_movers(
        self,
        direction: str = "post",
        window_days: int = 1,
        top_n: int = 20,
    ) -> List[Dict]:
        """Events that caused the largest absolute price moves."""
        rows = self.db.get_reactions()
        candidates = [
            {
                "ticker": r["ticker"],
                "event_date": r["event_date"],
                "event_type": r["event_type"],
                "title": r["title"][:80],
                "price_change_pct": r["price_change_pct"],
            }
            for r in rows
            if r["direction"] == direction
            and r["window_days"] == window_days
            and r["price_change_pct"] is not None
        ]
        return sorted(candidates, key=lambda x: abs(x["price_change_pct"] or 0), reverse=True)[:top_n]


# ── Date math helpers ──────────────────────────────────────────────────────

def _find_nearest_trading_day(
    date: str, price_map: Dict[str, dict], direction: str = "on_or_after"
) -> Optional[str]:
    sorted_dates = sorted(price_map.keys())
    if direction == "on_or_after":
        for d in sorted_dates:
            if d >= date:
                return d
    else:
        for d in reversed(sorted_dates):
            if d <= date:
                return d
    return None


def _offset_trading_day(
    anchor: str, price_map: Dict[str, dict], n: int, forward: bool
) -> Optional[str]:
    sorted_dates = sorted(price_map.keys())
    if anchor not in price_map:
        return None
    idx = sorted_dates.index(anchor)
    target_idx = idx + n if forward else idx - n
    if 0 <= target_idx < len(sorted_dates):
        return sorted_dates[target_idx]
    return None


def _pct_change(base, new) -> Optional[float]:
    try:
        b, n = float(base), float(new)
        if b == 0:
            return None
        return round((n - b) / b * 100, 4)
    except (TypeError, ValueError):
        return None
