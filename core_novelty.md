# Core Novelty (Single Source of Truth)

Use this file when you already know the **core novelty** of the paper and want the writing (IR/outline/draft) to revolve around it.

## User-provided core novelty

1. LLM as a Medicinal Chemist Reasoning Entity (Core Concept)

The central innovation of this work is the treatment of the LLM as a medicinal chemist ontology, rather than a text generator or heuristic proposal engine.

In this framework, the LLM:
   •  Performs explicit chemical reasoning, hypothesis formation, and trade-off analysis
   •  Interprets structure–activity signals in context
   •  Generates chemist-like insights that go beyond numerical prediction

This positions the LLM as a domain-aware reasoning entity, capable of articulating why certain molecular modifications are promising, not just what to generate.

Key distinction: the LLM reasons over chemical knowledge and evidence, instead of replacing it.

⸻

2. LLM-Orchestrated Multi-Agent Collaboration for Drug Design

We propose a multi-agent drug design architecture orchestrated by the LLM, where:
   •  Specialized agents handle structure-based inference, SAR analysis, design generation, and evaluation
   •  The LLM dynamically routes tasks, integrates feedback, and decides when deeper reasoning is required

This shifts drug design from single-pass inference to iterative, agentic reasoning loops, closer to how human medicinal chemists operate.

⸻

3. Explicit Reasoning Modes with Clear Semantic Boundaries

The system is structured into three explicit reasoning modes, each controlled and triggered by the LLM:
   •  Insights Mode
   •  Hypothesis generation
   •  Pattern discovery and interpretation
   •  Explaining observed structure–activity trends
   •  Design Mode
   •  Generating new molecular candidates under reasoning constraints
   •  Balancing exploration vs. conservativeness
   •  Evaluation Mode
   •  Quantitative assessment and structured feedback
   •  Determining next reasoning steps

This explicit mode separation enables controlled reasoning depth and avoids entangling insight generation with raw optimization.

⸻

4. Hierarchical Design Reasoning Guided by the LLM

Within Design Mode, we introduce a hierarchical reasoning structure:
   1. Data-grounded design, relying on validated structure–activity patterns
   2. Augmented reasoning, where the LLM interprets and extrapolates from these patterns
   3. Chemist-level reasoning, where the LLM evaluates competing hypotheses and proposes non-obvious modifications

Importantly, the LLM decides when to rely on empirical patterns and when to reason beyond them, enabling adaptive design strategies.

⸻

5. Interpretable SAR as a Structured Knowledge Substrate (Supporting Innovation)

Rather than treating SAR as a primary driver, this work uses interpretable, composable SAR representations as a structured knowledge substrate for LLM reasoning.

Key properties:
   •  SAR is encoded as explicit, testable rules with quantified effects
   •  Rule compatibility and compositionality are modeled explicitly
   •  Evidence chains are preserved for interpretability and validation

This allows the LLM to reason over SAR symbolically and quantitatively, instead of consuming it as unstructured correlations.

SAR here functions as externalized chemical memory, not as an autonomous decision-maker.

⸻

6. Pareto-Guided Agentic Reinforcement Learning with Reflection

The framework incorporates a Pareto-guided agentic reinforcement learning loop, where:
   •  Multi-objective trade-offs are expressed as Pareto fronts
   •  Evaluation feedback is summarized and reflected upon by the LLM
   •  Design strategies and reasoning paths are adaptively adjusted

This reflection mechanism allows the system to learn better reasoning strategies, not just better molecules.