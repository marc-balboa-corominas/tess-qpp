# Manuscript 1.8 - arXiv neutral bundle

## Status

**AUTHOR-APPROVED JOURNAL-NEUTRAL PREPRINT - TRANSPARENCY AMENDMENT APPLIED - ARXIV SUBMISSION PENDING**

This directory contains the journal-neutral public-preprint branch of Manuscript 1.

## Scientific source

The normative scientific source is the M1.6 author-approved manuscript:

- Tag: `manuscript1-author-approved-v1`.
- Commit: `d1007edcdbcf98b809ed46b0810fd62148f7b2af`.

The historical M1.7 journal-specific package is preserved in the repository but is not normative for the arXiv-neutral content or pagination.

## Neutral-preprint rules

The arXiv-neutral version is journal-independent.

It contains:

- The frozen Manuscript 1 title, abstract, sections, figures, tables, references, conclusions, and data/code statement.
- No journal-specific submission banner.
- No journal-specific running heads.
- No journal-specific line numbering.
- A landscape rendering of Figure 4 for readability.
- A generative-AI transparency acknowledgment.

Scientific changes relative to the author-approved scientific master are not authorized.

## Generative-AI transparency amendment

Before public arXiv submission, the neutral manuscript was amended to include the following acknowledgment:

> Generative AI tools were used selectively for editorial support and technical assistance, including the review and refinement of portions of the code and the preparation of some visualizations. The research workflow, scientific analysis, validation of results, and interpretation were carried out and verified by the author, who takes full responsibility for the content of this work.

This is a transparency-only editorial amendment.

It does not modify the scientific results, numerical values, figures, tables, references, claims, evidence-plane assignments, conclusions, or interpretations.

The initial neutral freeze remains preserved as:

`manuscript1-arxiv-neutral-v1`

A subsequent pre-submission freeze should preserve the transparency-amended state without moving or rewriting the original tag.

## Directory layout

- `bundle/` contains only files required to compile the arXiv preprint.
- `source/` contains the maintained neutral manuscript source.
- `evidence/` contains validation and provenance records.
- `review/` contains author-review and approval records.

The `bundle/` and `source/` copies of `manuscript_arxiv_neutral.tex` must remain synchronized for the public submission freeze.

## Author-reviewed presentation

The author-reviewed neutral manuscript uses:

- 22 pages.
- 5 figures.
- 4 tables.
- Figure 4 as the single landscape page.
- Clean section and figure placement established during the final author visual review.
- `Acknowledgments` immediately before `Data, code, and reproducibility resources`.

The preprint should not be compressed merely to preserve page count if a future required transparency or editorial statement causes natural reflow.

## Publication state

Current state:

- Scientific content: **frozen**.
- Author review: **complete**.
- Journal-neutral preparation: **complete**.
- Generative-AI acknowledgment: **included**.
- Public-infrastructure synchronization: **in progress**.
- arXiv metadata preparation: **in progress / not yet publicly submitted**.
- arXiv submission: **pending**.
- Journal submission: **pending**.
- Peer review: **not yet completed**.

No arXiv identifier, journal reference, DOI, or peer-review claim is recorded here until it exists.

## Preservation rule

Historical freezes, hashes, audits, and submission packages are not rewritten to make them appear current. Each frozen state remains recoverable through Git history and its corresponding tag or evidence record.

The current public-preprint state should be frozen only after the transparency-amended source and bundle have been validated and the corresponding public infrastructure has been synchronized.
