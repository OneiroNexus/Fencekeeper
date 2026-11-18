import json
import unittest
from pathlib import Path

from fencekeeper.core import MODULES, analyze
from tools.ablation_bench import measure
from tools.corpus import cases, family

ROOT = Path(__file__).resolve().parents[1]


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = measure(cases())

    def test_every_case_has_every_configuration(self):
        rows = self.results["results"]
        self.assertEqual(len(rows), 350)
        for case in cases():
            self.assertEqual({r["configuration"] for r in rows if r["case_id"] == case["id"]},
                             {"baseline", *MODULES})

    def test_full_contract_has_declared_results(self):
        baseline = self.results["summary"][0]
        self.assertEqual(baseline["matched"], 50)
        self.assertFalse(any(baseline["metrics"].values()))

    def test_every_disabled_module_is_labelled(self):
        for row in self.results["results"]:
            if row["configuration"] != "baseline":
                self.assertTrue(row["experimental"])
                self.assertEqual(row["disabled_modules"], [row["configuration"]])
                if row["error"] is None:
                    self.assertEqual(row["report_status"], "EXPERIMENT_ONLY")

    def test_every_ablation_exposes_at_least_one_difference(self):
        for row in self.results["summary"][1:]:
            self.assertGreater(row["changed_from_full_contract"], 0)

    def test_semantic_negative_stays_visible(self):
        rows = [r for r in self.results["results"]
                if r["negative_semantic_example"] and r["configuration"] == "baseline"]
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(r["expected_contract_matched"] for r in rows))

    def test_wolfram_fixture_expected_values_match_python_only(self):
        fixture = json.loads((ROOT / "wolfram/closure-fixture.json").read_text())
        p, _, _ = family("coupled-restriction-chain")
        rows = analyze(p)["records"]
        old = next(r for r in rows if r["id"] == "old")
        self.assertEqual(old["current_dependents"], fixture["expected_current_dependents"])
        # This test checks fixture agreement, not execution of Wolfram code.

    def test_packaged_fixture_is_regenerable(self):
        stored = json.loads((ROOT / "fixtures/cases.json").read_text())
        self.assertEqual(stored, cases())