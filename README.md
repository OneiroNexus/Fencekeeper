# Fencekeeper
## Before you forget, check what still depends on it.

**Aaron Michael Weis (ΩNeiron™)** · [ORCID 0009-0002-1906-148X](https://orcid.org/0009-0002-1906-148X) · v0.1.0

Fencekeeper is a local, review-bound **memory retirement inspector**. It separates stale records from a proposed current-context view without deleting the original packet. Before finalizing a retirement, it checks declared dependencies, replacements and coupled restrictions. Revoked permissions remain non-authorizing regardless of whether a retirement review has finished.

The package includes a Python tool, **six visible ablation switches**, synthetic experiments, a working methods paper, a natural-language blog draft, and a **read-only Godot 4 comparison viewer**. A small Wolfram graph-check companion is also included.

**Release state:** owner-review candidate. No public repository or DOI has been assigned here. Public reuse and training terms have not been selected; see `RIGHTS.md`. The Godot and Wolfram source companions were **not executed** in the build environment. Nothing was installed in the owner's MemoryNexus project.

## What it is useful for

- **Agent memory:** keep a superseded preference from continuing to support a plan.
- **MemoryNexus/Godot:** inspect a memory snapshot before generating an NPC/agent context or accepting a revised world-state note.
- **Permission changes:** keep a revocation visible while its historical record is preserved.
- **Evaluation:** show exactly what happens when a dependency, revocation or review rule is disabled.
- **Human review:** make the rationale, replacement and coupled restrictions explicit.

It does not infer dependencies from prose, determine factual truth, authenticate permissions, modify model weights, guarantee a model will obey the context, or erase private information. All hard dependencies in this version are **required together**; alternative support paths are not modeled.

## Quick start — Python only

Run from the source folder, with Python 3.10+ intended. The observed environment was CPython 3.13.15/Linux x86_64. No runtime dependencies are required.

```sh
python -m fencekeeper --help
python -m fencekeeper audit examples/coupled-restriction-chain.packet.json --output new-report.json
python -m fencekeeper plan examples/approved-retirement.packet.json --output new-review.json
```

The first audit intentionally returns exit **1**: current records still depend on a stale premise. Read `new-report.json`; do not treat the exit as a crash.

Review plans start with `approved: false`. A real reviewer must inspect the record, destination, constraints and rationale. The included approved reviews are conspicuously **fictional test fixtures**, not the author's approval.

Create a new preview bundle without modifying any source:

```sh
python -m fencekeeper project examples/coupled-restriction-chain.packet.json --output new-preview
```

That preview carries the held restriction in `conservative_guards`, even though its factual dependency is unresolved. It also preserves the exact input bytes in `source-packet.json`, retains quarantine/history, and writes a checksum manifest last. It does **not** alter an existing memory store.

For the fictional approved example only:

```sh
python -m fencekeeper project examples/approved-retirement.packet.json --review examples/approved-retirement.review.json --output approved-example-preview
```

### Portable command

The included `dist/fencekeeper-0.1.0.pyz` contains the same Python core:

```sh
python dist/fencekeeper-0.1.0.pyz --help
```

It still needs a compatible Python interpreter. It is not a native Windows executable.

## Visible experiments — never a hidden production switch

```sh
python -m fencekeeper ablate examples/coupled-restriction-chain.packet.json --disable dependency_check --output dependency-off.json
python tools/ablation_bench.py --output new-ablation.json
```

An ablated report says `EXPERIMENT_ONLY`, lists every disabled module, and returns exit **3**. The `project` command has **no ablation option**. The report is inspectable experimental data, not authorization to act.

| Module | What disabling it tests |
| --- | --- |
| `dependency_check` | Whether stale premises leave current dependents wrongly active. |
| `supersession_filter` | Whether superseded records re-enter current context. |
| `revocation_filter` | Whether revoked or unreinstated permission records become eligible. |
| `coupling_ack` | Whether a retirement can bypass acknowledgement of coupled current information. |
| `review_binding` | Whether an approval for a different packet can be reused. |
| `constraint_carry` | Whether held current restrictions disappear from the guard overlay. |

See `docs/ABLATIONS.md` for the measured table, expected labels and limitations. A disabled rule is a deliberate contract violation, not evidence that all real agents need this exact architecture.

## Supported release scope

This packet supports the Python CLI and standalone zipapp. The Wolfram JSON fixture is retained as a synthetic input to the Python tests. Godot and Wolfram runtimes remain outside this release's support scope.

## Reproduce the recorded checks

See [Verification and packaging](docs/REVIEW_STATUS.md) for the Windows
validation option and the CI evidence.

```sh
python -m unittest discover -s tests -v
python tools/validate.py --output new-validation
python tools/build_zipapp.py --output new-fencekeeper.pyz
python tools/check_packaging.py --zipapp new-fencekeeper.pyz --output new-packaging.json
```

Choose new output paths. Validation records each test outcome and the complete ablation matrix. It does not select the newest receipt from a directory. The build uses fixed ZIP metadata; the packaged command was run outside the source tree.

Recorded: **92 unit tests passed; 50 synthetic baseline cases matched their authored expectations; 350 comparison rows were produced; 10 packaging checks passed.** These are local implementation checks, not real-world memory accuracy or independent validation. The cases comprise ten scenario families with five correlated variants each.

## Read the package

| Artifact | Purpose |
| --- | --- |
| `paper/Before_You_Forget_v0.1.0.pdf` | Working methods paper with source-reviewed related work. |
| `paper/Before_You_Forget_v0.1.0.md` | Editable paper source. |
| `docs/RECORD_CONTRACT.md` | Exact data model, state rules and review boundary. |
| `docs/ABLATIONS.md` | Visible module registry and results interpretation. |
| `docs/LIMITATIONS.md` | What the prototype cannot establish. |
| `fixtures/cases.json` | Synthetic inputs, reviews and expected outputs. |
| `evidence/reference-run/` | Named unit log, validation receipt and experiment rows. |
| `evidence/packaging.json` | Standalone build checks. |

## Exit contract

| Code | Meaning |
| --- | --- |
| 0 | A normal preview is ready/reviewed, or a pending plan was written. Not a truth or safety certificate. |
| 1 | A normal report/preview was written and unresolved review work remains. |
| 2 | Invalid input or a failed I/O operation. A new partial output may remain. |
| 3 | An experiment-only report was written with a rule disabled. |

Source/history files may contain sensitive data. Do not upload the entire bundle to an agent by default. This is **not a PII redactor or privacy-erasure tool**.

## Citation and authorship

Weis, Aaron Michael. *Fencekeeper: Dependency-Aware Retirement of Stale AI Memory*. Version 0.1.0. Software and working methods draft. ORCID: 0009-0002-1906-148X. See RIGHTS.md for MIT software and CC BY 4.0 paper terms.

`CITATION.cff` supplies the same attribution. Requirements and direction came from the author; OpenAI's assistant through Notion AI assisted implementation, tests, packaging and writing. Human author review remains distinct. See `docs/RELATED_WORK.md`; this release does not claim to have invented dependency-aware memory revision, truth maintenance or ablation studies.
