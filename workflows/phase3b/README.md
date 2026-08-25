# Phase 3B

STATUS:
PHASE 3B CLOSED —
SYNTHETIC HELDOUT CHARACTERIZATION COMPLETE
CORRECTION NOT ESTABLISHED
READY FOR MANUSCRIPT 1

Phase 3B prospectively evaluated the frozen AFINO 0.5 baseline on controlled synthetic ground truth. DEVELOPMENT and independent single-use HELDOUT both show a low-sensitivity, extremely-high-specificity operating profile within the preregistered synthetic domain.

The DEVELOPMENT candidate rule was not promoted because it failed the frozen specificity-preservation gate. The final rule remained `delta_BIC01 > 10 AND delta_BIC21 > 10` with strict greater-than comparisons.

Final HELDOUT: TP=152, FN=1648, TN=1800, FP=0; sensitivity=152/1800=0.08444444444444445; specificity=1800/1800=1.0 with finite-sample Wilson uncertainty; final selection-function rows=156; period-recovery rows=152.

Formal gate: `HELDOUT_BASELINE_CHARACTERIZATION_SUCCESS`. Correction claim: `NOT_ESTABLISHED`.

The HELDOUT is consumed and cannot be reused for threshold or rule development. Phase 3B does not establish observational prevalence, observational sensitivity/specificity/FPR, physical QPP truth, or a validated population correction.

F3B.7 freeze: `phase3b-heldout-validation-v1` / `1a006edbafc05eab5ff9a6f46efbd4e94a074b49`.

F3B.8 closure artifacts live under `workflows/phase3b/closure/`. The next program state is Manuscript 1 evidence→claim→section architecture, not F3B.9.
