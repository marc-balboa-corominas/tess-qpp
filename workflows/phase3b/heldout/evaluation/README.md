# Phase 3B.7 — Single-use HELDOUT evaluation

This directory is the prospective single-use unblinding and final HELDOUT evaluation boundary.

Before any HELDOUT truth content is read:

1. the F3B.6 blind execution freeze must resolve to commit `7776676aab1e4d2922902f4046495500864f7ca1`;
2. the final rule must remain `FINAL_RULE_FREEZE_BASELINE_ONLY`, with strict `delta_BIC01 > 10 AND delta_BIC21 > 10`;
3. `evaluate_f3b_heldout.py` must reproduce the frozen DEVELOPMENT evaluator outputs;
4. the binding, authorization, evaluator, validator and test must be committed under `ops(phase3b): freeze single-use heldout unblinding procedure`.

The authorization permits truth joining and the preregistered HELDOUT metrics only after that procedure-freeze commit. It prohibits new AFINO execution, generator execution, candidate search, threshold mutation, rule refitting, DEVELOPMENT retuning and HELDOUT optimizer-stability reruns.

When the authorized HELDOUT evaluation starts, a runtime single-use consumption marker is created before the first truth-content read. The same HELDOUT cannot be reused for rule development after this point.

The formal branch is `BASELINE_ONLY`. Complete characterization can pass regardless of numerical performance; the correction claim remains `NOT_ESTABLISHED`.
