"""
Decision-tree simulation.

A scenario is modelled as a tree of linked nodes.  Each **decision node** offers
branches ("decision links") that lead to the next step; each branch nudges a
small set of latent organizational factors.  **Chance nodes** branch on
environment reactions with probabilities.  **Terminal nodes** convert the
accumulated latent state into outcomes (customer satisfaction, change in value,
PnL) and the six study dimensions, reusing ``metrics.evaluation.compute_metrics``.

The branches are deliberately the framework's levers:

    Structure          : Centralize  vs  Decentralize authority
    Limiting influence : Full transparency  vs  Restrict information
    Limiting action    : Aggressive (loose)  vs  Constrained (tight)
    Environment        : Favorable  vs  Adverse        (chance)
    Human alignment    : Human-led / AI-led / Hybrid

What the engine does
--------------------
1. **Expected-value rollback** over the tree to find the *optimal policy*
   (which branch to take at every decision node, given the state reached there).
2. **Monte Carlo simulation**: roll the tree out many times under a chosen
   policy, sampling chance nodes, to get outcome *distributions*.

Run:
    python -m decision_analysis.decision_tree
    python -m decision_analysis.decision_tree --runs 20000 --objective pnl
    python -m decision_analysis.decision_tree --tree my_tree.json --out result.json
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .metrics.evaluation import compute_metrics, MetricsSnapshot

# ── Latent state ────────────────────────────────────────────────────────────
# Every factor lives in [0, 1].  Branches apply deltas; we clamp after each step.
_FACTORS = (
    "info_quality",
    "adaptability",
    "authority_concentration",
    "alignment",
    "constraint_capacity",
    "environment_pressure",
)
_BASELINE = {
    "info_quality": 0.55,
    "adaptability": 0.50,
    "authority_concentration": 0.50,
    "alignment": 0.55,
    "constraint_capacity": 0.50,
    "environment_pressure": 0.40,
}


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def _apply(state: Dict[str, float], effects: Dict[str, float]) -> Dict[str, float]:
    new = dict(state)
    for k, dv in effects.items():
        new[k] = _clamp(new.get(k, 0.0) + dv)
    return new


# ── Tree model ──────────────────────────────────────────────────────────────

@dataclass
class Edge:
    label: str
    to: str
    pillar: str = ""                       # framework pillar this branch belongs to
    prob: float = 1.0                      # used only at chance nodes
    effects: Dict[str, float] = field(default_factory=dict)


@dataclass
class Node:
    id: str
    kind: str                              # 'decision' | 'chance' | 'terminal'
    label: str
    edges: List[Edge] = field(default_factory=list)


class DecisionTree:
    def __init__(self, nodes: Dict[str, Node], root: str) -> None:
        self.nodes = nodes
        self.root = root

    # ── construction ────────────────────────────────────────────────────────
    @classmethod
    def from_dict(cls, data: dict) -> "DecisionTree":
        nodes = {
            nid: Node(
                id=nid,
                kind=n["kind"],
                label=n.get("label", nid),
                edges=[Edge(**e) for e in n.get("edges", [])],
            )
            for nid, n in data["nodes"].items()
        }
        return cls(nodes, data["root"])

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "nodes": {
                nid: {"kind": n.kind, "label": n.label, "edges": [asdict(e) for e in n.edges]}
                for nid, n in self.nodes.items()
            },
        }


# ── Outcome model at a leaf ─────────────────────────────────────────────────

def evaluate_state(state: Dict[str, float]) -> MetricsSnapshot:
    """
    Turn an accumulated latent state into the framework's outcome metrics.

    Two real trade-offs are baked in so that stressful starting conditions
    flip the optimal policy:

    1. High authority_concentration + low info_quality is *less* bad than
       low authority_concentration + low info_quality (a single decision-maker
       avoids coordination chaos when information is noisy).
    2. High environment_pressure rewards lower constraint_capacity (agility
       over safety), but ONLY when adaptability is also high; otherwise the
       extra freedom destroys value.
    """
    info  = state["info_quality"]
    adapt = state["adaptability"]
    align = state["alignment"]
    conc  = state["authority_concentration"]
    cap   = state["constraint_capacity"]
    press = state["environment_pressure"]

    # Nonlinear bottleneck model: fixing a weak factor is worth more than
    # strengthening an already-strong one.  This makes the optimal branch depend
    # on which factor is the current constraint (= starting situation).
    #
    # For factor x, effective contribution = x * (1 + urgency(x))
    # where urgency rises as x falls below 0.5 — the scarcer it is, the more
    # each marginal unit is worth.

    def _eff(x: float, weight: float = 0.6) -> float:
        """Effective contribution of factor x with bottleneck urgency."""
        urgency = max(0.0, 0.5 - x) * weight   # 0 when x>=0.5; up to 0.3 when x=0
        return x * (1.0 + urgency)

    # Coordination — decentralization penalized when info is poor.
    noise_penalty = conc * max(0.0, 0.5 - info) * 1.0    # centralization helps when noisy
    coordination  = max(0.0, min(1.0,
        _eff(adapt) * 0.5 + _eff(align) * 0.5
        - conc * 0.20                            # bottleneck cost
        + noise_penalty
    ))

    # Decision quality — strong pressure × loose constraint blows up quality.
    pressure_penalty = press * cap * (1.0 - conc) * 0.55
    decision_quality = max(0.0, min(1.0,
        (_eff(info, 0.7) * 0.55 + _eff(adapt, 0.5) * 0.35 + _eff(align, 0.7) * 0.45)
        / (0.55 + 0.35 + 0.45)
        - pressure_penalty
    ))

    return compute_metrics(
        decision_quality=decision_quality,
        adaptability=adapt,
        authority_concentration=conc,
        coordination_efficiency=coordination,
        alignment=align,
        environment_pressure=press,
        constraints_capacity=cap,
    )


def _objective_value(metrics: MetricsSnapshot, objective: str) -> float:
    return float(getattr(metrics, objective))


# ── Expected-value rollback (optimal policy) ────────────────────────────────

def rollback(
    tree: DecisionTree,
    objective: str = "pnl",
    state: Optional[Dict[str, float]] = None,
    node_id: Optional[str] = None,
) -> Tuple[float, List[dict]]:
    """
    Return (expected objective value, optimal trace) from ``node_id`` given the
    accumulated ``state``.  Decision nodes maximize; chance nodes take the
    probability-weighted expectation.
    """
    state = dict(_BASELINE) if state is None else state
    node = tree.nodes[node_id or tree.root]

    if node.kind == "terminal":
        metrics = evaluate_state(state)
        return _objective_value(metrics, objective), [
            {"node": node.id, "label": node.label, "kind": "terminal",
             "metrics": asdict(metrics)}
        ]

    if node.kind == "chance":
        total = 0.0
        weight = sum(e.prob for e in node.edges) or 1.0
        best_child_trace: List[dict] = []
        for e in node.edges:
            v, _ = rollback(tree, objective, _apply(state, e.effects), e.to)
            total += (e.prob / weight) * v
        # for display, follow the most-likely branch
        likely = max(node.edges, key=lambda e: e.prob)
        _, sub = rollback(tree, objective, _apply(state, likely.effects), likely.to)
        best_child_trace = [{"node": node.id, "label": node.label, "kind": "chance",
                             "branch": f"{likely.label} (p={likely.prob})"}] + sub
        return total, best_child_trace

    # decision node — pick the branch with the highest expected value
    best_v = float("-inf")
    best_edge: Optional[Edge] = None
    best_sub: List[dict] = []
    for e in node.edges:
        v, sub = rollback(tree, objective, _apply(state, e.effects), e.to)
        if v > best_v:
            best_v, best_edge, best_sub = v, e, sub
    trace = [{"node": node.id, "label": node.label, "kind": "decision",
              "branch": best_edge.label, "pillar": best_edge.pillar}] + best_sub
    return best_v, trace


# ── Monte Carlo simulation ──────────────────────────────────────────────────

def simulate_once(
    tree: DecisionTree,
    objective: str,
    policy: str,
    rng: random.Random,
    initial_state: Optional[Dict[str, float]] = None,
) -> Tuple[MetricsSnapshot, List[str]]:
    """One stochastic rollout. policy: 'optimal' | 'random'."""
    state = dict(initial_state) if initial_state else dict(_BASELINE)
    node = tree.nodes[tree.root]
    path: List[str] = []

    while node.kind != "terminal":
        if node.kind == "chance":
            edge = _sample_chance(node.edges, rng)
        elif policy == "random":
            edge = rng.choice(node.edges)
        else:  # optimal — choose max-EV branch from the current state
            edge = max(
                node.edges,
                key=lambda e: rollback(tree, objective, _apply(state, e.effects), e.to)[0],
            )
        path.append(f"{node.label} -> {edge.label}")
        state = _apply(state, edge.effects)
        node = tree.nodes[edge.to]

    return evaluate_state(state), path


def _sample_chance(edges: List[Edge], rng: random.Random) -> Edge:
    total = sum(e.prob for e in edges) or 1.0
    r = rng.random() * total
    acc = 0.0
    for e in edges:
        acc += e.prob
        if r <= acc:
            return e
    return edges[-1]


def monte_carlo(
    tree: DecisionTree,
    runs: int = 10000,
    objective: str = "pnl",
    policy: str = "optimal",
    seed: int = 7,
    initial_state: Optional[Dict[str, float]] = None,
) -> dict:
    rng = random.Random(seed)
    samples: Dict[str, List[float]] = {}
    path_counts: Dict[str, int] = {}
    for _ in range(runs):
        metrics, path = simulate_once(tree, objective, policy, rng, initial_state)
        for k, v in asdict(metrics).items():
            samples.setdefault(k, []).append(v)
        path_counts[" | ".join(path)] = path_counts.get(" | ".join(path), 0) + 1

    summary = {
        metric: {
            "mean": round(statistics.mean(vals), 4),
            "stdev": round(statistics.stdev(vals), 4) if len(vals) > 1 else 0.0,
            "p05": round(_percentile(vals, 5), 4),
            "p95": round(_percentile(vals, 95), 4),
        }
        for metric, vals in samples.items()
    }
    top_paths = sorted(path_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
    return {
        "runs": runs,
        "policy": policy,
        "objective": objective,
        "metrics": summary,
        "top_paths": [{"path": p, "share": round(c / runs, 4)} for p, c in top_paths],
    }


def _percentile(vals: List[float], pct: float) -> float:
    s = sorted(vals)
    k = (len(s) - 1) * pct / 100.0
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


# ── Default scenario tree ───────────────────────────────────────────────────

def default_tree() -> DecisionTree:
    """A hybrid human-AI governance scenario: a material event hits the firm."""
    n = {
        "root": Node("root", "decision", "Material event hits the firm - set authority structure", [
            Edge("Centralize authority", "info_c", "structure",
                 effects={"authority_concentration": +0.25, "adaptability": -0.05}),
            Edge("Decentralize authority", "info_d", "structure",
                 effects={"authority_concentration": -0.20, "adaptability": +0.12}),
        ]),
        "info_c": Node("info_c", "decision", "Information strategy", [
            Edge("Full transparency", "act_c", "limiting_influence",
                 effects={"info_quality": +0.20, "alignment": +0.05}),
            Edge("Restrict information", "act_c", "limiting_influence",
                 effects={"info_quality": -0.20, "alignment": -0.08}),
        ]),
        "info_d": Node("info_d", "decision", "Information strategy", [
            Edge("Full transparency", "act_d", "limiting_influence",
                 effects={"info_quality": +0.22, "alignment": +0.07}),
            Edge("Restrict information", "act_d", "limiting_influence",
                 effects={"info_quality": -0.18, "alignment": -0.06}),
        ]),
        "act_c": Node("act_c", "decision", "Action constraints", [
            Edge("Aggressive (loose constraints)", "env", "limiting_action",
                 effects={"constraint_capacity": +0.20, "environment_pressure": +0.08}),
            Edge("Constrained (tight constraints)", "env", "limiting_action",
                 effects={"constraint_capacity": -0.18, "environment_pressure": -0.05}),
        ]),
        "act_d": Node("act_d", "decision", "Action constraints", [
            Edge("Aggressive (loose constraints)", "env", "limiting_action",
                 effects={"constraint_capacity": +0.22, "environment_pressure": +0.10}),
            Edge("Constrained (tight constraints)", "env", "limiting_action",
                 effects={"constraint_capacity": -0.16, "environment_pressure": -0.04}),
        ]),
        "env": Node("env", "chance", "Environment / market reaction", [
            Edge("Favorable", "align", "environment", prob=0.55,
                 effects={"environment_pressure": -0.20, "adaptability": +0.05}),
            Edge("Adverse", "align", "environment", prob=0.45,
                 effects={"environment_pressure": +0.25, "alignment": -0.05}),
        ]),
        "align": Node("align", "decision", "Human-AI alignment approach", [
            Edge("Human-led", "end", "alignment",
                 effects={"alignment": +0.10, "adaptability": -0.03}),
            Edge("AI-led", "end", "alignment",
                 effects={"alignment": +0.05, "adaptability": +0.08, "info_quality": +0.05}),
            Edge("Hybrid", "end", "alignment",
                 effects={"alignment": +0.15, "adaptability": +0.04}),
        ]),
        "end": Node("end", "terminal", "Outcome realized"),
    }
    return DecisionTree(n, "root")


# ── Pretty printing ─────────────────────────────────────────────────────────

def print_tree(tree: DecisionTree) -> None:
    glyph = {"decision": "[D]", "chance": "(C)", "terminal": "<T>"}
    seen: set = set()

    def walk(nid: str, prefix: str) -> None:
        node = tree.nodes[nid]
        for i, e in enumerate(node.edges):
            last = i == len(node.edges) - 1
            conn = "`-" if last else "|-"
            tag = f" p={e.prob}" if node.kind == "chance" else ""
            child = tree.nodes[e.to]
            print(f"{prefix}{conn} {e.label}{tag}  -> {glyph[child.kind]} {child.label}")
            if e.to not in seen:
                seen.add(e.to)
                walk(e.to, prefix + ("   " if last else "|  "))

    root = tree.nodes[tree.root]
    print(f"{glyph[root.kind]} {root.label}")
    walk(tree.root, "")


# ── CLI ─────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Decision-tree simulation")
    ap.add_argument("--tree", type=Path, default=None, help="JSON tree file (optional)")
    ap.add_argument("--runs", type=int, default=10000, help="Monte Carlo rollouts")
    ap.add_argument("--objective", default="pnl",
                    help="Metric to optimize/report: pnl, change_in_value, "
                         "customer_satisfaction, decision_quality, ethical_stability, …")
    ap.add_argument("--policy", default="optimal", choices=["optimal", "random"])
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path, default=None, help="Write JSON results")
    args = ap.parse_args()

    if args.tree:
        tree = DecisionTree.from_dict(json.loads(args.tree.read_text(encoding="utf-8")))
    else:
        tree = default_tree()

    print("=" * 64)
    print("DECISION TREE")
    print("=" * 64)
    print_tree(tree)

    print("\n" + "=" * 64)
    print(f"OPTIMAL POLICY  (rollback, maximizing {args.objective})")
    print("=" * 64)
    ev, trace = rollback(tree, objective=args.objective)
    for step in trace:
        if step["kind"] == "decision":
            print(f"  [D] {step['label']:<42} => {step['branch']}  ({step['pillar']})")
        elif step["kind"] == "chance":
            print(f"  (C) {step['label']:<42} => {step['branch']}")
        else:
            m = step["metrics"]
            print(f"  <T> {step['label']}")
            print(f"      pnl={m['pnl']:.2f}  change_in_value={m['change_in_value']:.3f}  "
                  f"customer_sat={m['customer_satisfaction']:.3f}")
    print(f"\n  Expected {args.objective} (optimal policy): {ev:.4f}")

    print("\n" + "=" * 64)
    print(f"MONTE CARLO  ({args.runs:,} runs, policy={args.policy})")
    print("=" * 64)
    mc = monte_carlo(tree, runs=args.runs, objective=args.objective,
                     policy=args.policy, seed=args.seed)
    print(f"  {'metric':<28}{'mean':>9}{'stdev':>9}{'p05':>9}{'p95':>9}")
    print(f"  {'-'*28}{'-'*9:>9}{'-'*8:>9}{'-'*8:>9}{'-'*8:>9}")
    for metric, s in mc["metrics"].items():
        print(f"  {metric:<28}{s['mean']:>9.3f}{s['stdev']:>9.3f}{s['p05']:>9.3f}{s['p95']:>9.3f}")
    print("\n  Most-traveled paths:")
    for p in mc["top_paths"]:
        print(f"    {p['share']*100:>5.1f}%  {p['path']}")

    if args.out:
        result = {"optimal": {"expected_value": ev, "trace": trace}, "monte_carlo": mc,
                  "tree": tree.to_dict()}
        args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nResults written -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
