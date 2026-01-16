# Pareto-Guided Multi-Round Agentic Optimization with Interpretable SAR Rule Mining for Peptide Lead Optimization under Weak Feedback  

---

## Abstract

- Lead optimization as a constrained, multi-objective, multi-round decision process under weak, local, noisy, and partially missing feedback
- Core challenge: convert heterogeneous experimental and in silico signals into actionable local edits under strict constraints and evaluation budgets
- Limitation of existing approaches: strong generators underutilize project-specific SAR and constraints; heuristics optimize black-box scores without interpretable evidence and strategy adaptation
- We propose a Pareto-guided, multi-round agentic optimizer grounded by interpretable SAR rule mining and a structured weak-feedback interface
- Hard mechanisms (explicit, reproducible):
  - Structured feedback interface: hierarchical multi-objective scoring with penalties, uncertainty, and missingness-aware fallbacks, exposing a per-candidate score breakdown
  - Pareto-based parent selection and convergence: non-dominated sorting + crowding-distance diversity for parent selection, with plateau-based convergence and max-round stopping
  - Dynamic strategy updates: structured reflection in JSON (with deterministic fallback) controlling exploration vs. exploitation and guiding next-round generation
- Empirical results (aligned with available artifacts): improved sample efficiency, constraint satisfaction, Pareto-front quality (e.g., hypervolume / first-front size), and robustness across feedback regimes

---

## 1. Introduction

### 1.1 Beyond Molecular Generation
- Why lead optimization is fundamentally different from de novo generation
- Iterative decision-making, hypothesis testing, and strategy adaptation
- The need for reasoning-centric optimization frameworks

### 1.2 The Challenge of Learning from Weak Feedback
- Operating conditions (what makes this hard in practice):
  - Small data and high noise: limited experimental measurements and assay variability
  - Multi-assay inconsistency: different assays imply different optimization directions (minimize vs maximize) and trade-offs
  - Expensive evaluation: structure prediction and energy scoring impose compute/time budgets
  - Missing and delayed signals: some metrics are unavailable per candidate/run; feedback may be incomplete or delayed
- Consequence: optimization must be budget-aware, robust to missingness, and able to adapt strategies from weak signals

### 1.3 Our Perspective and Contributions
- Framing lead optimization as learning under weak, structured feedback
- Treating the LLM as a bounded chemist-like planner and explainer, not as a free-form generator:
  - LLM plans edits and explains hypotheses
  - Quantitative signals come from tools/oracles (no hallucinated numbers)
  - Strategy updates are auditable via explicit rules + structured reflection artifacts
- Key contributions:
  - An interpretable SAR rule-mining algorithm that extracts composable mutation rules with quantified effects, builds a rule-compatibility graph via additivity tests, and proposes candidates via clique / transitive-clique / subtraction search
  - A Pareto-guided, multi-round agentic optimization loop that selects parents from Pareto fronts, adapts exploration vs. exploitation via structured reflection, and terminates via explicit convergence criteria
  - A structured weak-feedback interface that unifies multi-source signals (potency, structure, energetics, developability) into auditable outcomes with uncertainty/missingness handling and evidence chains
  - Empirical validation across sparse vs. rich feedback regimes, with ablations isolating each component (rule mining, Pareto selection, reflection, multi-round loop)

---

## 2. Related Work

### 2.1 Structure-/Sequence-Based Generation and Optimization
- Structure-based binder design and inverse folding (e.g., RFDiffusion + ProteinMPNN)
- Sequence-based peptide language models / MLM mutation sampling (sequence grammar / in silico evolution)
- What they miss in this setting: explicit project-specific SAR utilization, constraint-governed multi-round adaptation, and auditable strategy updates

### 2.2 Multi-Objective Optimization under Expensive/Weak Feedback
- NSGA-II and related Pareto-based evolutionary optimizers
- Bayesian optimization / bandit-style methods under limited feedback (as applicable)
- What they miss in this setting: interpretable evidence substrates (SAR rules), structured feedback interfaces tied to real scientific signals, and agentic planning/explanation

### 2.3 Tool-Augmented LLM Agents (Bounded vs. Open-Ended)
- LLM planning with tools; agentic workflows in science
- Distinction: bounded loops with structured state vs open-ended chat agents
- What we add: multi-round optimization as an explicit decision process with structured state, deterministic fallbacks, and auditable artifacts

### 2.4 Reproducibility, Numeric Governance, and Auditability
- Systems for experiment tracking and reproducible pipelines
- What we add: “all quantitative outputs from tools” plus per-round artifacts (records, reflections, convergence decisions) enabling audit and error analysis

