"""SQLite database schema and CRUD operations for market data."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, List, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "market_data.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    ticker      TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    sector      TEXT,
    industry    TEXT,
    exchange    TEXT,
    country     TEXT,
    market_cap  REAL,
    description TEXT,
    fetched_at  TEXT
);

CREATE TABLE IF NOT EXISTS prices (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker    TEXT NOT NULL,
    date      TEXT NOT NULL,
    open      REAL,
    high      REAL,
    low       REAL,
    close     REAL,
    adj_close REAL,
    volume    INTEGER,
    UNIQUE(ticker, date),
    FOREIGN KEY(ticker) REFERENCES companies(ticker)
);

CREATE TABLE IF NOT EXISTS events (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker            TEXT NOT NULL,
    date              TEXT NOT NULL,
    event_type        TEXT NOT NULL,
    title             TEXT NOT NULL,
    description       TEXT,
    source_url        TEXT,
    credibility_score REAL DEFAULT 0.5,
    source_domain     TEXT DEFAULT 'unknown',
    fetched_at        TEXT,
    FOREIGN KEY(ticker) REFERENCES companies(ticker)
);

CREATE TABLE IF NOT EXISTS cik_cache (
    ticker     TEXT PRIMARY KEY,
    cik        TEXT NOT NULL,
    name       TEXT,
    cached_at  TEXT
);

CREATE TABLE IF NOT EXISTS executives (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker      TEXT NOT NULL,
    name        TEXT NOT NULL,
    title       TEXT,
    start_date  TEXT,
    end_date    TEXT,
    is_current  INTEGER DEFAULT 0,
    total_pay   REAL,
    source      TEXT,
    fetched_at  TEXT,
    FOREIGN KEY(ticker) REFERENCES companies(ticker)
);

CREATE TABLE IF NOT EXISTS price_reactions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id          INTEGER NOT NULL,
    ticker            TEXT NOT NULL,
    window_days       INTEGER NOT NULL,
    direction         TEXT NOT NULL,
    price_change_pct  REAL,
    volume_change_pct REAL,
    computed_at       TEXT,
    UNIQUE(event_id, window_days, direction),
    FOREIGN KEY(event_id) REFERENCES events(id)
);

CREATE INDEX IF NOT EXISTS idx_prices_ticker_date  ON prices(ticker, date);
CREATE INDEX IF NOT EXISTS idx_events_ticker_date  ON events(ticker, date);
CREATE INDEX IF NOT EXISTS idx_events_type         ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_credibility  ON events(credibility_score);
CREATE INDEX IF NOT EXISTS idx_reactions_event     ON price_reactions(event_id);
CREATE INDEX IF NOT EXISTS idx_execs_ticker        ON executives(ticker, start_date);

-- ── Startup tables ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS startups (
    company_key  TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    sector       TEXT,
    industry     TEXT,
    founded      INTEGER,
    country      TEXT,
    hq_city      TEXT,
    description  TEXT,
    total_funding_usd REAL,
    latest_valuation_usd REAL,
    latest_round_type TEXT,
    latest_round_date TEXT
);

CREATE TABLE IF NOT EXISTS funding_rounds (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_key  TEXT NOT NULL,
    date         TEXT NOT NULL,
    round_type   TEXT NOT NULL,
    amount_usd   REAL,
    valuation_usd REAL,
    lead_investor TEXT,
    UNIQUE(company_key, date, round_type),
    FOREIGN KEY(company_key) REFERENCES startups(company_key)
);

CREATE TABLE IF NOT EXISTS startup_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_key  TEXT NOT NULL,
    date         TEXT NOT NULL,
    event_type   TEXT NOT NULL,
    title        TEXT NOT NULL,
    description  TEXT,
    source_url   TEXT,
    fetched_at   TEXT,
    FOREIGN KEY(company_key) REFERENCES startups(company_key)
);

CREATE TABLE IF NOT EXISTS valuation_reactions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id              INTEGER NOT NULL,
    company_key           TEXT NOT NULL,
    prev_round_id         INTEGER,
    next_round_id         INTEGER,
    months_to_next_round  REAL,
    valuation_change_pct  REAL,
    amount_change_pct     REAL,
    round_type_after      TEXT,
    computed_at           TEXT,
    FOREIGN KEY(event_id)      REFERENCES startup_events(id),
    FOREIGN KEY(prev_round_id) REFERENCES funding_rounds(id),
    FOREIGN KEY(next_round_id) REFERENCES funding_rounds(id)
);

CREATE INDEX IF NOT EXISTS idx_funding_company   ON funding_rounds(company_key, date);
CREATE INDEX IF NOT EXISTS idx_sevents_company   ON startup_events(company_key, date);
CREATE INDEX IF NOT EXISTS idx_sevents_type      ON startup_events(event_type);
CREATE INDEX IF NOT EXISTS idx_vreactions_event  ON valuation_reactions(event_id);
"""


