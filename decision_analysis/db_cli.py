"""
CLI for the market database.

Commands
--------
init       Create / upgrade the SQLite schema
fetch      Scrape prices + news events (yfinance; credibility-filtered)
edgar      Pull SEC 8-K filings (official; credibility = 1.0)
officers   Fetch current executive roster from yfinance
analyze    Compute price reactions around stored events
report     Print summary statistics and impact tables

Examples
--------
python -m decision_analysis.db_cli init
python -m decision_analysis.db_cli fetch --tickers AAPL MSFT
python -m decision_analysis.db_cli fetch --sector Technology
python -m decision_analysis.db_cli fetch --all

# EDGAR 8-K (best quality events — no API key needed)
python -m decision_analysis.db_cli edgar --tickers AAPL MSFT TSLA
python -m decision_analysis.db_cli edgar --sector Technology --start 2018-01-01
python -m decision_analysis.db_cli edgar --all

# Executive roster (current state + historical from 8-K)
python -m decision_analysis.db_cli officers --tickers AAPL MSFT
python -m decision_analysis.db_cli officers --all

python -m decision_analysis.db_cli analyze --tickers AAPL
python -m decision_analysis.db_cli report --impact-window 5
python -m decision_analysis.db_cli report --top-movers
python -m decision_analysis.db_cli report --ticker TSLA --leadership
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

if __package__ is None or __package__ == "":
    package_root = Path(__file__).resolve().parent.parent
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

    from decision_analysis.data.companies import COMPANY_REGISTRY, sectors, tickers_for_sector
    from decision_analysis.data.database import Database, DEFAULT_DB_PATH
    from decision_analysis.data.scraper import MarketScraper
    from decision_analysis.data.analysis import EventAnalyzer
    from decision_analysis.data.edgar import EDGARScraper
    from decision_analysis.data.leadership import LeadershipTracker
else:
    from .data.companies import COMPANY_REGISTRY, sectors, tickers_for_sector
    from .data.database import Database, DEFAULT_DB_PATH
    from .data.scraper import MarketScraper
    from .data.analysis import EventAnalyzer
    from .data.edgar import EDGARScraper
    from .data.leadership import LeadershipTracker


# ── CLI builder ────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m decision_analysis.db_cli",
        description="Market data database CLI",
    )
    p.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to SQLite database file")

    sub = p.add_subparsers(dest="command", required=True)

    # init
    sub.add_parser("init", help="Create / upgrade the database schema")

    # fetch
    f = sub.add_parser("fetch", help="Scrape and store price + event data")
    group = f.add_mutually_exclusive_group(required=True)
    group.add_argument("--tickers", nargs="+", metavar="TICKER", help="Specific ticker symbols")
    group.add_argument("--sector", metavar="SECTOR", help="All tickers in a sector")
    group.add_argument("--all", dest="fetch_all", action="store_true", help="All tracked companies")
    f.add_argument("--no-events", action="store_true", help="Skip news event scraping")
    f.add_argument("--no-earnings", action="store_true", help="Skip earnings event scraping")
    f.add_argument("--throttle", type=float, default=1.0, metavar="SECS",
                   help="Seconds to pause between tickers (default 1)")

    # edgar — SEC 8-K scraper
    eg = sub.add_parser("edgar", help="Pull SEC 8-K filings (credibility = 1.0)")
    eg_group = eg.add_mutually_exclusive_group(required=True)
    eg_group.add_argument("--tickers", nargs="+", metavar="TICKER")
    eg_group.add_argument("--sector", metavar="SECTOR")
    eg_group.add_argument("--all", dest="edgar_all", action="store_true")
    eg.add_argument("--start", default="2015-01-01", metavar="DATE",
                    help="Earliest filing date (default 2015-01-01)")
    eg.add_argument("--no-officers", action="store_true",
                    help="Skip fetching current officers from yfinance")
    eg.add_argument("--throttle", type=float, default=0.2, metavar="SECS",
                    help="Seconds between EDGAR requests (default 0.2)")
    eg.add_argument("--user-agent", default="", metavar="UA",
                    help="SEC User-Agent string (name + email). Overrides EDGAR_USER_AGENT env var.")

    # officers — executive roster
    off = sub.add_parser("officers", help="Fetch current executive roster")
    off_group = off.add_mutually_exclusive_group(required=True)
    off_group.add_argument("--tickers", nargs="+", metavar="TICKER")
    off_group.add_argument("--sector", metavar="SECTOR")
    off_group.add_argument("--all", dest="off_all", action="store_true")
    off.add_argument("--report", action="store_true",
                     help="Print leadership summary after fetching")

    # analyze
    a = sub.add_parser("analyze", help="Compute price reactions around events")
    a.add_argument("--tickers", nargs="+", metavar="TICKER")
    a.add_argument("--event-types", nargs="+", metavar="TYPE",
                   help="e.g. earnings acquisition leadership")
    a.add_argument("--min-credibility", type=float, default=0.0, metavar="SCORE",
                   help="Only use events with credibility >= SCORE (0.0–1.0)")

    # report
    r = sub.add_parser("report", help="Show statistics and impact tables")
    r.add_argument("--ticker", metavar="TICKER", help="Focus on a single company")
    r.add_argument("--impact-window", type=int, default=5, metavar="DAYS",
                   help="Post-event window in trading days (default 5)")
    r.add_argument("--top-movers", action="store_true",
                   help="Show the largest single-day moves after events")
    r.add_argument("--leadership", action="store_true",
                   help="Show leadership turnover and exec roster")
    r.add_argument("--min-credibility", type=float, default=0.0, metavar="SCORE",
                   help="Filter events to credibility >= SCORE")
    r.add_argument("--json", dest="as_json", action="store_true",
                   help="Output as JSON")

    return p


# ── Command handlers ───────────────────────────────────────────────────────

def cmd_init(db: Database, _args) -> int:
    db.init_schema()
    print(f"Database ready: {db.path}")
    return 0


def cmd_fetch(db: Database, args) -> int:
    # Resolve tickers
    if args.fetch_all:
        tickers = list(COMPANY_REGISTRY.keys())
    elif args.sector:
        tickers = tickers_for_sector(args.sector)
        if not tickers:
            print(f"Unknown sector '{args.sector}'.  Available: {', '.join(sectors())}")
            return 1
    else:
        tickers = [t.upper() for t in args.tickers]

    print(f"Fetching {len(tickers)} ticker(s)…")
    scraper = MarketScraper(db, throttle_seconds=args.throttle)
    results = scraper.fetch_all(
        tickers=tickers,
        include_events=not args.no_events,
        include_earnings=not args.no_earnings,
    )

    total_prices = sum(v["prices"] for v in results.values())
    total_events = sum(v["news_events"] + v["earnings_events"] for v in results.values())
    print(f"\nDone. New price rows: {total_prices}  |  New events: {total_events}")
    return 0


def cmd_edgar(db: Database, args) -> int:
    if args.edgar_all:
        tickers = list(COMPANY_REGISTRY.keys())
    elif args.sector:
        tickers = tickers_for_sector(args.sector)
        if not tickers:
            print(f"Unknown sector '{args.sector}'. Available: {', '.join(sectors())}")
            return 1
    else:
        tickers = [t.upper() for t in args.tickers]

    scraper = EDGARScraper(db, user_agent=args.user_agent, throttle=args.throttle)
    results = scraper.fetch_all(
        tickers=tickers,
        start=args.start,
        include_officers=not args.no_officers,
    )
    total_events = sum(v["8k_events"] for v in results.values())
    total_officers = sum(v["officers"] for v in results.values())
    print(f"\nDone. 8-K events stored: {total_events}  |  Officers fetched: {total_officers}")
    return 0


def cmd_officers(db: Database, args) -> int:
    if args.off_all:
        tickers = list(COMPANY_REGISTRY.keys())
    elif args.sector:
        tickers = tickers_for_sector(args.sector)
        if not tickers:
            print(f"Unknown sector '{args.sector}'. Available: {', '.join(sectors())}")
            return 1
    else:
        tickers = [t.upper() for t in args.tickers]

    scraper = EDGARScraper(db)
    total = 0
    for ticker in tickers:
        n = scraper.fetch_current_officers(ticker)
        print(f"  {ticker}: {n} officers")
        total += n

    if args.report:
        lt = LeadershipTracker(db)
        for ticker in tickers:
            roster = lt.current_roster(ticker)
            if roster:
                print(f"\n{ticker} current executives:")
                for e in roster:
                    pay = f"  pay=${e['total_pay']/1e6:.1f}M" if e.get("total_pay") else ""
                    print(f"  {e['title']:<40} {e['name']}{pay}")

    print(f"\nTotal officer records stored: {total}")
    return 0


def cmd_analyze(db: Database, args) -> int:
    analyzer = EventAnalyzer(db)
    tickers = [t.upper() for t in args.tickers] if args.tickers else None
    event_types = args.event_types if args.event_types else None
    n = analyzer.compute_reactions(tickers=tickers, event_types=event_types)
    print(f"Computed {n} price reaction data points.")
    return 0


def cmd_report(db: Database, args) -> int:
    analyzer = EventAnalyzer(db)
    stats = db.summary_stats()

    if args.as_json:
        out: dict = {"db_stats": stats}

        if args.top_movers:
            out["top_movers"] = analyzer.top_movers(window_days=1)

        impact = analyzer.impact_by_event_type(
            direction="post",
            window_days=args.impact_window,
            ticker=args.ticker,
        )
        out["impact_by_event_type"] = impact

        if args.ticker:
            out["company_events"] = analyzer.company_event_summary(
                args.ticker, window_days=args.impact_window
            )

        print(json.dumps(out, indent=2))
        return 0

    # Human-readable output
    print("=" * 60)
    print("DATABASE SUMMARY")
    print("=" * 60)
    print(f"  Companies   : {stats['companies']}")
    print(f"  Price rows  : {stats['price_rows']:,}")
    print(f"  Events      : {stats['events']:,}")
    print(f"  Reactions   : {stats['reactions']:,}")
    if stats["events_by_type"]:
        print("\n  Events by type:")
        for etype, n in stats["events_by_type"].items():
            print(f"    {etype:<20} {n:>5}")

    impact = analyzer.impact_by_event_type(
        direction="post",
        window_days=args.impact_window,
        ticker=args.ticker,
    )
    if impact:
        header = f"\nPRICE IMPACT (post-event, +{args.impact_window}d trading days)"
        if args.ticker:
            header += f" — {args.ticker}"
        print(header)
        print("-" * 60)
        print(f"  {'Event type':<22} {'Mean%':>7}  {'StDev%':>7}  {'N':>5}  {'%Pos':>6}")
        print(f"  {'-'*22}  {'-'*7}  {'-'*7}  {'-'*5}  {'-'*6}")
        for etype, vals in impact.items():
            print(
                f"  {etype:<22} {vals['mean_pct']:>+7.2f}  "
                f"{vals['stdev_pct']:>7.2f}  {vals['count']:>5}  "
                f"{vals['positive_rate']*100:>5.0f}%"
            )

    if args.top_movers:
        movers = analyzer.top_movers(window_days=1)
        print(f"\nTOP {len(movers)} SINGLE-DAY MOVERS (post-event +1d)")
        print("-" * 70)
        for m in movers:
            sign = "+" if (m["price_change_pct"] or 0) >= 0 else ""
            print(f"  {m['ticker']:<6} {m['event_date']}  {sign}{m['price_change_pct']:>+6.2f}%  "
                  f"[{m['event_type']}]  {m['title'][:45]}")

    if args.ticker:
        rows = analyzer.company_event_summary(args.ticker, window_days=args.impact_window)
        if rows:
            print(f"\nEVENT LOG — {args.ticker} (post +{args.impact_window}d)")
            print("-" * 70)
            for r in rows:
                chg = r["price_change_pct"]
                chg_str = f"{chg:+.2f}%" if chg is not None else "   n/a"
                src = r.get("source_domain", "")[:12]
                cred = r.get("credibility_score", 0)
                print(f"  {r['date']}  {r['event_type']:<15} {chg_str:>8}  "
                      f"[{src:<12} {cred:.1f}]  {r['title'][:35]}")

    if getattr(args, "leadership", False) and args.ticker:
        lt = LeadershipTracker(db)
        report = lt.company_leadership_report(args.ticker)
        print(f"\nLEADERSHIP — {args.ticker}")
        print("-" * 70)
        if report["current_roster"]:
            print("  Current executives:")
            for e in report["current_roster"]:
                pay = f"  ${e['total_pay']/1e6:.1f}M" if e.get("total_pay") else ""
                print(f"    {e['title']:<40} {e['name']}{pay}")
        to = report["turnover_since_2018"]
        print(f"\n  C-suite changes since 2018: {to['change_count']} "
              f"({to['annualised_rate']:.1f}/yr)")
        if to["events"]:
            for ev in to["events"][:10]:
                print(f"    {ev['date']}  {ev['title'][:55]}")

    return 0


# ── Entry point ────────────────────────────────────────────────────────────

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    db = Database(args.db)

    if args.command != "init":
        if not Path(args.db).exists():
            print(f"Database not found at {args.db}. Run 'init' first.")
            return 1

    dispatch = {
        "init": cmd_init,
        "fetch": cmd_fetch,
        "edgar": cmd_edgar,
        "officers": cmd_officers,
        "analyze": cmd_analyze,
        "report": cmd_report,
    }
    return dispatch[args.command](db, args)


if __name__ == "__main__":
    sys.exit(main())
