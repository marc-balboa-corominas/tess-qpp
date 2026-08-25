# DR-010 — Manuscript 1 definitive visual package

## Status

Definitive visual-package content freeze candidate. Formal closure requires final Git tag and
byte-exact OSF verification.

## Architecture freeze source

`manuscript1-architecture-v1` at `52024ec3728eeda25f9d640d8f1395a87671c541`.

## Visual scope

Five figures (`M1F01`–`M1F05`) and four tables (`M1T01`–`M1T04`) exactly.

## Five figure decisions

- M1F01: documentary evidence-plane architecture with BAII as a non-result positioning firewall.
- M1F02: F2→F3A continuity of design and change of scale without pooled rates.
- M1F03: F3A baseline gate plus baseline-concordant repeated-measure transitions; no TP/TN/FP/FN.
- M1F04: 156-row independent HELDOUT synthetic selection surface with nine structural no-exposure states preserved as N/E.
- M1F05: 152 selected-TP period-recovery points, visibly conditioned on 152/1800 selected synthetic positives.

## Four table decisions

- M1T01: six evidence planes/truth conditions, BAII explicitly auxiliary non-result.
- M1T02: F3A frozen catalogue/gate/transition/stability/period-comparable counts with interpretive scope.
- M1T03: DEVELOPMENT and HELDOUT synthetic metrics kept split-specific, with only frozen Wilson intervals.
- M1T04: manuscript-facing projection of frozen M1.1 claim boundaries; no new claim is created.

## Rendering-only transformation policy

Allowed transformations are frozen-scope row filtering, deterministic ordering, display pivoting,
unit/label formatting, direct categorical counting already defined by source rows, and visual
composition. No new binning, smoothing, regression, interpolation, confidence interval, estimator,
scientifically meaningful normalization, or cross-plane pooling is allowed.

## Numerical provenance policy

Every scientifically significant rendered number/cell/point is mapped in
`m1_2_rendered_value_audit.csv` to a frozen M1.1 source ID, source artifact, locator and source value.
`STRUCTURAL_NO_EXPOSURE` is not rendered as zero.

## Interpretation firewall

Observational robustness is not observational accuracy. F3A reference mismatches are not physical
falsifications. Zero F3A selection gains are not observational FPR. F3B is synthetic ground-truth
evidence only. Observed HELDOUT FP=0 does not establish population FPR=0. The synthetic selection
function is not an observational population correction. Period recovery is conditional on selection.

## Accessibility / readability policy

PDF is primary; PNG is a 300-dpi preview. Text remains vector in PDF. Figures use grayscale plus
text, marker shape, line style and/or hatching; color-only encoding is forbidden.

## Pre-freeze repair history

- `M1V-TOOL-001`: renderer API compatibility defect, repaired before the first definitive render; scientific effect `NONE`.
- `M1V-VIS-001`: first-candidate M1F04 publication-readability defect, repaired before the second render; scientific/source/claim effects `NONE`.
- `M1V-TOOL-002`: Windows file-lock interruption during rejected-candidate cleanup, recovered before the third render; scientific effect `NONE`.
- `M1V-VIS-002`: second-candidate M1F03/M1F04 readability polish, repaired before the third render; scientific/source/claim effects `NONE`.
- `M1V-VIS-003`: third-candidate M1F04 duplicate-title-layer defect, repaired before the fourth render; scientific/source/claim effects `NONE`.

Rejected visual candidates were never committed or tagged.

## No-new-analysis statement

`new_scientific_computation=false`, `new_statistical_inference=false`,
`new_bibliographic_search=false`, `new_afino_execution=false`,
`new_synthetic_generation=false`, and full manuscript prose remains unstarted.

## Next manuscript task

After final Git/OSF freeze and mentor approval, open Manuscript 1.3 — first complete scientific
draft, beginning with Methods + Results under claim-ID/evidence-plane traceability.
