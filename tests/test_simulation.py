"""Smoke tests for the simulation runner."""

import json
from pathlib import Path
import unittest

from decision_analysis.config import load_config
from decision_analysis.simulation import SimulationRunner


class SimulationTests(unittest.TestCase):
    def test_simulation_outputs_metrics(self) -> None:
        config_path = Path(__file__).resolve().parents[1] / "configs" / "example.json"
        config = load_config(config_path)
        runner = SimulationRunner(config)
        result = runner.run()

        for key in [
            "decision_quality",
            "organizational_adaptability",
            "power_distribution",
            "coordination_efficiency",
            "economic_performance",
            "ethical_stability",
            "customer_satisfaction",
            "change_in_value",
            "pnl",
        ]:
            self.assertIn(key, result)

        self.assertIn("history", result)
        self.assertEqual(result["cycles"], config.simulation["cycles"])
        json.dumps(result)  # ensure it is serializable


if __name__ == "__main__":
    unittest.main()
