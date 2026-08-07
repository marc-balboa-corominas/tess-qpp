from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import argparse
import csv
import hashlib
import io
import json
import math
import os
import platform
import re
import shutil
import sys
import warnings

import numpy as np
from astropy.io import fits
import astropy


PROJECT_ROOT = Path(__file__).resolve().parent

F21_HASHES = {
    "fase2_tarea01_build_observational_preregistration.py":
        "3c8e1c0e254c0a7d721c6dbe3678ea748accf3c5b928d7963f63b67ca2ba66e5",
    "fase2_tarea01_observational_robustness_preregistration.json":
        "ed37166ad6917b54711c3ce7ac9f3aeffdaaba9477672a9b1e5d506c07f427d7",
    "fase2_tarea01_frozen_observational_cohort.csv":
        "34f4a5ce53e7fb16ee16c976d5b06af524d6cacda4a4bc303a5d580193745cc1",
    "fase2_tarea01_window_perturbations.csv":
        "4e0a602e89f17594afe4624ae0d48781cfde7c17a17a1cc129002aeb0c45f130",
    "fase2_tarea01_processing_profiles.csv":
        "232af6bdc6fa09851cd1039c5b159849f2f675803ea6ff1f53f51e7a4a7629e0",
    "fase2_tarea01_planned_decision_grid.csv":
        "c177c10604a5f79aae1e3e154b450da1084ba96fb351298354654c0cbb6f61a0",
    "fase2_tarea01_preregistration_audit.json":
        "1111b5e060abc4f619f6c7ac01306d423bbc73ae520d8c15e7c31317afdfcf55",
}

OUTPUT_NAMES = [
    "fase2_tarea02_fits_source_audit.csv",
    "fase2_tarea02_observational_variant_manifest.csv",
    "fase2_tarea02_eligible_time_values.npy",
    "fase2_tarea02_eligible_flux_values.npy",
    "fase2_tarea02_eligible_fits_index_values.npy",
    "fase2_tarea02_eligible_variant_offsets.npy",
    "fase2_tarea02_resolved_decision_grid.csv",
    "fase2_tarea02_exact_afino_execution_plan.csv",
    "fase2_tarea02_variant_materialization_audit.json",
    "fase2_tarea02_variant_materialization_report.md",
    "fase2_tarea02_environment.txt",
]

FINAL_STATUS = "OBSERVATIONAL_VARIANTS_AND_EXACT_PLAN_FROZEN_BEFORE_AFINO"

ADMISSIBILITY_PRECEDENCE = [
    "MISSING_PRODUCT",
    "WINDOW_OUT_OF_RANGE",
    "PEAK_OUTSIDE_WINDOW",
    "PEAK_REMOVED_BY_QUALITY",
    "TOO_FEW_CADENCES",
    "NONFINITE_INPUT",
    "IRREGULAR_SAMPLING",
    "DETREND_FAILURE",
    "ELIGIBLE_FOR_AFINO",
]

