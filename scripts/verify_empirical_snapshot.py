#!/usr/bin/env python3
"""Verify the frozen age-stratified Argo CD observation and its audit."""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EMPIRICAL = ROOT / "empirical"
DATA = EMPIRICAL / "data"
COHORTS = ("recent", "about_1y", "about_3y", "about_5y")


def pct(count: int, total: int) -> str:
    return f"{100 * count / total:.1f}"


def has_external_issue_reference(row: dict[str, object]) -> bool:
    return bool(row["closing_issue_links"] or row["has_explicit_issue_reference"])


def main() -> int:
    payload = json.loads((DATA / "argocd_sample.json").read_text())
    summary = payload["summary"]
    prs = payload["pull_requests"]
    releases = payload["releases"]

    if len(prs) != 200 or Counter(row["cohort"] for row in prs) != Counter({name: 50 for name in COHORTS}):
        raise SystemExit("frozen PR sample is not four 50-PR cohorts")
    if len({row["number"] for row in prs}) != len(prs):
        raise SystemExit("duplicate PR in frozen cohorts")

    closing_present = sum(row["closing_issue_links"] > 0 for row in prs)
    explicit_only = sum(row["closing_issue_links"] == 0 and row["has_explicit_issue_reference"] for row in prs)
    no_external = sum(not has_external_issue_reference(row) for row in prs)
    approved = sum(row["approval_reviews"] > 0 for row in prs)
    release_lineage = sum(row["has_explicit_change_reference"] for row in releases)
    symbolic = sum(not row["target_is_full_sha"] for row in releases)
    expected = {
        "cohort_size": 50,
        "merged_pull_requests": len(prs),
        "closing_issue_link_present": closing_present,
        "closing_issue_link_present_pct": pct(closing_present, len(prs)),
        "explicit_nonclosing_issue_reference_only": explicit_only,
        "explicit_nonclosing_issue_reference_only_pct": pct(explicit_only, len(prs)),
        "without_external_issue_reference": no_external,
        "without_external_issue_reference_pct": pct(no_external, len(prs)),
        "with_approved_review_record": approved,
        "with_approved_review_record_pct": pct(approved, len(prs)),
        "releases": len(releases),
        "releases_with_explicit_change_reference": release_lineage,
        "releases_with_explicit_change_reference_pct": pct(release_lineage, len(releases)),
        "releases_with_symbolic_target_commitish": symbolic,
        "releases_with_symbolic_target_commitish_pct": pct(symbolic, len(releases)),
        "manual_audit_seed": 20260807,
        "manual_audit_size": 50,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise SystemExit(f"snapshot summary mismatch for {key}")

    with (DATA / "argocd_summary.csv").open(newline="", encoding="utf-8") as handle:
        observed_summary = [
            (row["evidence_observed"], int(row["count"]), int(row["denominator"]), row["percent"])
            for row in csv.DictReader(handle)
        ]
    expected_summary = [
        ("Closing-issue link present", closing_present, len(prs), pct(closing_present, len(prs))),
        ("Explicit non-closing issue reference only", explicit_only, len(prs), pct(explicit_only, len(prs))),
        ("No external issue reference", no_external, len(prs), pct(no_external, len(prs))),
        ("At least one APPROVED review record", approved, len(prs), pct(approved, len(prs))),
        ("Release with PR/compare reference", release_lineage, len(releases), pct(release_lineage, len(releases))),
    ]
    if observed_summary != expected_summary:
        raise SystemExit("CSV headline summary does not match frozen snapshot")

    with (DATA / "argocd_strata.csv").open(newline="", encoding="utf-8") as handle:
        strata = list(csv.DictReader(handle))
    for row in strata:
        key = {"age cohort": "cohort", "authorship": "authorship", "change type": "change_type"}[row["dimension"]]
        group = [pr for pr in prs if pr[key] == row["stratum"]]
        missing = sum(not has_external_issue_reference(pr) for pr in group)
        if (int(row["total"]), int(row["without_external_issue_reference"]), row["share_without_external_issue_reference"]) != (
            len(group), missing, pct(missing, len(group))
        ):
            raise SystemExit(f"stratum mismatch for {row['dimension']}/{row['stratum']}")

    macros = (EMPIRICAL / "argocd_macros.tex").read_text(encoding="ascii")
    required = {
        "ArgoPRTotal": len(prs),
        "ArgoClosingPresent": closing_present,
        "ArgoExplicitOnly": explicit_only,
        "ArgoNoExternal": no_external,
        "ArgoApproved": approved,
        "ArgoReleaseTotal": len(releases),
        "ArgoReleaseLineage": release_lineage,
    }
    for name, value in required.items():
        match = re.search(rf"\\newcommand\{{\\{name}\}}\{{(\d+)\}}", macros)
        if not match or int(match.group(1)) != value:
            raise SystemExit(f"LaTeX macro mismatch for {name}")

    subprocess.run([sys.executable, "empirical/test_reference_grammar.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "empirical/validate_manual_audit.py"], cwd=ROOT, check=True)
    print("PASS: frozen Argo CD cohorts, strata, grammar, audit, CSVs, and macros agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
