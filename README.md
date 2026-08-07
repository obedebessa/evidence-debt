# Evidence Debt

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21842021.svg)](https://doi.org/10.5281/zenodo.21842021)

Reproducibility package for the manuscript:

> **Evidence Debt: Measuring the Accumulated Cost of Missing Operational
> Evidence in Cloud-Native Systems**  
> Obede Bessa Rocha da Silva — Independent Researcher

The package contains the complete LaTeX source, a dependency-free simulation,
canonical synthetic outputs, a frozen public-repository census, programmatically
generated tables, and a field protocol. Version 1.1.0 adds the bounded Argo CD
observation and an explicit economic-accounting chain.

## Evidence boundary

The artifact establishes that the proposed constructs are computable and
discriminating in a seeded synthetic environment. The Argo CD census establishes
only that a declared intent-link deficit occurs in public repository evidence. It
does **not** report production reconstruction costs, an industrial case study, or
external replication.

## Repository map

| Path | Purpose |
|---|---|
| `main.tex`, `sections/`, `figs/`, `refs.bib` | Complete manuscript source |
| `code/experiment.py` | Synthetic generator, degradation arms, reconstruction, and aggregation |
| `data/` | Canonical raw/aggregated results and generated LaTeX tables |
| `empirical/` | Frozen Argo CD sample, generated counts, and collector |
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

The run takes roughly 30 seconds on a contemporary laptop. Seeded scientific
outputs are deterministic. The `secs` and `secs_sd` timing fields vary with
the machine and load and are intentionally excluded from exact comparison.

Run the stronger package check with:

```bash
python3 scripts/verify_artifact.py
```

The verifier preserves the canonical outputs in memory, re-executes the study,
and compares all non-timing fields plus the generated table. It also checks that
the frozen repository snapshot, CSV summary, and LaTeX macros agree. Live
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
`.zenodo.json`. Version 1.1.0 is archived at
<https://doi.org/10.5281/zenodo.21842021>; the version-independent concept DOI is
<https://doi.org/10.5281/zenodo.21841440>.

## License

Code, manuscript source, protocol text, data, and package metadata are released
under the MIT License. Third-party citations remain subject to their original
rights.
