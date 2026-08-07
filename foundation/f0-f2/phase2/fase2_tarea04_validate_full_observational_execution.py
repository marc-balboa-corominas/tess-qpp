#!/usr/bin/env python3
"""Independent structural validator for F2.4.

This script never imports AFINO or Astropy, never opens FITS, never executes a
model and opens SQLite read-only. It has two modes:

* --snapshot-only: freeze pre-execution hashes and the canary checkpoint state.
* --validate: validate the completed 2,784-row execution and create the
  diagnostic, audit, report and environment artifacts.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import sqlite3
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import scipy


ROOT = Path(__file__).resolve().parent

RUNNER = ROOT / "fase2_tarea03_run_observational_afino_checkpointed.py"
REFERENCE_RUNNER_NAME = "fase1_tarea11_run_nested_afino_checkpointed.py"
FULL_PLAN = ROOT / "fase2_tarea02_exact_afino_execution_plan.csv"
TIME_NPY = ROOT / "fase2_tarea02_eligible_time_values.npy"
FLUX_NPY = ROOT / "fase2_tarea02_eligible_flux_values.npy"
INDEX_NPY = ROOT / "fase2_tarea02_eligible_fits_index_values.npy"
OFFSETS_NPY = ROOT / "fase2_tarea02_eligible_variant_offsets.npy"
VARIANT_MANIFEST = ROOT / "fase2_tarea02_observational_variant_manifest.csv"
RESOLVED_GRID = ROOT / "fase2_tarea02_resolved_decision_grid.csv"
MATERIALIZATION_AUDIT = ROOT / "fase2_tarea02_variant_materialization_audit.json"
CANARY_CHECKPOINT = ROOT / "fase2_tarea03_observational_canary_checkpoint.sqlite"

FULL_CHECKPOINT = ROOT / "fase2_tarea04_observational_full_checkpoint.sqlite"
FULL_RESULTS = ROOT / "fase2_tarea04_observational_full_results.csv"
FULL_DECISIONS = ROOT / "fase2_tarea04_observational_full_decisions.csv"
PREFLIGHT_SNAPSHOT = ROOT / "fase2_tarea04_preflight_snapshot.json"
TEMPORAL_DIAGNOSTIC = ROOT / "fase2_tarea04_temporal_contract_diagnostic.csv"
AUDIT = ROOT / "fase2_tarea04_full_execution_audit.json"
REPORT = ROOT / "fase2_tarea04_full_execution_report.md"
ENVIRONMENT = ROOT / "fase2_tarea04_environment.txt"

EXECUTION_STATUS = "FULL_OBSERVATIONAL_PLAN_EXECUTION_COMPLETE"
TEMPORAL_STATUS = (
    "AFINO_0_5_CONTRACT_CONFIRMED_WITH_DOCUMENTED_"
    "PREREGISTERED_CHECK_MISMATCH"
)

RUNNER_FAMILY = "afino_checkpointed"
RUNNER_IMPLEMENTATION_VERSION = "1.2.0"
AFINO_COMMIT = "6aceac9518fc8056052807e666da9d0c8bebb010"
AFINO_PACKAGE = "0.5"
PYTHON_VERSION = "3.13.13"
NUMPY_VERSION = "2.5.1"
SCIPY_VERSION = "1.18.0"
CUTOFF_HZ = 1.0 / 40.0
ABS_TOLERANCE = 5e-12

EXPECTED_PHYSICAL_HASHES = {
    "fase2_tarea03_run_observational_afino_checkpointed.py":
        "1ddc7b9bafe668a7df8dab534f45bdcdb8519bc9d49041cb2b83ffc8079ad4ab",
    "fase2_tarea02_exact_afino_execution_plan.csv":
        "96c26a49bda9c2485ef02ed6a6de12caf56b54b45a9d997d86fb144e33abeb97",
    "fase2_tarea02_eligible_time_values.npy":
        "46a6c3c3afaf3c389dcdbc52715c68a9984849a12132e110cb0a80894c53b5e3",
    "fase2_tarea02_eligible_flux_values.npy":
        "e943e4f77ba642fc640e082a0fd75ae21ad6057fc31be299101262b42ee4e4f6",
    "fase2_tarea02_eligible_fits_index_values.npy":
        "43798bc41989283b31e863eec703c04719f592ba854f6f928f37e414723e3f06",
    "fase2_tarea02_eligible_variant_offsets.npy":
        "2a06abede71f3d53704f5ac55a4d0a49dccca68606233cdf487613bdabd8dd77",
    "fase2_tarea02_observational_variant_manifest.csv":
        "e89f33d433a48217feb44c07efae33b984377a205c218253553a604df71c5093",
    "fase2_tarea02_resolved_decision_grid.csv":
        "2150657765dff06fb69272c4c11b7bcea656dce2d3fd8faa15b35821dec944dd",
    "fase2_tarea02_variant_materialization_audit.json":
        "2264522b38cb6ea336518369200b3bce1370876bbe3b63273825cbaba3f7991b",
    "fase2_tarea03_observational_canary_checkpoint.sqlite":
        "d4da2f9bb41d78d7a6968bdbf8a7f287b402d109a47eb982d0a6a36ddbc32459",
}

EXPECTED_LOGICAL_HASHES = {
    "canonical_time_payload_sha256":
        "e2f3fbbc8cb12ae94bcb8514d345a708587bae41b9e593cf1cb5035a1b8576e7",
    "canonical_flux_payload_sha256":
        "47059dc92672828f8b6aa262b731dd47ef53aa830e2648cfb7bd4770e00372ee",
    "canonical_fits_index_payload_sha256":
        "d169e884b6dfb5810a192c0bbccb3aa9d08716cbf7353aec3512a585e69039b5",
    "variant_offsets_canonical_sha256":
        "009b2bac827816b2123a4dc1d90226c98e68324c605264f739f257ebe5ccd45b",
}

EXPECTED_REFERENCE_RUNNER_SHA256 = (
    "b5bdbccb4f1170a40163ef99f465fb63d75d51f9d227178af8cdd82934e5695f"
)

PLAN_FIELDS = [
    "job_id", "job_order", "planned_decision_id", "decision_class",
    "variant_id", "event_id", "pair_id", "observational_role",
    "window_variant_id", "processing_profile_id",
    "external_optimizer_seed", "model_id", "model_name", "n_samples",
    "payload_start_offset", "payload_end_offset", "input_time_sha256",
    "input_flux_sha256", "source_fits_sha256",
    "candidate_discovery_use",
]

RESULT_FIELDS = [
    "job_id", "job_order", "planned_decision_id", "decision_class",
    "variant_id", "event_id", "pair_id", "observational_role",
    "window_variant_id", "processing_profile_id",
    "external_optimizer_seed", "model_id", "model_name", "n_samples",
    "payload_start_offset", "payload_end_offset", "input_time_sha256",
    "input_flux_sha256", "input_fits_index_sha256", "source_fits_sha256",
    "median_dt_s", "expected_post_cutoff_bin_count", "status", "bic",
    "log_likelihood", "parameters_json", "formal_m1_period_s", "rchi2",
    "probability", "warning_count", "warning_types_json", "warnings_json",
    "parameter_at_bound", "bound_indices_json", "bound_hits_json",
    "afino_effective_dt_s", "post_cutoff_bin_count",
    "positive_frequency_bin_count", "minimum_frequency_hz",
    "maximum_frequency_hz", "runtime_seconds", "convergence_status",
    "error",
]

DECISION_FIELDS = [
    "planned_decision_id", "decision_class", "variant_id", "event_id",
    "pair_id", "observational_role", "window_variant_id",
    "processing_profile_id", "external_optimizer_seed",
    "decision_status", "valid_models", "bic_m0", "bic_m1", "bic_m2",
    "delta_bic_0_1", "delta_bic_2_1", "qpp_selected",
    "formal_m1_period_s", "period_label",
]

DIAGNOSTIC_FIELDS = [
    "planned_decision_id", "decision_class", "variant_id",
    "external_optimizer_seed", "n_samples", "median_dt_s", "mean_dt_s",
    "afino_effective_dt_s", "requested_median_dt_pass",
    "afino_mean_dt_pass", "requested_rfftfreq_bin_count",
    "afino_fftfreq_positive_bin_count",
    "afino_fftfreq_post_cutoff_bin_count",
    "observed_post_cutoff_bin_count", "requested_bin_contract_pass",
    "afino_bin_contract_pass", "models_agree_on_dt",
    "models_agree_on_bin_count",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(values: np.ndarray, dtype: str) -> str:
    array = np.ascontiguousarray(values, dtype=np.dtype(dtype))
    return hashlib.sha256(array.tobytes(order="C")).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(
    path: Path,
    fields: Sequence[str],
    rows: Iterable[dict[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(fields),
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=None if cwd is None else str(cwd),
        check=check,
        capture_output=True,
        text=True,
    )


def git(repo: Path, *args: str, check: bool = True):
    return run_command(
        ["git", "-C", str(repo), *args],
        check=check,
    )


def readonly_connection(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def locate_reference_runner() -> Path:
    candidates = [
        ROOT / REFERENCE_RUNNER_NAME,
        ROOT / "fase2_tarea03_reference" / REFERENCE_RUNNER_NAME,
    ]
    existing = [path for path in candidates if path.is_file()]
    valid = [
        path for path in existing
        if sha256(path) == EXPECTED_REFERENCE_RUNNER_SHA256
    ]
    invalid = [
        {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}
        for path in existing
        if sha256(path) != EXPECTED_REFERENCE_RUNNER_SHA256
    ]
    if invalid:
        raise RuntimeError(
            f"Non-normative F1.11 reference runner found: {invalid}"
        )
    if not valid:
        raise RuntimeError("No normative F1.11 reference runner found.")
    preferred = ROOT / REFERENCE_RUNNER_NAME
    return preferred if preferred in valid else valid[0]


def source_of_function(path: Path, name: str) -> str:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines()
    node = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    return "\n".join(lines[node.lineno - 1: node.end_lineno])


def verify_transaction_logic() -> dict[str, Any]:
    reference = locate_reference_runner()
    runner_function = source_of_function(
        RUNNER,
        "insert_result_transaction",
    )
    reference_function = source_of_function(
        reference,
        "insert_result_transaction",
    )
    byte_identical = runner_function == reference_function
    required_fragments = {
        "begin_immediate": 'connection.execute("BEGIN IMMEDIATE")',
        "single_insert": "INSERT INTO results",
        "commit": "connection.commit()",
        "rollback": "connection.rollback()",
    }
    fragment_checks = {
        key: fragment in runner_function
        for key, fragment in required_fragments.items()
    }
    if not byte_identical or not all(fragment_checks.values()):
        raise RuntimeError(
            "SQLite per-call transaction logic is not frozen."
        )
    return {
        "reference_runner": reference.name,
        "reference_runner_sha256": sha256(reference),
        "insert_result_transaction_byte_identical": byte_identical,
        "fragment_checks": fragment_checks,
        "one_transaction_per_completed_call": True,
    }


def verify_environment() -> dict[str, Any]:
    repo = ROOT / "afino_release_version"
    if not repo.is_dir():
        raise RuntimeError(f"Missing AFINO repository: {repo}")
    expected_python = (
        ROOT / ".venv" / "Scripts" / "python.exe"
    ).resolve()
    observed_python = Path(sys.executable).resolve()
    if observed_python != expected_python:
        raise RuntimeError(
            f"Wrong Python executable: {observed_python}; "
            f"expected {expected_python}."
        )
    commit = git(repo, "rev-parse", "HEAD").stdout.strip()
    tracked = git(repo, "diff", "--quiet", check=False).returncode
    staged = git(
        repo, "diff", "--cached", "--quiet", check=False
    ).returncode
    if commit != AFINO_COMMIT or tracked != 0 or staged != 0:
        raise RuntimeError(
            "AFINO repository commit or tracked/staged diff changed."
        )
    try:
        afino_version = importlib.metadata.version("afino")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError("AFINO package metadata missing.") from exc
    if afino_version != AFINO_PACKAGE:
        raise RuntimeError("AFINO package version mismatch.")
    if platform.python_version() != PYTHON_VERSION:
        raise RuntimeError("Python version mismatch.")
    if np.__version__ != NUMPY_VERSION:
        raise RuntimeError("NumPy version mismatch.")
    if scipy.__version__ != SCIPY_VERSION:
        raise RuntimeError("SciPy version mismatch.")
    status = git(repo, "status", "--porcelain").stdout.strip()
    pip_freeze = run_command(
        [sys.executable, "-m", "pip", "freeze"]
    ).stdout.splitlines()
    return {
        "python_version": platform.python_version(),
        "python_full": sys.version,
        "python_executable_relative":
            os.path.relpath(sys.executable, ROOT),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "afino_commit": commit,
        "afino_package_version": afino_version,
        "tracked_diff_exit_code": tracked,
        "staged_diff_exit_code": staged,
        "git_status_porcelain": status,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "pip_freeze": pip_freeze,
        "afino_imported": False,
        "astropy_imported": False,
        "fits_opened": False,
    }


def verify_frozen_inputs() -> tuple[dict[str, str], dict[str, str]]:
    physical = {}
    for filename, expected in EXPECTED_PHYSICAL_HASHES.items():
        path = ROOT / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = sha256(path)
        physical[filename] = observed
        if observed != expected:
            raise RuntimeError(
                f"Physical hash mismatch for {filename}: "
                f"{observed} != {expected}"
            )

    time_values = np.load(TIME_NPY, allow_pickle=False)
    flux_values = np.load(FLUX_NPY, allow_pickle=False)
    index_values = np.load(INDEX_NPY, allow_pickle=False)
    offsets = np.load(OFFSETS_NPY, allow_pickle=False)

    contracts = (
        (time_values, "<f8", (28380,)),
        (flux_values, "<f8", (28380,)),
        (index_values, "<i8", (28380,)),
        (offsets, "<i8", (515,)),
    )
    for array, dtype, shape in contracts:
        if array.dtype != np.dtype(dtype) or array.shape != shape:
            raise RuntimeError(
                f"Payload contract mismatch: "
                f"dtype={array.dtype}, shape={array.shape}."
            )
    logical = {
        "canonical_time_payload_sha256":
            canonical_sha256(time_values, "<f8"),
        "canonical_flux_payload_sha256":
            canonical_sha256(flux_values, "<f8"),
        "canonical_fits_index_payload_sha256":
            canonical_sha256(index_values, "<i8"),
        "variant_offsets_canonical_sha256":
            canonical_sha256(offsets, "<i8"),
    }
    if logical != EXPECTED_LOGICAL_HASHES:
        raise RuntimeError(
            f"Logical payload hash mismatch: {logical}"
        )
    audit = json.loads(
        MATERIALIZATION_AUDIT.read_text(encoding="utf-8")
    )

    required_audit_logical_hashes = {
        **logical,
        "ordered_variant_manifest_sha256":
            EXPECTED_PHYSICAL_HASHES[VARIANT_MANIFEST.name],
        "resolved_decision_grid_sha256":
            EXPECTED_PHYSICAL_HASHES[RESOLVED_GRID.name],
        "exact_execution_plan_sha256":
            EXPECTED_PHYSICAL_HASHES[FULL_PLAN.name],
    }
    recorded_logical_hashes = audit.get("logical_hashes")
    if not isinstance(recorded_logical_hashes, dict):
        raise RuntimeError(
            "F2.2 audit logical_hashes is missing or is not an object."
        )

    logical_audit_mismatches = {
        key: {
            "expected": expected,
            "observed": recorded_logical_hashes.get(key),
        }
        for key, expected in required_audit_logical_hashes.items()
        if recorded_logical_hashes.get(key) != expected
    }
    if logical_audit_mismatches:
        raise RuntimeError(
            "F2.2 audit logical hash mismatch: "
            f"{logical_audit_mismatches}"
        )

    required_physical_npy_hashes = {
        TIME_NPY.name: EXPECTED_PHYSICAL_HASHES[TIME_NPY.name],
        FLUX_NPY.name: EXPECTED_PHYSICAL_HASHES[FLUX_NPY.name],
        INDEX_NPY.name: EXPECTED_PHYSICAL_HASHES[INDEX_NPY.name],
        OFFSETS_NPY.name: EXPECTED_PHYSICAL_HASHES[OFFSETS_NPY.name],
    }
    recorded_physical_npy_hashes = audit.get("physical_npy_hashes")
    if not isinstance(recorded_physical_npy_hashes, dict):
        raise RuntimeError(
            "F2.2 audit physical_npy_hashes is missing or is not an object."
        )

    physical_audit_mismatches = {
        key: {
            "expected": expected,
            "observed": recorded_physical_npy_hashes.get(key),
        }
        for key, expected in required_physical_npy_hashes.items()
        if recorded_physical_npy_hashes.get(key) != expected
    }
    if physical_audit_mismatches:
        raise RuntimeError(
            "F2.2 audit physical NPY hash mismatch: "
            f"{physical_audit_mismatches}"
        )

    return physical, logical


def canary_checkpoint_state() -> dict[str, Any]:
    connection = readonly_connection(CANARY_CHECKPOINT)
    try:
        result_rows = int(
            connection.execute(
                "SELECT COUNT(*) FROM results"
            ).fetchone()[0]
        )
        metadata = {
            row["key"]: row["value"]
            for row in connection.execute(
                "SELECT key, value FROM metadata"
            )
        }
    finally:
        connection.close()
    if result_rows != 84 or metadata.get("plan_kind") != "canary":
        raise RuntimeError("Canary checkpoint state is not frozen.")
    return {
        "filename": CANARY_CHECKPOINT.name,
        "sha256": sha256(CANARY_CHECKPOINT),
        "result_rows": result_rows,
        "plan_kind": metadata.get("plan_kind"),
        "runner_implementation_version":
            metadata.get("runner_implementation_version"),
        "plan_sha256": metadata.get("plan_sha256"),
    }


def snapshot_only() -> None:
    if FULL_CHECKPOINT.exists():
        raise RuntimeError(
            "Full checkpoint already exists before execution."
        )
    for path in (
        FULL_RESULTS, FULL_DECISIONS, TEMPORAL_DIAGNOSTIC,
        AUDIT, REPORT, ENVIRONMENT,
    ):
        if path.exists():
            raise RuntimeError(
                f"F2.4 output already exists before execution: {path.name}"
            )
    if PREFLIGHT_SNAPSHOT.exists():
        raise RuntimeError(
            f"Refusing to overwrite {PREFLIGHT_SNAPSHOT.name}."
        )
    environment = verify_environment()
    physical, logical = verify_frozen_inputs()
    transaction = verify_transaction_logic()
    canary = canary_checkpoint_state()
    plan_rows = read_csv(FULL_PLAN)
    if len(plan_rows) != 2784:
        raise RuntimeError("Full plan does not contain 2,784 jobs.")
    if list(plan_rows[0]) != PLAN_FIELDS:
        raise RuntimeError("Full plan schema mismatch.")
    if len({row["job_id"] for row in plan_rows}) != 2784:
        raise RuntimeError("Duplicate job IDs in full plan.")
    if len({
        (
            row["variant_id"],
            row["external_optimizer_seed"],
            row["model_id"],
        )
        for row in plan_rows
    }) != 2784:
        raise RuntimeError("Duplicate scientific keys in full plan.")
    snapshot = {
        "created_at_utc": utc_now(),
        "execution_status": "NOT_STARTED",
        "full_checkpoint_exists": False,
        "full_checkpoint_preexisting_rows": 0,
        "expected_plan_kind": "full",
        "environment": environment,
        "frozen_physical_hashes": physical,
        "frozen_logical_hashes": logical,
        "canary_checkpoint": canary,
        "transaction_logic": transaction,
        "validator_sha256": sha256(Path(__file__).resolve()),
        "confirmations": {
            "afino_imported": False,
            "astropy_imported": False,
            "fits_opened": False,
            "models_executed": False,
        },
    }
    PREFLIGHT_SNAPSHOT.write_text(
        json.dumps(
            snapshot,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print("F2.4 PRE-EXECUTION SNAPSHOT COMPLETE")
    print("full_checkpoint_exists: false")
    print("full_checkpoint_preexisting_rows: 0")
    print("expected_plan_kind: full")
    print("models_executed: false")


def load_payloads() -> dict[str, Any]:
    time_values = np.load(TIME_NPY, allow_pickle=False)
    flux_values = np.load(FLUX_NPY, allow_pickle=False)
    index_values = np.load(INDEX_NPY, allow_pickle=False)
    offsets = np.load(OFFSETS_NPY, allow_pickle=False)
    manifest_rows = read_csv(VARIANT_MANIFEST)
    eligible = [
        row for row in manifest_rows
        if row["admissibility_status"] == "ELIGIBLE_FOR_AFINO"
    ]
    eligible.sort(key=lambda row: int(row["eligible_payload_order"]))
    if len(eligible) != 514:
        raise RuntimeError("Expected 514 eligible variants.")
    by_variant = {}
    for position, row in enumerate(eligible):
        start = int(offsets[position])
        end = int(offsets[position + 1])
        time_slice = np.asarray(
            time_values[start:end],
            dtype=np.float64,
        )
        flux_slice = np.asarray(
            flux_values[start:end],
            dtype=np.float64,
        )
        index_slice = np.asarray(
            index_values[start:end],
            dtype=np.int64,
        )
        if end - start != int(row["retained_n_samples"]):
            raise RuntimeError(
                f"Payload length mismatch: {row['variant_id']}"
            )
        if canonical_sha256(time_slice, "<f8") != row["time_sha256"]:
            raise RuntimeError(
                f"Time hash mismatch: {row['variant_id']}"
            )
        if canonical_sha256(flux_slice, "<f8") != row["flux_sha256"]:
            raise RuntimeError(
                f"Flux hash mismatch: {row['variant_id']}"
            )
        if (
            canonical_sha256(index_slice, "<i8")
            != row["retained_indices_sha256"]
        ):
            raise RuntimeError(
                f"Index hash mismatch: {row['variant_id']}"
            )
        if float(time_slice[0]) != 0.0:
            raise RuntimeError(
                f"Time origin mismatch: {row['variant_id']}"
            )
        if not np.all(np.diff(time_slice) > 0.0):
            raise RuntimeError(
                f"Time not increasing: {row['variant_id']}"
            )
        if not np.all(np.diff(index_slice) == 1):
            raise RuntimeError(
                f"FITS indices not consecutive: {row['variant_id']}"
            )
        by_variant[row["variant_id"]] = {
            "manifest": row,
            "time": time_slice,
            "flux": flux_slice,
            "indices": index_slice,
        }
    return {
        "time_values": time_values,
        "flux_values": flux_values,
        "index_values": index_values,
        "offsets": offsets,
        "by_variant": by_variant,
    }


def read_checkpoint() -> dict[str, Any]:
    connection = readonly_connection(FULL_CHECKPOINT)
    try:
        metadata = {
            row["key"]: row["value"]
            for row in connection.execute(
                "SELECT key, value FROM metadata"
            )
        }
        results = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM results ORDER BY job_order"
            )
        ]
        invocations = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM invocations ORDER BY invocation_id"
            )
        ]
        index_rows = [
            dict(row)
            for row in connection.execute(
                "PRAGMA index_list('results')"
            )
        ]
    finally:
        connection.close()
    return {
        "metadata": metadata,
        "results": results,
        "invocations": invocations,
        "index_rows": index_rows,
    }


def parse_optional_float(value: str) -> float | None:
    return None if value == "" else float(value)


def parse_optional_int(value: str) -> int | None:
    return None if value == "" else int(value)


def bool_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        if value in {"True", "False"}:
            return value
        if value in {"1", "0"}:
            return "True" if value == "1" else "False"
    return "True" if bool(value) else "False"


def compare_plan_result_metadata(
    plan_rows: list[dict[str, str]],
    sqlite_rows: list[dict[str, Any]],
    csv_rows: list[dict[str, str]],
) -> tuple[int, list[dict[str, Any]]]:
    sqlite_by_job = {row["job_id"]: row for row in sqlite_rows}
    csv_by_job = {row["job_id"]: row for row in csv_rows}
    mismatches = []
    mapping = {
        "job_id": "job_id",
        "job_order": "job_order",
        "planned_decision_id": "planned_decision_id",
        "decision_class": "decision_class",
        "variant_id": "variant_id",
        "event_id": "event_id",
        "pair_id": "pair_id",
        "observational_role": "observational_role",
        "window_variant_id": "window_variant_id",
        "processing_profile_id": "processing_profile_id",
        "external_optimizer_seed": "external_optimizer_seed",
        "model_id": "model_id",
        "model_name": "model_name",
        "n_samples": "n_samples",
        "payload_start_offset": "payload_start_offset",
        "payload_end_offset": "payload_end_offset",
        "input_time_sha256": "input_time_sha256",
        "input_flux_sha256": "input_flux_sha256",
        "source_fits_sha256": "source_fits_sha256",
    }
    integer_fields = {
        "job_order", "external_optimizer_seed", "n_samples",
        "payload_start_offset", "payload_end_offset",
    }
    for plan in plan_rows:
        job_id = plan["job_id"]
        sqlite_row = sqlite_by_job.get(job_id)
        csv_row = csv_by_job.get(job_id)
        if sqlite_row is None or csv_row is None:
            mismatches.append({
                "job_id": job_id,
                "kind": "missing_result",
                "sqlite_present": sqlite_row is not None,
                "csv_present": csv_row is not None,
            })
            continue
        for plan_field, result_field in mapping.items():
            expected: Any = plan[plan_field]
            sqlite_value: Any = sqlite_row[result_field]
            csv_value: Any = csv_row[result_field]
            if plan_field in integer_fields:
                expected = int(expected)
                csv_value = int(csv_value)
            if sqlite_value != expected or csv_value != expected:
                mismatches.append({
                    "job_id": job_id,
                    "field": plan_field,
                    "plan": expected,
                    "sqlite": sqlite_value,
                    "csv": csv_value,
                })
    return len(mismatches), mismatches[:100]


def compare_sqlite_csv(
    sqlite_rows: list[dict[str, Any]],
    csv_rows: list[dict[str, str]],
) -> tuple[int, list[dict[str, Any]]]:
    sqlite_by_job = {row["job_id"]: row for row in sqlite_rows}
    csv_by_job = {row["job_id"]: row for row in csv_rows}
    mismatches = []

    exact_text_map = {
        "job_id": "job_id",
        "planned_decision_id": "planned_decision_id",
        "decision_class": "decision_class",
        "variant_id": "variant_id",
        "event_id": "event_id",
        "pair_id": "pair_id",
        "observational_role": "observational_role",
        "window_variant_id": "window_variant_id",
        "processing_profile_id": "processing_profile_id",
        "model_id": "model_id",
        "model_name": "model_name",
        "input_time_sha256": "input_time_sha256",
        "input_flux_sha256": "input_flux_sha256",
        "input_fits_index_sha256": "input_fits_index_sha256",
        "source_fits_sha256": "source_fits_sha256",
        "status": "status",
        "parameters_json": "parameters_json",
        "warning_types_json": "warning_types_json",
        "warnings_json": "warnings_json",
        "bound_indices_json": "bound_indices_json",
        "bound_hits_json": "bound_details_json",
        "convergence_status": "convergence_status",
        "error": "error",
    }
    int_map = {
        "job_order": "job_order",
        "external_optimizer_seed": "external_optimizer_seed",
        "n_samples": "n_samples",
        "payload_start_offset": "payload_start_offset",
        "payload_end_offset": "payload_end_offset",
        "expected_post_cutoff_bin_count":
            "expected_post_cutoff_bin_count",
        "warning_count": "warning_count",
        "post_cutoff_bin_count": "bins_after_cutoff",
        "positive_frequency_bin_count": "positive_frequency_bins",
    }
    float_map = {
        "median_dt_s": "median_dt_s",
        "bic": "BIC",
        "log_likelihood": "lnlike",
        "formal_m1_period_s": "estimated_period_s",
        "rchi2": "rchi2",
        "probability": "probability",
        "afino_effective_dt_s": "afino_effective_dt_s",
        "minimum_frequency_hz": "minimum_frequency_hz",
        "maximum_frequency_hz": "maximum_frequency_hz",
        "runtime_seconds": "runtime_seconds",
    }
    for job_id, sqlite_row in sqlite_by_job.items():
        csv_row = csv_by_job.get(job_id)
        if csv_row is None:
            mismatches.append({
                "job_id": job_id,
                "kind": "missing_csv_row",
            })
            continue
        for csv_field, sqlite_field in exact_text_map.items():
            expected = sqlite_row[sqlite_field]
            expected_text = "" if expected is None else str(expected)
            if csv_row[csv_field] != expected_text:
                mismatches.append({
                    "job_id": job_id,
                    "field": csv_field,
                    "sqlite": expected,
                    "csv": csv_row[csv_field],
                })
        for csv_field, sqlite_field in int_map.items():
            expected = sqlite_row[sqlite_field]
            observed = parse_optional_int(csv_row[csv_field])
            if observed != expected:
                mismatches.append({
                    "job_id": job_id,
                    "field": csv_field,
                    "sqlite": expected,
                    "csv": observed,
                })
        for csv_field, sqlite_field in float_map.items():
            expected = sqlite_row[sqlite_field]
            observed = parse_optional_float(csv_row[csv_field])
            if observed != expected:
                mismatches.append({
                    "job_id": job_id,
                    "field": csv_field,
                    "sqlite": expected,
                    "csv": observed,
                })
        expected_bound = bool_text(sqlite_row["parameter_at_bound"])
        if csv_row["parameter_at_bound"] != expected_bound:
            mismatches.append({
                "job_id": job_id,
                "field": "parameter_at_bound",
                "sqlite": expected_bound,
                "csv": csv_row["parameter_at_bound"],
            })
    return len(mismatches), mismatches[:100]


def recalculate_decisions(
    sqlite_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[
        tuple[str, str, int],
        dict[str, dict[str, Any]],
    ] = defaultdict(dict)
    order = []
    for row in sqlite_rows:
        key = (
            row["planned_decision_id"],
            row["variant_id"],
            int(row["external_optimizer_seed"]),
        )
        if key not in grouped:
            order.append(key)
        grouped[key][row["model_id"]] = row

    decisions = []
    for key in order:
        models = grouped[key]
        if set(models) != {"M0", "M1", "M2"}:
            raise RuntimeError(f"Incomplete model trio: {key}")
        valid_models = sum(
            models[model]["status"] == "OK"
            and models[model]["BIC"] is not None
            and math.isfinite(float(models[model]["BIC"]))
            for model in ("M0", "M1", "M2")
        )
        valid = valid_models == 3
        delta01: float | str = ""
        delta21: float | str = ""
        selected: bool | str = ""
        period: float | str = ""
        label = "unavailable_incomplete_numerical"
        if (
            models["M1"]["status"] == "OK"
            and models["M1"]["estimated_period_s"] is not None
        ):
            period = float(models["M1"]["estimated_period_s"])
            label = "formal_m1_center_not_selected"
        if valid:
            delta01 = (
                float(models["M0"]["BIC"])
                - float(models["M1"]["BIC"])
            )
            delta21 = (
                float(models["M2"]["BIC"])
                - float(models["M1"]["BIC"])
            )
            selected = bool(delta01 > 10.0 and delta21 > 10.0)
            if selected:
                label = "recovered_period_selected"
        exemplar = models["M0"]
        decisions.append({
            "planned_decision_id": key[0],
            "decision_class": exemplar["decision_class"],
            "variant_id": key[1],
            "event_id": exemplar["event_id"],
            "pair_id": exemplar["pair_id"],
            "observational_role": exemplar["observational_role"],
            "window_variant_id": exemplar["window_variant_id"],
            "processing_profile_id":
                exemplar["processing_profile_id"],
            "external_optimizer_seed": key[2],
            "decision_status":
                "VALID" if valid else "INCOMPLETE_NUMERICAL",
            "valid_models": valid_models,
            "bic_m0": "" if models["M0"]["BIC"] is None
                else float(models["M0"]["BIC"]),
            "bic_m1": "" if models["M1"]["BIC"] is None
                else float(models["M1"]["BIC"]),
            "bic_m2": "" if models["M2"]["BIC"] is None
                else float(models["M2"]["BIC"]),
            "delta_bic_0_1": delta01,
            "delta_bic_2_1": delta21,
            "qpp_selected": selected,
            "formal_m1_period_s": period,
            "period_label": label,
        })
    return decisions


def compare_decisions(
    recalculated: list[dict[str, Any]],
    exported: list[dict[str, str]],
) -> tuple[int, list[dict[str, Any]]]:
    exported_by_key = {
        (
            row["planned_decision_id"],
            row["variant_id"],
            int(row["external_optimizer_seed"]),
        ): row
        for row in exported
    }
    mismatches = []
    float_fields = {
        "bic_m0", "bic_m1", "bic_m2",
        "delta_bic_0_1", "delta_bic_2_1",
        "formal_m1_period_s",
    }
    for wanted in recalculated:
        key = (
            wanted["planned_decision_id"],
            wanted["variant_id"],
            int(wanted["external_optimizer_seed"]),
        )
        observed = exported_by_key.get(key)
        if observed is None:
            mismatches.append({
                "key": key,
                "kind": "missing_decision",
            })
            continue
        for field in DECISION_FIELDS:
            expected = wanted[field]
            actual = observed[field]
            if field in float_fields:
                if expected == "":
                    passed = actual == ""
                else:
                    passed = (
                        actual != ""
                        and math.isclose(
                            float(actual),
                            float(expected),
                            rel_tol=0.0,
                            abs_tol=ABS_TOLERANCE,
                        )
                    )
            elif field == "qpp_selected":
                passed = actual == (
                    "" if expected == "" else str(bool(expected))
                )
            else:
                passed = actual == str(expected)
            if not passed:
                mismatches.append({
                    "key": key,
                    "field": field,
                    "expected": expected,
                    "observed": actual,
                })
    return len(mismatches), mismatches[:100]


def temporal_diagnostic(
    sqlite_rows: list[dict[str, Any]],
    payloads: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    grouped: dict[
        tuple[str, str, int],
        list[dict[str, Any]],
    ] = defaultdict(list)
    order = []
    for row in sqlite_rows:
        key = (
            row["planned_decision_id"],
            row["variant_id"],
            int(row["external_optimizer_seed"]),
        )
        if key not in grouped:
            order.append(key)
        grouped[key].append(row)

    rows = []
    counters = Counter()
    for key in order:
        models = sorted(
            grouped[key],
            key=lambda row: row["model_id"],
        )
        if len(models) != 3:
            raise RuntimeError(f"Temporal trio incomplete: {key}")
        payload = payloads["by_variant"][key[1]]
        time_seconds = payload["time"]
        differences = np.diff(time_seconds)
        median_dt = float(np.median(differences))
        mean_dt = float(np.mean(differences))

        requested_frequencies = np.fft.rfftfreq(
            len(time_seconds),
            d=median_dt,
        )
        requested_bins = int(np.count_nonzero(
            (requested_frequencies > 0.0)
            & (requested_frequencies < CUTOFF_HZ)
        ))

        afino_frequencies = np.fft.fftfreq(
            len(time_seconds),
            d=mean_dt,
        )
        afino_positive = afino_frequencies[
            afino_frequencies > 0.0
        ]
        afino_post_cutoff = int(np.count_nonzero(
            afino_positive < CUTOFF_HZ
        ))

        observed_dt_values = [
            row["afino_effective_dt_s"] for row in models
        ]
        observed_bin_values = [
            row["bins_after_cutoff"] for row in models
        ]
        observed_positive_values = [
            row["positive_frequency_bins"] for row in models
        ]

        models_agree_dt = (
            None not in observed_dt_values
            and len(set(observed_dt_values)) == 1
        )
        models_agree_bins = (
            None not in observed_bin_values
            and None not in observed_positive_values
            and len(set(observed_bin_values)) == 1
            and len(set(observed_positive_values)) == 1
        )
        observed_dt = (
            float(observed_dt_values[0])
            if models_agree_dt else float("nan")
        )
        observed_bins = (
            int(observed_bin_values[0])
            if models_agree_bins else -1
        )
        observed_positive = (
            int(observed_positive_values[0])
            if models_agree_bins else -1
        )

        requested_dt_pass = (
            models_agree_dt
            and math.isclose(
                observed_dt,
                median_dt,
                rel_tol=0.0,
                abs_tol=ABS_TOLERANCE,
            )
        )
        afino_dt_pass = (
            models_agree_dt
            and math.isclose(
                observed_dt,
                mean_dt,
                rel_tol=0.0,
                abs_tol=ABS_TOLERANCE,
            )
        )
        requested_bin_pass = (
            models_agree_bins
            and observed_bins == requested_bins
        )
        afino_bin_pass = (
            models_agree_bins
            and observed_bins == afino_post_cutoff
            and observed_positive == len(afino_positive)
        )

        counters["requested_median_dt_matches"] += int(
            requested_dt_pass
        )
        counters["afino_mean_dt_matches"] += int(afino_dt_pass)
        counters["requested_bin_contract_matches"] += int(
            requested_bin_pass
        )
        counters["afino_bin_contract_matches"] += int(
            afino_bin_pass
        )
        counters["models_agree_on_dt"] += int(models_agree_dt)
        counters["models_agree_on_bin_count"] += int(
            models_agree_bins
        )

        exemplar = models[0]
        rows.append({
            "planned_decision_id": key[0],
            "decision_class": exemplar["decision_class"],
            "variant_id": key[1],
            "external_optimizer_seed": key[2],
            "n_samples": exemplar["n_samples"],
            "median_dt_s": format(median_dt, ".17g"),
            "mean_dt_s": format(mean_dt, ".17g"),
            "afino_effective_dt_s":
                "" if not models_agree_dt
                else format(observed_dt, ".17g"),
            "requested_median_dt_pass":
                str(requested_dt_pass).lower(),
            "afino_mean_dt_pass": str(afino_dt_pass).lower(),
            "requested_rfftfreq_bin_count": requested_bins,
            "afino_fftfreq_positive_bin_count":
                len(afino_positive),
            "afino_fftfreq_post_cutoff_bin_count":
                afino_post_cutoff,
            "observed_post_cutoff_bin_count":
                "" if not models_agree_bins else observed_bins,
            "requested_bin_contract_pass":
                str(requested_bin_pass).lower(),
            "afino_bin_contract_pass":
                str(afino_bin_pass).lower(),
            "models_agree_on_dt":
                str(models_agree_dt).lower(),
            "models_agree_on_bin_count":
                str(models_agree_bins).lower(),
        })
    return rows, dict(counters)


def operational_diagnostics(
    sqlite_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sqlite_rows:
        by_model[row["model_id"]].append(row)
    output = {}
    for model in ("M0", "M1", "M2"):
        rows = by_model[model]
        runtimes = [float(row["runtime_seconds"]) for row in rows]
        output[model] = {
            "result_status_counts":
                dict(Counter(row["status"] for row in rows)),
            "warning_calls": sum(
                int(row["warning_count"] or 0) > 0
                for row in rows
            ),
            "warning_totals": sum(
                int(row["warning_count"] or 0)
                for row in rows
            ),
            "bound_hit_calls": sum(
                bool(row["parameter_at_bound"])
                for row in rows
            ),
            "runtime_total_seconds": sum(runtimes),
            "runtime_median_seconds":
                statistics.median(runtimes),
            "convergence_status_counts":
                dict(Counter(
                    row["convergence_status"] for row in rows
                )),
        }
    output["all_models"] = {
        "runtime_total_seconds": sum(
            float(row["runtime_seconds"])
            for row in sqlite_rows
        ),
        "result_status_counts":
            dict(Counter(row["status"] for row in sqlite_rows)),
        "convergence_status_counts":
            dict(Counter(
                row["convergence_status"] for row in sqlite_rows
            )),
    }
    return output


def environment_text(environment: dict[str, Any]) -> str:
    return "\n".join([
        f"Python: {environment['python_version']}",
        f"Python full: {environment['python_full']}",
        "Python executable relative: "
        f"{environment['python_executable_relative']}",
        f"NumPy: {environment['numpy_version']}",
        f"SciPy: {environment['scipy_version']}",
        f"AFINO commit: {environment['afino_commit']}",
        "AFINO package version: "
        f"{environment['afino_package_version']}",
        "Tracked diff exit code: "
        f"{environment['tracked_diff_exit_code']}",
        "Staged diff exit code: "
        f"{environment['staged_diff_exit_code']}",
        f"Platform: {environment['platform']}",
        f"Machine: {environment['machine']}",
        f"Processor: {environment['processor']}",
        "Git status --porcelain:",
        environment["git_status_porcelain"],
        "",
        "pip freeze:",
        *environment["pip_freeze"],
        "",
        "AFINO imported by validator: false",
        "Astropy imported by validator: false",
        "FITS opened by validator: false",
    ])


def validate() -> None:
    for output in (TEMPORAL_DIAGNOSTIC, AUDIT, REPORT, ENVIRONMENT):
        if output.exists():
            raise RuntimeError(
                f"Refusing to overwrite validation output: {output.name}"
            )
    for path in (
        PREFLIGHT_SNAPSHOT, FULL_CHECKPOINT,
        FULL_RESULTS, FULL_DECISIONS,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    snapshot = json.loads(
        PREFLIGHT_SNAPSHOT.read_text(encoding="utf-8")
    )
    environment = verify_environment()
    post_physical, post_logical = verify_frozen_inputs()
    canary_after = canary_checkpoint_state()
    transaction = verify_transaction_logic()

    if (
        snapshot["frozen_physical_hashes"] != post_physical
        or snapshot["frozen_logical_hashes"] != post_logical
    ):
        raise RuntimeError("F2.2 inputs changed during execution.")
    if snapshot["canary_checkpoint"] != canary_after:
        raise RuntimeError(
            "F2.3 canary checkpoint changed during F2.4."
        )

    plan_rows = read_csv(FULL_PLAN)
    csv_rows = read_csv(FULL_RESULTS)
    decision_rows = read_csv(FULL_DECISIONS)
    checkpoint = read_checkpoint()
    sqlite_rows = checkpoint["results"]
    invocations = checkpoint["invocations"]
    metadata = checkpoint["metadata"]

    if len(plan_rows) != 2784:
        raise RuntimeError("Plan row count is not 2,784.")
    if len(sqlite_rows) != 2784:
        raise RuntimeError("SQLite result count is not 2,784.")
    if len(csv_rows) != 2784:
        raise RuntimeError("CSV result count is not 2,784.")
    if len(decision_rows) != 928:
        raise RuntimeError("Decision count is not 928.")
    if list(plan_rows[0]) != PLAN_FIELDS:
        raise RuntimeError("Plan schema mismatch.")
    if list(csv_rows[0]) != RESULT_FIELDS:
        raise RuntimeError("Result CSV schema mismatch.")
    if list(decision_rows[0]) != DECISION_FIELDS:
        raise RuntimeError("Decision CSV schema mismatch.")

    duplicate_job_ids = (
        len(sqlite_rows)
        - len({row["job_id"] for row in sqlite_rows})
    )
    duplicate_scientific_keys = (
        len(sqlite_rows)
        - len({
            (
                row["variant_id"],
                row["external_optimizer_seed"],
                row["model_id"],
            )
            for row in sqlite_rows
        })
    )
    if duplicate_job_ids or duplicate_scientific_keys:
        raise RuntimeError("Duplicate checkpoint results detected.")

    expected_invocations = [
        {
            "existing_before": 0,
            "committed_new": 700,
            "total_after": 700,
            "stop_after": 700,
            "resume_requested": 0,
        },
        {
            "existing_before": 700,
            "committed_new": 700,
            "total_after": 1400,
            "stop_after": 700,
            "resume_requested": 1,
        },
        {
            "existing_before": 1400,
            "committed_new": 700,
            "total_after": 2100,
            "stop_after": 700,
            "resume_requested": 1,
        },
        {
            "existing_before": 2100,
            "committed_new": 684,
            "total_after": 2784,
            "stop_after": None,
            "resume_requested": 1,
        },
        {
            "existing_before": 2784,
            "committed_new": 0,
            "total_after": 2784,
            "stop_after": None,
            "resume_requested": 1,
        },
    ]
    if len(invocations) != 5:
        raise RuntimeError(
            f"Expected five invocations; found {len(invocations)}."
        )
    invocation_mismatches = []
    for observed, expected in zip(invocations, expected_invocations):
        for field, expected_value in expected.items():
            if observed[field] != expected_value:
                invocation_mismatches.append({
                    "invocation_id": observed["invocation_id"],
                    "field": field,
                    "expected": expected_value,
                    "observed": observed[field],
                })
    if invocation_mismatches:
        raise RuntimeError(
            f"Invocation sequence mismatch: {invocation_mismatches}"
        )

    if metadata.get("plan_kind") != "full":
        raise RuntimeError("Checkpoint plan_kind is not full.")
    if (
        metadata.get("plan_sha256")
        != EXPECTED_PHYSICAL_HASHES[FULL_PLAN.name]
    ):
        raise RuntimeError("Checkpoint plan hash mismatch.")
    if (
        metadata.get("runner_sha256")
        != EXPECTED_PHYSICAL_HASHES[RUNNER.name]
    ):
        raise RuntimeError("Checkpoint runner hash mismatch.")
    if (
        metadata.get("runner_implementation_version")
        != RUNNER_IMPLEMENTATION_VERSION
    ):
        raise RuntimeError("Checkpoint runner version mismatch.")

    model_counts = Counter(row["model_id"] for row in sqlite_rows)
    if model_counts != {"M0": 928, "M1": 928, "M2": 928}:
        raise RuntimeError(f"Rows per model mismatch: {model_counts}")

    plan_result_mismatches, plan_examples = (
        compare_plan_result_metadata(
            plan_rows,
            sqlite_rows,
            csv_rows,
        )
    )
    sqlite_csv_mismatches, csv_examples = compare_sqlite_csv(
        sqlite_rows,
        csv_rows,
    )
    recalculated = recalculate_decisions(sqlite_rows)
    decision_mismatches, decision_examples = compare_decisions(
        recalculated,
        decision_rows,
    )
    if (
        plan_result_mismatches
        or sqlite_csv_mismatches
        or decision_mismatches
    ):
        raise RuntimeError(
            "Plan/result/decision correspondence failed."
        )

    primary_decisions = sum(
        row["decision_class"] == "primary"
        for row in decision_rows
    )
    stability_decisions = sum(
        row["decision_class"] == "stability"
        for row in decision_rows
    )
    if primary_decisions != 514 or stability_decisions != 414:
        raise RuntimeError(
            "Primary/stability decision counts are incorrect."
        )

    payloads = load_payloads()
    diagnostic_rows, temporal_counts = temporal_diagnostic(
        sqlite_rows,
        payloads,
    )
    if len(diagnostic_rows) != 928:
        raise RuntimeError(
            "Temporal diagnostic does not contain 928 rows."
        )
    blocking_temporal = {
        "afino_mean_dt_matches":
            temporal_counts.get("afino_mean_dt_matches", 0),
        "afino_bin_contract_matches":
            temporal_counts.get("afino_bin_contract_matches", 0),
        "models_agree_on_dt":
            temporal_counts.get("models_agree_on_dt", 0),
        "models_agree_on_bin_count":
            temporal_counts.get("models_agree_on_bin_count", 0),
    }
    if blocking_temporal != {
        "afino_mean_dt_matches": 928,
        "afino_bin_contract_matches": 928,
        "models_agree_on_dt": 928,
        "models_agree_on_bin_count": 928,
    }:
        raise RuntimeError(
            f"AFINO 0.5 temporal contract blocked: "
            f"{blocking_temporal}"
        )
    write_csv(
        TEMPORAL_DIAGNOSTIC,
        DIAGNOSTIC_FIELDS,
        diagnostic_rows,
    )

    operational = operational_diagnostics(sqlite_rows)
    result_status_counts = dict(
        Counter(row["status"] for row in sqlite_rows)
    )
    decision_status_counts = dict(
        Counter(
            row["decision_status"] for row in decision_rows
        )
    )

    audit = {
        "date_utc": utc_now(),
        "execution_status": EXECUTION_STATUS,
        "temporal_validation_status": TEMPORAL_STATUS,
        "runner_family": RUNNER_FAMILY,
        "runner_implementation_version":
            RUNNER_IMPLEMENTATION_VERSION,
        "planned_jobs": 2784,
        "sqlite_result_rows": 2784,
        "exported_result_rows": 2784,
        "decision_rows": 928,
        "primary_decisions": 514,
        "stability_decisions": 414,
        "pending_jobs": 0,
        "rows_per_model": dict(model_counts),
        "result_status_counts": result_status_counts,
        "decision_status_counts": decision_status_counts,
        "duplicate_job_ids": duplicate_job_ids,
        "duplicate_scientific_keys":
            duplicate_scientific_keys,
        "plan_result_mismatches": plan_result_mismatches,
        "sqlite_csv_mismatches": sqlite_csv_mismatches,
        "decision_recalculation_mismatches":
            decision_mismatches,
        "afino_mean_dt_matches":
            temporal_counts["afino_mean_dt_matches"],
        "afino_bin_contract_matches":
            temporal_counts["afino_bin_contract_matches"],
        "models_agree_on_dt":
            temporal_counts["models_agree_on_dt"],
        "models_agree_on_bin_count":
            temporal_counts["models_agree_on_bin_count"],
        "requested_median_dt_matches":
            temporal_counts["requested_median_dt_matches"],
        "requested_median_dt_mismatches":
            928 - temporal_counts["requested_median_dt_matches"],
        "requested_rfftfreq_bin_matches":
            temporal_counts["requested_bin_contract_matches"],
        "requested_rfftfreq_bin_mismatches":
            928 - temporal_counts[
                "requested_bin_contract_matches"
            ],
        "resume_and_idempotence": {
            "committed_new_sequence": [700, 700, 700, 684, 0],
            "existing_before_sequence":
                [0, 700, 1400, 2100, 2784],
            "total_after_sequence":
                [700, 1400, 2100, 2784, 2784],
            "invocations": invocations,
        },
        "input_integrity": {
            "pre_execution_physical_hashes":
                snapshot["frozen_physical_hashes"],
            "post_execution_physical_hashes": post_physical,
            "pre_execution_logical_hashes":
                snapshot["frozen_logical_hashes"],
            "post_execution_logical_hashes": post_logical,
            "f2_2_inputs_unchanged": True,
            "runner_unchanged": True,
            "full_plan_unchanged": True,
        },
        "canary_checkpoint_integrity": {
            "before": snapshot["canary_checkpoint"],
            "after": canary_after,
            "unchanged": True,
        },
        "transaction_validation": transaction,
        "checkpoint": {
            "filename": FULL_CHECKPOINT.name,
            "sha256": sha256(FULL_CHECKPOINT),
            "plan_kind": metadata.get("plan_kind"),
            "runner_sha256": metadata.get("runner_sha256"),
            "plan_sha256": metadata.get("plan_sha256"),
            "result_rows": len(sqlite_rows),
            "invocation_rows": len(invocations),
        },
        "temporal_contract": {
            "absolute_tolerance_s": ABS_TOLERANCE,
            "relative_tolerance": 0.0,
            "requested_preregistered_check": {
                "dt": "median(diff(time_seconds))",
                "frequencies":
                    "numpy.fft.rfftfreq(N, d=requested_dt)",
                "dt_matches":
                    temporal_counts["requested_median_dt_matches"],
                "dt_mismatches":
                    928 - temporal_counts[
                        "requested_median_dt_matches"
                    ],
                "bin_matches":
                    temporal_counts[
                        "requested_bin_contract_matches"
                    ],
                "bin_mismatches":
                    928 - temporal_counts[
                        "requested_bin_contract_matches"
                    ],
                "mismatches_are_runner_failures": False,
            },
            "observed_afino_0_5_contract": {
                "dt": "mean(diff(time_seconds))",
                "frequencies":
                    "numpy.fft.fftfreq(N, d=afino_dt); "
                    "frequencies > 0",
                "dt_matches": 928,
                "bin_matches": 928,
                "models_agree_on_dt": 928,
                "models_agree_on_bin_count": 928,
                "confirmed": True,
            },
        },
        "operational_diagnostics": operational,
        "environment": environment,
        "validator": {
            "filename": Path(__file__).resolve().name,
            "sha256": sha256(Path(__file__).resolve()),
            "afino_imported": False,
            "astropy_imported": False,
            "fits_opened": False,
            "sqlite_opened_read_only": True,
            "models_executed": False,
        },
        "diagnostic": {
            "filename": TEMPORAL_DIAGNOSTIC.name,
            "sha256": sha256(TEMPORAL_DIAGNOSTIC),
            "rows": len(diagnostic_rows),
        },
        "mismatch_examples": {
            "plan_result": plan_examples,
            "sqlite_csv": csv_examples,
            "decisions": decision_examples,
        },
        "confirmations": {
            "canary_results_imported": False,
            "canary_checkpoint_modified": False,
            "fits_opened": False,
            "dataset_regenerated": False,
            "quality_filter_reapplied": False,
            "detrending_recomputed": False,
            "interpolation_performed": False,
            "gap_filling_performed": False,
            "candidate_discovery_authorized": False,
            "scientific_results_interpreted": False,
            "selection_threshold_modified": False,
            "afino_code_modified": False,
            "runner_modified": False,
            "full_plan_modified": False,
            "failed_jobs_redrawn": False,
            "jobs_removed": False,
        },
    }

    report = f"""# Fase 2 — Tarea 2.4

