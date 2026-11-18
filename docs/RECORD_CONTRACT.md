# Record contract — v0.1.0

This document describes the implemented Python contract, not an authorization protocol.

## Packet and records

A packet has exactly four fields: `schema` (`fencekeeper.packet.v1`), `records`, `couplings`, and `requested_retirements`. Every record has exactly the fields shown below:

```json
{
  "id": "scene-rule",
  "kind": "constraint",
  "scope": "synthetic-scene",
  "key": "export",
  "revision": 1,
  "status": "current",
  "text": "Do not export private scene identifiers.",
  "purpose": "Preserve the restriction while the scene plan changes.",
  "source_ref": "fixture:synthetic-author-event",
  "depends_on": [],
  "superseded_by": null,
  "reinstates": []
}
```

`kind` is `fact`, `constraint`, `permission`, `task`, or `note`. `status` is `current`, `superseded`, `revoked`, or `uncertain`. These are supplied assertions, not classifications extracted by a model. `source_ref` is a label; it is not fetched or authenticated.

IDs use `[A-Za-z][A-Za-z0-9_.:-]{0,79}`. A revision is an integer from 1 through 1,000,000, not a boolean or timestamp. `scope`, `key`, and `source_ref` are nonblank strings of at most 1,000 characters. Text is at most 16,000 characters. Purpose is at most 2,000 characters; an empty purpose is structurally allowed but blocks a retirement request.

The CLI accepts at most 4 MiB of UTF-8 JSON and 1 MiB for a review. It rejects duplicate keys, nonfinite numbers and unknown fields. There must be 1–1,000 records, at most 1,000 coupling groups and at most 20,000 dependency/reinstatement/coupling-member references in aggregate. The pure Python API has the record limits but does not measure the size of an already-decoded object.

## Hard dependencies and current eligibility

`depends_on` names existing record IDs. Every named dependency is required; this is AND-dependency logic, not alternative support reasoning. A record cannot depend on itself.

1. Start with records explicitly marked current.
2. Hold all records in a family with more than one current record sharing `(kind, scope, key)`. Higher revision alone does not choose a winner.
3. Hold hard-dependency cycles and their downstream records.
4. Apply the permission rule below.
5. Repeatedly remove a candidate whose dependencies are not all eligible, until stable.

The algorithm does not silently redirect dependencies from an old record to its successor. A task that named the old premise must be deliberately revised by its owner. Strictly increasing revision links prevent a supersession cycle. Hard-dependency cycles are allowed as input but held nonactive rather than treated as valid support.

## Supersession

Only a superseded record may have `superseded_by`. The successor must have the same kind, scope and key and a strictly greater revision. A chain resolves only at a current or revoked terminal record. A missing link or uncertain terminal remains unresolved.

Superseded information is excluded from the normal candidate context **before** a retirement review. Approval finalizes its disposition into history; it does not decide whether stale information remains current.

## Revocation and reinstatement

A revoked record is never in the normal active view. A current permission is blocked if any matching revoked permission has an equal/later revision or is absent from its `reinstates` list. Every reinstated ID must itself identify an earlier revoked permission with matching scope/key.

Reinstatement is an explicit later record, not an inference from a pleasant rationale, a newer timestamp, preserved history or a retirement approval. A successor ending in revocation cannot create a grant.

**Critical boundary:** even an eligible permission record is only internally eligible under these supplied fields. The tool cannot authenticate the grantor, detect an omitted revocation or prevent a caller from acting. An actual authorization layer must remain separate.

## Couplings are not dependencies

A coupling is `{"id": "...", "members": ["a", "b"], "reason": "..."}` with at least two existing members. It expresses an association that deserves review, not logical support.

Couplings can overlap and form cycles. When retiring a member, every coupling that still contains another current member must be acknowledged. An acknowledgement records attention; it does not prove semantic preservation.

## Four views and the guard overlay

- `active_ids`: eligible current records.
- `history_ids`: explicitly approved retirements.
- `quarantine_ids`: every remaining record.
- `guard_ids`: **overlay** containing every current constraint, including held constraints.

Active, history and quarantine partition the input IDs. Guards do not form a fourth partition; a held restriction can appear in quarantine and the guard overlay. Carrying a restriction is conservative context, not certification that its text is correct or that a model will comply. Conflicting guards require human resolution.

The projection includes revocation tombstones with ID, scope, key, revision and status. The exact original packet and full historical records remain available separately. Retirement is not deletion and does not satisfy an erasure request.

## Review

`plan` creates:

```json
{
  "schema": "fencekeeper.review.v1",
  "packet_sha256": "<computed full digest>",
  "decisions": [{
    "record_id": "old",
    "approved": false,
    "replacement_id": "new",
    "acknowledged_couplings": [],
    "reviewer": "",
    "rationale": ""
  }]
}
```

An approved retirement requires:

- A requested record explicitly superseded or revoked.
- A nonblank purpose.
- A resolved successor for superseded records; a current successor must be eligible.
- No transitive current dependent and no cycle/downstream blocker.
- The exact replacement ID, or null for a directly revoked record.
- All required coupling acknowledgements.
- Explicit boolean approval and nonblank reviewer/rationale.
- A matching packet fingerprint.

A reviewer cannot override unresolved dependency/state blockers by writing a persuasive rationale. To correct the situation, create a new packet that explicitly revises the relationships, then review that packet. False but structurally consistent assertions can still pass.

The fingerprint is SHA-256 of `Fencekeeper.Packet.v1`, a zero byte, and the project JSON encoding: sorted keys, compact separators, UTF-8, no NaN/Infinity, preserved array order and one trailing LF. Unicode is not normalized. This is **not RFC 8785** and not the raw input-file hash. Whitespace/key-order changes can preserve structured identity. `audit` additionally records the raw input-file digest.

Reviews are editable JSON, not signatures. The fingerprint detects accidental stale reuse, not fabricated approval or a maliciously rehashed packet.

## Reports and writes

`PREVIEW_READY` means the normal view has no tracked unresolved current/uncertain/supersession state or pending retirement. `REVIEWED_PREVIEW` additionally records approved retirement(s). `REVIEW_REQUIRED` means unresolved work remains. None is a semantic correctness verdict.

`project` writes only to a new directory: source snapshot, report, current context, history, pending-review template, optional supplied review, then a checksum manifest. It always uses the full safeguards. The pending template is new and unapproved even when a supplied review is also retained.

`ablate` produces a report only, with visible module states and `EXPERIMENT_ONLY`. It has no context-application operation. All commands are local; input strings are data, not instructions.