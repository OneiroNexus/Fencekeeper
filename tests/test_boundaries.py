import copy
import unittest

from fencekeeper.core import InputError, analyze, make_projection
from tools.corpus import approved, packet, pair, record


class BoundaryTests(unittest.TestCase):
    def test_unhashable_kind_rejected_by_core(self):
        p = packet([record("a")])
        p["records"][0]["kind"] = []
        with self.assertRaises(InputError):
            analyze(p)

    def test_unhashable_status_rejected_by_core(self):
        p = packet([record("a")])
        p["records"][0]["status"] = {}
        with self.assertRaises(InputError):
            analyze(p)

    def test_disabled_string_not_silently_split(self):
        with self.assertRaises(InputError):
            analyze(packet([record("a")]), disabled_modules="dependency_check")

    def test_nested_disabled_module_rejected(self):
        with self.assertRaises(InputError):
            analyze(packet([record("a")]), disabled_modules=[[]])

    def test_uncertain_state_is_visible_review_work(self):
        r = analyze(packet([record("a", status="uncertain")]))
        self.assertEqual(r["status"], "REVIEW_REQUIRED")
        self.assertEqual(r["views"]["unresolved_state_ids"], ["a"])

    def test_unresolved_supersession_without_request_is_review_work(self):
        r = analyze(packet([record("a", status="superseded")]))
        self.assertEqual(r["status"], "REVIEW_REQUIRED")
        self.assertEqual(r["views"]["unresolved_state_ids"], ["a"])

    def test_held_successor_cannot_finalize_retirement(self):
        rows = pair() + [record("premise", status="uncertain")]
        rows[1]["depends_on"] = ["premise"]
        p = packet(rows, ["old"])
        r = analyze(p)
        old = next(x for x in r["records"] if x["id"] == "old")
        self.assertIn("REPLACEMENT_NOT_ELIGIBLE", old["blockers"])
        with self.assertRaises(InputError):
            analyze(p, approved(p))

    def test_revoked_successor_does_not_restore_permission(self):
        rows = [
            record("old", kind="permission", key="publish", status="superseded",
                   successor="new"),
            record("new", kind="permission", key="publish", revision=2, status="revoked"),
        ]
        p = packet(rows, ["old"])
        r, context, history = make_projection(p, approved(p))
        self.assertEqual(r["views"]["record_eligible_permission_ids"], [])
        self.assertEqual(r["views"]["history_ids"], ["old"])
        self.assertEqual(context["revocation_tombstones"][0]["id"], "new")

    def test_two_independent_revocations_require_both_reinstatements(self):
        p = packet([
            record("rev-a", kind="permission", key="publish", status="revoked"),
            record("rev-b", kind="permission", key="publish", revision=2, status="revoked"),
            record("grant", kind="permission", key="publish", revision=3,
                   reinstates=["rev-a"]),
        ])
        self.assertEqual(analyze(p)["views"]["record_eligible_permission_ids"], [])
        p["records"][2]["reinstates"].append("rev-b")
        self.assertEqual(analyze(p)["views"]["record_eligible_permission_ids"], ["grant"])

    def test_couplings_are_not_hard_dependency_edges(self):
        p = packet([record("a"), record("b"), record("c")], couplings=[
            {"id": "ab", "members": ["a", "b"], "reason": "Related records."},
            {"id": "bc", "members": ["b", "c"], "reason": "Related records."},
            {"id": "ca", "members": ["c", "a"], "reason": "Related records."},
        ])
        self.assertEqual(analyze(p)["views"]["active_ids"], ["a", "b", "c"])

    def test_projection_never_mutates_source_or_supplied_review(self):
        p = packet(pair(), ["old"])
        review = approved(p)
        before = copy.deepcopy((p, review))
        make_projection(p, review)
        self.assertEqual((p, review), before)

    def test_constraints_overlay_is_not_double_counted_partition(self):
        p = packet([record("a", status="uncertain"),
                    record("fence", kind="constraint", depends=["a"])])
        r = analyze(p)
        self.assertEqual(r["views"]["guard_ids"], ["fence"])
        self.assertEqual(r["views"]["quarantine_ids"], ["a", "fence"])
        self.assertEqual(r["counts"]["active"] + r["counts"]["retired"]
                         + r["counts"]["quarantined"], r["counts"]["records"])