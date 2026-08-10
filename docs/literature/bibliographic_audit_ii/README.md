# Bibliographic Audit II

**STATUS:** `DEDUPLICATION AND SCREENING FROZEN — STRUCTURED EXTRACTION NOT STARTED`

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
- Design-impact or novelty verdicts authorized: **no**

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

BAII.3 does not assign `relevance_labels`, F3A/F3B design impact, Manuscript 1 positioning impact, or novelty. Detailed structured extraction has not started. BAII.4 is the first task permitted to extract detailed methods/results and assess observational or methodological overlap.
