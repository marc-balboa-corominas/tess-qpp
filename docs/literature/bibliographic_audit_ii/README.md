# Bibliographic Audit II

**STATUS:** `PROTOCOL FROZEN — SEARCH NOT YET EXECUTED`

Bibliographic Audit II is the literature gate between the frozen F0–F2 foundation and the future freeze of F3A. BAII.1 freezes the search, screening, versioning, extraction and design-impact rules before any systematic search of the recent corpus.

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

## BAII.1 boundaries

- Systematic searches executed: **0**
- Scientific papers screened under BAII: **0**
- F0–F2 modified: **no**
- F3A design frozen: **no**
- Candidate discovery authorized: **no**
- Scientific results computed: **no**
- Novelty verdicts authorized: **no**

The directory already contained `AUDIT_MATRIX.csv` and `SEED_SOURCES.csv` before BAII.1. They remain unchanged. `SEED_SOURCES.csv` is pre-existing seed/context material, not a systematically retrieved or screened BAII corpus. `AUDIT_MATRIX.csv` is a legacy empty template and is not the normative BAII.1 screening schema; future BAII screening uses `screening_schema.csv`.

The previously tracked `PROTOCOL.md` established the literature gate. BAII.1 updates that protocol and normalizes its repository filename to lowercase `protocol.md`; Git history preserves the earlier version.

## Freeze files

The BAII.1 freeze comprises:

- `README.md`
- `protocol.md`
- `search_plan.yaml`
- `screening_schema.csv`
- `audit_preregistration.json`
- `SHA256SUMS.txt`

`SHA256SUMS.txt` hashes the other five files and never hashes itself.

If a material error is discovered after the annotated design tag, the existing tag must not be moved or replaced. The incident must be documented, the protocol version incremented, and a new design tag created.
