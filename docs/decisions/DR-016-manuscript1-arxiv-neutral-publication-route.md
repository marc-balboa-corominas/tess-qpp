# DR-016 - Manuscript 1 arXiv-neutral publication route

STATUS: AUTHOR-APPROVED / FREEZE AUTHORIZED; FINAL CLOSURE PENDING GIT+OSF VERIFICATION

## Decision

Manuscript 1 publication work now proceeds through an arXiv-first, journal-neutral route. M1.6 (`manuscript1-author-approved-v1` at `d1007edcdbcf98b809ed46b0810fd62148f7b2af`) is the sole normative scientific source for M1.8. M1.7 (`manuscript1-submission-ready-v1` at `b457543887ff6fa3b7b418b5d8df0c6caecc894b`) remains a preserved historical ApJ-specific branch and must not be used as a normative source for content or pagination.

## M1.8 scope

M1.8 transforms the author-approved M1.6 paper into a self-contained, journal-neutral LaTeX source bundle, compiles it in a clean directory, performs automated scientific/technical identity checks, and then stops for explicit author visual review.

Permitted difference classes are FORMAT_ONLY, PAGINATION_ONLY, NEUTRAL_METADATA_ONLY, and SOURCE_PACKAGING_ONLY. Scientific changes, new claims, new scientific numerics, new scientific references, new figures, new tables, and new inference are forbidden.

## Author-requested neutral pagination revision

After the first 21-page candidate review, the author requested page breaks before Section 2, subsection 4.4 (Numerical stability), and References. After the subsequent 22-page v2 review, the author additionally requested that Section 3 Methods start on a fresh page and that Figure 3 be fully placed before subsection 4.5 so 4.5 starts cleanly after the figure. Subsection 4.7 is rechecked after that reflow and receives no extra break because it no longer begins in the final page quarter. Figure 4 remains the single landscape page; Introduction remains on page 1 after the abstract; no forced breaks are added before 3.2, 3.5, 4.6, 5.3, or 5.5. These are PAGINATION_ONLY changes.

The authoritative M1.6 manuscript itself contains the Data/code resources section followed by the bibliography and does not contain the funding/COI/author-contribution blocks materialized later for the historical M1.7 journal branch. Their absence in M1.8 is verified as deliberate rather than accidental.

## Author visual gate

The author completed a page-by-page review of all 22 pages of candidate v3 and explicitly approved the neutral PDF on 2026-08-29.

Author visual state: `PASS`.

The Git freeze/tag and final M1.8 OSF snapshot are now authorized. arXiv metadata freeze, public-infrastructure publication, endorsement handling, actual arXiv upload, and journal submission remain outside M1.8 and are not authorized by this decision record.

The canonical repository PDF is `build/manuscript_arxiv_neutral.pdf` with SHA-256 `04e5fc3b4fad60a6877d46b349d9327ccbf7476391a930d1032d81e038db08a5`. The standalone PDF used for the author's final visual review is render-identical on all 22 pages; serialization-byte differences do not alter the rendered manuscript.

## Deferred decisions

Primary/cross-list arXiv categories, license, comments field, endorsement, public-infrastructure transition, external link verification, actual arXiv submission, and OJAp submission are intentionally deferred beyond M1.8 candidate construction.
