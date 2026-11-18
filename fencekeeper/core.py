"""Pure record accounting. No network, filesystem, model or execution authority."""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict, deque

VERSION = "0.1.0"
SCHEMA = "fencekeeper.packet.v1"
MODULES = (
    "dependency_check",
    "supersession_filter",
    "revocation_filter",
    "coupling_ack",
    "review_binding",
    "constraint_carry",
)
KINDS = {"fact", "constraint", "permission", "task", "note"}
STATUSES = {"current", "superseded", "revoked", "uncertain"}
RECORD_FIELDS = {
    "id", "kind", "scope", "key", "revision", "status", "text", "purpose",
    "source_ref", "depends_on", "superseded_by", "reinstates",
}
ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,79}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class InputError(ValueError):
    """A bounded machine-readable error code, never an echo of input text."""


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def fingerprint(packet):
    return hashlib.sha256(b"Fencekeeper.Packet.v1\0" + canonical(packet)).hexdigest()


def _keys(value, fields, code):
    if type(value) is not dict or set(value) != set(fields):
        raise InputError(code)


def _text(value, maximum=16000, allow_blank=False):
    if type(value) is not str or len(value) > maximum or (
        not allow_blank and not value.strip()
    ):
        raise InputError("INVALID_TEXT")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise InputError("INVALID_UNICODE") from None


def _id(value):
    if type(value) is not str or not ID.fullmatch(value):
        raise InputError("INVALID_ID")


def _ids(value, maximum=1000):
    if type(value) is not list or len(value) > maximum:
        raise InputError("INVALID_ID_LIST")
    for item in value:
        _id(item)
    if len(set(value)) != len(value):
        raise InputError("DUPLICATE_REFERENCE")


def validate(packet):
    _keys(packet, {"schema", "records", "couplings", "requested_retirements"},
          "PACKET_FIELDS")
    if packet["schema"] != SCHEMA:
        raise InputError("PACKET_SCHEMA")
    records, groups = packet["records"], packet["couplings"]
    if type(records) is not list or not 1 <= len(records) <= 1000:
        raise InputError("RECORD_LIMIT")
    if type(groups) is not list or len(groups) > 1000:
        raise InputError("COUPLING_LIMIT")
    index = {}
    for r in records:
        _keys(r, RECORD_FIELDS, "RECORD_FIELDS")
        _id(r["id"])
        if r["id"] in index:
            raise InputError("DUPLICATE_ID")
        if (type(r["kind"]) is not str or type(r["status"]) is not str
                or r["kind"] not in KINDS or r["status"] not in STATUSES):
            raise InputError("INVALID_RECORD_ENUM")
        for key in ("scope", "key", "source_ref"):
            _text(r[key], 1000)
        _text(r["text"])
        _text(r["purpose"], 2000, allow_blank=True)
        if type(r["revision"]) is not int or not 1 <= r["revision"] <= 1_000_000:
            raise InputError("INVALID_REVISION")
        _ids(r["depends_on"])
        _ids(r["reinstates"])
        if r["id"] in r["depends_on"]:
            raise InputError("SELF_DEPENDENCY")
        if r["superseded_by"] is not None:
            _id(r["superseded_by"])
            if r["status"] != "superseded":
                raise InputError("UNEXPECTED_SUCCESSOR")
        if r["reinstates"] and r["kind"] != "permission":
            raise InputError("NON_PERMISSION_REINSTATEMENT")
        index[r["id"]] = r
    group_ids = set()
    for g in groups:
        _keys(g, {"id", "members", "reason"}, "COUPLING_FIELDS")
        _id(g["id"])
        if g["id"] in group_ids:
            raise InputError("DUPLICATE_COUPLING")
        group_ids.add(g["id"])
        _ids(g["members"])
        if len(g["members"]) < 2:
            raise InputError("SMALL_COUPLING")
        _text(g["reason"], 2000)
        if not set(g["members"]) <= index.keys():
            raise InputError("UNKNOWN_COUPLING_MEMBER")
    _ids(packet["requested_retirements"])
    if not set(packet["requested_retirements"]) <= index.keys():
        raise InputError("UNKNOWN_RETIREMENT")
    references = sum(len(r["depends_on"]) + len(r["reinstates"]) for r in records)
    references += sum(len(g["members"]) for g in groups)
    if references > 20000:
        raise InputError("REFERENCE_LIMIT")
    for r in records:
        if not set(r["depends_on"] + r["reinstates"]) <= index.keys():
            raise InputError("UNKNOWN_REFERENCE")
        if r["superseded_by"] is not None:
            successor = index.get(r["superseded_by"])
            if successor is None:
                raise InputError("UNKNOWN_SUCCESSOR")
            if any(successor[k] != r[k] for k in ("kind", "scope", "key")):
                raise InputError("SUCCESSOR_SCOPE_MISMATCH")
            if successor["revision"] <= r["revision"]:
                raise InputError("SUCCESSOR_NOT_NEWER")
        for target in r["reinstates"]:
            old = index[target]
            if (old["kind"] != "permission" or old["status"] != "revoked" or
                old["scope"] != r["scope"] or old["key"] != r["key"] or
                old["revision"] >= r["revision"]):
                raise InputError("INVALID_REINSTATEMENT")
    return index


