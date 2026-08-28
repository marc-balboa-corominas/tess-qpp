# DR-015 — Manuscript 1 submission-package freeze

STATUS: APPROVED / SUBMISSION-READY / GIT-OSF FREEZE AUTHORIZED

## Decision boundary
M1.7 is built exclusively from the author-approved M1.6 freeze (`manuscript1-author-approved-v1`, commit `d1007edcdbcf98b809ed46b0810fd62148f7b2af`) plus authoritative M1.5-v2 submission metadata (`manuscript1-submission-plan-v2`, commit `e01db0ae1a47fac6de77bef7477dd119ab9f5d14`). M1.4 remains historical input only and is not the source manuscript for this conversion.

## Permitted changes
AASTeX class and author macros, affiliation/corresponding metadata, line numbers, figure/table wrappers and filenames, bibliography formatting for the same eight scientific works, acknowledgments, author contributions, data/code statements, UAT/topical-corridor metadata, archive dataset metadata, and portal/arXiv packaging.

## Prohibited changes
No scientific rewrite, new scientific claim, scientific number, scientific work, statistic, figure, table, inference, AFINO execution, simulation, or statistical analysis.

## Scientific identity
The final M1.7 package preserves 27/27 frozen claims, accounts for 120/120 frozen scientific numeric identities, retains 8/8 scientific works, preserves the five author-approved figure files byte-exactly, and preserves the scientific content of all four author-approved tables. Table 1 uses only the AASTeX-authorized multi-page wrapper adaptation required for readable portrait rendering.

## AASTeX and compile identity
AASTeX 7.0.2 was materialized from the official AAS distribution. The flat portal bundle and arXiv source bundle both compile independently. The final submission PDF is 32 pages with SHA-256 `612ff8e1442647da10849251a252107d0bc8f5530c008d5cb006d1996c124197`.

## Final visual preflight
The final PDF was rendered and inspected page-by-page on 2026-08-28. Result: 32/32 pages PASS.

Specific checks:
- front matter and author metadata are readable;
- Table 1 is readable across pages 6–7 with all six evidence-plane rows retained;
- all five figures are readable;
- Figure 4 is intentionally rotated using the AASTeX-native `turnpage` mechanism on page 23 and retains the structural N/E cells;
- Tables 2 and 3 are readable;
- Table 4 is readable across pages 27–28;
- the references render completely across pages 31–32;
- no clipping, overlaps, broken references, missing citations, or placeholders are present.

Two overfull hbox and two overfull vbox warnings remain in the final TeX transcript. Direct rendered-page inspection shows that they are non-blocking and do not produce visible clipping or unreadable content.

## Tooling incidents
M1_7_TOOL_001–M1_7_TOOL_018 were all repaired before commit and have scientific effect NONE.

M1_7_TOOL_010 was a Windows ZIP path-normalization verifier defect in the first freeze attempt. That attempt aborted before payload installation, staging, commit, tag, push, or OSF snapshot creation.

M1_7_TOOL_011 was an over-strict staged-diff whitespace gate in the second freeze attempt. The gate treated upstream whitespace already present in the exact official AASTeX 7.0.2 class/BST files as a repository defect. The second attempt had installed the exact submission-ready payload and staged the 55 M1.7 paths, but aborted before commit, tag, push, or OSF snapshot creation. The staged state is explicitly recovered before the final freeze.

M1_7_TOOL_012 was a Git `core.autocrlf` byte-identity risk exposed by the same pre-commit log. The final freeze stages with `core.autocrlf=false`, verifies all 55 staged blobs byte-for-byte against the independently validated payload, applies `git diff --check` to every non-vendor path, and exempts only the four byte-verified official AAS vendor files from whitespace-style checking. This preserves the exact reviewed/package bytes in Git and in the Git-derived OSF snapshot.

M1_7_TOOL_013 was a Windows file-writability abort in the third freeze attempt. The script had successfully recovered the exact reviewed candidate but then received `PermissionError` while replacing `submission/final/arxiv_bundle/fig1.pdf`. The attempt aborted during payload installation, before staging, commit, tag, push, or OSF snapshot creation.

