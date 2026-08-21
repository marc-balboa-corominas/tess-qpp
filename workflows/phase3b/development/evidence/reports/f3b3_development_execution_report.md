# F3B.3 DEVELOPMENT AFINO execution report

## Provenance and scope

F3B.3 executed the frozen DEVELOPMENT-only AFINO plan derived from the approved F3B.2 materialization at commit `7550679a8b0ea1f028987a38cfbe7ac7671fb8ce` and tag `phase3b-development-materialization-v1`. No synthetic series were regenerated during this phase. The execution consumed only the retained DEVELOPMENT payloads frozen in F3B.2, while HELDOUT remained outside the authorized scope. The separation between the generator environment and the AFINO execution environment was preserved throughout.

## AFINO environment and blinded plan

The AFINO stack remained bound to version 0.5 at commit `6aceac9518fc8056052807e666da9d0c8bebb010`, using Python 3.13.13, NumPy 2.5.1 and SciPy 1.18.0. The frozen runner SHA-256 was `4d5b68cdda60abd7f3a4380abf63d1b0b5e9f4e5889caf22ff85f95b31d813bc`. The blinded plan contained exactly 12,744 jobs representing 4,248 decisions evaluated with M0, M1 and M2. Decision classes were exactly 3,600 `BASELINE` and 648 `NUMERICAL_STABILITY_EXTRA`. Ground-truth labels and scientific strata were excluded from inference inputs.

## Prospective canary

Before full authorization, the runner was frozen and validated on 216 canary decisions and 648 model jobs. The deliberately non-multiple-of-three resume sequence was 211 + 223 + 214 + 0, demonstrating safe resume through partial decisions. All 648 jobs were OK and all 216 decisions were VALID. The canary temporal contract passed 216/216, and six prospectively selected decisions were replayed across eighteen model jobs with absolute tolerance 5e-12 and relative tolerance zero. The replay produced 18/18 matches and zero mismatches. Those 648 canary jobs were reused in the full checkpoint rather than rerun.

## Full checkpoint and execution sequence

The full DEVELOPMENT checkpoint was created separately, initialized with full-plan metadata, and bootstrapped with the 648 validated canary results. Job identity, payload identity and `result_core_sha256` preservation were checked during bootstrap. The remaining 12,096 jobs were executed in the frozen sequence +3000, +3000, +3000, +3000 and +96. A final +0 invocation demonstrated idempotence. The completed checkpoint contains exactly 12,744/12,744 OK results and 4,248/4,248 complete decisions, with zero partial decisions and zero duplicate job identifiers or scientific keys.

## Output integrity

The exported results table contains 12,744 rows, the decision table 4,248 rows, and the temporal diagnostic 4,248 rows. M0, M1 and M2 each contribute exactly 4,248 calls. Independent validation found zero plan-to-checkpoint mismatches, zero checkpoint-to-CSV mismatches, zero frozen-payload mismatches, zero result-core recalculation mismatches and zero decision recalculation mismatches. The 648 imported canary results remained present with zero result-core mismatches. Decision assembly used only blinded AFINO outputs and execution identity. No confusion matrix or truth-conditioned performance table was created.

## Temporal and numerical diagnostics

For every DEVELOPMENT decision, the effective temporal contract used `mean(diff(time_seconds))` and positive frequencies from `np.fft.fftfreq`. All 4,248 decisions matched the AFINO effective cadence, and all 4,248 matched the positive-frequency-bin contract. Median cadence and positive `rfftfreq` counts were retained only as legacy diagnostics. Operational summaries were restricted to model level. M0 had 4248 calls, 0 warning calls, 0 total warnings, 158 bound calls and median runtime 0.281330 s. M1 had 4248 calls, 0 warning calls, 0 total warnings, 2733 bound calls and median runtime 0.838670 s. M2 had 4248 calls, 2001 warning calls, 16742 total warnings, 1682 bound calls and median runtime 0.490601 s. These diagnostics were not stratified by truth state, QPP fraction, red-noise alpha or sample count.

## Auditability and reproducibility controls

The completed execution preserves a direct audit chain from every blinded plan row to one checkpoint result and one exported result row. Each scientific key consists of `simulation_unit_id`, external optimizer seed and model identity, and that key is unique across all 12,744 calls. Frozen payload hashes remain attached to both plan and result identities. The independent validator also recalculates every stored result-core hash rather than trusting the database field alone, and reconstructs all 4,248 decisions from the three model rows before comparing them with the exported decision table. An initial pre-commit validator candidate was blocked by a comparison bug that treated plan-only AFINO provenance fields as if they were duplicated in each SQLite result row; it produced no scientific bytes or final reports, and the corrected validator checks those fields through the frozen plan and checkpoint metadata instead. The bootstrap audit is copied byte-for-byte from runtime evidence so that canary reuse remains inspectable in the final evidence set. Checksum evidence includes the runner, tests, blinded plan, canary artifacts, bootstrap audit, full outputs, reports and both runtime checkpoints. These controls establish provenance and mechanical reproducibility only; they do not reinterpret the AFINO outputs or introduce post-hoc filtering. No failed case was removed, no optimizer seed was changed, no payload was substituted, and no adaptive retry policy was introduced after observing outcomes.

## HELDOUT non-access and scientific boundary

HELDOUT remains ungenerated and unaccessed. Its registry contains 4,320 planned rows, while noise draws, period draws, phase draws, flux arrays, payloads and AFINO HELDOUT jobs remain zero. No HELDOUT dataset directory exists. The generator was not imported for inference, synthetic arrays were not regenerated, and truth was not used as an inference feature. F3B.3 therefore closes only the blinded AFINO execution layer on DEVELOPMENT.

## Validation state

The independent validation result is `PHASE3B_DEVELOPMENT_EXECUTION_VALIDATION_PASS`. This status establishes consistency among the frozen plan, checkpoint, exported tables, temporal contract, canary reuse and non-access constraints. It is not a statement of sensitivity, specificity, false-positive rate, balanced accuracy or any selection-function estimate. Scientific ground-truth metrics remain deliberately uncomputed, no candidate rule has been fitted, and no selection function has been estimated. Those analyses belong to F3B.4, where DEVELOPMENT outputs may be rejoined to known truth while HELDOUT remains prohibited.
