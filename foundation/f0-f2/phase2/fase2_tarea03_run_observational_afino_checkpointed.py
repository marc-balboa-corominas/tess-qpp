#!/usr/bin/env python3
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
import subprocess
import sys
import time
import traceback
import warnings
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import scipy


# =============================================================================
# Frozen F2.3 observational protocol
# =============================================================================

ROOT = Path(__file__).resolve().parent
REPO = ROOT / "afino_release_version"
RUNNER_FAMILY = "afino_checkpointed"
RUNNER_IMPLEMENTATION_VERSION = "1.2.0"

REFERENCE_RUNNER_NAME = "fase1_tarea11_run_nested_afino_checkpointed.py"
BUILD_CANARY_SCRIPT = ROOT / "fase2_tarea03_build_observational_canary.py"
FULL_PLAN_CSV = ROOT / "fase2_tarea02_exact_afino_execution_plan.csv"
CANARY_PLAN_CSV = ROOT / "fase2_tarea03_observational_canary_plan.csv"

TIME_NPY = ROOT / "fase2_tarea02_eligible_time_values.npy"
FLUX_NPY = ROOT / "fase2_tarea02_eligible_flux_values.npy"
FITS_INDEX_NPY = ROOT / "fase2_tarea02_eligible_fits_index_values.npy"
OFFSETS_NPY = ROOT / "fase2_tarea02_eligible_variant_offsets.npy"
VARIANT_MANIFEST_CSV = ROOT / "fase2_tarea02_observational_variant_manifest.csv"
RESOLVED_GRID_CSV = ROOT / "fase2_tarea02_resolved_decision_grid.csv"
MATERIALIZATION_AUDIT_JSON = ROOT / "fase2_tarea02_variant_materialization_audit.json"

DEFAULT_CHECKPOINT = ROOT / "fase2_tarea03_observational_canary_checkpoint.sqlite"
DEFAULT_RESULTS = ROOT / "fase2_tarea03_observational_canary_results.csv"
DEFAULT_DECISIONS = ROOT / "fase2_tarea03_observational_canary_decisions.csv"
DEFAULT_AUDIT = ROOT / "fase2_tarea03_observational_runner_validation_audit.json"
DEFAULT_REPORT = ROOT / "fase2_tarea03_observational_runner_validation_report.md"
DEFAULT_ENVIRONMENT = ROOT / "fase2_tarea03_environment.txt"

EXPECTED_AFINO_COMMIT = "6aceac9518fc8056052807e666da9d0c8bebb010"
EXPECTED_AFINO_VERSION = "0.5"
EXPECTED_PYTHON_VERSION = "3.13.13"
EXPECTED_NUMPY_VERSION = "2.5.1"
EXPECTED_SCIPY_VERSION = "1.18.0"
EXPECTED_REFERENCE_RUNNER_SHA256 = "b5bdbccb4f1170a40163ef99f465fb63d75d51f9d227178af8cdd82934e5695f"
EXPECTED_BUILD_CANARY_SHA256 = "6d65eb70b6476dd695979f1534ae1e6de1569c21649840387423519cf62b85b6"
EXPECTED_FULL_PLAN_SHA256 = "96c26a49bda9c2485ef02ed6a6de12caf56b54b45a9d997d86fb144e33abeb97"
EXPECTED_CANARY_PLAN_SHA256 = "54ea652f03943e2adce202343c39e074df88a1b0999faf57287d28d253c7dd1c"

EXPECTED_PHYSICAL_HASHES = {
    "fase2_tarea02_eligible_time_values.npy": "46a6c3c3afaf3c389dcdbc52715c68a9984849a12132e110cb0a80894c53b5e3",
    "fase2_tarea02_eligible_flux_values.npy": "e943e4f77ba642fc640e082a0fd75ae21ad6057fc31be299101262b42ee4e4f6",
    "fase2_tarea02_eligible_fits_index_values.npy": "43798bc41989283b31e863eec703c04719f592ba854f6f928f37e414723e3f06",
    "fase2_tarea02_eligible_variant_offsets.npy": "2a06abede71f3d53704f5ac55a4d0a49dccca68606233cdf487613bdabd8dd77",
    "fase2_tarea02_observational_variant_manifest.csv": "e89f33d433a48217feb44c07efae33b984377a205c218253553a604df71c5093",
    "fase2_tarea02_resolved_decision_grid.csv": "2150657765dff06fb69272c4c11b7bcea656dce2d3fd8faa15b35821dec944dd",
    "fase2_tarea02_exact_afino_execution_plan.csv": EXPECTED_FULL_PLAN_SHA256,
    "fase2_tarea02_variant_materialization_audit.json": "2264522b38cb6ea336518369200b3bce1370876bbe3b63273825cbaba3f7991b",
}

EXPECTED_LOGICAL_HASHES = {
    "canonical_time_payload_sha256": "e2f3fbbc8cb12ae94bcb8514d345a708587bae41b9e593cf1cb5035a1b8576e7",
    "canonical_flux_payload_sha256": "47059dc92672828f8b6aa262b731dd47ef53aa830e2648cfb7bd4770e00372ee",
    "canonical_fits_index_payload_sha256": "d169e884b6dfb5810a192c0bbccb3aa9d08716cbf7353aec3512a585e69039b5",
    "variant_offsets_canonical_sha256": "009b2bac827816b2123a4dc1d90226c98e68324c605264f739f257ebe5ccd45b",
}

MODEL_SPECS = {
    "M0": "pow_const",
    "M1": "pow_const_gauss",
    "M2": "bpow_const",
}
MODEL_ORDER = {"M0": 0, "M1": 1, "M2": 2}
LOW_FREQUENCY_CUTOFF_HZ = 1.0 / 40.0
BOUND_ATOL = 1.0e-7
ABS_TOLERANCE = 5.0e-12

OVERWRITE_GAUSS_BOUNDS = (
    (-10.0, 10.0),
    (-1.0, 6.0),
    (-20.0, 10.0),
    (-16.0, 5.0),
    (float(np.log(1.0 / 300.0)), float(np.log(1.0 / 40.0))),
    (0.05, 0.25),
)

