from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]

GENERATOR = ROOT / "workflows/phase3b/scripts/f3b_synthetic_generator.py"
F1_GENERATOR = ROOT / "foundation/f0-f2/phase1/fase1_tarea02_synthetic_generator.py"
F1_PREREG = ROOT / "foundation/f0-f2/phase1/fase1_tarea01_core_benchmark_preregistration.json"
F1_AUDIT = ROOT / "foundation/f0-f2/phase1/fase1_tarea02_generator_validation_audit.json"

BG_MANIFEST = ROOT / "workflows/phase3b/development/evidence/tables/f3b2_development_background_manifest.csv"
SERIES_MANIFEST = ROOT / "workflows/phase3b/development/evidence/tables/f3b2_development_series_manifest.csv"
TRUTH_LEDGER = ROOT / "workflows/phase3b/development/evidence/tables/f3b2_development_truth_ledger.csv"
ADMISSIBILITY = ROOT / "workflows/phase3b/development/evidence/tables/f3b2_development_admissibility.csv"
PAYLOAD_MANIFEST = ROOT / "workflows/phase3b/development/evidence/tables/f3b2_development_payload_manifest.csv"
DECISION_GRID = ROOT / "workflows/phase3b/development/evidence/tables/f3b2_development_decision_grid.csv"
EXACT_PLAN = ROOT / "workflows/phase3b/development/evidence/tables/f3b2_development_exact_afino_plan.csv"

MAT_AUDIT = ROOT / "workflows/phase3b/development/evidence/reports/f3b2_development_materialization_audit.json"
HELD_AUDIT = ROOT / "workflows/phase3b/development/evidence/reports/f3b2_heldout_nonmaterialization_audit.json"
LEAK_AUDIT = ROOT / "workflows/phase3b/development/evidence/reports/f3b2_development_leakage_audit.json"
GEN_AUDIT = ROOT / "workflows/phase3b/development/evidence/reports/f3b2_generator_validation_audit.json"
REPORT = ROOT / "workflows/phase3b/development/evidence/reports/f3b2_development_materialization_report.md"
SHA_REGISTRY = ROOT / "workflows/phase3b/development/evidence/f3b2_SHA256SUMS.txt"

NUMSTAB = ROOT / "workflows/phase3b/design/f3b1_numerical_stability_protocol.json"
ARRAY_DIR = ROOT / "data/interim/phase3b/f3b2_development"
HELDOUT_ARRAY_DIR = ROOT / "data/interim/phase3b/heldout"

ROOT_README = ROOT / "workflows/phase3b/README.md"
DEV_README = ROOT / "workflows/phase3b/development/README.md"
HELDOUT_README = ROOT / "workflows/phase3b/heldout/README.md"

ABS_TOL = 5e-12
F1_REFERENCE_CASES = [
    (15, 0.0, 0),
    (15, 2.0, 39),
    (30, 1.0, 17),
    (60, 0.0, 39),
    (120, 2.0, 0),
]
EXPECTED_HELDOUT_README_SHA = "9bd5944971a918a9bf5a3305d263a7ca39fedc83797704d62727942808e9184f"

ARRAY_FILES = {
    "background_noise": "background_noise.npy",
    "background_offsets": "background_offsets.npy",
    "latent_flux": "latent_flux.npy",
    "latent_offsets": "latent_offsets.npy",
    "retained_time_s": "retained_time_s.npy",
    "retained_flux": "retained_flux.npy",
    "retained_native_index": "retained_native_index.npy",
    "retained_offsets": "retained_offsets.npy",
}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


f3b = _load(GENERATOR, "f3b2_final_test_generator")
f1 = _load(F1_GENERATOR, "f1_final_test_generator")


def _f1_spec():
    return _json(F1_PREREG)


def _alpha_code(specification, alpha: float) -> int:
    mapping = specification["generator"]["noise"]["alpha_code"]
    for key in [str(float(alpha)), format(float(alpha), ".1f"), str(alpha)]:
        if key in mapping:
            return int(mapping[key])
    raise AssertionError(f"Missing alpha code for {alpha}")


