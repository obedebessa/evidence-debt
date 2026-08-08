#!/usr/bin/env python3
"""Build MANIFEST.sha256 for release files."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_SUFFIXES = {".aux", ".bbl", ".blg", ".log", ".out", ".xdv"}
RELEASE_PDF = Path("output/pdf/evidence-debt-v1.7.2.pdf")


def included(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    return (
        path.is_file()
        and path.name != "MANIFEST.sha256"
        and path.suffix not in EXCLUDED_SUFFIXES
        and path.name != "main.pdf"
        and path.name != "evidence-debt-paper.pdf"
        and (rel.parts[:2] != ("output", "pdf") or rel == RELEASE_PDF)
        and (not rel.parts or rel.parts[0] not in {"build", "originais", "qa", "release", "tmp"})
    )


def main() -> None:
    lines = []
    proc = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    candidates = (ROOT / line for line in proc.stdout.splitlines())
    for path in sorted(path for path in candidates if included(path)):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")
    (ROOT / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
