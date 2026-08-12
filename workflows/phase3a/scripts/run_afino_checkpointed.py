#!/usr/bin/env python3
"""
F3A.3 — checkpointed AFINO runner for the prospectively frozen catalogue canary.

The scientific execution core is inherited from the frozen F2 runner:
AfinoSeries -> prep_series -> per-model np.random.seed -> main_analysis.

F3A.3 safety boundary:
- the canary manifest is REQUIRED;
- the full 22,398-job plan is rejected unless --authorize-full-plan is explicit;
- F3A.3 must NOT use --authorize-full-plan;
- no FITS access, QUALITY filtering, detrending, variant regeneration,
  interpolation, gap filling, or candidate discovery occurs here.
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
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import scipy


RUNNER_FAMILY = "phase3a_checkpointed_canary"
RUNNER_IMPLEMENTATION_VERSION = "1.0.0"

F3A2_COMMIT = "6bf9beca8fa8016495693575f8c86a2dec5fecb1"
F3A2_TAG = "phase3a-execution-plan-v1"
F3A3_CANARY_PLAN_COMMIT = "b66764db49f7b823f6d7e3e21ce0da66476479bd"

EXPECTED_AFINO_COMMIT = "6aceac9518fc8056052807e666da9d0c8bebb010"
EXPECTED_AFINO_VERSION = "0.5"
EXPECTED_PYTHON_VERSION = "3.13.13"
EXPECTED_NUMPY_VERSION = "2.5.1"
EXPECTED_SCIPY_VERSION = "1.18.0"

EXPECTED_FULL_PLAN_SHA256 = (
    "d190a4f5e70339b05fd42b2d0cda9c51dd180c10e885c27fdfa43323c8dc1c6f"
)
EXPECTED_PAYLOAD_MANIFEST_SHA256 = (
    "fa5bdfa20eaf499e5354caf159221577633de92f43ec31f48be31e16cd84c148"
)
EXPECTED_CANARY_JOB_MANIFEST_SHA256 = (
    "e82647dc74513b5b4dccbc47f2fda4f5a687465b5ec123fcc7746f814292ce0a"
)
EXPECTED_CANARY_DECISION_MANIFEST_SHA256 = (
    "4ff4df46067e8ae7d57fd85ff2b6614a0d482f2496c163f5d08748eb40ad2a03"
)
EXPECTED_F3A2_CHECKSUM_REGISTRY_SHA256 = (
    "52d9cd40890a4d1e0e74ec8b5b2062840eceb968aecd4d3c4a8eea8255e5c08f"
)

PAYLOAD_PHYSICAL_HASHES = {
    "time_seconds.npy":
        "8302d2d9527ee358bfe3b809d1d91f88022f47411d08f6cdf2fc2a0e0c2113fa",
    "flux.npy":
        "aae865acd94446072e89175057ce2c6d49bb3fe294b14ae8c0a095eb42d280fa",
    "native_index.npy":
        "abe2c5b23bfcade8000c992b64067ee933c514a577deca8a870ea13ba562e52a",
    "offsets.npy":
        "72d87c7ca15ce446bdefa79651e70836cfd77826630f9c870119c80f80956a68",
}

MODEL_SPECS = {
    "M0": "pow_const",
    "M1": "pow_const_gauss",
    "M2": "bpow_const",
}
LOW_FREQUENCY_CUTOFF_HZ = 0.025
ABS_TOLERANCE = 5.0e-12
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

FULL_PLAN_REL = Path(
    "workflows/phase3a/evidence/tables/f3a2_exact_afino_plan.csv"
)
PAYLOAD_MANIFEST_REL = Path(
    "workflows/phase3a/evidence/tables/f3a2_payload_manifest.csv"
)
CANARY_DECISION_REL = Path(
    "workflows/phase3a/evidence/tables/f3a3_canary_decision_manifest.csv"
)
PAYLOAD_DIR_REL = Path("data/interim/phase3a/f3a2_payloads")
F3A2_CHECKSUM_REL = Path("workflows/phase3a/evidence/f3a2_SHA256SUMS.txt")

EXPECTED_FULL_JOBS = 22398
EXPECTED_FULL_DECISIONS = 7466
EXPECTED_CANARY_JOBS = 102
EXPECTED_CANARY_DECISIONS = 34

RESULT_COLUMNS = [
    "job_id",
    "job_order",
    "planned_decision_id",
    "decision_class",
    "phase3a_event_id",
    "variant_id",
    "matrix_cell_id",
    "window_variant_id",
    "processing_profile_id",
    "external_optimizer_seed",
    "model_id",
    "model_name",
    "payload_id",
    "payload_logical_sha256",
    "payload_offset",
    "payload_length",
    "input_time_sha256",
    "input_flux_sha256",
    "input_native_index_sha256",
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

RESULT_EXPORT_FIELDS = RESULT_COLUMNS.copy()


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
    time_seconds: np.ndarray,
    flux: np.ndarray,
    native_index: np.ndarray,
) -> str:
    h = hashlib.sha256()
    h.update(b"F3A2_LOGICAL_PAYLOAD_V1\0")
    h.update(canonical_array(time_seconds, "<f8").tobytes(order="C"))
    h.update(b"\0")
    h.update(canonical_array(flux, "<f8").tobytes(order="C"))
    h.update(b"\0")
    h.update(canonical_array(native_index, "<i8").tobytes(order="C"))
    return h.hexdigest()


def json_compact(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fields: Sequence[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=list(fields),
            extrasaction="raise",
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


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


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run_command(["git", "-C", str(repo), *args], check=check)


def finite_float(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise ValueError(f"{name} is not finite: {x!r}")
    return x


def allowed_afino_untracked(status: str) -> tuple[bool, list[str]]:
    lines = [x.strip() for x in status.splitlines() if x.strip()]
    unexpected = [
        line
        for line in lines
        if not (
            line.startswith("?? afino.egg-info/")
            or line == "?? afino.egg-info"
        )
    ]
    return not unexpected, unexpected


def verify_environment(afino_repo: Path) -> dict[str, Any]:
    if not afino_repo.is_dir():
        raise RuntimeError(f"AFINO repository does not exist: {afino_repo}")

    expected_python = (
        afino_repo.parent / ".venv" / "Scripts" / "python.exe"
        if os.name == "nt"
        else afino_repo.parent / ".venv" / "bin" / "python"
    ).resolve()
    observed_python = Path(sys.executable).resolve()
    if observed_python != expected_python:
        raise RuntimeError(
            "F3A.3 must use the frozen AFINO virtual environment.\n"
            f"observed={observed_python}\nexpected={expected_python}"
        )

    commit = git(afino_repo, "rev-parse", "HEAD").stdout.strip()
    if commit != EXPECTED_AFINO_COMMIT:
        raise RuntimeError(
            f"AFINO commit mismatch: {commit} != {EXPECTED_AFINO_COMMIT}"
        )

    tracked = git(afino_repo, "diff", "--quiet", check=False).returncode
    staged = git(afino_repo, "diff", "--cached", "--quiet", check=False).returncode
    if tracked != 0 or staged != 0:
        raise RuntimeError(
            f"AFINO tracked/staged diff is nonzero: tracked={tracked}, staged={staged}"
        )

    status = git(afino_repo, "status", "--porcelain").stdout.strip()
    untracked_ok, unexpected = allowed_afino_untracked(status)
    if not untracked_ok:
        raise RuntimeError(
            f"Unexpected AFINO working-tree content: {unexpected}"
        )

    try:
        afino_version = importlib.metadata.version("afino")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError("afino package is not installed in the frozen .venv") from exc

    checks = {
        "afino_version": (afino_version, EXPECTED_AFINO_VERSION),
        "python_version": (platform.python_version(), EXPECTED_PYTHON_VERSION),
        "numpy_version": (np.__version__, EXPECTED_NUMPY_VERSION),
        "scipy_version": (scipy.__version__, EXPECTED_SCIPY_VERSION),
    }
    for name, (observed, expected) in checks.items():
        if observed != expected:
            raise RuntimeError(f"{name} mismatch: {observed} != {expected}")

    return {
        "python_version": platform.python_version(),
        "python_full": sys.version,
        "python_executable": str(observed_python),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "afino_version": afino_version,
        "afino_commit": commit,
        "afino_repo": str(afino_repo.resolve()),
        "afino_tracked_diff_exit_code": tracked,
        "afino_staged_diff_exit_code": staged,
        "afino_git_status_porcelain": status,
        "afino_untracked_only_egg_info": True,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }


def verify_project_freeze(repo: Path) -> None:
    f3a2 = git(repo, "rev-parse", f"{F3A2_TAG}^{{}}").stdout.strip()
    if f3a2 != F3A2_COMMIT:
        raise RuntimeError(f"{F3A2_TAG} moved: {f3a2} != {F3A2_COMMIT}")

    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    if head != F3A3_CANARY_PLAN_COMMIT:
        raise RuntimeError(
            "F3A.3 execution must start from the frozen canary-plan commit.\n"
            f"HEAD={head}\nexpected={F3A3_CANARY_PLAN_COMMIT}"
        )

    expected_hashes = {
        FULL_PLAN_REL: EXPECTED_FULL_PLAN_SHA256,
        PAYLOAD_MANIFEST_REL: EXPECTED_PAYLOAD_MANIFEST_SHA256,
        CANARY_DECISION_REL: EXPECTED_CANARY_DECISION_MANIFEST_SHA256,
        F3A2_CHECKSUM_REL: EXPECTED_F3A2_CHECKSUM_REGISTRY_SHA256,
    }
    for rel, expected in expected_hashes.items():
        p = repo / rel
        if not p.is_file():
            raise RuntimeError(f"Missing frozen input: {rel}")
        actual = sha256_file(p)
        if actual != expected:
            raise RuntimeError(
                f"Frozen input hash mismatch: {rel}\n"
                f"expected={expected}\nactual={actual}"
            )

    protected = [
        "foundation/f0-f2",
        "docs/literature/bibliographic_audit_ii",
        "workflows/phase3a/design",
        "workflows/phase3a/config/f3a2_primary_catalogue_binding.json",
        "workflows/phase3a/config/f3a2_tess_product_binding_policy.json",
        "workflows/phase3a/evidence/f3a2_SHA256SUMS.txt",
        "workflows/phase3a/evidence/tables/f3a2_cohort_manifest.csv",
        "workflows/phase3a/evidence/tables/f3a2_payload_manifest.csv",
        "workflows/phase3a/evidence/tables/f3a2_resolved_decision_grid.csv",
        "workflows/phase3a/evidence/tables/f3a2_exact_afino_plan.csv",
        "data/interim/phase3a/f3a2_payloads",
    ]
    cp = git(
        repo,
        "diff",
        "--quiet",
        F3A2_TAG,
        "--",
        *protected,
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError("One or more F3A.2/protected inputs differ from the freeze.")


def load_payload_dataset(repo: Path) -> dict[str, Any]:
    payload_dir = repo / PAYLOAD_DIR_REL
    for name, expected in PAYLOAD_PHYSICAL_HASHES.items():
        p = payload_dir / name
        if not p.is_file():
            raise RuntimeError(f"Missing frozen payload array: {p}")
        actual = sha256_file(p)
        if actual != expected:
            raise RuntimeError(
                f"Payload physical hash mismatch {name}: {actual} != {expected}"
            )

    manifest_path = repo / PAYLOAD_MANIFEST_REL
    rows = read_csv(manifest_path)
    if len(rows) != 6422:
        raise RuntimeError(f"Expected 6422 payload rows, got {len(rows)}")

    time_values = np.load(
        payload_dir / "time_seconds.npy", mmap_mode="r", allow_pickle=False
    )
    flux_values = np.load(
        payload_dir / "flux.npy", mmap_mode="r", allow_pickle=False
    )
    native_values = np.load(
        payload_dir / "native_index.npy", mmap_mode="r", allow_pickle=False
    )
    offsets = np.load(
        payload_dir / "offsets.npy", mmap_mode="r", allow_pickle=False
    )

    if (
        time_values.dtype != np.dtype("<f8")
        or flux_values.dtype != np.dtype("<f8")
        or native_values.dtype != np.dtype("<i8")
        or offsets.dtype != np.dtype("<i8")
    ):
        raise RuntimeError("Frozen payload dtype mismatch.")
    if len(offsets) != 6423:
        raise RuntimeError("Frozen offsets length is not 6423.")
    if not (
        len(time_values)
        == len(flux_values)
        == len(native_values)
        == int(offsets[-1])
    ):
        raise RuntimeError("Frozen concatenated payload array lengths disagree.")

    by_payload: dict[str, dict[str, Any]] = {}
    for order, raw in enumerate(rows):
        row = dict(raw)
        row["offset"] = int(raw["offset"])
        row["length"] = int(raw["length"])
        start = row["offset"]
        end = start + row["length"]
        if int(offsets[order]) != start or int(offsets[order + 1]) != end:
            raise RuntimeError(f"Offset mismatch for {row['payload_id']}")
        if row["n_samples"] != str(row["length"]):
            raise RuntimeError(f"n_samples mismatch for {row['payload_id']}")
        by_payload[row["payload_id"]] = row

    if len(by_payload) != 6422:
        raise RuntimeError("Duplicate payload_id in frozen manifest.")

    return {
        "time": time_values,
        "flux": flux_values,
        "native": native_values,
        "offsets": offsets,
        "by_payload": by_payload,
    }


def validate_canary_row(
    raw: dict[str, str],
    full_by_job: dict[str, dict[str, str]],
    payloads: dict[str, Any],
) -> dict[str, Any]:
    full = full_by_job.get(raw["job_id"])
    if full is None:
        raise RuntimeError(f"Unknown canary job: {raw['job_id']}")

    for field in full.keys():
        if raw.get(field) != full[field]:
            raise RuntimeError(
                f"Canary/full-plan mismatch {raw['job_id']} field={field}"
            )

    if raw["model_id"] not in MODEL_SPECS:
        raise RuntimeError(f"Unknown model_id: {raw['job_id']}")
    if raw["model_name"] != MODEL_SPECS[raw["model_id"]]:
        raise RuntimeError(f"Model mismatch: {raw['job_id']}")

    seed = int(raw["external_optimizer_seed"])
    if raw["decision_class"] == "PRIMARY" and seed != 0:
        raise RuntimeError(f"PRIMARY seed mismatch: {raw['job_id']}")
    if raw["decision_class"] == "STABILITY" and seed not in range(1, 10):
        raise RuntimeError(f"STABILITY seed mismatch: {raw['job_id']}")
    if raw["decision_class"] not in {"PRIMARY", "STABILITY"}:
        raise RuntimeError(f"Decision class mismatch: {raw['job_id']}")

    if raw["afino_version"] != EXPECTED_AFINO_VERSION:
        raise RuntimeError(f"AFINO version mismatch: {raw['job_id']}")
    if raw["afino_commit"] != EXPECTED_AFINO_COMMIT:
        raise RuntimeError(f"AFINO commit mismatch: {raw['job_id']}")
    if not math.isclose(
        float(raw["low_frequency_cutoff_hz"]),
        LOW_FREQUENCY_CUTOFF_HZ,
        rel_tol=0.0,
        abs_tol=0.0,
    ):
        raise RuntimeError(f"Cutoff mismatch: {raw['job_id']}")
    if raw["execution_status"] != "NOT_EXECUTED":
        raise RuntimeError(f"Canary plan row is not NOT_EXECUTED: {raw['job_id']}")

    payload = payloads["by_payload"].get(raw["payload_id"])
    if payload is None:
        raise RuntimeError(f"Unknown payload_id: {raw['job_id']}")
    if payload["variant_id"] != raw["variant_id"]:
        raise RuntimeError(f"Payload/variant mismatch: {raw['job_id']}")
    if payload["logical_payload_sha256"] != raw["payload_logical_sha256"]:
        raise RuntimeError(f"Payload logical hash mismatch in plan: {raw['job_id']}")

    row: dict[str, Any] = dict(raw)
    row["job_order"] = int(raw["job_order"])
    row["external_optimizer_seed"] = seed
    row["payload_offset"] = int(payload["offset"])
    row["payload_length"] = int(payload["length"])
    row["input_time_sha256"] = payload["time_sha256"]
    row["input_flux_sha256"] = payload["flux_sha256"]
    row["input_native_index_sha256"] = payload["native_index_sha256"]
    return row


def load_plan(
    repo: Path,
    canary_manifest: Path,
    payloads: dict[str, Any],
    *,
    authorize_full_plan: bool,
) -> tuple[list[dict[str, Any]], str, str]:
    full_path = repo / FULL_PLAN_REL
    full_rows = read_csv(full_path)
    if len(full_rows) != EXPECTED_FULL_JOBS:
        raise RuntimeError("Frozen full-plan row count mismatch.")
    if len({r["job_id"] for r in full_rows}) != EXPECTED_FULL_JOBS:
        raise RuntimeError("Duplicate job_id in frozen full plan.")
    if len({
        (r["variant_id"], r["external_optimizer_seed"], r["model_id"])
        for r in full_rows
    }) != EXPECTED_FULL_JOBS:
        raise RuntimeError("Duplicate scientific key in frozen full plan.")

    full_by_job = {r["job_id"]: r for r in full_rows}
    manifest_sha = sha256_file(canary_manifest)

    if manifest_sha == EXPECTED_FULL_PLAN_SHA256:
        if not authorize_full_plan:
            raise RuntimeError(
                "FULL_PLAN_EXECUTION_REQUIRES_EXPLICIT_AUTHORIZATION"
            )
        rows = [
            validate_canary_row(r, full_by_job, payloads)
            for r in full_rows
        ]
        return rows, "full", manifest_sha

    if authorize_full_plan:
        raise RuntimeError(
            "--authorize-full-plan was supplied but the selected manifest is "
            "not the exact frozen full plan."
        )

    if manifest_sha != EXPECTED_CANARY_JOB_MANIFEST_SHA256:
        raise RuntimeError(
            "The required F3A.3 canary manifest has an unexpected SHA-256.\n"
            f"observed={manifest_sha}\n"
            f"expected={EXPECTED_CANARY_JOB_MANIFEST_SHA256}"
        )

    raw = read_csv(canary_manifest)
    if len(raw) != EXPECTED_CANARY_JOBS:
        raise RuntimeError(f"Expected 102 canary jobs, got {len(raw)}")

    rows = [
        validate_canary_row(r, full_by_job, payloads)
        for r in raw
    ]
    if [r["job_order"] for r in rows] != sorted(r["job_order"] for r in rows):
        raise RuntimeError("Canary is not ordered by original frozen job_order.")
    if len({r["job_id"] for r in rows}) != 102:
        raise RuntimeError("Duplicate canary job_id.")
    if len({
        (r["variant_id"], r["external_optimizer_seed"], r["model_id"])
        for r in rows
    }) != 102:
        raise RuntimeError("Duplicate canary scientific key.")
    if Counter(r["model_id"] for r in rows) != {
        "M0": 34, "M1": 34, "M2": 34
    }:
        raise RuntimeError("Canary M0/M1/M2 counts are not 34/34/34.")
    decisions = {
        (r["planned_decision_id"], r["variant_id"], r["external_optimizer_seed"])
        for r in rows
    }
    if len(decisions) != EXPECTED_CANARY_DECISIONS:
        raise RuntimeError("Canary decision count is not 34.")

    return rows, "canary", manifest_sha


def extract_payload(
    job: dict[str, Any],
    payloads: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    start = int(job["payload_offset"])
    end = start + int(job["payload_length"])
    t = np.asarray(payloads["time"][start:end], dtype=np.float64)
    f = np.asarray(payloads["flux"][start:end], dtype=np.float64)
    idx = np.asarray(payloads["native"][start:end], dtype=np.int64)

    if len(t) != job["payload_length"]:
        raise RuntimeError(f"Payload length mismatch: {job['job_id']}")
    if canonical_hash(t, "<f8") != job["input_time_sha256"]:
        raise RuntimeError(f"Frozen time hash rejection: {job['job_id']}")
    if canonical_hash(f, "<f8") != job["input_flux_sha256"]:
        raise RuntimeError(f"Frozen flux hash rejection: {job['job_id']}")
    if canonical_hash(idx, "<i8") != job["input_native_index_sha256"]:
        raise RuntimeError(f"Frozen native-index hash rejection: {job['job_id']}")
    if logical_payload_hash(t, f, idx) != job["payload_logical_sha256"]:
        raise RuntimeError(f"Frozen logical payload hash rejection: {job['job_id']}")
    if float(t[0]) != 0.0:
        raise RuntimeError(f"Frozen time origin mismatch: {job['job_id']}")
    if not np.all(np.diff(t) > 0.0):
        raise RuntimeError(f"Frozen time not strictly increasing: {job['job_id']}")
    if not np.all(np.diff(idx) == 1):
        raise RuntimeError(f"Frozen native indices not consecutive: {job['job_id']}")
    if not (np.all(np.isfinite(t)) and np.all(np.isfinite(f))):
        raise RuntimeError(f"Frozen payload contains non-finite values: {job['job_id']}")
    return t, f, idx


def inspect_bounds(
    model_name: str,
    parameters: np.ndarray,
) -> tuple[bool, list[dict[str, Any]]]:
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
        if lower is not None and np.isclose(
            value, lower, rtol=0.0, atol=BOUND_ATOL
        ):
            hits.append({
                "parameter_index": i,
                "side": "lower",
                "value": value,
                "bound": float(lower),
            })
        if upper is not None and np.isclose(
            value, upper, rtol=0.0, atol=BOUND_ATOL
        ):
            hits.append({
                "parameter_index": i,
                "side": "upper",
                "value": value,
                "bound": float(upper),
            })
    return bool(hits), hits


def warning_payload(
    caught: list[warnings.WarningMessage],
) -> tuple[int, str, str]:
    entries = [
        {
            "category": item.category.__name__,
            "message": str(item.message),
            "filename": Path(item.filename).name,
            "lineno": int(item.lineno),
        }
        for item in caught
    ]
    types = sorted({
        f"{entry['category']}: {entry['message']}"
        for entry in entries
    })
    return len(entries), json_compact(types), json_compact(entries)


def result_core_sha256(result: dict[str, Any]) -> str:
    fields = [
        "job_id", "planned_decision_id", "variant_id",
        "external_optimizer_seed", "model_id", "status",
        "bic", "log_likelihood", "parameters_json",
        "formal_m1_period_s", "rchi2", "probability",
        "warning_count", "warning_types_json", "warnings_json",
        "parameter_at_bound", "bound_parameters_json",
        "convergence_status", "afino_effective_dt_s",
        "positive_frequency_bin_count", "post_cutoff_bin_count",
        "minimum_frequency_hz", "maximum_frequency_hz",
        "afino_version", "afino_commit", "error",
    ]
    payload = {
        k: result.get(k)
        for k in fields
    }
    return hashlib.sha256(
        json_compact(payload).encode("utf-8")
    ).hexdigest()


def execute_one_job(
    job: dict[str, Any],
    payloads: dict[str, Any],
) -> dict[str, Any]:
    # Delayed import: unit tests and structural preflight do not require AFINO calls.
    from afino import afino_series
    from afino.afino_main_analysis3 import main_analysis

    time_seconds, flux, _ = extract_payload(job, payloads)
    started = time.perf_counter()

    base: dict[str, Any] = {
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
        "model_id": job["model_id"],
        "model_name": job["model_name"],
        "payload_id": job["payload_id"],
        "payload_logical_sha256": job["payload_logical_sha256"],
        "payload_offset": job["payload_offset"],
        "payload_length": job["payload_length"],
        "input_time_sha256": job["input_time_sha256"],
        "input_flux_sha256": job["input_flux_sha256"],
        "input_native_index_sha256": job["input_native_index_sha256"],
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

        effective_dt = finite_float(
            prepared.SampleTimes.dt,
            "afino_effective_dt_s",
        )
        positive_frequencies = np.asarray(
            prepared.PowerSpectrum.frequencies.positive,
            dtype=float,
        )

        # Frozen scientific rule: reset independently immediately before EACH model.
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
            formal_period = finite_float(
                1.0 / np.exp(parameters[4]),
                "formal_m1_period_s",
            )

        parameter_at_bound, bound_hits = inspect_bounds(
            job["model_name"], parameters
        )
        warning_count, warning_types_json, warnings_json = warning_payload(
            list(caught)
        )

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
            "parameter_at_bound": int(parameter_at_bound),
            "bound_parameters_json": json_compact(bound_hits),
            "afino_effective_dt_s": effective_dt,
            "positive_frequency_bin_count": int(positive_frequencies.size),
            "post_cutoff_bin_count": int(frequencies.size),
            "minimum_frequency_hz": float(np.min(frequencies)),
            "maximum_frequency_hz": float(np.max(frequencies)),
        })
    except Exception:
        base.update({
            "status": "ERROR",
            "error": traceback.format_exc(),
        })
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
    canary_manifest_sha256: str,
    runner_sha256: str,
    afino_environment: dict[str, Any],
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
                phase3a_event_id TEXT NOT NULL,
                variant_id TEXT NOT NULL,
                matrix_cell_id TEXT NOT NULL,
                window_variant_id TEXT NOT NULL,
                processing_profile_id TEXT NOT NULL,
                external_optimizer_seed INTEGER NOT NULL,
                model_id TEXT NOT NULL,
                model_name TEXT NOT NULL,
                payload_id TEXT NOT NULL,
                payload_logical_sha256 TEXT NOT NULL,
                payload_offset INTEGER NOT NULL,
                payload_length INTEGER NOT NULL,
                input_time_sha256 TEXT NOT NULL,
                input_flux_sha256 TEXT NOT NULL,
                input_native_index_sha256 TEXT NOT NULL,
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
                UNIQUE(variant_id, external_optimizer_seed, model_id)
            );

            CREATE TABLE IF NOT EXISTS invocations (
                invocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at_utc TEXT NOT NULL,
                finished_at_utc TEXT NOT NULL,
                canary_manifest_sha256 TEXT NOT NULL,
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
            "f3a2_commit": F3A2_COMMIT,
            "f3a2_tag": F3A2_TAG,
            "f3a3_canary_plan_commit": F3A3_CANARY_PLAN_COMMIT,
            "full_plan_sha256": EXPECTED_FULL_PLAN_SHA256,
            "payload_manifest_sha256": EXPECTED_PAYLOAD_MANIFEST_SHA256,
            "canary_manifest_sha256": canary_manifest_sha256,
            "canary_decision_manifest_sha256":
                EXPECTED_CANARY_DECISION_MANIFEST_SHA256,
            "runner_sha256": runner_sha256,
            "afino_version": EXPECTED_AFINO_VERSION,
            "afino_commit": EXPECTED_AFINO_COMMIT,
            "afino_environment": json_compact(afino_environment),
            "plan_kind": plan_kind,
            "payload_physical_hashes": json_compact(PAYLOAD_PHYSICAL_HASHES),
        }

        existing = {
            row["key"]: row["value"]
            for row in con.execute("SELECT key, value FROM metadata")
        }
        if existing:
            for key, value in metadata.items():
                if existing.get(key) != value:
                    raise RuntimeError(
                        f"Checkpoint incompatible metadata[{key}]."
                    )
        else:
            con.executemany(
                "INSERT INTO metadata(key, value) VALUES (?, ?)",
                list(metadata.items()),
            )
        con.commit()
    finally:
        con.close()


def insert_result_transaction(
    checkpoint: Path,
    result: dict[str, Any],
) -> None:
    con = connect_checkpoint(checkpoint)
    try:
        placeholders = ",".join("?" for _ in RESULT_COLUMNS)
        cols = ",".join(RESULT_COLUMNS)
        values = [result[c] for c in RESULT_COLUMNS]
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            f"INSERT INTO results ({cols}) VALUES ({placeholders})",
            values,
        )
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def result_ids(checkpoint: Path) -> set[str]:
    con = connect_checkpoint(checkpoint, readonly=True)
    try:
        return {
            row[0]
            for row in con.execute("SELECT job_id FROM results")
        }
    finally:
        con.close()


def result_count(checkpoint: Path) -> int:
    con = connect_checkpoint(checkpoint, readonly=True)
    try:
        return int(con.execute("SELECT COUNT(*) FROM results").fetchone()[0])
    finally:
        con.close()


def record_invocation(
    checkpoint: Path,
    *,
    started: str,
    manifest_sha: str,
    plan_kind: str,
    resume: bool,
    max_new_jobs: int,
    existing_before: int,
    new_jobs: int,
    skipped_existing: int,
    total_after: int,
    pending_after: int,
) -> None:
    con = connect_checkpoint(checkpoint)
    try:
        con.execute(
            """
            INSERT INTO invocations(
                started_at_utc, finished_at_utc,
                canary_manifest_sha256, plan_kind,
                resume_requested, max_new_jobs,
                existing_before, new_jobs, skipped_existing,
                total_after, pending_after
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                started,
                utc_now(),
                manifest_sha,
                plan_kind,
                int(resume),
                max_new_jobs,
                existing_before,
                new_jobs,
                skipped_existing,
                total_after,
                pending_after,
            ),
        )
        con.commit()
    finally:
        con.close()