## Ejecución completa del plan observacional exacto

**Estado de ejecución:** `{EXECUTION_STATUS}`  
**Validación temporal:** `{TEMPORAL_STATUS}`  
**Runner:** `{RUNNER_FAMILY}` `{RUNNER_IMPLEMENTATION_VERSION}`

### Completitud de ejecución

Se ejecutaron exactamente las 2.784 llamadas del plan F2.2: 928 para M0,
928 para M1 y 928 para M2. El checkpoint contiene 2.784 filas, el CSV exporta
2.784 resultados y la tabla de decisiones contiene 928 filas, distribuidas
en 514 decisiones primarias y 414 de estabilidad. No queda ningún trabajo
pendiente. Todos los estados, incluidos posibles errores numéricos, se
conservaron sin eliminar ni repetir selectivamente trabajos.

### Integridad plan–resultado

El validador independiente comparó literalmente los 2.784 `job_id` y sus
metadatos entre el plan, SQLite y el CSV. También verificó las claves
`variant_id`–seed–modelo, los offsets, tamaños, hashes de tiempo y flujo,
metadatos observacionales, warnings, bounds y outputs numéricos. No aparecieron
duplicados, discrepancias plan–resultado ni diferencias SQLite–CSV. Las 928
decisiones se recalcularon desde los tres BIC con tolerancia absoluta de
5×10⁻¹² y tolerancia relativa cero, sin discrepancias.

