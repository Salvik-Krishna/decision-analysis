"""
Build the flat, analysis-ready ``decision_dataset`` table from the raw market
data (events, prices, reactions, executives, startups, funding rounds).

One row = one real corporate **decision** — either a US-public-company 8-K
filing (a legally material, machine-classified event) or a startup funding /
news event with a measured valuation reaction.

Each column is mapped to a node of the decision-analysis framework:

  Framework › Limiting influence   -> source_credibility, source_domain,
                                       pre_event_drift_5d
  Framework › Limiting action      -> is_material, regulatory_constraint,
                                       action_class
  Framework › Structure            -> exec_count, leadership_turnover_24m,
                                       restructuring_24m
  Controlling › Human alignment    -> leadership_change_flag,
                                       alignment_with_market
  Analysing outcome                -> change_in_value_{1d,5d,30d},
                                       primary_change_in_value, primary_pnl,
                                       volume_reaction_5d, customer_proxy
  Study dimensions (heuristic)     -> decision_quality, organizational_adaptability,
                                       power_distribution, alignment_dynamics,
                                       coordination_efficiency, ethical_stability

Heuristic study-dimension columns are documented, transparent proxies derived
purely from the real data — they are starting points for analysis, not ground
truth.  Framework leaves that have **no** market-data basis (model intent,
agent personalities, surveyed customer satisfaction) are intentionally left
NULL and belong to the simulation layer.

Run:
    python -m decision_analysis.data.dataset            # rebuild the table
    python -m decision_analysis.data.dataset --csv out.csv
"""

from __future__ import annotations

import argparse
import math
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .database import Database, DEFAULT_DB_PATH

# 8-K event_type  ->  framework "action class"
_ACTION_CLASS: Dict[str, str] = {
    "earnings": "disclosure",
    "guidance": "disclosure",
    "leadership": "governance",
    "governance": "governance",
    "acquisition": "strategic",
    "deal": "strategic",
    "restructuring": "operational",
    "regulatory": "compliance",
    "bankruptcy": "compliance",
    "dividend": "capital_return",
    "other": "other",
}
_REGULATORY_TYPES = {"regulatory", "bankruptcy"}
_RECONFIG_TYPES = {"leadership", "restructuring"}

TABLE = "decision_dataset"

_SCHEMA = f"""
DROP TABLE IF EXISTS {TABLE};
CREATE TABLE {TABLE} (
    decision_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_key             TEXT UNIQUE,        -- entity_type:source_id
    entity_type              TEXT,               -- 'public' | 'startup'
    entity_id                TEXT,               -- ticker or company_key
    company_name             TEXT,
    sector                   TEXT,
    industry                 TEXT,
    decision_date            TEXT,
    decision_type            TEXT,
    decision_title           TEXT,
    source_url               TEXT,
    -- Framework: Limiting influence
    source_credibility       REAL,
    source_domain            TEXT,
    pre_event_drift_5d       REAL,
    -- Framework: Limiting action
    is_material              INTEGER,
    regulatory_constraint    INTEGER,
    action_class             TEXT,
    -- Framework: Structure of the organisation
    exec_count               INTEGER,
    leadership_turnover_24m  INTEGER,
    restructuring_24m        INTEGER,
    -- Controlling the situation: Human alignment
    leadership_change_flag   INTEGER,
    alignment_with_market    REAL,
    -- Analysing outcome
    change_in_value_1d       REAL,
    change_in_value_5d       REAL,
    change_in_value_30d      REAL,
    primary_change_in_value  REAL,
    primary_pnl              REAL,
    outcome_horizon          TEXT,
    volume_reaction_5d       REAL,
    customer_proxy           REAL,
    -- Study dimensions (heuristic proxies)
    decision_quality         REAL,
    organizational_adaptability REAL,
    power_distribution       REAL,
    alignment_dynamics       REAL,
    coordination_efficiency  REAL,
    ethical_stability        REAL,
    built_at                 TEXT
);
CREATE INDEX idx_dd_entity ON {TABLE}(entity_type, entity_id);
CREATE INDEX idx_dd_type   ON {TABLE}(decision_type);
CREATE INDEX idx_dd_date   ON {TABLE}(decision_date);
"""

