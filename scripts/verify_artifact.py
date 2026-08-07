#!/usr/bin/env python3
"""Re-execute the evidence-debt study and verify deterministic outputs."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def csv_without_timing(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    return [
        {key: value for key, value in row.items() if key not in {"secs", "secs_sd"}}
        for row in rows
    ]


def main() -> int:
    tracked = ["results_raw.csv", "results.csv"]
    before_csv = {name: csv_without_timing(DATA / name) for name in tracked}
    before_table = (DATA / "table_full.tex").read_bytes()
    before_rows = (DATA / "table_rows.tex").read_bytes()
    before_interest = (DATA / "interest.csv").read_bytes()

    subprocess.run([sys.executable, "code/experiment.py"], cwd=ROOT, check=True)

    for name in tracked:
        after = csv_without_timing(DATA / name)
        if after != before_csv[name]:
            raise SystemExit(f"non-timing scientific output changed: data/{name}")
    if (DATA / "table_full.tex").read_bytes() != before_table:
        raise SystemExit("generated table changed: data/table_full.tex")
    if (DATA / "table_rows.tex").read_bytes() != before_rows:
        raise SystemExit("generated rows changed: data/table_rows.tex")
    if (DATA / "interest.csv").read_bytes() != before_interest:
        raise SystemExit("interest curve changed: data/interest.csv")

    with (DATA / "results.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    keys = {(r["tag"], r["profile"], r["cls"], r["p"]) for r in rows}
    required = {
        ("main", "dense", "correlation_ids", "0.4"),
        ("main", "dense", "timestamps", "0.4"),
        ("main", "dense", "ids_plus_timestamps", "0.4"),
        ("main", "dense", "combined", "0.4"),
    }
    if not required.issubset(keys):
        raise SystemExit("required headline-result cells are missing")

    subprocess.run(
        [sys.executable, "scripts/verify_empirical_snapshot.py"], cwd=ROOT, check=True
    )
    print("PASS: all non-timing outputs and generated tables reproduced exactly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