### Reanudación e idempotencia

El checkpoint era nuevo y contenía cero filas antes de comenzar. Las cinco
invocaciones añadieron exactamente 700, 700, 700, 684 y 0 trabajos. Los
totales acumulados fueron 700, 1.400, 2.100, 2.784 y 2.784. La quinta pasada
no ejecutó llamadas nuevas y exportó desde el checkpoint. La lógica de una
transacción SQLite independiente por llamada coincide byte a byte con el
runner congelado F1.11.

### Contrato temporal solicitado

El control prerregistrado basado en `median(diff(time))` y
`numpy.fft.rfftfreq` se mantuvo sin modificar para conservar trazabilidad.
Coincidió en {audit['requested_median_dt_matches']} de 928 decisiones para la
cadencia y en {audit['requested_rfftfreq_bin_matches']} de 928 para el número
de bins. Sus desacuerdos se documentan, pero no se convierten en fallos del
runner porque no representan la convención utilizada por AFINO 0.5.

### Contrato temporal observado de AFINO 0.5

La validación separada calculó `mean(diff(time))` y las frecuencias
estrictamente positivas de `numpy.fft.fftfreq`. Este contrato coincidió en
928/928 decisiones para la cadencia efectiva y en 928/928 para los bins tras
el cutoff. Los tres modelos coincidieron entre sí en cadencia y conteo de bins
en 928/928 decisiones.

