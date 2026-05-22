"""Environment layer for external conditions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class EnvironmentState:
    pressure: float
    volatility: float
    shock_level: float


class EnvironmentLayer:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    def evaluate(self) -> EnvironmentState:
        market = self.config["market"]
        operational = self.config["operational"]
        stress = self.config["stress"]

        volatility = (
            market["demand_volatility"] * 0.4
            + market["competition_intensity"] * 0.3
            + market["customer_preference_variation"] * 0.2
            + market["market_shocks"] * 0.1
        )
        pressure = (
            stress["crisis_events"] * 0.4
            + stress["economic_downturns"] * 0.3
            + stress["misinformation_environments"] * 0.2
            + stress["adversarial_competitors"] * 0.1
        )
        shock_level = market["market_shocks"] * 0.5 + operational["supply_instability"] * 0.5

        return EnvironmentState(pressure=pressure, volatility=volatility, shock_level=shock_level)
