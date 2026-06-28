# T7 — Ranking library and pair selection: design proposal

> Draft. Authored by Gerard Martínez Canelles. Pre-implementation document for [issue #7](https://github.com/Softcatala/arena-cat/issues/7). Branch: `feature/T7_ranking`.

This document has **two audiences**:

1. **Reviewers** (Jordi, the team) — sections 1, 6, 7, 8 are the executive summary, the proposed module split, the open questions, and the plan.
2. **Gerard** (me, learning) — sections 2–5 are a long-form pedagogical walkthrough of the algorithms with worked examples in plain English. Skip if you already know Bradley-Terry / Elo / bootstrap CIs.

---

## Contents

1. [Executive summary](#1-executive-summary)
2. [What questions does the issue actually ask?](#2-what-questions-does-the-issue-actually-ask)
3. [Crash course: how the ranking algorithms work](#3-crash-course-how-the-ranking-algorithms-work)
   - [3.1. Raw pairwise win rates](#31-raw-pairwise-win-rates)
   - [3.2. Bradley-Terry](#32-bradley-terry)
   - [3.3. Elo](#33-elo)
   - [3.4. TrueSkill / OpenSkill](#34-trueskill--openskill)
   - [3.5. Side-by-side comparison](#35-side-by-side-comparison)
4. [Pair selection: random vs adaptive](#4-pair-selection-random-vs-adaptive)
5. [How do we know "we have enough votes"?](#5-how-do-we-know-we-have-enough-votes)
6. [Proposed design](#6-proposed-design)
7. [Open questions for the team](#7-open-questions-for-the-team)
8. [Plan ahead](#8-plan-ahead)

---

## 1. Executive summary

Issue #7 asks for a library that answers three questions:

1. Which model pair should the next user evaluate?
2. What is the current ranking?
3. Have we collected enough votes to trust the ranking?

After reading the project docs and the issue, my recommendation is:

| Question | Recommendation for Fita 1 (n=3 models) |
|---|---|
| **Q1 — next pair** | **Quota-balanced randomization** over (category, prompt, unordered_pair, side). Pick uniformly among currently underfilled cells. Behind a `TaskSampler` protocol so we can swap in active sampling later. |
| **Q2 — ranking** | **Raw pairwise stats as the primary public artifact**, with **per-category Bradley-Terry** as a secondary summary. BT fitted with our own ~30-line `scipy.optimize` solver, validated against `choix` in unit tests. |
| **Q3 — confidence** | **Prompt-cluster bootstrap with fixed labels** from the original fit. Report P(best is best), CI for current best minus strongest competitor, bootstrap rank distribution. |
| **Stopping rule** | `FixedBudgetRule` default for Fita 1 (we need the full dataset for the public release). `AdaptiveStoppingRule` implemented but not enabled — requires sequential-testing correction before production. |
| **ρ estimation** | Demoted from stopping logic to **sensitivity analysis** (a slider in the simulador, not a fitted parameter). With 10 prompts × 13 votes, a beta-binomial MLE is unstable. |
| **Library choice** | Direct `scipy.optimize` BT fit in production; `choix` as a test-time reference for validation only. TrueSkill/OpenSkill not used — they're optimized for online matchmaking, not transparent offline inference with cluster awareness. |

**Why raw pairwise stats are primary, not BT:** for n=3 models with ~133 votes per cell, BT's variance reduction over raw pairwise is ~33% in the symmetric case and falls toward 5% when one model dominates. Public communication is also cleaner: "Gemma beat Qwen in 73 of 120 decisive votes (61%, 95% CI [52%, 69%])" requires no model. BT is a useful secondary check and starts paying off in Fita 2+ when n grows.

**Why quota-balanced randomization, not iid uniform:** iid uniform over 90 (category × prompt × pair) cells with 1,200 votes gives Poisson variance per cell (≈3.6 SD on a mean of 13.3). After complaining about clustering, accepting that level of cell imbalance is self-defeating. Quota-balanced randomization is **not** outcome-adaptive — it depends only on accumulated counts, not on who's winning — so it doesn't trigger the *Leaderboard Illusion* critique.

**Why TrueSkill/OpenSkill are wrong fit (precise version):** both libraries are configurable enough to set drift to zero — the strong claim "they always inflate variance" is wrong. The real critique is that they're **designed for online ranking and matchmaking in games**, not for transparent offline inference over a fixed evaluation design. They don't naturally handle prompt clustering, tie/neither semantics, or fixed-quota sampling — the things that actually matter for us.

The substantive contribution of this task is **not the library choice** — it's the combination of **quota-balanced sampling** (to keep cells balanced) and **prompt-cluster bootstrap with fixed labels** (to get honest uncertainty estimates). The existing simulator's ±8.5% margin is a sensitivity calculation conditional on assumed ρ; under plausible ρ values (0.1–0.5) the per-cell margin is plausibly 13–23% (see [analysis/dimensioning.py](../analysis/dimensioning.py)).

---

## 2. What questions does the issue actually ask?

The full task body from [issue #7](https://github.com/Softcatala/arena-cat/issues/7):

> Implement a library that answers:
> - Which is the next pair of models to evaluate for the user?
> - What is the current ranking of the models?
> - What confidence do we have in the current ranking / have we reached enough evaluations (per category)?
>
> Evaluate using openskill, trueskill or similar. Create simulation scripts.

Reading carefully, this is **two separate concerns wedged into one issue**:

| Concern | Type | Stakes |
|---|---|---|
| **Pair selection** (Q1) | Online, runs on every API request | Low — wrong choice slightly biases sampling |
| **Ranking + confidence** (Q2, Q3) | Offline / periodic, runs on the full dataset | High — drives the public ranking and the stopping decision |

These should be **two modules**, not one. They have different testing needs, different update frequencies, and don't have to share a library.

---

## 3. Crash course: how the ranking algorithms work

This section is the long pedagogical walkthrough. Skip if you know these algorithms.

### 3.1. Raw pairwise win rates

**The simplest possible thing.** For every (model_A, model_B, category), count how many times A won and divide by total votes.

#### Worked example (correcció category)

Suppose after some voting we have:

| Match-up | Votes for A | Votes for B | Ties |
|---|---|---|---|
| Qwen vs Salamandra | 73 | 47 | 10 |
| Qwen vs Gemma | 60 | 60 | 10 |
| Salamandra vs Gemma | 30 | 90 | 10 |

(Ignoring ties for simplicity: many BT formulations drop them.)

Raw win rates:
- Qwen vs Salamandra: 73 / (73 + 47) = **60.8%** for Qwen
- Qwen vs Gemma: 60 / 120 = **50.0%** (tie at population level)
- Salamandra vs Gemma: 30 / 120 = **25.0%** for Salamandra (Gemma dominates)

**What's good about this:** transparent, no model assumptions, easy to put a binomial confidence interval on each pair.

**What's bad about this:**
1. **No global ranking.** You have three independent comparisons; combining them into a single skill score is informal.
2. **No transitivity sharing.** If Qwen beats Salamandra and Salamandra loses to Gemma, this evidence doesn't update our belief about Qwen vs Gemma.
3. **No CIs across pairs.** You can put a CI on each pair, but combining them into "the ranking is reliable" requires another step.

#### Confidence interval (Wilson, the right one to use)

For a single pair with `wins` out of `n` votes:

```python
p_hat = wins / n
ci_low, ci_high = wilson_ci(wins, n, confidence=0.95)
```

This is what the `simulador/index.html` is computing (approximately). The issue is that **n here is votes, not prompts** — so the CI is too tight when votes within a prompt are correlated. See section 5.

---

### 3.2. Bradley-Terry

**The idea:** assign each model a single number — its **skill** `θ_i`. The probability that model A beats model B is:

```
P(A beats B) = exp(θ_A) / (exp(θ_A) + exp(θ_B))
            = sigmoid(θ_A - θ_B)
```

This is just **logistic regression with model identity as the only feature**. If you've done classification in Python, you know this. If `θ_A = θ_B`, P(A wins) = 0.5. If `θ_A − θ_B = log(2) ≈ 0.69`, A wins 2/3 of the time. If the gap is `log(9) ≈ 2.2`, A wins 90% of the time.

#### Worked example: fitting BT by hand-wavy intuition

Using the data from §3.1, BT would assign skills like:

| Model | Skill `θ` (illustrative) | Interpretation |
|---|---|---|
| Gemma | +0.6 | strongest |
| Qwen | +0.2 | middle |
| Salamandra | −0.8 | weakest |

These don't have absolute meaning — only **differences** matter (BT is shift-invariant). What matters is `θ_Gemma − θ_Salamandra = 1.4`, which corresponds to `sigmoid(1.4) ≈ 80%` probability of Gemma winning, matching the 90/120 = 75% observed.

#### How BT is fitted in practice

Maximum likelihood, usually by **iterative algorithms** (MM, Newton, or simply gradient descent in PyTorch). The `choix` library does this for us:

```python
import choix

# Build a list of (winner_id, loser_id) pairs, ignoring ties.
data = [(qwen, salamandra)] * 73 + [(salamandra, qwen)] * 47 + ...

# Fit BT
skills = choix.ilsr_pairwise(n_models, data, alpha=0.01)
# → array like [0.2, -0.8, 0.6] for [qwen, salamandra, gemma]
```

`ilsr_pairwise` = Iterative Luce Spectral Ranking, an efficient solver. `alpha` is a small regularizer to keep things stable when one model has 0 wins or losses.

#### The transitivity argument (why BT is "better than raw")

Imagine we have 100 votes on (Qwen vs Salamandra) and 100 on (Salamandra vs Gemma), but **only 5 on (Qwen vs Gemma)** because the random sampler hasn't hit it much yet.

- **Raw approach:** for (Qwen vs Gemma), we have a CI based on n=5. Very wide.
- **BT approach:** even with 5 direct votes, the skills `θ_Qwen` and `θ_Gemma` are both *anchored* by the 200 votes that involve Salamandra. The implied (Qwen vs Gemma) probability is much better estimated than 5 votes alone would suggest.

This is the "transitivity savings" the README mentions. The savings grow with `log₂(n)/(n−1)`:

| n models | BT reduction factor | Savings |
|---|---|---|
| 2 | 1.00 | 0% |
| 3 | 0.79 | 21% |
| 5 | 0.58 | 42% |
| 10 | 0.37 | 63% |
| 20 | 0.23 | 77% |

For **Fita 1 (n=3), BT gives us a 21% reduction**. For Fita 2+ with 10+ models, it becomes much more valuable.

#### When BT fails

BT assumes a **single global axis** of skill. If reality is "Gemma is much better at correcció but Qwen is much better at traducció", a single global BT will smear both. **This is exactly why we fit BT per category, not globally** — see §6.

---

### 3.3. Elo

**Same model as BT, but fitted online with a simple update rule.**

Each model starts at e.g. 1500. After a match where A beats B:

```
expected_A = 1 / (1 + 10^((rating_B - rating_A) / 400))
rating_A += K * (1 - expected_A)
rating_B += K * (0 - expected_B)
```

Where K is a "learning rate" (typically 16–32 in chess).

**Worked example:**
- Both at 1500. A beats B.
- `expected_A = 1 / (1 + 10^0) = 0.5`.
- `rating_A += K * (1 - 0.5) = 0.5K`. With K=32, A goes to 1516, B drops to 1484.

**Why Elo isn't the right primary tool for us:**

1. **Order-dependent.** If you replay the same 200 votes in a different order, you get different final ratings. BT (fitted in batch) is order-independent.
2. **The K parameter is arbitrary.** Too high → noisy ratings. Too low → ratings don't track the data. There's no principled way to set K for a snapshot evaluation.
3. **The 400 scaling is a chess convention.** It's the same model as BT under the hood, just with a different parameterization (`log(10) / 400`).

**Where Elo is useful for us:** as a **cheap online estimate** for pair-selection during voting, computed on the fly without re-fitting a full BT model. But the public ranking should use offline BT.

LMSYS Chatbot Arena reports both — see their blog post on the method.

---

### 3.4. TrueSkill / OpenSkill

**Bayesian extension of Elo where each player has a (mean, variance) instead of a single rating.**

- TrueSkill: Microsoft, designed for Xbox Live matchmaking.
- OpenSkill: open-source replacement, similar API.

The mean is the estimate; the variance shrinks as more matches are observed. A new player starts with high variance ("we don't know"). After matches, the variance decreases.

**The problem for us:** both libraries model **dynamic skill** — they assume a player's true skill drifts over time, and they have parameters like "dynamics factor" or "tau" that govern how much variance is *added back* after each match to prevent the system from getting too confident.

But our models are **frozen snapshots**. Salamandra 7B's skill at correcció does not drift. Adding dynamics noise is not just unnecessary — it's actively harmful: it inflates variance and gives wider confidence intervals than the data justifies.

**Conclusion:** TrueSkill/OpenSkill solve a problem we don't have. The issue's suggestion to use them probably reflects which libraries are best-known, not which fits the statistical setting.

---

### 3.5. Side-by-side comparison

| Property | Raw win rates | Bradley-Terry | Elo | TrueSkill/OpenSkill |
|---|---|---|---|---|
| Global ranking | ❌ | ✅ | ✅ | ✅ |
| Transitivity sharing | ❌ | ✅ | ✅ | ✅ |
| Order-independent | ✅ | ✅ | ❌ | ❌ |
| Online updates | n/a | costly (refit) | cheap | cheap |
| Models dynamic skill | n/a | ❌ | weakly | ✅ |
| Easy CI from bootstrap | ✅ | ✅ | trickier | trickier |
| Fits our setting | partial | **best** | OK for online | overkill |

---

## 4. Task selection (correcting an earlier misreading)

When a user opens the app, the server must pick a **task** — a tuple of `(category, prompt, unordered_model_pair, side_assignment)` — to show them. The unit is not just a model pair: the prompt, the category, and which model is shown on the left vs right all matter.

### 4.1. Three candidates

| Strategy | How it picks | Pros | Cons |
|---|---|---|---|
| **iid uniform random** | Sample uniformly among all 90 (category × prompt × pair) cells, randomize side | Simple, unbiased | iid creates Poisson cell-count variance — some cells will have 5 votes, others 25, on a budget of 13. Self-defeating given our clustering concern. |
| **Quota-balanced random** | Sample uniformly among cells currently below the target count, randomize side. Avoid showing the same session the same cell twice. | Same statistical properties as uniform in expectation; cell counts converge to exactly equal. | Slightly more state in the sampler. |
| **Active sampling (Chiang 2024 rule)** | Probability ∝ `√(σ²/n) − √(σ²/(n+1))` — favors under-evaluated, high-variance pairs | ~30%+ vote savings; what Chiang and Singh both recommend. | Requires running BT estimate at sampling time; needs disclosure. |

### 4.2. The Leaderboard Illusion paper: what it actually says

I read Singh et al. 2025 carefully. **My earlier framing in this doc was wrong.** The paper's critique is **not** "adaptive sampling is bad". It is:

> *"undisclosed sampling rates that systematically over-represent a handful of proprietary providers"* (Section 4.1, paraphrased).

The paper's **Recommendation 4** is **to implement** the active sampling rule from Chiang et al. 2024 (FastChat Section 5, Eq. 9), arguing it "effectively prioritizes under-evaluated and high-variance pairs, aligning sampling with the goal of rapidly reducing uncertainty in rankings". The paper criticizes Chatbot Arena for **claiming** to do this but not actually deploying it.

So adaptive sampling is fine if: (a) it's based on uncertainty / under-sampling, not on rank closeness for its own sake, and (b) the strategy is publicly disclosed.

### 4.3. Recommendation

**For Fita 1: quota-balanced randomization, behind a `TaskSampler` protocol.** Reasons:
- It eliminates the iid-uniform imbalance problem essentially for free.
- It's not adaptive in any sense and has no disclosure burden.
- The savings from active sampling at n=3 with a fixed 1,200-vote budget are modest. We're better off spending complexity on bootstrap correctness.

**For Fita 2+: active sampling becomes attractive.** The Chiang et al. rule is implemented as a second strategy (`UncertaintyDrivenSampler`) and can be turned on via config, with the strategy disclosed on the public ranking page.

```python
# task_sampler.py

class TaskSampler(Protocol):
    """Estratègia per triar la propera tasca completa: (categoria, prompt, parella, costat)."""
    def select_next_task(self, session: Session) -> Task: ...


class QuotaBalancedSampler:
    """Tria uniformement entre cel·les (categoria, prompt, parella) que encara no han
    arribat al quota. Estratègia per defecte a la Fita 1."""

class UncertaintyDrivenSampler:
    """Implementa la regla de Chiang et al. 2024 (FastChat §5, eq. 9):
    P(a) ∝ √(σ²/n_a) − √(σ²/(n_a+1))
    Requereix una estimació actual de skills. Cal disclosure pública si s'activa."""

class DiversityWeightedSampler:
    """Quota-balanced però amb pesos dels prompts segons la diversitat dels outputs
    (vegeu §11.1). Els pesos són pre-calculats i no depenen de cap rànquing."""
```

**Side randomization is mandatory for all strategies** to avoid position bias. The sampler picks `side_assignment ∈ {A, B}` uniformly per task and does not canonicalize the order in the DB.

---

## 5. How do we know "we have enough votes"?

This is the **most underspecified** part of issue #7 and where careful statistics matters most.

### 5.1. The naive answer (what the simulator does)

For each (pair × category) cell, compute a binomial CI on the win rate:

```python
margin = z * sqrt(0.25 / n_votes)  # worst case at p=0.5
```

For 133 votes → 8.5% margin. **Stop when margin < target.**

This is wrong when votes within a prompt are correlated, which they are.

### 5.2. The cluster-aware answer

The Kish design effect formula:

```
N_effective = N_raw / (1 + (k − 1) * ρ)
```

- `k` = votes per prompt
- `ρ` = intra-prompt correlation (how much the prompt determines the verdict)

For Fita 1 with ρ ≈ 0.3, the per-cell margin is **plausibly 18%, not 8.5%** — but note this is a sensitivity calculation conditional on assumed ρ, not an empirical truth. With only 10 prompt clusters per category, even with the design effect properly accounted for, the small number of clusters limits the precision of any uncertainty estimate. The asymptotic z = 1.96 approximation is also optimistic at 10 clusters.

See the full analysis in [analysis/dimensioning.py](../analysis/dimensioning.py) and the four graphs in `analysis/out/`. The right way to communicate this publicly is **"under plausible ρ ∈ [0.1, 0.5], the margin is 13–23%"**, not "the true margin is 18%".

### 5.3. Operational confidence rule (and a bug fix)

**The actual question we want to answer per category:** "Is our currently-best model reliably better than the next-best competitor?"

This is *not* the same as "is the gap between rank 1 and rank 2 large?", because rank 1 and rank 2 can swap across bootstrap replicates. An earlier draft of this doc had a bug here: sorting skills inside each bootstrap replicate forces the gap to be non-negative by construction, which falsely declares stability even when the ranking is unstable.

**The fixed-labels cluster bootstrap (correct version):**

```python
# Original: 10 prompts per category (each with many votes)
# Step 1: Fit BT once on the full data to identify the *current* best.
theta_hat = fit_bt(all_votes_in_category)
best_model = argmax(theta_hat)
competitor_models = [m for m in models if m != best_model]

# Step 2: Resample whole prompts with replacement, refit BT each time,
# track the SAME model's gap (not the resampled rank 1).
deltas = []
for _ in range(n_bootstrap):
    sampled_prompts = random.choices(prompts_in_category, k=len(prompts_in_category))
    sampled_votes = flatten(p.votes for p in sampled_prompts)
    theta_b = fit_bt(sampled_votes)
    delta_b = theta_b[best_model] - max(theta_b[m] for m in competitor_models)
    deltas.append(delta_b)  # CAN BE NEGATIVE — that's the point

# Step 3: Two complementary summaries.
ci_lo, ci_hi = np.percentile(deltas, [2.5, 97.5])
p_best_is_best = np.mean([d > 0 for d in deltas])
ranking_is_stable = ci_lo > 0
```

**Why this works:** if the current best is genuinely better, most bootstrap replicates will still show it ahead → `p_best_is_best` close to 1 and `ci_lo > 0`. If the current best is barely ahead and the ranking is fragile, many replicates will show a different model ahead → `delta_b` goes negative in those replicates → `ci_lo < 0` and `p_best_is_best` near 0.5.

**Two complementary numbers, not one:**
- `p_best_is_best` — easy to communicate. "Gemma is the best model in correcció with 87% confidence."
- `ci_lo, ci_hi` — formal CI on the skill gap. Used in the stopping rule.

**Important caveats** (worth flagging in any public communication):
1. With **only 10 prompt clusters**, the cluster bootstrap is more honest than iid bootstrap, but it is not magic — cluster bootstrap with very few clusters has known small-sample issues.
2. The bootstrap accounts for **prompt-level dependence** only. **Session-level dependence** (one volunteer casting many votes) is a separate source of correlation we should report on but not fold into the bootstrap until v2 (when we have users).
3. The rule "**Pr(current best is best) > 95%**" is *not* the same as "**we have detected a statistically significant gap**" — be careful in public framing.

### 5.4. ρ is not in the public confidence story

`ρ` stays as a **sensitivity slider** in the simulador and an internal diagnostic. We do **not** fit a single ρ from the data and publish a confidence claim that depends on it — with 10 prompts × 13 votes, the beta-binomial MLE is unstable and a single ρ would hide several distinct sources of dependence (prompt difficulty, model-prompt interaction, session effects, position bias, category ambiguity). Treat ρ as a "what-if" tool, not as a parameter we estimate.

---

## 6. Proposed design

### 6.1. Module split

```
backend/app/ranking/
    __init__.py
    task_sampler.py     # Q1: pick next (category, prompt, pair, side) — quota-balanced default
    ranking.py          # Q2: raw pairwise stats + per-category BT (scipy.optimize, ~30 LOC)
    confidence.py       # Q3: fixed-label cluster bootstrap, P(best is best), stopping rules
    types.py            # dataclasses, kept free of SQLAlchemy
```

**Design constraint:** the core types and functions consume plain dataclasses or dataframes, not SQLAlchemy ORM rows. The API layer is responsible for translating ORM rows into core types. This keeps the math testable in isolation and avoids coupling ranking logic to the DB session.

Plus simulation scripts under `scripts/`:

```
scripts/
    simulate_ranking.py     # Drive the full pipeline end-to-end on synthetic data
    benchmark_methods.py    # Compare BT vs raw win rates on real-ish data
```

### 6.2. Public API (sketch)

#### Task sampler — Strategy pattern

To avoid technical debt later, we expose a `TaskSampler` protocol with three interchangeable implementations. The microservice picks one at startup via configuration. We start with `QuotaBalancedSampler` for Fita 1 and can switch to weighted or active sampling later without API changes.

```python
# task_sampler.py

class TaskSampler(Protocol):
    """Estratègia per triar la propera tasca completa:
    (categoria, prompt, parella, costat_A_o_B)."""
    def select_next_task(self, session_id: str | None) -> Task: ...


class QuotaBalancedSampler:
    """Tria uniformement entre cel·les (categoria, prompt, parella) per sota del quota.
    Randomitza el costat (A/B). Evita repetir la mateixa cel·la per a una sessió.
    Estratègia per defecte a la Fita 1."""

class DiversityWeightedSampler:
    """Quota-balanced, però amb pesos pre-calculats segons la diversitat
    dels outputs dels models per a aquell prompt (vegeu §11.1).
    Els pesos són fixos durant la campanya — no depenen dels vots acumulats."""

class UncertaintyDrivenSampler:
    """Implementa la regla d'active sampling de Chiang et al. 2024 (FastChat §5, eq. 9):
    P(a) ∝ √(σ²/n_a) − √(σ²/(n_a+1))
    Recomanat per Singh et al. 2025 com a remei a les biaixos de sampling.
    Requereix una estimació actual de skills; cal disclosure pública si s'activa."""


# ranking.py
@dataclass
class CategoryRanking:
    category_code: str
    bt_skills: dict[str, float]              # model → BT skill
    raw_win_rates: dict[tuple[str, str], float]  # (a, b) → P(a beats b)
    n_votes: int
    n_prompts: int

def compute_rankings(session: Session) -> list[CategoryRanking]:
    """Fit BT i calcula les estadístiques per cada categoria."""
    ...

# confidence.py
# Hi ha dues maneres d'usar la confiança:
#   - "report-only": col·lectar votes fins al budget i reportar la confiança final.
#   - "stopping rule": parar quan el CI bootstrap sobre el gap rank1-rank2 exclou zero.
# Implementem totes dues; la microservei tria via configuració.
@dataclass
class ConfidenceReport:
    category_code: str
    rank1_vs_rank2_skill_gap_ci: tuple[float, float]
    is_ranking_stable: bool
    estimated_rho: float
    naive_margin: float
    clustered_margin: float

def assess_confidence(
    session: Session,
    category_code: str,
    n_bootstrap: int = 1000,
) -> ConfidenceReport:
    """Bootstrap clustered per categoria; estima ρ a partir de les dades."""
    ...


class StoppingRule(Protocol):
    """Decideix si una categoria ha rebut prou vots."""
    def should_stop(self, session: Session, category_code: str) -> bool: ...


class FixedBudgetRule:
    """Para quan s'arriba a `votes_target` per cel·la. Estratègia per defecte a la Fita 1.
    Permet alliberar un dataset complet i comparable entre categories."""
    def __init__(self, votes_target_per_cell: int = 133): ...

class AdaptiveStoppingRule:
    """Para una categoria quan el CI bootstrap sobre rank1-rank2 exclou zero.
    Més eficient en hores humanes; introdueix biaix de 'peeking' si no es controla
    amb correcció seqüencial (alpha-spending) — implementació posterior si cal."""
    def __init__(self, min_votes_per_cell: int = 50, alpha: float = 0.05): ...
```

### 6.3. Dependencies to add

```toml
[project.dependencies]
numpy = "^1.26"
scipy = "^1.11"             # BT MLE via scipy.optimize.minimize; Wilson CIs; bootstrap stats

[project.optional-dependencies]
dev = [
    "choix = ^0.3",         # Reference BT implementation; used only in unit tests
]
```

**Why scipy in production, choix only in tests.** The BT log-likelihood is ~30 lines in pure scipy with a sum-to-zero constraint and an explicit L2 regularization parameter `alpha` whose meaning is unambiguous. `choix` is excellent but its `alpha` semantics are algorithm-dependent (pairwise pseudo-counts in MM solvers, L2/Gaussian in scipy-based solvers), which makes it slightly less transparent for our use case. We use it in unit tests to validate our scipy fit against an independent implementation on planted data.

**Complete separation guard.** If a model wins 0 or all decisive comparisons against another model in some category (possible with sparse data), the plain BT MLE diverges. The L2 regularization handles this gracefully; we test for it explicitly.

No frontend changes. No DB changes (the existing schema in `models.py` is sufficient).

### 6.4. TDD plan

Following the project convention (`AGENTS.md`), tests come first. In English identifiers, Catalan docstrings:

```python
# tests/test_pair_selector.py
def test_select_next_task_returns_two_distinct_models():
    """Comprova que la parella retornada té dos models diferents."""

def test_select_next_task_is_uniform_over_pairs():
    """Sobre molts mostratges, la distribució de parelles és aproximadament uniforme."""

# tests/test_ranking.py
def test_bt_recovers_planted_skills():
    """Amb dades sintètiques generades amb skills coneguts, BT els recupera dins l'error."""

def test_bt_handles_tie_votes():
    """Els empats no fan petar el solver; opcionalment es descompten o es divideixen."""

# tests/test_confidence.py
def test_clustered_bootstrap_wider_than_naive():
    """Quan ρ > 0, el CI clusteritzat és més ampli que el binomial."""

def test_stable_ranking_with_decisive_data():
    """Si un model guanya el 90% de votes a tots els altres, is_ranking_stable=True."""

def test_unstable_ranking_with_coin_flip_data():
    """Si totes les parelles són 50/50, is_ranking_stable=False."""
```

### 6.5. Why this design beats the literal issue #7

| What issue #7 says | What we propose | Why |
|---|---|---|
| "Use openskill / trueskill" | Direct scipy BT fit + choix-as-test-reference | openskill / trueskill are tuned for online matchmaking, not transparent offline inference |
| Single library | Three modules (sampler, ranking, confidence) | Different stakes, different test patterns. Sampler doesn't depend on BT; BT doesn't depend on bootstrap. |
| "Confidence in the ranking" | **Fixed-label** cluster bootstrap on `θ_best − max(θ_others)`, plus P(best is best) | Earlier "sort-and-take-top-2-gap" version had a sign bug; this one allows negative deltas and correctly reflects rank instability |
| Implicit: iid uniform sampling | Quota-balanced randomization | iid creates Poisson cell imbalance on small budgets; quota-balanced doesn't trigger Leaderboard Illusion either way |
| Simulation scripts | Plus benchmark of BT vs raw + adversarial cases | We show empirically that BT savings are ~33% in the symmetric case at n=3, falling toward 5% when one model dominates |

### 6.6. Other product / methodology considerations

| Concern | Handling |
|---|---|
| **Position bias (A vs B side)** | Side randomized per task by the sampler. Audit metric: per-model A-vs-B win-rate difference, reported in `confidence.py` outputs. |
| **Session-level clustering** | `session_id` tracked, reported as a concentration metric (max votes per session, Herfindahl index). Not folded into the bootstrap until v2 introduces users. |
| **Tie vs neither** | Reported as **separate** rates. For BT input: drop both. For raw stats: half-credit for tie, exclude neither (not half-credit, because neither means "neither is acceptable" not "they're equivalent"). |
| **Category code immutability** | `cultura → reformulacio` (commit `439463a`) is a real rename. Category **codes** must be immutable for longitudinal analysis; display names can change. Flag this convention in `AGENTS.md` and our module README. |
| **Model versioning in public outputs** | The public ranking exports `model + inference_metadata.{seed, temperature, top_p, quantization, model_version}` so the result can't be retroactively attributed to a different checkpoint. The data is already in the schema (`Response.inference_metadata`). |
| **Cycle detection** | With n=3 raw pairwise can produce a cycle (A>B>C>A) that BT smooths away. Report when this happens — it's a meaningful signal about heterogeneity, not a bug. |

---

## 7. Open questions for the team

Before implementation starts, I'd like to confirm:

**Q1.** Do we want **per-category** rankings, **global**, or **both**? The README implies per-category but doesn't say it explicitly.
> **My recommendation:** per-category is the product question. Global is a nice-to-have.

**Q2.** Is the team OK with **random uniform** pair selection, or do you want adaptive? I argue strongly for random — see §4.
> **My recommendation:** implement **both** behind a `PairSelector` protocol (§6.2) and ship `UniformRandomSelector` as the Fita 1 default. This way we can switch to adaptive later via config without a new PR. Adaptive will require public disclosure to avoid the Leaderboard Illusion critique (see `leaderboard_illusion_response.md`).

**Q3.** How do we handle **ties and "neither"** votes? Three options:
- (a) Drop them entirely.
- (b) Count a tie as half a win for each side.
- (c) Model ties explicitly with a "tie threshold" parameter (Rao-Kupper extension of BT).
> **My recommendation:** (b) for raw win rates, (a) for BT (it's the standard).

**Q4.** What's the **stopping criterion** for Fita 1? Hit the 1,200-vote target regardless, or stop early per-category if the ranking stabilizes?
> **My recommendation:** implement **both** behind a `StoppingRule` protocol (§6.2) and ship `FixedBudgetRule` as the Fita 1 default — we want the full dataset for the public release (`projecte.md` §6.2). `AdaptiveStoppingRule` is wired up for later use, but requires sequential-testing corrections (alpha-spending) before production use to avoid the "peeking" bias.

**Q5.** The "Leaderboard Illusion" concern in the bibliography — Arena Cat's response to each critique is documented in [`leaderboard_illusion_response.md`](leaderboard_illusion_response.md).

---

## 8. Plan ahead

### Phase 0 — Alignment (this doc + review)
- ✅ Branch `feature/T7_ranking` created.
- ⏳ Post this doc as a comment on issue #7 and request feedback from Jordi.
- ⏳ Resolve the 5 open questions in §7.

### Phase 1 — Synthetic validation (no production code yet)
- Write `scripts/simulate_ranking.py` that generates synthetic votes from known model skills with a given ρ.
- Confirm that the cluster bootstrap recovers the right CI width.
- Reproduce the 21% BT savings empirically for n=3 models.
- This is the work that lets us say "this design works" *before* anyone uses it.

### Phase 2 — Implementation (TDD, small PRs)
- PR 1: `pair_selector.py` + tests. Trivial; opens the door.
- PR 2: `ranking.py` (BT per category + raw stats) + tests.
- PR 3: `confidence.py` (cluster bootstrap, ρ estimation, stopping rule) + tests.
- PR 4: Integration test that wires all three modules together on seeded data.

### Phase 3 — Integration with the microservice (issue #6)
- Once issue #6's FastAPI service exists, expose three endpoints:
  - `GET /api/task` calls `pair_selector.select_next_task`.
  - `GET /api/stats` calls `ranking.compute_rankings` + `confidence.assess_confidence`.
  - The `POST /api/vote` already exists per `pla_detallat.md`; just writes to the DB.
- This phase is **out of scope for this task** but the API surface is designed so it slots in cleanly.

### Phase 4 — Documentation
- Update `docs/db_schema.md` if any new tables/views are needed (currently I think we can compute everything from `votes` + `responses` + `prompts` + `categories`).
- Add a short `backend/app/ranking/README.md` explaining the three modules.

### Estimated effort

| Phase | Hours |
|---|---|
| Phase 0 (alignment) | ~3 |
| Phase 1 (synthetic validation) | ~8 |
| Phase 2 (implementation, 4 PRs) | ~20 |
| Phase 3 (FastAPI wiring) | depends on #6 |
| Phase 4 (docs) | ~2 |
| **Total (excluding #6 dependency)** | **~33 hours** |

This fits the ~120-hour Fita 1 budget called out in [README.md](../README.md#fita-1-prova-de-concepte).

---

## 11. Updates after rebase onto main (2026-06-27)

The branch was rebased onto `origin/main` and the issue / PR list was re-checked. Two commits had landed on main since the doc was written; neither affects this design directly:

- `00c5228` — disabled reasoning in `scripts/inferencia.py`, added per-model inference time tracking.
- `39bd981` — removed the `contributors-readme-action` workflow.

Three open items on the repo deserve a mention because they touch our scope.

### 11.1. PR #18 — "Càlcul de diversitat dels prompts" (open, Jordi)

Adds two scripts:
- `scripts/metriques.py` — computes pairwise distances between the three models' outputs on the same prompt, using **chrF** (character n-gram similarity) and **Levenshtein**, both normalized to a 0–1 distance.
- `scripts/analitza_inferencies.py` — produces a `results.txt` that ranks the 30 prompts by how *discriminating* they are (prompts where the three models produce more divergent outputs rank higher).

**Why this matters for our pair selector.** If two models produce nearly identical outputs for a given prompt, a human evaluator cannot meaningfully prefer one. The vote becomes near-50/50 noise, which:
- Wastes human time.
- Inflates the intra-prompt correlation `ρ` we worried about in §5, because the random noise dominates the within-prompt signal.

This is genuinely useful **prior information** that's computable offline, before any vote is collected.

**Two ways to use it (both compatible with §4's "no Leaderboard Illusion" stance):**

| Approach | What it does | Trade-off |
|---|---|---|
| **A — Filter** | Drop prompts where pairwise output similarity is above a threshold (e.g., `chrF_d < 0.15`) | Cleaner stats; smaller dataset |
| **B — Weighted random sampling** | Down-weight (but don't exclude) non-discriminating prompts in the random sampler | Keeps all prompts; biases toward informative ones |

**Important — why this is NOT adaptive sampling in the harmful sense.** The diversity weights are:
- Computed **once** from the pre-generated model outputs.
- **Frozen** before voting starts.
- **Independent** of the current ranking estimate.

The Leaderboard Illusion critique targets samplers that bias toward currently-close-in-ranking pairs *based on accumulating vote data*. A frozen prior on prompt informativeness doesn't do that — it's the same logic as power analysis for test selection, which is standard practice.

**My recommendation:** Once PR #18 merges, use `DiversityWeightedSampler` (the third strategy in §6.2) as an optional config — quota-balanced randomization, but with prompts within each (category, pair) cell sampled in proportion to their pre-computed diversity scores. Implementation in `task_sampler.py`:

```python
# Per (category × pair) cell, pick prompts according to diversity-weighted quota.
# Weights are computed once at startup from PR #18's output, frozen for the campaign.
```

If PR #18 doesn't merge, fall back to plain `QuotaBalancedSampler` (uniform among under-quota cells). No code change required.

**Open question for the team:** is Approach B acceptable, or do you want strict uniform for maximum transparency? My weak preference is B because it makes better use of the volunteer budget.

### 11.2. Issue #6 (microservice) is assigned to Isaac Nicolas

The downstream consumer of our library. Worth coordinating once we land Phase 1 so the API surface is what he needs. **Not verified yet:** whether Isaac has started, whether a draft API contract exists.

**Action:** ping Isaac before locking down `pair_selector.select_next_task` and `ranking.compute_rankings` signatures.

### 11.3. Issue #14 (idempotent DB loader, unassigned) is not a blocker

Without #14 there are no real votes in the DB to test against, but **Phase 1 (synthetic validation)** doesn't need them — we generate votes from planted skills. Real-DB integration belongs in Phase 2 / Phase 3.

### 11.4. Net effect on the design

No breaking changes. Two updates to the plan:

- **§4** — add a follow-up line: "If PR #18 merges before Phase 2, switch the sampler to weighted random based on the diversity scores. The argument against adaptive sampling does not apply to frozen prompt-diversity priors (see §11.1)."
- **§6.4 (test plan)** — add a test: `test_select_next_task_respects_diversity_weights()` if Approach B is taken.

---

---

## 12. Post-review log (2026-06-27)

An external adversarial review (sent to ChatGPT Pro) found a real bug and several places where the original design was less careful than it should have been. This section logs what changed and why.

### 12.1. Bug fixed

The original §5.3 bootstrap code sorted skills inside each replicate and took `sorted[0] - sorted[1]`, which is non-negative by construction. This **falsely declares stability** when the best model swaps with the second across bootstrap replicates. Fix: identify the current best from the full-data fit, then track the **same** model's gap (signed, can go negative) in each replicate. New code in §5.3.

### 12.2. Design changes confirmed and incorporated

| Change | Reason |
|---|---|
| iid random → **quota-balanced random** sampling | iid Poisson variance defeats the clustering analysis on a 13-vote/cell budget |
| Module rename: `pair_selector.py` → `task_sampler.py` | We sample (category, prompt, pair, side), not just a pair |
| Library: `choix` only in tests, scipy direct fit in production | `choix.ilsr_pairwise`'s `alpha` semantics are algorithm-dependent; scipy with explicit L2 is more transparent for ~30 LOC |
| `ρ` demoted from estimated parameter → sensitivity slider | Beta-binomial MLE is unstable on 10 prompts × 13 votes; a single ρ hides multiple distinct sources of dependence |
| Public margin language softened | "Under plausible ρ ∈ [0.1, 0.5], margin ≈ 13–23%" replaces "the true margin is 18%" |
| TrueSkill/OpenSkill critique sharpened | Strong "they inflate variance" claim was wrong (drift is configurable); precise reason is they're tuned for online matchmaking |
| Raw pairwise stats promoted to **primary public artifact** | At n=3 with ~133 votes/cell, BT variance saving is ~33% in symmetric case, drops to ~5% when one model dominates. Public communication is also cleaner without BT. |
| Tie/neither handled separately | Tie = "both comparable"; neither = "both failed". Different signals, separate rates. |
| Position bias / session clustering / cycle detection added to §6.6 | Independent sources of dependence that we should at least report on |

### 12.3. The Leaderboard Illusion paper — correction to my earlier reading

I had framed adaptive sampling as walking into the same critique as Chatbot Arena. After reading Singh et al. 2025 directly (Section 6, Recommendation 4): **the paper recommends adopting** the Chiang et al. 2024 active sampling rule, arguing it "effectively prioritizes under-evaluated and high-variance pairs". The critique is about **undisclosed sampling rates that systematically over-represent proprietary providers**, not about adaptive sampling itself.

This means `UncertaintyDrivenSampler` (the Chiang rule) is a perfectly defensible strategy if turned on later — with public disclosure. [`leaderboard_illusion_response.md`](leaderboard_illusion_response.md) has been updated accordingly.

### 12.4. Revised time estimate

The original ~33 hours was optimistic. Realistic estimate after the review:

| Phase | Hours |
|---|---|
| Phase 0 (this design doc + review) | ~4 (already spent) |
| Phase 1 (synthetic validation, including bootstrap correctness tests) | ~10 |
| Phase 2 (implementation, 4 PRs) | ~25 |
| Phase 4 (docs) | ~2 |
| **Total (excluding #6 dependency)** | **~40** |

Where it's likely to slip: tie/neither semantics with the team, complete-separation handling, deterministic scipy outputs across platforms, A/B side bookkeeping, the cluster-bootstrap edge cases (very few clusters, cycles).

### 12.5. Out of scope, but worth a future ticket

- **Multi-level model** for prompt × model random effects (`u_{p,i}` term). Cleaner conceptually but needs PyMC/Stan, prior-driven with 10 prompts.
- **Davidson tie model** for explicit tie probability in BT. Half-credit is a scoring convention; Davidson is a likelihood model. Defer to Fita 2+ when there's enough data to identify the tie parameter.
- **Adversarial-voting defenses** beyond per-session rate limiting. The Singh paper's limitations section flags this as critical for community benchmarks; defer to v2 (when we have users).

---

## References

- Project docs: [`README.md`](../README.md), [`projecte.md`](../projecte.md), [`pla_detallat.md`](../pla_detallat.md), [`AGENTS.md`](../AGENTS.md)
- Issue: [#7 Biblioteca de rànquing i selecció de parelles](https://github.com/Softcatala/arena-cat/issues/7)
- Related open: [#6 microservei (Isaac)](https://github.com/Softcatala/arena-cat/issues/6), [#14 càrrega idempotent](https://github.com/Softcatala/arena-cat/issues/14), [PR #18 diversitat de prompts](https://github.com/Softcatala/arena-cat/pull/18)
- Schema: [`backend/app/models.py`](../backend/app/models.py), [`docs/db_schema.md`](db_schema.md)
- Sample-size analysis: [`analysis/dimensioning.py`](../analysis/dimensioning.py) and four graphs in `analysis/out/`
- External: [choix docs](https://choix.lum.li/en/latest/), [Bradley-Terry on Wikipedia](https://en.wikipedia.org/wiki/Bradley%E2%80%93Terry_model), [Leaderboard Illusion paper](https://arxiv.org/abs/2504.20879)
