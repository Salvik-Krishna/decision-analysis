"""Interaction and negotiation layer."""

from __future__ import annotations

from typing import Dict, Any


class InteractionLayer:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    def coordination_efficiency(self, trust: float, bottleneck_risk: float) -> float:
        collaboration = self.config["collaboration_rate"]
        negotiation = self.config["negotiation_rate"]
        competition = self.config["competition_rate"]
        deception = self.config["deception_rate"]

        positive = (collaboration + negotiation) * 0.5 * trust
        negative = (competition + deception) * 0.5 * (1.0 + bottleneck_risk)
        return max(0.0, min(1.0, positive - negative + 0.5))
