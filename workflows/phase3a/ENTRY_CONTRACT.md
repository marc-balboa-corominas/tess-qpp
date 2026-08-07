# Phase 3A Entry Contract

**Contract ID:** `PHASE3A_ENTRY_FROM_F2_6_V1`

**Status:** `ENTRY_CONTRACT_ESTABLISHED_DESIGN_NOT_YET_FROZEN`

## Purpose

Phase 3A extends the observational robustness question from the frozen ten-event F2 pilot to a prospectively defined catalogue-scale cohort.

This contract defines what Phase 3A inherits from F2 and what it is not allowed to claim.

It does not yet define the final F3A cohort, perturbation grid, execution plan, statistical analysis, or success criteria.

Those elements must be frozen in subsequent preregistration artifacts before scientific execution.

## Frozen scientific inheritance

Phase 3A inherits the following principles from F0–F2:

1. Observational baseline reproduction, synthetic ground truth, numerical diagnostics, observational robustness, and physical interpretation are distinct evidence planes.

2. Input inadmissibility is not equivalent to non-selection.

3. Classification robustness must be evaluated separately from numerical optimizer behaviour.

4. Period analysis is conditional on retained selection unless a separately justified outcome definition is prospectively established.

5. Stable classification across optimizer seeds does not demonstrate a unique numerical optimum.

6. Warnings, parameter bounds, convergence limitations, and numerical multiplicity remain reportable diagnostics and must not be silently discarded.

7. The effective frozen AFINO 0.5 temporal convention must be respected and explicitly documented.

8. F2 observations are historical evidence and may motivate F3 design, but F2 may not be relabelled as independent confirmatory validation of a procedure developed after seeing F2.

## Phase 3A scientific role

Phase 3A is a catalogue-scale observational robustness study.

Its purpose is to determine whether the dependence on admissibility, temporal window, processing choices, classification stability, period stability, and numerical diagnostics observed in F2 persists or changes in a broader prospectively defined observational cohort.

## Required prospective design

Before running the F3A scientific execution, the following must be explicitly defined and frozen:

- source catalogue or catalogues;
- event eligibility criteria;
- cohort construction procedure;
- inclusion and exclusion rules;
- handling of duplicates and repeated observations;
- observational roles or strata;
- baseline reconstruction rule;
- admissibility contract;
- temporal-window perturbations;
- processing profiles;
- optimizer-seed policy;
- primary and secondary outcomes;
- denominators for every reported quantity;
- period-analysis eligibility;
- missingness and failed-execution handling;
- numerical diagnostic fields;
- analysis plan;
- multiplicity policy where applicable;
- planned tables and figures or their selection rules.

The exact F2 perturbation design must not be inherited silently.

F2 may motivate F3A choices, but all F3A choices must be made explicit before execution.

## Candidate discovery

Candidate discovery is not authorized by this entry contract.

If Phase 3A uses QPP-labelled or comparison events, their provenance and selection rules must be defined independently of the F3A output being evaluated.

Any future discovery program requires its own prospective scientific contract.

## Prohibited Phase 3A interpretations

Phase 3A alone must not be used to claim:

- observational validation of AFINO;
- physical truth of QPP labels;
- sensitivity or specificity;
- observational false-positive rate;
- that comparison objects are true negatives;
- validation of a corrected procedure;
- unique optimizer convergence;
- causal attribution of classification changes to warnings, bounds, processing steps, or window changes without a design that identifies such causality.

## Relation to Phase 3B

Questions requiring known truth, correction development, recovery performance, or confirmatory validation belong to Phase 3B.

Phase 3B must maintain explicit separation between development data and held-out validation data.

A corrective rule cannot be declared validated merely because it performs favourably on F2 or on data used to design it.

## Gate to F3A execution

Scientific F3A execution is prohibited until a subsequent design package has frozen the cohort, input contract, perturbation grid, outcomes, denominators, execution plan, and analysis plan.

Current status:

`PHASE3A_ENTRY_CONTRACT_ESTABLISHED_DESIGN_NOT_YET_FROZEN`