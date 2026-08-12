from __future__ import annotations

import csv
import importlib.util
import json
import sqlite3
import warnings
from pathlib import Path

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[3]
RUNNER_PATH = REPO / "workflows/phase3a/scripts/run_afino_checkpointed.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("f3a3_runner_test", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


R = load_runner()


def fake_payloads(tmp_path: Path):
    t = np.arange(15, dtype="<f8") * 20.0
    f = np.linspace(1.0, 2.0, 15, dtype="<f8")
    idx = np.arange(100, 115, dtype="<i8")
    offsets = np.array([0, 15], dtype="<i8")
    p = {
        "payload_id": "PAY1",
        "variant_id": "VAR1",
        "offset": 0,
        "length": 15,
        "time_sha256": R.canonical_hash(t, "<f8"),
        "flux_sha256": R.canonical_hash(f, "<f8"),
        "native_index_sha256": R.canonical_hash(idx, "<i8"),
        "logical_payload_sha256": R.logical_payload_hash(t, f, idx),
        "n_samples": "15",
    }
    return {
        "time": t,
        "flux": f,
        "native": idx,
        "offsets": offsets,
        "by_payload": {"PAY1": p},
    }, p


def fake_job(p):
    return {
        "job_id": "JOB1",
        "job_order": 1,
        "planned_decision_id": "D1",
        "decision_class": "PRIMARY",
        "phase3a_event_id": "E1",
        "variant_id": "VAR1",
        "matrix_cell_id": "C1",
        "window_variant_id": "W00",
        "processing_profile_id": "P00",
        "external_optimizer_seed": 0,
        "model_id": "M0",
        "model_name": "pow_const",
        "payload_id": "PAY1",
        "payload_logical_sha256": p["logical_payload_sha256"],
        "payload_offset": 0,
        "payload_length": 15,
        "input_time_sha256": p["time_sha256"],
        "input_flux_sha256": p["flux_sha256"],
        "input_native_index_sha256": p["native_index_sha256"],
        "afino_version": "0.5",
        "afino_commit": R.EXPECTED_AFINO_COMMIT,
        "low_frequency_cutoff_hz": 0.025,
        "execution_status": "NOT_EXECUTED",
    }


def fake_result(job, model_id="M0", bic=20.0):
    row = {c: None for c in R.RESULT_COLUMNS}
    row.update({
        "job_id": job["job_id"],
        "job_order": job["job_order"],
        "planned_decision_id": job["planned_decision_id"],
        "decision_class": job["decision_class"],
        "phase3a_event_id": job["phase3a_event_id"],
        "variant_id": job["variant_id"],
        "matrix_cell_id": job["matrix_cell_id"],
        "window_variant_id": job["window_variant_id"],
        "processing_profile_id": job["processing_profile_id"],
        "external_optimizer_seed": job["external_optimizer_seed"],
        "model_id": model_id,
        "model_name": R.MODEL_SPECS[model_id],
        "payload_id": job["payload_id"],
        "payload_logical_sha256": job["payload_logical_sha256"],
        "payload_offset": job["payload_offset"],
        "payload_length": job["payload_length"],
        "input_time_sha256": job["input_time_sha256"],
        "input_flux_sha256": job["input_flux_sha256"],
        "input_native_index_sha256": job["input_native_index_sha256"],
        "status": "OK",
        "bic": bic,
        "log_likelihood": -10.0,
        "parameters_json": "[1.0,2.0,3.0]",
        "warning_count": 0,
        "warning_types_json": "[]",
        "warnings_json": "[]",
        "parameter_at_bound": 0,
        "bound_parameters_json": "[]",
        "convergence_status": "NOT_AUDITABLE",
        "afino_effective_dt_s": 20.0,
        "positive_frequency_bin_count": 7,
        "post_cutoff_bin_count": 1,
        "runtime_seconds": 0.1,
        "afino_version": "0.5",
        "afino_commit": R.EXPECTED_AFINO_COMMIT,
        "result_core_sha256": "x" * 64,
        "completed_at_utc": "2026-01-01T00:00:00+00:00",
    })
    if model_id == "M1":
        row["formal_m1_period_s"] = 60.0
    return row


