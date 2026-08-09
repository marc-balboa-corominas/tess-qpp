# Bibliographic Audit II

**STATUS:** `DESIGN v1.1.0 FROZEN — BAII.2 RESTART PENDING`

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

- Complete 12/12 BAII.2 raw corpus frozen: **no**
- Incomplete technical retrieval attempts preserved: **2**
- Successful provider executions before v1.1.0: **12 arXiv executions across two attempts**
- Failed provider executions before v1.1.0: **12 SciX executions across two attempts**
- Scientific papers screened under BAII: **0**
- Deduplication / `work_id` assignment: **0**
- F0–F2 modified: **no**
- F3A or F3B modified: **no**
- Candidate discovery authorized: **no**
- Scientific results computed: **no**
- Design-impact or novelty verdicts authorized: **no**

The directory already contained `AUDIT_MATRIX.csv` and `SEED_SOURCES.csv` before BAII.1. They remain unchanged. `SEED_SOURCES.csv` is pre-existing seed/context material, not a systematically retrieved or screened BAII corpus. `AUDIT_MATRIX.csv` is a legacy empty template and is not the normative BAII.1 screening schema; future BAII screening uses `screening_schema.csv`.

The previously tracked `PROTOCOL.md` established the literature gate. BAII.1 normalized it to lowercase `protocol.md`; Git history preserves the earlier version. The immutable v1.0.0 design remains tagged `bibliographic-audit-ii-design-v1`. Amendment v1.1.0 documents the two incomplete BAII.2 attempts and changes only SciX parser serialization of the already frozen exact `date` range.

## Freeze files

The current v1.1.0 design freeze comprises:

- `README.md`
- `protocol.md`
- `search_plan.yaml`
- `screening_schema.csv`
- `audit_preregistration.json`
- `amendments/BAII_DESIGN_V1_1_0.md`
- `SHA256SUMS.txt`

`screening_schema.csv` is unchanged from v1.0.0. `SHA256SUMS.txt` hashes the six content files above and never hashes itself.

The v1.0.0 tag must not be moved or replaced. Version 1.1.0 must be committed separately and annotated-tagged as `bibliographic-audit-ii-design-v2`. If another material error is discovered, retrieval stops, the incident is documented, the protocol version is incremented again, and a new immutable design tag is created.