@pytest.mark.parametrize("n_samples,alpha,data_seed", F1_REFERENCE_CASES)
def test_f1_generator_continuity_reference_cases(n_samples, alpha, data_seed):
    spec = _f1_spec()
    audit = _json(F1_AUDIT)
    cases = {
        (
            int(c["n_samples"]),
            float(c["red_noise_alpha"]),
            int(c["data_seed"]),
        )
        for c in audit["independent_reference"]["cases"]
    }
    assert (n_samples, alpha, data_seed) in cases

    reference = f1.generate_paired_block(n_samples, alpha, data_seed, spec)
    candidate = f3b.f1_compatible_block(
        n_samples,
        alpha,
        data_seed,
        master_seed=int(spec["rng_and_pairing"]["master_seed"]),
        alpha_code=_alpha_code(spec, alpha),
    )
    np.testing.assert_allclose(candidate["time_s"], reference["time_s"], rtol=0, atol=ABS_TOL)
    np.testing.assert_allclose(candidate["flare_envelope"], reference["flare_envelope"], rtol=0, atol=ABS_TOL)
    np.testing.assert_allclose(candidate["noise"], reference["noise"], rtol=0, atol=ABS_TOL)
    assert math.isclose(float(candidate["phase_rad"]), float(reference["phase_rad"]), rel_tol=0, abs_tol=ABS_TOL)

    cand_null = f3b.materialize_null_latent(candidate)
    ref_null = f1.materialize_null(reference, spec)
    np.testing.assert_allclose(cand_null, ref_null, rtol=0, atol=ABS_TOL)

    cand_pos, cand_component = f3b.f1_compatible_positive(candidate, 50.0, 0.02)
    ref_pos = f1.materialize_positive(reference, 50.0, 0.02, spec)
    np.testing.assert_allclose(cand_pos, ref_pos, rtol=0, atol=ABS_TOL)
    np.testing.assert_allclose(cand_pos - cand_null, cand_component, rtol=0, atol=ABS_TOL)


def test_predraw_binding_constants():
    assert f3b.F3B1_BACKGROUND_NAMESPACE == "TESS-QPP:F3B1:v1"
    assert f3b.F3B1_PERIOD_NAMESPACE == "TESS-QPP:F3B1:PERIOD:v1"
    assert f3b.ALLOWED_N_SAMPLES == (15, 30, 60, 120)
    assert f3b.ALLOWED_RED_NOISE_ALPHA == (0.0, 1.0, 2.0)
    assert f3b.ALLOWED_QPP_FRACTION == (0.01, 0.02, 0.04)
    assert f3b.FLOAT64_DTYPE.str == "<f8"
    assert f3b.INT64_DTYPE.str == "<i8"
    assert f3b.BOOL_DTYPE.str == "|b1"


def test_materialization_counts_truth_and_states():
    series = _csv(SERIES_MANIFEST)
    truth = _csv(TRUTH_LEDGER)
    adm = _csv(ADMISSIBILITY)
    assert len(series) == len(truth) == len(adm) == 4320
    assert len({r["simulation_unit_id"] for r in series}) == 4320
    assert Counter(r["truth_state"] for r in series) == Counter({
        "SYNTHETIC_QPP_PRESENT": 2160,
        "SYNTHETIC_QPP_ABSENT": 2160,
    })
    primary = [r for r in series if r["evidence_plane"] == "SYNTHETIC_GROUND_TRUTH_CLASSIFICATION"]
    challenge = [r for r in series if r["evidence_plane"] == "INPUT_ADMISSIBILITY"]
    assert len(primary) == 3600
    assert len(challenge) == 720
    assert all(r["input_state"] == "ELIGIBLE_FOR_AFINO" for r in primary)
    assert all(r["input_state"] == "INPUT_INADMISSIBLE" for r in challenge)
    assert all(r["materialization_status"] == "MATERIALIZED" for r in series)
    assert all(r["synthetic_ground_truth_known"] == "True" for r in truth)


def test_background_manifest_redraw_period_support():
    rows = _csv(BG_MANIFEST)
    assert len(rows) == 1800
    assert len({r["background_realization_id"] for r in rows}) == 1800
    assert all(r["split"] == "DEVELOPMENT" for r in rows)
    assert all(r["generation_status"] == "MATERIALIZED" for r in rows)
    assert all(int(r["redraw_count"]) == 0 for r in rows)
    assert all(40.0 <= float(r["true_period_s"]) <= 300.0 for r in rows)
    assert all(float(r["cycles_in_window"]) >= 3.0 for r in rows)


def test_admissibility_reason_counts():
    rows = _csv(ADMISSIBILITY)
    primary_reason = Counter(
        r["primary_inadmissibility_reason"]
        for r in rows if r["primary_inadmissibility_reason"]
    )
    all_reason = Counter()
    for r in rows:
        for reason in r["all_triggered_reasons"].split("|"):
            if reason:
                all_reason[reason] += 1
    assert primary_reason == Counter({
        "IRREGULAR_SAMPLING": 270,
        "PEAK_REMOVED_BY_QUALITY": 360,
        "TOO_FEW_CADENCES": 90,
    })
    assert all_reason == Counter({
        "IRREGULAR_SAMPLING": 720,
        "PEAK_REMOVED_BY_QUALITY": 360,
        "TOO_FEW_CADENCES": 180,
    })


