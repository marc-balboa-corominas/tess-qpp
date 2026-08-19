from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

F3B1_BACKGROUND_NAMESPACE = "TESS-QPP:F3B1:v1"
F3B1_PERIOD_NAMESPACE = "TESS-QPP:F3B1:PERIOD:v1"

CADENCE_S = np.float64(20.0)
BASELINE_FLUX = np.float64(1.0)
FLARE_PEAK_EXCESS = np.float64(0.5)
PEAK_FRACTION = np.float64(0.20)
RISE_TAU_FRACTION = np.float64(0.04)
DECAY_TAU_FRACTION = np.float64(0.30)
RED_NOISE_STD = np.float64(0.005)
PERIOD_MIN_S = np.float64(40.0)
PERIOD_MAX_S = np.float64(300.0)
MINIMUM_CYCLES = np.float64(3.0)

ALLOWED_N_SAMPLES = (15, 30, 60, 120)
ALLOWED_RED_NOISE_ALPHA = (0.0, 1.0, 2.0)
ALLOWED_QPP_FRACTION = (0.01, 0.02, 0.04)

FLOAT64_DTYPE = np.dtype("<f8")
INT64_DTYPE = np.dtype("<i8")
BOOL_DTYPE = np.dtype("|b1")


class F3BGenerationError(RuntimeError):
    """Frozen-generator failure. A failed realization must never be redrawn."""


