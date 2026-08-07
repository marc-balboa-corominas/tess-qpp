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
# Frozen F1.4 protocol
# =============================================================================

ROOT = Path(__file__).resolve().parent
REPO = ROOT / "afino_release_version"
RUNNER_IMPLEMENTATION_VERSION = "1.0.1"

BUILD_PLAN_SCRIPT = ROOT / "fase1_tarea04_build_execution_plan.py"
FULL_PLAN_CSV = ROOT / "fase1_tarea04_full_execution_plan.csv"
CANARY_PLAN_CSV = ROOT / "fase1_tarea04_canary_plan.csv"

FLUX_NPY = ROOT / "fase1_tarea03_core_flux_values.npy"
SERIES_OFFSETS_NPY = ROOT / "fase1_tarea03_core_series_offsets.npy"
TIME_VALUES_NPY = ROOT / "fase1_tarea03_core_time_values.npy"
TIME_OFFSETS_NPY = ROOT / "fase1_tarea03_core_time_offsets.npy"
SERIES_MANIFEST_CSV = ROOT / "fase1_tarea03_core_series_manifest.csv"
TIME_MANIFEST_CSV = ROOT / "fase1_tarea03_time_vector_manifest.csv"
MATERIALIZATION_AUDIT_JSON = ROOT / "fase1_tarea03_materialization_audit.json"

DEFAULT_CHECKPOINT = ROOT / "fase1_tarea04_canary_checkpoint.sqlite"
DEFAULT_RESULTS = ROOT / "fase1_tarea04_canary_results.csv"
DEFAULT_DECISIONS = ROOT / "fase1_tarea04_canary_decisions.csv"
DEFAULT_AUDIT = ROOT / "fase1_tarea04_runner_validation_audit.json"
DEFAULT_REPORT = ROOT / "fase1_tarea04_runner_validation_report.md"
DEFAULT_ENVIRONMENT = ROOT / "fase1_tarea04_environment.txt"

EXPECTED_AFINO_COMMIT = "6aceac9518fc8056052807e666da9d0c8bebb010"
EXPECTED_AFINO_VERSION = "0.5"

EXPECTED_BUILD_PLAN_SCRIPT_SHA256 = (
    "0980c0c8630106dc19627f50722ffe54c46b35d68809e6db6be651be537c79d3"
)
EXPECTED_FULL_PLAN_SHA256 = (
    "ccc7b6232b921e6422097fa1fc2525ec7f559459994ba7dfb222dbb0abfecf03"
)
EXPECTED_CANARY_PLAN_SHA256 = (
    "5663ee0c5607db3764abe26f7e4e231a0b36d467714bb2f62778a3c414d47480"
)

EXPECTED_PHYSICAL_HASHES = {
    "fase1_tarea03_core_flux_values.npy": (
        "f5fdd48f2951a1e055355d76b8b82c931fceea8cbb0688ca0099fe329594e60d"
    ),
    "fase1_tarea03_core_series_offsets.npy": (
        "9169e4253cee3fb75b52e6ef61995efcdb71514720ba39c311eb9a085e901d85"
    ),
    "fase1_tarea03_core_time_values.npy": (
        "730e97faa7b9bbcf03ea9b8c897790fd500c36fadb8f7c47608d9614fbba8513"
    ),
    "fase1_tarea03_core_time_offsets.npy": (
        "c58d96df35b66a33ec3ffe37347f745af78cfd3eaa4e77762230206513f4c233"
    ),
    "fase1_tarea03_core_series_manifest.csv": (
        "2020c849348c81235036443d3215395c602b80b00debe64fec692935dda778f4"
    ),
    "fase1_tarea03_time_vector_manifest.csv": (
        "ce7f2f465f7ee73c8de983a91a8415b1a9d75e3b65a5e94b553d42c94068a5e7"
    ),
    "fase1_tarea03_materialization_audit.json": (
        "8fa6d0b108dd9f4c2d941729221ad9fcbfea14af63baaec1474cce751bb51310"
    ),
}

