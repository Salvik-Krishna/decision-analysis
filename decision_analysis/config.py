"""Configuration loader and defaults for the framework."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
import json

DEFAULTS: Dict[str, Dict[str, Any]] = {
    "simulation": {
        "cycles": 12,
        "seed": 7,
    },
    "environment": {
        "market": {
            "demand_volatility": 0.4,
            "competition_intensity": 0.6,
            "customer_preference_variation": 0.5,
            "market_shocks": 0.2,
        },
        "operational": {
            "resource_availability": 0.7,
            "supply_instability": 0.3,
            "regulatory_constraints": 0.4,
        },
        "stress": {
            "crisis_events": 0.1,
            "economic_downturns": 0.2,
            "misinformation_environments": 0.2,
            "adversarial_competitors": 0.3,
        },
    },
    "organization": {
        "model": "hybrid_human_ai_governance",
        "hierarchy_depth": 3,
        "span_of_control": 5,
        "communication_restrictions": 0.3,
        "authority_concentration": 0.6,
        "decision_approval_requirements": 0.4,
        "decentralization_index": 0.4,
    },
    "agents": {
        "counts": {
            "executives": 3,
            "managers": 8,
            "employees": 30,
            "customers": 200,
            "ai_systems": 4,
        },
        "properties": {
            "rationality_level": 0.6,
            "bounded_reasoning_capacity": 0.5,
            "memory_limitations": 0.4,
            "uncertainty_tolerance": 0.5,
            "cooperation_tendency": 0.6,
            "risk_preference": 0.5,
            "strategic_aggressiveness": 0.4,
            "conformity_tendency": 0.5,
            "trust_level": 0.5,
            "influence_capacity": 0.5,
            "alliance_formation_tendency": 0.4,
            "ai_optimization_objective": 0.6,
            "ai_explainability_level": 0.5,
            "ai_alignment_score": 0.6,
            "ai_override_resistance": 0.4,
            "ai_reward_exploitation_tendency": 0.3,
        },
    },
    "information": {
        "information_delay": 0.3,
        "incomplete_visibility": 0.4,
        "reporting_bias": 0.2,
        "misinformation_injection": 0.2,
        "transparency_level": 0.5,
        "communication_noise": 0.3,
    },
    "incentives": {
        "profit": 0.6,
        "personal_advancement": 0.4,
        "team_performance": 0.5,
        "ethical": 0.5,
        "survival": 0.4,
        "short_term_focus": 0.5,
        "metric_optimization": 0.4,
    },
    "constraints": {
        "budget_limits": 0.5,
        "communication_restrictions": 0.3,
        "authority_boundaries": 0.4,
        "time_pressure": 0.4,
        "legal_constraints": 0.3,
        "ethical_limitations": 0.4,
    },
    "alignment": {
        "human_human_alignment": 0.6,
        "human_ai_alignment": 0.6,
        "intent_drift_rate": 0.2,
        "dependency_risk": 0.3,
    },
    "decision_engine": {
        "mode": "hybrid",
        "risk_weight": 0.5,
        "information_weight": 0.6,
        "alignment_weight": 0.5,
    },
    "interaction": {
        "collaboration_rate": 0.6,
        "negotiation_rate": 0.5,
        "competition_rate": 0.4,
        "deception_rate": 0.2,
    },
    "measurement": {
        "pnl_weight": 0.6,
        "customer_weight": 0.4,
        "ethical_weight": 0.5,
    },
}


def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


@dataclass
class Config:
    simulation: Dict[str, Any]
    environment: Dict[str, Any]
    organization: Dict[str, Any]
    agents: Dict[str, Any]
    information: Dict[str, Any]
    incentives: Dict[str, Any]
    constraints: Dict[str, Any]
    alignment: Dict[str, Any]
    decision_engine: Dict[str, Any]
    interaction: Dict[str, Any]
    measurement: Dict[str, Any]


def load_config(path: str | Path) -> Config:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    merged = _merge_dicts(DEFAULTS, raw)
    return Config(**merged)