### Diagnósticos operativos

Los conteos de estado, warnings, bounds, tiempos totales y medianos y
`convergence_status` se registraron únicamente por modelo. No se calcularon
tasas de selección, retención, ganancias, pérdidas ni comparaciones por clase,
producto, perfil, ventana o periodo.

### Interpretaciones científicas aplazadas

Los payloads F2.2, el plan completo, el runner y el checkpoint canary F2.3
permanecieron intactos. No se abrió ningún FITS, no se repitió preprocesamiento
y no se interpretaron resultados científicos. El análisis prerregistrado de
robustez queda reservado para F2.5. Esta tarea solo establece que la ejecución
fue completa, reanudable, idempotente y estructuralmente coherente con los
artefactos congelados; no evalúa el significado físico de ninguna selección.

`{EXECUTION_STATUS}`
"""

    report_word_count = len(
        re.findall(
            r"\b[\wÁÉÍÓÚÜÑáéíóúüñ]+\b",
            report,
        )
    )
    if not 450 <= report_word_count <= 700:
        raise RuntimeError(
            f"Report word count {report_word_count} outside 450-700."
        )
    audit["report_word_count"] = report_word_count

    ENVIRONMENT.write_text(
        environment_text(environment),
        encoding="utf-8",
    )
    AUDIT.write_text(
        json.dumps(
            audit,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )
    REPORT.write_text(report, encoding="utf-8")

    print(EXECUTION_STATUS)
    print(TEMPORAL_STATUS)
    print("planned_jobs: 2784")
    print("sqlite_result_rows: 2784")
    print("exported_result_rows: 2784")
    print("decision_rows: 928")
    print("pending_jobs: 0")
    print("afino_mean_dt_matches: 928/928")
    print("afino_bin_contract_matches: 928/928")
    print("models_agree_on_dt: 928/928")
    print("models_agree_on_bin_count: 928/928")
    print("scientific_results_interpreted: false")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--snapshot-only", action="store_true")
    mode.add_argument("--validate", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.snapshot_only:
        snapshot_only()
    else:
        validate()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"F2.4 VALIDATION BLOCKED: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise
