# F3B.5 ? HELDOUT materialization report

## 1. Authorization and task scope

F3B.5 materializes the single-use synthetic HELDOUT population only after the DEVELOPMENT analysis and final rule were frozen. The authorization boundary is the committed artifact `f3b5_heldout_materialization_authorization.json`, created after commit `703ea23a1bf8e3f5c6e0daf0045f636dfc7358bf` and before the first HELDOUT stochastic draw. The operative authorization commit is `5e9f62eacfd2c82cc4db5e3c3df48fc3bd6e7565`. This task is deliberately limited to deterministic materialization, integrity checks, reproducibility checks, and construction of a future blinded AFINO worklist. It does not authorize AFINO execution, rule application, rule refitting, threshold changes, candidate development, or inspection of inferential outcomes.

## 2. Provenance

The materialization is tied to byte-pinned upstream inputs. The F3B.1 split registry identifies the preassigned DEVELOPMENT and HELDOUT units. The F3B.2 generator implementation binding fixes Python 3.13.13, NumPy 2.3.5, little-endian execution, the RNG architecture, and the exact generator implementation. The generator SHA-256 is `d538d53c7845916e29c4dd351b85ae91076d5a342acb5619898788ef5d825d11`; the binding SHA-256 is `b6519f84c0e6aa6b0c86cbd7a66dd79c1de1758e313d96ea4d750ebb212d9946`. The final-rule freeze SHA-256 is `e2faffdbb15d6e0fec52ff166e81a2ed58f5665d7d3f9dc43cb8b78f5c0a198c`. These inputs were checked before materialization and remained unchanged afterward.

## 3. Byte-exact F3B.2 generator

The HELDOUT materializer does not introduce a new scientific generator. It mechanically reuses the frozen F3B.2 generator and derives the HELDOUT orchestration from the byte-pinned DEVELOPMENT `materialize_dataset` implementation, changing only the split boundary and associated guards. The inherited mechanics retain the same background RNG namespace, period RNG namespace, `SeedSequence(...).spawn(2)` structure for noise and phase, period transform, signal construction, quality-mask application, canonical serialization, and logical hashing. The derived orchestration source was itself fingerprinted before use. This preserves the prospective design: HELDOUT differs from DEVELOPMENT by preassigned identities, not by a newly chosen generation procedure.

## 4. Frozen HELDOUT registry

The materialized population contains 1,800 background realizations and 4,320 series. Of these series, 3,600 belong to the frozen primary synthetic-classification plane and 720 belong to the input-admissibility challenge plane. Across the complete HELDOUT registry there are 2,160 synthetic-positive and 2,160 synthetic-null series. The primary plane contains 1,800 positive and 1,800 null series. Each primary background carries its preassigned positive/null pair, preserving the paired-background structure. Challenge rows remain distinct from the primary population and retain their preassigned masking regimes. No DEVELOPMENT simulation identifier is present in the F3B.5 materialization manifests.

## 5. Stochastic materialization

The first persistent HELDOUT materialization generated all 1,800 backgrounds and all 4,320 series in one authorized run. It recorded 1,800 background RNG initializations, 1,800 period draws, 1,800 phase draws, and 1,800 noise draws. No redraw was required and no generation failure occurred. Eight persistent array files were written under `data/interim/phase3b/f3b5_heldout/`, while the associated manifests were written under the Git-tracked F3B.5 evidence tree. The persistent files were immediately fingerprinted. Subsequent gates treated these first persistent bytes as immutable and explicitly prohibited rerunning the first materialization.

## 6. Synthetic truth bookkeeping

Synthetic truth is preserved in a dedicated truth ledger for later authorized evaluation, but it is not part of the future AFINO execution worklist. The truth ledger covers all 4,320 HELDOUT simulation units and remains aligned with the series manifest through `simulation_unit_id`. Positive and null series sharing a primary background preserve the same generated background realization, while their latent constructions follow the pre-frozen truth state. The F3B.5 validator also confirms that challenge masking does not alter the underlying latent flux identity associated with the corresponding background/truth construction. This keeps generation truth available for later evaluation without exposing it to model execution planning.

## 7. Input admissibility

All 3,600 primary series are `ELIGIBLE_FOR_AFINO`; none of the primary rows is marked inadmissible. All 720 challenge series are `INPUT_INADMISSIBLE` and therefore receive no future AFINO job. The frozen inadmissibility reasons are `IRREGULAR_SAMPLING` on 720 challenge rows, `PEAK_REMOVED_BY_QUALITY` on 360 rows, and `TOO_FEW_CADENCES` on 180 rows; reasons may co-occur on a row. Period-support and minimum-cycle generation constraints remain satisfied for the accepted background realizations, with zero redraws. Admissibility is therefore handled as a pre-execution input-state decision rather than being inferred from later AFINO outputs.

## 8. Payload integrity

The persistent physical representation uses eight NumPy arrays for backgrounds, latent series, retained times, retained fluxes, retained native indices, and offset vectors. The Git-tracked manifests retain canonical SHA-256 identities for background noise, latent flux, retained arrays, logical payloads, and truth records. Independent roundtrip validation reconstructed slices through the stored offset vectors and recomputed the canonical hashes. The final validator recorded zero background roundtrip mismatches, zero payload roundtrip mismatches, and zero challenge latent mismatches. The first persistent file hashes also remained unchanged across the later validation gates, establishing that verification did not mutate the materialized HELDOUT bytes.

## 9. Full rematerialization

A second complete materialization was executed only inside a temporary directory as the frozen reproducibility check. It used the same generator, split registry, and derived HELDOUT orchestration, without replacing or rewriting the first persistent arrays. The second run again required zero redraws. Its background-hash map, latent-hash map, retained logical-payload map, and truth-record map matched the persistent materialization exactly. The five regenerated CSV payloads were byte-identical to the persistent manifests, and the eight regenerated `.npy` files were byte-identical to the persistent arrays. The temporary copy was discarded after comparison; no third materialization was performed.

## 10. Blinded future AFINO plan

The frozen worklist contains exactly 3,600 planned decisions, one for each eligible primary HELDOUT series. Every decision uses external optimizer seed `0` only and expands to exactly three future model calls, M0, M1, and M2, for 10,800 planned calls in total. There are 3,600 planned calls for each model. No numerical-stability-extra decisions are present. The decision grid and exact worklist omit synthetic truth fields and synthetic-generation parameters that could reveal the answer to the future execution. Every work item remains `NOT_EXECUTED`. AFINO version 0.5, commit `6aceac9518fc8056052807e666da9d0c8bebb010`, and cutoff 0.025 Hz are inherited from the frozen DEVELOPMENT operational contract.

## 11. Single-use boundary

The single-use boundary audit records that HELDOUT stochastic truth has now been generated, while AFINO execution, rule application, outcome inspection, candidate search, threshold modification, and rule refitting remain absent. The first persistent materialization was not rerun during recovery from tooling incidents. The required second temporary rematerialization was completed exactly once, and no third materialization occurred. Tooling incidents F3B5-TOOL-001, F3B5-TOOL-002, and F3B5-TOOL-003 are documented as workflow issues without mutation of the accepted first persistent scientific bytes. The next transition is closure and Git freeze; it is not model execution.

## 12. Absence of HELDOUT inferential results

F3B.5 ends before any HELDOUT AFINO job is run. No HELDOUT rule has been applied, no HELDOUT inferential metric has been computed, and the synthetic truth ledger has not been joined to AFINO results because no such results exist. The materialization artifacts therefore establish only the frozen population, its provenance, physical integrity, admissibility states, deterministic reproducibility, and the blinded future execution plan. They do not constitute an inferential evaluation of the frozen classifier. The annotated materialization tag, remote verification, and pre-execution snapshot must be completed before the first HELDOUT AFINO job is permitted.
