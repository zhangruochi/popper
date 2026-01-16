# Technical Guide: Structure-Activity Relationship (SAR) Analysis

This document provides comprehensive technical details and usage instructions for the SAR analysis tool.

---

## Table of Contents

1. [Algorithm Overview](#algorithm-overview)
2. [Technical Details](#technical-details)
3. [Usage Guide](#usage-guide)
4. [Configuration Reference](#configuration-reference)
5. [Data Format Requirements](#data-format-requirements)
6. [Output Interpretation](#output-interpretation)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Usage](#advanced-usage)

---

## Algorithm Overview

The SAR analysis tool implements a **graph-based rule mining** approach that:

1. **Extracts mutation rules** from experimental data by comparing wild-type and mutant molecules
2. **Tests additivity** (multiplicative compositionality) of rule effects
3. **Builds a rule compatibility graph** where edges connect additively-compatible rules
4. **Generates candidates** using three strategies of increasing exploration aggressiveness:
   - **Clique**: Conservative, uses only directly validated rule combinations
   - **TransitiveClique**: More aggressive, uses transitive closure of rule compatibility
   - **Subtraction**: Most aggressive, uses inferred rules from factorization

### Key Innovation

Unlike black-box QSAR models, this approach:
- Produces **interpretable rules** with explicit effect magnitudes
- Provides **evidence chains** linking candidates to supporting data
- Supports **controllable exploration** via strategy selection and parameters

---

## Technical Details

### 1. Data Processing Pipeline

#### 1.1 Data Loading (`src/tools/data_loader.py`)

**Input formats**: CSV, Excel (.xlsx, .xls), JSON

**Processing steps**:
1. Load file and parse into pandas DataFrame
2. Extract position columns (by prefix, e.g., `P1`, `P2`, ...)
3. Filter rows based on activity threshold:
   - For `score_mode: "gd"` (good data): keep rows where `activity > threshold`
   - For `score_mode: "bd"` (bad data): keep rows where `activity <= threshold`
4. Convert activity to fitness:
   - `activity_direction: "minimize"` (IC50, Kd): `fitness = 1 / (activity × 10⁻⁹)`
   - `activity_direction: "maximize"` (pIC50, activity): `fitness = activity`
5. Create `SeqMol` objects for each row

**Data structure**: `SeqMol(id, seq, smiles, fp, fitness)`
- `seq`: Dictionary mapping position → fragment/residue token
- `fitness`: Scalar where larger is better

#### 1.2 Rule Extraction (`src/tools/rules.py`, `src/analyzer.py`)

For each wild-type molecule \(w\) in the dataset:

1. **Compare with all mutants** \(m \in \mathcal{D}\):
   - Compute mutation set: \(\Delta(w, m) = \{p: w(p) \neq m(p)\}\)
   - Encode as rule string: `"pos1-wt1-mut1|pos2-wt2-mut2|..."`
   - Calculate amplification factor: \(a = f(m) / f(w)\)

2. **Filter rules**:
   - Keep only if: \(|r| \leq \texttt{max\_n\_mut}\) and \(a \geq \texttt{amp\_th}\)
   - Group by rule string (multiple wild-type/mutant pairs can yield the same rule)

3. **Store rule map**: `rules[rule_string] = (dataset_index, amplification_factor)`

**Implementation note**: Rules are extracted for \(n=1\) to `max_n_mut` mutation points separately, allowing analysis of single-point vs. multi-point effects.

#### 1.3 Additivity Testing (`src/tools/deduce_add.py`)

For each multi-point rule \(R\):

1. **Enumerate non-trivial partitions**: \(R = R_1 \cup R_2\) where \(R_1 \cap R_2 = \varnothing\)

2. **Test multiplicative factorization**:
   - If both \(R_1\) and \(R_2\) are observed:
     - Compute relative error: \(\epsilon = \frac{a(R)}{a(R_1) \cdot a(R_2)} - 1\)
     - If \(|\epsilon| \leq \texttt{tolerance}\) and \(a(R_1) > 1, a(R_2) > 1\):
       - Mark \((R_1, R_2)\) as an **additive relation** (edge in rule graph)
   - If only one sub-rule is observed (e.g., \(R_1\)):
     - **Deduce** the missing rule: \(\hat{a}(R_2) = \frac{a(R)}{a(R_1)}\)
     - Store as **deduced rule** with provenance path

**Output**:
- `relations`: List of \((R_1, R_2, R)\) tuples (additive edges)
- `deduced_rules`: Dictionary of inferred rules with amplification factors
- `deduced_rule_path`: Dictionary mapping deduced rules to their source \((R_1, R)\)

#### 1.4 Rule Graph Construction (`src/tools/strategy.py`)

Build undirected graph \(G = (V, E)\):
- **Vertices** \(V\): All observed rules
- **Edges** \(E\): Pairs \((r_i, r_j)\) that participate in validated additive relations

**Implementation**: Uses `networkx.Graph()` for graph operations.

#### 1.5 Candidate Generation Strategies

##### Strategy A: Clique (`Clique` class)

**Algorithm**:
1. Find all cliques of size \(\geq 3\) in rule graph \(G\)
2. For each clique \(C = \{r_1, \dots, r_k\}\):
   - Apply all rules to wild-type: \(\hat{x} = \text{Apply}(w, C)\)
   - Predict conservative lower bound:
     \[
     \hat{f}_{\text{lb}} = f(w) \cdot a(r_1) \cdot \prod_{i=2}^{k} (1 - \texttt{tolerance}) \cdot a(r_i)
     \]
3. Store candidate with supporting rule indices

**Cleaning**: `clean_cliques()` removes redundant cliques where one rule set is a subset of another.

##### Strategy B: Transitive Clique (`TransitiveClique` class)

**Algorithm**:
1. **Expand graph** via limited transitive closure:
   - For `max_hop` iterations:
     - For each edge \((r_1, r_2)\) and \((r_2, r_3)\):
       - If \(r_1, r_2, r_3\) have no position conflicts:
         - Add edge \((r_1, r_3)\)
2. Find cliques in expanded graph
3. Generate candidates with decay factor:
   \[
   \hat{f} = f(w) \cdot \texttt{decay\_factor} \cdot \prod_{i=1}^{k} a(r_i)
   \]

**Conflict detection**: Two rules conflict if they mutate the same position to different targets.

##### Strategy C: Subtraction (`Subtraction` class)

**Algorithm**:
1. For each deduced rule \(\hat{r}\) from additivity testing:
   - Check constraints:
     - \(|r| \geq \texttt{num\_mut\_min}\)
     - \(\hat{a}(\hat{r}) \geq \texttt{amp\_min}\)
   - If satisfied:
     - Apply rule: \(\hat{x} = \text{Apply}(w, \{\hat{r}\})\)
     - Predict: \(\hat{f} = f(w) \cdot \hat{a}(\hat{r})\)
2. Store candidate with provenance path (which observed rules support the deduction)

#### 1.6 Filtering and Validation (`src/tools/filter.py`)

**Available filters**:
- `FitnessFilter`: Minimum predicted fitness threshold
- `MinSeqDistFilter`: Minimum/maximum sequence distance from nearest neighbor
- `PositionBlackListFilter`: Exclude specific positions
- `PositionWhiteListFilter`: Include only specific positions
- `SubtractLogicFilter`: For Subtraction strategy, constraints on minuend fitness and subtrahend distance

**Validation**:
- If candidate exists in dataset (mutation distance = 0):
  - Compare predicted vs. observed fitness
  - "Hit" if: \(f_{\text{ref}} \geq \hat{f} / 3\)

#### 1.7 Output Generation (`src/tools/excel.py`, `src/analyzer.py`)

**Excel output**:
- Color-coded mutation highlights (green for source rules, light blue for nearest neighbors)
- Evidence chain: wild-type → supporting rules → candidate → nearest neighbors
- Activity values converted back to display units (nM, pIC50, etc.)

**CSV output**:
- Simplified candidate list with sequences and predicted activities

---

## Usage Guide

### Basic Workflow

1. **Prepare data file** (CSV/Excel/JSON) with required columns
2. **Create configuration YAML** file
3. **Run analysis**:
   ```bash
   python sar_analysis.py --config config/your_config.yaml
   ```
4. **Review results** in timestamped output directory

### Command-Line Interface

```bash
python sar_analysis.py [OPTIONS]
```

**Required options**:
- `--config`, `-c`: Path to YAML configuration file

**Optional options**:
- `--data`, `-d`: Override data file path from config
- `--output`, `-o`: Override output directory from config
- `--verbose`, `-v`: Enable verbose logging
- `--cpu`, `-n`: Override number of CPU cores

**Example**:
```bash
# Basic run
python sar_analysis.py --config config/fcrn.yaml

# Override data file and use 8 cores
python sar_analysis.py --config config/fcrn.yaml --data data/custom.csv --cpu 8

# Verbose mode
python sar_analysis.py --config config/fcrn.yaml --verbose
```

### Configuration File Structure

See `config/fcrn.yaml` or `config/kras.yaml` for complete examples.

**Minimal configuration**:
```yaml
data:
  root: "./data"
  dataset: "your_dataset"
  extension: "csv"
  id_column: "ID"
  activity_column: "IC50(nM)"
  activity_direction: "minimize"
  pos_prefix: "P"

sar:
  tolerance: 0.2
  amp_th: 1
  max_n_mut: 10
  out_dir: "./output"
  n_cpu: 4

strategies:
  use_clique: true
  use_transitive_clique: true
  use_subtraction: true
  clique_fitness_threshold: 1e-8
  transitive_fitness_threshold: 1e-8
  subtractive_fitness_threshold: 1e-8
```

---

## Configuration Reference

### Data Configuration (`data:`)

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `root` | string | Root directory for data files | `"./data/fcrn/raw"` |
| `dataset` | string | Dataset filename (without extension) | `"fcrn_wetlab_0221"` |
| `extension` | string | File extension | `"csv"`, `"xlsx"`, `"json"` |
| `id_column` | string | Column name for compound IDs | `"Entity ID"` |
| `activity_column` | string | Column name for activity values | `"IC50(nM)"` |
| `activity_direction` | string | `"minimize"` (IC50/Kd) or `"maximize"` (pIC50) | `"minimize"` |
| `smiles_column` | string | Optional SMILES column | `"SMILES"` |
| `pos_prefix` | string | Prefix for position columns | `"P"` (for P1, P2, ...) |
| `pos_columns` | list | Optional explicit position column list | `["P1", "P2", "P3"]` |
| `column_headers` | list | Custom output column headers | `["ID", "P1", "P2", "IC50"]` |
| `threshold` | float | Activity threshold for filtering | `6.30` (for pIC50) |
| `score_mode` | string | `"gd"` (good data) or `"bd"` (bad data) | `"gd"` |

### SAR Parameters (`sar:`)

| Parameter | Type | Description | Default | Impact |
|-----------|------|-------------|---------|--------|
| `tolerance` | float | Max relative error for additivity test | `0.2` | Lower = stricter additivity |
| `amp_th` | float | Min amplification factor to extract rules | `1` | Higher = only strong effects |
| `max_n_mut` | int | Max mutation points per rule | `10` | Higher = more complex rules |
| `out_dir` | string | Output directory | `"./output"` | - |
| `n_cpu` | int | Number of CPU cores | `4` | Higher = faster (parallel) |
| `verbose` | bool | Verbose logging | `false` | - |
| `use_fingerprints` | bool | Use molecular fingerprints | `false` | Advanced feature |
| `position` | int | Position for fingerprint analysis | `8` | Only if `use_fingerprints: true` |
| `position_order` | list | Custom position display order | Auto-inferred | Display only |
| `fitness_transform` | string | Display transform | `"ic50_nm"` | `"ic50_nm"`, `"ic50_um"`, `"identity"`, `"log10"` |

### Strategy Configuration (`strategies:`)

#### Common Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `use_clique` | bool | Enable Clique strategy | `true` |
| `use_transitive_clique` | bool | Enable TransitiveClique strategy | `true` |
| `use_subtraction` | bool | Enable Subtraction strategy | `true` |
| `min_seq_dist` | int | Minimum sequence distance from nearest neighbor | `1` |
| `position_blacklist` | list | Positions to exclude | `null` |
| `position_whitelist` | list | Positions to include only | `null` |

#### Clique Strategy

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `clique_fitness_threshold` | float | Minimum predicted fitness | `1e-8` |

#### Transitive Clique Strategy

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `transitive_fitness_threshold` | float | Minimum predicted fitness | `1e-8` |
| `max_hop` | int | Max transitive closure iterations | `1` |
| `decay_factor` | float | Decay factor for predictions | `0.7` |

#### Subtraction Strategy

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `subtractive_fitness_threshold` | float | Minimum predicted fitness | `1e-8` |
| `num_mut_min` | int | Minimum mutation points in deduced rule | `3` |
| `amp_min` | float | Minimum amplification for deduced rule | `10` |
| `subtract_logic_threshold` | float | Minuend fitness threshold | `5e-8` |

### Output Configuration (`output:`)

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `export_csv` | bool | Export CSV files | `true` |
| `export_excel` | bool | Export Excel files | `true` |

---

## Data Format Requirements

### Required Columns

1. **ID column**: Unique identifier for each compound
2. **Activity column**: Numeric activity values (IC50, Kd, pIC50, etc.)
3. **Position columns**: One column per position (e.g., `P1`, `P2`, `P3`, ...)

### Position Column Format

- **Prefix-based**: Columns named `P1`, `P2`, `P3`, ... (configurable via `pos_prefix`)
- **Explicit list**: Specify `pos_columns: ["P1", "P2", "P3"]` in config

### Activity Column Format

- **Numeric values only**: Non-numeric entries are filtered out
- **Units**: Can be nM, μM, pIC50, etc. (specify `activity_direction` accordingly)

### Example CSV Format

```csv
Entity ID,P1,P2,P3,P4,IC50(nM)
compound_1,Arg,Gly,Trp,Ala,125.3
compound_2,Arg,Gly,Trp,Val,89.7
compound_3,Lys,Gly,Trp,Ala,156.2
```

### Example Excel Format

Same structure as CSV, but saved as `.xlsx` or `.xls`.

### JSON Format

```json
[
  {
    "Entity ID": "compound_1",
    "P1": "Arg",
    "P2": "Gly",
    "P3": "Trp",
    "P4": "Ala",
    "IC50(nM)": 125.3
  },
  ...
]
```

---

## Output Interpretation

### Output Directory Structure

```
output/
└── YYYYMMDD_HHMMSS/
    ├── Clique_tol0.2.xlsx
    ├── Clique_tol0.2_candidates.csv
    ├── TransitiveClique_hop1_tol0.2.xlsx
    ├── TransitiveClique_hop1_tol0.2_candidates.csv
    ├── Subtraction_mut3_amp10.xlsx
    └── Subtraction_mut3_amp10_candidates.csv
```

### Excel File Structure

Each Excel file contains:

1. **Header row**: ID, position columns (P1, P2, ...), activity column
2. **Source section** (green highlights):
   - Wild-type row
   - Supporting rule rows (molecules used to infer the candidate)
3. **Candidate section** (light blue highlights):
   - Candidate row (predicted molecule)
   - Nearest neighbor rows (closest molecules in dataset)

**Color coding**:
- **Green**: Mutations relative to wild-type (source rules)
- **Light blue**: Mutations relative to candidate (nearest neighbors)

### CSV File Structure

Simplified candidate list:
- One row per candidate
- Columns: ID, position columns, activity (predicted)

### Console Output

During execution, you'll see:
```
Loading configuration from config/fcrn.yaml
Loading dataset
Loaded 150 entries
Initializing analyzer
Building strategies
Running analysis
==================== Strategy Clique_tol0.2 ====================
25 new candidates found
Validated 5 entries, success rate: 80.00%
Excel results saved to output/20250105_120000/Clique_tol0.2.xlsx
```

**Key metrics**:
- **New candidates found**: Number of unique candidates proposed
- **Validated entries**: Candidates that exist in dataset (for validation)
- **Success rate**: Percentage where \(f_{\text{ref}} \geq \hat{f}/3\)

---

## Troubleshooting

### Common Issues

#### 1. "No valid data entries found in dataset"

**Causes**:
- All rows filtered out by activity threshold
- Activity column contains non-numeric values
- Activity column name mismatch

**Solutions**:
- Check `threshold` value in config (too high/low)
- Verify `activity_column` name matches CSV header
- Check for missing/NaN values in activity column

#### 2. "Key error during analysis"

**Causes**:
- Position index mismatch (e.g., config expects P1-P10 but data has P0-P9)
- Missing position columns

**Solutions**:
- Verify `pos_prefix` matches your column naming
- Use explicit `pos_columns` list if needed
- Check `position_order` if using fingerprints

#### 3. "No candidates found"

**Causes**:
- `amp_th` too high (no rules extracted)
- `tolerance` too strict (no additive relations)
- Fitness thresholds too high (all candidates filtered)

**Solutions**:
- Lower `amp_th` (try `0` to extract all rules)
- Increase `tolerance` (try `0.3` or `0.5`)
- Lower fitness thresholds in strategy config

#### 4. Too many candidates

**Causes**:
- `amp_th` too low (extracting noise)
- `tolerance` too loose (false additive relations)

**Solutions**:
- Increase `amp_th` to focus on strong effects
- Decrease `tolerance` for stricter additivity

#### 5. Performance issues

**Causes**:
- Large dataset with high `max_n_mut`
- Too many CPU cores (overhead)

**Solutions**:
- Reduce `max_n_mut` (e.g., `5` instead of `10`)
- Set `n_cpu` to number of physical cores (not threads)
- Use `amp_th > 0` to prune weak rules early

### Debug Mode

Enable verbose logging:
```bash
python sar_analysis.py --config config/your_config.yaml --verbose
```

Or in config:
```yaml
sar:
  verbose: true
```

This prints:
- Number of rules extracted per mutation point
- Number of additive relations found
- Filter statistics

---

## Advanced Usage

### Fingerprint-Based Analysis

For analyzing molecular fingerprints at a specific position:

```yaml
sar:
  use_fingerprints: true
  position: 8  # Position to analyze
```

**Requirements**:
- Fingerprint dictionary file at specified path (see `src/tools/utils.py::get_AA_fingerprint`)
- Position must exist in all sequences

### Custom Position Order

Override automatic position inference:

```yaml
sar:
  position_order: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
```

### Position Filtering

Exclude or restrict positions:

```yaml
strategies:
  position_blacklist: [1, 2]  # Exclude positions 1 and 2
  position_whitelist: [3, 4, 5]  # Only use positions 3, 4, 5
```

### pIC50 Data

For pIC50 (higher is better):

```yaml
data:
  activity_column: "pIC50"
  activity_direction: "maximize"
  threshold: 6.30  # Keep pIC50 > 6.30

sar:
  fitness_transform: "identity"  # Display pIC50 directly

strategies:
  clique_fitness_threshold: 7.0  # pIC50 > 7
```

### Programmatic Usage

Use as a Python library:

```python
from src.analyzer import SARAnalyzer
from src.tools.data_loader import DataLoader
from src.tools.config import SARConfig
from src.tools.strategy import Clique, TransitiveClique, Subtraction

# Load config
config = SARConfig("config/fcrn.yaml")

# Load data
data_loader = DataLoader(config.get_data_config())
dataset = data_loader.load_data()

# Initialize analyzer
analyzer = SARAnalyzer(
    data_list=dataset,
    activity_column=config.get_data_config()["activity_column"],
    score_mode=config.get_data_config().get("score_mode", "gd"),
    out_dir="./output",
    tolerance=0.2,
    amp_th=1,
    max_n_mut=10,
    n_cpu=4
)

# Build strategies
strategies = config.build_strategies()

# Run analysis
results_df = analyzer.analyze(strategies=strategies)
```

---

## Performance Considerations

### Computational Complexity

- **Rule extraction**: \(O(N^2 \cdot L)\) where \(N\) = dataset size, \(L\) = number of positions
- **Additivity testing**: \(O(R \cdot 2^k)\) where \(R\) = number of rules, \(k\) = max mutation points
- **Clique enumeration**: NP-hard in worst case, but typically fast on sparse graphs

### Optimization Tips

1. **Parallel processing**: Set `n_cpu` to number of physical cores
2. **Early pruning**: Use `amp_th > 0` to filter weak rules
3. **Limit complexity**: Set `max_n_mut` to 5-7 for large datasets
4. **Strategy selection**: Disable unused strategies to save computation

### Typical Runtime

- **Small dataset** (N < 100): < 1 minute
- **Medium dataset** (N = 100-500): 1-10 minutes
- **Large dataset** (N > 500): 10+ minutes (depends on `max_n_mut` and `n_cpu`)

---

## References

- **Algorithm design**: See `ALGORITHM_DESIGN.md` for mathematical formulation
- **Code structure**: See `README.md` for project organization
- **Example configs**: See `config/fcrn.yaml` and `config/kras.yaml`

---

## Support

For issues or questions:
1. Check this guide and `README.md`
2. Review example configurations in `config/`
3. Enable verbose mode for debugging
4. Check console output for specific error messages

