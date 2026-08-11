# Phase 3A scientific protocol — catalogue-scale observational robustness

**Study:** `TESS_QPP_PHASE3A_CATALOGUE_ROBUSTNESS_V1`
**Status:** `PHASE3A_SCIENTIFIC_DESIGN_FROZEN_WITH_DOCUMENTED_LIMITATION`
**Design date:** 2026-08-11

## Scientific role after Bibliographic Audit II

Bibliographic Audit II closed with `F3A_DESIGN_RECONSIDERATION_REQUIRED`. That gate does not cancel
Phase 3A. It changes the question that Phase 3A is allowed to claim. Catalogue-scale TESS QPP
catalogues and classification studies already exist in the audited literature, so catalogue size,
TESS usage, or QPP classification alone cannot define the contribution. F3A is instead frozen as a
prospective catalogue-scale stress test of independently defined observational QPP reference
classifications. The stress test asks whether classifications and selected periods remain stable
when the temporal window, photometric product, QUALITY treatment, simple detrending, input
admissibility, and optimizer seed are varied under a protocol specified before F3A results exist.

This remains an observational robustness study. It is not an observational validation of AFINO,
does not establish physical QPP truth, sensitivity, specificity, an observational false-positive
rate, or a corrected detector. Those questions require known truth or independent validation and
remain reserved for Phase 3B.

## Difference from the catalogue-scale literature

BAIIW0001 is selected as the primary cohort source. BAII records it as a 20-second-cadence TESS
flare survey over Sectors 27–80 with an AFINO-based QPP classification. BAIIW0003 is a separate
catalogue-scale TESS QPP study using a different cadence and an FCN-based classification. F3A does
not reproduce either paper as a new catalogue. It freezes BAIIW0001 as an external source of the
parent flare universe and primary observational labels, then applies a project-defined robustness
matrix to those already defined labels. BAIIW0003 can only provide a separately provenanced
external-label annotation when deterministic cross-matching is possible.

The distinction is therefore question-based, not a priority claim. F3A evaluates robustness of
pre-existing observational classifications under perturbations. It does not claim to be the first
catalogue-scale TESS QPP analysis, the first TESS QPP catalogue, or the first study of methodological
robustness.

## Primary catalogue and cohort strategy

The sole primary source is BAIIW0001/BAIIV0002. The source identity is frozen now. F3A.2 must
locate and checksum the exact event-level catalogue representation and establish deterministic
event identifiers, timing markers, and archive-product mappings before any light curve is opened
for scientific analysis. BAII establishes paper-level population counts and labels but did not
freeze the machine-readable event schema. This is a documented implementation limitation rather
than an open scientific choice. If the required event-level provenance cannot be established,
materialization is blocked and the design must be versioned; another catalogue is not substituted
automatically.

The reference stratum contains every unique source event already QPP-selected by BAIIW0001. The
comparison stratum is drawn only from source flares not selected as QPP by that same source
procedure. These are observational roles, not positive and negative physical truth. One comparison
event is selected without replacement for each reference event. Reference events are processed in
ascending canonical source key. Controls are matched deterministically using a fixed hierarchy:
same TIC and sector, same TIC, same sector, then the global source pool; within each level, nearest
log flare duration is chosen and canonical event key breaks ties. No failed or inadmissible event is
replaced after materialization.

Exact duplicate source rows collapse to one canonical event with all provenance retained. Separate
flares on the same star remain separate events, and repeated sectors are distinct because sector is
part of the event key. No additional stellar-class filter is added. Candidate discovery is false:
F3A cannot add QPP events because an F3A result looks interesting.

## Reference labels and baseline reproduction

The primary reference roles are `PUBLISHED_QPP_REFERENCE` and
`PUBLISHED_NOT_SELECTED_REFERENCE`. The latter means only that the source method did not select the
flare as QPP; it is not a true negative. Other published classifiers retain independent provenance
under `OTHER_EXTERNAL_CLASSIFIER_REFERENCE`. A deterministic cross-match with a conflicting label
is marked `REFERENCE_LABEL_CONFLICT`; F3A output is never used to resolve the conflict.

Before any robustness transition is interpreted, each event passes a baseline reproduction gate at
`W00/P00/seed0`. The project uses the frozen F0–F2 AFINO execution contract: M0 `pow_const`, M1
`pow_const_gauss`, M2 `bpow_const`, low-frequency cutoff 1/40 Hz, and selection only when both
`BIC_M0-BIC_M1` and `BIC_M2-BIC_M1` exceed 10. A baseline result matching the source role is
`REFERENCE_CONCORDANT`. An evaluable disagreement is `REFERENCE_BASELINE_MISMATCH`; it remains in
the audit trail and is not forced to agree. Inadmissible or numerically incomplete baselines remain
separate states. Robustness summaries that require a reproduced baseline use only
`REFERENCE_CONCORDANT` events.

