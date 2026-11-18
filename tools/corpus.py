"""Synthetic fixtures only. Reviews name a fictional fixture reviewer."""
from __future__ import annotations

import copy

from fencekeeper.core import fingerprint, review_template


def record(rid, *, kind="fact", key=None, scope="demo-world", revision=1,
           status="current", text=None, purpose="Retain the declared demo fact.",
           depends=(), successor=None, reinstates=()):
    return {
        "id": rid, "kind": kind, "scope": scope, "key": key or rid,
        "revision": revision, "status": status,
        "text": text or f"Synthetic information for {rid}.",
        "purpose": purpose, "source_ref": "fixture:synthetic-author-event",
        "depends_on": list(depends), "superseded_by": successor,
        "reinstates": list(reinstates),
    }


def packet(records, requested=(), couplings=()):
    return {"schema": "fencekeeper.packet.v1", "records": records,
            "couplings": list(couplings), "requested_retirements": list(requested)}


def pair():
    return [
        record("old", key="setting", status="superseded", successor="new",
               text="The synthetic scene uses setting A.",
               purpose="Record the previous setting and its replacement."),
        record("new", key="setting", revision=2,
               text="The synthetic scene now uses setting B."),
    ]


def approved(p, *, acknowledge=()):
    review = review_template(p)
    for d in review["decisions"]:
        d.update(approved=True, reviewer="FICTIONAL FIXTURE REVIEWER",
                 rationale="Synthetic approval for testing; not a real-person decision.",
                 acknowledged_couplings=list(acknowledge))
    return review


def family(name):
    if name == "pending-supersession":
        p = packet(pair() + [record("extra")], ["old"])
        return p, None, {"active_ids": ["extra", "new"], "guard_ids": [], "history_ids": []}
    if name == "approved-retirement":
        p = packet(pair(), ["old"])
        return p, approved(p), {"active_ids": ["new"], "guard_ids": [], "history_ids": ["old"]}
    if name == "dependent-current-record":
        p = packet(pair() + [record("child", depends=["old"])], ["old"])
        return p, None, {"active_ids": ["new"], "guard_ids": [], "history_ids": []}
    if name == "coupled-restriction-chain":
        p = packet(pair() + [
            record("child", depends=["old"]),
            record("fence", kind="constraint", depends=["child"],
                   text="Do not export private scene identifiers.")], ["old"])
        return p, None, {"active_ids": ["new"], "guard_ids": ["fence"], "history_ids": []}
    if name == "missing-coupling-ack":
        group = {"id": "bundle", "members": ["old", "fence"],
                 "reason": "The previous setting was recorded beside a persistent restriction."}
        p = packet(pair() + [record("fence", kind="constraint")], ["old"], [group])
        return p, approved(p), {"error": "COUPLING_NOT_ACKNOWLEDGED"}
    if name == "revoked-permission":
        p = packet([record("context"), record("grant", kind="permission", key="publish",
                   status="revoked", text="Historical permission; explicitly revoked.")])
        return p, None, {"active_ids": ["context"], "guard_ids": [], "history_ids": []}
    if name == "missing-explicit-reinstatement":
        p = packet([
            record("old-grant", kind="permission", key="publish", status="revoked"),
            record("new-grant", kind="permission", key="publish", revision=2)])
        return p, None, {"active_ids": [], "guard_ids": [], "history_ids": []}
    if name == "stale-review":
        p = packet(pair(), ["old"])
        review = approved(p)
        p["records"][1]["text"] += " The input changed after the review."
        return p, review, {"error": "STALE_REVIEW"}
    if name == "false-but-consistent-review":
        rows = pair()
        rows[0]["text"] = "The measured value must equal 5."
        rows[1]["text"] = "The measured value must exceed 5."
        p = packet(rows, ["old"])
        return p, approved(p), {"active_ids": ["new"], "guard_ids": [], "history_ids": ["old"]}
    if name == "explicit-reinstatement":
        p = packet([
            record("condition", kind="constraint"),
            record("old-grant", kind="permission", key="publish", status="revoked"),
            record("new-grant", kind="permission", key="publish", revision=2,
                   reinstates=["old-grant"], depends=["condition"])])
        return p, None, {"active_ids": ["condition", "new-grant"],
                        "guard_ids": ["condition"], "history_ids": []}
    raise ValueError(name)


FAMILIES = (
    "pending-supersession", "approved-retirement", "dependent-current-record",
    "coupled-restriction-chain", "missing-coupling-ack", "revoked-permission",
    "missing-explicit-reinstatement", "stale-review",
    "false-but-consistent-review", "explicit-reinstatement",
)


def cases():
    output = []
    for name in FAMILIES:
        for variant in range(5):
            p, review, expected = family(name)
            p = copy.deepcopy(p)
            # Deterministic variations affect scope, revision labels and prose,
            # not the expected relationships.
            for row in p["records"]:
                row["scope"] = f"synthetic-scene-{variant}"
                row["revision"] += variant * 3
                row["text"] += f" Fixture variant {variant}."
            if review is not None:
                review = copy.deepcopy(review)
                review["packet_sha256"] = (
                    "0" * 64 if name == "stale-review" else fingerprint(p))
            output.append({
                "id": f"{name}-{variant}", "family": name,
                "synthetic": True,
                "negative_semantic_example": name == "false-but-consistent-review",
                "packet": p, "review": review, "expected": expected,
            })
    return output