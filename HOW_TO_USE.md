# How to Use These Templates (Complete Guide)

This document explains how to use this reusable template system to systematically generate high-quality papers in new projects.

## 📁 Prerequisites (New Project Setup)

### Step 0.1 — Copy Template Files to New Project Directory

In your new project's paper directory (e.g., `your_project/paper/`), copy the following files:

```bash
# Copy these files from maco_mol directory
cp writting_instruction.md your_project/paper/
cp outline_writing.md your_project/paper/
cp paper_generation_playbook.md your_project/paper/
cp PROMPT_TEMPLATE.md your_project/paper/
cp core_novelty.md your_project/paper/  # Optional but recommended: user-provided core novelty as a file
cp assumed_results.template.json your_project/paper/assumed_results.json  # Optional, if you want to use example numbers
cp generate_plots_table.py your_project/paper/  # Optional: generate figures/tables from assumed/real results with one command
```

### Step 0.2 — Confirm Project Documentation Exists

Make sure you have:

- `README.md` (project functionality description)
- Technical documentation/design documents (architecture, algorithm details, assumptions)
- Code entry points and core module locations (at least know the paths)
- (Optional) Experiment logs/result JSONs/figures

### Step 0.3 — Decide Whether to Use Assumed Results

- **If you already have real experimental results**: Skip `assumed_results.json`, and numbers in subsequent templates will be read directly from experimental data.
- **If you need to write the paper with example numbers first**: Use `assumed_results.template.json` to create `assumed_results.json`, and follow the **single-file policy** (all placeholder numbers are in this file).
- **Recommended workflow**: First generate the complete outline → have the agent produce `assumed_results.json` based on the outline (specify required experiments + virtual SOTA results + figure/table asset specifications) → use `generate_plots_table.py` to generate conference/CNS-style figures with one command.

### Step 0.4 — (Optional) Provide the Core Novelty Upfront (Recommended)

In some cases, you already know the **core novelty** of the whole paper (the one idea the paper should revolve around).
Providing it upfront makes the outline/draft much more coherent and prevents narrative drift.

How to provide:

- Create a file in this directory: `core_novelty.md`
- Put your core novelty (1–3 sentences) in that file.
- In Template A/B/C inputs, provide the file path: `paper/core_novelty.md` (or an absolute path).

How the agent should behave:

- Treat user-provided novelty as highest-priority input.
- The agent may propose a better framing, but must not silently replace it. If meaning changes, it must ask for confirmation.

---

## 🔄 Complete Workflow (4 Stages)

### Stage 1: Inventory + Project IR (Initial Exploration)

**Goal**: Have the agent understand the project structure and produce a structured intermediate representation (IR), without writing an outline.

**Steps**:

1. **Open Template A** (in `PROMPT_TEMPLATE.md`)
2. **Fill in template variables**:

   ```text
   <PASTE or ATTACH PATHS> → Replace with your README.md, technical documentation paths
   <PATH to assumed_results.json> → If using assumed results, fill in the path; otherwise delete this line
   ```

3. **Send to agent** (e.g., in Cursor/Claude/ChatGPT)
4. **Receive output**: Should include:
   - Project IR (structured project information extraction)
   - Missing Information list (if there is unknown information)
   - Evidence map (which claims can be supported by which evidence)

**Checkpoints**:

- [ ] Are the "contribution candidates" in the IR specific enough (3-5 items)?
- [ ] Does the "evaluation plan" include datasets, baselines, ablation experiments?
- [ ] Are there more than 10 Missing Information items? (If yes, supplement documentation first before continuing)

---

### Stage 2: Generate Outline (Write Outline Only, No Body Text)

**Goal**: Produce a reviewer-ready outline where each section has specific content commitments.

**Steps**:

1. **Open Template B** (in `PROMPT_TEMPLATE.md`)
2. **Select paper type** (single choice):
   - [ ] Systems/platform/workflow (emphasize reliability, end-to-end design)
   - [ ] Algorithm/model (emphasize method novelty, experimental strength)
   - [ ] Theory (emphasize theorems, assumptions, proof clarity)
3. **Fill in template variables**:

   ```text
   <PASTE the IR from Template A> → Paste the Project IR produced in Stage 1
   <PATH> → Path to assumed_results.json (if used)
   ```

4. **Send to agent**
5. **Receive output**: Should include:
   - Selected paper type (one line)
   - Complete outline (each section has 3-8 specific bullets)
   - Figure/Table plan (each labeled Real/Assumed/Planned)
   - Claim→evidence mapping (top 10 claims)
   - Experiment list (aggregated from entire outline: Datasets / Metrics / Baselines / Ablations / Robustness / Efficiency / Error analysis)

**Checkpoints**:

