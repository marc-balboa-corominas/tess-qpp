from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import math
import platform
import subprocess
import sys
import time
import traceback
import warnings
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from afino import afino_series
from afino.afino_main_analysis3 import main_analysis


# =============================================================================
# Protocolo congelado F0.8
# =============================================================================

EXPECTED_COMMIT = "6aceac9518fc8056052807e666da9d0c8bebb010"
EXPECTED_MANIFEST_SHA256 = (
    "38b9a47929fcde55ef94e197270c7782906f44080b0aead00b09dccded1e7c5d"
)

ROOT = Path(__file__).resolve().parent
REPO = ROOT / "afino_release_version"
INPUT_DIR = ROOT / "fase0_tarea06_tess_reconstruction"
INPUT_MANIFEST = INPUT_DIR / "fase0_tarea07_pilot_input_manifest.csv"

RESULTS_CSV = ROOT / "fase0_tarea08_real_pilot_results.csv"
EXECUTION_LOG = ROOT / "fase0_tarea08_execution_log.txt"
EXECUTION_AUDIT = ROOT / "fase0_tarea08_execution_audit.json"
ENVIRONMENT_FILE = ROOT / "fase0_tarea08_environment.txt"

LOW_FREQUENCY_CUTOFF_HZ = 1.0 / 40.0
PUBLISHED_PERIOD_S = 68.52768338
PUBLISHED_DELTA_BIC_0_1 = 17.01318061
PUBLISHED_DELTA_BIC_2_1 = 14.57959220

OPTIMIZER_SEEDS = tuple(range(10))

OVERWRITE_GAUSS_BOUNDS = (
    (-10.0, 10.0),
    (-1.0, 6.0),
    (-20.0, 10.0),
    (-16.0, 5.0),
    (float(np.log(1.0 / 300.0)), float(np.log(1.0 / 40.0))),
    (0.05, 0.25),
)

MODEL_SPECS = (
    ("M0", "pow_const"),
    ("M1", "pow_const_gauss"),
    ("M2", "bpow_const"),
)

# Bounds used only for external diagnostics. M1 uses the explicitly frozen
# overwrite; M0 and M2 retain the public defaults.
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

BOUND_ATOL = 1.0e-7
SECONDS_PER_DAY = 86400.0

EXPECTED_VARIANTS = (
    {
        "variant_id": "published_qpp_pdcsap_all",
        "filename": "fase0_tarea07_published_qpp_pdcsap_all.csv",
        "event_role": "published_qpp",
        "flux_type": "PDCSAP_FLUX",
        "quality_policy": "finite_all",
        "sampling_status": "regular",
        "execution_role": "primary_pilot",
        "interpretation_scope": "scientific_candidate",
    },
    {
        "variant_id": "published_qpp_sap_all",
        "filename": "fase0_tarea07_published_qpp_sap_all.csv",
        "event_role": "published_qpp",
        "flux_type": "SAP_FLUX",
        "quality_policy": "finite_all",
        "sampling_status": "regular",
        "execution_role": "predeclared_comparison",
        "interpretation_scope": "scientific_candidate",
    },
    {
        "variant_id": "published_qpp_pdcsap_q0",
        "filename": "fase0_tarea07_published_qpp_pdcsap_q0.csv",
        "event_role": "published_qpp",
        "flux_type": "PDCSAP_FLUX",
        "quality_policy": "quality_zero_only",
        "sampling_status": "regular",
        "execution_role": "predeclared_comparison",
        "interpretation_scope": "scientific_candidate",
    },
    {
        "variant_id": "published_qpp_sap_q0",
        "filename": "fase0_tarea07_published_qpp_sap_q0.csv",
        "event_role": "published_qpp",
        "flux_type": "SAP_FLUX",
        "quality_policy": "quality_zero_only",
        "sampling_status": "regular",
        "execution_role": "predeclared_comparison",
        "interpretation_scope": "scientific_candidate",
    },
    {
        "variant_id": "notselected_pdcsap_all",
        "filename": "fase0_tarea07_notselected_pdcsap_all.csv",
        "event_role": "not_selected_qpp",
        "flux_type": "PDCSAP_FLUX",
        "quality_policy": "finite_all",
        "sampling_status": "regular",
        "execution_role": "predeclared_comparison",
        "interpretation_scope": "scientific_candidate",
    },
    {
        "variant_id": "notselected_sap_all",
        "filename": "fase0_tarea07_notselected_sap_all.csv",
        "event_role": "not_selected_qpp",
        "flux_type": "SAP_FLUX",
        "quality_policy": "finite_all",
        "sampling_status": "regular",
        "execution_role": "predeclared_comparison",
        "interpretation_scope": "scientific_candidate",
    },
    {
        "variant_id": "notselected_pdcsap_q0",
        "filename": "fase0_tarea07_notselected_pdcsap_q0.csv",
        "event_role": "not_selected_qpp",
        "flux_type": "PDCSAP_FLUX",
        "quality_policy": "quality_zero_only",
        "sampling_status": "diagnostic_irregular_sampling",
        "execution_role": "predeclared_comparison",
        "interpretation_scope": "diagnostic_only",
    },
    {
        "variant_id": "notselected_sap_q0",
        "filename": "fase0_tarea07_notselected_sap_q0.csv",
        "event_role": "not_selected_qpp",
        "flux_type": "SAP_FLUX",
        "quality_policy": "quality_zero_only",
        "sampling_status": "diagnostic_irregular_sampling",
        "execution_role": "predeclared_comparison",
        "interpretation_scope": "diagnostic_only",
    },
)

