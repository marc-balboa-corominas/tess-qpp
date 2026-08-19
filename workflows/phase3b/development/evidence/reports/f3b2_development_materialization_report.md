# F3B.2 — DEVELOPMENT generator/materialization report

## 1. Frozen F3B.1 inputs

F3B.2 was executed downstream of the immutable F3B.1 design freeze
`phase3b-design-v1` at commit `b8680934644be1bfec196e2009311b3060968f0a`. The frozen split registry defines
4,320 DEVELOPMENT and 4,320 HELDOUT simulation units, with the split made at
the `background_realization_id` level. No F3B.1 scientific or design artifact
was edited during this task. The frozen generator family, parameter support,
quality-mask regimes, truth labels, numerical-stability subset and HELDOUT
single-use policy therefore remain authoritative.

## 2. Implementation RNG binding

Before any accepted F3B.2 stochastic evidence, the implementation binding was
committed at `467abe9d5fc8379e342f7c98d735aae12ad56ea1`. Accepted generation uses Python 3.13,
NumPy 2.3.5, little-endian execution, PCG64, the frozen background namespace,
`SeedSequence(...).spawn(2)` for noise and phase, and the separately namespaced
period RNG. The first attempted canary under NumPy 2.5.1 was invalidated as
`F3B2-ENV-001`, archived, removed from the active evidence set and never used
as scientific evidence. A later helper-only `py_compile` NameError was recorded
as `F3B2-TOOL-001`; it occurred before full-DEVELOPMENT RNG initialization and
generated no scientific bytes.

## 3. F1 generator continuity

The accepted environment re-ran the five frozen F1 regression cases. Time
grid, asymmetric flare envelope, Fourier red-noise realization, phase pairing,
null flux, stationary QPP component and positive flux remained continuous with
the validated F1 implementation at absolute tolerance 5e-12 and relative
tolerance zero. The accepted status is
`F3B2_F1_GENERATOR_CONTINUITY_PASS`. This establishes implementation
continuity for inherited generator mechanics; it is not an empirical-realism
claim.

## 4. F3B generator canary

The valid 88-series canary used 36 frozen DEVELOPMENT backgrounds from the
numerical-stability protocol, producing 72 primary paired series, plus four
deterministically selected DEVELOPMENT challenge backgrounds producing 16
challenge series. The canary passed time-grid, flare-envelope, red-noise,
pairing, period, phase and mask-invariance checks with zero redraws. No HELDOUT
identity entered a background, period, phase or noise stochastic call.

## 5. DEVELOPMENT backgrounds

Full DEVELOPMENT materialization generated exactly 1,800 frozen nuisance
background realizations. Every background retained redraw count zero. The
period draw attached to the positive member of each pair remained inside the
frozen 40–300 s support and every accepted positive period satisfied at least
three cycles within the native window. All 1,800 persisted background slices
passed physical-array roundtrip hash reconstruction.

## 6. Synthetic truth

The DEVELOPMENT registry contains 2,160 `SYNTHETIC_QPP_PRESENT` and 2,160
`SYNTHETIC_QPP_ABSENT` series when primary and challenge units are combined.
Synthetic truth is known by construction and remains explicitly distinct from
observational reference labels. Positive series carry the stationary
envelope-modulated sinusoid, true period, amplitude fraction and phase. Null
series record the QPP component and true period as not applicable at the
series-truth level.

## 7. Primary series

All 3,600 primary contiguous-all-good series materialized successfully and all
3,600 satisfy the frozen AFINO input-admissibility contract. There were zero
generation failures and zero primary inadmissible series. This is a structural
input result only. No AFINO model has been called, so no selection decision or
classification-performance quantity exists at F3B.2.

## 8. Admissibility challenges

All 720 prospectively assigned challenge series are
`INPUT_INADMISSIBLE`. The audit retains every simultaneously triggered reason
rather than collapsing each row to one explanation. Across all triggered
reasons, `IRREGULAR_SAMPLING` occurs 720 times,
`PEAK_REMOVED_BY_QUALITY` 360 times and `TOO_FEW_CADENCES` 180 times.
Under the inherited technical precedence, the primary reason counts are
270 irregular-sampling, 360 peak-removed and 90 too-few-cadences cases. These
challenge frequencies are design stress-test frequencies, not estimates of
observed TESS data-quality prevalence.

## 9. Payload integrity

The eight persistent DEVELOPMENT arrays are stored under
`data/interim/phase3b/f3b2_development/` and are excluded from ordinary Git
tracking. All 4,320 series can be reconstructed from their offsets and hashes:
the first physical roundtrip is 1,800/1,800 backgrounds and 4,320/4,320 series
with zero mismatches. A second complete temporary materialization reproduced
all background hashes, latent hashes, retained-payload hashes, truth-record
hashes and physical `.npy` files byte-for-byte. The status is
`F3B2_DEVELOPMENT_REMATERIALIZATION_EXACT`.

## 10. Exact future AFINO plan

AFINO remains unexecuted. F3B.2 freezes the future DEVELOPMENT worklist from
the materialized inputs. The baseline contains 3,600 decisions at external
optimizer seed 0, one for each eligible primary series. The pre-registered
72-series numerical-stability subset adds only seeds 1–9, producing 648 extra
decisions. The exact total is therefore 4,248 decisions. Each decision has
three planned model calls, M0, M1 and M2, for 12,744 exact future jobs. Every
job is pinned to AFINO 0.5, commit `6aceac9518fc8056052807e666da9d0c8bebb010`, the 0.025 Hz cutoff and
its frozen logical payload SHA-256. Every job remains `NOT_EXECUTED`.

## 11. HELDOUT non-materialization and leakage controls

The HELDOUT registry still contains 4,320 planned rows and 1,800 frozen
background identities, but no HELDOUT materialization directory exists. The
recorded counts remain zero for HELDOUT background RNG initializations, period
draws, noise draws, phase draws, flux arrays and payloads. The F3B.1 HELDOUT
README guard remains byte-exact. Truth was used to construct synthetic
positive/null series but has not been used as an AFINO inference feature.
Observational labels were not substituted for synthetic truth.

## 12. Limitations and task boundary

F3B.2 validates deterministic generator implementation, exact DEVELOPMENT
materialization, truth bookkeeping, admissibility handling, payload integrity
and the future execution plan. It does not report sensitivity, specificity,
FPR, balanced accuracy, a selection function, candidate thresholds or AFINO
outcomes because none yet exist. AFINO execution and rule development belong
to later tasks. HELDOUT remains ungenerated and unaccessed. The next permitted
step is closure validation and Git/OSF freezing of F3B.2; only after that
freeze may F3B.3 begin DEVELOPMENT runner validation and baseline execution.