- [ ] Are the bullets in the outline specific? (Cannot be "we discuss X", should be "definition of X + comparison with Y + experimental results of Z")
- [ ] Is each Figure/Table labeled with evidence status (Real/Assumed/Planned)?
- [ ] Can contribution points be verified in Method + Evaluation?
- [ ] If the outline is not strong enough, go back to Stage 1 to supplement IR or modify Template B instructions

**💡 Tip**: If the outline quality is unsatisfactory, **do not jump directly to writing the body text**. Fix the outline first, because subsequent expansion will strictly follow the outline.

---

### Stage 3: Expand Outline into Complete Paper

**Goal**: Expand the outline into a complete paper draft, strictly following the assumed-results single-file policy.

**Steps**:

1. **Open Template C** (in `PROMPT_TEMPLATE.md`)
2. **Fill in template variables**:

   ```text
   <PASTE outline> → Paste the outline produced in Stage 2
   <PASTE or ATTACH PATHS> → Project documentation paths
   <PATH> → assumed_results.json path (if used)
   ```

3. **Send to agent**
4. **Receive output**: Complete paper draft (a full `paper.tex`-style manuscript with detailed sections, equations, and concrete experimental protocol text)

**Checkpoints**:

- [ ] Is the Abstract 150-220 words with no citations?
- [ ] Does each table/figure using assumed numbers include "**Assumed**" in the caption?
- [ ] Is notation consistent (symbols defined once, used consistently throughout)?
- [ ] Are there "marketing claims" (e.g., "universal guarantee")? If yes, change to scoped statements.

#### If your generated paper is too short / not rich enough (most common issue)

This usually happens because Template C does not enforce length/depth by default, or because you skipped the outline, or because you did not provide the existing LaTeX skeleton.

**Fix (recommended)**: run Template C in “FULL DRAFT MODE” by adding the following constraints to your prompt:

```text
FULL DRAFT MODE (anti-shortness constraints):
- You MUST use the existing LaTeX skeleton if provided (e.g., paper/paper.tex). Do not invent a new structure.
- Output must be a full manuscript (not an outline), with detailed prose.
- Minimum depth:
  - Each major section must contain at least 3 paragraphs (except Conclusion).
  - Introduction must contain: setting + 2–4 concrete pain points + system boundary + 3–5 contributions + novelty alignment paragraph.
  - Method/System sections must include at least: interfaces, data/control flow, failure handling, and at least 2 equations or pseudo-formal definitions.
  - Experimental Setup must specify: datasets (what is real vs assumed), split protocol, metrics, baselines, ablations, and robustness suite.
- Target length: roughly 6–8 pages of content (typical conference draft), i.e., ~3,000–5,000 English words.
- If you cannot fit everything, output ONE section at a time (start with Introduction + Methodology), but keep the same skeleton and cross-references.
```

**Fix (fast)**: regenerate only the weakest section (often `Related Work` or `Experimental Setup`) with explicit “minimum 3 paragraphs + concrete protocol text” constraints, instead of rewriting the whole paper.

**⚠️ Important**:

- If you find the body text deviates from the outline or quality is substandard, **modify Template C instructions** (e.g., require stricter adherence to outline), regenerate the corresponding section.
- Do not rewrite the entire paper at once, prioritize fixing problematic sections.

---

## 🔧 Optional: Generate Figures/Tables from JSON with One Command (Highly Recommended)

### Goal

- Make `assumed_results.json` / `real_results.json` the **single source of truth** for numbers.
- When writing the paper, only reference generated `assets/figs/*` and `assets/tables/*`.

### Generate (Assumed)

Run in your paper directory:

```bash
python generate_plots_table.py --results assumed_results.json --outdir .
```

Default output:

- `assets/figs/*.pdf` + `assets/figs/*.png`
- `assets/tables/*.tex` + `assets/tables/*.png`

### Replace with Real Results

When real experimental results are available, organize them into `real_results.json` with the same schema (usually only need to replace `experiments[*].values/series/points`), then run:

```bash
python generate_plots_table.py --results real_results.json --outdir .
```

This way, the paper only needs to change the "Assumed" labels and a small amount of narrative to real descriptions.

---

### Stage 4: Reviewer Attack Self-Review + Targeted Revision

**Goal**: Discover potential rejection issues from a reviewer's perspective and produce a revised version.

**Steps**:

1. **Open Template D** (in `PROMPT_TEMPLATE.md`)
2. **Fill in template variables**:

   ```text
   <PASTE paper draft> → Paste the complete draft produced in Stage 3
   <PATH> → assumed_results.json path (if used)
   ```

3. **Send to agent**
4. **Receive output**: Should include:
   - Ranked issue list (top 12 issues)
   - Specific fix suggestions for each issue
   - Revised: Abstract, Contributions, Methodology outline, Limitations

**Checkpoints**:

- [ ] Does the issue list include: fabrication, notation inconsistency, unfair baselines, unverifiable contributions, etc.?
- [ ] Are fix suggestions specific? (Not "improve writing", but "add complexity analysis in Section 3.2")
- [ ] Are Limitations honest? (Cannot only mention advantages)

