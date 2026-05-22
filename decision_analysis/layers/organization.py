"""Organization structure effects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class OrganizationEffects:
    coordination_latency: float
    information_distortion: float
    adaptability: float
    bottleneck_risk: float


class OrganizationLayer:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    def compute_effects(self) -> OrganizationEffects:
        depth = self.config["hierarchy_depth"]
        span = self.config["span_of_control"]
        restrictions = self.config["communication_restrictions"]
        authority = self.config["authority_concentration"]
        decentralization = self.config["decentralization_index"]

        coordination_latency = min(1.0, 0.1 * depth + 0.02 * span + restrictions * 0.4)
        information_distortion = min(1.0, 0.2 * depth + authority * 0.4 + restrictions * 0.2)
        adaptability = max(0.0, 1.0 - (authority * 0.4 + restrictions * 0.3 + depth * 0.05))
        bottleneck_risk = min(1.0, authority * 0.6 + depth * 0.05 - decentralization * 0.2)

        return OrganizationEffects(
            coordination_latency=coordination_latency,
            information_distortion=information_distortion,
            adaptability=adaptability,
            bottleneck_risk=bottleneck_risk,
        )
