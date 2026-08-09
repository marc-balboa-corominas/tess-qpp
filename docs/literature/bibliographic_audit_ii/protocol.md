# Bibliographic Audit II — Search and Screening Protocol

**Audit ID:** `tess_qpp_bibliographic_audit_ii_v1`  
**Version:** `1.1.0`  
**Status:** `AMENDED_AND_REFROZEN_BEFORE_BAII2_RESTART`  
**Recent-window start:** `2024-01-01`  
**Search freeze date:** `2026-08-07`

## 1. Purpose and boundary

Bibliographic Audit II (BAII) is a prospective literature audit placed after the frozen F0–F2 foundation and before the final freeze of F3A. Its purpose is to determine whether recent literature changes the prospective design, comparator set, or manuscript positioning of the TESS QPP research programme. BAII does not reinterpret F0–F2, authorize candidate discovery, calculate new scientific results, or validate a correction.

The governing F2.6 premises remain fixed: `robustness_manuscript_viable = true`, `correction_claim_established = false`, `held_out_validation_required_for_correction = true`, and `candidate_discovery_allowed = false`. The ten F2 events have already been observed and cannot later serve simultaneously as development data and independent validation of a rule motivated by them.

The repository already contains eight pre-existing seed sources and an empty legacy audit matrix created when the BAII gate was established. Those records are context known before this preregistration; they are not a systematically retrieved corpus and have not been screened under the BAII.1 rules. They remain unchanged and do not alter `papers_screened_before_freeze = false`.

## 2. Scientific questions

**Q1 — Observational overlap.** ¿Existen trabajos recientes que hayan construido catálogos o muestras QPP de fulguraciones TESS que se solapen materialmente con el espacio previsto para F3A?

**Q2 — Methodological overlap.** ¿Existen métodos recientes de detección o clasificación QPP aplicables a TESS que deban incluirse como comparadores, contexto o potenciales alternativas en F3A/F3B?

**Q3 — Validation.** ¿Existen estudios recientes con injection–recovery, simulaciones con ground truth, calibración de selección o validación held-out relevantes para el diseño de F3B?

**Q4 — Positioning.** ¿Cambian los trabajos recientes la novedad o el framing defendible del programa TESS QPP?

A null result from one query family cannot support statements such as “no prior work exists” or “our approach is novel”. Novelty or priority positioning may only be assessed after the complete retrieval, deduplication, screening, extraction and citation-chaining workflow.

## 3. Time window

The primary recent window is `2024-01-01` through `2026-08-07`. The 2024 start is a buffer intended to capture preprints that later became 2025–2026 journal publications. Earlier work may enter only through backward citation as `FOUNDATIONAL_CONTEXT`, `METHOD_PRECURSOR`, or `CATALOG_PRECURSOR`; such records do not count as recent BAII findings.

For ADS/SciX the frozen query uses the searchable machine-readable `date` field, which represents publication date. In v1.1.0 the timestamp colons inside the `date` range are escaped (`\:`) because the current SciX parser rejected the unescaped v1.0.0 strings. The interval remains exactly `2024-01-01T00:00:00.000Z` through `2026-08-07T23:59:59.999Z`; no subject term, Boolean group, field, or scientific date boundary is changed. For arXiv the frozen query uses `submittedDate`, which represents arXiv submission time. These are intentionally different source-native date semantics and will be preserved in the raw search log rather than forced into a false equivalence.

## 4. Sources and reproducibility

Primary retrieval sources are NASA ADS / SciX and arXiv. Crossref, publisher/editorial pages and DOI landing pages may be used only to verify bibliographic identity, publication status, DOI, dates or version relationships. Google Scholar is not a normative counting source. It may only be used to locate an already identified work, and any such use must be recorded as auxiliary.

The exact six query families are frozen in `search_plan.yaml`. Their ADS/SciX syntax uses fielded `abs:` searches, Boolean grouping and the machine-readable `date` range. Their arXiv syntax uses supported field prefixes, Boolean operators, quoted phrases and `submittedDate`.

BAII.1 v1.0.0 defined the original strings before systematic retrieval. During BAII.2, two incomplete technical retrieval attempts exposed a provider-authentication incident and then a SciX parser incompatibility in the unescaped `date` timestamps. No 12/12 raw corpus was completed or frozen, and no scientific screening, deduplication, `work_id` assignment, design-impact judgment, or novelty assessment was performed. Version 1.1.0 is therefore a narrow technical amendment: only the SciX timestamp escaping and provider-documentation provenance are corrected; all scientific query semantics and every arXiv query remain unchanged.

The BAII.2 restart must execute the v1.1.0 frozen queries exactly, record database, query ID, exact query string, execution timestamp, total result count and pagination, and preserve the raw corpus before any scientific inclusion decision. A further syntax failure or service limitation is an incident and does not permit silent query editing.

## 5. Inclusion and exclusion

A work is eligible for full screening when at least one criterion I1–I7 applies: direct TESS stellar-flare QPP analysis; a TESS catalogue or sample material to F3A; a QPP detection method applicable to stellar flare time series; robustness to temporal window, detrending, preprocessing, gaps or noise; injection–recovery, ground-truth simulation or selection-function characterization relevant to F3B; methodologically relevant AFINO use; or a recent sufficiently close method that could alter reasonable Manuscript 1 comparators.

Criteria E1–E6 exclude compact-object QPO/QPP without material methodological transfer to stellar flares; solar-only work without material transfer; TESS work without pertinent flare/QPP analysis; conference abstracts lacking recoverable methods/results unless they are the only known material version; duplicate or earlier substantially equivalent versions; and purely physical papers that do not affect F3A/F3B design, catalogue, selection or method. Relevant E2/E6 records may remain traceable as `BACKGROUND_ONLY`.

