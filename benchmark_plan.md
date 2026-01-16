# Evaluation Plan: Computational Biologist Copilot vs. SOTA Baselines

## 1. Overview

This evaluation aims to demonstrate that **Computational Biologist Copilot** offers a superior approach for **Lead Optimization** compared to state-of-the-art structural and sequence-based design methods.

While methods like RFDiffusion excel at *de novo* binder generation and Protein Language Models (pLMs) capture evolutionary rules, we hypothesize they lack the ability to:

1. Iteratively optimize a specific parent molecule based on project-specific SAR data.
2. Balance multi-objective constraints (e.g., developability rules, specific mutations).
3. Explain their design choices (Interpretability).

## 2. Baseline Definitions

To provide a rigorous assessment, we define four tiers of baselines, covering structural, sequence-based, heuristic, and generalist approaches.

### Primary Baseline: Structure-Based SOTA

**Model:** **RFDiffusion + ProteinMPNN**

* **Implementation Strategy**:
  * **Step 1 (Backbone Generation)**: Use RFDiffusion in `binder_design` or `partial_diffusion` mode. Provide the target protein structure and the *parent peptide* backbone as a template (with added noise) to simulate "optimization" rather than completely random *de novo* generation.
  * **Step 2 (Sequence Design)**: Use ProteinMPNN to design sequences for the generated backbones.
  * **Step 3 (Filtering)**: Filter outputs using AlphaFold2/Boltz pLDDT to select the best designs (standard protocol).
* **Role in Benchmark**: Represents the **"Physics/Geometry-only"** approach. It ignores historical SAR data and project-specific constraints.

### Secondary Baseline: Heuristic Optimization

**Model:** **NSGA-II (Non-dominated Sorting Genetic Algorithm)**

* **Implementation**: A standard multi-objective genetic algorithm using the exact same scoring functions (Oracle) as the Copilot.
* **Role in Benchmark**: Represents **"Brute Force"** optimization without reasoning.

### Tertiary Baseline: Direct LLM

**Model:** **Zero-Shot GPT-4o**

* **Implementation**: Prompting the LLM to optimize the sequence based on the parent and constraints, without access to MCP tools or structure prediction.
* **Role in Benchmark**: Represents **"Hallucination"** risks and proves the necessity of the agentic architecture.

### Quaternary Baseline: Sequence-Based SOTA (New)

**Model:** **PepMLM (Linear Peptide Masked Language Model)**
*(Note: Represents architectures like ESM-2 or specialized peptide BERTs fine-tuned on peptide data)*

* **Implementation Strategy**:
  * **Input**: The parent peptide sequence.
  * **Method**: Utilize **Masked Language Modeling (MLM)**. Systematically mask residues in the parent sequence and ask the model to predict the most probable substitutions based on learned "peptide grammar."
  * **Optimization Mode**: Generate variants by sampling high-probability tokens from the model's logits, effectively performing "in-silico evolution."
* **Role in Benchmark**: Represents the **"Sequence Grammar / Evolutionary"** approach. It assumes that sequences with high likelihood (low perplexity) are more likely to be bioactive and stable, but it lacks explicit modeling of 3D structure or user-defined constraints.

---

## 3. Experimental Strategy

We will conduct comparisons across the three scenarios defined previously (Scenario A: Sparse, B: Rich, C: Cyclic Case Study).

### Scenario Definitions & Datasets

To evaluate performance across realistic lead-optimization phases, we define three regimes that differ primarily in the **amount and quality of available SAR**.

#### Scenario A — Sparse SAR (Early Lead Optimization / SAR-Scarce)

**Data source**: A set of targets with limited, cleanable SAR extracted from **SKEMPI 2.0**. These datasets contain relatively few mutation–effect measurements (typically < 30; often single digits to teens after filtering), making them representative of **early-stage** projects.

**Available datasets**:

* `1F47`, `1GL0`, `1GL1`, `1KNE`, `1SMF`
* `3EQS`, `3EQY`, `3LNZ`, `3RF3`
* `4CPA`, `4J2L`
* `5UML`, `5UMM`, `5XCO`

