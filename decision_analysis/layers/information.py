"""Information layer controls for asymmetry and noise."""

from __future__ import annotations

from typing import Dict, Any


class InformationLayer:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    def quality(self) -> float:
        delay = self.config["information_delay"]
        incomplete = self.config["incomplete_visibility"]
        bias = self.config["reporting_bias"]
        misinformation = self.config["misinformation_injection"]
        noise = self.config["communication_noise"]
        transparency = self.config["transparency_level"]

        degradation = 0.2 * delay + 0.25 * incomplete + 0.2 * bias + 0.2 * misinformation + 0.15 * noise
        quality = max(0.0, min(1.0, transparency - degradation))
        return quality
