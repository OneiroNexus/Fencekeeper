# Visible ablations

## What “ablation” means here

One **record-processing safeguard** is disabled while the exact same supplied packet/review is analyzed. No model weights, neurons, prompts from a live model, original documents or MemoryNexus records are deleted.

The reference experiment uses ten authored families with five deterministic variants each. Variants alter scope labels, revision labels and prose while retaining the relationship pattern. The 50 cases are correlated regression checks, not 50 independent real-world observations. Baseline plus six one-rule-off configurations produces 350 rows.

`fixtures/cases.json` supplies explicit expected baseline views/errors. `evidence/reference-run/ablation.json` contains every measured row, including failures and the deliberately false-but-consistent review.

## Measured contract sensitivity

| Configuration | Cases differing from full contract | Observed differences |
| --- | --- | --- |
| Full configuration | 0 / 50 | All authored baseline expectations matched. |
| Dependency check off | 10 / 50 | 15 extra active-record appearances. |
| Supersession filter off | 15 / 50 | 30 extra active-record appearances. |
| Revocation filter off | 15 / 50 | 20 extra active-record appearances. |
| Coupling acknowledgement off | 5 / 50 | 5 expected rejections no longer occurred. |
| Review binding off | 5 / 50 | 5 stale-review rejections no longer occurred. |
| Constraint carry off | 5 / 50 | 5 required guard appearances were lost. |

“Appearances” count record IDs across rows, not unique people or independent incidents. Metrics can overlap; do not sum them into an accuracy rate. No missing active-record appearances occurred in this selected corpus, which is **not** evidence of zero collateral loss in practice.

The harness separately records extra/missing active IDs, missing/extra guards, retirement-set differences, missed expected rejections and unexpected rejections. For a fixture whose expected outcome is rejection, it checks the rejection code rather than pretending a valid expected view exists.

## Why these switches are useful

- **During MemoryNexus development:** find which declared relationship creates a hold, rather than disabling all checks because the whole system seems restrictive.
- **Before context construction:** reveal a restriction lost when a stale supporting fact is filtered.
- **During regression testing:** retain the case that once restored a revoked permission or reused a stale approval.
- **In a paper:** show the negative result beside the baseline instead of hiding it behind a single pass total.
- **In Godot:** view both outputs for the same case without writing them into live memory.

All states are visible: `modules`, `disabled_modules`, `experimental`, and `EXPERIMENT_ONLY`. The Godot checkboxes display saved states; choosing a configuration selects a precomputed result. The prototype does not execute an ablation inside Godot.

## A falsifying example that remains included

The old record says “The measured value must equal 5.” The successor says “The measured value must exceed 5.” A fictional reviewer approves the explicit successor. The record contract can accept the retirement despite changed meaning.

This is an intentional negative example, not semantic-preservation success. Fencekeeper checks supplied structure, not equivalence of propositions.

## Next experiment — not yet performed

Use multiple real, consented editing/memory tasks with independently labeled dependencies. Compare the full configuration with clearly named alternatives under the same retrieval/model/token budget. Record stale facts used, constraints lost, revoked actions attempted, useful context retained, abstentions and human review effort. Keep unsuccessful seeds and do not equate lower answer coverage with better factual reliability.

No such model experiment, user study or performance benchmark is claimed in this release.