def _cycle_or_downstream(index):
    """Kahn leftovers: cycle members and records blocked downstream of a cycle."""
    degree = {rid: len(r["depends_on"]) for rid, r in index.items()}
    reverse = defaultdict(list)
    for rid, r in index.items():
        for target in r["depends_on"]:
            reverse[target].append(rid)
    queue = deque(sorted(rid for rid, n in degree.items() if n == 0))
    removed = set()
    while queue:
        rid = queue.popleft()
        removed.add(rid)
        for dependent in reverse[rid]:
            degree[dependent] -= 1
            if degree[dependent] == 0:
                queue.append(dependent)
    return set(index) - removed, reverse


def _current_dependents(rid, index, reverse):
    seen = {rid}
    queue = deque([rid])
    while queue:
        for other in reverse[queue.popleft()]:
            if other not in seen:
                seen.add(other)
                queue.append(other)
    return sorted(x for x in seen - {rid} if index[x]["status"] == "current")


def _successor(rid, index):
    current = index[rid]
    while current["status"] == "superseded":
        target = current["superseded_by"]
        if target is None:
            return None
        current = index[target]
    return current["id"] if current["status"] in {"current", "revoked"} else None


def _review(review, packet, index, disabled):
    if review is None:
        return {}
    _keys(review, {"schema", "packet_sha256", "decisions"}, "REVIEW_FIELDS")
    if review["schema"] != "fencekeeper.review.v1":
        raise InputError("REVIEW_SCHEMA")
    if type(review["packet_sha256"]) is not str or not DIGEST.fullmatch(review["packet_sha256"]):
        raise InputError("REVIEW_DIGEST")
    if "review_binding" not in disabled and review["packet_sha256"] != fingerprint(packet):
        raise InputError("STALE_REVIEW")
    if type(review["decisions"]) is not list or len(review["decisions"]) > 1000:
        raise InputError("DECISION_LIMIT")
    result = {}
    group_ids = {g["id"] for g in packet["couplings"]}
    for d in review["decisions"]:
        _keys(d, {"record_id", "approved", "replacement_id",
                  "acknowledged_couplings", "reviewer", "rationale"},
              "DECISION_FIELDS")
        _id(d["record_id"])
        if d["record_id"] not in packet["requested_retirements"]:
            raise InputError("UNREQUESTED_DECISION")
        if d["record_id"] in result:
            raise InputError("DUPLICATE_DECISION")
        if type(d["approved"]) is not bool:
            raise InputError("APPROVAL_NOT_BOOLEAN")
        if d["replacement_id"] is not None:
            _id(d["replacement_id"])
            if d["replacement_id"] not in index:
                raise InputError("UNKNOWN_REVIEW_REPLACEMENT")
        _ids(d["acknowledged_couplings"])
        if not set(d["acknowledged_couplings"]) <= group_ids:
            raise InputError("UNKNOWN_ACKNOWLEDGEMENT")
        _text(d["reviewer"], 1000, allow_blank=not d["approved"])
        _text(d["rationale"], 4000, allow_blank=not d["approved"])
        result[d["record_id"]] = d
    return result


