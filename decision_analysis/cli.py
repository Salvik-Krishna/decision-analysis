"""Command-line entrypoint for running simulations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config
from .simulation import SimulationRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run organizational decision simulations")
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to JSON config file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output JSON file for summary",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = load_config(args.config)
    runner = SimulationRunner(config)
    result = runner.run()

    output_text = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(output_text, encoding="utf-8")
    else:
        print(output_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
