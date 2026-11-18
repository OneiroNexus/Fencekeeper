# Selected source-reviewed related work

The following primary pages/abstracts were consulted. This is a focused comparison, not a systematic literature review. No benchmark from these works was rerun.

## StateGraph / dependency-aware state revision

Wang, Yiqi; Zhao, Tongyuan; Zhang, Jiaqi; Duan, Yiqun; Wu, Zhangkai; Zheng, Mingkai; Cai, Taotao. **A State Change Is Local, Its Consequences Are Not: Dependency-Aware State Revision for Long-Term Agent Memory.** arXiv:2611.02912v1, 2026.

[Primary abstract](https://arxiv.org/abs/2611.02912v1).

The abstract describes recovering dependency edges from interaction histories, counterfactual verification, and invalidating a dependent state when strict support fails without an independent support path. It also introduces StateChangeBench. This is close prior work and rules out a claim here that dependency-aware agent-memory revision is a newly invented general idea.

Fencekeeper is narrower: manually declared AND-dependencies, review-bound retirement, a separate guard overlay, explicit revocation handling and visible record-rule ablations. It neither reproduces StateGraph nor measures against it. The fact that both projects use a count of 50 cases does not make their corpora comparable; Fencekeeper's 50 rows come from ten families with five correlated variants each.

## MEME

Jung, Seokwon; Rubinstein, Alexander; Uselis, Arnas; Yun, Sangdoo; Oh, Seong Joon. **MEME: Multi-entity & Evolving Memory Evaluation.** arXiv:2605.12477, 2026.

[Primary abstract](https://arxiv.org/abs/2605.12477).

The abstract describes evolving multi-entity memory tasks including Cascade, Absence and Deletion. Its model/system evaluations motivate looking beyond static retrieval. Fencekeeper does not implement or claim a score on MEME.

## Context engineering

Anthropic. **Effective context engineering for AI agents.** 2025.

[Engineering article](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).

The article discusses context management, compaction and structured note-taking for long-running agents. Fencekeeper addresses one local boundary before context construction; it is not a complete context-engineering system.

## Ablation and collateral effects

Vicentino, Caio S. **Hallucination-Induction, Not Calibration: When Multi-Feature SAE Steering Looks Like It Works.** ICML 2026 workshop poster page.

[Primary conference page](https://icml.cc/virtual/2026/79571).

The abstract reports a multi-feature steering result that looks significant against a control while a separate known-entity audit exposes harmful changes. This supports reporting collateral damage rather than a single favorable number. It studies model-internal SAE steering; Fencekeeper's switches disable record-processing rules. The mechanisms and measurements are not interchangeable.

## Implementation documentation

[Godot JSON](https://docs.godotengine.org/en/stable/classes/class_json.html) and [Godot FileAccess](https://docs.godotengine.org/en/stable/classes/class_fileaccess.html) informed the optional display adapter. Documentation review is not a runtime test.

Truth maintenance, belief revision, dependency graphs, checksums, human review and ablation studies are established technique families. This project claims an inspectable implementation and bounded experiment, not ownership of those families.