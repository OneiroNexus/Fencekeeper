"""Run local checks into a new receipt directory. Never choose evidence by recency."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import platform
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fencekeeper.core import canonical
from tools.ablation_bench import measure


def snapshots():
    paths = []
    for folder in ("fencekeeper", "tools", "tests", "fixtures", "examples",
                   "godot", "wolfram"):
        paths.extend(p for p in (ROOT / folder).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts
                     and not (folder == "godot" and "data" in p.relative_to(ROOT).parts))
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes.append({"id": test.id(), "outcome": "pass"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcomes.append({"id": test.id(), "outcome": "fail"})

    def addError(self, test, err):
        super().addError(test, err)
        self.outcomes.append({"id": test.id(), "outcome": "error"})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcomes.append({"id": test.id(), "outcome": "skip", "reason": reason})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-windows-symlink-skip", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    before = snapshots()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    with (args.output / "unittest.log").open("x", encoding="utf-8") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2,
                                        resultclass=RecordedResult).run(suite)
    corpus = json.loads((ROOT / "fixtures/cases.json").read_text(encoding="utf-8"))
    experiment = measure(corpus)
    (args.output / "ablation.json").write_bytes(canonical(experiment))
    after = snapshots()
    receipt = {
        "schema": "fencekeeper.validation.v1",
        "started_at": started,
        "ended_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "environment": {"implementation": platform.python_implementation(),
                        "python": platform.python_version(),
                        "system": platform.system(), "machine": platform.machine()},
        "unit": {"run": result.testsRun, "failures": len(result.failures),
                 "errors": len(result.errors), "skips": len(result.skipped),
                 "outcomes": result.outcomes},
        "experiment": {"cases": experiment["cases"], "rows": experiment["rows"],
                       "summary": experiment["summary"]},
        "tracked_sources_unchanged": before == after,
        "source_sha256": before,
        "record_sha256": {
            name: hashlib.sha256((args.output / name).read_bytes()).hexdigest()
            for name in ("unittest.log", "ablation.json")
        },
        "limitations": ["Local self-recorded checks, not independent validation.",
                        "Synthetic record processing, not measured model behavior.",
                        "Godot and Wolfram are not exercised by this runner."],
    }
    skips = [(test.id().rsplit(".", 1)[-1], reason) for test, reason in result.skipped]
    skips_ok = not skips or (
        args.allow_windows_symlink_skip and sys.platform == "win32"
        and skips == [("test_symlink_output_not_followed", "Windows account cannot create symlinks (WinError 1314)")]
    )
    okay = (result.wasSuccessful() and skips_ok and before == after
            and experiment["summary"][0]["matched"] == len(corpus))
    receipt["all_required_checks_passed"] = okay
    (args.output / "validation.json").write_bytes(canonical(receipt))
    print(json.dumps({"unit_run": result.testsRun, "passed": okay,
                      "baseline_cases_matched": experiment["summary"][0]["matched"],
                      "comparison_rows": experiment["rows"]}))
    return 0 if okay else 1


if __name__ == "__main__":
    raise SystemExit(main())