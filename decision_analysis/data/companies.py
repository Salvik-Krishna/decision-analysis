"""Curated list of publicly traded companies to track."""

from __future__ import annotations

from typing import Dict, List

# Each entry: ticker -> {name, sector, industry, exchange}
COMPANY_REGISTRY: Dict[str, Dict[str, str]] = {
    # ── Technology ──────────────────────────────────────────────────────
    "AAPL":  {"name": "Apple Inc.",                       "sector": "Technology",         "industry": "Consumer Electronics",         "exchange": "NASDAQ"},
    "MSFT":  {"name": "Microsoft Corporation",            "sector": "Technology",         "industry": "Software—Infrastructure",      "exchange": "NASDAQ"},
    "GOOGL": {"name": "Alphabet Inc.",                    "sector": "Technology",         "industry": "Internet Content & Information","exchange": "NASDAQ"},
    "AMZN":  {"name": "Amazon.com Inc.",                  "sector": "Consumer Cyclical",  "industry": "Internet Retail",              "exchange": "NASDAQ"},
    "META":  {"name": "Meta Platforms Inc.",              "sector": "Technology",         "industry": "Internet Content & Information","exchange": "NASDAQ"},
    "NVDA":  {"name": "NVIDIA Corporation",               "sector": "Technology",         "industry": "Semiconductors",               "exchange": "NASDAQ"},
    "TSLA":  {"name": "Tesla Inc.",                       "sector": "Consumer Cyclical",  "industry": "Auto Manufacturers",           "exchange": "NASDAQ"},
    "ORCL":  {"name": "Oracle Corporation",               "sector": "Technology",         "industry": "Software—Infrastructure",      "exchange": "NYSE"},
    "CRM":   {"name": "Salesforce Inc.",                  "sector": "Technology",         "industry": "Software—Application",         "exchange": "NYSE"},
    "INTC":  {"name": "Intel Corporation",                "sector": "Technology",         "industry": "Semiconductors",               "exchange": "NASDAQ"},
    "AMD":   {"name": "Advanced Micro Devices Inc.",      "sector": "Technology",         "industry": "Semiconductors",               "exchange": "NASDAQ"},
    "ADBE":  {"name": "Adobe Inc.",                       "sector": "Technology",         "industry": "Software—Application",         "exchange": "NASDAQ"},
    "NFLX":  {"name": "Netflix Inc.",                     "sector": "Communication",      "industry": "Entertainment",                "exchange": "NASDAQ"},
    "UBER":  {"name": "Uber Technologies Inc.",           "sector": "Technology",         "industry": "Software—Application",         "exchange": "NYSE"},

    # ── Finance ─────────────────────────────────────────────────────────
    "JPM":   {"name": "JPMorgan Chase & Co.",             "sector": "Financial Services", "industry": "Banks—Diversified",            "exchange": "NYSE"},
    "BAC":   {"name": "Bank of America Corp.",            "sector": "Financial Services", "industry": "Banks—Diversified",            "exchange": "NYSE"},
    "GS":    {"name": "Goldman Sachs Group Inc.",         "sector": "Financial Services", "industry": "Capital Markets",              "exchange": "NYSE"},
    "MS":    {"name": "Morgan Stanley",                   "sector": "Financial Services", "industry": "Capital Markets",              "exchange": "NYSE"},
    "BRK-B": {"name": "Berkshire Hathaway Inc.",          "sector": "Financial Services", "industry": "Insurance—Diversified",        "exchange": "NYSE"},
    "V":     {"name": "Visa Inc.",                        "sector": "Financial Services", "industry": "Credit Services",              "exchange": "NYSE"},
    "MA":    {"name": "Mastercard Incorporated",          "sector": "Financial Services", "industry": "Credit Services",              "exchange": "NYSE"},
    "BLK":   {"name": "BlackRock Inc.",                   "sector": "Financial Services", "industry": "Asset Management",             "exchange": "NYSE"},

    # ── Healthcare ──────────────────────────────────────────────────────
    "JNJ":   {"name": "Johnson & Johnson",                "sector": "Healthcare",         "industry": "Drug Manufacturers—General",   "exchange": "NYSE"},
    "PFE":   {"name": "Pfizer Inc.",                      "sector": "Healthcare",         "industry": "Drug Manufacturers—General",   "exchange": "NYSE"},
    "UNH":   {"name": "UnitedHealth Group Inc.",          "sector": "Healthcare",         "industry": "Healthcare Plans",             "exchange": "NYSE"},
    "ABBV":  {"name": "AbbVie Inc.",                      "sector": "Healthcare",         "industry": "Drug Manufacturers—General",   "exchange": "NYSE"},
    "LLY":   {"name": "Eli Lilly and Company",            "sector": "Healthcare",         "industry": "Drug Manufacturers—General",   "exchange": "NYSE"},
    "MRK":   {"name": "Merck & Co. Inc.",                 "sector": "Healthcare",         "industry": "Drug Manufacturers—General",   "exchange": "NYSE"},

    # ── Consumer ────────────────────────────────────────────────────────
    "WMT":   {"name": "Walmart Inc.",                     "sector": "Consumer Defensive", "industry": "Discount Stores",              "exchange": "NYSE"},
    "KO":    {"name": "The Coca-Cola Company",            "sector": "Consumer Defensive", "industry": "Beverages—Non-Alcoholic",      "exchange": "NYSE"},
    "PEP":   {"name": "PepsiCo Inc.",                     "sector": "Consumer Defensive", "industry": "Beverages—Non-Alcoholic",      "exchange": "NASDAQ"},
    "MCD":   {"name": "McDonald's Corporation",           "sector": "Consumer Cyclical",  "industry": "Restaurants",                  "exchange": "NYSE"},
    "SBUX":  {"name": "Starbucks Corporation",            "sector": "Consumer Cyclical",  "industry": "Restaurants",                  "exchange": "NASDAQ"},
    "NKE":   {"name": "NIKE Inc.",                        "sector": "Consumer Cyclical",  "industry": "Footwear & Accessories",       "exchange": "NYSE"},
    "COST":  {"name": "Costco Wholesale Corporation",     "sector": "Consumer Defensive", "industry": "Discount Stores",              "exchange": "NASDAQ"},

    # ── Energy ──────────────────────────────────────────────────────────
    "XOM":   {"name": "Exxon Mobil Corporation",          "sector": "Energy",             "industry": "Oil & Gas Integrated",         "exchange": "NYSE"},
    "CVX":   {"name": "Chevron Corporation",              "sector": "Energy",             "industry": "Oil & Gas Integrated",         "exchange": "NYSE"},
    "COP":   {"name": "ConocoPhillips",                   "sector": "Energy",             "industry": "Oil & Gas E&P",                "exchange": "NYSE"},

    # ── Industrials ─────────────────────────────────────────────────────
    "BA":    {"name": "Boeing Company",                   "sector": "Industrials",        "industry": "Aerospace & Defense",          "exchange": "NYSE"},
    "GE":    {"name": "GE Aerospace",                     "sector": "Industrials",        "industry": "Aerospace & Defense",          "exchange": "NYSE"},
    "CAT":   {"name": "Caterpillar Inc.",                  "sector": "Industrials",        "industry": "Farm & Heavy Construction",    "exchange": "NYSE"},
    "HON":   {"name": "Honeywell International Inc.",     "sector": "Industrials",        "industry": "Conglomerates",                "exchange": "NASDAQ"},
    "UPS":   {"name": "United Parcel Service Inc.",       "sector": "Industrials",        "industry": "Integrated Freight & Logistics","exchange": "NYSE"},

    # ── Retail / E-commerce ─────────────────────────────────────────────
    "TGT":   {"name": "Target Corporation",               "sector": "Consumer Defensive", "industry": "Discount Stores",              "exchange": "NYSE"},
    "HD":    {"name": "The Home Depot Inc.",               "sector": "Consumer Cyclical",  "industry": "Home Improvement Retail",      "exchange": "NYSE"},

    # ── Telecom ─────────────────────────────────────────────────────────
    "T":     {"name": "AT&T Inc.",                        "sector": "Communication",      "industry": "Telecom Services",             "exchange": "NYSE"},
    "VZ":    {"name": "Verizon Communications Inc.",      "sector": "Communication",      "industry": "Telecom Services",             "exchange": "NYSE"},

    # ── Media / Entertainment ────────────────────────────────────────────
    "DIS":   {"name": "The Walt Disney Company",          "sector": "Communication",      "industry": "Entertainment",                "exchange": "NYSE"},
    "CMCSA": {"name": "Comcast Corporation",              "sector": "Communication",      "industry": "Telecom Services",             "exchange": "NASDAQ"},
}

# Convenient sector → tickers index
SECTORS: Dict[str, List[str]] = {}
for _ticker, _info in COMPANY_REGISTRY.items():
    SECTORS.setdefault(_info["sector"], []).append(_ticker)

DEFAULT_WATCHLIST = list(COMPANY_REGISTRY.keys())


def tickers_for_sector(sector: str) -> List[str]:
    return SECTORS.get(sector, [])


def sectors() -> List[str]:
    return sorted(SECTORS.keys())