def test_background_array_roundtrip_all_1800():
    rows = _csv(BG_MANIFEST)
    noise = np.load(ARRAY_DIR / ARRAY_FILES["background_noise"], allow_pickle=False)
    offsets = np.load(ARRAY_DIR / ARRAY_FILES["background_offsets"], allow_pickle=False)
    assert noise.dtype == np.dtype("float64")
    assert offsets.dtype == np.dtype("int64")
    assert len(offsets) == 1801
    for i, row in enumerate(rows):
        arr = noise[int(offsets[i]):int(offsets[i + 1])]
        assert f3b.canonical_float64_sha256(arr) == row["noise_sha256"]


def test_series_payload_roundtrip_all_4320():
    rows = _csv(SERIES_MANIFEST)
    payload_rows = _csv(PAYLOAD_MANIFEST)
    payload_by_sid = {r["simulation_unit_id"]: r for r in payload_rows}
    latent = np.load(ARRAY_DIR / ARRAY_FILES["latent_flux"], allow_pickle=False)
    loff = np.load(ARRAY_DIR / ARRAY_FILES["latent_offsets"], allow_pickle=False)
    rt = np.load(ARRAY_DIR / ARRAY_FILES["retained_time_s"], allow_pickle=False)
    rf = np.load(ARRAY_DIR / ARRAY_FILES["retained_flux"], allow_pickle=False)
    ri = np.load(ARRAY_DIR / ARRAY_FILES["retained_native_index"], allow_pickle=False)
    roff = np.load(ARRAY_DIR / ARRAY_FILES["retained_offsets"], allow_pickle=False)

    assert latent.dtype == rt.dtype == rf.dtype == np.dtype("float64")
    assert ri.dtype == loff.dtype == roff.dtype == np.dtype("int64")
    assert len(loff) == len(roff) == 4321

    for i, row in enumerate(rows):
        sid = row["simulation_unit_id"]
        p = payload_by_sid[sid]
        l = latent[int(loff[i]):int(loff[i + 1])]
        t = rt[int(roff[i]):int(roff[i + 1])]
        f = rf[int(roff[i]):int(roff[i + 1])]
        idx = ri[int(roff[i]):int(roff[i + 1])]
        assert f3b.canonical_float64_sha256(l) == row["latent_flux_sha256"]
        assert f3b.canonical_float64_sha256(t) == row["retained_time_sha256"]
        assert f3b.canonical_float64_sha256(f) == row["retained_flux_sha256"]
        assert f3b.canonical_int64_sha256(idx) == row["retained_native_index_sha256"]
        logical = f3b.logical_payload_sha256(sid, t, f, idx)
        assert logical == row["logical_payload_sha256"] == p["logical_payload_sha256"]


def test_rematerialization_audit_exact():
    audit = _json(MAT_AUDIT)
    assert audit["materialized_series"] == 4320
    assert audit["materialization_failures"] == 0
    assert audit["primary_eligible"] == 3600
    assert audit["primary_inadmissible"] == 0
    assert audit["rematerialization"]["status"] == "F3B2_DEVELOPMENT_REMATERIALIZATION_EXACT"
    for key in [
        "background_hash_mismatches",
        "latent_hash_mismatches",
        "retained_payload_hash_mismatches",
        "truth_record_mismatches",
        "array_file_byte_mismatches",
    ]:
        assert audit["rematerialization"][key] == 0


def test_heldout_nonmaterialization():
    audit = _json(HELD_AUDIT)
    assert not HELDOUT_ARRAY_DIR.exists()
    assert audit["heldout_registry_rows"] == 4320
    assert audit["heldout_backgrounds"] == 1800
    for key in [
        "heldout_background_rng_initializations",
        "heldout_period_draws",
        "heldout_phase_draws",
        "heldout_noise_draws",
        "heldout_flux_arrays",
        "heldout_payloads",
    ]:
        assert audit[key] == 0
    assert audit["heldout_generated"] is False
    assert audit["heldout_accessed"] is False
    assert audit["heldout_readme_byte_exact_to_f3b1_tag"] is True


def test_decision_grid_exact_counts_and_seeds():
    rows = _csv(DECISION_GRID)
    assert len(rows) == 4248
    assert Counter(r["decision_class"] for r in rows) == Counter({
        "BASELINE": 3600,
        "NUMERICAL_STABILITY_EXTRA": 648,
    })
    assert all(r["execution_status"] == "NOT_EXECUTED" for r in rows)
    baseline = [r for r in rows if r["decision_class"] == "BASELINE"]
    extra = [r for r in rows if r["decision_class"] == "NUMERICAL_STABILITY_EXTRA"]
    assert all(int(r["external_optimizer_seed"]) == 0 for r in baseline)
    assert set(int(r["external_optimizer_seed"]) for r in extra) == set(range(1, 10))
    assert len({(r["simulation_unit_id"], r["external_optimizer_seed"]) for r in rows}) == 4248