_COLUMNS = [
    "decision_key", "entity_type", "entity_id", "company_name", "sector", "industry",
    "decision_date", "decision_type", "decision_title", "source_url",
    "source_credibility", "source_domain", "pre_event_drift_5d",
    "is_material", "regulatory_constraint", "action_class",
    "exec_count", "leadership_turnover_24m", "restructuring_24m",
    "leadership_change_flag", "alignment_with_market",
    "change_in_value_1d", "change_in_value_5d", "change_in_value_30d",
    "primary_change_in_value", "primary_pnl", "outcome_horizon",
    "volume_reaction_5d", "customer_proxy",
    "decision_quality", "organizational_adaptability", "power_distribution",
    "alignment_dynamics", "coordination_efficiency", "ethical_stability",
    "built_at",
]


def build_decision_dataset(db: Database) -> int:
    """(Re)build the ``decision_dataset`` table. Returns the row count."""
    conn = sqlite3.connect(db.path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_SCHEMA)
        now = datetime.utcnow().isoformat(timespec="seconds")
        rows: List[dict] = []
        rows += _build_public_rows(conn, now)
        rows += _build_startup_rows(conn, now)
        if rows:
            placeholders = ", ".join(f":{c}" for c in _COLUMNS)
            conn.executemany(
                f"INSERT OR REPLACE INTO {TABLE} ({', '.join(_COLUMNS)}) VALUES ({placeholders})",
                rows,
            )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


# ── Public-company decisions (8-K events) ──────────────────────────────────

def _build_public_rows(conn: sqlite3.Connection, now: str) -> List[dict]:
    exec_counts = {
        r["ticker"]: r["n"]
        for r in conn.execute("SELECT ticker, COUNT(*) AS n FROM executives GROUP BY ticker")
    }

    events = conn.execute("""
        SELECT e.id, e.ticker, e.date, e.event_type, e.title, e.source_url,
               e.credibility_score, e.source_domain,
               c.name AS company_name, c.sector, c.industry,
               MAX(CASE WHEN r.direction='post' AND r.window_days=1  THEN r.price_change_pct END)  AS post1,
               MAX(CASE WHEN r.direction='post' AND r.window_days=5  THEN r.price_change_pct END)  AS post5,
               MAX(CASE WHEN r.direction='post' AND r.window_days=30 THEN r.price_change_pct END)  AS post30,
               MAX(CASE WHEN r.direction='pre'  AND r.window_days=5  THEN r.price_change_pct END)  AS pre5,
               MAX(CASE WHEN r.direction='post' AND r.window_days=5  THEN r.volume_change_pct END) AS vol5
        FROM events e
        JOIN companies c ON e.ticker = c.ticker
        LEFT JOIN price_reactions r ON r.event_id = e.id
        GROUP BY e.id
        ORDER BY e.ticker, e.date
    """).fetchall()

    # Per-ticker ordered (date, type) list for trailing-window aggregates.
    by_ticker: Dict[str, List[sqlite3.Row]] = {}
    for ev in events:
        by_ticker.setdefault(ev["ticker"], []).append(ev)

    rows: List[dict] = []
    for ticker, evs in by_ticker.items():
        for ev in evs:
            etype = ev["event_type"]
            turnover = _trailing_count(evs, ev["date"], {"leadership"})
            restructuring = _trailing_count(evs, ev["date"], {"restructuring"})
            reconfig = _trailing_count(evs, ev["date"], _RECONFIG_TYPES)
            regul_24m = _trailing_count(evs, ev["date"], _REGULATORY_TYPES)

            post1, post5, post30 = ev["post1"], ev["post5"], ev["post30"]
            pre5 = ev["pre5"]
            primary = post5 if post5 is not None else post1
            quality = post30 if post30 is not None else (post5 if post5 is not None else post1)

            rows.append({
                "decision_key": f"public:{ev['id']}",
                "entity_type": "public",
                "entity_id": ticker,
                "company_name": ev["company_name"],
                "sector": ev["sector"],
                "industry": ev["industry"],
                "decision_date": ev["date"],
                "decision_type": etype,
                "decision_title": ev["title"],
                "source_url": ev["source_url"],
                # limiting influence
                "source_credibility": ev["credibility_score"],
                "source_domain": ev["source_domain"],
                "pre_event_drift_5d": pre5,
                # limiting action
                "is_material": 1,
                "regulatory_constraint": 1 if etype in _REGULATORY_TYPES else 0,
                "action_class": _ACTION_CLASS.get(etype, "other"),
                # structure
                "exec_count": exec_counts.get(ticker),
                "leadership_turnover_24m": turnover,
                "restructuring_24m": restructuring,
                # alignment / control
                "leadership_change_flag": 1 if etype == "leadership" else 0,
                "alignment_with_market": _alignment(pre5, post5),
                # outcomes
                "change_in_value_1d": post1,
                "change_in_value_5d": post5,
                "change_in_value_30d": post30,
                "primary_change_in_value": primary,
                "primary_pnl": primary,
                "outcome_horizon": "+5d",
                "volume_reaction_5d": ev["vol5"],
                "customer_proxy": None,  # no surveyed-CSAT source for public cos
                # study dimensions (heuristic)
                "decision_quality": quality,
                "organizational_adaptability": _adaptability(reconfig),
                "power_distribution": _power_distribution(exec_counts.get(ticker)),
                "alignment_dynamics": _alignment(pre5, post5),
                "coordination_efficiency": _coordination(post1, post30),
                "ethical_stability": _ethical(regul_24m),
                "built_at": now,
            })
    return rows