class F3BSpecificationError(RuntimeError):
    """Input does not conform to the frozen F3B design/binding."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_float64_bytes(value: Any) -> bytes:
    arr = np.ascontiguousarray(value, dtype=FLOAT64_DTYPE)
    return arr.tobytes(order="C")


def canonical_int64_bytes(value: Any) -> bytes:
    arr = np.ascontiguousarray(value, dtype=INT64_DTYPE)
    return arr.tobytes(order="C")


def canonical_bool_bytes(value: Any) -> bytes:
    arr = np.ascontiguousarray(value, dtype=BOOL_DTYPE)
    return arr.tobytes(order="C")


def canonical_float64_sha256(value: Any) -> str:
    return sha256_bytes(canonical_float64_bytes(value))


def canonical_int64_sha256(value: Any) -> str:
    return sha256_bytes(canonical_int64_bytes(value))


def canonical_bool_sha256(value: Any) -> str:
    return sha256_bytes(canonical_bool_bytes(value))


def canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_json_sha256(obj: Any) -> str:
    return sha256_bytes(canonical_json_bytes(obj))


def logical_payload_sha256(
    simulation_unit_id: str,
    retained_time_s: Any,
    retained_flux: Any,
    retained_native_index: Any,
) -> str:
    if "\x00" in simulation_unit_id:
        raise F3BSpecificationError("simulation_unit_id may not contain NUL.")
    payload = (
        b"F3B2_PAYLOAD_V1\x00"
        + simulation_unit_id.encode("utf-8")
        + b"\x00"
        + canonical_float64_bytes(retained_time_s)
        + canonical_float64_bytes(retained_flux)
        + canonical_int64_bytes(retained_native_index)
    )
    return sha256_bytes(payload)


def _validate_n_samples(n_samples: int) -> int:
    n = int(n_samples)
    if n not in ALLOWED_N_SAMPLES:
        raise F3BSpecificationError(f"n_samples={n} outside frozen domain.")
    return n


def _validate_alpha(alpha: float) -> float:
    value = float(alpha)
    if value not in ALLOWED_RED_NOISE_ALPHA:
        raise F3BSpecificationError(f"red_noise_alpha={value} outside frozen domain.")
    return value


def _validate_qpp_fraction(qpp_fraction: float) -> float:
    value = float(qpp_fraction)
    if value not in ALLOWED_QPP_FRACTION:
        raise F3BSpecificationError(f"qpp_fraction={value} outside frozen domain.")
    return value


def _entropy_from_namespace(namespace: str, background_realization_id: str) -> int:
    if not isinstance(background_realization_id, str) or not background_realization_id:
        raise F3BSpecificationError("background_realization_id must be a non-empty string.")
    digest = hashlib.sha256(
        f"{namespace}:{background_realization_id}".encode("utf-8")
    ).hexdigest()
    return int(digest[:32], 16)


def background_entropy(background_realization_id: str) -> int:
    return _entropy_from_namespace(
        F3B1_BACKGROUND_NAMESPACE, background_realization_id
    )


def period_entropy(background_realization_id: str) -> int:
    return _entropy_from_namespace(
        F3B1_PERIOD_NAMESPACE, background_realization_id
    )


def _seed_metadata(seed_sequence: np.random.SeedSequence) -> dict[str, Any]:
    entropy = seed_sequence.entropy
    if isinstance(entropy, np.ndarray):
        ent: Any = [int(x) for x in entropy.tolist()]
    elif isinstance(entropy, (list, tuple)):
        ent = [int(x) for x in entropy]
    else:
        ent = int(entropy)
    return {
        "entropy": ent,
        "spawn_key": [int(x) for x in seed_sequence.spawn_key],
        "pool_size": int(seed_sequence.pool_size),
    }


def build_time_and_flare(n_samples: int) -> dict[str, Any]:
    n = _validate_n_samples(n_samples)
    cadence_s = float(CADENCE_S)
    duration_s = np.float64((n - 1) * cadence_s)
    time_s = np.arange(n, dtype=np.float64) * CADENCE_S
    peak_index = int(round(float(PEAK_FRACTION) * (n - 1)))
    t_peak_s = np.float64(time_s[peak_index])
    rise_tau_s = np.float64(float(RISE_TAU_FRACTION) * float(duration_s))
    decay_tau_s = np.float64(float(DECAY_TAU_FRACTION) * float(duration_s))
    flare_envelope = np.where(
        time_s <= t_peak_s,
        FLARE_PEAK_EXCESS * np.exp((time_s - t_peak_s) / rise_tau_s),
        FLARE_PEAK_EXCESS * np.exp(-(time_s - t_peak_s) / decay_tau_s),
    ).astype(np.float64, copy=False)

    time_s.setflags(write=False)
    flare_envelope.setflags(write=False)
    return {
        "n_samples": n,
        "duration_s": duration_s,
        "time_s": time_s,
        "peak_index": peak_index,
        "t_peak_s": t_peak_s,
        "rise_tau_s": rise_tau_s,
        "decay_tau_s": decay_tau_s,
        "flare_envelope": flare_envelope,
    }


def generate_red_noise_from_rng(
    n_samples: int,
    red_noise_alpha: float,
    rng_noise: np.random.Generator,
) -> np.ndarray:
    n = _validate_n_samples(n_samples)
    alpha = _validate_alpha(red_noise_alpha)

    freq = np.fft.rfftfreq(n, d=float(CADENCE_S))
    scale = np.zeros_like(freq)
    scale[1:] = freq[1:] ** (-alpha / 2.0)

    z = rng_noise.normal(size=freq.size) + 1j * rng_noise.normal(size=freq.size)
    z[0] = 0.0
    if n % 2 == 0:
        # Frozen F1 rule: replace final complex draw with one extra real draw.
        z[-1] = rng_noise.normal()

    noise = np.fft.irfft(z * scale, n=n)
    noise = noise - np.mean(noise)
    std_before = float(np.std(noise, ddof=1))
    if not math.isfinite(std_before) or std_before == 0.0:
        raise F3BGenerationError(
            "Non-finite or zero pre-scaling noise standard deviation; no redraw."
        )
    noise = np.asarray((noise / std_before) * RED_NOISE_STD, dtype=np.float64)
    if not np.all(np.isfinite(noise)):
        raise F3BGenerationError("Generated noise is non-finite; no redraw.")
    noise.setflags(write=False)
    return noise


def generate_phase_from_rng(rng_phase: np.random.Generator) -> np.float64:
    phase = np.float64(rng_phase.uniform(0.0, 2.0 * np.pi))
    if not math.isfinite(float(phase)):
        raise F3BGenerationError("Generated phase is non-finite; no redraw.")
    return phase


def generate_background_realization(
    background_realization_id: str,
    n_samples: int,
    red_noise_alpha: float,
) -> dict[str, Any]:
    block = build_time_and_flare(n_samples)
    entropy = background_entropy(background_realization_id)

    # Frozen F3B.1 semantics: exactly spawn(2), never spawn(3).
    seed_sequence = np.random.SeedSequence(entropy)
    noise_seed, phase_seed = seed_sequence.spawn(2)
    rng_noise = np.random.Generator(np.random.PCG64(noise_seed))
    rng_phase = np.random.Generator(np.random.PCG64(phase_seed))

    noise = generate_red_noise_from_rng(
        block["n_samples"], red_noise_alpha, rng_noise
    )
    phase_rad = generate_phase_from_rng(rng_phase)

    block.update(
        {
            "background_realization_id": background_realization_id,
            "red_noise_alpha": float(red_noise_alpha),
            "background_entropy": int(entropy),
            "noise": noise,
            "phase_rad": phase_rad,
            "noise_seed_metadata": _seed_metadata(noise_seed),
            "phase_seed_metadata": _seed_metadata(phase_seed),
            "redraw_count": 0,
        }
    )
    return block


def period_upper_bound_s(duration_s: float) -> np.float64:
    upper = min(float(PERIOD_MAX_S), float(duration_s) / float(MINIMUM_CYCLES))
    if upper < float(PERIOD_MIN_S):
        raise F3BGenerationError(
            "Frozen duration cannot support the 40-s lower period with >=3 cycles."
        )
    return np.float64(upper)


def draw_true_period(
    background_realization_id: str,
    duration_s: float,
) -> dict[str, Any]:
    entropy = period_entropy(background_realization_id)
    seed = np.random.SeedSequence(entropy)
    rng = np.random.Generator(np.random.PCG64(seed))

    lower = np.float64(PERIOD_MIN_S)
    upper = period_upper_bound_s(duration_s)
    u = np.float64(rng.uniform(0.0, 1.0))
    period = np.float64(
        np.exp(
            np.log(lower)
            + u * (np.log(upper) - np.log(lower))
        )
    )
    cycles = np.float64(float(duration_s) / float(period))

    if not (
        float(PERIOD_MIN_S) <= float(period) <= float(PERIOD_MAX_S)
        and float(period) <= float(upper)
        and float(cycles) >= float(MINIMUM_CYCLES)
    ):
        raise F3BGenerationError("Frozen period draw violates its support.")

    return {
        "period_entropy": int(entropy),
        "period_seed_metadata": _seed_metadata(seed),
        "period_uniform_u": u,
        "period_upper_bound_s": upper,
        "true_period_s": period,
        "cycles_in_window": cycles,
    }


def materialize_null_latent(block: dict[str, Any]) -> np.ndarray:
    flux = BASELINE_FLUX + block["flare_envelope"] + block["noise"]
    return np.asarray(flux, dtype=np.float64)


def qpp_component(
    block: dict[str, Any],
    true_period_s: float,
    qpp_fraction: float,
) -> np.ndarray:
    qfrac = _validate_qpp_fraction(qpp_fraction)
    period = float(true_period_s)
    upper = float(period_upper_bound_s(float(block["duration_s"])))
    if not float(PERIOD_MIN_S) <= period <= upper:
        raise F3BSpecificationError(
            f"true_period_s={period} outside duration-conditioned frozen support."
        )
    component = (
        np.float64(qfrac)
        * block["flare_envelope"]
        * np.sin(
            2.0
            * np.pi
            * (block["time_s"] - block["t_peak_s"])
            / np.float64(period)
            + block["phase_rad"]
        )
    )
    return np.asarray(component, dtype=np.float64)


def materialize_positive_latent(
    block: dict[str, Any],
    true_period_s: float,
    qpp_fraction: float,
) -> tuple[np.ndarray, np.ndarray]:
    component = qpp_component(block, true_period_s, qpp_fraction)
    flux = (
        BASELINE_FLUX
        + block["flare_envelope"]
        + block["noise"]
        + component
    )
    return np.asarray(flux, dtype=np.float64), component


def build_retain_mask(block: dict[str, Any], regime: str) -> np.ndarray:
    n = int(block["n_samples"])
    peak = int(block["peak_index"])
    mask = np.ones(n, dtype=np.bool_)

    if regime == "CONTIGUOUS_ALL_GOOD":
        pass
    elif regime == "ONE_INTERNAL_NONPEAK_SAMPLE_MASKED":
        index = peak + 1
        if index >= n:
            raise F3BGenerationError("Internal non-peak mask index outside array.")
        mask[index] = False
    elif regime == "PEAK_SAMPLE_MASKED":
        mask[peak] = False
    else:
        raise F3BSpecificationError(f"Unknown gap/quality regime: {regime}")

    return np.asarray(mask, dtype=np.bool_)


def apply_retain_mask(
    block: dict[str, Any],
    latent_flux: np.ndarray,
    regime: str,
) -> dict[str, np.ndarray]:
    latent = np.asarray(latent_flux, dtype=np.float64)
    if latent.shape != (int(block["n_samples"]),):
        raise F3BSpecificationError("latent_flux length mismatch.")
    mask = build_retain_mask(block, regime)
    native_index = np.arange(int(block["n_samples"]), dtype=np.int64)
    retained = {
        "retain_mask": mask,
        "retained_time_s": np.asarray(block["time_s"][mask], dtype=np.float64),
        "retained_flux": np.asarray(latent[mask], dtype=np.float64),
        "retained_native_index": np.asarray(native_index[mask], dtype=np.int64),
    }
    return retained


def f1_compatible_block(
    n_samples: int,
    red_noise_alpha: float,
    data_seed: int,
    *,
    master_seed: int,
    alpha_code: int,
) -> dict[str, Any]:
    """
    Regression-only helper reproducing the frozen F1 seed construction.
    It is never used for F3B DEVELOPMENT/HELDOUT identities.
    """
    block = build_time_and_flare(n_samples)
    ss = np.random.SeedSequence(
        [int(master_seed), int(n_samples), int(alpha_code), int(data_seed)]
    )
    noise_seed, phase_seed = ss.spawn(2)
    rng_noise = np.random.Generator(np.random.PCG64(noise_seed))
    rng_phase = np.random.Generator(np.random.PCG64(phase_seed))
    noise = generate_red_noise_from_rng(n_samples, red_noise_alpha, rng_noise)
    phase = generate_phase_from_rng(rng_phase)
    block.update(
        {
            "red_noise_alpha": float(red_noise_alpha),
            "noise": noise,
            "phase_rad": phase,
            "noise_seed_metadata": _seed_metadata(noise_seed),
            "phase_seed_metadata": _seed_metadata(phase_seed),
        }
    )
    return block


def f1_compatible_positive(
    block: dict[str, Any],
    period_s: float,
    qpp_fraction: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    F1 regression helper. Unlike the F3B positive materializer, this accepts
    the frozen F1 reference periods directly so continuity can be tested.
    """
    qfrac = _validate_qpp_fraction(qpp_fraction)
    period = np.float64(period_s)
    component = (
        np.float64(qfrac)
        * block["flare_envelope"]
        * np.sin(
            2.0
            * np.pi
            * (block["time_s"] - block["t_peak_s"])
            / period
            + block["phase_rad"]
        )
    )
    flux = (
        BASELINE_FLUX
        + block["flare_envelope"]
        + block["noise"]
        + component
    )
    return np.asarray(flux, dtype=np.float64), np.asarray(component, dtype=np.float64)
