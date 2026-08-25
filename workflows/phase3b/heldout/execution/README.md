# Phase 3B.6 ? HELDOUT blind single-use execution

This directory freezes the blind HELDOUT execution boundary before truth unblinding.

## Scientific boundary

- 3,600 HELDOUT decisions.
- 10,800 AFINO calls: M0/M1/M2 once per decision.
- AFINO 0.5 at the frozen source commit.
- Frozen BASELINE rule: `delta_BIC01 > 10 AND delta_BIC21 > 10`.
- Blind decisions are frozen row by row.
- The aggregate number or fraction selected is deliberately not reported.
- Ground truth is not joined in F3B.6.
- Performance metrics, selection-function analysis and period-recovery evaluation are deferred to F3B.7.

## Execution sequence

`3000 + 3000 + 3000 + 1800 + 0`

The final zero-new-job invocation demonstrates idempotence after all 10,800 jobs were checkpointed.

## Validation

Required independent result:

`PHASE3B_HELDOUT_BLINDED_EXECUTION_VALIDATION_PASS`

The validation audit records 10,800/10,800 `OK`, 3,600/3,600 `VALID`, zero identity/recalculation/temporal mismatches, DEVELOPMENT regression 18/18 exact, and the blinding firewall.

## Important files

- `config/`: frozen execution binding and single-use authorization.
- `evidence/tables/f3b6_heldout_results_blinded.csv`: 10,800 blind model outputs.
- `evidence/tables/f3b6_heldout_decisions_blinded.csv`: 3,600 frozen blind decisions.
- `evidence/tables/f3b6_temporal_contract_diagnostic.csv`: independent temporal-contract diagnostic.
- `evidence/reports/`: environment, validation, single-use boundary, execution audit and report.
- `evidence/f3b6_SHA256SUMS.txt`: byte-level integrity registry.

The completed SQLite checkpoint remains outside Git at `runtime/phase3b/f3b6/`. It is intended for the archival snapshot rather than the Git commit.

Do not join the F3B.5 truth ledger to these artifacts until the F3B.6 Git freeze, remote verification and archival snapshot are complete.
