# Bibliographic Audit II

**STATUS:** `BIBLIOGRAPHIC AUDIT II CLOSED — F3A GATE DECISION FROZEN`

Bibliographic Audit II is the literature gate between the frozen F0–F2 foundation and the future freeze of F3A. BAII.1 v1.0.0 froze the prospective search and screening design. BAII.1 v1.1.0 is a narrow technical amendment created after incomplete BAII.2 retrieval attempts exposed a SciX parser incompatibility in the exact `date` timestamp syntax. The scientific query semantics and screening design remain unchanged.

## Sequence

```text
BAII.1 protocol freeze
        ↓
BAII.2 systematic search + raw corpus freeze
        ↓
BAII.3 deduplication + screening
        ↓
BAII.4 structured extraction + overlap analysis
        ↓
BAII.5 synthesis + F3A gate decision
```

## BAII.1 / amendment boundaries

- Complete 12/12 BAII.2 raw corpus frozen: **yes**
- Incomplete technical retrieval attempts preserved: **2**
- Successful provider executions before v1.1.0: **12 arXiv executions across two attempts**
- Failed provider executions before v1.1.0: **12 SciX executions across two attempts**
- BAII.2 normative executions: **12/12 successful**
- BAII.2 raw hit rows: **322** (**249 SciX + 73 arXiv**)
- BAII.2 deterministic rebuild: **`RAW_LEDGER_REBUILD_EXACT`**
- BAII.3 raw hits mapped: **322/322**
- BAII.3 unique intellectual works: **190**
- BAII.3 bibliographic versions: **283**
- BAII.3 preferred versions: **190**
- BAII.3 screening outcomes: **40 include / 33 background / 117 exclude / 0 unresolved**
- BAII.3 automatic candidate rebuild: **`AUTO_WORK_CANDIDATE_REBUILD_EXACT`**
- Scientific works screened under BAII.3: **190**
- Deduplication / `work_id` assignment: **complete and frozen for BAII.3**
- F0–F2 modified: **no**
- F3A or F3B modified: **no**
- Candidate discovery authorized: **no**
- Scientific results computed: **no**
- BAII.4 prospective design-impact assessment: **complete and frozen**
- BAII.5 final F3A gate decision: **`F3A_DESIGN_RECONSIDERATION_REQUIRED`**
- Formal novelty assessment performed: **no**
- Priority claim authorized: **no**

The directory already contained `AUDIT_MATRIX.csv` and `SEED_SOURCES.csv` before BAII.1. They remain unchanged. `SEED_SOURCES.csv` is pre-existing seed/context material, not a systematically retrieved or screened BAII corpus. `AUDIT_MATRIX.csv` is a legacy empty template and is not the normative BAII.1 screening schema; future BAII screening uses `screening_schema.csv`.

The previously tracked `PROTOCOL.md` established the literature gate. BAII.1 normalized it to lowercase `protocol.md`; Git history preserves the earlier version. The immutable v1.0.0 design remains tagged `bibliographic-audit-ii-design-v1`. Amendment v1.1.0 documents the two incomplete BAII.2 attempts and changes only SciX parser serialization of the already frozen exact `date` range.

## Design-freeze files

At the immutable `bibliographic-audit-ii-design-v2` tag, the v1.1.0 design freeze comprises:

- `README.md`
- `protocol.md`
- `search_plan.yaml`
- `screening_schema.csv`
- `audit_preregistration.json`
- `amendments/BAII_DESIGN_V1_1_0.md`
- `SHA256SUMS.txt`

`screening_schema.csv` is unchanged from v1.0.0. At the design tag, `SHA256SUMS.txt` hashes the six content files above and never hashes itself. After BAII.2 the working-branch `README.md` advances status, so the working-branch checksum manifest updates only that README checksum; the original design-v2 checksum manifest remains immutable in Git history.

The v1.0.0 tag must not be moved or replaced. Version 1.1.0 is frozen by annotated tag `bibliographic-audit-ii-design-v2` at commit `a53ea8c5935e686df1fe8680b9c36bdf5111d05e`. If another material error is discovered, retrieval stops, the incident is documented, the protocol version is incremented again, and a new immutable design tag is created.


