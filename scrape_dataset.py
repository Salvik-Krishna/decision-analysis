"""
scrape_dataset.py — build the full real-data decision dataset, dependency-free.

Populates market_data.db for every company in COMPANY_REGISTRY using only the
Python standard library (no yfinance / pandas):

  - company metadata   : from the curated registry
  - daily price history : Yahoo Finance v8 chart API   (urllib)
  - corporate events    : SEC EDGAR 8-K filings         (urllib)
  - price reactions     : computed locally from stored prices + events

Run:
    python scrape_dataset.py                 # all 49 registry companies
    python scrape_dataset.py AAPL MSFT TSLA  # a subset
    python scrape_dataset.py --start 2015-01-01

Output: market_data.db in the project root (raw tables).  Build the flat
analysis table afterwards with:  python -m decision_analysis.data.dataset
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from decision_analysis.data.tls import configure_tls
from decision_analysis.data.database import Database
from decision_analysis.data.companies import COMPANY_REGISTRY
from decision_analysis.data.edgar import EDGARScraper
from decision_analysis.data.analysis import EventAnalyzer
from decision_analysis.data.yahoo_prices import YahooPriceFetcher

DB_PATH = Path(__file__).resolve().parent / "market_data.db"


def main() -> int:
    ap = argparse.ArgumentParser(description="Scrape the full real-data decision dataset")
    ap.add_argument("tickers", nargs="*", help="Specific tickers (default: whole registry)")
    ap.add_argument("--start", default="2018-01-01", help="History / filing start date")
    ap.add_argument("--db", default=str(DB_PATH), help="SQLite database path")
    ap.add_argument("--ua", default="decision-analysis research salvikknautiyal@gmail.com",
                    help="SEC EDGAR User-Agent (name + email, per SEC policy)")
    ap.add_argument("--skip-prices", action="store_true")
    ap.add_argument("--skip-events", action="store_true")
    ap.add_argument("--skip-reactions", action="store_true")
    args = ap.parse_args()

    ctx = configure_tls()
    print(f"TLS CA bundle: {Path(__import__('os').environ.get('SSL_CERT_FILE','<default>')).name}")

    tickers = [t.upper() for t in args.tickers] or list(COMPANY_REGISTRY.keys())
    db = Database(args.db)
    db.init_schema()
    print(f"Schema ready -> {Path(args.db).name}")
    print(f"Companies to process: {len(tickers)}\n")

    # 1. Company metadata (from curated registry; no network needed) ──────────
    for ticker in tickers:
        meta = COMPANY_REGISTRY.get(ticker, {})
        db.upsert_company(
            ticker=ticker,
            name=meta.get("name", ticker),
            sector=meta.get("sector"),
            industry=meta.get("industry"),
            exchange=meta.get("exchange"),
            country="United States",
        )
    print(f"[1/4] {len(tickers)} company records upserted\n")

    # 2. Prices (Yahoo v8 chart API) ──────────────────────────────────────────
    if not args.skip_prices:
        pf = YahooPriceFetcher(db, ssl_context=ctx, throttle=0.4)
        total_px = 0
        for i, ticker in enumerate(tickers, 1):
            n = pf.fetch_prices(ticker, start=args.start)
            total_px += n
            print(f"  [{i:>2}/{len(tickers)}] {ticker:<6} prices +{n}")
        print(f"[2/4] Prices done — {total_px:,} new rows\n")

    # 3. Events (SEC EDGAR 8-K) ────────────────────────────────────────────────
    if not args.skip_events:
        edgar = EDGARScraper(db, user_agent=args.ua, throttle=0.2)
        total_ev = 0
        for i, ticker in enumerate(tickers, 1):
            try:
                n = edgar.fetch_8k_events(ticker, start=args.start)
            except Exception as exc:  # noqa: BLE001
                print(f"  [{i:>2}/{len(tickers)}] {ticker:<6} EDGAR error: {exc}")
                n = 0
            total_ev += n
            print(f"  [{i:>2}/{len(tickers)}] {ticker:<6} 8-K events +{n}")
            time.sleep(0.1)
        print(f"[3/4] EDGAR events done — {total_ev:,} events\n")

    # 4. Price reactions ───────────────────────────────────────────────────────
    if not args.skip_reactions:
        ea = EventAnalyzer(db)
        n_rx = ea.compute_reactions(tickers=tickers)
        print(f"[4/4] Price reactions computed — {n_rx:,} data points\n")

    # Summary ──────────────────────────────────────────────────────────────────
    stats = db.summary_stats()
    print("=" * 56)
    print("RAW DATASET SUMMARY")
    print("=" * 56)
    for k in ("companies", "price_rows", "events", "reactions",
              "startups", "funding_rounds", "startup_events", "valuation_reactions"):
        print(f"  {k:<22} {stats[k]:,}")
    if stats["events_by_type"]:
        print("\n  Events by type:")
        for etype, n in stats["events_by_type"].items():
            print(f"    {etype:<16} {n:>5}  {'#' * min(n, 40)}")
    print(f"\nDatabase saved -> {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
