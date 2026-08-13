# Phase 3A

Catalogue-scale observational robustness analysis.

## STATUS

CATALOGUE-SCALE ROBUSTNESS CHARACTERIZED —
PHASE 3A CLOSURE NOT STARTED

Phase 3A remains a prospectively defined catalogue-scale stress test of independently defined
observational QPP reference classifications under frozen temporal-window, processing,
admissibility, and numerical perturbations.

The historical pre-BAII boundary remains preserved in:

- [`ENTRY_CONTRACT.md`](ENTRY_CONTRACT.md)
- [`FROZEN_INPUTS.json`](FROZEN_INPUTS.json)

Those two files are historical references. The scientific design frozen after Bibliographic
Audit II remains unchanged in [`design/`](design/).

F3A.2 has now established, before any Phase 3A AFINO execution:

- byte-level provenance for the BAIIW0001 parent catalogue and QPP table;
- a deterministic 122-event cohort: 61 published-QPP references and 61 matched observational
  non-selected controls, without replacement;
- exact SPOC 20-second TESS product bindings for 87 unique TIC-sector products serving all
  122 events;
- valid deterministic source-marker to native-cadence mappings for all 122 events;
- the complete 9,516-row primary 13x6 robustness matrix;
- frozen exact payloads for every eligible primary variant;
- the resolved primary and W00/P00 numerical-stability decision grid;
- an exact three-model AFINO call plan whose rows remain `NOT_EXECUTED`.

No Phase 3A AFINO model has been imported or executed by the F3A.2 materialization workflow, no
Phase 3A classification has been observed, and no scientific result has been computed.

The next authorized task after review/freeze of F3A.2 is F3A.3: canary/checkpointed validation of
the catalogue-scale runner against the frozen execution plan before any full catalogue execution.
