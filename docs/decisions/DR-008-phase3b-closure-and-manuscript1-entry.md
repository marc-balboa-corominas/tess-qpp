# DR-008 — Phase 3B closure and Manuscript 1 entry

## Status

Accepted for closure candidate validation.

## Context

Phase 3B was designed to characterize the frozen AFINO 0.5 rule on controlled synthetic ground truth while preserving a strict DEVELOPMENT / single-use HELDOUT boundary. The DEVELOPMENT candidate improved sensitivity but failed the preregistered specificity-preservation criterion C4. It was not promoted, no runner-up rescue was permitted, and the final pre-HELDOUT rule remained `delta_BIC01 > 10 AND delta_BIC21 > 10`.

The blinded HELDOUT decisions were frozen before truth access. F3B.7 then consumed HELDOUT once for the authorized truth join and baseline characterization.

## Decision

Close Phase 3B with `PHASE3B_COMPLETE_HELDOUT_BASELINE_CHARACTERIZED_CORRECTION_NOT_ESTABLISHED_PROCEED_TO_MANUSCRIPT1`. HELDOUT yielded 152 TP, 1648 FN, 1800 TN and 0 FP on 1800 synthetic positives and 1800 synthetic nulls. Zero observed false selections retains finite-sample Wilson uncertainty and is not proof of population FPR=0.

The final selection surface is the 156-row F3B.7 HELDOUT `STRATIFIED_EMPIRICAL` table, adopted without DEVELOPMENT pooling, smoothing or a new probabilistic fit. It is valid for the frozen synthetic domain only. Correction remains `NOT_ESTABLISHED`.

## Consequences

Phase 3B supports controlled synthetic-ground-truth performance claims, the candidate rejection, the frozen 10/10 baseline, independent HELDOUT selection behavior and conditional period-recovery results. It does not support observational prevalence, observational PPV/sensitivity/specificity/FPR, physical QPP truth, unqualified observational validation of AFINO, or a validated TESS population correction.

The consumed HELDOUT is permanently closed to new threshold/rule development. Population transport is F4+. F0 observational reproduction, F1 synthetic/numerical benchmarking, F2 observational pilot robustness, F3A catalogue-scale observational robustness and F3B synthetic ground-truth validation must remain separate evidence planes in Manuscript 1.

F3B.8 performs zero AFINO calls, zero generator calls, no new stochastic draw, no threshold mutation, no candidate search, no rule refit, no DEVELOPMENT retuning and no new inferential test. The original F3B.5 truth ledger is not reopened.

After `PHASE3B_CLOSURE_VALIDATION_PASS` and Git/OSF freeze, the next step is Manuscript 1 evidence→claim→section architecture, not F3B.9.
