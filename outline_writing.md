# Outline Writing Guide (Reusable Across Projects)

This document helps an agent (or human) reliably produce a **strong, reviewer-ready outline** from project artifacts (README/dev docs/code). It is designed to work for:
- Systems / platform / workflow papers
- Algorithm / model / architecture papers
- Theory-heavy papers

The goal is to prevent “generic outlines” by forcing a structured extraction step and concrete section commitments.

===============================================================================
0) Inputs you should have
===============================================================================
Minimum:
- `README.md` (what the system/method does)
- A technical guide / design doc (architecture, algorithm details, assumptions)
- A minimal code map (entrypoints + core modules)

Optional (recommended):
- Experiment logs/results
- `assumed_results.json` (only if drafting with placeholder numbers)

===============================================================================
1) Step 1 — Build the Project IR (Intermediate Representation)
===============================================================================
Extract the following fields before drafting the outline. Keep each answer short and concrete.

## 1.1 Problem & Scope
- Task: inputs → outputs, prediction/optimization target, units/types.
- Scope: what is in-scope and explicitly out-of-scope.
- Constraints: data size regime, noise/corruption, latency/compute limits, privacy, etc.

## 1.2 Core novelty (explicit, user-anchored if provided)
Provide:
- **User-provided core novelty** (if given; copy verbatim first).
- **Agent-inferred novelty** (from artifacts; 1–3 sentences).
- **Final novelty** (choose one; 1–3 sentences).
- **Novelty scope guardrails** (2–5 bullets: what it is NOT claiming).
- **Novelty → contributions mapping** (3–6 bullets): each contribution must validate some facet of the novelty.

Rules:
- If user-provided novelty exists, it has the highest priority.
- The agent may propose a better framing, but must not silently replace the user novelty; ask for confirmation if meaning changes.

## 1.3 Why existing approaches are insufficient
- Pick 2–4 concrete failure modes (e.g., instability at small n, fragile pipelines, cost, non-determinism).
- Tie each failure mode to a specific class of baselines.

## 1.4 What you built (components and boundaries)
- Components/modules (3–8 items) with 1-line responsibilities each.
- Execution model: training loop? inference-only? orchestration graph? theorem/proof stack?
- Artifacts: what gets saved (configs, splits, logs, reports, models).
- **Mathematical formulation readiness**: For algorithm/model papers, identify which components need mathematical formalization (objectives, update rules, constraints, etc.).

## 1.5 Contributions (candidate list)
Write 5 candidates; later you will keep the best 3–5.
Each candidate must be verifiable by: algorithm, theorem, or experiment.

## 1.6 Evaluation plan (even if not executed yet)
- Datasets: names, sizes, task types.
- Protocol: splits, seeds, CV, scaffold split, etc.
- Metrics: primary + secondary.
- Baselines: at least 4–8 appropriate methods.
- Ablations: isolate each novel component.
- Robustness/sensitivity: corruptions, data size sweep, hyperparameter sweep, etc.

## 1.7 Assumed results (optional)
If using placeholder numbers:
- Confirm a single source of truth file exists (e.g., `assumed_results.json`).
- Mark which plots/tables will be **Assumed**.

===============================================================================
2) Step 2 — Select the Primary Paper Type (one only)
===============================================================================
Pick exactly one primary type; use others as supporting sections.

- Systems/platform/workflow: emphasize reliability, orchestration, end-to-end evaluation.
- Algorithm/model: emphasize method novelty, ablations, strong empirical comparisons.
- Theory: emphasize assumptions, theorems, proofs; empirics only to validate regimes/intuition.

===============================================================================
3) Step 3 — Use the Appropriate Outline Skeleton
===============================================================================
Each section must include:
- 3–8 bullet commitments (what will be said, not “we discuss …”)
- planned figures/tables (names only)
- evidence status: real vs assumed vs planned

-------------------------------------------------------------------------------
3.1 Systems / Platform / Workflow Outline Skeleton
-------------------------------------------------------------------------------
## Title (working)
- [1-line title; avoid buzzwords; include core mechanism + domain]

## Abstract (150–220 words)
- Problem setting and why it is hard operationally
- Key idea (system abstraction)
- 3 contributions (system, method, evaluation)
- Results summary (real or explicitly assumed/planned)

## 1. Introduction
- Problem + operating conditions (small/messy/evolving data, tool failures)
- Why training-centric / script-centric pipelines fail in practice
- What the platform enables (capabilities + boundaries)
- Contributions (3–5 bullet points)

## 2. Related Work
- Pipeline/workflow systems
- Domain modeling baselines (models/AutoML)
- Agentic orchestration (with explicit distinction: bounded vs open-ended)

## 3. System Overview
- Architecture: tiers/modules
- Data/control flow
- Artifact story (what is saved, reproducibility)
- Figure: “Overall workflow”

