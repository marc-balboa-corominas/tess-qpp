# Phase 3B.6 ? Blind single-use HELDOUT execution report

## Scope and provenance

Phase 3B.6 executed the preregistered blind HELDOUT inference stage of the TESS QPP robustness programme. Its purpose was deliberately narrower than scientific evaluation: execute the frozen AFINO baseline on the materialized HELDOUT payloads, derive the frozen blind classification for every HELDOUT decision, validate execution integrity, and stop before any ground-truth join or performance calculation. The HELDOUT materialization originated in F3B.5 at commit `690b54212ffc91d5d396da02db2bcd883b359e6b`, tag `phase3b-heldout-materialization-v1`. No generator execution or rematerialization was part of this stage.

The final decision rule was inherited unchanged from the DEVELOPMENT freeze: AFINO 0.5 BASELINE with `delta_BIC01 > 10 AND delta_BIC21 > 10`, using strict greater-than comparisons. No threshold search, candidate search, rule refit, or post-HELDOUT tuning was performed.

## Runner and environment provenance

The HELDOUT adapter reused the frozen F3B.3 numerical runner rather than implementing a new AFINO core. The execution adapter SHA-256 was `dc270bcc8576f7eb82e5efb013ab95c7c975712ef4274f446f82d208f690c719`. AFINO remained version 0.5 at source commit `6aceac9518fc8056052807e666da9d0c8bebb010`. The scientific model identities were M0=`pow_const`, M1=`pow_const_gauss`, and M2=`bpow_const`; the low-frequency cutoff remained 0.025 Hz and the external optimizer seed remained 0.

Before HELDOUT execution, the DEVELOPMENT regression audit established 18/18 exact replay matches. The execution environment was the previously frozen Python 3.13.13 / NumPy 2.5.1 / SciPy 1.18.0 / AFINO 0.5 environment. No dependency update or scientific-code modification was introduced during the HELDOUT run.

## Authorization and tooling recovery

The single-use execution was governed by authorization V3 committed at `faf688a2b8c260cdee0d92c181971d0154df4532`. Its firewall authorized HELDOUT AFINO execution while explicitly withholding authorization for truth joining, HELDOUT metrics, candidate search, threshold mutation, and rule refitting.

A tooling incident, F3B6-TOOL-007, occurred before the successful HELDOUT execution. The initial HELDOUT adapter had omitted normalization through the frozen F3B.3 `validate_job` contract, causing `KeyError: 'model_name'` before AFINO model execution. The failed checkpoint contained zero result rows and zero invocation rows; no scientific HELDOUT fit was completed or persisted. The adapter was corrected only to normalize HELDOUT jobs through the frozen DEVELOPMENT contract and strengthen preflight. The recovery was committed before scientific execution resumed. No AFINO source, HELDOUT payload, HELDOUT plan, seed, final rule, or environment was changed.

## Blind checkpoint execution

The successful checkpoint execution followed the frozen sequence exactly: 3000, 3000, 3000, 1800, and finally 0 new jobs for the idempotence invocation. The completed SQLite checkpoint contains exactly 10,800 successful model results: 3,600 M0, 3,600 M1, and 3,600 M2. No completed job had a non-OK status. The final invocation observed 10,800 existing jobs, executed zero additional jobs, and left zero pending jobs, demonstrating checkpoint idempotence after completion.

The checkpoint SHA-256 is `f652555516bf830b82a23c1911a47d8ce72e2851b11b97b11614c23c6f944945`. Export to the blinded results table preserved all 10,800 job identities and result-core hashes with zero checkpoint-to-CSV mismatches. The blinded results CSV SHA-256 is `2a55963e4b916a997efa5db5893e1b49f6a091b536fa6b98099da7733af7fe30`.

## Blind rule application and payload identity

The 10,800 model outputs were grouped into the 3,600 preregistered BASELINE decisions, with exactly one M0, M1, and M2 result per decision. The blind assembler independently checked the frozen decision grid and payload identities before applying the final rule. All 3,600 decisions received status `VALID`. Independent validator recalculation produced zero decision mismatches.

The decisions table SHA-256 is `bc7c8720d9cdeed249301f986bcf960ef46c2d75ec4e38356a0dfa42ee3b3ab1`. Although the row-level `qpp_selected` classification is now frozen, Phase 3B.6 deliberately does not calculate or report its aggregate count or fraction. Those values are HELDOUT outcomes and are not required to establish execution integrity.

Payload identity checks produced zero mismatches across the frozen plan, decision grid, payload manifest, checkpoint, and exported blinded products. The persistent F3B.5 arrays were hash-checked and were not regenerated.

## Temporal contract and operational diagnostics

The temporal diagnostic independently reconstructed each retained time payload and repeated the AFINO structural sampling contract. All 3,600 decisions matched `mean(diff(time_seconds))` across M0, M1, and M2, and all 3,600 matched the strictly positive bins from `numpy.fft.fftfreq`. The historical `median(dt)` and `rfftfreq` quantities remain diagnostic-only. The temporal diagnostic SHA-256 is `1f15cc39f147e923d89697d400d3979a73e168ab3096daaac5678e7f30da715f`.

Operational diagnostics are recorded in `f3b6_execution_audit.json`. They are restricted to execution properties such as call counts, warnings, parameter-bound flags, runtime when available, and convergence-status counts. They contain no scientific performance evaluation.

## Independent validation and blinding boundary

The independent global validator verified the complete chain from the 10,800-job frozen plan to checkpoint, exported results, 3,600 blind decisions, payload identities, and temporal diagnostic. It found zero duplicate job IDs, zero duplicate scientific keys, zero plan-to-checkpoint mismatches, zero checkpoint-to-CSV mismatches, zero payload-identity mismatches, zero decision-recalculation mismatches, and zero temporal mismatches. DEVELOPMENT replay remained 18/18 exact. The validation result was `PHASE3B_HELDOUT_BLINDED_EXECUTION_VALIDATION_PASS`.

No truth columns occur in the blinded results, decisions, or temporal diagnostic. The F3B.6 operational sources do not reference the HELDOUT truth-ledger filename. No truth join, confusion matrix, sensitivity, specificity, false-positive rate, balanced accuracy, selection function, period-recovery evaluation, or performance stratification has been computed. The total number of selected HELDOUT decisions also remains deliberately unreported.

The single-use boundary therefore stops after blind execution and blind rule application. F3B.7 is the first authorized phase in which the frozen 3,600 classifications may be joined to the previously frozen HELDOUT truth ledger and evaluated prospectively. Phase 3B.6 makes no claim about classifier performance.
