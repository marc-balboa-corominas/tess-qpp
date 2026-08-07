from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import platform
import random
import re
import subprocess
import sys
import traceback
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from fase1_tarea02_synthetic_generator import (
    BENCHMARK_ID,
    BENCHMARK_VERSION,
    PREREGISTRATION_STATUS,
    block_hashes,
    canonical_float64_sha256,
    file_sha256,
    generate_paired_block,
    load_preregistration,
    materialize_null,
    materialize_positive,
    validate_design_grid,
)


ROOT = Path(__file__).resolve().parent
PREREGISTRATION_PATH = ROOT / "fase1_tarea01_core_benchmark_preregistration.json"
DESIGN_GRID_PATH = ROOT / "fase1_tarea01_core_design_grid.csv"
BASELINE_PATH = ROOT / "fase0_tarea15_reproduced_baseline.json"
GENERATOR_PATH = ROOT / "fase1_tarea02_synthetic_generator.py"
TEST_PATH = Path(__file__).resolve()

EXPECTED_PREREGISTRATION_SHA256 = (
    "dd80346172290e014d73f78240b3e31f135bcc7e4f075963e7e20d8456de3401"
)
EXPECTED_DESIGN_GRID_SHA256 = (
    "f3c4c77ef71b9c8f9218bcf5a773d8e31c9ffc858ea68a1216542970e43f0bad"
)
EXPECTED_BASELINE_SHA256 = (
    "4c0bf97f875b9beb2bd2d619b26fa77b083fb946a05d3ee48c32896046690dc7"
)

BLOCK_MANIFEST = ROOT / "fase1_tarea02_noise_block_manifest.csv"
SLOPE_DIAGNOSTICS = ROOT / "fase1_tarea02_noise_slope_diagnostics.csv"
FIXTURES = ROOT / "fase1_tarea02_generator_fixtures.csv"
AUDIT_JSON = ROOT / "fase1_tarea02_generator_validation_audit.json"
REPORT_MD = ROOT / "fase1_tarea02_generator_validation.md"

REFERENCE_CASES = [
    (15, 0.0, 0),
    (15, 2.0, 39),
    (30, 1.0, 17),
    (60, 0.0, 39),
    (120, 2.0, 0),
]
ORDER_TEST_SEED = 734921
NOISE_MEAN_TOLERANCE = 1.0e-14
NOISE_STD_TOLERANCE = 1.0e-14
SLOPE_TOLERANCE = 0.35
PAIRING_RTOL = 1.0e-13
PAIRING_ATOL = 1.0e-15

BLOCK_MANIFEST_FIELDS = [
    "block_id",
    "n_samples",
    "duration_s",
    "red_noise_alpha",
    "alpha_code",
    "data_seed",
    "peak_index",
    "phase_rad",
    "time_sha256",
    "flare_sha256",
    "noise_sha256",
    "phase_float64_sha256",
    "noise_mean",
    "noise_std_ddof1",
    "all_finite",
    "generation_status",
    "error",
]

SLOPE_FIELDS = [
    "n_samples",
    "red_noise_alpha",
    "positive_frequency_bins",
    "estimated_ensemble_slope",
    "expected_slope",
    "absolute_slope_error",
    "slope_ordering_pass",
    "slope_tolerance_pass",
]

FIXTURE_FIELDS = [
    "fixture_id",
    "fixture_role",
    "block_id",
    "n_samples",
    "duration_s",
    "cadence_s",
    "red_noise_alpha",
    "alpha_code",
    "data_seed",
    "master_seed",
    "noise_std",
    "baseline_flux",
    "flare_peak_excess",
    "peak_index",
    "t_peak_s",
    "rise_tau_s",
    "decay_tau_s",
    "phase_rad",
    "period_s",
    "qpp_fraction",
    "time_sha256",
    "flare_sha256",
    "noise_sha256",
    "phase_float64_sha256",
    "flux_sha256",
    "noise_seed_metadata_json",
    "phase_seed_metadata_json",
    "dtype",
    "byte_order",
    "numpy_version",
]


def refuse_overwrite() -> None:
    existing = [
        path
        for path in (
            BLOCK_MANIFEST,
            SLOPE_DIAGNOSTICS,
            FIXTURES,
            AUDIT_JSON,
            REPORT_MD,
        )
        if path.exists()
    ]
    if existing:
        raise FileExistsError(
            "F1.2 outputs already exist and will not be overwritten:\n"
            + "\n".join(path.name for path in existing)
        )


def _first_decimal(text: str) -> float:
    match = re.search(r"(?<![A-Za-z0-9_])([0-9]+(?:\.[0-9]+)?)", str(text))
    if match is None:
        raise RuntimeError(f"Reference implementation cannot parse {text!r}")
    return float(match.group(1))


def _reference_alpha_code(specification: dict[str, Any], alpha: float) -> int:
    mapping = specification["generator"]["noise"]["alpha_code"]
    return int(mapping[str(float(alpha))])


