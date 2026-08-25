# Manuscript 1 scope contract

## Status

`EVIDENCE_CLAIM_SECTION_ARCHITECTURE_ONLY — MANUSCRIPT PROSE NOT STARTED`

## Scientific thesis

The manuscript evaluates the reproducibility, methodological robustness, numerical behavior,
and synthetic-ground-truth selection properties of the frozen AFINO implementation applied in
the TESS QPP context, progressing from published-event reproduction and synthetic benchmarking
to catalogue-scale observational robustness and independent held-out injection–recovery
validation.

The manuscript architecture deliberately separates five primary evidence planes:

1. F0 observational reproduction;
2. F1 synthetic/numerical benchmark;
3. F2 observational pilot robustness;
4. F3A catalogue-scale observational robustness;
5. F3B synthetic-ground-truth heldout validation.

BAII is an auxiliary positioning and precedence plane, not a sixth result plane.

## Explicit non-claims

This manuscript does not present:

- a validated observational correction;
- observational sensitivity, specificity or FPR;
- real-TESS QPP prevalence;
- physical confirmation or falsification of individual observational QPPs;
- a universal selection function;
- candidate discovery;
- a claim that AFINO is observationally validated;
- a global priority claim unsupported by the frozen BAII scope.

## Interpretation firewall

Observational reproduction is not observational physical truth.
Synthetic ground truth is not observational ground truth.
Classification robustness is not classifier accuracy.
Held-out synthetic performance is not observational validation.
A zero observed HELDOUT false-selection count is not proof of a population FPR of zero.
The F3B synthetic selection function is not a population correction.

## Computation and literature firewall

Manuscript 1.1 performs no AFINO execution, synthetic generation, new statistical inference,
new bibliography search, threshold search, candidate-rule development or scientific
re-analysis. It only binds frozen sources and fixes evidence→claim→section architecture.

No `manuscript.tex`, `main.md`, abstract, introduction or discussion draft is authorized in
Manuscript 1.1.
