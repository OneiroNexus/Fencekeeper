"""Check one named zipapp in an isolated temporary directory; write a new receipt."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fencekeeper.core import canonical
from tools.build_zipapp import build_bytes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zipapp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    app = args.zipapp.resolve()
    app_bytes = app.read_bytes()
    checks = []

    def record(name, condition):
        checks.append({"name": name, "passed": bool(condition)})

    record("deterministic_zipapp_rebuild", app_bytes == build_bytes())
    with tempfile.TemporaryDirectory(prefix="fencekeeper-package-") as temp:
        cwd = Path(temp)
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        environment["PYTHONNOUSERSITE"] = "1"

        def run(*argv):
            return subprocess.run([sys.executable, "-I", str(app), *map(str, argv)],
                                  cwd=cwd, env=environment, capture_output=True,
                                  text=True, timeout=15)

        record("standalone_help_outside_source", run("--help").returncode == 0)
        source = ROOT / "examples/coupled-restriction-chain.packet.json"
        original = source.read_bytes()
        pending = run("audit", source, "--output", cwd / "pending.json")
        record("review_required_exit_one", pending.returncode == 1
               and json.loads((cwd / "pending.json").read_text())["status"] == "REVIEW_REQUIRED")
        duplicate = run("audit", source, "--output", cwd / "pending.json")
        record("existing_output_refused", duplicate.returncode == 2
               and json.loads((cwd / "pending.json").read_text())["status"] == "REVIEW_REQUIRED")
        p = ROOT / "examples/revoked-permission.packet.json"
        experiment = run("ablate", p, "--disable", "revocation_filter",
                         "--output", cwd / "experiment.json")
        er = json.loads((cwd / "experiment.json").read_text())
        record("experimental_exit_three_and_visible_rule",
               experiment.returncode == 3 and er["experimental"]
               and er["disabled_modules"] == ["revocation_filter"]
               and "grant" in er["views"]["active_ids"])
        preview = cwd / "preview"
        projected = run("project", source, "--output", preview)
        record("projection_keeps_exact_input_bytes",
               projected.returncode == 1 and (preview / "source-packet.json").read_bytes() == original)
        context = json.loads((preview / "current-context.json").read_text())
        record("projection_carries_held_constraint",
               [r["id"] for r in context["conservative_guards"]] == ["fence"]
               and context["does_not_authorize_actions"] and context["preview_only"])
        manifest = json.loads((preview / "manifest.json").read_text())
        record("projection_manifest_matches",
               manifest["complete"] and all(hashlib.sha256((preview / name).read_bytes()).hexdigest() == digest
                                           for name, digest in manifest["files_sha256"].items()))
        p = ROOT / "examples/approved-retirement.packet.json"
        review = ROOT / "examples/approved-retirement.review.json"
        final = run("audit", p, "--review", review, "--output", cwd / "reviewed.json")
        record("reviewed_example_runs_standalone",
               final.returncode == 0 and json.loads((cwd / "reviewed.json").read_text())["views"]["history_ids"] == ["old"])
        record("selected_source_unchanged", source.read_bytes() == original)
    receipt = {
        "schema": "fencekeeper.packaging.v1",
        "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "environment": {"python": platform.python_version(), "system": platform.system(),
                        "machine": platform.machine()},
        "zipapp_sha256": hashlib.sha256(app_bytes).hexdigest(),
        "checks": checks, "all_passed": all(c["passed"] for c in checks),
        "not_exercised": ["Godot runtime", "Wolfram runtime", "owner's Windows project",
                          "external model", "network deployment"],
    }
    with args.output.open("xb") as stream:
        stream.write(canonical(receipt))
    print(json.dumps({"checks": len(checks), "passed": sum(c["passed"] for c in checks)}))
    return 0 if receipt["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())