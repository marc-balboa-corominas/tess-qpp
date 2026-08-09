# Bibliographic Audit II — Design Amendment v1.1.0

**Audit ID:** `tess_qpp_bibliographic_audit_ii_v1`  
**Amendment version:** `1.1.0`  
**Amendment date:** `2026-08-09`  
**Status:** `AMENDED_AND_REFROZEN_BEFORE_BAII2_RESTART`  
**Prior immutable design:** `bibliographic-audit-ii-design-v1` @ `24b3ddde7a9b7baf35f6b236d83e80ec20571c95`  
**Target design tag:** `bibliographic-audit-ii-design-v2`

## Reason

BAII.2 exposed a technical incompatibility in the six SciX query strings frozen in v1.0.0. The semantic `abs:` expressions were accepted by SciX, but the exact machine-readable `date` ranges contained unescaped timestamp colons. Every SciX execution therefore failed with HTTP 400 `INVALID_SYNTAX_CANNOT_PARSE`.

The scientific search design is not being revised. This amendment is restricted to parser-safe serialization of the already frozen exact date range.

## Preserved incidents

### Attempt 01 — authentication failure

`attempt01_ads401`

- SciX/ADS complete executions: 0/6
- arXiv complete executions: 6/6
- failure: HTTP 401 before SciX record retrieval
- raw ledger rows produced from the completed arXiv calls: 73
- deterministic rebuild: `RAW_LEDGER_REBUILD_EXACT`
- review-bundle SHA-256: `3c3ebc12ff15c2aae86c9ae83b15ed86022cff84ca42259c2bafe0897596bb25`

### Attempt 02 — SciX parser failure

`attempt02_scix400_syntax`

- SciX complete executions: 0/6
- arXiv complete executions: 6/6
- failure: HTTP 400 `INVALID_SYNTAX_CANNOT_PARSE` on all six SciX strings
- raw ledger rows produced from the completed arXiv calls: 73
- deterministic rebuild: `RAW_LEDGER_REBUILD_EXACT`
- review-bundle SHA-256: `e5a4d9e0a3f2dbea6e76caa8496579c07c9dd1244a38975ecf2120ad4b743b90`

Neither attempt is the normative BAII.2 raw corpus. Both remain incident evidence outside the final corpus and must not be merged into it.

## Parser diagnostic

After authentication was verified independently, four non-corpus parser probes were executed against SciX:

| Probe | Form | Result | `numFound` |
|---|---|---:|---:|
| `P0_ABS_ONLY` | fielded `abs:` control | OK | 1829 |
| `P1_PUBDATE_DOCUMENTED` | monthly `pubdate` range | OK | 245 |
| `P2_DATE_QUOTED` | exact quoted `date` timestamps | OK | 245 |
| `P3_DATE_ESCAPED` | exact `date` timestamps with escaped colons | OK | 245 |

These probes were technical parser diagnostics, not corpus retrievals. No returned bibliographic content was screened or used to alter the search design.

## Frozen correction

v1.0.0:

```text
date:[2024-01-01T00:00:00.000Z TO 2026-08-07T23:59:59.999Z]
```

v1.1.0:

```text
date:[2024-01-01T00\:00\:00.000Z TO 2026-08-07T23\:59\:59.999Z]
```

This is the only change to the six SciX query strings.

## Invariants

The amendment changes none of the following:

- six semantic query families or their Boolean content;
- `2024-01-01` recent-window start;
- `2026-08-07` search cutoff;
- any arXiv query string;
- inclusion criteria I1–I7;
- exclusion criteria E1–E6;
- relevance labels or impact categories;
- `work_id`/version policy;
- candidate-discovery prohibition;
- F0–F2;
- F3A or F3B design;
- novelty/priority rules.

No complete 12/12 raw corpus has yet been frozen. No screening, deduplication, `work_id` assignment, inclusion/exclusion decision, design-impact assessment, or novelty assessment has occurred.

## Restart rule

After v1.1.0 is committed and annotated-tagged as `bibliographic-audit-ii-design-v2`, BAII.2 restarts from empty normative `local_archive/bibliographic_audit_ii/baii2_raw/` and `docs/literature/bibliographic_audit_ii/retrieval/` locations.

The v1 tag is immutable and must not be moved. If another material defect appears, stop retrieval and document a new amendment rather than editing a frozen query silently.