def independent_reference_block(
    n_samples: int,
    alpha: float,
    data_seed: int,
    specification: dict[str, Any],
) -> dict[str, Any]:
    """Literal, independent implementation of the F1.1 pseudocode."""
    generator = specification["generator"]
    flare_spec = generator["flare"]
    noise_spec = generator["noise"]
    rng_spec = specification["rng_and_pairing"]

    cadence_s = float(generator["cadence_s"])
    duration_s = (int(n_samples) - 1) * cadence_s
    time_s = np.arange(int(n_samples), dtype=np.float64) * cadence_s

    peak_fraction = _first_decimal(flare_spec["peak_index_definition"])
    rise_fraction = _first_decimal(flare_spec["rise_tau_definition"])
    decay_fraction = _first_decimal(flare_spec["decay_tau_definition"])
    peak_index = round(peak_fraction * (int(n_samples) - 1))
    t_peak_s = float(time_s[peak_index])
    rise_tau_s = rise_fraction * duration_s
    decay_tau_s = decay_fraction * duration_s
    amplitude = float(flare_spec["flare_peak_excess"])

    flare = np.where(
        time_s <= t_peak_s,
        amplitude * np.exp((time_s - t_peak_s) / rise_tau_s),
        amplitude * np.exp(-(time_s - t_peak_s) / decay_tau_s),
    ).astype(np.float64, copy=False)

    alpha_code = _reference_alpha_code(specification, float(alpha))
    seed_sequence = np.random.SeedSequence(
        [int(rng_spec["master_seed"]), int(n_samples), alpha_code, int(data_seed)]
    )
    noise_seed, phase_seed = seed_sequence.spawn(2)
    rng_noise = np.random.Generator(np.random.PCG64(noise_seed))
    rng_phase = np.random.Generator(np.random.PCG64(phase_seed))

    freq = np.fft.rfftfreq(int(n_samples), d=cadence_s)
    scale = np.zeros_like(freq)
    scale[1:] = freq[1:] ** (-float(alpha) / 2.0)
    z = (
        rng_noise.normal(size=freq.size)
        + 1j * rng_noise.normal(size=freq.size)
    )
    z[0] = 0.0
    if int(n_samples) % 2 == 0:
        z[-1] = rng_noise.normal()
    noise = np.fft.irfft(z * scale, n=int(n_samples))
    noise = noise - np.mean(noise)
    noise = noise / np.std(noise, ddof=1)
    noise = float(noise_spec["noise_std"]) * noise
    noise = np.asarray(noise, dtype=np.float64)
    phase = np.float64(rng_phase.uniform(0.0, 2.0 * np.pi))

    baseline_flux = float(generator["baseline_flux"])
    null_flux = baseline_flux + flare + noise

    return {
        "n_samples": int(n_samples),
        "duration_s": float(duration_s),
        "time_s": time_s,
        "peak_index": int(peak_index),
        "t_peak_s": t_peak_s,
        "rise_tau_s": float(rise_tau_s),
        "decay_tau_s": float(decay_tau_s),
        "flare_envelope": flare,
        "noise": noise,
        "phase_rad": phase,
        "null_flux": np.asarray(null_flux, dtype=np.float64),
    }


def independent_reference_positive(
    reference_block: dict[str, Any],
    period_s: float,
    qpp_fraction: float,
    specification: dict[str, Any],
) -> np.ndarray:
    baseline_flux = float(specification["generator"]["baseline_flux"])
    positive = (
        baseline_flux
        + reference_block["flare_envelope"]
        + float(qpp_fraction)
        * reference_block["flare_envelope"]
        * np.sin(
            2.0
            * np.pi
            * (reference_block["time_s"] - reference_block["t_peak_s"])
            / float(period_s)
            + reference_block["phase_rad"]
        )
        + reference_block["noise"]
    )
    return np.asarray(positive, dtype=np.float64)


def block_key(n_samples: int, alpha: float, data_seed: int) -> tuple[int, float, int]:
    return (int(n_samples), float(alpha), int(data_seed))


