from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np


BENCHMARK_ID = "afino_core_stationary_rednoise_v1"
BENCHMARK_VERSION = "1.0.0"
PREREGISTRATION_STATUS = "FROZEN_BEFORE_SYNTHETIC_GENERATION"

DESIGN_GRID_FIELDS = [
    "condition_id",
    "ground_truth",
    "n_samples",
    "duration_s",
    "red_noise_alpha",
    "period_s",
    "qpp_fraction",
    "minimum_cycles",
    "data_seed_start",
    "data_seed_end",
    "data_seed_count",
    "primary_optimizer_seed",
    "stability_data_seed",
    "stability_optimizer_seed_start",
    "stability_optimizer_seed_end",
    "planned_series_count",
    "planned_primary_model_calls",
    "planned_stability_model_calls",
    "planned_total_model_calls",
]


class SpecificationError(RuntimeError):
    """Raised when a frozen input does not match the normative specification."""


class GenerationError(RuntimeError):
    """Raised for an invalid synthetic realization without redrawing it."""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_float64_sha256(array: Any) -> str:
    """Hash a scalar or array as little-endian float64 in contiguous C order."""
    canonical = np.ascontiguousarray(array, dtype="<f8")
    return hashlib.sha256(canonical.tobytes(order="C")).hexdigest()


def _first_decimal(text: str, field: str) -> float:
    match = re.search(r"(?<![A-Za-z0-9_])([0-9]+(?:\.[0-9]+)?)", str(text))
    if match is None:
        raise SpecificationError(f"Could not parse a numeric fraction from {field}: {text!r}")
    return float(match.group(1))


def _alpha_code(specification: dict[str, Any], alpha: float) -> int:
    mapping = specification["generator"]["noise"]["alpha_code"]
    candidates = [str(float(alpha)), format(float(alpha), ".1f"), str(alpha)]
    for key in candidates:
        if key in mapping:
            return int(mapping[key])
    raise SpecificationError(f"No alpha_code is defined for alpha={alpha!r}.")


