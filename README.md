# Evidence Debt

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21841440.svg)](https://doi.org/10.5281/zenodo.21841440)

Reproducibility package for the current development manuscript:

> **Evidence Debt: Modeling the Deferred Reconstruction Burden of Missing Operational
> Evidence in Cloud-Native Systems**  
> Obede Bessa Rocha da Silva — Independent Researcher

The revised title and v1.7.2 manuscript are archived at Zenodo under the
version-specific DOI <https://doi.org/10.5281/zenodo.21845695>.

## Read and cite the paper

- [Read the manuscript (PDF)](output/pdf/evidence-debt-v1.7.2.pdf)
- [Open the permanent Zenodo record](https://doi.org/10.5281/zenodo.21845695)
- Use GitHub's **Cite this repository** control for automatically generated
  citation formats. The preferred citation in `CITATION.cff` points to the
  manuscript; cite the software package separately only when referring to its
  code, data, or reproducibility materials.

**APA**

> Bessa Rocha da Silva, O. (2026). *Evidence Debt: Modeling the Deferred
> Reconstruction Burden of Missing Operational Evidence in Cloud-Native
> Systems* (Version 1.7.2) [Preprint]. Zenodo.
> https://doi.org/10.5281/zenodo.21845695

**BibTeX**

```bibtex
@techreport{bessa_rocha_da_silva_evidence_debt_2026,
  author  = {Obede Bessa Rocha da Silva},
  title   = {Evidence Debt: Modeling the Deferred Reconstruction Burden of Missing Operational Evidence in Cloud-Native Systems},
  year    = {2026},
  month   = aug,
  version = {1.7.2},
  doi     = {10.5281/zenodo.21845695},
  url     = {https://doi.org/10.5281/zenodo.21845695},
  note    = {Preprint}
}
```

The package contains the complete LaTeX source, a dependency-free simulation,
canonical synthetic outputs, a frozen public-repository observation,
programmatically generated tables, and a field protocol. Version 1.7.2 makes
acceptance independent of ground truth, distinguishes theoretical $ED^*$ from
policy-specific $ED_\rho$, adds an explicit complete-corpus reference arm to field
drills, separates policy abstention from physical irrecoverability, and executes
joint $\lambda/\pi$ sensitivity.

## Evidence boundary

The artifact establishes that the proposed constructs are computable and
discriminating in a seeded synthetic environment. The Argo CD observation
establishes only that missing external issue linkage occurs under a declared
repository schema. It does **not** establish inadequate intent documentation,
temporal decay, production reconstruction cost, or industrial prevalence.

## Repository map

| Path | Purpose |
|---|---|
| `main.tex`, `sections/`, `figs/`, `refs.bib` | Complete manuscript source |
| `code/experiment.py` | Synthetic generator, degradation arms, reconstruction, and aggregation |
| `data/` | Canonical raw/aggregated results, paired path diagnostics, three-channel penalty sensitivity, and generated LaTeX tables |
| `empirical/` | Frozen Argo CD cohorts, strata, manual audit, generated counts, and collector |
| `reviewer2-response.md` | Adversarial review and point-by-point disposition |
| `scripts/verify_artifact.py` | Re-execution and deterministic-result verification |
| `output/pdf/` | Verified compiled manuscript |
| `originais/archive_3/` | Unmodified incoming PDF, source ZIP, and original review memo (local only) |
| `build/latex/` | Local LaTeX intermediates (local only) |
| `qa/renders/` | Page renders and contact sheets used for visual QA (local only) |

## Reproduce the study

Python 3.10 or newer is required; the study uses only the standard library.

```bash
python3 code/experiment.py
```

The run takes roughly 45 seconds on a contemporary laptop. Seeded scientific
outputs are deterministic. The `secs` and `secs_sd` timing fields vary with
the machine and load and are intentionally excluded from exact comparison.

Run the stronger package check with:

```bash
python3 scripts/verify_artifact.py
```

The verifier preserves the canonical outputs in memory, re-executes the study,
and compares all non-timing fields plus the generated tables, including the
exact S/W/N partition, six-value abstention-penalty sensitivity, joint $\lambda/\pi$ grid,
and paired path-survival diagnostic. It also checks the
frozen repository cohorts, strata, grammar tests, manual audit, CSVs, and LaTeX
macros. Live
recollection requires `gh auth login` and is intentionally separate because public
repository state can change.

## Compile the manuscript

With TeX Live:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Tectonic is also supported:

```bash
tectonic -X compile main.tex
```

## Citation and release

Citation metadata is provided in `CITATION.cff`; Zenodo deposit metadata is in
`.zenodo.json`. The version-independent concept DOI is
<https://doi.org/10.5281/zenodo.21841440>; version 1.2.0 is archived at
<https://doi.org/10.5281/zenodo.21843147>; version 1.7.2 is archived at
<https://doi.org/10.5281/zenodo.21845695>.

## License

Code, manuscript source, protocol text, data, and package metadata are released
under the MIT License. Third-party citations remain subject to their original
rights.