**Why this matters for Copilot**: Although explicit SAR is scarce, our **multi-round reflection** mechanism can (i) form hypotheses from weak signals, (ii) propose targeted mutations to probe uncertainty, and (iii) distill emergent constraints/hotspots across rounds—effectively **recovering actionable SAR** from limited evidence.

#### Scenario B — Rich SAR (Mid-Stage Optimization / SAR-Rich)

**Data source**: SAR mined from the literature via data mining (e.g., reported potency/affinity changes across systematic mutation series). These datasets typically contain **> 30** SAR entries and better reflect mid-stage medicinal chemistry / peptide optimization.

**Targets (literature-mined)**:

* PDZ
* Bcl-2
* GLP-1
* MDM2
* PD-L1

#### Scenario C — Cyclic Peptide Case Study (Project-Style Iteration)

**Data source**: `Krpep-2d_WT` (17 entries). This is a synthetic cyclic peptide series designed and optimized to selectively inhibit the **K-Ras(G12D)** mutant (a representative “project-like” case study with strong constraints and iterative design logic).

### Experiment 1: Optimization Efficiency & SAR Adherence

**Objective**: Can the model utilize existing data to improve potency efficiently?

* **Method**:
  * **Task**: Optimize a parent peptide under two SAR regimes:
    * **Scenario B (Rich SAR)**: Use the **PD-L1/PD-1** dataset as the primary benchmark.
    * **Scenario A (Sparse SAR)**: Replicate the same protocol on selected SKEMPI-derived targets to quantify data-efficiency under SAR scarcity.
  * **Constraint**: The optimization must respect known SAR "Hotspots" (e.g., specific residues that must remain hydrophobic).
* **Comparison**:
  * **Copilot**: Uses `insight_sar_mining` to identify hotspots and `design_mutation_plan` to preserve them.
  * **RFD + ProteinMPNN**: Generates sequences based solely on geometric fit, often ignoring SAR.
  * **PepMLM**: Generates mutations that are "statistically natural" or "evolutionarily plausible" but often fails to capture **Project-Specific SAR** (e.g., a specific non-natural mutation that increases potency but is rare in public training data).
* **Metric**:
  * **SAR Violation Rate**: Percentage of generated candidates that mutate known critical conserved residues.
  * **Success Rate (SR)**: Percentage of candidates achieving higher predicted affinity than the parent.

### Experiment 2: Multi-Objective Constraint Satisfaction

**Objective**: Can the model balance Potency with Developability (Net Charge, Solubility)?

* **Method**:
  * **Task**: Generate binders with `net_charge` strictly between [-2, +2] and `aggregation_risk` = Low.
* **Comparison**:
  * **Copilot**: Explicitly handles these constraints via the **Layer 1** scoring and **Penalty Factor** mechanism.
  * **RFD + ProteinMPNN**: ProteinMPNN tends to generate highly positive charged sequences to optimize solubility/affinity.
  * **PepMLM**: Cannot natively handle constraints like "Net Charge < 2". It generates sequences based on probability distributions, often creating aggregation-prone hydrophobic patches if they are common in the training distribution (e.g., transmembrane domains).
* **Metric**:
  * **Constraint Satisfaction Rate**: % of high-affinity candidates that also meet developability criteria.
  * **Pareto Frontier**: Visualization of Potency vs. Developability.

### Experiment 3: Structural Validity (The RFDiffusion Stronghold)

**Objective**: Does Copilot generate physically valid structures comparable to RFDiffusion?

* **Method**:
  * **Task**: Structure prediction of the top 10 generated candidates from all methods using an independent oracle (e.g., AlphaFold3 or Boltz-1).
* **Comparison**:
  * **Copilot**: Uses `design_score_candidates` (Boltz integration) to filter designs.
  * **RFD + ProteinMPNN**: Natively generates valid protein geometries.
  * **PepMLM**: Optimizes sequence likelihood only; resulting structures are unverified during generation.
