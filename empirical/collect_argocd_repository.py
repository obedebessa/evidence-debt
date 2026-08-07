#!/usr/bin/env python3
"""Collect a frozen, age-stratified public-evidence sample from Argo CD.

The collector requires an authenticated GitHub CLI (``gh auth login``). It uses
``mergedAt`` for selection, resolves candidate GitHub issue tokens through the
API, and stores only the public fields needed to reproduce the reported counts.
It does not infer intent quality, organizational authorization, policy
compliance, evidence-debt magnitude, or reconstruction cost.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


OWNER = "argoproj"
REPOSITORY = "argo-cd"
DEFAULT_CUTOFF = "2026-08-07T15:30:00Z"
COHORT_SIZE = 50
RELEASE_TARGET = 30
AUDIT_SEED = 20260807
AUDIT_ALLOCATION = {"recent": 13, "about_1y": 13, "about_3y": 12, "about_5y": 12}


@dataclass(frozen=True)
class CohortSpec:
    name: str
    start: str
    end: str
    target: str
    selection: str


COHORTS = (
    CohortSpec("recent", "2026-07-01", "2026-08-07", DEFAULT_CUTOFF, "latest"),
    CohortSpec("about_1y", "2025-06-23", "2025-09-21", "2025-08-07T15:30:00Z", "nearest"),
    CohortSpec("about_3y", "2023-06-23", "2023-09-21", "2023-08-07T15:30:00Z", "nearest"),
    CohortSpec("about_5y", "2021-06-08", "2021-10-06", "2021-08-07T15:30:00Z", "nearest"),
)

SEARCH_QUERY = r"""
query($queryString:String!,$first:Int!,$after:String){
  search(query:$queryString,type:ISSUE,first:$first,after:$after){
    issueCount
    nodes{
      ... on PullRequest{
        number
        mergedAt
        title
        bodyText
        url
        author{login __typename}
        closingIssuesReferences(first:20){
          totalCount
          nodes{number url state repository{nameWithOwner}}
        }
        reviews(first:1,states:APPROVED){totalCount nodes{state}}
        files(first:20){totalCount nodes{path}}
        labels(first:30){nodes{name}}
        mergeCommit{oid}
      }
    }
    pageInfo{hasNextPage endCursor}
  }
}
"""

FULL_ISSUE_URL = re.compile(
    r"https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/"
    r"(?P<repo>[A-Za-z0-9_.-]+)/issues/(?P<number>\d+)",
    re.IGNORECASE,
)
SCOPED_REFERENCE = re.compile(
    r"(?<![A-Za-z0-9_.-])(?P<owner>[A-Za-z0-9_.-]+)/"
    r"(?P<repo>[A-Za-z0-9_.-]+)#(?P<number>\d+)\b"
)
LOCAL_REFERENCE = re.compile(r"(?<![A-Za-z0-9_/#.-])#(?P<number>\d+)\b")


def gh_json(*args: str) -> object:
    for attempt in range(5):
        proc = subprocess.run(
            ["gh", "api", *args], text=True, capture_output=True
        )
        if not proc.returncode:
            return json.loads(proc.stdout)
        if attempt == 4:
            raise RuntimeError(proc.stderr.strip() or f"gh api failed with {proc.returncode}")
        time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def gh_json_optional(*args: str) -> object | None:
    for attempt in range(5):
        proc = subprocess.run(
            ["gh", "api", *args], text=True, capture_output=True
        )
        if not proc.returncode:
            return json.loads(proc.stdout)
        if "HTTP 404" in proc.stderr:
            return None
        if attempt < 4:
            time.sleep(2 ** attempt)
    raise RuntimeError(proc.stderr.strip() or "gh api failed after retries")


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def search_window(spec: CohortSpec, cutoff: str) -> list[dict[str, object]]:
    query = (
        f"repo:{OWNER}/{REPOSITORY} is:pr is:merged "
        f"merged:{spec.start}..{spec.end}"
    )
    rows: list[dict[str, object]] = []
    cursor: str | None = None
    issue_count: int | None = None
    while True:
        args = [
            "graphql",
            "-f", f"query={SEARCH_QUERY}",
            "-F", f"queryString={query}",
            "-F", "first=40",
        ]
        if cursor:
            args += ["-f", f"after={cursor}"]
        payload = gh_json(*args)
        connection = payload["data"]["search"]
        issue_count = connection["issueCount"]
        if issue_count > 1000:
            raise RuntimeError(f"Search window for {spec.name} exceeds GitHub's 1000-result limit")
        rows.extend(node for node in connection["nodes"] if node and node.get("mergedAt"))
        if not connection["pageInfo"]["hasNextPage"]:
            break
        cursor = connection["pageInfo"]["endCursor"]

    cutoff_dt = parse_utc(cutoff)
    rows = [row for row in rows if parse_utc(row["mergedAt"]) <= cutoff_dt]
    if spec.selection == "latest":
        rows.sort(key=lambda row: (parse_utc(row["mergedAt"]), row["number"]), reverse=True)
    else:
        target = parse_utc(spec.target)
        rows.sort(key=lambda row: (abs((parse_utc(row["mergedAt"]) - target).total_seconds()), row["number"]))
    if len(rows) < COHORT_SIZE:
        raise RuntimeError(f"Only {len(rows)} eligible PRs for cohort {spec.name}")
    return rows[:COHORT_SIZE]


def non_overlapping_matches(text: str) -> list[dict[str, object]]:
    candidates: list[tuple[int, int, str, str, int]] = []
    for match in FULL_ISSUE_URL.finditer(text):
        candidates.append((match.start(), match.end(), match.group("owner"), match.group("repo"), int(match.group("number"))))
    for match in SCOPED_REFERENCE.finditer(text):
        candidates.append((match.start(), match.end(), match.group("owner"), match.group("repo"), int(match.group("number"))))
    for match in LOCAL_REFERENCE.finditer(text):
        candidates.append((match.start(), match.end(), OWNER, REPOSITORY, int(match.group("number"))))

    selected: list[tuple[int, int, str, str, int]] = []
    for item in sorted(candidates, key=lambda value: (value[0], -(value[1] - value[0]))):
        if any(item[0] < other[1] and other[0] < item[1] for other in selected):
            continue
        selected.append(item)
    return [
        {
            "token": text[start:end],
            "repository": f"{owner}/{repo}",
            "number": number,
        }
        for start, end, owner, repo, number in selected
    ]


def resolve_references(
    tokens: Iterable[dict[str, object]], cache: dict[tuple[str, int], dict[str, object]]
) -> list[dict[str, object]]:
    resolved: list[dict[str, object]] = []
    for token in tokens:
        repository = str(token["repository"])
        number = int(token["number"])
        key = (repository.lower(), number)
        if key not in cache:
            payload = gh_json_optional(f"repos/{repository}/issues/{number}")
            if payload is None:
                cache[key] = {"kind": "missing_or_inaccessible", "state": None, "url": None}
            elif "pull_request" in payload:
                cache[key] = {"kind": "pull_request", "state": payload.get("state"), "url": payload.get("html_url")}
            else:
                cache[key] = {"kind": "issue", "state": payload.get("state"), "url": payload.get("html_url")}
        resolved.append({**token, **cache[key]})
    return resolved


def classify_authorship(node: dict[str, object]) -> str:
    author = node.get("author") or {}
    login = str(author.get("login") or "").lower()
    if author.get("__typename") == "Bot" or login.endswith("[bot]") or "renovate" in login or "dependabot" in login:
        return "bot-authored"
    return "human-authored"


def classify_change(node: dict[str, object]) -> str:
    title = str(node.get("title") or "").lower().strip()
    labels = {str(label["name"]).lower() for label in node["labels"]["nodes"]}
    paths = [str(item["path"]).lower() for item in node["files"]["nodes"]]
    documentation_only = bool(paths) and all(
        path.endswith((".md", ".mdx", ".rst")) or path.startswith(("docs/", "doc/"))
        for path in paths
    ) and node["files"]["totalCount"] <= 20
    if title.startswith(("docs", "doc:")) or "documentation" in labels or documentation_only:
        return "documentation"
    if (
        classify_authorship(node) == "bot-authored"
        or "dependencies" in labels
        or re.match(r"^(?:chore|build)\(deps[^)]*\):", title)
        or any(term in title for term in ("dependency", "dependencies", "renovate", "bump "))
    ):
        return "dependency/maintenance"
    if title.startswith(("feat", "fix", "bug")) or labels.intersection({"bug", "feature", "enhancement", "kind/bug"}):
        return "feature/bug"
    if title.startswith(("chore", "build", "ci", "refactor", "perf", "test", "revert")):
        return "dependency/maintenance"
    return "other"


def normalize_pr(node: dict[str, object], cohort: str, cache: dict[tuple[str, int], dict[str, object]]) -> tuple[dict[str, object], str]:
    body = str(node.get("bodyText") or "")
    text = f"{node['title']}\n{body}"
    references = resolve_references(non_overlapping_matches(text), cache)
    approvals = int(node["reviews"]["totalCount"])
    closing = node["closingIssuesReferences"]
    row = {
        "cohort": cohort,
        "number": node["number"],
        "merged_at": node["mergedAt"],
        "title": node["title"],
        "url": node["url"],
        "author_login": (node.get("author") or {}).get("login"),
        "authorship": classify_authorship(node),
        "change_type": classify_change(node),
        "labels": sorted(label["name"] for label in node["labels"]["nodes"]),
        "changed_files": node["files"]["totalCount"],
        "file_scan_truncated": node["files"]["totalCount"] > 20,
        "closing_issue_links": closing["totalCount"],
        "closing_issue_targets": [
            {
                "repository": item["repository"]["nameWithOwner"],
                "number": item["number"],
                "state": item["state"],
                "url": item["url"],
            }
            for item in closing["nodes"]
        ],
        "explicit_reference_tokens": references,
        "has_explicit_issue_reference": any(item["kind"] == "issue" for item in references),
        "approval_reviews": approvals,
        "review_objects": node["reviews"]["totalCount"],
        "review_scan_truncated": False,
        "merge_commit": (node.get("mergeCommit") or {}).get("oid"),
    }
    return row, body


def collect_prs(cutoff: str) -> tuple[list[dict[str, object]], dict[int, str]]:
    cache: dict[tuple[str, int], dict[str, object]] = {}
    rows: list[dict[str, object]] = []
    bodies: dict[int, str] = {}
    for spec in COHORTS:
        for node in search_window(spec, cutoff):
            row, body = normalize_pr(node, spec.name, cache)
            rows.append(row)
            bodies[int(row["number"])] = body
    if len({row["number"] for row in rows}) != len(rows):
        raise RuntimeError("Cohort selection produced duplicate pull requests")
    return rows, bodies


def collect_releases(cutoff: str) -> list[dict[str, object]]:
    payload = gh_json(f"repos/{OWNER}/{REPOSITORY}/releases?per_page=100")
    rows: list[dict[str, object]] = []
    reference = re.compile(
        rf"(?:#\d+|github\.com/{OWNER}/{REPOSITORY}/(?:pull|compare)/|/pull/\d+)",
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
    if len(rows) != RELEASE_TARGET:
        raise RuntimeError(f"Only collected {len(rows)} releases before cutoff")
    return rows


def pct(count: int, total: int) -> str:
    return f"{100 * count / total:.1f}"


def has_external_issue_reference(row: dict[str, object]) -> bool:
    return bool(row["closing_issue_links"] or row["has_explicit_issue_reference"])


def summarize_strata(prs: list[dict[str, object]]) -> list[dict[str, object]]:
    dimensions = {
        "age cohort": [spec.name for spec in COHORTS],
        "authorship": ["human-authored", "bot-authored"],
        "change type": ["feature/bug", "dependency/maintenance", "documentation", "other"],
    }
    rows: list[dict[str, object]] = []
    for dimension, strata in dimensions.items():
        key = {"age cohort": "cohort", "authorship": "authorship", "change type": "change_type"}[dimension]
        for stratum in strata:
            group = [row for row in prs if row[key] == stratum]
            if not group:
                continue
            missing = sum(not has_external_issue_reference(row) for row in group)
            rows.append({
                "dimension": dimension,
                "stratum": stratum,
                "total": len(group),
                "without_external_issue_reference": missing,
                "share_without_external_issue_reference": pct(missing, len(group)),
            })
    return rows


def write_audit_sample(output_dir: Path, prs: list[dict[str, object]], bodies: dict[int, str]) -> None:
    rng = random.Random(AUDIT_SEED)
    selected: list[dict[str, object]] = []
    for cohort, count in AUDIT_ALLOCATION.items():
        candidates = sorted((row for row in prs if row["cohort"] == cohort), key=lambda row: row["number"])
        selected.extend(rng.sample(candidates, count))
    selected.sort(key=lambda row: (row["cohort"], row["number"]))
    with (output_dir / "argocd_audit_sample.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["cohort", "number", "url", "title", "body_text", "collector_external_issue_reference"])
        for row in selected:
            writer.writerow([
                row["cohort"], row["number"], row["url"], row["title"],
                bodies[int(row["number"])], int(has_external_issue_reference(row)),
            ])


def write_outputs(output_dir: Path, cutoff: str, prs: list[dict[str, object]], releases: list[dict[str, object]], bodies: dict[int, str]) -> dict[str, object]:
    closing_present = sum(row["closing_issue_links"] > 0 for row in prs)
    explicit_only = sum(row["closing_issue_links"] == 0 and row["has_explicit_issue_reference"] for row in prs)
    no_external = sum(not has_external_issue_reference(row) for row in prs)
    approved = sum(row["approval_reviews"] > 0 for row in prs)
    release_lineage = sum(row["has_explicit_change_reference"] for row in releases)
    symbolic_target = sum(not row["target_is_full_sha"] for row in releases)
    strata = summarize_strata(prs)
    summary = {
        "repository": f"{OWNER}/{REPOSITORY}",
        "cutoff_utc": cutoff,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sampling_rule": "Four disjoint mergedAt cohorts: 50 latest merged PRs before cutoff and 50 PRs nearest each of the 1-, 3-, and 5-year target ages.",
        "cohort_size": COHORT_SIZE,
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
        "releases_with_symbolic_target_commitish": symbolic_target,
        "releases_with_symbolic_target_commitish_pct": pct(symbolic_target, len(releases)),
        "manual_audit_seed": AUDIT_SEED,
        "manual_audit_size": sum(AUDIT_ALLOCATION.values()),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "argocd_sample.json").write_text(
        json.dumps({"summary": summary, "cohort_definitions": [spec.__dict__ for spec in COHORTS], "pull_requests": prs, "releases": releases}, indent=2) + "\n",
        encoding="utf-8",
    )
    with (output_dir / "argocd_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["evidence_observed", "count", "denominator", "percent"])
        writer.writerows([
            ["Closing-issue link present", closing_present, len(prs), pct(closing_present, len(prs))],
            ["Explicit non-closing issue reference only", explicit_only, len(prs), pct(explicit_only, len(prs))],
            ["No external issue reference", no_external, len(prs), pct(no_external, len(prs))],
            ["At least one APPROVED review record", approved, len(prs), pct(approved, len(prs))],
            ["Release with PR/compare reference", release_lineage, len(releases), pct(release_lineage, len(releases))],
        ])
    with (output_dir / "argocd_strata.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(strata[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(strata)
    write_audit_sample(output_dir, prs, bodies)

    tex = """%% Generated by empirical/collect_argocd_repository.py
