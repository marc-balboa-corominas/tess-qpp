# DR-001 — Preservation model for the F0–F2 foundation

**Date:** 2026-08-07  
**Status:** Accepted

## Context

Phases F0–F2 produced a complete historical research package containing source code, scientific results, execution artifacts, numerical materializations, reports, audits, figures, logs, and provenance information.

Using the complete package directly as the active Git repository would mix immutable historical evidence with future development and would unnecessarily version large regenerated or runtime artifacts.

## Decision

The F0–F2 foundation will use a dual preservation model.

### Complete archive

The complete byte-preserving historical snapshot is stored in the private OSF component:

`01 — Frozen F0–F2 Foundation`

https://osf.io/539ub/

### Git documentary foundation

The project Git repository contains a curated documentary subset under:

`foundation/f0-f2/`

This subset preserves scientifically relevant source, documentation, evidence, and selected derived outputs while excluding material unsuitable for long-term Git history.

## Consequences

F0–F2 is treated as historical and frozen.

Phase 3 and subsequent work must be developed outside the frozen foundation.

Historical F0–F2 artifacts must not be silently refactored or rewritten.

Future public releases may be derived from the archive only after a dedicated release and privacy audit.

## Integrity reference

Canonical archive SHA-256:

`62d06b47d596b0373459d1284093e0f9532e3847e8402bb6dcc1ec653636a2a3`