#!/usr/bin/env python3
"""
F3B.3 — checkpointed AFINO runner for frozen DEVELOPMENT payloads.

Scientific execution core is intentionally inherited from the validated F3A runner:
AfinoSeries -> prep_series -> per-model np.random.seed -> main_analysis.

Safety boundary:
- only the frozen F3B.2 DEVELOPMENT retained payload arrays are opened;
- no generator module is imported and no synthetic arrays are regenerated;
- truth tables are not read by this runner;
- HELDOUT paths/manifests are rejected;
- full-plan execution requires an explicit committed authorization JSON;
- AFINO execution environment must match the frozen F3A environment binding.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import sqlite3
import subprocess
import sys
import time
import traceback
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
import scipy

RUNNER_FAMILY = "phase3b_development_checkpointed"
RUNNER_IMPLEMENTATION_VERSION = "1.0.0"

F3B2_COMMIT = "7550679a8b0ea1f028987a38cfbe7ac7671fb8ce"
F3B2_TAG = "phase3b-development-materialization-v1"

EXPECTED_AFINO_VERSION = "0.5"
EXPECTED_AFINO_COMMIT = "6aceac9518fc8056052807e666da9d0c8bebb010"
EXPECTED_PYTHON_VERSION = "3.13.13"
EXPECTED_NUMPY_VERSION = "2.5.1"
EXPECTED_SCIPY_VERSION = "1.18.0"
EXPECTED_OS = "Windows-11-10.0.26200-SP0"
EXPECTED_ARCHITECTURE = "AMD64"
EXPECTED_BYTEORDER = "little"

EXPECTED_SOURCE_PLAN_SHA256 = "7cb503b0c43c1251c28d828aa71707208ebca8fced4680f13662cb91ab2a2daf"
EXPECTED_PAYLOAD_MANIFEST_SHA256 = "fcfc9b20d111ba711fc4e05de28f340bed9046efe40e6877efbd991c410df6c6"
EXPECTED_BLINDED_PLAN_SHA256 = "180446352dc055132989cfb562e28c3df4730f2de8f38be767c6a79cc83cf600"
EXPECTED_CANARY_DECISION_SHA256 = "91921998ddf9a7b57884b9da578f80a360d2e278570c5f962d2b4c5d4a213d5f"
EXPECTED_CANARY_JOB_SHA256 = "e28fca1275abdab169d47b95ce97eab51df81a2e2a3a2b2c7646072471095f82"
EXPECTED_ENV_BINDING_SHA256 = "1105199deead4782b76008d4a7c1ba636f7b3898a4808bb76585909d1bbe85c9"

EXPECTED_FULL_JOBS = 12744
EXPECTED_FULL_DECISIONS = 4248
EXPECTED_CANARY_JOBS = 648
EXPECTED_CANARY_DECISIONS = 216

MODEL_SPECS = {
    "M0": "pow_const",
    "M1": "pow_const_gauss",
    "M2": "bpow_const",
}
LOW_FREQUENCY_CUTOFF_HZ = 0.025
BOUND_ATOL = 1.0e-7

OVERWRITE_GAUSS_BOUNDS = (
    (-10.0, 10.0),
    (-1.0, 6.0),
    (-20.0, 10.0),
    (-16.0, 5.0),
    (float(np.log(1.0 / 300.0)), float(np.log(1.0 / 40.0))),
    (0.05, 0.25),
)
MODEL_BOUNDS = {
    "pow_const": (
        (-10.0, 10.0),
        (-1.0, 6.0),
        (-20.0, 10.0),
    ),
    "pow_const_gauss": OVERWRITE_GAUSS_BOUNDS,
    "bpow_const": (
        (None, None),
        (1.0, 9.0),
        (0.0033, 0.25),
        (1.0, 9.0),
        (None, None),
    ),
}

TABLE_DIR = Path("workflows/phase3b/development/evidence/tables")
CONFIG_DIR = Path("workflows/phase3b/development/config")
ARRAY_DIR = Path("data/interim/phase3b/f3b2_development")

SOURCE_PLAN_REL = TABLE_DIR / "f3b2_development_exact_afino_plan.csv"
PAYLOAD_MANIFEST_REL = TABLE_DIR / "f3b2_development_payload_manifest.csv"
BLINDED_PLAN_REL = TABLE_DIR / "f3b3_blinded_execution_plan.csv"
CANARY_DECISION_REL = TABLE_DIR / "f3b3_canary_decision_manifest.csv"
CANARY_JOB_REL = TABLE_DIR / "f3b3_canary_job_manifest.csv"
ENV_BINDING_REL = CONFIG_DIR / "f3b3_afino_execution_environment_binding.json"

PAYLOAD_PHYSICAL_HASHES = {
    "retained_time_s.npy": "fe86e78f73780a3c965be8f34385ea3ece4a7eedf7b566a9f206df445aee8e7b",
    "retained_flux.npy": "b12a873c629125843c5dc9dcc77ecc4bf3bc6272bbfd1d5dac9d3078c8e1c6a4",
    "retained_native_index.npy": "982b010abc1e59c723e01c088f85868d1a0a87fac45368a495005418f055e2ca",
    "retained_offsets.npy": "b1a25174a990266223d4c7d8c7313297db2ecf12674765950c90a5e24a2e4364",
}

RESULT_COLUMNS = [
    "job_id",
    "job_order",
    "planned_decision_id",
    "decision_class",
    "simulation_unit_id",
    "background_realization_id",
    "external_optimizer_seed",
    "model_id",
    "model_name",
    "payload_logical_sha256",
    "status",
    "bic",
    "log_likelihood",
    "parameters_json",
    "formal_m1_period_s",
    "rchi2",
    "probability",
    "warning_count",
    "warning_types_json",
    "warnings_json",
    "parameter_at_bound",
    "bound_parameters_json",
    "convergence_status",
    "afino_effective_dt_s",
    "positive_frequency_bin_count",
    "post_cutoff_bin_count",
    "minimum_frequency_hz",
    "maximum_frequency_hz",
    "runtime_seconds",
    "afino_version",
    "afino_commit",
    "result_core_sha256",
    "error",
    "completed_at_utc",
]

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def canonical_array(values: Any, dtype: str) -> np.ndarray:
    return np.ascontiguousarray(values, dtype=np.dtype(dtype))

def canonical_hash(values: Any, dtype: str) -> str:
    return sha256_bytes(canonical_array(values, dtype).tobytes(order="C"))

def logical_payload_hash(
    simulation_unit_id: str,
    time_seconds: np.ndarray,
    flux: np.ndarray,
    native_index: np.ndarray,
) -> str:
    if "\x00" in simulation_unit_id:
        raise RuntimeError("simulation_unit_id contains NUL")
    payload = (
        b"F3B2_PAYLOAD_V1\x00"
        + simulation_unit_id.encode("utf-8")
        + b"\x00"
        + canonical_array(time_seconds, "<f8").tobytes(order="C")
        + canonical_array(flux, "<f8").tobytes(order="C")
        + canonical_array(native_index, "<i8").tobytes(order="C")
    )
    return sha256_bytes(payload)

def json_compact(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fields), extrasaction="raise", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)

def run_command(command: list[str], *, cwd: Path | None = None, check: bool = True):
    return subprocess.run(
        command,
        cwd=None if cwd is None else str(cwd),
        check=check,
        capture_output=True,
        text=True,
    )

def git(repo: Path, *args: str, check: bool = True):
    return run_command(["git", "-C", str(repo), *args], check=check)

def finite_float(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise ValueError(f"{name} is not finite: {x!r}")
    return x

def verify_environment(afino_repo: Path, binding: dict[str, Any]) -> dict[str, Any]:
    if not afino_repo.is_dir():
        raise RuntimeError(f"AFINO repo missing: {afino_repo}")

    expected_python = (
        afino_repo.parent / ".venv" / "Scripts" / "python.exe"
        if os.name == "nt"
        else afino_repo.parent / ".venv" / "bin" / "python"
    ).resolve()
    observed_python = Path(sys.executable).resolve()
    if observed_python != expected_python:
        raise RuntimeError(
            "F3B.3 must use the frozen F3A AFINO environment.\n"
            f"observed={observed_python}\nexpected={expected_python}"
        )

    commit = git(afino_repo, "rev-parse", "HEAD").stdout.strip()
    if commit != EXPECTED_AFINO_COMMIT:
        raise RuntimeError(f"AFINO commit mismatch: {commit}")

    if git(afino_repo, "diff", "--quiet", check=False).returncode != 0:
        raise RuntimeError("AFINO tracked working tree differs from frozen commit.")
    if git(afino_repo, "diff", "--cached", "--quiet", check=False).returncode != 0:
        raise RuntimeError("AFINO staged tree differs from frozen commit.")

    try:
        version = importlib.metadata.version("afino")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError("afino package not installed") from exc

    observed = {
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "os": platform.platform(),
        "architecture": platform.machine(),
        "byteorder": sys.byteorder,
        "afino_package_version": version,
        "afino_commit": commit,
    }
    expected = {
        "python_version": EXPECTED_PYTHON_VERSION,
        "numpy_version": EXPECTED_NUMPY_VERSION,
        "scipy_version": EXPECTED_SCIPY_VERSION,
        "os": EXPECTED_OS,
        "architecture": EXPECTED_ARCHITECTURE,
        "byteorder": EXPECTED_BYTEORDER,
        "afino_package_version": EXPECTED_AFINO_VERSION,
        "afino_commit": EXPECTED_AFINO_COMMIT,
    }
    for key, exp in expected.items():
        if observed[key] != exp:
            raise RuntimeError(f"F3B.3 environment mismatch {key}: {observed[key]} != {exp}")

    frozen = binding["execution_environment"]
    for key in ["python_version", "numpy_version", "scipy_version", "os", "architecture", "byteorder",
                "afino_package_version", "afino_commit"]:
        if frozen[key] != expected[key]:
            raise RuntimeError(f"Execution binding drift in {key}")

    return observed

def verify_project_freeze(repo: Path) -> dict[str, Any]:
    peeled = git(repo, "rev-parse", f"{F3B2_TAG}^{{}}").stdout.strip()
    if peeled != F3B2_COMMIT:
        raise RuntimeError(f"{F3B2_TAG} moved: {peeled} != {F3B2_COMMIT}")

    if git(repo, "merge-base", "--is-ancestor", F3B2_COMMIT, "HEAD", check=False).returncode != 0:
        raise RuntimeError("Current HEAD is not descended from frozen F3B.2 commit.")

    expected_hashes = {
        SOURCE_PLAN_REL: EXPECTED_SOURCE_PLAN_SHA256,
        PAYLOAD_MANIFEST_REL: EXPECTED_PAYLOAD_MANIFEST_SHA256,
        BLINDED_PLAN_REL: EXPECTED_BLINDED_PLAN_SHA256,
        CANARY_DECISION_REL: EXPECTED_CANARY_DECISION_SHA256,
        CANARY_JOB_REL: EXPECTED_CANARY_JOB_SHA256,
        ENV_BINDING_REL: EXPECTED_ENV_BINDING_SHA256,
    }
    for rel, expected in expected_hashes.items():
        p = repo / rel
        if not p.is_file():
            raise RuntimeError(f"Missing frozen input: {rel}")
        actual = sha256_file(p)
        if actual != expected:
            raise RuntimeError(f"Hash mismatch {rel}: {actual} != {expected}")

    if (repo / "data/interim/phase3b/heldout").exists():
        raise RuntimeError("HELDOUT materialized path exists; F3B.3 execution is blocked.")

    status = git(repo, "status", "--porcelain").stdout.strip()
    if status:
        raise RuntimeError("F3B.3 execution requires a clean Git working tree.")

    binding = json.loads((repo / ENV_BINDING_REL).read_text(encoding="utf-8"))
    return binding

def load_payload_dataset(repo: Path) -> dict[str, Any]:
    for name, expected in PAYLOAD_PHYSICAL_HASHES.items():
        p = repo / ARRAY_DIR / name
        if not p.is_file():
            raise RuntimeError(f"Missing DEVELOPMENT payload array: {p}")
        actual = sha256_file(p)
        if actual != expected:
            raise RuntimeError(f"Frozen array hash mismatch {name}: {actual}")

    manifest = read_csv(repo / PAYLOAD_MANIFEST_REL)
    if len(manifest) != 4320:
        raise RuntimeError(f"Unexpected payload manifest rows: {len(manifest)}")

    mapping: dict[str, dict[str, Any]] = {}
    for row in manifest:
        sid = row["simulation_unit_id"]
        if sid in mapping:
            raise RuntimeError(f"Duplicate payload simulation_unit_id: {sid}")
        mapping[sid] = {
            "simulation_unit_id": sid,
            "background_realization_id": row["background_realization_id"],
            "offset": int(row["retained_offset"]),
            "length": int(row["retained_length"]),
            "time_sha256": row["retained_time_sha256"],
            "flux_sha256": row["retained_flux_sha256"],
            "native_index_sha256": row["retained_native_index_sha256"],
            "logical_payload_sha256": row["logical_payload_sha256"],
            "materialization_status": row["materialization_status"],
        }

    arrays = {
        "time": np.load(repo / ARRAY_DIR / "retained_time_s.npy", mmap_mode="r"),
        "flux": np.load(repo / ARRAY_DIR / "retained_flux.npy", mmap_mode="r"),
        "native_index": np.load(repo / ARRAY_DIR / "retained_native_index.npy", mmap_mode="r"),
        "offsets": np.load(repo / ARRAY_DIR / "retained_offsets.npy", mmap_mode="r"),
    }
    if len(arrays["offsets"]) != 4321:
        raise RuntimeError("retained_offsets.npy must contain 4321 entries.")

    return {"manifest": mapping, **arrays}

def validate_job(job: dict[str, str]) -> dict[str, Any]:
    model_id = job["model_id"]
    if model_id not in MODEL_SPECS:
        raise RuntimeError(f"Unknown model_id: {model_id}")
    if job["afino_version"] != EXPECTED_AFINO_VERSION:
        raise RuntimeError("Plan AFINO version mismatch.")
    if job["afino_commit"] != EXPECTED_AFINO_COMMIT:
        raise RuntimeError("Plan AFINO commit mismatch.")
    if float(job["low_frequency_cutoff_hz"]) != LOW_FREQUENCY_CUTOFF_HZ:
        raise RuntimeError("Plan low-frequency cutoff mismatch.")
    if job["execution_status"] != "NOT_EXECUTED":
        raise RuntimeError("Frozen plan job is not NOT_EXECUTED.")
    return {
        **job,
        "job_order": int(job["job_order"]),
        "external_optimizer_seed": int(job["external_optimizer_seed"]),
        "model_name": MODEL_SPECS[model_id],
    }

def validate_full_authorization(authorization_path: Path | None) -> dict[str, Any]:
    if authorization_path is None:
        raise RuntimeError("FULL_DEVELOPMENT_EXECUTION_REQUIRES_EXPLICIT_AUTHORIZATION")
    if "heldout" in str(authorization_path.resolve()).lower():
        raise RuntimeError("HELDOUT authorization path is prohibited.")
    if not authorization_path.is_file():
        raise RuntimeError(f"Full authorization missing: {authorization_path}")
    auth = json.loads(authorization_path.read_text(encoding="utf-8"))
    required = {
        "frozen_jobs": 12744,
        "frozen_decisions": 4248,
        "baseline_decisions": 3600,
        "stability_extra_decisions": 648,
        "validated_canary_jobs": 648,
        "remaining_new_jobs": 12096,
        "canary_reuse": True,
        "canary_rerun": False,
        "development_only": True,
        "heldout_authorized": False,
        "scientific_metrics_authorized": False,
        "candidate_rule_fitting_authorized": False,
    }
    for key, value in required.items():
        if auth.get(key) != value:
            raise RuntimeError(f"Invalid full authorization field {key}.")
    return auth

def load_plan(
    repo: Path,
    manifest_path: Path,
    *,
    authorization_path: Path | None = None,
) -> tuple[list[dict[str, Any]], str, str]:
    full_rows_raw = read_csv(repo / BLINDED_PLAN_REL)
    if len(full_rows_raw) != EXPECTED_FULL_JOBS:
        raise RuntimeError("Blinded full plan row count mismatch.")
    full_by_id = {r["job_id"]: r for r in full_rows_raw}
    if len(full_by_id) != EXPECTED_FULL_JOBS:
        raise RuntimeError("Duplicate job_id in blinded full plan.")

    manifest_path = manifest_path.resolve()
    canary_path = (repo / CANARY_JOB_REL).resolve()
    full_path = (repo / BLINDED_PLAN_REL).resolve()

    if "heldout" in str(manifest_path).lower():
        raise RuntimeError("HELDOUT plan is prohibited.")

    if manifest_path == canary_path:
        rows = read_csv(manifest_path)
        if len(rows) != EXPECTED_CANARY_JOBS:
            raise RuntimeError("Canary job count mismatch.")
        jobs: list[dict[str, Any]] = []
        for row in rows:
            src = full_by_id.get(row["job_id"])
            if src is None:
                raise RuntimeError(f"Unknown canary job: {row['job_id']}")
            projected = {k: row[k] for k in src.keys()}
            if projected != src:
                raise RuntimeError(f"Canary job differs from blinded source plan: {row['job_id']}")
            jobs.append(validate_job(projected))
        if len({(j["simulation_unit_id"], j["external_optimizer_seed"], j["model_id"]) for j in jobs}) != len(jobs):
            raise RuntimeError("Duplicate scientific key in canary manifest.")
        jobs.sort(key=lambda r: int(next(x["canary_job_order"] for x in rows if x["job_id"] == r["job_id"])))
        return jobs, "canary", sha256_file(manifest_path)

    if manifest_path == full_path:
        validate_full_authorization(authorization_path)
        jobs = [validate_job(r) for r in full_rows_raw]
        if len({(j["simulation_unit_id"], j["external_optimizer_seed"], j["model_id"]) for j in jobs}) != len(jobs):
            raise RuntimeError("Duplicate scientific key in blinded full plan.")
        return jobs, "full", sha256_file(manifest_path)

    raise RuntimeError("Unknown job manifest. Only frozen canary or blinded full plan is accepted.")

def extract_payload(job: dict[str, Any], payloads: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    row = payloads["manifest"].get(job["simulation_unit_id"])
    if row is None:
        raise RuntimeError(f"Unknown payload simulation_unit_id: {job['simulation_unit_id']}")
    if row["materialization_status"] != "MATERIALIZED":
        raise RuntimeError("Job references a non-materialized payload.")
    if row["background_realization_id"] != job["background_realization_id"]:
        raise RuntimeError("Background-realization mismatch.")
    if row["logical_payload_sha256"] != job["payload_logical_sha256"]:
        raise RuntimeError("Payload logical SHA mismatch.")

    off, length = row["offset"], row["length"]
    t = np.asarray(payloads["time"][off:off+length], dtype=np.float64)
    f = np.asarray(payloads["flux"][off:off+length], dtype=np.float64)
    idx = np.asarray(payloads["native_index"][off:off+length], dtype=np.int64)

    if len(t) != length or len(f) != length or len(idx) != length:
        raise RuntimeError("Payload slice length mismatch.")
    if canonical_hash(t, "<f8") != row["time_sha256"]:
        raise RuntimeError("Payload time hash mismatch.")
    if canonical_hash(f, "<f8") != row["flux_sha256"]:
        raise RuntimeError("Payload flux hash mismatch.")
    if canonical_hash(idx, "<i8") != row["native_index_sha256"]:
        raise RuntimeError("Payload native-index hash mismatch.")
    if logical_payload_hash(job["simulation_unit_id"], t, f, idx) != row["logical_payload_sha256"]:
        raise RuntimeError("Payload logical hash reconstruction mismatch.")
    if not np.all(np.isfinite(t)) or not np.all(np.isfinite(f)):
        raise RuntimeError("Non-finite DEVELOPMENT payload.")
    if not np.all(np.diff(t) > 0.0):
        raise RuntimeError("Time is not strictly increasing.")
    if not np.all(np.diff(idx) == 1):
        raise RuntimeError("Native indices are not consecutive.")
    return t, f, idx

def inspect_bounds(model_name: str, parameters: np.ndarray) -> tuple[bool, list[dict[str, Any]]]:
    bounds = MODEL_BOUNDS[model_name]
    if len(parameters) != len(bounds):
        return False, [{
            "status": "parameter_count_mismatch",
            "parameter_count": int(len(parameters)),
            "bound_count": int(len(bounds)),
        }]
    hits: list[dict[str, Any]] = []
    for i, (value, (lower, upper)) in enumerate(zip(parameters, bounds)):
        value = float(value)
        if lower is not None and np.isclose(value, lower, rtol=0.0, atol=BOUND_ATOL):
            hits.append({"parameter_index": i, "side": "lower", "value": value, "bound": float(lower)})
        if upper is not None and np.isclose(value, upper, rtol=0.0, atol=BOUND_ATOL):
            hits.append({"parameter_index": i, "side": "upper", "value": value, "bound": float(upper)})
    return bool(hits), hits

def warning_payload(caught: list[warnings.WarningMessage]) -> tuple[int, str, str]:
    entries = [{
        "category": item.category.__name__,
        "message": str(item.message),
        "filename": Path(item.filename).name,
        "lineno": int(item.lineno),
    } for item in caught]
    types = sorted({f"{x['category']}: {x['message']}" for x in entries})
    return len(entries), json_compact(types), json_compact(entries)

def result_core_sha256(result: dict[str, Any]) -> str:
    fields = [
        "job_id", "job_order", "planned_decision_id", "decision_class", "simulation_unit_id",
        "background_realization_id", "external_optimizer_seed", "model_id", "model_name",
        "payload_logical_sha256", "status", "bic", "log_likelihood",
        "parameters_json", "formal_m1_period_s", "rchi2", "probability",
        "warning_count", "warning_types_json", "warnings_json", "parameter_at_bound",
        "bound_parameters_json", "convergence_status", "afino_effective_dt_s",
        "positive_frequency_bin_count", "post_cutoff_bin_count",
        "minimum_frequency_hz", "maximum_frequency_hz",
        "afino_version", "afino_commit", "error",
    ]
    payload = {k: result.get(k) for k in fields}
    return hashlib.sha256(json_compact(payload).encode("utf-8")).hexdigest()

def execute_one_job(job: dict[str, Any], payloads: dict[str, Any]) -> dict[str, Any]:
    # Delayed import: preflight/tests do not import AFINO execution code.
    from afino import afino_series
    from afino.afino_main_analysis3 import main_analysis

    time_seconds, flux, _ = extract_payload(job, payloads)
    started = time.perf_counter()
    base: dict[str, Any] = {
        "job_id": job["job_id"],
        "job_order": job["job_order"],
        "planned_decision_id": job["planned_decision_id"],
        "decision_class": job["decision_class"],
        "simulation_unit_id": job["simulation_unit_id"],
        "background_realization_id": job["background_realization_id"],
        "external_optimizer_seed": job["external_optimizer_seed"],
        "model_id": job["model_id"],
        "model_name": job["model_name"],
        "payload_logical_sha256": job["payload_logical_sha256"],
        "status": "NOT_RUN",
        "bic": None,
        "log_likelihood": None,
        "parameters_json": None,
        "formal_m1_period_s": None,
        "rchi2": None,
        "probability": None,
        "warning_count": None,
        "warning_types_json": None,
        "warnings_json": None,
        "parameter_at_bound": None,
        "bound_parameters_json": None,
        "convergence_status": "NOT_AUDITABLE",
        "afino_effective_dt_s": None,
        "positive_frequency_bin_count": None,
        "post_cutoff_bin_count": None,
        "minimum_frequency_hz": None,
        "maximum_frequency_hz": None,
        "runtime_seconds": None,
        "afino_version": EXPECTED_AFINO_VERSION,
        "afino_commit": EXPECTED_AFINO_COMMIT,
        "result_core_sha256": None,
        "error": None,
        "completed_at_utc": None,
    }

    try:
        series = afino_series.AfinoSeries(time_seconds, flux)
        prepared = afino_series.prep_series(series)
        effective_dt = finite_float(prepared.SampleTimes.dt, "afino_effective_dt_s")
        positive_frequencies = np.asarray(prepared.PowerSpectrum.frequencies.positive, dtype=float)

        np.random.seed(job["external_optimizer_seed"])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            if job["model_id"] == "M1":
                result = main_analysis(
                    prepared,
                    model=job["model_name"],
                    low_frequency_cutoff=LOW_FREQUENCY_CUTOFF_HZ,
                    overwrite_gauss_bounds=OVERWRITE_GAUSS_BOUNDS,
                )
            else:
                result = main_analysis(
                    prepared,
                    model=job["model_name"],
                    low_frequency_cutoff=LOW_FREQUENCY_CUTOFF_HZ,
                )

        parameters = np.asarray(result["params"], dtype=float)
        frequencies = np.asarray(result["frequencies"], dtype=float)
        if not np.all(np.isfinite(parameters)):
            raise ValueError("AFINO parameters contain non-finite values.")
        if frequencies.size == 0 or not np.all(np.isfinite(frequencies)):
            raise ValueError("No finite frequencies remain after cutoff.")

        formal_period = None
        if job["model_id"] == "M1":
            if parameters.size <= 4:
                raise ValueError("M1 did not return params[4].")
            formal_period = finite_float(1.0 / np.exp(parameters[4]), "formal_m1_period_s")

        at_bound, bound_hits = inspect_bounds(job["model_name"], parameters)
        warning_count, warning_types_json, warnings_json = warning_payload(list(caught))
        base.update({
            "status": "OK",
            "bic": finite_float(result["BIC"], "BIC"),
            "log_likelihood": finite_float(result["lnlike"], "lnlike"),
            "parameters_json": json_compact(parameters.tolist()),
            "formal_m1_period_s": formal_period,
            "rchi2": finite_float(result["rchi2"], "rchi2"),
            "probability": finite_float(result["probability"], "probability"),
            "warning_count": warning_count,
            "warning_types_json": warning_types_json,
            "warnings_json": warnings_json,
            "parameter_at_bound": int(at_bound),
            "bound_parameters_json": json_compact(bound_hits),
            "afino_effective_dt_s": effective_dt,
            "positive_frequency_bin_count": int(positive_frequencies.size),
            "post_cutoff_bin_count": int(frequencies.size),
            "minimum_frequency_hz": float(np.min(frequencies)),
            "maximum_frequency_hz": float(np.max(frequencies)),
        })
    except Exception:
        base["status"] = "ERROR"
        base["error"] = traceback.format_exc()
    finally:
        base["runtime_seconds"] = time.perf_counter() - started
        base["completed_at_utc"] = utc_now()
        base["result_core_sha256"] = result_core_sha256(base)
    return base

def connect_checkpoint(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(path)
        con.execute("PRAGMA journal_mode=DELETE")
        con.execute("PRAGMA synchronous=FULL")
        con.execute("PRAGMA foreign_keys=ON")
    con.row_factory = sqlite3.Row
    return con

def initialize_checkpoint(
    checkpoint: Path,
    *,
    plan_sha256: str,
    manifest_sha256: str,
    runner_sha256: str,
    environment: dict[str, Any],
    plan_kind: str,
) -> None:
    con = connect_checkpoint(checkpoint)
    try:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS results (
            job_id TEXT PRIMARY KEY,
            job_order INTEGER NOT NULL,
            planned_decision_id TEXT NOT NULL,
            decision_class TEXT NOT NULL,
            simulation_unit_id TEXT NOT NULL,
            background_realization_id TEXT NOT NULL,
            external_optimizer_seed INTEGER NOT NULL,
            model_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            payload_logical_sha256 TEXT NOT NULL,
            status TEXT NOT NULL,
            bic REAL,
            log_likelihood REAL,
            parameters_json TEXT,
            formal_m1_period_s REAL,
            rchi2 REAL,
            probability REAL,
            warning_count INTEGER,
            warning_types_json TEXT,
            warnings_json TEXT,
            parameter_at_bound INTEGER,
            bound_parameters_json TEXT,
            convergence_status TEXT NOT NULL,
            afino_effective_dt_s REAL,
            positive_frequency_bin_count INTEGER,
            post_cutoff_bin_count INTEGER,
            minimum_frequency_hz REAL,
            maximum_frequency_hz REAL,
            runtime_seconds REAL NOT NULL,
            afino_version TEXT NOT NULL,
            afino_commit TEXT NOT NULL,
            result_core_sha256 TEXT NOT NULL,
            error TEXT,
            completed_at_utc TEXT NOT NULL,
            UNIQUE(simulation_unit_id, external_optimizer_seed, model_id)
        );
        CREATE TABLE IF NOT EXISTS invocations (
            invocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at_utc TEXT NOT NULL,
            finished_at_utc TEXT NOT NULL,
            manifest_sha256 TEXT NOT NULL,
            plan_kind TEXT NOT NULL,
            resume_requested INTEGER NOT NULL,
            max_new_jobs INTEGER NOT NULL,
            existing_before INTEGER NOT NULL,
            new_jobs INTEGER NOT NULL,
            skipped_existing INTEGER NOT NULL,
            total_after INTEGER NOT NULL,
            pending_after INTEGER NOT NULL
        );
        """)
        metadata = {
            "schema_version": "1.0.0",
            "runner_family": RUNNER_FAMILY,
            "runner_implementation_version": RUNNER_IMPLEMENTATION_VERSION,
            "f3b2_commit": F3B2_COMMIT,
            "f3b2_tag": F3B2_TAG,
            "blinded_plan_sha256": plan_sha256,
            "payload_manifest_sha256": EXPECTED_PAYLOAD_MANIFEST_SHA256,
            "execution_environment_binding_sha256": EXPECTED_ENV_BINDING_SHA256,
            "manifest_sha256": manifest_sha256,
            "runner_sha256": runner_sha256,
            "afino_version": EXPECTED_AFINO_VERSION,
            "afino_commit": EXPECTED_AFINO_COMMIT,
            "execution_environment": json_compact(environment),
            "split": "DEVELOPMENT",
            "plan_kind": plan_kind,
        }
        existing = {row["key"]: row["value"] for row in con.execute("SELECT key,value FROM metadata")}
        if existing:
            for key, value in metadata.items():
                if existing.get(key) != value:
                    raise RuntimeError(f"Checkpoint metadata mismatch: {key}")
        else:
            con.executemany("INSERT INTO metadata(key,value) VALUES (?,?)", list(metadata.items()))
        con.commit()
    finally:
        con.close()

