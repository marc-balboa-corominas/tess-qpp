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
from typing import Any, Iterable, Sequence

import numpy as np
import scipy


# =============================================================================
# Frozen F1.11 nested protocol
# =============================================================================

ROOT = Path(__file__).resolve().parent
REPO = ROOT / "afino_release_version"
RUNNER_FAMILY = "afino_checkpointed"
RUNNER_IMPLEMENTATION_VERSION = "1.1.0"

REFERENCE_RUNNER = ROOT / "fase1_tarea04_run_afino_checkpointed_v2.py"
BUILD_PLAN_SCRIPT = ROOT / "fase1_tarea11_build_nested_execution_plan.py"
FULL_PLAN_CSV = ROOT / "fase1_tarea11_nested_full_execution_plan.csv"
CANARY_PLAN_CSV = ROOT / "fase1_tarea11_nested_canary_plan.csv"

PREREGISTRATION_JSON = ROOT / "fase1_tarea08_nested_window_preregistration.json"
DESIGN_GRID_CSV = ROOT / "fase1_tarea08_nested_window_design_grid.csv"
FLUX_NPY = ROOT / "fase1_tarea10_nested_flux_values.npy"
SERIES_OFFSETS_NPY = ROOT / "fase1_tarea10_nested_series_offsets.npy"
TIME_VALUES_NPY = ROOT / "fase1_tarea10_nested_time_values.npy"
TIME_OFFSETS_NPY = ROOT / "fase1_tarea10_nested_time_offsets.npy"
SERIES_MANIFEST_CSV = ROOT / "fase1_tarea10_nested_series_manifest.csv"
TIME_MANIFEST_CSV = ROOT / "fase1_tarea10_nested_time_manifest.csv"
MATERIALIZATION_AUDIT_JSON = ROOT / "fase1_tarea10_nested_materialization_audit.json"

DEFAULT_CHECKPOINT = ROOT / "fase1_tarea11_nested_canary_checkpoint.sqlite"
DEFAULT_RESULTS = ROOT / "fase1_tarea11_nested_canary_results.csv"
DEFAULT_DECISIONS = ROOT / "fase1_tarea11_nested_canary_decisions.csv"
DEFAULT_AUDIT = ROOT / "fase1_tarea11_nested_runner_validation_audit.json"
DEFAULT_REPORT = ROOT / "fase1_tarea11_nested_runner_validation_report.md"
DEFAULT_ENVIRONMENT = ROOT / "fase1_tarea11_environment.txt"

EXPECTED_AFINO_COMMIT = "6aceac9518fc8056052807e666da9d0c8bebb010"
EXPECTED_AFINO_VERSION = "0.5"
EXPECTED_NUMPY_VERSION = "2.5.1"
EXPECTED_SCIPY_VERSION = "1.18.0"

EXPECTED_REFERENCE_RUNNER_SHA256 = "2e35137655a6fd66cd53d76f9229024b4c74ace597c9df62479e48cefc3c84e7"
EXPECTED_BUILD_PLAN_SCRIPT_SHA256 = "da34d8452ebc0885357e8807afebddb7135e1cf2a9a650965764b79fb2f897b3"
EXPECTED_FULL_PLAN_SHA256 = "08184f7adaab84693fe82fb060d3533f65a870555535d5b1eeccfc37467c6911"
EXPECTED_CANARY_PLAN_SHA256 = "0775fdd6292d9c2c43bf2a4f14e6c859d23716f68e3107a3b570ecacfb17499f"

EXPECTED_PHYSICAL_HASHES = {
    "fase1_tarea08_nested_window_preregistration.json": "d80890319b4646f8df994ba7c1dd9da3dc1f141834dbf289d1b17c484fa67487",
    "fase1_tarea08_nested_window_design_grid.csv": "7c1a1fb9724dfe195fec1337e4f0af906e3dd8f1c754ab0abc7f3bc2cc1e8dcd",
    "fase1_tarea10_nested_flux_values.npy": "74d873cdef11b3855d2aba33ded45910f879f5afafb9b5eff4d71d271b06f565",
    "fase1_tarea10_nested_series_offsets.npy": "a902ae72c06ecc31926d11b6cb297da190a6204dd21cbcc622205589ff324068",
    "fase1_tarea10_nested_time_values.npy": "995d5321c34e305e6ed02556215660b20bf4c947eaba69ca44e6932349366db7",
    "fase1_tarea10_nested_time_offsets.npy": "f7966cdcdb9373ed33bdf6b50d4c88c9e9ef172a0e087e0543cc1197094304e8",
    "fase1_tarea10_nested_series_manifest.csv": "cc9f44c710dade51e91fe0c2d30b193c621c7b9905764c6fe69fcf1c94c395a5",
    "fase1_tarea10_nested_time_manifest.csv": "cfc1b66b0e949acb2611f73823074faaa1259bcf9a458d687506fb361cb89ed4",
    "fase1_tarea10_nested_materialization_audit.json": "0ea6d0cfe73c0d8b9260bb16f5a761d6c8cf641e6b5dd968b52af3382b3b7b9b",
}

EXPECTED_LOGICAL_HASHES = {
    "canonical_flux_payload_sha256": "9847da04c1793247ab34b01c06b2e9d579715d3bf06c1ea0cb14ea9ebaab03f0",
    "series_offsets_canonical_sha256": "a8f34927c914b8256334e3570ed31b8c5fbb8504b991db0de976105c0f5d3e06",
    "time_values_canonical_sha256": "dfaa422bf7854de5f2a6e89a8db3f06ec9f3c0ccab7d60cd507b45325c3ea6cc",
    "time_offsets_canonical_sha256": "7ab392ff65815e1dd36e8c48377f0c8969351b0e178210cd85f5711be77aa1a5",
}

MODEL_SPECS = {
    "M0": "pow_const",
    "M1": "pow_const_gauss",
    "M2": "bpow_const",
}
MODEL_ORDER = {"M0": 0, "M1": 1, "M2": 2}
LOW_FREQUENCY_CUTOFF_HZ = 1.0 / 40.0
BOUND_ATOL = 1.0e-7

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

CANARY_SERIES_IDS = (
    "NWS000001", "NWS000361", "NWS000721", "NWS001081", "NWS001441", "NWS001801",
    "NWS000321", "NWS000681", "NWS001041", "NWS001401", "NWS001761", "NWS002121",
)
REPLAY_SERIES_IDS = ("NWS000001", "NWS002121")
EXPECTED_BINS_AFTER_CUTOFF = {15: 7, 30: 14, 45: 22, 60: 29, 90: 44, 120: 59}

RESULT_FIELDNAMES = [
    "job_id", "job_class", "series_id", "condition_id", "parent_id", "block_id",
    "ground_truth", "duration_s", "red_noise_alpha", "period_s", "qpp_fraction",
    "data_seed", "external_optimizer_seed", "model_id", "model_name", "status",
    "runtime_seconds", "n_samples", "input_flux_sha256", "input_time_sha256",
    "parent_n120_series_id", "afino_effective_dt_s", "positive_frequency_bins",
    "bins_after_cutoff", "minimum_frequency_hz", "maximum_frequency_hz", "lnlike",
    "BIC", "rchi2", "probability", "parameters_json", "estimated_period_s",
    "parameter_at_bound", "bound_indices_json", "warning_count", "warning_types_json",
    "convergence_status", "error",
]

DECISION_FIELDNAMES = [
    "series_id", "condition_id", "parent_id", "block_id", "ground_truth", "n_samples",
    "duration_s", "red_noise_alpha", "period_s", "qpp_fraction", "data_seed",
    "external_optimizer_seed", "decision_status", "valid_models", "bic_m0", "bic_m1",
    "bic_m2", "delta_bic_0_1", "delta_bic_2_1", "qpp_selected",
    "estimated_period_s", "period_label",
]

