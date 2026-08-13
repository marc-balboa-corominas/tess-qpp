# DR-005 — Phase 3A closure and F3B entry

**Status:** Accepted  
**Date:** 2026-08-13

## Decision

`PHASE3A_COMPLETE_PROCEED_TO_F3B_WITH_LIMITATIONS`

## F2→F3A continuity

The frozen 13×6 observational robustness experiment scales from the 10-event F2
pilot to the 122-event F3A catalogue cohort. Both phases preserve inadmissibility
as a separate outcome, show baseline-relative QPP-reference selection losses,
and show seed-stable binary classification in their frozen optimizer scopes.

## F3A baseline-reproduction limitation

F3A baseline reproduction is 65 concordant, 51 mismatch and 6 inadmissible. All
51 mismatches are in `PUBLISHED_QPP_REFERENCE`: 8 concordant / 51 mismatch / 2
inadmissible. The mismatch is against the frozen observational reference state;
its cause is `UNRESOLVED_WITHIN_F3A` and it is not evidence of 51 false QPPs.

## Robustness conclusion

Among baseline-concordant transition-eligible rows, F3A contains 295
`SELECTED_RETAINED`, 171 `SELECTION_LOST`, 3,178 `NOT_SELECTED_RETAINED` and 0
`SELECTION_GAINED`. Zero gains do not establish observational FPR=0.

## Numerical conclusion

116/116 W00/P00 input-eligible events retain binary classification across seeds
0–9, while each event has 10 parameter payloads for M0/M1/M2 and convergence
remains `NOT_AUDITABLE`. Stable classification does not establish a unique optimum.

## Period conclusion

Period robustness is conditional on retained selection and contains 295
selected→selected comparable rows.

## What F3A establishes

Catalogue-scale descriptive evidence of classification sensitivity to frozen
methodological perturbations, explicit input-admissibility limits, seed-stable
binary decisions in the frozen stability plane, and conditional period robustness.

## What F3A does not establish

Ground truth, physical QPP truth, observational validation of AFINO, sensitivity,
specificity, observational FPR, a validated correction, a selection function or
candidate-discovery performance.

## Manuscript 1 status

The robustness component is supported with explicit limitations. The
validation/correction component remains incomplete.

## Why F3B is required

F3B must introduce known ground truth, frozen injection–recovery domain,
development/held-out separation, prospective metrics and a final rule frozen
before held-out access.

## Next task

F3B.1 — preregister injection–recovery, development/held-out split and validation
architecture before generating a single injection.
