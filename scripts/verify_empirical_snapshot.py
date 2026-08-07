#!/usr/bin/env python3
"""Verify internal consistency of the frozen Argo CD repository snapshot."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EMPIRICAL = ROOT / "empirical"


def pct(count: int, total: int) -> str:
    return f"{100 * count / total:.1f}"


def main() -> int:
    payload = json.loads((EMPIRICAL / "data/argocd_sample.json").read_text())
    summary = payload["summary"]
    prs = payload["pull_requests"]
    releases = payload["releases"]

    no_issue = sum(row["closing_issue_links"] == 0 for row in prs)
    no_issue_reference = sum(
        row["closing_issue_links"] == 0 and not row["has_explicit_issue_reference"]
        for row in prs
    )
    no_approval = sum(row["approval_reviews"] == 0 for row in prs)
    neither = sum(
        row["closing_issue_links"] == 0 and row["approval_reviews"] == 0
        for row in prs
    )
    no_release_lineage = sum(
        not row["has_explicit_change_reference"] for row in releases
    )
    symbolic = sum(not row["target_is_full_sha"] for row in releases)
    expected = {
        "merged_pull_requests": len(prs),
        "without_machine_resolvable_closing_issue_link": no_issue,
        "without_machine_resolvable_closing_issue_link_pct": pct(no_issue, len(prs)),
        "without_closing_link_or_explicit_issue_reference": no_issue_reference,
        "without_closing_link_or_explicit_issue_reference_pct": pct(no_issue_reference, len(prs)),
        "without_explicit_approved_review": no_approval,
        "without_explicit_approved_review_pct": pct(no_approval, len(prs)),
        "without_either_link_or_approval": neither,
        "without_either_link_or_approval_pct": pct(neither, len(prs)),
        "releases": len(releases),
        "releases_without_explicit_change_reference": no_release_lineage,
        "releases_without_explicit_change_reference_pct": pct(no_release_lineage, len(releases)),
        "releases_with_symbolic_target_commitish": symbolic,
        "releases_with_symbolic_target_commitish_pct": pct(symbolic, len(releases)),
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise SystemExit(f"snapshot summary mismatch for {key}")

    with (EMPIRICAL / "data/argocd_summary.csv").open(newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    csv_expected = [
        ("Merged PRs without closing-issue link", no_issue, len(prs)),
        ("Merged PRs without closing link or explicit issue reference", no_issue_reference, len(prs)),
        ("Merged PRs without approved review object", no_approval, len(prs)),
        ("Merged PRs without either artifact", neither, len(prs)),
        ("Releases without explicit PR/compare reference", no_release_lineage, len(releases)),
        ("Releases whose target_commitish is symbolic", symbolic, len(releases)),
    ]
    observed = [
        (row["measure"], int(row["count"]), int(row["denominator"]))
        for row in csv_rows
    ]
    if observed != csv_expected:
        raise SystemExit("CSV summary does not match frozen snapshot")

    macros = (EMPIRICAL / "argocd_macros.tex").read_text(encoding="ascii")
    required = {
        "ArgoPRTotal": len(prs),
        "ArgoNoIssue": no_issue,
        "ArgoNoIssueReference": no_issue_reference,
        "ArgoNoApproval": no_approval,
        "ArgoNeither": neither,
        "ArgoReleaseTotal": len(releases),
        "ArgoNoReleaseLineage": no_release_lineage,
        "ArgoSymbolicTarget": symbolic,
    }
    for name, value in required.items():
        match = re.search(rf"\\newcommand\{{\\{name}\}}\{{(\d+)\}}", macros)
        if not match or int(match.group(1)) != value:
            raise SystemExit(f"LaTeX macro mismatch for {name}")

    print("PASS: frozen Argo CD snapshot, CSV summary, and LaTeX macros agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