\\newcommand{\\ArgoPRTotal}{%d}
\\newcommand{\\ArgoClosingPresent}{%d}
\\newcommand{\\ArgoClosingPresentPct}{%s\\%%}
\\newcommand{\\ArgoExplicitOnly}{%d}
\\newcommand{\\ArgoExplicitOnlyPct}{%s\\%%}
\\newcommand{\\ArgoNoExternal}{%d}
\\newcommand{\\ArgoNoExternalPct}{%s\\%%}
\\newcommand{\\ArgoApproved}{%d}
\\newcommand{\\ArgoApprovedPct}{%s\\%%}
\\newcommand{\\ArgoReleaseTotal}{%d}
\\newcommand{\\ArgoReleaseLineage}{%d}
\\newcommand{\\ArgoReleaseLineagePct}{%s\\%%}
""" % (
        len(prs), closing_present, pct(closing_present, len(prs)), explicit_only,
        pct(explicit_only, len(prs)), no_external, pct(no_external, len(prs)),
        approved, pct(approved, len(prs)), len(releases), release_lineage,
        pct(release_lineage, len(releases)),
    )
    stratum_macros = {
        ("age cohort", "recent"): "ArgoRecent",
        ("age cohort", "about_1y"): "ArgoOneYear",
        ("age cohort", "about_3y"): "ArgoThreeYear",
        ("age cohort", "about_5y"): "ArgoFiveYear",
        ("authorship", "human-authored"): "ArgoHuman",
        ("authorship", "bot-authored"): "ArgoBot",
        ("change type", "feature/bug"): "ArgoFeatureBug",
        ("change type", "dependency/maintenance"): "ArgoMaintenance",
        ("change type", "documentation"): "ArgoDocumentation",
    }
    for row in strata:
        macro = stratum_macros.get((row["dimension"], row["stratum"]))
        if not macro:
            continue
        tex += f"\\newcommand{{\\{macro}Total}}{{{row['total']}}}\n"
        tex += f"\\newcommand{{\\{macro}NoExternal}}{{{row['without_external_issue_reference']}}}\n"
        tex += f"\\newcommand{{\\{macro}NoExternalPct}}{{{row['share_without_external_issue_reference']}\\%}}\n"
    (output_dir.parent / "argocd_macros.tex").write_text(tex, encoding="ascii")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cutoff", default=DEFAULT_CUTOFF)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "data")
    args = parser.parse_args()
    parse_utc(args.cutoff)

    prs, bodies = collect_prs(args.cutoff)
    releases = collect_releases(args.cutoff)
    summary = write_outputs(args.output_dir, args.cutoff, prs, releases, bodies)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
