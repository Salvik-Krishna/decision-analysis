# Decision Analysis — Formal Problem Statement & Framework

## 1. Problem statement

We study **decision-making in organizations governed jointly by humans and AI
systems**. A decision is taken inside an organizational structure, under
informational and resource constraints, by agents whose objectives are only
partially aligned. The same nominal decision can produce very different
outcomes depending on *how influence is limited*, *how action is limited*, and
*how the organization is structured and aligned*.

**Central question.** How do the controllable properties of an organization —
its information regime, its constraint regime, its structure, and its
human–AI alignment — causally shape (i) the quality and outcomes of decisions
and (ii) the emergent systemic properties of the organization?

Formally, we posit a (stochastic) map

```
        Φ
   Θ  ────▶  (Y, Z)
```

from a **control/configuration space** `Θ` to an **outcome space** `Y` and a
**latent systemic-property space** `Z`. The research program is to characterize
`Φ`: estimate effects, find stable/unstable regimes, and identify
configurations that are Pareto-good across `Y` and `Z`.

The framework is realized in two complementary instruments:
1. a **synthetic simulator** (`decision_analysis/layers/…`) that *generates*
   `Φ` from mechanistic assumptions, and
2. a **real-world dataset** (`decision_dataset`) of observed corporate decisions
   against which proxies for `Θ, Y, Z` are *measured*.

---

## 2. Formal objects

Let an organization at time `t` be a tuple

```
S_t = ⟨ A, G_t, x, E_t ⟩
```

- **`A`** — set of agents, partitioned `A = H ∪ M` into humans `H` and AI models
  `M`. Each agent `a` carries a parameter vector (rationality, risk preference,
  cooperation, trust, and — for `m ∈ M` — optimization objective, explainability,
  alignment score, override-resistance, reward-exploitation tendency).
- **`G_t`** — the **organizational structure**: a directed authority graph over
  `A` with hierarchy depth, span of control, authority concentration, and
  decentralization index.
- **`x`** — the **control vector** (the levers we vary), detailed in §3.
- **`E_t`** — the **environment**: market volatility, competition, shocks,
  resource availability, regulatory and adversarial pressure.

A **decision** is the unit of observation:

```
d = ⟨ a, t, c, u, ω ⟩
```

an agent `a` selecting action `u ∈ U(c)` from a feasible set in context `c`,
yielding realized outcome `ω`. `U(c)` is itself shaped by the constraint regime
(§3.2) — *limiting action narrows `U`*.

---

## 3. The framework — three control pillars

The control vector partitions into the three pillars of the framework,
`x = (x_inf, x_act, x_str)`, plus a control/alignment overlay `x_align`.

### 3.1 Limiting influence  (`x_inf`)
Operators that attenuate, delay, or bias the **information and incentive
signal** reaching a decision. Let `σ*` be the ground-truth signal; the agent
acts on a corrupted signal

```
σ̂ = T_inf(σ* ; x_inf),     x_inf = (delay, incomplete_visibility,
                                      reporting_bias, misinformation,
                                      transparency, comm_noise,
                                      incentive_weights)
```

`T_inf` lowers information quality and tilts incentives (profit vs. ethical vs.
short-term vs. metric-gaming). *Limiting influence = choosing `T_inf`.*

### 3.2 Limiting action  (`x_act`)
The **constraint set** that restricts the feasible action space:

```
U(c ; x_act) ⊆ U_full(c),   x_act = (budget, authority_boundaries,
                                      time_pressure, legal, ethical,
                                      comm_restrictions, approval_requirements)
```

*Limiting action = choosing how tightly `U` is bound.*

### 3.3 Structure of the organisation  (`x_str`)
The shape of `G_t`: `hierarchy_depth, span_of_control, authority_concentration,
decentralization_index, approval_requirements`. Structure governs who may
decide, how information routes, and where bottlenecks form.

### 3.4 Controlling the situation — Human alignment  (`x_align`)
Alignment is a *dynamic* overlay, not a static lever. With misalignment
pressure `π` from incentives:

```
human_human(t+1)  = max(0, hh(t) − 0.3·π)
human_ai(t+1)     = max(0, ha(t) − 0.4·π)
dependency_risk(t+1) = min(1, dr(t) + 0.2·π)
```

The framework distinguishes three alignment sub-questions:
- **With human** — `human_human_alignment`, `human_ai_alignment` (measurable).
- **Intent of model** — does `m ∈ M` pursue the *intended* objective vs. a
  proxy it can game (`ai_optimization_objective`, `ai_reward_exploitation`)?
- **Comparison (personalities)** — how outcomes vary across agent
  personality/parameter profiles, holding `(x_inf, x_act, x_str)` fixed.

