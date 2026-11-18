# Before You Forget
## Dependency-Aware Retirement of Stale AI Memory

**Aaron Michael Weis (ΩNeiron™)**

ORCID: [0009-0002-1906-148X](https://orcid.org/0009-0002-1906-148X)

**Working methods draft · Fencekeeper v0.1.0 · Prepared 17 November 2026 (America/Denver)**

### Abstract

An agent can stop retrieving an obsolete fact while continuing to use a plan that depends on it. A cleanup can also remove a restriction that was stored beside the obsolete material. These are related but distinct failures: unsupported information remains active, or a useful boundary disappears. This paper presents Fencekeeper, a local inspector for explicitly declared memory records, dependencies, supersession, revocation and coupled restrictions.

The implementation treats retirement as a change of context disposition, not deletion. Superseded and revoked records leave the normal candidate view immediately. Finalizing a retirement into retained history requires a packet-bound review, a stated purpose, a resolved replacement where applicable, no unresolved current dependent, and acknowledgement of coupled current records. A separate guard overlay carries current restrictions even when their supporting facts are held. No review can silently restore a revoked permission.

Six visible rule ablations compare the same synthetic inputs with one safeguard disabled. In the recorded environment, 92 unit tests passed. Fifty baseline cases matched their authored expectations; seven configurations produced 350 comparison rows. Disabling individual rules exposed extra active records, missed expected rejections or lost guards. Ten packaging checks passed. These are correlated synthetic implementation checks, not measurements of hallucination reduction or real-world memory accuracy.

The package includes an unexecuted Godot comparison viewer and an unexecuted Wolfram graph-check companion. A false but structurally consistent review remains accepted in an intentional negative example. The contribution is an inspectable retirement contract, runnable local implementation and explicit failure-sensitive experiment—not a new invention of dependency-aware memory revision or a semantic truth detector.

> Working principle: removing a premise must not silently preserve its unsupported consequences; retiring a fact must not silently discard a restriction.

### Keywords

Agent memory; context engineering; dependency tracking; supersession; revocation; ablation; human review; reproducible software.

### Authorship and assistance

The author supplied requirements, direction and attribution. OpenAI's assistant through Notion AI assisted implementation, test construction, packaging and writing. Human author review remains distinct. This is a working methods draft, not a peer-reviewed publication or degree thesis.

<!-- PAGE -->

## 1. The problem and its existing context

Consider a persistent assistant that remembers a scene setting, a plan based on that setting, and a restriction recorded in the same conversation. The setting changes. Simply removing its old text does not establish whether the plan remains supported. Simply keeping the entire old conversation can continue to expose obsolete facts. Either action can miss the restriction.

The “Chesterton's fence” analogy is operational here: understand a record's purpose and relationships before finalizing its retirement. It is not a rule that stale information must remain authoritative. In particular, a revoked permission must stop authorizing immediately; preserving its history cannot delay that effect.

### Related work

Context-management practice already includes compaction and structured note-taking for long-running agents. The Anthropic context-engineering article describes these approaches and their tradeoffs. Fencekeeper occupies one narrower boundary: inspecting a declared snapshot before constructing a candidate context.[^https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents]

StateGraph is especially close prior work. Wang and colleagues formulate dependency-aware state revision, recover dependency edges from interaction histories, and use counterfactual verification to distinguish support dependence from semantic relatedness. Their abstract describes invalidation when strict support fails and no independent support path remains. Fencekeeper does not claim this general problem or solution family is new. Its dependencies are manually declared, all are required together, and no edge-recovery model or alternative-support reasoning is implemented.[^https://arxiv.org/abs/2611.02912v1]

MEME evaluates evolving multi-entity memory, including Cascade, Absence and Deletion tasks. It supplies further motivation to examine relationships and post-change state rather than static retrieval alone. Fencekeeper was not evaluated on MEME, and its synthetic counts are not comparable benchmark scores.[^https://arxiv.org/abs/2605.12477]

The evaluation design also separates favorable effects from collateral loss. Vicentino's workshop abstract reports a model-internal steering result whose apparent improvement coexists with harmful known-entity changes under another audit. That is motivation for explicit negative measurements, not evidence that Fencekeeper's record-level switches operate like weight-level ablation.[^https://icml.cc/virtual/2026/79571]

### Research questions

- **RQ1:** Can a local contract keep stale records and unsupported dependents out of a candidate view while preserving originals and current restrictions?
- **RQ2:** Can a retirement review be bound to one declared snapshot without allowing it to bypass unresolved dependencies or restore revoked authority?
- **RQ3:** Can visible one-rule-off experiments expose which contract properties depend on each safeguard?

These questions concern implemented record behavior. They do not ask whether the program can discover every real dependency, authenticate a permission, or infer the truth of a successor's prose.

<!-- PAGE -->

## 2. Records, dependency closure and views

A packet contains records, coupling groups and requested retirements. A record names its ID, kind, scope, key, revision, status, text, purpose, source reference, dependencies, successor and reinstated permissions. Kinds distinguish facts, constraints, permissions, tasks and notes. Status distinguishes current, superseded, revoked and uncertain records.

The source reference is a supplied label, not a fetched or authenticated source. Revisions are explicit integers, not inferred timestamps. The parser rejects unknown fields, duplicate JSON keys, duplicate identifiers, invalid references and malformed values. There is no language-model classifier.

### Hard dependencies

Let D(r) denote the declared prerequisites of record r. An initially eligible set contains current records with unambiguous identity families and admissible permission state. Hard-dependency cycles and their downstream records are held. The algorithm then repeatedly removes any candidate r for which D(r) is not a subset of the remaining candidates.

This is conservative AND-dependency logic. An alternative independent support path is not represented. A dependency on an old record is not automatically redirected to its successor: the record owner must explicitly revise that relationship.

Two current records with the same kind, scope and key are held as ambiguous even if one has a higher revision. A supersession link must stay within that identity family and increase revision strictly. A chain resolves only at a current or revoked terminal record; an uncertain terminal remains unresolved.

### Partition and overlay

| View | Interpretation |
| --- | --- |
| Active | Records eligible for the proposed current context. |
| History | Requested retirements explicitly approved under the contract. |
| Quarantine | Every source record not in active or approved history. |
| Guards | An overlay containing all current constraints, including held constraints. |

Active, history and quarantine partition the source IDs. Guards are not a fourth disjoint group. A restriction with an unresolved prerequisite can remain both quarantined as a factual record and carried as a conservative guard.

This separation matters. Carrying “do not export private identifiers” does not assert that its old factual premise is still correct. It prevents the restriction from disappearing silently while the premise is being resolved. Conflicting guard text still requires human judgment.

### Couplings are not support edges

A coupling groups related records with a stated reason. It is not a logical dependency and can overlap other groups or form a cycle. If a requested retirement belongs to a coupling that still has a current member, the review must acknowledge that group. This makes the association inspectable without pretending that every nearby sentence logically depends on every other sentence.

The complete field contract and executable implementation accompany the paper [R1, R3].

<!-- PAGE -->

## 3. Retirement, review and revoked permissions

Superseded and revoked records are nonactive in the full configuration before review. Approval determines their final disposition into retained history; it does not permit stale content to remain authoritative while the reviewer is busy.

A requested retirement must identify a superseded or revoked record and retain a nonblank purpose. A superseded record needs a resolved replacement; a current replacement must itself be eligible. A current transitive dependent, a dependency cycle or another unresolved state blocker prevents approval. The decision must identify the exact replacement and acknowledge required couplings.

### Bound review, not authenticated review

A generated review plan contains only pending decisions. Approval is a separate boolean, with reviewer and rationale fields required when true. The review names the SHA-256 fingerprint of the structured packet.

The fingerprint uses a documented domain prefix and deterministic project JSON encoding: sorted object keys, compact separators, UTF-8, preserved array order and one trailing line feed. Unicode is not normalized. Formatting changes can preserve this structured identity; a separate raw input digest is reported by the audit command.

The binding exposes accidental stale reuse. It is not a signature, trusted timestamp or immutable evidence record. A person can edit the JSON and recompute the digest. A plausible reviewer label does not authenticate a reviewer.

### Revocation cannot wait for cleanup

Revoked permission records remain nonactive. A later current permission is blocked unless it explicitly reinstates every matching earlier revocation; equal or later revocations also block it. A retirement approval cannot serve as reinstatement. A successor ending in revocation cannot create a grant.

The context preview carries revocation tombstones separately from full history. Even so, an internally eligible permission remains an unauthenticated record. The application must use a separate authorization layer and must not interpret a successful audit exit as permission to act.

### Two examples

**A stale premise with a surviving fence.** The old setting is superseded. A current child record depends on it, and a current restriction depends on the child. Both dependent records are held. The restriction remains in the guard overlay. The retirement is not finalized while current dependents remain.

**An intentionally wrong successor.** The original says “The measured value must equal 5.” The successor says “The measured value must exceed 5.” A fictional review supplies a structurally valid approval. The contract can accept the retirement even though the propositions differ.

> A review can make a judgment explicit without making it true. The negative example is preserved so that structural consistency is not advertised as semantic preservation.

No input record is deleted, rewritten or executed by these operations.

<!-- PAGE -->

## 4. Visible ablation and observed results

The reference corpus contains ten authored scenario families with five deterministic variants each. Variants change scope labels, revision labels and prose while keeping the relationship pattern. They are correlated regression checks, not independent samples of real memory use.

Each case runs under the full configuration and six one-rule-off configurations. The resulting 350 rows retain case IDs, disabled modules, errors, active/guard/history IDs and separate difference counters. Expected labels describe the full contract; disabling a safeguard intentionally changes that contract.

| Configuration | Changed / 50 | Observed contract differences |
| --- | --- | --- |
| Full configuration | 0 | All expected views/errors matched. |
| Dependency check off | 10 | 15 extra active-record appearances. |
| Supersession filter off | 15 | 30 extra active-record appearances. |
| Revocation filter off | 15 | 20 extra active-record appearances. |
| Coupling acknowledgement off | 5 | 5 expected rejections missed. |
| Review binding off | 5 | 5 stale-review rejections missed. |
| Constraint carry off | 5 | 5 required guard appearances lost. |

An appearance counts a record ID in one comparison row. These numbers can overlap and must not be summed into an accuracy rate. The harness also measures missing active records, unexpected guards, retirement-set differences and unexpected rejections. No missing active-record appearances occurred in this selected corpus; that is not evidence of zero real-world collateral loss.

### Recorded environment and checks

The reference validation ran on CPython 3.13.15, Linux x86_64, from `2026-11-18T02:22:14.348448+00:00` to `2026-11-18T02:22:15.077172+00:00`. These are local recorded times, not external attestations.

All **92 unit tests passed**, with no failures, errors or skips. All **50 baseline cases** matched their expected views or rejection codes. All **10 packaging checks passed**, including isolated standalone execution, deterministic zipapp rebuilding, preserved input bytes, report-only experimental exit behavior and preview-manifest checks [R2].

Tracked code and fixture fingerprints remained unchanged during validation. Each test outcome and every experiment row are included. Some unit tests recheck the same corpus; these counts are not independent experiments.

### What the experiment does not show

The ablations demonstrate implementation sensitivity to its declared rules. They do not show hallucination reduction, statistical superiority, real agent task success, semantic equivalence, speed or human time savings. The false-but-consistent review is included among expected baseline outcomes; accepting it demonstrates a boundary, not a success at truth detection.

<!-- PAGE -->

## 5. Where it fits in MemoryNexus

Fencekeeper is designed to inspect an explicit snapshot between a memory update and context construction. It is not a replacement for a memory database, retrieval engine, authorization service or game runtime.

| Insertion point | Useful inspection |
| --- | --- |
| After a fact changes | Which current records still name the old premise? |
| Before constructing agent context | Which records are active, held, guarded or revoked? |
| Before finalizing a cleanup | What purpose, replacement and coupled information must be reviewed? |
| In a development panel | What changes when one named rule is disabled? |
| In regression testing | Does a past failure remain visible on the same declared input? |

### A read-only Godot companion

The included Godot 4 source loads the precomputed synthetic comparison file. Case and configuration selectors show the baseline beside a chosen experiment. All six module states remain visible, and every ablated result carries an experiment-only warning. The checkboxes display recorded states; they are not hidden switches that modify live memory.

The viewer reads bounded JSON as data. It does not execute Python, invoke a model, write memory records or apply a preview. Its checks are display-oriented rather than a second authoritative schema implementation. Godot's documented JSON permissiveness makes upstream validation important.[^https://docs.godotengine.org/en/stable/classes/class_json.html]

**Godot was not available in the recorded environment.** The source is prepared but unexecuted. The owner's Windows project was not accessed. The handoff calls for a separate demo smoke test before copying the adapter into a new, version-controlled add-on path.

### A small Wolfram companion

An optional Wolfram Language script checks reachable current dependents in one explicit graph fixture, with edges directed from premise to dependent. A Python test confirms that the fixture's expected IDs agree with the Python result.

**Wolfram was not available either.** The script was not run. Fixture agreement is not a cross-language execution test, proof of full parity or independent verification.

### The application boundary

A future MemoryNexus application adapter could consume an approved normal preview after separate policy checks. That adapter is not included. Keeping the boundary explicit prevents a research comparison from becoming an action-authorization bypass.

An ablated Python run produces a report and exit code 3. The projection command exposes no ablation option. All produced artifacts remain previews; no command applies a result to an existing store.

<!-- PAGE -->

## 6. Threat boundary, reproduction and release

The pure core performs no filesystem or network I/O and does not call a model. The CLI reads bounded snapshots and creates new files/directories. Supplied text is data: it is not executed, followed as a command or fetched as a source.

The packet limit is 4 MiB, the review limit 1 MiB, the record limit 1,000 and the aggregate relationship-member limit 20,000. These are defensive bounds, not measured denial-of-service resistance.

### Limits that cannot be hidden by a receipt

- Undeclared dependencies, omitted revocations and false source labels cannot be discovered from an otherwise consistent packet.
- All hard prerequisites are required together; alternative support paths and semantic conflict resolution are absent.
- Guard retention can overconstrain a task or carry conflicting text. It does not compel model behavior.
- Reports can expose IDs, relationships, fingerprints, reviewer labels and rationales. Context/history files include source text.
- Exclusive output creation does not protect against all hostile filesystem actors, parent-path substitution or interrupted writes. Shell redirection is outside the no-overwrite promise.
- Retirement preserves originals and history. It is not privacy erasure, secret detection or compliance evidence.

### Reproduction

From the source directory:

```text
python -m unittest discover -s tests -v
python tools/validate.py --output new-validation
python tools/build_zipapp.py --output new-fencekeeper.pyz
```

The validation command creates a fresh named receipt directory rather than overwriting an earlier run. The README supplies the separate packaging-check command and exact CLI exit contract. The source package and zipapp require only Python's standard library. Optional PDF rendering uses locally installed ReportLab and fonts.

A normal exit zero means a view/plan was produced under the contract; it is not a truth or security certificate. Exit one means a report was produced with unresolved review work. Exit two identifies input/I/O failure. Exit three identifies a report-only ablation.

### Public usefulness without private disclosure

The included examples are synthetic. No private workspace export, private provenance generator, private stamp or proprietary game mechanism is included. The author attribution and ORCID are visible; public URLs and DOI remain unassigned.

This is an owner-review release candidate. Software reuse, document/data reuse, training terms and public submission remain explicit owner decisions. No public license or external deposit was selected in this build.

<!-- PAGE -->

## 7. Conclusion and next experiments

Fencekeeper makes a deliberately limited promise: original records remain accounted for, explicitly stale records do not retain current eligibility, and a useful restriction does not disappear merely because its premise is held. Retirement review, dependency support and permission authority remain separate questions.

The visible ablations make those design choices inspectable. A reviewer can see the exact input, the disabled safeguard and the changed records, rather than trusting an aggregate “passed” label. The negative successor example prevents that inspectability from being mistaken for semantic understanding.

The next useful study would use independently labeled, consented memory tasks under matched model, retrieval and token budgets. It should measure stale facts used, restrictions lost, revoked actions attempted, useful context retained, abstentions and review effort. It should also compare alternative-support reasoning rather than assuming all dependencies are necessary. No such study is reported here.

### Selected references

**[1]** Anthropic. *Effective context engineering for AI agents.* Engineering article, 2025. [Primary article](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).

**[2]** Wang, Yiqi, et al. *A State Change Is Local, Its Consequences Are Not: Dependency-Aware State Revision for Long-Term Agent Memory.* arXiv:2611.02912v1, 2026. [Primary abstract](https://arxiv.org/abs/2611.02912v1).

**[3]** Jung, Seokwon, et al. *MEME: Multi-entity & Evolving Memory Evaluation.* arXiv:2605.12477, 2026. [Primary abstract](https://arxiv.org/abs/2605.12477).

**[4]** Vicentino, Caio S. *Hallucination-Induction, Not Calibration: When Multi-Feature SAE Steering Looks Like It Works.* ICML 2026 workshop poster page. [Primary conference page](https://icml.cc/virtual/2026/79571).

**[5]** Godot Engine documentation. *JSON.* [Documentation](https://docs.godotengine.org/en/stable/classes/class_json.html).

The cited pages/abstracts were source-reviewed; this is not a systematic review or novelty determination. Their experiments were not reproduced.

### Associated project records

**R1.** Weis, Aaron Michael. *Fencekeeper*, v0.1.0. Accompanying software and documentation. Public repository and DOI not yet assigned.

**R2.** `evidence/reference-run/validation.json`, `unittest.log`, `ablation.json`, and `evidence/packaging.json`. Local observations and fingerprints, not independent attestations.

**R3.** `fixtures/cases.json`, `docs/RECORD_CONTRACT.md`, `docs/ABLATIONS.md`, and `docs/MEMORYNEXUS_HANDOFF.md`. Inputs, expected outcomes, contract and integration boundary.