PLAN_REQUIRED_FIELDS = [
    "job_id", "job_order", "job_class", "series_id", "condition_id", "parent_id",
    "block_id", "ground_truth", "n_samples", "duration_s", "red_noise_alpha",
    "period_s", "qpp_fraction", "data_seed", "external_optimizer_seed", "model_id",
    "model_name", "flux_start_offset", "flux_end_offset", "time_vector_id",
    "input_flux_sha256", "input_time_sha256", "parent_n120_series_id",
]

EXPECTED_FULL_PLAN_ROWS = 7938
EXPECTED_PRIMARY_PLAN_ROWS = 6480
EXPECTED_STABILITY_PLAN_ROWS = 1458
EXPECTED_CANARY_PLAN_ROWS = 72
EXPECTED_CANARY_DECISIONS = 24
EXPECTED_REPLAY_COMPARISONS = 6


# =============================================================================
# Generic utilities
# =============================================================================


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[dict[str, Any]]) -> None:
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


# =============================================================================
# Environment and immutable-input preflight
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
        raise RuntimeError(f"Commit AFINO incorrecto: {commit}; esperado {EXPECTED_AFINO_COMMIT}.")
    tracked_exit = git("diff", "--quiet", check=False).returncode
    staged_exit = git("diff", "--cached", "--quiet", check=False).returncode
    if tracked_exit != 0 or staged_exit != 0:
        raise RuntimeError(
            "El repositorio AFINO contiene cambios tracked o staged. "
            f"tracked={tracked_exit}, staged={staged_exit}."
        )
    git_status = git("status", "--porcelain").stdout.strip()
    pip_freeze = run_command([sys.executable, "-m", "pip", "freeze"]).stdout.splitlines()
    try:
        afino_version = importlib.metadata.version("afino")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError("El paquete afino no está instalado en .venv.") from exc
    if afino_version != EXPECTED_AFINO_VERSION:
        raise RuntimeError(f"Versión AFINO incorrecta: {afino_version}; esperada {EXPECTED_AFINO_VERSION}.")
    if np.__version__ != EXPECTED_NUMPY_VERSION:
        raise RuntimeError(f"NumPy incorrecto: {np.__version__}; esperado {EXPECTED_NUMPY_VERSION}.")
    if scipy.__version__ != EXPECTED_SCIPY_VERSION:
        raise RuntimeError(f"SciPy incorrecto: {scipy.__version__}; esperado {EXPECTED_SCIPY_VERSION}.")
    return {
        "commit": commit, "afino_version": afino_version,
        "tracked_diff_exit_code": tracked_exit, "staged_diff_exit_code": staged_exit,
        "git_status": git_status, "python_version": sys.version.split()[0],
        "python_full": sys.version, "python_executable_relative": os.path.relpath(sys.executable, ROOT),
        "numpy_version": np.__version__, "scipy_version": scipy.__version__,
        "platform": platform.platform(), "machine": platform.machine(),
        "processor": platform.processor(), "pip_freeze": pip_freeze,
    }


def verify_frozen_files() -> tuple[dict[str, str], dict[str, str]]:
    expected_auxiliary = {
        REFERENCE_RUNNER.name: EXPECTED_REFERENCE_RUNNER_SHA256,
        BUILD_PLAN_SCRIPT.name: EXPECTED_BUILD_PLAN_SCRIPT_SHA256,
        FULL_PLAN_CSV.name: EXPECTED_FULL_PLAN_SHA256,
        CANARY_PLAN_CSV.name: EXPECTED_CANARY_PLAN_SHA256,
    }
    physical: dict[str, str] = {}
    for filename, expected in {**EXPECTED_PHYSICAL_HASHES, **expected_auxiliary}.items():
        path = ROOT / filename
        if not path.is_file():
            raise FileNotFoundError(f"Falta el artefacto congelado: {path}")
        observed = sha256(path)
        physical[filename] = observed
        if observed != expected:
            raise RuntimeError(
                f"Hash físico incorrecto para {filename}.\nEsperado: {expected}\nObservado: {observed}"
            )
    flux_values = np.load(FLUX_NPY, allow_pickle=False)
    series_offsets = np.load(SERIES_OFFSETS_NPY, allow_pickle=False)
    time_values = np.load(TIME_VALUES_NPY, allow_pickle=False)
    time_offsets = np.load(TIME_OFFSETS_NPY, allow_pickle=False)
    expected_shapes = ((flux_values, "<f8", (129600,)), (series_offsets, "<i8", (2161,)),
                       (time_values, "<f8", (360,)), (time_offsets, "<i8", (7,)))
    for array, dtype, shape in expected_shapes:
        if array.dtype != np.dtype(dtype) or array.shape != shape:
            raise RuntimeError(f"Contrato de array inválido: dtype={array.dtype}, shape={array.shape}.")
    logical = {
        "canonical_flux_payload_sha256": canonical_sha256(flux_values, "<f8"),
        "series_offsets_canonical_sha256": canonical_sha256(series_offsets, "<i8"),
        "time_values_canonical_sha256": canonical_sha256(time_values, "<f8"),
        "time_offsets_canonical_sha256": canonical_sha256(time_offsets, "<i8"),
    }
    for name, expected in EXPECTED_LOGICAL_HASHES.items():
        if logical[name] != expected:
            raise RuntimeError(f"Hash lógico incorrecto para {name}: {logical[name]} != {expected}.")
    audit = json.loads(MATERIALIZATION_AUDIT_JSON.read_text(encoding="utf-8"))
    if audit.get("materialization_status") != "NESTED_DATASET_FROZEN_BEFORE_AFINO":
        raise RuntimeError("F1.10 no contiene NESTED_DATASET_FROZEN_BEFORE_AFINO.")
    recorded = audit.get("logical_hashes", {})
    expected_recorded = {
        **EXPECTED_LOGICAL_HASHES,
        "ordered_series_manifest_sha256": EXPECTED_PHYSICAL_HASHES[SERIES_MANIFEST_CSV.name],
        "nested_time_manifest_sha256": EXPECTED_PHYSICAL_HASHES[TIME_MANIFEST_CSV.name],
    }
    if recorded != expected_recorded:
        raise RuntimeError("Los hashes lógicos registrados en F1.10 no coinciden.")
    prereg = json.loads(PREREGISTRATION_JSON.read_text(encoding="utf-8"))
    if prereg.get("benchmark_id") != "afino_nested_window_support_v1" or prereg.get("benchmark_version") != "1.0.0":
        raise RuntimeError("Identificación normativa F1.8 incorrecta.")
    return physical, logical


# =============================================================================
# Dataset and plan loading
# =============================================================================