def load_preregistration(
    path: Path,
    *,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing preregistration: {path}")
    observed = file_sha256(path)
    if expected_sha256 is not None and observed != expected_sha256:
        raise SpecificationError(
            f"Preregistration hash mismatch for {path.name}.\n"
            f"Expected: {expected_sha256}\nObserved: {observed}"
        )
    specification = json.loads(path.read_text(encoding="utf-8"))
    if specification.get("benchmark_id") != BENCHMARK_ID:
        raise SpecificationError("Unexpected benchmark_id.")
    if specification.get("benchmark_version") != BENCHMARK_VERSION:
        raise SpecificationError("Unexpected benchmark_version.")
    if specification.get("preregistration_status") != PREREGISTRATION_STATUS:
        raise SpecificationError("Unexpected preregistration_status.")
    return specification


def _csv_value_matches(expected: Any, observed: str) -> bool:
    if expected is None:
        return observed == ""
    if isinstance(expected, bool):
        return observed.lower() == str(expected).lower()
    if isinstance(expected, int) and not isinstance(expected, bool):
        try:
            return int(observed) == expected
        except ValueError:
            return False
    if isinstance(expected, float):
        try:
            return math.isclose(float(observed), expected, rel_tol=1.0e-14, abs_tol=0.0)
        except ValueError:
            return False
    return observed == str(expected)


def validate_design_grid(
    path: Path,
    specification: dict[str, Any],
    *,
    expected_sha256: str | None = None,
) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing design grid: {path}")
    observed_hash = file_sha256(path)
    if expected_sha256 is not None and observed_hash != expected_sha256:
        raise SpecificationError(
            f"Design-grid hash mismatch for {path.name}.\n"
            f"Expected: {expected_sha256}\nObserved: {observed_hash}"
        )
    embedded_hash = specification["design_grid"].get("grid_sha256")
    if embedded_hash != observed_hash:
        raise SpecificationError(
            "The preregistration does not link the observed design-grid hash."
        )

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != DESIGN_GRID_FIELDS:
            raise SpecificationError(
                f"Unexpected grid columns: {reader.fieldnames!r}"
            )
        rows = list(reader)

    expected_rows = specification["design_grid"]["conditions"]
    if len(rows) != len(expected_rows):
        raise SpecificationError(
            f"Grid row count mismatch: {len(rows)} != {len(expected_rows)}"
        )

    for index, (observed, expected) in enumerate(zip(rows, expected_rows, strict=True)):
        for field in DESIGN_GRID_FIELDS:
            if not _csv_value_matches(expected[field], observed[field]):
                raise SpecificationError(
                    f"Grid mismatch at row {index + 1}, field {field}: "
                    f"expected {expected[field]!r}, observed {observed[field]!r}"
                )
    return rows


def build_time_and_flare(
    n_samples: int,
    specification: dict[str, Any],
) -> dict[str, Any]:
    generator = specification["generator"]
    flare_spec = generator["flare"]
    allowed_n = [int(value) for value in generator["n_samples"]]
    if int(n_samples) not in allowed_n:
        raise SpecificationError(f"n_samples={n_samples} is outside the frozen grid.")

    cadence_s = float(generator["cadence_s"])
    duration_s = (int(n_samples) - 1) * cadence_s
    expected_duration = float(generator["durations_s"][str(int(n_samples))])
    if duration_s != expected_duration:
        raise SpecificationError(
            f"Duration mismatch for N={n_samples}: {duration_s} != {expected_duration}"
        )

    peak_fraction = _first_decimal(
        flare_spec["peak_index_definition"], "peak_index_definition"
    )
    rise_fraction = _first_decimal(
        flare_spec["rise_tau_definition"], "rise_tau_definition"
    )
    decay_fraction = _first_decimal(
        flare_spec["decay_tau_definition"], "decay_tau_definition"
    )

    time_s = np.arange(int(n_samples), dtype=np.float64) * cadence_s
    peak_index = round(peak_fraction * (int(n_samples) - 1))
    embedded_peak_index = int(flare_spec["peak_indices"][str(int(n_samples))])
    if peak_index != embedded_peak_index:
        raise SpecificationError(
            f"Peak-index mismatch for N={n_samples}: {peak_index} != {embedded_peak_index}"
        )

    t_peak_s = float(time_s[peak_index])
    rise_tau_s = rise_fraction * duration_s
    decay_tau_s = decay_fraction * duration_s
    flare_peak_excess = float(flare_spec["flare_peak_excess"])

    flare_envelope = np.where(
        time_s <= t_peak_s,
        flare_peak_excess * np.exp((time_s - t_peak_s) / rise_tau_s),
        flare_peak_excess * np.exp(-(time_s - t_peak_s) / decay_tau_s),
    ).astype(np.float64, copy=False)

    time_s.setflags(write=False)
    flare_envelope.setflags(write=False)

    return {
        "n_samples": int(n_samples),
        "duration_s": float(duration_s),
        "time_s": time_s,
        "peak_index": int(peak_index),
        "t_peak_s": t_peak_s,
        "rise_tau_s": float(rise_tau_s),
        "decay_tau_s": float(decay_tau_s),
        "flare_envelope": flare_envelope,
    }


def _seed_metadata(seed_sequence: np.random.SeedSequence) -> dict[str, Any]:
    entropy = seed_sequence.entropy
    if isinstance(entropy, np.ndarray):
        entropy_value: Any = [int(value) for value in entropy.tolist()]
    elif isinstance(entropy, (list, tuple)):
        entropy_value = [int(value) for value in entropy]
    else:
        entropy_value = int(entropy)
    return {
        "entropy": entropy_value,
        "spawn_key": [int(value) for value in seed_sequence.spawn_key],
        "pool_size": int(seed_sequence.pool_size),
    }


def generate_paired_block(
    n_samples: int,
    alpha: float,
    data_seed: int,
    specification: dict[str, Any],
) -> dict[str, Any]:
    generator = specification["generator"]
    noise_spec = generator["noise"]
    rng_spec = specification["rng_and_pairing"]

    alpha_value = float(alpha)
    allowed_alpha = [float(value) for value in noise_spec["red_noise_alpha"]]
    if alpha_value not in allowed_alpha:
        raise SpecificationError(f"alpha={alpha} is outside the frozen grid.")

    seed_start = int(rng_spec["data_seed_start"])
    seed_end = int(rng_spec["data_seed_end"])
    if not seed_start <= int(data_seed) <= seed_end:
        raise SpecificationError(
            f"data_seed={data_seed} is outside [{seed_start}, {seed_end}]."
        )
    if rng_spec["bit_generator"] != "numpy.random.PCG64":
        raise SpecificationError("Only the frozen PCG64 bit generator is supported.")

    block = build_time_and_flare(int(n_samples), specification)
    alpha_code = _alpha_code(specification, alpha_value)
    master_seed = int(rng_spec["master_seed"])

    seed_sequence = np.random.SeedSequence(
        [master_seed, int(n_samples), alpha_code, int(data_seed)]
    )
    noise_seed, phase_seed = seed_sequence.spawn(2)
    rng_noise = np.random.Generator(np.random.PCG64(noise_seed))
    rng_phase = np.random.Generator(np.random.PCG64(phase_seed))

    cadence_s = float(generator["cadence_s"])
    freq = np.fft.rfftfreq(int(n_samples), d=cadence_s)
    scale = np.zeros_like(freq)
    scale[1:] = freq[1:] ** (-alpha_value / 2.0)

    z = (
        rng_noise.normal(size=freq.size)
        + 1j * rng_noise.normal(size=freq.size)
    )
    z[0] = 0.0
    if int(n_samples) % 2 == 0:
        z[-1] = rng_noise.normal()

    noise = np.fft.irfft(z * scale, n=int(n_samples))
    noise = noise - np.mean(noise)
    noise_std_before_scale = float(np.std(noise, ddof=1))
    if not math.isfinite(noise_std_before_scale) or noise_std_before_scale == 0.0:
        raise GenerationError(
            "Non-finite or zero pre-scaling noise standard deviation; realization not redrawn."
        )
    noise = noise / noise_std_before_scale
    noise = float(noise_spec["noise_std"]) * noise
    noise = np.asarray(noise, dtype=np.float64)
    if not np.all(np.isfinite(noise)):
        raise GenerationError("Generated noise is non-finite; realization not redrawn.")

    phase_rad = np.float64(rng_phase.uniform(0.0, 2.0 * np.pi))
    if not math.isfinite(float(phase_rad)):
        raise GenerationError("Generated phase is non-finite; realization not redrawn.")

    noise.setflags(write=False)
    block.update(
        {
            "red_noise_alpha": alpha_value,
            "alpha_code": alpha_code,
            "data_seed": int(data_seed),
            "noise": noise,
            "phase_rad": phase_rad,
            "noise_seed_metadata": _seed_metadata(noise_seed),
            "phase_seed_metadata": _seed_metadata(phase_seed),
        }
    )
    return block


def materialize_null(
    block: dict[str, Any],
    specification: dict[str, Any],
) -> np.ndarray:
    baseline_flux = float(specification["generator"]["baseline_flux"])
    flux = baseline_flux + block["flare_envelope"] + block["noise"]
    return np.asarray(flux, dtype=np.float64)


def materialize_positive(
    block: dict[str, Any],
    period_s: float,
    qpp_fraction: float,
    specification: dict[str, Any],
) -> np.ndarray:
    generator = specification["generator"]
    qpp_spec = generator["qpp"]
    period_value = float(period_s)
    qpp_value = float(qpp_fraction)

    allowed_periods = [
        float(value)
        for value in qpp_spec["allowed_periods_by_n"][str(block["n_samples"])]
    ]
    if period_value not in allowed_periods:
        raise SpecificationError(
            f"period_s={period_value} is not admitted for N={block['n_samples']}."
        )
    allowed_qpp = [float(value) for value in qpp_spec["qpp_fraction"]]
    if qpp_value not in allowed_qpp:
        raise SpecificationError(
            f"qpp_fraction={qpp_value} is outside the frozen grid."
        )

    baseline_flux = float(generator["baseline_flux"])
    periodic_component = (
        qpp_value
        * block["flare_envelope"]
        * np.sin(
            2.0
            * np.pi
            * (block["time_s"] - block["t_peak_s"])
            / period_value
            + block["phase_rad"]
        )
    )
    flux = (
        baseline_flux
        + block["flare_envelope"]
        + periodic_component
        + block["noise"]
    )
    return np.asarray(flux, dtype=np.float64)


def block_hashes(block: dict[str, Any]) -> dict[str, str]:
    return {
        "time_sha256": canonical_float64_sha256(block["time_s"]),
        "flare_sha256": canonical_float64_sha256(block["flare_envelope"]),
        "noise_sha256": canonical_float64_sha256(block["noise"]),
        "phase_float64_sha256": canonical_float64_sha256(block["phase_rad"]),
    }


if __name__ == "__main__":
    raise SystemExit(
        "This module defines the frozen generator. Run fase1_tarea02_test_generator.py "
        "to perform the preflight and validation suite."
    )