M1_7_TOOL_014 was an over-broad unchanged-asset writability preflight in the fourth freeze attempt. That script correctly identified the residual working tree as 53 exact reviewed files plus 2 exact v3-payload files, with 0 unknown files, but then unnecessarily required write access to all 55 paths. Windows denied attribute modification on the unchanged `arxiv_bundle/fig1.pdf`, so the attempt aborted before any content restoration/install, staging, commit, tag, push, or OSF snapshot creation. The preflight may have cleared the Windows read-only attribute on an earlier prefix of files, but it did not change tracked file content or repository history.

The final freeze therefore follows a minimal-mutation rule: unchanged assets that already equal the final payload are never opened for writing; only files whose bytes actually differ from the final payload are preflighted and atomically replaced; all 55 final working-tree bytes are then verified against the final payload before staging.

M1_7_TOOL_015 was a Git clean-filter/index-normalization blocker in the fifth freeze attempt. The exact v5 payload was installed and validated successfully, but normal `git add` staging transformed the official AASTeX class bytes despite `core.autocrlf=false`; the 55/55 staged-byte gate detected the difference and aborted before commit, tag, push, or OSF snapshot creation. The final freeze no longer uses `git add` for the M1.7 payload. Instead, each exact payload byte stream is written as a raw Git blob with `git hash-object -w --stdin`, and the index is populated explicitly with `git update-index --cacheinfo`. The staged 55/55 byte identity is then reverified before commit.

M1_7_TOOL_016 was a retry-state classification defect exposed by immediately rerunning the fifth freeze script after TOOL_015. That rerun correctly unstaged the 55 paths, but its recovery classifier allowed only reviewed/v3 states and did not recognize the already fully installed exact v5 payload, so it aborted before changing content or history.

M1_7_TOOL_017 was a tracked Git-attributes EOL-policy conflict identified by the read-only diagnostic after the sixth freeze attempt. The repository root `.gitattributes` applied `text=auto eol=lf` to ten byte-exact CRLF assets (two official AASTeX class files and eight submission evidence/metadata CSV files), creating a predicted post-commit dirty state even though the raw working-tree and staged bytes were 55/55 identical to the validated payload. The final freeze appends twelve exact-path exceptions (`-text -eol`): the four official AAS class/BST vendor files plus the eight CRLF CSV files. The exceptions are repository policy only; they do not alter submission-package bytes.

M1_7_TOOL_018 was a `git diff --check` CRLF false-positive blocker in the sixth freeze attempt. Raw byte-exact staging succeeded 55/55, but Git reported each CRLF terminator in the eight CSV files as trailing whitespace. Independent byte inspection found 0 bare-LF violations and 0 actual space/tab-before-EOL violations in all eight files. The final freeze therefore uses a CRLF-aware byte-level whitespace audit for those eight exact CSV assets, preserves byte-exact upstream vendor files, and retains standard `git diff --check` for every other project-authored staged path.

The freeze commit intentionally contains 56 changed paths: the 55 submission-package paths plus the root `.gitattributes` repository-policy update required to make exact-byte checkout/status behavior reproducible. The OSF submission-ready snapshot remains restricted to the 55 submission-package paths and does not include `.gitattributes`.

These are tooling/formatting incidents only. In particular, M1_7_TOOL_006 repaired the AASTeX/pdflscape global-rotation conflict, M1_7_TOOL_007 repaired the overheight Table 1 wrapper, M1_7_TOOL_008 repaired stale multi-pass compile evidence, and M1_7_TOOL_009 corrected an over-constrained table-byte-identity test.

## Submission state
`MANUSCRIPT1_SUBMISSION_PACKAGE_VALIDATION_PASS` is the required final validator state.

The package is ready for direct author submission to The Astrophysical Journal without an additional scientific, bibliographic, authorial, or visual decision. Actual journal submission and actual arXiv upload have not been performed.

## Freeze
Commit subject: `docs(manuscript1): freeze ApJ submission-ready package`

Annotated tag: `manuscript1-submission-ready-v1`

OSF archive: `05 — Manuscript 1/manuscript1_submission_ready_v1.zip`

This new M1.7 archive does not replace the M1.6 author-approved archive.