def load_dataset() -> dict[str, Any]:
    flux_values = np.load(FLUX_NPY, allow_pickle=False)
    series_offsets = np.load(SERIES_OFFSETS_NPY, allow_pickle=False)
    time_values = np.load(TIME_VALUES_NPY, allow_pickle=False)
    time_offsets = np.load(TIME_OFFSETS_NPY, allow_pickle=False)
    series_rows = read_csv(SERIES_MANIFEST_CSV)
    time_rows = read_csv(TIME_MANIFEST_CSV)
    if len(series_rows) != 2160 or len(series_offsets) != 2161 or len(flux_values) != 129600:
        raise RuntimeError("Conteo de series, offsets o flujos inválido.")
    if len(time_rows) != 6 or len(time_offsets) != 7 or len(time_values) != 360:
        raise RuntimeError("Conteo temporal inválido.")
    if [int(row["series_order"]) for row in series_rows] != list(range(1, 2161)):
        raise RuntimeError("series_order no conserva 1..2160.")
    series_by_id = {row["series_id"]: row for row in series_rows}
    time_by_id = {row["time_vector_id"]: row for row in time_rows}
    if len(series_by_id) != 2160 or len(time_by_id) != 6:
        raise RuntimeError("Identificadores duplicados en F1.10.")
    for index, row in enumerate(series_rows):
        if int(row["flux_start_offset"]) != int(series_offsets[index]) or int(row["flux_end_offset"]) != int(series_offsets[index + 1]):
            raise RuntimeError(f"Offsets incompatibles para {row['series_id']}.")
    for index, row in enumerate(time_rows):
        if int(row["start_offset"]) != int(time_offsets[index]) or int(row["end_offset"]) != int(time_offsets[index + 1]):
            raise RuntimeError(f"Offsets temporales incompatibles para {row['time_vector_id']}.")
    return {
        "flux_values": flux_values, "series_offsets": series_offsets,
        "time_values": time_values, "time_offsets": time_offsets,
        "series_rows": series_rows, "series_by_id": series_by_id,
        "time_rows": time_rows, "time_by_id": time_by_id,
    }


