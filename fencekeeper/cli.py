"""Bounded local I/O around the pure Fencekeeper core."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

from .core import (MODULES, InputError, analyze, canonical,
                   make_projection, review_template)


def read_json(path, limit):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise InputError("NOT_REGULAR_FILE")
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise InputError("INPUT_LIMIT")

    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise InputError("DUPLICATE_JSON_KEY")
            obj[key] = value
        return obj

    def no_constant(_):
        raise InputError("NONFINITE_JSON")

    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                      parse_constant=no_constant), raw


def write_new(path, raw):
    with Path(path).open("xb") as stream:
        stream.write(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for command in ("audit", "plan", "project", "ablate"):
        sub = subs.add_parser(command)
        sub.add_argument("packet")
        sub.add_argument("--output", required=True)
        if command != "plan":
            sub.add_argument("--review")
        if command == "ablate":
            sub.add_argument("--disable", required=True, choices=MODULES)
    args = parser.parse_args(argv)
    try:
        packet, raw_packet = read_json(args.packet, 4 * 1024 * 1024)
        review = None
        raw_review = None
        if getattr(args, "review", None):
            review, raw_review = read_json(args.review, 1024 * 1024)
        if args.command == "plan":
            result = review_template(packet)
            write_new(args.output, canonical(result))
            print(json.dumps({"created": "pending-review", "approved": False}))
            return 0
        if args.command == "project":
            report, context, archive = make_projection(packet, review)
            output = Path(args.output)
            output.mkdir(parents=True, exist_ok=False)
            files = {
                "source-packet.json": raw_packet,
                "report.json": canonical(report),
                "current-context.json": canonical(context),
                "history.json": canonical(archive),
                "pending-review.json": canonical(review_template(packet)),
            }
            if raw_review is not None:
                files["supplied-review.json"] = raw_review
            for name, raw in files.items():
                write_new(output / name, raw)
            manifest = {
                "schema": "fencekeeper.bundle.v1", "complete": True,
                "preview_only": True,
                "files_sha256": {name: hashlib.sha256(raw).hexdigest()
                                 for name, raw in sorted(files.items())},
            }
            write_new(output / "manifest.json", canonical(manifest))
            print(json.dumps({"created": "preview-bundle", "status": report["status"]}))
        else:
            disabled = (args.disable,) if args.command == "ablate" else ()
            report = analyze(packet, review, disabled_modules=disabled)
            report["input_file_sha256"] = hashlib.sha256(raw_packet).hexdigest()
            write_new(args.output, canonical(report))
            print(json.dumps({"created": "report", "status": report["status"]}))
        if report["experimental"]:
            return 3
        return 1 if report["status"] == "REVIEW_REQUIRED" else 0
    except (InputError, OSError, UnicodeError, ValueError, TypeError, KeyError,
            RecursionError, OverflowError) as error:
        code = str(error) if isinstance(error, InputError) else "INPUT_OR_OUTPUT_ERROR"
        sys.stderr.write(json.dumps({"status": "INPUT_ERROR", "code": code}) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())