* **Metric**:
  * **pLDDT / iPTM Score**: Confidence of the predicted structure.
  * **Interface $\Delta G$**: Predicted binding energy.
  * *Hypothesis*: RFDiffusion will likely win or tie on pLDDT, but Copilot should achieve comparable validity while offering better chemical properties.

---

## 4. Method Comparison Table

This table summarizes the fundamental differences between your Agentic approach and the Baselines.

| Feature / Capability | **Copilot (Ours)** | **RFDiffusion + ProteinMPNN** | **PepMLM (Seq. Model)** | **NSGA-II (Genetic Alg.)** | **Direct LLM (GPT-4)** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Core Approach** | **Agentic Reasoning** (Data + Structure + Logic) | **Geometric Deep Learning** (Structure only) | **Masked Language Modeling** (Sequence probability) | **Heuristic Search** (Stochastic) | **Probabilistic** (Text prediction) |
| **Optimization Logic** | **Multi-Round Reflection** (Hypothesis-driven) | **Inverse Folding** (Fit to backbone) | **In-Silico Evolution** (High likelihood sampling) | **Fitness Function** (Brute force) | **Semantics** (Instruction following) |
| **SAR Awareness** | ✅ **Explicit** (Mines local project data) | ❌ No (Physics/Geometry only) | ⚠️ **Implicit** (Global evolutionary priors) | ❌ No | ⚠️ Partial (In-context) |
| **Constraint Handling** | ✅ **Strict** (Pre/Post-check logic) | ⚠️ Weak (Structure biased) | ❌ **None** (Requires post-filtering) | ✅ Explicit | ⚠️ Weak |
| **Structural Validity** | ✅ **Verified** (Calls ext. tools) | ✅ **Native** (Best in class) | ⚠️ **Unknown** (Not modeled) | ⚠️ Random | ❌ Hallucination Risk |
| **Non-Natural AA** | ✅ **Supported** (If tools allow) | ❌ No (Standard 20 only) | ❌ No (Standard 20 only) | ✅ Supported | ✅ Supported |
| **Output Type** | Optimized Lead + **Rationale** | New Backbone + Sequence | Sequence Variants | List of Sequences | Text / Sequence |

---

## 5. Metrics Calculation Standards

To ensure a fair comparison, all generated molecules (from Copilot, RFD, PepMLM, or NSGA-II) must be evaluated by a **Unified Ground Truth Oracle** (In Silico):

1. **Potency**: Assessed by your trained **TabularModel** (trained on all available data excluding the test parent).
2. **Structure**: Assessed by **Boltz-1** (running in `structure_prediction_run` tool).
3. **Developability**: Assessed by the standard rules defined in `METRICS_GUIDE.md`.

### Evaluation Formula

The comparison will focus on the **Hit Rate ($HR$)** at Top-K:

$$HR@K = \frac{1}{K} \sum_{i=1}^{K} \mathbb{1}(S_{final}^{(i)} > S_{parent} \land \text{Valid})$$

Where:

* $S_{final}$ is the **Final Score** (Layer 1-3 composite).
* **Valid** means pLDDT > 0.7 and Net Charge within range.

---

## 6. Expected Results (Hypothesis for Paper)

1. **RFDiffusion** will generate highly stable structures (High `structural_quality_score`) but may produce sequences that violate known SAR rules or developability constraints (Lower `potency_score` or `developability_score`).
2. **PepMLM** will likely score high on **"Sequence Naturalness"** (resembling known bioactive peptides) but will underperform in **"Target Specificity"**. Without structural context (interaction interface) or specific SAR data, PepMLM tends to propose conservative mutations that preserve stability but fail to significantly boost potency against a specific, difficult target.
3. **Copilot** will generate candidates that are **Balanced**. They may have slightly lower structural confidence than RFD but significantly higher predicted potency and better physicochemical properties, resulting in a higher **Overall Success Rate**.
4. **Copilot** will demonstrate **Data Efficiency** in the "Rich Data" scenario, finding optima in fewer steps than NSGA-II.