def analyze(packet, review=None, *, disabled_modules=()):
    """Return an inspection report. Disabled modules always mean EXPERIMENT ONLY."""
    if (type(disabled_modules) not in (tuple, list, set, frozenset)
            or any(type(item) is not str for item in disabled_modules)):
        raise InputError("INVALID_MODULE_LIST")
    disabled = set(disabled_modules)
    if not disabled <= set(MODULES):
        raise InputError("UNKNOWN_MODULE")
    index = validate(packet)
    decisions = _review(review, packet, index, disabled)
    cyclic, reverse = _cycle_or_downstream(index)
    reasons = {rid: set() for rid in index}
    families = defaultdict(list)
    for rid, r in index.items():
        if r["status"] == "current":
            families[(r["kind"], r["scope"], r["key"])].append(rid)
    ambiguous = {rid for ids in families.values() if len(ids) > 1 for rid in ids}
    eligible = set()
    for rid, r in index.items():
        allowed_status = r["status"] == "current"
        allowed_status |= r["status"] == "superseded" and "supersession_filter" in disabled
        allowed_status |= r["status"] == "revoked" and "revocation_filter" in disabled
        if not allowed_status:
            reasons[rid].add("NONCURRENT_RECORD")
        if rid in ambiguous:
            reasons[rid].add("AMBIGUOUS_CURRENT_RECORDS")
        if "dependency_check" not in disabled and rid in cyclic:
            reasons[rid].add("DEPENDENCY_CYCLE_OR_DOWNSTREAM")
        if r["kind"] == "permission" and "revocation_filter" not in disabled:
            revocations = [
                old for old in index.values()
                if old["kind"] == "permission" and old["status"] == "revoked"
                and old["scope"] == r["scope"] and old["key"] == r["key"]
            ]
            if any(old["revision"] >= r["revision"] or old["id"] not in r["reinstates"]
                   for old in revocations):
                reasons[rid].add("REVOCATION_NOT_EXPLICITLY_REINSTATED")
        if not reasons[rid]:
            eligible.add(rid)
    if "dependency_check" not in disabled:
        while True:
            lost = {rid for rid in eligible if not set(index[rid]["depends_on"]) <= eligible}
            if not lost:
                break
            for rid in lost:
                reasons[rid].add("INACTIVE_DEPENDENCY")
            eligible -= lost

    requests = set(packet["requested_retirements"])
    retired = set()
    rows = []
    pending = False
    for rid in sorted(index):
        r = index[rid]
        blockers = []
        current_dependents = _current_dependents(rid, index, reverse)
        required_groups = sorted(g["id"] for g in packet["couplings"]
                                 if rid in g["members"]
                                 and any(index[m]["status"] == "current"
                                         for m in g["members"] if m != rid))
        replacement = _successor(rid, index) if r["status"] == "superseded" else None
        disposition = "RETAIN" if rid in eligible else "HOLD_NONACTIVE"
        retirement = "NOT_REQUESTED"
        if rid in requests:
            if r["status"] not in {"superseded", "revoked"}:
                blockers.append("NO_EXPLICIT_RETIREMENT_STATE")
            if not r["purpose"].strip():
                blockers.append("MISSING_PURPOSE")
            if r["status"] == "superseded" and replacement is None:
                blockers.append("NO_RESOLVED_REPLACEMENT")
            if (replacement is not None and index[replacement]["status"] == "current"
                    and replacement not in eligible):
                blockers.append("REPLACEMENT_NOT_ELIGIBLE")
            if "dependency_check" not in disabled:
                if current_dependents:
                    blockers.append("CURRENT_DEPENDENTS")
                if rid in cyclic:
                    blockers.append("DEPENDENCY_CYCLE_OR_DOWNSTREAM")
            d = decisions.get(rid)
            if d and d["approved"]:
                if blockers:
                    raise InputError("APPROVAL_HAS_UNRESOLVED_DEPENDENCIES_OR_STATE")
                if d["replacement_id"] != replacement:
                    raise InputError("REVIEW_REPLACEMENT_MISMATCH")
                if "coupling_ack" not in disabled and not set(required_groups) <= set(d["acknowledged_couplings"]):
                    raise InputError("COUPLING_NOT_ACKNOWLEDGED")
                retired.add(rid)
                disposition = "RETIRE_FROM_ACTIVE_CONTEXT"
                retirement = "APPROVED"
            else:
                pending = True
                retirement = "REVIEW_REQUIRED"
        rows.append({
            "id": rid, "kind": r["kind"], "declared_status": r["status"],
            "disposition": disposition, "retirement": retirement,
            "reasons": sorted(reasons[rid]), "blockers": blockers,
            "current_dependents": current_dependents if rid in requests else [],
            "replacement_id": replacement if rid in requests else None,
            "couplings_requiring_ack": required_groups if rid in requests else [],
        })
    # Approved retirement must not leave an ablated record in the candidate view.
    eligible -= retired
    guards = {rid for rid, r in index.items()
              if r["kind"] == "constraint" and r["status"] == "current"}
    if "constraint_carry" in disabled:
        guards &= eligible
    held_current = {rid for rid, r in index.items()
                    if r["status"] == "current" and rid not in eligible}
    unresolved_state = {
        rid for rid, r in index.items()
        if r["status"] == "uncertain"
        or (r["status"] == "superseded" and _successor(rid, index) is None)
    }
    unresolved = bool(held_current or pending or unresolved_state)
    status = ("EXPERIMENT_ONLY" if disabled else
              "REVIEW_REQUIRED" if unresolved else
              "REVIEWED_PREVIEW" if retired else "PREVIEW_READY")
    return {
        "schema": "fencekeeper.report.v1", "tool_version": VERSION,
        "packet_sha256": fingerprint(packet), "status": status,
        "experimental": bool(disabled), "disabled_modules": sorted(disabled),
        "modules": {name: name not in disabled for name in MODULES},
        "does_not_authorize_actions": True, "source_modified": False,
        "views": {
            "active_ids": sorted(eligible),
            "guard_ids": sorted(guards),
            "history_ids": sorted(retired),
            "quarantine_ids": sorted(set(index) - eligible - retired),
            "record_eligible_permission_ids": sorted(
                rid for rid in eligible if index[rid]["kind"] == "permission"),
            "blocked_permission_ids": sorted(
                rid for rid, r in index.items() if r["kind"] == "permission" and rid not in eligible),
            "held_current_ids": sorted(held_current),
            "unresolved_state_ids": sorted(unresolved_state),
        },
        "records": rows,
        "reviewed_retirements": [
            {"record_id": rid, "reviewer": decisions[rid]["reviewer"],
             "rationale": decisions[rid]["rationale"],
             "acknowledged_couplings": decisions[rid]["acknowledged_couplings"]}
            for rid in sorted(retired)
        ],
        "counts": {"records": len(index), "active": len(eligible),
                   "guards": len(guards), "retired": len(retired),
                   "quarantined": len(index) - len(eligible) - len(retired),
                   "held_current": len(held_current)},
        "limitations": [
            "Relationships, states, sources and reviews are supplied assertions.",
            "Missing or false dependencies cannot be inferred from record prose.",
            "A review fingerprint is not a signature or proof of reviewer identity.",
            "Retirement preserves source history; this is not privacy erasure.",
            "Candidate permissions are not authenticated grants or enforcement.",
        ],
    }


