"""
seed_database.py — fetch real market data for 2 public companies + 2 startups.

Run:
    python seed_database.py

Sources used:
  - yfinance          : live prices, company metadata, news headlines
  - SEC EDGAR API     : 8-K filings (official events, no API key, 1.0 credibility)
  - Built-in registry : startup funding rounds (OpenAI, Stripe)

Output: market_data.db in the project root
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yfinance as yf

from decision_analysis.data.database import Database
from decision_analysis.data.edgar import EDGARScraper
from decision_analysis.data.scraper import MarketScraper
from decision_analysis.data.analysis import EventAnalyzer
from decision_analysis.data.startup_scraper import StartupScraper
from decision_analysis.data.startup_analysis import StartupAnalyzer
from decision_analysis.data.leadership import LeadershipTracker

DB_PATH = Path(__file__).resolve().parent / "market_data.db"

# ── Companies and startups to seed ────────────────────────────────────────
PUBLIC_TICKERS  = ["AAPL", "MSFT"]
STARTUP_KEYS    = ["OPENAI", "STRIPE"]
HISTORY_START   = "2018-01-01"   # price history start
EDGAR_START     = "2018-01-01"   # 8-K events start

# ══════════════════════════════════════════════════════════════════════════
# 1. Schema
# ══════════════════════════════════════════════════════════════════════════

db = Database(DB_PATH)
db.init_schema()
print(f"\n[1/6] Schema ready → {DB_PATH.name}\n")

# ══════════════════════════════════════════════════════════════════════════
# 2. Fetch real company metadata + prices + news from yfinance
# ══════════════════════════════════════════════════════════════════════════

ms = MarketScraper(db, throttle_seconds=1.0)

for ticker in PUBLIC_TICKERS:
    print(f"── {ticker}: fetching metadata from yfinance…")
    ok = ms.fetch_company(ticker)
    if not ok:
        print(f"   [warn] metadata unavailable, skipping {ticker}")
        continue

    comp = db.get_company(ticker)
    print(f"   {comp['name']}  |  sector: {comp['sector']}  |  mktcap: "
          f"${(comp['market_cap'] or 0)/1e12:.2f}T")

    print(f"── {ticker}: fetching price history from {HISTORY_START}…")
    n_prices = ms.fetch_prices(ticker, start=HISTORY_START)
    print(f"   {n_prices:,} new price rows inserted")

    print(f"── {ticker}: fetching news events (credibility-filtered)…")
    n_news = ms.fetch_events(ticker)
    print(f"   {n_news} news events stored (trusted sources only)")

    print(f"── {ticker}: fetching earnings dates…")
    n_earn = ms.fetch_earnings_events(ticker)
    print(f"   {n_earn} earnings events stored")

    print()
    time.sleep(1)

print("[2/6] yfinance data fetched\n")

# ══════════════════════════════════════════════════════════════════════════
# 3. Fetch current executive roster from yfinance
# ══════════════════════════════════════════════════════════════════════════

edgar = EDGARScraper(db, throttle=0.25)

for ticker in PUBLIC_TICKERS:
    print(f"── {ticker}: fetching current officers from yfinance…")
    n_off = edgar.fetch_current_officers(ticker)
    print(f"   {n_off} officer records stored")

print("\n[3/6] Executive rosters fetched\n")

# ══════════════════════════════════════════════════════════════════════════
# 4. Fetch SEC EDGAR 8-K filings (official events, credibility = 1.0)
# ══════════════════════════════════════════════════════════════════════════

for ticker in PUBLIC_TICKERS:
    print(f"── {ticker}: fetching SEC EDGAR 8-K filings from {EDGAR_START}…")
    try:
        n_8k = edgar.fetch_8k_events(ticker, start=EDGAR_START)
        print(f"   {n_8k} 8-K events stored (earnings, leadership, restructuring, deals, etc.)")
    except Exception as exc:
        print(f"   [error] EDGAR fetch failed: {exc}")
    print()

print("[4/6] EDGAR 8-K events fetched\n")

# ══════════════════════════════════════════════════════════════════════════
# 5. Load startup data (OpenAI + Stripe)
# ══════════════════════════════════════════════════════════════════════════

ss = StartupScraper(db, throttle_seconds=2.0)

print("── Loading startup funding rounds from built-in registry…")
round_counts = ss.load_registry(STARTUP_KEYS)
ss.load_funding_as_events(STARTUP_KEYS)

for key, n in round_counts.items():
    startup = db.get_startup(key)
    latest_val = startup["latest_valuation_usd"]
    val_str = f"${latest_val/1e9:.0f}B" if latest_val else "undisclosed"
    total = startup["total_funding_usd"]
    total_str = f"${total/1e9:.1f}B raised" if total else ""
    print(f"   {startup['name']:<20} {n} rounds  |  latest val: {val_str}  |  {total_str}")

print()
print("── Scraping startup news from Google News RSS…")
for key in STARTUP_KEYS:
    try:
        n_news = ss.fetch_news_events(key)
        print(f"   {key}: {n_news} news events scraped")
    except Exception as exc:
        print(f"   {key}: news scrape failed ({exc})")
    time.sleep(2)

print("\n[5/6] Startup data loaded\n")

# ══════════════════════════════════════════════════════════════════════════
# 6. Compute reactions
# ══════════════════════════════════════════════════════════════════════════

print("── Computing stock price reactions around events (AAPL + MSFT)…")
ea = EventAnalyzer(db)
n_price_rx = ea.compute_reactions(tickers=PUBLIC_TICKERS)
print(f"   {n_price_rx} price reaction records")

print("── Computing valuation reactions around events (OpenAI + Stripe)…")
sa = StartupAnalyzer(db)
n_val_rx = sa.compute_reactions(company_keys=STARTUP_KEYS)
print(f"   {n_val_rx} valuation reaction records")

print(f"\n[6/6] Reactions computed\n")

# ══════════════════════════════════════════════════════════════════════════
# Summary report
# ══════════════════════════════════════════════════════════════════════════

stats = db.summary_stats()

print("═" * 65)
print("DATABASE SUMMARY")
print("═" * 65)
print(f"  Public companies   : {stats['companies']}")
print(f"  Price rows         : {stats['price_rows']:,}")
print(f"  Events (public)    : {stats['events']:,}")
print(f"  Price reactions    : {stats['reactions']:,}")
print(f"  Startups           : {stats['startups']}")
print(f"  Funding rounds     : {stats['funding_rounds']:,}")
print(f"  Startup events     : {stats['startup_events']:,}")
print(f"  Valuation reactions: {stats['valuation_reactions']:,}")

if stats["events_by_type"]:
    print("\n  Events by type (public companies):")
    for etype, n in stats["events_by_type"].items():
        bar = "█" * min(n, 30)
        print(f"    {etype:<22} {n:>4}  {bar}")

# Price impact table
impact = ea.impact_by_event_type(direction="post", window_days=5)
if impact:
    print("\n  Stock price impact: mean % change in 5 trading days after event")
    print(f"  {'Event type':<22} {'Mean Δ%':>8}  {'StDev':>6}  {'N':>4}  {'% Up':>5}  Source")
    print(f"  {'-'*22}  {'-'*8}  {'-'*6}  {'-'*4}  {'-'*5}  ------")
    for etype, v in impact.items():
        print(f"  {etype:<22} {v['mean_pct']:>+8.2f}  {v['stdev_pct']:>6.2f}  "
              f"{v['count']:>4}  {v['positive_rate']*100:>4.0f}%")

# Leadership summary
print()
lt = LeadershipTracker(db)
for ticker in PUBLIC_TICKERS:
    roster = lt.current_roster(ticker)
    comp = db.get_company(ticker)
    if roster:
        print(f"  {comp['name']} — current executives ({len(roster)}):")
        for e in roster[:5]:
            pay = f"  ${e['total_pay']/1e6:.1f}M" if e.get("total_pay") else ""
            print(f"    {e['title']:<42} {e['name']}{pay}")
        if len(roster) > 5:
            print(f"    … and {len(roster)-5} more")
        print()

# Startup valuation impact
val_impact = sa.impact_by_event_type()
if val_impact:
    print("  Startup valuation change after each event type:")
    print(f"  {'Event type':<22} {'Mean ΔVal%':>10}  {'Avg months to next round':>24}  N")
    print(f"  {'-'*22}  {'-'*10}  {'-'*24}  -")
    for etype, v in val_impact.items():
        print(f"  {etype:<22} {v['mean_valuation_change_pct']:>+10.1f}%  "
              f"{v['mean_months_to_next_round']:>24.1f}  {v['count']}")

# Startup funding trajectories
for key in STARTUP_KEYS:
    traj = sa.funding_trajectory(key)
    startup = db.get_startup(key)
    if traj:
        print(f"\n  {startup['name']} funding trajectory:")
        print(f"  {'Date':<12} {'Round':<16} {'Raised':>9}  {'Valuation':>12}  Lead investor")
        print(f"  {'-'*12}  {'-'*16}  {'-'*9}  {'-'*12}  -------------")
        for r in traj:
            amt = f"${r['amount_usd']/1e6:.0f}M" if r["amount_usd"] else "      n/a"
            val = f"${r['valuation_usd']/1e9:.1f}B" if r["valuation_usd"] else "         n/a"
            print(f"  {r['date']:<12}  {r['round_type']:<16}  {amt:>9}  {val:>12}  {r['lead_investor']}")

print(f"\nDatabase saved → {DB_PATH}")
