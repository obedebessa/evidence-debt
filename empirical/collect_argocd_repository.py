#!/usr/bin/env python3
"""Collect a frozen, minimal public-evidence census from argoproj/argo-cd.

The script requires an authenticated GitHub CLI (`gh auth login`). It stores only
the fields needed to reproduce the reported counts; it does not infer organizational
policy compliance from missing GitHub links.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


OWNER = "argoproj"
REPOSITORY = "argo-cd"
DEFAULT_CUTOFF = "2026-08-07T15:30:00Z"
PR_TARGET = 200
RELEASE_TARGET = 30

QUERY = r"""
query($owner:String!,$name:String!,$first:Int!,$after:String){
  repository(owner:$owner,name:$name){
    pullRequests(first:$first,after:$after,states:MERGED,
      orderBy:{field:UPDATED_AT,direction:DESC}){
      nodes{
        number
        mergedAt
        title
        bodyText
        url
        closingIssuesReferences(first:1){totalCount}
        reviews(first:100){totalCount nodes{state}}
        mergeCommit{oid}
      }
      pageInfo{hasNextPage endCursor}
    }
  }
}
"""


def gh_json(*args: str) -> object:
    proc = subprocess.run(
        ["gh", "api", *args], check=True, text=True, capture_output=True
    )
    return json.loads(proc.stdout)


def collect_prs(cutoff: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    cursor: str | None = None
    issue_reference = re.compile(
        rf"(?:github\.com/{OWNER}/{REPOSITORY}/issues/\d+|"
        r"(?:fix(?:e[sd])?|close[sd]?|resolve[sd]?|issue(?:s)?|related\s+to)\s*:?\s*#\d+)",
        re.IGNORECASE,
    )
    for _ in range(20):
        args = [
            "graphql", "-f", f"query={QUERY}", "-F", f"owner={OWNER}",
            "-F", f"name={REPOSITORY}", "-F", "first=100",
        ]
        if cursor:
            args += ["-f", f"after={cursor}"]
        payload = gh_json(*args)
        connection = payload["data"]["repository"]["pullRequests"]
        for node in connection["nodes"]:
            if node["mergedAt"] <= cutoff:
                approvals = sum(
                    1 for review in node["reviews"]["nodes"]
                    if review["state"] == "APPROVED"
                )
                rows.append({
                    "number": node["number"],
                    "merged_at": node["mergedAt"],
                    "title": node["title"],
                    "url": node["url"],
                    "closing_issue_links": node["closingIssuesReferences"]["totalCount"],
                    "has_explicit_issue_reference": bool(
                        issue_reference.search(f"{node['title']}\n{node.get('bodyText') or ''}")
                    ),
                    "approval_reviews": approvals,
                    "review_objects": node["reviews"]["totalCount"],
                    "review_scan_truncated": node["reviews"]["totalCount"] > 100,
                    "merge_commit": (node["mergeCommit"] or {}).get("oid"),
                })
                if len(rows) == PR_TARGET:
                    return rows
        if not connection["pageInfo"]["hasNextPage"]:
            break
        cursor = connection["pageInfo"]["endCursor"]
    raise RuntimeError(f"Only collected {len(rows)} merged PRs before cutoff")


def collect_releases(cutoff: str) -> list[dict[str, object]]:
    payload = gh_json(f"repos/{OWNER}/{REPOSITORY}/releases?per_page=100")
    rows: list[dict[str, object]] = []
    reference = re.compile(
        rf"(?:#{1}\d+|github\.com/{OWNER}/{REPOSITORY}/(?:pull|compare)/|/pull/\d+)",
        re.IGNORECASE,
    )
    sha = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
    for release in payload:
        published = release.get("published_at")
        if not published or published > cutoff or release.get("draft"):
            continue
        body = release.get("body") or ""
        rows.append({
            "tag_name": release["tag_name"],
            "published_at": published,
            "url": release["html_url"],
            "target_commitish": release.get("target_commitish"),
            "has_explicit_change_reference": bool(reference.search(body)),
            "target_is_full_sha": bool(sha.fullmatch(release.get("target_commitish") or "")),
        })
        if len(rows) == RELEASE_TARGET:
            break
    if not rows:
        raise RuntimeError("No releases found before cutoff")
    return rows


def pct(count: int, total: int) -> str:
    return f"{100 * count / total:.1f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cutoff", default=DEFAULT_CUTOFF)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "data")
    args = parser.parse_args()
    cutoff = args.cutoff
    datetime.fromisoformat(cutoff.replace("Z", "+00:00"))

    prs = collect_prs(cutoff)
    releases = collect_releases(cutoff)
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
    symbolic_target = sum(not row["target_is_full_sha"] for row in releases)
    summary = {
        "repository": f"{OWNER}/{REPOSITORY}",
        "cutoff_utc": cutoff,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sampling_rule": f"Most recently updated {PR_TARGET} merged pull requests before cutoff; most recent {len(releases)} published non-draft releases before cutoff.",
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
        "releases_with_symbolic_target_commitish": symbolic_target,
        "releases_with_symbolic_target_commitish_pct": pct(symbolic_target, len(releases)),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "argocd_sample.json").write_text(
        json.dumps({"summary": summary, "pull_requests": prs, "releases": releases}, indent=2) + "\n",
        encoding="utf-8",
    )
    with (args.output_dir / "argocd_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["measure", "count", "denominator", "percent"])
        writer.writerows([
            ["Merged PRs without closing-issue link", no_issue, len(prs), pct(no_issue, len(prs))],
            ["Merged PRs without closing link or explicit issue reference", no_issue_reference, len(prs), pct(no_issue_reference, len(prs))],
            ["Merged PRs without approved review object", no_approval, len(prs), pct(no_approval, len(prs))],
            ["Merged PRs without either artifact", neither, len(prs), pct(neither, len(prs))],
            ["Releases without explicit PR/compare reference", no_release_lineage, len(releases), pct(no_release_lineage, len(releases))],
            ["Releases whose target_commitish is symbolic", symbolic_target, len(releases), pct(symbolic_target, len(releases))],
        ])
    tex = """%% Generated by empirical/collect_argocd_repository.py
\\newcommand{\\ArgoPRTotal}{%d}
\\newcommand{\\ArgoNoIssue}{%d}
\\newcommand{\\ArgoNoIssuePct}{%s\\%%}
\\newcommand{\\ArgoNoIssueReference}{%d}
\\newcommand{\\ArgoNoIssueReferencePct}{%s\\%%}
\\newcommand{\\ArgoNoApproval}{%d}
\\newcommand{\\ArgoNoApprovalPct}{%s\\%%}
\\newcommand{\\ArgoNeither}{%d}
\\newcommand{\\ArgoNeitherPct}{%s\\%%}
\\newcommand{\\ArgoReleaseTotal}{%d}
\\newcommand{\\ArgoNoReleaseLineage}{%d}
\\newcommand{\\ArgoNoReleaseLineagePct}{%s\\%%}
\\newcommand{\\ArgoSymbolicTarget}{%d}
\\newcommand{\\ArgoSymbolicTargetPct}{%s\\%%}
""" % (
        len(prs), no_issue, pct(no_issue, len(prs)), no_issue_reference,
        pct(no_issue_reference, len(prs)), no_approval,
        pct(no_approval, len(prs)), neither, pct(neither, len(prs)), len(releases),
        no_release_lineage, pct(no_release_lineage, len(releases)), symbolic_target,
        pct(symbolic_target, len(releases)),
    )
    (args.output_dir.parent / "argocd_macros.tex").write_text(tex, encoding="ascii")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