MODEL_ROWS = [
    ("M0", "pow_const"),
    ("M1", "pow_const_gauss"),
    ("M2", "bpow_const"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize the frozen F2.1 observational variants, resolve "
            "technical admissibility and freeze the exact pre-AFINO plan."
        )
    )
    parser.add_argument(
        "--fits-root",
        required=True,
        type=Path,
        help="Local directory containing the frozen FITS products.",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_array(
    values: Any,
    dtype: str,
) -> np.ndarray:
    return np.ascontiguousarray(values, dtype=np.dtype(dtype))


def canonical_array_hash(
    values: Any,
    dtype: str,
) -> str:
    array = canonical_array(values, dtype)
    return sha256_bytes(array.tobytes(order="C"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fields: list[str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({
                field: row.get(field, "")
                for field in fields
            })


def parse_bool(value: str) -> bool:
    if value == "True":
        return True
    if value == "False":
        return False
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"Unexpected Boolean value: {value!r}")


def parse_optional_float(value: str) -> float | None:
    return None if value == "" else float(value)


def clean_number(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(float(value)):
            return ""
        return float(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    return value


def redact_path(path: Path) -> str:
    resolved = path.resolve()
    home = Path.home().resolve()
    try:
        relative = resolved.relative_to(home)
    except ValueError:
        return str(resolved)
    return str(Path("$HOME") / relative)


def locate_exactly_one(
    search_root: Path,
    filename: str,
) -> Path:
    matches = sorted(
        path for path in search_root.rglob(filename)
        if path.is_file()
    )
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one {filename!r} below "
            f"{redact_path(search_root)}; found {len(matches)}."
        )
    return matches[0]


def locate_project_artifact(filename: str) -> Path:
    direct = PROJECT_ROOT / filename
    if direct.is_file():
        return direct
    matches = sorted(
        path for path in PROJECT_ROOT.rglob(filename)
        if path.is_file()
        and ".fase2_tarea02_staging_" not in str(path)
    )
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one frozen project artifact {filename!r}; "
            f"found {len(matches)}."
        )
    return matches[0]


def masked_float64(column: Any) -> np.ndarray:
    array = np.ma.asarray(column, dtype=np.float64)
    return np.asarray(np.ma.filled(array, np.nan), dtype=np.float64)


def masked_int64(column: Any) -> np.ndarray:
    array = np.ma.asarray(column)
    filled = np.ma.filled(array, np.iinfo(np.int64).min)
    return np.asarray(filled, dtype=np.int64)


def inspect_fits(
    path: Path,
) -> dict[str, Any]:
    captured_warnings: list[str] = []
    stderr_buffer = io.StringIO()
    try:
        with warnings.catch_warnings(record=True) as records:
            warnings.simplefilter("always")
            with redirect_stderr(stderr_buffer):
                with fits.open(
                    path,
                    mode="readonly",
                    memmap=False,
                    checksum=True,
                    do_not_scale_image_data=False,
                ) as hdul:
                    lightcurve_hdu = None
                    for hdu in hdul:
                        if (
                            getattr(hdu, "name", "").upper() == "LIGHTCURVE"
                            and getattr(hdu, "data", None) is not None
                        ):
                            lightcurve_hdu = hdu
                            break
                    if lightcurve_hdu is None:
                        for hdu in hdul:
                            if (
                                isinstance(hdu, fits.BinTableHDU)
                                and getattr(hdu, "data", None) is not None
                            ):
                                lightcurve_hdu = hdu
                                break
                    if lightcurve_hdu is None:
                        raise RuntimeError("No readable binary table HDU found.")

                    columns = {
                        name.upper()
                        for name in lightcurve_hdu.columns.names
                    }
                    data = lightcurve_hdu.data
                    table_row_count = len(data)

                    arrays: dict[str, np.ndarray | None] = {
                        "TIME": (
                            masked_float64(data["TIME"])
                            if "TIME" in columns else None
                        ),
                        "QUALITY": (
                            masked_int64(data["QUALITY"])
                            if "QUALITY" in columns else None
                        ),
                        "SAP_FLUX": (
                            masked_float64(data["SAP_FLUX"])
                            if "SAP_FLUX" in columns else None
                        ),
                        "PDCSAP_FLUX": (
                            masked_float64(data["PDCSAP_FLUX"])
                            if "PDCSAP_FLUX" in columns else None
                        ),
                    }

                    checksum_values: list[int] = []
                    datasum_values: list[int] = []
                    checksum_keywords = 0
                    datasum_keywords = 0
                    for hdu in hdul:
                        if "CHECKSUM" in hdu.header:
                            checksum_keywords += 1
                            checksum_values.append(int(hdu.verify_checksum()))
                        if "DATASUM" in hdu.header:
                            datasum_keywords += 1
                            datasum_values.append(int(hdu.verify_datasum()))

            captured_warnings.extend(str(record.message) for record in records)

        stderr_text = stderr_buffer.getvalue().strip()
        if stderr_text:
            captured_warnings.append(stderr_text)

        failed_text = any(
            "checksum verification failed" in value.lower()
            or "datasum verification failed" in value.lower()
            for value in captured_warnings
        )
        failed_numeric = any(value == 0 for value in checksum_values + datasum_values)
        if failed_text or failed_numeric:
            checksum_status = "FAIL"
        elif checksum_keywords == 0 and datasum_keywords == 0:
            checksum_status = "NO_CHECKSUM_KEYWORDS"
        elif all(value == 1 for value in checksum_values + datasum_values):
            checksum_status = "PASS"
        else:
            checksum_status = "PARTIAL_OR_NOT_VERIFIED"

        return {
            "table_row_count": table_row_count,
            "columns": columns,
            "arrays": arrays,
            "fits_checksum_status": checksum_status,
            "warnings": captured_warnings,
            "read_status": "READABLE",
            "error": "",
        }
    except Exception as exc:
        return {
            "table_row_count": "",
            "columns": set(),
            "arrays": {},
            "fits_checksum_status": "NOT_EVALUATED",
            "warnings": captured_warnings,
            "read_status": "ERROR",
            "error": f"{type(exc).__name__}: {exc}",
        }


def raw_bytes_hash_from_csv_column(
    rows: list[dict[str, str]],
    column: str,
    dtype: str,
) -> str:
    values = [row[column] for row in rows]
    return canonical_array_hash(values, dtype)


def baseline_reference_for_event(
    event: dict[str, str],
    f09_manifest: list[dict[str, str]],
    f013_manifest: list[dict[str, str]],
) -> dict[str, Any]:
    event_id = event["event_id"]
    if event["pair_id"] == "calibration_pair":
        event_role = (
            "published_qpp"
            if event["observational_role"] == "PUBLISHED_QPP_REPRODUCED"
            else "not_selected_qpp"
        )
        matches = [
            row for row in f09_manifest
            if row["event_role"] == event_role
            and row["flux_type"] == "PDCSAP_FLUX"
            and row["quality_policy"] == "finite_all"
        ]
        index_start_field = "start_fits_row_index"
        index_end_field = "end_fits_row_index"
        n_field = "n_rows_used"
    else:
        matches = [
            row for row in f013_manifest
            if row["variant_id"] == event_id
        ]
        index_start_field = "start_fits_index"
        index_end_field = "end_fits_index"
        n_field = "n_rows_used"

    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one frozen baseline input manifest row for "
            f"{event_id}; found {len(matches)}."
        )
    source = matches[0]
    output_filename = source["output_filename"]
    output_path = locate_project_artifact(output_filename)
    observed_output_sha = sha256_file(output_path)
    if observed_output_sha != source["output_sha256"]:
        raise RuntimeError(
            f"Frozen baseline CSV hash mismatch for {output_filename}."
        )
    rows = read_csv(output_path)
    if len(rows) != int(source[n_field]):
        raise RuntimeError(
            f"Frozen baseline CSV row count mismatch for {event_id}."
        )
    required_columns = {"time_tbjd", "flux"}
    if not required_columns.issubset(rows[0]):
        raise RuntimeError(
            f"Frozen baseline CSV {output_filename} lacks time/flux."
        )

    time_tbjd = canonical_array(
        [float(row["time_tbjd"]) for row in rows],
        "<f8",
    )
    time_seconds = canonical_array(
        (time_tbjd - time_tbjd[0]) * 86400.0,
        "<f8",
    )
    flux = canonical_array(
        [float(row["flux"]) for row in rows],
        "<f8",
    )

    if "fits_row_index" in rows[0]:
        fits_indices = canonical_array(
            [int(row["fits_row_index"]) for row in rows],
            "<i8",
        )
    else:
        fits_indices = np.arange(
            int(source[index_start_field]),
            int(source[index_end_field]) + 1,
            dtype="<i8",
        )
    if len(fits_indices) != len(rows):
        raise RuntimeError(
            f"Frozen baseline index count mismatch for {event_id}."
        )

    return {
        "source_manifest_row": source,
        "source_csv_filename": output_filename,
        "source_csv_sha256": observed_output_sha,
        "n_samples": len(rows),
        "first_fits_index": int(fits_indices[0]),
        "last_fits_index": int(fits_indices[-1]),
        "time_sha256": canonical_array_hash(time_seconds, "<f8"),
        "flux_sha256": canonical_array_hash(flux, "<f8"),
        "fits_index_sha256": canonical_array_hash(fits_indices, "<i8"),
    }


def main() -> None:
    args = parse_args()
    fits_root = args.fits_root.expanduser().resolve()
    if not fits_root.is_dir():
        raise NotADirectoryError(
            f"FITS root is not a directory: {redact_path(fits_root)}"
        )

    for output_name in OUTPUT_NAMES:
        if (PROJECT_ROOT / output_name).exists():
            raise FileExistsError(
                f"Refusing to overwrite existing artifact: {output_name}"
            )

    staging = PROJECT_ROOT / (
        ".fase2_tarea02_staging_"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    )
    staging.mkdir(parents=False, exist_ok=False)

    print("F2.2 OBSERVATIONAL VARIANT MATERIALIZATION")
    print(f"fits_root: {redact_path(fits_root)}")
    print(f"staging_directory: {staging.name}")
    print("afino_executed: false")
    print("fits_downloaded: false")
    print("candidate_discovery_authorized: false")
    print()

    try:
        print("===== F2.2 PREFLIGHT =====")
        f21_hashes_before: dict[str, str] = {}
        for filename, expected in F21_HASHES.items():
            path = PROJECT_ROOT / filename
            if not path.is_file():
                raise FileNotFoundError(path)
            observed = sha256_file(path)
            print(f"{filename}: {observed}")
            if observed != expected:
                raise RuntimeError(
                    f"F2.1 hash mismatch for {filename}: "
                    f"{observed} != {expected}"
                )
            f21_hashes_before[filename] = observed

        prereg = json.loads(
            (
                PROJECT_ROOT
                / "fase2_tarea01_observational_robustness_preregistration.json"
            ).read_text(encoding="utf-8")
        )
        if prereg["study_id"] != "afino_tess_frozen_cohort_robustness_v1":
            raise RuntimeError("Unexpected F2.1 study_id.")
        if prereg["study_version"] != "1.0.0":
            raise RuntimeError("Unexpected F2.1 study_version.")
        if prereg["preregistration_status"] != (
            "FROZEN_BEFORE_VARIANT_MATERIALIZATION"
        ):
            raise RuntimeError("F2.1 is not frozen before materialization.")
        if prereg["candidate_discovery_allowed"] is not False:
            raise RuntimeError("Candidate discovery is not blocked.")

        cohort = read_csv(
            PROJECT_ROOT / "fase2_tarea01_frozen_observational_cohort.csv"
        )
        windows = read_csv(
            PROJECT_ROOT / "fase2_tarea01_window_perturbations.csv"
        )
        profiles = read_csv(
            PROJECT_ROOT / "fase2_tarea01_processing_profiles.csv"
        )
        planned_grid = read_csv(
            PROJECT_ROOT / "fase2_tarea01_planned_decision_grid.csv"
        )
        primary_plan = [
            row for row in planned_grid
            if row["decision_class"] == "primary"
        ]
        if len(cohort) != 10 or len(windows) != 13 or len(profiles) != 6:
            raise RuntimeError("F2.1 design counts changed.")
        if len(primary_plan) != 780 or len(planned_grid) != 1320:
            raise RuntimeError("F2.1 decision-grid counts changed.")

        cohort_by_event = {row["event_id"]: row for row in cohort}
        window_by_id = {
            row["window_variant_id"]: row for row in windows
        }
        profile_by_id = {
            row["processing_profile_id"]: row for row in profiles
        }

        # The hashes of the baseline input manifests were frozen by F2.1.
        f21_audit = json.loads(
            (
                PROJECT_ROOT
                / "fase2_tarea01_preregistration_audit.json"
            ).read_text(encoding="utf-8")
        )
        frozen_source_hashes = f21_audit[
            "source_hashes_verified"
        ]["before"]

        f09_manifest_path = locate_project_artifact(
            "fase0_tarea09_index_window_manifest.csv"
        )
        f013_manifest_path = locate_project_artifact(
            "fase0_tarea13_validation_input_manifest.csv"
        )
        for path in (f09_manifest_path, f013_manifest_path):
            expected = frozen_source_hashes.get(path.name)
            if expected is None:
                raise RuntimeError(
                    f"F2.1 audit lacks the frozen hash for {path.name}."
                )
            observed = sha256_file(path)
            if observed != expected:
                raise RuntimeError(
                    f"Frozen baseline manifest changed: {path.name}."
                )
        f09_manifest = read_csv(f09_manifest_path)
        f013_manifest = read_csv(f013_manifest_path)

        print()
        print("===== FITS SOURCE VERIFICATION =====")
        fits_cache: dict[str, dict[str, Any]] = {}
        fits_audit_rows: list[dict[str, Any]] = []
        fits_physical_hashes_before: dict[str, str] = {}

        for event in cohort:
            filename = event["source_fits_filename"]
            expected_sha = event["source_fits_sha256"]
            fits_path = locate_exactly_one(fits_root, filename)
            observed_sha = sha256_file(fits_path)
            if observed_sha != expected_sha:
                raise RuntimeError(
                    f"FITS SHA-256 mismatch for {filename}: "
                    f"{observed_sha} != {expected_sha}"
                )
            fits_physical_hashes_before[filename] = observed_sha

            if filename not in fits_cache:
                inspected = inspect_fits(fits_path)
                if inspected["read_status"] != "READABLE":
                    raise RuntimeError(
                        f"FITS unreadable for {filename}: "
                        f"{inspected['error']}"
                    )
                inspected["path"] = fits_path
                fits_cache[filename] = inspected
            inspected = fits_cache[filename]
            columns = inspected["columns"]

            fits_audit_rows.append({
                "event_id": event["event_id"],
                "source_fits_filename": filename,
                "expected_sha256": expected_sha,
                "observed_sha256": observed_sha,
                "file_size_bytes": fits_path.stat().st_size,
                "table_row_count": inspected["table_row_count"],
                "time_column_present": "TIME" in columns,
                "quality_column_present": "QUALITY" in columns,
                "sap_column_present": "SAP_FLUX" in columns,
                "pdcsap_column_present": "PDCSAP_FLUX" in columns,
                "fits_checksum_status":
                    inspected["fits_checksum_status"],
                "read_status": inspected["read_status"],
                "error": inspected["error"],
            })
            print(
                f"{event['event_id']}: {filename} "
                f"SHA OK, rows={inspected['table_row_count']}, "
                f"checksum={inspected['fits_checksum_status']}"
            )

        fits_audit_fields = [
            "event_id",
            "source_fits_filename",
            "expected_sha256",
            "observed_sha256",
            "file_size_bytes",
            "table_row_count",
            "time_column_present",
            "quality_column_present",
            "sap_column_present",
            "pdcsap_column_present",
            "fits_checksum_status",
            "read_status",
            "error",
        ]
        write_csv(
            staging / "fase2_tarea02_fits_source_audit.csv",
            fits_audit_rows,
            fits_audit_fields,
        )

        print()
        print("===== VARIANT MATERIALIZATION =====")
        variant_rows: list[dict[str, Any]] = []
        eligible_times: list[np.ndarray] = []
        eligible_fluxes: list[np.ndarray] = []
        eligible_indices: list[np.ndarray] = []
        offsets = [0]
        primary_variant_by_key: dict[
            tuple[str, str, str], dict[str, Any]
        ] = {}

        for variant_order, planned in enumerate(primary_plan, start=1):
            variant_id = f"F2V{variant_order:06d}"
            event = cohort_by_event[planned["event_id"]]
            window = window_by_id[planned["window_variant_id"]]
            profile = profile_by_id[planned["processing_profile_id"]]
            inspected = fits_cache[event["source_fits_filename"]]
            arrays = inspected["arrays"]
            columns = inspected["columns"]
            table_row_count = int(inspected["table_row_count"])

            baseline_start = int(event["baseline_start_index"])
            baseline_peak = int(event["baseline_peak_index"])
            baseline_end = int(event["baseline_end_index"])
            shifted_start = (
                baseline_start + int(window["delta_start_cadences"])
            )
            shifted_end = (
                baseline_end + int(window["delta_end_cadences"])
            )

            raw_indices: np.ndarray | None = None
            retained_indices: np.ndarray | None = None
            retained_time_tbjd: np.ndarray | None = None
            retained_flux: np.ndarray | None = None
            time_seconds: np.ndarray | None = None
            final_flux: np.ndarray | None = None

            raw_n_samples: int | str = ""
            retained_n_samples: int | str = ""
            removed_nonfinite_count: int | str = ""
            removed_quality_count: int | str = ""
            peak_in_raw_window: bool | str = ""
            peak_retained: bool | str = ""
            retained_index_start: int | str = ""
            retained_index_end: int | str = ""
            retained_indices_consecutive: bool | str = ""
            retained_indices_sha256 = ""
            time_strictly_increasing: bool | str = ""
            time_has_duplicates: bool | str = ""
            median_cadence_s: float | str = ""
            max_interval_deviation_s: float | str = ""
            detrend_beta0: float | str = ""
            detrend_beta1: float | str = ""
            detrend_scale: float | str = ""
            all_finite: bool | str = ""
            diagnostic_flags: dict[str, Any] = {
                "fits_checksum_status":
                    inspected["fits_checksum_status"],
                "fits_open_warnings": inspected["warnings"],
                "missing_columns": [],
                "precedence": ADMISSIBILITY_PRECEDENCE,
            }

            required_flux_column = (
                "PDCSAP_FLUX"
                if profile["flux_product"] == "PDCSAP"
                else "SAP_FLUX"
            )
            missing_columns = []
            if "TIME" not in columns:
                missing_columns.append("TIME")
            if required_flux_column not in columns:
                missing_columns.append(required_flux_column)
            if (
                profile["quality_policy"] == "q0_native"
                and "QUALITY" not in columns
            ):
                missing_columns.append("QUALITY")
            diagnostic_flags["missing_columns"] = missing_columns

            status = ""
            reason = ""
            error = ""

            try:
                if missing_columns:
                    status = "MISSING_PRODUCT"
                    reason = (
                        "Required FITS column(s) absent: "
                        + "|".join(missing_columns)
                    )
                elif (
                    shifted_start < 0
                    or shifted_end >= table_row_count
                    or shifted_start > shifted_end
                ):
                    status = "WINDOW_OUT_OF_RANGE"
                    reason = (
                        f"Shifted inclusive window [{shifted_start},"
                        f"{shifted_end}] outside [0,{table_row_count - 1}] "
                        "or start>end."
                    )
                else:
                    raw_indices = np.arange(
                        shifted_start,
                        shifted_end + 1,
                        dtype=np.int64,
                    )
                    raw_n_samples = len(raw_indices)
                    peak_in_raw_window = bool(
                        shifted_start <= baseline_peak <= shifted_end
                    )
                    if not peak_in_raw_window:
                        status = "PEAK_OUTSIDE_WINDOW"
                        reason = (
                            f"Frozen peak index {baseline_peak} is outside "
                            f"[{shifted_start},{shifted_end}]."
                        )
                    else:
                        raw_time = np.asarray(
                            arrays["TIME"][raw_indices],
                            dtype=np.float64,
                        )
                        raw_flux = np.asarray(
                            arrays[required_flux_column][raw_indices],
                            dtype=np.float64,
                        )
                        finite_mask = (
                            np.isfinite(raw_time)
                            & np.isfinite(raw_flux)
                        )
                        removed_nonfinite_count = int(
                            len(raw_indices) - np.count_nonzero(finite_mask)
                        )
                        if profile["quality_policy"] == "q0_native":
                            raw_quality = np.asarray(
                                arrays["QUALITY"][raw_indices],
                                dtype=np.int64,
                            )
                            quality_mask = raw_quality == 0
                            removed_quality_count = int(
                                np.count_nonzero(
                                    finite_mask & ~quality_mask
                                )
                            )
                            mask = finite_mask & quality_mask
                        elif profile["quality_policy"] == "finite_all":
                            removed_quality_count = 0
                            mask = finite_mask
                        else:
                            raise RuntimeError(
                                "Unexpected frozen quality policy: "
                                f"{profile['quality_policy']}"
                            )

                        retained_indices = canonical_array(
                            raw_indices[mask],
                            "<i8",
                        )
                        retained_time_tbjd = canonical_array(
                            raw_time[mask],
                            "<f8",
                        )
                        retained_flux = canonical_array(
                            raw_flux[mask],
                            "<f8",
                        )
                        retained_n_samples = len(retained_indices)
                        peak_retained = bool(
                            np.any(retained_indices == baseline_peak)
                        )
                        if retained_n_samples > 0:
                            retained_index_start = int(
                                retained_indices[0]
                            )
                            retained_index_end = int(
                                retained_indices[-1]
                            )
                            retained_indices_sha256 = (
                                canonical_array_hash(
                                    retained_indices,
                                    "<i8",
                                )
                            )

                        if not peak_retained:
                            status = "PEAK_REMOVED_BY_QUALITY"
                            reason = (
                                f"Frozen peak index {baseline_peak} is "
                                "absent after the frozen quality mask."
                            )
                        elif retained_n_samples < 15:
                            status = "TOO_FEW_CADENCES"
                            reason = (
                                f"{retained_n_samples} retained cadences; "
                                "minimum is 15."
                            )
                        else:
                            time_seconds = canonical_array(
                                (
                                    retained_time_tbjd
                                    - retained_time_tbjd[0]
                                )
                                * 86400.0,
                                "<f8",
                            )
                            if (
                                not np.all(np.isfinite(time_seconds))
                                or not np.all(np.isfinite(retained_flux))
                            ):
                                status = "NONFINITE_INPUT"
                                reason = (
                                    "Non-finite time_seconds or flux "
                                    "remained after the frozen mask."
                                )
                            else:
                                differences = np.diff(time_seconds)
                                time_strictly_increasing = bool(
                                    np.all(differences > 0.0)
                                )
                                time_has_duplicates = bool(
                                    len(np.unique(time_seconds))
                                    != len(time_seconds)
                                )
                                retained_indices_consecutive = bool(
                                    np.all(
                                        np.diff(retained_indices) == 1
                                    )
                                )
                                median_cadence_s = float(
                                    np.median(differences)
                                )
                                max_interval_deviation_s = float(
                                    np.max(
                                        np.abs(
                                            differences
                                            - median_cadence_s
                                        )
                                    )
                                )
                                irregular_reasons = []
                                if not time_strictly_increasing:
                                    irregular_reasons.append(
                                        "time_not_strictly_increasing"
                                    )
                                if time_has_duplicates:
                                    irregular_reasons.append(
                                        "duplicate_times"
                                    )
                                if not retained_indices_consecutive:
                                    irregular_reasons.append(
                                        "retained_indices_not_consecutive"
                                    )
                                if (
                                    max_interval_deviation_s
                                    > 0.001
                                ):
                                    irregular_reasons.append(
                                        "interval_deviation_gt_0.001_s"
                                    )
                                if irregular_reasons:
                                    status = "IRREGULAR_SAMPLING"
                                    reason = "|".join(irregular_reasons)
                                elif profile["detrending"] == "none":
                                    final_flux = canonical_array(
                                        retained_flux,
                                        "<f8",
                                    )
                                    all_finite = bool(
                                        np.all(np.isfinite(time_seconds))
                                        and np.all(np.isfinite(final_flux))
                                    )
                                    status = "ELIGIBLE_FOR_AFINO"
                                    reason = ""
                                elif profile["detrending"] == (
                                    "linear_residual_plus_one"
                                ):
                                    try:
                                        x = (
                                            time_seconds
                                            - np.mean(time_seconds)
                                        )
                                        X = np.column_stack(
                                            [np.ones(len(x)), x]
                                        )
                                        beta = np.linalg.lstsq(
                                            X,
                                            retained_flux,
                                            rcond=None,
                                        )[0]
                                        trend = X @ beta
                                        scale = np.median(retained_flux)
                                        detrend_beta0 = float(beta[0])
                                        detrend_beta1 = float(beta[1])
                                        detrend_scale = float(scale)
                                        transformed = (
                                            1.0
                                            + (retained_flux - trend)
                                            / scale
                                        )
                                        final_flux = canonical_array(
                                            transformed,
                                            "<f8",
                                        )
                                        detrend_valid = (
                                            math.isfinite(
                                                detrend_scale
                                            )
                                            and detrend_scale != 0.0
                                            and np.all(np.isfinite(beta))
                                            and np.all(np.isfinite(trend))
                                            and np.all(
                                                np.isfinite(final_flux)
                                            )
                                        )
                                        if not detrend_valid:
                                            status = "DETREND_FAILURE"
                                            reason = (
                                                "Frozen detrending "
                                                "validity requirements failed."
                                            )
                                        else:
                                            all_finite = bool(
                                                np.all(
                                                    np.isfinite(time_seconds)
                                                )
                                                and np.all(
                                                    np.isfinite(final_flux)
                                                )
                                            )
                                            status = "ELIGIBLE_FOR_AFINO"
                                            reason = ""
                                    except Exception as exc:
                                        status = "DETREND_FAILURE"
                                        reason = (
                                            f"{type(exc).__name__}: {exc}"
                                        )
                                else:
                                    raise RuntimeError(
                                        "Unexpected frozen detrending: "
                                        f"{profile['detrending']}"
                                    )
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                raise

            if status not in ADMISSIBILITY_PRECEDENCE:
                raise RuntimeError(
                    f"Variant {variant_id} received invalid status {status!r}."
                )

            eligible_payload_order: int | str = ""
            payload_start_offset: int | str = ""
            payload_end_offset: int | str = ""
            time_sha = ""
            flux_sha = ""
            materialization_status = "INPUT_INADMISSIBLE"

            if status == "ELIGIBLE_FOR_AFINO":
                assert time_seconds is not None
                assert final_flux is not None
                assert retained_indices is not None
                if len(time_seconds) != len(final_flux):
                    raise RuntimeError(
                        f"Eligible length mismatch for {variant_id}."
                    )
                if len(time_seconds) != len(retained_indices):
                    raise RuntimeError(
                        f"Eligible index length mismatch for {variant_id}."
                    )
                eligible_payload_order = len(eligible_times) + 1
                payload_start_offset = offsets[-1]
                payload_end_offset = (
                    payload_start_offset + len(time_seconds)
                )
                eligible_times.append(time_seconds)
                eligible_fluxes.append(final_flux)
                eligible_indices.append(retained_indices)
                offsets.append(payload_end_offset)
                time_sha = canonical_array_hash(time_seconds, "<f8")
                flux_sha = canonical_array_hash(final_flux, "<f8")
                materialization_status = "MATERIALIZED"

            diagnostic_flags.update({
                "peak_index": baseline_peak,
                "raw_window": [shifted_start, shifted_end],
                "retained_count": retained_n_samples,
                "time_regular_atol_s": 0.001,
                "interpolation_performed": False,
                "gap_filling_performed": False,
                "time_reindexed": False,
            })

            manifest_row = {
                "variant_id": variant_id,
                "variant_order": variant_order,
                "primary_planned_decision_id":
                    planned["planned_decision_id"],
                "event_id": event["event_id"],
                "pair_id": event["pair_id"],
                "observational_role":
                    event["observational_role"],
                "window_variant_id":
                    window["window_variant_id"],
                "processing_profile_id":
                    profile["processing_profile_id"],
                "flux_product": profile["flux_product"],
                "quality_policy": profile["quality_policy"],
                "detrending": profile["detrending"],
                "source_fits_filename":
                    event["source_fits_filename"],
                "source_fits_sha256":
                    event["source_fits_sha256"],
                "baseline_start_index": baseline_start,
                "baseline_peak_index": baseline_peak,
                "baseline_end_index": baseline_end,
                "shifted_start_index": shifted_start,
                "shifted_end_index": shifted_end,
                "raw_n_samples": raw_n_samples,
                "retained_n_samples": retained_n_samples,
                "removed_nonfinite_count":
                    removed_nonfinite_count,
                "removed_quality_count": removed_quality_count,
                "peak_in_raw_window": peak_in_raw_window,
                "peak_retained": peak_retained,
                "retained_index_start": retained_index_start,
                "retained_index_end": retained_index_end,
                "retained_indices_consecutive":
                    retained_indices_consecutive,
                "retained_indices_sha256":
                    retained_indices_sha256,
                "time_strictly_increasing":
                    time_strictly_increasing,
                "time_has_duplicates": time_has_duplicates,
                "median_cadence_s": median_cadence_s,
                "max_interval_deviation_s":
                    max_interval_deviation_s,
                "detrend_beta0": detrend_beta0,
                "detrend_beta1": detrend_beta1,
                "detrend_scale": detrend_scale,
                "admissibility_status": status,
                "admissibility_reason": reason,
                "diagnostic_flags_json": json.dumps(
                    diagnostic_flags,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                "eligible_payload_order":
                    eligible_payload_order,
                "payload_start_offset": payload_start_offset,
                "payload_end_offset": payload_end_offset,
                "time_sha256": time_sha,
                "flux_sha256": flux_sha,
                "all_finite": all_finite,
                "materialization_status":
                    materialization_status,
                "error": error,
            }
            variant_rows.append(manifest_row)
            primary_variant_by_key[
                (
                    event["event_id"],
                    window["window_variant_id"],
                    profile["processing_profile_id"],
                )
            ] = manifest_row

        if len(variant_rows) != 780:
            raise RuntimeError("Variant manifest does not contain 780 rows.")

        variant_fields = [
            "variant_id",
            "variant_order",
            "primary_planned_decision_id",
            "event_id",
            "pair_id",
            "observational_role",
            "window_variant_id",
            "processing_profile_id",
            "flux_product",
            "quality_policy",
            "detrending",
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
            "admissibility_status",
            "admissibility_reason",
            "diagnostic_flags_json",
            "eligible_payload_order",
            "payload_start_offset",
            "payload_end_offset",
            "time_sha256",
            "flux_sha256",
            "all_finite",
            "materialization_status",
            "error",
        ]
        manifest_path = (
            staging
            / "fase2_tarea02_observational_variant_manifest.csv"
        )
        write_csv(manifest_path, variant_rows, variant_fields)

        eligible_count = len(eligible_times)
        if eligible_count == 0:
            raise RuntimeError("No primary variants were eligible.")

        time_values = canonical_array(
            np.concatenate(eligible_times),
            "<f8",
        )
        flux_values = canonical_array(
            np.concatenate(eligible_fluxes),
            "<f8",
        )
        index_values = canonical_array(
            np.concatenate(eligible_indices),
            "<i8",
        )
        offset_values = canonical_array(offsets, "<i8")

        if not (
            len(time_values)
            == len(flux_values)
            == len(index_values)
        ):
            raise RuntimeError("Eligible payload lengths differ.")
        if int(offset_values[0]) != 0:
            raise RuntimeError("Eligible offsets do not start at zero.")
        if int(offset_values[-1]) != len(time_values):
            raise RuntimeError("Eligible offsets do not end at payload length.")
        if len(offset_values) != eligible_count + 1:
            raise RuntimeError("Eligible offset count is incorrect.")

        time_path = (
            staging / "fase2_tarea02_eligible_time_values.npy"
        )
        flux_path = (
            staging / "fase2_tarea02_eligible_flux_values.npy"
        )
        index_path = (
            staging / "fase2_tarea02_eligible_fits_index_values.npy"
        )
        offsets_path = (
            staging / "fase2_tarea02_eligible_variant_offsets.npy"
        )
        np.save(time_path, time_values, allow_pickle=False)
        np.save(flux_path, flux_values, allow_pickle=False)
        np.save(index_path, index_values, allow_pickle=False)
        np.save(offsets_path, offset_values, allow_pickle=False)

        print(f"primary_variant_rows: {len(variant_rows)}")
        print(f"eligible_primary_variants: {eligible_count}")
        print(
            "inadmissible_primary_variants: "
            f"{len(variant_rows) - eligible_count}"
        )

        print()
        print("===== W00/P00 BASELINE EQUIVALENCE =====")
        baseline_comparisons: list[dict[str, Any]] = []
        for event in cohort:
            variant = primary_variant_by_key[
                (event["event_id"], "W00", "P00")
            ]
            if variant["admissibility_status"] != "ELIGIBLE_FOR_AFINO":
                raise RuntimeError(
                    f"W00/P00 is not eligible for {event['event_id']}: "
                    f"{variant['admissibility_status']}"
                )
            reference = baseline_reference_for_event(
                event,
                f09_manifest,
                f013_manifest,
            )
            comparison = {
                "event_id": event["event_id"],
                "variant_id": variant["variant_id"],
                "reference_csv":
                    reference["source_csv_filename"],
                "reference_csv_sha256":
                    reference["source_csv_sha256"],
                "n_samples_match": (
                    int(variant["retained_n_samples"])
                    == reference["n_samples"]
                ),
                "time_sha256_match": (
                    variant["time_sha256"]
                    == reference["time_sha256"]
                ),
                "flux_sha256_match": (
                    variant["flux_sha256"]
                    == reference["flux_sha256"]
                ),
                "first_index_match": (
                    int(variant["retained_index_start"])
                    == reference["first_fits_index"]
                ),
                "last_index_match": (
                    int(variant["retained_index_end"])
                    == reference["last_fits_index"]
                ),
            }
            comparison["exact_match"] = all(
                value
                for key, value in comparison.items()
                if key.endswith("_match")
            )
            if not comparison["exact_match"]:
                raise RuntimeError(
                    f"W00/P00 baseline mismatch for {event['event_id']}: "
                    f"{comparison}"
                )
            baseline_comparisons.append(comparison)
            print(f"{event['event_id']}: exact")

        if sum(row["exact_match"] for row in baseline_comparisons) != 10:
            raise RuntimeError("Baseline exact-match count is not 10.")

        print()
        print("===== ROUND-TRIP =====")
        reloaded_time = np.load(time_path, allow_pickle=False)
        reloaded_flux = np.load(flux_path, allow_pickle=False)
        reloaded_index = np.load(index_path, allow_pickle=False)
        reloaded_offsets = np.load(offsets_path, allow_pickle=False)

        if reloaded_time.dtype.str != "<f8":
            raise RuntimeError("Reloaded time dtype is not <f8.")
        if reloaded_flux.dtype.str != "<f8":
            raise RuntimeError("Reloaded flux dtype is not <f8.")
        if reloaded_index.dtype.str != "<i8":
            raise RuntimeError("Reloaded index dtype is not <i8.")
        if reloaded_offsets.dtype.str != "<i8":
            raise RuntimeError("Reloaded offsets dtype is not <i8.")

        roundtrip_time_matches = 0
        roundtrip_flux_matches = 0
        roundtrip_index_matches = 0
        eligible_manifest_rows = [
            row for row in variant_rows
            if row["admissibility_status"] == "ELIGIBLE_FOR_AFINO"
        ]
        eligible_manifest_rows.sort(
            key=lambda row: int(row["eligible_payload_order"])
        )
        for position, row in enumerate(eligible_manifest_rows):
            start = int(reloaded_offsets[position])
            end = int(reloaded_offsets[position + 1])
            expected_length = int(row["retained_n_samples"])
            if end - start != expected_length:
                raise RuntimeError(
                    f"Round-trip offset length mismatch for "
                    f"{row['variant_id']}."
                )
            time_slice = canonical_array(
                reloaded_time[start:end],
                "<f8",
            )
            flux_slice = canonical_array(
                reloaded_flux[start:end],
                "<f8",
            )
            index_slice = canonical_array(
                reloaded_index[start:end],
                "<i8",
            )
            if canonical_array_hash(time_slice, "<f8") == row["time_sha256"]:
                roundtrip_time_matches += 1
            if canonical_array_hash(flux_slice, "<f8") == row["flux_sha256"]:
                roundtrip_flux_matches += 1
            if (
                canonical_array_hash(index_slice, "<i8")
                == row["retained_indices_sha256"]
            ):
                roundtrip_index_matches += 1

            if float(time_slice[0]) != 0.0:
                raise RuntimeError(
                    f"Round-trip time does not start at 0 for "
                    f"{row['variant_id']}."
                )
            if not np.all(np.diff(time_slice) > 0.0):
                raise RuntimeError(
                    f"Round-trip time is not increasing for "
                    f"{row['variant_id']}."
                )
            if not np.all(np.diff(index_slice) == 1):
                raise RuntimeError(
                    f"Round-trip indices are not consecutive for "
                    f"{row['variant_id']}."
                )
            differences = np.diff(time_slice)
            if (
                np.max(
                    np.abs(differences - np.median(differences))
                )
                > 0.001
            ):
                raise RuntimeError(
                    f"Round-trip cadence is irregular for "
                    f"{row['variant_id']}."
                )
            if not (
                np.all(np.isfinite(time_slice))
                and np.all(np.isfinite(flux_slice))
            ):
                raise RuntimeError(
                    f"Round-trip non-finite values for "
                    f"{row['variant_id']}."
                )

        if roundtrip_time_matches != eligible_count:
            raise RuntimeError("Not all eligible time round-trips matched.")
        if roundtrip_flux_matches != eligible_count:
            raise RuntimeError("Not all eligible flux round-trips matched.")
        if roundtrip_index_matches != eligible_count:
            raise RuntimeError("Not all eligible index round-trips matched.")

        print(
            f"eligible time round-trips: "
            f"{roundtrip_time_matches}/{eligible_count}"
        )
        print(
            f"eligible flux round-trips: "
            f"{roundtrip_flux_matches}/{eligible_count}"
        )
        print(
            f"eligible index round-trips: "
            f"{roundtrip_index_matches}/{eligible_count}"
        )

        print()
        print("===== RESOLVED DECISION GRID =====")
        resolved_rows: list[dict[str, Any]] = []
        for planned in planned_grid:
            key = (
                planned["event_id"],
                planned["window_variant_id"],
                planned["processing_profile_id"],
            )
            variant = primary_variant_by_key[key]
            eligible = (
                variant["admissibility_status"]
                == "ELIGIBLE_FOR_AFINO"
            )
            resolved_rows.append({
                **planned,
                "variant_id": variant["variant_id"],
                "admissibility_status":
                    variant["admissibility_status"],
                "execute_afino": "true" if eligible else "false",
                "input_n_samples": (
                    variant["retained_n_samples"] if eligible else ""
                ),
                "input_time_sha256": (
                    variant["time_sha256"] if eligible else ""
                ),
                "input_flux_sha256": (
                    variant["flux_sha256"] if eligible else ""
                ),
                "payload_start_offset": (
                    variant["payload_start_offset"] if eligible else ""
                ),
                "payload_end_offset": (
                    variant["payload_end_offset"] if eligible else ""
                ),
                "resolved_decision_status": (
                    "READY_FOR_AFINO"
                    if eligible
                    else "INPUT_INADMISSIBLE"
                ),
            })

        if len(resolved_rows) != 1320:
            raise RuntimeError("Resolved grid does not contain 1320 rows.")
        resolved_fields = list(planned_grid[0].keys()) + [
            "variant_id",
            "admissibility_status",
            "execute_afino",
            "input_n_samples",
            "input_time_sha256",
            "input_flux_sha256",
            "payload_start_offset",
            "payload_end_offset",
            "resolved_decision_status",
        ]
        resolved_path = (
            staging / "fase2_tarea02_resolved_decision_grid.csv"
        )
        write_csv(resolved_path, resolved_rows, resolved_fields)

        eligible_primary_decisions = sum(
            row["decision_class"] == "primary"
            and row["execute_afino"] == "true"
            for row in resolved_rows
        )
        eligible_w00_profile_variants = sum(
            row["window_variant_id"] == "W00"
            and row["admissibility_status"] == "ELIGIBLE_FOR_AFINO"
            for row in variant_rows
        )
        eligible_stability_decisions = sum(
            row["decision_class"] == "stability"
            and row["execute_afino"] == "true"
            for row in resolved_rows
        )
        if eligible_primary_decisions != eligible_count:
            raise RuntimeError("Primary eligibility did not propagate.")
        if eligible_stability_decisions != (
            9 * eligible_w00_profile_variants
        ):
            raise RuntimeError(
                "Stability eligibility inheritance is incorrect."
            )
        exact_executable_decisions = sum(
            row["execute_afino"] == "true"
            for row in resolved_rows
        )

        print(
            f"eligible_w00_profile_variants: "
            f"{eligible_w00_profile_variants}"
        )
        print(
            f"eligible_stability_decisions: "
            f"{eligible_stability_decisions}"
        )
        print(
            f"exact_executable_decisions: "
            f"{exact_executable_decisions}"
        )

        print()
        print("===== EXACT AFINO EXECUTION PLAN =====")
        exact_jobs: list[dict[str, Any]] = []
        for resolved in resolved_rows:
            if resolved["execute_afino"] != "true":
                continue
            event = cohort_by_event[resolved["event_id"]]
            for model_id, model_name in MODEL_ROWS:
                job_order = len(exact_jobs) + 1
                exact_jobs.append({
                    "job_id": f"F2J{job_order:06d}",
                    "job_order": job_order,
                    "planned_decision_id":
                        resolved["planned_decision_id"],
                    "decision_class":
                        resolved["decision_class"],
                    "variant_id": resolved["variant_id"],
                    "event_id": resolved["event_id"],
                    "pair_id": resolved["pair_id"],
                    "observational_role":
                        resolved["observational_role"],
                    "window_variant_id":
                        resolved["window_variant_id"],
                    "processing_profile_id":
                        resolved["processing_profile_id"],
                    "external_optimizer_seed":
                        resolved["external_optimizer_seed"],
                    "model_id": model_id,
                    "model_name": model_name,
                    "n_samples": resolved["input_n_samples"],
                    "payload_start_offset":
                        resolved["payload_start_offset"],
                    "payload_end_offset":
                        resolved["payload_end_offset"],
                    "input_time_sha256":
                        resolved["input_time_sha256"],
                    "input_flux_sha256":
                        resolved["input_flux_sha256"],
                    "source_fits_sha256":
                        event["source_fits_sha256"],
                    "candidate_discovery_use": "false",
                })

        exact_model_calls = 3 * exact_executable_decisions
        if len(exact_jobs) != exact_model_calls:
            raise RuntimeError("Exact job count is not 3 per decision.")
        job_counts = Counter(row["model_id"] for row in exact_jobs)
        rows_per_model = exact_executable_decisions
        if job_counts != {
            "M0": rows_per_model,
            "M1": rows_per_model,
            "M2": rows_per_model,
        }:
            raise RuntimeError("Exact plan model counts differ.")
        if len({row["job_id"] for row in exact_jobs}) != len(exact_jobs):
            raise RuntimeError("Duplicate job IDs.")
        scientific_job_keys = {
            (
                row["variant_id"],
                row["external_optimizer_seed"],
                row["model_id"],
            )
            for row in exact_jobs
        }
        if len(scientific_job_keys) != len(exact_jobs):
            raise RuntimeError("Duplicate scientific job keys.")
        if any(
            row["candidate_discovery_use"] != "false"
            for row in exact_jobs
        ):
            raise RuntimeError("Candidate discovery appeared in exact plan.")

        exact_fields = [
            "job_id",
            "job_order",
            "planned_decision_id",
            "decision_class",
            "variant_id",
            "event_id",
            "pair_id",
            "observational_role",
            "window_variant_id",
            "processing_profile_id",
            "external_optimizer_seed",
            "model_id",
            "model_name",
            "n_samples",
            "payload_start_offset",
            "payload_end_offset",
            "input_time_sha256",
            "input_flux_sha256",
            "source_fits_sha256",
            "candidate_discovery_use",
        ]
        exact_plan_path = (
            staging / "fase2_tarea02_exact_afino_execution_plan.csv"
        )
        write_csv(exact_plan_path, exact_jobs, exact_fields)
        print(f"exact_model_calls: {len(exact_jobs)}")
        print(f"rows_per_model: {rows_per_model}")

        # Confirm FITS and F2.1 inputs stayed unchanged.
        fits_physical_hashes_after = {}
        for filename, expected in fits_physical_hashes_before.items():
            path = fits_cache[filename]["path"]
            observed = sha256_file(path)
            if observed != expected:
                raise RuntimeError(
                    f"Frozen FITS changed during F2.2: {filename}"
                )
            fits_physical_hashes_after[filename] = observed

        f21_hashes_after = {
            filename: sha256_file(PROJECT_ROOT / filename)
            for filename in F21_HASHES
        }
        if f21_hashes_after != f21_hashes_before:
            raise RuntimeError("A frozen F2.1 source changed during F2.2.")

        environment_text = "\n".join([
            f"Python: {platform.python_version()}",
            f"Python full: {sys.version.replace(os.linesep, ' ')}",
            "Python executable relative: "
            + (
                str(Path(sys.executable).resolve().relative_to(PROJECT_ROOT))
                if Path(sys.executable).resolve().is_relative_to(PROJECT_ROOT)
                else redact_path(Path(sys.executable))
            ),
            f"NumPy: {np.__version__}",
            f"Astropy: {astropy.__version__}",
            f"Platform: {platform.platform()}",
            f"Machine: {platform.machine()}",
            f"Processor: {platform.processor()}",
            f"FITS root: {redact_path(fits_root)}",
            "AFINO imported: false",
            "AFINO executed: false",
            "FITS downloaded: false",
            "",
        ])
        environment_path = staging / "fase2_tarea02_environment.txt"
        environment_path.write_text(environment_text, encoding="utf-8")

        admissibility_status_counts = dict(
            sorted(
                Counter(
                    row["admissibility_status"]
                    for row in variant_rows
                ).items()
            )
        )
        counts_by_profile: dict[str, dict[str, int]] = {}
        for profile in profiles:
            group = [
                row for row in variant_rows
                if row["processing_profile_id"]
                == profile["processing_profile_id"]
            ]
            counts_by_profile[profile["processing_profile_id"]] = dict(
                sorted(
                    Counter(
                        row["admissibility_status"]
                        for row in group
                    ).items()
                )
            )
        counts_by_window: dict[str, dict[str, int]] = {}
        for window in windows:
            group = [
                row for row in variant_rows
                if row["window_variant_id"]
                == window["window_variant_id"]
            ]
            counts_by_window[window["window_variant_id"]] = dict(
                sorted(
                    Counter(
                        row["admissibility_status"]
                        for row in group
                    ).items()
                )
            )

        inadmissible_reasons = [
            f"{status}={count}"
            for status, count in admissibility_status_counts.items()
            if status != "ELIGIBLE_FOR_AFINO"
        ]
        reasons_text = (
            ", ".join(inadmissible_reasons)
            if inadmissible_reasons
            else "ninguna"
        )
        checksum_fail_rows = sum(
            row["fits_checksum_status"] == "FAIL"
            for row in fits_audit_rows
        )

        report = f"""# Fase 2 — Tarea 2.2

## Materialización de variantes y congelación del plan exacto

**Estado:** `{FINAL_STATUS}`

Se localizaron los diez productos FITS asociados a la cohorte congelada y
cada archivo coincidió con el SHA-256 registrado en F2.1. La tabla
`LIGHTCURVE` fue legible en todos los casos y se registraron el número de
filas y la presencia de `TIME`, `QUALITY`, `SAP_FLUX` y `PDCSAP_FLUX`.
Hubo {checksum_fail_rows} filas de auditoría con fallos históricos de
`CHECKSUM` o `DATASUM`; estos avisos se conservaron como metadatos porque el
hash físico coincidió y la tabla fue utilizable. No se descargó ningún FITS.

Se resolvieron las 780 combinaciones primarias en el orden exacto del grid
F2.1 y se asignaron los identificadores `F2V000001` a `F2V000780` sin
reordenar por evento, clase, ventana, perfil o elegibilidad. Resultaron
{eligible_count} variantes `ELIGIBLE_FOR_AFINO` y
{len(variant_rows) - eligible_count} inadmisibles. Las razones técnicas
observadas fueron: {reasons_text}. Cada variante recibió una única categoría
según la precedencia congelada. Las inadmisibles permanecen en el manifiesto
con `INPUT_INADMISSIBLE`, sin BIC, sin selección y sin payload.

Las diez variantes baseline `W00/P00` fueron elegibles. Sus números de
muestras, hashes lógicos de tiempo y flujo, y primeros y últimos índices FITS
coincidieron exactamente con los CSV baseline físicamente congelados por
F0.9/F0.10 y F0.13/F0.14. La comparación no ejecutó AFINO y no recalculó una
clasificación.

Solo las variantes elegibles se escribieron en los cuatro payloads
contiguos. Los tiempos y flujos se persistieron como `<f8`; los índices FITS y
offsets como `<i8`. Tras cerrar y recargar los `.npy` con
`allow_pickle=False`, coincidieron {roundtrip_time_matches}/{eligible_count}
hashes de tiempo, {roundtrip_flux_matches}/{eligible_count} hashes de flujo y
{roundtrip_index_matches}/{eligible_count} hashes de índices. Desde los arrays
releídos también se confirmó `time[0]==0`, crecimiento temporal estricto,
índices consecutivos, regularidad dentro de 0,001 s y valores finitos.

El grid resuelto conserva las 1.320 decisiones máximas. Las
{eligible_primary_decisions} decisiones primarias elegibles usan su propia
variante. En la estabilidad, las seeds 1–9 heredaron únicamente la
elegibilidad del mismo evento y perfil en `W00`; por ello existen
{eligible_w00_profile_variants} variantes W00-perfil elegibles y
{eligible_stability_decisions} decisiones de estabilidad ejecutables. El plan
exacto congela {exact_executable_decisions} decisiones y
{exact_model_calls} llamadas: {rows_per_model} para cada uno de M0, M1 y M2.
No se forzó el máximo teórico de 3.960 llamadas.

No se interpoló, rellenó ni reindexó ninguna curva. Los perfiles P00–P03 no
fueron normalizados, recentrados o reescalados. El detrending P04/P05 utilizó
literalmente la fórmula prerregistrada y sus fallos, cuando existieron,
permanecieron como inadmisibilidad. No se añadió ninguna ventana, perfil,
evento o umbral.

F2.2 resolvió exclusivamente la elegibilidad técnica y congeló inputs y
trabajos futuros. No se importó ni ejecutó AFINO, no se observaron resultados
de clasificación QPP y no se comparó científicamente la elegibilidad entre las
dos clases observacionales. La búsqueda de candidatos continúa bloqueada.

Los conteos de elegibilidad documentan qué inputs satisfacen el contrato
prerregistrado de muestreo, calidad y preprocesamiento. No describen una
diferencia física entre detecciones publicadas y controles, ni permiten
calcular sensibilidad, especificidad o una tasa observacional de falsos
positivos. La interpretación científica de las clasificaciones permanecerá
aplazada hasta que el plan exacto sea validado mediante canary y ejecutado con
checkpointing en tareas posteriores.

`{FINAL_STATUS}`
"""
        report_word_count = len(
            re.findall(
                r"\b[\wÁÉÍÓÚÜÑáéíóúüñ]+\b",
                report,
            )
        )
        if not 500 <= report_word_count <= 800:
            raise RuntimeError(
                f"Report word count {report_word_count} outside 500-800."
            )
        report_path = (
            staging
            / "fase2_tarea02_variant_materialization_report.md"
        )
        report_path.write_text(report, encoding="utf-8")

        physical_npy_hashes = {
            time_path.name: sha256_file(time_path),
            flux_path.name: sha256_file(flux_path),
            index_path.name: sha256_file(index_path),
            offsets_path.name: sha256_file(offsets_path),
        }
        logical_hashes = {
            "canonical_time_payload_sha256":
                canonical_array_hash(reloaded_time, "<f8"),
            "canonical_flux_payload_sha256":
                canonical_array_hash(reloaded_flux, "<f8"),
            "canonical_fits_index_payload_sha256":
                canonical_array_hash(reloaded_index, "<i8"),
            "variant_offsets_canonical_sha256":
                canonical_array_hash(reloaded_offsets, "<i8"),
            "ordered_variant_manifest_sha256":
                sha256_file(manifest_path),
            "resolved_decision_grid_sha256":
                sha256_file(resolved_path),
            "exact_execution_plan_sha256":
                sha256_file(exact_plan_path),
        }

        audit = {
            "materialization_status": FINAL_STATUS,
            "study_id": prereg["study_id"],
            "study_version": prereg["study_version"],
            "date_utc": datetime.now(timezone.utc).isoformat(),
            "source_hashes": {
                "f2_1_before": f21_hashes_before,
                "f2_1_after": f21_hashes_after,
                "fits_before": fits_physical_hashes_before,
                "fits_after": fits_physical_hashes_after,
                "baseline_input_manifests": {
                    f09_manifest_path.name:
                        sha256_file(f09_manifest_path),
                    f013_manifest_path.name:
                        sha256_file(f013_manifest_path),
                },
            },
            "source_fits_rows": 10,
            "primary_variant_rows": 780,
            "resolved_decision_rows": 1320,
            "eligible_primary_variants": eligible_count,
            "inadmissible_primary_variants":
                len(variant_rows) - eligible_count,
            "eligible_w00_profile_variants":
                eligible_w00_profile_variants,
            "eligible_stability_decisions":
                eligible_stability_decisions,
            "exact_executable_decisions":
                exact_executable_decisions,
            "exact_model_calls": exact_model_calls,
            "rows_per_model": rows_per_model,
            "admissibility_status_counts":
                admissibility_status_counts,
            "admissibility_counts_by_profile":
                counts_by_profile,
            "admissibility_counts_by_window":
                counts_by_window,
            "baseline_w00_p00_exact_matches": 10,
            "baseline_comparisons": baseline_comparisons,
            "duplicate_variant_ids":
                len(variant_rows)
                - len({row["variant_id"] for row in variant_rows}),
            "duplicate_resolved_decision_ids":
                len(resolved_rows)
                - len({
                    row["planned_decision_id"]
                    for row in resolved_rows
                }),
            "duplicate_job_ids":
                len(exact_jobs)
                - len({row["job_id"] for row in exact_jobs}),
            "duplicate_scientific_job_keys":
                len(exact_jobs) - len(scientific_job_keys),
            "roundtrip_time_matches":
                roundtrip_time_matches,
            "roundtrip_flux_matches":
                roundtrip_flux_matches,
            "roundtrip_index_matches":
                roundtrip_index_matches,
            "physical_npy_hashes": physical_npy_hashes,
            "logical_hashes": logical_hashes,
            "report_word_count": report_word_count,
            "incidents": [],
            "confirmations": {
                "afino_executed": False,
                "fits_downloaded": False,
                "new_events_added": False,
                "cohort_modified": False,
                "baseline_modified": False,
                "inadmissible_variants_treated_as_not_selected":
                    False,
                "interpolation_performed": False,
                "gap_filling_performed": False,
                "time_reindexed": False,
                "profiles_added": False,
                "windows_added": False,
                "candidate_discovery_authorized": False,
                "scientific_classification_results_observed":
                    False,
                "new_selection_threshold_added": False,
            },
        }
        audit_path = (
            staging / "fase2_tarea02_variant_materialization_audit.json"
        )
        audit_path.write_text(
            json.dumps(
                audit,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )

        # Final structural validation before publishing.
        if len(read_csv(manifest_path)) != 780:
            raise RuntimeError("Published variant manifest count changed.")
        if len(read_csv(resolved_path)) != 1320:
            raise RuntimeError("Published resolved-grid count changed.")
        if len(read_csv(exact_plan_path)) != exact_model_calls:
            raise RuntimeError("Published exact-plan count changed.")
        if audit["duplicate_variant_ids"] != 0:
            raise RuntimeError("Duplicate variant IDs detected.")
        if audit["duplicate_resolved_decision_ids"] != 0:
            raise RuntimeError("Duplicate resolved decision IDs detected.")
        if audit["duplicate_job_ids"] != 0:
            raise RuntimeError("Duplicate job IDs detected.")
        if audit["duplicate_scientific_job_keys"] != 0:
            raise RuntimeError("Duplicate scientific job keys detected.")
        if any(audit["confirmations"].values()):
            raise RuntimeError("A prohibited operation was recorded.")

        # Publish all official outputs atomically after complete validation.
        for output_name in OUTPUT_NAMES:
            source = staging / output_name
            target = PROJECT_ROOT / output_name
            if not source.is_file():
                raise FileNotFoundError(source)
            if target.exists():
                raise FileExistsError(target)
        for output_name in OUTPUT_NAMES:
            os.replace(
                staging / output_name,
                PROJECT_ROOT / output_name,
            )
        staging.rmdir()

        print()
        print("===== FINAL HASHES =====")
        for output_name in OUTPUT_NAMES:
            print(
                f"{output_name}: "
                f"{sha256_file(PROJECT_ROOT / output_name)}"
            )
        print()
        print(FINAL_STATUS)
        print("F2.2 VARIANT MATERIALIZATION COMPLETE")
    except Exception:
        print()
        print("F2.2 MATERIALIZATION STOPPED")
        print(
            "Preserve the console output and staging directory. "
            "Do not overwrite frozen inputs."
        )
        raise


if __name__ == "__main__":
    main()