class Database:
    def __init__(self, path: Path | str = DEFAULT_DB_PATH) -> None:
        self.path = Path(path)

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            # Migrate existing events table (columns added in v2)
            for col, definition in [
                ("credibility_score", "REAL DEFAULT 0.5"),
                ("source_domain",     "TEXT DEFAULT 'unknown'"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE events ADD COLUMN {col} {definition}")
                except sqlite3.OperationalError:
                    pass  # column already exists

    # ── Companies ──────────────────────────────────────────────────────────

    def upsert_company(self, ticker: str, name: str, **kwargs) -> None:
        fields = {"ticker": ticker, "name": name, "fetched_at": _now(), **kwargs}
        cols = ", ".join(fields)
        placeholders = ", ".join(["?"] * len(fields))
        updates = ", ".join(f"{k}=excluded.{k}" for k in fields if k != "ticker")
        sql = f"""
            INSERT INTO companies ({cols}) VALUES ({placeholders})
            ON CONFLICT(ticker) DO UPDATE SET {updates}
        """
        with self._connect() as conn:
            conn.execute(sql, list(fields.values()))

    def get_company(self, ticker: str) -> Optional[sqlite3.Row]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM companies WHERE ticker=?", (ticker,)
            ).fetchone()
        return row

    def list_companies(self) -> List[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM companies ORDER BY ticker").fetchall()

    # ── Prices ─────────────────────────────────────────────────────────────

    def insert_prices(self, rows: List[dict]) -> int:
        if not rows:
            return 0
        sql = """
            INSERT OR IGNORE INTO prices
                (ticker, date, open, high, low, close, adj_close, volume)
            VALUES
                (:ticker, :date, :open, :high, :low, :close, :adj_close, :volume)
        """
        with self._connect() as conn:
            conn.executemany(sql, rows)
            return conn.execute("SELECT changes()").fetchone()[0]

    def get_prices(
        self,
        ticker: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> List[sqlite3.Row]:
        sql = "SELECT * FROM prices WHERE ticker=?"
        params: list = [ticker]
        if start:
            sql += " AND date>=?"
            params.append(start)
        if end:
            sql += " AND date<=?"
            params.append(end)
        sql += " ORDER BY date"
        with self._connect() as conn:
            return conn.execute(sql, params).fetchall()

    def latest_price_date(self, ticker: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT MAX(date) FROM prices WHERE ticker=?", (ticker,)
            ).fetchone()
        return row[0] if row else None

    # ── Events ─────────────────────────────────────────────────────────────

    def insert_event(
        self,
        ticker: str,
        date: str,
        event_type: str,
        title: str,
        description: str = "",
        source_url: str = "",
        credibility_score: float = 0.5,
        source_domain: str = "unknown",
    ) -> int:
        # Deduplicate: same ticker + date + event_type + first-60-chars of title
        title_key = title[:60]
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM events WHERE ticker=? AND date=? AND event_type=? AND title LIKE ?",
                (ticker, date, event_type, title_key + "%"),
            ).fetchone()
            if existing:
                return existing["id"]

            sql = """
                INSERT INTO events
                    (ticker, date, event_type, title, description, source_url,
                     credibility_score, source_domain, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cur = conn.execute(sql, (
                ticker, date, event_type, title, description, source_url,
                credibility_score, source_domain, _now(),
            ))
            return cur.lastrowid

    def get_events(
        self,
        ticker: Optional[str] = None,
        event_type: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        min_credibility: float = 0.0,
    ) -> List[sqlite3.Row]:
        sql = "SELECT * FROM events WHERE 1=1"
        params: list = []
        if ticker:
            sql += " AND ticker=?"
            params.append(ticker)
        if event_type:
            sql += " AND event_type=?"
            params.append(event_type)
        if start:
            sql += " AND date>=?"
            params.append(start)
        if end:
            sql += " AND date<=?"
            params.append(end)
        if min_credibility > 0:
            sql += " AND credibility_score>=?"
            params.append(min_credibility)
        sql += " ORDER BY date"
        with self._connect() as conn:
            return conn.execute(sql, params).fetchall()

    # ── Price reactions ────────────────────────────────────────────────────

    def upsert_reaction(
        self,
        event_id: int,
        ticker: str,
        window_days: int,
        direction: str,
        price_change_pct: Optional[float],
        volume_change_pct: Optional[float],
    ) -> None:
        sql = """
            INSERT INTO price_reactions
                (event_id, ticker, window_days, direction, price_change_pct, volume_change_pct, computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id, window_days, direction) DO UPDATE SET
                price_change_pct=excluded.price_change_pct,
                volume_change_pct=excluded.volume_change_pct,
                computed_at=excluded.computed_at
        """
        with self._connect() as conn:
            conn.execute(
                sql,
                (event_id, ticker, window_days, direction, price_change_pct, volume_change_pct, _now()),
            )

    def get_reactions(
        self,
        ticker: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> List[sqlite3.Row]:
        sql = """
            SELECT r.*, e.event_type, e.title, e.date AS event_date
            FROM price_reactions r
            JOIN events e ON r.event_id = e.id
            WHERE 1=1
        """
        params: list = []
        if ticker:
            sql += " AND r.ticker=?"
            params.append(ticker)
        if event_type:
            sql += " AND e.event_type=?"
            params.append(event_type)
        sql += " ORDER BY e.date, r.window_days"
        with self._connect() as conn:
            return conn.execute(sql, params).fetchall()

    def summary_stats(self) -> dict:
        with self._connect() as conn:
            companies = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
            prices = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
            events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            reactions = conn.execute("SELECT COUNT(*) FROM price_reactions").fetchone()[0]
            by_type = conn.execute(
                "SELECT event_type, COUNT(*) as n FROM events GROUP BY event_type ORDER BY n DESC"
            ).fetchall()
            startups = conn.execute("SELECT COUNT(*) FROM startups").fetchone()[0]
            funding = conn.execute("SELECT COUNT(*) FROM funding_rounds").fetchone()[0]
            s_events = conn.execute("SELECT COUNT(*) FROM startup_events").fetchone()[0]
            v_reactions = conn.execute("SELECT COUNT(*) FROM valuation_reactions").fetchone()[0]
        return {
            "companies": companies,
            "price_rows": prices,
            "events": events,
            "reactions": reactions,
            "events_by_type": {r["event_type"]: r["n"] for r in by_type},
            "startups": startups,
            "funding_rounds": funding,
            "startup_events": s_events,
            "valuation_reactions": v_reactions,
        }

    # ── Startup CRUD ───────────────────────────────────────────────────────

    def upsert_startup(self, company_key: str, name: str, **kwargs) -> None:
        fields = {"company_key": company_key, "name": name, **kwargs}
        cols = ", ".join(fields)
        placeholders = ", ".join(["?"] * len(fields))
        updates = ", ".join(f"{k}=excluded.{k}" for k in fields if k != "company_key")
        sql = f"""
            INSERT INTO startups ({cols}) VALUES ({placeholders})
            ON CONFLICT(company_key) DO UPDATE SET {updates}
        """
        with self._connect() as conn:
            conn.execute(sql, list(fields.values()))

    def get_startup(self, company_key: str) -> Optional[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM startups WHERE company_key=?", (company_key,)
            ).fetchone()

    def list_startups(self) -> List[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM startups ORDER BY company_key").fetchall()

    # ── Funding rounds ─────────────────────────────────────────────────────

    def upsert_funding_round(
        self,
        company_key: str,
        date: str,
        round_type: str,
        amount_usd: Optional[float] = None,
        valuation_usd: Optional[float] = None,
        lead_investor: str = "",
    ) -> int:
        sql = """
            INSERT INTO funding_rounds (company_key, date, round_type, amount_usd, valuation_usd, lead_investor)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(company_key, date, round_type) DO UPDATE SET
                amount_usd=excluded.amount_usd,
                valuation_usd=excluded.valuation_usd,
                lead_investor=excluded.lead_investor
        """
        with self._connect() as conn:
            conn.execute(sql, (company_key, date, round_type, amount_usd, valuation_usd, lead_investor))
            return conn.execute(
                "SELECT id FROM funding_rounds WHERE company_key=? AND date=? AND round_type=?",
                (company_key, date, round_type),
            ).fetchone()[0]

    def get_funding_rounds(self, company_key: str) -> List[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM funding_rounds WHERE company_key=? ORDER BY date",
                (company_key,),
            ).fetchall()

    # ── Startup events ─────────────────────────────────────────────────────

    def insert_startup_event(
        self,
        company_key: str,
        date: str,
        event_type: str,
        title: str,
        description: str = "",
        source_url: str = "",
    ) -> int:
        sql = """
            INSERT INTO startup_events
                (company_key, date, event_type, title, description, source_url, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        with self._connect() as conn:
            cur = conn.execute(
                sql, (company_key, date, event_type, title, description, source_url, _now())
            )
            return cur.lastrowid

    def get_startup_events(
        self,
        company_key: Optional[str] = None,
        event_type: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> List[sqlite3.Row]:
        sql = "SELECT * FROM startup_events WHERE 1=1"
        params: list = []
        if company_key:
            sql += " AND company_key=?"
            params.append(company_key)
        if event_type:
            sql += " AND event_type=?"
            params.append(event_type)
        if start:
            sql += " AND date>=?"
            params.append(start)
        if end:
            sql += " AND date<=?"
            params.append(end)
        sql += " ORDER BY date"
        with self._connect() as conn:
            return conn.execute(sql, params).fetchall()

    # ── Valuation reactions ────────────────────────────────────────────────

    def upsert_valuation_reaction(
        self,
        event_id: int,
        company_key: str,
        prev_round_id: Optional[int],
        next_round_id: Optional[int],
        months_to_next_round: Optional[float],
        valuation_change_pct: Optional[float],
        amount_change_pct: Optional[float],
        round_type_after: Optional[str],
    ) -> None:
        sql = """
            INSERT INTO valuation_reactions
                (event_id, company_key, prev_round_id, next_round_id,
                 months_to_next_round, valuation_change_pct, amount_change_pct,
                 round_type_after, computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT DO NOTHING
        """
        with self._connect() as conn:
            conn.execute(sql, (
                event_id, company_key, prev_round_id, next_round_id,
                months_to_next_round, valuation_change_pct, amount_change_pct,
                round_type_after, _now(),
            ))

    def get_valuation_reactions(
        self,
        company_key: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> List[sqlite3.Row]:
        sql = """
            SELECT vr.*, se.event_type, se.title, se.date AS event_date
            FROM valuation_reactions vr
            JOIN startup_events se ON vr.event_id = se.id
            WHERE 1=1
        """
        params: list = []
        if company_key:
            sql += " AND vr.company_key=?"
            params.append(company_key)
        if event_type:
            sql += " AND se.event_type=?"
            params.append(event_type)
        sql += " ORDER BY se.date"
        with self._connect() as conn:
            return conn.execute(sql, params).fetchall()


    # ── CIK cache ──────────────────────────────────────────────────────────

    def get_cik(self, ticker: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT cik FROM cik_cache WHERE ticker=?", (ticker,)
            ).fetchone()
        return row["cik"] if row else None

    def cache_cik(self, ticker: str, cik: str, name: str = "") -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO cik_cache (ticker, cik, name, cached_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(ticker) DO UPDATE SET cik=excluded.cik, cached_at=excluded.cached_at""",
                (ticker, cik, name, _now()),
            )

    # ── Executives ─────────────────────────────────────────────────────────

    def upsert_executive(
        self,
        ticker: str,
        name: str,
        title: str = "",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_current: bool = False,
        total_pay: Optional[float] = None,
        source: str = "",
    ) -> None:
        # If a current-source record exists for same ticker+name, update it
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM executives WHERE ticker=? AND name=? AND (end_date IS NULL OR is_current=1)",
                (ticker, name),
            ).fetchone()
            if existing:
                conn.execute(
                    """UPDATE executives SET title=?, is_current=?, total_pay=?,
                       source=?, fetched_at=?
                       WHERE id=?""",
                    (title, int(is_current), total_pay, source, _now(), existing["id"]),
                )
            else:
                conn.execute(
                    """INSERT INTO executives
                           (ticker, name, title, start_date, end_date, is_current, total_pay, source, fetched_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (ticker, name, title, start_date, end_date, int(is_current),
                     total_pay, source, _now()),
                )

    def close_executive_tenure(self, ticker: str, name: str, end_date: str) -> None:
        """Mark an active executive record as departed."""
        with self._connect() as conn:
            conn.execute(
                """UPDATE executives SET end_date=?, is_current=0
                   WHERE ticker=? AND name LIKE ? AND end_date IS NULL""",
                (end_date, ticker, f"%{name}%"),
            )

    def get_executives(
        self,
        ticker: Optional[str] = None,
        current_only: bool = False,
    ) -> List[sqlite3.Row]:
        sql = "SELECT * FROM executives WHERE 1=1"
        params: list = []
        if ticker:
            sql += " AND ticker=?"
            params.append(ticker)
        if current_only:
            sql += " AND (is_current=1 OR end_date IS NULL)"
        sql += " ORDER BY start_date DESC"
        with self._connect() as conn:
            return conn.execute(sql, params).fetchall()

    def get_executives_at_date(
        self, ticker: str, date: str
    ) -> List[sqlite3.Row]:
        sql = """
            SELECT * FROM executives
            WHERE ticker=?
              AND (start_date IS NULL OR start_date <= ?)
              AND (end_date IS NULL OR end_date > ?)
            ORDER BY start_date
        """
        with self._connect() as conn:
            return conn.execute(sql, (ticker, date, date)).fetchall()


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")
