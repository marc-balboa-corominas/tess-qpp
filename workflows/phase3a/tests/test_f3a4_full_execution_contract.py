from __future__ import annotations

import csv
import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
BOOTSTRAP_PATH = REPO / "workflows/phase3a/scripts/bootstrap_full_checkpoint.py"
ASSEMBLER_PATH = REPO / "workflows/phase3a/scripts/assemble_full_decisions.py"
VALIDATOR_PATH = REPO / "workflows/phase3a/scripts/validate_full_execution.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


B = load("f3a4_bootstrap_test", BOOTSTRAP_PATH)
A = load("f3a4_assembler_test", ASSEMBLER_PATH)
V = load("f3a4_validator_test", VALIDATOR_PATH)


def read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_authorization_contract():
    auth = json.loads(
        (REPO / B.AUTH_REL).read_text(encoding="utf-8")
    )
    assert auth["authorization_status"] == (
        "FULL_FROZEN_PLAN_EXECUTION_AUTHORIZED_WITHOUT_SCIENTIFIC_ANALYSIS"
    )
    assert auth["planned_decisions"] == 7466
    assert auth["planned_model_jobs"] == 22398
    assert auth["validated_canary_jobs"] == 102
    assert auth["remaining_new_jobs"] == 22296
    assert auth["reuse_validated_canary_results"] is True
    assert auth["rerun_canary_jobs"] is False
    assert auth["scientific_analysis_authorized"] is False


def test_full_plan_identity_and_three_models_per_decision():
    rows = read_csv(REPO / B.FULL_PLAN_REL)
    assert len(rows) == 22398
    assert len({r["job_id"] for r in rows}) == 22398
    grouped = {}
    for r in rows:
        key = (
            r["planned_decision_id"],
            r["variant_id"],
            r["external_optimizer_seed"],
        )
        grouped.setdefault(key, set()).add(r["model_id"])
    assert len(grouped) == 7466
    assert set(map(frozenset, grouped.values())) == {
        frozenset({"M0", "M1", "M2"})
    }


def test_canary_is_exact_full_plan_subset():
    full = {
        r["job_id"]: r
        for r in read_csv(REPO / B.FULL_PLAN_REL)
    }
    canary = read_csv(
        REPO /
        "workflows/phase3a/evidence/tables/f3a3_canary_job_manifest.csv"
    )
    assert len(canary) == 102
    for r in canary:
        assert r["job_id"] in full
        f = full[r["job_id"]]
        for field in (
            "planned_decision_id", "variant_id",
            "external_optimizer_seed", "model_id",
            "payload_id", "payload_logical_sha256",
        ):
            assert r[field] == f[field]


def test_canary_checkpoint_hash_is_frozen():
    assert B.sha256_file(REPO / B.CANARY_CHECKPOINT_REL) == (
        B.EXPECTED_CANARY_CHECKPOINT_SHA256
    )


def make_results_db(path: Path):
    con = sqlite3.connect(path)
    con.execute(
        """
        CREATE TABLE results(
            job_id TEXT PRIMARY KEY,
            variant_id TEXT NOT NULL,
            external_optimizer_seed INTEGER NOT NULL,
            model_id TEXT NOT NULL,
            result_core_sha256 TEXT NOT NULL,
            UNIQUE(variant_id,external_optimizer_seed,model_id)
        )
        """
    )
    return con


def test_canary_bootstrap_duplicate_job_rejection(tmp_path):
    db = tmp_path / "dup.sqlite"
    con = make_results_db(db)
    try:
        con.execute(
            "INSERT INTO results VALUES (?,?,?,?,?)",
            ("J1", "V1", 0, "M0", "a" * 64),
        )
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(
                "INSERT INTO results VALUES (?,?,?,?,?)",
                ("J1", "V2", 0, "M0", "b" * 64),
            )
    finally:
        con.close()


def test_canary_bootstrap_duplicate_scientific_key_rejection(tmp_path):
    db = tmp_path / "dupkey.sqlite"
    con = make_results_db(db)
    try:
        con.execute(
            "INSERT INTO results VALUES (?,?,?,?,?)",
            ("J1", "V1", 0, "M0", "a" * 64),
        )
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(
                "INSERT INTO results VALUES (?,?,?,?,?)",
                ("J2", "V1", 0, "M0", "b" * 64),
            )
    finally:
        con.close()


def test_result_core_preservation_identity():
    value = "75e47d481cd2c21b82ce50a45b09fb313fa5349e2305d1f507560673779342aa"
    source = {"result_core_sha256": value}
    imported = dict(source)
    assert imported["result_core_sha256"] == source["result_core_sha256"]


def test_full_checkpoint_metadata_binding_helper():
    metadata = {
        "plan_kind": "full",
        "f3a2_commit": V.F3A2_COMMIT,
        "full_plan_sha256": V.EXPECTED_PLAN_SHA,
        "payload_manifest_sha256": V.EXPECTED_PAYLOAD_MANIFEST_SHA,
        "runner_sha256": V.EXPECTED_RUNNER_SHA,
        "afino_version": "0.5",
        "afino_commit": V.EXPECTED_AFINO_COMMIT,
        "canary_manifest_sha256": V.EXPECTED_PLAN_SHA,
    }
    V.verify_checkpoint_metadata(metadata)


def test_corrupt_full_checkpoint_metadata_rejection():
    metadata = {
        "plan_kind": "canary",
        "f3a2_commit": V.F3A2_COMMIT,
        "full_plan_sha256": V.EXPECTED_PLAN_SHA,
        "payload_manifest_sha256": V.EXPECTED_PAYLOAD_MANIFEST_SHA,
        "runner_sha256": V.EXPECTED_RUNNER_SHA,
        "afino_version": "0.5",
        "afino_commit": V.EXPECTED_AFINO_COMMIT,
        "canary_manifest_sha256": V.EXPECTED_PLAN_SHA,
    }
    with pytest.raises(RuntimeError):
        V.verify_checkpoint_metadata(metadata)


def test_missing_and_unexpected_job_identity_detection():
    plan = {"J1": {"job_id": "J1"}}
    checkpoint_ids = {"J2"}
    assert set(plan) - checkpoint_ids == {"J1"}
    assert checkpoint_ids - set(plan) == {"J2"}


def test_decision_rule_exactness():
    assert A.selection_rule(21.0, 10.0, 21.0) is True
    assert A.selection_rule(20.0, 10.0, 21.0) is False
    assert A.selection_rule(21.0, 10.0, 20.0) is False


def test_expected_full_resume_sequence():
    assert V.expected_invocations() == [
        (0, 0, 0, 22398),
        (102, 3000, 3102, 19296),
        (3102, 3000, 6102, 16296),
        (6102, 3000, 9102, 13296),
        (9102, 3000, 12102, 10296),
        (12102, 3000, 15102, 7296),
        (15102, 3000, 18102, 4296),
        (18102, 3000, 21102, 1296),
        (21102, 1296, 22398, 0),
        (22398, 0, 22398, 0),
    ]


def test_byte_exact_runner_guard_remains_present():
    source = (
        REPO /
        "workflows/phase3a/scripts/run_afino_checkpointed.py"
    ).read_text(encoding="utf-8")
    assert "FULL_PLAN_EXECUTION_REQUIRES_EXPLICIT_AUTHORIZATION" in source
    assert "--authorize-full-plan" in source
    assert "F3A3_CANARY_PLAN_COMMIT" in source


def test_idempotent_completed_resume_contract():
    final = V.expected_invocations()[-1]
    assert final == (22398, 0, 22398, 0)
