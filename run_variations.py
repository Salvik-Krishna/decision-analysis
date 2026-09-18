"""
run_variations.py -- systematic grid of ~17 scenarios, small parameter steps.

Varies three axes with small increments (holding the others at baseline):
  - info_quality         : 0.20, 0.35, 0.50, 0.65, 0.80
  - environment_pressure : 0.20, 0.35, 0.55, 0.70, 0.85
  - alignment            : 0.25, 0.40, 0.55, 0.70, 0.85
Plus 4 diagonal scenarios (info and pressure move in opposite directions).

Each scenario: EV rollback + 5000-run Monte Carlo.
Results saved to run_summary.json.

Run:
    python run_variations.py
"""

from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from decision_analysis.decision_tree import rollback, monte_carlo, _apply, DecisionTree, Node, Edge

# ── Tree (same as example_simulation.py build_demo_tree) ──────────────────
def _build_tree() -> DecisionTree:
    n = {
        "root": Node("root", "decision", "Authority structure", [
            Edge("Centralize", "info", pillar="structure",
                 effects={"authority_concentration": +0.40, "adaptability": -0.12,
                          "constraint_capacity": +0.18, "alignment": +0.18,
                          "info_quality": +0.12}),
            Edge("Decentralize", "info", pillar="structure",
                 effects={"authority_concentration": -0.35, "adaptability": +0.18,
                          "constraint_capacity": -0.06, "alignment": -0.08}),
        ]),
        "info": Node("info", "decision", "Info strategy", [
            Edge("Full transparency", "env", pillar="limiting_influence",
                 effects={"info_quality": +0.30, "alignment": +0.10,
                          "environment_pressure": +0.12}),
            Edge("Restrict information", "env", pillar="limiting_influence",
                 effects={"info_quality": -0.10, "alignment": -0.06,
                          "environment_pressure": -0.48, "constraint_capacity": +0.10}),
        ]),
        "env": Node("env", "chance", "Market reaction", [
            Edge("Favorable", "response", prob=0.60,
                 effects={"environment_pressure": -0.22, "alignment": +0.06}),
            Edge("Adverse", "response", prob=0.40,
                 effects={"environment_pressure": +0.28, "alignment": -0.10,
                          "adaptability": -0.05}),
        ]),
        "response": Node("response", "decision", "Response mode", [
            Edge("Human-led", "end", pillar="alignment",
                 effects={"alignment": +0.28, "adaptability": -0.08, "info_quality": +0.05}),
            Edge("AI-led", "end", pillar="alignment",
                 effects={"alignment": +0.05, "adaptability": +0.26, "info_quality": +0.14}),
            Edge("Hybrid", "end", pillar="alignment",
                 effects={"alignment": +0.16, "adaptability": +0.12, "info_quality": +0.09}),
        ]),
        "end": Node("end", "terminal", "Outcome realized"),
    }
    return DecisionTree(n, "root")

PILLAR = {
    "structure":          "Authority",
    "limiting_influence": "Info strategy",
    "alignment":          "Response",
}

def _decisions(trace: list) -> dict:
    out = {}
    for step in trace:
        if step["kind"] == "decision":
            key = PILLAR.get(step["pillar"], step["pillar"])
            out[key] = step["branch"]
        elif step["kind"] == "chance":
            out["Market"] = step["branch"].split("(")[0].strip()
    return out


BASE = {
    "info_quality":            0.50,
    "adaptability":            0.55,
    "authority_concentration": 0.55,
    "alignment":               0.55,
    "constraint_capacity":     0.50,
    "environment_pressure":    0.45,
}

# ── Build grid ────────────────────────────────────────────────────────────
grid = []
for iq in [0.20, 0.35, 0.50, 0.65, 0.80]:
    grid.append(("info", iq, {**BASE, "info_quality": iq}))
for ep in [0.20, 0.35, 0.70, 0.85]:           # 0.55 is near-base; skip
    grid.append(("press", ep, {**BASE, "environment_pressure": ep}))
for al in [0.25, 0.40, 0.70, 0.85]:           # 0.55 is near-base; skip
    grid.append(("align", al, {**BASE, "alignment": al}))
for delta in [-0.20, -0.10, +0.10, +0.20]:    # diagonal: info+, press-
    s = {**BASE,
         "info_quality":        max(0, min(1, BASE["info_quality"] + delta)),
         "environment_pressure":max(0, min(1, BASE["environment_pressure"] - delta))}
    label = "diag+" if delta > 0 else "diag-"
    grid.append((label, abs(delta), s))

# ── Run ───────────────────────────────────────────────────────────────────
tree = build = _build_tree()
scenarios = []

HEADER = (f"{'#':>2}  {'axis':<7} {'val':>5}  "
          f"{'Authority':<12} {'Info strategy':<20} {'Response':<11}  "
          f"{'E[PnL]':>7}  {'p05':>6}  {'p95':>6}")
print()
print("=" * len(HEADER))
print(f"  VARIATION GRID -- CEO departs unexpectedly")
print("=" * len(HEADER))
print(HEADER)
print("-" * len(HEADER))

for i, (axis, val, state) in enumerate(grid, 1):
    ev, trace = rollback(tree, objective="pnl", state=state)
    dec = _decisions(trace)
    mc  = monte_carlo(tree, runs=5000, objective="pnl",
                      policy="optimal", seed=7, initial_state=state)
    ps  = mc["metrics"]["pnl"]
    leaf = next(s for s in trace if s["kind"] == "terminal")
    m    = leaf["metrics"]

    auth  = dec.get("Authority", "?")
    info  = dec.get("Info strategy", "?")
    resp  = dec.get("Response", "?")
    print(f"{i:>2}  {axis:<7} {val:>5.2f}  "
          f"{auth:<12} {info:<20} {resp:<11}  "
          f"{ev:>7.2f}  {ps['p05']:>6.2f}  {ps['p95']:>6.2f}")

    # full trace for embedding in the artifact
    trace_clean = []
    for step in trace:
        trace_clean.append({
            "kind":    step["kind"],
            "label":   step["label"],
            "branch":  step.get("branch", ""),
            "pillar":  step.get("pillar", ""),
            "metrics": step.get("metrics"),
        })

    scenarios.append({
        "id":           i,
        "axis":         axis,
        "val":          round(val, 2),
        "state":        {k: round(v, 3) for k, v in state.items()},
        "decisions":    dec,
        "expected_pnl": round(ev, 4),
        "leaf_metrics": {k: round(v, 4) for k, v in m.items()},
        "mc_pnl":       {k: round(v, 4) for k, v in ps.items()},
        "trace":        trace_clean,
    })

out = {
    "event":     "CEO departs unexpectedly",
    "objective": "pnl",
    "baseline":  BASE,
    "scenarios": scenarios,
}
Path("run_summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print()
print(f"  {len(scenarios)} scenarios --> run_summary.json")
print("=" * len(HEADER))