## BAII.2 raw-corpus freeze

The normative BAII.2 retrieval completed all 12 frozen query × provider executions successfully.
The frozen ledger contains 322 raw hits. BAII.3 maps every hit exactly once into 190 unique `work_id` entities while preserving all raw-hit provenance.

The raw archive is `bibliographic_audit_ii_raw_corpus_v1.zip` with SHA-256
`9dd526ecf58b6fed8af4d2902989dc6b8d4255126fd82aed02ce59d07537f993`.

## BAII.3 work-resolution and screening freeze

BAII.3 resolves the 322 raw hits into **190 unique intellectual works** and **283 bibliographic versions**, with exactly one preferred version per work. The automatic resolution layer produced 201 exact bibliographic components; 11 explicit same-work adjudications reduced this to 190 works, while 11 explicit distinct-work adjudications prevented false fuzzy merges. No relationship remains unresolved.

Final screening at work level yields **40 `INCLUDE_FOR_BAII4`**, **33 `BACKGROUND_ONLY`**, **117 `EXCLUDE`**, and **0 access-limited unresolved decisions**. `SEED_SOURCES.csv` remains outside the systematic denominator; four seeds (S005–S008) also occur independently in the systematic corpus.

BAII.3 did not assign `relevance_labels`, F3A/F3B design impact, Manuscript 1 positioning impact, or novelty. BAII.4 subsequently extracted the 40 included works and froze descriptive overlap plus prospective impact annotations against the pre-frozen F3 comparison reference. Novelty remains unassessed and the final F3A gate remains reserved for BAII.5.


## BAII.4 structured extraction and overlap freeze

Before systematic extraction, the documentary F3 comparison target was frozen in
`extraction/f3_overlap_reference.json` (SHA-256
`1b6be4a17d23457d3164b23c4b16557467e84ae44bbb35df57064b7c9566639e`) and committed at
`9ae33ce9458ceb826e1efbea31a4f96843334f5d`.

BAII.4 extracted **40/40** included works, retaining **160 extraction-evidence rows**, **40
work-level overlap assessments**, **62 dimensional overlap-evidence rows**, and **40 source-access
records**. No work is blocked. Five work records retain explicitly documented source-access
limitations and unresolved detail is encoded as `NOT_REPORTED`.

Descriptive overlap is **2 DIRECT / 36 PARTIAL / 2 CONTEXT_ONLY** for F3A and **7 DIRECT / 2
PARTIAL / 31 CONTEXT_ONLY** for F3B. The impact rubric records **2 `F3A_REDRAFT_REQUIRED`**, **13
`F3A_DESIGN_ADJUSTMENT_POSSIBLE`**, **9 `F3B_DESIGN_ADJUSTMENT_POSSIBLE`**, and **23
`POSITIONING_ONLY`** assignments. These are prospective literature-gate annotations, not actual
changes to F3A/F3B and not novelty or precedence claims.

BAII.5 has now completed the final synthesis and frozen the pre-F3A gate decision. No BAII.3 screening field or BAII.4 extraction/overlap field was retrospectively modified.

## BAII.5 final synthesis and gate freeze

BAII.5 reviewed all **15** works carrying prospective F3A impact, including the two
`F3A_REDRAFT_REQUIRED` / `DIRECT` overlap works, assessed all **11** comparator candidates, and
represented all **9** F3B-impact works. The systematic denominator remains **190 works / 40 primary
extracted works**.

The frozen hierarchical gate resolves to:

`F3A_DESIGN_RECONSIDERATION_REQUIRED`

BAIIW0001 independently satisfies the highest gate branch through direct catalogue-scale TESS QPP
overlap with sufficient evidence. BAIIW0003 independently reinforces the catalogue/classification
overlap but retains its documented source-access limitation; unresolved implementation details
remain `NOT_REPORTED`.

The gate does not cancel F3A and is not a novelty verdict. It means that the next task must
prospectively reformulate and freeze F3A while addressing the open BAII.5 requirements before any
catalogue-scale execution.

F0–F2 remain frozen. F3A and F3B remain scientifically unfrozen.

Next task: **F3A.1 — prospective reconsideration and freeze of the F3A scientific design from the
BAII.5 gate.**