def fetch_results(
    checkpoint: Path,
    jobs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    con = connect_checkpoint(checkpoint, readonly=True)
    try:
        by_id = {
            row["job_id"]: dict(row)
            for row in con.execute("SELECT * FROM results")
        }
    finally:
        con.close()
    return [
        by_id[j["job_id"]]
        for j in jobs
        if j["job_id"] in by_id
    ]


def export_results(
    checkpoint: Path,
    jobs: list[dict[str, Any]],
    output: Path,
) -> int:
    rows = fetch_results(checkpoint, jobs)
    write_csv(output, rows, RESULT_EXPORT_FIELDS)
    return len(rows)


def selection_rule(bic_m0: float, bic_m1: float, bic_m2: float) -> bool:
    return bool(
        (bic_m0 - bic_m1 > 10.0)
        and (bic_m2 - bic_m1 > 10.0)
    )


def assemble_complete_decisions(
    result_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[
        tuple[str, str, int],
        dict[str, dict[str, Any]],
    ] = defaultdict(dict)

    for row in result_rows:
        key = (
            str(row["planned_decision_id"]),
            str(row["variant_id"]),
            int(row["external_optimizer_seed"]),
        )
        grouped[key][str(row["model_id"])] = row

    output = []
    for key in sorted(
        grouped,
        key=lambda k: min(
            int(x["job_order"]) for x in grouped[k].values()
        ),
    ):
        by_model = grouped[key]
        if set(by_model) != {"M0", "M1", "M2"}:
            continue

        valid = all(
            by_model[m]["status"] == "OK"
            and by_model[m]["bic"] is not None
            and math.isfinite(float(by_model[m]["bic"]))
            for m in MODEL_SPECS
        )

        exemplar = by_model["M0"]
        delta01: float | str = ""
        delta21: float | str = ""
        selected: bool | str = ""
        formal_period: float | str = ""
        period_label = "unavailable_incomplete_numerical"

        if (
            by_model["M1"]["status"] == "OK"
            and by_model["M1"]["formal_m1_period_s"] is not None
        ):
            formal_period = float(by_model["M1"]["formal_m1_period_s"])
            period_label = "formal_m1_center_not_selected"

        if valid:
            delta01 = float(by_model["M0"]["bic"]) - float(by_model["M1"]["bic"])
            delta21 = float(by_model["M2"]["bic"]) - float(by_model["M1"]["bic"])
            selected = selection_rule(
                float(by_model["M0"]["bic"]),
                float(by_model["M1"]["bic"]),
                float(by_model["M2"]["bic"]),
            )
            if selected:
                period_label = "recovered_period_selected"

        output.append({
            "planned_decision_id": key[0],
            "decision_class": exemplar["decision_class"],
            "phase3a_event_id": exemplar["phase3a_event_id"],
            "variant_id": key[1],
            "window_variant_id": exemplar["window_variant_id"],
            "processing_profile_id": exemplar["processing_profile_id"],
            "external_optimizer_seed": key[2],
            "bic_m0": "" if by_model["M0"]["bic"] is None else by_model["M0"]["bic"],
            "bic_m1": "" if by_model["M1"]["bic"] is None else by_model["M1"]["bic"],
            "bic_m2": "" if by_model["M2"]["bic"] is None else by_model["M2"]["bic"],
            "delta_bic_0_1": delta01,
            "delta_bic_2_1": delta21,
            "qpp_selected": selected,
            "formal_m1_period_s": formal_period,
            "period_label": period_label,
            "decision_status": "VALID" if valid else "INCOMPLETE_NUMERICAL",
        })
    return output


def run_jobs(
    *,
    checkpoint: Path,
    jobs: list[dict[str, Any]],
    payloads: dict[str, Any],
    max_new_jobs: int,
    resume: bool,
    manifest_sha: str,
    plan_kind: str,
    runner_sha: str,
    environment: dict[str, Any],
) -> dict[str, int]:
    if max_new_jobs < 0:
        raise ValueError("--max-new-jobs must be >= 0")
    if checkpoint.exists() and not resume:
        raise RuntimeError(
            f"Checkpoint already exists: {checkpoint}. "
            "Use --resume; F3A.3 does not delete prior results."
        )
    if resume and not checkpoint.exists():
        raise RuntimeError(
            "--resume requested but the checkpoint does not exist."
        )

    initialize_checkpoint(
        checkpoint,
        canary_manifest_sha256=manifest_sha,
        runner_sha256=runner_sha,
        afino_environment=environment,
        plan_kind=plan_kind,
    )

    started = utc_now()
    existing = result_ids(checkpoint)
    existing_before = len(existing)
    missing = [j for j in jobs if j["job_id"] not in existing]
    to_run = missing[:max_new_jobs]
    skipped_existing = len(jobs) - len(missing)

    new_jobs = 0
    for job in to_run:
        result = execute_one_job(job, payloads)
        insert_result_transaction(checkpoint, result)
        existing.add(job["job_id"])
        new_jobs += 1
        print(
            f"[{len(existing)}/{len(jobs)}] "
            f"{job['job_id']} {job['variant_id']} "
            f"seed={job['external_optimizer_seed']} "
            f"{job['model_id']} {result['status']} "
            f"({result['runtime_seconds']:.3f}s)",
            flush=True,
        )

    total_after = result_count(checkpoint)
    pending_after = len(jobs) - total_after

    record_invocation(
        checkpoint,
        started=started,
        manifest_sha=manifest_sha,
        plan_kind=plan_kind,
        resume=resume,
        max_new_jobs=max_new_jobs,
        existing_before=existing_before,
        new_jobs=new_jobs,
        skipped_existing=skipped_existing,
        total_after=total_after,
        pending_after=pending_after,
    )

    summary = {
        "existing_before": existing_before,
        "new_jobs": new_jobs,
        "total_after": total_after,
        "pending_after": pending_after,
    }
    print("CHECKPOINT_INVOCATION_SUMMARY=" + json.dumps(summary, sort_keys=True))
    return summary


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="F3A.3 checkpointed AFINO runner for the frozen canary."
    )
    p.add_argument("--repo-root", default=".")
    p.add_argument("--afino-repo", type=Path, required=True)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--canary-job-manifest", type=Path, required=True)
    p.add_argument("--max-new-jobs", type=int, required=True)
    p.add_argument("--export-results", type=Path)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--preflight-only", action="store_true")
    p.add_argument("--authorize-full-plan", action="store_true")
    return p


def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo / path


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = Path(args.repo_root).resolve()
    afino_repo = args.afino_repo.resolve()
    checkpoint = resolve(repo, args.checkpoint)
    manifest = resolve(repo, args.canary_job_manifest)
    export_path = (
        resolve(repo, args.export_results)
        if args.export_results is not None
        else None
    )

    if args.preflight_only:
        if args.resume or args.max_new_jobs != 0 or args.export_results is not None:
            raise RuntimeError(
                "--preflight-only requires --max-new-jobs 0 and cannot "
                "be combined with --resume or --export-results."
            )
        if args.authorize_full_plan:
            raise RuntimeError(
                "--authorize-full-plan is prohibited during F3A.3 preflight."
            )

    print("F3A.3 — CHECKPOINTED AFINO CANARY RUNNER", flush=True)
    verify_project_freeze(repo)
    environment = verify_environment(afino_repo)
    payloads = load_payload_dataset(repo)
    jobs, plan_kind, manifest_sha = load_plan(
        repo,
        manifest,
        payloads,
        authorize_full_plan=args.authorize_full_plan,
    )

    if plan_kind == "full" and not args.authorize_full_plan:
        raise RuntimeError("FULL_PLAN_EXECUTION_REQUIRES_EXPLICIT_AUTHORIZATION")
    if plan_kind == "full":
        print(
            "FULL_PLAN_EXECUTION_REQUIRES_EXPLICIT_AUTHORIZATION: "
            "authorization flag present",
            flush=True,
        )
    else:
        print("Full plan execution authorized: false", flush=True)

    runner_sha = sha256_file(Path(__file__).resolve())
    print(f"Runner SHA-256: {runner_sha}")
    print(f"Canary manifest SHA-256: {manifest_sha}")
    print(f"Plan kind: {plan_kind}")
    print(f"Jobs selected: {len(jobs)}")
    print(f"AFINO: {environment['afino_version']} / {environment['afino_commit']}")
    print(f"Python: {environment['python_version']}")
    print(f"NumPy: {environment['numpy_version']}")
    print(f"SciPy: {environment['scipy_version']}")
    print("FITS opened: false")
    print("Variants regenerated: false")
    print("QUALITY reapplied: false")
    print("Detrending recomputed: false")

    if args.preflight_only:
        if plan_kind != "canary":
            raise RuntimeError("F3A.3 preflight accepts only the frozen canary.")
        print("PHASE3A_F3A3_RUNNER_PREFLIGHT_PASS — NO AFINO CALLS")
        return 0

    summary = run_jobs(
        checkpoint=checkpoint,
        jobs=jobs,
        payloads=payloads,
        max_new_jobs=args.max_new_jobs,
        resume=args.resume,
        manifest_sha=manifest_sha,
        plan_kind=plan_kind,
        runner_sha=runner_sha,
        environment=environment,
    )

    if export_path is not None:
        n = export_results(checkpoint, jobs, export_path)
        print(f"exported_result_rows={n}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"PHASE3A_RUNNER_VALIDATION_BLOCKED: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise
