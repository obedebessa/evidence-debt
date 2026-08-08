# Release notes

## v1.7.2 — 2026-08-07

- Defines a sound exhaustive policy as one that both completes the declared source
  exhaustion and accepts only evidence-established answers at the confidence
  threshold.
- Qualifies Propositions 2--4, Figure 1, and the interest discussion: physical
  irrecoverability forces abstention only for sound exhaustive policies; another
  policy may return $W$.
- Corrects the remaining unqualified numerical reference from $ED$ to $ED_\rho$.
- Makes Evidence Liability explicitly refer to wrongly answered parts or parts
  left uncertified by $\rho$.
- Rephrases Evidence Schema to prevent the apparent extracted-text join in
  "evidence elements required."
- Makes no new empirical claim and publishes the exact reproducible artifact as
  Zenodo DOI `10.5281/zenodo.21845695`.

## v1.7.1 — 2026-08-07 (local release candidate; not published)

- Renames the manuscript around deferred reconstruction *burden*, matching the
  effort, accepted-error, and policy-abstention estimand.
- Defines $N$ everywhere as no answer certified by $\rho$, rather than wording that
  could imply universal irrecoverability.
- Reworks the lifecycle and technical-debt comparison figures so physical
  irrecoverability is the terminal evidence state, not an additive-policy outcome.
- Corrects the Figure 4(d) panel title from unqualified $ED$ to $ED_\rho$.
- Replaces premature "released artifact/data" wording with "accompanying" while
  the exact version remains local and unpublished.
- Makes no new empirical claim and does not represent the field protocol as
  executed.

## v1.7.0 — 2026-08-07 (local release candidate; not published)

- Separates policy abstention ($N$) from certified physical irrecoverability
  throughout the definitions, model, metrics, simulation, and field protocol.
- Declares the evaluation measure underlying every expectation and probability.
- Replaces computed "write-off" labels with abstention exposure while preserving
  physical IRR and the mandatory irrecoverability boundary as separate constructs.
- Regenerates the main table to show S/W/N shares, FRR, physical IRR, ERC, and
  policy-specific $ED_\rho$ directly.
- Limits the redundancy plateau proposition to effort unless the surviving path
  also preserves the relevant consequence profile.
- Explains the mixed density result through ambiguity and denominator selection,
  corrects the residual density claim in threats to validity, and strengthens the
  pre-ground-truth acceptance statement in the abstract and introduction.
- Adds a practical low/base/high consequence-weight calibration guide and a formal
  capture-cost-versus-risk gate without claiming field calibration.
- Keeps the public v1.2.0 DOI visibly distinct from this unpublished local version.

## v1.6.0 — 2026-08-07 (local release candidate; not published)

- Makes the acceptance indicator a corpus-only policy decision made before
  ground-truth scoring; ambiguous candidates are abstentions even when lucky.
- Regenerates all results under the exact S/W/N partition and verifies
  `supported + accepted-wrong + no-certifiable = 1` in every cell.
- Separates theoretical optimal debt $ED^*$ from the fixed-policy estimand
  $ED_\rho$ and marks synthetic numerical results accordingly.
- Adds a controlled complete-corpus reference arm to the field-drill protocol.
- Adds a 5-by-5 joint $\lambda/\pi$ sensitivity grid, retains the complete
  six-slice table in the artifact, and compresses the body table.
- Reports the isolated density test as mixed rather than preserving a monotonic
  claim unsupported under the preregistered acceptance policy.
- Makes field irrecoverability relative to a declared source universe,
  confidence threshold, and exhaustion protocol; softens absolute novelty claims.

## v1.5.0 — 2026-08-07 (local release candidate; not published)

- Defines one default reconstruction policy with mutually exclusive
  supported-correct, accepted-wrong, and no-certifiable-answer outcomes.
- Replaces effort-only optimization with an information-monotone optimum over
  total effort, error, and no-certifiable-answer burden; fixed-policy estimates
  are explicitly distinguished from the formal optimum.
- Regenerates the simulation with exclusive error/write-off accounting and adds
  verifier invariants for outcome exclusivity and component totals.
- Expands reconstruction performance to ERC plus False Reconstruction Rate and
  includes both channels in the EDI specification and field protocol.
- Broadens RQ3 to effort, accuracy, and confidence; qualifies the plateau-and-cliff
  result to effort/write-off unless path error is constant between events.
- Recasts Proposition 5 as four input families and clarifies the chain-level IRR
  display versus link-level write-off computation.

## v1.4.0 — 2026-08-07 (local release candidate; not published)

- Adds the wrong-answer consequence channel $\lambda_q\Pr(\mathrm{Err}_q)$ to the
  definition and to the executed end-to-end debt calculation.
- Uses optimal information-monotone attempt cost and an augmented ideal corpus to
  guarantee nonnegative excess burden.
- Adds a paired, per-link acceptable-path census that tests Proposition 2 on
  identical source records and identifier/timestamp masks.
- Reframes the main pairwise result as superadditive coverage loss consistent with
  the proposition, without treating record survival as path survival.
- Regenerates tables and figures with effort/error/write-off decomposition and
  limits ranking claims to the tested penalty grid.
- Renames M4 to Evidence Debt Inflow Rate, distinguishes repayment from negative
  interest, corrects the interest-curve label, and softens the documentation-debt
  comparison.
- Documents the repository-stratum coding rules and explicitly scopes the missing
  second-reviewer validation as future work.
- Prepares release metadata without reusing the v1.2.0 version DOI.

## v1.3.0 — 2026-08-07 (local draft; not published)

- Softens the manuscript title to focus on modeling deferred reconstruction cost.
- Removes the remaining commissioning-brief language from the manuscript.
- Defines reconstruction-attempt cost as finite effort ending in either a
  confidence-qualified answer or a certificate of irrecoverability after source
  exhaustion.
- Corrects Proposition 2 by proving superadditivity of the irrecoverability
  indicator, with a finite penalty term rather than an undefined/infinite cost.
- Corrects the factorial description to seven arms and shows the pairwise arm in
  the experiment diagram.
- Adds a generated sensitivity analysis for
  $\pi\in\{0,1,10,25,50,100\}$, reporting effort, write-off, total debt, and the
  complete arm ranking in `data/pi_sensitivity.csv` and Table II.
- Extends the deterministic verifier to reproduce the new sensitivity outputs.

## v1.2.0 — 2026-08-07

- Replaces `updatedAt` sampling with four disjoint 50-PR cohorts selected by
  `mergedAt`: recent, approximately one year, three years, and five years old.
- Reports mutually exclusive linkage categories and descriptive strata for age,
  authorship, and change type.
- Defines and tests the exact external issue-reference grammar, resolving candidate
  GitHub tokens to distinguish Issues, PRs, and missing targets.
- Adds a seeded 50-PR single-reviewer audit with frozen coding, confusion matrix,
  precision, recall, and explicit non-blinding limitation.
- Reframes the external result as missing external issue linkage, not an intent
  deficit, intent-quality judgment, temporal-decay finding, or debt measurement.
- Compresses the abstract to 220 words, restores the effort-before-visible-failure
  result, makes the economic-chain figure robust in monochrome, and adds a Data and
  Code Availability section with DOI, repository tag, and SHA-256 manifest.

## v1.1.0 — 2026-08-07

- Adds a frozen, reproducible census of 200 merged Argo CD pull requests and 30 releases.
- Distinguishes an observed linkage absence from approval and release-lineage controls.
- States explicitly that repository observations are not evidence-debt or cost measurements.
- Adds a causal accounting figure from evidence deficit to reconstruction effort, operational/audit cost, and financial exposure.
- Expands verification to check the frozen empirical snapshot against the generated CSV and LaTeX macros.

## v1.0.0 — 2026-08-07

- Incorporates the complete simulated Reviewer #2 revision.
- Adds the pairwise identifier/timestamp arm and reports the all-class arm as deletion-dominated and subadditive.
- Computes evidence debt end to end under a declared workload.
- Separates record loss from identifiability-based irrecoverability.
- Replaces implementation-dependent effort with fallback and candidate counts.
- Adds removal and sensitivity arms and a single-knob density sweep.
- Generates the reported table from the same run that generates the results.
- Adds release metadata, integrity checks, and a verified compiled manuscript.