---

## 3. Problem Formulation

### 3.1 Optimization as Sequential Decision-Making
- Local edit space and iterative actions (bounded number of mutations per round)
- Partial observability: not all objectives are observable each round/candidate
- Noisy outcomes: assay and oracle noise; inconsistent feedback across objectives

### 3.2 Objectives and Constraints
- Multiple, potentially conflicting objectives (potency, structural quality, developability, etc.)
- Hard constraints (protected positions, max mutation count, ring/closure constraints)
- Soft constraints (penalties for charge, aggregation risk, low backbone confidence)
- Trade-offs are first-class: we track Pareto fronts instead of collapsing everything into a single scalar prematurely

### 3.3 Feedback as a Learning Signal
- Feedback as structured but incomplete information
- No assumption of global validity or consistency
- Goal: learn how to act under uncertainty while preserving interpretable evidence (rules, provenance, and score breakdowns)

### 3.4 Formal Objects (State / Action / Feedback / Cost)
- State \(s_t\): parent set (one or more sequences), SAR evidence summary (trend/SHAP and/or mined rules + provenance), structure/energy guidance, and multi-round history (round records + reflection JSON)
- Action \(a_t\): constrained local edits (mutation sets) respecting protected positions and max-mutation budget; optionally rule-based edits (clique/subtraction proposals)
- Feedback \(o_t\): vector-valued outcomes (potency_score, structural_quality_score, developability_score, plus optional sub-metrics), with uncertainty and missingness; also per-candidate score breakdown and evidence chain
- Cost \(c_t\): evaluation budget (structure prediction calls, energy scoring calls, wall-clock), enabling cost-aware comparisons

---

## 4. Method

### 4.1 Algorithmic Overview

- System view: a bounded LangGraph workflow with explicit modes (Insight / Design / Evaluation) and a multi-round optimization loop in Design mode
- Separation of concerns:
  - Interpretable SAR substrate (trend/SHAP and/or rule mining + provenance)
  - Candidate proposal (rule-based proposals and LLM-guided edits under constraints)
  - Execution and evaluation (structured multi-objective scoring with uncertainty/missingness)
  - Strategy update (Pareto selection + structured reflection + convergence)

---

### 4.2 System / Orchestration Overview (Bounded Agentic Loop)
- Three modes with clear semantic boundaries:
  - Insight: produce SAR evidence and actionable strategies (light vs full)
  - Design: generate candidates, score, select parents, update strategy, iterate
  - Evaluation: critically assess external candidates and provide structured feedback
- Bounded execution: deterministic fallbacks, skip/retry policies, and explicit termination conditions
- Figure: overall workflow diagram (from `paper/README.md`)

---

### 4.3 Interpretable SAR Rule Mining (Evidence Substrate)
- Rule encoding from wild-type → mutant differences and amplification factors
- Additivity test under multiplicative compositionality with tolerance
- Rule-compatibility graph construction and conflict checks
- Candidate generation strategies: Clique (conservative), TransitiveClique (aggressive), Subtraction (deduced-rule exploration)
- Evidence chains: provenance paths and nearest-neighbor context (for audit and follow-up)
- Implementation note: this paper provides mathematical definitions, algorithm blocks, and an interface contract for reproducibility

---

### 4.4 Structured Weak-Feedback Interface (Core)
- Hierarchical multi-objective scoring:
  - Layered score aggregation (e.g., potency / structural quality / developability) with explicit weights
  - Penalty mechanism for critical failures (e.g., charge, aggregation, low backbone confidence)
  - Per-candidate `score_breakdown` for audit and ablations
- Uncertainty and missingness:
  - Represent missing structure/energy metrics explicitly
  - Define deterministic fallbacks/defaults when tools are unavailable
- Define Pareto objectives used for non-dominated sorting (default: potency_score, structural_quality_score, developability_score)

---

### 4.5 Multi-Round Optimization Algorithm (Core)
- Parent selection:
  - Pareto front calculation via non-dominated sorting
  - Diversity via crowding distance; bounded front size
  - Fallback to composite score ranking when needed
- Convergence:
  - Stop at max_rounds
  - Plateau detection based on top-score improvement threshold with patience
- Strategy update via reflection:
  - LLM outputs structured JSON (`validated_hypotheses`, `failed_hypotheses`, `next_round_strategy`, `exploration_vs_exploitation`)
  - Deterministic fallback when parsing fails; dynamic exploration adjustment based on score trends
- Pseudocode: end-to-end optimization loop with explicit state, feedback, and stopping conditions

---