def result_ids(checkpoint: Path) -> set[str]:
    con = connect_checkpoint(checkpoint, readonly=True)
    try:
        return {row["job_id"] for row in con.execute("SELECT job_id FROM results")}
    finally:
        con.close()

def validate_existing_checkpoint_rows(checkpoint: Path, jobs: list[dict[str, Any]]) -> None:
    if not checkpoint.exists():
        return
    expected = {j["job_id"]: j for j in jobs}
    for row in fetch_results(checkpoint):
        job = expected.get(row["job_id"])
        if job is None:
            raise RuntimeError(f"Checkpoint contains unknown job_id: {row['job_id']}")
        for field in [
            "planned_decision_id", "decision_class", "simulation_unit_id",
            "background_realization_id", "external_optimizer_seed", "model_id",
            "model_name", "payload_logical_sha256",
        ]:
            if str(row[field]) != str(job[field]):
                raise RuntimeError(f"Checkpoint scientific identity mismatch {row['job_id']} {field}")
        if result_core_sha256(row) != row["result_core_sha256"]:
            raise RuntimeError(f"Checkpoint result core mismatch: {row['job_id']}")

def result_count(checkpoint: Path) -> int:
    con = connect_checkpoint(checkpoint, readonly=True)
    try:
        return int(con.execute("SELECT COUNT(*) FROM results").fetchone()[0])
    finally:
        con.close()

