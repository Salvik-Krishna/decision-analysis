"""Human-AI alignment dynamics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class AlignmentState:
    human_alignment: float
    human_ai_alignment: float
    dependency_risk: float


class AlignmentLayer:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    def evolve(self, misalignment_pressure: float) -> AlignmentState:
        human_alignment = max(0.0, self.config["human_human_alignment"] - misalignment_pressure * 0.3)
        human_ai_alignment = max(0.0, self.config["human_ai_alignment"] - misalignment_pressure * 0.4)
        dependency_risk = min(1.0, self.config["dependency_risk"] + misalignment_pressure * 0.2)

        return AlignmentState(
            human_alignment=human_alignment,
            human_ai_alignment=human_ai_alignment,
            dependency_risk=dependency_risk,
        )
