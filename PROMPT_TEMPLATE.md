# PROMPT_TEMPLATE.md (Reusable)

Copy-paste templates for driving an agent to produce **high-quality** outlines and papers from project docs, with strict assumed-results handling.

You should pair this with:
- `writting_instruction.md` (protocol + branches + quality gates)
- `outline_writing.md` (IR + outline skeletons)
- `paper_generation_playbook.md` (multi-pass process)
- `assumed_results.json` (optional, single source of truth for placeholder numbers)

===============================================================================
Global optional input — Core Novelty (high priority if provided)
===============================================================================
In some cases, the user provides the **core novelty** of the whole paper. If so, the agent must organize the outline/draft around it.

How to provide it:
- Core novelty file path (recommended): <PATH to core_novelty.md>
  - Prefer `paper/core_novelty.md` as the single source of truth.

Rules:
- If provided, this is the highest-priority input.
- The agent may propose a better framing, but must not silently replace it; present alternatives and ask for confirmation if meaning changes.

===============================================================================
Template A — Inventory + Project IR (do this first)
===============================================================================
Use when you want the agent to read the project and build a structured IR (no outline yet).

```text
You are writing a conference-quality ML paper. Follow the reusable protocol in `writting_instruction.md` and the IR extraction in `outline_writing.md`.

Inputs:
- (Optional, recommended) Core novelty file: <PATH to core_novelty.md>
- Project README / dev docs: <PASTE or ATTACH PATHS>
- (Optional) Experiment artifacts: <PASTE or ATTACH PATHS>
- (Optional) Assumed results file: <PATH to assumed_results.json> (all placeholder numbers must come from this file only)

Task (IR only):
- Build the Project IR with the fields in `outline_writing.md` Section 1.
- Explicitly mark each field as one of: Known / Unknown / Assumed.
- Produce a short “Evidence map”: which claims can be supported by which artifacts.

Constraints:
- Do not fabricate datasets, metrics, protocols, or citations.
- If a detail is unknown, write “Unknown” and add it to a “Missing Information” list (max 10 bullets).

Output:
- Project IR (structured bullets)
- Missing Information (if any)
- Evidence map
```

===============================================================================
Template B — Outline-only (reviewer-ready outline, no prose)
===============================================================================
Use after Template A, or when the project docs are already clear.

```text
Follow `outline_writing.md` and `writting_instruction.md`.

Primary paper type (choose ONE):
- [ ] Systems / platform / workflow
- [ ] Algorithm / model / architecture
- [ ] Theory

Inputs:
- (Optional, recommended) Core novelty file: <PATH to core_novelty.md>
- Project IR: <PASTE the IR from Template A, or provide doc paths>
- (Optional) assumed_results.json: <PATH> (if present, all numbers are assumed unless proven real)

Task (outline only):
- Produce a full outline using the skeleton for the chosen paper type.
- Each section must have 3–8 concrete bullet commitments (no vague “we discuss” bullets).
- Provide a figure/table plan (3–8 items) with evidence tags: Real / Assumed / Planned.
- Provide a “claim → evidence” mapping for the top 10 claims.
- Explicitly output:
  - Final novelty statement (1–3 sentences).
  - Novelty → contributions mapping (3–5 bullets).
- Provide a “baseline plan”:
  - Must-include baselines (protocol-matched) vs optional baselines.
  - If needed, list “candidate SOTA baselines to verify via web search” (no fabricated citations).

Assumed-results policy:
- If any quantitative values appear in the outline, they must be sourced from `assumed_results.json` and labeled Assumed.

Output:
- Chosen paper type (one line)
- Outline
- Figure/Table plan with evidence tags
- Claim→evidence mapping
 - Baseline plan
```

===============================================================================
Template C — Draft paper from outline (controlled expansion)
===============================================================================
Use when you have an outline you like.

```text
Follow `writting_instruction.md` strictly (multi-pass workflow + quality gates).

Inputs:
- (Optional, recommended) Core novelty file: <PATH to core_novelty.md>
- (Strongly recommended) Existing LaTeX skeleton: <PATH to paper.tex> (if present, this is the single source of truth)
- (Recommended) BibTeX file: <PATH to references.bib> (if present)
- (Optional) Figure/table assets directory: <PATH to assets/> (if present)
- Outline: <PASTE outline>
- Project docs: <PASTE or ATTACH PATHS>
- (Optional) assumed_results.json: <PATH> (single source of truth for any placeholder numbers)

Task:
- Write a full manuscript draft in LaTeX, suitable to be saved as `paper.tex`.
- If an existing `paper.tex` is provided, you MUST preserve its preamble/macros and fill/expand the body (do not invent a new structure).
- Keep claims scoped and evidence-backed.
- Ensure the draft stays aligned with the Final novelty; include a short "Novelty alignment" paragraph at the end of the Introduction explaining how the contributions realize the novelty.
- If using assumed numbers, ensure every related table/figure caption contains the word “Assumed”.
- For baselines/SOTA:
  - Use web search if needed to find widely-accepted baselines and cite them.
  - Do not fabricate citations; list “candidate baselines needing verification” if uncertain.

Required sections:
- Title, Abstract (150–220 words, no citations), Introduction (with 3–5 contributions),
  Related Work, Methodology, Experiments, Results & Discussion, Limitations, Conclusion, References.

FULL DRAFT MODE (recommended when you want a rich paper, not a short draft):
- Output must be detailed prose, not an outline.
- Minimum depth:
  - Each major section must contain at least 3 paragraphs (except Conclusion).
  - Experimental Setup must contain concrete protocols: split/CV/seeds, metrics, baselines, ablations, robustness suite.
  - Method/System sections must include at least 2 equations or pseudo-formal definitions (as appropriate to the paper type).
  - **For Algorithm/Model papers**: The Method section MUST be written using mathematical language. All key algorithmic components (objectives, update rules, constraints, optimization procedures) must be expressed as formal mathematical equations with proper notation. Prose should explain intuition, but the core content must be mathematical.
- Target length: roughly 6–8 pages of content (typical conference draft), i.e., ~3,000–5,000 English words.
- If length would exceed the chat limit, output ONE section at a time (start with Introduction + Methodology), but keep the same LaTeX skeleton and cross-references.

Hard constraints:
- No fabricated results or citations.
- No SOTA claims unless supported by real evidence.
- Consistent notation end-to-end.

Output:
- Full paper draft (LaTeX headings + equations where needed)
```

===============================================================================
Template D — “Reviewer Attack” self-check and revision (do this last)
===============================================================================
Use after a full draft exists.

```text
You are a critical conference reviewer. Use the Quality Gates in `writting_instruction.md` Section 6.

Inputs:
- Current draft: <PASTE paper draft>
- (Optional) assumed_results.json: <PATH>

Task:
- List the top 12 concrete issues (ranked) that would cause rejection.
- For each issue: propose a specific fix (text-level, section-level, or experiment-level).
- Then provide a revised version of:
  - Abstract
  - Contributions bullets
  - Methodology section outline (subsections + what each contains)
  - Limitations section

Constraints:
- Do not invent new experiments or numbers. If proposing experiments, describe them as Planned.

Output:
- Ranked issue list + fixes
- Revised Abstract + Contributions + Methodology outline + Limitations
```