INPUT_COLUMNS = (
    "time_tbjd",
    "flux",
    "quality",
    "cadence_index_within_window",
)

FIELDNAMES = [
    "variant_id",
    "event_role",
    "flux_type",
    "quality_policy",
    "window_variant",
    "sampling_status",
    "execution_role",
    "interpretation_scope",
    "input_filename",
    "input_sha256",
    "optimizer_seed",
    "model_id",
    "model",
    "status",
    "runtime_seconds",
    "n_samples",
    "median_cadence_s",
    "max_gap_s",
    "afino_effective_dt_s",
    "sampling_interval_min_s",
    "sampling_interval_max_s",
    "sampling_max_deviation_from_median_s",
    "fft_positive_bins_before_cutoff",
    "fft_bins_after_cutoff",
    "frequency_min_hz",
    "frequency_max_hz",
    "low_frequency_cutoff_hz",
    "lnlike",
    "BIC",
    "rchi2",
    "probability",
    "estimated_period_s",
    "parameters_json",
    "parameter_at_bound",
    "bound_hits_json",
    "warning_count",
    "warning_types",
    "warnings_json",
    "error",
    "delta_bic_0_1",
    "delta_bic_2_1",
    "qpp_selected",
    "published_selection_comparison",
    "period_absolute_difference_s",
    "period_relative_difference_percent",
    "delta_bic_0_1_difference_from_published",
    "delta_bic_2_1_difference_from_published",
    "manifest_sha256",
    "script_sha256",
    "afino_commit",
    "afino_version",
    "python_version",
]


# =============================================================================
# Generic helpers
# =============================================================================

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    return run_command(
        ["git", "-C", str(REPO), *args],
        check=check,
    )


