"""
Decision-tree demo — one event, five situations.

Same event  : "CEO departs unexpectedly."
Five situations change one or two parameters.
For each, the tree rolls back from that state and shows
which decisions flip and why.

Run:
    python example_simulation.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from decision_analysis.decision_tree import (
    DecisionTree, Node, Edge,
    rollback, monte_carlo, _apply, evaluate_state,
)

# ── Richer tree ───────────────────────────────────────────────────────────
# Branch effects are large enough so different starting states flip choices.
# Three genuine decision points + one chance node.
#
#   [D] Authority structure
#        Centralize  |  Decentralize
#   [D] Information strategy
#        Full transparency  |  Restrict information
#   (C) Market reaction
#        Favorable 0.60  |  Adverse 0.40
#   [D] Response mode
#        Human-led  |  AI-led  |  Hybrid
#   <T> Outcome

def build_demo_tree() -> DecisionTree:
    """
    Tree designed so different starting situations flip the optimal branch.

    Trade-offs encoded:
    - Centralize helps when info_quality is low (single clear voice cuts noise).
      It costs adaptability — bad when environment is hostile.
    - Restrict information dramatically reduces environment_pressure (panic control).
      It costs info_quality — bad when info was already low.
    - Human-led gives a large alignment bonus — most valuable when alignment is
      the bottleneck (bottleneck urgency model in evaluate_state).
    - AI-led gives a large adaptability bonus — most valuable when adaptability
      is the bottleneck (hostile market / budget freeze).
    """
    n = {
        "root": Node("root", "decision", "Authority structure", [
            Edge(
                "Centralize",
                "info",
                pillar="structure",
                effects={
                    "authority_concentration": +0.40,
                    "adaptability":            -0.12,
                    "constraint_capacity":     +0.18,
                    "alignment":               +0.18,  # strong: single clear voice
                    "info_quality":            +0.12,  # clearer signal from unified command
                },
            ),
            Edge(
                "Decentralize",
                "info",
                pillar="structure",
                effects={
                    "authority_concentration": -0.35,
                    "adaptability":            +0.18,
                    "constraint_capacity":     -0.06,
                    "alignment":               -0.08,  # cost: coordination overhead
                },
            ),
        ]),
        "info": Node("info", "decision", "Information strategy", [
            Edge(
                "Full transparency",
                "env",
                pillar="limiting_influence",
                effects={
                    "info_quality":         +0.30,
                    "alignment":            +0.10,
                    "environment_pressure": +0.12,  # cost: bad news travels fast
                },
            ),
            Edge(
                "Restrict information",
                "env",
                pillar="limiting_influence",
                effects={
                    "info_quality":         -0.10,
                    "alignment":            -0.06,
                    "environment_pressure": -0.48,  # large: panic / leak prevention
                    "constraint_capacity":  +0.10,
                },
            ),
        ]),
        "env": Node("env", "chance", "Market reaction", [
            Edge("Favorable", "response", prob=0.60,
                 effects={"environment_pressure": -0.22, "alignment": +0.06}),
            Edge("Adverse",   "response", prob=0.40,
                 effects={"environment_pressure": +0.28, "alignment": -0.10,
                          "adaptability": -0.05}),
        ]),
        "response": Node("response", "decision", "Response mode", [
            Edge(
                "Human-led",
                "end",
                pillar="alignment",
                effects={
                    "alignment":            +0.28,   # large: trust-building
                    "adaptability":         -0.08,   # slower deliberation
                    "info_quality":         +0.05,
                },
            ),
            Edge(
                "AI-led",
                "end",
                pillar="alignment",
                effects={
                    "alignment":            +0.05,
                    "adaptability":         +0.26,   # large: rapid analysis
                    "info_quality":         +0.14,
                },
            ),
            Edge(
                "Hybrid",
                "end",
                pillar="alignment",
                effects={
                    "alignment":            +0.16,
                    "adaptability":         +0.12,
                    "info_quality":         +0.09,
                },
            ),
        ]),
        "end": Node("end", "terminal", "Outcome realized"),
    }
    return DecisionTree(n, "root")


# ── Base state ────────────────────────────────────────────────────────────
BASE_STATE = {
    "info_quality":            0.50,
    "adaptability":            0.55,
    "authority_concentration": 0.55,
    "alignment":               0.55,
    "constraint_capacity":     0.50,
    "environment_pressure":    0.45,
}

# ── Five situations (tweaks on top of base) ───────────────────────────────
SITUATIONS = [
    {
        "id":    "A",
        "name":  "Baseline",
        "desc":  "Neutral org — balanced starting point.",
        "tweaks": {},
    },
    {
        "id":    "B",
        "name":  "Info vacuum",
        "desc":  "Rumours spread; info quality is very low, alignment breaking down.",
        "tweaks": {
            "info_quality": -0.35,
            "alignment":    -0.20,
        },
    },
    {
        "id":    "C",
        "name":  "Hostile market",
        "desc":  "Competitor strikes same week — environment pressure is extreme.",
        "tweaks": {
            "environment_pressure": +0.40,
            "adaptability":         -0.15,
        },
    },
    {
        "id":    "D",
        "name":  "Budget freeze",
        "desc":  "Board freezes spending — constraint capacity is very tight.",
        "tweaks": {
            "constraint_capacity":   -0.40,
            "adaptability":          -0.10,
        },
    },
    {
        "id":    "E",
        "name":  "Strong AI backbone",
        "desc":  "Mature, trusted AI stack — alignment and info quality are high.",
        "tweaks": {
            "alignment":    +0.25,
            "info_quality": +0.20,
            "adaptability": +0.12,
        },
    },
]

OBJECTIVE = "pnl"

PILLAR_LABEL = {
    "structure":          "Authority structure",
    "limiting_influence": "Info strategy",
    "alignment":          "Response mode",
}


def state_for(sit: dict) -> dict:
    s = dict(BASE_STATE)
    for k, dv in sit["tweaks"].items():
        s[k] = round(max(0.0, min(1.0, s[k] + dv)), 3)
    return s


def decisions_from_trace(trace: list) -> dict:
    out = {}
    for step in trace:
        if step["kind"] == "decision":
            pl = PILLAR_LABEL.get(step["pillar"], step["pillar"])
            out[pl] = step["branch"]
        elif step["kind"] == "chance":
            out["Market reaction"] = step["branch"].split("(")[0].strip()
    return out


# ── Run ───────────────────────────────────────────────────────────────────
tree = build_demo_tree()
all_results = []

print()
print("=" * 68)
print(f"  EVENT : CEO departs unexpectedly")
print("=" * 68)

# Tree structure
print()
print("  TREE STRUCTURE")
print()
labels = {"decision": "[D]", "chance": "(C)", "terminal": "<T>"}
order = ["root", "info", "env", "response", "end"]
for nid in order:
    node = tree.nodes[nid]
    indent = "  " * order.index(nid)
    print(f"    {indent}{labels[node.kind]} {node.label}")
    for e in node.edges:
        child = tree.nodes[e.to]
        tag = f"  p={e.prob}" if node.kind == "chance" else ""
        eff = "  ".join(f"{k}({'+' if v>=0 else ''}{v})" for k, v in e.effects.items())
        print(f"    {indent}    |- {e.label}{tag}   [{eff}]")

print()
print("=" * 68)
print("  SITUATION ANALYSIS")
print("=" * 68)

baseline_decisions = None

for sit in SITUATIONS:
    state = state_for(sit)
    ev, trace = rollback(tree, objective=OBJECTIVE, state=state)
    decisions = decisions_from_trace(trace)
    leaf = next(s for s in trace if s["kind"] == "terminal")
    m = leaf["metrics"]
    mc = monte_carlo(tree, runs=8000, objective=OBJECTIVE,
                     policy="optimal", seed=7, initial_state=state)
    ps = mc["metrics"]["pnl"]

    flips = []
    if baseline_decisions:
        for pillar, choice in decisions.items():
            if pillar in baseline_decisions and baseline_decisions[pillar] != choice:
                flips.append(f"{pillar}: {baseline_decisions[pillar]} -> {choice}")
    if baseline_decisions is None:
        baseline_decisions = decisions

    print()
    print(f"  [{sit['id']}] {sit['name']}")
    print(f"      {sit['desc']}")
    if sit["tweaks"]:
        tw = "   ".join(
            f"{k} {'+' if v>=0 else ''}{v}" for k, v in sit["tweaks"].items()
        )
        print(f"      Tweaks: {tw}")
    print()
    for pillar, choice in decisions.items():
        flag = "  ** FLIPPED **" if pillar in [f.split(":")[0] for f in flips] else ""
        print(f"      {pillar:<22}  =>  {choice}{flag}")
    print()
    print(f"      Leaf PnL={m['pnl']:.1f}  change_in_value={m['change_in_value']:.3f}"
          f"  customer_sat={m['customer_satisfaction']:.3f}"
          f"  ethical_stability={m['ethical_stability']:.3f}")
    print(f"      Monte Carlo (8k runs): mean={ps['mean']:.1f}"
          f"  p05={ps['p05']:.1f}  p95={ps['p95']:.1f}")
    if flips:
        print()
        for f in flips:
            print(f"      !! Decision flipped  —  {f}")

    all_results.append({
        "situation": sit["id"] + " " + sit["name"],
        "state": state,
        "optimal_decisions": decisions,
        "expected_pnl": round(ev, 3),
        "leaf": m,
        "mc_pnl": ps,
        "flips_vs_baseline": flips,
    })

# ── Comparison table ──────────────────────────────────────────────────────
print()
print("=" * 68)
print("  COMPARISON TABLE  (* = flipped from Baseline)")
print("=" * 68)
pillars = list(PILLAR_LABEL.values()) + ["Market reaction"]
cw = 16
print()
print(f"  {'Situation':<18}" + "".join(f"{p:<{cw}}" for p in pillars)
      + f"  {'E[PnL]':>7}")
print("  " + "-" * (18 + cw * len(pillars) + 9))

baseline_d = all_results[0]["optimal_decisions"]
for r in all_results:
    row = f"  {r['situation']:<18}"
    for p in pillars:
        val = r["optimal_decisions"].get(p, "-")
        star = "*" if val != baseline_d.get(p) else " "
        row += f"{star}{val[:cw-1]:<{cw-1}}"
    row += f"  {r['expected_pnl']:>7.1f}"
    print(row)

# ── Save ──────────────────────────────────────────────────────────────────
Path("tree_result.json").write_text(
    json.dumps({"event": "CEO departs unexpectedly", "situations": all_results},
               indent=2),
    encoding="utf-8",
)
print()
print("  Saved -> tree_result.json")