# ── Startup decisions (funding / news events) ──────────────────────────────

def _build_startup_rows(conn: sqlite3.Connection, now: str) -> List[dict]:
    try:
        events = conn.execute("""
            SELECT se.id, se.company_key, se.date, se.event_type, se.title, se.source_url,
                   s.name AS company_name, s.sector, s.industry,
                   vr.valuation_change_pct, vr.amount_change_pct, vr.months_to_next_round
            FROM startup_events se
            JOIN startups s ON se.company_key = s.company_key
            LEFT JOIN valuation_reactions vr ON vr.event_id = se.id
            ORDER BY se.company_key, se.date
        """).fetchall()
    except sqlite3.OperationalError:
        return []

    by_key: Dict[str, List[sqlite3.Row]] = {}
    for ev in events:
        by_key.setdefault(ev["company_key"], []).append(ev)

    rows: List[dict] = []
    for key, evs in by_key.items():
        for ev in evs:
            etype = ev["event_type"]
            val_chg = ev["valuation_change_pct"]
            reconfig = _trailing_count(evs, ev["date"], _RECONFIG_TYPES)
            regul_24m = _trailing_count(evs, ev["date"], _REGULATORY_TYPES)
            rows.append({
                "decision_key": f"startup:{ev['id']}",
                "entity_type": "startup",
                "entity_id": key,
                "company_name": ev["company_name"],
                "sector": ev["sector"],
                "industry": ev["industry"],
                "decision_date": ev["date"],
                "decision_type": etype,
                "decision_title": ev["title"],
                "source_url": ev["source_url"],
                "source_credibility": None,
                "source_domain": "startup_registry/news",
                "pre_event_drift_5d": None,
                "is_material": 0,
                "regulatory_constraint": 1 if etype in _REGULATORY_TYPES else 0,
                "action_class": _ACTION_CLASS.get(etype, "other"),
                "exec_count": None,
                "leadership_turnover_24m": None,
                "restructuring_24m": None,
                "leadership_change_flag": 1 if etype == "leadership" else 0,
                "alignment_with_market": None,
                "change_in_value_1d": None,
                "change_in_value_5d": None,
                "change_in_value_30d": None,
                "primary_change_in_value": val_chg,
                "primary_pnl": val_chg,
                "outcome_horizon": "next_funding_round",
                "volume_reaction_5d": None,
                "customer_proxy": None,
                "decision_quality": val_chg,
                "organizational_adaptability": _adaptability(reconfig),
                "power_distribution": None,
                "alignment_dynamics": None,
                "coordination_efficiency": (
                    _months_to_speed(ev["months_to_next_round"])
                ),
                "ethical_stability": _ethical(regul_24m),
                "built_at": now,
            })
    return rows