def json_compact(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def finite_float(value: Any, name: str) -> float:
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{name} no es finito: {converted!r}")
    return converted


def floats_equal_exact(left: Any, right: Any) -> bool:
    left_float = float(left)
    right_float = float(right)

    if math.isnan(left_float) and math.isnan(right_float):
        return True

    return left_float == right_float


# =============================================================================
# Preflight and input validation
# =============================================================================

def verify_environment() -> dict[str, Any]:
    if not REPO.is_dir():
        raise RuntimeError(f"No existe el repositorio esperado: {REPO}")

    expected_python = (ROOT / ".venv" / "Scripts" / "python.exe").resolve()
    observed_python = Path(sys.executable).resolve()

    if observed_python != expected_python:
        raise RuntimeError(
            "No se está usando el intérprete congelado de AFINO.\n"
            f"Esperado: {expected_python}\n"
            f"Observado: {observed_python}"
        )

    commit = git("rev-parse", "HEAD").stdout.strip()
    if commit != EXPECTED_COMMIT:
        raise RuntimeError(
            f"Commit incorrecto: {commit}. Se esperaba {EXPECTED_COMMIT}."
        )

    tracked_exit = git("diff", "--quiet", check=False).returncode
    staged_exit = git("diff", "--cached", "--quiet", check=False).returncode

    if tracked_exit != 0 or staged_exit != 0:
        raise RuntimeError(
            "Hay cambios versionados o preparados para commit en "
            "AFINO-public."
        )

    git_status = git("status", "--short").stdout.strip()

    freeze = run_command(
        [sys.executable, "-m", "pip", "freeze"],
        check=True,
    ).stdout

    ENVIRONMENT_FILE.write_text(
        freeze,
        encoding="utf-8",
        newline="\n",
    )

    return {
        "commit": commit,
        "git_status": git_status,
        "tracked_diff_exit_code": tracked_exit,
        "staged_diff_exit_code": staged_exit,
        "python": sys.version,
        "python_executable": str(observed_python),
        "platform": platform.platform(),
        "afino_version": importlib.metadata.version("afino"),
        "environment_sha256": sha256(ENVIRONMENT_FILE),
        "script_sha256": sha256(Path(__file__).resolve()),
    }


def read_manifest() -> dict[str, dict[str, str]]:
    if not INPUT_MANIFEST.exists():
        raise FileNotFoundError(
            f"No existe el manifiesto congelado: {INPUT_MANIFEST}"
        )

    manifest_hash = sha256(INPUT_MANIFEST)
    if manifest_hash != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError(
            "El manifiesto F0.7 no coincide con la versión congelada.\n"
            f"Esperado: {EXPECTED_MANIFEST_SHA256}\n"
            f"Observado: {manifest_hash}"
        )

    with INPUT_MANIFEST.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    if len(rows) != 8:
        raise RuntimeError(
            f"El manifiesto contiene {len(rows)} filas, no 8."
        )

    by_filename = {row["output_filename"]: row for row in rows}

    if len(by_filename) != 8:
        raise RuntimeError("El manifiesto contiene nombres duplicados.")

    expected_names = {
        specification["filename"]
        for specification in EXPECTED_VARIANTS
    }
    if set(by_filename) != expected_names:
        raise RuntimeError(
            "Los archivos del manifiesto no coinciden con las ocho "
            "variantes predeclaradas."
        )

    for specification in EXPECTED_VARIANTS:
        row = by_filename[specification["filename"]]

        for field in (
            "event_role",
            "flux_type",
            "quality_policy",
        ):
            if row[field] != specification[field]:
                raise RuntimeError(
                    f"{specification['filename']}: {field} inesperado. "
                    f"Esperado={specification[field]!r}, "
                    f"observado={row[field]!r}."
                )

        if row["window_variant"] != "tau0_published":
            raise RuntimeError(
                f"{specification['filename']} no usa tau0_published."
            )

    return by_filename


def load_and_validate_inputs(
    manifest: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    loaded: list[dict[str, Any]] = []

    for specification in EXPECTED_VARIANTS:
        manifest_row = manifest[specification["filename"]]
        path = INPUT_DIR / specification["filename"]

        if not path.exists():
            raise FileNotFoundError(f"No existe la entrada: {path}")

        observed_hash = sha256(path)
        expected_hash = manifest_row["output_sha256"]

        if observed_hash != expected_hash:
            raise RuntimeError(
                f"Hash incorrecto para {path.name}.\n"
                f"Esperado: {expected_hash}\n"
                f"Observado: {observed_hash}"
            )

        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != INPUT_COLUMNS:
                raise RuntimeError(
                    f"Columnas incorrectas en {path.name}: "
                    f"{reader.fieldnames!r}"
                )
            source_rows = list(reader)

        if not source_rows:
            raise RuntimeError(f"{path.name} está vacío.")

        time_tbjd = np.asarray(
            [float(row["time_tbjd"]) for row in source_rows],
            dtype=float,
        )
        flux = np.asarray(
            [float(row["flux"]) for row in source_rows],
            dtype=float,
        )
        quality = np.asarray(
            [int(row["quality"]) for row in source_rows],
            dtype=np.int64,
        )
        cadence_indices = np.asarray(
            [
                int(row["cadence_index_within_window"])
                for row in source_rows
            ],
            dtype=np.int64,
        )

        if not np.all(np.isfinite(time_tbjd)):
            raise RuntimeError(f"{path.name} contiene TIME no finito.")
        if not np.all(np.isfinite(flux)):
            raise RuntimeError(f"{path.name} contiene flujo no finito.")
        if not np.all(np.diff(time_tbjd) > 0):
            raise RuntimeError(
                f"{path.name} no tiene tiempo estrictamente creciente."
            )
        if len(source_rows) != int(manifest_row["n_rows_used"]):
            raise RuntimeError(
                f"{path.name}: el número de filas no coincide con el "
                "manifiesto."
            )

        if specification["sampling_status"] == "regular":
            differences_s = np.diff(time_tbjd) * SECONDS_PER_DAY
            if not np.allclose(
                differences_s,
                np.median(differences_s),
                rtol=0.0,
                atol=1.0e-3,
            ):
                raise RuntimeError(
                    f"{path.name} estaba etiquetada como regular pero no "
                    "superó la comprobación previa."
                )
        else:
            if specification["sampling_status"] != (
                "diagnostic_irregular_sampling"
            ):
                raise RuntimeError("sampling_status desconocido.")

        # Única transformación autorizada, solo en memoria.
        time_seconds = (
            time_tbjd - time_tbjd[0]
        ) * SECONDS_PER_DAY

        differences_s = np.diff(time_seconds)
        median_cadence_s = float(np.median(differences_s))
        max_gap_s = float(np.max(differences_s))
        min_interval_s = float(np.min(differences_s))
        max_interval_s = float(np.max(differences_s))
        max_deviation_s = float(
            np.max(np.abs(differences_s - median_cadence_s))
        )

        loaded.append(
            {
                **specification,
                "path": path,
                "input_sha256": observed_hash,
                "manifest_row": manifest_row,
                "time_tbjd": time_tbjd,
                "time_seconds": time_seconds,
                "flux": flux,
                "quality": quality,
                "cadence_indices": cadence_indices,
                "n_samples": len(source_rows),
                "median_cadence_s": median_cadence_s,
                "max_gap_s": max_gap_s,
                "sampling_interval_min_s": min_interval_s,
                "sampling_interval_max_s": max_interval_s,
                "sampling_max_deviation_from_median_s": max_deviation_s,
            }
        )

    return loaded


# =============================================================================
# Model execution and diagnostics
# =============================================================================

def inspect_bounds(
    model: str,
    parameters: np.ndarray,
) -> tuple[bool, list[dict[str, Any]]]:
    bounds = MODEL_BOUNDS[model]
    hits: list[dict[str, Any]] = []

    if len(parameters) != len(bounds):
        return False, [
            {
                "type": "parameter_count_mismatch",
                "parameter_count": len(parameters),
                "bound_count": len(bounds),
            }
        ]

    for index, (value, (lower, upper)) in enumerate(
        zip(parameters, bounds)
    ):
        value_float = float(value)

        if lower is not None and np.isclose(
            value_float,
            lower,
            rtol=0.0,
            atol=BOUND_ATOL,
        ):
            hits.append(
                {
                    "parameter_index": index,
                    "side": "lower",
                    "value": value_float,
                    "bound": float(lower),
                    "absolute_distance": abs(value_float - lower),
                }
            )

        if upper is not None and np.isclose(
            value_float,
            upper,
            rtol=0.0,
            atol=BOUND_ATOL,
        ):
            hits.append(
                {
                    "parameter_index": index,
                    "side": "upper",
                    "value": value_float,
                    "bound": float(upper),
                    "absolute_distance": abs(value_float - upper),
                }
            )

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

    warning_types = sorted(
        {
            f"{entry['category']}: {entry['message']}"
            for entry in entries
        }
    )

    return (
        len(entries),
        json_compact(warning_types),
        json_compact(entries),
    )


def base_row(
    variant: dict[str, Any],
    optimizer_seed: int,
    model_id: str,
    model: str,
    environment: dict[str, Any],
) -> dict[str, Any]:
    return {
        "variant_id": variant["variant_id"],
        "event_role": variant["event_role"],
        "flux_type": variant["flux_type"],
        "quality_policy": variant["quality_policy"],
        "window_variant": "tau0_published",
        "sampling_status": variant["sampling_status"],
        "execution_role": variant["execution_role"],
        "interpretation_scope": variant["interpretation_scope"],
        "input_filename": variant["filename"],
        "input_sha256": variant["input_sha256"],
        "optimizer_seed": optimizer_seed,
        "model_id": model_id,
        "model": model,
        "status": "NOT_RUN",
        "runtime_seconds": "",
        "n_samples": variant["n_samples"],
        "median_cadence_s": variant["median_cadence_s"],
        "max_gap_s": variant["max_gap_s"],
        "afino_effective_dt_s": "",
        "sampling_interval_min_s": variant[
            "sampling_interval_min_s"
        ],
        "sampling_interval_max_s": variant[
            "sampling_interval_max_s"
        ],
        "sampling_max_deviation_from_median_s": variant[
            "sampling_max_deviation_from_median_s"
        ],
        "fft_positive_bins_before_cutoff": "",
        "fft_bins_after_cutoff": "",
        "frequency_min_hz": "",
        "frequency_max_hz": "",
        "low_frequency_cutoff_hz": LOW_FREQUENCY_CUTOFF_HZ,
        "lnlike": "",
        "BIC": "",
        "rchi2": "",
        "probability": "",
        "estimated_period_s": "",
        "parameters_json": "",
        "parameter_at_bound": "",
        "bound_hits_json": "",
        "warning_count": "",
        "warning_types": "",
        "warnings_json": "",
        "error": "",
        "delta_bic_0_1": "",
        "delta_bic_2_1": "",
        "qpp_selected": "",
        "published_selection_comparison": "",
        "period_absolute_difference_s": "",
        "period_relative_difference_percent": "",
        "delta_bic_0_1_difference_from_published": "",
        "delta_bic_2_1_difference_from_published": "",
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "script_sha256": environment["script_sha256"],
        "afino_commit": environment["commit"],
        "afino_version": environment["afino_version"],
        "python_version": sys.version.split()[0],
    }


def run_one_model(
    variant: dict[str, Any],
    optimizer_seed: int,
    model_id: str,
    model: str,
    environment: dict[str, Any],
) -> dict[str, Any]:
    row = base_row(
        variant,
        optimizer_seed,
        model_id,
        model,
        environment,
    )

    started = time.perf_counter()

    try:
        # Fresh objects for every individual call: no cross-call mutation.
        series = afino_series.AfinoSeries(
            variant["time_seconds"].copy(),
            variant["flux"].copy(),
        )
        prepared = afino_series.prep_series(series)

        effective_dt_s = finite_float(
            prepared.SampleTimes.dt,
            "afino_effective_dt_s",
        )
        positive_frequencies = np.asarray(
            prepared.PowerSpectrum.frequencies.positive,
            dtype=float,
        )
        positive_before = int(positive_frequencies.size)

        # Reset immediately before main_analysis, as frozen.
        np.random.seed(optimizer_seed)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")

            if model == "pow_const_gauss":
                result = main_analysis(
                    prepared,
                    model=model,
                    low_frequency_cutoff=LOW_FREQUENCY_CUTOFF_HZ,
                    overwrite_gauss_bounds=OVERWRITE_GAUSS_BOUNDS,
                )
            else:
                result = main_analysis(
                    prepared,
                    model=model,
                    low_frequency_cutoff=LOW_FREQUENCY_CUTOFF_HZ,
                )

        runtime_seconds = time.perf_counter() - started

        parameters = np.asarray(result["params"], dtype=float)
        frequencies = np.asarray(result["frequencies"], dtype=float)

        lnlike = finite_float(result["lnlike"], "lnlike")
        bic = finite_float(result["BIC"], "BIC")
        rchi2 = finite_float(result["rchi2"], "rchi2")
        probability = finite_float(
            result["probability"],
            "probability",
        )

        if not np.all(np.isfinite(parameters)):
            raise ValueError("Los parámetros contienen valores no finitos.")
        if frequencies.size == 0:
            raise ValueError(
                "No quedaron frecuencias tras aplicar el cutoff."
            )
        if not np.all(np.isfinite(frequencies)):
            raise ValueError("Las frecuencias contienen valores no finitos.")

        estimated_period: float | str = ""
        if model == "pow_const_gauss":
            if parameters.size <= 4:
                raise ValueError(
                    "M1 no devolvió params[4] para el centro del bump."
                )
            estimated_period = finite_float(
                1.0 / np.exp(parameters[4]),
                "estimated_period_s",
            )

        at_bound, bound_hits = inspect_bounds(model, parameters)
        warning_count, warning_types, warnings_json = warning_payload(
            list(caught)
        )

        row.update(
            {
                "status": "OK",
                "runtime_seconds": runtime_seconds,
                "afino_effective_dt_s": effective_dt_s,
                "fft_positive_bins_before_cutoff": positive_before,
                "fft_bins_after_cutoff": int(frequencies.size),
                "frequency_min_hz": float(np.min(frequencies)),
                "frequency_max_hz": float(np.max(frequencies)),
                "lnlike": lnlike,
                "BIC": bic,
                "rchi2": rchi2,
                "probability": probability,
                "estimated_period_s": estimated_period,
                "parameters_json": json_compact(
                    parameters.tolist()
                ),
                "parameter_at_bound": at_bound,
                "bound_hits_json": json_compact(bound_hits),
                "warning_count": warning_count,
                "warning_types": warning_types,
                "warnings_json": warnings_json,
                "error": "",
            }
        )

    except Exception:
        runtime_seconds = time.perf_counter() - started
        row.update(
            {
                "status": "ERROR",
                "runtime_seconds": runtime_seconds,
                "error": traceback.format_exc(),
            }
        )

    return row


def attach_decisions(rows: list[dict[str, Any]]) -> None:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        grouped[
            (str(row["variant_id"]), int(row["optimizer_seed"]))
        ].append(row)

    for (variant_id, _seed), group_rows in grouped.items():
        by_model = {
            str(row["model_id"]): row
            for row in group_rows
        }

        valid = (
            set(by_model) == {"M0", "M1", "M2"}
            and all(
                by_model[model_id]["status"] == "OK"
                for model_id in ("M0", "M1", "M2")
            )
        )

        if not valid:
            continue

        delta_0_1 = (
            float(by_model["M0"]["BIC"])
            - float(by_model["M1"]["BIC"])
        )
        delta_2_1 = (
            float(by_model["M2"]["BIC"])
            - float(by_model["M1"]["BIC"])
        )
        selected = bool(
            delta_0_1 > 10.0
            and delta_2_1 > 10.0
        )

        event_role = str(group_rows[0]["event_role"])

        if event_role == "published_qpp":
            selection_comparison = (
                "selection_reproduced"
                if selected
                else "selection_not_reproduced"
            )
            delta_0_difference = (
                delta_0_1 - PUBLISHED_DELTA_BIC_0_1
            )
            delta_2_difference = (
                delta_2_1 - PUBLISHED_DELTA_BIC_2_1
            )
        else:
            selection_comparison = "not_applicable"
            delta_0_difference = ""
            delta_2_difference = ""

        period_absolute: float | str = ""
        period_relative: float | str = ""

        if selected and event_role == "published_qpp":
            period = float(
                by_model["M1"]["estimated_period_s"]
            )
            period_absolute = abs(
                period - PUBLISHED_PERIOD_S
            )
            period_relative = (
                period_absolute
                / PUBLISHED_PERIOD_S
                * 100.0
            )

        for row in group_rows:
            row["delta_bic_0_1"] = delta_0_1
            row["delta_bic_2_1"] = delta_2_1
            row["qpp_selected"] = selected
            row[
                "published_selection_comparison"
            ] = selection_comparison
            row[
                "period_absolute_difference_s"
            ] = period_absolute
            row[
                "period_relative_difference_percent"
            ] = period_relative
            row[
                "delta_bic_0_1_difference_from_published"
            ] = delta_0_difference
            row[
                "delta_bic_2_1_difference_from_published"
            ] = delta_2_difference


# =============================================================================
# Invariants and output
# =============================================================================

def compare_invariant_rows(
    left: dict[str, Any],
    right: dict[str, Any],
) -> dict[str, Any]:
    issues: list[str] = []

    if left["status"] != right["status"]:
        issues.append("status")

    if left["status"] == "OK" and right["status"] == "OK":
        for field in (
            "lnlike",
            "BIC",
            "rchi2",
            "probability",
            "estimated_period_s",
            "delta_bic_0_1",
            "delta_bic_2_1",
        ):
            left_value = left[field]
            right_value = right[field]

            if left_value == "" and right_value == "":
                continue
            if left_value == "" or right_value == "":
                issues.append(field)
                continue
            if not floats_equal_exact(left_value, right_value):
                issues.append(field)

        if left["parameters_json"] != right["parameters_json"]:
            issues.append("parameters_json")

        if left["qpp_selected"] != right["qpp_selected"]:
            issues.append("qpp_selected")

    return {
        "passed": not issues,
        "issues": issues,
    }


def evaluate_invariants(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    row_index = {
        (
            str(row["variant_id"]),
            int(row["optimizer_seed"]),
            str(row["model_id"]),
        ): row
        for row in rows
    }

    definitions = (
        {
            "name": "invariant_A_published_sap_all_equals_q0",
            "left": "published_qpp_sap_all",
            "right": "published_qpp_sap_q0",
        },
        {
            "name": "invariant_B_published_pdcsap_all_equals_q0",
            "left": "published_qpp_pdcsap_all",
            "right": "published_qpp_pdcsap_q0",
        },
    )

    results: list[dict[str, Any]] = []

    for definition in definitions:
        comparisons: list[dict[str, Any]] = []

        for seed in OPTIMIZER_SEEDS:
            for model_id, _model in MODEL_SPECS:
                left = row_index[
                    (definition["left"], seed, model_id)
                ]
                right = row_index[
                    (definition["right"], seed, model_id)
                ]
                comparison = compare_invariant_rows(left, right)

                comparisons.append(
                    {
                        "optimizer_seed": seed,
                        "model_id": model_id,
                        **comparison,
                    }
                )

        results.append(
            {
                **definition,
                "comparison_count": len(comparisons),
                "passed_count": sum(
                    item["passed"]
                    for item in comparisons
                ),
                "all_passed": all(
                    item["passed"]
                    for item in comparisons
                ),
                "comparisons": comparisons,
            }
        )

    return {
        "all_invariants_passed": all(
            item["all_passed"]
            for item in results
        ),
        "invariants": results,
    }


def write_results(rows: list[dict[str, Any]]) -> None:
    with RESULTS_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=FIELDNAMES,
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def summarize_rows(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    summary: dict[str, Any] = {}

    for specification in EXPECTED_VARIANTS:
        variant_id = specification["variant_id"]
        variant_rows = [
            row
            for row in rows
            if row["variant_id"] == variant_id
        ]
        m1_rows = [
            row
            for row in variant_rows
            if row["model_id"] == "M1"
        ]
        valid_decisions = [
            row
            for row in m1_rows
            if row["qpp_selected"] in (True, False)
        ]
        selected_rows = [
            row
            for row in valid_decisions
            if row["qpp_selected"] is True
        ]
        periods = [
            float(row["estimated_period_s"])
            for row in m1_rows
            if row["status"] == "OK"
            and row["estimated_period_s"] != ""
        ]
        d01 = [
            float(row["delta_bic_0_1"])
            for row in valid_decisions
        ]
        d21 = [
            float(row["delta_bic_2_1"])
            for row in valid_decisions
        ]

        warning_count = sum(
            int(row["warning_count"])
            for row in variant_rows
            if row["warning_count"] != ""
        )

        warning_types: Counter[str] = Counter()
        for row in variant_rows:
            if row["warning_types"] in ("", "[]"):
                continue
            for warning_type in json.loads(
                row["warning_types"]
            ):
                warning_types[warning_type] += 1

        summary[variant_id] = {
            "sampling_status": specification[
                "sampling_status"
            ],
            "attempted_calls": len(variant_rows),
            "successful_calls": sum(
                row["status"] == "OK"
                for row in variant_rows
            ),
            "errors": sum(
                row["status"] == "ERROR"
                for row in variant_rows
            ),
            "valid_decisions": len(valid_decisions),
            "m1_selected_count": len(selected_rows),
            "period_median_s": (
                float(np.median(periods))
                if periods
                else None
            ),
            "period_min_s": min(periods) if periods else None,
            "period_max_s": max(periods) if periods else None,
            "delta_bic_0_1_min": min(d01) if d01 else None,
            "delta_bic_0_1_max": max(d01) if d01 else None,
            "delta_bic_2_1_min": min(d21) if d21 else None,
            "delta_bic_2_1_max": max(d21) if d21 else None,
            "rows_at_bound": sum(
                row["parameter_at_bound"] is True
                for row in variant_rows
            ),
            "warning_count": warning_count,
            "warning_types": dict(warning_types),
            "n_samples": specification.get("n_samples"),
            "fft_bins_after_cutoff_values": sorted(
                {
                    int(row["fft_bins_after_cutoff"])
                    for row in variant_rows
                    if row["fft_bins_after_cutoff"] != ""
                }
            ),
            "afino_effective_dt_s_values": sorted(
                {
                    float(row["afino_effective_dt_s"])
                    for row in variant_rows
                    if row["afino_effective_dt_s"] != ""
                }
            ),
        }

    return summary


def main() -> int:
    for output in (
        RESULTS_CSV,
        EXECUTION_LOG,
        EXECUTION_AUDIT,
        ENVIRONMENT_FILE,
    ):
        if output.exists():
            raise FileExistsError(
                f"No se sobrescribirá un artefacto F0.8 existente: "
                f"{output}"
            )

    environment = verify_environment()
    manifest = read_manifest()
    variants = load_and_validate_inputs(manifest)

    expected_calls = (
        len(variants)
        * len(OPTIMIZER_SEEDS)
        * len(MODEL_SPECS)
    )
    if expected_calls != 240:
        raise RuntimeError(
            f"El protocolo no produce 240 llamadas: {expected_calls}."
        )

    print("F0.8 — PILOTO REAL DE AFINO-PUBLIC")
    print(f"Fecha local: {datetime.now().astimezone().isoformat()}")
    print(f"Commit: {environment['commit']}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"AFINO: {environment['afino_version']}")
    print(f"Manifest SHA-256: {EXPECTED_MANIFEST_SHA256}")
    print(f"Script SHA-256: {environment['script_sha256']}")
    print(f"Low-frequency cutoff: {LOW_FREQUENCY_CUTOFF_HZ:.17g} Hz")
    print(
        "M1 center bounds: "
        f"{OVERWRITE_GAUSS_BOUNDS[4][0]:.17g} to "
        f"{OVERWRITE_GAUSS_BOUNDS[4][1]:.17g} ln(Hz)"
    )
    print("AFINO-public code modified: no")
    print("Input CSV files modified: no")
    print("")

    rows: list[dict[str, Any]] = []
    completed = 0
    started_total = time.perf_counter()

    for variant in variants:
        print(
            f"[{variant['variant_id']}] "
            f"N={variant['n_samples']}, "
            f"sampling={variant['sampling_status']}, "
            f"median_dt={variant['median_cadence_s']:.9f} s, "
            f"max_gap={variant['max_gap_s']:.9f} s"
        )

        for optimizer_seed in OPTIMIZER_SEEDS:
            print(f"  seed={optimizer_seed}")

            for model_id, model in MODEL_SPECS:
                row = run_one_model(
                    variant,
                    optimizer_seed,
                    model_id,
                    model,
                    environment,
                )
                rows.append(row)
                completed += 1

                print(
                    f"    {model_id} {model}: {row['status']} "
                    f"({float(row['runtime_seconds']):.3f} s) "
                    f"[{completed}/{expected_calls}]"
                )

    attach_decisions(rows)
    invariants = evaluate_invariants(rows)
    write_results(rows)

    total_runtime = time.perf_counter() - started_total
    summary = summarize_rows(rows)

    audit = {
        "date_local": datetime.now().astimezone().isoformat(),
        "protocol": {
            "variant_count": len(variants),
            "optimizer_seeds": list(OPTIMIZER_SEEDS),
            "models": [
                {"model_id": model_id, "model": model}
                for model_id, model in MODEL_SPECS
            ],
            "expected_calls": expected_calls,
            "attempted_calls": len(rows),
            "low_frequency_cutoff_hz": (
                LOW_FREQUENCY_CUTOFF_HZ
            ),
            "overwrite_gauss_bounds": [
                list(bound)
                for bound in OVERWRITE_GAUSS_BOUNDS
            ],
            "time_transform": (
                "(time_tbjd - time_tbjd[0]) * 86400.0"
            ),
            "external_normalization": False,
            "external_detrending": False,
            "external_smoothing": False,
            "interpolation": False,
            "window_extension": False,
            "afino_code_modified": False,
            "all_variants_executed_regardless_of_earlier_results": True,
        },
        "environment": environment,
        "manifest": {
            "filename": INPUT_MANIFEST.name,
            "sha256": sha256(INPUT_MANIFEST),
        },
        "inputs": [
            {
                "variant_id": variant["variant_id"],
                "filename": variant["filename"],
                "sha256": variant["input_sha256"],
                "event_role": variant["event_role"],
                "flux_type": variant["flux_type"],
                "quality_policy": variant["quality_policy"],
                "sampling_status": variant["sampling_status"],
                "execution_role": variant["execution_role"],
                "interpretation_scope": variant[
                    "interpretation_scope"
                ],
                "n_samples": variant["n_samples"],
                "median_cadence_s": variant[
                    "median_cadence_s"
                ],
                "max_gap_s": variant["max_gap_s"],
                "sampling_interval_min_s": variant[
                    "sampling_interval_min_s"
                ],
                "sampling_interval_max_s": variant[
                    "sampling_interval_max_s"
                ],
            }
            for variant in variants
        ],
        "published_reference": {
            "period_s": PUBLISHED_PERIOD_S,
            "delta_bic_0_1": PUBLISHED_DELTA_BIC_0_1,
            "delta_bic_2_1": PUBLISHED_DELTA_BIC_2_1,
        },
        "invariants": invariants,
        "summary_by_variant": summary,
        "results_csv": {
            "filename": RESULTS_CSV.name,
            "sha256": sha256(RESULTS_CSV),
            "row_count": len(rows),
        },
        "total_runtime_seconds": total_runtime,
        "status_counts": dict(
            Counter(str(row["status"]) for row in rows)
        ),
        "afino_convergence_formally_auditable": False,
        "convergence_note": (
            "main_analysis does not return or check res.success or "
            "res.message."
        ),
    }

    EXECUTION_AUDIT.write_text(
        json.dumps(
            audit,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    log_lines = [
        "===== F0.8 — RESUMEN DE EJECUCIÓN =====",
        f"Fecha local: {audit['date_local']}",
        f"Commit: {environment['commit']}",
        f"Git status: {environment['git_status']}",
        f"Python: {environment['python']}",
        f"AFINO version: {environment['afino_version']}",
        f"Script SHA-256: {environment['script_sha256']}",
        f"Manifest SHA-256: {sha256(INPUT_MANIFEST)}",
        f"Environment SHA-256: {environment['environment_sha256']}",
        f"Llamadas esperadas: {expected_calls}",
        f"Llamadas intentadas: {len(rows)}",
        f"Duración total (s): {total_runtime:.6f}",
        f"Status counts: {audit['status_counts']}",
        (
            "Invariantes idénticos superados: "
            f"{invariants['all_invariants_passed']}"
        ),
        (
            "Convergencia formal: NO AUDITABLE; main_analysis no "
            "devuelve ni comprueba res.success."
        ),
        "",
        "RESUMEN POR VARIANTE",
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ),
        "",
        "INVARIANTES",
        json.dumps(
            invariants,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ),
        "",
        f"Results CSV SHA-256: {sha256(RESULTS_CSV)}",
        f"Audit JSON SHA-256: {sha256(EXECUTION_AUDIT)}",
    ]

    EXECUTION_LOG.write_text(
        "\n".join(log_lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print("")
    print("\n".join(log_lines))

    if len(rows) != expected_calls:
        return 2

    errors = sum(row["status"] != "OK" for row in rows)
    invariant_failure = not invariants["all_invariants_passed"]

    if errors and invariant_failure:
        return 5
    if errors:
        return 3
    if invariant_failure:
        return 4

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