def insert_result_transaction(checkpoint: Path, result: dict[str, Any]) -> None:
    con = connect_checkpoint(checkpoint)
    try:
        cols = ",".join(RESULT_COLUMNS)
        placeholders = ",".join("?" for _ in RESULT_COLUMNS)
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            f"INSERT INTO results ({cols}) VALUES ({placeholders})",
            [result[c] for c in RESULT_COLUMNS],
        )
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def record_invocation(
    checkpoint: Path, *, started: str, manifest_sha: str, plan_kind: str,
    resume: bool, max_new_jobs: int, existing_before: int, new_jobs: int,
    skipped_existing: int, total_after: int, pending_after: int,
) -> None:
    con = connect_checkpoint(checkpoint)
    try:
        con.execute(
            """INSERT INTO invocations(
                started_at_utc,finished_at_utc,manifest_sha256,plan_kind,resume_requested,
                max_new_jobs,existing_before,new_jobs,skipped_existing,total_after,pending_after
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (started, utc_now(), manifest_sha, plan_kind, int(resume), max_new_jobs,
             existing_before, new_jobs, skipped_existing, total_after, pending_after)
        )
        con.commit()
    finally:
        con.close()

def fetch_results(checkpoint: Path) -> list[dict[str, Any]]:
    con = connect_checkpoint(checkpoint, readonly=True)
    try:
        rows = con.execute("SELECT * FROM results ORDER BY job_order").fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()

def checkpoint_metadata(checkpoint: Path) -> dict[str, str]:
    con = connect_checkpoint(checkpoint, readonly=True)
    try:
        return {row["key"]: row["value"] for row in con.execute("SELECT key,value FROM metadata")}
    finally:
        con.close()

def bootstrap_canary_results(
    *,
    source_checkpoint: Path,
    destination_checkpoint: Path,
    canary_jobs: list[dict[str, Any]],
    full_jobs: list[dict[str, Any]],
    full_manifest_sha: str,
    runner_sha: str,
    environment: dict[str, Any],
    authorization_path: Path,
) -> dict[str, int]:
    """Import the complete canary checkpoint into a fresh full DEVELOPMENT checkpoint without AFINO calls."""
    validate_full_authorization(authorization_path)
    if destination_checkpoint.exists():
        raise RuntimeError("Full checkpoint already exists; bootstrap refuses overwrite.")
    if not source_checkpoint.is_file():
        raise RuntimeError("Canary checkpoint missing.")
    meta = checkpoint_metadata(source_checkpoint)
    if meta.get("plan_kind") != "canary":
        raise RuntimeError("Bootstrap source is not a canary checkpoint.")
    if meta.get("blinded_plan_sha256") != EXPECTED_BLINDED_PLAN_SHA256:
        raise RuntimeError("Canary checkpoint blinded-plan hash mismatch.")
    if meta.get("runner_sha256") != runner_sha:
        raise RuntimeError("Canary checkpoint runner hash mismatch.")

    source_rows = fetch_results(source_checkpoint)
    if len(source_rows) != EXPECTED_CANARY_JOBS:
        raise RuntimeError(f"Canary bootstrap requires {EXPECTED_CANARY_JOBS} rows.")
    canary_by_id = {j["job_id"]: j for j in canary_jobs}
    full_by_id = {j["job_id"]: j for j in full_jobs}
    if len(canary_by_id) != EXPECTED_CANARY_JOBS or len(full_by_id) != EXPECTED_FULL_JOBS:
        raise RuntimeError("Bootstrap job-universe count mismatch.")
    if set(canary_by_id) - set(full_by_id):
        raise RuntimeError("Canary contains jobs outside frozen full plan.")
    if {r["job_id"] for r in source_rows} != set(canary_by_id):
        raise RuntimeError("Canary checkpoint job identity mismatch.")

    identity_fields = [
        "planned_decision_id", "decision_class", "simulation_unit_id",
        "background_realization_id", "external_optimizer_seed", "model_id",
        "model_name", "payload_logical_sha256",
    ]
    for row in source_rows:
        job = full_by_id[row["job_id"]]
        for field in identity_fields:
            if str(row[field]) != str(job[field]):
                raise RuntimeError(f"Canary bootstrap identity mismatch {row['job_id']} {field}")
        if result_core_sha256(row) != row["result_core_sha256"]:
            raise RuntimeError(f"Canary result_core_sha256 mismatch: {row['job_id']}")

    initialize_checkpoint(
        destination_checkpoint,
        plan_sha256=EXPECTED_BLINDED_PLAN_SHA256,
        manifest_sha256=full_manifest_sha,
        runner_sha256=runner_sha,
        environment=environment,
        plan_kind="full",
    )
    for row in source_rows:
        insert_result_transaction(destination_checkpoint, row)

    copied = fetch_results(destination_checkpoint)
    copied_by_id = {r["job_id"]: r for r in copied}
    core_mismatches = sum(copied_by_id[r["job_id"]]["result_core_sha256"] != r["result_core_sha256"] for r in source_rows)
    payload_mismatches = sum(copied_by_id[r["job_id"]]["payload_logical_sha256"] != r["payload_logical_sha256"] for r in source_rows)
    if len(copied) != EXPECTED_CANARY_JOBS or core_mismatches or payload_mismatches:
        raise RuntimeError("Canary bootstrap preservation failure.")
    return {
        "imported_rows": len(copied),
        "result_core_mismatches": core_mismatches,
        "payload_mismatches": payload_mismatches,
        "remaining_new_jobs": EXPECTED_FULL_JOBS - len(copied),
    }

def export_results(checkpoint: Path, path: Path) -> int:
    rows = fetch_results(checkpoint)
    write_csv(path, rows, RESULT_COLUMNS)
    return len(rows)

def selection_rule(bic_m0: float, bic_m1: float, bic_m2: float) -> bool:
    return (float(bic_m0) - float(bic_m1) > 10.0) and (float(bic_m2) - float(bic_m1) > 10.0)

def assemble_complete_decisions(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    meta: dict[tuple[str, int], dict[str, Any]] = {}
    for row in results:
        key = (str(row["simulation_unit_id"]), int(row["external_optimizer_seed"]))
        groups.setdefault(key, {})[str(row["model_id"])] = row
        meta.setdefault(key, row)
    out = []
    for key in sorted(groups):
        models = groups[key]
        if set(models) != {"M0","M1","M2"}:
            continue
        if any(models[m]["status"] != "OK" for m in ("M0","M1","M2")):
            status = "INVALID_MODEL_STATUS"
            selected = ""
        else:
            status = "VALID"
            selected = int(selection_rule(models["M0"]["bic"], models["M1"]["bic"], models["M2"]["bic"]))
        out.append({
            "simulation_unit_id": key[0],
            "external_optimizer_seed": key[1],
            "decision_status": status,
            "qpp_selected": selected,
        })
    return out

def _fake_result_for_test(job: dict[str, Any]) -> dict[str, Any]:
    # Only for unit tests through injected executor.
    now = utc_now()
    base = {
        "job_id": job["job_id"], "job_order": job["job_order"],
        "planned_decision_id": job["planned_decision_id"], "decision_class": job["decision_class"],
        "simulation_unit_id": job["simulation_unit_id"], "background_realization_id": job["background_realization_id"],
        "external_optimizer_seed": job["external_optimizer_seed"], "model_id": job["model_id"],
        "model_name": job["model_name"], "payload_logical_sha256": job["payload_logical_sha256"],
        "status": "OK", "bic": float(job["job_order"]), "log_likelihood": -1.0,
        "parameters_json": "[]", "formal_m1_period_s": None, "rchi2": 1.0,
        "probability": 0.5, "warning_count": 0, "warning_types_json": "[]", "warnings_json": "[]",
        "parameter_at_bound": 0, "bound_parameters_json": "[]", "convergence_status": "NOT_AUDITABLE",
        "afino_effective_dt_s": 20.0, "positive_frequency_bin_count": 7,
        "post_cutoff_bin_count": 6, "minimum_frequency_hz": 0.03, "maximum_frequency_hz": 0.2,
        "runtime_seconds": 0.0, "afino_version": EXPECTED_AFINO_VERSION,
        "afino_commit": EXPECTED_AFINO_COMMIT, "result_core_sha256": None,
        "error": None, "completed_at_utc": now,
    }
    base["result_core_sha256"] = result_core_sha256(base)
    return base

def run_jobs(
    *,
    checkpoint: Path,
    jobs: list[dict[str, Any]],
    payloads: dict[str, Any] | None,
    max_new_jobs: int,
    resume: bool,
    manifest_sha: str,
    plan_kind: str,
    runner_sha: str,
    environment: dict[str, Any],
    executor: Callable[[dict[str, Any], dict[str, Any] | None], dict[str, Any]] | None = None,
) -> dict[str, int]:
    if max_new_jobs < 0:
        raise ValueError("--max-new-jobs must be >= 0")
    if checkpoint.exists() and not resume:
        raise RuntimeError("Checkpoint exists; use --resume.")
    if resume and not checkpoint.exists():
        raise RuntimeError("--resume requested but checkpoint does not exist.")

    initialize_checkpoint(
        checkpoint,
        plan_sha256=EXPECTED_BLINDED_PLAN_SHA256,
        manifest_sha256=manifest_sha,
        runner_sha256=runner_sha,
        environment=environment,
        plan_kind=plan_kind,
    )
    validate_existing_checkpoint_rows(checkpoint, jobs)
    existing = result_ids(checkpoint)
    existing_before = len(existing)
    missing = [j for j in jobs if j["job_id"] not in existing]
    to_run = missing[:max_new_jobs]
    skipped_existing = len(jobs) - len(missing)
    execute = executor or execute_one_job
    started = utc_now()
    new_jobs = 0
    for job in to_run:
        result = execute(job, payloads)
        insert_result_transaction(checkpoint, result)
        existing.add(job["job_id"])
        new_jobs += 1
        print(
            f"[{len(existing)}/{len(jobs)}] {job['job_id']} "
            f"{job['simulation_unit_id']} seed={job['external_optimizer_seed']} "
            f"{job['model_id']} {result['status']} ({result['runtime_seconds']:.3f}s)",
            flush=True,
        )
        if result["status"] != "OK" and executor is None:
            raise RuntimeError(
                "PHASE3B_DEVELOPMENT_EXECUTION_BLOCKED: numerical job status != OK"
            )

    total_after = result_count(checkpoint)
    pending_after = len(jobs) - total_after
    record_invocation(
        checkpoint, started=started, manifest_sha=manifest_sha, plan_kind=plan_kind,
        resume=resume, max_new_jobs=max_new_jobs, existing_before=existing_before,
        new_jobs=new_jobs, skipped_existing=skipped_existing,
        total_after=total_after, pending_after=pending_after,
    )
    summary = {
        "existing_before": existing_before,
        "new_jobs": new_jobs,
        "total_after": total_after,
        "pending_after": pending_after,
    }
    print("CHECKPOINT_INVOCATION_SUMMARY=" + json.dumps(summary, sort_keys=True))
    return summary

def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else (repo / path).resolve()

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="F3B.3 checkpointed AFINO runner on frozen DEVELOPMENT.")
    p.add_argument("--repo-root", default=".")
    p.add_argument("--afino-repo", type=Path, required=True)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--job-manifest", type=Path, required=True)
    p.add_argument("--max-new-jobs", type=int, required=True)
    p.add_argument("--authorization", type=Path)
    p.add_argument("--export-results", type=Path)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--preflight-only", action="store_true")
    return p

def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = Path(args.repo_root).resolve()
    afino_repo = args.afino_repo.resolve()
    checkpoint = resolve(repo, args.checkpoint)
    manifest = resolve(repo, args.job_manifest)
    authorization = resolve(repo, args.authorization) if args.authorization else None
    export_path = resolve(repo, args.export_results) if args.export_results else None

    if args.preflight_only:
        if args.resume or args.max_new_jobs != 0 or export_path is not None:
            raise RuntimeError("--preflight-only requires max-new-jobs=0, no resume/export.")

    print("F3B.3 — CHECKPOINTED AFINO DEVELOPMENT RUNNER", flush=True)
    binding = verify_project_freeze(repo)
    environment = verify_environment(afino_repo, binding)
    payloads = load_payload_dataset(repo)
    jobs, plan_kind, manifest_sha = load_plan(repo, manifest, authorization_path=authorization)

    print(f"Runner SHA-256: {sha256_file(Path(__file__).resolve())}")
    print(f"Manifest SHA-256: {manifest_sha}")
    print(f"Plan kind: {plan_kind}")
    print(f"Jobs selected: {len(jobs)}")
    print(f"AFINO: {environment['afino_package_version']} / {environment['afino_commit']}")
    print(f"Python: {environment['python_version']}")
    print(f"NumPy: {environment['numpy_version']}")
    print(f"SciPy: {environment['scipy_version']}")
    print("Generator imported: false")
    print("Synthetic arrays regenerated: false")
    print("Truth used as inference feature: false")
    print("HELDOUT generated: false")
    print("HELDOUT accessed: false")

    if args.preflight_only:
        if plan_kind != "canary":
            raise RuntimeError("Preflight before canary accepts only frozen canary manifest.")
        print("PHASE3B_F3B3_RUNNER_PREFLIGHT_PASS — NO AFINO CALLS")
        return 0

    summary = run_jobs(
        checkpoint=checkpoint,
        jobs=jobs,
        payloads=payloads,
        max_new_jobs=args.max_new_jobs,
        resume=args.resume,
        manifest_sha=manifest_sha,
        plan_kind=plan_kind,
        runner_sha=sha256_file(Path(__file__).resolve()),
        environment=environment,
    )

    if export_path is not None:
        n = export_results(checkpoint, export_path)
        print(f"exported_result_rows={n}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
