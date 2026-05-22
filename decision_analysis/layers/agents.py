"""Agent population modeling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class AgentProfile:
    rationality: float
    trust: float
    risk_preference: float
    influence: float
    ai_alignment: float


class AgentPopulation:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.counts = config["counts"]
        self.properties = config["properties"]

    def summary_profile(self) -> AgentProfile:
        props = self.properties
        rationality = props["rationality_level"] * (1.0 - props["bounded_reasoning_capacity"] * 0.3)
        trust = props["trust_level"] * (1.0 - props["conformity_tendency"] * 0.1)
        risk_preference = props["risk_preference"]
        influence = props["influence_capacity"]
        ai_alignment = props["ai_alignment_score"] * (1.0 - props["ai_reward_exploitation_tendency"] * 0.4)

        return AgentProfile(
            rationality=rationality,
            trust=trust,
            risk_preference=risk_preference,
            influence=influence,
            ai_alignment=ai_alignment,
        )
