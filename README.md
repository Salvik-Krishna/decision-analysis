# Decision Analysis Framework

This codebase is a scaffold for studying organizational decision dynamics, human-AI interaction, information and incentive effects, and systemic stability. It mirrors the layered architecture you outlined and provides a minimal simulation loop with measurable outputs.

## What is included

- Modular layers: environment, organization, agents, information, incentives, constraints, decision engine, interaction, alignment
- Metrics: decision quality, organizational adaptability, power distribution, coordination efficiency, economic performance, ethical stability, customer satisfaction, change in value, PnL
- JSON configuration files for experiments
- CLI runner
- Basic tests

## Quick start

```bash
python -m decision_analysis.cli --config configs/example.json
```

Optional output file:

```bash
python -m decision_analysis.cli --config configs/example.json --output run_summary.json
```

## Where to extend

- Add richer behavioral models in `decision_analysis/layers/`
- Expand metrics in `decision_analysis/metrics/evaluation.py`
- Introduce experimental conditions as additional configs in `configs/`
- Add temporal dynamics and learning in `decision_analysis/simulation.py`

## Layer mapping to the framework

- Environment layer: `decision_analysis/layers/environment.py`
- Organizational structure: `decision_analysis/layers/organization.py`
- Agent population: `decision_analysis/layers/agents.py`
- Information and incentive systems: `decision_analysis/layers/information.py`, `decision_analysis/layers/incentives.py`
- Decision engine: `decision_analysis/layers/decision_engine.py`
- Interaction and negotiation: `decision_analysis/layers/interaction.py`
- Alignment: `decision_analysis/layers/alignment.py`
- Measurement: `decision_analysis/metrics/evaluation.py`

## Testing

```bash
python -m unittest tests/test_simulation.py
```