## Primary robustness matrix

The primary matrix deliberately reuses the full F2 family: thirteen temporal windows crossed with
six processing profiles, yielding exactly 78 cells per planned event, all at external optimizer
seed 0. This is not silent inheritance. The reason for exact reuse is to test whether the
robustness pattern observed in the frozen F2 pilot persists at larger scale without changing the
perturbation family after observing catalogue results.

The windows are W00, four start-boundary shifts, four end-boundary shifts, and four symmetric
extensions/contractions by one or two cadences. The profiles are P00–P05: PDCSAP or SAP, either
finite-only or native QUALITY==0 filtering where specified, and the two prespecified
linear-residual-plus-one detrending profiles. No interpolation or gap filling is introduced.
Methods identified by BAII do not become extra cells in this matrix.

## Admissibility, QUALITY, and gaps

Input inadmissibility is not non-selection. The F2 technical contract is retained: the requested
product must exist; source windows must map inside the native light curve; the source peak must
remain in the perturbed window and survive filtering; at least 15 cadences must remain; times must
be finite, strictly increasing, duplicate-free and based on consecutive retained native indices;
the maximum cadence deviation from the median must be at most 1e-3 seconds; flux must be finite;
and any frozen detrending must succeed. Interpolation, gap filling, or reindexing to hide gaps is
forbidden.

Scientific output states keep `INPUT_INADMISSIBLE`, `INCOMPLETE_NUMERICAL`, and
`REFERENCE_BASELINE_MISMATCH` separate from selected/not-selected transitions. Every reported
fraction carries its planned and eligible denominator, so an apparently stable result cannot be
created by silently discarding hard cases.

## Classification, period, and robustness outcomes

For a reference-concordant baseline, classification transitions are
`SELECTED_RETAINED`, `SELECTION_LOST`, `NOT_SELECTED_RETAINED`, and `SELECTION_GAINED`.
Inadmissibility, numerical incompleteness, and baseline mismatch remain explicit additional states.

Period change is defined only when the baseline is selected, the variant is selected, and both
selected M1 periods are available. A formal M1 centre from a non-selected fit can be retained as a
numerical diagnostic but is not a recovered QPP period. F3A may report the
classification-concordance fraction among eligible cells, with its denominator, but no frozen
threshold converts that fraction into a binary robust/not-robust label. Accuracy, sensitivity,
specificity, observational FPR, and physical truth are prohibited outputs.

The analysis is descriptive and complete rather than result-selected. The planned outputs include
the cohort/provenance flow, all-cell transition and eligibility tables, marginal window/profile
summaries, conditional period-change summaries, complete 13×6 heatmaps, and numerical diagnostics.
No inferential p-value family is preregistered; consequently no significance-based multiplicity
procedure or data-driven choice of favourable cells is authorized.

## Numerical stability

Numerical stability is a separate evidence plane. The 78-cell matrix uses seed 0 only. Every cohort
event with eligible W00/P00 input is additionally evaluated at W00/P00 with external optimizer
seeds 0 through 9. The audit records classification discordance, all three BICs and selection
margins, formal M1 period range, unique parameter payloads, warnings, parameter-bound hits,
convergence status, and incomplete executions. Seed stability does not demonstrate a unique
numerical optimum, and F3A cannot claim optimizer uniqueness.

## BAII comparators

All eleven BAII comparator candidates are resolved prospectively. None is inserted into the
primary 78-cell matrix in design v1. Wavelet QPP detection and several upstream flare-detection or
processing approaches are retained for citation and positioning where they clarify methodological
scope. Methods whose value is primarily injection-recovery, known-truth performance, retraining,
or selection-function characterization are deferred to F3B. This is not a judgment that those
methods are inferior; it prevents F3A from expanding into a second method-development study after
the BAII gate.

A future secondary implementation would require a versioned design amendment before its outputs
are inspected. The present F3A freeze therefore contains no opportunistic comparator adoption.

## Interpretation boundaries and next gate

Permitted framing is: “F3A evaluates the catalogue-scale robustness of independently defined
observational QPP classifications under prospectively specified perturbations.” Prohibited framing
includes “first catalogue-scale TESS QPP study”, “first TESS QPP catalogue”, “first QPP
injection-recovery study”, “first study of methodological robustness”, or “AFINO validated
observationally”. F3A is also not a correction of AFINO.

F3A.1 ends before cohort materialization. F3A.2 must verify the exact primary-source event table,
provenance keys, timing markers, TESS product mapping and admissibility inputs, then freeze the
materialized cohort and exact execution plan. No scientific result from F3A may be inspected before
that next freeze. If the event-level source contract cannot be satisfied, execution is blocked and
a versioned scientific-design amendment is required.