def test_exact_afino_plan_contract():
    rows = _csv(EXACT_PLAN)
    assert len(rows) == 12744
    assert Counter(r["model_id"] for r in rows) == Counter({
        "M0": 4248, "M1": 4248, "M2": 4248
    })
    assert all(r["execution_status"] == "NOT_EXECUTED" for r in rows)
    assert all(r["afino_version"] == "0.5" for r in rows)
    assert all(r["afino_commit"] == "6aceac9518fc8056052807e666da9d0c8bebb010" for r in rows)
    assert all(float(r["low_frequency_cutoff_hz"]) == 0.025 for r in rows)
    grouped = defaultdict(list)
    for r in rows:
        grouped[r["planned_decision_id"]].append(r["model_id"])
    assert len(grouped) == 4248
    assert all(sorted(models) == ["M0", "M1", "M2"] for models in grouped.values())


def test_stability_subset_exact_72():
    num = _json(NUMSTAB)
    frozen_sids = {
        sid
        for item in num["selected_backgrounds"]
        for sid in item["simulation_unit_ids"]
    }
    assert len(frozen_sids) == 72
    rows = _csv(DECISION_GRID)
    by_sid = defaultdict(set)
    for r in rows:
        by_sid[r["simulation_unit_id"]].add(int(r["external_optimizer_seed"]))
    stability_sids = {sid for sid, seeds in by_sid.items() if seeds == set(range(10))}
    assert stability_sids == frozen_sids
    assert all(by_sid[sid] == {0} for sid in by_sid if sid not in frozen_sids)


def test_no_challenge_in_afino_plan():
    series = {r["simulation_unit_id"]: r for r in _csv(SERIES_MANIFEST)}
    plan = _csv(EXACT_PLAN)
    assert all(series[r["simulation_unit_id"]]["evidence_plane"] == "SYNTHETIC_GROUND_TRUTH_CLASSIFICATION" for r in plan)
    assert all(series[r["simulation_unit_id"]]["input_state"] == "ELIGIBLE_FOR_AFINO" for r in plan)


def test_evidence_checksum_registry():
    evidence_root = ROOT / "workflows/phase3b/development/evidence"
    lines = SHA_REGISTRY.read_text(encoding="ascii").splitlines()
    assert len(lines) == 13
    for line in lines:
        digest, rel = line.split("  ", 1)
        assert _sha(evidence_root / rel) == digest


def test_readme_states_and_heldout_guard():
    root = ROOT_README.read_text(encoding="utf-8")
    dev = DEV_README.read_text(encoding="utf-8")
    assert "DEVELOPMENT MATERIALIZED —" in root
    assert "AFINO EXECUTION NOT STARTED" in root
    assert "HELDOUT NOT GENERATED" in root
    assert "DEVELOPMENT MATERIALIZED AND FROZEN —" in dev
    assert "AFINO NOT STARTED" in dev
    assert _sha(HELDOUT_README) == EXPECTED_HELDOUT_README_SHA


def test_no_afino_outcomes_or_scientific_metrics():
    mat = _json(MAT_AUDIT)
    leak = _json(LEAK_AUDIT)
    assert mat["afino_executed"] is False
    assert mat["candidate_rule_fitted"] is False
    assert mat["candidate_thresholds_generated"] is False
    assert mat["scientific_metrics_computed"] is False
    assert mat["all_plan_jobs_execution_status"] == "NOT_EXECUTED"
    assert leak["afino_executed"] is False
    assert leak["candidate_rule_fitted"] is False
    assert leak["candidate_thresholds_generated"] is False
    assert leak["scientific_metrics_computed"] is False
    text = REPORT.read_text(encoding="utf-8").lower()
    assert "no afino model has been called" in text
    assert 900 <= len(re.findall(r"\b[\wΔ≥–-]+(?:['’][\w]+)?\b", REPORT.read_text(encoding="utf-8"))) <= 1300


def test_incident_provenance_and_valid_environment():
    gen = _json(GEN_AUDIT)
    mat = _json(MAT_AUDIT)
    assert gen["execution_environment"]["numpy_version"] == "2.3.5"
    assert gen["execution_environment"]["python_major_minor"] == [3, 13]
    assert gen["execution_environment"]["byteorder"] == "little"
    assert mat["pre_materialization_environment_incident"]["incident_id"] == "F3B2-ENV-001"
    assert mat["pre_materialization_environment_incident"]["invalid_canary_used_as_scientific_evidence"] is False
    assert mat["pre_materialization_tooling_incident"]["incident_id"] == "F3B2-TOOL-001"
    assert mat["pre_materialization_tooling_incident"]["scientific_bytes_generated_by_failed_attempt"] is False
