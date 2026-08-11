#!/usr/bin/env python3
"""
F3A.2 — materialize the frozen 78-cell observational robustness matrix for the
already frozen Phase 3A cohort, freeze exact payload arrays, resolve executable
decisions, and emit the exact AFINO model-call plan.

This task DOES NOT import or execute AFINO and DOES NOT compute QPP results.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits


EXPECTED_NUMPY = "2.5.1"

F3A1_HASHES = {
    "workflows/phase3a/design/cohort_contract.yaml":
        "613267b13bdcfbcb89859ee9f2ed7f072d161b43c295574b718a0d3061d48c86",
    "workflows/phase3a/design/reference_label_policy.json":
        "e139db5e335eb6ae059a25166e08918c9fa5f7ae2d9a7f6d406ef5c52e2412f0",
    "workflows/phase3a/design/robustness_matrix.csv":
        "2412c686b91a287361865347f8159fb48fabae809eee783222dbbc190f0d3590",
    "workflows/phase3a/design/outcomes_denominators.json":
        "59b5513c763e6fba0859ddd139ca9c746374b75c0682dfa8e6c474ed47d3234c",
    "workflows/phase3a/design/numerical_stability_protocol.json":
        "c7869210a9d7d75532d285349a39f62be108e72acb53dd4143e2e4891b66686a",
    "workflows/phase3a/design/preregistration.json":
        "b37741f058b6cc133014b52bef6621ee34ddfc9cc671d80113c2ec7b76094ba5",
}

COHORT_REL = Path("workflows/phase3a/evidence/tables/f3a2_cohort_manifest.csv")
PRODUCT_REL = Path("workflows/phase3a/evidence/tables/f3a2_tess_product_manifest.csv")
TIME_REL = Path("workflows/phase3a/evidence/tables/f3a2_time_mapping_audit.csv")
MATRIX_REL = Path("workflows/phase3a/design/robustness_matrix.csv")

VARIANT_REL = Path("workflows/phase3a/evidence/tables/f3a2_primary_variant_manifest.csv")
PAYLOAD_MANIFEST_REL = Path("workflows/phase3a/evidence/tables/f3a2_payload_manifest.csv")
DECISION_REL = Path("workflows/phase3a/evidence/tables/f3a2_resolved_decision_grid.csv")
PLAN_REL = Path("workflows/phase3a/evidence/tables/f3a2_exact_afino_plan.csv")

PAYLOAD_DIR_REL = Path("data/interim/phase3a/f3a2_payloads")
RAW_FITS_REL = Path("data/raw/phase3a/tess")

AFINO_VERSION = "0.5"
AFINO_COMMIT = "6aceac9518fc8056052807e666da9d0c8bebb010"
LOW_FREQUENCY_CUTOFF_HZ = 0.025
MODEL_ROWS = [
    ("M0", "pow_const"),
    ("M1", "pow_const_gauss"),
    ("M2", "bpow_const"),
]

INADMISSIBILITY_CODES = {
    "MISSING_PRODUCT",
    "WINDOW_OUT_OF_RANGE",
    "PEAK_OUTSIDE_WINDOW",
    "PEAK_REMOVED_BY_QUALITY",
    "TOO_FEW_CADENCES",
    "NONFINITE_INPUT",
    "IRREGULAR_SAMPLING",
    "DETREND_FAILURE",
    "SOURCE_TIME_MAPPING_UNRESOLVED",
}

VARIANT_FIELDS = [
    "variant_id",
    "variant_order",
    "primary_planned_decision_id",
    "phase3a_event_id",
    "pair_id",
    "observational_reference_role",
    "matrix_cell_id",
    "window_variant_id",
    "processing_profile_id",
    "flux_product",
    "quality_policy",
    "detrending",
    "external_optimizer_seed",
    "source_fits_filename",
    "source_fits_sha256",
    "baseline_start_index",
    "baseline_peak_index",
    "baseline_end_index",
    "shifted_start_index",
    "shifted_end_index",
    "raw_n_samples",
    "retained_n_samples",
    "removed_nonfinite_count",
    "removed_quality_count",
    "peak_in_raw_window",
    "peak_retained",
    "retained_index_start",
    "retained_index_end",
    "retained_indices_consecutive",
    "retained_indices_sha256",
    "time_strictly_increasing",
    "time_has_duplicates",
    "median_cadence_s",
    "max_interval_deviation_s",
    "detrend_beta0",
    "detrend_beta1",
    "detrend_scale",
    "materialization_status",
    "inadmissibility_reason_code",
    "inadmissibility_reason",
    "diagnostic_flags_json",
    "eligible_payload_order",
    "payload_offset",
    "payload_length",
    "time_sha256",
    "flux_sha256",
    "native_index_sha256",
    "logical_payload_sha256",
    "all_finite",
    "error",
]

PAYLOAD_FIELDS = [
    "payload_id",
    "variant_id",
    "offset",
    "length",
    "time_sha256",
    "flux_sha256",
    "native_index_sha256",
    "logical_payload_sha256",
    "n_samples",
    "first_time_s",
    "last_time_s",
    "time_dtype",
    "flux_dtype",
    "native_index_dtype",
]

DECISION_FIELDS = [
    "planned_decision_id",
    "decision_order",
    "decision_class",
    "phase3a_event_id",
    "pair_id",
    "observational_reference_role",
    "variant_id",
    "matrix_cell_id",
    "window_variant_id",
    "processing_profile_id",
    "external_optimizer_seed",
    "payload_id",
    "payload_logical_sha256",
    "input_n_samples",
    "resolved_decision_status",
]

PLAN_FIELDS = [
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
    "afino_version",
    "afino_commit",
    "low_frequency_cutoff_hz",
    "seed_application_contract",
    "selection_rule",
    "execution_status",
]


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


def canonical_array_hash(values: Any, dtype: str) -> str:
    arr = canonical_array(values, dtype)
    return sha256_bytes(arr.tobytes(order="C"))


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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})
    tmp.replace(path)


def verify_frozen_inputs(repo: Path) -> None:
    for rel, expected in F3A1_HASHES.items():
        p = repo / rel
        if not p.is_file():
            raise RuntimeError(f"Missing frozen F3A.1 input: {rel}")
        actual = sha256_file(p)
        if actual != expected:
            raise RuntimeError(
                f"Frozen F3A.1 hash mismatch: {rel}\n"
                f"expected={expected}\nactual={actual}"
            )


def load_and_validate_matrix(repo: Path) -> list[dict[str, str]]:
    rows = read_csv(repo / MATRIX_REL)
    if len(rows) != 78:
        raise RuntimeError(f"Expected 78 frozen matrix cells, got {len(rows)}")
    if len({r["matrix_cell_id"] for r in rows}) != 78:
        raise RuntimeError("Duplicate matrix_cell_id")
    if any(r["primary_or_secondary"] != "PRIMARY" for r in rows):
        raise RuntimeError("Non-primary cell found in frozen primary matrix")
    if any(r["changes_from_f2"] != "NONE" for r in rows):
        raise RuntimeError("A matrix cell changes the F2 definition")
    if any(r["external_optimizer_seed"] != "0" for r in rows):
        raise RuntimeError("Primary matrix seed is not uniformly 0")
    combos = {
        (r["window_variant_id"], r["processing_profile_id"])
        for r in rows
    }
    if len(combos) != 78:
        raise RuntimeError("Frozen matrix is not a 78-cell Cartesian product")
    return rows


def fits_arrays(path: Path) -> tuple[dict[str, np.ndarray], int]:
    with fits.open(path, memmap=True, checksum=False) as hdul:
        if len(hdul) < 2 or getattr(hdul[1], "data", None) is None:
            raise RuntimeError(f"No LC table in {path}")
        d = hdul[1].data
        names = set(d.names or [])
        required = {"TIME", "SAP_FLUX", "PDCSAP_FLUX", "QUALITY"}
        missing = sorted(required - names)
        if missing:
            raise RuntimeError(f"Missing FITS columns in {path.name}: {missing}")
        arrays = {
            "TIME": np.asarray(d["TIME"], dtype=np.float64),
            "SAP_FLUX": np.asarray(d["SAP_FLUX"], dtype=np.float64),
            "PDCSAP_FLUX": np.asarray(d["PDCSAP_FLUX"], dtype=np.float64),
            "QUALITY": np.asarray(d["QUALITY"], dtype=np.int64),
        }
        return arrays, len(d)


def bool_text(v: bool | str) -> str:
    if isinstance(v, str):
        return v
    return "true" if v else "false"


def materialize_variant(
    event: dict[str, str],
    product: dict[str, str],
    cell: dict[str, str],
    arrays: dict[str, np.ndarray] | None,
    table_row_count: int | None,
) -> tuple[dict[str, Any], tuple[np.ndarray, np.ndarray, np.ndarray] | None]:
    baseline_start = int(product["source_start_index"]) if product["source_start_index"] else -1
    baseline_peak = int(product["source_peak_index"]) if product["source_peak_index"] else -1
    baseline_end = int(product["source_end_index"]) if product["source_end_index"] else -1

    shifted_start = baseline_start + int(cell["delta_start_cadences"])
    shifted_end = baseline_end + int(cell["delta_end_cadences"])

    flux_col = "PDCSAP_FLUX" if cell["flux_product"] == "PDCSAP" else "SAP_FLUX"

    row: dict[str, Any] = {
        "phase3a_event_id": event["phase3a_event_id"],
        "pair_id": event["pair_id"],
        "observational_reference_role": event["observational_reference_role"],
        "matrix_cell_id": cell["matrix_cell_id"],
        "window_variant_id": cell["window_variant_id"],
        "processing_profile_id": cell["processing_profile_id"],
        "flux_product": cell["flux_product"],
        "quality_policy": cell["quality_policy"],
        "detrending": cell["detrending"],
        "external_optimizer_seed": 0,
        "source_fits_filename": product.get("physical_filename", ""),
        "source_fits_sha256": product.get("physical_sha256", ""),
        "baseline_start_index": baseline_start if baseline_start >= 0 else "",
        "baseline_peak_index": baseline_peak if baseline_peak >= 0 else "",
        "baseline_end_index": baseline_end if baseline_end >= 0 else "",
        "shifted_start_index": shifted_start if baseline_start >= 0 else "",
        "shifted_end_index": shifted_end if baseline_end >= 0 else "",
    }

    diag = {
        "f2_definition_inherited": cell["f2_definition_inherited"],
        "changes_from_f2": cell["changes_from_f2"],
        "window_perturbation_family": cell["window_perturbation_family"],
        "product_status": product.get("product_status", ""),
        "time_mapping_status": product.get("time_mapping_status", ""),
    }

    reason_code = ""
    reason = ""
    error = ""
    payload = None

    raw_n = ""
    retained_n = ""
    removed_nonfinite = ""
    removed_quality = ""
    peak_in_raw: bool | str = ""
    peak_retained: bool | str = ""
    retained_start = ""
    retained_end = ""
    retained_consecutive: bool | str = ""
    retained_idx_sha = ""
    time_increasing: bool | str = ""
    time_duplicates: bool | str = ""
    median_cadence_s: float | str = ""
    max_dev_s: float | str = ""
    beta0: float | str = ""
    beta1: float | str = ""
    scale_out: float | str = ""
    all_finite: bool | str = ""

    try:
        if product.get("product_status") != "BOUND_DOWNLOADED" or arrays is None:
            reason_code = "MISSING_PRODUCT"
            reason = "Exact frozen product is unavailable."
        elif product.get("time_mapping_status") != "TIME_MAPPING_VALID":
            reason_code = "SOURCE_TIME_MAPPING_UNRESOLVED"
            reason = f"Event time mapping status={product.get('time_mapping_status','')}"
        elif (
            table_row_count is None
            or shifted_start < 0
            or shifted_end >= table_row_count
            or shifted_start > shifted_end
        ):
            reason_code = "WINDOW_OUT_OF_RANGE"
            reason = (
                f"Shifted inclusive window [{shifted_start},{shifted_end}] "
                f"outside [0,{(table_row_count or 0)-1}] or start>end."
            )
        else:
            raw_idx = np.arange(shifted_start, shifted_end + 1, dtype=np.int64)
            raw_n = len(raw_idx)
            peak_in_raw = bool(shifted_start <= baseline_peak <= shifted_end)
            if not peak_in_raw:
                reason_code = "PEAK_OUTSIDE_WINDOW"
                reason = (
                    f"Frozen peak index {baseline_peak} is outside "
                    f"[{shifted_start},{shifted_end}]."
                )
            else:
                raw_time = np.asarray(arrays["TIME"][raw_idx], dtype=np.float64)
                raw_flux = np.asarray(arrays[flux_col][raw_idx], dtype=np.float64)

                finite_mask = np.isfinite(raw_time) & np.isfinite(raw_flux)
                removed_nonfinite = int(len(raw_idx) - np.count_nonzero(finite_mask))

                if cell["quality_policy"] == "finite_all":
                    mask = finite_mask
                    removed_quality = 0
                elif cell["quality_policy"] == "q0_native":
                    quality = np.asarray(arrays["QUALITY"][raw_idx], dtype=np.int64)
                    quality_mask = quality == 0
                    removed_quality = int(np.count_nonzero(finite_mask & ~quality_mask))
                    mask = finite_mask & quality_mask
                else:
                    raise RuntimeError(
                        f"Unexpected quality policy: {cell['quality_policy']}"
                    )

                retained_idx = canonical_array(raw_idx[mask], "<i8")
                retained_time = canonical_array(raw_time[mask], "<f8")
                retained_flux = canonical_array(raw_flux[mask], "<f8")
                retained_n = len(retained_idx)
                peak_retained = bool(np.any(retained_idx == baseline_peak))

                if retained_n:
                    retained_start = int(retained_idx[0])
                    retained_end = int(retained_idx[-1])
                    retained_idx_sha = canonical_array_hash(retained_idx, "<i8")

                if not peak_retained:
                    reason_code = "PEAK_REMOVED_BY_QUALITY"
                    reason = "Frozen peak cadence is absent after frozen mask."
                elif retained_n < 15:
                    reason_code = "TOO_FEW_CADENCES"
                    reason = f"{retained_n} retained cadences; minimum is 15."
                else:
                    # Exact F2 temporal convention.
                    time_seconds = canonical_array(
                        (retained_time - retained_time[0]) * 86400.0,
                        "<f8",
                    )
                    if (
                        not np.all(np.isfinite(time_seconds))
                        or not np.all(np.isfinite(retained_flux))
                    ):
                        reason_code = "NONFINITE_INPUT"
                        reason = "Non-finite retained time_seconds or flux."
                    else:
                        diffs = np.diff(time_seconds)
                        time_increasing = bool(np.all(diffs > 0.0))
                        time_duplicates = bool(
                            len(np.unique(time_seconds)) != len(time_seconds)
                        )
                        retained_consecutive = bool(
                            np.all(np.diff(retained_idx) == 1)
                        )
                        median_cadence_s = float(np.median(diffs))
                        max_dev_s = float(
                            np.max(np.abs(diffs - median_cadence_s))
                        )
                        irregular = []
                        if not time_increasing:
                            irregular.append("time_not_strictly_increasing")
                        if time_duplicates:
                            irregular.append("duplicate_times")
                        if not retained_consecutive:
                            irregular.append("retained_indices_not_consecutive")
                        if max_dev_s > 0.001:
                            irregular.append("interval_deviation_gt_0.001_s")
                        if irregular:
                            reason_code = "IRREGULAR_SAMPLING"
                            reason = "|".join(irregular)
                        else:
                            if cell["detrending"] == "none":
                                final_flux = canonical_array(retained_flux, "<f8")
                            elif cell["detrending"] == "linear_residual_plus_one":
                                try:
                                    x = time_seconds - np.mean(time_seconds)
                                    X = np.column_stack([np.ones(len(x)), x])
                                    beta = np.linalg.lstsq(
                                        X, retained_flux, rcond=None
                                    )[0]
                                    trend = X @ beta
                                    scale = np.median(retained_flux)
                                    beta0 = float(beta[0])
                                    beta1 = float(beta[1])
                                    scale_out = float(scale)
                                    final_flux = canonical_array(
                                        1.0 + (retained_flux - trend) / scale,
                                        "<f8",
                                    )
                                    detrend_valid = (
                                        math.isfinite(scale_out)
                                        and scale_out != 0.0
                                        and np.all(np.isfinite(beta))
                                        and np.all(np.isfinite(trend))
                                        and np.all(np.isfinite(final_flux))
                                    )
                                    if not detrend_valid:
                                        reason_code = "DETREND_FAILURE"
                                        reason = (
                                            "Frozen linear_residual_plus_one "
                                            "validity requirements failed."
                                        )
                                except Exception as exc:
                                    reason_code = "DETREND_FAILURE"
                                    reason = f"{type(exc).__name__}: {exc}"
                                    final_flux = None
                            else:
                                raise RuntimeError(
                                    f"Unexpected detrending={cell['detrending']}"
                                )

                            if not reason_code:
                                all_finite = bool(
                                    np.all(np.isfinite(time_seconds))
                                    and np.all(np.isfinite(final_flux))
                                )
                                payload = (
                                    canonical_array(time_seconds, "<f8"),
                                    canonical_array(final_flux, "<f8"),
                                    canonical_array(retained_idx, "<i8"),
                                )

    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        raise

    if payload is None:
        if reason_code not in INADMISSIBILITY_CODES:
            raise RuntimeError(
                f"Invalid inadmissibility code {reason_code!r} "
                f"for {event['phase3a_event_id']} {cell['matrix_cell_id']}"
            )
        materialization_status = "INPUT_INADMISSIBLE"
    else:
        materialization_status = "ELIGIBLE_FOR_AFINO"

    row.update({
        "raw_n_samples": raw_n,
        "retained_n_samples": retained_n,
        "removed_nonfinite_count": removed_nonfinite,
        "removed_quality_count": removed_quality,
        "peak_in_raw_window": bool_text(peak_in_raw) if peak_in_raw != "" else "",
        "peak_retained": bool_text(peak_retained) if peak_retained != "" else "",
        "retained_index_start": retained_start,
        "retained_index_end": retained_end,
        "retained_indices_consecutive":
            bool_text(retained_consecutive) if retained_consecutive != "" else "",
        "retained_indices_sha256": retained_idx_sha,
        "time_strictly_increasing":
            bool_text(time_increasing) if time_increasing != "" else "",
        "time_has_duplicates":
            bool_text(time_duplicates) if time_duplicates != "" else "",
        "median_cadence_s": median_cadence_s,
        "max_interval_deviation_s": max_dev_s,
        "detrend_beta0": beta0,
        "detrend_beta1": beta1,
        "detrend_scale": scale_out,
        "materialization_status": materialization_status,
        "inadmissibility_reason_code": reason_code,
        "inadmissibility_reason": reason,
        "diagnostic_flags_json": json.dumps(
            diag, sort_keys=True, separators=(",", ":")
        ),
        "all_finite": bool_text(all_finite) if all_finite != "" else "",
        "error": error,
    })
    return row, payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()

    if np.__version__ != EXPECTED_NUMPY:
        raise RuntimeError(
            f"Frozen F2-compatible materialization requires numpy=={EXPECTED_NUMPY}; "
            f"found {np.__version__}. Install with: "
            f"python -m pip install --upgrade \"numpy=={EXPECTED_NUMPY}\""
        )

    verify_frozen_inputs(repo)
    matrix = load_and_validate_matrix(repo)

    cohort = read_csv(repo / COHORT_REL)
    product_rows = read_csv(repo / PRODUCT_REL)
    time_rows = read_csv(repo / TIME_REL)

    if len(cohort) != 122:
        raise RuntimeError(f"Expected 122 frozen cohort events, got {len(cohort)}")
    if len(product_rows) != 122 or len(time_rows) != 122:
        raise RuntimeError("TESS event-product/time manifests must each contain 122 rows.")

    cohort = sorted(cohort, key=lambda r: r["phase3a_event_id"])
    matrix = sorted(matrix, key=lambda r: r["matrix_cell_id"])

    product_by_event = {r["phase3a_event_id"]: r for r in product_rows}
    time_by_event = {r["phase3a_event_id"]: r for r in time_rows}
    if len(product_by_event) != 122 or len(time_by_event) != 122:
        raise RuntimeError("Duplicate event IDs in TESS manifests.")

    for event in cohort:
        eid = event["phase3a_event_id"]
        if eid not in product_by_event or eid not in time_by_event:
            raise RuntimeError(f"Missing TESS binding for {eid}")
        if product_by_event[eid]["time_mapping_status"] != time_by_event[eid]["time_mapping_status"]:
            raise RuntimeError(f"Product/time mapping status disagreement for {eid}")

    fits_cache: dict[str, tuple[dict[str, np.ndarray], int]] = {}
    fitspath_by_name: dict[str, Path] = {}

    raw_dir = repo / RAW_FITS_REL
    for product in product_rows:
        if product["product_status"] != "BOUND_DOWNLOADED":
            continue
        name = product["physical_filename"]
        if name in fitspath_by_name:
            continue
        p = raw_dir / name
        if not p.is_file():
            raise RuntimeError(f"Frozen FITS missing: {p}")
        actual = sha256_file(p)
        if actual != product["physical_sha256"]:
            raise RuntimeError(
                f"Frozen FITS hash mismatch for {name}: "
                f"{actual} != {product['physical_sha256']}"
            )
        fitspath_by_name[name] = p

    if len(fitspath_by_name) != 87:
        raise RuntimeError(
            f"Expected 87 unique frozen physical FITS, got {len(fitspath_by_name)}"
        )

    payload_dir = repo / PAYLOAD_DIR_REL
    payload_dir.mkdir(parents=True, exist_ok=True)

    # Refuse silent overwrite of the frozen payload files.
    payload_paths = {
        "time": payload_dir / "time_seconds.npy",
        "flux": payload_dir / "flux.npy",
        "index": payload_dir / "native_index.npy",
        "offsets": payload_dir / "offsets.npy",
    }
    if any(p.exists() for p in payload_paths.values()):
        raise RuntimeError(
            "One or more F3A.2 payload arrays already exist. "
            "Refusing overwrite; preserve them or remove intentionally after audit."
        )

    variant_rows: list[dict[str, Any]] = []
    eligible_times: list[np.ndarray] = []
    eligible_flux: list[np.ndarray] = []
    eligible_indices: list[np.ndarray] = []
    offsets = [0]
    payload_rows: list[dict[str, Any]] = []
    variant_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    event_by_id = {e["phase3a_event_id"]: e for e in cohort}

    current_fits_name = None
    current_arrays = None
    current_nrows = None

    for event in cohort:
        eid = event["phase3a_event_id"]
        product = product_by_event[eid]
        fits_name = product.get("physical_filename", "")

        if product.get("product_status") == "BOUND_DOWNLOADED":
            if fits_name != current_fits_name:
                # Load exact physical FITS once for consecutive event usage.
                current_arrays, current_nrows = fits_arrays(fitspath_by_name[fits_name])
                current_fits_name = fits_name
        else:
            current_arrays, current_nrows, current_fits_name = None, None, None

        for cell in matrix:
            variant_order = len(variant_rows) + 1
            variant_id = f"F3AV{variant_order:06d}"
            primary_decision_id = f"F3ADP{variant_order:06d}"

            row, payload = materialize_variant(
                event, product, cell, current_arrays, current_nrows
            )
            row["variant_id"] = variant_id
            row["variant_order"] = variant_order
            row["primary_planned_decision_id"] = primary_decision_id

            if payload is not None:
                time_s, flux, native_idx = payload
                offset = offsets[-1]
                length = len(time_s)
                offsets.append(offset + length)

                time_sha = canonical_array_hash(time_s, "<f8")
                flux_sha = canonical_array_hash(flux, "<f8")
                idx_sha = canonical_array_hash(native_idx, "<i8")
                logical_sha = logical_payload_hash(time_s, flux, native_idx)
                payload_order = len(payload_rows) + 1
                payload_id = f"F3APAY{payload_order:06d}"

                row.update({
                    "eligible_payload_order": payload_order,
                    "payload_offset": offset,
                    "payload_length": length,
                    "time_sha256": time_sha,
                    "flux_sha256": flux_sha,
                    "native_index_sha256": idx_sha,
                    "logical_payload_sha256": logical_sha,
                })

                payload_rows.append({
                    "payload_id": payload_id,
                    "variant_id": variant_id,
                    "offset": offset,
                    "length": length,
                    "time_sha256": time_sha,
                    "flux_sha256": flux_sha,
                    "native_index_sha256": idx_sha,
                    "logical_payload_sha256": logical_sha,
                    "n_samples": length,
                    "first_time_s": float(time_s[0]),
                    "last_time_s": float(time_s[-1]),
                    "time_dtype": "<f8",
                    "flux_dtype": "<f8",
                    "native_index_dtype": "<i8",
                })

                eligible_times.append(time_s)
                eligible_flux.append(flux)
                eligible_indices.append(native_idx)

            variant_rows.append(row)
            variant_by_key[
                (eid, cell["window_variant_id"], cell["processing_profile_id"])
            ] = row

    expected_variants = 122 * 78
    if len(variant_rows) != expected_variants:
        raise RuntimeError(
            f"Expected {expected_variants} primary variant rows, got {len(variant_rows)}"
        )

    if any(
        sum(
            1
            for row in variant_rows
            if row["phase3a_event_id"] == event["phase3a_event_id"]
        ) != 78
        for event in cohort
    ):
        raise RuntimeError("At least one event does not have exactly 78 primary rows.")

    write_csv(repo / VARIANT_REL, variant_rows, VARIANT_FIELDS)
    write_csv(repo / PAYLOAD_MANIFEST_REL, payload_rows, PAYLOAD_FIELDS)

    eligible_count = len(payload_rows)
    inadmissible_count = len(variant_rows) - eligible_count
    if eligible_count == 0:
        raise RuntimeError("No eligible F3A primary variants.")

    time_values = canonical_array(np.concatenate(eligible_times), "<f8")
    flux_values = canonical_array(np.concatenate(eligible_flux), "<f8")
    index_values = canonical_array(np.concatenate(eligible_indices), "<i8")
    offset_values = canonical_array(offsets, "<i8")

    if not (
        len(time_values) == len(flux_values) == len(index_values)
        == int(offset_values[-1])
    ):
        raise RuntimeError("Concatenated payload lengths disagree.")
    if len(offset_values) != eligible_count + 1 or int(offset_values[0]) != 0:
        raise RuntimeError("Offsets payload structure invalid.")

    np.save(payload_paths["time"], time_values, allow_pickle=False)
    np.save(payload_paths["flux"], flux_values, allow_pickle=False)
    np.save(payload_paths["index"], index_values, allow_pickle=False)
    np.save(payload_paths["offsets"], offset_values, allow_pickle=False)

    # Mandatory round-trip exactness from physical frozen NPY arrays.
    rt_time = np.load(payload_paths["time"], mmap_mode="r", allow_pickle=False)
    rt_flux = np.load(payload_paths["flux"], mmap_mode="r", allow_pickle=False)
    rt_index = np.load(payload_paths["index"], mmap_mode="r", allow_pickle=False)
    rt_offsets = np.load(payload_paths["offsets"], mmap_mode="r", allow_pickle=False)

    roundtrip_mismatches = 0
    for p in payload_rows:
        start = int(p["offset"])
        end = start + int(p["length"])
        if canonical_array_hash(rt_time[start:end], "<f8") != p["time_sha256"]:
            roundtrip_mismatches += 1
        if canonical_array_hash(rt_flux[start:end], "<f8") != p["flux_sha256"]:
            roundtrip_mismatches += 1
        if canonical_array_hash(rt_index[start:end], "<i8") != p["native_index_sha256"]:
            roundtrip_mismatches += 1
        if logical_payload_hash(
            rt_time[start:end], rt_flux[start:end], rt_index[start:end]
        ) != p["logical_payload_sha256"]:
            roundtrip_mismatches += 1

    if roundtrip_mismatches != 0:
        raise RuntimeError(
            f"Payload roundtrip mismatches: {roundtrip_mismatches}"
        )
    if not np.array_equal(rt_offsets, offset_values):
        raise RuntimeError("Offset NPY roundtrip mismatch.")

    payload_by_variant = {p["variant_id"]: p for p in payload_rows}

    # Resolve executable decisions. Primary: seed 0 for every eligible variant.
    decisions: list[dict[str, Any]] = []
    for row in variant_rows:
        if row["materialization_status"] != "ELIGIBLE_FOR_AFINO":
            continue
        p = payload_by_variant[row["variant_id"]]
        decisions.append({
            "planned_decision_id": row["primary_planned_decision_id"],
            "decision_order": len(decisions) + 1,
            "decision_class": "PRIMARY",
            "phase3a_event_id": row["phase3a_event_id"],
            "pair_id": row["pair_id"],
            "observational_reference_role": row["observational_reference_role"],
            "variant_id": row["variant_id"],
            "matrix_cell_id": row["matrix_cell_id"],
            "window_variant_id": row["window_variant_id"],
            "processing_profile_id": row["processing_profile_id"],
            "external_optimizer_seed": 0,
            "payload_id": p["payload_id"],
            "payload_logical_sha256": p["logical_payload_sha256"],
            "input_n_samples": p["n_samples"],
            "resolved_decision_status": "READY_FOR_AFINO",
        })

    primary_decisions = len(decisions)

    # Stability: only W00/P00, seeds 1..9. Seed 0 already exists as primary.
    w00p00_eligible_events = []
    for event in cohort:
        row = variant_by_key[(event["phase3a_event_id"], "W00", "P00")]
        if row["materialization_status"] == "ELIGIBLE_FOR_AFINO":
            w00p00_eligible_events.append(event["phase3a_event_id"])

    stability_extra = 0
    for eid in w00p00_eligible_events:
        row = variant_by_key[(eid, "W00", "P00")]
        p = payload_by_variant[row["variant_id"]]
        event = event_by_id[eid]
        for seed in range(1, 10):
            stability_extra += 1
            decisions.append({
                "planned_decision_id": f"F3ADS{stability_extra:06d}",
                "decision_order": len(decisions) + 1,
                "decision_class": "STABILITY",
                "phase3a_event_id": eid,
                "pair_id": event["pair_id"],
                "observational_reference_role":
                    event["observational_reference_role"],
                "variant_id": row["variant_id"],
                "matrix_cell_id": row["matrix_cell_id"],
                "window_variant_id": "W00",
                "processing_profile_id": "P00",
                "external_optimizer_seed": seed,
                "payload_id": p["payload_id"],
                "payload_logical_sha256": p["logical_payload_sha256"],
                "input_n_samples": p["n_samples"],
                "resolved_decision_status": "READY_FOR_AFINO",
            })

    if stability_extra != 9 * len(w00p00_eligible_events):
        raise RuntimeError("Stability decision identity failed.")

    if len({
        (d["variant_id"], int(d["external_optimizer_seed"]))
        for d in decisions
    }) != len(decisions):
        raise RuntimeError("Duplicate executable decision scientific keys.")

    write_csv(repo / DECISION_REL, decisions, DECISION_FIELDS)

    # Exact model-call plan.
    jobs: list[dict[str, Any]] = []
    for d in decisions:
        for model_id, model_name in MODEL_ROWS:
            order = len(jobs) + 1
            jobs.append({
                "job_id": f"F3AJ{order:07d}",
                "job_order": order,
                "planned_decision_id": d["planned_decision_id"],
                "decision_class": d["decision_class"],
                "phase3a_event_id": d["phase3a_event_id"],
                "variant_id": d["variant_id"],
                "matrix_cell_id": d["matrix_cell_id"],
                "window_variant_id": d["window_variant_id"],
                "processing_profile_id": d["processing_profile_id"],
                "external_optimizer_seed": d["external_optimizer_seed"],
                "model_id": model_id,
                "model_name": model_name,
                "payload_id": d["payload_id"],
                "payload_logical_sha256": d["payload_logical_sha256"],
                "afino_version": AFINO_VERSION,
                "afino_commit": AFINO_COMMIT,
                "low_frequency_cutoff_hz": LOW_FREQUENCY_CUTOFF_HZ,
                "seed_application_contract":
                    "np.random.seed(external_optimizer_seed) immediately before each model",
                "selection_rule":
                    "BIC_M0-BIC_M1>10 AND BIC_M2-BIC_M1>10",
                "execution_status": "NOT_EXECUTED",
            })

    if len(jobs) != 3 * len(decisions):
        raise RuntimeError("Exact model calls are not 3 × executable decisions.")
    model_counts = Counter(j["model_id"] for j in jobs)
    if model_counts != {
        "M0": len(decisions),
        "M1": len(decisions),
        "M2": len(decisions),
    }:
        raise RuntimeError(f"Unequal model-call counts: {model_counts}")
    if len({j["job_id"] for j in jobs}) != len(jobs):
        raise RuntimeError("Duplicate job_id")
    if len({
        (
            j["variant_id"],
            int(j["external_optimizer_seed"]),
            j["model_id"],
        )
        for j in jobs
    }) != len(jobs):
        raise RuntimeError("Duplicate exact-plan scientific keys.")
    if any(j["execution_status"] != "NOT_EXECUTED" for j in jobs):
        raise RuntimeError("Unexpected executed job in F3A.2.")

    write_csv(repo / PLAN_REL, jobs, PLAN_FIELDS)

    reason_counts = Counter(
        r["inadmissibility_reason_code"]
        for r in variant_rows
        if r["materialization_status"] == "INPUT_INADMISSIBLE"
    )

    print("PHASE3A_PRIMARY_VARIANTS_PAYLOADS_AND_PLAN_MATERIALIZATION_PASS")
    print(f"numpy_version={np.__version__}")
    print(f"frozen_cohort_events={len(cohort)}")
    print(f"primary_planned_variants={len(variant_rows)}")
    print(f"primary_eligible_variants={eligible_count}")
    print(f"primary_inadmissible_variants={inadmissible_count}")
    print("inadmissibility_counts=" + json.dumps(
        dict(sorted(reason_counts.items())), sort_keys=True
    ))
    print(f"w00_p00_eligible_events={len(w00p00_eligible_events)}")
    print(f"primary_executable_decisions={primary_decisions}")
    print(f"stability_extra_decisions={stability_extra}")
    print(f"total_executable_decisions={len(decisions)}")
    print(f"exact_model_calls={len(jobs)}")
    print(f"m0_calls={model_counts['M0']}")
    print(f"m1_calls={model_counts['M1']}")
    print(f"m2_calls={model_counts['M2']}")
    print(f"payload_roundtrip_mismatches={roundtrip_mismatches}")
    print(f"payload_time_npy_sha256={sha256_file(payload_paths['time'])}")
    print(f"payload_flux_npy_sha256={sha256_file(payload_paths['flux'])}")
    print(f"payload_native_index_npy_sha256={sha256_file(payload_paths['index'])}")
    print(f"payload_offsets_npy_sha256={sha256_file(payload_paths['offsets'])}")
    print("afino_imported=false")
    print("afino_executed=false")
    print("scientific_results_computed=false")
    print("baseline_classifications_observed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
