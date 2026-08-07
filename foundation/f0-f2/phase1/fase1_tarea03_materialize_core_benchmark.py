from __future__ import annotations

import csv
import gc
import hashlib
import importlib.util
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


# =============================================================================
# F1.3 frozen materialization protocol
# =============================================================================

ROOT = Path(__file__).resolve().parent

PREREGISTRATION_JSON = ROOT / "fase1_tarea01_core_benchmark_preregistration.json"
DESIGN_GRID_CSV = ROOT / "fase1_tarea01_core_design_grid.csv"
GENERATOR_PY = ROOT / "fase1_tarea02_synthetic_generator.py"
BLOCK_MANIFEST_F12 = ROOT / "fase1_tarea02_noise_block_manifest.csv"
FIXTURES_F12 = ROOT / "fase1_tarea02_generator_fixtures.csv"
VALIDATION_AUDIT_F12 = ROOT / "fase1_tarea02_generator_validation_audit.json"

EXPECTED_INPUT_HASHES = {
    PREREGISTRATION_JSON.name: "dd80346172290e014d73f78240b3e31f135bcc7e4f075963e7e20d8456de3401",
    DESIGN_GRID_CSV.name: "f3c4c77ef71b9c8f9218bcf5a773d8e31c9ffc858ea68a1216542970e43f0bad",
    GENERATOR_PY.name: "743005e580f20be331408d9165522932a289d256cef0efbe4c4f24fcb38c54bd",
    BLOCK_MANIFEST_F12.name: "898a47f697b3de765f2b73b4bc01181f031c485df5875b0a88e6216591e7883d",
    FIXTURES_F12.name: "0cf7966f4447cd6188d39aa37e66d6818152440b560a6046cef7825a0dad5fbd",
    VALIDATION_AUDIT_F12.name: "3e4d588110dbe535038dc0e85ec08a60e47de946d438c05b121b379ee0c02f11",
}

EXPECTED_NUMPY_VERSION = "2.3.5"
EXPECTED_VALIDATION_CONCLUSION = "GENERATOR_VALIDATED"
EXPECTED_BASELINE_SHA256 = "4c0bf97f875b9beb2bd2d619b26fa77b083fb946a05d3ee48c32896046690dc7"

EXPECTED_SERIES_COUNT = 4440
EXPECTED_NULL_COUNT = 480
EXPECTED_POSITIVE_COUNT = 3960
EXPECTED_CONDITION_COUNT = 111
EXPECTED_BLOCK_COUNT = 480
EXPECTED_TOTAL_FLUX_VALUES = 264600
EXPECTED_TIME_VECTOR_COUNT = 4
EXPECTED_TOTAL_TIME_VALUES = 225
EXPECTED_FIXTURE_COUNT = 23

OUTPUTS = {
    "flux_values": ROOT / "fase1_tarea03_core_flux_values.npy",
    "series_offsets": ROOT / "fase1_tarea03_core_series_offsets.npy",
    "time_values": ROOT / "fase1_tarea03_core_time_values.npy",
    "time_offsets": ROOT / "fase1_tarea03_core_time_offsets.npy",
    "series_manifest": ROOT / "fase1_tarea03_core_series_manifest.csv",
    "time_manifest": ROOT / "fase1_tarea03_time_vector_manifest.csv",
    "audit": ROOT / "fase1_tarea03_materialization_audit.json",
    "report": ROOT / "fase1_tarea03_materialization_report.md",
}

SERIES_MANIFEST_FIELDS = [
    "series_id",
    "series_order",
    "condition_id",
    "ground_truth",
    "n_samples",
    "duration_s",
    "red_noise_alpha",
    "period_s",
    "qpp_fraction",
    "minimum_cycles",
    "data_seed",
    "block_id",
    "alpha_code",
    "phase_rad",
    "time_vector_id",
    "time_sha256",
    "flare_sha256",
    "noise_sha256",
    "phase_float64_sha256",
    "flux_start_offset",
    "flux_end_offset",
    "flux_sha256",
    "all_finite",
    "flux_mean",
    "flux_std_ddof1",
    "flux_min",
    "flux_max",
    "materialization_status",
    "error",
]

TIME_MANIFEST_FIELDS = [
    "time_vector_id",
    "n_samples",
    "cadence_s",
    "duration_s",
    "start_offset",
    "end_offset",
    "time_sha256",
    "all_finite",
    "strictly_increasing",
]


class MaterializationError(RuntimeError):
    """Raised when a frozen invariant is not met."""


# =============================================================================
# Utilities
# =============================================================================


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_float64_sha256(array: Any) -> str:
    canonical = np.ascontiguousarray(array, dtype="<f8")
    return hashlib.sha256(canonical.tobytes(order="C")).hexdigest()


def canonical_int64_sha256(array: Any) -> str:
    canonical = np.ascontiguousarray(array, dtype="<i8")
    return hashlib.sha256(canonical.tobytes(order="C")).hexdigest()


def format_float(value: float) -> str:
    return format(float(value), ".17g")


def optional_float(text: str) -> float | None:
    stripped = str(text).strip()
    return None if stripped == "" else float(stripped)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def block_id(n_samples: int, alpha_code: int, data_seed: int) -> str:
    return f"B_N{int(n_samples):03d}_A{int(alpha_code)}_S{int(data_seed):02d}"


def time_vector_id(n_samples: int) -> str:
    return f"T_N{int(n_samples):03d}"


def verify_hash(path: Path, expected: str) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing frozen artifact: {path}")
    observed = file_sha256(path)
    if observed != expected:
        raise MaterializationError(
            f"Hash mismatch for {path.name}. Expected {expected}; observed {observed}."
        )
    return observed


