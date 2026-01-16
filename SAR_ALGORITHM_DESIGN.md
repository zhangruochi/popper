# Algorithm Design Document: Graph-Based Rule Mining for Structure–Activity Relationship (SAR) Analysis

This document describes the algorithm implemented in `scripts/structure_activity_analysis` for **interpretable SAR rule mining** and **candidate generation** in peptide / fragment-based molecular datasets.

The emphasis is on **mathematical definitions** and **paper-ready notation**, with direct mapping to the repository implementation.

---

## 1. Problem Setup

### 1.1 Dataset

We are given a dataset of \(N\) experimentally measured molecules:

\[
\mathcal{D} = \{(x_i, y_i)\}_{i=1}^{N}
\]

where:
- \(x_i\) is a structured representation (e.g., residue/fragment identity at each position),
- \(y_i\) is an observed activity value (e.g., IC50 in nM, Kd, pIC50).

The code represents each entry as a `SeqMol` object:
- `id`: identifier
- `seq`: a dictionary of **position \(\rightarrow\) fragment token**
- `fitness`: a scalar score where **larger is better**

### 1.2 Fitness Transformation

The algorithm operates on a **fitness** value \(f(x)\) with “higher is better”.

Common cases:

- **Minimize** (IC50/Kd in nM): set

\[
f(x) = \frac{1}{y(x)\cdot 10^{-9}}
\]

so that smaller \(y\) gives larger \(f\).

- **Maximize** (e.g., pIC50): set \(f(x)=y(x)\).

The default display conversion back to IC50(nM) is:

\[
\text{IC50}_{\text{nM}} = \frac{1}{f(x)}\cdot 10^{9}
\]

Implementation:
- Fitness is computed in `src/tools/data_loader.py`
- Display transform is configured in `src/tools/config.py` and applied in `src/analyzer.py`

---

## 2. Structural Representation and Mutation Rules

### 2.1 Positionwise Representation

Let positions be indexed by \(p \in \mathcal{P}\) (e.g., \(p=1,\dots,L\)).
Each molecule \(x\) is represented as a mapping:

\[
x(p) \in \Sigma_p
\]

where \(\Sigma_p\) is the set of possible fragments/residues at position \(p\).

In code: `SeqMol.seq` is a `Dict[pos, token]`.

### 2.2 Mutation / Edit Operators

Given a **wild-type** \(w\) and a **mutant** \(m\), define the set of mutated positions:

\[
\Delta(w,m) = \{p \in \mathcal{P}: w(p) \neq m(p)\} \cup
\{p \in \mathcal{P}: p \notin \mathrm{dom}(m)\} \cup
\{p \in \mathcal{P}: p \notin \mathrm{dom}(w)\}
\]

where missing keys correspond to “deletion” or “insertion” in the dictionary representation.

Implementation of mutation detection: `find_mut_pos` in `src/tools/utils.py`.

### 2.3 Rule Encoding

Each position-level mutation is encoded as a token:

\[
t = (p, a, b)
\]

where \(a = w(p)\) (possibly `None`) and \(b = m(p)\) (possibly `None`).

In code, each token becomes a string:

```
{pos}-{wt_fragment}-{mut_fragment}
```

Multi-point rules are concatenations of tokens in sorted order:

\[
r = t_1 \mid t_2 \mid \dots \mid t_k
\]

In code: `rule_list_to_str`, `rule_str_to_list` in `src/tools/utils.py`.

### 2.4 Rule Effect (Amplification Factor)

For a rule observed between a wild-type \(w\) and a mutant \(m\), define the **amplification factor**:

\[
a(r; w\to m) = \frac{f(m)}{f(w)}
\]

The algorithm keeps only rules with:

\[
a(r; w\to m) \ge \texttt{amp\_th}
\]

where `amp_th` is a user-defined threshold.

Implementation: `find_rules_one_wt` in `src/tools/rules.py`, called by `SARAnalyzer.extract_rules()` in `src/analyzer.py`.

---

## 3. Additivity as Multiplicative Factorization

### 3.1 Assumption

The central modeling assumption is a **multiplicative compositionality** of rule effects:

\[
a(r_1 \cup r_2) \approx a(r_1)\cdot a(r_2)
\]

Intuitively, on the fitness scale, independent beneficial edits multiply.

### 3.2 Additivity Test via Relative Error

Let \(R\) be a multi-point rule and \((R_1,R_2)\) be a non-trivial partition:

\[
R = R_1 \cup R_2,\quad R_1\cap R_2=\varnothing,\quad R_1\neq\varnothing,\ R_2\neq\varnothing
\]

