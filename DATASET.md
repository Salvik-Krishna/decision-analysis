# Decision Dataset

A real-data, analysis-ready table for studying corporate **decisions**, built
entirely from public sources with no third-party Python dependencies (stdlib
`urllib` only). It lives as the `decision_dataset` table inside
`market_data.db`, alongside the raw tables it is derived from.

**One row = one real decision.** Two kinds:

| `entity_type` | Unit of observation | Source | Outcome measure |
|---------------|---------------------|--------|-----------------|
| `public`  | A US public company 8-K filing (legally material event) | SEC EDGAR | Stock price reaction (+1d/+5d/+30d) |
| `startup` | A startup funding / news event | Built-in registry + Google News | Valuation change to next round |

## How to (re)build

```bash
# 1. Populate the raw tables (prices + EDGAR events + reactions) for all companies
python scrape_dataset.py                      # whole registry (49 companies)
python scrape_dataset.py AAPL MSFT TSLA       # a subset

# 2. Materialize the flat analysis table
python -m decision_analysis.data.dataset                  # rebuild table
python -m decision_analysis.data.dataset --csv decisions.csv   # + CSV export
```

`scrape_dataset.py` is dependency-free: prices come from the Yahoo Finance v8
chart JSON API and events from SEC EDGAR 8-K filings, both over the standard
library. TLS is verified against a discovered system CA bundle
(`decision_analysis/data/tls.py`) — verification is **not** disabled.

## Framework → column mapping

The columns are organized to mirror the decision-analysis framework.

### Framework › Limiting influence
*What information shapes the decision, and how trustworthy / already-priced-in is it.*
- `source_credibility` — 1.0 for SEC filings (official, legally mandated)
- `source_domain` — provenance of the signal (`sec.gov`, …)
- `pre_event_drift_5d` — 5-day price drift **before** the disclosure (information leakage / influence already absorbed by the market)

### Framework › Limiting action
*The constraints binding the decision.*
- `is_material` — 1 for 8-K filings (material by law)
- `regulatory_constraint` — 1 for regulatory / bankruptcy events
- `action_class` — `disclosure` · `governance` · `strategic` · `operational` · `compliance` · `capital_return` · `other`

### Framework › Structure of the organisation
*The org configuration around the decision.*
- `exec_count` — named officers on record for the entity
- `leadership_turnover_24m` — leadership-change events in the trailing 24 months
- `restructuring_24m` — restructuring events in the trailing 24 months

### Controlling the situation › Human alignment
- `leadership_change_flag` — 1 if the decision is a leadership change (human governance control)
- `alignment_with_market` — +1 if pre-event drift and post-event reaction agree in sign, −1 if they diverge (was the decision aligned with stakeholder expectations)

> **Not covered by market data:** *intent of model* and *agent personalities /
> comparison* have no real-data proxy here — they belong to the simulation
> layer (`decision_analysis/layers/alignment.py`) and are intentionally left out.

### Analysing outcome
- `change_in_value_1d`, `change_in_value_5d`, `change_in_value_30d` — % price reaction at each horizon (public)
- `primary_change_in_value` — headline outcome (+5d for public, next-round valuation change for startups)
- `primary_pnl` — realized return proxy (= primary change in value)
- `outcome_horizon` — `+5d` (public) or `next_funding_round` (startup)
- `volume_reaction_5d` — trading-volume change (attention proxy)
- `customer_proxy` — **NULL**: surveyed customer satisfaction (NPS/reviews) is not in this dataset; wire a separate source if needed

### Study dimensions (heuristic proxies)
Transparent proxies derived from the real data — **starting points for
analysis, not ground truth**. Formulas in `decision_analysis/data/dataset.py`.

| Column | Proxy definition |
|--------|------------------|
| `decision_quality` | +30d return (market's multi-week verdict; falls back to +5d/+1d) |
| `organizational_adaptability` | `1 − 1/(1 + reconfig_events_24m)` (leadership + restructuring activity) |
| `power_distribution` | normalized named-officer count (`min(exec_count,30)/30`) |
| `alignment_dynamics` | = `alignment_with_market` |
| `coordination_efficiency` | consistency of +1d vs +30d reaction; startups use follow-on round speed |
| `ethical_stability` | `1/(1 + regulatory_incidents_24m)` |

## Caveats
- **Officer data is sparse.** Current-officer rosters come from yfinance, which
  was unavailable in this environment; `exec_count` (and therefore
  `power_distribution`) is only well-populated where officer records already
  existed. Refresh with `db_cli officers` once yfinance is installed.
- Study-dimension proxies are heuristic and unnormalized across sectors — treat
  them as features to model, not labels.
- 8-K coverage starts at the `--start` date (default 2018-01-01).