**Follow-up Actions**:

- Based on the issue list and revision suggestions, **manually or via agent rewrite** the corresponding sections.
- If there are too many issues, consider going back to Stage 2 to regenerate the outline.

---

## 🎯 Quick Reference (Common Scenarios)

### Scenario A: Starting from Scratch, Project Documentation Complete

```text
1. Stage 1 (Template A) → Get IR
2. Stage 2 (Template B) → Get outline
3. Stage 3 (Template C) → Get paper draft
4. Stage 4 (Template D) → Get issue list + revision suggestions
5. Manual fixes → Final paper.tex
```

### Scenario B: Already Have Outline, Write Body Text Directly

```text
1. Skip Stages 1-2
2. Stage 3 (Template C, but directly provide your existing outline) → Get paper draft
3. Stage 4 (Template D) → Get issue list + revision suggestions
```

### Scenario C: Already Have Paper Draft, Only Do Self-Review

```text
1. Skip Stages 1-3
2. Stage 4 (Template D) → Get issue list + revision suggestions
3. Manual fixes
```

### Scenario D: Using Assumed Results (Example Numbers)

```text
1. Copy assumed_results.template.json → assumed_results.json
2. Fill in placeholder numbers (your expected reasonable values)
3. Reference this file path in all stage templates (A/B/C/D)
4. Ensure all tables/figures using assumed numbers produced in Stage 3 include "**Assumed**" in captions
```

### Scenario E: You Provide the Core Novelty, Agent Writes Around It

Use when you already have a clear “one-sentence novelty” and want the paper to be organized around it.

```text
1. Put your core novelty into `paper/core_novelty.md` (1–3 sentences)
2. Stage 1 (Template A) → IR includes user novelty + agent-inferred novelty + final novelty
3. Stage 2 (Template B) → outline includes novelty→contributions mapping
4. Stage 3 (Template C) → draft includes a brief "Novelty alignment" paragraph in the Introduction
```

---

## ⚠️ Common Errors and Fixes

### Error 1: Agent Output Too "Vague" or "Marketing Style"

**Cause**: Stage 1 IR may not be specific enough, or Stage 2 outline bullets may not be detailed enough.

**Fix**:

- Go back to Stage 1, explicitly require in Template A: "each contribution must have algorithm/system/theorem + experiment/proof support"
- Or directly require in Template B: "each bullet must contain specific content commitments, cannot be 'we discuss X'"

### Error 2: Agent Fabricated Datasets/Metrics/Citations

**Cause**: Template C constraints are not strong enough, or project documentation lacks experimental details.

**Fix**:

- Add hard constraint in Template C: "if experimental details are unknown, write as Planned (cannot fabricate specific numbers)"
- Or supplement experimental documentation in Stage 1 Missing Information before continuing

### Error 3: Assumed Results Scattered Throughout Body Text, Hard to Manage

**Cause**: Did not follow single-file policy.

**Fix**:

- Use `assumed_results.json` as the **only** source of numbers
- Explicitly require in Template C: "any number from assumed_results.json must be labeled '**Assumed**' in table/figure captions"
- If you find assumed numbers in the body text not in the JSON, manually move them to JSON and regenerate the corresponding section

### Error 4: Paper Type Confusion (Systems/Algorithm/Theory Mixed Together)

**Cause**: Stage 2 selected wrong primary type, or outline did not strictly follow corresponding skeleton.

**Fix**:

- Re-select primary type in Template B
- If the project truly spans types, choose **one primary** (e.g., "systems"), treat other parts as supporting sections

---

## 📝 File Checklist (Final Deliverables)

After completing all stages, your paper directory should contain:

- ✅ `paper.tex` (main manuscript)
- ✅ `references.bib` (references)
- ✅ `outline.md` (optional, Stage 2 output)
- ✅ `assumed_results.json` (**only when using example numbers**)
- ✅ (Optional) `scripts/generate_assets.py` (script to generate tables/figures from assumed/real results)
- ✅ (Optional) `assets/tables/*.tex`, `assets/figs/*.{pdf,png}` (generated tables/figures)

---

## 🚀 Next Steps: Iterative Optimization

1. **If quality is still unsatisfactory**:
   - Go back to Stage 2 to regenerate outline (this is the most time-efficient correction entry point)
   - Or modify Template C/D instructions, add project-specific constraints

2. **If a particular section is especially weak**:
   - Use Template C, but only require rewriting that section
   - Or mark that section in Template D issue list, require focused revision

3. **If you need to supplement experiments before writing**:
   - First use Template A/B to produce outline
   - Run experiments, update `assumed_results.json` (or replace with real results JSON)
   - Then use Template C to write body text

---

**Need Help?** If stuck at any stage, check:

1. Have all template variables been filled in strictly?
2. Have sufficient project documentation been provided as input?
3. Has the assumed-results single-file policy been followed (if used)?