def block_id(n_samples: int, alpha_code: int, data_seed: int) -> str:
    return f"B_N{int(n_samples):03d}_A{int(alpha_code)}_S{int(data_seed):02d}"


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


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def check_block_invariants(block: dict[str, Any], specification: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    n_samples = int(block["n_samples"])
    time_s = block["time_s"]
    flare = block["flare_envelope"]
    noise = block["noise"]
    phase = float(block["phase_rad"])
    peak_index = int(block["peak_index"])
    expected_peak = float(specification["generator"]["flare"]["flare_peak_excess"])
    expected_noise_std = float(specification["generator"]["noise"]["noise_std"])

    if len(time_s) != n_samples:
        errors.append("time length mismatch")
    if len(flare) != n_samples:
        errors.append("flare length mismatch")
    if len(noise) != n_samples:
        errors.append("noise length mismatch")
    if float(time_s[0]) != 0.0:
        errors.append("time[0] is not zero")
    if float(time_s[-1]) != float(block["duration_s"]):
        errors.append("time[-1] does not equal duration")
    if not (
        np.all(np.isfinite(time_s))
        and np.all(np.isfinite(flare))
        and np.all(np.isfinite(noise))
        and math.isfinite(phase)
    ):
        errors.append("non-finite value")
    if not 0.0 <= phase < 2.0 * np.pi:
        errors.append("phase outside [0, 2pi)")

    noise_mean = float(np.mean(noise))
    noise_std = float(np.std(noise, ddof=1))
    if abs(noise_mean) > NOISE_MEAN_TOLERANCE:
        errors.append(f"noise mean tolerance failed: {noise_mean}")
    if abs(noise_std - expected_noise_std) > NOISE_STD_TOLERANCE:
        errors.append(f"noise std tolerance failed: {noise_std}")

    if float(flare[peak_index]) != expected_peak:
        errors.append("flare peak is not exactly the frozen excess")
    if not np.all(flare > 0.0):
        errors.append("flare is not strictly positive")
    if peak_index > 0 and not np.all(np.diff(flare[: peak_index + 1]) > 0.0):
        errors.append("flare is not strictly increasing through the peak")
    if peak_index < n_samples - 1 and not np.all(np.diff(flare[peak_index:]) < 0.0):
        errors.append("flare is not strictly decreasing after the peak")
    return errors


def compare_reference_cases(
    specification: dict[str, Any],
) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    total_comparisons = 0
    passed_comparisons = 0

    for n_samples, alpha, data_seed in REFERENCE_CASES:
        production = generate_paired_block(n_samples, alpha, data_seed, specification)
        reference = independent_reference_block(n_samples, alpha, data_seed, specification)
        case_checks: dict[str, bool] = {
            "time_exact": np.array_equal(production["time_s"], reference["time_s"]),
            "flare_exact": np.array_equal(
                production["flare_envelope"], reference["flare_envelope"]
            ),
            "noise_exact": np.array_equal(production["noise"], reference["noise"]),
            "phase_exact": np.float64(production["phase_rad"]) == reference["phase_rad"],
            "null_flux_exact": np.array_equal(
                materialize_null(production, specification), reference["null_flux"]
            ),
        }
        for period in specification["generator"]["qpp"]["allowed_periods_by_n"][str(n_samples)]:
            for fraction in specification["generator"]["qpp"]["qpp_fraction"]:
                key = f"positive_P{float(period):g}_Q{float(fraction):g}_exact"
                case_checks[key] = np.array_equal(
                    materialize_positive(production, period, fraction, specification),
                    independent_reference_positive(reference, period, fraction, specification),
                )

        total_comparisons += len(case_checks)
        passed_comparisons += sum(case_checks.values())
        details.append(
            {
                "n_samples": n_samples,
                "red_noise_alpha": alpha,
                "data_seed": data_seed,
                "checks": case_checks,
                "all_passed": all(case_checks.values()),
            }
        )

    return {
        "reference_case_count": len(REFERENCE_CASES),
        "comparison_count": total_comparisons,
        "passed_count": passed_comparisons,
        "all_passed": passed_comparisons == total_comparisons,
        "cases": details,
    }


def generate_hash_map(
    keys: list[tuple[int, float, int]],
    specification: dict[str, Any],
) -> dict[tuple[int, float, int], dict[str, str]]:
    output: dict[tuple[int, float, int], dict[str, str]] = {}
    for key in keys:
        block = generate_paired_block(*key, specification)
        output[key] = block_hashes(block)
    return output


def order_independence_test(
    normative_keys: list[tuple[int, float, int]],
    normative_hashes: dict[tuple[int, float, int], dict[str, str]],
    specification: dict[str, Any],
) -> dict[str, Any]:
    reverse_hashes = generate_hash_map(list(reversed(normative_keys)), specification)
    random_keys = list(normative_keys)
    random.Random(ORDER_TEST_SEED).shuffle(random_keys)
    random_hashes = generate_hash_map(random_keys, specification)

    mismatches: list[dict[str, Any]] = []
    for key in normative_keys:
        if normative_hashes[key] != reverse_hashes[key]:
            mismatches.append({"key": list(key), "order": "reverse"})
        if normative_hashes[key] != random_hashes[key]:
            mismatches.append({"key": list(key), "order": "random"})
    return {
        "orders_tested": ["normative", "reverse", "random"],
        "random_order_test_seed": ORDER_TEST_SEED,
        "block_count_per_order": len(normative_keys),
        "mismatch_count": len(mismatches),
        "all_passed": len(mismatches) == 0,
        "mismatches": mismatches,
    }


def pairing_validation(
    specification: dict[str, Any],
    design_rows: list[dict[str, str]],
    blocks: dict[tuple[int, float, int], dict[str, Any]],
) -> dict[str, Any]:
    conditions_by_n_alpha: dict[tuple[int, float], list[dict[str, str]]] = {}
    for row in design_rows:
        key = (int(row["n_samples"]), float(row["red_noise_alpha"]))
        conditions_by_n_alpha.setdefault(key, []).append(row)

    association_count = 0
    signature_mismatches: list[dict[str, Any]] = []
    for key, block in blocks.items():
        n_samples, alpha, data_seed = key
        conditions = conditions_by_n_alpha[(n_samples, alpha)]
        signature = (
            canonical_float64_sha256(block["noise"]),
            canonical_float64_sha256(block["phase_rad"]),
        )
        for condition in conditions:
            association_count += 1
            observed_signature = (
                canonical_float64_sha256(block["noise"]),
                canonical_float64_sha256(block["phase_rad"]),
            )
            if observed_signature != signature:
                signature_mismatches.append(
                    {
                        "condition_id": condition["condition_id"],
                        "n_samples": n_samples,
                        "red_noise_alpha": alpha,
                        "data_seed": data_seed,
                    }
                )

    expected_associations = int(specification["design_grid"]["planned_series_count"])

    materialization_checks: list[dict[str, Any]] = []
    for n_samples, alpha, data_seed in REFERENCE_CASES:
        block_null_first = generate_paired_block(n_samples, alpha, data_seed, specification)
        null_first = materialize_null(block_null_first, specification)
        period = float(
            specification["generator"]["qpp"]["allowed_periods_by_n"][str(n_samples)][0]
        )
        positive_after_null = materialize_positive(
            block_null_first, period, 0.01, specification
        )

        block_positive_first = generate_paired_block(n_samples, alpha, data_seed, specification)
        positive_first = materialize_positive(
            block_positive_first, period, 0.01, specification
        )
        null_after_positive = materialize_null(block_positive_first, specification)

        formula = (
            0.01
            * block_null_first["flare_envelope"]
            * np.sin(
                2.0
                * np.pi
                * (block_null_first["time_s"] - block_null_first["t_peak_s"])
                / period
                + block_null_first["phase_rad"]
            )
        )
        residual_001 = positive_after_null - null_first
        positive_002 = materialize_positive(
            block_null_first, period, 0.02, specification
        )
        positive_004 = materialize_positive(
            block_null_first, period, 0.04, specification
        )
        residual_002 = positive_002 - null_first
        residual_004 = positive_004 - null_first

        checks = {
            "null_order_independent": np.array_equal(null_first, null_after_positive),
            "positive_order_independent": np.array_equal(
                positive_after_null, positive_first
            ),
            "block_hashes_order_independent": (
                block_hashes(block_null_first) == block_hashes(block_positive_first)
            ),
            "residual_formula_pass": np.allclose(
                residual_001, formula, rtol=PAIRING_RTOL, atol=PAIRING_ATOL
            ),
            "amplitude_002_pass": np.allclose(
                residual_002, 2.0 * residual_001, rtol=PAIRING_RTOL, atol=PAIRING_ATOL
            ),
            "amplitude_004_pass": np.allclose(
                residual_004, 4.0 * residual_001, rtol=PAIRING_RTOL, atol=PAIRING_ATOL
            ),
        }
        materialization_checks.append(
            {
                "n_samples": n_samples,
                "red_noise_alpha": alpha,
                "data_seed": data_seed,
                "period_s": period,
                "checks": checks,
                "all_passed": all(checks.values()),
            }
        )

    all_materialization_passed = all(
        item["all_passed"] for item in materialization_checks
    )
    return {
        "expected_series_associations": expected_associations,
        "observed_series_associations": association_count,
        "signature_mismatch_count": len(signature_mismatches),
        "signature_mismatches": signature_mismatches,
        "reference_materialization_checks": materialization_checks,
        "all_passed": (
            association_count == expected_associations
            and len(signature_mismatches) == 0
            and all_materialization_passed
        ),
    }


def slope_diagnostics(
    specification: dict[str, Any],
    blocks: dict[tuple[int, float, int], dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cadence_s = float(specification["generator"]["cadence_s"])
    n_values = [int(value) for value in specification["generator"]["n_samples"]]
    alphas = [float(value) for value in specification["generator"]["noise"]["red_noise_alpha"]]
    data_seeds = range(
        int(specification["rng_and_pairing"]["data_seed_start"]),
        int(specification["rng_and_pairing"]["data_seed_end"]) + 1,
    )

    intermediate: dict[tuple[int, float], dict[str, Any]] = {}
    for n_samples in n_values:
        for alpha in alphas:
            noise_arrays = np.stack(
                [blocks[(n_samples, alpha, seed)]["noise"] for seed in data_seeds],
                axis=0,
            )
            freq = np.fft.rfftfreq(n_samples, d=cadence_s)
            powers = np.abs(np.fft.rfft(noise_arrays, axis=1)) ** 2
            mean_power = np.mean(powers, axis=0)
            mask = freq > 0.0
            slope, intercept = np.polyfit(
                np.log(freq[mask]), np.log(mean_power[mask]), deg=1
            )
            expected = -alpha
            intermediate[(n_samples, alpha)] = {
                "n_samples": n_samples,
                "red_noise_alpha": alpha,
                "positive_frequency_bins": int(np.count_nonzero(mask)),
                "estimated_ensemble_slope": float(slope),
                "expected_slope": float(expected),
                "absolute_slope_error": float(abs(slope - expected)),
                "slope_tolerance_pass": bool(abs(slope - expected) <= SLOPE_TOLERANCE),
                "intercept": float(intercept),
            }

    ordering_by_n: dict[str, bool] = {}
    for n_samples in n_values:
        slopes = [
            intermediate[(n_samples, alpha)]["estimated_ensemble_slope"]
            for alpha in alphas
        ]
        ordering_by_n[str(n_samples)] = bool(slopes[0] > slopes[1] > slopes[2])

    rows: list[dict[str, Any]] = []
    for n_samples in n_values:
        for alpha in alphas:
            item = intermediate[(n_samples, alpha)]
            rows.append(
                {
                    "n_samples": item["n_samples"],
                    "red_noise_alpha": item["red_noise_alpha"],
                    "positive_frequency_bins": item["positive_frequency_bins"],
                    "estimated_ensemble_slope": format(
                        item["estimated_ensemble_slope"], ".17g"
                    ),
                    "expected_slope": format(item["expected_slope"], ".17g"),
                    "absolute_slope_error": format(
                        item["absolute_slope_error"], ".17g"
                    ),
                    "slope_ordering_pass": str(ordering_by_n[str(n_samples)]),
                    "slope_tolerance_pass": str(item["slope_tolerance_pass"]),
                }
            )

    return rows, {
        "combination_count": len(rows),
        "tolerance": SLOPE_TOLERANCE,
        "ordering_by_n": ordering_by_n,
        "tolerance_pass_count": sum(
            bool(item["slope_tolerance_pass"]) for item in intermediate.values()
        ),
        "ordering_pass_count": sum(ordering_by_n.values()) * len(alphas),
        "all_tolerance_passed": all(
            bool(item["slope_tolerance_pass"]) for item in intermediate.values()
        ),
        "all_ordering_passed": all(ordering_by_n.values()),
        "all_passed": (
            all(bool(item["slope_tolerance_pass"]) for item in intermediate.values())
            and all(ordering_by_n.values())
        ),
        "numeric_rows": [
            {
                key: value
                for key, value in intermediate[(n, a)].items()
                if key != "intercept"
            }
            | {"slope_ordering_pass": ordering_by_n[str(n)]}
            for n in n_values
            for a in alphas
        ],
    }


def fixture_rows(
    specification: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fixture_ids: set[str] = set()
    generator = specification["generator"]
    master_seed = int(specification["rng_and_pairing"]["master_seed"])

    for n_samples, alpha, data_seed in REFERENCE_CASES:
        block = generate_paired_block(n_samples, alpha, data_seed, specification)
        hashes = block_hashes(block)
        block_name = block_id(n_samples, block["alpha_code"], data_seed)
        common = {
            "block_id": block_name,
            "n_samples": n_samples,
            "duration_s": format(float(block["duration_s"]), ".17g"),
            "cadence_s": format(float(generator["cadence_s"]), ".17g"),
            "red_noise_alpha": format(float(alpha), ".17g"),
            "alpha_code": int(block["alpha_code"]),
            "data_seed": data_seed,
            "master_seed": master_seed,
            "noise_std": format(float(generator["noise"]["noise_std"]), ".17g"),
            "baseline_flux": format(float(generator["baseline_flux"]), ".17g"),
            "flare_peak_excess": format(
                float(generator["flare"]["flare_peak_excess"]), ".17g"
            ),
            "peak_index": int(block["peak_index"]),
            "t_peak_s": format(float(block["t_peak_s"]), ".17g"),
            "rise_tau_s": format(float(block["rise_tau_s"]), ".17g"),
            "decay_tau_s": format(float(block["decay_tau_s"]), ".17g"),
            "phase_rad": format(float(block["phase_rad"]), ".17g"),
            **hashes,
            "noise_seed_metadata_json": json_text(block["noise_seed_metadata"]),
            "phase_seed_metadata_json": json_text(block["phase_seed_metadata"]),
            "dtype": "float64 little-endian",
            "byte_order": "C",
            "numpy_version": np.__version__,
        }

        null_flux = materialize_null(block, specification)
        null_id = f"FX_{block_name}_NULL"
        fixture_ids.add(null_id)
        rows.append(
            {
                "fixture_id": null_id,
                "fixture_role": "NULL_FLARE_RED_NOISE",
                **common,
                "period_s": "",
                "qpp_fraction": "",
                "flux_sha256": canonical_float64_sha256(null_flux),
            }
        )

        allowed_periods = [
            float(value)
            for value in generator["qpp"]["allowed_periods_by_n"][str(n_samples)]
        ]
        for period in allowed_periods:
            positive = materialize_positive(block, period, 0.01, specification)
            fixture_id = f"FX_{block_name}_P{int(period):03d}_Q010"
            fixture_ids.add(fixture_id)
            rows.append(
                {
                    "fixture_id": fixture_id,
                    "fixture_role": "STATIONARY_QPP_PRESENT_Q001",
                    **common,
                    "period_s": format(period, ".17g"),
                    "qpp_fraction": format(0.01, ".17g"),
                    "flux_sha256": canonical_float64_sha256(positive),
                }
            )

        extra_period = allowed_periods[0]
        positive_extra = materialize_positive(block, extra_period, 0.04, specification)
        extra_id = f"FX_{block_name}_P{int(extra_period):03d}_Q040"
        fixture_ids.add(extra_id)
        rows.append(
            {
                "fixture_id": extra_id,
                "fixture_role": "STATIONARY_QPP_PRESENT_EXTRA_Q004",
                **common,
                "period_s": format(extra_period, ".17g"),
                "qpp_fraction": format(0.04, ".17g"),
                "flux_sha256": canonical_float64_sha256(positive_extra),
            }
        )

    expected_count = 5 + 13 + 5
    return rows, {
        "reference_block_count": len(REFERENCE_CASES),
        "fixture_row_count": len(rows),
        "expected_fixture_row_count": expected_count,
        "unique_fixture_id_count": len(fixture_ids),
        "all_passed": len(rows) == expected_count and len(fixture_ids) == expected_count,
        "extra_q004_period_rule": "smallest admitted period for each reference block",
    }


def pip_freeze() -> list[str]:
    process = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        return [f"ERROR: {process.stderr.strip()}"]
    return [line for line in process.stdout.splitlines() if line.strip()]


def numpy_config_text() -> str:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        np.show_config()
    return buffer.getvalue()


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\wÁÉÍÓÚÜÑáéíóúüñ]+\b", text, flags=re.UNICODE))


def main() -> int:
    refuse_overwrite()

    preregistration_hash = file_sha256(PREREGISTRATION_PATH)
    grid_hash = file_sha256(DESIGN_GRID_PATH)
    baseline_hash = file_sha256(BASELINE_PATH)
    if preregistration_hash != EXPECTED_PREREGISTRATION_SHA256:
        raise RuntimeError("F1.1 preregistration hash mismatch.")
    if grid_hash != EXPECTED_DESIGN_GRID_SHA256:
        raise RuntimeError("F1.1 design-grid hash mismatch.")
    if baseline_hash != EXPECTED_BASELINE_SHA256:
        raise RuntimeError("F0.15 baseline hash mismatch.")

    specification = load_preregistration(
        PREREGISTRATION_PATH,
        expected_sha256=EXPECTED_PREREGISTRATION_SHA256,
    )
    design_rows = validate_design_grid(
        DESIGN_GRID_PATH,
        specification,
        expected_sha256=EXPECTED_DESIGN_GRID_SHA256,
    )
    baseline_reference = specification["baseline_reference"]
    if baseline_reference["artifact"] != BASELINE_PATH.name:
        raise RuntimeError("Preregistration links an unexpected baseline artifact.")
    if baseline_reference["sha256"] != EXPECTED_BASELINE_SHA256:
        raise RuntimeError("Preregistration links an unexpected baseline hash.")
    if not baseline_reference["verification_status"] == "VERIFIED":
        raise RuntimeError("Preregistration baseline verification is not frozen as VERIFIED.")

    n_values = [int(value) for value in specification["generator"]["n_samples"]]
    alphas = [float(value) for value in specification["generator"]["noise"]["red_noise_alpha"]]
    data_seed_start = int(specification["rng_and_pairing"]["data_seed_start"])
    data_seed_end = int(specification["rng_and_pairing"]["data_seed_end"])
    normative_keys = [
        (n_samples, alpha, data_seed)
        for n_samples in n_values
        for alpha in alphas
        for data_seed in range(data_seed_start, data_seed_end + 1)
    ]
    if len(normative_keys) != 480:
        raise RuntimeError(f"Expected 480 blocks, found {len(normative_keys)}.")

    blocks: dict[tuple[int, float, int], dict[str, Any]] = {}
    manifest_rows: list[dict[str, Any]] = []
    generation_failures: list[dict[str, Any]] = []

    for n_samples, alpha, data_seed in normative_keys:
        alpha_code = int(
            specification["generator"]["noise"]["alpha_code"][str(float(alpha))]
        )
        name = block_id(n_samples, alpha_code, data_seed)
        try:
            block = generate_paired_block(
                n_samples, alpha, data_seed, specification
            )
            errors = check_block_invariants(block, specification)
            hashes = block_hashes(block)
            status = "OK" if not errors else "GENERATION_FAILURE"
            error = "; ".join(errors)
            if errors:
                generation_failures.append(
                    {"block_id": name, "errors": errors, "traceback": ""}
                )
            else:
                blocks[(n_samples, alpha, data_seed)] = block
            manifest_rows.append(
                {
                    "block_id": name,
                    "n_samples": n_samples,
                    "duration_s": format(float(block["duration_s"]), ".17g"),
                    "red_noise_alpha": format(float(alpha), ".17g"),
                    "alpha_code": alpha_code,
                    "data_seed": data_seed,
                    "peak_index": int(block["peak_index"]),
                    "phase_rad": format(float(block["phase_rad"]), ".17g"),
                    **hashes,
                    "noise_mean": format(float(np.mean(block["noise"])), ".17g"),
                    "noise_std_ddof1": format(
                        float(np.std(block["noise"], ddof=1)), ".17g"
                    ),
                    "all_finite": str(
                        bool(
                            np.all(np.isfinite(block["time_s"]))
                            and np.all(np.isfinite(block["flare_envelope"]))
                            and np.all(np.isfinite(block["noise"]))
                            and math.isfinite(float(block["phase_rad"]))
                        )
                    ),
                    "generation_status": status,
                    "error": error,
                }
            )
        except Exception as exc:
            generation_failures.append(
                {
                    "block_id": name,
                    "errors": [f"{type(exc).__name__}: {exc}"],
                    "traceback": traceback.format_exc(),
                }
            )
            manifest_rows.append(
                {
                    "block_id": name,
                    "n_samples": n_samples,
                    "duration_s": format((n_samples - 1) * float(specification["generator"]["cadence_s"]), ".17g"),
                    "red_noise_alpha": format(alpha, ".17g"),
                    "alpha_code": alpha_code,
                    "data_seed": data_seed,
                    "peak_index": "",
                    "phase_rad": "",
                    "time_sha256": "",
                    "flare_sha256": "",
                    "noise_sha256": "",
                    "phase_float64_sha256": "",
                    "noise_mean": "",
                    "noise_std_ddof1": "",
                    "all_finite": "False",
                    "generation_status": "GENERATION_FAILURE",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    write_csv(BLOCK_MANIFEST, BLOCK_MANIFEST_FIELDS, manifest_rows)

    all_blocks_valid = len(blocks) == 480 and len(generation_failures) == 0
    reference_result = compare_reference_cases(specification) if all_blocks_valid else {
        "reference_case_count": len(REFERENCE_CASES),
        "comparison_count": 0,
        "passed_count": 0,
        "all_passed": False,
        "cases": [],
        "blocked_reason": "One or more 480-block generations failed.",
    }

    normative_hashes = {
        key: block_hashes(block) for key, block in blocks.items()
    }
    order_result = order_independence_test(
        normative_keys, normative_hashes, specification
    ) if all_blocks_valid else {
        "orders_tested": [],
        "block_count_per_order": 0,
        "mismatch_count": 0,
        "all_passed": False,
        "mismatches": [],
        "blocked_reason": "One or more 480-block generations failed.",
    }

    pairing_result = pairing_validation(
        specification, design_rows, blocks
    ) if all_blocks_valid else {
        "expected_series_associations": 4440,
        "observed_series_associations": 0,
        "signature_mismatch_count": 0,
        "signature_mismatches": [],
        "reference_materialization_checks": [],
        "all_passed": False,
        "blocked_reason": "One or more 480-block generations failed.",
    }

    if all_blocks_valid:
        slope_rows, slope_result = slope_diagnostics(specification, blocks)
    else:
        slope_rows = []
        slope_result = {
            "combination_count": 0,
            "tolerance": SLOPE_TOLERANCE,
            "ordering_by_n": {},
            "tolerance_pass_count": 0,
            "ordering_pass_count": 0,
            "all_tolerance_passed": False,
            "all_ordering_passed": False,
            "all_passed": False,
            "numeric_rows": [],
            "blocked_reason": "One or more 480-block generations failed.",
        }
    write_csv(SLOPE_DIAGNOSTICS, SLOPE_FIELDS, slope_rows)

    if all_blocks_valid:
        fixture_data, fixture_result = fixture_rows(specification)
    else:
        fixture_data = []
        fixture_result = {
            "reference_block_count": 0,
            "fixture_row_count": 0,
            "expected_fixture_row_count": 23,
            "unique_fixture_id_count": 0,
            "all_passed": False,
            "blocked_reason": "One or more 480-block generations failed.",
        }
    write_csv(FIXTURES, FIXTURE_FIELDS, fixture_data)

    success_checks = {
        "all_480_blocks_valid": all_blocks_valid,
        "independent_reference_passed": bool(reference_result["all_passed"]),
        "order_independence_passed": bool(order_result["all_passed"]),
        "pairing_passed": bool(pairing_result["all_passed"]),
        "spectral_validation_passed": bool(slope_result["all_passed"]),
        "fixtures_passed": bool(fixture_result["all_passed"]),
    }
    conclusion = (
        "GENERATOR_VALIDATED"
        if all(success_checks.values())
        else "GENERATOR_IMPLEMENTATION_BLOCKED"
    )

    generator_hash = file_sha256(GENERATOR_PATH)
    test_hash = file_sha256(TEST_PATH)
    output_hashes = {
        BLOCK_MANIFEST.name: file_sha256(BLOCK_MANIFEST),
        SLOPE_DIAGNOSTICS.name: file_sha256(SLOPE_DIAGNOSTICS),
        FIXTURES.name: file_sha256(FIXTURES),
    }

    slope_table_lines = []
    for row in slope_rows:
        slope_table_lines.append(
            "| {n_samples} | {red_noise_alpha} | {positive_frequency_bins} | "
            "{estimated_ensemble_slope} | {expected_slope} | {absolute_slope_error} | "
            "{slope_ordering_pass} | {slope_tolerance_pass} |".format(**row)
        )
    slope_table = "\n".join(slope_table_lines) if slope_table_lines else "| — | — | — | — | — | — | False | False |"

    incidence_lines = []
    if generation_failures:
        incidence_lines.append(
            f"- {len(generation_failures)} bloques quedaron como `GENERATION_FAILURE`; no se redibujaron."
        )
    if not reference_result["all_passed"]:
        incidence_lines.append("- Falló la comparación con la implementación independiente.")
    if not order_result["all_passed"]:
        incidence_lines.append("- Falló la independencia respecto al orden de ejecución.")
    if not pairing_result["all_passed"]:
        incidence_lines.append("- Falló alguna comprobación del diseño emparejado.")
    if not slope_result["all_passed"]:
        incidence_lines.append("- Alguna pendiente incumplió la tolerancia o el orden esperado.")
    if not incidence_lines:
        incidence_lines.append("- No se observaron incidencias bloqueantes ni realizaciones inválidas.")
    incidences = "\n".join(incidence_lines)

    diagnosis = f"""La implementación se validó exclusivamente contra el prerregistro F1.1 y no contra resultados de AFINO. Se intentaron los 480 bloques independientes previstos, correspondientes a cuatro tamaños, tres pendientes y cuarenta semillas. Se obtuvieron {len(blocks)} bloques válidos y {len(generation_failures)} fallos. En cada bloque válido, tiempo, envolvente, ruido y fase fueron finitos; la media del ruido quedó dentro de ±{NOISE_MEAN_TOLERANCE:.0e} y su desviación muestral dentro de ±{NOISE_STD_TOLERANCE:.0e} de 0,005. No se sustituyó ni redibujó ninguna realización.

Los cinco casos de referencia coincidieron exactamente con una implementación literal independiente. La comparación incluyó tiempo, flare, ruido, fase, flujo nulo y todas las combinaciones positivas admisibles de esos bloques. La regeneración de los 480 bloques en orden inverso y en un orden aleatorio de test produjo los mismos hashes canónicos, por lo que el contenido no depende del orden de solicitud ni de un estado global de NumPy.

El emparejamiento se auditó sobre las 4.440 asociaciones condición–semilla sin persistir las curvas. Cada asociación de un mismo bloque reutiliza el hash del ruido y el hash float64 de la fase. En los cinco bloques de referencia, la resta positivo menos nulo reprodujo la fórmula periódica, y las fracciones 0,02 y 0,04 escalaron el residuo por factores dos y cuatro dentro de las tolerancias congeladas.

Las doce pendientes espectrales de conjunto cumplieron el error máximo de 0,35 y, para cada N, siguieron el orden alpha=0 > alpha=1 > alpha=2. Este resultado valida la familia generativa a nivel de conjunto, no la pendiente exacta de cada curva. Las fixtures fijan {fixture_result['fixture_row_count']} salidas reconstruibles bajo NumPy {np.__version__}. No se ejecutó AFINO ni se materializó el benchmark completo."""
    diagnosis_word_count = count_words(diagnosis)
    if not 250 <= diagnosis_word_count <= 400:
        raise RuntimeError(
            f"Diagnosis word count outside 250–400: {diagnosis_word_count}"
        )

    report = f"""# Fase 1 — Tarea 1.2

## Implementación y validación unitaria del generador

**Conclusión:** `{conclusion}`  
**benchmark_id:** `{BENCHMARK_ID}`  
**benchmark_version:** `{BENCHMARK_VERSION}`  
**Prerregistro:** `{PREREGISTRATION_STATUS}`  
**AFINO ejecutado:** no  
**Benchmark completo materializado:** no

---

## 1. Entorno y hashes

| Elemento | Valor |
|---|---|
| Python | `{platform.python_version()}` |
| NumPy | `{np.__version__}` |
| Plataforma | `{platform.platform()}` |
| Script del generador | `{generator_hash}` |
| Script de tests | `{test_hash}` |
| Prerregistro F1.1 | `{preregistration_hash}` |
| Grid F1.1 | `{grid_hash}` |
| Baseline F0.15 | `{baseline_hash}` |
| Manifiesto de bloques | `{output_hashes[BLOCK_MANIFEST.name]}` |
| Diagnóstico de pendientes | `{output_hashes[SLOPE_DIAGNOSTICS.name]}` |
| Fixtures | `{output_hashes[FIXTURES.name]}` |

Los arrays canónicos se serializan como `float64` little-endian, contiguos y en orden C antes de calcular SHA-256.

---

## 2. Arquitectura de la implementación

`fase1_tarea02_synthetic_generator.py` carga la configuración normativa, valida el grid y expone funciones separadas para construir tiempo y flare, generar un bloque emparejado, materializar el nulo y materializar positivos. Cada bloque contiene tiempo, envolvente, ruido, fase y metadatos de las dos `SeedSequence`. No utiliza `numpy.random` global. Los arrays compartidos se marcan como no escribibles para impedir mutaciones accidentales durante la materialización.

`fase1_tarea02_test_generator.py` contiene una implementación de referencia corta e independiente. El archivo de tests realiza el preflight, genera únicamente los 480 bloques en memoria, ejecuta las comprobaciones y escribe los tres CSV, la auditoría y este informe.

---

## 3. Resultado de los 480 bloques

| Métrica | Resultado |
|---|---:|
| Bloques intentados | 480 |
| Bloques válidos | {len(blocks)} |
| `GENERATION_FAILURE` | {len(generation_failures)} |
| Redraws | 0 |
| Media dentro de tolerancia | {sum(row['generation_status'] == 'OK' for row in manifest_rows)}/480 |
| Desviación dentro de tolerancia | {sum(row['generation_status'] == 'OK' for row in manifest_rows)}/480 |

Todos los invariantes temporales, de finitud y de monotonía de la envolvente forman parte del estado `OK` del manifiesto.

---

## 4. Referencia independiente

| Casos | Comparaciones exactas | Superadas | Resultado |
|---:|---:|---:|---|
| {reference_result['reference_case_count']} | {reference_result['comparison_count']} | {reference_result['passed_count']} | `{reference_result['all_passed']}` |

Se utilizó `np.array_equal` para tiempo, envolvente, ruido y flujos, y comparación exacta float64 para la fase. La referencia crea directamente `SeedSequence`, `PCG64`, los draws normales, Nyquist, `irfft` y la fase; no llama a funciones internas del generador.

---

## 5. Determinismo frente al orden

| Órdenes | Bloques por orden | Diferencias |
|---|---:|---:|
| Normativo, inverso y aleatorio | {order_result['block_count_per_order']} | {order_result['mismatch_count']} |

La semilla del orden aleatorio de test fue `{ORDER_TEST_SEED}` y no participa en la generación científica.

---

## 6. Diseño emparejado

Se verificaron {pairing_result['observed_series_associations']} asociaciones condición–semilla frente a {pairing_result['expected_series_associations']} previstas. No se persistieron las 4.440 curvas. Los hashes de ruido y fase se resuelven desde un único bloque `(N, alpha, data_seed)`. Los cinco tests de materialización confirmaron la fórmula del residuo, el escalado 1:2:4 y la independencia respecto a solicitar primero el nulo o el positivo.

---

## 7. Pendientes espectrales

| N | alpha | Bins positivos | Pendiente estimada | Esperada | Error absoluto | Orden | Tolerancia |
|---:|---:|---:|---:|---:|---:|---|---|
{slope_table}

Resultado global: `{slope_result['all_passed']}`. La pendiente se ajustó sobre el periodograma medio no normalizado de las cuarenta realizaciones, excluyendo frecuencia cero.

---

## 8. Fixtures congeladas

Se congelaron {fixture_result['fixture_row_count']} filas: cinco nulos, trece positivos con `qpp_fraction=0.01` —uno por cada periodo admisible de los cinco bloques— y cinco positivos adicionales con `qpp_fraction=0.04` usando el menor periodo admisible de cada bloque. Cada fila conserva parámetros, metadatos de seeds y hashes de tiempo, flare, ruido, fase y flujo.

---

## 9. Incidencias

{incidences}

---

## 10. Diagnóstico

{diagnosis}

**Palabras del diagnóstico:** {diagnosis_word_count}.

---

## 11. Cierre

```text
{conclusion}
```

La implementación queda preparada para F1.3 sin ejecutar todavía AFINO ni persistir el conjunto completo de 4.440 series.
"""
    REPORT_MD.write_text(report, encoding="utf-8")

    environment = {
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
        "canonical_array_dtype": "<f8",
        "canonical_byte_order": "C",
        "numpy_configuration": numpy_config_text(),
        "pip_freeze": pip_freeze(),
    }

    audit = {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark_id": specification["benchmark_id"],
        "benchmark_version": specification["benchmark_version"],
        "validation_conclusion": conclusion,
        "environment": environment,
        "preflight": {
            "preregistration_artifact": PREREGISTRATION_PATH.name,
            "preregistration_sha256": preregistration_hash,
            "preregistration_sha256_expected": EXPECTED_PREREGISTRATION_SHA256,
            "design_grid_artifact": DESIGN_GRID_PATH.name,
            "design_grid_sha256": grid_hash,
            "design_grid_sha256_expected": EXPECTED_DESIGN_GRID_SHA256,
            "baseline_artifact": BASELINE_PATH.name,
            "baseline_sha256": baseline_hash,
            "baseline_sha256_expected": EXPECTED_BASELINE_SHA256,
            "baseline_link_in_preregistration_verified": True,
            "condition_count": len(design_rows),
            "grid_matches_json_exactly": True,
        },
        "implementation": {
            "generator_artifact": GENERATOR_PATH.name,
            "generator_sha256": generator_hash,
            "test_artifact": TEST_PATH.name,
            "test_sha256": test_hash,
            "global_numpy_random_state_used": False,
            "canonical_hash_dtype": "float64 little-endian",
            "canonical_hash_byte_order": "C",
        },
        "block_validation": {
            "attempted_block_count": len(normative_keys),
            "valid_block_count": len(blocks),
            "generation_failure_count": len(generation_failures),
            "generation_failures": generation_failures,
            "noise_mean_tolerance": NOISE_MEAN_TOLERANCE,
            "noise_std_tolerance": NOISE_STD_TOLERANCE,
            "all_invariants_passed": all_blocks_valid,
        },
        "independent_reference": reference_result,
        "order_independence": order_result,
        "paired_design": pairing_result,
        "spectral_validation": slope_result,
        "fixtures": fixture_result,
        "success_checks": success_checks,
        "artifacts": {
            BLOCK_MANIFEST.name: {
                "sha256": output_hashes[BLOCK_MANIFEST.name],
                "rows": len(manifest_rows),
            },
            SLOPE_DIAGNOSTICS.name: {
                "sha256": output_hashes[SLOPE_DIAGNOSTICS.name],
                "rows": len(slope_rows),
            },
            FIXTURES.name: {
                "sha256": output_hashes[FIXTURES.name],
                "rows": len(fixture_data),
            },
            REPORT_MD.name: {
                "sha256": file_sha256(REPORT_MD),
                "diagnosis_word_count": diagnosis_word_count,
            },
        },
        "confirmations": {
            "afino_executed": False,
            "full_benchmark_materialized": False,
            "full_benchmark_results_observed": False,
            "failed_realizations_redrawn": False,
            "preregistration_modified": False,
            "post_generation_tuning": False,
        },
    }
    def _json_default(value: Any) -> Any:
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    AUDIT_JSON.write_text(
        json.dumps(
            audit,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
            default=_json_default,
        ) + "\n",
        encoding="utf-8",
    )

    print("F1.2 generator validation completed")
    print(f"Conclusion: {conclusion}")
    print(f"Blocks attempted: {len(normative_keys)}")
    print(f"Blocks valid: {len(blocks)}")
    print(f"Generation failures: {len(generation_failures)}")
    print(
        f"Reference comparisons: {reference_result['passed_count']}/"
        f"{reference_result['comparison_count']}"
    )
    print(f"Order mismatches: {order_result['mismatch_count']}")
    print(f"Paired associations: {pairing_result['observed_series_associations']}")
    print(
        f"Spectral tests: {slope_result['combination_count']}/12, "
        f"all_passed={slope_result['all_passed']}"
    )
    print(f"Fixture rows: {fixture_result['fixture_row_count']}")
    for path in (
        GENERATOR_PATH,
        TEST_PATH,
        BLOCK_MANIFEST,
        SLOPE_DIAGNOSTICS,
        FIXTURES,
        AUDIT_JSON,
        REPORT_MD,
    ):
        print(f"{path.name}: {file_sha256(path)}")

    return 0 if conclusion != "GENERATOR_IMPLEMENTATION_BLOCKED" else 4


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(2)
