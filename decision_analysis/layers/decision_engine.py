"""Decision engine for generating decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class DecisionResult:
    quality: float
    action_strength: float


class DecisionEngine:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    def decide(self, info_quality: float, adaptability: float, alignment: float, constraints: float) -> DecisionResult:
        risk_weight = self.config["risk_weight"]
        information_weight = self.config["information_weight"]
        alignment_weight = self.config["alignment_weight"]

        base_quality = (
            info_quality * information_weight
            + adaptability * (1.0 - risk_weight)
            + alignment * alignment_weight
        ) / (information_weight + (1.0 - risk_weight) + alignment_weight)

        action_strength = max(0.0, min(1.0, base_quality * constraints))
        return DecisionResult(quality=base_quality, action_strength=action_strength)
