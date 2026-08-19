#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import py_compile
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

EXPECTED_HEAD = "467abe9d5fc8379e342f7c98d735aae12ad56ea1"
F3B1_COMMIT = "b8680934644be1bfec196e2009311b3060968f0a"
F3B1_TAG = "phase3b-design-v1"

EXPECTED_HASHES = {
    "workflows/phase3b/development/config/f3b2_generator_implementation_binding.json":
        "b6519f84c0e6aa6b0c86cbd7a66dd79c1de1758e313d96ea4d750ebb212d9946",
    "workflows/phase3b/scripts/f3b_synthetic_generator.py":
        "d538d53c7845916e29c4dd351b85ae91076d5a342acb5619898788ef5d825d11",
    "workflows/phase3b/design/f3b1_split_registry.csv":
        "2316e09ba061910d360ba0d11aa4a766a3b657f56182bb6ba1c455d2b8120c93",
    "workflows/phase3b/development/evidence/tables/f3b2_generator_canary_manifest.csv":
        "6f1b42bfd1d7ae5dd58888c5821d120b0ffb1cedd3bf870099bc1dfe93c981a1",
    "workflows/phase3b/development/evidence/reports/f3b2_generator_validation_audit.json":
        "e17ed74394c8cc0f78c65dc72a7385168fda626402a794a3b84be18383bec9f7",
    "workflows/phase3b/scripts/build_f3b2_generator_canary.py":
        "04508c681ba686d6fc8c70bcfdbb3211d99aeed7299e4e8b81e1fb9da27e91e2",
}

EXPECTED_PREEXISTING_UNTRACKED = {
    "workflows/phase3b/development/evidence/reports/f3b2_generator_validation_audit.json",
    "workflows/phase3b/development/evidence/tables/f3b2_generator_canary_manifest.csv",
    "workflows/phase3b/scripts/build_f3b2_generator_canary.py",
}

STALE_FAILED_V2_REPO_SCRIPT = (
    "workflows/phase3b/scripts/materialize_f3b_development.py"
)
STALE_FAILED_V2_SHA256 = (
    "fbdf5b1815542918017053d93a0872c494288cc0dd809db7bd033e0f33d70807"
)

GENERATOR_PATH = Path("workflows/phase3b/scripts/f3b_synthetic_generator.py")
SPLIT_PATH = Path("workflows/phase3b/design/f3b1_split_registry.csv")
BINDING_PATH = Path(
    "workflows/phase3b/development/config/"
    "f3b2_generator_implementation_binding.json"
)
CANARY_AUDIT = Path(
    "workflows/phase3b/development/evidence/reports/"
    "f3b2_generator_validation_audit.json"
)
REPO_SCRIPT = Path("workflows/phase3b/scripts/materialize_f3b_development.py")

TABLE_DIR = Path("workflows/phase3b/development/evidence/tables")
REPORT_DIR = Path("workflows/phase3b/development/evidence/reports")
ARRAY_DIR = Path("data/interim/phase3b/f3b2_development")
HELDOUT_ARRAY_DIR = Path("data/interim/phase3b/heldout")

BACKGROUND_MANIFEST = TABLE_DIR / "f3b2_development_background_manifest.csv"
SERIES_MANIFEST = TABLE_DIR / "f3b2_development_series_manifest.csv"
TRUTH_LEDGER = TABLE_DIR / "f3b2_development_truth_ledger.csv"
ADMISSIBILITY = TABLE_DIR / "f3b2_development_admissibility.csv"
PAYLOAD_MANIFEST = TABLE_DIR / "f3b2_development_payload_manifest.csv"

MATERIALIZATION_AUDIT = REPORT_DIR / "f3b2_development_materialization_audit.json"
HELDOUT_AUDIT = REPORT_DIR / "f3b2_heldout_nonmaterialization_audit.json"
LEAKAGE_AUDIT = REPORT_DIR / "f3b2_development_leakage_audit.json"

ARRAY_FILES = {
    "background_noise": "background_noise.npy",
    "background_offsets": "background_offsets.npy",
    "latent_flux": "latent_flux.npy",
    "latent_offsets": "latent_offsets.npy",
    "retained_time_s": "retained_time_s.npy",
    "retained_flux": "retained_flux.npy",
    "retained_native_index": "retained_native_index.npy",
    "retained_offsets": "retained_offsets.npy",
}

# F3A/F2 inherited technical precedence for the overlapping input checks.
# All triggered reasons are retained; this order only selects the primary code.
PRIMARY_REASON_PRECEDENCE = [
    "GENERATION_FAILURE",
    "PEAK_REMOVED_BY_QUALITY",
    "TOO_FEW_CADENCES",
    "NONFINITE_INPUT",
    "IRREGULAR_SAMPLING",
]

ABS_TOL = 5e-12
CADENCE_TOLERANCE_S = 1e-3
MIN_RETAINED_CADENCES = 15


def run(repo: Path, *args: str, check: bool = True):
    cp = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and cp.returncode:
        raise RuntimeError(
            "git " + " ".join(args) + " failed: "
            + cp.stderr.decode(errors="replace").strip()
        )
    return cp


