# Bibliographic Audit II — BAII.2 retrieval

**STATUS:** `RAW CORPUS FROZEN — SCREENING NOT STARTED`

The raw bibliographic corpus was retrieved under `bibliographic-audit-ii-design-v2`
(commit `a53ea8c5935e686df1fe8680b9c36bdf5111d05e`) using the six frozen query families
against SciX and arXiv.

## Frozen retrieval

- planned executions: **12**
- successful executions: **12**
- partial executions: **0**
- failed executions: **0**
- raw hit rows: **322**
- SciX raw hits: **249**
- arXiv raw hits: **73**
- deterministic ledger rebuild: **`RAW_LEDGER_REBUILD_EXACT`**
- OSF snapshot: **`bibliographic_audit_ii_raw_corpus_v1.zip`**
- OSF snapshot SHA-256: **`9dd526ecf58b6fed8af4d2902989dc6b8d4255126fd82aed02ce59d07537f993`**

Duplicate hits are expected and preserved. `SEED_SOURCES.csv` remains separate from the systematic
retrieval. No `work_id` exists yet. No paper has been included or excluded. No scientific screening,
deduplication, design-impact assessment, or novelty assessment has been performed.

The raw provider payloads are archived outside Git under
`local_archive/bibliographic_audit_ii/baii2_raw/` and in the OSF raw-corpus snapshot.

The OSF ZIP uses a two-stage hash binding because a ZIP cannot literally contain a manifest that
already stores that same ZIP's physical SHA-256. The snapshot contains the exact pre-archive manifest;
the final Git `retrieval_manifest.json` records the physical archive hash and the SHA-256 of that
snapshot-internal manifest.
