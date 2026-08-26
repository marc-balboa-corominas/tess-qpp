# DR-011 — Manuscript 1 first complete scientific draft

**Status:** FIRST COMPLETE DRAFT CANDIDATE; SCIENTIFIC / EDITORIAL REVIEW NOT YET COMPLETE

## Thesis statement

The study characterizes the reproducibility, methodological robustness, numerical behavior, and synthetic-ground-truth selection properties of the frozen AFINO implementation in the TESS QPP context, while explicitly separating observational reference evidence from known synthetic ground truth.

## Evidence-plane treatment

F0, F1, F2, F3A and F3B remain distinct scientific evidence planes. BAII remains an auxiliary documentary positioning plane. No observational reference role is promoted to physical ground truth, and synthetic-ground-truth metrics are not transported to observational performance.

## Section realization

The M1.1 section map is realized as a full neutral preprint. Mentor-requested Results subsections 4.5 and 4.6 split the frozen M1.1 classifier-performance section into DEVELOPMENT and independent HELDOUT reporting; Results 4.7 realizes the frozen selection-function/period-recovery section. No new scientific claim is introduced by this editorial split.

## Citation policy

`references.bib` is constructed only from frozen BAII seed/work metadata. No internet or new bibliographic lookup is used. Priority language remains bounded by BAII.

## Figure/table integration

M1F01--M1F05 are included directly from the M1.2 frozen PDFs. M1T01--M1T04 are included directly from the M1.2 frozen TeX tables. No visual artifact is regenerated.

## Correction boundary

The correction claim remains `NOT_ESTABLISHED`. The F3B selection surface is synthetic-domain evidence, not an observational population correction.

## Traceability

Scientific prose uses temporary `M1TRACE` comments. Claim usage, numerical values, citations, and visual usage are registered under `draft/evidence/`.

## Pre-freeze review history

- `M1D-REV-001` — The first complete-draft review identified an unqualified `held-out validation` subsection heading despite the manuscript-wide rule that validation terminology remain explicitly scoped. Before Git freeze, the heading was repaired to `synthetic-ground-truth held-out validation`. The repair changes no source, claim, number, result, evidence plane, figure, or table.

## Editorial pending items

Title, target journal, author/affiliation metadata, supplement placement, final bibliography style, and submission-specific layout remain editorial questions recorded in `m1_3_author_queries.md`.

## Current counts

- Main-text words: 5725
- Abstract words: 212
- Scientific paragraph trace records: 71
- Figure caption trace records: 5
- Claim-usage records: 76
- Visual usage records: 9
- Numeric trace items: 120
- Figures: 5/5
- Tables: 4/4

## Freeze target

Commit subject: `docs(manuscript1): freeze first complete scientific draft`

Annotated tag: `manuscript1-first-draft-v1`

OSF snapshot target: `manuscript1_first_complete_draft_v1.zip`
