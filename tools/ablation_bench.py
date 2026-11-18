"""Visible one-module-at-a-time experiments on the packaged synthetic corpus."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fencekeeper.core import MODULES, InputError, analyze, canonical


def measure(corpus):
    results = []
    for case in corpus:
        for disabled in (None, *MODULES):
            error = None
            report = None
            try:
                report = analyze(case["packet"], case["review"],
                                 disabled_modules=() if disabled is None else (disabled,))
            except InputError as exc:
                error = str(exc)
            expected = case["expected"]
            counters = {"false_active": 0, "missing_active": 0,
                        "missing_guards": 0, "unexpected_guards": 0,
                        "retirement_mismatch": 0, "missed_rejection": 0,
                        "unexpected_rejection": 0}
            if "error" in expected:
                matched = error == expected["error"]
                counters["missed_rejection"] = int(error is None)
                counters["unexpected_rejection"] = int(error is not None and not matched)
            elif error is not None:
                matched = False
                counters["unexpected_rejection"] = 1
            else:
                actual = report["views"]
                counters["false_active"] = len(set(actual["active_ids"]) - set(expected["active_ids"]))
                counters["missing_active"] = len(set(expected["active_ids"]) - set(actual["active_ids"]))
                counters["missing_guards"] = len(set(expected["guard_ids"]) - set(actual["guard_ids"]))
                counters["unexpected_guards"] = len(set(actual["guard_ids"]) - set(expected["guard_ids"]))
                counters["retirement_mismatch"] = len(set(actual["history_ids"]) ^ set(expected["history_ids"]))
                matched = not any(counters.values())
            results.append({
                "case_id": case["id"], "family": case["family"],
                "configuration": disabled or "baseline",
                "disabled_modules": [] if disabled is None else [disabled],
                "experimental": disabled is not None,
                "expected_contract_matched": matched, "error": error,
                "report_status": report["status"] if report else None,
                "counts": report["counts"] if report else None,
                "active_ids": report["views"]["active_ids"] if report else None,
                "guard_ids": report["views"]["guard_ids"] if report else None,
                "history_ids": report["views"]["history_ids"] if report else None,
                "metrics": counters,
                "negative_semantic_example": case["negative_semantic_example"],
            })
    summary = []
    for label in ("baseline", *MODULES):
        rows = [r for r in results if r["configuration"] == label]
        summary.append({
            "configuration": label, "cases": len(rows),
            "matched": sum(r["expected_contract_matched"] for r in rows),
            "changed_from_full_contract": sum(not r["expected_contract_matched"] for r in rows),
            "metrics": {name: sum(r["metrics"][name] for r in rows)
                        for name in rows[0]["metrics"]},
        })
    return {
        "schema": "fencekeeper.ablation.v1", "experiment_only": True,
        "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "environment": {"python": platform.python_version(),
                        "system": platform.system(), "machine": platform.machine()},
        "corpus_sha256": hashlib.sha256(canonical(corpus)).hexdigest(),
        "cases": len(corpus), "rows": len(results), "summary": summary,
        "results": results,
        "interpretation": (
            "Synthetic contract-sensitivity checks, not LLM performance. "
            "Expected labels were authored for the full configuration. "
            "Disabling a rule intentionally changes that contract."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    corpus = json.loads((ROOT / "fixtures/cases.json").read_text(encoding="utf-8"))
    result = measure(corpus)
    with args.output.open("xb") as stream:
        stream.write(canonical(result))
    print(json.dumps({"cases": result["cases"], "rows": result["rows"],
                      "baseline_matched": result["summary"][0]["matched"]}))
    return 0 if result["summary"][0]["matched"] == len(corpus) else 1


if __name__ == "__main__":
    raise SystemExit(main())