Exclusion is never silent: the raw corpus remains intact and the screening record preserves the reason.

## 6. Work identity and version policy

The counting unit is `work_id`, representing one intellectual work. An arXiv preprint and a later journal article are one `work_id`, not two papers. The audit preserves `first_public_date`, `latest_version_date`, `arxiv_id`, `doi`, `bibcode`, `preferred_citation_version` and `peer_review_status`, together with duplicate/version links.

Scientific claims preferentially cite the journal version when available and substantively current. Priority retains the earliest verifiable public date, including arXiv v1 where applicable. Material scientific changes between versions must be documented rather than silently collapsed.

## 7. Relevance and impact classification

Included works may receive multiple relevance labels: `DIRECT_F3A_OVERLAP`, `DIRECT_F3B_OVERLAP`, `CATALOG_RELEVANT`, `DETECTION_METHOD_RELEVANT`, `ROBUSTNESS_RELEVANT`, `SELECTION_FUNCTION_RELEVANT`, `PHYSICAL_CONTEXT`, and `BACKGROUND_ONLY`.

Prospective impact is classified as `NO_DESIGN_IMPACT`, `POSITIONING_ONLY`, `F3A_DESIGN_ADJUSTMENT_POSSIBLE`, `F3B_DESIGN_ADJUSTMENT_POSSIBLE`, or `F3A_REDRAFT_REQUIRED`. `NOVEL`, `NOT_NOVEL`, and `SCOOPED` are not screening categories.

`POSITIONING_ONLY` applies when a work changes related-work framing, terminology or priority context without requiring a different cohort, comparator, outcome, preprocessing contract, validation split or analysis design. `F3A_DESIGN_ADJUSTMENT_POSSIBLE` applies when recent work materially overlaps the intended catalogue/sample, introduces a comparator required for a fair test, or reveals a design-relevant processing/selection issue. `F3B_DESIGN_ADJUSTMENT_POSSIBLE` applies to materially relevant injection–recovery, ground-truth, held-out, selection-function, complexity or multiplicity frameworks. `F3A_REDRAFT_REQUIRED` is reserved for evidence that materially duplicates the central planned F3A contribution or renders its prospective design framing inadequate before freeze.

## 8. Screening and extraction contract

`screening_schema.csv` is frozen with a header and zero scientific rows. Future records capture bibliographic identity, database/query provenance, duplicate/version linkage, TESS and stellar-flare use, catalogue scale and sample size, detection method and AFINO use, comparison methods, window/processing robustness, gap handling, optimizer stability, injection–recovery, ground truth, held-out validation, selection-function characterization, relevance labels, screening decision/reasons, prospective F3A/F3B impact and Manuscript 1 positioning impact.

Backward-citation additions must retain provenance and their foundational/precursor class. No work is removed from the audit trail because it fails inclusion.

## 9. F3A gate

BAII.5 may issue only `NO_CHANGE_TO_F3A`, `POSITIONING_UPDATE_ONLY`, `F3A_DESIGN_ADJUSTMENT_REQUIRED`, or `F3A_DESIGN_RECONSIDERATION_REQUIRED`. No gate decision is made in BAII.1, and F3A remains unfrozen.

Any change motivated by BAII is prospective. BAII cannot revise the frozen F0–F2 evidence, transform observational roles into physical ground truth, estimate sensitivity/specificity, authorize discovery, or establish a validated correction. A correction remains a separate programme requiring preregistration and independent held-out validation.

## 10. Amendment v1.1.0 — SciX parser correction

The immutable v1.0.0 design remains identified by Git tag `bibliographic-audit-ii-design-v1` at commit `24b3ddde7a9b7baf35f6b236d83e80ec20571c95`. That tag must never be moved.

After v1.0.0, BAII.2 produced two incomplete technical attempts, both preserved outside the normative corpus:

1. `attempt01_ads401`: all six ADS/SciX calls failed before retrieval with HTTP 401 while the six arXiv calls completed. Review-bundle SHA-256: `3c3ebc12ff15c2aae86c9ae83b15ed86022cff84ca42259c2bafe0897596bb25`.
2. `attempt02_scix400_syntax`: after authentication was repaired and the current SciX API endpoint was used, all six SciX calls failed with HTTP 400 `INVALID_SYNTAX_CANNOT_PARSE` while the six arXiv calls completed. Review-bundle SHA-256: `e5a4d9e0a3f2dbea6e76caa8496579c07c9dd1244a38975ecf2120ad4b743b90`.

The visible arXiv result counts from these attempts were retrieval diagnostics only. They were not used to alter query terms, inclusion/exclusion criteria, relevance labels, impact rules, F3A/F3B design, or any scientific claim.

A provider parser diagnostic then tested four non-corpus queries: an `abs:` control, the documented monthly `pubdate` form, a quoted exact `date` range, and an exact `date` range with escaped timestamp colons. All four parsed successfully; the three date-bounded variants returned the same diagnostic count in that probe. Version 1.1.0 adopts the escaped-colon exact `date` form because it is the minimal parser correction to v1.0.0 and preserves the exact frozen recent-window boundaries.

This amendment does **not** change the six semantic query families, Boolean content, recent-window start, search freeze date, arXiv strings, screening schema, inclusion/exclusion criteria, version policy, relevance labels, impact categories, F0–F2, F3A, or F3B. It exists solely to make the frozen SciX strings executable and to record the pre-restart incidents transparently.

BAII.2 must restart from an empty normative `baii2_raw/` and `retrieval/` location after the v1.1.0 design is committed and tagged as `bibliographic-audit-ii-design-v2`. The two failed attempts remain incident evidence and are never merged into the normative raw corpus.