# ── Heuristic helpers ──────────────────────────────────────────────────────

def _trailing_count(events: List[sqlite3.Row], as_of: str, types: set) -> int:
    """Count events of given types in the 24 months *before or on* as_of."""
    start = _shift_months(as_of, -24)
    return sum(
        1 for e in events
        if e["event_type"] in types and start <= e["date"] <= as_of
    )


def _alignment(pre: Optional[float], post: Optional[float]) -> Optional[float]:
    """+1 if pre-event drift and post-event reaction move the same way, else -1."""
    if pre is None or post is None:
        return None
    if pre == 0 or post == 0:
        return 0.0
    return 1.0 if (pre > 0) == (post > 0) else -1.0


def _adaptability(reconfig_24m: int) -> float:
    """0..1 — more leadership/restructuring activity ⇒ higher structural adaptability."""
    return round(1.0 - 1.0 / (1.0 + reconfig_24m), 4)


def _power_distribution(exec_count: Optional[int]) -> Optional[float]:
    """0..1 structural proxy — more named officers on record ⇒ more distributed authority."""
    if not exec_count:
        return None
    return round(min(exec_count, 30) / 30.0, 4)


def _coordination(post1: Optional[float], post30: Optional[float]) -> Optional[float]:
    """0..1 — consistency between the 1-day and 30-day reaction (small gap ⇒ coordinated)."""
    if post1 is None or post30 is None:
        return None
    spread = abs(post30 - post1)
    return round(1.0 / (1.0 + spread / 5.0), 4)


def _ethical(regulatory_24m: int) -> float:
    """0..1 — fewer trailing compliance/regulatory incidents ⇒ higher ethical stability."""
    return round(1.0 / (1.0 + regulatory_24m), 4)


def _months_to_speed(months: Optional[float]) -> Optional[float]:
    """0..1 — faster follow-on funding round ⇒ tighter coordination."""
    if months is None:
        return None
    return round(1.0 / (1.0 + max(months, 0.0) / 12.0), 4)


def _shift_months(date_str: str, delta_months: int) -> str:
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d")
    except ValueError:
        return date_str
    month_index = d.year * 12 + (d.month - 1) + delta_months
    year, month = divmod(month_index, 12)
    month += 1
    day = min(d.day, 28)
    return f"{year:04d}-{month:02d}-{day:02d}"


# ── CLI ────────────────────────────────────────────────────────────────────

def _export_csv(db: Database, path: Path) -> int:
    import csv
    conn = sqlite3.connect(db.path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(f"SELECT * FROM {TABLE} ORDER BY decision_date").fetchall()
    finally:
        conn.close()
    if not rows:
        return 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(rows[0].keys())
        for r in rows:
            writer.writerow(list(r))
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the decision_dataset analysis table")
    ap.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite database path")
    ap.add_argument("--csv", default=None, help="Also export the table to a CSV file")
    args = ap.parse_args()

    db = Database(args.db)
    db.init_schema()
    n = build_decision_dataset(db)
    print(f"Built {TABLE}: {n:,} decision rows")

    conn = sqlite3.connect(db.path)
    try:
        by_entity = conn.execute(
            f"SELECT entity_type, COUNT(*) FROM {TABLE} GROUP BY entity_type"
        ).fetchall()
        by_type = conn.execute(
            f"SELECT decision_type, COUNT(*) AS n FROM {TABLE} GROUP BY decision_type ORDER BY n DESC"
        ).fetchall()
        with_outcome = conn.execute(
            f"SELECT COUNT(*) FROM {TABLE} WHERE primary_change_in_value IS NOT NULL"
        ).fetchone()[0]
    finally:
        conn.close()

    print("  by entity :", ", ".join(f"{e}={c}" for e, c in by_entity))
    print(f"  with measured outcome: {with_outcome:,}")
    print("  by decision_type:")
    for t, c in by_type:
        print(f"    {t:<16} {c:>5}")

    if args.csv:
        m = _export_csv(db, Path(args.csv))
        print(f"Exported {m:,} rows -> {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
