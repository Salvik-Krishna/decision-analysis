"""
CLI for the startup market database.

Commands
--------
init       Create / upgrade the SQLite schema (same DB as public-market data)
load       Seed the DB from the built-in startup registry (no network)
fetch      Load registry + scrape Google News events for one or more companies
analyze    Compute valuation reactions around events
report     Print summary tables

Examples
--------
python -m decision_analysis.startup_cli init
python -m decision_analysis.startup_cli load
python -m decision_analysis.startup_cli load --keys OPENAI STRIPE DATABRICKS
python -m decision_analysis.startup_cli fetch --keys OPENAI ANTHROPIC STRIPE
python -m decision_analysis.startup_cli fetch --sector "Artificial Intelligence"
python -m decision_analysis.startup_cli fetch --all --no-news
python -m decision_analysis.startup_cli analyze
python -m decision_analysis.startup_cli analyze --keys FTX KLARNA --event-types funding leadership
python -m decision_analysis.startup_cli report
python -m decision_analysis.startup_cli report --key STRIPE
python -m decision_analysis.startup_cli report --top-jumps
python -m decision_analysis.startup_cli report --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    package_root = Path(__file__).resolve().parent.parent
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

    from decision_analysis.data.startups import STARTUP_REGISTRY, startup_keys_for_sector, startup_sectors
    from decision_analysis.data.database import Database, DEFAULT_DB_PATH
    from decision_analysis.data.startup_scraper import StartupScraper
    from decision_analysis.data.startup_analysis import StartupAnalyzer
else:
    from .data.startups import STARTUP_REGISTRY, startup_keys_for_sector, startup_sectors
    from .data.database import Database, DEFAULT_DB_PATH
    from .data.startup_scraper import StartupScraper
    from .data.startup_analysis import StartupAnalyzer


# ── CLI builder ────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m decision_analysis.startup_cli",
        description="Startup valuation database CLI",
    )
    p.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to SQLite database")

    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create / upgrade database schema")

    # load (registry only, no network)
    ld = sub.add_parser("load", help="Seed DB from built-in registry (offline)")
    ld_group = ld.add_mutually_exclusive_group()
    ld_group.add_argument("--keys", nargs="+", metavar="KEY")
    ld_group.add_argument("--sector", metavar="SECTOR")
    ld_group.add_argument("--all", dest="load_all", action="store_true", default=True)
    ld.add_argument("--funding-events", action="store_true", default=True,
                    help="Also convert funding rounds to events (default: on)")

    # fetch (registry + live news)
    fe = sub.add_parser("fetch", help="Load registry + scrape news events")
    fe_group = fe.add_mutually_exclusive_group(required=True)
    fe_group.add_argument("--keys", nargs="+", metavar="KEY")
    fe_group.add_argument("--sector", metavar="SECTOR")
    fe_group.add_argument("--all", dest="fetch_all", action="store_true")
    fe.add_argument("--no-news", action="store_true", help="Skip Google News scraping")
    fe.add_argument("--throttle", type=float, default=2.0, metavar="SECS")

    # analyze
    an = sub.add_parser("analyze", help="Compute valuation reactions around events")
    an.add_argument("--keys", nargs="+", metavar="KEY")
    an.add_argument("--event-types", nargs="+", metavar="TYPE")

    # report
    rp = sub.add_parser("report", help="Print statistics and impact tables")
    rp.add_argument("--key", metavar="KEY", help="Focus on a single company")
    rp.add_argument("--top-jumps", action="store_true", help="Show top valuation jump events")
    rp.add_argument("--top-drops", action="store_true", help="Show top down-round events")
    rp.add_argument("--trajectory", metavar="KEY", help="Show funding trajectory for a company")
    rp.add_argument("--compare", metavar="EVENT_TYPE", default=None,
                    help="Cross-company ranking by valuation change for event type")
    rp.add_argument("--json", dest="as_json", action="store_true")

    return p


# ── Handlers ───────────────────────────────────────────────────────────────

def cmd_init(db: Database, _args) -> int:
    db.init_schema()
    print(f"Database ready: {db.path}")
    return 0


def cmd_load(db: Database, args) -> int:
    keys = _resolve_keys(args, db)
    scraper = StartupScraper(db)
    counts = scraper.load_registry(keys)
    total_rounds = sum(counts.values())
    if getattr(args, "funding_events", True):
        events = scraper.load_funding_as_events(keys)
        print(f"Loaded {len(keys)} companies, {total_rounds} funding rounds, {events} funding events.")
    else:
        print(f"Loaded {len(keys)} companies, {total_rounds} funding rounds.")
    return 0


def cmd_fetch(db: Database, args) -> int:
    keys = _resolve_keys(args, db)
    scraper = StartupScraper(db, throttle_seconds=args.throttle)
    results = scraper.fetch_all(
        company_keys=keys,
        include_news=not args.no_news,
    )
    total_rounds = sum(v["funding_rounds"] for v in results.values())
    total_news = sum(v["news_events"] for v in results.values())
    print(f"\nDone. Funding rounds loaded: {total_rounds}  |  News events: {total_news}")
    return 0


def cmd_analyze(db: Database, args) -> int:
    analyzer = StartupAnalyzer(db)
    keys = [k.upper() for k in args.keys] if args.keys else None
    etypes = args.event_types if args.event_types else None
    n = analyzer.compute_reactions(company_keys=keys, event_types=etypes)
    print(f"Computed {n} valuation reaction records.")
    return 0


def cmd_report(db: Database, args) -> int:
    analyzer = StartupAnalyzer(db)
    stats = db.summary_stats()

    if args.as_json:
        out: dict = {
            "db_stats": {
                "startups": stats["startups"],
                "funding_rounds": stats["funding_rounds"],
                "startup_events": stats["startup_events"],
                "valuation_reactions": stats["valuation_reactions"],
            }
        }
        if args.key:
            out["timeline"] = analyzer.company_timeline(args.key)
            out["funding_trajectory"] = analyzer.funding_trajectory(args.key)
        else:
            out["impact_by_event_type"] = analyzer.impact_by_event_type()
        if args.top_jumps:
            out["top_valuation_jumps"] = analyzer.biggest_valuation_jumps()
        if args.top_drops:
            out["top_valuation_drops"] = analyzer.biggest_valuation_drops()
        if args.compare:
            out["cross_company_comparison"] = analyzer.cross_company_comparison(args.compare)
        if args.trajectory:
            out["trajectory"] = analyzer.funding_trajectory(args.trajectory)
        print(json.dumps(out, indent=2))
        return 0

    # Human-readable
    print("=" * 65)
    print("STARTUP DATABASE SUMMARY")
    print("=" * 65)
    print(f"  Startups tracked  : {stats['startups']}")
    print(f"  Funding rounds    : {stats['funding_rounds']:,}")
    print(f"  Events            : {stats['startup_events']:,}")
    print(f"  Valuation reactions: {stats['valuation_reactions']:,}")

    impact = analyzer.impact_by_event_type(company_key=args.key)
    if impact:
        header = "\nVALUATION IMPACT BY EVENT TYPE"
        if args.key:
            header += f" — {args.key}"
        print(header)
        print("-" * 65)
        print(f"  {'Event type':<20} {'MeanΔVal%':>9}  {'StDev':>7}  {'N':>5}  {'%↑':>5}  {'Avg months':>10}")
        print(f"  {'-'*20}  {'-'*9}  {'-'*7}  {'-'*5}  {'-'*5}  {'-'*10}")
        for etype, v in impact.items():
            print(
                f"  {etype:<20} {v['mean_valuation_change_pct']:>+9.1f}  "
                f"{v['stdev_valuation_change_pct']:>7.1f}  "
                f"{v['count']:>5}  {v['positive_rate']*100:>4.0f}%  "
                f"{v['mean_months_to_next_round']:>10.1f}"
            )

    if args.key:
        tl = analyzer.company_timeline(args.key)
        if tl:
            print(f"\nEVENT TIMELINE — {args.key}")
            print("-" * 65)
            for row in tl:
                chg = row["valuation_change_pct"]
                chg_str = f"{chg:+.0f}%" if chg is not None else "  n/a"
                mo = row["months_to_next_round"]
                mo_str = f"{mo:.0f}mo" if mo else "  -"
                print(
                    f"  {row['date']}  {row['event_type']:<14} "
                    f"ΔVal={chg_str:>7}  next={mo_str:>5}  {row['title'][:38]}"
                )

        traj = analyzer.funding_trajectory(args.key)
        if traj:
            print(f"\nFUNDING TRAJECTORY — {args.key}")
            print("-" * 65)
            for r in traj:
                val = f"${r['valuation_usd']/1e9:.1f}B" if r["valuation_usd"] else "     n/a"
                amt = f"${r['amount_usd']/1e6:.0f}M" if r["amount_usd"] else "   n/a"
                cum = f"${r['cumulative_raised_usd']/1e6:.0f}M total"
                print(f"  {r['date']}  {r['round_type']:<15} {amt:>8}  val={val:>10}  {cum}")

    if args.top_jumps:
        jumps = analyzer.biggest_valuation_jumps()
        print(f"\nTOP {len(jumps)} VALUATION JUMPS AFTER AN EVENT")
        print("-" * 65)
        for j in jumps:
            print(
                f"  {j['company_key']:<20} {j['event_date']}  "
                f"+{j['valuation_change_pct']:.0f}%  [{j['event_type']}]  {j['title'][:35]}"
            )

    if args.top_drops:
        drops = analyzer.biggest_valuation_drops()
        print(f"\nTOP {len(drops)} VALUATION DROPS AFTER AN EVENT")
        print("-" * 65)
        for d in drops:
            print(
                f"  {d['company_key']:<20} {d['event_date']}  "
                f"{d['valuation_change_pct']:+.0f}%  [{d['event_type']}]  {d['title'][:35]}"
            )

    if args.compare:
        comp = analyzer.cross_company_comparison(args.compare)
        print(f"\nCROSS-COMPANY RANKING — event_type={args.compare}")
        print("-" * 65)
        for row in comp:
            print(
                f"  {row['name']:<28} {row[f'mean_valuation_change_pct']:>+7.1f}%  "
                f"n={row['count']}  [{row['sector']}]"
            )

    if args.trajectory:
        traj = analyzer.funding_trajectory(args.trajectory)
        if traj:
            print(f"\nFUNDING TRAJECTORY — {args.trajectory}")
            print("-" * 65)
            for r in traj:
                val = f"${r['valuation_usd']/1e9:.1f}B" if r["valuation_usd"] else "     n/a"
                amt = f"${r['amount_usd']/1e6:.0f}M" if r["amount_usd"] else "   n/a"
                print(f"  {r['date']}  {r['round_type']:<15} {amt:>8}  val={val:>10}  {r['lead_investor']}")

    return 0


# ── Helpers ────────────────────────────────────────────────────────────────

def _resolve_keys(args, db: Database):
    if getattr(args, "sector", None):
        keys = startup_keys_for_sector(args.sector)
        if not keys:
            print(f"Unknown sector '{args.sector}'. Available: {', '.join(startup_sectors())}")
            sys.exit(1)
        return keys
    if getattr(args, "keys", None):
        return [k.upper() for k in args.keys]
    return list(STARTUP_REGISTRY.keys())


# ── Entry point ────────────────────────────────────────────────────────────

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    db = Database(args.db)

    if args.command != "init" and not Path(args.db).exists():
        print(f"Database not found at {args.db}. Run 'init' first.")
        return 1

    return {
        "init": cmd_init,
        "load": cmd_load,
        "fetch": cmd_fetch,
        "analyze": cmd_analyze,
        "report": cmd_report,
    }[args.command](db, args)


if __name__ == "__main__":
    sys.exit(main())
