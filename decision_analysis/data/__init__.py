"""
Market data layer.

Public companies  : MarketScraper (yfinance prices) + EDGARScraper (8-K filings)
Startups          : StartupScraper (funding registry + Google News)
Analysis          : EventAnalyzer (price reactions), StartupAnalyzer (valuation reactions)
Leadership        : LeadershipTracker (executive roster + turnover)
"""

from importlib import import_module

from .database import Database

__all__ = [
    "Database",
    "MarketScraper",
    "EventAnalyzer",
    "EDGARScraper",
    "LeadershipTracker",
    "StartupScraper",
    "StartupAnalyzer",
]


def __getattr__(name: str):
    lazy_modules = {
        "MarketScraper": ".scraper",
        "EventAnalyzer": ".analysis",
        "EDGARScraper": ".edgar",
        "LeadershipTracker": ".leadership",
        "StartupScraper": ".startup_scraper",
        "StartupAnalyzer": ".startup_analysis",
    }
    module_name = lazy_modules.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
