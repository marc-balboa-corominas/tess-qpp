# DR-007 — Phase 3B DEVELOPMENT gate and final rule

- Status: Accepted
- Phase: F3B.4
- Decision: Retain the AFINO 0.5 baseline rule for HELDOUT
- Final rule: `delta_BIC01 > 10 AND delta_BIC21 > 10`
- Comparator: strict greater-than
- Candidate promoted: no
- Correction claim: `NOT_ESTABLISHED`

## Context

Phase 3B.4 used the frozen DEVELOPMENT synthetic-ground-truth
population to characterize the baseline AFINO 0.5 rule and, if
justified by the preregistered promotion gate, permit one
two-threshold BIC candidate to replace it.

The one-shot candidate family was restricted to:

`delta_BIC01 > t01 AND delta_BIC21 > t21`

Truth was used only as the objective/evaluation target. The inference
features were exactly `delta_BIC01` and `delta_BIC21`. True period,
QPP fraction, red-noise exponent, challenge state and optimizer
stability diagnostics were not candidate-rule features.

## DEVELOPMENT result

The baseline balanced accuracy was 0.5394444444444445.

The one-shot DEVELOPMENT optimum was:

- t01 = -7.517054630023225
- t21 = -4.4514075428899105
- balanced accuracy = 0.635
- balanced-accuracy improvement = 0.0955555555555555

The candidate improved DEVELOPMENT sensitivity substantially but
reduced specificity substantially.

## Frozen promotion decision

All four preregistered criteria were mandatory.

The candidate passed:

1. point balanced-accuracy improvement >= 0.025;
2. lower 95% paired-bootstrap bound for delta balanced accuracy > 0;
3. lower bound for delta sensitivity > -0.025.

It failed:

4. lower bound for delta specificity > -0.025.

The promotion result was therefore 3/4 and the candidate was not
promoted.

## Decision

Retain the original AFINO 0.5 baseline:

`delta_BIC01 > 10 AND delta_BIC21 > 10`

No runner-up rescue, alternate candidate search, post-hoc threshold
change, post-hoc binning change or comparator change is permitted.

## Consequences

The baseline 10/10 rule is the only rule permitted to proceed to
single-use HELDOUT validation.

HELDOUT cannot be used to tune or reconsider this decision. A HELDOUT
failure may affect scientific conclusions about the frozen rule, but
cannot reopen DEVELOPMENT optimization.

All F3B.4 performance values remain DEVELOPMENT
synthetic-ground-truth results and are not observational validation.

The permanent validator and regression tests must pass before the
formal F3B.4 Git/tag freeze.

The tag `phase3b-final-rule-v1` must exist before any HELDOUT
stochastic byte is generated.


### Explicit promotion outcome

The candidate was not promoted: it passed 3/4 preregistered promotion criteria, with C4 failing because the lower 95% paired-bootstrap confidence bound for the candidate-minus-baseline specificity difference was below the permitted threshold. Consequently, the frozen final rule remains the AFINO 0.5 baseline, `delta_BIC01 > 10 AND delta_BIC21 > 10`; runner-up rescue and alternate candidate search remain forbidden.
