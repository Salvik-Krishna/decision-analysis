"""Incentive layer modeling."""

from __future__ import annotations

from typing import Dict, Any


class IncentiveLayer:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    def alignment_pressure(self) -> float:
        ethical = self.config["ethical"]
        profit = self.config["profit"]
        metric = self.config["metric_optimization"]
        short_term = self.config["short_term_focus"]

        misalignment = max(0.0, profit * 0.6 + metric * 0.5 + short_term * 0.4 - ethical * 0.7)
        return min(1.0, misalignment)
