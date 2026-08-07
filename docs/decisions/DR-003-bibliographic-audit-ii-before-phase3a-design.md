# DR-003 — Bibliographic Audit II before Phase 3A design freeze

**Date:** 2026-08-07
**Status:** Accepted

## Context

The Phase 3A entry contract requires the observational cohort, perturbation design, outcomes, denominators, and analysis plan to be defined prospectively before scientific execution.

The scientific novelty of the broader project has not yet been frozen as a final claim.

Relevant QPP literature continued to appear during 2025 and 2026, including new TESS catalogue-scale studies and new methodological or review work.

Freezing the F3A design before auditing this literature could produce an unnecessarily redundant cohort design, weaken the manuscript positioning, or overlook a more informative comparison.

## Decision

Bibliographic Audit II is a mandatory pre-design gate for Phase 3A.

The audit must be completed before:

- freezing the final F3A observational cohort;
- freezing the final perturbation grid;
- committing to a catalogue-scale sampling strategy;
- defining a final manuscript novelty claim;
- beginning scientific F3A execution.

Bibliographic reading and source acquisition are permitted during this gate.

The existing Phase 3A entry contract remains valid and is not superseded.

## Audit purpose

Bibliographic Audit II will determine whether the intended F3A/F3B contribution is:

1. materially novel within its specific methodological scope;
2. partially overlapping and in need of repositioning;
3. materially duplicated and in need of redesign; or
4. insufficiently established from the available literature.

## Required comparison axes

The audit must explicitly compare relevant work by:

- observational mission and cadence;
- flare and QPP sample construction;
- QPP detection method;
- temporal-window treatment;
- preprocessing and detrending;
- treatment of gaps and inadmissible inputs;
- optimizer or numerical stability assessment;
- synthetic validation;
- injection-recovery design;
- held-out validation;
- selection effects;
- population inference;
- reproducibility and availability of data/code.

## Gate outcome

The audit must close with one of the following states:

- `NO_MATERIAL_OVERLAP_PROCEED`
- `PARTIAL_OVERLAP_REPOSITION_AND_PROCEED`
- `MATERIAL_OVERLAP_REDESIGN_REQUIRED`
- `INSUFFICIENT_EVIDENCE_AUDIT_REMAINS_OPEN`

Only the first two states authorize progression to the F3A design freeze.

## Non-retroactivity

Bibliographic Audit II may change future design and manuscript positioning.

It must not alter or reinterpret the frozen F0–F2 scientific evidence.