def gt(repo: Path, *args: str) -> str:
    return run(repo, *args).stdout.decode("utf-8", errors="replace").strip()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def csv_bytes(rows: list[dict[str, Any]], fields: list[str]) -> bytes:
    sio = io.StringIO(newline="")
    writer = csv.DictWriter(sio, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return sio.getvalue().encode("utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_truth_record(f3b: Any, row: dict[str, str], block: dict[str, Any],
                           period: dict[str, Any]) -> dict[str, Any]:
    is_pos = row["truth_state"] == "SYNTHETIC_QPP_PRESENT"
    truth = {
        "simulation_unit_id": row["simulation_unit_id"],
        "truth_state": row["truth_state"],
        "synthetic_ground_truth_known": True,
        "qpp_component_present": is_pos,
        "true_period_s": float(period["true_period_s"]) if is_pos else "NOT_APPLICABLE",
        "qpp_fraction": (
            float(row["positive_pair_qpp_fraction"])
            if is_pos else "NOT_APPLICABLE"
        ),
        "qpp_phase_rad": float(block["phase_rad"]) if is_pos else "NOT_APPLICABLE",
        "signal_family": (
            "STATIONARY_ENVELOPE_MODULATED_SINUSOID"
            if is_pos else "NONE"
        ),
        "n_samples": int(row["n_samples"]),
        "red_noise_alpha": float(row["red_noise_alpha"]),
        "gap_quality_regime": row["gap_quality_regime"],
        "truth_source": "F3B2_FROZEN_GENERATOR_BINDING",
    }
    truth["truth_sha256"] = f3b.canonical_json_sha256(truth)
    return truth


def admissibility_state(
    *,
    retained_time: np.ndarray,
    retained_flux: np.ndarray,
    retained_native_index: np.ndarray,
    retain_mask: np.ndarray,
    peak_index: int,
    generation_failure: str = "",
) -> dict[str, Any]:
    triggered: list[str] = []
    irregular_details: list[str] = []

    if generation_failure:
        triggered.append("GENERATION_FAILURE")

    peak_retained = bool(
        0 <= int(peak_index) < len(retain_mask)
        and bool(retain_mask[int(peak_index)])
    )
    if not peak_retained:
        triggered.append("PEAK_REMOVED_BY_QUALITY")

    retained_n = int(len(retained_time))
    if retained_n < MIN_RETAINED_CADENCES:
        triggered.append("TOO_FEW_CADENCES")

    finite = bool(
        np.all(np.isfinite(retained_time))
        and np.all(np.isfinite(retained_flux))
    )
    if not finite:
        triggered.append("NONFINITE_INPUT")

    # Evaluate each frozen regularity condition independently so that all
    # triggered causes are recorded even when TOO_FEW_CADENCES or peak loss
    # also applies.
    if retained_n >= 2:
        diffs_t = np.diff(np.asarray(retained_time, dtype=np.float64))
        increasing = bool(np.all(diffs_t > 0.0))
        duplicate_times = bool(
            len(np.unique(retained_time)) != len(retained_time)
        )
        if not increasing:
            irregular_details.append("time_not_strictly_increasing")
        if duplicate_times:
            irregular_details.append("duplicate_times")

        idx = np.asarray(retained_native_index, dtype=np.int64)
        duplicate_indices = bool(len(np.unique(idx)) != len(idx))
        if duplicate_indices:
            irregular_details.append("duplicate_native_indices")
        consecutive = bool(np.all(np.diff(idx) == 1))
        if not consecutive:
            irregular_details.append("retained_indices_not_consecutive")

        if finite:
            median_cadence = float(np.median(diffs_t))
            max_dev = float(np.max(np.abs(diffs_t - median_cadence)))
            if max_dev > CADENCE_TOLERANCE_S:
                irregular_details.append(
                    "interval_deviation_gt_0.001_s"
                )
    else:
        irregular_details.append("insufficient_points_for_regular_grid_check")

    if irregular_details:
        triggered.append("IRREGULAR_SAMPLING")

    # Preserve technical precedence while also reporting all triggered reasons.
    primary = ""
    for code in PRIMARY_REASON_PRECEDENCE:
        if code in triggered:
            primary = code
            break

    return {
        "input_state": (
            "ELIGIBLE_FOR_AFINO" if not triggered else "INPUT_INADMISSIBLE"
        ),
        "all_triggered_reasons": "|".join(triggered),
        "primary_inadmissibility_reason": primary,
        "irregular_sampling_details": "|".join(irregular_details),
        "retained_cadences": retained_n,
        "finite_time_flux": finite,
        "strictly_increasing_time": (
            "" if retained_n < 2 else bool(np.all(np.diff(retained_time) > 0.0))
        ),
        "native_indices_consecutive": (
            "" if retained_n < 2 else
            bool(np.all(np.diff(retained_native_index) == 1))
        ),
        "no_duplicate_times": (
            "" if retained_n < 1 else
            bool(len(np.unique(retained_time)) == len(retained_time))
        ),
        "no_duplicate_native_indices": (
            "" if retained_n < 1 else
            bool(
                len(np.unique(retained_native_index))
                == len(retained_native_index)
            )
        ),
        "regular_cadence_tolerance_s": CADENCE_TOLERANCE_S,
        "peak_retained": peak_retained,
    }


def deterministic_order(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(rows, key=lambda r: r["simulation_unit_id"])


def group_by_background(rows: list[dict[str, str]]):
    out: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        out[row["background_realization_id"]].append(row)
    return out


def validate_background_registry(
    development_rows: list[dict[str, str]],
    heldout_rows: list[dict[str, str]],
):
    dev_bg = {
        r["background_realization_id"] for r in development_rows
    }
    held_bg = {
        r["background_realization_id"] for r in heldout_rows
    }
    if len(dev_bg) != 1800 or len(held_bg) != 1800:
        raise RuntimeError("Expected 1800 DEVELOPMENT and 1800 HELDOUT backgrounds.")
    if dev_bg & held_bg:
        raise RuntimeError("DEVELOPMENT/HELDOUT split contamination.")
    return dev_bg, held_bg


def materialize_dataset(
    *,
    repo: Path,
    f3b: Any,
    development_rows: list[dict[str, str]],
    heldout_backgrounds: set[str],
    output_dir: Path,
    write_arrays: bool,
) -> dict[str, Any]:
    ordered_rows = deterministic_order(development_rows)
    by_bg = group_by_background(development_rows)
    bg_ids = sorted(by_bg)

    background_noise_chunks: list[np.ndarray] = []
    background_offsets = [0]

    latent_chunks: list[np.ndarray] = []
    latent_offsets = [0]

    retained_time_chunks: list[np.ndarray] = []
    retained_flux_chunks: list[np.ndarray] = []
    retained_index_chunks: list[np.ndarray] = []
    retained_offsets = [0]

    background_manifest: list[dict[str, Any]] = []
    series_manifest: list[dict[str, Any]] = []
    truth_ledger: list[dict[str, Any]] = []
    admissibility_rows: list[dict[str, Any]] = []
    payload_manifest: list[dict[str, Any]] = []

    background_hashes: dict[str, str] = {}
    latent_hashes: dict[str, str] = {}
    retained_payload_hashes: dict[str, str] = {}
    truth_hashes: dict[str, str] = {}

    block_cache: dict[str, dict[str, Any]] = {}
    period_cache: dict[str, dict[str, Any]] = {}
    generation_failures: dict[str, str] = {}

    background_rng_initializations = 0
    period_draws = 0
    phase_draws = 0
    noise_draws = 0
    redraw_total = 0

    # One background/phase generation + one period generation per DEVELOPMENT
    # background. No HELDOUT identity is accepted by this loop.
    for bg in bg_ids:
        if bg in heldout_backgrounds:
            raise RuntimeError("HELDOUT ID reached DEVELOPMENT materializer.")
        rows = by_bg[bg]
        exemplar = rows[0]
        n_samples = int(exemplar["n_samples"])
        alpha = float(exemplar["red_noise_alpha"])

        try:
            background_rng_initializations += 1
            phase_draws += 1
            noise_draws += 1
            block = f3b.generate_background_realization(
                bg, n_samples, alpha
            )
            block_cache[bg] = block
            redraw_total += int(block["redraw_count"])

            period_draws += 1
            period = f3b.draw_true_period(bg, float(block["duration_s"]))
            period_cache[bg] = period

            noise = np.asarray(block["noise"], dtype=np.float64)
            if noise.dtype != np.dtype("float64"):
                raise RuntimeError("Background noise dtype is not float64.")
            background_noise_chunks.append(noise)
            background_offsets.append(
                background_offsets[-1] + len(noise)
            )
            noise_sha = f3b.canonical_float64_sha256(noise)
            background_hashes[bg] = noise_sha

            bg_first = min(rows, key=lambda r: r["simulation_unit_id"])
            background_manifest.append(
                {
                    "background_realization_id": bg,
                    "split": "DEVELOPMENT",
                    "n_samples": n_samples,
                    "duration_s": float(exemplar["duration_s"]),
                    "red_noise_alpha": alpha,
                    "positive_pair_qpp_fraction":
                        float(exemplar["positive_pair_qpp_fraction"]),
                    "split_rank_sha256": exemplar["split_rank_sha256"],
                    "challenge_rank_sha256": exemplar["challenge_rank_sha256"],
                    "background_entropy": int(block["background_entropy"]),
                    "period_entropy": int(period["period_entropy"]),
                    "noise_offset": background_offsets[-2],
                    "noise_length": len(noise),
                    "noise_sha256": noise_sha,
                    "phase_rad": float(block["phase_rad"]),
                    "phase_sha256_or_canonical_repr":
                        f3b.canonical_float64_sha256(
                            np.asarray([block["phase_rad"]], dtype=np.float64)
                        ),
                    "true_period_s": float(period["true_period_s"]),
                    "period_upper_bound_s":
                        float(period["period_upper_bound_s"]),
                    "cycles_in_window": float(period["cycles_in_window"]),
                    "generation_status": "MATERIALIZED",
                    "generation_failure_reason": "",
                    "redraw_count": int(block["redraw_count"]),
                }
            )
        except Exception as exc:
            # No redraw. Record a zero-length background slice and propagate
            # failure to all series of the background. This path is expected to
            # be unused but preserves the frozen failure policy.
            generation_failures[bg] = (
                f"{type(exc).__name__}:{str(exc)}"
            )
            background_offsets.append(background_offsets[-1])
            background_hashes[bg] = ""
            background_manifest.append(
                {
                    "background_realization_id": bg,
                    "split": "DEVELOPMENT",
                    "n_samples": n_samples,
                    "duration_s": float(exemplar["duration_s"]),
                    "red_noise_alpha": alpha,
                    "positive_pair_qpp_fraction":
                        float(exemplar["positive_pair_qpp_fraction"]),
                    "split_rank_sha256": exemplar["split_rank_sha256"],
                    "challenge_rank_sha256": exemplar["challenge_rank_sha256"],
                    "background_entropy": "",
                    "period_entropy": "",
                    "noise_offset": background_offsets[-2],
                    "noise_length": 0,
                    "noise_sha256": "",
                    "phase_rad": "",
                    "phase_sha256_or_canonical_repr": "",
                    "true_period_s": "",
                    "period_upper_bound_s": "",
                    "cycles_in_window": "",
                    "generation_status": "GENERATION_FAILURE",
                    "generation_failure_reason": generation_failures[bg],
                    "redraw_count": 0,
                }
            )

    if redraw_total != 0:
        raise RuntimeError("Any redraw blocks F3B.2 immediately.")

    bg_manifest_by_id = {
        r["background_realization_id"]: r
        for r in background_manifest
    }

    for row in ordered_rows:
        sid = row["simulation_unit_id"]
        bg = row["background_realization_id"]
        generation_failure = generation_failures.get(bg, "")
        is_pos = row["truth_state"] == "SYNTHETIC_QPP_PRESENT"

        if generation_failure:
            latent = np.asarray([], dtype=np.float64)
            retained = {
                "retain_mask": np.asarray([], dtype=np.bool_),
                "retained_time_s": np.asarray([], dtype=np.float64),
                "retained_flux": np.asarray([], dtype=np.float64),
                "retained_native_index": np.asarray([], dtype=np.int64),
            }
            period = None
            qpp_component = None
            admiss = admissibility_state(
                retained_time=retained["retained_time_s"],
                retained_flux=retained["retained_flux"],
                retained_native_index=retained["retained_native_index"],
                retain_mask=retained["retain_mask"],
                peak_index=-1,
                generation_failure=generation_failure,
            )
            truth = {
                "simulation_unit_id": sid,
                "truth_state": row["truth_state"],
                "synthetic_ground_truth_known": True,
                "qpp_component_present": is_pos,
                "true_period_s": "GENERATION_FAILURE" if is_pos else "NOT_APPLICABLE",
                "qpp_fraction": (
                    float(row["positive_pair_qpp_fraction"])
                    if is_pos else "NOT_APPLICABLE"
                ),
                "qpp_phase_rad": "GENERATION_FAILURE" if is_pos else "NOT_APPLICABLE",
                "signal_family": (
                    "STATIONARY_ENVELOPE_MODULATED_SINUSOID"
                    if is_pos else "NONE"
                ),
                "n_samples": int(row["n_samples"]),
                "red_noise_alpha": float(row["red_noise_alpha"]),
                "gap_quality_regime": row["gap_quality_regime"],
                "truth_source": "F3B2_FROZEN_GENERATOR_BINDING",
            }
            truth["truth_sha256"] = f3b.canonical_json_sha256(truth)
            materialization_status = "GENERATION_FAILURE"
        else:
            block = block_cache[bg]
            period = period_cache[bg]
            null_latent = f3b.materialize_null_latent(block)
            if is_pos:
                latent, qpp_component = f3b.materialize_positive_latent(
                    block,
                    float(period["true_period_s"]),
                    float(row["positive_pair_qpp_fraction"]),
                )
            else:
                latent = null_latent
                qpp_component = None

            retained = f3b.apply_retain_mask(
                block, latent, row["gap_quality_regime"]
            )
            admiss = admissibility_state(
                retained_time=retained["retained_time_s"],
                retained_flux=retained["retained_flux"],
                retained_native_index=retained["retained_native_index"],
                retain_mask=retained["retain_mask"],
                peak_index=int(block["peak_index"]),
            )
            truth = canonical_truth_record(
                f3b, row, block, period
            )
            materialization_status = "MATERIALIZED"

            # Pairing/truth mechanics.
            if is_pos:
                component_check = np.asarray(
                    latent - null_latent, dtype=np.float64
                )
                if not np.allclose(
                    component_check,
                    qpp_component,
                    rtol=0.0,
                    atol=ABS_TOL,
                ):
                    raise RuntimeError(
                        "Positive-minus-null differs from QPP component."
                    )

        latent_offset = latent_offsets[-1]
        latent_len = len(latent)
        latent_chunks.append(np.asarray(latent, dtype=np.float64))
        latent_offsets.append(latent_offset + latent_len)

        retained_offset = retained_offsets[-1]
        retained_len = len(retained["retained_flux"])
        retained_time_chunks.append(
            np.asarray(retained["retained_time_s"], dtype=np.float64)
        )
        retained_flux_chunks.append(
            np.asarray(retained["retained_flux"], dtype=np.float64)
        )
        retained_index_chunks.append(
            np.asarray(retained["retained_native_index"], dtype=np.int64)
        )
        retained_offsets.append(retained_offset + retained_len)

        latent_sha = (
            f3b.canonical_float64_sha256(latent)
            if materialization_status == "MATERIALIZED" else ""
        )
        retained_time_sha = (
            f3b.canonical_float64_sha256(retained["retained_time_s"])
            if materialization_status == "MATERIALIZED" else ""
        )
        retained_flux_sha = (
            f3b.canonical_float64_sha256(retained["retained_flux"])
            if materialization_status == "MATERIALIZED" else ""
        )
        retained_idx_sha = (
            f3b.canonical_int64_sha256(retained["retained_native_index"])
            if materialization_status == "MATERIALIZED" else ""
        )
        logical_sha = (
            f3b.logical_payload_sha256(
                sid,
                retained["retained_time_s"],
                retained["retained_flux"],
                retained["retained_native_index"],
            )
            if materialization_status == "MATERIALIZED" else ""
        )

        latent_hashes[sid] = latent_sha
        retained_payload_hashes[sid] = logical_sha
        truth_hashes[sid] = truth["truth_sha256"]

        true_period_value: Any
        phase_value: Any
        qfrac_value: Any
        signal_family_value: str
        if is_pos and materialization_status == "MATERIALIZED":
            true_period_value = float(period["true_period_s"])
            phase_value = float(block_cache[bg]["phase_rad"])
            qfrac_value = float(row["positive_pair_qpp_fraction"])
            signal_family_value = "STATIONARY_ENVELOPE_MODULATED_SINUSOID"
        elif is_pos:
            true_period_value = "GENERATION_FAILURE"
            phase_value = "GENERATION_FAILURE"
            qfrac_value = float(row["positive_pair_qpp_fraction"])
            signal_family_value = "STATIONARY_ENVELOPE_MODULATED_SINUSOID"
        else:
            true_period_value = "NOT_APPLICABLE"
            phase_value = "NOT_APPLICABLE"
            qfrac_value = "NOT_APPLICABLE"
            signal_family_value = "NONE"

        series_manifest.append(
            {
                "simulation_unit_id": sid,
                "background_realization_id": bg,
                "split": "DEVELOPMENT",
                "truth_state": row["truth_state"],
                "evidence_plane": row["evidence_plane"],
                "gap_quality_regime": row["gap_quality_regime"],
                "n_samples": int(row["n_samples"]),
                "red_noise_alpha": float(row["red_noise_alpha"]),
                "qpp_fraction": qfrac_value,
                "true_period_s": true_period_value,
                "qpp_phase_rad": phase_value,
                "signal_family": signal_family_value,
                "latent_offset": latent_offset,
                "latent_length": latent_len,
                "latent_flux_sha256": latent_sha,
                "retained_offset": retained_offset,
                "retained_length": retained_len,
                "retained_time_sha256": retained_time_sha,
                "retained_flux_sha256": retained_flux_sha,
                "retained_native_index_sha256": retained_idx_sha,
                "logical_payload_sha256": logical_sha,
                "input_state": admiss["input_state"],
                "inadmissibility_reasons": admiss["all_triggered_reasons"],
                "primary_inadmissibility_reason":
                    admiss["primary_inadmissibility_reason"],
                "materialization_status": materialization_status,
            }
        )

        truth_ledger.append(truth)

        admissibility_rows.append(
            {
                "simulation_unit_id": sid,
                "background_realization_id": bg,
                "truth_state": row["truth_state"],
                "evidence_plane": row["evidence_plane"],
                "gap_quality_regime": row["gap_quality_regime"],
                "retained_cadences": admiss["retained_cadences"],
                "finite_time_flux": admiss["finite_time_flux"],
                "strictly_increasing_time":
                    admiss["strictly_increasing_time"],
                "native_indices_consecutive":
                    admiss["native_indices_consecutive"],
                "no_duplicate_times": admiss["no_duplicate_times"],
                "no_duplicate_native_indices":
                    admiss["no_duplicate_native_indices"],
                "regular_cadence_tolerance_s":
                    admiss["regular_cadence_tolerance_s"],
                "peak_retained": admiss["peak_retained"],
                "all_triggered_reasons":
                    admiss["all_triggered_reasons"],
                "primary_inadmissibility_reason":
                    admiss["primary_inadmissibility_reason"],
                "irregular_sampling_details":
                    admiss["irregular_sampling_details"],
                "input_state": admiss["input_state"],
                "materialization_status": materialization_status,
            }
        )

        payload_manifest.append(
            {
                "simulation_unit_id": sid,
                "background_realization_id": bg,
                "latent_array_file": ARRAY_FILES["latent_flux"],
                "latent_offset": latent_offset,
                "latent_length": latent_len,
                "latent_flux_sha256": latent_sha,
                "retained_time_array_file": ARRAY_FILES["retained_time_s"],
                "retained_flux_array_file": ARRAY_FILES["retained_flux"],
                "retained_native_index_array_file":
                    ARRAY_FILES["retained_native_index"],
                "retained_offset": retained_offset,
                "retained_length": retained_len,
                "retained_time_sha256": retained_time_sha,
                "retained_flux_sha256": retained_flux_sha,
                "retained_native_index_sha256": retained_idx_sha,
                "logical_payload_sha256": logical_sha,
                "materialization_status": materialization_status,
            }
        )

    def concatenate_or_empty(chunks, dtype):
        if not chunks:
            return np.asarray([], dtype=dtype)
        return np.concatenate(chunks).astype(dtype, copy=False)

    arrays = {
        "background_noise": concatenate_or_empty(
            background_noise_chunks, np.float64
        ),
        "background_offsets": np.asarray(background_offsets, dtype=np.int64),
        "latent_flux": concatenate_or_empty(latent_chunks, np.float64),
        "latent_offsets": np.asarray(latent_offsets, dtype=np.int64),
        "retained_time_s": concatenate_or_empty(
            retained_time_chunks, np.float64
        ),
        "retained_flux": concatenate_or_empty(
            retained_flux_chunks, np.float64
        ),
        "retained_native_index": concatenate_or_empty(
            retained_index_chunks, np.int64
        ),
        "retained_offsets": np.asarray(retained_offsets, dtype=np.int64),
    }

    if len(background_manifest) != 1800:
        raise RuntimeError("Background manifest row count != 1800.")
    if len(series_manifest) != 4320:
        raise RuntimeError("Series manifest row count != 4320.")
    if len(truth_ledger) != 4320:
        raise RuntimeError("Truth ledger row count != 4320.")
    if len(admissibility_rows) != 4320:
        raise RuntimeError("Admissibility row count != 4320.")
    if len(payload_manifest) != 4320:
        raise RuntimeError("Payload manifest row count != 4320.")
    if len(arrays["background_offsets"]) != 1801:
        raise RuntimeError("background_offsets length != 1801.")
    if len(arrays["latent_offsets"]) != 4321:
        raise RuntimeError("latent_offsets length != 4321.")
    if len(arrays["retained_offsets"]) != 4321:
        raise RuntimeError("retained_offsets length != 4321.")

    if write_arrays:
        if output_dir.exists():
            raise RuntimeError(
                "Output directory already exists; refusing overwrite: "
                + str(output_dir)
            )
        output_dir.mkdir(parents=True)
        for key, filename in ARRAY_FILES.items():
            np.save(output_dir / filename, arrays[key], allow_pickle=False)

    return {
        "background_manifest": background_manifest,
        "series_manifest": series_manifest,
        "truth_ledger": truth_ledger,
        "admissibility": admissibility_rows,
        "payload_manifest": payload_manifest,
        "arrays": arrays,
        "background_hashes": background_hashes,
        "latent_hashes": latent_hashes,
        "retained_payload_hashes": retained_payload_hashes,
        "truth_hashes": truth_hashes,
        "generation_failures": generation_failures,
        "counts": {
            "background_rng_initializations": background_rng_initializations,
            "period_draws": period_draws,
            "phase_draws": phase_draws,
            "noise_draws": noise_draws,
            "redraw_total": redraw_total,
        },
    }


def roundtrip_validate(
    *,
    repo: Path,
    f3b: Any,
    result: dict[str, Any],
) -> dict[str, int]:
    arr_dir = repo / ARRAY_DIR
    loaded = {
        key: np.load(arr_dir / filename, allow_pickle=False)
        for key, filename in ARRAY_FILES.items()
    }

    # Exact dtype contract.
    expected_dtypes = {
        "background_noise": np.dtype("float64"),
        "background_offsets": np.dtype("int64"),
        "latent_flux": np.dtype("float64"),
        "latent_offsets": np.dtype("int64"),
        "retained_time_s": np.dtype("float64"),
        "retained_flux": np.dtype("float64"),
        "retained_native_index": np.dtype("int64"),
        "retained_offsets": np.dtype("int64"),
    }
    for key, dtype in expected_dtypes.items():
        if loaded[key].dtype != dtype:
            raise RuntimeError(
                f"Roundtrip dtype mismatch for {key}: "
                f"{loaded[key].dtype} != {dtype}"
            )

    bg_mismatch = 0
    bg_rows = sorted(
        result["background_manifest"],
        key=lambda r: r["background_realization_id"],
    )
    for i, row in enumerate(bg_rows):
        start = int(loaded["background_offsets"][i])
        end = int(loaded["background_offsets"][i + 1])
        noise = loaded["background_noise"][start:end]
        if row["generation_status"] == "MATERIALIZED":
            if f3b.canonical_float64_sha256(noise) != row["noise_sha256"]:
                bg_mismatch += 1
        elif len(noise) != 0:
            bg_mismatch += 1

    series_mismatch = 0
    series_rows = result["series_manifest"]
    for i, row in enumerate(series_rows):
        l0 = int(loaded["latent_offsets"][i])
        l1 = int(loaded["latent_offsets"][i + 1])
        r0 = int(loaded["retained_offsets"][i])
        r1 = int(loaded["retained_offsets"][i + 1])
        latent = loaded["latent_flux"][l0:l1]
        rt = loaded["retained_time_s"][r0:r1]
        rf = loaded["retained_flux"][r0:r1]
        ri = loaded["retained_native_index"][r0:r1]

        if row["materialization_status"] == "MATERIALIZED":
            checks = [
                f3b.canonical_float64_sha256(latent)
                == row["latent_flux_sha256"],
                f3b.canonical_float64_sha256(rt)
                == row["retained_time_sha256"],
                f3b.canonical_float64_sha256(rf)
                == row["retained_flux_sha256"],
                f3b.canonical_int64_sha256(ri)
                == row["retained_native_index_sha256"],
                f3b.logical_payload_sha256(
                    row["simulation_unit_id"], rt, rf, ri
                ) == row["logical_payload_sha256"],
            ]
            if not all(checks):
                series_mismatch += 1
        elif any(len(x) for x in [latent, rt, rf, ri]):
            series_mismatch += 1

    return {
        "background_roundtrip_mismatches": bg_mismatch,
        "series_roundtrip_mismatches": series_mismatch,
    }


def rematerialization_validate(
    *,
    repo: Path,
    f3b: Any,
    development_rows: list[dict[str, str]],
    heldout_backgrounds: set[str],
    first: dict[str, Any],
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="f3b2_rematerialization_") as td:
        temp_dir = Path(td) / "f3b2_development"
        second = materialize_dataset(
            repo=repo,
            f3b=f3b,
            development_rows=development_rows,
            heldout_backgrounds=heldout_backgrounds,
            output_dir=temp_dir,
            write_arrays=True,
        )

        bg_mismatch = sum(
            first["background_hashes"].get(k)
            != second["background_hashes"].get(k)
            for k in first["background_hashes"]
        )
        latent_mismatch = sum(
            first["latent_hashes"].get(k)
            != second["latent_hashes"].get(k)
            for k in first["latent_hashes"]
        )
        retained_mismatch = sum(
            first["retained_payload_hashes"].get(k)
            != second["retained_payload_hashes"].get(k)
            for k in first["retained_payload_hashes"]
        )
        truth_mismatch = sum(
            first["truth_hashes"].get(k)
            != second["truth_hashes"].get(k)
            for k in first["truth_hashes"]
        )

        # Compare exact .npy file bytes as an additional deterministic guard.
        array_byte_mismatches = 0
        for filename in ARRAY_FILES.values():
            if (repo / ARRAY_DIR / filename).read_bytes() != (
                temp_dir / filename
            ).read_bytes():
                array_byte_mismatches += 1

    return {
        "background_hash_mismatches": int(bg_mismatch),
        "latent_hash_mismatches": int(latent_mismatch),
        "retained_payload_hash_mismatches": int(retained_mismatch),
        "truth_record_mismatches": int(truth_mismatch),
        "array_file_byte_mismatches": int(array_byte_mismatches),
        "status": (
            "F3B2_DEVELOPMENT_REMATERIALIZATION_EXACT"
            if not any(
                [
                    bg_mismatch,
                    latent_mismatch,
                    retained_mismatch,
                    truth_mismatch,
                    array_byte_mismatches,
                ]
            )
            else "REMATERIALIZATION_MISMATCH"
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()
    repo = Path(args.repo_root).resolve()

    if gt(repo, "rev-parse", "HEAD") != EXPECTED_HEAD:
        raise RuntimeError(
            "Full DEVELOPMENT materialization must run from the committed "
            "F3B.2 implementation-binding HEAD."
        )
    if gt(repo, "rev-parse", F3B1_TAG + "^{}") != F3B1_COMMIT:
        raise RuntimeError("F3B.1 authoritative tag mismatch.")

    if sys.version_info[:2] != (3, 13):
        raise RuntimeError(
            f"Python binding mismatch: {sys.version_info[:2]} != (3,13)"
        )
    if np.__version__ != "2.3.5":
        raise RuntimeError(
            f"NumPy binding mismatch: {np.__version__} != 2.3.5"
        )
    if sys.byteorder != "little":
        raise RuntimeError("F3B.2 binding requires little-endian execution.")

    # No staged changes. The only permitted dirty pre-state is the reviewed
    # 88-series canary evidence + canary script.
    if gt(repo, "diff", "--cached", "--name-only"):
        raise RuntimeError("Staged changes exist before DEVELOPMENT materialization.")
    status_lines = run(
        repo, "status", "--short", "--untracked-files=all"
    ).stdout.decode("utf-8", errors="replace").splitlines()
    changed_paths = {
        line[3:].strip().replace("\\", "/")
        for line in status_lines
        if line.strip()
    }

    tooling_incident_recovered = False
    expected_with_stale_v2 = (
        EXPECTED_PREEXISTING_UNTRACKED | {STALE_FAILED_V2_REPO_SCRIPT}
    )
    if changed_paths == expected_with_stale_v2:
        stale = repo / STALE_FAILED_V2_REPO_SCRIPT
        if not stale.is_file():
            raise RuntimeError("Expected stale failed-v2 helper is missing.")
        if sha_file(stale) != STALE_FAILED_V2_SHA256:
            raise RuntimeError(
                "Stale failed-v2 helper exists but SHA is not the exact "
                "known failed helper; refusing automatic recovery."
            )
        if (repo / ARRAY_DIR).exists():
            raise RuntimeError(
                "DEVELOPMENT arrays exist after failed-v2 NameError; "
                "manual audit required."
            )
        if (repo / HELDOUT_ARRAY_DIR).exists():
            raise RuntimeError(
                "HELDOUT array directory exists after failed-v2 NameError."
            )
        # The NameError occurred immediately after copying the helper, before
        # importing the F3B generator or initializing any F3B RNG.
        stale.unlink()
        tooling_incident_recovered = True
        changed_paths = EXPECTED_PREEXISTING_UNTRACKED.copy()

    if changed_paths != EXPECTED_PREEXISTING_UNTRACKED:
        raise RuntimeError(
            "Unexpected pre-materialization working-tree changes: "
            + repr(sorted(changed_paths))
        )

    for rel, expected_sha in EXPECTED_HASHES.items():
        path = repo / rel
        if not path.is_file() or sha_file(path) != expected_sha:
            raise RuntimeError("Frozen/reviewed SHA mismatch: " + rel)

    # The canary itself must have passed before full DEVELOPMENT generation.
    canary_audit = json.loads(
        (repo / CANARY_AUDIT).read_text(encoding="utf-8")
    )
    if canary_audit["status"] != "F3B2_GENERATOR_CANARY_PASS":
        raise RuntimeError("F3B canary has not passed.")
    if (
        canary_audit["f1_generator_continuity_status"]
        != "F3B2_F1_GENERATOR_CONTINUITY_PASS"
    ):
        raise RuntimeError("F1 continuity status is not PASS.")
    valid_env = canary_audit.get("execution_environment", {})
    if valid_env.get("numpy_version") != "2.3.5":
        raise RuntimeError("Valid canary audit is not bound to NumPy 2.3.5.")
    if valid_env.get("byteorder") != "little":
        raise RuntimeError("Valid canary audit byteorder is not little.")
    if valid_env.get("python_major_minor") != [3, 13]:
        raise RuntimeError("Valid canary audit Python major/minor is not 3.13.")

    # No overwrite and no HELDOUT dataset.
    targets = [
        repo / REPO_SCRIPT,
        repo / BACKGROUND_MANIFEST,
        repo / SERIES_MANIFEST,
        repo / TRUTH_LEDGER,
        repo / ADMISSIBILITY,
        repo / PAYLOAD_MANIFEST,
        repo / MATERIALIZATION_AUDIT,
        repo / HELDOUT_AUDIT,
        repo / LEAKAGE_AUDIT,
    ]
    for p in targets:
        if p.exists():
            raise RuntimeError("Refusing to overwrite F3B.2 artifact: " + str(p))
    if (repo / ARRAY_DIR).exists():
        raise RuntimeError("DEVELOPMENT array directory already exists.")
    if (repo / HELDOUT_ARRAY_DIR).exists():
        raise RuntimeError("HELDOUT array directory exists before materialization.")

    # Preserve exact HELDOUT README guard.
    heldout_guard = repo / "workflows/phase3b/heldout/README.md"
    tagged_guard = run(
        repo,
        "show",
        F3B1_TAG + ":workflows/phase3b/heldout/README.md",
    ).stdout
    if heldout_guard.read_bytes() != tagged_guard:
        raise RuntimeError("HELDOUT README guard differs from F3B.1.")

    # Copy exact executed helper into repository before materialization so the
    # evidence always contains the generating implementation.
    source = Path(__file__).read_bytes()
    repo_script = repo / REPO_SCRIPT
    repo_script.parent.mkdir(parents=True, exist_ok=True)
    repo_script.write_bytes(source)
    py_compile.compile(
        str(repo_script),
        cfile=str(Path(tempfile.gettempdir()) / "materialize_f3b_development.pyc"),
        doraise=True,
    )
    if sha_file(repo_script) != sha_bytes(source):
        raise RuntimeError("Repository materializer script copy mismatch.")

    f3b = load_module(repo / GENERATOR_PATH, "f3b2_full_materializer_generator")
    binding = json.loads((repo / BINDING_PATH).read_text(encoding="utf-8"))
    if binding["environment_binding"]["numpy_version"] != "2.3.5":
        raise RuntimeError("Binding NumPy version differs from expected.")

    split_rows = read_csv(repo / SPLIT_PATH)
    development_rows = [
        r for r in split_rows if r["split"] == "DEVELOPMENT"
    ]
    heldout_rows = [
        r for r in split_rows if r["split"] == "HELDOUT"
    ]
    if len(development_rows) != 4320 or len(heldout_rows) != 4320:
        raise RuntimeError("Split registry is not 4320 DEVELOPMENT / 4320 HELDOUT.")
    dev_backgrounds, heldout_backgrounds = validate_background_registry(
        development_rows, heldout_rows
    )

    primary_rows = [
        r for r in development_rows
        if r["gap_quality_regime"] == "CONTIGUOUS_ALL_GOOD"
    ]
    challenge_rows = [
        r for r in development_rows
        if r["gap_quality_regime"] != "CONTIGUOUS_ALL_GOOD"
    ]
    if len(primary_rows) != 3600 or len(challenge_rows) != 720:
        raise RuntimeError("Frozen DEVELOPMENT primary/challenge counts mismatch.")
    if Counter(r["truth_state"] for r in development_rows) != Counter(
        {
            "SYNTHETIC_QPP_PRESENT": 2160,
            "SYNTHETIC_QPP_ABSENT": 2160,
        }
    ):
        raise RuntimeError("Frozen DEVELOPMENT truth counts mismatch.")

    first = materialize_dataset(
        repo=repo,
        f3b=f3b,
        development_rows=development_rows,
        heldout_backgrounds=heldout_backgrounds,
        output_dir=repo / ARRAY_DIR,
        write_arrays=True,
    )

    # Write Git evidence tables deterministically.
    bg_fields = [
        "background_realization_id", "split", "n_samples", "duration_s",
        "red_noise_alpha", "positive_pair_qpp_fraction",
        "split_rank_sha256", "challenge_rank_sha256",
        "background_entropy", "period_entropy",
        "noise_offset", "noise_length", "noise_sha256",
        "phase_rad", "phase_sha256_or_canonical_repr",
        "true_period_s", "period_upper_bound_s", "cycles_in_window",
        "generation_status", "generation_failure_reason", "redraw_count",
    ]
    series_fields = [
        "simulation_unit_id", "background_realization_id", "split",
        "truth_state", "evidence_plane", "gap_quality_regime",
        "n_samples", "red_noise_alpha", "qpp_fraction",
        "true_period_s", "qpp_phase_rad", "signal_family",
        "latent_offset", "latent_length", "latent_flux_sha256",
        "retained_offset", "retained_length",
        "retained_time_sha256", "retained_flux_sha256",
        "retained_native_index_sha256", "logical_payload_sha256",
        "input_state", "inadmissibility_reasons",
        "primary_inadmissibility_reason", "materialization_status",
    ]
    truth_fields = [
        "simulation_unit_id", "truth_state",
        "synthetic_ground_truth_known", "qpp_component_present",
        "true_period_s", "qpp_fraction", "qpp_phase_rad",
        "signal_family", "n_samples", "red_noise_alpha",
        "gap_quality_regime", "truth_source", "truth_sha256",
    ]
    adm_fields = [
        "simulation_unit_id", "background_realization_id", "truth_state",
        "evidence_plane", "gap_quality_regime", "retained_cadences",
        "finite_time_flux", "strictly_increasing_time",
        "native_indices_consecutive", "no_duplicate_times",
        "no_duplicate_native_indices", "regular_cadence_tolerance_s",
        "peak_retained", "all_triggered_reasons",
        "primary_inadmissibility_reason", "irregular_sampling_details",
        "input_state", "materialization_status",
    ]
    payload_fields = [
        "simulation_unit_id", "background_realization_id",
        "latent_array_file", "latent_offset", "latent_length",
        "latent_flux_sha256", "retained_time_array_file",
        "retained_flux_array_file", "retained_native_index_array_file",
        "retained_offset", "retained_length", "retained_time_sha256",
        "retained_flux_sha256", "retained_native_index_sha256",
        "logical_payload_sha256", "materialization_status",
    ]

    table_payloads = {
        repo / BACKGROUND_MANIFEST:
            csv_bytes(first["background_manifest"], bg_fields),
        repo / SERIES_MANIFEST:
            csv_bytes(first["series_manifest"], series_fields),
        repo / TRUTH_LEDGER:
            csv_bytes(first["truth_ledger"], truth_fields),
        repo / ADMISSIBILITY:
            csv_bytes(first["admissibility"], adm_fields),
        repo / PAYLOAD_MANIFEST:
            csv_bytes(first["payload_manifest"], payload_fields),
    }
    for path, data in table_payloads.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    # Persistent-array roundtrip and independent full rematerialization.
    roundtrip = roundtrip_validate(repo=repo, f3b=f3b, result=first)
    if roundtrip["background_roundtrip_mismatches"] != 0:
        raise RuntimeError("Background roundtrip mismatch.")
    if roundtrip["series_roundtrip_mismatches"] != 0:
        raise RuntimeError("Series payload roundtrip mismatch.")

    remat = rematerialization_validate(
        repo=repo,
        f3b=f3b,
        development_rows=development_rows,
        heldout_backgrounds=heldout_backgrounds,
        first=first,
    )
    if remat["status"] != "F3B2_DEVELOPMENT_REMATERIALIZATION_EXACT":
        raise RuntimeError("Full DEVELOPMENT rematerialization mismatch.")

    # Structural counts — no classifier/scientific metric is computed.
    input_counts = Counter(
        r["input_state"] for r in first["admissibility"]
    )
    primary_input_counts = Counter(
        r["input_state"]
        for r in first["admissibility"]
        if r["evidence_plane"] == "SYNTHETIC_GROUND_TRUTH_CLASSIFICATION"
    )
    challenge_input_counts = Counter(
        r["input_state"]
        for r in first["admissibility"]
        if r["evidence_plane"] == "INPUT_ADMISSIBILITY"
    )
    primary_reason_counts = Counter(
        r["primary_inadmissibility_reason"]
        for r in first["admissibility"]
        if r["primary_inadmissibility_reason"]
    )
    all_reason_counts: Counter[str] = Counter()
    for r in first["admissibility"]:
        for code in str(r["all_triggered_reasons"]).split("|"):
            if code:
                all_reason_counts[code] += 1

    positive_periods = [
        float(r["true_period_s"])
        for r in first["truth_ledger"]
        if (
            r["truth_state"] == "SYNTHETIC_QPP_PRESENT"
            and isinstance(r["true_period_s"], float)
        )
    ]
    positive_background_rows = [
        r for r in first["background_manifest"]
        if r["generation_status"] == "MATERIALIZED"
    ]
    period_support_pass = all(40.0 <= p <= 300.0 for p in positive_periods)
    min_cycle_pass = all(
        float(r["cycles_in_window"]) >= 3.0
        for r in positive_background_rows
    )

    generation_failure_count = len(first["generation_failures"])
    if generation_failure_count:
        status = (
            "PHASE3B_DEVELOPMENT_GENERATOR_VALIDATED_AND_MATERIALIZED_"
            "WITH_LIMITATION_PENDING_PLAN_FREEZE"
        )
    else:
        status = (
            "PHASE3B_DEVELOPMENT_GENERATOR_VALIDATED_AND_MATERIALIZED_"
            "PENDING_PLAN_FREEZE"
        )

    array_hashes = {
        filename: sha_file(repo / ARRAY_DIR / filename)
        for filename in ARRAY_FILES.values()
    }

    materialization_audit = {
        "schema_version": 1,
        "phase": "F3B.2",
        "artifact_role": "DEVELOPMENT_MATERIALIZATION_AUDIT",
        "status": status,
        "final_f3b2_status_not_yet_declared": True,
        "f3b1_design_tag": F3B1_TAG,
        "f3b1_design_commit": F3B1_COMMIT,
        "f3b2_implementation_binding_commit": EXPECTED_HEAD,
        "f1_generator_continuity_status":
            canary_audit["f1_generator_continuity_status"],
        "generator_canary_status": canary_audit["status"],
        "generator_canary_environment": canary_audit["execution_environment"],
        "pre_materialization_environment_incident": {
            "incident_id": "F3B2-ENV-001",
            "invalidated_canary_numpy_version": "2.5.1",
            "bound_and_valid_numpy_version": "2.3.5",
            "quarantine_archive_sha256": "752749fe09bdace7ab878121e677fc55a54fd74774eec2419db84ce26e10cbd5",
            "invalid_canary_used_as_scientific_evidence": False,
        },
        "pre_materialization_tooling_incident": {
            "incident_id": "F3B2-TOOL-001",
            "failed_helper_sha256": STALE_FAILED_V2_SHA256,
            "failure": "NameError: py_compile not imported",
            "failure_stage": (
                "after copying helper into repo, before loading F3B generator "
                "and before any full-DEVELOPMENT stochastic draw"
            ),
            "stale_helper_recovered": tooling_incident_recovered,
            "scientific_bytes_generated_by_failed_attempt": False,
            "heldout_bytes_generated_by_failed_attempt": False,
            "afino_executed_by_failed_attempt": False,
        },
        "development_registry_rows": len(development_rows),
        "development_backgrounds": len(dev_backgrounds),
        "primary_planned": len(primary_rows),
        "challenge_planned": len(challenge_rows),
        "positive_total": sum(
            r["truth_state"] == "SYNTHETIC_QPP_PRESENT"
            for r in development_rows
        ),
        "null_total": sum(
            r["truth_state"] == "SYNTHETIC_QPP_ABSENT"
            for r in development_rows
        ),
        "materialized_series": sum(
            r["materialization_status"] == "MATERIALIZED"
            for r in first["series_manifest"]
        ),
        "materialization_failures": sum(
            r["materialization_status"] == "GENERATION_FAILURE"
            for r in first["series_manifest"]
        ),
        "generation_failure_backgrounds": generation_failure_count,
        "primary_eligible": primary_input_counts.get(
            "ELIGIBLE_FOR_AFINO", 0
        ),
        "primary_inadmissible": primary_input_counts.get(
            "INPUT_INADMISSIBLE", 0
        ),
        "challenge_input_state_counts": dict(challenge_input_counts),
        "all_input_state_counts": dict(input_counts),
        "inadmissibility_primary_reason_counts":
            dict(primary_reason_counts),
        "inadmissibility_all_triggered_reason_counts":
            dict(all_reason_counts),
        "period_support_40_300_s_pass": period_support_pass,
        "minimum_cycles_ge_3_pass": min_cycle_pass,
        "background_roundtrip_mismatches":
            roundtrip["background_roundtrip_mismatches"],
        "series_roundtrip_mismatches":
            roundtrip["series_roundtrip_mismatches"],
        "rematerialization": remat,
        "arrays": {
            "directory": ARRAY_DIR.as_posix(),
            "files": array_hashes,
        },
        "heldout_registry_rows": len(heldout_rows),
        "heldout_materialized_rows": 0,
        "heldout_noise_draws": 0,
        "heldout_period_draws": 0,
        "heldout_phase_draws": 0,
        "heldout_flux_arrays": 0,
        "heldout_payloads": 0,
        "afino_executed": False,
        "candidate_rule_fitted": False,
        "candidate_thresholds_generated": False,
        "scientific_metrics_computed": False,
        "afino_plan_frozen": False,
        "next_required_block":
            "build exact DEVELOPMENT AFINO decision grid/plan and final validator",
    }
    write_json(repo / MATERIALIZATION_AUDIT, materialization_audit)

    heldout_audit = {
        "schema_version": 1,
        "phase": "F3B.2",
        "artifact_role": "HELDOUT_NONMATERIALIZATION_AUDIT",
        "status": "F3B2_HELDOUT_NONMATERIALIZATION_PASS",
        "heldout_registry_rows": len(heldout_rows),
        "heldout_backgrounds": len(heldout_backgrounds),
        "heldout_background_rng_initializations": 0,
        "heldout_period_draws": 0,
        "heldout_phase_draws": 0,
        "heldout_noise_draws": 0,
        "heldout_flux_arrays": 0,
        "heldout_payloads": 0,
        "heldout_generated": False,
        "heldout_accessed": False,
        "heldout_array_directory_exists": (repo / HELDOUT_ARRAY_DIR).exists(),
        "heldout_readme_byte_exact_to_f3b1_tag":
            heldout_guard.read_bytes() == tagged_guard,
    }
    if heldout_audit["heldout_array_directory_exists"]:
        raise RuntimeError("HELDOUT array directory appeared during materialization.")
    write_json(repo / HELDOUT_AUDIT, heldout_audit)

    leakage_audit = {
        "schema_version": 1,
        "phase": "F3B.2",
        "artifact_role": "DEVELOPMENT_LEAKAGE_AUDIT",
        "status": "F3B2_DEVELOPMENT_LEAKAGE_AUDIT_PASS",
        "development_backgrounds": len(dev_backgrounds),
        "heldout_backgrounds": len(heldout_backgrounds),
        "background_split_overlap": len(dev_backgrounds & heldout_backgrounds),
        "heldout_stochastic_draws": 0,
        "truth_used_to_construct_positive_null_series": True,
        "truth_used_as_afino_inference_feature": False,
        "observational_labels_used_as_truth": False,
        "development_outcomes_observed": False,
        "afino_executed": False,
        "candidate_rule_fitted": False,
        "candidate_thresholds_generated": False,
        "scientific_metrics_computed": False,
    }
    write_json(repo / LEAKAGE_AUDIT, leakage_audit)

    # Historical scopes and heldout guard still exact.
    for scope in [
        "foundation/f0-f2",
        "docs/literature/bibliographic_audit_ii",
        "workflows/phase3a",
    ]:
        if gt(repo, "diff", "--name-only", F3B1_COMMIT, "--", scope):
            raise RuntimeError("Protected historical scope changed: " + scope)
    if heldout_guard.read_bytes() != tagged_guard:
        raise RuntimeError("HELDOUT README changed during F3B.2 materialization.")

    print("F3B2_DEVELOPMENT_MATERIALIZATION_PASS")
    print("valid_canary_builder_sha256 = 04508c681ba686d6fc8c70bcfdbb3211d99aeed7299e4e8b81e1fb9da27e91e2")
    print("valid_canary_audit_sha256 = e17ed74394c8cc0f78c65dc72a7385168fda626402a794a3b84be18383bec9f7")
    print("valid_canary_numpy_version = 2.3.5")
    print("invalid_canary_incident_id = F3B2-ENV-001")
    print("invalid_canary_used_as_scientific_evidence = false")
    print("tooling_incident_id = F3B2-TOOL-001")
    print("failed_v2_stale_helper_recovered =", str(tooling_incident_recovered).lower())
    print("failed_v2_scientific_bytes_generated = false")
    print("materialization_status =", status)
    print("materializer_sha256 =", sha_file(repo / REPO_SCRIPT))
    print("development_registry_rows = 4320")
    print("development_backgrounds = 1800")
    print("primary_planned = 3600")
    print("challenge_planned = 720")
    print("positive_total = 2160")
    print("null_total = 2160")
    print(
        "materialized_series =",
        materialization_audit["materialized_series"],
    )
    print(
        "materialization_failures =",
        materialization_audit["materialization_failures"],
    )
    print("primary_eligible =", materialization_audit["primary_eligible"])
    print("primary_inadmissible =", materialization_audit["primary_inadmissible"])
    print(
        "challenge_input_state_counts =",
        json.dumps(dict(challenge_input_counts), sort_keys=True),
    )
    print(
        "inadmissibility_primary_reason_counts =",
        json.dumps(dict(primary_reason_counts), sort_keys=True),
    )
    print(
        "inadmissibility_all_triggered_reason_counts =",
        json.dumps(dict(all_reason_counts), sort_keys=True),
    )
    print("period_support_40_300_s = PASS" if period_support_pass else
          "period_support_40_300_s = FAIL")
    print("minimum_cycles_ge_3 = PASS" if min_cycle_pass else
          "minimum_cycles_ge_3 = FAIL")
    print("background_roundtrip = 1800/1800 EXACT")
    print("series_payload_roundtrip = 4320/4320 EXACT")
    print("rematerialization_status =", remat["status"])
    print("rematerialization_background_hash_mismatches =",
          remat["background_hash_mismatches"])
    print("rematerialization_latent_hash_mismatches =",
          remat["latent_hash_mismatches"])
    print("rematerialization_retained_payload_hash_mismatches =",
          remat["retained_payload_hash_mismatches"])
    print("rematerialization_truth_record_mismatches =",
          remat["truth_record_mismatches"])
    print("rematerialization_array_file_byte_mismatches =",
          remat["array_file_byte_mismatches"])
    print("background_manifest_sha256 =", sha_file(repo / BACKGROUND_MANIFEST))
    print("series_manifest_sha256 =", sha_file(repo / SERIES_MANIFEST))
    print("truth_ledger_sha256 =", sha_file(repo / TRUTH_LEDGER))
    print("admissibility_sha256 =", sha_file(repo / ADMISSIBILITY))
    print("payload_manifest_sha256 =", sha_file(repo / PAYLOAD_MANIFEST))
    print("materialization_audit_sha256 =", sha_file(repo / MATERIALIZATION_AUDIT))
    print("heldout_nonmaterialization_audit_sha256 =", sha_file(repo / HELDOUT_AUDIT))
    print("development_leakage_audit_sha256 =", sha_file(repo / LEAKAGE_AUDIT))
    print("heldout_registry_rows = 4320")
    print("heldout_background_rng_initializations = 0")
    print("heldout_period_draws = 0")
    print("heldout_noise_draws = 0")
    print("heldout_flux_arrays = 0")
    print("heldout_generated = false")
    print("heldout_accessed = false")
    print("afino_executed = false")
    print("candidate_rule_fitted = false")
    print("scientific_metrics_computed = false")
    print("afino_plan_frozen = false")
    print("NEXT = review materialization; do not build/run AFINO yet")

if __name__ == "__main__":
    main()