## 4. Orchestration / Execution Model
- State machine / scheduler / policy
- Bounded recovery (retry budget, skip/clarify/report)
- Failure taxonomy and handling
- Figure: “State machine” or “decision paths”

## 5. Core Modeling / Inference Component (as needed)
- What statistical engine is used and why it matches constraints
- Inputs/outputs and interfaces
- Any local selection/retrieval mechanism
- Complexity/latency

## 6. Experiments
- Benchmarks (accuracy)
- Efficiency (time-to-model, throughput, compute)
- Robustness suite (corruptions, schema drift, tool outages)
- Ablations (remove orchestrator, remove modeling component, etc.)
- Tables: main results, runtime, robustness, ablation

## 7. Discussion
- What worked and why (connect to failure modes)
- Where it fails; operational tradeoffs
- How to extend (future work grounded in the system boundaries)

## 8. Limitations
- Explicit limitations: modality, assumptions, scaling, external dependencies

## 9. Conclusion
- 2–4 sentences summary; no new claims

-------------------------------------------------------------------------------
3.2 Algorithm / Model / Architecture Outline Skeleton
-------------------------------------------------------------------------------
## Title
- Method name + what it does + key setting

## Abstract
- Problem
- Key idea (method)
- Contributions (3 bullets)
- Results summary (real/assumed/planned)

## 1. Introduction
- Problem and motivation
- Why existing methods are insufficient (2–3 concrete points)
- Contributions (3–5 bullets)

## 2. Related Work
- Closest methods (by mechanism)
- Baselines (by paradigm)
- Differentiation (what is actually new)

## 3. Problem Setup
- Notation, inputs/outputs
- Objective and constraints
- Any special data regime assumptions

## 4. Method
- High-level idea
- Detailed algorithm/model
- **Mathematical formulation** (CRITICAL: must use formal mathematical language)
  - Problem formulation as mathematical objective
  - All algorithmic components expressed as equations/formulas
  - Update rules, constraints, and optimization procedures in mathematical notation
  - Formal definitions of all variables, functions, and operators
- Pseudocode (complements, not replaces, the mathematical formulation)
- Complexity analysis

## 5. Theoretical Analysis (optional)
- Formal statements if applicable
- Proof sketch (appendix for full proofs)

## 6. Experiments
- Datasets + protocol
- Baselines + implementation details
- Main results table(s)
- Ablations (each novelty)
- Sensitivity (hyperparameters, data size, noise)
- Error analysis

## 7. Discussion + Limitations
- Why it works
- Failure cases
- Practical considerations

## 8. Conclusion

-------------------------------------------------------------------------------
3.3 Theory Outline Skeleton
-------------------------------------------------------------------------------
## Title
- Theoretical object + result type + setting

## Abstract
- Problem and assumptions in one sentence
- Main theorem(s) and meaning
- (Optional) empirical validation summary

## 1. Introduction
- Motivation and what is unknown in prior work
- Contributions: theorem statements (informal) + novelty

## 2. Related Work
- Prior theory, closest results, gaps

## 3. Preliminaries
- Definitions and notation
- Assumptions (explicit, numbered)

## 4. Main Results
- Theorems/lemmas/propositions (clear statements)
- Intuition for each result

## 5. Proof Sketches (Full proofs in Appendix)
- High-level proof strategy
- Key technical lemmas

## 6. Empirical Validation (optional)
- What qualitative claim is validated (regime boundaries, scaling, etc.)
- Minimal experiments; no over-claiming

## 7. Limitations and Scope

## 8. Conclusion

===============================================================================
4) Evidence Tagging (Required)
===============================================================================
For every planned figure/table and every quantitative claim, tag it:
- **Real**: measured in project artifacts
- **Assumed**: from `assumed_results.json` (must be explicitly marked Assumed)
- **Planned**: described as future work; no numbers

===============================================================================
4.5) Experimental Section Constraints (Mandatory for Domain-Specific Papers)
===============================================================================

Required approach for outline:
- In the "Experiments" section bullets, describe methodology accurately but use generic terms:
  - "Evaluation on standard benchmark datasets"
  - "Experiments on multiple benchmark targets"
  - "Comparison against baselines on widely-adopted evaluation protocols"
- When listing datasets/tasks in the outline, use generic identifiers:
  - "Benchmark Dataset 1", "Benchmark Dataset 2", or
  - "Standard evaluation targets", "Multiple benchmark sets"
- Maintain methodological detail (protocols, metrics, splits) while anonymizing specific targets.

Quality check for outline:
- Verify no actual target names appear in experimental section bullets.
- Ensure methodology is accurately represented using generic benchmark framing.

===============================================================================
1) Prompt Template (Outline-only Mode)
===============================================================================
Use this when asking an agent to draft an outline:

- Task: produce a reviewer-ready outline only (no full prose).
- Inputs: README/dev-docs + assumed-results policy.
- Output: chosen paper type + outline skeleton with section bullets + figure/table plan + evidence tags.


