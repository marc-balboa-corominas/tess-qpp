# DR-004 — Phase 3A scientific design freeze

**Status:** Accepted
**Date:** 2026-08-11

## Decision

Freeze Phase 3A design v1 before cohort materialization under the status:

`PHASE3A_SCIENTIFIC_DESIGN_FROZEN_WITH_DOCUMENTED_LIMITATION`

The design resolves the closed Bibliographic Audit II gate
`F3A_DESIGN_RECONSIDERATION_REQUIRED` without modifying the frozen BAII artifacts or the
historical Phase 3A entry contract.

## BAII gate being resolved

BAII.5 established that catalogue-scale TESS QPP studies already overlap directly with the
pre-BAII framing of F3A. The response is not to cancel F3A and not to make a priority claim.
F3A is reframed as a prospective catalogue-scale stress test of independently defined
observational QPP classifications under frozen robustness perturbations.

All ten BAII F3A gate requirements are resolved in `workflows/phase3a/design/gate_resolution_matrix.csv`.

## Scientific role of F3A

F3A is an observational robustness study. It asks whether source classifications survive
prospectively specified changes in temporal window, photometric product, QUALITY policy, simple
detrending, input admissibility, and optimizer seed.

F3A does not establish physical ground truth, sensitivity, specificity, observational FPR,
validation of AFINO, or a corrected procedure.

## Primary catalogue source

`BAIIW0001` / `BAIIV0002` is the sole `PRIMARY_COHORT_SOURCE`.

Its 20-second TESS, Sectors 27–80 source universe supplies the independently defined parent flare
population and primary observational QPP/non-selection roles. The exact event-level table/schema
and native TESS product mapping must be physically verified in F3A.2. If that provenance cannot
be established, materialization is blocked and a versioned design amendment is required; no
automatic catalogue substitution is permitted.

BAIIW0003 is retained as a secondary external-label/reference source when deterministic
cross-matching is possible, not as the primary cohort.

## Cohort strategy

Use all unique source QPP-reference events and select a deterministic 1:1 matched sample, without
replacement, from source non-selected flares. Matching is frozen before scientific execution and
uses TIC/sector priority followed by nearest log duration and canonical-key tie-breaking.

Membership is never rewritten because an event is later inadmissible, numerically incomplete, or
baseline-discordant.

## Primary robustness matrix

Freeze exactly the F2 family:

- 13 temporal-window variants: `W00`, `WSm2`, `WSm1`, `WSp1`, `WSp2`, `WEm2`, `WEm1`, `WEp1`,
  `WEp2`, `WX1`, `WC1`, `WX2`, `WC2`;
- 6 processing profiles: `P00`–`P05`;
- 78 primary cells per event;
- external optimizer seed 0 for every primary cell.

The reuse is deliberate and explicit: F3A tests whether the F2 robustness pattern generalizes at
catalogue scale. BAII comparator methods do not enter the 78-cell matrix.

## Comparator strategy

All 11 BAII comparator candidates are resolved prospectively. Design v1 implements none as a
secondary scientific execution. Direct QPP or upstream processing comparators that only bound the
literature are citation/positioning items; methods requiring training, known truth,
injection-recovery, or selection-function evaluation are deferred to F3B.

A future implementation requires a versioned pre-result amendment.

## Numerical strategy

The primary 78-cell matrix uses seed 0 only. Numerical stability is a separate analysis at
`W00/P00` with external optimizer seeds 0–9 for every event whose W00/P00 input is eligible.

Required diagnostics include classification discordance, BIC ranges, formal M1 period range,
unique parameter payloads, warnings, bounds, and convergence status. Stable classification is
not evidence of a unique numerical optimum.

## Interpretation boundaries

Permitted framing:

> F3A evaluates the catalogue-scale robustness of independently defined observational QPP
> classifications under prospectively specified perturbations.

Prohibited claims include priority statements, observational validation of AFINO, physical QPP
truth, accuracy/sensitivity/specificity, observational FPR, or correction validation.

## Consequences

- F0–F2 remain frozen.
- Bibliographic Audit II remains frozen.
- `workflows/phase3a/ENTRY_CONTRACT.md` remains unchanged.
- `workflows/phase3a/FROZEN_INPUTS.json` remains unchanged.
- F3B remains unchanged.
- No F3A cohort is materialized by this decision.
- No TESS light curve is opened and no AFINO execution is authorized by F3A.1.

## What remains for F3B

Known-truth injection-recovery, selection-function performance, model/classifier training,
correction development, and independent held-out validation remain Phase 3B responsibilities.

## Next task

F3A.2 will deterministically materialize the frozen cohort, verify source and TESS provenance,
resolve admissibility inputs, and freeze the exact execution plan before any AFINO scientific
execution.
