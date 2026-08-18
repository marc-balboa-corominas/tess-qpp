# DR-006 — Phase 3B validation design freeze

**Status:** Accepted
**Date:** 2026-08-18

## F3A entry decision

Phase 3A closed with
`PHASE3A_COMPLETE_PROCEED_TO_F3B_WITH_LIMITATIONS`.
The authoritative predecessor is `phase3a-complete-v2` at commit
`1f3b1cc21286c25dea6a0e5779c0dc18edd81933`.
Its observational evidence does not establish physical QPP truth,
sensitivity, specificity, observational FPR or a correction.

## Scientific role of F3B

F3B moves the validation problem to prospectively generated data with known
synthetic truth. Its primary purpose is to characterize the frozen AFINO 0.5
selection procedure over a bounded synthetic domain. Development of a
correction rule is permitted but not mandatory.

## Ground-truth strategy

Truth states are `SYNTHETIC_QPP_PRESENT` and `SYNTHETIC_QPP_ABSENT`.
Observational labels are not truth. Real observational backgrounds are not
primary synthetic null truth. F2/F3A events are not independent held-out data.

## Simulation domain

Primary AFINO period support is 40–300 s with at least three cycles in the
window. The primary generator continues the validated F1 stationary
envelope-modulated sinusoid, asymmetric flare and power-law-noise construction
at 20-s cadence, with prospectively frozen sampling lengths, signal strengths
and noise slopes. Gap/quality challenges remain a secondary admissibility
plane.

## DEVELOPMENT/HELDOUT architecture

The split unit is `background_realization_id`. There are 1,800 background
realizations in DEVELOPMENT and 1,800 disjoint backgrounds in HELDOUT,
stratified over 36 designated cells. Positive and null series sharing a
background remain in the same split.

## Held-out non-access policy

HELDOUT identities are frozen but its stochastic realizations and flux series
do not exist at F3B.1 freeze. Generation is allowed only after
`FINAL_RULE_FREEZE`. HELDOUT is single-use; no tuning or second attempt on the
same held-out is allowed after failure.

## Metrics

Primary classifier metrics among eligible known-truth series are sensitivity,
specificity and FPR with explicit numerators, denominators and Wilson
intervals. Input inadmissibility and end-to-end recovery are reported
separately. Period recovery is a separate evidence plane.

## Selection-function strategy

The primary representation is `STRATIFIED_EMPIRICAL`, separately estimating
input eligibility, conditional selection and end-to-end selection. No
post-hoc fitted selection model may replace this primary representation.

## Correction-rule policy

AFINO 0.5 at commit `6aceac9518fc8056052807e666da9d0c8bebb010`,
with both BIC improvements greater than 10, remains the mandatory baseline.
Any candidate is DEVELOPMENT-only and restricted to a two-threshold
conjunction on `delta_BIC01` and `delta_BIC21`. A correction is not mandatory.
If no candidate passes its promotion gate, the baseline alone proceeds and the
correction claim remains `NOT_ESTABLISHED`.

## Comparator strategy

The six BAII/F3A.1 `DEFER_TO_F3B` comparators are resolved prospectively.
Four are `CITATION_ONLY` and two are
`UNAVAILABLE_WITH_DOCUMENTED_REASON`. No external comparator is executed in
DEVELOPMENT or HELDOUT in F3B v1.

## Success/failure gates

Baseline characterization, candidate-rule promotion and held-out validation
are separate gates. A failed DEVELOPMENT candidate is
`NOT_PROMOTED_TO_HELDOUT`. A failed held-out candidate is
`HELDOUT_VALIDATION_FAILED` and cannot be modified and retested on the same
held-out set.

## What remains prohibited

Before the appropriate future gate: no synthetic HELDOUT generation, no
held-out access, no rule tuning with held-out information, no observational
ground-truth claim, no observational sensitivity/specificity/FPR claim, no
retrospective feature addition, no same-heldout retry, and no interpretation
of optimizer-seed stability as proof of a unique optimum.

## Next task

After the F3B.1 freeze is independently validated, committed, tagged and
archived, proceed to **F3B.2 — implementation and validation of the generator
plus materialization of DEVELOPMENT only. HELDOUT remains ungenerated.**