EXPECTED_LOGICAL_HASHES = {
    "canonical_flux_payload_sha256": (
        "f593637faabf57bdcd9c4bea66f161cbaace77ad09de682179d709b002167abe"
    ),
    "series_offsets_canonical_sha256": (
        "b7ed6562c1d5a256309ca417744ed3f0520c79fb3d85b43a67383d9d4810817e"
    ),
    "time_values_canonical_sha256": (
        "6809c6c9ecb0667c5eda35e62fccbd958dc5c619845f9da37e0713f5b1580537"
    ),
    "time_offsets_canonical_sha256": (
        "28d9acdf22fdfaf6737337f20331e37a52710ec0d43c5b39251119b619a875a4"
    ),
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

CANARY_CONDITION_IDS = (
    "C001_NULL_N015_A0",
    "C030_QPP_N015_P080_A2_Q040",
    "C004_NULL_N030_A0",
    "C057_QPP_N030_P140_A2_Q040",
    "C007_NULL_N060_A0",
    "C084_QPP_N060_P140_A2_Q040",
    "C010_NULL_N120_A0",
    "C111_QPP_N120_P140_A2_Q040",
)

REPLAY_CONDITION_IDS = (
    "C001_NULL_N015_A0",
    "C111_QPP_N120_P140_A2_Q040",
)

RESULT_FIELDNAMES = [
    "job_id",
    "job_class",
    "series_id",
    "condition_id",
    "ground_truth",
    "data_seed",
    "external_optimizer_seed",
    "model_id",
    "model_name",
    "status",
    "runtime_seconds",
    "n_samples",
    "input_flux_sha256",
    "input_time_sha256",
    "afino_effective_dt_s",
    "positive_frequency_bins",
    "bins_after_cutoff",
    "minimum_frequency_hz",
    "maximum_frequency_hz",
    "lnlike",
    "BIC",
    "rchi2",
    "probability",
    "parameters_json",
    "estimated_period_s",
    "parameter_at_bound",
    "bound_indices_json",
    "warning_count",
    "warning_types_json",
    "convergence_status",
    "error",
]

DECISION_FIELDNAMES = [
    "series_id",
    "condition_id",
    "ground_truth",
    "external_optimizer_seed",
    "valid_models",
    "delta_bic_0_1",
    "delta_bic_2_1",
    "qpp_selected",
    "estimated_period_s",
    "period_label",
]

PLAN_REQUIRED_FIELDS = [
    "job_id",
    "job_order",
    "job_class",
    "series_id",
    "condition_id",
    "ground_truth",
    "data_seed",
    "external_optimizer_seed",
    "model_id",
    "model_name",
    "n_samples",
    "period_s",
    "qpp_fraction",
    "flux_start_offset",
    "flux_end_offset",
    "time_vector_id",
    "input_flux_sha256",
    "input_time_sha256",
]

EXPECTED_FULL_PLAN_ROWS = 16317
EXPECTED_PRIMARY_PLAN_ROWS = 13320
EXPECTED_STABILITY_PLAN_ROWS = 2997
EXPECTED_CANARY_PLAN_ROWS = 48
EXPECTED_CANARY_DECISIONS = 16
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
        raise RuntimeError(
            f"Commit AFINO incorrecto: {commit}; esperado {EXPECTED_AFINO_COMMIT}."
        )

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
        raise RuntimeError(
            f"Versión AFINO incorrecta: {afino_version}; esperada {EXPECTED_AFINO_VERSION}."
        )

    return {
        "commit": commit,
        "afino_version": afino_version,
        "tracked_diff_exit_code": tracked_exit,
        "staged_diff_exit_code": staged_exit,
        "git_status": git_status,
        "python_version": sys.version.split()[0],
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
    expected_auxiliary = {
        BUILD_PLAN_SCRIPT.name: EXPECTED_BUILD_PLAN_SCRIPT_SHA256,
        FULL_PLAN_CSV.name: EXPECTED_FULL_PLAN_SHA256,
        CANARY_PLAN_CSV.name: EXPECTED_CANARY_PLAN_SHA256,
    }
    physical: dict[str, str] = {}
    for filename, expected in {**EXPECTED_PHYSICAL_HASHES, **expected_auxiliary}.items():
        path = ROOT / filename
        if not path.exists():
            raise FileNotFoundError(f"Falta el artefacto congelado: {path}")
        observed = sha256(path)
        physical[filename] = observed
        if observed != expected:
            raise RuntimeError(
                f"Hash físico incorrecto para {filename}.\n"
                f"Esperado: {expected}\nObservado: {observed}"
            )

    flux_values = np.load(FLUX_NPY, allow_pickle=False)
    series_offsets = np.load(SERIES_OFFSETS_NPY, allow_pickle=False)
    time_values = np.load(TIME_VALUES_NPY, allow_pickle=False)
    time_offsets = np.load(TIME_OFFSETS_NPY, allow_pickle=False)

    if flux_values.dtype != np.dtype("<f8") or flux_values.ndim != 1:
        raise RuntimeError("core_flux_values.npy no es un vector <f8.")
    if series_offsets.dtype != np.dtype("<i8") or series_offsets.ndim != 1:
        raise RuntimeError("core_series_offsets.npy no es un vector <i8.")
    if time_values.dtype != np.dtype("<f8") or time_values.ndim != 1:
        raise RuntimeError("core_time_values.npy no es un vector <f8.")
    if time_offsets.dtype != np.dtype("<i8") or time_offsets.ndim != 1:
        raise RuntimeError("core_time_offsets.npy no es un vector <i8.")

    logical = {
        "canonical_flux_payload_sha256": canonical_sha256(flux_values, "<f8"),
        "series_offsets_canonical_sha256": canonical_sha256(series_offsets, "<i8"),
        "time_values_canonical_sha256": canonical_sha256(time_values, "<f8"),
        "time_offsets_canonical_sha256": canonical_sha256(time_offsets, "<i8"),
    }
    for name, expected in EXPECTED_LOGICAL_HASHES.items():
        if logical[name] != expected:
            raise RuntimeError(
                f"Hash lógico incorrecto para {name}.\n"
                f"Esperado: {expected}\nObservado: {logical[name]}"
            )

    audit = json.loads(MATERIALIZATION_AUDIT_JSON.read_text(encoding="utf-8"))
    if audit.get("materialization_status") != "DATASET_FROZEN_BEFORE_AFINO":
        raise RuntimeError("La auditoría F1.3 no contiene DATASET_FROZEN_BEFORE_AFINO.")
    if audit.get("logical_hashes", {}) != {
        **EXPECTED_LOGICAL_HASHES,
        "ordered_series_manifest_sha256": EXPECTED_PHYSICAL_HASHES[
            "fase1_tarea03_core_series_manifest.csv"
        ],
        "time_vector_manifest_sha256": EXPECTED_PHYSICAL_HASHES[
            "fase1_tarea03_time_vector_manifest.csv"
        ],
    }:
        raise RuntimeError("Los hashes lógicos registrados en F1.3 no coinciden.")

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

    if len(series_rows) != 4440 or len(series_offsets) != 4441:
        raise RuntimeError("Conteo de series u offsets inválido.")
    if len(time_rows) != 4 or len(time_offsets) != 5:
        raise RuntimeError("Conteo de tiempos u offsets inválido.")
    if len(flux_values) != 264600 or len(time_values) != 225:
        raise RuntimeError("Longitud del payload persistido inválida.")

    series_by_id = {row["series_id"]: row for row in series_rows}
    time_by_id = {row["time_vector_id"]: row for row in time_rows}
    if len(series_by_id) != 4440 or len(time_by_id) != 4:
        raise RuntimeError("Identificadores duplicados en manifiestos F1.3.")

    return {
        "flux_values": flux_values,
        "series_offsets": series_offsets,
        "time_values": time_values,
        "time_offsets": time_offsets,
        "series_rows": series_rows,
        "series_by_id": series_by_id,
        "time_rows": time_rows,
        "time_by_id": time_by_id,
    }


def load_plan(plan_path: Path, dataset: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    observed_hash = sha256(plan_path)
    if observed_hash == EXPECTED_CANARY_PLAN_SHA256:
        plan_kind = "canary"
        expected_count = EXPECTED_CANARY_PLAN_ROWS
    elif observed_hash == EXPECTED_FULL_PLAN_SHA256:
        plan_kind = "full"
        expected_count = EXPECTED_FULL_PLAN_ROWS
    else:
        raise RuntimeError(
            f"Plan no congelado: {plan_path.name} tiene SHA-256 {observed_hash}."
        )

    raw_rows = read_csv(plan_path)
    if len(raw_rows) != expected_count:
        raise RuntimeError(
            f"El plan {plan_path.name} contiene {len(raw_rows)} filas, no {expected_count}."
        )
    if not raw_rows or list(raw_rows[0]) != PLAN_REQUIRED_FIELDS:
        raise RuntimeError("El esquema del plan no coincide con F1.4.")

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
        for field in (
            "job_order",
            "data_seed",
            "external_optimizer_seed",
            "n_samples",
            "flux_start_offset",
            "flux_end_offset",
        ):
            row[field] = int(raw[field])

        if row["job_id"] in seen_job_ids:
            raise RuntimeError(f"job_id duplicado: {row['job_id']}.")
        seen_job_ids.add(row["job_id"])
        key = (row["series_id"], row["external_optimizer_seed"], row["model_id"])
        if key in seen_scientific:
            raise RuntimeError(f"Clave científica duplicada: {key}.")
        seen_scientific.add(key)

        series = dataset["series_by_id"].get(row["series_id"])
        if series is None:
            raise RuntimeError(f"Serie desconocida en plan: {row['series_id']}.")
        expected_pairs = {
            "condition_id": series["condition_id"],
            "ground_truth": series["ground_truth"],
            "data_seed": int(series["data_seed"]),
            "n_samples": int(series["n_samples"]),
            "period_s": series["period_s"],
            "qpp_fraction": series["qpp_fraction"],
            "flux_start_offset": int(series["flux_start_offset"]),
            "flux_end_offset": int(series["flux_end_offset"]),
            "time_vector_id": series["time_vector_id"],
            "input_flux_sha256": series["flux_sha256"],
            "input_time_sha256": dataset["time_by_id"][series["time_vector_id"]][
                "time_sha256"
            ],
        }
        for field, expected in expected_pairs.items():
            if row[field] != expected:
                raise RuntimeError(
                    f"El plan no coincide con F1.3 para {row['job_id']} campo {field}."
                )

        if row["job_class"] == "primary" and row["external_optimizer_seed"] != 0:
            raise RuntimeError(f"Primary con seed no nula: {row['job_id']}.")
        if row["job_class"] == "stability" and (
            row["data_seed"] != 0
            or not 1 <= row["external_optimizer_seed"] <= 9
        ):
            raise RuntimeError(f"Stability fuera de protocolo: {row['job_id']}.")
        plan_rows.append(row)

    if plan_kind == "full":
        counts = Counter(row["job_class"] for row in plan_rows)
        if counts != {"primary": 13320, "stability": 2997}:
            raise RuntimeError(f"Conteos del plan completo incorrectos: {counts}.")
        if [row["job_order"] for row in plan_rows] != list(range(1, 16318)):
            raise RuntimeError("El plan completo no conserva job_order 1–16317.")
    else:
        condition_order: list[str] = []
        for row in plan_rows:
            if row["condition_id"] not in condition_order:
                condition_order.append(row["condition_id"])
        if tuple(condition_order) != CANARY_CONDITION_IDS:
            raise RuntimeError("El canary no conserva las ocho condiciones congeladas.")
        if set(Counter(row["condition_id"] for row in plan_rows).values()) != {6}:
            raise RuntimeError("Cada condición canary debe contener seis trabajos.")

    return plan_rows, plan_kind


def extract_series_and_time(job: dict[str, Any], dataset: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    start = job["flux_start_offset"]
    end = job["flux_end_offset"]
    flux = np.asarray(dataset["flux_values"][start:end], dtype=np.float64).copy()
    if len(flux) != job["n_samples"]:
        raise RuntimeError(f"Longitud de flujo inválida en {job['job_id']}.")
    if canonical_sha256(flux, "<f8") != job["input_flux_sha256"]:
        raise RuntimeError(f"Hash de flujo inválido en {job['job_id']}.")

    time_meta = dataset["time_by_id"][job["time_vector_id"]]
    time_index = [row["time_vector_id"] for row in dataset["time_rows"]].index(
        job["time_vector_id"]
    )
    time_start = int(dataset["time_offsets"][time_index])
    time_end = int(dataset["time_offsets"][time_index + 1])
    time_seconds = np.asarray(
        dataset["time_values"][time_start:time_end], dtype=np.float64
    ).copy()
    if len(time_seconds) != job["n_samples"]:
        raise RuntimeError(f"Longitud temporal inválida en {job['job_id']}.")
    if canonical_sha256(time_seconds, "<f8") != job["input_time_sha256"]:
        raise RuntimeError(f"Hash temporal inválido en {job['job_id']}.")
    if float(time_seconds[0]) != 0.0 or not np.all(np.diff(time_seconds) > 0):
        raise RuntimeError(f"Vector temporal inválido en {job['job_id']}.")
    if time_meta["time_sha256"] != job["input_time_sha256"]:
        raise RuntimeError(f"Manifiesto temporal inválido en {job['job_id']}.")
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
        "job_id": job["job_id"],
        "job_order": job["job_order"],
        "job_class": job["job_class"],
        "series_id": job["series_id"],
        "condition_id": job["condition_id"],
        "ground_truth": job["ground_truth"],
        "data_seed": job["data_seed"],
        "external_optimizer_seed": job["external_optimizer_seed"],
        "model_id": job["model_id"],
        "model_name": job["model_name"],
        "status": "NOT_RUN",
        "runtime_seconds": None,
        "n_samples": job["n_samples"],
        "input_flux_sha256": job["input_flux_sha256"],
        "input_time_sha256": job["input_time_sha256"],
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
    "job_id",
    "job_order",
    "job_class",
    "series_id",
    "condition_id",
    "ground_truth",
    "data_seed",
    "external_optimizer_seed",
    "model_id",
    "model_name",
    "status",
    "runtime_seconds",
    "n_samples",
    "input_flux_sha256",
    "input_time_sha256",
    "afino_effective_dt_s",
    "positive_frequency_bins",
    "bins_after_cutoff",
    "minimum_frequency_hz",
    "maximum_frequency_hz",
    "lnlike",
    "BIC",
    "rchi2",
    "probability",
    "parameters_json",
    "estimated_period_s",
    "parameter_at_bound",
    "bound_indices_json",
    "bound_details_json",
    "warning_count",
    "warning_types_json",
    "warnings_json",
    "convergence_status",
    "error",
    "completed_at_utc",
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
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS results (
                job_id TEXT PRIMARY KEY,
                job_order INTEGER NOT NULL,
                job_class TEXT NOT NULL,
                series_id TEXT NOT NULL,
                condition_id TEXT NOT NULL,
                ground_truth TEXT NOT NULL,
                data_seed INTEGER NOT NULL,
                external_optimizer_seed INTEGER NOT NULL,
                model_id TEXT NOT NULL,
                model_name TEXT NOT NULL,
                status TEXT NOT NULL,
                runtime_seconds REAL NOT NULL,
                n_samples INTEGER NOT NULL,
                input_flux_sha256 TEXT NOT NULL,
                input_time_sha256 TEXT NOT NULL,
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
                UNIQUE(series_id, external_optimizer_seed, model_id)
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
            """
        )

        metadata = {
            "schema_version": "1.0.0",
            "runner_implementation_version": RUNNER_IMPLEMENTATION_VERSION,
            "plan_filename": plan_path.name,
            "plan_sha256": plan_sha256,
            "plan_kind": plan_kind,
            "runner_sha256": runner_sha256,
            "dataset_physical_hashes": json_compact(physical_hashes),
            "dataset_logical_hashes": json_compact(logical_hashes),
            "afino_commit": EXPECTED_AFINO_COMMIT,
            "afino_version": EXPECTED_AFINO_VERSION,
            "created_at_utc": utc_now(),
        }
        existing = {
            row["key"]: row["value"]
            for row in connection.execute("SELECT key, value FROM metadata")
        }
        if existing:
            immutable_keys = (
                "schema_version",
                "runner_implementation_version",
                "plan_filename",
                "plan_sha256",
                "plan_kind",
                "runner_sha256",
                "dataset_physical_hashes",
                "dataset_logical_hashes",
                "afino_commit",
                "afino_version",
            )
            for key in immutable_keys:
                if existing.get(key) != metadata[key]:
                    raise RuntimeError(
                        f"Checkpoint incompatible en metadata[{key}]."
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
            "El plan completo está bloqueado en F1.4. "
            "F1.5 deberá usar --allow-full-plan de forma explícita."
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


def export_results(
    checkpoint: Path,
    plan_rows: list[dict[str, Any]],
    output_path: Path,
) -> list[dict[str, Any]]:
    rows = fetch_results_for_plan(checkpoint, plan_rows)
    export_rows: list[dict[str, Any]] = []
    for row in rows:
        export_rows.append(
            {
                "job_id": row["job_id"],
                "job_class": row["job_class"],
                "series_id": row["series_id"],
                "condition_id": row["condition_id"],
                "ground_truth": row["ground_truth"],
                "data_seed": row["data_seed"],
                "external_optimizer_seed": row["external_optimizer_seed"],
                "model_id": row["model_id"],
                "model_name": row["model_name"],
                "status": row["status"],
                "runtime_seconds": row["runtime_seconds"],
                "n_samples": row["n_samples"],
                "input_flux_sha256": row["input_flux_sha256"],
                "input_time_sha256": row["input_time_sha256"],
                "afino_effective_dt_s": empty_if_none(row["afino_effective_dt_s"]),
                "positive_frequency_bins": empty_if_none(row["positive_frequency_bins"]),
                "bins_after_cutoff": empty_if_none(row["bins_after_cutoff"]),
                "minimum_frequency_hz": empty_if_none(row["minimum_frequency_hz"]),
                "maximum_frequency_hz": empty_if_none(row["maximum_frequency_hz"]),
                "lnlike": empty_if_none(row["lnlike"]),
                "BIC": empty_if_none(row["BIC"]),
                "rchi2": empty_if_none(row["rchi2"]),
                "probability": empty_if_none(row["probability"]),
                "parameters_json": empty_if_none(row["parameters_json"]),
                "estimated_period_s": empty_if_none(row["estimated_period_s"]),
                "parameter_at_bound": parse_database_bool(row["parameter_at_bound"]),
                "bound_indices_json": empty_if_none(row["bound_indices_json"]),
                "warning_count": empty_if_none(row["warning_count"]),
                "warning_types_json": empty_if_none(row["warning_types_json"]),
                "convergence_status": row["convergence_status"],
                "error": empty_if_none(row["error"]),
            }
        )
    write_csv(output_path, RESULT_FIELDNAMES, export_rows)
    return export_rows


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
        valid_models = sum(by_model[model]["status"] == "OK" for model in MODEL_SPECS)
        valid = valid_models == 3
        delta01: float | str = ""
        delta21: float | str = ""
        selected: bool | str = ""
        estimated_period: float | str = ""
        period_label = ""
        if by_model["M1"]["status"] == "OK":
            estimated_period = float(by_model["M1"]["estimated_period_s"])
            period_label = "formal_m1_center_not_selected"
        if valid:
            delta01 = float(by_model["M0"]["BIC"]) - float(by_model["M1"]["BIC"])
            delta21 = float(by_model["M2"]["BIC"]) - float(by_model["M1"]["BIC"])
            selected = bool(delta01 > 10.0 and delta21 > 10.0)
            if selected:
                period_label = "recovered_period_selected"

        exemplar = by_model["M0"]
        decisions.append(
            {
                "series_id": key[0],
                "condition_id": exemplar["condition_id"],
                "ground_truth": exemplar["ground_truth"],
                "external_optimizer_seed": key[1],
                "valid_models": valid_models,
                "delta_bic_0_1": delta01,
                "delta_bic_2_1": delta21,
                "qpp_selected": selected,
                "estimated_period_s": estimated_period,
                "period_label": period_label,
            }
        )
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
        row
        for row in plan_rows
        if row["condition_id"] in REPLAY_CONDITION_IDS
        and row["data_seed"] == 0
        and row["external_optimizer_seed"] == 0
    ]
    if len(targets) != EXPECTED_REPLAY_COMPARISONS:
        raise RuntimeError(f"Se esperaban seis trabajos de replay y hay {len(targets)}.")

    connection = connect_checkpoint(checkpoint, readonly=True)
    try:
        originals = {
            row["job_id"]: dict(row)
            for row in connection.execute("SELECT * FROM results")
        }
    finally:
        connection.close()

    comparisons: list[dict[str, Any]] = []
    for job in targets:
        if job["job_id"] not in originals:
            raise RuntimeError(f"Falta el resultado original de {job['job_id']}.")
        replay = execute_one_job(job, dataset)
        passed, detail = exact_replay_compare(originals[job["job_id"]], replay)
        comparisons.append(
            {
                "job_id": job["job_id"],
                "series_id": job["series_id"],
                "condition_id": job["condition_id"],
                "model_id": job["model_id"],
                "passed": passed,
                **detail,
            }
        )
        print(f"REPLAY {job['job_id']} {job['model_id']}: {'PASS' if passed else 'FAIL'}")

    passed_count = sum(item["passed"] for item in comparisons)
    return {
        "expected_count": EXPECTED_REPLAY_COMPARISONS,
        "passed_count": passed_count,
        "failed_count": EXPECTED_REPLAY_COMPARISONS - passed_count,
        "comparisons": comparisons,
    }


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
    lines = [
        f"Python: {environment['python_version']}",
        f"Python full: {environment['python_full']}",
        f"Python executable relative: {environment['python_executable_relative']}",
        f"NumPy: {environment['numpy_version']}",
        f"SciPy: {environment['scipy_version']}",
        f"Platform: {environment['platform']}",
        f"Machine: {environment['machine']}",
        f"Processor: {environment['processor']}",
        f"AFINO commit: {environment['commit']}",
        f"AFINO package version: {environment['afino_version']}",
        f"Tracked diff exit code: {environment['tracked_diff_exit_code']}",
        f"Staged diff exit code: {environment['staged_diff_exit_code']}",
        "Git status --porcelain:",
        environment["git_status"] or "<empty>",
        "",
        "pip freeze:",
        *environment["pip_freeze"],
        "",
    ]
    return "\n".join(lines)


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


def finalize_canary(
    *,
    plan_rows: list[dict[str, Any]],
    checkpoint: Path,
    results_path: Path,
    decisions_path: Path,
    audit_path: Path,
    report_path: Path,
    environment_path: Path,
    environment: dict[str, Any],
    physical_hashes: dict[str, str],
    logical_hashes: dict[str, str],
    replay: dict[str, Any],
) -> dict[str, Any]:
    state = read_checkpoint_audit(checkpoint)
    results = state["results"]
    invocations = state["invocations"]
    duplicates = duplicate_counts(results)

    result_rows = export_results(checkpoint, plan_rows, results_path)
    decision_rows = export_decisions(result_rows, decisions_path)

    if len(results) != 48 or len(result_rows) != 48:
        raise RuntimeError("El checkpoint o export canary no contiene 48 resultados.")
    if len(decision_rows) != 16:
        raise RuntimeError("El canary no contiene 16 decisiones.")
    if len(invocations) != 3:
        raise RuntimeError(
            f"Se esperaban exactamente tres invocaciones canary; observadas {len(invocations)}."
        )

    completed_sequence = [int(row["committed_new"]) for row in invocations]
    if completed_sequence != [17, 31, 0]:
        raise RuntimeError(
            f"Secuencia de reanudación incorrecta: {completed_sequence}; esperada [17, 31, 0]."
        )
    if duplicates != {
        "duplicate_job_id_rows": 0,
        "duplicate_scientific_key_rows": 0,
    }:
        raise RuntimeError(f"Se detectaron duplicados: {duplicates}.")
    if replay["passed_count"] != 6:
        raise RuntimeError("Los seis replays no coinciden exactamente.")

    # Postflight: prove that canary execution and replay did not alter AFINO,
    # the frozen dataset, the plans or the builder.
    post_environment = verify_environment()
    post_physical_hashes, post_logical_hashes = verify_frozen_files()
    if post_physical_hashes != physical_hashes:
        raise RuntimeError("Algún artefacto físico cambió durante el canary.")
    if post_logical_hashes != logical_hashes:
        raise RuntimeError("Algún payload lógico cambió durante el canary.")
    for field in (
        "commit",
        "afino_version",
        "tracked_diff_exit_code",
        "staged_diff_exit_code",
    ):
        if post_environment[field] != environment[field]:
            raise RuntimeError(f"El entorno AFINO cambió durante el canary: {field}.")

    environment_path.write_text(environment_text(post_environment), encoding="utf-8")

    full_plan_rows = read_csv(FULL_PLAN_CSV)
    primary_rows = sum(row["job_class"] == "primary" for row in full_plan_rows)
    stability_rows = sum(row["job_class"] == "stability" for row in full_plan_rows)
    status_counts = Counter(row["status"] for row in results)

    all_structural_pass = (
        len(full_plan_rows) == 16317
        and primary_rows == 13320
        and stability_rows == 2997
        and len(plan_rows) == 48
        and len(results) == 48
        and completed_sequence == [17, 31, 0]
        and not any(duplicates.values())
        and replay["passed_count"] == 6
        and all(row["input_flux_sha256"] for row in results)
        and all(row["input_time_sha256"] for row in results)
    )
    validation_conclusion = (
        "RUNNER_VALIDATED_BEFORE_FULL_BENCHMARK"
        if all_structural_pass
        else "RUNNER_VALIDATION_BLOCKED"
    )

    # Hash checkpoint only after all three invocations are committed and the DB is closed.
    checkpoint_sha = sha256(checkpoint)
    output_hashes = {
        "fase1_tarea04_build_execution_plan.py": sha256(BUILD_PLAN_SCRIPT),
        "fase1_tarea04_full_execution_plan.csv": sha256(FULL_PLAN_CSV),
        "fase1_tarea04_canary_plan.csv": sha256(CANARY_PLAN_CSV),
        Path(__file__).resolve().name: sha256(Path(__file__).resolve()),
        checkpoint.name: checkpoint_sha,
        results_path.name: sha256(results_path),
        decisions_path.name: sha256(decisions_path),
        environment_path.name: sha256(environment_path),
    }

    audit = {
        "date_utc": utc_now(),
        "runner_implementation_version": RUNNER_IMPLEMENTATION_VERSION,
        "validation_conclusion": validation_conclusion,
        "environment": environment,
        "preflight": {
            "dataset_physical_hashes": physical_hashes,
            "dataset_logical_hashes": logical_hashes,
            "afino_commit_verified": environment["commit"] == EXPECTED_AFINO_COMMIT,
            "afino_version_verified": environment["afino_version"] == EXPECTED_AFINO_VERSION,
            "tracked_git_diff_empty": environment["tracked_diff_exit_code"] == 0,
            "staged_git_diff_empty": environment["staged_diff_exit_code"] == 0,
            "git_status_porcelain": environment["git_status"],
            "persisted_time_used_directly_in_seconds": True,
            "tbjd_conversion_reapplied": False,
        },
        "postflight": {
            "dataset_physical_hashes": post_physical_hashes,
            "dataset_logical_hashes": post_logical_hashes,
            "dataset_unchanged": post_physical_hashes == physical_hashes
            and post_logical_hashes == logical_hashes,
            "afino_commit": post_environment["commit"],
            "afino_version": post_environment["afino_version"],
            "tracked_git_diff_empty": post_environment["tracked_diff_exit_code"] == 0,
            "staged_git_diff_empty": post_environment["staged_diff_exit_code"] == 0,
            "git_status_porcelain": post_environment["git_status"],
            "plans_and_builder_unchanged": (
                post_physical_hashes[BUILD_PLAN_SCRIPT.name]
                == EXPECTED_BUILD_PLAN_SCRIPT_SHA256
                and post_physical_hashes[FULL_PLAN_CSV.name]
                == EXPECTED_FULL_PLAN_SHA256
                and post_physical_hashes[CANARY_PLAN_CSV.name]
                == EXPECTED_CANARY_PLAN_SHA256
            ),
        },
        "plan": {
            "full_plan_rows": len(full_plan_rows),
            "primary_plan_rows": primary_rows,
            "stability_plan_rows": stability_rows,
            "canary_plan_rows": len(plan_rows),
            "full_plan_sha256": sha256(FULL_PLAN_CSV),
            "canary_plan_sha256": sha256(CANARY_PLAN_CSV),
            "unique_full_plan_job_ids": len({row["job_id"] for row in full_plan_rows}),
            "unique_full_plan_scientific_keys": len(
                {
                    (
                        row["series_id"],
                        row["external_optimizer_seed"],
                        row["model_id"],
                    )
                    for row in full_plan_rows
                }
            ),
        },
        "canary": {
            "condition_ids": list(CANARY_CONDITION_IDS),
            "canary_completed_rows": len(results),
            "result_status_counts": dict(status_counts),
            "decision_rows": len(decision_rows),
            "canary_results_eligible_for_primary_analysis": False,
            "scientific_rates_computed": False,
        },
        "resume_test": {
            "resume_first_pass_completed": completed_sequence[0],
            "resume_second_pass_new": completed_sequence[1],
            "resume_third_pass_new": completed_sequence[2],
            "invocations": invocations,
            "duplicate_result_rows": sum(duplicates.values()),
            **duplicates,
        },
        "exact_replay": replay,
        "checkpoint": {
            "filename": checkpoint.name,
            "sha256": checkpoint_sha,
            "result_rows": len(results),
            "metadata": state["metadata"],
            "sqlite_transaction_policy": "one independent transaction per completed model call",
            "unique_job_id_enforced": True,
            "unique_series_seed_model_enforced": True,
        },
        "protocol": {
            "low_frequency_cutoff_hz": LOW_FREQUENCY_CUTOFF_HZ,
            "models": MODEL_SPECS,
            "M1_bounds": [list(bounds) for bounds in OVERWRITE_GAUSS_BOUNDS],
            "seed_reset_before_each_model_call": True,
            "selection_rule": (
                "(BIC_M0 - BIC_M1 > 10.0) and "
                "(BIC_M2 - BIC_M1 > 10.0)"
            ),
            "convergence_status": "NOT_AUDITABLE",
        },
        "output_hashes": output_hashes,
        "incidents": [],
        "confirmations": {
            "full_benchmark_executed": False,
            "canary_results_used_for_tuning": False,
            "afino_code_modified": False,
            "dataset_modified": False,
            "dataset_regenerated": False,
            "scientific_protocol_modified": False,
            "canary_results_eligible_for_primary_analysis": False,
        },
    }

    diagnosis = report_diagnosis(audit)
    report = f"""# Fase 1 — Tarea 1.4

## Congelación del plan y validación del runner reanudable

**Conclusión:** `{validation_conclusion}`  
**Runner implementation:** `{RUNNER_IMPLEMENTATION_VERSION}`  
**AFINO commit:** `{environment['commit']}`  
**AFINO:** `{environment['afino_version']}`  
**Plan completo ejecutado:** no  
**Canary:** 48 llamadas  

## 1. Entorno y preflight

Se verificaron los hashes físicos y lógicos de F1.3 antes de cualquier llamada. Los tiempos persistidos se entregaron directamente en segundos relativos. El repositorio AFINO no contenía cambios tracked ni staged. El estado no versionado se conserva en la auditoría y puede incluir `afino.egg-info/`.

## 2. Plan normativo

| Bloque | Trabajos |
|---|---:|
| Primario | 13.320 |
| Estabilidad | 2.997 |
| **Plan completo** | **16.317** |
| Canary | 48 |

El plan completo conserva claves únicas `(series_id, external_optimizer_seed, model_id)` y no fue ejecutado durante F1.4.

## 3. Checkpoint y reanudación

| Pasada | Trabajos nuevos | Total confirmado |
|---|---:|---:|
| Primera (`--stop-after 17`) | 17 | 17 |
| Segunda | 31 | 48 |
| Tercera | 0 | 48 |

Duplicados: 0. Cada llamada confirmada corresponde a una transacción SQLite independiente.

## 4. Repetibilidad directa

Los seis replays predeclarados coincidieron exactamente: `{replay['passed_count']}/6`. La comparación incluyó BIC, log-likelihood, parámetros, periodo formal de M1, rchi2, probabilidad, warnings y bounds.

## 5. Resultados canary

Se exportaron 48 filas de modelo y 16 decisiones únicamente para comprobar la infraestructura. No se presentan tasas de detección o selección y las decisiones canary no son elegibles para el análisis primario.

## 6. Hashes congelados

| Artefacto | SHA-256 |
|---|---|
""" + "\n".join(
        f"| `{filename}` | `{digest}` |"
        for filename, digest in output_hashes.items()
    ) + f"""

## 7. Incidencias

No se registraron incidencias mecánicas. Los resultados científicos del canary no se utilizaron para alterar el protocolo.

## 8. Diagnóstico

{diagnosis}

## 9. Conclusión

`{validation_conclusion}`
"""

    audit_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(report, encoding="utf-8")
    return audit


# =============================================================================
# CLI
# =============================================================================


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Runner AFINO reanudable y checkpointed para F1.4/F1.5."
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
    parser.add_argument("--environment", type=Path, default=DEFAULT_ENVIRONMENT)
    parser.add_argument("--allow-full-plan", action="store_true")
    return parser


def resolve_under_root(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan_path = resolve_under_root(args.plan)
    checkpoint = resolve_under_root(args.checkpoint)
    export_path = resolve_under_root(args.export) if args.export else None
    decisions_path = resolve_under_root(args.decisions) if args.decisions else None
    audit_path = resolve_under_root(args.audit)
    report_path = resolve_under_root(args.report)
    environment_path = resolve_under_root(args.environment)

    if args.finalize_canary and (export_path is None or decisions_path is None):
        raise RuntimeError(
            "--finalize-canary exige --export y --decisions en la misma invocación."
        )
    if args.finalize_canary and not args.replay:
        raise RuntimeError("--finalize-canary exige --replay.")

    print("F1.4 — RUNNER AFINO CHECKPOINTED", flush=True)
    print(f"Runner implementation: {RUNNER_IMPLEMENTATION_VERSION}", flush=True)
    environment = verify_environment()
    physical_hashes, logical_hashes = verify_frozen_files()
    dataset = load_dataset()
    plan_rows, plan_kind = load_plan(plan_path, dataset)
    if args.finalize_canary and plan_kind != "canary":
        raise RuntimeError("La finalización F1.4 solo admite el plan canary.")

    runner_sha = sha256(Path(__file__).resolve())
    print(f"Runner SHA-256: {runner_sha}", flush=True)
    print(f"Plan: {plan_path.name} ({plan_kind}, {len(plan_rows)} filas)", flush=True)
    print("Hashes físicos y lógicos de F1.3: verificados", flush=True)
    print(f"AFINO commit: {environment['commit']}", flush=True)
    print(f"AFINO version: {environment['afino_version']}", flush=True)

    summary = run_plan(
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
        result_rows = export_results(checkpoint, plan_rows, export_path)
        print(f"Exportados {len(result_rows)} resultados a {export_path.name}")
    if decisions_path is not None:
        if result_rows is None:
            result_rows = fetch_results_for_plan(checkpoint, plan_rows)
        decision_rows = export_decisions(result_rows, decisions_path)
        print(f"Exportadas {len(decision_rows)} decisiones a {decisions_path.name}")

    replay = None
    if args.replay:
        replay = run_replays(checkpoint, plan_rows, dataset)
        print(
            f"Exact replay: {replay['passed_count']}/{replay['expected_count']}",
            flush=True,
        )

    if args.finalize_canary:
        assert export_path is not None
        assert decisions_path is not None
        assert replay is not None
        audit = finalize_canary(
            plan_rows=plan_rows,
            checkpoint=checkpoint,
            results_path=export_path,
            decisions_path=decisions_path,
            audit_path=audit_path,
            report_path=report_path,
            environment_path=environment_path,
            environment=environment,
            physical_hashes=physical_hashes,
            logical_hashes=logical_hashes,
            replay=replay,
        )
        print(f"Conclusión: {audit['validation_conclusion']}")
        print(f"Checkpoint SHA-256: {audit['checkpoint']['sha256']}")
        print(f"Auditoría: {audit_path.name}")
        print(f"Informe: {report_path.name}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RUNNER_VALIDATION_BLOCKED: {exc}", file=sys.stderr, flush=True)
        raise
