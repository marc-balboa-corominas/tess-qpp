# Phase 3B.4 — DEVELOPMENT analysis

STATUS:
PHASE3B_DEVELOPMENT_CHARACTERIZED_FINAL_RULE_FROZEN_BASELINE_ONLY

This directory contains the frozen Phase 3B.4 DEVELOPMENT-only
synthetic-ground-truth characterization and the exact rule selected
for later HELDOUT evaluation.

## Scientific boundary

The classifier population is exactly 3,600 eligible primary
BASELINE/seed-0 series: 1,800 synthetic-positive and 1,800
synthetic-null observations.

Challenge series are input-admissibility evidence only and are not
re-coded as FN/TN. Numerical-stability extra seeds are diagnostics
only and are not independent classifier observations.

Reported sensitivity, specificity, FPR, balanced accuracy, selection
function and period-recovery quantities are DEVELOPMENT
synthetic-ground-truth results. They are not observational
performance estimates and are not final HELDOUT validation.

## Final rule

The one-shot DEVELOPMENT candidate was not promoted because the frozen
four-part promotion gate passed 3/4 criteria and failed the lower
specificity-difference criterion.

The final frozen rule is therefore the AFINO 0.5 baseline:

`delta_BIC01 > 10 AND delta_BIC21 > 10`

with strict greater-than semantics.

Threshold mutation, runner-up rescue and alternate candidate search
after freeze are forbidden.

## Reproducibility

`validate_f3b4_development_analysis.py` independently reconstructs the
baseline confusion matrix, Wilson intervals, end-to-end separation,
selection-function topology, period recovery, numerical stability,
candidate feature/axis contract, fixed paired PCG64 bootstrap,
promotion decision and final-rule freeze.

`test_f3b4_development_analysis.py` provides the permanent regression
suite for these contracts.

`SHA256SUMS.txt` binds all F3B.4 closure artifacts except itself.

## HELDOUT firewall

At F3B.4 closure, HELDOUT has not been generated, materialized,
accessed or used for rule selection.

No HELDOUT stochastic bytes may be generated until the complete F3B.4
closure is independently validated, committed, tagged as
`phase3b-final-rule-v1`, pushed and remotely verified.

Any subsequent HELDOUT evaluation must use the frozen 10/10 rule
without tuning or return to DEVELOPMENT for rule mutation.
