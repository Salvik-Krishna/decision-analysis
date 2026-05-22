"""Operational constraint layer."""

from __future__ import annotations

from typing import Dict, Any


class ConstraintLayer:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    def capacity(self) -> float:
        budget = self.config["budget_limits"]
        communication = self.config["communication_restrictions"]
        authority = self.config["authority_boundaries"]
        time = self.config["time_pressure"]
        legal = self.config["legal_constraints"]
        ethical = self.config["ethical_limitations"]

        friction = 0.2 * budget + 0.15 * communication + 0.2 * authority + 0.2 * time + 0.15 * legal + 0.1 * ethical
        return max(0.0, 1.0 - friction)
