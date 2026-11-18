import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from fencekeeper.cli import read_json
from tools.corpus import approved, family, packet, pair, record

ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.input = self.base / "packet.json"
        self.p = packet([record("a")])
        self.input.write_text(json.dumps(self.p))

    def command(self, *args):
        return subprocess.run([sys.executable, "-m", "fencekeeper", *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True, timeout=10)

    def test_audit(self):
        p = self.command("audit", self.input, "--output", self.base / "report.json")
        self.assertEqual(p.returncode, 0)

    def test_new_plan_has_no_approval(self):
        self.input.write_text(json.dumps(packet(pair(), ["old"])))
        out = self.base / "plan.json"
        p = self.command("plan", self.input, "--output", out)
        self.assertEqual(p.returncode, 0)
        self.assertFalse(json.loads(out.read_text())["decisions"][0]["approved"])

    def test_refuses_existing_output(self):
        out = self.base / "existing.json"
        out.write_text("retain")
        p = self.command("audit", self.input, "--output", out)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(out.read_text(), "retain")

    def test_refuses_input_collision(self):
        before = self.input.read_bytes()
        p = self.command("audit", self.input, "--output", self.input)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(before, self.input.read_bytes())

    def test_preserves_exact_source_bytes_in_projection(self):
        raw = ('\n' + json.dumps(self.p, indent=4) + '\n\n').encode()
        self.input.write_bytes(raw)
        out = self.base / "bundle"
        p = self.command("project", self.input, "--output", out)
        self.assertEqual(p.returncode, 0)
        self.assertEqual((out / "source-packet.json").read_bytes(), raw)
        self.assertTrue(json.loads((out / "manifest.json").read_text())["complete"])

    def test_projection_existing_directory_refused(self):
        p = self.command("project", self.input, "--output", self.base)
        self.assertEqual(p.returncode, 2)

    def test_review_required_exit(self):
        self.input.write_text(json.dumps(packet(pair(), ["old"])))
        p = self.command("audit", self.input, "--output", self.base / "r.json")
        self.assertEqual(p.returncode, 1)

    def test_experiment_exit_and_label(self):
        out = self.base / "experiment.json"
        p = self.command("ablate", self.input, "--disable", "dependency_check",
                         "--output", out)
        self.assertEqual(p.returncode, 3)
        self.assertTrue(json.loads(out.read_text())["experimental"])

    def test_no_ablation_switch_on_project(self):
        p = self.command("project", self.input, "--disable", "dependency_check",
                         "--output", self.base / "bundle")
        self.assertEqual(p.returncode, 2)
        self.assertFalse((self.base / "bundle").exists())

    def test_duplicate_json_keys(self):
        self.input.write_text('{"schema":1,"schema":2}')
        p = self.command("audit", self.input, "--output", self.base / "r.json")
        self.assertEqual(p.returncode, 2)
        self.assertIn("DUPLICATE_JSON_KEY", p.stderr)

    def test_input_bound(self):
        self.input.write_bytes(b"x" * 100)
        with self.assertRaisesRegex(ValueError, "INPUT_LIMIT"):
            read_json(self.input, 99)

    def test_nonfinite_json(self):
        self.input.write_text('{"x":NaN}')
        p = self.command("audit", self.input, "--output", self.base / "r.json")
        self.assertEqual(p.returncode, 2)

    def test_untrusted_text_is_not_executed(self):
        marker = self.base / "should-not-exist"
        self.p["records"][0]["text"] = f"$(touch {marker}) https://example.invalid/"
        self.input.write_text(json.dumps(self.p))
        p = self.command("audit", self.input, "--output", self.base / "r.json")
        self.assertEqual(p.returncode, 0)
        self.assertFalse(marker.exists())

    def test_symlink_output_not_followed(self):
        target = self.base / "target"
        target.write_text("keep")
        link = self.base / "link"
        try:
            link.symlink_to(target)
        except OSError as error:
            if os.name == "nt" and getattr(error, "winerror", None) == 1314:
                self.skipTest("Windows account cannot create symlinks (WinError 1314)")
            raise
        p = self.command("audit", self.input, "--output", link)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(target.read_text(), "keep")

    def test_reviewed_projection(self):
        p = packet(pair(), ["old"])
        self.input.write_text(json.dumps(p))
        review = self.base / "review.json"
        review.write_text(json.dumps(approved(p)))
        out = self.base / "reviewed"
        result = self.command("project", self.input, "--review", review, "--output", out)
        self.assertEqual(result.returncode, 0)
        archive = json.loads((out / "history.json").read_text())
        self.assertEqual(archive["approved_retired_records"][0]["id"], "old")


if __name__ == "__main__":
    unittest.main()
