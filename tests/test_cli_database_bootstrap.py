"""Integration tests for the shared SQLite database used by both CLIs."""

from __future__ import annotations

import tempfile
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from decision_analysis.data.analysis import EventAnalyzer
from decision_analysis.data.database import Database
from decision_analysis.data.startup_scraper import StartupScraper


class CLIDatabaseBootstrapTests(unittest.TestCase):
    def test_shared_database_can_store_market_and_startup_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.sqlite"
            db = Database(db_path)
            db.init_schema()

            # Market side: one tracked company with an event and enough price
            # history for a one-day pre/post reaction pair.
            db.upsert_company(
                ticker="AAPL",
                name="Apple Inc.",
                sector="Technology",
                industry="Consumer Electronics",
                exchange="NASDAQ",
                country="US",
            )
            db.insert_prices([
                {
                    "ticker": "AAPL",
                    "date": "2024-01-01",
                    "open": 180.0,
                    "high": 182.0,
                    "low": 179.0,
                    "close": 181.0,
                    "adj_close": 181.0,
                    "volume": 100_000_000,
                },
                {
                    "ticker": "AAPL",
                    "date": "2024-01-02",
                    "open": 181.0,
                    "high": 183.0,
                    "low": 180.0,
                    "close": 182.0,
                    "adj_close": 182.0,
                    "volume": 101_000_000,
                },
                {
                    "ticker": "AAPL",
                    "date": "2024-01-03",
                    "open": 182.0,
                    "high": 184.0,
                    "low": 181.0,
                    "close": 183.0,
                    "adj_close": 183.0,
                    "volume": 102_000_000,
                },
            ])
            db.insert_event(
                ticker="AAPL",
                date="2024-01-02",
                event_type="product",
                title="Apple announces new hardware",
                description="Synthetic test event",
                source_url="https://example.com/apple",
                credibility_score=1.0,
                source_domain="example.com",
            )

            # Startup side: seed two companies from the built-in registry.
            startup_scraper = StartupScraper(db)
            counts = startup_scraper.load_registry(["OPENAI", "STRIPE"])
            self.assertEqual(counts["OPENAI"], 4)
            self.assertEqual(counts["STRIPE"], 8)
            self.assertEqual(startup_scraper.load_funding_as_events(["OPENAI", "STRIPE"]), 12)

            # Validate the market side reaction calculations.
            self.assertEqual(EventAnalyzer(db).compute_reactions(tickers=["AAPL"]), 2)

            stats = db.summary_stats()
            self.assertEqual(stats["companies"], 1)
            self.assertEqual(stats["events"], 1)
            self.assertEqual(stats["reactions"], 2)
            self.assertEqual(stats["startups"], 2)
            self.assertEqual(stats["funding_rounds"], 12)
            self.assertEqual(stats["startup_events"], 12)


if __name__ == "__main__":
    unittest.main()