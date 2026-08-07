# Frozen Argo CD repository observation

This directory contains the bounded public-repository observation reported in the
manuscript. It is an occurrence check for missing external issue linkage under a
declared repository schema, not a measurement of intent quality, Evidence Debt,
reconstruction cost, governance quality, or temporal decay.

## Frozen design

- Repository: `argoproj/argo-cd`
- Cutoff: `2026-08-07T15:30:00Z`
- Pull requests: four disjoint `mergedAt` cohorts of 50 PRs each
  - `recent`: the 50 latest merges before the cutoff, selected from
    `2026-07-01..2026-08-07`
  - `about_1y`: the 50 merges nearest `2025-08-07T15:30:00Z`, selected from
    `2025-06-23..2025-09-21`
  - `about_3y`: the 50 merges nearest `2023-08-07T15:30:00Z`, selected from
    `2023-06-23..2023-09-21`
  - `about_5y`: the 50 merges nearest `2021-08-07T15:30:00Z`, selected from
    `2021-06-08..2021-10-06`
- Releases: the 30 most recent published, non-draft releases before the cutoff
- Review-record presence control: at least one `APPROVED` GitHub review object
- Release-lineage presence control: an explicit PR or compare reference in
  release notes

The age cohorts are a cross-sectional description. Differences between them can
reflect changes in contribution mix, templates, bots, or project practice; they do
not show that links disappeared with age.

## External issue-reference grammar

Only PR title and body are scanned. Review comments, commit messages, linked
documents, and external trackers are outside the schema.

Candidate tokens are:

1. local `#123` references, interpreted in `argoproj/argo-cd`;
2. scoped `owner/repository#123` references;
3. full `https://github.com/owner/repository/issues/123` URLs.

Every candidate is resolved through GitHub's API. A token counts only when the
resolved object is an Issue. A pull request is excluded even though GitHub exposes
issues and PRs through the same endpoint. Closed issues count as present. Missing,
deleted, or inaccessible targets do not count. `related to 123` without `#`, Jira
keys, PR URLs, and template placeholders such as `[ISSUE #]` do not count. A
GraphQL `closingIssuesReferences` relation is reported separately from resolved
non-closing title/body references.

This grammar detects external issue linkage. It does not determine whether the PR
itself explains intent adequately or whether a referenced issue is substantively
useful.

## Descriptive strata

Authorship is `bot-authored` when GitHub types the author as a Bot or the login is
a Dependabot/Renovate-style bot; otherwise it is `human-authored`. Change type is
assigned deterministically from title prefix, labels, and up to 20 changed paths:
documentation; dependency/maintenance; feature/bug; or other. These strata are
descriptive controls, not causal adjustments.

## Manual audit

A 50-PR audit sample is drawn within cohorts using seed `20260807` (13 recent,
13 about one year, 12 about three years, and 12 about five years). One reviewer
manually inspected the title/body and resolved-target interpretation after the
automatic collection; the audit was not blinded. The coding and confusion matrix
are frozen in `argocd_audit_coding.csv` and `argocd_validation.csv`.

## Files

- `data/argocd_sample.json`: frozen source fields, resolved tokens, and summary
- `data/argocd_summary.csv`: mutually exclusive headline evidence categories
- `data/argocd_strata.csv`: age, authorship, and change-type strata
- `data/argocd_audit_sample.csv`: seeded 50-PR manual-audit input
- `data/argocd_audit_coding.csv`: frozen single-reviewer coding
- `data/argocd_validation.csv`: confusion matrix, precision, recall, and agreement
- `argocd_macros.tex`: generated values consumed by the manuscript
- `collect_argocd_repository.py`: authenticated GitHub collector
- `test_reference_grammar.py`: offline grammar tests
- `validate_manual_audit.py`: audit validator

## Recollect and verify

Recollection requires Python 3.10+, an authenticated GitHub CLI, and live network
access:

```bash
python3 empirical/collect_argocd_repository.py
python3 scripts/verify_empirical_snapshot.py
```

The live repository can change. Recollection is therefore separate from the main
artifact verifier, which checks the internal consistency of the frozen snapshot.

## Interpretation limits

A self-contained PR may document intent adequately; an issue may live in a private
or non-GitHub tracker; an upstream dependency changelog can contribute a resolved
reference without documenting Argo CD intent; approval can be encoded elsewhere;
and current API state cannot show that a link once existed and later disappeared.
The results establish occurrence under the declared schema, not prevalence,
negligence, causal cost, financial magnitude, or evidence decay.
