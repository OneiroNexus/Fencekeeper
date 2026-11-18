"""Build a deterministic standard-library zipapp into a new file."""
from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_bytes():
    files = {"__main__.py": b"from fencekeeper.cli import main\nraise SystemExit(main())\n"}
    files.update({p.relative_to(ROOT).as_posix(): p.read_bytes()
                  for p in sorted((ROOT / "fencekeeper").glob("*.py"))})
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.output.open("xb") as stream:
        stream.write(build_bytes())
    print("Created new zipapp; no source files changed.")


if __name__ == "__main__":
    main()