def init_test_db(path: Path):
    R.initialize_checkpoint(
        path,
        canary_manifest_sha256=R.EXPECTED_CANARY_JOB_MANIFEST_SHA256,
        runner_sha256="r" * 64,
        afino_environment={
            "python_version": "3.13.13",
            "numpy_version": "2.5.1",
            "scipy_version": "1.18.0",
            "afino_version": "0.5",
            "afino_commit": R.EXPECTED_AFINO_COMMIT,
        },
        plan_kind="canary",
    )


def test_frozen_payload_extraction():
    payloads, p = fake_payloads(Path("."))
    job = fake_job(p)
    t, f, idx = R.extract_payload(job, payloads)
    assert len(t) == len(f) == len(idx) == 15
    assert t[0] == 0.0
    assert np.array_equal(np.diff(idx), np.ones(14, dtype=np.int64))


def test_payload_hash_rejection():
    payloads, p = fake_payloads(Path("."))
    job = fake_job(p)
    job["payload_logical_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="logical payload hash rejection"):
        R.extract_payload(job, payloads)


def test_unknown_job_rejection():
    payloads, p = fake_payloads(Path("."))
    raw = {
        "job_id": "UNKNOWN",
        "model_id": "M0",
        "model_name": "pow_const",
    }
    with pytest.raises(RuntimeError, match="Unknown canary job"):
        R.validate_canary_row(raw, {}, payloads)


def test_model_mismatch_rejection():
    payloads, p = fake_payloads(Path("."))
    full = {
        "job_id": "JOB1",
        "job_order": "1",
        "planned_decision_id": "D1",
        "decision_class": "PRIMARY",
        "phase3a_event_id": "E1",
        "variant_id": "VAR1",
        "matrix_cell_id": "C1",
        "window_variant_id": "W00",
        "processing_profile_id": "P00",
        "external_optimizer_seed": "0",
        "model_id": "M0",
        "model_name": "pow_const",
        "payload_id": "PAY1",
        "payload_logical_sha256": p["logical_payload_sha256"],
        "afino_version": "0.5",
        "afino_commit": R.EXPECTED_AFINO_COMMIT,
        "low_frequency_cutoff_hz": "0.025",
        "seed_application_contract":
            "np.random.seed(external_optimizer_seed) immediately before each model",
        "selection_rule": "BIC_M0-BIC_M1>10 AND BIC_M2-BIC_M1>10",
        "execution_status": "NOT_EXECUTED",
    }
    raw = dict(full)
    raw["model_name"] = "wrong"
    # Scientific-column literal-subset check itself rejects this.
    with pytest.raises(RuntimeError):
        R.validate_canary_row(raw, {"JOB1": full}, payloads)


def test_seed_mismatch_rejection():
    payloads, p = fake_payloads(Path("."))
    full = {
        "job_id": "JOB1",
        "job_order": "1",
        "planned_decision_id": "D1",
        "decision_class": "PRIMARY",
        "phase3a_event_id": "E1",
        "variant_id": "VAR1",
        "matrix_cell_id": "C1",
        "window_variant_id": "W00",
        "processing_profile_id": "P00",
        "external_optimizer_seed": "1",
        "model_id": "M0",
        "model_name": "pow_const",
        "payload_id": "PAY1",
        "payload_logical_sha256": p["logical_payload_sha256"],
        "afino_version": "0.5",
        "afino_commit": R.EXPECTED_AFINO_COMMIT,
        "low_frequency_cutoff_hz": "0.025",
        "seed_application_contract":
            "np.random.seed(external_optimizer_seed) immediately before each model",
        "selection_rule": "BIC_M0-BIC_M1>10 AND BIC_M2-BIC_M1>10",
        "execution_status": "NOT_EXECUTED",
    }
    with pytest.raises(RuntimeError, match="PRIMARY seed mismatch"):
        R.validate_canary_row(full, {"JOB1": full}, payloads)


def test_duplicate_checkpoint_prevention(tmp_path):
    payloads, p = fake_payloads(tmp_path)
    job = fake_job(p)
    db = tmp_path / "cp.sqlite"
    init_test_db(db)
    r = fake_result(job)
    R.insert_result_transaction(db, r)
    with pytest.raises(sqlite3.IntegrityError):
        R.insert_result_transaction(db, r)


def test_partial_decision_resume_and_completed_skip(tmp_path, monkeypatch):
    payloads, p = fake_payloads(tmp_path)
    jobs = []
    for i in range(4):
        j = fake_job(p)
        j["job_id"] = f"J{i}"
        j["job_order"] = i + 1
        j["variant_id"] = f"VAR{i}"
        jobs.append(j)

    def fake_exec(job, payloads):
        return fake_result(job, "M0", 20.0)

    monkeypatch.setattr(R, "execute_one_job", fake_exec)
    db = tmp_path / "cp.sqlite"
    env = {
        "python_version": "3.13.13",
        "numpy_version": "2.5.1",
        "scipy_version": "1.18.0",
        "afino_version": "0.5",
        "afino_commit": R.EXPECTED_AFINO_COMMIT,
    }
    first = R.run_jobs(
        checkpoint=db, jobs=jobs, payloads=payloads,
        max_new_jobs=1, resume=False,
        manifest_sha=R.EXPECTED_CANARY_JOB_MANIFEST_SHA256,
        plan_kind="canary", runner_sha="r"*64, environment=env,
    )
    second = R.run_jobs(
        checkpoint=db, jobs=jobs, payloads=payloads,
        max_new_jobs=2, resume=True,
        manifest_sha=R.EXPECTED_CANARY_JOB_MANIFEST_SHA256,
        plan_kind="canary", runner_sha="r"*64, environment=env,
    )
    assert first["existing_before"] == 0
    assert first["new_jobs"] == 1
    assert second["existing_before"] == 1
    assert second["new_jobs"] == 2
    assert R.result_count(db) == 3


def test_decision_assembly_only_after_complete_trio():
    payloads, p = fake_payloads(Path("."))
    job = fake_job(p)
    m0 = fake_result(job, "M0", 30.0)
    m1 = fake_result(job, "M1", 10.0)
    assert R.assemble_complete_decisions([m0, m1]) == []
    m2 = fake_result(job, "M2", 25.0)
    decisions = R.assemble_complete_decisions([m0, m1, m2])
    assert len(decisions) == 1
    assert decisions[0]["decision_status"] == "VALID"


def test_idempotent_second_export(tmp_path):
    payloads, p = fake_payloads(tmp_path)
    job = fake_job(p)
    jobs = [job]
    db = tmp_path / "cp.sqlite"
    init_test_db(db)
    R.insert_result_transaction(db, fake_result(job))
    out = tmp_path / "results.csv"
    assert R.export_results(db, jobs, out) == 1
    first = out.read_bytes()
    assert R.export_results(db, jobs, out) == 1
    assert out.read_bytes() == first


def test_selection_rule_exactness():
    assert R.selection_rule(21.0, 10.0, 21.0) is True
    assert R.selection_rule(20.0, 10.0, 21.0) is False
    assert R.selection_rule(21.0, 10.0, 20.0) is False


def test_warning_serialization():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        warnings.warn("checkpoint-test-warning", RuntimeWarning)
    count, types_json, warnings_json = R.warning_payload(list(caught))
    assert count == 1
    assert "RuntimeWarning" in types_json
    assert "checkpoint-test-warning" in warnings_json


def test_full_plan_guard_string_is_present():
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert "FULL_PLAN_EXECUTION_REQUIRES_EXPLICIT_AUTHORIZATION" in source
    assert "--authorize-full-plan" in source
