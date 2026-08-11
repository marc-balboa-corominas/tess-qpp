# Bibliographic Audit II — BAII.5 Final Synthesis Report

## 1. Objective and scope

BAII.5 closes Bibliographic Audit II as a documentary gate between the frozen F0–F2 foundation and the future scientific freeze of Phase 3A. It does not redesign F3A, modify F3B, execute new scientific analyses, reopen screening, or perform a new systematic literature search. Its purpose is narrower: synthesize the frozen BAII.1–BAII.4 evidence into one traceable decision about what must happen before F3A can be scientifically frozen.

The final gate is therefore a governance and design-readiness decision. It uses the four preregistered gate states only, applies the frozen hierarchical rule, and preserves the distinction between bibliographic overlap, prospective design impact, and claims of novelty or priority. No global novelty assessment is made.

## 2. Corpus and screening

The systematic BAII corpus remains unchanged at 190 unique intellectual works derived from the frozen 322 raw hits. BAII.3 included 40 works for primary structured extraction, retained 33 as background-only context, excluded 117, and left no unresolved screening decisions. BAII.4 subsequently extracted exactly those 40 included works, producing 160 evidence rows, 40 work-level overlap assessments, 62 dimensional overlap assessments, and 40 source-access records.

BAII.5 does not alter any of those denominators. The deferred citation candidate discovered in BAII.4 is treated separately as supplemental context and never becomes a retrospective systematic hit. Likewise, no background-only work is promoted into the primary 40-work extraction set.

## 3. Panorama of the 40 included works

The 40 works cover several distinct literature roles: catalogue-scale TESS flare and QPP studies, QPP-detection/classification methods, general flare-detection pipelines, robustness or processing studies, and injection–recovery/known-truth validation approaches. BAII.4 identified 26 catalogue-relevant works, 17 detection-method-relevant works, 10 robustness-relevant works, seven direct F3B-overlap works, and eight selection-function-relevant works.

Evidence depth is heterogeneous. Five works retain documented access limitations. Only three were extracted primarily from full text, while 35 were extracted primarily from abstracts and two from table/provider-metadata sources. BAII.5 therefore keeps detailed implementation claims conservative and does not replace NOT_REPORTED fields with inference.

## 4. Direct overlap with F3A

Two works remain DIRECT F3A overlaps after critical review: BAIIW0001, *Stationary quasi-periodic pulsations in 20-second cadence TESS flares*, and BAIIW0003, *Properties of Flare Quasiperiodic Pulsations Based on a New TESS Flare Catalog*. Both retain the BAII.4 category F3A_REDRAFT_REQUIRED.

BAIIW0001 is sufficient on its own to trigger the highest gate branch. It uses 20-second TESS data from Sectors 27–80, reports 3,878 flares across 1,285 flaring stars, identifies 61 QPPs across 57 stars, and applies AFINO Fourier model comparison after automated flare detection. This directly overlaps both the catalogue-scale and QPP-classification reference dimensions of the prospective F3A comparison target.

The overlap does not mean that BAIIW0001 implements the complete planned F3A programme. The frozen evidence does not establish the full prospective window, processing, quality/gap and numerical-stability robustness architecture, nor does it provide known physical truth or the project-specific independent held-out validation reserved for F3B. The implication is therefore redesign/reframing, not cancellation.

## 5. The two catalogue-scale TESS QPP works

BAIIW0003 provides a second, independent reason that F3A cannot be framed simply as catalogue-scale TESS QPP work. It reports a large TESS 2-minute flare catalogue with 208,280 flare events from about 29,280 flaring stars and applies a previously published fully convolutional QPP classifier, selecting 10,465 M-star flares with QPP features.

BAII.5 performed the required final allowed-source recheck. The high-level catalogue and QPP-classification facts remain supported, but the complete classifier training, validation, robustness and selection-function details were not resolved through the allowed-source path. The BAII.4 access limitation is therefore retained. This limitation does not justify weakening the direct catalogue/classification overlap, but it prevents BAII.5 from making stronger claims about the classifier’s complete validation architecture.

Together, BAIIW0001 and BAIIW0003 establish that catalogue scale, TESS use and QPP classification cannot themselves define the distinctive F3A contribution.

## 6. F3A design considerations

Beyond the two redraft-required cases, 13 works retain F3A_DESIGN_ADJUSTMENT_POSSIBLE. Their implications cluster into concrete design questions rather than automatic method changes.

First, the cohort universe and catalogue source must be frozen prospectively. Large TESS flare catalogues generated by different automated pipelines already exist, and upstream event construction can affect the population presented to QPP analysis. Second, QPP reference labels require explicit provenance: AFINO-based observational selection, neural-network classification and comparison-event roles must not be confused with physical truth.