> **Identifiability note.** *Intent of model* and *personality comparison* are
> only observable in the **simulator** (we control `m`'s objective and persona).
> In the real `decision_dataset` they have no proxy and are left NULL.

---

## 4. Decision engine and outcomes

### 4.1 Decision formation
A decision's intrinsic quality is a weighted combination of the corrupted
signal quality, structural adaptability, and alignment, normalized by the
weights, with realized action strength gated by the constraint capacity:

```
q(d)  = ( w_I·info_quality + (1−w_R)·adaptability + w_A·alignment )
        / ( w_I + (1−w_R) + w_A )
a_str = clip( q(d) · constraint_capacity , 0, 1 )
```

### 4.2 Analysing outcome  (`Y`)
The outcome vector the framework cares about:

```
Y = ( customer_satisfaction , change_in_value , pnl )
```

- **Change in value** — `economic_performance − λ·environment_pressure`.
- **PnL** — monetized change in value.
- **Customer satisfaction** — function of economic performance and coordination
  efficiency (simulator); requires an external survey source for real data.

---

## 5. Study dimensions  (`Z`)

The six emergent properties under study, each defined as a **latent construct**
and given a **measurable proxy** in each instrument.

| # | Dimension | Construct (what it means) | Simulator measure | `decision_dataset` proxy |
|---|-----------|---------------------------|-------------------|--------------------------|
| 1 | **Decision quality** | Goodness of decisions vs. ground truth | `q(d)` | +30d abnormal price reaction (market verdict) |
| 2 | **Organizational adaptability** | Capacity to reconfigure under pressure | structural adaptability term | reconfig-event rate (leadership+restructuring, 24m) |
| 3 | **Power distribution** | Dispersion of decision authority | `1 − authority_concentration` | normalized named-officer count |
| 4 | **Alignment dynamics** | Evolution of human–human / human–AI alignment | `human_ai_alignment(t)` trajectory | sign-agreement of pre-drift vs post-reaction |
| 5 | **Coordination efficiency** | Friction-free joint action | trust × (1 − bottleneck_risk) | consistency of +1d vs +30d reaction / follow-on round speed |
| 6 | **Ethical stability** | Resistance to ethical drift | `0.7·alignment + 0.3·power_distribution` | inverse of trailing regulatory/compliance incidents |

---

## 6. Research questions & hypotheses

- **RQ1 (Influence).** Does tightening `x_inf` (more delay/bias/gaming) degrade
  decision quality faster than it degrades outcomes — i.e. is the market/agent
  fooled before it is hurt? *H1: `∂q/∂bias < 0` and `∂Y/∂bias` lags `∂q/∂bias`.*
- **RQ2 (Action).** Is there an interior optimum of constraint tightness — too
  loose breeds risk, too tight breeds paralysis? *H2: `Y` is concave in `x_act`.*
- **RQ3 (Structure).** Does authority concentration trade decision *speed* for
  *power distribution* and *ethical stability*? *H3: `∂coordination/∂concentration
  > 0` while `∂ethical_stability/∂concentration < 0`.*
- **RQ4 (Alignment).** Under what incentive pressure `π` does alignment collapse
  (a phase transition in `human_ai_alignment`)? *H4: ∃ threshold `π*`.*
- **RQ5 (Intent / personality).** Holding structure fixed, how much outcome
  variance is attributable to model intent and agent personality? (simulator
  only.)

---

## 7. Empirical instantiation — the dataset

The `decision_dataset` table operationalizes `(Θ, Y, Z)` for **real observed
decisions** (one row = one SEC 8-K filing or startup funding event):

| Theory object | Dataset columns |
|---------------|-----------------|
| `x_inf` — limiting influence | `source_credibility`, `source_domain`, `pre_event_drift_5d` |
| `x_act` — limiting action | `is_material`, `regulatory_constraint`, `action_class` |
| `x_str` — structure | `exec_count`, `leadership_turnover_24m`, `restructuring_24m` |
| `x_align` — alignment/control | `leadership_change_flag`, `alignment_with_market` |
| `Y` — outcome | `change_in_value_{1d,5d,30d}`, `primary_pnl`, `volume_reaction_5d`, `customer_proxy` |
| `Z` — study dimensions | `decision_quality`, `organizational_adaptability`, `power_distribution`, `alignment_dynamics`, `coordination_efficiency`, `ethical_stability` |

**Estimation.** With one row per decision `d`, estimate effects of the form

```
Y_d = β·x_d + γ·(sector, year fixed effects) + ε_d
```

(and analogously for each `Z` component), using event-study abnormal returns as
the outcome and the framework factors as regressors. The simulator supplies the
counterfactuals the observational data cannot (randomized `x_inf, x_act, x_str`,
controlled model intent and personality), enabling identification of `Φ`.

---

## 8. Scope and honesty boundaries

- Real market data measures **outcomes** well (prices, valuations) and
  **structure/influence/action** partially; it does **not** observe model
  intent, agent personality, or surveyed customer satisfaction — those are
  simulator-only or require additional data sources.
- Study-dimension proxies are transparent heuristics (see `dataset.py`), meant
  as **features/labels to model**, not as ground truth.
