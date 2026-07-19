---
name: restricted-clean-gene-screen
description: Restricted-clean solver strategy for iterative gene-perturbation discovery screens. Use as the harness --skill for BDAbench closed-loop tasks; selects untested actions from public candidates using literature prior plus current-run feedback only.
---

# Restricted-Clean Gene Screen Strategy

You are the **solver**. Choose perturbation actions only from the public candidate action space provided in the harness prompt. Obey the harness output contract exactly.

## Non-negotiable constraints

- Do **not** read local files, manifests, hidden oracle artifacts, prior run directories, or repository code.
- Do **not** invent access to untested scores, ranks, hit labels, thresholds, or dataset identity.
- Use only: the public task brief, the strategy below, and **current-run** feedback returned by the harness.
- Every `Solution:` must contain exactly the requested number of **unique, previously untested** action IDs from the candidate space.
- Never put prose after the `Solution:` line. On repair prompts, return only the `Solution:` line.

## Scientific prior (general, no memorized hit lists)

For exhaustion-resistance / fitness-under-stress screens in engineered immune cells, prefer mechanisms that are biologically plausible under the stated system and perturbation operation:

1. **Stress / exhaustion axis regulators** — pathways that modulate T-cell dysfunction, persistence, or tonic signaling under chronic antigen pressure.
2. **Metabolic fitness** — interventions that support survival, oxidative balance, or nutrient handling during prolonged activation.
3. **Cytokine / co-stimulatory tone** — regulators that reshape activating vs inhibitory signaling without assuming a specific secret gene list.
4. **Epigenetic / transcriptional control of state** — factors that stabilize effector or memory-like programs under the stated perturbation operation (e.g. activation vs knockout).

Treat literature prior as soft guidance for **hypotheses**, not as a ranked answer key. If the prompt's biology differs, reweight these axes to match the stated system and readout.

## Round-0 selection (no feedback yet)

1. Build 3–5 mechanism buckets from the task brief (system + perturbation + readout).
2. Allocate the batch across buckets (avoid putting the entire batch on one narrow hypothesis).
3. Inside each bucket, pick diverse candidate IDs that are clearly in-domain for that mechanism story.
4. Prefer breadth over near-duplicate synonyms of the same idea when IDs allow it.
5. Reserve a minority slice (~15–25%) for exploratory / less obvious candidates so later rounds have contrast.
6. Before emitting `Solution:`, self-check: exact batch size, all unique, none already tested (none yet in round 0).

## Later rounds (with current-run feedback)

1. Separate returned observations into relatively stronger vs weaker outcomes using only the feedback text provided.
2. **Exploit**: enlarge around mechanisms that produced stronger outcomes (related pathway neighbors still untested).
3. **Explore**: keep a minority slice for untouched mechanism buckets so you do not collapse to one local peak too early.
4. Never resubmit an ID already listed as tested in the current run.
5. If feedback is sparse, noisy, or policy-limited, keep wider exploration and do not overfit a single lucky batch.
6. Update Level-1 rationale to cite **this run's** feedback patterns + mechanism hypothesis; do not cite hidden labels.

## Output discipline

### Normal rounds

Return:

1. **Level 1 — Scientific Evidence and Rationale**  
   Short mechanism plan: what you are testing, how prior/feedback shaped the batch, how the batch is diversified.

2. **Level 2 — Executable Action**  
   One line:

```text
Solution: 1. ACTION1, 2. ACTION2, ..., N. ACTIONN
```

`N` must equal the batch size stated in the harness prompt.

### Repair rounds

Return **only**:

```text
Solution: <exactly N unique valid previously untested action IDs>
```

Use membership notes from the harness to replace invalid / duplicate / already-tested IDs. Do not argue with the harness.

## Quality bar for a good batch

- Exact cardinality and parseable `Solution:` line
- All IDs from the public action space; no duplicates; no already-tested IDs
- Mechanism diversity appropriate to the round (broader early, more focused later if feedback supports it)
- Level-1 rationale is about strategy, not about claiming access to hidden truth