Third, F3A must preserve its intended robustness focus. The literature supplies concrete alternatives involving wavelet/window choices, stochastic or Gaussian-process baselines, detrending, quality/gap handling and automated flare pipelines. These do not mandate a maximal comparison grid, but the future F3A design must state which dimensions are included, which comparators are deferred, and why. Finally, AFINO numerical behaviour remains a separate evidence plane from classification robustness; optimizer-seed and convergence diagnostics must remain prospectively specified.

These issues are recorded as open F3A gate requirements. BAII.5 does not mark any of them ADOPTED, REJECTED or IMPLEMENTED.

## 7. Literature relevant to F3B

Nine included works carry F3B_DESIGN_ADJUSTMENT_POSSIBLE. They include injection–recovery studies, synthetic known-truth experiments, completeness/selection-function characterization and QPP or flare classifiers tested on controlled data. These works establish that injection–recovery and selection-function ideas are not new in the adjacent flare/QPP methodological space.

At the same time, BAII did not identify an included work assessed as matching the complete project-specific F3B architecture: explicit prospective development/validation separation combined with an independent held-out benchmark under the frozen F3B reference. This is a bounded statement about the 40 included works, not a global priority claim. F3B remains scientifically unfrozen, and its signal families, noise/background model, success criteria and held-out protocol remain future design decisions.

## 8. Comparators

BAII.4 identified 11 sufficiently defined comparator candidates. BAII.5 represents all 11 and assigns consideration priority without adopting any of them. Directly relevant examples include Morlet wavelet QPP analysis, the fully convolutional QPP classifier, multiple TESS flare-detection pipelines, hidden-Markov/Celerite approaches, ARMA/GARCH processing, wavelet denoising, FLARENET and Bayesian additive GP/HMM models.

The comparator matrix distinguishes methods that must be addressed before the F3A freeze from those primarily relevant to F3B. “Must address” means that the later design must explicitly implement, reject with rationale, defer, or treat the method as positioning-only. It does not mean that every comparator must be run.

## 9. Positioning and claims to avoid

The audit supports several bounded positioning statements. Catalogue-scale TESS QPP studies are present in the included literature. AFINO has already been applied at catalogue scale to TESS QPP analysis. Machine-learning QPP classification has been applied to a large TESS flare catalogue. Injection–recovery and selection-function approaches are represented in adjacent flare/QPP methodology.

Consequently, F3A must not be described as the first catalogue-scale TESS QPP study. F3B must not be described as the first QPP injection–recovery study. Claims that no previous work examined methodological robustness are contradicted by included literature. The audit also does not authorize a global claim that the project is the first to study TESS QPP selection effects. Non-retrieval of an exact precedent is not proof of absence from the literature.

## 10. Bibliographic limitations

The gate inherits the frozen 2024–2026 search window, the two principal providers, the preregistered query families, uneven source-access depth, the exclusion of 33 background-only works from primary extraction, and the distinction between systematic and citation-chased context. Literature after the 2026-08-07 search freeze is not systematically covered.

The deferred candidate arXiv:2602.20402 concerns TESS flare detection in nearby young moving-group members. Its abstract provides relevant upstream flare/cadence context but does not establish a direct QPP overlap. It remains outside the systematic denominator.

## 11. Formal gate decision

The frozen hierarchical rule selects **F3A_DESIGN_RECONSIDERATION_REQUIRED**. Hierarchy A is satisfied because at least one case—and in practice two cases—remains F3A_REDRAFT_REQUIRED plus DIRECT F3A overlap with evidence sufficient for gate use and material relevance to the central catalogue-scale contribution or experimental framing.

BAIIW0001 independently satisfies the trigger, so the access limitation on BAIIW0003 is not outcome-determinative. The decision means that freezing the pre-BAII conception of F3A without explicit reconsideration would be methodologically inappropriate. It does not mean F3A is cancelled, invalid, or demonstrated to be non-novel.

## 12. Exact implication for the next task

Bibliographic Audit II is complete. F0–F2 remain frozen. BAII.1–BAII.4 remain frozen. F3A and F3B remain scientifically unfrozen.

The next task is **F3A.1 — prospective reconsideration and freeze of the F3A scientific design from the BAII.5 gate**. F3A.1 must resolve the open cohort, catalogue, event-selection, QPP-reference, robustness, numerical and comparator questions before any catalogue-scale execution. Only after that prospective design is explicitly frozen should scientific execution begin.
