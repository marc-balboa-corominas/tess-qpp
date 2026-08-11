# BAII.4 structured extraction and overlap assessment

## Scope and completion

BAII.4 extracted all 40 work entities frozen as `INCLUDE_FOR_BAII4` in BAII.3. No excluded or `BACKGROUND_ONLY` work was inserted into the primary extraction denominator, and the frozen `work_id` and preferred-version assignments were retained without modification. The documentary F3 comparison target was frozen before systematic extraction in `f3_overlap_reference.json`; BAII.4 therefore compares the literature against a stable description of the prospective F3A/F3B questions rather than against a design that changes during review.

The 40 works span several literature classes. They include catalogue-scale TESS stellar-flare and QPP studies, single-target or small-sample QPP analyses, flare-detection and classification methods, injection–recovery and completeness studies, multi-mission activity catalogues, conference abstracts, a VizieR catalogue record, and the AFINO software record. Thirty-five extractions used abstract-level evidence as the primary evidence level, three used full-text evidence for methodological details, one used a structured table/catalogue source, and one used provider metadata. Five works are marked `COMPLETE_WITH_ACCESS_LIMITATION`; none is `BLOCKED`. Missing methodological detail is represented as `NOT_REPORTED`, not inferred as methodological absence.

## Observational and methodological overlap with F3A

At the aggregate work level, two works are classified as `DIRECT` F3A overlap, 36 as `PARTIAL`, and two as `CONTEXT_ONLY`. The two direct cases are BAIIW0001 and BAIIW0003. Both operate at catalogue scale and combine TESS flare populations with QPP identification/classification. Under the frozen BAII.4 rubric, both receive `F3A_REDRAFT_REQUIRED`. This category is deliberately narrower than a gate decision: it means the planned F3A contribution, cohort definition, and positioning should not be frozen without explicitly reconsidering this material overlap. It does not assert novelty, precedence, or that F3A has been superseded.

Thirteen additional works receive `F3A_DESIGN_ADJUSTMENT_POSSIBLE`. They identify concrete choices that merit consideration before a future F3A freeze, including catalogue construction, event-selection rules, processing/detrending choices, wavelet or machine-learning comparators, temporal robustness, flare/background modeling, data-quality/gap treatment, and the role of AFINO as a baseline method. The remaining 25 works have `NO_DESIGN_IMPACT` for F3A: they contribute context or confirm practices without introducing a concrete design requirement under the present evidence.

The dimensional evidence table keeps these judgments reconstructable. It links each direct or partial aggregate assessment to one or more frozen dimensions such as `F3A_COHORT_UNIVERSE`, `F3A_CATALOG_SCALE`, `F3A_EVENT_SELECTION`, `F3A_QPP_CLASSIFICATION_REFERENCE`, `F3A_WINDOW_ROBUSTNESS`, `F3A_PROCESSING_ROBUSTNESS`, `F3A_QUALITY_AND_GAPS`, or `F3A_NUMERICAL_STABILITY`, together with source-level evidence IDs and the corresponding project-reference source.

## Validation overlap with F3B

Seven works have `DIRECT` F3B overlap, two have `PARTIAL` overlap, and 31 are `CONTEXT_ONLY`. The direct group contains explicit injection–recovery, synthetic-ground-truth, or selection-function evaluations that closely match the validation role reserved for F3B. The partial group contains related selection or simulation machinery without reproducing the complete planned validation architecture.

Nine works receive `F3B_DESIGN_ADJUSTMENT_POSSIBLE`: BAIIW0024, BAIIW0071, BAIIW0098, BAIIW0147, BAIIW0149, BAIIW0150, BAIIW0154, BAIIW0156, and BAIIW0168. They collectively show relevant approaches to synthetic signal generation, injection into realistic or observed backgrounds, recovery/completeness measurement, false-selection characterization, or simulation-based evaluation. No included work was found to implement the exact frozen prospective combination of explicit development/validation separation plus an independent held-out benchmark required by the F3B reference. That absence is recorded descriptively and is not converted into a novelty claim.

## Potential methodological comparators

Eleven works are flagged as comparator candidates because the available source describes a procedure sufficiently concretely to support a future controlled comparison. These include wavelet-based QPP analysis, supervised flare classifiers, HMM/celerite flare models, deterministic-trend plus ARMA/GARCH modeling, a fully convolutional QPP classifier, LSTM flare detection, wavelet denoising with injection tests, the `ardor` flare pipeline, logistic-regression/FRED flare detection, the `flarenet` CNN, and the VAE/Celerite/HMM additive Bayesian model. The flag does not mean any comparator has been adopted; that decision belongs to BAII.5 and any subsequent F3 design freeze.

## Positioning and source limitations

Twenty-three works receive `POSITIONING_ONLY` for Manuscript 1. These works materially affect which prior methods, catalogues, or validation studies should be cited or how background claims should be framed, but do not by themselves require an experimental change. Seventeen receive `NO_DESIGN_IMPACT` for positioning under the current rubric.

Five work records retain documented access limitations at the preferred-version evidence level: BAIIW0003, BAIIW0029, BAIIW0043, BAIIW0182, and BAIIW0188. They remain in the extraction because their available sources are sufficient for bounded overlap assessment, while unresolved details are left `NOT_REPORTED`. No work was excluded or downgraded merely because a detail could not be accessed.

One external citation candidate was encountered while verifying BAIIW0182: `arXiv:2602.20402`, a later related study. It is recorded only in `deferred_citation_candidates`. It is not assigned a BAII `work_id`, is not added to the 190-work systematic corpus, and does not alter the 40-work extraction denominator.


## Evidence accounting

The structured extraction contains 160 evidence rows, four retained evidence summaries per included work, and 62 long-format overlap-dimension rows. Evidence is separated from the aggregate judgment so that BAII.5 can inspect the source basis for a label or impact assignment without reverse-engineering prose summaries. The source-access log contains one primary-extraction access record for every included `work_id`; local copyrighted copies are not part of the Git deliverable. All dimensional claims classified `DIRECT` or `PARTIAL` point to existing extraction evidence and to the frozen F3 project-reference source. This separation also preserves the distinction between what a paper reports, what BAII.4 extracts from that report, and the prospective comparison made against F3A/F3B.

## Boundary for BAII.5

BAII.4 assigns relevance labels and prospective impact categories because those are required to make the evidence matrix usable. It does not modify F0–F2, F3A, or F3B; does not authorize candidate discovery; does not alter BAII.3 screening decisions or preferred versions; and does not assess novelty. The final gate among `NO_CHANGE_TO_F3A`, `POSITIONING_UPDATE_ONLY`, `F3A_DESIGN_ADJUSTMENT_REQUIRED`, or `F3A_DESIGN_RECONSIDERATION_REQUIRED` remains explicitly open for BAII.5.