def load_frozen_generator() -> Any:
    module_spec = importlib.util.spec_from_file_location(
        "fase1_tarea02_synthetic_generator_frozen", GENERATOR_PY
    )
    if module_spec is None or module_spec.loader is None:
        raise MaterializationError("Could not load the frozen generator module.")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def environment_record() -> dict[str, Any]:
    try:
        pip_freeze = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    except Exception as exc:  # pragma: no cover - diagnostic only
        pip_freeze = [f"PIP_FREEZE_FAILURE: {type(exc).__name__}: {exc}"]

    try:
        config = subprocess.run(
            [sys.executable, "-c", "import numpy as np; np.show_config()"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except Exception as exc:  # pragma: no cover - diagnostic only
        config = f"NUMPY_CONFIG_FAILURE: {type(exc).__name__}: {exc}"

    return {
        "python_version": platform.python_version(),
        "python_full": sys.version,
        "python_executable_name": Path(sys.executable).name,
        "python_prefix_differs_from_base_prefix": sys.prefix != sys.base_prefix,
        "numpy_version": np.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "byteorder": sys.byteorder,
        "float64_itemsize": np.dtype(np.float64).itemsize,
        "int64_itemsize": np.dtype(np.int64).itemsize,
        "canonical_float_dtype": "<f8",
        "canonical_int_dtype": "<i8",
        "canonical_byte_order": "C",
        "numpy_configuration": config,
        "pip_freeze": pip_freeze,
    }


def refuse_overwrite() -> None:
    existing = [path for path in OUTPUTS.values() if path.exists()]
    if existing:
        raise FileExistsError(
            "F1.3 refuses to overwrite existing outputs:\n"
            + "\n".join(str(path) for path in existing)
        )


# =============================================================================
# Preflight and source validation
# =============================================================================


def preflight() -> tuple[dict[str, Any], list[dict[str, str]], Any, dict[str, Any]]:
    verified_hashes = {
        filename: verify_hash(ROOT / filename, expected)
        for filename, expected in EXPECTED_INPUT_HASHES.items()
    }

    if np.__version__ != EXPECTED_NUMPY_VERSION:
        raise MaterializationError(
            f"NumPy version mismatch: expected {EXPECTED_NUMPY_VERSION}, observed {np.__version__}."
        )

    validation_audit = json.loads(VALIDATION_AUDIT_F12.read_text(encoding="utf-8"))
    if validation_audit.get("validation_conclusion") != EXPECTED_VALIDATION_CONCLUSION:
        raise MaterializationError(
            "F1.2 validation_conclusion is not GENERATOR_VALIDATED."
        )
    if validation_audit.get("environment", {}).get("numpy_version") != EXPECTED_NUMPY_VERSION:
        raise MaterializationError("F1.2 audit is not linked to NumPy 2.3.5.")

    generator = load_frozen_generator()
    specification = generator.load_preregistration(
        PREREGISTRATION_JSON,
        expected_sha256=EXPECTED_INPUT_HASHES[PREREGISTRATION_JSON.name],
    )
    grid_rows = generator.validate_design_grid(
        DESIGN_GRID_CSV,
        specification,
        expected_sha256=EXPECTED_INPUT_HASHES[DESIGN_GRID_CSV.name],
    )

    baseline_reference = specification.get("baseline_reference", {})
    if baseline_reference.get("artifact") != "fase0_tarea15_reproduced_baseline.json":
        raise MaterializationError("Unexpected linked baseline artifact.")
    if baseline_reference.get("sha256") != EXPECTED_BASELINE_SHA256:
        raise MaterializationError("Preregistration baseline hash is not the frozen F0.15 hash.")
    if baseline_reference.get("verification_status") != "VERIFIED":
        raise MaterializationError("Preregistration baseline link is not verified.")

    if len(grid_rows) != EXPECTED_CONDITION_COUNT:
        raise MaterializationError(f"Expected 111 grid rows; observed {len(grid_rows)}.")
    condition_numbers = [int(row["condition_id"][1:4]) for row in grid_rows]
    if condition_numbers != list(range(1, EXPECTED_CONDITION_COUNT + 1)):
        raise MaterializationError("Condition order is not the frozen C001-C111 order.")

    return specification, grid_rows, generator, {
        "verified_hashes": verified_hashes,
        "baseline_reference": baseline_reference,
        "validation_conclusion": validation_audit["validation_conclusion"],
        "f1_2_numpy_version": validation_audit["environment"]["numpy_version"],
    }


# =============================================================================
# Blocks and fixtures
# =============================================================================


def verify_all_blocks(
    specification: dict[str, Any],
    generator: Any,
) -> tuple[dict[tuple[int, float, int], dict[str, Any]], dict[str, Any]]:
    expected_rows = read_csv(BLOCK_MANIFEST_F12)
    if len(expected_rows) != EXPECTED_BLOCK_COUNT:
        raise MaterializationError(
            f"F1.2 block manifest contains {len(expected_rows)} rows, not 480."
        )

    expected_by_key: dict[tuple[int, float, int], dict[str, str]] = {}
    for row in expected_rows:
        key = (int(row["n_samples"]), float(row["red_noise_alpha"]), int(row["data_seed"]))
        if key in expected_by_key:
            raise MaterializationError(f"Duplicate block key in F1.2 manifest: {key}")
        expected_by_key[key] = row

    blocks: dict[tuple[int, float, int], dict[str, Any]] = {}
    mismatch_records: list[dict[str, Any]] = []
    expected_keys: list[tuple[int, float, int]] = []
    for n_samples in specification["generator"]["n_samples"]:
        for alpha in specification["generator"]["noise"]["red_noise_alpha"]:
            for data_seed in range(
                int(specification["rng_and_pairing"]["data_seed_start"]),
                int(specification["rng_and_pairing"]["data_seed_end"]) + 1,
            ):
                expected_keys.append((int(n_samples), float(alpha), int(data_seed)))

    if len(expected_keys) != EXPECTED_BLOCK_COUNT or set(expected_keys) != set(expected_by_key):
        raise MaterializationError("F1.2 block-key set does not match the normative 480 blocks.")

    for key in expected_keys:
        n_samples, alpha, data_seed = key
        expected = expected_by_key[key]
        try:
            block = generator.generate_paired_block(
                n_samples, alpha, data_seed, specification
            )
            observed_hashes = generator.block_hashes(block)
        except Exception as exc:
            mismatch_records.append(
                {
                    "key": key,
                    "status": "BLOCK_GENERATION_FAILURE",
                    "error": "".join(
                        traceback.format_exception(type(exc), exc, exc.__traceback__)
                    ),
                }
            )
            continue

        mismatched_fields = {
            field: {"expected": expected[field], "observed": observed_hashes[field]}
            for field in (
                "time_sha256",
                "flare_sha256",
                "noise_sha256",
                "phase_float64_sha256",
            )
            if observed_hashes[field] != expected[field]
        }
        if mismatched_fields:
            mismatch_records.append(
                {
                    "key": key,
                    "status": "BLOCK_HASH_MISMATCH",
                    "fields": mismatched_fields,
                }
            )
            continue

        expected_id = expected["block_id"]
        observed_id = block_id(n_samples, int(block["alpha_code"]), data_seed)
        if observed_id != expected_id:
            mismatch_records.append(
                {
                    "key": key,
                    "status": "BLOCK_ID_MISMATCH",
                    "expected": expected_id,
                    "observed": observed_id,
                }
            )
            continue

        blocks[key] = block

    if mismatch_records:
        raise MaterializationError(
            "BLOCK_HASH_MISMATCH: one or more frozen blocks differ from F1.2. "
            + json.dumps(mismatch_records[:5], ensure_ascii=False)
        )
    if len(blocks) != EXPECTED_BLOCK_COUNT:
        raise MaterializationError("Not all 480 blocks were verified.")

    return blocks, {
        "expected_block_count": EXPECTED_BLOCK_COUNT,
        "attempted_block_count": len(expected_keys),
        "matched_block_count": len(blocks),
        "mismatch_count": 0,
        "status": "480/480 block hash sets matched",
    }


def fixture_key(row: dict[str, str]) -> tuple[str, str, float | None, float | None]:
    truth = "NULL_FLARE_RED_NOISE" if row["fixture_role"] == "NULL_FLARE_RED_NOISE" else "STATIONARY_QPP_PRESENT"
    return (
        row["block_id"],
        truth,
        optional_float(row["period_s"]),
        optional_float(row["qpp_fraction"]),
    )


def load_fixture_map() -> dict[tuple[str, str, float | None, float | None], dict[str, str]]:
    rows = read_csv(FIXTURES_F12)
    if len(rows) != EXPECTED_FIXTURE_COUNT:
        raise MaterializationError(f"Expected 23 fixtures; observed {len(rows)}.")
    mapping: dict[tuple[str, str, float | None, float | None], dict[str, str]] = {}
    for row in rows:
        key = fixture_key(row)
        if key in mapping:
            raise MaterializationError(f"Duplicate fixture mapping: {key}")
        mapping[key] = row
    return mapping


# =============================================================================
# Materialization
# =============================================================================


def materialize_dataset(
    specification: dict[str, Any],
    grid_rows: list[dict[str, str]],
    generator: Any,
    blocks: dict[tuple[int, float, int], dict[str, Any]],
    staging: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    fixture_map = load_fixture_map()

    planned_series = sum(int(row["planned_series_count"]) for row in grid_rows)
    total_flux_values = sum(
        int(row["n_samples"]) * int(row["data_seed_count"])
        for row in grid_rows
    )
    if planned_series != EXPECTED_SERIES_COUNT:
        raise MaterializationError(f"Grid plans {planned_series} series, not 4440.")
    if total_flux_values != EXPECTED_TOTAL_FLUX_VALUES:
        raise MaterializationError(
            f"Grid plans {total_flux_values} flux values, not 264600."
        )

    flux_values = np.empty(total_flux_values, dtype="<f8")
    series_offsets = np.empty(planned_series + 1, dtype="<i8")
    series_offsets[0] = 0
    series_manifest_rows: list[dict[str, Any]] = []
    fixture_comparisons: list[dict[str, Any]] = []

    current_offset = 0
    series_index = 0
    null_count = 0
    positive_count = 0
    condition_counts: Counter[str] = Counter()
    block_series: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for condition in grid_rows:
        condition_id = condition["condition_id"]
        truth = condition["ground_truth"]
        n_samples = int(condition["n_samples"])
        duration_s = float(condition["duration_s"])
        alpha = float(condition["red_noise_alpha"])
        period_s = optional_float(condition["period_s"])
        qpp_fraction = optional_float(condition["qpp_fraction"])
        minimum_cycles = optional_float(condition["minimum_cycles"])
        seed_start = int(condition["data_seed_start"])
        seed_end = int(condition["data_seed_end"])

        if truth == "NULL_FLARE_RED_NOISE":
            if period_s is not None or qpp_fraction is not None or minimum_cycles is not None:
                raise MaterializationError(f"Null condition {condition_id} has QPP parameters.")
        elif truth == "STATIONARY_QPP_PRESENT":
            if period_s is None or qpp_fraction is None or minimum_cycles is None:
                raise MaterializationError(f"Positive condition {condition_id} lacks QPP parameters.")
        else:
            raise MaterializationError(f"Unexpected ground truth: {truth}")

        for data_seed in range(seed_start, seed_end + 1):
            series_index += 1
            if series_index > planned_series:
                raise MaterializationError("Series count exceeded the planned total.")
            key = (n_samples, alpha, data_seed)
            block = blocks[key]
            alpha_code = int(block["alpha_code"])
            b_id = block_id(n_samples, alpha_code, data_seed)

            try:
                if truth == "NULL_FLARE_RED_NOISE":
                    flux = generator.materialize_null(block, specification)
                    null_count += 1
                else:
                    assert period_s is not None and qpp_fraction is not None
                    flux = generator.materialize_positive(
                        block, period_s, qpp_fraction, specification
                    )
                    positive_count += 1

                flux = np.ascontiguousarray(flux, dtype="<f8")
                all_finite = bool(np.all(np.isfinite(flux)))
                if flux.ndim != 1 or len(flux) != n_samples:
                    raise MaterializationError(
                        f"Invalid flux shape for {condition_id}, seed {data_seed}: {flux.shape}"
                    )
                if not all_finite:
                    raise MaterializationError(
                        f"Non-finite flux for {condition_id}, seed {data_seed}."
                    )

                start = current_offset
                end = start + n_samples
                flux_values[start:end] = flux
                current_offset = end
                series_offsets[series_index] = end
                flux_hash = canonical_float64_sha256(flux)
                error = ""
                status = "OK"
            except Exception as exc:
                error = "".join(
                    traceback.format_exception(type(exc), exc, exc.__traceback__)
                )
                status = "MATERIALIZATION_FAILURE"
                raise MaterializationError(
                    f"Series materialization failed without redraw for {condition_id}, "
                    f"data_seed={data_seed}: {error}"
                ) from exc

            hashes = generator.block_hashes(block)
            row = {
                "series_id": f"S{series_index:06d}",
                "series_order": series_index,
                "condition_id": condition_id,
                "ground_truth": truth,
                "n_samples": n_samples,
                "duration_s": format_float(duration_s),
                "red_noise_alpha": format_float(alpha),
                "period_s": "" if period_s is None else format_float(period_s),
                "qpp_fraction": "" if qpp_fraction is None else format_float(qpp_fraction),
                "minimum_cycles": "" if minimum_cycles is None else format_float(minimum_cycles),
                "data_seed": data_seed,
                "block_id": b_id,
                "alpha_code": alpha_code,
                "phase_rad": format_float(float(block["phase_rad"])),
                "time_vector_id": time_vector_id(n_samples),
                "time_sha256": hashes["time_sha256"],
                "flare_sha256": hashes["flare_sha256"],
                "noise_sha256": hashes["noise_sha256"],
                "phase_float64_sha256": hashes["phase_float64_sha256"],
                "flux_start_offset": start,
                "flux_end_offset": end,
                "flux_sha256": flux_hash,
                "all_finite": str(all_finite).lower(),
                "flux_mean": format_float(float(np.mean(flux))),
                "flux_std_ddof1": format_float(float(np.std(flux, ddof=1))),
                "flux_min": format_float(float(np.min(flux))),
                "flux_max": format_float(float(np.max(flux))),
                "materialization_status": status,
                "error": error,
            }
            series_manifest_rows.append(row)
            condition_counts[condition_id] += 1
            block_series[b_id].append(row)

            f_key = (b_id, truth, period_s, qpp_fraction)
            if f_key in fixture_map:
                fixture = fixture_map[f_key]
                passed = flux_hash == fixture["flux_sha256"]
                fixture_comparisons.append(
                    {
                        "fixture_id": fixture["fixture_id"],
                        "series_id": row["series_id"],
                        "expected_flux_sha256": fixture["flux_sha256"],
                        "observed_flux_sha256": flux_hash,
                        "passed": passed,
                    }
                )

    if series_index != EXPECTED_SERIES_COUNT:
        raise MaterializationError(f"Materialized {series_index} series, not 4440.")
    if current_offset != EXPECTED_TOTAL_FLUX_VALUES:
        raise MaterializationError(
            f"Materialized {current_offset} flux values, not 264600."
        )
    if null_count != EXPECTED_NULL_COUNT or positive_count != EXPECTED_POSITIVE_COUNT:
        raise MaterializationError(
            f"Ground-truth counts are {null_count}/{positive_count}, expected 480/3960."
        )
    if len(condition_counts) != EXPECTED_CONDITION_COUNT:
        raise MaterializationError("The materialized dataset does not contain 111 conditions.")
    if any(count != 40 for count in condition_counts.values()):
        raise MaterializationError("At least one condition does not occur exactly 40 times.")
    if series_manifest_rows[0]["series_id"] != "S000001":
        raise MaterializationError("First series_id is not S000001.")
    if series_manifest_rows[0]["condition_id"] != "C001_NULL_N015_A0" or int(series_manifest_rows[0]["data_seed"]) != 0:
        raise MaterializationError("First series does not map to C001 data_seed=0.")
    if series_manifest_rows[-1]["series_id"] != "S004440":
        raise MaterializationError("Last series_id is not S004440.")
    if series_manifest_rows[-1]["condition_id"] != grid_rows[-1]["condition_id"] or int(series_manifest_rows[-1]["data_seed"]) != 39:
        raise MaterializationError("Last series does not map to C111 data_seed=39.")

    if len(fixture_comparisons) != EXPECTED_FIXTURE_COUNT:
        raise MaterializationError(
            f"Matched {len(fixture_comparisons)} fixtures, expected 23."
        )
    fixture_failures = [row for row in fixture_comparisons if not row["passed"]]
    if fixture_failures:
        raise MaterializationError(
            "Fixture hash mismatch: " + json.dumps(fixture_failures, ensure_ascii=False)
        )

    # Pairing structure by block.
    admitted_by_n = {
        int(n): len(periods)
        for n, periods in (
            (n, specification["generator"]["qpp"]["allowed_periods_by_n"][str(n)])
            for n in specification["generator"]["n_samples"]
        )
    }
    q_count = len(specification["generator"]["qpp"]["qpp_fraction"])
    pairing_failures: list[dict[str, Any]] = []
    for b_id, rows in block_series.items():
        n_samples = int(rows[0]["n_samples"])
        expected_positive = admitted_by_n[n_samples] * q_count
        null_rows = [row for row in rows if row["ground_truth"] == "NULL_FLARE_RED_NOISE"]
        positive_rows = [row for row in rows if row["ground_truth"] == "STATIONARY_QPP_PRESENT"]
        noise_hashes = {row["noise_sha256"] for row in rows}
        phase_hashes = {row["phase_float64_sha256"] for row in rows}
        if (
            len(null_rows) != 1
            or len(positive_rows) != expected_positive
            or len(noise_hashes) != 1
            or len(phase_hashes) != 1
        ):
            pairing_failures.append(
                {
                    "block_id": b_id,
                    "null_count": len(null_rows),
                    "positive_count": len(positive_rows),
                    "expected_positive_count": expected_positive,
                    "noise_hash_count": len(noise_hashes),
                    "phase_hash_count": len(phase_hashes),
                }
            )
    if len(block_series) != EXPECTED_BLOCK_COUNT:
        raise MaterializationError(f"Observed {len(block_series)} block groups, not 480.")
    if pairing_failures:
        raise MaterializationError(
            "Pairing audit failed: " + json.dumps(pairing_failures[:10], ensure_ascii=False)
        )

    # Time arrays in frozen N order.
    time_vectors: list[np.ndarray] = []
    time_offsets = np.zeros(EXPECTED_TIME_VECTOR_COUNT + 1, dtype="<i8")
    time_manifest_rows: list[dict[str, Any]] = []
    time_offset = 0
    for index, n_samples_raw in enumerate(specification["generator"]["n_samples"]):
        n_samples = int(n_samples_raw)
        time_data = generator.build_time_and_flare(n_samples, specification)["time_s"]
        time_data = np.ascontiguousarray(time_data, dtype="<f8")
        start = time_offset
        end = start + n_samples
        time_vectors.append(time_data)
        time_offset = end
        time_offsets[index + 1] = end
        time_manifest_rows.append(
            {
                "time_vector_id": time_vector_id(n_samples),
                "n_samples": n_samples,
                "cadence_s": format_float(float(specification["generator"]["cadence_s"])),
                "duration_s": format_float(float(time_data[-1])),
                "start_offset": start,
                "end_offset": end,
                "time_sha256": canonical_float64_sha256(time_data),
                "all_finite": str(bool(np.all(np.isfinite(time_data)))).lower(),
                "strictly_increasing": str(bool(np.all(np.diff(time_data) > 0.0))).lower(),
            }
        )
    time_values = np.ascontiguousarray(np.concatenate(time_vectors), dtype="<f8")

    if len(time_values) != EXPECTED_TOTAL_TIME_VALUES:
        raise MaterializationError(f"Observed {len(time_values)} time values, not 225.")
    if not np.array_equal(time_offsets, np.array([0, 15, 45, 105, 225], dtype="<i8")):
        raise MaterializationError(f"Unexpected time offsets: {time_offsets.tolist()}")

    # Structural offset invariants before save.
    expected_lengths = np.array(
        [int(row["n_samples"]) for row in series_manifest_rows], dtype="<i8"
    )
    if series_offsets[0] != 0 or series_offsets[-1] != EXPECTED_TOTAL_FLUX_VALUES:
        raise MaterializationError("Series offsets do not span the complete flux array.")
    if not np.array_equal(np.diff(series_offsets), expected_lengths):
        raise MaterializationError("Series offset differences do not equal manifest n_samples.")

    write_csv(staging / OUTPUTS["series_manifest"].name, SERIES_MANIFEST_FIELDS, series_manifest_rows)
    write_csv(staging / OUTPUTS["time_manifest"].name, TIME_MANIFEST_FIELDS, time_manifest_rows)

    np.save(staging / OUTPUTS["flux_values"].name, flux_values, allow_pickle=False)
    np.save(staging / OUTPUTS["series_offsets"].name, series_offsets, allow_pickle=False)
    np.save(staging / OUTPUTS["time_values"].name, time_values, allow_pickle=False)
    np.save(staging / OUTPUTS["time_offsets"].name, time_offsets, allow_pickle=False)

    canonical_hashes = {
        "canonical_flux_payload_sha256": canonical_float64_sha256(flux_values),
        "series_offsets_canonical_sha256": canonical_int64_sha256(series_offsets),
        "time_values_canonical_sha256": canonical_float64_sha256(time_values),
        "time_offsets_canonical_sha256": canonical_int64_sha256(time_offsets),
    }

    distinct_flux_count = len({row["flux_sha256"] for row in series_manifest_rows})

    # Delete in-memory arrays before the mandatory read-back.
    del flux_values, series_offsets, time_values, time_offsets
    gc.collect()

    return series_manifest_rows, time_manifest_rows, {
        "null_series_count": null_count,
        "positive_series_count": positive_count,
        "condition_count": len(condition_counts),
        "block_count": len(block_series),
        "total_flux_values": current_offset,
        "time_vector_count": len(time_manifest_rows),
        "total_time_values": time_offset,
        "distinct_flux_content_count": distinct_flux_count,
        "condition_counts_all_equal_40": all(count == 40 for count in condition_counts.values()),
        "pairing_status": "PASSED",
        "pairing_failure_count": 0,
        "fixture_comparisons": fixture_comparisons,
        "fixture_match_count": len(fixture_comparisons),
        "fixture_failure_count": 0,
        "canonical_hashes": canonical_hashes,
    }


# =============================================================================
# Persisted round-trip and reporting
# =============================================================================


def validate_round_trip(
    staging: Path,
    series_manifest_rows: list[dict[str, Any]],
    time_manifest_rows: list[dict[str, Any]],
    canonical_hashes: dict[str, str],
) -> dict[str, Any]:
    flux_values = np.load(staging / OUTPUTS["flux_values"].name, allow_pickle=False)
    series_offsets = np.load(staging / OUTPUTS["series_offsets"].name, allow_pickle=False)
    time_values = np.load(staging / OUTPUTS["time_values"].name, allow_pickle=False)
    time_offsets = np.load(staging / OUTPUTS["time_offsets"].name, allow_pickle=False)

    dtype_checks = {
        "flux_values": flux_values.dtype.str == "<f8",
        "series_offsets": series_offsets.dtype.str == "<i8",
        "time_values": time_values.dtype.str == "<f8",
        "time_offsets": time_offsets.dtype.str == "<i8",
    }
    if not all(dtype_checks.values()):
        raise MaterializationError(f"Persisted dtype check failed: {dtype_checks}")
    if flux_values.ndim != 1 or len(flux_values) != EXPECTED_TOTAL_FLUX_VALUES:
        raise MaterializationError("Persisted flux array has an unexpected shape.")
    if series_offsets.ndim != 1 or len(series_offsets) != EXPECTED_SERIES_COUNT + 1:
        raise MaterializationError("Persisted series offsets have an unexpected shape.")
    if time_values.ndim != 1 or len(time_values) != EXPECTED_TOTAL_TIME_VALUES:
        raise MaterializationError("Persisted time array has an unexpected shape.")
    if time_offsets.ndim != 1 or len(time_offsets) != EXPECTED_TIME_VECTOR_COUNT + 1:
        raise MaterializationError("Persisted time offsets have an unexpected shape.")

    if canonical_float64_sha256(flux_values) != canonical_hashes["canonical_flux_payload_sha256"]:
        raise MaterializationError("Persisted flux canonical payload differs after round-trip.")
    if canonical_int64_sha256(series_offsets) != canonical_hashes["series_offsets_canonical_sha256"]:
        raise MaterializationError("Persisted series offsets differ after round-trip.")
    if canonical_float64_sha256(time_values) != canonical_hashes["time_values_canonical_sha256"]:
        raise MaterializationError("Persisted time values differ after round-trip.")
    if canonical_int64_sha256(time_offsets) != canonical_hashes["time_offsets_canonical_sha256"]:
        raise MaterializationError("Persisted time offsets differ after round-trip.")

    matched = 0
    failures: list[dict[str, Any]] = []
    for index, row in enumerate(series_manifest_rows):
        start = int(series_offsets[index])
        end = int(series_offsets[index + 1])
        n_samples = int(row["n_samples"])
        if end - start != n_samples:
            failures.append(
                {"series_id": row["series_id"], "reason": "OFFSET_LENGTH_MISMATCH"}
            )
            continue
        series = flux_values[start:end]
        observed_hash = canonical_float64_sha256(series)
        if observed_hash != row["flux_sha256"]:
            failures.append(
                {
                    "series_id": row["series_id"],
                    "reason": "FLUX_HASH_MISMATCH",
                    "expected": row["flux_sha256"],
                    "observed": observed_hash,
                }
            )
            continue
        time_id = row["time_vector_id"]
        time_row_index = {r["time_vector_id"]: i for i, r in enumerate(time_manifest_rows)}[time_id]
        t_start = int(time_offsets[time_row_index])
        t_end = int(time_offsets[time_row_index + 1])
        time_array = time_values[t_start:t_end]
        if len(time_array) != n_samples:
            failures.append(
                {"series_id": row["series_id"], "reason": "TIME_LENGTH_MISMATCH"}
            )
            continue
        if canonical_float64_sha256(time_array) != row["time_sha256"]:
            failures.append(
                {"series_id": row["series_id"], "reason": "TIME_HASH_MISMATCH"}
            )
            continue
        matched += 1

    if failures:
        raise MaterializationError(
            "Persisted round-trip failures: " + json.dumps(failures[:10], ensure_ascii=False)
        )
    if matched != EXPECTED_SERIES_COUNT:
        raise MaterializationError(f"Round-trip matched {matched}, not 4440 series.")

    return {
        "expected_series_count": EXPECTED_SERIES_COUNT,
        "matched_series_count": matched,
        "failure_count": 0,
        "status": "4440/4440 persisted series round-trip exact",
        "dtype_checks": dtype_checks,
    }


def diagnosis_text() -> str:
    return (
        "La materialización transforma el grid prerregistrado en un dataset binario "
        "cerrado sin introducir una nueva decisión científica. Antes de escribir las "
        "curvas definitivas se regeneraron los 480 bloques con NumPy 2.3.5 y se "
        "compararon, byte a byte mediante hashes canónicos, sus vectores de tiempo, "
        "envolventes, ruidos y fases con F1.2. Los 480 conjuntos coincidieron. Después "
        "se recorrieron las condiciones C001–C111 y, dentro de cada una, las semillas "
        "0–39, asignando S000001–S004440 sin reordenación posterior. Los nulos "
        "conservaron vacíos los campos de periodo, fracción QPP y ciclos nominales.\n\n"
        "Los 4.440 flujos se almacenaron como un único payload float64 little-endian, "
        "acompañado por offsets int64. Los cuatro tiempos posibles se persistieron por "
        "separado, de modo que la fase de AFINO deberá leerlos y no reconstruirlos. "
        "Cada serie quedó vinculada a su bloque emparejado mediante hashes de ruido y "
        "fase. En los 480 bloques apareció exactamente un nulo y el número previsto de "
        "positivos, determinado por los periodos admitidos y las tres amplitudes. No "
        "se redibujó, retiró ni sustituyó ninguna realización.\n\n"
        "Las 23 fixtures de F1.2 coincidieron exactamente con sus flujos materializados. "
        "Tras guardar los cuatro archivos NPY, los arrays se liberaron, se recargaron "
        "con allow_pickle=False y se reconstruyeron las 4.440 series desde sus offsets. "
        "Todos los hashes de flujo y tiempo volvieron a coincidir. Se registran hashes "
        "físicos de los archivos y hashes lógicos de los payloads canónicos para "
        "distinguir cambios reales de datos de posibles diferencias futuras en las "
        "cabeceras NPY. El número observado de contenidos distintos se conserva como "
        "descripción y no como criterio de aprobación.\n\n"
        "La limitación relevante es deliberada: el dataset queda ligado bit a bit a "
        "NumPy 2.3.5, PCG64 y la implementación validada en F1.2. Esta congelación "
        "elimina la regeneración cruzada entre entornos, pero no evalúa AFINO, BIC, "
        "periodos ajustados ni rendimiento. La siguiente fase debe consumir estos "
        "arrays exactamente como están."
    )


def build_report(
    script_hash: str,
    input_hashes: dict[str, str],
    dataset_counts: dict[str, Any],
    round_trip: dict[str, Any],
    physical_hashes: dict[str, str],
    canonical_hashes: dict[str, str],
    output_file_sizes: dict[str, int],
) -> str:
    diagnosis = diagnosis_text()
    diagnosis_words = len(re.findall(r"\b[\wÀ-ÿ0-9–-]+\b", diagnosis))
    if not 250 <= diagnosis_words <= 400:
        raise MaterializationError(
            f"Diagnosis word count {diagnosis_words} is outside 250-400."
        )

    input_table = "\n".join(
        f"| `{name}` | `{digest}` |" for name, digest in input_hashes.items()
    )
    binary_table = "\n".join(
        f"| `{name}` | {output_file_sizes[name]:,} | `{physical_hashes[name]}` |".replace(",", ".")
        for name in (
            OUTPUTS["flux_values"].name,
            OUTPUTS["series_offsets"].name,
            OUTPUTS["time_values"].name,
            OUTPUTS["time_offsets"].name,
        )
    )
    canonical_table = "\n".join(
        f"| `{key}` | `{value}` |" for key, value in canonical_hashes.items()
    )

    return f"""# Fase 1 — Tarea 1.3

## Materialización y congelación del dataset sintético núcleo

**Estado:** `DATASET_FROZEN_BEFORE_AFINO`  
**Series persistidas:** 4.440  
**AFINO ejecutado:** no  
**BIC, selección y periodos ajustados calculados:** no

---

## 1. Procedencia y hashes

El script verificó los artefactos normativos antes de importar el generador:

| Artefacto | SHA-256 |
|---|---|
{input_table}

| Script | SHA-256 |
|---|---|
| `{Path(__file__).name}` | `{script_hash}` |

El entorno exigido y observado fue Python `{platform.python_version()}` y NumPy `{np.__version__}`.

---

## 2. Formato binario

Los flujos se guardaron concatenados en `<f8` y sus offsets en `<i8`. Los cuatro vectores temporales —N=15, 30, 60 y 120— se almacenaron una sola vez, también en `<f8`, con offsets `<i8`. Todos los archivos usan el formato NPY sin pickle.

| Archivo | Bytes | SHA-256 físico |
|---|---:|---|
{binary_table}

---

## 3. Conteos

| Magnitud | Resultado |
|---|---:|
| Condiciones | {dataset_counts['condition_count']} |
| Series nulas | {dataset_counts['null_series_count']} |
| Series positivas | {dataset_counts['positive_series_count']} |
| Series totales | {EXPECTED_SERIES_COUNT} |
| Bloques emparejados | {dataset_counts['block_count']} |
| Valores de flujo | {dataset_counts['total_flux_values']:,} |
| Vectores temporales | {dataset_counts['time_vector_count']} |
| Valores temporales | {dataset_counts['total_time_values']} |
| Contenidos de flujo distintos | {dataset_counts['distinct_flux_content_count']} |

Cada condición aparece exactamente 40 veces. La primera serie es `S000001`, correspondiente a `C001_NULL_N015_A0`, semilla 0; la última es `S004440`, correspondiente a `C111`, semilla 39.

---

## 4. Correspondencia bloque–condición–serie

La regeneración previa produjo `480/480 block hash sets matched`. Dentro de cada bloque, todas las series comparten los hashes de ruido y fase; existe exactamente un nulo y el número de positivos coincide con los periodos admitidos multiplicados por las tres amplitudes. No se produjo redraw, retirada ni sustitución.

---

## 5. Fixtures

Las 23 fixtures congeladas en F1.2 se localizaron en el orden materializado y sus hashes canónicos de flujo coincidieron:

```text
23/23 fixture flux hashes matched
```

---

## 6. Round-trip

Los cuatro arrays se cerraron y recargaron mediante `np.load(..., allow_pickle=False)`. Las 4.440 series se reconstruyeron desde los offsets, junto con su vector temporal referenciado. Resultado:

```text
{round_trip['status']}
```

---

## 7. Hash lógico

| Payload canónico | SHA-256 |
|---|---|
{canonical_table}

El manifiesto ordenado de series tiene SHA-256 físico `{physical_hashes[OUTPUTS['series_manifest'].name]}`. El manifiesto de tiempos tiene SHA-256 `{physical_hashes[OUTPUTS['time_manifest'].name]}`.

---

## 8. Incidencias

No hubo discrepancias de bloque, fallos de materialización, fixtures discordantes ni errores de round-trip. La dependencia bit a bit respecto de NumPy 2.3.5 se conserva como limitación documentada del dataset, no como fallo. El número de contenidos de flujo distintos se registra sin imponer unicidad.

---

## 9. Diagnóstico ({diagnosis_words} palabras)

{diagnosis}

---

## Conclusión

**DATASET_FROZEN_BEFORE_AFINO**
"""


def publish_staging(staging: Path) -> None:
    for key, final_path in OUTPUTS.items():
        staged_path = staging / final_path.name
        if not staged_path.exists():
            raise MaterializationError(f"Missing staged output: {staged_path.name}")
    for final_path in OUTPUTS.values():
        os.replace(staging / final_path.name, final_path)
    staging.rmdir()


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    refuse_overwrite()
    script_hash = file_sha256(Path(__file__))
    environment = environment_record()
    specification, grid_rows, generator, preflight_record = preflight()

    print("F1.3 — MATERIALIZACIÓN DEL DATASET SINTÉTICO NÚCLEO")
    print(f"Python: {environment['python_version']}")
    print(f"NumPy: {environment['numpy_version']}")
    print("AFINO ejecutado: no")
    print("Verificando 480 bloques contra F1.2...")

    blocks, block_verification = verify_all_blocks(specification, generator)
    print(block_verification["status"])

    staging = Path(
        tempfile.mkdtemp(prefix=".fase1_tarea03_staging_", dir=str(ROOT))
    )
    try:
        series_rows, time_rows, dataset = materialize_dataset(
            specification, grid_rows, generator, blocks, staging
        )
        print(f"Series materializadas: {len(series_rows)}")
        print(f"Fixtures: {dataset['fixture_match_count']}/23")

        round_trip = validate_round_trip(
            staging,
            series_rows,
            time_rows,
            dataset["canonical_hashes"],
        )
        print(round_trip["status"])

        # Physical hashes available before report/audit.
        data_names = [
            OUTPUTS["flux_values"].name,
            OUTPUTS["series_offsets"].name,
            OUTPUTS["time_values"].name,
            OUTPUTS["time_offsets"].name,
            OUTPUTS["series_manifest"].name,
            OUTPUTS["time_manifest"].name,
        ]
        physical_hashes = {
            name: file_sha256(staging / name) for name in data_names
        }
        file_sizes = {name: (staging / name).stat().st_size for name in data_names}

        report_text = build_report(
            script_hash,
            preflight_record["verified_hashes"],
            dataset,
            round_trip,
            physical_hashes,
            dataset["canonical_hashes"],
            file_sizes,
        )
        report_path = staging / OUTPUTS["report"].name
        report_path.write_text(report_text, encoding="utf-8")
        physical_hashes[OUTPUTS["report"].name] = file_sha256(report_path)
        file_sizes[OUTPUTS["report"].name] = report_path.stat().st_size

        audit = {
            "date_utc": datetime.now(timezone.utc).isoformat(),
            "materialization_status": "DATASET_FROZEN_BEFORE_AFINO",
            "benchmark_id": specification["benchmark_id"],
            "benchmark_version": specification["benchmark_version"],
            "environment": environment,
            "script": {
                "filename": Path(__file__).name,
                "sha256": script_hash,
            },
            "preflight": {
                **preflight_record,
                "numpy_version_required": EXPECTED_NUMPY_VERSION,
                "numpy_version_observed": np.__version__,
                "generator_imported_from_verified_file": True,
                "scientific_parameters_loaded_from_preregistration": True,
            },
            "block_verification": block_verification,
            "dataset_counts": {
                "series_count": len(series_rows),
                "null_series_count": dataset["null_series_count"],
                "positive_series_count": dataset["positive_series_count"],
                "condition_count": dataset["condition_count"],
                "block_count": dataset["block_count"],
                "total_flux_values": dataset["total_flux_values"],
                "time_vector_count": dataset["time_vector_count"],
                "total_time_values": dataset["total_time_values"],
                "distinct_flux_content_count": dataset["distinct_flux_content_count"],
                "condition_counts_all_equal_40": dataset["condition_counts_all_equal_40"],
            },
            "ordering": {
                "condition_order": "C001 through C111 as stored in the frozen grid",
                "data_seed_order": "0 through 39 within every condition",
                "first_series": {
                    "series_id": series_rows[0]["series_id"],
                    "condition_id": series_rows[0]["condition_id"],
                    "data_seed": series_rows[0]["data_seed"],
                },
                "last_series": {
                    "series_id": series_rows[-1]["series_id"],
                    "condition_id": series_rows[-1]["condition_id"],
                    "data_seed": series_rows[-1]["data_seed"],
                },
            },
            "storage": {
                "flux_dtype": "<f8",
                "series_offsets_dtype": "<i8",
                "time_dtype": "<f8",
                "time_offsets_dtype": "<i8",
                "allow_pickle": False,
                "flux_values_length": dataset["total_flux_values"],
                "series_offsets_length": len(series_rows) + 1,
                "time_values_length": dataset["total_time_values"],
                "time_offsets_length": len(time_rows) + 1,
            },
            "pairing": {
                "status": dataset["pairing_status"],
                "block_count": dataset["block_count"],
                "failure_count": dataset["pairing_failure_count"],
                "same_noise_hash_within_block": True,
                "same_phase_hash_within_block": True,
                "one_null_per_block": True,
                "positive_count_matches_admitted_periods_times_amplitudes": True,
            },
            "fixtures": {
                "expected_count": EXPECTED_FIXTURE_COUNT,
                "matched_count": dataset["fixture_match_count"],
                "failure_count": dataset["fixture_failure_count"],
                "status": "23/23 fixture flux hashes matched",
                "comparisons": dataset["fixture_comparisons"],
            },
            "round_trip": round_trip,
            "physical_hashes": physical_hashes,
            "physical_file_sizes_bytes": file_sizes,
            "logical_hashes": {
                **dataset["canonical_hashes"],
                "ordered_series_manifest_sha256": physical_hashes[OUTPUTS["series_manifest"].name],
                "time_vector_manifest_sha256": physical_hashes[OUTPUTS["time_manifest"].name],
            },
            "incidents": [],
            "confirmations": {
                "afino_executed": False,
                "bic_computed": False,
                "model_selection_computed": False,
                "period_fit_computed": False,
                "curves_visually_selected": False,
                "failed_series_redrawn": False,
                "series_removed": False,
                "preregistration_modified": False,
                "generator_modified": False,
            },
        }
        audit_path = staging / OUTPUTS["audit"].name
        audit_path.write_text(
            json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )

        # Final structural check of staged outputs before publication.
        staged_manifest = read_csv(staging / OUTPUTS["series_manifest"].name)
        staged_time_manifest = read_csv(staging / OUTPUTS["time_manifest"].name)
        if len(staged_manifest) != EXPECTED_SERIES_COUNT:
            raise MaterializationError("Staged series manifest does not contain 4440 rows.")
        if len(staged_time_manifest) != EXPECTED_TIME_VECTOR_COUNT:
            raise MaterializationError("Staged time manifest does not contain four rows.")
        if any(
            row["period_s"] or row["qpp_fraction"] or row["minimum_cycles"]
            for row in staged_manifest
            if row["ground_truth"] == "NULL_FLARE_RED_NOISE"
        ):
            raise MaterializationError("A persisted null row has a fictitious QPP parameter.")

        publish_staging(staging)

        print("Estado: DATASET_FROZEN_BEFORE_AFINO")
        print(f"Contenidos de flujo distintos: {dataset['distinct_flux_content_count']}")
        print(f"canonical_flux_payload_sha256: {dataset['canonical_hashes']['canonical_flux_payload_sha256']}")
        for key, path in OUTPUTS.items():
            print(f"{path.name}: {file_sha256(path)}")
        return 0
    except Exception:
        print(f"STAGING_PRESERVED: {staging}", file=sys.stderr)
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileExistsError as exc:
        print(f"F1.3 REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except Exception as exc:
        print(f"F1.3 BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(3)
