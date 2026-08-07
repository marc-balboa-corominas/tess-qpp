# Repository and Artifact Policy

## Purpose

This repository is the active version-controlled workspace for the TESS QPP research program.

It is not intended to contain every generated scientific artifact.

## Storage roles

### GitHub

GitHub contains:

- maintained source code;
- phase-specific workflows;
- tests;
- configuration;
- protocols under active development;
- selected textual and tabular scientific evidence;
- project documentation;
- manuscript sources.

### OSF

OSF is the canonical location for:

- frozen phase snapshots;
- preregistrations;
- governance records;
- complete historical evidence packages;
- immutable research materials.

### Zenodo

Zenodo is reserved for public, citable releases and DOI-bearing research outputs.

## Data policy

Raw or large observational data are not committed to Git.

Materialized numerical arrays, runtime checkpoints, large regenerated execution tables, and temporary artifacts are excluded from the Git repository unless a specific scientific reason requires otherwise.

## Historical evidence

Frozen historical evidence is never silently rewritten.

Any correction to a frozen result must be documented through an explicit erratum, superseding artifact, or decision record.

## Privacy and publication readiness

Because this repository may eventually become public, private credentials, personal filesystem paths, email addresses not intended for publication, and machine-specific information must not enter Git history.

## Reproducibility

The repository should retain sufficient code, configuration, provenance, and documentation to connect scientific claims to the corresponding frozen evidence and archival objects.