Define the relative factorization error:

\[
\epsilon(R;R_1,R_2) = \frac{a(R)}{a(R_1)\,a(R_2)} - 1
\]

If both \(R_1\) and \(R_2\) are observed rules and

\[
|\epsilon(R;R_1,R_2)| \le \texttt{tolerance}
\]

then \((R_1,R_2)\) is considered **additive-compatible**.

Implementation: `deduce_add` in `src/tools/deduce_add.py`.

### 3.3 Deduced Rules via “Division” (Subtraction)

If \(R\) and \(R_1\) are observed but \(R_2\) is not, the algorithm deduces:

\[
\hat{a}(R_2) = \frac{a(R)}{a(R_1)}
\]

This expands the searchable space with **deduced rules** \(\hat{R}\) and records a provenance path.

Implementation: `deduced_rules` and `deduced_rule_path` returned by `deduce_add`.

---

## 4. Rule Graph Construction

Define an undirected graph \(G=(V,E)\) where:
- \(V\) are observed rule nodes,
- an edge \((r_i,r_j)\in E\) exists if the pair participates in at least one validated additive relation (via the test above).

In code:
- graph is built per wild-type in `Clique.propose()` / `TransitiveClique.propose()` using `networkx.Graph()`
- edges are added from `relations` produced by `deduce_add`

---

## 5. Candidate Generation Strategies

The algorithm provides three strategies of increasing exploration aggressiveness:

### 5.1 Strategy A: Clique (Conservative)

**Idea:** If a set of rules forms a clique in \(G\), they are pairwise additive-compatible, thus jointly applicable.

Let \(C=\{r_1,\dots,r_k\}\) be a clique with \(k\ge 3\).
Generate a candidate by applying all rule edits to the wild-type:

\[
\hat{x} = \mathrm{Apply}(w, C)
\]

Predict a conservative lower bound on fitness:

\[
\hat{f}_{\mathrm{lb}}(\hat{x}) = f(w)\cdot a(r_1)\cdot
\prod_{i=2}^{k}\left((1-\texttt{tolerance})\,a(r_i)\right)
\]

Implementation: `Clique.propose()` in `src/tools/strategy.py` and `apply_rules()` in `src/tools/utils.py`.

### 5.2 Strategy B: Transitive Clique (More Aggressive)

**Idea:** Expand the edge set by limited transitive closure, then find cliques.

If \(r_1\) is adjacent to \(r_2\) and \(r_2\) adjacent to \(r_3\), we add an edge between \(r_1\) and \(r_3\) if the three rules do not conflict.

Conflict criterion used in code: if two tokens mutate the same position to different targets, the combination is rejected.

This closure is performed for up to `max_hop` iterations.

To compensate for additional uncertainty, the prediction is scaled by a decay:

\[
\hat{f}(\hat{x}) = f(w)\cdot \texttt{decay\_factor}\cdot \prod_{i=1}^{k} a(r_i)
\]

Implementation: `TransitiveClique.propose()` in `src/tools/strategy.py`.

### 5.3 Strategy C: Subtraction (Most Aggressive)

**Idea:** Use deduced rules \(\hat{r}\) from factorization “division” to propose new edits even when not directly observed.

For each deduced rule \(\hat{r}\) with effect \(\hat{a}(\hat{r})\), apply to wild-type:

\[
\hat{x} = \mathrm{Apply}(w, \{\hat{r}\}),\quad
\hat{f}(\hat{x}) = f(w)\cdot \hat{a}(\hat{r})
\]

The algorithm retains only deduced rules satisfying:

\[
|\hat{r}|\ge \texttt{num\_mut\_min},\quad \hat{a}(\hat{r}) \ge \texttt{amp\_min}
\]

Implementation: `Subtraction.propose()` in `src/tools/strategy.py`.

---

## 6. Filtering, Validation, and Reporting

### 6.1 Nearest-Neighbor Lookup

For each candidate \(\hat{x}\), the algorithm finds the closest dataset molecules by mutation distance:

\[
d(\hat{x}, x) = |\Delta(\hat{x}, x)|
\]

The nearest neighbors minimize \(d\).

Implementation:
- `find_closest_idxs` in `src/tools/utils.py`
- a fingerprint-based variant `find_closest_idxs_fp` exists for fingerprint mode

### 6.2 Empirical Validation Metric

If the candidate already exists in the dataset (minimum distance \(=0\)), it can be validated against the true measured fitness \(f_{\mathrm{ref}}\).

The code uses a simple “hit” condition:

\[
f_{\mathrm{ref}} \ge \frac{\hat{f}}{3}
\]