MODEL_BOUNDS: dict[str, tuple[tuple[float | None, float | None], ...]] = {
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

REPLAY_DECISION_IDS = ("F2D000471", "F2D000461")
EXPECTED_FULL_PLAN_ROWS = 2784
EXPECTED_FULL_DECISIONS = 928
EXPECTED_CANARY_PLAN_ROWS = 84
EXPECTED_CANARY_DECISIONS = 28
EXPECTED_REPLAY_COMPARISONS = 6

FULL_PLAN_FIELDS = [
    "job_id", "job_order", "planned_decision_id", "decision_class",
    "variant_id", "event_id", "pair_id", "observational_role",
    "window_variant_id", "processing_profile_id",
    "external_optimizer_seed", "model_id", "model_name", "n_samples",
    "payload_start_offset", "payload_end_offset", "input_time_sha256",
    "input_flux_sha256", "source_fits_sha256",
    "candidate_discovery_use",
]
CANARY_PLAN_FIELDS = FULL_PLAN_FIELDS + ["canary_order"]

RESULT_FIELDNAMES = [
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

DECISION_FIELDNAMES = [
    "planned_decision_id", "decision_class", "variant_id", "event_id",
    "pair_id", "observational_role", "window_variant_id",
    "processing_profile_id", "external_optimizer_seed",
    "decision_status", "valid_models", "bic_m0", "bic_m1", "bic_m2",
    "delta_bic_0_1", "delta_bic_2_1", "qpp_selected",
    "formal_m1_period_s", "period_label",
]


# =============================================================================
# Generic utilities
# =============================================================================


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(array: np.ndarray, dtype: str) -> str:
    canonical = np.ascontiguousarray(array, dtype=dtype)
    return hashlib.sha256(canonical.tobytes(order="C")).hexdigest()


def json_compact(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Iterable[dict[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(fieldnames),
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


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run_command(["git", "-C", str(REPO), *args], check=check)


def finite_float(value: Any, name: str) -> float:
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{name} no es finito: {converted!r}")
    return converted


def empty_if_none(value: Any) -> Any:
    return "" if value is None else value


def parse_database_bool(value: Any) -> bool | str:
    if value is None or value == "":
        return ""
    return bool(int(value))


def locate_reference_runner() -> Path:
    candidates = [
        ROOT / REFERENCE_RUNNER_NAME,
        ROOT / "fase2_tarea03_reference" / REFERENCE_RUNNER_NAME,
    ]
    existing = [path for path in candidates if path.is_file()]
    if not existing:
        raise RuntimeError(
            "No verified F1.11 reference runner was found."
        )

    invalid = [
        {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
        }
        for path in existing
        if sha256(path) != EXPECTED_REFERENCE_RUNNER_SHA256
    ]
    if invalid:
        raise RuntimeError(
            "At least one F1.11 reference runner has a non-normative hash: "
            f"{invalid}"
        )

    preferred = ROOT / REFERENCE_RUNNER_NAME
    if preferred in existing:
        return preferred
    return existing[0]


# =============================================================================
# Environment and frozen-input preflight
# =============================================================================


def expected_python_candidates() -> list[Path]:
    return [
        (ROOT / ".venv" / "Scripts" / "python.exe").resolve(),
        (ROOT / ".venv" / "bin" / "python").resolve(),
    ]


def verify_environment() -> dict[str, Any]:
    if not REPO.is_dir():
        raise RuntimeError(f"No existe el repositorio AFINO: {REPO}")
    observed_python = Path(sys.executable).resolve()
    candidates = expected_python_candidates()
    if observed_python not in candidates:
        raise RuntimeError(
            "No se está usando el entorno .venv congelado de AFINO.\n"
            f"Observado: {observed_python}\n"
            f"Esperados: {', '.join(str(path) for path in candidates)}"
        )
    commit = git("rev-parse", "HEAD").stdout.strip()
    if commit != EXPECTED_AFINO_COMMIT:
        raise RuntimeError(
            f"Commit AFINO incorrecto: {commit}; "
            f"esperado {EXPECTED_AFINO_COMMIT}."
        )
    tracked_exit = git("diff", "--quiet", check=False).returncode
    staged_exit = git("diff", "--cached", "--quiet", check=False).returncode
    if tracked_exit != 0 or staged_exit != 0:
        raise RuntimeError(
            "El repositorio AFINO contiene cambios tracked o staged. "
            f"tracked={tracked_exit}, staged={staged_exit}."
        )
    git_status = git("status", "--porcelain").stdout.strip()
    pip_freeze = run_command(
        [sys.executable, "-m", "pip", "freeze"]
    ).stdout.splitlines()
    try:
        afino_version = importlib.metadata.version("afino")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError("El paquete afino no está instalado en .venv.") from exc
    observed_python_version = platform.python_version()
    if afino_version != EXPECTED_AFINO_VERSION:
        raise RuntimeError("Versión AFINO incorrecta.")
    if observed_python_version != EXPECTED_PYTHON_VERSION:
        raise RuntimeError(
            f"Python incorrecto: {observed_python_version}; "
            f"esperado {EXPECTED_PYTHON_VERSION}."
        )
    if np.__version__ != EXPECTED_NUMPY_VERSION:
        raise RuntimeError("Versión NumPy incorrecta.")
    if scipy.__version__ != EXPECTED_SCIPY_VERSION:
        raise RuntimeError("Versión SciPy incorrecta.")
    return {
        "commit": commit,
        "afino_version": afino_version,
        "tracked_diff_exit_code": tracked_exit,
        "staged_diff_exit_code": staged_exit,
        "git_status": git_status,
        "python_version": observed_python_version,
        "python_full": sys.version,
        "python_executable_relative": os.path.relpath(sys.executable, ROOT),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "pip_freeze": pip_freeze,
    }


def verify_frozen_files() -> tuple[dict[str, str], dict[str, str]]:
    expected = {
        **EXPECTED_PHYSICAL_HASHES,
        BUILD_CANARY_SCRIPT.name: EXPECTED_BUILD_CANARY_SHA256,
        CANARY_PLAN_CSV.name: EXPECTED_CANARY_PLAN_SHA256,
    }
    physical: dict[str, str] = {}
    for filename, expected_hash in expected.items():
        path = ROOT / filename
        if not path.is_file():
            raise FileNotFoundError(f"Falta el artefacto congelado: {path}")
        observed = sha256(path)
        physical[filename] = observed
        if observed != expected_hash:
            raise RuntimeError(
                f"Hash físico incorrecto para {filename}.\n"
                f"Esperado: {expected_hash}\nObservado: {observed}"
            )
    reference = locate_reference_runner()
    physical[reference.name] = sha256(reference)

    time_values = np.load(TIME_NPY, allow_pickle=False)
    flux_values = np.load(FLUX_NPY, allow_pickle=False)
    fits_indices = np.load(FITS_INDEX_NPY, allow_pickle=False)
    offsets = np.load(OFFSETS_NPY, allow_pickle=False)
    contracts = (
        (time_values, "<f8", (28380,)),
        (flux_values, "<f8", (28380,)),
        (fits_indices, "<i8", (28380,)),
        (offsets, "<i8", (515,)),
    )
    for array, dtype, shape in contracts:
        if array.dtype != np.dtype(dtype) or array.shape != shape:
            raise RuntimeError(
                f"Contrato de array inválido: dtype={array.dtype}, "
                f"shape={array.shape}."
            )
    logical = {
        "canonical_time_payload_sha256":
            canonical_sha256(time_values, "<f8"),
        "canonical_flux_payload_sha256":
            canonical_sha256(flux_values, "<f8"),
        "canonical_fits_index_payload_sha256":
            canonical_sha256(fits_indices, "<i8"),
        "variant_offsets_canonical_sha256":
            canonical_sha256(offsets, "<i8"),
    }
    if logical != EXPECTED_LOGICAL_HASHES:
        raise RuntimeError(
            f"Hashes lógicos F2.2 incorrectos: {logical}."
        )
    audit = json.loads(
        MATERIALIZATION_AUDIT_JSON.read_text(encoding="utf-8")
    )
    if audit.get("materialization_status") != (
        "OBSERVATIONAL_VARIANTS_AND_EXACT_PLAN_FROZEN_BEFORE_AFINO"
    ):
        raise RuntimeError("F2.2 does not have the frozen pre-AFINO status.")
    recorded = audit.get("logical_hashes", {})
    for key, value in EXPECTED_LOGICAL_HASHES.items():
        if recorded.get(key) != value:
            raise RuntimeError(f"F2.2 audit logical hash mismatch: {key}.")
    return physical, logical


# =============================================================================
# Dataset and plan loading
# =============================================================================


def independent_temporal_contract(
    time_seconds: np.ndarray,
) -> tuple[float, int]:
    differences = np.diff(time_seconds)
    median_dt_s = finite_float(np.median(differences), "median_dt_s")
    frequencies = np.fft.rfftfreq(len(time_seconds), d=median_dt_s)
    expected_bins = int(
        np.count_nonzero(
            (frequencies > 0.0)
            & (frequencies < LOW_FREQUENCY_CUTOFF_HZ)
        )
    )
    return median_dt_s, expected_bins


def load_dataset() -> dict[str, Any]:
    time_values = np.load(TIME_NPY, allow_pickle=False)
    flux_values = np.load(FLUX_NPY, allow_pickle=False)
    fits_indices = np.load(FITS_INDEX_NPY, allow_pickle=False)
    offsets = np.load(OFFSETS_NPY, allow_pickle=False)
    manifest_rows = read_csv(VARIANT_MANIFEST_CSV)
    if len(manifest_rows) != 780:
        raise RuntimeError("F2.2 variant manifest must contain 780 rows.")
    eligible_rows = [
        row for row in manifest_rows
        if row["admissibility_status"] == "ELIGIBLE_FOR_AFINO"
    ]
    eligible_rows.sort(key=lambda row: int(row["eligible_payload_order"]))
    if len(eligible_rows) != 514:
        raise RuntimeError("F2.2 must contain 514 eligible variants.")
    if [int(row["eligible_payload_order"]) for row in eligible_rows] != (
        list(range(1, 515))
    ):
        raise RuntimeError("Eligible payload order is not 1..514.")
    by_variant: dict[str, dict[str, Any]] = {}
    temporal_contracts: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(eligible_rows):
        start = int(offsets[index])
        end = int(offsets[index + 1])
        if start != int(raw["payload_start_offset"]):
            raise RuntimeError(f"Start offset mismatch: {raw['variant_id']}.")
        if end != int(raw["payload_end_offset"]):
            raise RuntimeError(f"End offset mismatch: {raw['variant_id']}.")
        if end - start != int(raw["retained_n_samples"]):
            raise RuntimeError(f"Sample count mismatch: {raw['variant_id']}.")
        time_seconds = np.asarray(time_values[start:end], dtype=np.float64)
        flux = np.asarray(flux_values[start:end], dtype=np.float64)
        indices = np.asarray(fits_indices[start:end], dtype=np.int64)
        if canonical_sha256(time_seconds, "<f8") != raw["time_sha256"]:
            raise RuntimeError(f"Time hash mismatch: {raw['variant_id']}.")
        if canonical_sha256(flux, "<f8") != raw["flux_sha256"]:
            raise RuntimeError(f"Flux hash mismatch: {raw['variant_id']}.")
        if (
            canonical_sha256(indices, "<i8")
            != raw["retained_indices_sha256"]
        ):
            raise RuntimeError(f"Index hash mismatch: {raw['variant_id']}.")
        if float(time_seconds[0]) != 0.0:
            raise RuntimeError(f"Time origin mismatch: {raw['variant_id']}.")
        if not np.all(np.diff(time_seconds) > 0.0):
            raise RuntimeError(f"Non-increasing time: {raw['variant_id']}.")
        if not np.all(np.diff(indices) == 1):
            raise RuntimeError(f"Non-consecutive indices: {raw['variant_id']}.")
        if not (
            np.all(np.isfinite(time_seconds))
            and np.all(np.isfinite(flux))
        ):
            raise RuntimeError(f"Non-finite payload: {raw['variant_id']}.")
        median_dt_s, expected_bins = independent_temporal_contract(
            time_seconds
        )
        row = dict(raw)
        row["payload_start_offset"] = start
        row["payload_end_offset"] = end
        row["retained_n_samples"] = int(raw["retained_n_samples"])
        by_variant[row["variant_id"]] = row
        temporal_contracts[row["variant_id"]] = {
            "median_dt_s": median_dt_s,
            "expected_post_cutoff_bin_count": expected_bins,
            "input_fits_index_sha256": raw["retained_indices_sha256"],
        }
    return {
        "time_values": time_values,
        "flux_values": flux_values,
        "fits_indices": fits_indices,
        "offsets": offsets,
        "manifest_rows": manifest_rows,
        "eligible_rows": eligible_rows,
        "by_variant": by_variant,
        "temporal_contracts": temporal_contracts,
    }


def parse_plan_row(
    raw: dict[str, str],
    dataset: dict[str, Any],
) -> dict[str, Any]:
    row: dict[str, Any] = dict(raw)
    for field in (
        "job_order", "external_optimizer_seed", "n_samples",
        "payload_start_offset", "payload_end_offset",
    ):
        row[field] = int(raw[field])
    if "canary_order" in raw:
        row["canary_order"] = int(raw["canary_order"])
    if row["model_id"] not in MODEL_SPECS:
        raise RuntimeError(f"Invalid model: {row['model_id']}.")
    if row["model_name"] != MODEL_SPECS[row["model_id"]]:
        raise RuntimeError(f"Model name mismatch: {row['job_id']}.")
    if row["decision_class"] not in {"primary", "stability"}:
        raise RuntimeError(f"Invalid decision class: {row['job_id']}.")
    if row["candidate_discovery_use"] != "false":
        raise RuntimeError(f"Candidate discovery in {row['job_id']}.")
    variant = dataset["by_variant"].get(row["variant_id"])
    if variant is None:
        raise RuntimeError(f"Unknown eligible variant: {row['variant_id']}.")
    expected_pairs = {
        "event_id": variant["event_id"],
        "pair_id": variant["pair_id"],
        "observational_role": variant["observational_role"],
        "window_variant_id": variant["window_variant_id"],
        "processing_profile_id": variant["processing_profile_id"],
        "n_samples": variant["retained_n_samples"],
        "payload_start_offset": variant["payload_start_offset"],
        "payload_end_offset": variant["payload_end_offset"],
        "input_time_sha256": variant["time_sha256"],
        "input_flux_sha256": variant["flux_sha256"],
        "source_fits_sha256": variant["source_fits_sha256"],
    }
    for field, expected in expected_pairs.items():
        if row[field] != expected:
            raise RuntimeError(
                f"Plan/manifest mismatch {row['job_id']} field {field}."
            )
    if (
        row["decision_class"] == "primary"
        and row["external_optimizer_seed"] != 0
    ):
        raise RuntimeError(f"Primary seed mismatch: {row['job_id']}.")
    if (
        row["decision_class"] == "stability"
        and not 1 <= row["external_optimizer_seed"] <= 9
    ):
        raise RuntimeError(f"Stability seed mismatch: {row['job_id']}.")
    contract = dataset["temporal_contracts"][row["variant_id"]]
    row.update(contract)
    return row


def load_plan(
    plan_path: Path,
    dataset: dict[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    full_raw = read_csv(FULL_PLAN_CSV)
    if len(full_raw) != EXPECTED_FULL_PLAN_ROWS:
        raise RuntimeError("Full plan row count mismatch.")
    if not full_raw or list(full_raw[0]) != FULL_PLAN_FIELDS:
        raise RuntimeError("Full plan schema mismatch.")
    full_rows = [parse_plan_row(row, dataset) for row in full_raw]
    if [row["job_order"] for row in full_rows] != list(range(1, 2785)):
        raise RuntimeError("Full job_order is not 1..2784.")
    if len({row["job_id"] for row in full_rows}) != 2784:
        raise RuntimeError("Duplicate full job IDs.")
    if len({
        (
            row["variant_id"],
            row["external_optimizer_seed"],
            row["model_id"],
        )
        for row in full_rows
    }) != 2784:
        raise RuntimeError("Duplicate full scientific keys.")
    if Counter(row["model_id"] for row in full_rows) != {
        "M0": 928, "M1": 928, "M2": 928,
    }:
        raise RuntimeError("Full rows per model mismatch.")
    full_decisions = {
        (row["planned_decision_id"], row["external_optimizer_seed"])
        for row in full_rows
    }
    if len(full_decisions) != EXPECTED_FULL_DECISIONS:
        raise RuntimeError("Full executable decision count mismatch.")

    observed_hash = sha256(plan_path)
    if observed_hash == EXPECTED_FULL_PLAN_SHA256:
        if list(read_csv(plan_path)[0]) != FULL_PLAN_FIELDS:
            raise RuntimeError("Full plan schema mismatch.")
        return full_rows, "full"
    if observed_hash != EXPECTED_CANARY_PLAN_SHA256:
        raise RuntimeError(
            f"Plan no congelado: {plan_path.name} SHA={observed_hash}."
        )
    raw_rows = read_csv(plan_path)
    if len(raw_rows) != EXPECTED_CANARY_PLAN_ROWS:
        raise RuntimeError("Canary row count mismatch.")
    if not raw_rows or list(raw_rows[0]) != CANARY_PLAN_FIELDS:
        raise RuntimeError("Canary plan schema mismatch.")
    full_by_job = {row["job_id"]: raw for row, raw in zip(full_rows, full_raw)}
    plan_rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        full_match = full_by_job.get(raw["job_id"])
        if full_match is None:
            raise RuntimeError(f"Canary job absent from full plan: {raw['job_id']}.")
        for field in FULL_PLAN_FIELDS:
            if raw[field] != full_match[field]:
                raise RuntimeError(
                    f"Canary is not literal for {raw['job_id']} field {field}."
                )
        plan_rows.append(parse_plan_row(raw, dataset))
    if [row["canary_order"] for row in plan_rows] != list(range(1, 85)):
        raise RuntimeError("canary_order is not 1..84.")
    if [row["job_order"] for row in plan_rows] != sorted(
        row["job_order"] for row in plan_rows
    ):
        raise RuntimeError("Canary is not ordered by original job_order.")
    if len({row["job_id"] for row in plan_rows}) != 84:
        raise RuntimeError("Duplicate canary job IDs.")
    if len({
        (
            row["variant_id"],
            row["external_optimizer_seed"],
            row["model_id"],
        )
        for row in plan_rows
    }) != 84:
        raise RuntimeError("Duplicate canary scientific keys.")
    if Counter(row["model_id"] for row in plan_rows) != {
        "M0": 28, "M1": 28, "M2": 28,
    }:
        raise RuntimeError("Canary rows per model mismatch.")
    decisions = {
        (row["planned_decision_id"], row["external_optimizer_seed"])
        for row in plan_rows
    }
    primary = {
        key
        for key in decisions
        if next(
            row for row in plan_rows
            if (
                row["planned_decision_id"],
                row["external_optimizer_seed"],
            ) == key
        )["decision_class"] == "primary"
    }
    stability = decisions - primary
    if len(primary) != 16 or len(stability) != 12:
        raise RuntimeError("Canary decision composition mismatch.")
    if len({row["variant_id"] for row in plan_rows}) != 16:
        raise RuntimeError("Canary unique variant count mismatch.")
    if {row["processing_profile_id"] for row in plan_rows} != {
        "P00", "P01", "P02", "P03", "P04", "P05",
    }:
        raise RuntimeError("Canary profile coverage mismatch.")
    if {row["observational_role"] for row in plan_rows} != {
        "PUBLISHED_QPP_REPRODUCED", "MATCHED_NOT_SELECTED",
    }:
        raise RuntimeError("Canary role coverage mismatch.")
    if {row["window_variant_id"] for row in plan_rows} != {"W00", "WX2"}:
        raise RuntimeError("Canary window coverage mismatch.")
    return plan_rows, "canary"


def extract_series_and_time(
    job: dict[str, Any],
    dataset: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    start = job["payload_start_offset"]
    end = job["payload_end_offset"]
    time_seconds = np.asarray(
        dataset["time_values"][start:end],
        dtype=np.float64,
    )
    flux = np.asarray(
        dataset["flux_values"][start:end],
        dtype=np.float64,
    )
    fits_indices = np.asarray(
        dataset["fits_indices"][start:end],
        dtype=np.int64,
    )
    if len(time_seconds) != job["n_samples"]:
        raise RuntimeError(f"Time length mismatch: {job['job_id']}.")
    if len(flux) != job["n_samples"]:
        raise RuntimeError(f"Flux length mismatch: {job['job_id']}.")
    if len(fits_indices) != job["n_samples"]:
        raise RuntimeError(f"Index length mismatch: {job['job_id']}.")
    if canonical_sha256(time_seconds, "<f8") != job["input_time_sha256"]:
        raise RuntimeError(f"Time hash mismatch: {job['job_id']}.")
    if canonical_sha256(flux, "<f8") != job["input_flux_sha256"]:
        raise RuntimeError(f"Flux hash mismatch: {job['job_id']}.")
    if (
        canonical_sha256(fits_indices, "<i8")
        != job["input_fits_index_sha256"]
    ):
        raise RuntimeError(f"Index hash mismatch: {job['job_id']}.")
    if float(time_seconds[0]) != 0.0:
        raise RuntimeError(f"Time does not start at zero: {job['job_id']}.")
    if not np.all(np.diff(time_seconds) > 0.0):
        raise RuntimeError(f"Time not strictly increasing: {job['job_id']}.")
    if not np.all(np.diff(fits_indices) == 1):
        raise RuntimeError(f"FITS indices not consecutive: {job['job_id']}.")
    return time_seconds, flux


# =============================================================================
# Frozen AFINO execution core
# =============================================================================


def inspect_bounds(model_name: str, parameters: np.ndarray) -> tuple[bool, list[int], list[dict[str, Any]]]:
    bounds = MODEL_BOUNDS[model_name]
    hits: list[dict[str, Any]] = []
    if len(parameters) != len(bounds):
        return False, [], [
            {
                "status": "parameter_count_mismatch",
                "parameter_count": int(len(parameters)),
                "bound_count": int(len(bounds)),
            }
        ]

    for index, (value, (lower, upper)) in enumerate(zip(parameters, bounds)):
        value_float = float(value)
        if lower is not None and np.isclose(
            value_float, lower, rtol=0.0, atol=BOUND_ATOL
        ):
            hits.append(
                {
                    "parameter_index": index,
                    "side": "lower",
                    "value": value_float,
                    "bound": float(lower),
                }
            )
        if upper is not None and np.isclose(
            value_float, upper, rtol=0.0, atol=BOUND_ATOL
        ):
            hits.append(
                {
                    "parameter_index": index,
                    "side": "upper",
                    "value": value_float,
                    "bound": float(upper),
                }
            )
    indices = sorted({int(item["parameter_index"]) for item in hits})
    return bool(hits), indices, hits


def warning_payload(caught: list[warnings.WarningMessage]) -> tuple[int, str, str]:
    entries = [
        {
            "category": item.category.__name__,
            "message": str(item.message),
            "filename": Path(item.filename).name,
            "lineno": int(item.lineno),
        }
        for item in caught
    ]
    warning_types = sorted(
        {f"{entry['category']}: {entry['message']}" for entry in entries}
    )
    return len(entries), json_compact(warning_types), json_compact(entries)


def execute_one_job(job: dict[str, Any], dataset: dict[str, Any]) -> dict[str, Any]:
    # Delayed import ensures structural commands fail cleanly when AFINO is absent.
    from afino import afino_series
    from afino.afino_main_analysis3 import main_analysis

    time_seconds, flux = extract_series_and_time(job, dataset)
    started = time.perf_counter()
    base = {
        "job_id": job["job_id"],
        "job_order": job["job_order"],
        "planned_decision_id": job["planned_decision_id"],
        "decision_class": job["decision_class"],
        "variant_id": job["variant_id"],
        "event_id": job["event_id"],
        "pair_id": job["pair_id"],
        "observational_role": job["observational_role"],
        "window_variant_id": job["window_variant_id"],
        "processing_profile_id": job["processing_profile_id"],
        "external_optimizer_seed": job["external_optimizer_seed"],
        "model_id": job["model_id"],
        "model_name": job["model_name"],
        "status": "NOT_RUN",
        "runtime_seconds": None,
        "n_samples": job["n_samples"],
        "payload_start_offset": job["payload_start_offset"],
        "payload_end_offset": job["payload_end_offset"],
        "input_flux_sha256": job["input_flux_sha256"],
        "input_time_sha256": job["input_time_sha256"],
        "input_fits_index_sha256": job["input_fits_index_sha256"],
        "source_fits_sha256": job["source_fits_sha256"],
        "median_dt_s": job["median_dt_s"],
        "expected_post_cutoff_bin_count":
            job["expected_post_cutoff_bin_count"],
        "afino_effective_dt_s": None,
        "positive_frequency_bins": None,
        "bins_after_cutoff": None,
        "minimum_frequency_hz": None,
        "maximum_frequency_hz": None,
        "lnlike": None,
        "BIC": None,
        "rchi2": None,
        "probability": None,
        "parameters_json": None,
        "estimated_period_s": None,
        "parameter_at_bound": None,
        "bound_indices_json": None,
        "bound_details_json": None,
        "warning_count": None,
        "warning_types_json": None,
        "warnings_json": None,
        "convergence_status": "NOT_AUDITABLE",
        "error": None,
        "completed_at_utc": None,
    }
    try:
        series = afino_series.AfinoSeries(time_seconds, flux)
        prepared = afino_series.prep_series(series)
        effective_dt = finite_float(prepared.SampleTimes.dt, "afino_effective_dt_s")
        positive_frequencies = np.asarray(
            prepared.PowerSpectrum.frequencies.positive,
            dtype=float,
        )

        # Frozen rule: independent reset immediately before each individual model.
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
            raise ValueError("Los parámetros contienen valores no finitos.")
        if frequencies.size == 0 or not np.all(np.isfinite(frequencies)):
            raise ValueError("No quedaron frecuencias finitas tras el cutoff.")

        estimated_period: float | None = None
        if job["model_id"] == "M1":
            if parameters.size <= 4:
                raise ValueError("M1 no devolvió params[4].")
            estimated_period = finite_float(
                1.0 / np.exp(parameters[4]),
                "estimated_period_s",
            )

        parameter_at_bound, bound_indices, bound_details = inspect_bounds(
            job["model_name"], parameters
        )
        warning_count, warning_types_json, warnings_json = warning_payload(list(caught))

        base.update(
            {
                "status": "OK",
                "afino_effective_dt_s": effective_dt,
                "positive_frequency_bins": int(positive_frequencies.size),
                "bins_after_cutoff": int(frequencies.size),
                "minimum_frequency_hz": float(np.min(frequencies)),
                "maximum_frequency_hz": float(np.max(frequencies)),
                "lnlike": finite_float(result["lnlike"], "lnlike"),
                "BIC": finite_float(result["BIC"], "BIC"),
                "rchi2": finite_float(result["rchi2"], "rchi2"),
                "probability": finite_float(result["probability"], "probability"),
                "parameters_json": json_compact(parameters.tolist()),
                "estimated_period_s": estimated_period,
                "parameter_at_bound": int(parameter_at_bound),
                "bound_indices_json": json_compact(bound_indices),
                "bound_details_json": json_compact(bound_details),
                "warning_count": warning_count,
                "warning_types_json": warning_types_json,
                "warnings_json": warnings_json,
            }
        )
    except Exception:
        base.update(
            {
                "status": "ERROR",
                "error": traceback.format_exc(),
            }
        )
    finally:
        base["runtime_seconds"] = time.perf_counter() - started
        base["completed_at_utc"] = utc_now()
    return base


# =============================================================================
# SQLite checkpoint
# =============================================================================


RESULT_COLUMNS = [
    "job_id", "job_order", "planned_decision_id", "decision_class",
    "variant_id", "event_id", "pair_id", "observational_role",
    "window_variant_id", "processing_profile_id",
    "external_optimizer_seed", "model_id", "model_name", "status",
    "runtime_seconds", "n_samples", "payload_start_offset",
    "payload_end_offset", "input_flux_sha256", "input_time_sha256",
    "input_fits_index_sha256", "source_fits_sha256", "median_dt_s",
    "expected_post_cutoff_bin_count", "afino_effective_dt_s",
    "positive_frequency_bins", "bins_after_cutoff",
    "minimum_frequency_hz", "maximum_frequency_hz", "lnlike", "BIC",
    "rchi2", "probability", "parameters_json", "estimated_period_s",
    "parameter_at_bound", "bound_indices_json", "bound_details_json",
    "warning_count", "warning_types_json", "warnings_json",
    "convergence_status", "error", "completed_at_utc",
]


def connect_checkpoint(
    path: Path,
    *,
    readonly: bool = False,
) -> sqlite3.Connection:
    if readonly:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    else:
        connection = sqlite3.connect(path)
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
    connection.row_factory = sqlite3.Row
    return connection


def initialize_checkpoint(
    checkpoint: Path,
    *,
    plan_path: Path,
    plan_sha256: str,
    plan_kind: str,
    runner_sha256: str,
    physical_hashes: dict[str, str],
    logical_hashes: dict[str, str],
) -> None:
    connection = connect_checkpoint(checkpoint)
    try:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS results (
                job_id TEXT PRIMARY KEY,
                job_order INTEGER NOT NULL,
                planned_decision_id TEXT NOT NULL,
                decision_class TEXT NOT NULL,
                variant_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                pair_id TEXT NOT NULL,
                observational_role TEXT NOT NULL,
                window_variant_id TEXT NOT NULL,
                processing_profile_id TEXT NOT NULL,
                external_optimizer_seed INTEGER NOT NULL,
                model_id TEXT NOT NULL,
                model_name TEXT NOT NULL,
                status TEXT NOT NULL,
                runtime_seconds REAL NOT NULL,
                n_samples INTEGER NOT NULL,
                payload_start_offset INTEGER NOT NULL,
                payload_end_offset INTEGER NOT NULL,
                input_flux_sha256 TEXT NOT NULL,
                input_time_sha256 TEXT NOT NULL,
                input_fits_index_sha256 TEXT NOT NULL,
                source_fits_sha256 TEXT NOT NULL,
                median_dt_s REAL NOT NULL,
                expected_post_cutoff_bin_count INTEGER NOT NULL,
                afino_effective_dt_s REAL,
                positive_frequency_bins INTEGER,
                bins_after_cutoff INTEGER,
                minimum_frequency_hz REAL,
                maximum_frequency_hz REAL,
                lnlike REAL,
                BIC REAL,
                rchi2 REAL,
                probability REAL,
                parameters_json TEXT,
                estimated_period_s REAL,
                parameter_at_bound INTEGER,
                bound_indices_json TEXT,
                bound_details_json TEXT,
                warning_count INTEGER,
                warning_types_json TEXT,
                warnings_json TEXT,
                convergence_status TEXT NOT NULL,
                error TEXT,
                completed_at_utc TEXT NOT NULL,
                UNIQUE(
                    variant_id,
                    external_optimizer_seed,
                    model_id
                )
            );
            CREATE TABLE IF NOT EXISTS invocations (
                invocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_sha256 TEXT NOT NULL,
                plan_kind TEXT NOT NULL,
                started_at_utc TEXT NOT NULL,
                finished_at_utc TEXT NOT NULL,
                resume_requested INTEGER NOT NULL,
                stop_after INTEGER,
                existing_before INTEGER NOT NULL,
                committed_new INTEGER NOT NULL,
                skipped_existing INTEGER NOT NULL,
                total_after INTEGER NOT NULL
            );
        """)
        metadata = {
            "schema_version": "1.2.0",
            "runner_family": RUNNER_FAMILY,
            "runner_implementation_version": RUNNER_IMPLEMENTATION_VERSION,
            "plan_filename": plan_path.name,
            "plan_sha256": plan_sha256,
            "plan_kind": plan_kind,
            "full_plan_sha256": EXPECTED_FULL_PLAN_SHA256,
            "canary_plan_sha256": EXPECTED_CANARY_PLAN_SHA256,
            "runner_sha256": runner_sha256,
            "dataset_physical_hashes": json_compact(physical_hashes),
            "dataset_logical_hashes": json_compact(logical_hashes),
            "afino_commit": EXPECTED_AFINO_COMMIT,
            "afino_version": EXPECTED_AFINO_VERSION,
            "created_at_utc": utc_now(),
        }
        existing = {
            row["key"]: row["value"]
            for row in connection.execute(
                "SELECT key, value FROM metadata"
            )
        }
        if existing:
            for key in (
                "schema_version", "runner_family",
                "runner_implementation_version", "plan_filename",
                "plan_sha256", "plan_kind", "full_plan_sha256",
                "canary_plan_sha256", "runner_sha256",
                "dataset_physical_hashes", "dataset_logical_hashes",
                "afino_commit", "afino_version",
            ):
                if existing.get(key) != metadata[key]:
                    raise RuntimeError(
                        f"Checkpoint incompatible in metadata[{key}]."
                    )
        else:
            connection.executemany(
                "INSERT INTO metadata(key, value) VALUES (?, ?)",
                list(metadata.items()),
            )
        connection.commit()
    finally:
        connection.close()


def insert_result_transaction(checkpoint: Path, result: dict[str, Any]) -> None:
    connection = connect_checkpoint(checkpoint)
    try:
        placeholders = ",".join("?" for _ in RESULT_COLUMNS)
        columns = ",".join(RESULT_COLUMNS)
        values = [result[column] for column in RESULT_COLUMNS]
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            f"INSERT INTO results ({columns}) VALUES ({placeholders})",
            values,
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def record_invocation(
    checkpoint: Path,
    *,
    plan_sha256: str,
    plan_kind: str,
    started_at: str,
    resume_requested: bool,
    stop_after: int | None,
    existing_before: int,
    committed_new: int,
    skipped_existing: int,
    total_after: int,
) -> None:
    connection = connect_checkpoint(checkpoint)
    try:
        connection.execute(
            """
            INSERT INTO invocations(
                plan_sha256, plan_kind, started_at_utc, finished_at_utc,
                resume_requested, stop_after, existing_before,
                committed_new, skipped_existing, total_after
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_sha256, plan_kind, started_at, utc_now(),
                int(resume_requested), stop_after, existing_before,
                committed_new, skipped_existing, total_after,
            ),
        )
        connection.commit()
    finally:
        connection.close()


def checkpoint_result_ids(checkpoint: Path) -> set[str]:
    connection = connect_checkpoint(checkpoint, readonly=True)
    try:
        return {
            row[0]
            for row in connection.execute("SELECT job_id FROM results")
        }
    finally:
        connection.close()


def checkpoint_count(checkpoint: Path) -> int:
    connection = connect_checkpoint(checkpoint, readonly=True)
    try:
        return int(
            connection.execute("SELECT COUNT(*) FROM results").fetchone()[0]
        )
    finally:
        connection.close()


def run_plan(
    *,
    plan_path: Path,
    plan_rows: list[dict[str, Any]],
    plan_kind: str,
    checkpoint: Path,
    resume: bool,
    stop_after: int | None,
    dataset: dict[str, Any],
    runner_sha256: str,
    physical_hashes: dict[str, str],
    logical_hashes: dict[str, str],
    allow_full_plan: bool,
) -> dict[str, int]:
    if plan_kind == "full" and not allow_full_plan:
        raise RuntimeError(
            "The complete observational plan is blocked in F2.3. "
            "F2.4 must use --allow-full-plan explicitly."
        )
    if checkpoint.exists() and not resume:
        raise RuntimeError(
            f"Checkpoint already exists: {checkpoint}. "
            "Use --resume or preserve it."
        )
    if stop_after is not None and stop_after <= 0:
        raise ValueError("--stop-after must be positive.")
    plan_sha = sha256(plan_path)
    initialize_checkpoint(
        checkpoint,
        plan_path=plan_path,
        plan_sha256=plan_sha,
        plan_kind=plan_kind,
        runner_sha256=runner_sha256,
        physical_hashes=physical_hashes,
        logical_hashes=logical_hashes,
    )
    started_at = utc_now()
    existing_ids = checkpoint_result_ids(checkpoint)
    existing_before = len(existing_ids)
    committed_new = 0
    skipped_existing = 0
    for job in plan_rows:
        if job["job_id"] in existing_ids:
            skipped_existing += 1
            continue
        result = execute_one_job(job, dataset)
        insert_result_transaction(checkpoint, result)
        existing_ids.add(job["job_id"])
        committed_new += 1
        print(
            f"[{len(existing_ids)}/{len(plan_rows)}] "
            f"{job['job_id']} {job['variant_id']} "
            f"seed={job['external_optimizer_seed']} "
            f"{job['model_id']}: {result['status']} "
            f"({result['runtime_seconds']:.3f} s)",
            flush=True,
        )
        if stop_after is not None and committed_new >= stop_after:
            break
    total_after = checkpoint_count(checkpoint)
    record_invocation(
        checkpoint,
        plan_sha256=plan_sha,
        plan_kind=plan_kind,
        started_at=started_at,
        resume_requested=resume,
        stop_after=stop_after,
        existing_before=existing_before,
        committed_new=committed_new,
        skipped_existing=skipped_existing,
        total_after=total_after,
    )
    summary = {
        "existing_before": existing_before,
        "committed_new": committed_new,
        "skipped_existing": skipped_existing,
        "total_after": total_after,
        "pending_after": len(plan_rows) - total_after,
    }
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return summary


# =============================================================================
# Export, decisions and replay
# =============================================================================


def fetch_results_for_plan(
    checkpoint: Path,
    plan_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    connection = connect_checkpoint(checkpoint, readonly=True)
    try:
        fetched = {
            row["job_id"]: dict(row)
            for row in connection.execute("SELECT * FROM results")
        }
    finally:
        connection.close()
    return [
        fetched[row["job_id"]]
        for row in plan_rows
        if row["job_id"] in fetched
    ]


def result_export_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": row["job_id"],
        "job_order": row["job_order"],
        "planned_decision_id": row["planned_decision_id"],
        "decision_class": row["decision_class"],
        "variant_id": row["variant_id"],
        "event_id": row["event_id"],
        "pair_id": row["pair_id"],
        "observational_role": row["observational_role"],
        "window_variant_id": row["window_variant_id"],
        "processing_profile_id": row["processing_profile_id"],
        "external_optimizer_seed": row["external_optimizer_seed"],
        "model_id": row["model_id"],
        "model_name": row["model_name"],
        "n_samples": row["n_samples"],
        "payload_start_offset": row["payload_start_offset"],
        "payload_end_offset": row["payload_end_offset"],
        "input_time_sha256": row["input_time_sha256"],
        "input_flux_sha256": row["input_flux_sha256"],
        "input_fits_index_sha256": row["input_fits_index_sha256"],
        "source_fits_sha256": row["source_fits_sha256"],
        "median_dt_s": row["median_dt_s"],
        "expected_post_cutoff_bin_count":
            row["expected_post_cutoff_bin_count"],
        "status": row["status"],
        "bic": empty_if_none(row["BIC"]),
        "log_likelihood": empty_if_none(row["lnlike"]),
        "parameters_json": empty_if_none(row["parameters_json"]),
        "formal_m1_period_s": empty_if_none(row["estimated_period_s"]),
        "rchi2": empty_if_none(row["rchi2"]),
        "probability": empty_if_none(row["probability"]),
        "warning_count": empty_if_none(row["warning_count"]),
        "warning_types_json": empty_if_none(row["warning_types_json"]),
        "warnings_json": empty_if_none(row["warnings_json"]),
        "parameter_at_bound":
            parse_database_bool(row["parameter_at_bound"]),
        "bound_indices_json": empty_if_none(row["bound_indices_json"]),
        "bound_hits_json": empty_if_none(row["bound_details_json"]),
        "afino_effective_dt_s":
            empty_if_none(row["afino_effective_dt_s"]),
        "post_cutoff_bin_count":
            empty_if_none(row["bins_after_cutoff"]),
        "positive_frequency_bin_count":
            empty_if_none(row["positive_frequency_bins"]),
        "minimum_frequency_hz":
            empty_if_none(row["minimum_frequency_hz"]),
        "maximum_frequency_hz":
            empty_if_none(row["maximum_frequency_hz"]),
        "runtime_seconds": row["runtime_seconds"],
        "convergence_status": row["convergence_status"],
        "error": empty_if_none(row["error"]),
    }


def export_results(
    checkpoint: Path,
    plan_rows: list[dict[str, Any]],
    output_path: Path,
) -> list[dict[str, Any]]:
    rows = fetch_results_for_plan(checkpoint, plan_rows)
    write_csv(
        output_path,
        RESULT_FIELDNAMES,
        [result_export_row(row) for row in rows],
    )
    return rows


def build_decisions(
    result_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[
        tuple[str, str, int],
        dict[str, dict[str, Any]],
    ] = defaultdict(dict)
    order: list[tuple[str, str, int]] = []
    for row in result_rows:
        key = (
            str(row["planned_decision_id"]),
            str(row["variant_id"]),
            int(row["external_optimizer_seed"]),
        )
        if key not in grouped:
            order.append(key)
        grouped[key][str(row["model_id"])] = row
    decisions: list[dict[str, Any]] = []
    for key in order:
        by_model = grouped[key]
        if set(by_model) != {"M0", "M1", "M2"}:
            raise RuntimeError(f"Incomplete model trio for {key}.")
        valid_models = sum(
            by_model[model]["status"] == "OK"
            and by_model[model]["BIC"] is not None
            and math.isfinite(float(by_model[model]["BIC"]))
            for model in MODEL_SPECS
        )
        valid = valid_models == 3
        delta01: float | str = ""
        delta21: float | str = ""
        selected: bool | str = ""
        estimated_period: float | str = ""
        period_label = "unavailable_incomplete_numerical"
        if (
            by_model["M1"]["status"] == "OK"
            and by_model["M1"]["estimated_period_s"] is not None
        ):
            estimated_period = float(
                by_model["M1"]["estimated_period_s"]
            )
            period_label = "formal_m1_center_not_selected"
        if valid:
            delta01 = (
                float(by_model["M0"]["BIC"])
                - float(by_model["M1"]["BIC"])
            )
            delta21 = (
                float(by_model["M2"]["BIC"])
                - float(by_model["M1"]["BIC"])
            )
            selected = bool(delta01 > 10.0 and delta21 > 10.0)
            if selected:
                period_label = "recovered_period_selected"
        exemplar = by_model["M0"]
        decisions.append({
            "planned_decision_id": key[0],
            "decision_class": exemplar["decision_class"],
            "variant_id": key[1],
            "event_id": exemplar["event_id"],
            "pair_id": exemplar["pair_id"],
            "observational_role": exemplar["observational_role"],
            "window_variant_id": exemplar["window_variant_id"],
            "processing_profile_id": exemplar["processing_profile_id"],
            "external_optimizer_seed": key[2],
            "decision_status":
                "VALID" if valid else "INCOMPLETE_NUMERICAL",
            "valid_models": valid_models,
            "bic_m0": empty_if_none(by_model["M0"]["BIC"]),
            "bic_m1": empty_if_none(by_model["M1"]["BIC"]),
            "bic_m2": empty_if_none(by_model["M2"]["BIC"]),
            "delta_bic_0_1": delta01,
            "delta_bic_2_1": delta21,
            "qpp_selected": selected,
            "formal_m1_period_s": estimated_period,
            "period_label": period_label,
        })
    return decisions


def export_decisions(
    result_rows: list[dict[str, Any]],
    output_path: Path,
) -> list[dict[str, Any]]:
    decisions = build_decisions(result_rows)
    write_csv(output_path, DECISION_FIELDNAMES, decisions)
    return decisions


def exact_replay_compare(original: dict[str, Any], replay: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    fields = [
        "status",
        "BIC",
        "lnlike",
        "parameters_json",
        "estimated_period_s",
        "rchi2",
        "probability",
        "warning_count",
        "warning_types_json",
        "warnings_json",
        "parameter_at_bound",
        "bound_indices_json",
        "bound_details_json",
    ]
    differences: list[dict[str, Any]] = []
    for field in fields:
        left = original.get(field)
        right = replay.get(field)
        if left != right:
            differences.append({"field": field, "checkpoint": left, "replay": right})
    passed = not differences and original.get("status") == "OK" and replay.get("status") == "OK"
    return passed, {"fields_compared": fields, "differences": differences}


def run_replays(
    checkpoint: Path,
    plan_rows: list[dict[str, Any]],
    dataset: dict[str, Any],
) -> dict[str, Any]:
    targets = [
        row for row in plan_rows
        if row["planned_decision_id"] in REPLAY_DECISION_IDS
        and row["external_optimizer_seed"] == 0
    ]
    if len(targets) != EXPECTED_REPLAY_COMPARISONS:
        raise RuntimeError(
            f"Expected six replay jobs; found {len(targets)}."
        )
    connection = connect_checkpoint(checkpoint, readonly=True)
    try:
        originals = {
            row["job_id"]: dict(row)
            for row in connection.execute("SELECT * FROM results")
        }
    finally:
        connection.close()
    extra_fields = [
        "afino_effective_dt_s",
        "bins_after_cutoff",
        "error",
    ]
    comparisons: list[dict[str, Any]] = []
    for job in targets:
        original = originals.get(job["job_id"])
        if original is None:
            raise RuntimeError(f"Missing original: {job['job_id']}.")
        replay = execute_one_job(job, dataset)
        core_passed, detail = exact_replay_compare(original, replay)
        extra_differences = [
            {
                "field": field,
                "checkpoint": original.get(field),
                "replay": replay.get(field),
            }
            for field in extra_fields
            if original.get(field) != replay.get(field)
        ]
        passed = core_passed and not extra_differences
        comparisons.append({
            "job_id": job["job_id"],
            "planned_decision_id": job["planned_decision_id"],
            "variant_id": job["variant_id"],
            "model_id": job["model_id"],
            "passed": passed,
            **detail,
            "additional_fields_compared": extra_fields,
            "additional_differences": extra_differences,
        })
        print(
            f"REPLAY {job['job_id']} {job['model_id']}: "
            f"{'PASS' if passed else 'FAIL'}"
        )
    passed_count = sum(item["passed"] for item in comparisons)
    return {
        "expected_count": EXPECTED_REPLAY_COMPARISONS,
        "passed_count": passed_count,
        "failed_count":
            EXPECTED_REPLAY_COMPARISONS - passed_count,
        "comparisons": comparisons,
    }


# =============================================================================
# Independent validation, audit and report
# =============================================================================


def read_checkpoint_audit(checkpoint: Path) -> dict[str, Any]:
    connection = connect_checkpoint(checkpoint, readonly=True)
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
    finally:
        connection.close()
    return {
        "metadata": metadata,
        "results": results,
        "invocations": invocations,
    }


def duplicate_counts(
    results: list[dict[str, Any]],
) -> dict[str, int]:
    job_counts = Counter(row["job_id"] for row in results)
    scientific_counts = Counter(
        (
            row["variant_id"],
            row["external_optimizer_seed"],
            row["model_id"],
        )
        for row in results
    )
    return {
        "duplicate_job_ids": sum(
            count - 1 for count in job_counts.values() if count > 1
        ),
        "duplicate_scientific_keys": sum(
            count - 1
            for count in scientific_counts.values()
            if count > 1
        ),
    }


def environment_text(environment: dict[str, Any]) -> str:
    return "\n".join([
        f"Python: {environment['python_version']}",
        f"Python full: {environment['python_full']}",
        "Python executable relative: "
        f"{environment['python_executable_relative']}",
        f"NumPy: {environment['numpy_version']}",
        f"SciPy: {environment['scipy_version']}",
        f"Platform: {environment['platform']}",
        f"Machine: {environment['machine']}",
        f"Processor: {environment['processor']}",
        f"AFINO commit: {environment['commit']}",
        f"AFINO package version: {environment['afino_version']}",
        "Tracked diff exit code: "
        f"{environment['tracked_diff_exit_code']}",
        "Staged diff exit code: "
        f"{environment['staged_diff_exit_code']}",
        "Git status --porcelain:",
        environment["git_status"],
        "",
        "pip freeze:",
        *environment["pip_freeze"],
        "",
        "Astropy imported: false",
        "FITS opened: false",
    ])


def function_source(source: str, name: str) -> str:
    tree = ast.parse(source)
    node = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    lines = source.splitlines()
    return "\n".join(lines[node.lineno - 1: node.end_lineno])


def runner_diff_audit() -> dict[str, Any]:
    import difflib
    reference_path = locate_reference_runner()
    reference_source = reference_path.read_text(encoding="utf-8")
    current_source = Path(__file__).resolve().read_text(encoding="utf-8")
    diff_lines = list(
        difflib.unified_diff(
            reference_source.splitlines(),
            current_source.splitlines(),
            lineterm="",
        )
    )
    exact_functions = {
        name: (
            function_source(reference_source, name)
            == function_source(current_source, name)
        )
        for name in (
            "inspect_bounds",
            "warning_payload",
            "insert_result_transaction",
            "exact_replay_compare",
        )
    }
    marker_start = "        series = afino_series.AfinoSeries"
    marker_end = "    except Exception:"
    old_start = reference_source.index(marker_start)
    new_start = current_source.index(marker_start)
    old_core = reference_source[
        old_start:
        reference_source.index(marker_end, old_start)
    ]
    new_core = current_source[
        new_start:
        current_source.index(marker_end, new_start)
    ]
    scientific_core = {
        "model_specs_identical":
            MODEL_SPECS == {
                "M0": "pow_const",
                "M1": "pow_const_gauss",
                "M2": "bpow_const",
            },
        "cutoff_identical":
            LOW_FREQUENCY_CUTOFF_HZ == 1.0 / 40.0,
        "m1_bounds_identical":
            OVERWRITE_GAUSS_BOUNDS == (
                (-10.0, 10.0), (-1.0, 6.0), (-20.0, 10.0),
                (-16.0, 5.0),
                (
                    float(np.log(1.0 / 300.0)),
                    float(np.log(1.0 / 40.0)),
                ),
                (0.05, 0.25),
            ),
        "afino_import_lines_identical": (
            "    from afino import afino_series\n"
            "    from afino.afino_main_analysis3 import main_analysis"
        ) in current_source,
        "afino_execution_fragment_byte_identical": old_core == new_core,
        "seed_reset_before_each_model_call": (
            'np.random.seed(job["external_optimizer_seed"])'
            in new_core
        ),
        "parameter_serialization_identical": (
            '"parameters_json": json_compact(parameters.tolist())'
            in new_core
        ),
        "double_bic_rule_identical": (
            "selected = bool(delta01 > 10.0 and delta21 > 10.0)"
            in current_source
        ),
        **{
            f"function_{name}_byte_identical": value
            for name, value in exact_functions.items()
        },
    }
    if not all(scientific_core.values()):
        raise RuntimeError(
            f"Scientific core differs from runner 1.1.0: "
            f"{scientific_core}"
        )
    return {
        "reference_runner": reference_path.name,
        "reference_sha256": sha256(reference_path),
        "observational_runner": Path(__file__).resolve().name,
        "observational_sha256": sha256(Path(__file__).resolve()),
        "unified_diff_sha256": hashlib.sha256(
            "\n".join(diff_lines).encode("utf-8")
        ).hexdigest(),
        "unified_diff_line_count": len(diff_lines),
        "classified_changes": [
            {
                "category": "dataset_contract",
                "sections": [
                    "constants", "verify_frozen_files", "load_dataset",
                    "load_plan", "extract_series_and_time",
                ],
                "description":
                    "F2.2 observational payloads and logical hashes.",
            },
            {
                "category": "observational_metadata",
                "sections": [
                    "plan fields", "SQLite result schema",
                    "result and decision export", "temporal contract",
                ],
                "description":
                    "Event, pair, role, window, profile and FITS-source metadata.",
            },
            {
                "category": "output_naming",
                "sections": [
                    "checkpoint, CSV, audit, report and environment names",
                ],
                "description": "F2.3 observational artifact namespace.",
            },
            {
                "category": "job_counts",
                "sections": [
                    "2784 full rows, 84 canary rows, 31+53+0 resume",
                ],
                "description": "F2.2/F2.3 frozen job counts.",
            },
            {
                "category": "plan_kind_validation",
                "sections": [
                    "literal canary subset and explicit full-plan guard",
                ],
                "description":
                    "Canary accepted by frozen hash; full execution blocked by default.",
            },
        ],
        "scientific_core_checks": scientific_core,
        "scientific_core_modified": False,
    }


def csv_expected_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def compare_results_csv(
    database_rows: list[dict[str, Any]],
    results_path: Path,
) -> int:
    observed = read_csv(results_path)
    expected = [result_export_row(row) for row in database_rows]
    if len(observed) != len(expected):
        return abs(len(observed) - len(expected)) + 1
    mismatches = 0
    for actual, wanted in zip(observed, expected):
        for field in RESULT_FIELDNAMES:
            if actual[field] != csv_expected_cell(wanted[field]):
                mismatches += 1
    return mismatches


def compare_decisions_csv(
    database_rows: list[dict[str, Any]],
    decisions_path: Path,
) -> tuple[int, int]:
    observed = read_csv(decisions_path)
    expected = build_decisions(database_rows)
    if len(observed) != len(expected):
        return abs(len(observed) - len(expected)) + 1, 1
    mismatches = 0
    delta_mismatches = 0
    float_fields = {
        "bic_m0", "bic_m1", "bic_m2",
        "delta_bic_0_1", "delta_bic_2_1",
        "formal_m1_period_s",
    }
    for actual, wanted in zip(observed, expected):
        for field in DECISION_FIELDNAMES:
            left = actual[field]
            right = wanted[field]
            if field in float_fields and left != "" and right != "":
                if not math.isclose(
                    float(left),
                    float(right),
                    rel_tol=0.0,
                    abs_tol=ABS_TOLERANCE,
                ):
                    mismatches += 1
                    if field.startswith("delta_"):
                        delta_mismatches += 1
            elif left != csv_expected_cell(right):
                mismatches += 1
                if field.startswith("delta_"):
                    delta_mismatches += 1
    return mismatches, delta_mismatches


def finalize_canary(
    *,
    checkpoint: Path,
    plan_rows: list[dict[str, Any]],
    dataset: dict[str, Any],
    physical_hashes: dict[str, str],
    logical_hashes: dict[str, str],
    environment: dict[str, Any],
    results_path: Path,
    decisions_path: Path,
    audit_path: Path,
    report_path: Path,
    environment_path: Path,
    replay: dict[str, Any],
) -> dict[str, Any]:
    state = read_checkpoint_audit(checkpoint)
    results = state["results"]
    invocations = state["invocations"]
    duplicates = duplicate_counts(results)
    decisions = build_decisions(results)
    completed_sequence = [
        int(row["committed_new"]) for row in invocations
    ]
    if completed_sequence != [31, 53, 0]:
        raise RuntimeError(
            f"Incorrect resume sequence: {completed_sequence}."
        )
    temporal_mismatches = []
    error_rows_without_temporal_output = []
    for row in results:
        if row["status"] == "OK":
            if not math.isclose(
                float(row["afino_effective_dt_s"]),
                float(row["median_dt_s"]),
                rel_tol=0.0,
                abs_tol=ABS_TOLERANCE,
            ):
                temporal_mismatches.append({
                    "job_id": row["job_id"],
                    "kind": "effective_dt",
                    "expected": row["median_dt_s"],
                    "observed": row["afino_effective_dt_s"],
                })
            if int(row["bins_after_cutoff"]) != int(
                row["expected_post_cutoff_bin_count"]
            ):
                temporal_mismatches.append({
                    "job_id": row["job_id"],
                    "kind": "post_cutoff_bin_count",
                    "expected":
                        row["expected_post_cutoff_bin_count"],
                    "observed": row["bins_after_cutoff"],
                })
        else:
            error_rows_without_temporal_output.append(row["job_id"])
    result_csv_mismatches = compare_results_csv(results, results_path)
    (
        decision_csv_mismatches,
        decision_recalculation_mismatches,
    ) = compare_decisions_csv(results, decisions_path)
    diff_audit = runner_diff_audit()
    post_environment = verify_environment()
    post_physical, post_logical = verify_frozen_files()
    for field in (
        "commit", "afino_version", "python_version",
        "numpy_version", "scipy_version",
    ):
        if post_environment[field] != environment[field]:
            raise RuntimeError(f"Environment changed: {field}.")
    environment_path.write_text(
        environment_text(post_environment),
        encoding="utf-8",
    )
    status_counts = Counter(row["status"] for row in results)
    decision_counts = Counter(
        row["decision_status"] for row in decisions
    )
    structural_pass = (
        len(results) == 84
        and len(decisions) == 28
        and completed_sequence == [31, 53, 0]
        and not any(duplicates.values())
        and replay["passed_count"] == 6
        and not temporal_mismatches
        and result_csv_mismatches == 0
        and decision_csv_mismatches == 0
        and decision_recalculation_mismatches == 0
        and post_physical == physical_hashes
        and post_logical == logical_hashes
        and not diff_audit["scientific_core_modified"]
        and state["metadata"].get("plan_kind") == "canary"
        and state["metadata"].get("full_plan_sha256")
            == EXPECTED_FULL_PLAN_SHA256
        and state["metadata"].get("canary_plan_sha256")
            == EXPECTED_CANARY_PLAN_SHA256
    )
    if structural_pass and status_counts == {"OK": 84}:
        conclusion = (
            "OBSERVATIONAL_RUNNER_VALIDATED_BEFORE_FULL_EXECUTION"
        )
    elif structural_pass:
        conclusion = (
            "OBSERVATIONAL_RUNNER_VALIDATED_WITH_DOCUMENTED_LIMITATION"
        )
    else:
        conclusion = "OBSERVATIONAL_RUNNER_VALIDATION_BLOCKED"

    audit = {
        "date_utc": utc_now(),
        "validation_conclusion": conclusion,
        "runner_family": RUNNER_FAMILY,
        "runner_implementation_version":
            RUNNER_IMPLEMENTATION_VERSION,
        "environment": environment,
        "full_plan_rows": 2784,
        "full_executable_decisions": 928,
        "canary_unique_variants": 16,
        "canary_primary_decisions": 16,
        "canary_stability_decisions": 12,
        "canary_decision_rows": 28,
        "canary_plan_rows": 84,
        "canary_result_rows": len(results),
        "first_pass_completed": 31,
        "second_pass_new": 53,
        "third_pass_new": 0,
        "rows_per_model": 28,
        **duplicates,
        "decision_recalculation_mismatches":
            decision_recalculation_mismatches,
        "exact_replay_passed": replay["passed_count"],
        "preflight": {
            "physical_hashes": physical_hashes,
            "logical_hashes": logical_hashes,
            "payloads_loaded_with_allow_pickle_false": True,
            "persisted_time_and_flux_used_directly": True,
        },
        "postflight": {
            "physical_hashes": post_physical,
            "logical_hashes": post_logical,
            "f2_2_inputs_unchanged": (
                post_physical == physical_hashes
                and post_logical == logical_hashes
            ),
            "tracked_git_diff_empty":
                post_environment["tracked_diff_exit_code"] == 0,
            "staged_git_diff_empty":
                post_environment["staged_diff_exit_code"] == 0,
            "git_status_porcelain":
                post_environment["git_status"],
        },
        "runner_diff": diff_audit,
        "plan": {
            "full_plan_sha256": EXPECTED_FULL_PLAN_SHA256,
            "canary_plan_sha256": EXPECTED_CANARY_PLAN_SHA256,
            "literal_subset": True,
            "unique_variants": 16,
            "primary_decisions": 16,
            "stability_decisions": 12,
            "rows_per_model": {
                "M0": 28, "M1": 28, "M2": 28,
            },
        },
        "canary": {
            "result_status_counts": dict(status_counts),
            "decision_status_counts": dict(decision_counts),
            "temporal_contract_mismatches": temporal_mismatches,
            "error_rows_without_temporal_output":
                error_rows_without_temporal_output,
            "result_csv_sqlite_mismatches":
                result_csv_mismatches,
            "decision_csv_sqlite_mismatches":
                decision_csv_mismatches,
            "canary_results_eligible_for_analysis": False,
        },
        "resume_test": {
            "invocations": invocations,
            "completed_sequence": completed_sequence,
        },
        "exact_replay": replay,
        "checkpoint": {
            "filename": checkpoint.name,
            "sha256": sha256(checkpoint),
            "result_rows": len(results),
            "metadata": state["metadata"],
            "sqlite_transaction_policy":
                "one independent transaction per completed model call",
            "primary_key_job_id": True,
            "unique_variant_seed_model": True,
        },
        "protocol": {
            "low_frequency_cutoff_hz":
                LOW_FREQUENCY_CUTOFF_HZ,
            "models": MODEL_SPECS,
            "M1_bounds": [
                list(bounds) for bounds in OVERWRITE_GAUSS_BOUNDS
            ],
            "seed_reset_before_each_model_call": True,
            "selection_rule":
                "(BIC_M0 - BIC_M1 > 10.0) and "
                "(BIC_M2 - BIC_M1 > 10.0)",
            "convergence_status": "NOT_AUDITABLE",
            "absolute_tolerance": ABS_TOLERANCE,
            "relative_tolerance": 0.0,
        },
        "output_hashes": {
            BUILD_CANARY_SCRIPT.name: sha256(BUILD_CANARY_SCRIPT),
            CANARY_PLAN_CSV.name: sha256(CANARY_PLAN_CSV),
            Path(__file__).resolve().name:
                sha256(Path(__file__).resolve()),
            checkpoint.name: sha256(checkpoint),
            results_path.name: sha256(results_path),
            decisions_path.name: sha256(decisions_path),
            environment_path.name: sha256(environment_path),
        },
        "incidents": [],
        "confirmations": {
            "full_observational_plan_executed": False,
            "fits_opened": False,
            "dataset_regenerated": False,
            "detrending_recomputed": False,
            "quality_filter_reapplied": False,
            "canary_results_used_for_tuning": False,
            "canary_results_eligible_for_analysis": False,
            "candidate_discovery_authorized": False,
            "afino_code_modified": False,
            "scientific_protocol_modified": False,
            "f2_2_plan_modified": False,
            "f2_2_payloads_modified": False,
            "checkpoint_reused": False,
        },
    }

    report = f"""# Fase 2 — Tarea 2.3

## Validación canary del runner observacional checkpointed

**Conclusión:** `{conclusion}`  
**Runner:** `{RUNNER_FAMILY}` `{RUNNER_IMPLEMENTATION_VERSION}`  
**AFINO:** `{environment['commit']}` / `{environment['afino_version']}`  
**Plan completo ejecutado:** no

El canary contiene 84 trabajos y es un subconjunto literal del plan exacto
F2.2: conserva cada `job_id`, todos los campos científicos y el `job_order`
original, añadiendo únicamente `canary_order`. Sus 16 variantes únicas
producen 28 decisiones: 16 primarias y 12 de estabilidad, con 28 filas para
cada uno de M0, M1 y M2.

La pareja P3 en W00 cubre P00–P05 para ambos miembros y para las seeds 0 y 1.
Por tanto, el canary incluye PDCSAP, SAP, `finite_all`, `q0_native`, ausencia
de detrending y `linear_residual_plus_one`, además de las dos clases
observacionales y de decisiones primarias y de estabilidad. Las cuatro
decisiones P2 en WX2 incorporan una ventana perturbada, inputs más largos y
detrending fuera del baseline.

El runner cargó exclusivamente los cuatro payloads F2.2 mediante
`np.load(..., allow_pickle=False)`. Para cada trabajo utilizó directamente
los slices persistidos de tiempo y flujo. Los índices FITS solo se emplearon
para comprobar hashes y consecutividad. No se abrió ningún FITS, no se
reaplicó QUALITY, no se repitió detrending y no se reconstruyeron,
normalizaron, interpolaron o rellenaron curvas.

La interrupción ocurrió después de 31 transacciones confirmadas, dejando 53
trabajos pendientes y una decisión con trío incompleto. La segunda pasada
conservó las 31 filas y añadió exactamente 53. La tercera encontró 84
resultados existentes, ejecutó cero llamadas nuevas y exportó desde SQLite.
No aparecieron `job_id` ni claves científicas duplicadas.

El contrato temporal se calculó independientemente desde cada tiempo
persistido. Para los resultados OK, `afino_effective_dt_s` coincidió con la
mediana de los intervalos con tolerancia absoluta de 5×10⁻¹² s, y el número
de bins tras el cutoff coincidió con el conteo derivado de las frecuencias
FFT y el límite congelado de 1/40 Hz. SQLite y los dos CSV coincidieron, y los
deltas BIC se recalcularon sin discrepancias.

Los seis replays externos al checkpoint —M0, M1 y M2 para F2D000471 y
F2D000461— coincidieron exactamente en estado, BIC, log-likelihood,
parámetros, periodo formal de M1, rchi2, probabilidad, warnings, bounds,
cadencia efectiva, bins y error.

El diff frente al runner 1.1.0 clasificó los cambios únicamente como
`dataset_contract`, `observational_metadata`, `output_naming`, `job_counts`
y `plan_kind_validation`. La importación y llamadas AFINO, modelos, bounds,
cutoff, reinicio de semillas, warnings, diagnóstico de bounds, serialización,
regla doble BIC, transacción por llamada y lógica base de replay permanecieron
intactos.

Los resultados canary no son elegibles para analizar robustez ni para ajustar
perfiles, ventanas, umbrales o cohorte. El plan completo de 2.784 llamadas
permanece sin ejecutar.

`{conclusion}`
"""
    report_word_count = len(
        re.findall(
            r"\b[\wÁÉÍÓÚÜÑáéíóúüñ]+\b",
            report,
        )
    )
    if not 400 <= report_word_count <= 650:
        raise RuntimeError(
            f"Report word count {report_word_count} outside 400-650."
        )
    audit["report_word_count"] = report_word_count
    audit_path.write_text(
        json.dumps(
            audit,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(report, encoding="utf-8")
    return audit


# =============================================================================
# CLI
# =============================================================================


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Checkpointed observational AFINO runner for F2.3/F2.4."
        )
    )
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--stop-after", type=int)
    parser.add_argument("--export", type=Path)
    parser.add_argument("--decisions", type=Path)
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--finalize-canary", action="store_true")
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--environment",
        type=Path,
        default=DEFAULT_ENVIRONMENT,
    )
    parser.add_argument("--allow-full-plan", action="store_true")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help=(
            "Verify environment, frozen inputs, literal plan and "
            "scientific-core diff without creating a checkpoint or "
            "calling AFINO."
        ),
    )
    return parser


def resolve_under_root(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan_path = resolve_under_root(args.plan)
    checkpoint = resolve_under_root(args.checkpoint)
    export_path = (
        resolve_under_root(args.export) if args.export else None
    )
    decisions_path = (
        resolve_under_root(args.decisions)
        if args.decisions else None
    )
    audit_path = resolve_under_root(args.audit)
    report_path = resolve_under_root(args.report)
    environment_path = resolve_under_root(args.environment)
    if args.finalize_canary and (
        export_path is None or decisions_path is None
    ):
        raise RuntimeError(
            "--finalize-canary requires --export and --decisions."
        )
    if args.finalize_canary and not args.replay:
        raise RuntimeError("--finalize-canary requires --replay.")
    if args.preflight_only and any((
        args.resume,
        args.stop_after is not None,
        args.export is not None,
        args.decisions is not None,
        args.replay,
        args.finalize_canary,
        args.allow_full_plan,
    )):
        raise RuntimeError(
            "--preflight-only cannot be combined with execution, export, "
            "replay, finalization or full-plan authorization."
        )
    print("F2.3 — OBSERVATIONAL AFINO CHECKPOINTED RUNNER", flush=True)
    print(f"Runner family: {RUNNER_FAMILY}", flush=True)
    print(
        f"Runner implementation: {RUNNER_IMPLEMENTATION_VERSION}",
        flush=True,
    )
    environment = verify_environment()
    physical_hashes, logical_hashes = verify_frozen_files()
    dataset = load_dataset()
    plan_rows, plan_kind = load_plan(plan_path, dataset)
    if args.finalize_canary and plan_kind != "canary":
        raise RuntimeError("F2.3 finalization only accepts the canary.")
    runner_sha = sha256(Path(__file__).resolve())
    print(f"Runner SHA-256: {runner_sha}", flush=True)
    print(
        f"Plan: {plan_path.name} ({plan_kind}, "
        f"{len(plan_rows)} rows)",
        flush=True,
    )
    print("F2.2 physical and logical hashes: verified", flush=True)
    print(f"AFINO commit: {environment['commit']}", flush=True)
    print(f"AFINO version: {environment['afino_version']}", flush=True)
    diff_audit = runner_diff_audit()
    print(
        "Scientific core against F1.11: verified unchanged",
        flush=True,
    )
    print(
        f"Reference runner selected: {diff_audit['reference_runner']}",
        flush=True,
    )
    if args.preflight_only:
        if plan_kind != "canary":
            raise RuntimeError(
                "F2.3 preflight accepts only the frozen canary plan."
            )
        print(
            "F2.3 COMPREHENSIVE PREFLIGHT COMPLETE — NO AFINO CALLS",
            flush=True,
        )
        return 0
    run_plan(
        plan_path=plan_path,
        plan_rows=plan_rows,
        plan_kind=plan_kind,
        checkpoint=checkpoint,
        resume=args.resume,
        stop_after=args.stop_after,
        dataset=dataset,
        runner_sha256=runner_sha,
        physical_hashes=physical_hashes,
        logical_hashes=logical_hashes,
        allow_full_plan=args.allow_full_plan,
    )
    result_rows: list[dict[str, Any]] | None = None
    if export_path is not None:
        result_rows = export_results(
            checkpoint,
            plan_rows,
            export_path,
        )
        print(
            f"Exported {len(result_rows)} results to "
            f"{export_path.name}"
        )
    if decisions_path is not None:
        if result_rows is None:
            result_rows = fetch_results_for_plan(
                checkpoint,
                plan_rows,
            )
        decisions = export_decisions(
            result_rows,
            decisions_path,
        )
        print(
            f"Exported {len(decisions)} decisions to "
            f"{decisions_path.name}"
        )
    replay_result: dict[str, Any] | None = None
    if args.replay:
        replay_result = run_replays(
            checkpoint,
            plan_rows,
            dataset,
        )
        print(
            "Exact replays: "
            f"{replay_result['passed_count']}/"
            f"{replay_result['expected_count']}"
        )
    if args.finalize_canary:
        if (
            result_rows is None
            or replay_result is None
            or export_path is None
            or decisions_path is None
        ):
            raise RuntimeError("Incomplete state for finalization.")
        audit = finalize_canary(
            checkpoint=checkpoint,
            plan_rows=plan_rows,
            dataset=dataset,
            physical_hashes=physical_hashes,
            logical_hashes=logical_hashes,
            environment=environment,
            results_path=export_path,
            decisions_path=decisions_path,
            audit_path=audit_path,
            report_path=report_path,
            environment_path=environment_path,
            replay=replay_result,
        )
        print(f"Conclusion: {audit['validation_conclusion']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"OBSERVATIONAL_RUNNER_VALIDATION_BLOCKED: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise
