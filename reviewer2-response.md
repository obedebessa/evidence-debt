# Reviewer #2 Simulation — Report and Point-by-Point Response

**Manuscript:** *Evidence Debt: Measuring the Accumulated Cost of Missing Operational Evidence in Cloud-Native Systems*
**Process:** the compiled draft — including the released simulator (`code/experiment.py`) and its data (`data/*.csv`) — was submitted to an independent adversarial review (simulated Reviewer #2 for a TSE/EMSE/JSS-class journal) with explicit instructions to audit every reported number against the data files and to scrutinize the code for apparatus-driven conclusions. The reviewer did exactly that, and the review was unusually consequential: it identified factual errors, an apparatus-entailed "confirmation," a refuted headline prediction, and a never-computed central construct. §1 summarizes the review; §2 records the disposition of every item in the revised manuscript. The revision required a substantially upgraded simulator (v2) and full re-execution — not wording changes.

---

## 1. The review as received (summary)

> **Recommendation: Reject.** … the submission's flagship "confirmed prediction" of superadditive interaction is **contradicted by the authors' own released data**; … the central construct of the paper — ED(t) — is **never computed anywhere**; … the simulation's remaining "confirmations" are baked into the apparatus; … the abstract and Table I contain factual errors.

**Major objections:** M1 superadditivity (PR2/F2) refuted by the data — combined-arm losses are *sub*additive, the "confirmation" rested on silently excluding the deletion arm from "single-class arms"; M2 ED(t) never instantiated, counterfactual corpus E\* underdefined, Definitions 3 and 8 mutually contradictory, Proposition 5's proof vacuous; M3 abstract misreports results ("≤1.2%" cherry-picked; "2–4× before coverage visibly degrades" overstated); M4 generator/reconstructor co-design entails PR1/PR3/PR4 ("preregistered-style" unearned; heuristic window built wider than the maximum true gap; filer=author always; dense profile bundles three knobs); M5 the irrecoverability "validation" against 1−(1−p)⁶ is circular and the scored construct implements only the destroyed-record clause of Definition 5; M6 the effort metric is not implementation-invariant (baseline was an artifact of an unindexed linear scan); M7 nine of twelve Table I SDs disagree with the released CSV and the "below 1.5 points" variance claim is false; M8 the metaphor concedes everything and the paper never shows what "debt" adds over "reconstruction exposure"; M9 schema/workload relativity makes ED non-comparable across estates; M10 missing literatures — MSR "missing links" (Bachmann, Bird), traceability recovery (Gotel & Finkelstein, Antoniol), process mining (van der Aalst), dark/social/hidden debt (STELLA, Tamburri, Sculley), logging-practice studies (Yuan).

**Minors (m1–m12):** overclaimed "all metrics computed"; a "within one point" claim off by 0.1; degenerate half-life; dead code in the artifact; unexplained references to a private "commissioning brief"; table formatting inconsistencies; figure/series mismatches; bib entry type and mis-cited Rahman paper; unstated scoring-orientation asymmetry; bundled density knobs; fragile manual cross-references; run-on abstract.

---

## 2. Point-by-point disposition

### Major — all addressed with re-execution, not rhetoric

**M1 — Superadditivity.** *Resolved by redesign and re-execution.* The old F2 is retracted. Simulator v2 adds a **pairwise arm (correlation identifiers + timestamps)** that instantiates Proposition 2's actual premise — neither class deletes records (record loss is 0.000 in every pairwise cell). The result is a genuine, pre-committed, could-have-failed test, and it passed strongly: joint coverage loss 35.2 points vs. a 16.0-point sum of singles (dense) and 32.6 vs. 4.0 (sparse — an eight-fold excess). The all-classes arm is now reported for what the data show: **deletion-dominated and subadditive in coverage** (16.1 vs. 16.9 points at p=5%, dense), with the saturation mechanism explained by the model. The false "at most 0.6 points" sentence is gone. (Finding 2, §VI.)

**M2 — ED(t) never computed.** *Resolved.* v2 computes ED end to end under a declared synthetic workload (one full-chain audit query per configuration; declared unit costs; π=50/irrecoverable link): Finding 6, Fig. 3(d), and the ED column of Table I. The decomposition result (write-off term dominates effort by ≥10× under this declaration, and inverts if π is small) is reported as content, feeding §X-B. E\* is now precisely defined (ideal corpus: schema-complete, decay-free, with the attribution consequence stated — §III, Def. 6). Definitions 3 and 8 are reconciled (interest = path decay + corpus decay, both distinguished from new borrowing). Proposition 5 is restated as an input-enumeration result with two "honesty notes" (calibration is the hard empirical part; relativity conditions), and RQ2's answer is correspondingly conditioned.

**M3 — Abstract misreporting.** *Resolved.* The abstract now reports the full range ("between 0.9 and 16 points of link coverage depending on class"), the pairwise result, and drops the invariance-broken "2–4×" formulation.

**M4 — Apparatus co-design.** *Resolved by honest repositioning plus falsification-capable arms.* "Preregistered-style" deleted. §VI now opens by separating **demonstrations** (design-entailed; evidential force tested by removal arms) from **falsifiable tests**. New arms, all executed and reported: redundancy-off (coverage 84.0→72.6%, irrecoverability 65.3→84.7%, ED 1.6× — the plateau's dependence on redundancy is now quantified by its removal); heuristic window 24h < 36h max gap (trades reach against confidence: coverage −0.6 points, irrecoverability −7.6 points); filer≠author for 30% of chains (intent coverage 99.1→97.5%, irrecoverability 16.8→23.4% — showing which headline numbers lean on the assumption); single-knob density sweep (false joins 10.1→16.1→19.5% with actors and window fixed — density effect isolated, M4+m10 together).

**M5 — Circular irrecoverability.** *Resolved.* v2 scores **both** constructs: "record loss" (the old quantity, relabeled) and **identifiability-based irrecoverability** implementing Definition 5 in full (destroyed OR no key path survives AND discriminators fail to single out the true parent). The constructs diverge exactly as the model requires (65.3% vs. 0.000 under pure key stripping, dense/40%) — Finding 5 and Fig. 3(c). The 1−(1−p)⁶ comparison is retained but relabeled "consistency check," with the text stating the agreement is arithmetically expected and claiming nothing more.

**M6 — Effort metric invariance.** *Resolved.* v2 charges all exact and redundant joins zero (index lookups) and counts effort only at heuristic decision points, as two invariant quantities: fallback links per chain and candidates examined. Baseline effort is now exactly 0; the old 25.5/75.5 linear-scan artifacts are gone, and Finding 3 is restated in the new units (0.97 of 6 links in fallback at 146 candidates/chain while coverage is still 84%). A new correctness-without-confidence observation (84% correct vs. 65% not certifiable) emerged from the fix and is reported.

**M7 — Table/variance errors.** *Resolved structurally.* The results table is now generated programmatically by the simulator (`data/table_full.tex`, `\input` into the paper) — hand transcription is eliminated as a failure mode. The variance claim is corrected to the actual maximum (1.9 coverage points, cell named in text).

**M8 — Metaphor value.** *Resolved by concession plus a positive argument.* §X-A now embraces the skeptic's reading — the measured quantity *is* reconstruction exposure — and then states precisely what the debt framing adds: binding the aggregate to identifiable, dated, attributable deferral decisions, licensing per-decision registration, practice-level attribution (P1–P8), and the inflow/stock separation. Framed as decisions-and-accountabilities over a metaphor-free measurement core, with the failed financial intuitions (rates, compounding, refinancing) explicitly disavowed.

**M9 — Relativity.** *Resolved as a named limitation with a constructive proposal.* New §X-B "Relativity of the Construct": what is inter-subjectively measurable is the ingredient vector; ED is an accounting quantity relative to published declarations; a reference declaration (Σ_ref = the six-interrogative schema; Q_ref parameterized by public covariates) is proposed for comparability, with the financial-reporting analogy for why shared rules, not observer-independence, are the standard. Finding 6's declaration-sensitivity result grounds the discussion empirically.

**M10 — Missing literatures.** *Resolved.* Added and engaged: Bachmann et al. (FSE 2010) and Bird et al. (ESEC/FSE 2009) — treated as *measured instances of the phenomenon in the wild* (P5 and the false-join bias channel), strengthening rather than weakening the paper, and confronted in the novelty positioning; Gotel & Finkelstein and Antoniol et al. (traceability recovery); van der Aalst (process mining and log quality); Sculley et al., Tamburri et al., and the STELLA dark-debt report (debt family extension — "evidence debt gives one species of dark debt a measurement theory"); Yuan et al. (logging practice). §IX-F now states what evidence debt adds over each (estate-level economic aggregation, decay dynamics, irrecoverability boundary) and what they supply (field evidence and execution venues).

### Minor

- **m1** metric-computation claim scoped precisely (which metric is computed where; M4/M6 declared not exercised). ✔
- **m2** "within one point" → "within 1.2 points." ✔
- **m3** half-life degeneracy in the worked example acknowledged; "most actionable" claim reformulated as a property of schedule-reading rather than a model output. ✔
- **m4** dead code removed in the v2 rewrite; the manuscript reports the artifact at the appropriate approximate scale (≈560 lines; current packaged file: 585 lines). ✔
- **m5** all "commissioning brief" references excised; the reviewer-mode and metric-rejection stances are now self-contained authorial commitments. ✔
- **m6** results table rebuilt (table*, uniform SD reporting for Cov/FJ/Irr/FB/ED). ✔
- **m7** figure panels rebuilt: pairwise series added to (a); (c) now shows both irrecoverability constructs; (d) shows computed ED; intent-link numbers carried in Table I. ✔
- **m8** `rindell2019` → `@inproceedings`; drift/IaC sentence now cites the Rahman *mapping study* (`rahman2019mapping`), with the smells paper cited where it belongs; all previously uncited entries now cited (hunt2002, lientz1980, nist80053, avgeriou2016) or removed. ✔
- **m9** approval-link scoring orientation now stated in §VI (scoring subsection). ✔
- **m10** single-knob density sweep added (see M4); profile-bundling explicitly discussed. ✔
- **m11** manual "-B/-C" cross-references replaced with proper subsection labels. ✔
- **m12** abstract broken into sentences (still dense; further compression is an editorial choice for the target venue's word limit). △

---

## 3. Residual state

The revised manuscript compiles to 18 two-column pages with zero undefined references, zero overfull boxes ≥10pt, no dead or missing bibliography entries, and a results table produced by the same program that produced the results. The simulation now contains one genuinely falsifiable headline test (passed), quantified removal arms for every design-entailed behavior, both irrecoverability constructs, invariant effort, and an end-to-end ED computation. At that review stage, field data were absent. Versions 1.1.0 and 1.2.0 subsequently added the bounded Argo CD observation documented below; it remains an occurrence check rather than a cost measurement.

---

## 4. Follow-up methodological review (v1.2.0)

The subsequent review accepted the external occurrence check but identified four
remaining threats: calling missing issue linkage an intent deficit; selecting by
mutable `updatedAt`; hiding bot/change-type composition; and leaving the collector
grammar and artifact location implicit. Version 1.2.0 addresses each point:

1. Every external claim now says **missing external issue linkage under the
   declared repository schema** and explicitly disclaims inadequate intent
   documentation, decay, debt magnitude, and reconstruction cost.
2. The observation now uses four disjoint `mergedAt` cohorts (50 recent and 50
   nearest each of one, three, and five years), after retrieving complete declared
   date windows. Cohort differences are treated as cross-sectional composition,
   not link decay.
3. Mutually exclusive headline categories replace nested absence rows. Separate
   age, human/bot, and feature/bug, maintenance/dependency, and documentation
   strata are frozen in `empirical/data/argocd_strata.csv` and reported in the
   manuscript.
4. The collector grammar is exact and executable: `#123`, `owner/repo#123`, and
   full GitHub issue URLs in title/body are candidates; targets must resolve to an
   Issue; PRs, missing targets, bare numbers, Jira keys, comments, PR URLs, and
   placeholders are excluded. Eight offline unit tests cover the boundary cases.
5. A seeded 50-PR manual audit (single reviewer, unblinded) produced TP=29, TN=21,
   FP=0, FN=0, precision=1.000, and recall=1.000 for the declared grammar. This is
   implementation validation, not construct validation.
6. The abstract is 220 words and restores the effort-before-visible-failure result;
   the economic chain uses monochrome-safe line/fill encodings; and a dedicated
   Data and Code Availability section states the Zenodo concept DOI, release tag,
   repository URL, and SHA-256 manifest.