Implementation: `judge_hit()` methods in each strategy (`strategy.py`).

### 6.3 Filters

Candidates are filtered by modular constraints, including:
- minimum/maximum sequence distance constraints,
- minimum predicted fitness thresholds,
- subtraction-specific logic constraints (e.g., bounding how far the “subtrahend” is from the wild-type).

Implementation: `src/tools/filter.py` and `SARConfig.build_strategies()` in `src/tools/config.py`.

### 6.4 Outputs (Paper-Friendly Evidence Chain)

For each strategy, results include:
- candidate sequences,
- predicted fitness (converted back to display units if configured),
- a provenance trail: which rules / dataset indices support the proposal,
- optional nearest-neighbor evidence tables.

Implementation: `src/tools/excel.py` (Excel and CSV), and `SARAnalyzer.generate_table()` in `src/analyzer.py`.

---

## 7. Pseudocode (Algorithm Block)

### Algorithm 1: Graph-Based SAR Rule Mining and Candidate Generation

**Input:** dataset \(\mathcal{D}\), parameters \(\texttt{amp\_th},\texttt{tolerance},\texttt{max\_n\_mut}\), strategies \(\mathcal{S}\)  
**Output:** candidate set \(\mathcal{C}\) with provenance

1. For each wild-type \(w\in\mathcal{D}\) (parallelizable):
2. \(\quad\) Initialize empty observed rule map \(R \leftarrow \varnothing\)
3. \(\quad\) For each \(m\in\mathcal{D}\):
4. \(\quad\quad\) Compute rule \(r=\mathrm{Encode}(\Delta(w,m))\)
5. \(\quad\quad\) If \(|r| \le \texttt{max\_n\_mut}\) and \(a=f(m)/f(w)\ge \texttt{amp\_th}\): store \(R[r]\leftarrow a\)
6. \(\quad\) Run `deduce_add(R, tolerance)` to obtain:
7. \(\quad\quad\) additive relations \(\mathcal{E}\), deduced rules \(\hat{R}\), provenance paths \(\Pi\)
8. \(\quad\) Build rule graph \(G=(V,E)\) from \(\mathcal{E}\)
9. \(\quad\) For each strategy \(s\in\mathcal{S}\):
10. \(\quad\quad\) Propose candidates \(\mathcal{C}_s \leftarrow s.\mathrm{propose}(w,R,\mathcal{E},\hat{R},\Pi)\)
11. \(\quad\quad\) For each candidate \(\hat{x}\in\mathcal{C}_s\):
12. \(\quad\quad\quad\) Find nearest neighbors in \(\mathcal{D}\)
13. \(\quad\quad\quad\) Apply filters; if candidate exists, optionally validate
14. Merge and export candidates across all \(w\) and \(s\)

---

## 8. Computational Complexity (Discussion-Ready)

Let \(L\) be the number of positions.

- **Per wild-type rule extraction:** compares to all \(N\) mutants and computes mutation differences in \(O(L)\), yielding \(O(NL)\).
- **All wild-types:** \(O(N^2L)\) (mitigated by multiprocessing via `process_map`).
- **Additivity deduction:** for each multi-point rule with \(k\) tokens, enumerating non-trivial partitions costs \(O(2^k)\) in the worst case; in practice \(k\) is bounded by `max_n_mut` and rule counts are pruned by `amp_th`.
- **Clique enumeration:** worst-case NP-hard, but the rule graph is typically sparse after pruning; additionally, `clean_cliques` removes redundant rulesets.

---

## 9. Novelty (Suggested Paper Claim Language)

Compared with conventional black-box QSAR regression, this approach:

1. **Learns interpretable, composable mutation rules** with explicit multiplicative effects on fitness.
2. **Builds a rule–compatibility graph** via an additive (factorization) test with a controllable tolerance.
3. **Supports multi-granularity exploration** (Clique / TransitiveClique / Subtraction), trading off conservativeness vs. search breadth.
4. **Produces evidence-linked candidates** by retaining provenance paths and nearest-neighbor context, facilitating experimental follow-up and ablation analysis.

---

## 10. Implementation Mapping (Where to Cite in Appendix)

- Data parsing & fitness construction: `src/tools/data_loader.py`
- Rule encoding & mutation detection: `src/tools/utils.py`, `src/tools/rules.py`
- Additivity deduction: `src/tools/deduce_add.py`
- Candidate strategies: `src/tools/strategy.py`
- Filtering constraints: `src/tools/filter.py`
- Orchestration & export: `src/analyzer.py`, `src/tools/excel.py`, CLI in `sar_analysis.py`


