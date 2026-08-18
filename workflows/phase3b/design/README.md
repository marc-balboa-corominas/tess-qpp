# F3B.1 validation design

STATUS:
PHASE3B_VALIDATION_DESIGN_FROZEN_BEFORE_ANY_INJECTION

The design defines known synthetic truth, a bounded primary simulation domain,
a single generator shared by DEVELOPMENT and HELDOUT, deterministic split
identities, sample size, input-admissibility handling, metrics, empirical
selection-function estimation, period-recovery handling, the mandatory AFINO
0.5 baseline, an optional restricted correction-rule family, six resolved
BAII/F3A.1 deferred comparators, a separate numerical-stability plane and
prospective success/failure gates.

Execution state:
- injections generated: false
- AFINO executed: false
- DEVELOPMENT generated: false
- HELDOUT generated: false
- HELDOUT accessed: false
- candidate rule frozen: false
- correction claim established: false
- scientific results computed: false

`f3b1_split_registry.csv` freezes identities and assignments only; it does not
contain realized stochastic noise, periods, phases or synthetic flux arrays.

HELDOUT is single-use and may be generated only after `FINAL_RULE_FREEZE`.
F2/F3A observations are not held-out truth.

No protected historical scope is modified by F3B.1.
