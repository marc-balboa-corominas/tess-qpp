# Bibliographic Audit II — BAII.3 screening report

## Scope

BAII.3 converted the frozen BAII.2 retrieval corpus into a work-level screening set without beginning structured methodological extraction. The input was the immutable 322-row `raw_hit_ledger.csv` associated with `bibliographic-audit-ii-corpus-v1`. Resolution and screening used the amended design v1.1.0 (`bibliographic-audit-ii-design-v2`). No F0–F2, F3A, or F3B file was modified, and no relevance label, prospective design-impact category, manuscript-positioning category, or novelty judgment was assigned.

## Work and version resolution

The 322 raw hits resolve to **190 unique intellectual works**. The automatic bibliographic layer first produced **201 components** using only exact provider-record identity, normalized journal DOI, normalized arXiv base identifier, and explicit provider cross-links. Fuzzy title matching was not permitted to merge records. Its deterministic candidate table contained 10 candidate pairs and rebuilt byte-for-byte identically in two independent runs (`AUTO_WORK_CANDIDATE_REBUILD_EXACT`).

Manual review was then recorded explicitly in `manual_adjudications.csv`. There were **11 `MANUAL_CONFIRMED_SAME_WORK` adjudications** and **11 `MANUAL_CONFIRMED_DISTINCT_WORKS` adjudications**, with **0 unresolved mappings**. The same-work decisions cover cases such as conference precursors to journal articles, substantially equivalent meeting versions, and one provider-associated data catalogue. The distinct-work decisions prevent false merges where similar titles, authors, or subject vocabulary refer to different targets, samples, events, or grant records. After these adjudications, all 322 raw hits map to exactly one `work_id`; no hit is lost and no hit is multiply mapped.

The work set contains **283 distinct bibliographic versions**: 125 journal articles, 109 arXiv/preprint versions, 41 conference abstracts, and 8 other records. Every work has exactly one preferred version. The frozen policy was applied mechanically: a substantively current journal version is preferred when available; otherwise the available arXiv version is preferred, followed by the only recoverable conference/other version. Earlier preprints and conference versions remain in `version_registry.csv` and are never deleted merely because a journal version exists.

## Screening outcome

Screening was performed at `work_id` level using the preferred version's title, abstract, and provider metadata. No systematic full-text extraction was required to resolve eligibility. The final outcomes are:

- **40 `INCLUDE_FOR_BAII4`**
- **33 `BACKGROUND_ONLY`**
- **117 `EXCLUDE`**
- **0 `UNRESOLVED_ACCESS_LIMITATION`**

Every included work satisfies at least one frozen I1–I7 criterion. Because a work may satisfy multiple criteria, the inclusion counts overlap: I1 = 4, I2 = 25, I3 = 7, I4 = 10, I5 = 8, I6 = 2, and I7 = 10. These counts are screening gates only; they are not claims about methodological overlap or design impact.

Every excluded work has a primary frozen E criterion. Work-level exclusion counts are E1 = 11, E2 = 6, E3 = 33, E4 = 0, E5 = 0, and E6 = 67. E5 is principally a version-resolution rule in this task: earlier substantially equivalent versions remain registered under the same `work_id` rather than creating an independently excluded work. The 33 background records are retained separately because they remain useful context while not meeting the structured-extraction threshold; 28 are solar-only context under E2 and 5 are broader stellar/QPP physical context under E6.

No work was excluded because content was inaccessible. All final decisions were resolved from the frozen bibliographic evidence available in BAII.2. Four auxiliary verification lookups are recorded transparently in `verification_lookup_log.csv`; none altered work identity, screening evidence, or the systematic denominator, and no newly encountered citation was inserted into the 322-hit corpus.

## Seeds and next boundary

The pre-existing seed list remains outside the systematic denominator. Four seed sources are also independently represented by systematic BAII.2 work IDs: S005, S006, S007, and S008. This match is recorded for provenance only; no seed was manually injected as a hit.

BAII.3 therefore closes with a fully mapped and screened corpus ready for structured extraction. **BAII.4 has not started.** The fields `relevance_labels`, `f3a_design_impact`, `f3b_design_impact`, and `manuscript1_positioning_impact` remain empty in `screened_works.csv`. The 40 included works may proceed to BAII.4, where detailed methodological/observational extraction and overlap analysis can begin under a separate task boundary.
