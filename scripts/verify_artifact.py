#!/usr/bin/env python3
"""Re-execute the evidence-debt study and verify deterministic outputs."""

from __future__ import annotations

import csv
import runpy
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
    experiment = runpy.run_path(str(ROOT / "code" / "experiment.py"))
    classify = experiment["classify_outcome"]
    if classify(False, "truth", "truth") != "N":
        raise SystemExit("an unaccepted lucky guess must remain N")
    if classify(False, "wrong", "truth") != "N":
        raise SystemExit("an unaccepted wrong guess must remain N")
    if classify(True, "truth", "truth") != "S":
        raise SystemExit("an accepted correct answer must be S")
    if classify(True, "wrong", "truth") != "W":
        raise SystemExit("an accepted wrong answer must be W")

    tracked = ["results_raw.csv", "results.csv"]
    before_csv = {name: csv_without_timing(DATA / name) for name in tracked}
    before_table = (DATA / "table_full.tex").read_bytes()
    before_rows = (DATA / "table_rows.tex").read_bytes()
    before_interest = (DATA / "interest.csv").read_bytes()
    before_pi = (DATA / "pi_sensitivity.csv").read_bytes()
    before_pi_table = (DATA / "table_pi_sensitivity.tex").read_bytes()
    before_pi_compact = (DATA / "table_pi_sensitivity_compact.tex").read_bytes()
    before_weights = (DATA / "weight_sensitivity.csv").read_bytes()
    before_weight_table = (DATA / "table_weight_sensitivity.tex").read_bytes()
    before_paths = (DATA / "pairwise_path_diagnostic.csv").read_bytes()
    before_path_summary = (DATA / "pairwise_path_summary.csv").read_bytes()

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
    if (DATA / "pi_sensitivity.csv").read_bytes() != before_pi:
        raise SystemExit("penalty sensitivity changed: data/pi_sensitivity.csv")
    if (DATA / "table_pi_sensitivity.tex").read_bytes() != before_pi_table:
        raise SystemExit(
            "generated penalty table changed: data/table_pi_sensitivity.tex"
        )
    if (DATA / "table_pi_sensitivity_compact.tex").read_bytes() != before_pi_compact:
        raise SystemExit("generated compact consequence-weight table changed")
    if (DATA / "weight_sensitivity.csv").read_bytes() != before_weights:
        raise SystemExit("joint consequence-weight sensitivity changed")
    if (DATA / "table_weight_sensitivity.tex").read_bytes() != before_weight_table:
        raise SystemExit("generated joint consequence-weight table changed")
    if (DATA / "pairwise_path_diagnostic.csv").read_bytes() != before_paths:
        raise SystemExit("paired path diagnostic changed")
    if (DATA / "pairwise_path_summary.csv").read_bytes() != before_path_summary:
        raise SystemExit("paired path summary changed")

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

    for row in rows:
        err = float(row["error_links"])
        no_cert = float(row["no_cert_links"])
        supported = float(row["coverage"])
        if abs(supported + err + no_cert - 1.0) > 1e-12:
            raise SystemExit("S/W/N outcomes do not form an exact partition")
        components = (
            float(row["ed_effort"])
            + float(row["ed_error"])
            + float(row["ed_abstention"])
        )
        if abs(components - float(row["ed"])) > 1e-9:
            raise SystemExit("evidence-debt components do not sum to total")

    with (DATA / "pi_sensitivity.csv").open(newline="", encoding="utf-8") as stream:
        pi_rows = list(csv.DictReader(stream))
    if len(pi_rows) != 42:
        raise SystemExit("penalty sensitivity must contain 6 penalties x 7 arms")
    penalties = {float(r["pi"]) for r in pi_rows}
    if penalties != {0.0, 1.0, 10.0, 25.0, 50.0, 100.0}:
        raise SystemExit("penalty sensitivity grid is incomplete")

    with (DATA / "weight_sensitivity.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        weight_rows = list(csv.DictReader(stream))
    if len(weight_rows) != 175:
        raise SystemExit("weight sensitivity must contain 5 x 5 x 7 rows")
    grid = {(float(r["lambda"]), float(r["pi"])) for r in weight_rows}
    expected_grid = {(x, y) for x in {0.0, 10.0, 25.0, 50.0, 100.0}
                     for y in {0.0, 10.0, 25.0, 50.0, 100.0}}
    if grid != expected_grid:
        raise SystemExit("joint lambda/pi sensitivity grid is incomplete")

    with (DATA / "pairwise_path_summary.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        path_rows = list(csv.DictReader(stream))
    endpoints = {
        row["profile"]: float(row["only_union_loss_rate"])
        for row in path_rows
        if float(row["p"]) == 0.4
    }
    if set(endpoints) != {"sparse", "dense"} or not all(
        value > 0 for value in endpoints.values()
    ):
        raise SystemExit("Proposition-2 path-loss endpoint is missing")

    subprocess.run(
        [sys.executable, "scripts/verify_empirical_snapshot.py"], cwd=ROOT, check=True
    )
    print(
        "PASS: outputs reproduced exactly; S/W/N partition, physical-IRR "
        "separation, and ED-component invariants hold"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
