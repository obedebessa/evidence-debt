# Frozen Argo CD repository observation

This directory contains the bounded public-repository census reported in the
manuscript. It is an occurrence check for declared evidence-deficit classes, not
an Evidence Debt, reconstruction-cost, or governance-quality measurement.

## Frozen design

- Repository: `argoproj/argo-cd`
- Cutoff: `2026-08-07T15:30:00Z`
- Pull requests: the 200 most recently updated merged PRs before the cutoff
- Releases: the 30 most recent published, non-draft releases before the cutoff
- Intent proxy: a machine-resolvable closing-issue link or an explicit issue
  reference in the PR title/body
- Authorization proxy: at least one `APPROVED` GitHub review object
- Release-lineage proxy: an explicit PR or compare reference in release notes

The proxy schema is deliberately narrow and does not represent Argo CD's internal
processes or the manuscript's full six-interrogative schema.

## Files

- `data/argocd_sample.json`: minimal frozen source fields and summary
- `data/argocd_summary.csv`: human-readable result table
- `argocd_macros.tex`: generated values consumed by the manuscript
- `collect_argocd_repository.py`: authenticated GitHub collector

## Recollect and verify

Recollection requires Python 3.10+, an authenticated GitHub CLI, and live network
access:

```bash
python3 empirical/collect_argocd_repository.py
python3 scripts/verify_empirical_snapshot.py
```

The live repository can change. Recollection is therefore separate from the main
artifact verifier, which checks internal consistency of the frozen snapshot.

## Interpretation limits

A PR can document intent without an issue; an issue may exist in a private or
external tracker; approval can be encoded outside GitHub; and current API state
cannot show that a link once existed and was later removed. The sample is recent
and purposive, not random. The results support occurrence under the declared
schema, not prevalence, negligence, causal cost, or financial magnitude.
