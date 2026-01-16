# Computational Biologist Copilot – User Guide

This document provides a practical guide for using the Computational Biologist Copilot workflow.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Three Operating Modes](#three-operating-modes)
3. [API Reference](#api-reference)
4. [Configuration](#configuration)
5. [Usage Examples](#usage-examples)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

The copilot is part of the `local_agent` package. Ensure you have the required dependencies installed:

```bash
conda activate research
pip install -e .
```

### Using LangGraph Studio (langgraph dev)

You can run the workflow interactively using LangGraph Studio:

```bash
# Install LangGraph CLI (if not already installed)
pip install --upgrade "langgraph-cli[inmem]"

# From the workflow directory
cd local_agent/langgraph/workflows/computational_biologist_copilot
langgraph dev

# Or from the project root
langgraph dev local_agent/langgraph/workflows/computational_biologist_copilot

# Custom port (using localhost - recommended for Studio)
langgraph dev --port 8080

# For remote access via tunnel (if needed)
langgraph dev --tunnel --port 8080

# From project root with custom port
langgraph dev local_agent/langgraph/workflows/computational_biologist_copilot --port 8080
```

**Configuration Options:**

- **Host**: Use `--host` to specify the network interface (default: `127.0.0.1`)
  - `127.0.0.1` or `localhost`: Recommended for LangGraph Studio (default)
  - `0.0.0.0`: Accessible from any network interface, but **not compatible with Studio UI** (CORS issues)
  
- **Port**: Use `--port` to specify the port number (default: `2024`)
  - Example: `--port 8080` to use port 8080

- **Tunnel**: Use `--tunnel` to create a public tunnel for remote access
  - Creates a public URL that can be accessed from anywhere
  - Useful when you need to share access or access from remote locations

**Stopping the Server:**

- **If running in foreground**: Press `Ctrl+C` in the terminal where `langgraph dev` is running
- **If running in background or terminal is closed**: Find and kill the process by port:
  ```bash
  # Find process ID by port
  lsof -ti:10049
  
  # Kill the process (replace PID with actual process ID)
  kill <PID>
  
  # Or force kill if needed
  kill -9 <PID>
  
  # One-liner to kill by port
  kill $(lsof -ti:10049) 2>/dev/null || echo "No process found on port 10049"
  ```

This will start a development server (default: `http://127.0.0.1:2024`) and open LangGraph Studio in your browser, where you can:
- Visualize the graph structure
- Test the workflow interactively
- Debug node execution
- Inspect state at each step

The `app.py` file exports the compiled graph, which LangGraph Studio uses to run and visualize the workflow.

### Basic Usage (Python API)

The simplest way to use the copilot is to let it **auto-detect the mode** from natural-language input:

```python
from local_agent.langgraph.workflows.computational_biologist_copilot import run_pipeline

result = await run_pipeline(
    user_input="Analyze SAR patterns in the ACVR2A dataset",
    mcp_url="http://81.70.177.174:10047/mcp",
    config={
        "verbose": True,
        "data_path": "/path/to/data.csv",
    },
)

print("Mode:", result.get("mode"))
print("Report:", result.get("report_text"))
```

The router will automatically:
- Classify the intent: `"analyze SAR"` → Insight mode, `"design"` → Design mode, `"evaluate"` → Evaluation mode
- Route into the corresponding subgraph
- Return a mode-specific report

---

## Three Operating Modes

### Mode 1: Insight Mode

**Goal:** Turn a SAR table into **position-wise SAR**, **mechanistic hypotheses**, and **actionable design strategies**.

#### Dual-Path Architecture

Insight Mode supports two analysis depths:

- **Light Path** – Quick, chat-based responses using only `sar_trend` statistics
  - Ideal for simple questions about patterns, positions, or trends
  - No ML model training required
  - Response in seconds

- **Full Path** – Complete analysis with ML model training and SHAP
  - For comprehensive, predictive analyses
  - Includes model training, feature importance, and detailed reports
  - Use when you need predictions or deep statistical insights

#### Example Queries

**Light Path:**

```
"What patterns do you see at P3?"
"Which mutations are favorable for selectivity?"
"Summarize the SAR trends in this data"
```

**Full Path:**

```
"Train a model and analyze feature importance"
"Give me a comprehensive SAR analysis"
"I need SHAP explanations for the selectivity data"
```

#### Usage

```python
from local_agent.langgraph.workflows.computational_biologist_copilot import run_insight_mode

insight_result = await run_insight_mode(
    user_input="Summarize SAR for NPR1 selectivity and propose design rules",
    data_path="/path/to/npr1_sar_table.csv",
    mcp_url="http://81.70.177.174:10047/mcp",
    config={"verbose": True, "insight_depth": "full"},  # or "light" or "auto"
)

print(insight_result["insight_report"]["summary"])
```

#### Output

- **Light path**: Conversational response with data citations (`report_type: "insight_light"`)
- **Full path**: `InsightReport` object with:
  - Data scope & quality
  - Position-wise SAR
  - Mechanistic hypotheses
  - Concrete design strategies and suggested experiments

---

### Mode 2: Design Mode

**Goal:** Generate and rank **new peptide candidates** that respect structural constraints and multi-objective criteria.

#### Inputs

- `parent_peptides`: List of parent sequences (e.g. hit or lead sequences)
- Objectives:
  - Improve potency/selectivity
  - Maintain or improve developability
  - Keep ring size / Cys pairing fixed
- Constraints:
  - Max mutations per candidate (e.g. ≤3)
  - Allowed amino-acid vocabulary per position
  - Optional structural constraints

#### Usage

```python
from local_agent.langgraph.workflows.computational_biologist_copilot import run_design_mode

design_result = await run_design_mode(
    user_input="Design new ACVR2A-selective macrocycles with <=3 mutations",
    parent_peptides=[
        "Ac-Lys-Cys-Phe-Gly-Cys-Pro-Lys-Ile-Ser-Arg-Leu-Cys-NH2",
    ],
    mcp_url="http://81.70.177.174:10047/mcp",
    config={
        "verbose": True,
        "scoring_weights": {
            "potency": 0.50,
            "interface_score": 0.25,
            "backbone_quality": 0.15,
            "developability": 0.10,
        },
        "max_mutations": 3,
    },
)

for cand in design_result["design_report"]["ranked_candidates"][:5]:
    print(cand["sequence"], cand["composite_score"], cand["rationale"])
```

#### Multi-Round Optimization

Design Mode supports iterative multi-round optimization:

```python
from local_agent.langgraph.workflows.computational_biologist_copilot import run_design_mode

design_result = await run_design_mode(
    user_input="Design peptides with >100x ACVR2A/ACVR2B selectivity",
    parent_peptides=["Ac-Cys-Leu-Pro-Ile-His-Phe-Arg-Tyr-Cys-Ser-Leu-Cys-Met-NH2"],
    mcp_url="http://81.70.177.174:10047/mcp",
    config={
        "verbose": True,
        "design": {
            "multi_round_optimization": {
                "enabled": True,
                "max_rounds": 5,
                "top_k_parents": 3,
                "convergence_threshold": 0.01,
            }
        }
    },
)

# Access round-by-round results
if "rounds" in design_result:
    for i, round_data in enumerate(design_result["rounds"], 1):
        print(f"Round {i}: Top score = {round_data['top_score']:.3f}")
```

#### Output

- `DesignReport` with:
  - Ranked candidates
  - Numeric scores and uncertainties
  - Per-candidate rationales
  - Tiered synthesis recommendations

---

### Mode 3: Evaluation Mode

**Goal:** Act as a **critical reviewer** for a list of candidate peptides.

#### Inputs

- A list of sequences or IDs in `user_input` / `candidates`
- Program objectives (potency, selectivity, developability)

#### Usage

```python
from local_agent.langgraph.workflows.computational_biologist_copilot import run_evaluation_mode

eval_result = await run_evaluation_mode(
    user_input="Evaluate these NPR1 candidates for potency and developability risks",
    candidates=[
        "Ac-Lys-Cys-Phe-Gly-Cys-Pro-Lys-Ile-Ser-Arg-Leu-Cys-NH2",
        "Ac-Gln-Cys-Phe-Gly-Cys-Pro-Lys-Ile-Ser-Arg-Leu-Cys-NH2",
    ],
    mcp_url="http://81.70.177.174:10047/mcp",
    config={"verbose": True},
)

for row in eval_result["evaluation_report"]["prioritized_candidates"]:
    print(row["sequence"], row["priority"], row["summary"])
```

#### Output

- `EvaluationReport`:
  - Prioritized table with per-candidate commentary
  - Cross-checks against SAR trends and program objectives
  - Risk flags and redesign suggestions

---

## API Reference

### Top-Level Entry Point

#### `run_pipeline(...)`

Auto-detects mode from natural-language input.

```python
from local_agent.langgraph.workflows.computational_biologist_copilot import run_pipeline

result = await run_pipeline(
    user_input: str,
    mcp_url: str | None = None,
    config: dict | None = None,
    mode: str | None = None,  # Optional mode override
) -> CopilotState
```

**Parameters:**
- `user_input`: User's query or request
- `mcp_url`: URL for MCP server (if not using multi-server config)
- `config`: Configuration dictionary (see [Configuration](#configuration))
- `mode`: Optional mode override ('insight', 'design', 'evaluation')

**Returns:**
- Final state with mode-specific report

### Direct Mode APIs

#### `run_insight_mode(...)`

```python
from local_agent.langgraph.workflows.computational_biologist_copilot import run_insight_mode

result = await run_insight_mode(
    user_input: str,
    data_path: str,
    mcp_url: str | None = None,
    config: dict | None = None,
) -> CopilotState
```

#### `run_design_mode(...)`

```python
from local_agent.langgraph.workflows.computational_biologist_copilot import run_design_mode

result = await run_design_mode(
    user_input: str,
    parent_peptides: List[str],
    mcp_url: str | None = None,
    config: dict | None = None,
) -> CopilotState
```

#### `run_evaluation_mode(...)`

```python
from local_agent.langgraph.workflows.computational_biologist_copilot import run_evaluation_mode

result = await run_evaluation_mode(
    user_input: str,
    candidates: List[str],
    mcp_url: str | None = None,
    config: dict | None = None,
) -> CopilotState
```

### Runner Class

For long-lived applications (e.g. a web UI):

```python
from local_agent.langgraph.workflows.computational_biologist_copilot import get_copilot_runner

runner = await get_copilot_runner(
    mcp_url="http://81.70.177.174:10047/mcp",
    config={"verbose": True},
)

response = await runner.chat(
    user_input="Analyze SAR patterns in the ACVR2A dataset",
    data_path="/path/to/acvr2a_sar.csv",
)

print(response["mode"])
print(response["report"]["summary"])

await runner.close()
```

### Saving Reports

```python
from local_agent.langgraph.workflows.computational_biologist_copilot import save_report

await save_report(
    report=insight_result["insight_report"],
    output_path="/path/to/INSIGHT_REPORT.md",
)
```

---

## Configuration

### Basic Configuration

```python
config = {
    # Verbosity
    "verbose": True,  # Enable detailed logging
    
    # LLM Configuration
    "model": {
        "name": "deepseek-chat",           # Main model for reasoning
        "base_url": "https://api.example.com",
        "api_key": "your-api-key",
        "model_provider": "openai"
    },
    
    # MCP Configuration
    # Option 1: Single Server Mode (backward compatible)
    # Use mcp_url parameter in function call, or set here:
    "mcp_url": "http://81.70.177.174:10047/mcp",  # Single MCP server for all tools
    "mcp_timeout": 300.0,  # Timeout in seconds
    
    # Option 2: Multi-Server Mode (recommended for production)
    # If mcp_servers is provided, mcp_url is ignored
    # Route different tools to different servers for optimal performance
    "mcp_servers": {
        "default": "http://81.70.177.174:10047/mcp",  # Default/remote server
        "local": "http://localhost:10039/mcp",         # Local server for fast operations
        "remote": "http://81.70.177.174:10047/mcp",    # Remote server for heavy compute
        "tools": {
            # Fast tools → local server (low latency)
            "table_parser": "local",
            "sar_trend_analyze": "local",
            "tabular_model": "local",
            "composer": "local",
            # Heavy compute → remote server (GPU resources)
            "structure_prediction_run": "default",
            "energy_score_calculate": "default",
        }
    },
}
```

### Mode-Specific Configuration

#### Insight Mode

```python
config = {
    "insight_depth": "auto",  # "light" | "full" | "auto" (default: "auto")
    "data_path": "/path/to/sar_table.csv",  # Required for Insight mode
}
```

#### Design Mode

```python
config = {
    "parent_peptides": ["ACDEFGHIKLMNPQ"],  # Required for Design mode
    "scoring_weights": {
        "potency": 0.50,
        "interface_score": 0.25,
        "backbone_quality": 0.15,
        "developability": 0.10,
    },
    "max_mutations": 3,  # Maximum mutations per candidate
    
    # Multi-round optimization
    "design": {
        "multi_round_optimization": {
            "enabled": True,
            "max_rounds": 5,
            "convergence_threshold": 0.01,  # 1% improvement threshold
            "plateau_patience": 2,  # Stop after 2 consecutive low-improvement rounds
            "top_k_parents": 3,  # Number of top candidates to use as parents
            "target_final_score": 0.95,  # Optional: stop if top score >= this value
            "target_kd_nm": 5.0,  # Optional: stop if predicted Kd <= this value (nM)
        }
    },
    
    # SSH adapter for remote structure prediction (optional)
    "remote_host": "Syneron1",  # SSH host alias for remote structure prediction
}
```

#### Evaluation Mode

```python
config = {
    "candidates_to_evaluate": ["SEQ001", "SEQ002"],  # Required for Evaluation mode
}
```

### Logging Configuration

```python
config = {
    "enable_file_logging": True,  # Save logs to disk
    "log_dir": "./logs/copilot_runs",  # Log directory
    "verbose": True,  # Print to console
}
```

### Configuration Parameters Reference

**Top-level Config:**
- `verbose`: Enable detailed logging (bool, default: `False`)
- `mcp_url`: Single MCP server URL (str, for backward compatibility). **Note:** Ignored if `mcp_servers` is provided in config.
- `mcp_timeout`: MCP request timeout in seconds (float, default: `300.0`)
- `mcp_servers`: Multi-server MCP configuration (dict). **Note:** If provided, `mcp_url` is ignored. Structure:
  - `default`: Default/remote server URL (str)
  - `local`: Local server URL (str)
  - `remote`: Remote server URL (str, optional, can use `default`)
  - `tools`: Dict mapping tool names to server keys (`"local"`, `"default"`, `"remote"`)

**Model Config (`config["model"]`):**
- `name`: Model name (str, default: `"deepseek-chat"`)
- `base_url`: API base URL (str, optional)
- `api_key`: API key (str, optional)
- `model_provider`: Model provider (str, optional, e.g., `"openai"`)

**Insight Mode Config:**
- `insight_depth`: Analysis depth - `"light"` | `"full"` | `"auto"` (default: `"auto"`)
- `data_path`: Path to SAR table CSV/TSV (str, required for Insight mode)

**Design Mode Config:**
- `parent_peptides`: List of parent sequences (list[str], required for Design mode)
- `scoring_weights`: Multi-objective scoring weights (dict, optional)
- `max_mutations`: Maximum mutations per candidate (int, optional)
- `remote_host`: SSH host alias for remote structure prediction (str, optional, default: "Syneron1")
- `design.multi_round_optimization`: Multi-round optimization config (dict, optional):
  - `enabled`: Enable multi-round optimization (bool, default: `max_rounds > 1`)
  - `max_rounds`: Maximum number of rounds (int, default: 1, min: 1)
  - `convergence_threshold`: Score improvement threshold to detect plateau (float, default: 0.01, range: [0.0, 1.0])
  - `plateau_patience`: Number of consecutive low-improvement rounds before stopping (int, default: 2, min: 1)
  - `top_k_parents`: Number of top candidates to use as parents for next round (int, default: 3, min: 1)
  - `target_final_score`: Optional target score to stop early if achieved (float, optional)
  - `target_kd_nm`: Optional target Kd (nM) to stop early if achieved (float, optional)

**Evaluation Mode Config:**
- `candidates_to_evaluate`: List of candidate sequences to evaluate (list[str], required for Evaluation mode)

---

## Usage Examples

### MCP Configuration Modes

The workflow supports two MCP configuration modes:

1. **Single Server Mode** (backward compatible): Use `mcp_url` parameter
   - All tools use the same MCP server
   - Simple setup, suitable for basic use cases
   - Example: `mcp_url="http://81.70.177.174:10047/mcp"`

2. **Multi-Server Mode** (recommended for production): Use `mcp_servers` in config
   - Route different tools to different servers (local/remote)
   - Optimize performance by using local servers for fast operations
   - Route heavy compute tasks to remote servers
   - Example: See Example 3b below

**Note:** If `mcp_servers` is provided in config, the `mcp_url` parameter is ignored.

### Example 1: Insight Mode - Light Path (Quick Analysis)

```python
result = await run_insight_mode(
    user_input="What patterns do you see at position P3 in the ACVR2A dataset?",
    data_path="/path/to/acvr2a_sar.csv",
    mcp_url="http://81.70.177.174:10047/mcp",
    config={"insight_depth": "light", "verbose": True},
)

print(result["report_text"])
```

### Example 2: Insight Mode - Full Path (Comprehensive Analysis)

```python
result = await run_insight_mode(
    user_input="Give me a comprehensive SAR analysis with SHAP explanations for the ACVR2A dataset",
    data_path="/path/to/acvr2a_sar.csv",
    mcp_url="http://81.70.177.174:10047/mcp",
    config={"insight_depth": "full", "verbose": True},
)

report = result["insight_report"]
print(report["summary"])
print(f"Found {len(report['sar_findings'])} SAR findings")
```

### Example 3: Design Mode - Basic Generation (Single Server Mode)

**Note:** This example uses single server mode (backward compatible). For multi-server mode with local/remote routing, see Example 3b below.

```python
result = await run_design_mode(
    user_input="Design new candidates with improved potency for ACVR2A. Max 3 mutations.",
    parent_peptides=["Ac-Cys-Leu-Pro-Ile-His-Phe-Arg-Tyr-Cys-Ser-Leu-Cys-Met-NH2"],
    mcp_url="http://81.70.177.174:10047/mcp",  # Single MCP server URL
    config={
        "max_mutations": 3,
        "verbose": True,
    },
)

for i, cand in enumerate(result["design_report"]["ranked_candidates"][:5], 1):
    print(f"{i}. {cand['sequence']}")
    print(f"   Score: {cand['composite_score']:.3f}")
    print(f"   Rationale: {cand['rationale']}")
```

### Example 3b: Design Mode - Multi-Server MCP Configuration

**Note:** This example uses multi-server mode, routing different tools to local or remote MCP servers for optimal performance.

```python
result = await run_design_mode(
    user_input="Design new candidates with improved potency for ACVR2A. Max 3 mutations.",
    parent_peptides=["Ac-Cys-Leu-Pro-Ile-His-Phe-Arg-Tyr-Cys-Ser-Leu-Cys-Met-NH2"],
    # Note: Multi-server mode does NOT use mcp_url parameter
    # Instead, configure mcp_servers in config
    config={
        "mcp_servers": {
            "default": "http://81.70.177.174:10047/mcp",  # Remote server for heavy compute
            "local": "http://localhost:10039/mcp",         # Local server for fast operations
            "tools": {
                # Fast tools on local server
                "table_parser": "local",
                "sar_trend_analyze": "local",
                "tabular_model": "local",
                "composer": "local",
                # Heavy compute on remote server
                "structure_prediction_run": "default",
                "energy_score_calculate": "default",
            }
        },
        "max_mutations": 3,
        "verbose": True,
    },
)

for i, cand in enumerate(result["design_report"]["ranked_candidates"][:5], 1):
    print(f"{i}. {cand['sequence']}")
    print(f"   Score: {cand['composite_score']:.3f}")
    print(f"   Rationale: {cand['rationale']}")
```

### Example 4: Design Mode - Multi-Round Optimization

```python
result = await run_design_mode(
    user_input="Design peptides with >100x ACVR2A/ACVR2B selectivity",
    parent_peptides=["Ac-Cys-Leu-Pro-Ile-His-Phe-Arg-Tyr-Cys-Ser-Leu-Cys-Met-NH2"],
    mcp_url="http://81.70.177.174:10047/mcp",
    config={
        "verbose": True,
        "design": {
            "multi_round_optimization": {
                "enabled": True,
                "max_rounds": 5,
                "convergence_threshold": 0.01,  # 1% improvement threshold
                "plateau_patience": 2,  # Stop after 2 consecutive low-improvement rounds
                "top_k_parents": 3,
                "target_final_score": 0.95,  # Optional: stop if top score >= 0.95
            }
        }
    },
)

# Access round-by-round results
if "rounds" in result:
    for i, round_data in enumerate(result["rounds"], 1):
        print(f"Round {i}: Top score = {round_data['top_score']:.3f}")
        print(f"  Convergence reason: {round_data.get('convergence_reason', 'N/A')}")
```

**Multi-Round Configuration Notes**:
- **Convergence Detection**: Only activates after round 2+ (round 1 always continues)
- **Plateau Patience**: Requires multiple consecutive low-improvement rounds before stopping (prevents premature stopping)
- **Alternative Config Keys**: Also supports `config["multi_round"]` or `config["design"]["multi_round"]` for backward compatibility

### Example 5: Evaluation Mode

```python
result = await run_evaluation_mode(
    user_input="Evaluate these candidates against ACVR2A potency target > 10nM",
    candidates=[
        "Ac-Lys-Cys-Phe-Gly-Cys-Pro-Lys-Ile-Ser-Arg-Leu-Cys-NH2",
        "Ac-Gln-Cys-Phe-Gly-Cys-Pro-Lys-Ile-Ser-Arg-Leu-Cys-NH2",
    ],
    mcp_url="http://81.70.177.174:10047/mcp",
    config={"verbose": True},
)

for row in result["evaluation_report"]["prioritized_candidates"]:
    print(f"{row['sequence']}: {row['priority']} - {row['summary']}")
```

### Example 6: Design Mode - Multi-Objective with Structure Prediction

```python
result = await run_design_mode(
    user_input="Design candidates with improved potency and excellent structural properties",
    parent_peptides=["Ac-Cys-Leu-Pro-Ile-His-Phe-Arg-Tyr-Cys-Ser-Leu-Cys-Met-NH2"],
    mcp_url="http://81.70.177.174:10047/mcp",
    config={
        "max_mutations": 3,
        "scoring_weights": {
            "potency": 0.40,
            "interface_score": 0.30,
            "backbone_quality": 0.20,
            "developability": 0.10,
        },
        "enable_structure_prediction": True,
        "verbose": True,
    },
)

for candidate in result["design_report"]["ranked_candidates"][:3]:
    print(f"Candidate: {candidate['sequence']}")
    print(f"  Potency: {candidate['scores'].get('potency', 0):.3f}")
    print(f"  Interface Score: {candidate['scores'].get('interface_score', 0):.3f}")
    print(f"  Backbone Quality: {candidate['scores'].get('backbone_quality', 0):.3f}")
    print(f"  Composite: {candidate['composite_score']:.3f}")
```

### Example 7: Evaluation Mode - Detailed Risk Assessment

```python
result = await run_evaluation_mode(
    user_input="""
    Evaluate candidates for:
    1. Sub-5 nM potency
    2. >20x selectivity
    3. Low aggregation risk
    4. Synthetic feasibility
    """,
    candidates=[
        "Ac-Lys-Cys-Phe-Gly-Cys-Pro-Lys-Ile-Ser-Arg-Leu-Cys-NH2",
        "Ac-Gln-Cys-Phe-Gly-Cys-Pro-Lys-Ile-Ser-Arg-Leu-Cys-NH2",
    ],
    mcp_url="http://81.70.177.174:10047/mcp",
    config={
        "model_id": "model_20251231_143052",
        "enable_structure_prediction": True,
        "verbose": True,
    },
)

for eval_result in result["evaluation_report"]["evaluated_candidates"]:
    print(f"\nCandidate: {eval_result['candidate_id']}")
    print(f"Risk Factors: {len(eval_result.get('risk_factors', []))}")
    for risk in eval_result.get('risk_factors', []):
        print(f"  - {risk}")
```

### Example 8: Reusing Insight Mode Results in Design

```python
# Step 1: Run Insight mode and get model ID
insight_result = await run_insight_mode(
    user_input="Train a comprehensive model",
    data_path="/path/to/sar.csv",
    mcp_url="http://81.70.177.174:10047/mcp",
    config={"insight_depth": "full"},
)

model_id = insight_result.get("model_id")
sar_findings = insight_result.get("sar_findings")

# Step 2: Run Design mode using the trained model
design_result = await run_design_mode(
    user_input="Optimize based on SAR insights",
    parent_peptides=["Ac-Cys-Leu-Pro-Ile-His-Phe-Arg-Tyr-Cys-Ser-Leu-Cys-Met-NH2"],
    mcp_url="http://81.70.177.174:10047/mcp",
    config={
        "model_id": model_id,  # Reuse trained model
        "sar_findings": sar_findings,  # Provide SAR context
        "max_mutations": 2,
    },
)
```

### Example 9: Design Mode with Remote Structure Prediction (SSH Adapter)

When structure prediction tools run on a remote server, use the SSH adapter:

```python
result = await run_design_mode(
    user_input="Design candidates with structure-based scoring",
    parent_peptides=["Ac-Cys-Leu-Pro-Ile-His-Phe-Arg-Tyr-Cys-Ser-Leu-Cys-Met-NH2"],
    mcp_url="http://remote-server:10047/mcp",
    config={
        "remote_host": "Syneron1",  # SSH host alias
        "max_mutations": 3,
        "enable_structure_prediction": True,
        "verbose": True,
    },
)

# The SSH adapter automatically:
# 1. Uploads input CSV to remote server
# 2. Runs structure prediction on remote server
# 3. Downloads results (CIF files, confidence JSONs) back to local machine
# 4. Auto-detects chain IDs from CIF files for energy scoring
```

**SSH Adapter Features**:
- **Automatic File Transfer**: Handles upload/download transparently
- **Chain ID Auto-Detection**: Automatically detects protein and ligand chains from CIF files
- **Error Handling**: Robust error handling with cleanup on failures
- **Remote Host Configuration**: Set `remote_host` in config (default: "Syneron1")

### Example 10: REST API Integration

```python
from fastapi import APIRouter
from pydantic import BaseModel
from local_agent.langgraph.workflows.computational_biologist_copilot import run_pipeline

class CopilotRequest(BaseModel):
    user_input: str
    data_path: str | None = None
    mode: str | None = None  # "insight" | "design" | "evaluation"

router = APIRouter()

@router.post("/api/copilot/run")
async def run_copilot(req: CopilotRequest) -> dict:
    config: dict = {"verbose": True}
    if req.data_path:
        config["data_path"] = req.data_path
    if req.mode:
        config["mode"] = req.mode

    result = await run_pipeline(
        user_input=req.user_input,
        mcp_url="http://81.70.177.174:10047/mcp",
        config=config,
    )
    return result
```

---

## Error Handling

### Handling Errors in Results

```python
try:
    result = await run_pipeline(
        user_input="Analyze SAR patterns",
        mcp_url="http://81.70.177.174:10047/mcp",
        config={"data_path": "/path/to/data.csv"}
    )
    
    # Check for clarification needed
    if result.get('clarification_needed'):
        print(f"Clarification needed: {result.get('clarification_question')}")
        # Handle clarification case
    
    # Check for errors
    elif result.get('error'):
        print(f"Error: {result.get('error')}")
        # Handle error case
    
    else:
        print("Workflow completed successfully")
        # Access results
        report = result.get('insight_report')  # or design_report, evaluation_report
        
except Exception as e:
    print(f"Pipeline execution failed: {e}")
```

### Common Issues and Solutions

**Issue: Missing data_path for Insight mode**
- Ensure `data_path` is provided in config or user_input
- Check file permissions and path validity

**Issue: Missing parent_peptides for Design mode**
- Provide `parent_peptides` in config or user_input
- Ensure sequences are valid peptide sequences

**Issue: MCP timeout during model training**
```python
config = {
    "mcp_timeout": 600.0,  # Increase timeout for long-running operations
    "verbose": True
}
```

**Issue: Mode classification fails**
- Use explicit mode parameter: `run_insight_mode()`, `run_design_mode()`, etc.
- Or provide clearer user_input with mode-specific keywords

---

## Best Practices

### Data Preparation

1. **SAR Table Format**: Ensure your SAR table has:
   - Sequence columns (AA0–AA16, Sequence, etc.)
   - Key assay columns (e.g. ACVR2A reporter IC50)
   - Consistent naming conventions

2. **Parent Sequences**: For Design mode, provide:
   - Valid peptide sequences
   - Sequences with known activity (if available)
   - Multiple parents for diversity

### Workflow Selection

1. **Use Light Path** for quick questions about patterns or trends
2. **Use Full Path** when you need:
   - Comprehensive analysis
   - Model predictions
   - SHAP explanations
   - Design strategies

3. **Use Multi-Round Optimization** for:
   - Iterative refinement
   - Complex objectives
   - When you have time for multiple rounds

### Performance Optimization

1. **Caching**: Use `table_id` and `model_id` to cache parsed tables and trained models
2. **Async Operations**: Enable async structure prediction for design mode
3. **Timeout Configuration**: Adjust `mcp_timeout` for long-running operations
4. **Multi-Server MCP**: Distribute load across multiple MCP servers
5. **SSH Adapter**: Use remote structure prediction when local resources are limited
6. **Multi-Round Optimization**: Use plateau patience to prevent premature stopping

### Logging

1. **Enable file logging** for production runs
2. **Use verbose mode** only for debugging
3. **Review logs** to understand decision-making process

---

## Logging and Explainability

The workflow includes a comprehensive logging system that tracks all decisions, tool calls, and model interactions for complete transparency.

### Enabling Logging

```python
config = {
    "enable_file_logging": True,  # Save logs to disk (default: True)
    "log_dir": "./logs/copilot_runs",  # Log directory (default: ./logs/copilot_runs/)
    "verbose": True,  # Print logs to console (default: False)
}

result = await run_pipeline(
    user_input="Analyze SAR patterns",
    mcp_url="http://81.70.177.174:10047/mcp",
    config=config,
)
```

### Log Output Structure

Logs are saved to `logs/copilot_runs/{run_id}/` with the following structure:

```
logs/copilot_runs/{run_id}/
├── full_log.json              # Complete log with all categories
├── decisions.json             # Decision log only
├── tool_calls.json            # Tool call log only
├── model_io.json              # Model I/O log only
├── candidate_journeys.json    # Molecular journey log only (Design mode)
├── performance.json           # Performance metrics only
└── user_narrative.md          # Human-readable narrative
```

### Accessing Logs Programmatically

```python
result = await run_pipeline(
    user_input="Analyze SAR",
    mcp_url="http://81.70.177.174:10047/mcp",
    config={"enable_file_logging": True}
)

# Get logger from result
exp_logger = result.get("explainability_logger")

if exp_logger:
    # Generate summary
    summary = exp_logger.generate_summary()
    
    print(f"Total Duration: {summary['total_duration_ms']:.0f}ms")
    print(f"Decisions Made: {summary['summary']['decisions_made']}")
    print(f"Tools Called: {summary['summary']['tools_called']}")
    
    # Access specific log categories
    decisions = summary['decision_log']
    tool_calls = summary['tool_call_log']
    
    print("\n=== Key Decisions ===")
    for decision in decisions:
        print(f"{decision['decision_point']}: {decision['decision']}")
        print(f"  Reasoning: {decision['reasoning']}")
```

### Reading Saved Log Files

```python
import json

run_id = "run_20251231_143052_a8b3c4d5"
log_dir = f"./logs/copilot_runs/{run_id}"

# Read decision log
with open(f"{log_dir}/decisions.json", "r") as f:
    decisions = json.load(f)

# Read user narrative (human-readable)
with open(f"{log_dir}/user_narrative.md", "r") as f:
    narrative = f.read()
    print(narrative)
```

### Log Categories

1. **Decision Log**: Routing choices with reasoning and alternatives
2. **Tool Call Log**: MCP interactions with inputs/outputs and timing
3. **Model I/O Log**: LLM interactions with prompts and responses
4. **Candidate Journey Log**: Candidate evolution in Design mode (generation → scoring → ranking)
5. **Performance Log**: Timing for each workflow stage
6. **User Narrative**: Human-readable explanations of workflow execution

### Performance Impact

Logging has minimal overhead:
- **Insight Light**: +0-1 second
- **Insight Full**: +1-2 seconds
- **Design Mode**: +2-4 seconds

**Recommendations:**
- ✅ Enable file logging for production (minimal overhead)
- ✅ Enable verbose console logging only for debugging
- ⚠️ Overhead scales with candidate count in design mode

---

### Problem: Workflow returns clarification request

**Solution:** Provide missing information:
- For Insight mode: ensure `data_path` is set
- For Design mode: ensure `parent_peptides` is set
- For Evaluation mode: ensure `candidates` is set

### Problem: MCP tool calls timeout

**Solution:** Increase timeout:
```python
config = {
    "mcp_timeout": 600.0,  # Increase from default 300.0
}
```

### Problem: Mode classification incorrect

**Solution:** Use explicit mode:
```python
# Instead of run_pipeline, use:
result = await run_insight_mode(...)  # or run_design_mode, run_evaluation_mode
```

### Problem: Low-quality candidates in Design mode

**Solution:** 
- Provide better parent sequences
- Adjust scoring weights
- Enable multi-round optimization
- Check SAR insights for guidance

### Problem: Logs not being generated

**Solution:** Enable logging in config:
```python
config = {
    "enable_file_logging": True,
    "log_dir": "./logs/copilot_runs",
}
```

### Problem: Multi-round optimization stops too early

**Solution:** Adjust plateau patience:
```python
config = {
    "design": {
        "multi_round_optimization": {
            "plateau_patience": 3,  # Increase from default 2
            "convergence_threshold": 0.005,  # Lower threshold for more sensitivity
        }
    }
}
```

### Problem: SSH adapter file transfer fails

**Solution:** 
- Ensure SSH connectivity: `ssh Syneron1` should work
- Check that MCP server and SSH host share the same filesystem
- Verify file permissions on remote server
- Check disk space on remote server

---

## Working Directory Structure

All intermediate results, generated reports, and artifacts are saved to a working directory. The default location is:

```
results/copilot/<run_id>/
```

The working directory structure:
```
<run_dir>/
├── insight_report.md          # Insight Mode report (if applicable)
├── design_report.md           # Design Mode report (if applicable)
├── evaluation_report.md       # Evaluation Mode report (if applicable)
├── state.json                 # Final workflow state
└── artifacts/                 # Additional artifacts (if any)
    ├── sar_findings.json
    ├── candidate_designs.json
    └── ...
```

---

## Additional Resources

- **Developer Guide**: See `README.md` for technical implementation details
- **Code Examples**: See `logging_integration_guide.py` for logging integration patterns
- **MCP Tools**: Refer to MCP server documentation for available tools

---

## Support

For questions or issues:
1. Check this user guide's troubleshooting section
2. Review the developer guide for technical details
3. Check logs in `logs/copilot_runs/{run_id}/` for execution details

