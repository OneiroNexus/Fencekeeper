import copy
import unittest

from fencekeeper.core import (MODULES, InputError, analyze, fingerprint,
                             make_projection, review_template, validate)
from tools.corpus import approved, family, packet, pair, record


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.p = packet([record("a")])

    def reject(self, code):
        with self.assertRaisesRegex(InputError, code):
            validate(self.p)

    def test_unknown_top_field(self):
        self.p["extra"] = 1
        self.reject("PACKET_FIELDS")

    def test_unknown_record_field(self):
        self.p["records"][0]["extra"] = 1
        self.reject("RECORD_FIELDS")

    def test_bad_schema(self):
        self.p["schema"] = "later"
        self.reject("PACKET_SCHEMA")

    def test_empty_records(self):
        self.p["records"] = []
        self.reject("RECORD_LIMIT")

    def test_record_limit(self):
        self.p["records"] = [record("x" + str(i)) for i in range(1001)]
        self.reject("RECORD_LIMIT")

    def test_duplicate_record(self):
        self.p["records"] *= 2
        self.reject("DUPLICATE_ID")

    def test_invalid_id(self):
        self.p["records"][0]["id"] = "../a"
        self.reject("INVALID_ID")

    def test_boolean_revision(self):
        self.p["records"][0]["revision"] = True
        self.reject("INVALID_REVISION")

    def test_unknown_dependency(self):
        self.p["records"][0]["depends_on"] = ["missing"]
        self.reject("UNKNOWN_REFERENCE")

    def test_self_dependency(self):
        self.p["records"][0]["depends_on"] = ["a"]
        self.reject("SELF_DEPENDENCY")

    def test_duplicate_dependency(self):
        self.p["records"][0]["depends_on"] = ["other", "other"]
        self.reject("DUPLICATE_REFERENCE")

    def test_bad_text(self):
        self.p["records"][0]["text"] = ""
        self.reject("INVALID_TEXT")

    def test_surrogate(self):
        self.p["records"][0]["text"] = "\ud800"
        self.reject("INVALID_UNICODE")

    def test_unknown_successor(self):
        self.p["records"][0].update(status="superseded", superseded_by="missing")
        self.reject("UNKNOWN_SUCCESSOR")

    def test_successor_must_be_newer(self):
        self.p = packet(pair())
        self.p["records"][1]["revision"] = 1
        self.reject("SUCCESSOR_NOT_NEWER")

    def test_successor_scope(self):
        self.p = packet(pair())
        self.p["records"][1]["scope"] = "other"
        self.reject("SUCCESSOR_SCOPE_MISMATCH")

    def test_nonpermission_reinstatement(self):
        self.p["records"][0]["reinstates"] = ["a"]
        self.reject("NON_PERMISSION_REINSTATEMENT")

    def test_bad_reinstatement_scope(self):
        self.p = packet([
            record("old", kind="permission", status="revoked", key="publish"),
            record("new", kind="permission", revision=2, key="publish",
                   scope="other", reinstates=["old"])])
        self.reject("INVALID_REINSTATEMENT")

    def test_unknown_coupling_member(self):
        self.p["couplings"] = [{"id": "g", "members": ["a", "b"], "reason": "Example."}]
        self.reject("UNKNOWN_COUPLING_MEMBER")

    def test_unknown_retirement(self):
        self.p["requested_retirements"] = ["missing"]
        self.reject("UNKNOWN_RETIREMENT")


