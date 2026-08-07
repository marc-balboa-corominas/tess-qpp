# Bibliographic Audit II Protocol

**Audit ID:** `TESS_QPP_BIBLIOGRAPHIC_AUDIT_II_V1`

**Search cutoff:** 2026-08-07

**Status:** `PROTOCOL_ESTABLISHED_AUDIT_OPEN`

## Objective

Determine the current literature position of the TESS QPP project before freezing the Phase 3A observational design.

The audit is specifically intended to test whether the planned combination of catalogue-scale observational robustness, numerical diagnostics, selection-effect characterization, injection-recovery, and held-out validation is already represented in the literature or requires repositioning.

## Scope

The core search interval is 2015 through the search cutoff.

Earlier work may be included when required to establish methodological provenance.

Priority is given to:

- QPP detection methodology;
- AFINO and Fourier model comparison;
- stellar QPP catalogues;
- TESS QPP studies;
- 20-second or other high-cadence stellar flare studies;
- methodological robustness and benchmark studies;
- preprocessing, temporal-window, detrending, and colored-noise effects;
- synthetic QPP benchmarks;
- injection-recovery studies;
- machine-learning QPP detection;
- selection functions and validation;
- recent reviews relevant to the interpretation of stellar QPP populations.

## Search resources

The audit will use multiple complementary resources:

- NASA ADS / SciX;
- arXiv;
- journal and DOI records;
- NASA TESS publication records;
- backward citation chaining;
- forward citation chaining;
- associated public code and data repositories where scientifically relevant.

No single search engine is treated as exhaustive.

## Core search families

Searches will combine terms from the following families.

### TESS and observational samples

- TESS quasi-periodic pulsations
- TESS QPP stellar flares
- 20 second cadence TESS QPP
- short-period stellar QPP
- TESS QPP catalogue
- TESS flare catalogue QPP

### Methodological robustness

- QPP detection robustness
- QPP temporal window trimming
- QPP detrending preprocessing
- QPP colored noise detection
- AFINO robustness
- AFINO window
- AFINO synthetic benchmark

### Validation and selection effects

- QPP injection recovery
- QPP synthetic ground truth
- QPP false positive detection
- QPP selection effects
- QPP detection benchmark
- QPP held-out validation
- QPP machine learning detection

## Inclusion criteria

A source is included in the detailed audit when at least one of the following applies:

- it introduces or evaluates a QPP detection method relevant to this project;
- it performs a catalogue-scale stellar or solar QPP analysis;
- it uses TESS for QPP detection or population analysis;
- it evaluates temporal-window, preprocessing, detrending, noise, or numerical robustness;
- it performs synthetic validation, injection-recovery, or method comparison;
- it materially affects the novelty or interpretation of F3A, F3B, Manuscript 01, or later population work;
- it is a recent review that identifies relevant methodological or observational developments.

## Exclusion criteria

A source may be recorded but excluded from detailed comparison when it is:

- a purely theoretical QPP mechanism paper with no direct methodological or observational-design implication;
- an isolated case study with no methodological relevance to the project;
- a duplicate conference abstract superseded by a full paper;
- a secondary source when the corresponding primary source is available.

Exclusion must be documented rather than silent.

## Extraction fields

For each included source, the audit will record:

- bibliographic identity;
- observational domain;
- mission and cadence;
- sample size and construction;
- QPP detection method;
- relevant thresholds;
- window definition;
- preprocessing and detrending;
- treatment of gaps or invalid inputs;
- numerical diagnostics;
- synthetic ground truth;
- injection-recovery;
- independent or held-out validation;
- selection-effect treatment;
- population claims;
- reproducibility resources;
- overlap with F3A;
- overlap with F3B;
- implications for manuscript novelty.

## Novelty rule

No statement such as `first`, `novel`, `unprecedented`, or `not previously studied` is authorized from an individual source comparison.

Novelty is assessed only after the search, extraction, and citation-chaining stages are complete.

## Relationship to Phase 3A

Bibliographic Audit II does not authorize candidate discovery or scientific execution.

It is a design-stage literature audit.

The F3A cohort and analysis design remain unfrozen until this audit closes.

## Relationship to OSF

The final audit package will be preserved in the private OSF component:

`02 — Bibliographic Audit II`

The working Git representation contains the protocol, source matrix, synthesis, and design implications suitable for version control.