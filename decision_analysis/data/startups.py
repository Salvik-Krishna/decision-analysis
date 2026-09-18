"""
Curated registry of notable private and recently-public startups.

For each company we record:
  - Static metadata (sector, founded, country, stage)
  - Known funding rounds (date, type, amount_usd, post_money_valuation_usd, lead_investors)

All figures are from public sources (press releases, Crunchbase, PitchBook reports,
Bloomberg, Reuters).  Values are approximate where exact figures were not disclosed.
"""

from __future__ import annotations

from typing import Dict, List, Any

# round_type values: Seed | Angel | Pre-Seed | Series A-H | Growth | Debt | IPO | SPAC | Acquisition
STARTUP_REGISTRY: Dict[str, Dict[str, Any]] = {

    # ── AI / ML ─────────────────────────────────────────────────────────────
    "OPENAI": {
        "name": "OpenAI",
        "sector": "Artificial Intelligence",
        "industry": "AI Research & Products",
        "founded": 2015,
        "country": "US",
        "hq_city": "San Francisco",
        "description": "AI safety research lab and creator of GPT series and ChatGPT.",
        "funding_rounds": [
            {"date": "2019-07-22", "type": "Corporate Round", "amount_usd": 1_000_000_000, "valuation_usd": None,           "lead": "Microsoft"},
            {"date": "2021-01-01", "type": "Corporate Round", "amount_usd": 10_000_000,    "valuation_usd": None,           "lead": "Khosla Ventures"},
            {"date": "2023-01-23", "type": "Corporate Round", "amount_usd": 10_000_000_000,"valuation_usd": 29_000_000_000, "lead": "Microsoft"},
            {"date": "2024-10-02", "type": "Series E",        "amount_usd": 6_600_000_000, "valuation_usd": 157_000_000_000,"lead": "Thrive Capital"},
        ],
    },

    "ANTHROPIC": {
        "name": "Anthropic",
        "sector": "Artificial Intelligence",
        "industry": "AI Research & Products",
        "founded": 2021,
        "country": "US",
        "hq_city": "San Francisco",
        "description": "AI safety company and creator of Claude.",
        "funding_rounds": [
            {"date": "2021-04-01", "type": "Series A",  "amount_usd": 124_000_000,    "valuation_usd": None,            "lead": "Spark Capital"},
            {"date": "2022-04-01", "type": "Series B",  "amount_usd": 580_000_000,    "valuation_usd": 4_100_000_000,   "lead": "Spark Capital"},
            {"date": "2023-05-23", "type": "Series C",  "amount_usd": 450_000_000,    "valuation_usd": 4_100_000_000,   "lead": "Spark Capital"},
            {"date": "2023-07-01", "type": "Corporate", "amount_usd": 300_000_000,    "valuation_usd": None,            "lead": "Google"},
            {"date": "2024-03-01", "type": "Series E",  "amount_usd": 2_750_000_000,  "valuation_usd": 18_400_000_000,  "lead": "Google"},
            {"date": "2025-03-01", "type": "Series F",  "amount_usd": 3_500_000_000,  "valuation_usd": 61_500_000_000,  "lead": "Google"},
        ],
    },

    "MISTRAL": {
        "name": "Mistral AI",
        "sector": "Artificial Intelligence",
        "industry": "AI Models",
        "founded": 2023,
        "country": "FR",
        "hq_city": "Paris",
        "description": "Open-weight large language model company.",
        "funding_rounds": [
            {"date": "2023-06-13", "type": "Seed",     "amount_usd": 113_000_000,   "valuation_usd": 264_000_000,    "lead": "Lightspeed"},
            {"date": "2023-12-11", "type": "Series A", "amount_usd": 415_000_000,   "valuation_usd": 2_000_000_000,  "lead": "Andreessen Horowitz"},
            {"date": "2024-06-11", "type": "Series B", "amount_usd": 600_000_000,   "valuation_usd": 6_000_000_000,  "lead": "General Catalyst"},
        ],
    },

    "PERPLEXITY": {
        "name": "Perplexity AI",
        "sector": "Artificial Intelligence",
        "industry": "AI Search",
        "founded": 2022,
        "country": "US",
        "hq_city": "San Francisco",
        "description": "AI-powered answer engine.",
        "funding_rounds": [
            {"date": "2023-01-01", "type": "Series A", "amount_usd": 25_900_000,    "valuation_usd": None,           "lead": "NEA"},
            {"date": "2024-01-04", "type": "Series B", "amount_usd": 73_600_000,    "valuation_usd": 520_000_000,    "lead": "IVP"},
            {"date": "2024-06-13", "type": "Series C", "amount_usd": 250_000_000,   "valuation_usd": 3_000_000_000,  "lead": "Institutional Venture Partners"},
            {"date": "2025-01-01", "type": "Series D", "amount_usd": 500_000_000,   "valuation_usd": 9_000_000_000,  "lead": "SoftBank"},
        ],
    },

    # ── Fintech ──────────────────────────────────────────────────────────────
    "STRIPE": {
        "name": "Stripe",
        "sector": "Fintech",
        "industry": "Payments Infrastructure",
        "founded": 2010,
        "country": "US",
        "hq_city": "San Francisco",
        "description": "Online payments infrastructure for the internet.",
        "funding_rounds": [
            {"date": "2011-03-28", "type": "Seed",     "amount_usd": 2_000_000,      "valuation_usd": None,            "lead": "Peter Thiel"},
            {"date": "2012-02-09", "type": "Series A", "amount_usd": 18_000_000,     "valuation_usd": None,            "lead": "Sequoia Capital"},
            {"date": "2014-01-22", "type": "Series B", "amount_usd": 80_000_000,     "valuation_usd": None,            "lead": "Founders Fund"},
            {"date": "2016-11-25", "type": "Series D", "amount_usd": 150_000_000,    "valuation_usd": 9_200_000_000,   "lead": "General Catalyst"},
            {"date": "2019-09-19", "type": "Series F", "amount_usd": 250_000_000,    "valuation_usd": 35_000_000_000,  "lead": "Andreessen Horowitz"},
            {"date": "2021-03-14", "type": "Series H", "amount_usd": 600_000_000,    "valuation_usd": 95_000_000_000,  "lead": "Allianz X"},
            {"date": "2023-03-15", "type": "Series I", "amount_usd": 6_500_000_000,  "valuation_usd": 50_000_000_000,  "lead": "Andreessen Horowitz"},
            {"date": "2025-02-01", "type": "Series J", "amount_usd": 1_100_000_000,  "valuation_usd": 91_500_000_000,  "lead": "Sequoia Capital"},
        ],
    },

    "KLARNA": {
        "name": "Klarna",
        "sector": "Fintech",
        "industry": "Buy Now Pay Later",
        "founded": 2005,
        "country": "SE",
        "hq_city": "Stockholm",
        "description": "BNPL and payments platform.",
        "funding_rounds": [
            {"date": "2020-09-10", "type": "Series F", "amount_usd": 650_000_000,    "valuation_usd": 10_650_000_000,  "lead": "Silver Lake"},
            {"date": "2021-03-03", "type": "Series G", "amount_usd": 1_000_000_000,  "valuation_usd": 31_000_000_000,  "lead": "SoftBank"},
            {"date": "2021-06-10", "type": "Series H", "amount_usd": 639_000_000,    "valuation_usd": 45_600_000_000,  "lead": "SoftBank"},
            {"date": "2022-07-20", "type": "Down Round","amount_usd": 800_000_000,   "valuation_usd": 6_700_000_000,   "lead": "SEQ"},
            {"date": "2023-07-18", "type": "Series ?", "amount_usd": 400_000_000,    "valuation_usd": 6_700_000_000,   "lead": "Canada Pension Plan"},
            {"date": "2024-07-12", "type": "IPO filing","amount_usd": None,          "valuation_usd": 15_000_000_000,  "lead": "Public Markets"},
        ],
    },

    "REVOLUT": {
        "name": "Revolut",
        "sector": "Fintech",
        "industry": "Neobank",
        "founded": 2015,
        "country": "GB",
        "hq_city": "London",
        "description": "Global digital banking and financial services app.",
        "funding_rounds": [
            {"date": "2018-04-26", "type": "Series C", "amount_usd": 250_000_000,    "valuation_usd": 1_700_000_000,   "lead": "DST Global"},
            {"date": "2020-02-24", "type": "Series D", "amount_usd": 500_000_000,    "valuation_usd": 5_500_000_000,   "lead": "TCV"},
            {"date": "2021-07-15", "type": "Series E", "amount_usd": 800_000_000,    "valuation_usd": 33_000_000_000,  "lead": "Tiger Global"},
            {"date": "2024-08-16", "type": "Secondary","amount_usd": 1_000_000_000,  "valuation_usd": 45_000_000_000,  "lead": "Motley Fool"},
        ],
    },

    "CHIME": {
        "name": "Chime",
        "sector": "Fintech",
        "industry": "Neobank",
        "founded": 2013,
        "country": "US",
        "hq_city": "San Francisco",
        "description": "US neobank offering fee-free financial services.",
        "funding_rounds": [
            {"date": "2019-03-05", "type": "Series D", "amount_usd": 200_000_000,    "valuation_usd": 1_500_000_000,   "lead": "DST Global"},
            {"date": "2019-12-18", "type": "Series E", "amount_usd": 500_000_000,    "valuation_usd": 5_800_000_000,   "lead": "DST Global"},
            {"date": "2021-08-13", "type": "Series G", "amount_usd": 750_000_000,    "valuation_usd": 25_000_000_000,  "lead": "Sequoia Capital"},
        ],
    },

    # ── SaaS / Cloud ─────────────────────────────────────────────────────────
    "DATABRICKS": {
        "name": "Databricks",
        "sector": "Enterprise Software",
        "industry": "Data & AI Platform",
        "founded": 2013,
        "country": "US",
        "hq_city": "San Francisco",
        "description": "Unified data analytics and AI platform built on Apache Spark.",
        "funding_rounds": [
            {"date": "2019-10-22", "type": "Series E", "amount_usd": 400_000_000,    "valuation_usd": 6_200_000_000,   "lead": "Andreessen Horowitz"},
            {"date": "2021-02-01", "type": "Series G", "amount_usd": 1_000_000_000,  "valuation_usd": 28_000_000_000,  "lead": "Franklin Templeton"},
            {"date": "2021-08-31", "type": "Series H", "amount_usd": 1_600_000_000,  "valuation_usd": 38_000_000_000,  "lead": "Counterpoint Global"},
            {"date": "2023-09-14", "type": "Series I", "amount_usd": 500_000_000,    "valuation_usd": 43_000_000_000,  "lead": "T. Rowe Price"},
            {"date": "2024-12-17", "type": "Series J", "amount_usd": 15_300_000_000, "valuation_usd": 62_000_000_000,  "lead": "Thrive Capital"},
        ],
    },

    "CANVA": {
        "name": "Canva",
        "sector": "Enterprise Software",
        "industry": "Design Tools",
        "founded": 2013,
        "country": "AU",
        "hq_city": "Sydney",
        "description": "Visual communication and design platform.",
        "funding_rounds": [
            {"date": "2019-10-14", "type": "Series D", "amount_usd": 85_000_000,     "valuation_usd": 3_200_000_000,   "lead": "General Catalyst"},
            {"date": "2020-06-01", "type": "Series E", "amount_usd": 60_000_000,     "valuation_usd": 6_000_000_000,   "lead": "T. Rowe Price"},
            {"date": "2021-09-14", "type": "Series F", "amount_usd": 200_000_000,    "valuation_usd": 40_000_000_000,  "lead": "T. Rowe Price"},
        ],
    },

    "FIGMA": {
        "name": "Figma",
        "sector": "Enterprise Software",
        "industry": "Design Tools",
        "founded": 2012,
        "country": "US",
        "hq_city": "San Francisco",
        "description": "Collaborative interface design tool.",
        "funding_rounds": [
            {"date": "2019-02-27", "type": "Series C", "amount_usd": 40_000_000,     "valuation_usd": 440_000_000,     "lead": "Kleiner Perkins"},
            {"date": "2020-04-30", "type": "Series D", "amount_usd": 50_000_000,     "valuation_usd": 2_000_000_000,   "lead": "Andreessen Horowitz"},
            {"date": "2021-06-24", "type": "Series E", "amount_usd": 200_000_000,    "valuation_usd": 10_000_000_000,  "lead": "Durable Capital"},
            {"date": "2022-09-15", "type": "Acquisition","amount_usd": 20_000_000_000,"valuation_usd": 20_000_000_000, "lead": "Adobe (blocked by EU)"},
        ],
    },

    "AIRTABLE": {
        "name": "Airtable",
        "sector": "Enterprise Software",
        "industry": "No-Code / Productivity",
        "founded": 2012,
        "country": "US",
        "hq_city": "San Francisco",
        "description": "Low-code platform for building collaborative apps.",
        "funding_rounds": [
            {"date": "2020-09-22", "type": "Series D", "amount_usd": 185_000_000,    "valuation_usd": 2_585_000_000,   "lead": "Benchmark"},
            {"date": "2021-03-17", "type": "Series E", "amount_usd": 270_000_000,    "valuation_usd": 5_770_000_000,   "lead": "Greenoaks Capital"},
            {"date": "2021-12-17", "type": "Series F", "amount_usd": 735_000_000,    "valuation_usd": 11_700_000_000,  "lead": "Greenoaks Capital"},
        ],
    },

    "NOTION": {
        "name": "Notion",
        "sector": "Enterprise Software",
        "industry": "Productivity",
        "founded": 2016,
        "country": "US",
        "hq_city": "San Francisco",
        "description": "All-in-one workspace for notes, docs, and project management.",
        "funding_rounds": [
            {"date": "2019-03-08", "type": "Series A", "amount_usd": 10_000_000,     "valuation_usd": None,            "lead": "Index Ventures"},
            {"date": "2020-04-01", "type": "Series B", "amount_usd": 50_000_000,     "valuation_usd": 2_000_000_000,   "lead": "Index Ventures"},
            {"date": "2021-10-08", "type": "Series C", "amount_usd": 275_000_000,    "valuation_usd": 10_000_000_000,  "lead": "Sequoia Capital"},
        ],
    },

    # ── Consumer / Marketplace ────────────────────────────────────────────────
    "AIRBNB_PRE_IPO": {
        "name": "Airbnb (pre-IPO)",
        "sector": "Travel & Hospitality",
        "industry": "Short-term Rental Marketplace",
        "founded": 2008,
        "country": "US",
        "hq_city": "San Francisco",
        "description": "Home-sharing marketplace (IPO Dec 2020 at ~$47B).",
        "funding_rounds": [
            {"date": "2011-07-25", "type": "Series B", "amount_usd": 112_000_000,    "valuation_usd": None,            "lead": "Andreessen Horowitz"},
            {"date": "2015-06-26", "type": "Series E", "amount_usd": 1_500_000_000,  "valuation_usd": 25_500_000_000,  "lead": "General Atlantic"},
            {"date": "2017-03-09", "type": "Series F", "amount_usd": 447_000_000,    "valuation_usd": 31_000_000_000,  "lead": "Various"},
            {"date": "2020-04-06", "type": "Debt",     "amount_usd": 2_000_000_000,  "valuation_usd": None,            "lead": "Silver Lake / Sixth Street"},
        ],
    },

    "INSTACART": {
        "name": "Instacart",
        "sector": "Consumer",
        "industry": "Grocery Delivery",
        "founded": 2012,
        "country": "US",
        "hq_city": "San Francisco",
        "description": "Grocery delivery and pick-up marketplace.",
        "funding_rounds": [
            {"date": "2018-10-19", "type": "Series F", "amount_usd": 600_000_000,    "valuation_usd": 7_600_000_000,   "lead": "Coatue"},
            {"date": "2020-06-05", "type": "Series G", "amount_usd": 225_000_000,    "valuation_usd": 13_700_000_000,  "lead": "D1 Capital"},
            {"date": "2021-03-02", "type": "Series H", "amount_usd": 265_000_000,    "valuation_usd": 39_000_000_000,  "lead": "Andreessen Horowitz"},
            {"date": "2023-09-19", "type": "IPO",      "amount_usd": 660_000_000,    "valuation_usd": 9_900_000_000,   "lead": "Public Markets"},
        ],
    },

    "DOORDASH_PRE_IPO": {
        "name": "DoorDash (pre-IPO)",
        "sector": "Consumer",
        "industry": "Food Delivery",
        "founded": 2013,
        "country": "US",
        "hq_city": "San Francisco",
        "description": "Food delivery platform (IPO Dec 2020).",
        "funding_rounds": [
            {"date": "2018-03-01", "type": "Series D", "amount_usd": 535_000_000,    "valuation_usd": 1_400_000_000,   "lead": "SoftBank"},
            {"date": "2019-05-17", "type": "Series F", "amount_usd": 600_000_000,    "valuation_usd": 12_600_000_000,  "lead": "Dragoneer"},
            {"date": "2020-06-18", "type": "Series H", "amount_usd": 400_000_000,    "valuation_usd": 16_000_000_000,  "lead": "Durable Capital"},
        ],
    },

    "SHEIN": {
        "name": "Shein",
        "sector": "Consumer",
        "industry": "Fast Fashion E-commerce",
        "founded": 2008,
        "country": "CN",
        "hq_city": "Singapore",
        "description": "Ultra-fast fashion e-commerce platform.",
        "funding_rounds": [
            {"date": "2020-08-01", "type": "Series D", "amount_usd": 2_000_000_000,  "valuation_usd": 15_000_000_000,  "lead": "Tiger Global"},
            {"date": "2021-08-01", "type": "Series E", "amount_usd": 1_000_000_000,  "valuation_usd": 30_000_000_000,  "lead": "IDG Capital"},
            {"date": "2022-04-01", "type": "Series F", "amount_usd": 1_000_000_000,  "valuation_usd": 100_000_000_000, "lead": "Sequoia China"},
            {"date": "2023-05-01", "type": "Series ?", "amount_usd": 2_000_000_000,  "valuation_usd": 66_000_000_000,  "lead": "General Atlantic"},
        ],
    },

    # ── Space / Deep Tech ─────────────────────────────────────────────────────
    "SPACEX": {
        "name": "SpaceX",
        "sector": "Aerospace & Defense",
        "industry": "Space Transportation",
        "founded": 2002,
        "country": "US",
        "hq_city": "Hawthorne, CA",
        "description": "Private space transportation and Starlink satellite internet.",
        "funding_rounds": [
            {"date": "2019-05-24", "type": "Series N", "amount_usd": 535_000_000,    "valuation_usd": 33_300_000_000,  "lead": "Various"},
            {"date": "2021-04-01", "type": "Series P", "amount_usd": 850_000_000,    "valuation_usd": 74_000_000_000,  "lead": "Various"},
            {"date": "2023-12-01", "type": "Secondary","amount_usd": 175_000_000,    "valuation_usd": 180_000_000_000, "lead": "Various"},
            {"date": "2025-01-01", "type": "Secondary","amount_usd": None,           "valuation_usd": 350_000_000_000, "lead": "Various"},
        ],
    },

    "RELATIVITY_SPACE": {
        "name": "Relativity Space",
        "sector": "Aerospace & Defense",
        "industry": "Launch Vehicles",
        "founded": 2015,
        "country": "US",
        "hq_city": "Long Beach, CA",
        "description": "3D-printed rocket manufacturer.",
        "funding_rounds": [
            {"date": "2020-10-01", "type": "Series D", "amount_usd": 500_000_000,    "valuation_usd": 2_300_000_000,   "lead": "Tiger Global"},
            {"date": "2021-06-08", "type": "Series E", "amount_usd": 650_000_000,    "valuation_usd": 4_200_000_000,   "lead": "General Atlantic"},
        ],
    },

    # ── Health Tech ──────────────────────────────────────────────────────────
    "NURO": {
        "name": "Nuro",
        "sector": "Transportation",
        "industry": "Autonomous Delivery",
        "founded": 2016,
        "country": "US",
        "hq_city": "Mountain View",
        "description": "Autonomous delivery vehicle company.",
        "funding_rounds": [
            {"date": "2019-02-11", "type": "Series B", "amount_usd": 940_000_000,    "valuation_usd": 2_700_000_000,   "lead": "SoftBank"},
            {"date": "2021-11-02", "type": "Series C", "amount_usd": 600_000_000,    "valuation_usd": 8_600_000_000,   "lead": "Tiger Global"},
        ],
    },

    "OSCAR_HEALTH": {
        "name": "Oscar Health",
        "sector": "Health Tech",
        "industry": "Health Insurance",
        "founded": 2012,
        "country": "US",
        "hq_city": "New York",
        "description": "Tech-driven health insurance company.",
        "funding_rounds": [
            {"date": "2018-08-01", "type": "Series F", "amount_usd": 375_000_000,    "valuation_usd": 3_200_000_000,   "lead": "Alphabet"},
            {"date": "2020-09-01", "type": "Series ?", "amount_usd": 225_000_000,    "valuation_usd": 3_600_000_000,   "lead": "Various"},
            {"date": "2021-03-03", "type": "IPO",      "amount_usd": 1_440_000_000,  "valuation_usd": 7_700_000_000,   "lead": "Public Markets"},
        ],
    },

    # ── Mobility ─────────────────────────────────────────────────────────────
    "WAYMO": {
        "name": "Waymo",
        "sector": "Transportation",
        "industry": "Autonomous Vehicles",
        "founded": 2009,
        "country": "US",
        "hq_city": "Mountain View",
        "description": "Self-driving technology company, Alphabet subsidiary.",
        "funding_rounds": [
            {"date": "2020-03-02", "type": "Series A", "amount_usd": 2_250_000_000,  "valuation_usd": 30_000_000_000,  "lead": "Silver Lake"},
            {"date": "2020-05-11", "type": "Series A+","amount_usd": 750_000_000,    "valuation_usd": None,            "lead": "Various"},
            {"date": "2021-06-16", "type": "Series B", "amount_usd": 2_500_000_000,  "valuation_usd": 30_000_000_000,  "lead": "Andreessen Horowitz"},
        ],
    },

    "NAVAN": {
        "name": "Navan (TripActions)",
        "sector": "Enterprise Software",
        "industry": "Corporate Travel",
        "founded": 2015,
        "country": "US",
        "hq_city": "Palo Alto",
        "description": "Business travel and expense management platform.",
        "funding_rounds": [
            {"date": "2021-10-14", "type": "Series G", "amount_usd": 275_000_000,    "valuation_usd": 9_200_000_000,   "lead": "Andreessen Horowitz"},
            {"date": "2022-10-18", "type": "Series H", "amount_usd": 154_000_000,    "valuation_usd": 9_200_000_000,   "lead": "Various"},
        ],
    },

    # ── Crypto / Web3 ────────────────────────────────────────────────────────
    "FTX": {
        "name": "FTX (defunct)",
        "sector": "Crypto",
        "industry": "Crypto Exchange",
        "founded": 2019,
        "country": "BS",
        "hq_city": "Nassau",
        "description": "Crypto exchange that collapsed in Nov 2022.",
        "funding_rounds": [
            {"date": "2021-07-20", "type": "Series B", "amount_usd": 900_000_000,    "valuation_usd": 18_000_000_000,  "lead": "Sequoia Capital"},
            {"date": "2022-01-31", "type": "Series C", "amount_usd": 400_000_000,    "valuation_usd": 32_000_000_000,  "lead": "SoftBank"},
            {"date": "2022-11-11", "type": "Bankruptcy","amount_usd": None,          "valuation_usd": 0,               "lead": "N/A"},
        ],
    },

    "COINBASE_PRE_IPO": {
        "name": "Coinbase (pre-IPO)",
        "sector": "Crypto",
        "industry": "Crypto Exchange",
        "founded": 2012,
        "country": "US",
        "hq_city": "San Francisco",
        "description": "Largest US crypto exchange (direct listing Apr 2021).",
        "funding_rounds": [
            {"date": "2018-10-30", "type": "Series E", "amount_usd": 300_000_000,    "valuation_usd": 8_000_000_000,   "lead": "Tiger Global"},
            {"date": "2021-04-14", "type": "Direct Listing","amount_usd": None,      "valuation_usd": 85_780_000_000,  "lead": "Public Markets"},
        ],
    },

    # ── Climate / Energy ─────────────────────────────────────────────────────
    "CLIMEWORKS": {
        "name": "Climeworks",
        "sector": "Climate Tech",
        "industry": "Direct Air Capture",
        "founded": 2009,
        "country": "CH",
        "hq_city": "Zurich",
        "description": "Direct air carbon capture and storage.",
        "funding_rounds": [
            {"date": "2022-04-05", "type": "Series C", "amount_usd": 650_000_000,    "valuation_usd": None,            "lead": "Partners Group"},
        ],
    },

    "H2_GREEN_STEEL": {
        "name": "H2 Green Steel",
        "sector": "Climate Tech",
        "industry": "Green Steel",
        "founded": 2020,
        "country": "SE",
        "hq_city": "Stockholm",
        "description": "Hydrogen-based green steel manufacturer.",
        "funding_rounds": [
            {"date": "2021-09-01", "type": "Series A", "amount_usd": 105_000_000,    "valuation_usd": None,            "lead": "Vargas"},
            {"date": "2022-06-09", "type": "Series B", "amount_usd": 190_000_000,    "valuation_usd": None,            "lead": "Goldman Sachs"},
            {"date": "2023-01-01", "type": "Series C", "amount_usd": 1_500_000_000,  "valuation_usd": None,            "lead": "Various"},
        ],
    },

    # ── Communications ────────────────────────────────────────────────────────
    "DISCORD": {
        "name": "Discord",
        "sector": "Communication",
        "industry": "Social Messaging",
        "founded": 2015,
        "country": "US",
        "hq_city": "San Francisco",
        "description": "Voice, video, and text communication platform.",
        "funding_rounds": [
            {"date": "2020-06-30", "type": "Series G", "amount_usd": 100_000_000,    "valuation_usd": 3_500_000_000,   "lead": "Greenoaks Capital"},
            {"date": "2021-09-14", "type": "Series H", "amount_usd": 500_000_000,    "valuation_usd": 15_000_000_000,  "lead": "Dragoneer"},
        ],
    },

    # ── Logistics ────────────────────────────────────────────────────────────
    "FLEXPORT": {
        "name": "Flexport",
        "sector": "Logistics",
        "industry": "Digital Freight",
        "founded": 2013,
        "country": "US",
        "hq_city": "San Francisco",
        "description": "Digital freight forwarding and supply chain platform.",
        "funding_rounds": [
            {"date": "2019-02-21", "type": "Series D", "amount_usd": 1_000_000_000,  "valuation_usd": 3_200_000_000,   "lead": "SoftBank"},
            {"date": "2022-02-10", "type": "Series E", "amount_usd": 935_000_000,    "valuation_usd": 8_000_000_000,   "lead": "Andreessen Horowitz"},
        ],
    },
}

# Sector → company keys index
STARTUP_SECTORS: Dict[str, List[str]] = {}
for _key, _info in STARTUP_REGISTRY.items():
    STARTUP_SECTORS.setdefault(_info["sector"], []).append(_key)

DEFAULT_STARTUP_WATCHLIST = list(STARTUP_REGISTRY.keys())


def startup_keys_for_sector(sector: str) -> List[str]:
    return STARTUP_SECTORS.get(sector, [])


def startup_sectors() -> List[str]:
    return sorted(STARTUP_SECTORS.keys())