### 4.6 Candidate Generation (Mechanized, Constraint-Aware)
- Inputs: parents, SAR evidence (trend/SHAP and/or mined rules), structure/energy guidance, constraints (protected positions, max mutations)
- Proposal sources:
  - SAR-top proposals (data-grounded)
  - SAR-guided LLM proposals (bounded prompts with evidence)
  - Novel med-chem proposals (exploratory proposals controlled by exploration_vs_exploitation)
- Safety and determinism:
  - Deterministic mutation application for point mutations
  - Deterministic sequence normalization/conversion when possible; LLM only as a fallback for non-standard residues

---

## 5. Experiments

### 5.1 Experimental Setup

#### 5.1.1 Feedback Regimes and Datasets
- Sparse feedback regime
- Rich feedback regime
- Structured feedback from real-world optimization tasks

#### 5.1.2 Baselines
- Structure-based SOTA: RFDiffusion + ProteinMPNN (physics/geometry-first)
- Sequence-model baseline: peptide MLM / pLM mutation sampling (sequence grammar)
- Heuristic multi-objective optimizer: NSGA-II on the same scoring oracle
- Direct LLM: single-pass prompting without tools / without multi-round updates

#### 5.1.3 Evaluation Metrics
- HR@K / SR@K: fraction of top-K candidates improving over parent while meeting validity constraints
- Constraint satisfaction: charge bounds, aggregation risk, structural thresholds (e.g., pLDDT/iPTM cutoffs), protected-position violations
- Pareto-front quality: first-front size, hypervolume (normalized objective space), diversity (crowding distance statistics)
- Sample efficiency: rounds-to-target and oracle-calls-to-target; best-score vs round curves
- Cost-aware metrics: number of structure/energy calls and wall-clock vs achieved score/front quality

---

### 5.2 Main Results

#### 5.2.1 Optimization under Sparse Feedback
- Performance gains from adaptive reasoning
- Comparison to non-adaptive baselines
- Figure: score vs round; oracle-call vs score; robustness when structure/energy is missing

#### 5.2.2 Multi-Objective Trade-offs
- Quality of Pareto fronts
- Stability across rounds
- Figure: Pareto dashboard (front scatter + hypervolume by round + rank distribution)

---

### 5.3 Ablation Studies

- Remove SAR rule-mining substrate:
  - Use only trend/SHAP evidence (or only LLM guidance) and compare sample efficiency and constraint violations
- Remove Pareto parent selection:
  - Replace with weighted composite ranking; compare hypervolume/front size and diversity
- Remove reflection and dynamic exploration:
  - Fix exploration ratio; disable optimization_insights injection into next-round prompts
- Single-pass vs multi-round:
  - Same evaluation budget (oracle calls) and compare final quality
- Remove hierarchical scoring / penalty:
  - Single scalar score without penalty; measure constraint satisfaction and failure cases
- Remove structure/energy guidance:
  - Potency-only guidance; measure structural failure rates and wasted oracle calls

---

### 5.4 Case Studies

- Representative optimization trajectories
- Evolution of decision strategies
- Failure cases and analysis
- Evidence-chain visualization: mined SAR rules/provenance and how they influence edits across rounds

---

## 6. Discussion

### 6.1 Reasoning and Adaptation as Core Algorithmic Primitives
- Why feedback utilization matters more than raw generation
- Implications for learning systems under weak supervision
- When and why Pareto selection beats scalarization in multi-objective peptide optimization

### 6.2 Generalization Beyond Molecular Design
- Applicability to other domains with structured feedback
- Connections to decision-making and planning research
- What aspects are general (multi-round, Pareto, auditability) vs domain-bound (peptide scoring heuristics)

### 6.3 Limitations and Future Work
- Dependence on oracle quality (ML potency predictor, structure prediction, energy scoring) and their biases
- Domain binding: peptide-specific constraints and scoring heuristics; transfer to other modalities requires redefining the feedback interface
- Multi-round compute cost: oracle calls and latency; cost-aware scheduling as future work
- Prompt sensitivity: reflection/planning prompts can affect behavior; deterministic fallbacks mitigate but do not eliminate it
- Reproducibility of SAR rule mining: provide implementation details, interfaces, and reference runs (interface + pseudocode + code)

---

## 7. Conclusion

- Lead optimization as budgeted multi-objective decision-making under weak feedback
- Interpretable SAR rule mining as an evidence substrate for controlled search
- Pareto-guided multi-round agentic optimization with auditable strategy updates

---

## Appendix

- Algorithm pseudocode
- Metric definitions
- Additional experiments
- Reproducibility details
- SAR engine interface and example inputs/outputs