def review_template(packet):
    report = analyze(packet)
    return {
        "schema": "fencekeeper.review.v1", "packet_sha256": report["packet_sha256"],
        "decisions": [
            {"record_id": row["id"], "approved": False,
             "replacement_id": row["replacement_id"],
             "acknowledged_couplings": [], "reviewer": "", "rationale": ""}
            for row in report["records"] if row["retirement"] != "NOT_REQUESTED"
        ],
    }


def make_projection(packet, review=None):
    """Full safeguards only. Returns data for a preview, never a store mutation."""
    report = analyze(packet, review)
    index = {r["id"]: r for r in packet["records"]}
    views = report["views"]
    context = {
        "schema": "fencekeeper.context.v1",
        "packet_sha256": report["packet_sha256"],
        "status": report["status"], "preview_only": True,
        "does_not_authorize_actions": True,
        "active_records": [index[rid] for rid in views["active_ids"]],
        "conservative_guards": [index[rid] for rid in views["guard_ids"]],
        "held_current_ids": views["held_current_ids"],
        "unresolved_state_ids": views["unresolved_state_ids"],
        "blocked_permission_ids": views["blocked_permission_ids"],
        "revocation_tombstones": [
            {k: r[k] for k in ("id", "scope", "key", "revision", "status")}
            for r in sorted(index.values(), key=lambda x: x["id"])
            if r["kind"] == "permission" and r["status"] == "revoked"
        ],
    }
    archive = {
        "schema": "fencekeeper.history.v1",
        "packet_sha256": report["packet_sha256"],
        "approved_retired_records": [index[rid] for rid in views["history_ids"]],
        "quarantined_records": [index[rid] for rid in views["quarantine_ids"]],
        "note": "Retained history, not deletion or erasure.",
    }
    return report, context, archive