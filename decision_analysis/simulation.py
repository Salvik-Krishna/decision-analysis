"""Simulation runner that connects all layers."""

from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Any, List

from .config import Config
from .layers.environment import EnvironmentLayer
from .layers.organization import OrganizationLayer
from .layers.agents import AgentPopulation
from .layers.information import InformationLayer
from .layers.incentives import IncentiveLayer
from .layers.constraints import ConstraintLayer
from .layers.decision_engine import DecisionEngine
from .layers.interaction import InteractionLayer
from .layers.alignment import AlignmentLayer
from .metrics.evaluation import compute_metrics


class SimulationRunner:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.environment_layer = EnvironmentLayer(config.environment)
        self.organization_layer = OrganizationLayer(config.organization)
        self.agent_layer = AgentPopulation(config.agents)
        self.information_layer = InformationLayer(config.information)
        self.incentive_layer = IncentiveLayer(config.incentives)
        self.constraint_layer = ConstraintLayer(config.constraints)
        self.decision_engine = DecisionEngine(config.decision_engine)
        self.interaction_layer = InteractionLayer(config.interaction)
        self.alignment_layer = AlignmentLayer(config.alignment)

    def run(self) -> Dict[str, Any]:
        cycles = self.config.simulation["cycles"]
        history: List[Dict[str, Any]] = []

        for _ in range(cycles):
            env_state = self.environment_layer.evaluate()
            org_effects = self.organization_layer.compute_effects()
            agent_profile = self.agent_layer.summary_profile()
            info_quality = self.information_layer.quality()
            misalignment_pressure = self.incentive_layer.alignment_pressure()
            constraints_capacity = self.constraint_layer.capacity()
            alignment_state = self.alignment_layer.evolve(misalignment_pressure)
            decision = self.decision_engine.decide(
                info_quality=info_quality,
                adaptability=org_effects.adaptability,
                alignment=alignment_state.human_ai_alignment,
                constraints=constraints_capacity,
            )
            coordination = self.interaction_layer.coordination_efficiency(
                trust=agent_profile.trust,
                bottleneck_risk=org_effects.bottleneck_risk,
            )
            metrics = compute_metrics(
                decision_quality=decision.quality,
                adaptability=org_effects.adaptability,
                authority_concentration=self.config.organization["authority_concentration"],
                coordination_efficiency=coordination,
                alignment=alignment_state.human_ai_alignment,
                environment_pressure=env_state.pressure,
                constraints_capacity=constraints_capacity,
            )

            history.append(asdict(metrics))

        summary = _aggregate(history)
        summary["cycles"] = cycles
        summary["history"] = history
        return summary


def _aggregate(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    totals: Dict[str, float] = {}
    for snapshot in history:
        for key, value in snapshot.items():
            totals[key] = totals.get(key, 0.0) + float(value)

    return {key: value / max(1, len(history)) for key, value in totals.items()}