class AccountingTests(unittest.TestCase):
    def test_identity(self):
        r = analyze(packet([record("a")]))
        self.assertEqual(r["status"], "PREVIEW_READY")
        self.assertEqual(r["views"]["active_ids"], ["a"])

    def test_superseded_is_never_active_by_default(self):
        p, _, _ = family("pending-supersession")
        self.assertNotIn("old", analyze(p)["views"]["active_ids"])

    def test_revoked_permission_is_nonactive_without_review(self):
        p, _, _ = family("revoked-permission")
        r = analyze(p)
        self.assertEqual(r["views"]["blocked_permission_ids"], ["grant"])
        self.assertTrue(r["does_not_authorize_actions"])

    def test_current_dependent_is_held(self):
        p, _, _ = family("dependent-current-record")
        r = analyze(p)
        self.assertIn("child", r["views"]["held_current_ids"])
        old = next(x for x in r["records"] if x["id"] == "old")
        self.assertIn("CURRENT_DEPENDENTS", old["blockers"])

    def test_transitive_dependency(self):
        p, _, _ = family("coupled-restriction-chain")
        r = analyze(p)
        self.assertEqual(r["views"]["held_current_ids"], ["child", "fence"])
        self.assertEqual(r["views"]["guard_ids"], ["fence"])

    def test_uncertain_record_is_not_current(self):
        r = analyze(packet([record("a", status="uncertain")]))
        self.assertEqual(r["views"]["active_ids"], [])

    def test_conflicting_current_records(self):
        p = packet([record("a", key="k"), record("b", key="k", revision=2)])
        self.assertEqual(analyze(p)["views"]["held_current_ids"], ["a", "b"])

    def test_hard_dependency_cycle(self):
        p = packet([record("a", depends=["b"]), record("b", depends=["a"]),
                    record("c", depends=["a"])])
        self.assertEqual(analyze(p)["views"]["held_current_ids"], ["a", "b", "c"])

    def test_coupling_is_not_a_hard_dependency_cycle(self):
        p = packet([record("a"), record("b")], couplings=[
            {"id": "g", "members": ["a", "b"], "reason": "Related but independent."}])
        self.assertEqual(analyze(p)["views"]["active_ids"], ["a", "b"])

    def test_missing_purpose_stays_visible(self):
        p = packet(pair(), ["old"])
        p["records"][0]["purpose"] = ""
        row = next(x for x in analyze(p)["records"] if x["id"] == "old")
        self.assertIn("MISSING_PURPOSE", row["blockers"])

    def test_missing_successor_cannot_retire(self):
        p = packet([record("a", status="superseded")], ["a"])
        self.assertIn("NO_RESOLVED_REPLACEMENT", analyze(p)["records"][0]["blockers"])

    def test_uncertain_successor_cannot_retire(self):
        p = packet(pair(), ["old"])
        p["records"][1]["status"] = "uncertain"
        self.assertIn("NO_RESOLVED_REPLACEMENT", analyze(p)["records"][1]["blockers"])

    def test_successor_chain(self):
        rows = pair()
        rows[1].update(status="superseded", superseded_by="latest")
        rows.append(record("latest", key="setting", revision=3))
        p = packet(rows, ["old"])
        d = review_template(p)["decisions"][0]
        self.assertEqual(d["replacement_id"], "latest")

    def test_explicit_reinstatement(self):
        p, _, _ = family("explicit-reinstatement")
        self.assertEqual(analyze(p)["views"]["record_eligible_permission_ids"], ["new-grant"])

    def test_newer_permission_does_not_implicitly_reinstate(self):
        p, _, _ = family("missing-explicit-reinstatement")
        self.assertEqual(analyze(p)["views"]["record_eligible_permission_ids"], [])

    def test_new_revocation_blocks_earlier_reinstatement(self):
        p, _, _ = family("explicit-reinstatement")
        p["records"].append(record("revoked-again", kind="permission", key="publish",
                                   revision=3, status="revoked"))
        self.assertEqual(analyze(p)["views"]["record_eligible_permission_ids"], [])

    def test_no_mutation(self):
        p, review, _ = family("approved-retirement")
        before = copy.deepcopy((p, review))
        analyze(p, review)
        self.assertEqual((p, review), before)

    def test_deterministic_report(self):
        p, review, _ = family("approved-retirement")
        self.assertEqual(analyze(p, review), analyze(p, review))

    def test_accounting_partition(self):
        p, review, _ = family("approved-retirement")
        v = analyze(p, review)["views"]
        parts = [set(v[k]) for k in ("active_ids", "history_ids", "quarantine_ids")]
        self.assertEqual(set.union(*parts), {r["id"] for r in p["records"]})
        self.assertEqual(sum(map(len, parts)), len(set.union(*parts)))

    def test_projection_keeps_source_and_revocation_information(self):
        p, _, _ = family("revoked-permission")
        _, context, archive = make_projection(p)
        self.assertTrue(context["preview_only"])
        self.assertEqual(context["revocation_tombstones"][0]["id"], "grant")
        self.assertEqual(archive["quarantined_records"][0]["id"], "grant")


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.p = packet(pair(), ["old"])
        self.review = approved(self.p)

    def reject(self, code):
        with self.assertRaisesRegex(InputError, code):
            analyze(self.p, self.review)

    def test_pending_template(self):
        d = review_template(self.p)["decisions"][0]
        self.assertFalse(d["approved"])
        self.assertEqual(d["reviewer"], "")

    def test_explicit_review_retires(self):
        r = analyze(self.p, self.review)
        self.assertEqual(r["status"], "REVIEWED_PREVIEW")
        self.assertEqual(r["views"]["history_ids"], ["old"])

    def test_stale_review(self):
        self.p["records"][1]["text"] += " changed"
        self.reject("STALE_REVIEW")

    def test_approval_boolean_required(self):
        self.review["decisions"][0]["approved"] = "yes"
        self.reject("APPROVAL_NOT_BOOLEAN")

    def test_reviewer_required(self):
        self.review["decisions"][0]["reviewer"] = " "
        self.reject("INVALID_TEXT")

    def test_rationale_required(self):
        self.review["decisions"][0]["rationale"] = ""
        self.reject("INVALID_TEXT")

    def test_wrong_replacement(self):
        self.review["decisions"][0]["replacement_id"] = "old"
        self.reject("REVIEW_REPLACEMENT_MISMATCH")

    def test_duplicate_decision(self):
        self.review["decisions"] *= 2
        self.reject("DUPLICATE_DECISION")

    def test_unknown_review_field(self):
        self.review["approval"] = True
        self.reject("REVIEW_FIELDS")

    def test_live_dependency_cannot_be_reviewed_away(self):
        self.p["records"].append(record("child", depends=["old"]))
        self.review["packet_sha256"] = fingerprint(self.p)
        self.reject("APPROVAL_HAS_UNRESOLVED")

    def test_coupling_ack_required(self):
        self.p, self.review, _ = family("missing-coupling-ack")
        self.reject("COUPLING_NOT_ACKNOWLEDGED")

    def test_coupling_ack_preserves_fence(self):
        self.p, self.review, _ = family("missing-coupling-ack")
        self.review["decisions"][0]["acknowledged_couplings"] = ["bundle"]
        r = analyze(self.p, self.review)
        self.assertEqual(r["views"]["guard_ids"], ["fence"])
        self.assertEqual(r["views"]["history_ids"], ["old"])

    def test_false_semantic_review_is_not_detected(self):
        p, review, _ = family("false-but-consistent-review")
        self.assertEqual(analyze(p, review)["status"], "REVIEWED_PREVIEW")

    def test_review_does_not_allow_current_retirement(self):
        self.p["requested_retirements"] = ["new"]
        self.review = approved(self.p)
        self.reject("APPROVAL_HAS_UNRESOLVED")

    def test_fingerprint_key_order_normalized(self):
        reordered = dict(reversed(list(self.p.items())))
        self.assertEqual(fingerprint(self.p), fingerprint(reordered))

    def test_fingerprint_binds_text(self):
        changed = copy.deepcopy(self.p)
        changed["records"][0]["text"] += "."
        self.assertNotEqual(fingerprint(self.p), fingerprint(changed))

    def test_every_ablation_explicitly_labeled(self):
        for module in MODULES:
            r = analyze(self.p, disabled_modules=[module])
            self.assertEqual(r["status"], "EXPERIMENT_ONLY")
            self.assertFalse(r["modules"][module])
            self.assertTrue(r["does_not_authorize_actions"])

    def test_unknown_ablation_rejected(self):
        with self.assertRaisesRegex(InputError, "UNKNOWN_MODULE"):
            analyze(self.p, disabled_modules=["hidden"])


if __name__ == "__main__":
    unittest.main()