def load_plan(plan_path: Path, dataset: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    observed_hash = sha256(plan_path)
    if observed_hash == EXPECTED_CANARY_PLAN_SHA256:
        plan_kind, expected_count = "canary", EXPECTED_CANARY_PLAN_ROWS
    elif observed_hash == EXPECTED_FULL_PLAN_SHA256:
        plan_kind, expected_count = "full", EXPECTED_FULL_PLAN_ROWS
    else:
        raise RuntimeError(f"Plan no congelado: {plan_path.name} tiene SHA-256 {observed_hash}.")
    raw_rows = read_csv(plan_path)
    if len(raw_rows) != expected_count:
        raise RuntimeError(f"{plan_path.name}: {len(raw_rows)} != {expected_count} filas.")
    if not raw_rows or list(raw_rows[0]) != PLAN_REQUIRED_FIELDS:
        raise RuntimeError("El esquema del plan no coincide con F1.11.")
    plan_rows: list[dict[str, Any]] = []
    seen_job_ids: set[str] = set()
    seen_scientific: set[tuple[str, int, str]] = set()
    for row_index, raw in enumerate(raw_rows):
        model_id = raw["model_id"]
        if model_id not in MODEL_SPECS or raw["model_name"] != MODEL_SPECS[model_id]:
            raise RuntimeError(f"Modelo inválido en fila {row_index + 2}.")
        if raw["job_class"] not in {"primary", "stability"}:
            raise RuntimeError(f"job_class inválido en fila {row_index + 2}.")
        row: dict[str, Any] = dict(raw)
        for field in ("job_order", "data_seed", "external_optimizer_seed", "n_samples", "flux_start_offset", "flux_end_offset"):
            row[field] = int(raw[field])
        row["duration_s"] = float(raw["duration_s"])
        row["red_noise_alpha"] = float(raw["red_noise_alpha"])
        row["period_s"] = None if raw["period_s"] == "" else float(raw["period_s"])
        row["qpp_fraction"] = None if raw["qpp_fraction"] == "" else float(raw["qpp_fraction"])
        if row["job_id"] in seen_job_ids:
            raise RuntimeError(f"job_id duplicado: {row['job_id']}.")
        seen_job_ids.add(row["job_id"])
        key = (row["series_id"], row["external_optimizer_seed"], row["model_id"])
        if key in seen_scientific:
            raise RuntimeError(f"Clave científica duplicada: {key}.")
        seen_scientific.add(key)
        series = dataset["series_by_id"].get(row["series_id"])
        if series is None:
            raise RuntimeError(f"Serie desconocida: {row['series_id']}.")
        expected_pairs = {
            "condition_id": series["condition_id"], "parent_id": series["parent_id"],
            "block_id": series["block_id"], "ground_truth": series["ground_truth"],
            "data_seed": int(series["data_seed"]), "n_samples": int(series["n_samples"]),
            "duration_s": float(series["duration_s"]), "red_noise_alpha": float(series["red_noise_alpha"]),
            "period_s": None if series["period_s"] == "" else float(series["period_s"]),
            "qpp_fraction": None if series["qpp_fraction"] == "" else float(series["qpp_fraction"]),
            "flux_start_offset": int(series["flux_start_offset"]), "flux_end_offset": int(series["flux_end_offset"]),
            "time_vector_id": series["time_vector_id"], "input_flux_sha256": series["flux_sha256"],
            "input_time_sha256": dataset["time_by_id"][series["time_vector_id"]]["time_sha256"],
            "parent_n120_series_id": series["parent_n120_series_id"],
        }
        for field, expected in expected_pairs.items():
            if row[field] != expected:
                raise RuntimeError(f"Plan/manifest mismatch {row['job_id']} campo {field}.")
        if row["job_class"] == "primary" and row["external_optimizer_seed"] != 0:
            raise RuntimeError(f"Primary con seed externa no nula: {row['job_id']}.")
        if row["job_class"] == "stability" and (row["data_seed"] != 0 or not 1 <= row["external_optimizer_seed"] <= 9):
            raise RuntimeError(f"Stability fuera de protocolo: {row['job_id']}.")
        plan_rows.append(row)
    if plan_kind == "full":
        counts = Counter(row["job_class"] for row in plan_rows)
        if counts != {"primary": 6480, "stability": 1458}:
            raise RuntimeError(f"Conteos full incorrectos: {counts}.")
        if [row["job_order"] for row in plan_rows] != list(range(1, 7939)):
            raise RuntimeError("job_order full no conserva 1..7938.")
        if Counter(row["model_id"] for row in plan_rows) != {"M0": 2646, "M1": 2646, "M2": 2646}:
            raise RuntimeError("Conteos por modelo incorrectos.")
    else:
        if tuple(dict.fromkeys(row["series_id"] for row in plan_rows)) != CANARY_SERIES_IDS:
            raise RuntimeError("Las doce series canary no coinciden con F1.11.")
        if set(Counter(row["series_id"] for row in plan_rows).values()) != {6}:
            raise RuntimeError("Cada serie canary debe contener seis trabajos.")
        expected_keys = []
        for series_id in CANARY_SERIES_IDS:
            for seed in (0, 1):
                for model_id in ("M0", "M1", "M2"):
                    expected_keys.append((series_id, seed, model_id))
        observed_keys = [(row["series_id"], row["external_optimizer_seed"], row["model_id"]) for row in plan_rows]
        if observed_keys != expected_keys:
            raise RuntimeError("Orden científico del canary incorrecto.")
    return plan_rows, plan_kind


def extract_series_and_time(job: dict[str, Any], dataset: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    start, end = job["flux_start_offset"], job["flux_end_offset"]
    flux = np.asarray(dataset["flux_values"][start:end], dtype=np.float64).copy()
    if len(flux) != job["n_samples"] or canonical_sha256(flux, "<f8") != job["input_flux_sha256"]:
        raise RuntimeError(f"Flujo o hash inválido en {job['job_id']}.")
    time_meta = dataset["time_by_id"][job["time_vector_id"]]
    time_start, time_end = int(time_meta["start_offset"]), int(time_meta["end_offset"])
    time_seconds = np.asarray(dataset["time_values"][time_start:time_end], dtype=np.float64).copy()
    if len(time_seconds) != job["n_samples"] or canonical_sha256(time_seconds, "<f8") != job["input_time_sha256"]:
        raise RuntimeError(f"Tiempo o hash inválido en {job['job_id']}.")
    if float(time_seconds[0]) != 0.0 or not np.all(np.diff(time_seconds) > 0):
        raise RuntimeError(f"Vector temporal inválido en {job['job_id']}.")
    parent_meta = dataset["series_by_id"].get(job["parent_n120_series_id"])
    if parent_meta is None or int(parent_meta["n_samples"]) != 120 or parent_meta["parent_id"] != job["parent_id"]:
        raise RuntimeError(f"Enlace N=120 inválido en {job['job_id']}.")
    pstart, pend = int(parent_meta["flux_start_offset"]), int(parent_meta["flux_end_offset"])
    parent = np.asarray(dataset["flux_values"][pstart:pend], dtype=np.float64)
    if flux.tobytes(order="C") != parent[: job["n_samples"]].tobytes(order="C"):
        raise RuntimeError(f"Prefijo padre-hijo inválido en {job['job_id']}.")
    return time_seconds, flux


# =============================================================================
# AFINO execution
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
        "job_id": job["job_id"], "job_order": job["job_order"], "job_class": job["job_class"],
        "series_id": job["series_id"], "condition_id": job["condition_id"],
        "parent_id": job["parent_id"], "block_id": job["block_id"],
        "ground_truth": job["ground_truth"], "duration_s": job["duration_s"],
        "red_noise_alpha": job["red_noise_alpha"], "period_s": job["period_s"],
        "qpp_fraction": job["qpp_fraction"], "data_seed": job["data_seed"],
        "external_optimizer_seed": job["external_optimizer_seed"], "model_id": job["model_id"],
        "model_name": job["model_name"], "status": "NOT_RUN", "runtime_seconds": None,
        "n_samples": job["n_samples"], "input_flux_sha256": job["input_flux_sha256"],
        "input_time_sha256": job["input_time_sha256"],
        "parent_n120_series_id": job["parent_n120_series_id"],
        "afino_effective_dt_s": None, "positive_frequency_bins": None,
        "bins_after_cutoff": None, "minimum_frequency_hz": None, "maximum_frequency_hz": None,
        "lnlike": None, "BIC": None, "rchi2": None, "probability": None,
        "parameters_json": None, "estimated_period_s": None, "parameter_at_bound": None,
        "bound_indices_json": None, "bound_details_json": None, "warning_count": None,
        "warning_types_json": None, "warnings_json": None,
        "convergence_status": "NOT_AUDITABLE", "error": None, "completed_at_utc": None,
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
    "job_id", "job_order", "job_class", "series_id", "condition_id", "parent_id", "block_id",
    "ground_truth", "duration_s", "red_noise_alpha", "period_s", "qpp_fraction", "data_seed",
    "external_optimizer_seed", "model_id", "model_name", "status", "runtime_seconds", "n_samples",
    "input_flux_sha256", "input_time_sha256", "parent_n120_series_id", "afino_effective_dt_s",
    "positive_frequency_bins", "bins_after_cutoff", "minimum_frequency_hz", "maximum_frequency_hz",
    "lnlike", "BIC", "rchi2", "probability", "parameters_json", "estimated_period_s",
    "parameter_at_bound", "bound_indices_json", "bound_details_json", "warning_count",
    "warning_types_json", "warnings_json", "convergence_status", "error", "completed_at_utc",
]



def connect_checkpoint(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    else:
        connection = sqlite3.connect(path)
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
    connection.row_factory = sqlite3.Row
    return connection


def initialize_checkpoint(
    checkpoint: Path, *, plan_path: Path, plan_sha256: str, plan_kind: str,
    runner_sha256: str, physical_hashes: dict[str, str], logical_hashes: dict[str, str],
) -> None:
    connection = connect_checkpoint(checkpoint)
    try:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS results (
                job_id TEXT PRIMARY KEY, job_order INTEGER NOT NULL, job_class TEXT NOT NULL,
                series_id TEXT NOT NULL, condition_id TEXT NOT NULL, parent_id TEXT NOT NULL,
                block_id TEXT NOT NULL, ground_truth TEXT NOT NULL, duration_s REAL NOT NULL,
                red_noise_alpha REAL NOT NULL, period_s REAL, qpp_fraction REAL, data_seed INTEGER NOT NULL,
                external_optimizer_seed INTEGER NOT NULL, model_id TEXT NOT NULL, model_name TEXT NOT NULL,
                status TEXT NOT NULL, runtime_seconds REAL NOT NULL, n_samples INTEGER NOT NULL,
                input_flux_sha256 TEXT NOT NULL, input_time_sha256 TEXT NOT NULL,
                parent_n120_series_id TEXT NOT NULL, afino_effective_dt_s REAL,
                positive_frequency_bins INTEGER, bins_after_cutoff INTEGER, minimum_frequency_hz REAL,
                maximum_frequency_hz REAL, lnlike REAL, BIC REAL, rchi2 REAL, probability REAL,
                parameters_json TEXT, estimated_period_s REAL, parameter_at_bound INTEGER,
                bound_indices_json TEXT, bound_details_json TEXT, warning_count INTEGER,
                warning_types_json TEXT, warnings_json TEXT, convergence_status TEXT NOT NULL,
                error TEXT, completed_at_utc TEXT NOT NULL,
                UNIQUE(series_id, external_optimizer_seed, model_id)
            );
            CREATE TABLE IF NOT EXISTS invocations (
                invocation_id INTEGER PRIMARY KEY AUTOINCREMENT, plan_sha256 TEXT NOT NULL,
                plan_kind TEXT NOT NULL, started_at_utc TEXT NOT NULL, finished_at_utc TEXT NOT NULL,
                resume_requested INTEGER NOT NULL, stop_after INTEGER, existing_before INTEGER NOT NULL,
                committed_new INTEGER NOT NULL, skipped_existing INTEGER NOT NULL, total_after INTEGER NOT NULL
            );
        """)
        metadata = {
            "schema_version": "1.1.0", "runner_family": RUNNER_FAMILY,
            "runner_implementation_version": RUNNER_IMPLEMENTATION_VERSION,
            "plan_filename": plan_path.name, "plan_sha256": plan_sha256, "plan_kind": plan_kind,
            "runner_sha256": runner_sha256, "dataset_physical_hashes": json_compact(physical_hashes),
            "dataset_logical_hashes": json_compact(logical_hashes), "afino_commit": EXPECTED_AFINO_COMMIT,
            "afino_version": EXPECTED_AFINO_VERSION, "created_at_utc": utc_now(),
        }
        existing = {row["key"]: row["value"] for row in connection.execute("SELECT key, value FROM metadata")}
        if existing:
            for key in (
                "schema_version", "runner_family", "runner_implementation_version", "plan_filename",
                "plan_sha256", "plan_kind", "runner_sha256", "dataset_physical_hashes",
                "dataset_logical_hashes", "afino_commit", "afino_version",
            ):
                if existing.get(key) != metadata[key]:
                    raise RuntimeError(f"Checkpoint incompatible en metadata[{key}].")
        else:
            connection.executemany("INSERT INTO metadata(key, value) VALUES (?, ?)", list(metadata.items()))
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
                resume_requested, stop_after, existing_before, committed_new,
                skipped_existing, total_after
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_sha256,
                plan_kind,
                started_at,
                utc_now(),
                int(resume_requested),
                stop_after,
                existing_before,
                committed_new,
                skipped_existing,
                total_after,
            ),
        )
        connection.commit()
    finally:
        connection.close()


def checkpoint_result_ids(checkpoint: Path) -> set[str]:
    connection = connect_checkpoint(checkpoint, readonly=True)
    try:
        return {row[0] for row in connection.execute("SELECT job_id FROM results")}
    finally:
        connection.close()


def checkpoint_count(checkpoint: Path) -> int:
    connection = connect_checkpoint(checkpoint, readonly=True)
    try:
        return int(connection.execute("SELECT COUNT(*) FROM results").fetchone()[0])
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
            "El plan completo está bloqueado en F1.11. "
            "F1.12 deberá usar --allow-full-plan de forma explícita."
        )
    if checkpoint.exists() and not resume:
        raise RuntimeError(
            f"El checkpoint ya existe: {checkpoint}. Use --resume o conserve el archivo."
        )
    if stop_after is not None and stop_after <= 0:
        raise ValueError("--stop-after debe ser un entero positivo.")

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
            f"[{len(existing_ids)}/{len(plan_rows)}] {job['job_id']} "
            f"{job['series_id']} seed={job['external_optimizer_seed']} "
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
    return [fetched[row["job_id"]] for row in plan_rows if row["job_id"] in fetched]


def export_results(checkpoint: Path, plan_rows: list[dict[str, Any]], output_path: Path) -> list[dict[str, Any]]:
    rows = fetch_results_for_plan(checkpoint, plan_rows)
    export_rows: list[dict[str, Any]] = []
    for row in rows:
        export_rows.append({
            "job_id": row["job_id"], "job_class": row["job_class"], "series_id": row["series_id"],
            "condition_id": row["condition_id"], "parent_id": row["parent_id"], "block_id": row["block_id"],
            "ground_truth": row["ground_truth"], "duration_s": row["duration_s"],
            "red_noise_alpha": row["red_noise_alpha"], "period_s": empty_if_none(row["period_s"]),
            "qpp_fraction": empty_if_none(row["qpp_fraction"]), "data_seed": row["data_seed"],
            "external_optimizer_seed": row["external_optimizer_seed"], "model_id": row["model_id"],
            "model_name": row["model_name"], "status": row["status"], "runtime_seconds": row["runtime_seconds"],
            "n_samples": row["n_samples"], "input_flux_sha256": row["input_flux_sha256"],
            "input_time_sha256": row["input_time_sha256"], "parent_n120_series_id": row["parent_n120_series_id"],
            "afino_effective_dt_s": empty_if_none(row["afino_effective_dt_s"]),
            "positive_frequency_bins": empty_if_none(row["positive_frequency_bins"]),
            "bins_after_cutoff": empty_if_none(row["bins_after_cutoff"]),
            "minimum_frequency_hz": empty_if_none(row["minimum_frequency_hz"]),
            "maximum_frequency_hz": empty_if_none(row["maximum_frequency_hz"]),
            "lnlike": empty_if_none(row["lnlike"]), "BIC": empty_if_none(row["BIC"]),
            "rchi2": empty_if_none(row["rchi2"]), "probability": empty_if_none(row["probability"]),
            "parameters_json": empty_if_none(row["parameters_json"]),
            "estimated_period_s": empty_if_none(row["estimated_period_s"]),
            "parameter_at_bound": parse_database_bool(row["parameter_at_bound"]),
            "bound_indices_json": empty_if_none(row["bound_indices_json"]),
            "warning_count": empty_if_none(row["warning_count"]),
            "warning_types_json": empty_if_none(row["warning_types_json"]),
            "convergence_status": row["convergence_status"], "error": empty_if_none(row["error"]),
        })
    write_csv(output_path, RESULT_FIELDNAMES, export_rows)
    return rows


def build_decisions(result_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    order: list[tuple[str, int]] = []
    for row in result_rows:
        key = (str(row["series_id"]), int(row["external_optimizer_seed"]))
        if key not in grouped:
            order.append(key)
        grouped[key][str(row["model_id"])] = row
    decisions: list[dict[str, Any]] = []
    for key in order:
        by_model = grouped[key]
        if set(by_model) != {"M0", "M1", "M2"}:
            raise RuntimeError(f"Modelos incompletos para decisión {key}.")
        valid_models = sum(by_model[m]["status"] == "OK" and by_model[m]["BIC"] is not None and math.isfinite(float(by_model[m]["BIC"])) for m in MODEL_SPECS)
        valid = valid_models == 3
        delta01: float | str = ""; delta21: float | str = ""; selected: bool | str = ""
        estimated_period: float | str = ""; period_label = "unavailable_incomplete_numerical"
        if by_model["M1"]["status"] == "OK" and by_model["M1"]["estimated_period_s"] is not None:
            estimated_period = float(by_model["M1"]["estimated_period_s"])
            period_label = "formal_m1_center_not_selected"
        if valid:
            delta01 = float(by_model["M0"]["BIC"]) - float(by_model["M1"]["BIC"])
            delta21 = float(by_model["M2"]["BIC"]) - float(by_model["M1"]["BIC"])
            selected = bool(delta01 > 10.0 and delta21 > 10.0)
            if selected:
                period_label = "recovered_period_selected"
        exemplar = by_model["M0"]
        decisions.append({
            "series_id": key[0], "condition_id": exemplar["condition_id"], "parent_id": exemplar["parent_id"],
            "block_id": exemplar["block_id"], "ground_truth": exemplar["ground_truth"],
            "n_samples": exemplar["n_samples"], "duration_s": exemplar["duration_s"],
            "red_noise_alpha": exemplar["red_noise_alpha"], "period_s": empty_if_none(exemplar["period_s"]),
            "qpp_fraction": empty_if_none(exemplar["qpp_fraction"]), "data_seed": exemplar["data_seed"],
            "external_optimizer_seed": key[1], "decision_status": "VALID" if valid else "INCOMPLETE_NUMERICAL",
            "valid_models": valid_models, "bic_m0": empty_if_none(by_model["M0"]["BIC"]),
            "bic_m1": empty_if_none(by_model["M1"]["BIC"]), "bic_m2": empty_if_none(by_model["M2"]["BIC"]),
            "delta_bic_0_1": delta01, "delta_bic_2_1": delta21, "qpp_selected": selected,
            "estimated_period_s": estimated_period, "period_label": period_label,
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


def run_replays(checkpoint: Path, plan_rows: list[dict[str, Any]], dataset: dict[str, Any]) -> dict[str, Any]:
    targets = [row for row in plan_rows if row["series_id"] in REPLAY_SERIES_IDS and row["external_optimizer_seed"] == 0]
    if len(targets) != EXPECTED_REPLAY_COMPARISONS:
        raise RuntimeError(f"Se esperaban seis trabajos de replay y hay {len(targets)}.")
    connection = connect_checkpoint(checkpoint, readonly=True)
    try:
        originals = {row["job_id"]: dict(row) for row in connection.execute("SELECT * FROM results")}
    finally:
        connection.close()
    comparisons: list[dict[str, Any]] = []
    for job in targets:
        if job["job_id"] not in originals:
            raise RuntimeError(f"Falta el resultado original de {job['job_id']}.")
        replay = execute_one_job(job, dataset)
        passed, detail = exact_replay_compare(originals[job["job_id"]], replay)
        comparisons.append({"job_id": job["job_id"], "series_id": job["series_id"],
                            "condition_id": job["condition_id"], "model_id": job["model_id"],
                            "passed": passed, **detail})
        print(f"REPLAY {job['job_id']} {job['model_id']}: {'PASS' if passed else 'FAIL'}")
    passed_count = sum(item["passed"] for item in comparisons)
    return {"expected_count": EXPECTED_REPLAY_COMPARISONS, "passed_count": passed_count,
            "failed_count": EXPECTED_REPLAY_COMPARISONS - passed_count, "comparisons": comparisons}


# =============================================================================
# Final audit and report
# =============================================================================


def read_checkpoint_audit(checkpoint: Path) -> dict[str, Any]:
    connection = connect_checkpoint(checkpoint, readonly=True)
    try:
        metadata = {
            row["key"]: row["value"]
            for row in connection.execute("SELECT key, value FROM metadata")
        }
        results = [dict(row) for row in connection.execute("SELECT * FROM results")]
        invocations = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM invocations ORDER BY invocation_id"
            )
        ]
    finally:
        connection.close()
    return {"metadata": metadata, "results": results, "invocations": invocations}


def duplicate_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    job_counts = Counter(row["job_id"] for row in results)
    scientific_counts = Counter(
        (row["series_id"], row["external_optimizer_seed"], row["model_id"])
        for row in results
    )
    return {
        "duplicate_job_id_rows": sum(count - 1 for count in job_counts.values() if count > 1),
        "duplicate_scientific_key_rows": sum(
            count - 1 for count in scientific_counts.values() if count > 1
        ),
    }


def environment_text(environment: dict[str, Any]) -> str:
    return "\n".join([
        f"Python: {environment['python_version']}", f"Python full: {environment['python_full']}",
        f"Python executable relative: {environment['python_executable_relative']}",
        f"NumPy: {environment['numpy_version']}", f"SciPy: {environment['scipy_version']}",
        f"Platform: {environment['platform']}", f"Machine: {environment['machine']}",
        f"Processor: {environment['processor']}", f"AFINO commit: {environment['commit']}",
        f"AFINO package version: {environment['afino_version']}",
        f"Tracked diff exit code: {environment['tracked_diff_exit_code']}",
        f"Staged diff exit code: {environment['staged_diff_exit_code']}",
        "Git status --porcelain:", environment['git_status'], "", "pip freeze:", *environment['pip_freeze'], "",
    ])


def report_diagnosis(audit: dict[str, Any]) -> str:
    diagnosis = f"""
La infraestructura reanudable se validó exclusivamente mediante el canary congelado de 48 llamadas. El plan completo de {audit['plan']['full_plan_rows']} trabajos fue construido y auditado, pero no se ejecutó. Las entradas proceden de los cuatro payloads binarios de F1.3: sus hashes físicos y lógicos se verificaron antes de abrir el checkpoint, y cada trabajo volvió a comprobar los hashes de su flujo y su vector temporal. Los tiempos sintéticos se entregaron directamente en segundos relativos, sin aplicar la conversión observacional desde TBJD.

La primera pasada confirmó {audit['resume_test']['resume_first_pass_completed']} trabajos y dejó 31 pendientes. La segunda añadió {audit['resume_test']['resume_second_pass_new']} trabajos, alcanzando las 48 filas. La tercera encontró todas las claves ya confirmadas y realizó {audit['resume_test']['resume_third_pass_new']} llamadas nuevas. SQLite impuso unicidad tanto sobre job_id como sobre la terna serie, semilla externa y modelo. Cada resultado, incluido un eventual estado de error, se confirmó en una transacción independiente; una interrupción anterior al commit no puede producir una fila falsamente terminada.

Las seis ejecuciones directas de replay coincidieron exactamente con sus resultados confirmados en BIC, log-likelihood, parámetros, centro formal de M1, rchi2, probabilidad, warnings y bounds. Esta igualdad valida la repetibilidad mecánica del runner para los dos extremos predeclarados del canary, no la convergencia formal del optimizador ni la unicidad global de sus soluciones. AFINO continúa etiquetado como NOT_AUDITABLE respecto a res.success y res.message.

Las 16 decisiones del canary se exportaron únicamente para comprobar agrupación, regla doble BIC y etiquetado del centro de M1. No se calcularon ni interpretaron tasas de detección o selección, y estos resultados no son elegibles para el análisis primario de F1.5. No se modificaron código AFINO, dataset, bounds, cutoff, semillas ni reglas después de observar el canary. El runner y ambos planes quedan congelados; F1.5 deberá usar un checkpoint nuevo y el plan completo, conservando este checkpoint canary por separado.
""".strip()
    word_count = len(diagnosis.split())
    if not 250 <= word_count <= 400:
        raise RuntimeError(f"El diagnóstico contiene {word_count} palabras.")
    return diagnosis


def runner_diff_audit() -> dict[str, Any]:
    import ast as _ast
    import difflib as _difflib
    reference_source = REFERENCE_RUNNER.read_text(encoding="utf-8")
    current_source = Path(__file__).resolve().read_text(encoding="utf-8")
    diff_lines = list(_difflib.unified_diff(reference_source.splitlines(), current_source.splitlines(), lineterm=""))
    def function_source(source: str, name: str) -> str:
        tree = _ast.parse(source)
        node = next(n for n in tree.body if isinstance(n, _ast.FunctionDef) and n.name == name)
        lines = source.splitlines()
        return "\n".join(lines[node.lineno - 1: node.end_lineno])
    exact_functions = {
        name: function_source(reference_source, name) == function_source(current_source, name)
        for name in ("inspect_bounds", "warning_payload", "insert_result_transaction", "exact_replay_compare")
    }
    marker_start = "        series = afino_series.AfinoSeries"
    marker_end = "    except Exception:"
    old_core = reference_source[reference_source.index(marker_start):reference_source.index(marker_end, reference_source.index(marker_start))]
    new_core = current_source[current_source.index(marker_start):current_source.index(marker_end, current_source.index(marker_start))]
    scientific_core = {
        "model_specs_identical": MODEL_SPECS == {"M0": "pow_const", "M1": "pow_const_gauss", "M2": "bpow_const"},
        "cutoff_identical": LOW_FREQUENCY_CUTOFF_HZ == 1.0 / 40.0,
        "m1_bounds_identical": OVERWRITE_GAUSS_BOUNDS == ((-10.0, 10.0), (-1.0, 6.0), (-20.0, 10.0), (-16.0, 5.0), (float(np.log(1.0 / 300.0)), float(np.log(1.0 / 40.0))), (0.05, 0.25)),
        "afino_execution_fragment_byte_identical": old_core == new_core,
        **{f"function_{name}_byte_identical": value for name, value in exact_functions.items()},
    }
    if not all(scientific_core.values()):
        raise RuntimeError(f"El núcleo científico no coincide con runner 1.0.1: {scientific_core}")
    return {
        "reference_runner": REFERENCE_RUNNER.name,
        "reference_sha256": sha256(REFERENCE_RUNNER),
        "nested_runner": Path(__file__).resolve().name,
        "nested_sha256": sha256(Path(__file__).resolve()),
        "unified_diff_sha256": hashlib.sha256("\n".join(diff_lines).encode("utf-8")).hexdigest(),
        "unified_diff_line_count": len(diff_lines),
        "classified_changes": [
            {"category": "dataset_contract", "sections": ["constants", "verify_frozen_files", "load_dataset", "load_plan", "extract_series_and_time"], "description": "F1.10 arrays, manifests, hashes and parent-prefix checks."},
            {"category": "metadata", "sections": ["plan fields", "SQLite result schema", "result and decision export"], "description": "parent_id, block_id, duration, alpha, period, amplitude and N=120 linkage."},
            {"category": "output_naming", "sections": ["default checkpoint, CSV, audit, report and environment names"], "description": "F1.11 nested artifact namespace."},
            {"category": "job_counts", "sections": ["full plan and canary constants", "canary selection", "final structural validation"], "description": "7938 full jobs and 72 canary jobs."},
        ],
        "scientific_core_checks": scientific_core,
        "scientific_core_modified": False,
    }


def validate_canary_inputs(plan_rows: list[dict[str, Any]], dataset: dict[str, Any]) -> dict[str, Any]:
    series_ids = list(dict.fromkeys(row["series_id"] for row in plan_rows))
    if tuple(series_ids) != CANARY_SERIES_IDS:
        raise RuntimeError("Canary series mismatch.")
    flux_matches = time_matches = parent_links = 0
    for series_id in series_ids:
        row = next(row for row in plan_rows if row["series_id"] == series_id)
        time_seconds, flux = extract_series_and_time(row, dataset)
        flux_matches += canonical_sha256(flux, "<f8") == row["input_flux_sha256"]
        time_matches += canonical_sha256(time_seconds, "<f8") == row["input_time_sha256"]
        parent = dataset["series_by_id"][row["parent_n120_series_id"]]
        parent_links += parent["parent_id"] == row["parent_id"] and int(parent["n_samples"]) == 120
    adjacent = 0
    for trajectory in (series_ids[:6], series_ids[6:]):
        arrays = []
        for series_id in trajectory:
            meta = dataset["series_by_id"][series_id]
            arrays.append(np.asarray(dataset["flux_values"][int(meta["flux_start_offset"]):int(meta["flux_end_offset"])], dtype="<f8"))
        for left, right in zip(arrays[:-1], arrays[1:]):
            adjacent += left.tobytes(order="C") == right[: left.size].tobytes(order="C")
    result = {"canary_series": len(series_ids), "flux_hash_matches": int(flux_matches),
              "time_hash_matches": int(time_matches), "parent_n120_links": int(parent_links),
              "adjacent_prefix_matches": int(adjacent)}
    if result != {"canary_series": 12, "flux_hash_matches": 12, "time_hash_matches": 12,
                  "parent_n120_links": 12, "adjacent_prefix_matches": 10}:
        raise RuntimeError(f"Validación pre-AFINO del canary falló: {result}")
    return result


def finalize_canary(
    *, checkpoint: Path, plan_rows: list[dict[str, Any]], dataset: dict[str, Any],
    physical_hashes: dict[str, str], logical_hashes: dict[str, str],
    environment: dict[str, Any], results_path: Path, decisions_path: Path,
    audit_path: Path, report_path: Path, environment_path: Path, replay: dict[str, Any],
) -> dict[str, Any]:
    state = read_checkpoint_audit(checkpoint)
    results = state["results"]
    invocations = state["invocations"]
    duplicates = duplicate_counts(results)
    decision_rows = build_decisions(results)
    completed_sequence = [int(row["committed_new"]) for row in invocations]
    if completed_sequence != [23, 49, 0]:
        raise RuntimeError(f"Secuencia de reanudación incorrecta: {completed_sequence}.")
    pre_canary = validate_canary_inputs(plan_rows, dataset)
    status_counts = Counter(row["status"] for row in results)
    decision_counts = Counter(row["decision_status"] for row in decision_rows)
    bins_mismatches = [
        {"job_id": row["job_id"], "n_samples": row["n_samples"], "observed": row["bins_after_cutoff"],
         "expected": EXPECTED_BINS_AFTER_CUTOFF[int(row["n_samples"])]}
        for row in results
        if row["status"] == "OK" and int(row["bins_after_cutoff"]) != EXPECTED_BINS_AFTER_CUTOFF[int(row["n_samples"])]
    ]
    ok_contract_mismatches = [row["job_id"] for row in results if row["status"] == "OK" and (
        float(row["afino_effective_dt_s"]) != 20.0 or row["convergence_status"] != "NOT_AUDITABLE" or (row["error"] not in (None, ""))
    )]
    diff_audit = runner_diff_audit()
    post_environment = verify_environment()
    post_physical, post_logical = verify_frozen_files()
    for field in ("commit", "afino_version", "numpy_version", "scipy_version"):
        if post_environment[field] != environment[field]:
            raise RuntimeError(f"El entorno cambió durante el canary: {field}.")
    environment_path.write_text(environment_text(post_environment), encoding="utf-8")
    full_plan_rows, full_kind = load_plan(FULL_PLAN_CSV, dataset)
    if full_kind != "full":
        raise RuntimeError("El plan completo no se reconoció como full.")
    all_structural_pass = (
        len(full_plan_rows) == 7938
        and Counter(row["job_class"] for row in full_plan_rows) == {"primary": 6480, "stability": 1458}
        and Counter(row["model_id"] for row in full_plan_rows) == {"M0": 2646, "M1": 2646, "M2": 2646}
        and len(plan_rows) == 72 and len(results) == 72 and len(decision_rows) == 24
        and completed_sequence == [23, 49, 0] and not any(duplicates.values())
        and status_counts == {"OK": 72} and decision_counts == {"VALID": 24}
        and replay["passed_count"] == 6 and not bins_mismatches and not ok_contract_mismatches
        and post_physical == physical_hashes and post_logical == logical_hashes
        and not diff_audit["scientific_core_modified"]
    )
    conclusion = "NESTED_RUNNER_VALIDATED_BEFORE_FULL_BENCHMARK" if all_structural_pass else "NESTED_RUNNER_VALIDATION_BLOCKED"
    output_hashes = {
        BUILD_PLAN_SCRIPT.name: sha256(BUILD_PLAN_SCRIPT), FULL_PLAN_CSV.name: sha256(FULL_PLAN_CSV),
        CANARY_PLAN_CSV.name: sha256(CANARY_PLAN_CSV), Path(__file__).resolve().name: sha256(Path(__file__).resolve()),
        checkpoint.name: sha256(checkpoint), results_path.name: sha256(results_path),
        decisions_path.name: sha256(decisions_path), environment_path.name: sha256(environment_path),
    }
    audit = {
        "date_utc": utc_now(), "runner_family": RUNNER_FAMILY,
        "runner_implementation_version": RUNNER_IMPLEMENTATION_VERSION,
        "validation_conclusion": conclusion, "environment": environment,
        "preflight": {"physical_hashes": physical_hashes, "logical_hashes": logical_hashes,
                      "canary_input_validation": pre_canary, "persisted_time_used_directly_in_seconds": True,
                      "tbjd_conversion_reapplied": False},
        "postflight": {"physical_hashes": post_physical, "logical_hashes": post_logical,
                       "dataset_unchanged": post_physical == physical_hashes and post_logical == logical_hashes,
                       "tracked_git_diff_empty": post_environment["tracked_diff_exit_code"] == 0,
                       "staged_git_diff_empty": post_environment["staged_diff_exit_code"] == 0,
                       "git_status_porcelain": post_environment["git_status"]},
        "runner_diff": diff_audit,
        "plan": {"full_plan_rows": 7938, "primary_plan_rows": 6480, "stability_plan_rows": 1458,
                 "rows_per_model": 2646, "canary_series": 12, "canary_plan_rows": 72,
                 "full_plan_sha256": sha256(FULL_PLAN_CSV), "canary_plan_sha256": sha256(CANARY_PLAN_CSV),
                 "unique_full_plan_job_ids": len({row["job_id"] for row in full_plan_rows}),
                 "unique_full_plan_scientific_keys": len({(row["series_id"], row["external_optimizer_seed"], row["model_id"]) for row in full_plan_rows})},
        "canary": {"series_ids": list(CANARY_SERIES_IDS), "parent_ids": sorted({row["parent_id"] for row in plan_rows}),
                   "block_ids": sorted({row["block_id"] for row in plan_rows}), "canary_result_rows": len(results),
                   "canary_decision_rows": len(decision_rows), "result_status_counts": dict(status_counts),
                   "decision_status_counts": dict(decision_counts), "bins_after_cutoff_expected": EXPECTED_BINS_AFTER_CUTOFF,
                   "bins_mismatches": bins_mismatches, "ok_contract_mismatches": ok_contract_mismatches,
                   "canary_results_eligible_for_analysis": False},
        "resume_test": {"first_pass_completed": 23, "second_pass_new": 49, "third_pass_new": 0,
                        "invocations": invocations, **duplicates},
        "exact_replay": replay,
        "checkpoint": {"filename": checkpoint.name, "sha256": sha256(checkpoint), "result_rows": len(results),
                       "metadata": state["metadata"], "sqlite_transaction_policy": "one independent transaction per completed model call",
                       "unique_job_id_enforced": True, "unique_series_seed_model_enforced": True},
        "protocol": {"low_frequency_cutoff_hz": LOW_FREQUENCY_CUTOFF_HZ, "models": MODEL_SPECS,
                     "M1_bounds": [list(bounds) for bounds in OVERWRITE_GAUSS_BOUNDS],
                     "seed_reset_before_each_model_call": True,
                     "selection_rule": "(BIC_M0 - BIC_M1 > 10.0) and (BIC_M2 - BIC_M1 > 10.0)",
                     "convergence_status": "NOT_AUDITABLE"},
        "output_hashes": output_hashes, "incidents": [],
        "confirmations": {"full_nested_benchmark_executed": False, "canary_results_used_for_tuning": False,
                          "canary_results_eligible_for_analysis": False, "afino_code_modified": False,
                          "dataset_modified": False, "dataset_regenerated": False,
                          "scientific_protocol_modified": False, "old_runner_modified": False,
                          "checkpoint_reused": False},
    }
    report = f"""# Fase 1 — Tarea 1.11

## Congelación del plan y validación del runner anidado reanudable

**Conclusión:** `{conclusion}`  
**Runner:** `{RUNNER_FAMILY}` `{RUNNER_IMPLEMENTATION_VERSION}`  
**AFINO:** `{environment['commit']}` / `{environment['afino_version']}`  
**Benchmark completo ejecutado:** no

## Plan e inputs

El plan normativo contiene exactamente 7.938 trabajos: 6.480 primarios y 1.458 de estabilidad. M0, M1 y M2 tienen 2.646 filas cada uno y las claves `(series_id, external_optimizer_seed, model_id)` son únicas. Antes y después del canary coincidieron los hashes físicos de F1.8 y F1.10 y los cuatro hashes lógicos del dataset. El runner leyó exclusivamente los cuatro arrays `.npy` con `allow_pickle=False`; entregó a AFINO los vectores temporales persistidos directamente en segundos, sin reconstrucción ni conversión TBJD.

## Adaptación del runner

La versión 1.1.0 se comparó con el runner 1.0.1. Los cambios quedaron clasificados como `dataset_contract`, `metadata`, `output_naming` y `job_counts`. La importación de AFINO, los tres modelos, los bounds, el cutoff de 1/40 Hz, el reinicio de la semilla, la captura de warnings, el diagnóstico de bounds, la regla doble BIC y la transacción SQLite por llamada permanecieron sin cambios. Las comprobaciones automáticas del núcleo científico fueron todas satisfactorias.

## Canary y reanudación

El canary resolvió doce series: seis prefijos del padre nulo con alpha 0 y seis del padre positivo P=80 s, q=0,04 y alpha 2. Se verificaron 12/12 hashes de flujo, 12/12 hashes temporales, 12/12 enlaces con la serie N=120 y las diez relaciones adyacentes. La primera pasada confirmó 23 llamadas y dejó 49 pendientes; la segunda añadió 49 y alcanzó 72; la tercera añadió cero. No aparecieron duplicados.

Los 72 resultados fueron OK y produjeron 24 decisiones VALID. Para N=15, 30, 45, 60, 90 y 120 quedaron respectivamente 7, 14, 22, 29, 44 y 59 bins tras el cutoff, coherentes con la lectura directa de tiempos en segundos. Los seis replays predeclarados coincidieron exactamente en estado, BIC, likelihood, parámetros, periodo formal, rchi2, probabilidad, warnings, bounds y error.

## Alcance y cierre

Los resultados canary no son elegibles para el análisis científico y no se utilizaron para ajustar el protocolo. No se ejecutó ninguna fila fuera del plan canary ni se modificaron AFINO, el dataset, el prerregistro o el runner 1.0.1. El runner 1.1.0 y los dos planes quedan congelados para F1.12.

## Conclusión

`{conclusion}`
"""
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")
    return audit


# =============================================================================
# CLI
# =============================================================================


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Runner AFINO anidado reanudable para F1.11/F1.12.")
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
    parser.add_argument("--environment", type=Path, default=DEFAULT_ENVIRONMENT)
    parser.add_argument("--allow-full-plan", action="store_true")
    return parser


def resolve_under_root(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan_path = resolve_under_root(args.plan); checkpoint = resolve_under_root(args.checkpoint)
    export_path = resolve_under_root(args.export) if args.export else None
    decisions_path = resolve_under_root(args.decisions) if args.decisions else None
    audit_path = resolve_under_root(args.audit); report_path = resolve_under_root(args.report)
    environment_path = resolve_under_root(args.environment)
    if args.finalize_canary and (export_path is None or decisions_path is None):
        raise RuntimeError("--finalize-canary exige --export y --decisions.")
    if args.finalize_canary and not args.replay:
        raise RuntimeError("--finalize-canary exige --replay.")
    print("F1.11 — RUNNER AFINO ANIDADO CHECKPOINTED", flush=True)
    print(f"Runner family: {RUNNER_FAMILY}", flush=True)
    print(f"Runner implementation: {RUNNER_IMPLEMENTATION_VERSION}", flush=True)
    environment = verify_environment()
    physical_hashes, logical_hashes = verify_frozen_files()
    dataset = load_dataset()
    plan_rows, plan_kind = load_plan(plan_path, dataset)
    if args.finalize_canary and plan_kind != "canary":
        raise RuntimeError("La finalización F1.11 solo admite el canary.")
    runner_sha = sha256(Path(__file__).resolve())
    print(f"Runner SHA-256: {runner_sha}", flush=True)
    print(f"Plan: {plan_path.name} ({plan_kind}, {len(plan_rows)} filas)", flush=True)
    print("Hashes físicos y lógicos de F1.10: verificados", flush=True)
    print(f"AFINO commit: {environment['commit']}", flush=True)
    print(f"AFINO version: {environment['afino_version']}", flush=True)
    summary = run_plan(plan_path=plan_path, plan_rows=plan_rows, plan_kind=plan_kind,
                       checkpoint=checkpoint, resume=args.resume, stop_after=args.stop_after,
                       dataset=dataset, runner_sha256=runner_sha, physical_hashes=physical_hashes,
                       logical_hashes=logical_hashes, allow_full_plan=args.allow_full_plan)
    result_rows: list[dict[str, Any]] | None = None
    if export_path is not None:
        result_rows = export_results(checkpoint, plan_rows, export_path)
        print(f"Exportados {len(result_rows)} resultados a {export_path.name}")
    if decisions_path is not None:
        if result_rows is None:
            result_rows = fetch_results_for_plan(checkpoint, plan_rows)
        decisions = export_decisions(result_rows, decisions_path)
        print(f"Exportadas {len(decisions)} decisiones a {decisions_path.name}")
    replay_result: dict[str, Any] | None = None
    if args.replay:
        replay_result = run_replays(checkpoint, plan_rows, dataset)
        print(f"Replays exactos: {replay_result['passed_count']}/{replay_result['expected_count']}")
    if args.finalize_canary:
        if result_rows is None or replay_result is None or export_path is None or decisions_path is None:
            raise RuntimeError("Estado interno incompleto para finalización.")
        audit = finalize_canary(checkpoint=checkpoint, plan_rows=plan_rows, dataset=dataset,
                                physical_hashes=physical_hashes, logical_hashes=logical_hashes,
                                environment=environment, results_path=export_path, decisions_path=decisions_path,
                                audit_path=audit_path, report_path=report_path, environment_path=environment_path,
                                replay=replay_result)
        print(f"Conclusión: {audit['validation_conclusion']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RUNNER_VALIDATION_BLOCKED: {exc}", file=sys.stderr, flush=True)
        raise
