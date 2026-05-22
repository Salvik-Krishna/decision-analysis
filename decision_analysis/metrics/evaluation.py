"""Metrics and evaluation utilities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MetricsSnapshot:
    decision_quality: float
    organizational_adaptability: float
    power_distribution: float
    coordination_efficiency: float
    economic_performance: float
    ethical_stability: float
    customer_satisfaction: float
    change_in_value: float
    pnl: float


def compute_metrics(
    decision_quality: float,
    adaptability: float,
    authority_concentration: float,
    coordination_efficiency: float,
    alignment: float,
    environment_pressure: float,
    constraints_capacity: float,
) -> MetricsSnapshot:
    power_distribution = max(0.0, 1.0 - authority_concentration)
    economic_performance = max(0.0, decision_quality * 0.6 + adaptability * 0.2 + constraints_capacity * 0.2)
    ethical_stability = max(0.0, alignment * 0.7 + power_distribution * 0.3)
    customer_satisfaction = max(0.0, economic_performance * 0.6 + coordination_efficiency * 0.4)
    change_in_value = economic_performance - environment_pressure * 0.2
    pnl = change_in_value * 100.0

    return MetricsSnapshot(
        decision_quality=decision_quality,
        organizational_adaptability=adaptability,
        power_distribution=power_distribution,
        coordination_efficiency=coordination_efficiency,
        economic_performance=economic_performance,
        ethical_stability=ethical_stability,
        customer_satisfaction=customer_satisfaction,
        change_in_value=change_in_value,
        pnl=pnl,
    )
