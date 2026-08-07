#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


EXPECTED_HASHES = {
    "fase1_tarea01_core_benchmark_preregistration.json":
        "dd80346172290e014d73f78240b3e31f135bcc7e4f075963e7e20d8456de3401",
    "fase1_tarea01_core_design_grid.csv":
        "f3c4c77ef71b9c8f9218bcf5a773d8e31c9ffc858ea68a1216542970e43f0bad",
    "fase1_tarea03_core_series_manifest.csv":
        "2020c849348c81235036443d3215395c602b80b00debe64fec692935dda778f4",
    "fase1_tarea05_full_checkpoint.sqlite":
        "9751062964e3db79f116270c58461a859c75c570d28bfc988a72a1cb577a934b",
    "fase1_tarea05_core_results.csv":
        "1ba98f4f0df406f36c17c75cf90d0773b09c3139eb2e11dc35d67ac42ac02775",
    "fase1_tarea05_core_decisions.csv":
        "bf2b65aa42f40fa798910096ee62127556dc9cbe67445222df465b6a1352ab27",
    "fase1_tarea05_full_execution_audit.json":
        "7f4a6be19897bced53482cc5fd225f400ad85cd0c28544449e4c58e17d275205",
}

EXPECTED_COUNTS = {
    "results": 16317,
    "decisions": 5439,
    "primary_decisions": 4440,
    "stability_decisions": 999,
    "conditions": 111,
    "paired_contrasts": 288,
    "model_diagnostics": 30,
}

ABS_TOLERANCE = 5e-12
REL_TOLERANCE = 0.0
WILSON_Z = 1.959963984540054

OUTPUT_NAMES = [
    "fase1_tarea06_primary_series_analysis.csv",
    "fase1_tarea06_condition_summary.csv",
    "fase1_tarea06_paired_contrasts.csv",
    "fase1_tarea06_optimizer_stability_summary.csv",
    "fase1_tarea06_model_diagnostics.csv",
    "fase1_tarea06_fig01_null_false_selection.png",
    "fase1_tarea06_fig02_positive_detection_grid.png",
    "fase1_tarea06_fig03_period_error.png",
    "fase1_tarea06_fig04_optimizer_stability.png",
    "fase1_tarea06_fig05_numerical_diagnostics.png",
    "fase1_tarea06_analysis_audit.json",
    "fase1_tarea06_core_benchmark_analysis.md",
]

MODEL_IDS = ("M0", "M1", "M2")
NULL_LABEL = "NULL_FLARE_RED_NOISE"
POSITIVE_LABEL = "STATIONARY_QPP_PRESENT"

RESULT_CSV_FIELDS = [
    "job_id", "job_class", "series_id", "condition_id", "ground_truth",
    "data_seed", "external_optimizer_seed", "model_id", "model_name",
    "status", "runtime_seconds", "n_samples", "input_flux_sha256",
    "input_time_sha256", "afino_effective_dt_s", "positive_frequency_bins",
    "bins_after_cutoff", "minimum_frequency_hz", "maximum_frequency_hz",
    "lnlike", "BIC", "rchi2", "probability", "parameters_json",
    "estimated_period_s", "parameter_at_bound", "bound_indices_json",
    "warning_count", "warning_types_json", "convergence_status", "error",
]

DECISION_CSV_FIELDS = [
    "job_class", "series_id", "condition_id", "ground_truth", "data_seed",
    "external_optimizer_seed", "valid_models", "decision_status",
    "delta_bic_0_1", "delta_bic_2_1", "qpp_selected",
    "estimated_period_s", "period_label",
]

PRIMARY_FIELDS = [
    "series_id", "condition_id", "ground_truth", "n_samples", "duration_s",
    "red_noise_alpha", "period_s", "qpp_fraction", "nominal_window_cycles",
    "data_seed", "external_optimizer_seed", "decision_status", "bic_m0",
    "bic_m1", "bic_m2", "delta_bic_0_1", "delta_bic_2_1",
    "delta_bic_min", "qpp_selected", "estimated_period_s", "period_label",
    "period_error_s", "period_absolute_error_s",
    "period_relative_error_percent", "m0_parameter_at_bound",
    "m1_parameter_at_bound", "m2_parameter_at_bound", "m0_warning_count",
    "m1_warning_count", "m2_warning_count",
]

CONDITION_FIELDS = [
    "condition_id", "ground_truth", "n_samples", "duration_s",
    "red_noise_alpha", "period_s", "qpp_fraction", "nominal_window_cycles",
    "n_planned", "n_valid", "valid_run_rate", "n_selected",
    "selection_rate", "selection_rate_ci95_lower",
    "selection_rate_ci95_upper", "rate_name", "selected_period_n",
    "selected_period_median_signed_error_s",
    "selected_period_median_absolute_error_s",
    "selected_period_p90_absolute_error_s",
    "selected_period_median_relative_error_percent",
    "formal_m1_median_signed_error_s",
    "formal_m1_median_absolute_error_s",
    "formal_m1_p90_absolute_error_s", "median_delta_bic_0_1",
    "median_delta_bic_2_1", "median_delta_bic_min", "m0_bound_hit_rate",
    "m1_bound_hit_rate", "m2_bound_hit_rate", "m0_warning_rate",
    "m1_warning_rate", "m2_warning_rate",
]

PAIRED_FIELDS = [
    "contrast_type", "left_condition_id", "right_condition_id", "n_samples",
    "red_noise_alpha", "left_period_s", "right_period_s",
    "left_qpp_fraction", "right_qpp_fraction", "n_pairs",
    "left_selection_rate", "right_selection_rate",
    "paired_selection_difference", "n_left0_right0", "n_left0_right1",
    "n_left1_right0", "n_left1_right1",
    "median_paired_change_delta_bic_min",
]

STABILITY_FIELDS = [
    "condition_id", "series_id", "ground_truth", "n_samples",
    "red_noise_alpha", "period_s", "qpp_fraction",
    "n_valid_optimizer_seeds", "n_selected_optimizer_seeds",
    "optimizer_seed_decision_discordance", "any_decision_change",
    "m0_bic_range", "m1_bic_range", "m2_bic_range",
    "m2_multiple_solution_flag", "formal_m1_period_range_s",
    "selected_period_range_s", "m0_bound_seed_count", "m1_bound_seed_count",
    "m2_bound_seed_count", "m0_warning_seed_count", "m1_warning_seed_count",
    "m2_warning_seed_count",
]

DIAGNOSTIC_FIELDS = [
    "analysis_scope", "grouping", "n_samples", "model_id", "calls",
    "ok_calls", "warning_calls", "warning_total", "bound_hit_calls",
    "warning_rate", "bound_hit_rate", "runtime_total_seconds",
    "runtime_median_seconds",
]


class AnalysisError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def serialize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: serialize(row.get(field)) for field in fields})


def parse_int(value: Any, field: str) -> int:
    try:
        return int(value)
    except Exception as exc:
        raise AnalysisError(f"Invalid integer in {field}: {value!r}") from exc


def parse_float(value: Any, field: str) -> float:
    try:
        result = float(value)
    except Exception as exc:
        raise AnalysisError(f"Invalid float in {field}: {value!r}") from exc
    if not math.isfinite(result):
        raise AnalysisError(f"Non-finite float in {field}: {value!r}")
    return result


def parse_optional_float(value: Any, field: str) -> float | None:
    if value is None or value == "":
        return None
    return parse_float(value, field)


def parse_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise AnalysisError(f"Invalid Boolean in {field}: {value!r}")


def exact_optional_text(value: Any) -> str:
    return "" if value is None else str(value)


def float_equal(left: float, right: float, *, atol: float = 0.0) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=atol)


def median(values: Sequence[float]) -> float | None:
    return None if not values else float(np.median(np.asarray(values, dtype=float)))


def quantile90(values: Sequence[float]) -> float | None:
    return None if not values else float(
        np.quantile(np.asarray(values, dtype=float), 0.90, method="linear")
    )


def numeric_range(values: Sequence[float]) -> float | None:
    return None if not values else float(max(values) - min(values))


def wilson_interval(selected: int, valid: int) -> tuple[float | None, float | None]:
    if valid <= 0:
        return None, None
    p = selected / valid
    z2 = WILSON_Z * WILSON_Z
    denominator = 1.0 + z2 / valid
    center = (p + z2 / (2.0 * valid)) / denominator
    half = WILSON_Z * math.sqrt(
        p * (1.0 - p) / valid + z2 / (4.0 * valid * valid)
    ) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def validate_json_text(text: str, field: str) -> None:
    try:
        json.loads(text)
    except Exception as exc:
        raise AnalysisError(f"Invalid JSON in {field}: {text!r}") from exc


def ensure_output_directory_clean(output_dir: Path, script_path: Path) -> None:
    for name in OUTPUT_NAMES:
        path = output_dir / name
        if path.exists():
            raise AnalysisError(f"Output already exists and must be preserved: {path}")
    normative_script = output_dir / "fase1_tarea06_analyze_core_benchmark.py"
    if normative_script.exists() and normative_script.resolve() != script_path.resolve():
        raise AnalysisError(f"A different normative analysis script already exists: {normative_script}")


def verify_input_hashes(root: Path) -> dict[str, str]:
    observed: dict[str, str] = {}
    for name, expected in EXPECTED_HASHES.items():
        path = root / name
        if not path.is_file():
            raise AnalysisError(f"Missing required input: {path}")
        digest = sha256(path)
        if digest != expected:
            raise AnalysisError(f"Hash mismatch for {name}: {digest} != {expected}")
        observed[name] = digest
    return observed


def load_preregistration(root: Path) -> dict[str, Any]:
    prereg = json.loads(
        (root / "fase1_tarea01_core_benchmark_preregistration.json").read_text(
            encoding="utf-8"
        )
    )
    if prereg.get("preregistration_status") != "FROZEN_BEFORE_SYNTHETIC_GENERATION":
        raise AnalysisError("The F1.1 preregistration is not frozen.")
    if prereg.get("design_grid", {}).get("condition_count") != 111:
        raise AnalysisError("The preregistration does not define 111 conditions.")
    return prereg


def load_design(root: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    fields, raw_rows = read_csv(root / "fase1_tarea01_core_design_grid.csv")
    if len(raw_rows) != EXPECTED_COUNTS["conditions"]:
        raise AnalysisError(f"Design grid has {len(raw_rows)} rows, not 111.")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_rows:
        row: dict[str, Any] = dict(raw)
        row["n_samples"] = parse_int(raw["n_samples"], "n_samples")
        row["duration_s"] = parse_float(raw["duration_s"], "duration_s")
        row["red_noise_alpha"] = parse_float(raw["red_noise_alpha"], "red_noise_alpha")
        row["period_s"] = parse_optional_float(raw["period_s"], "period_s")
        row["qpp_fraction"] = parse_optional_float(raw["qpp_fraction"], "qpp_fraction")
        row["minimum_cycles"] = parse_optional_float(raw["minimum_cycles"], "minimum_cycles")
        row["data_seed_count"] = parse_int(raw["data_seed_count"], "data_seed_count")
        row["planned_series_count"] = parse_int(raw["planned_series_count"], "planned_series_count")
        cid = raw["condition_id"]
        if cid in seen:
            raise AnalysisError(f"Duplicate condition_id in design grid: {cid}")
        seen.add(cid)
        if row["data_seed_count"] != 40 or row["planned_series_count"] != 40:
            raise AnalysisError(f"Condition {cid} does not contain 40 planned series.")
        if row["ground_truth"] not in {NULL_LABEL, POSITIVE_LABEL}:
            raise AnalysisError(f"Unknown ground truth in {cid}.")
        rows.append(row)
    return rows, {row["condition_id"]: row for row in rows}


def load_manifest(root: Path, design_by_id: dict[str, dict[str, Any]]) -> tuple[
    list[dict[str, Any]], dict[str, dict[str, Any]], dict[tuple[str, int], dict[str, Any]]
]:
    _, raw_rows = read_csv(root / "fase1_tarea03_core_series_manifest.csv")
    if len(raw_rows) != 4440:
        raise AnalysisError(f"Series manifest has {len(raw_rows)} rows, not 4440.")
    rows: list[dict[str, Any]] = []
    by_series: dict[str, dict[str, Any]] = {}
    by_condition_seed: dict[tuple[str, int], dict[str, Any]] = {}
    condition_counts: Counter[str] = Counter()
    for raw in raw_rows:
        row: dict[str, Any] = dict(raw)
        for field in ("series_order", "n_samples", "data_seed", "flux_start_offset", "flux_end_offset"):
            row[field] = parse_int(raw[field], field)
        for field in ("duration_s", "red_noise_alpha", "phase_rad"):
            row[field] = parse_float(raw[field], field)
        row["period_s"] = parse_optional_float(raw["period_s"], "period_s")
        row["qpp_fraction"] = parse_optional_float(raw["qpp_fraction"], "qpp_fraction")
        row["minimum_cycles"] = parse_optional_float(raw["minimum_cycles"], "minimum_cycles")
        sid = row["series_id"]
        key = (row["condition_id"], row["data_seed"])
        if sid in by_series:
            raise AnalysisError(f"Duplicate series_id in manifest: {sid}")
        if key in by_condition_seed:
            raise AnalysisError(f"Duplicate condition/data_seed in manifest: {key}")
        design = design_by_id.get(row["condition_id"])
        if design is None:
            raise AnalysisError(f"Manifest condition absent from grid: {row['condition_id']}")
        for field in ("ground_truth", "n_samples", "duration_s", "red_noise_alpha", "period_s", "qpp_fraction", "minimum_cycles"):
            if row[field] != design[field]:
                raise AnalysisError(
                    f"Design/manifest mismatch for {sid}, field {field}: {row[field]!r} != {design[field]!r}"
                )
        if not (0 <= row["data_seed"] <= 39):
            raise AnalysisError(f"Invalid data_seed in {sid}.")
        if raw["materialization_status"] != "OK" or raw["error"] != "":
            raise AnalysisError(f"Manifest row {sid} is not a valid frozen series.")
        rows.append(row)
        by_series[sid] = row
        by_condition_seed[key] = row
        condition_counts[row["condition_id"]] += 1
    if set(condition_counts.values()) != {40} or len(condition_counts) != 111:
        raise AnalysisError("Manifest does not contain exactly 40 series for each condition.")
    return rows, by_series, by_condition_seed


def connect_checkpoint(root: Path) -> sqlite3.Connection:
    path = root / "fase1_tarea05_full_checkpoint.sqlite"
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def load_sqlite_results(root: Path) -> tuple[list[dict[str, Any]], dict[str, str], list[dict[str, Any]]]:
    connection = connect_checkpoint(root)
    try:
        table_names = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if table_names != {"results", "invocations", "metadata", "sqlite_sequence"}:
            raise AnalysisError(f"Unexpected checkpoint tables: {sorted(table_names)}")
        results = [dict(row) for row in connection.execute("SELECT * FROM results ORDER BY job_order")]
        metadata = {
            row["key"]: row["value"]
            for row in connection.execute("SELECT key, value FROM metadata ORDER BY key")
        }
        invocations = [
            dict(row) for row in connection.execute(
                "SELECT * FROM invocations ORDER BY invocation_id"
            )
        ]
    finally:
        connection.close()
    if len(results) != EXPECTED_COUNTS["results"]:
        raise AnalysisError(f"SQLite contains {len(results)} result rows, not 16317.")
    if metadata.get("plan_kind") != "full":
        raise AnalysisError("Checkpoint plan_kind is not full.")
    if not invocations or invocations[0]["existing_before"] != 0:
        raise AnalysisError("Checkpoint invocation history did not begin at zero.")
    if invocations[-1]["total_after"] != EXPECTED_COUNTS["results"]:
        raise AnalysisError("Checkpoint invocation history does not end at 16317.")
    return results, metadata, invocations


def validate_execution_audit(root: Path) -> dict[str, Any]:
    audit = json.loads((root / "fase1_tarea05_full_execution_audit.json").read_text(encoding="utf-8"))
    if audit.get("execution_status") != "FULL_BENCHMARK_EXECUTION_COMPLETE":
        raise AnalysisError("F1.5 execution status is not complete.")
    execution = audit.get("execution", {})
    decisions = audit.get("decisions", {})
    checks = {
        "checkpoint_result_rows": EXPECTED_COUNTS["results"],
        "exported_result_rows": EXPECTED_COUNTS["results"],
        "pending_jobs": 0,
        "duplicate_job_ids": 0,
        "duplicate_scientific_keys": 0,
        "plan_result_metadata_mismatches": 0,
        "input_hash_mismatches": 0,
    }
    for key, expected in checks.items():
        if execution.get(key) != expected:
            raise AnalysisError(f"F1.5 audit mismatch for {key}: {execution.get(key)} != {expected}")
    if execution.get("status_counts") != {"OK": EXPECTED_COUNTS["results"]}:
        raise AnalysisError("F1.5 audit does not report all model calls as OK.")
    if decisions.get("decision_status_counts") != {"VALID": EXPECTED_COUNTS["decisions"]}:
        raise AnalysisError("F1.5 audit does not report all decisions as VALID.")
    confirmations = audit.get("confirmations", {})
    for key in (
        "runner_modified", "execution_plan_modified", "afino_code_modified",
        "dataset_modified", "dataset_regenerated", "canary_checkpoint_reused",
        "canary_results_imported", "jobs_removed", "failed_jobs_redrawn",
        "scientific_protocol_modified", "scientific_results_interpreted_during_execution",
    ):
        if confirmations.get(key) is not False:
            raise AnalysisError(f"Unexpected F1.5 confirmation value for {key}.")
    return audit


def normalize_csv_result(row: dict[str, str]) -> dict[str, Any]:
    normalized: dict[str, Any] = dict(row)
    for field in (
        "data_seed", "external_optimizer_seed", "n_samples",
        "positive_frequency_bins", "bins_after_cutoff", "warning_count",
    ):
        normalized[field] = parse_int(row[field], field)
    for field in (
        "runtime_seconds", "afino_effective_dt_s", "minimum_frequency_hz",
        "maximum_frequency_hz", "lnlike", "BIC", "rchi2", "probability",
    ):
        normalized[field] = parse_float(row[field], field)
    normalized["estimated_period_s"] = parse_optional_float(row["estimated_period_s"], "estimated_period_s")
    normalized["parameter_at_bound"] = parse_bool(row["parameter_at_bound"], "parameter_at_bound")
    return normalized


def compare_csv_and_sqlite(
    root: Path,
    sqlite_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], int]:
    fields, raw_rows = read_csv(root / "fase1_tarea05_core_results.csv")
    if fields != RESULT_CSV_FIELDS:
        raise AnalysisError("F1.5 results CSV schema differs from the frozen schema.")
    if len(raw_rows) != EXPECTED_COUNTS["results"]:
        raise AnalysisError(f"Results CSV contains {len(raw_rows)} rows, not 16317.")
    csv_rows = [normalize_csv_result(row) for row in raw_rows]
    if len({row["job_id"] for row in csv_rows}) != len(csv_rows):
        raise AnalysisError("Duplicate job_id values in results CSV.")
    scientific_keys = {
        (row["series_id"], row["external_optimizer_seed"], row["model_id"])
        for row in csv_rows
    }
    if len(scientific_keys) != len(csv_rows):
        raise AnalysisError("Duplicate scientific keys in results CSV.")
    sqlite_by_job = {row["job_id"]: row for row in sqlite_rows}
    if len(sqlite_by_job) != len(sqlite_rows):
        raise AnalysisError("Duplicate job_id values in SQLite.")
    mismatches = 0
    text_fields = {
        "job_class", "series_id", "condition_id", "ground_truth", "model_id",
        "model_name", "status", "input_flux_sha256", "input_time_sha256",
        "parameters_json", "bound_indices_json", "warning_types_json",
        "convergence_status", "error",
    }
    integer_fields = {
        "data_seed", "external_optimizer_seed", "n_samples",
        "positive_frequency_bins", "bins_after_cutoff", "warning_count",
    }
    float_fields = {
        "runtime_seconds", "afino_effective_dt_s", "minimum_frequency_hz",
        "maximum_frequency_hz", "lnlike", "BIC", "rchi2", "probability",
        "estimated_period_s",
    }
    for index, csv_row in enumerate(csv_rows, start=1):
        if csv_row["job_id"] != f"J{index:06d}":
            raise AnalysisError(f"Results CSV order is not canonical at row {index}.")
        sqlite_row = sqlite_by_job.get(csv_row["job_id"])
        if sqlite_row is None:
            raise AnalysisError(f"CSV job absent from SQLite: {csv_row['job_id']}")
        if sqlite_row["job_order"] != index:
            mismatches += 1
        for field in text_fields:
            if csv_row[field] != exact_optional_text(sqlite_row[field]):
                mismatches += 1
        for field in integer_fields:
            if csv_row[field] != int(sqlite_row[field]):
                mismatches += 1
        for field in float_fields:
            csv_value = csv_row[field]
            sqlite_value = sqlite_row[field]
            if csv_value is None or sqlite_value is None:
                if csv_value is not None or sqlite_value is not None:
                    mismatches += 1
            elif csv_value != float(sqlite_value):
                mismatches += 1
        if csv_row["parameter_at_bound"] != bool(sqlite_row["parameter_at_bound"]):
            mismatches += 1
        for field in ("parameters_json", "bound_indices_json", "warning_types_json"):
            validate_json_text(csv_row[field], f"{csv_row['job_id']}:{field}")
        if sqlite_row["bound_details_json"] is not None:
            validate_json_text(sqlite_row["bound_details_json"], f"{csv_row['job_id']}:bound_details_json")
        if sqlite_row["warnings_json"] is not None:
            validate_json_text(sqlite_row["warnings_json"], f"{csv_row['job_id']}:warnings_json")
        if csv_row["status"] != "OK" or csv_row["convergence_status"] != "NOT_AUDITABLE":
            raise AnalysisError(f"Non-valid model result in {csv_row['job_id']}.")
        if csv_row["error"] != "":
            raise AnalysisError(f"OK result has a non-empty error in {csv_row['job_id']}.")
    if mismatches:
        raise AnalysisError(f"SQLite/CSV mismatches: {mismatches}")
    by_job = {row["job_id"]: row for row in csv_rows}
    return csv_rows, by_job, mismatches


def load_and_recalculate_decisions(
    root: Path,
    results: list[dict[str, Any]],
    manifest_by_series: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[tuple[str, int], dict[str, Any]], int]:
    fields, raw_rows = read_csv(root / "fase1_tarea05_core_decisions.csv")
    if fields != DECISION_CSV_FIELDS:
        raise AnalysisError("F1.5 decisions CSV schema differs from the frozen schema.")
    if len(raw_rows) != EXPECTED_COUNTS["decisions"]:
        raise AnalysisError(f"Decisions CSV contains {len(raw_rows)} rows, not 5439.")
    decisions: list[dict[str, Any]] = []
    decision_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for raw in raw_rows:
        row: dict[str, Any] = dict(raw)
        for field in ("data_seed", "external_optimizer_seed", "valid_models"):
            row[field] = parse_int(raw[field], field)
        for field in ("delta_bic_0_1", "delta_bic_2_1", "estimated_period_s"):
            row[field] = parse_float(raw[field], field)
        row["qpp_selected"] = parse_bool(raw["qpp_selected"], "qpp_selected")
        key = (row["series_id"], row["external_optimizer_seed"])
        if key in decision_by_key:
            raise AnalysisError(f"Duplicate decision key: {key}")
        decisions.append(row)
        decision_by_key[key] = row
    grouped_results: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in results:
        key = (row["series_id"], row["external_optimizer_seed"])
        if row["model_id"] in grouped_results[key]:
            raise AnalysisError(f"Duplicate model within result trio: {key}, {row['model_id']}")
        grouped_results[key][row["model_id"]] = row
    if set(grouped_results) != set(decision_by_key):
        raise AnalysisError("Decision keys do not match result trios.")
    mismatches = 0
    for key, by_model in grouped_results.items():
        if set(by_model) != set(MODEL_IDS):
            raise AnalysisError(f"Incomplete model trio: {key}")
        decision = decision_by_key[key]
        manifest = manifest_by_series.get(key[0])
        if manifest is None:
            raise AnalysisError(f"Decision series absent from manifest: {key[0]}")
        if decision["decision_status"] != "VALID" or decision["valid_models"] != 3:
            raise AnalysisError(f"Non-valid decision in {key}")
        for field in ("condition_id", "ground_truth"):
            if decision[field] != manifest[field]:
                mismatches += 1
        if decision["data_seed"] != manifest["data_seed"]:
            mismatches += 1
        b0 = by_model["M0"]["BIC"]
        b1 = by_model["M1"]["BIC"]
        b2 = by_model["M2"]["BIC"]
        delta01 = b0 - b1
        delta21 = b2 - b1
        selected = delta01 > 10.0 and delta21 > 10.0
        if not float_equal(decision["delta_bic_0_1"], delta01, atol=ABS_TOLERANCE):
            mismatches += 1
        if not float_equal(decision["delta_bic_2_1"], delta21, atol=ABS_TOLERANCE):
            mismatches += 1
        if decision["qpp_selected"] != selected:
            mismatches += 1
        estimated = by_model["M1"]["estimated_period_s"]
        if estimated is None or not float_equal(decision["estimated_period_s"], estimated, atol=ABS_TOLERANCE):
            mismatches += 1
        expected_label = "recovered_period_selected" if selected else "formal_m1_center_not_selected"
        if decision["period_label"] != expected_label:
            mismatches += 1
        if decision["job_class"] == "primary":
            if key[1] != 0:
                mismatches += 1
        elif decision["job_class"] == "stability":
            if manifest["data_seed"] != 0 or not 1 <= key[1] <= 9:
                mismatches += 1
        else:
            mismatches += 1
    if mismatches:
        raise AnalysisError(f"Decision recalculation mismatches: {mismatches}")
    class_counts = Counter(row["job_class"] for row in decisions)
    if class_counts != {
        "primary": EXPECTED_COUNTS["primary_decisions"],
        "stability": EXPECTED_COUNTS["stability_decisions"],
    }:
        raise AnalysisError(f"Unexpected decision class counts: {class_counts}")
    return decisions, decision_by_key, mismatches


def verify_no_canary_provenance(
    execution_audit: dict[str, Any],
    checkpoint_metadata: dict[str, str],
    invocations: list[dict[str, Any]],
) -> None:
    confirmations = execution_audit["confirmations"]
    if confirmations["canary_checkpoint_reused"] or confirmations["canary_results_imported"]:
        raise AnalysisError("F1.5 reports canary reuse/import.")
    if checkpoint_metadata.get("plan_kind") != "full":
        raise AnalysisError("Checkpoint provenance is not the full plan.")
    if invocations[0]["existing_before"] != 0:
        raise AnalysisError("Full checkpoint did not start empty.")
    if checkpoint_metadata.get("plan_filename") != "fase1_tarea04_full_execution_plan.csv":
        raise AnalysisError("Checkpoint does not reference the frozen full execution plan.")
    prohibited_keys = {
        "canary_checkpoint_imported",
        "canary_results_imported",
        "canary_checkpoint_filename",
    }
    if prohibited_keys.intersection(checkpoint_metadata):
        raise AnalysisError("Checkpoint metadata contains canary import fields.")


def index_results(results: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, dict[str, Any]]]:
    indexed: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in results:
        indexed[(row["series_id"], row["external_optimizer_seed"])][row["model_id"]] = row
    return indexed


def build_primary_rows(
    decisions: list[dict[str, Any]],
    result_index: dict[tuple[str, int], dict[str, dict[str, Any]]],
    manifest_by_series: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for decision in decisions:
        if decision["job_class"] != "primary":
            continue
        manifest = manifest_by_series[decision["series_id"]]
        by_model = result_index[(decision["series_id"], 0)]
        delta_min = min(decision["delta_bic_0_1"], decision["delta_bic_2_1"])
        period_error = None
        period_absolute_error = None
        period_relative_error = None
        if manifest["ground_truth"] == POSITIVE_LABEL:
            true_period = manifest["period_s"]
            if true_period is None:
                raise AnalysisError(f"Positive series lacks a true period: {decision['series_id']}")
            period_error = decision["estimated_period_s"] - true_period
            period_absolute_error = abs(period_error)
            period_relative_error = 100.0 * period_error / true_period
        rows.append({
            "series_id": decision["series_id"],
            "condition_id": decision["condition_id"],
            "ground_truth": decision["ground_truth"],
            "n_samples": manifest["n_samples"],
            "duration_s": manifest["duration_s"],
            "red_noise_alpha": manifest["red_noise_alpha"],
            "period_s": manifest["period_s"],
            "qpp_fraction": manifest["qpp_fraction"],
            "nominal_window_cycles": manifest["minimum_cycles"],
            "data_seed": manifest["data_seed"],
            "external_optimizer_seed": 0,
            "decision_status": decision["decision_status"],
            "bic_m0": by_model["M0"]["BIC"],
            "bic_m1": by_model["M1"]["BIC"],
            "bic_m2": by_model["M2"]["BIC"],
            "delta_bic_0_1": decision["delta_bic_0_1"],
            "delta_bic_2_1": decision["delta_bic_2_1"],
            "delta_bic_min": delta_min,
            "qpp_selected": decision["qpp_selected"],
            "estimated_period_s": decision["estimated_period_s"],
            "period_label": decision["period_label"],
            "period_error_s": period_error,
            "period_absolute_error_s": period_absolute_error,
            "period_relative_error_percent": period_relative_error,
            "m0_parameter_at_bound": by_model["M0"]["parameter_at_bound"],
            "m1_parameter_at_bound": by_model["M1"]["parameter_at_bound"],
            "m2_parameter_at_bound": by_model["M2"]["parameter_at_bound"],
            "m0_warning_count": by_model["M0"]["warning_count"],
            "m1_warning_count": by_model["M1"]["warning_count"],
            "m2_warning_count": by_model["M2"]["warning_count"],
        })
    if len(rows) != EXPECTED_COUNTS["primary_decisions"]:
        raise AnalysisError(f"Primary analysis has {len(rows)} rows, not 4440.")
    return rows


def build_condition_summary(
    design_rows: list[dict[str, Any]],
    primary_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in primary_rows:
        grouped[row["condition_id"]].append(row)
    summaries: list[dict[str, Any]] = []
    for condition in design_rows:
        cid = condition["condition_id"]
        rows = grouped.get(cid, [])
        if len(rows) != 40:
            raise AnalysisError(f"Condition {cid} has {len(rows)} primary rows, not 40.")
        valid = [row for row in rows if row["decision_status"] == "VALID"]
        selected = [row for row in valid if row["qpp_selected"]]
        n_valid = len(valid)
        n_selected = len(selected)
        selection_rate = None if n_valid == 0 else n_selected / n_valid
        ci_lower, ci_upper = wilson_interval(n_selected, n_valid)
        is_positive = condition["ground_truth"] == POSITIVE_LABEL
        selected_period_errors = [row["period_error_s"] for row in selected] if is_positive else []
        selected_absolute_errors = [row["period_absolute_error_s"] for row in selected] if is_positive else []
        selected_relative_errors = [row["period_relative_error_percent"] for row in selected] if is_positive else []
        formal_period_errors = [row["period_error_s"] for row in valid] if is_positive else []
        formal_absolute_errors = [row["period_absolute_error_s"] for row in valid] if is_positive else []
        model_valid_denominator = {
            model: sum(1 for row in rows if row["decision_status"] == "VALID")
            for model in MODEL_IDS
        }
        summary = {
            "condition_id": cid,
            "ground_truth": condition["ground_truth"],
            "n_samples": condition["n_samples"],
            "duration_s": condition["duration_s"],
            "red_noise_alpha": condition["red_noise_alpha"],
            "period_s": condition["period_s"],
            "qpp_fraction": condition["qpp_fraction"],
            "nominal_window_cycles": condition["minimum_cycles"],
            "n_planned": 40,
            "n_valid": n_valid,
            "valid_run_rate": n_valid / 40.0,
            "n_selected": n_selected,
            "selection_rate": selection_rate,
            "selection_rate_ci95_lower": ci_lower,
            "selection_rate_ci95_upper": ci_upper,
            "rate_name": "synthetic_false_selection_rate" if not is_positive else "synthetic_detection_rate",
            "selected_period_n": n_selected if is_positive else None,
            "selected_period_median_signed_error_s": median(selected_period_errors),
            "selected_period_median_absolute_error_s": median(selected_absolute_errors),
            "selected_period_p90_absolute_error_s": quantile90(selected_absolute_errors),
            "selected_period_median_relative_error_percent": median(selected_relative_errors),
            "formal_m1_median_signed_error_s": median(formal_period_errors),
            "formal_m1_median_absolute_error_s": median(formal_absolute_errors),
            "formal_m1_p90_absolute_error_s": quantile90(formal_absolute_errors),
            "median_delta_bic_0_1": median([row["delta_bic_0_1"] for row in valid]),
            "median_delta_bic_2_1": median([row["delta_bic_2_1"] for row in valid]),
            "median_delta_bic_min": median([row["delta_bic_min"] for row in valid]),
            "m0_bound_hit_rate": sum(row["m0_parameter_at_bound"] for row in valid) / model_valid_denominator["M0"],
            "m1_bound_hit_rate": sum(row["m1_parameter_at_bound"] for row in valid) / model_valid_denominator["M1"],
            "m2_bound_hit_rate": sum(row["m2_parameter_at_bound"] for row in valid) / model_valid_denominator["M2"],
            "m0_warning_rate": sum(row["m0_warning_count"] > 0 for row in rows) / 40.0,
            "m1_warning_rate": sum(row["m1_warning_count"] > 0 for row in rows) / 40.0,
            "m2_warning_rate": sum(row["m2_warning_count"] > 0 for row in rows) / 40.0,
        }
        summaries.append(summary)
    if len(summaries) != EXPECTED_COUNTS["conditions"]:
        raise AnalysisError("Condition summary does not contain 111 rows.")
    return summaries


def verify_pairing(
    left_condition: str,
    right_condition: str,
    manifest_by_condition_seed: dict[tuple[str, int], dict[str, Any]],
) -> None:
    for data_seed in range(40):
        left = manifest_by_condition_seed[(left_condition, data_seed)]
        right = manifest_by_condition_seed[(right_condition, data_seed)]
        for field in (
            "n_samples", "red_noise_alpha", "data_seed", "block_id",
            "noise_sha256", "phase_float64_sha256", "phase_rad",
        ):
            if left[field] != right[field]:
                raise AnalysisError(
                    f"Invalid pairing {left_condition} vs {right_condition}, seed {data_seed}, field {field}"
                )


def contrast_row(
    contrast_type: str,
    left_condition: dict[str, Any],
    right_condition: dict[str, Any],
    primary_by_condition_seed: dict[tuple[str, int], dict[str, Any]],
    manifest_by_condition_seed: dict[tuple[str, int], dict[str, Any]],
) -> dict[str, Any]:
    left_id = left_condition["condition_id"]
    right_id = right_condition["condition_id"]
    verify_pairing(left_id, right_id, manifest_by_condition_seed)
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for data_seed in range(40):
        left = primary_by_condition_seed[(left_id, data_seed)]
        right = primary_by_condition_seed[(right_id, data_seed)]
        pairs.append((left, right))
    contingency = Counter((int(left["qpp_selected"]), int(right["qpp_selected"])) for left, right in pairs)
    left_rate = sum(left["qpp_selected"] for left, _ in pairs) / 40.0
    right_rate = sum(right["qpp_selected"] for _, right in pairs) / 40.0
    changes = [right["delta_bic_min"] - left["delta_bic_min"] for left, right in pairs]
    return {
        "contrast_type": contrast_type,
        "left_condition_id": left_id,
        "right_condition_id": right_id,
        "n_samples": left_condition["n_samples"],
        "red_noise_alpha": left_condition["red_noise_alpha"],
        "left_period_s": left_condition["period_s"],
        "right_period_s": right_condition["period_s"],
        "left_qpp_fraction": left_condition["qpp_fraction"],
        "right_qpp_fraction": right_condition["qpp_fraction"],
        "n_pairs": 40,
        "left_selection_rate": left_rate,
        "right_selection_rate": right_rate,
        "paired_selection_difference": right_rate - left_rate,
        "n_left0_right0": contingency[(0, 0)],
        "n_left0_right1": contingency[(0, 1)],
        "n_left1_right0": contingency[(1, 0)],
        "n_left1_right1": contingency[(1, 1)],
        "median_paired_change_delta_bic_min": median(changes),
    }


def build_paired_contrasts(
    design_rows: list[dict[str, Any]],
    primary_rows: list[dict[str, Any]],
    manifest_by_condition_seed: dict[tuple[str, int], dict[str, Any]],
) -> list[dict[str, Any]]:
    design_by_id = {row["condition_id"]: row for row in design_rows}
    primary_by_condition_seed = {
        (row["condition_id"], row["data_seed"]): row for row in primary_rows
    }
    null_lookup = {
        (row["n_samples"], row["red_noise_alpha"]): row
        for row in design_rows if row["ground_truth"] == NULL_LABEL
    }
    positive_rows = [row for row in design_rows if row["ground_truth"] == POSITIVE_LABEL]
    positive_lookup = {
        (row["n_samples"], row["period_s"], row["red_noise_alpha"], row["qpp_fraction"]): row
        for row in positive_rows
    }
    contrasts: list[dict[str, Any]] = []
    for positive in positive_rows:
        null = null_lookup[(positive["n_samples"], positive["red_noise_alpha"])]
        contrasts.append(contrast_row(
            "qpp_vs_null", null, positive, primary_by_condition_seed, manifest_by_condition_seed
        ))
    for n_samples in sorted({row["n_samples"] for row in positive_rows}):
        periods = sorted({row["period_s"] for row in positive_rows if row["n_samples"] == n_samples})
        for period_s in periods:
            for alpha in sorted({row["red_noise_alpha"] for row in positive_rows}):
                conditions = {
                    q: positive_lookup[(n_samples, period_s, alpha, q)]
                    for q in (0.01, 0.02, 0.04)
                }
                for left_q, right_q in ((0.01, 0.02), (0.02, 0.04), (0.01, 0.04)):
                    contrasts.append(contrast_row(
                        "amplitude", conditions[left_q], conditions[right_q],
                        primary_by_condition_seed, manifest_by_condition_seed
                    ))
    for n_samples in sorted({row["n_samples"] for row in positive_rows}):
        periods = sorted({row["period_s"] for row in positive_rows if row["n_samples"] == n_samples})
        for alpha in sorted({row["red_noise_alpha"] for row in positive_rows}):
            for qpp_fraction in (0.01, 0.02, 0.04):
                for left_period, right_period in combinations(periods, 2):
                    left = positive_lookup[(n_samples, left_period, alpha, qpp_fraction)]
                    right = positive_lookup[(n_samples, right_period, alpha, qpp_fraction)]
                    contrasts.append(contrast_row(
                        "period", left, right, primary_by_condition_seed, manifest_by_condition_seed
                    ))
    counts = Counter(row["contrast_type"] for row in contrasts)
    if counts != {"qpp_vs_null": 99, "amplitude": 99, "period": 90}:
        raise AnalysisError(f"Unexpected paired contrast counts: {counts}")
    if len(contrasts) != EXPECTED_COUNTS["paired_contrasts"]:
        raise AnalysisError("Paired contrast table does not contain 288 rows.")
    return contrasts


def build_optimizer_stability(
    design_rows: list[dict[str, Any]],
    decision_by_key: dict[tuple[str, int], dict[str, Any]],
    result_index: dict[tuple[str, int], dict[str, dict[str, Any]]],
    manifest_by_condition_seed: dict[tuple[str, int], dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for condition in design_rows:
        cid = condition["condition_id"]
        series = manifest_by_condition_seed[(cid, 0)]
        sid = series["series_id"]
        decisions = [decision_by_key[(sid, seed)] for seed in range(10)]
        if any(decision["decision_status"] != "VALID" for decision in decisions):
            raise AnalysisError(f"Invalid optimizer decision in condition {cid}.")
        selected = [decision["qpp_selected"] for decision in decisions]
        n_valid = len(selected)
        n_selected = sum(selected)
        n_not_selected = n_valid - n_selected
        discordance = None if n_valid < 2 else (
            2.0 * n_selected * n_not_selected / (n_valid * (n_valid - 1))
        )
        model_bics = {
            model: [result_index[(sid, seed)][model]["BIC"] for seed in range(10)]
            for model in MODEL_IDS
        }
        model_bound_counts = {
            model: sum(result_index[(sid, seed)][model]["parameter_at_bound"] for seed in range(10))
            for model in MODEL_IDS
        }
        model_warning_counts = {
            model: sum(result_index[(sid, seed)][model]["warning_count"] > 0 for seed in range(10))
            for model in MODEL_IDS
        }
        formal_periods = [decision["estimated_period_s"] for decision in decisions]
        selected_periods = [
            decision["estimated_period_s"] for decision in decisions if decision["qpp_selected"]
        ]
        m2_range = numeric_range(model_bics["M2"])
        rows.append({
            "condition_id": cid,
            "series_id": sid,
            "ground_truth": condition["ground_truth"],
            "n_samples": condition["n_samples"],
            "red_noise_alpha": condition["red_noise_alpha"],
            "period_s": condition["period_s"],
            "qpp_fraction": condition["qpp_fraction"],
            "n_valid_optimizer_seeds": n_valid,
            "n_selected_optimizer_seeds": n_selected,
            "optimizer_seed_decision_discordance": discordance,
            "any_decision_change": n_selected > 0 and n_not_selected > 0,
            "m0_bic_range": numeric_range(model_bics["M0"]),
            "m1_bic_range": numeric_range(model_bics["M1"]),
            "m2_bic_range": m2_range,
            "m2_multiple_solution_flag": bool(m2_range is not None and m2_range > 0.001),
            "formal_m1_period_range_s": numeric_range(formal_periods),
            "selected_period_range_s": numeric_range(selected_periods),
            "m0_bound_seed_count": model_bound_counts["M0"],
            "m1_bound_seed_count": model_bound_counts["M1"],
            "m2_bound_seed_count": model_bound_counts["M2"],
            "m0_warning_seed_count": model_warning_counts["M0"],
            "m1_warning_seed_count": model_warning_counts["M1"],
            "m2_warning_seed_count": model_warning_counts["M2"],
        })
    if len(rows) != EXPECTED_COUNTS["conditions"]:
        raise AnalysisError("Optimizer stability table does not contain 111 rows.")
    return rows


def diagnostic_row(
    analysis_scope: str,
    grouping: str,
    n_samples: int | None,
    model_id: str,
    calls: list[dict[str, Any]],
) -> dict[str, Any]:
    runtimes = [row["runtime_seconds"] for row in calls]
    warning_calls = sum(row["warning_count"] > 0 for row in calls)
    bound_calls = sum(row["parameter_at_bound"] for row in calls)
    return {
        "analysis_scope": analysis_scope,
        "grouping": grouping,
        "n_samples": n_samples,
        "model_id": model_id,
        "calls": len(calls),
        "ok_calls": sum(row["status"] == "OK" for row in calls),
        "warning_calls": warning_calls,
        "warning_total": sum(row["warning_count"] for row in calls),
        "bound_hit_calls": bound_calls,
        "warning_rate": warning_calls / len(calls),
        "bound_hit_rate": bound_calls / len(calls),
        "runtime_total_seconds": sum(runtimes),
        "runtime_median_seconds": median(runtimes),
    }


def build_model_diagnostics(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scope in ("primary", "stability"):
        scoped = [row for row in results if row["job_class"] == scope]
        for model in MODEL_IDS:
            calls = [row for row in scoped if row["model_id"] == model]
            rows.append(diagnostic_row(scope, "global", None, model, calls))
        for n_samples in (15, 30, 60, 120):
            for model in MODEL_IDS:
                calls = [
                    row for row in scoped
                    if row["n_samples"] == n_samples and row["model_id"] == model
                ]
                rows.append(diagnostic_row(scope, "by_n_samples", n_samples, model, calls))
    if len(rows) != EXPECTED_COUNTS["model_diagnostics"]:
        raise AnalysisError("Model diagnostics do not contain 30 rows.")
    return rows


def create_figures(
    output_dir: Path,
    condition_rows: list[dict[str, Any]],
    primary_rows: list[dict[str, Any]],
    stability_rows: list[dict[str, Any]],
    diagnostic_rows: list[dict[str, Any]],
) -> None:
    null_rows = [row for row in condition_rows if row["ground_truth"] == NULL_LABEL]
    labels = [f"N={row['n_samples']}, alpha={int(row['red_noise_alpha'])}" for row in null_rows]
    rates = np.asarray([row["selection_rate"] for row in null_rows], dtype=float)
    lower = np.asarray([row["selection_rate_ci95_lower"] for row in null_rows], dtype=float)
    upper = np.asarray([row["selection_rate_ci95_upper"] for row in null_rows], dtype=float)
    y = np.arange(len(null_rows))
    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    ax.errorbar(rates, y, xerr=np.vstack([rates - lower, upper - rates]), fmt="o", capsize=3)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0.0, max(0.10, float(max(upper)) * 1.15))
    ax.set_xlabel("Synthetic false selection rate (Wilson 95% interval)")
    ax.set_title("Null conditions: synthetic selection of M1")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "fase1_tarea06_fig01_null_false_selection.png", dpi=180)
    plt.close(fig)

    positive = [row for row in condition_rows if row["ground_truth"] == POSITIVE_LABEL]
    strata_keys = sorted(
        {(row["n_samples"], row["period_s"], row["red_noise_alpha"]) for row in positive},
        key=lambda item: (item[0], item[1], item[2]),
    )
    amplitudes = (0.01, 0.02, 0.04)
    lookup = {
        (row["n_samples"], row["period_s"], row["red_noise_alpha"], row["qpp_fraction"]): row
        for row in positive
    }
    matrix = np.asarray([
        [lookup[(n, p, a, q)]["selection_rate"] for q in amplitudes]
        for n, p, a in strata_keys
    ], dtype=float)
    fig, ax = plt.subplots(figsize=(7.5, 13.5))
    image = ax.imshow(matrix, aspect="auto", vmin=0.0, vmax=1.0)
    ax.set_xticks(np.arange(3), ["q=0.01", "q=0.02", "q=0.04"])
    ax.set_yticks(
        np.arange(len(strata_keys)),
        [f"N={n}, P={int(p)} s, alpha={int(a)}" for n, p, a in strata_keys],
        fontsize=7,
    )
    ax.set_title("Synthetic detection rate by complete positive-condition stratum")
    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label("Synthetic detection rate")
    fig.tight_layout()
    fig.savefig(output_dir / "fase1_tarea06_fig02_positive_detection_grid.png", dpi=180)
    plt.close(fig)

    positive_primary = [row for row in primary_rows if row["ground_truth"] == POSITIVE_LABEL]
    data: list[list[float]] = []
    period_labels: list[str] = []
    for period in (50.0, 80.0, 140.0):
        selected_abs = [
            row["period_absolute_error_s"] for row in positive_primary
            if row["period_s"] == period and row["qpp_selected"]
        ]
        formal_abs = [
            row["period_absolute_error_s"] for row in positive_primary
            if row["period_s"] == period
        ]
        data.extend([selected_abs, formal_abs])
        period_labels.extend([f"P={int(period)} selected", f"P={int(period)} formal M1"])
    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    ax.boxplot(data, tick_labels=period_labels, showfliers=False)
    ax.set_yscale("log")
    ax.set_ylabel("Absolute period error (s, logarithmic scale)")
    ax.set_title("Selected periods versus formal M1 centers in positive runs")
    ax.tick_params(axis="x", rotation=25)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "fase1_tarea06_fig03_period_error.png", dpi=180)
    plt.close(fig)

    m2_ranges = [row["m2_bic_range"] for row in stability_rows]
    m2_flag_count = sum(row["m2_multiple_solution_flag"] for row in stability_rows)
    decision_change_count = sum(row["any_decision_change"] for row in stability_rows)
    fig, ax = plt.subplots(figsize=(8.5, 5.8))
    ax.hist(m2_ranges, bins=24)
    ax.axvline(0.001, linestyle="--", label="M2 flag threshold = 0.001")
    ax.set_xlabel("M2 BIC range across optimizer seeds 0-9")
    ax.set_ylabel("Conditions")
    ax.set_title(
        f"Optimizer audit: decision changes {decision_change_count}/111; "
        f"M2 flags {m2_flag_count}/111"
    )
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "fase1_tarea06_fig04_optimizer_stability.png", dpi=180)
    plt.close(fig)

    global_diagnostics = [row for row in diagnostic_rows if row["grouping"] == "global"]
    labels = [f"{row['analysis_scope']} {row['model_id']}" for row in global_diagnostics]
    warning_rates = [row["warning_rate"] for row in global_diagnostics]
    bound_rates = [row["bound_hit_rate"] for row in global_diagnostics]
    x = np.arange(len(labels))
    width = 0.38
    fig, ax = plt.subplots(figsize=(10.5, 6.0))
    ax.bar(x - width / 2, warning_rates, width, label="warning rate")
    ax.bar(x + width / 2, bound_rates, width, label="bound-hit rate")
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("Fraction of calls")
    ax.set_title("Numerical diagnostics kept separate for primary and stability calls")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "fase1_tarea06_fig05_numerical_diagnostics.png", dpi=180)
    plt.close(fig)


def rate_text(rate: float) -> str:
    return f"{100.0 * rate:.1f}%"


def build_report(
    condition_rows: list[dict[str, Any]],
    primary_rows: list[dict[str, Any]],
    paired_rows: list[dict[str, Any]],
    stability_rows: list[dict[str, Any]],
    diagnostic_rows: list[dict[str, Any]],
) -> str:
    null_rows = [row for row in condition_rows if row["ground_truth"] == NULL_LABEL]
    positive_rows = [row for row in condition_rows if row["ground_truth"] == POSITIVE_LABEL]
    null_selected = sum(row["n_selected"] for row in null_rows)
    positive_rates = [row["selection_rate"] for row in positive_rows]
    positive_nonzero = [row for row in positive_rows if row["n_selected"] > 0]
    positive_zero = [row for row in positive_rows if row["n_selected"] == 0]
    max_rows = [row for row in positive_rows if row["selection_rate"] == max(positive_rates)]

    amplitude_rows = [row for row in paired_rows if row["contrast_type"] == "amplitude"]
    amplitude_signs = Counter(
        "positive" if row["paired_selection_difference"] > 0 else
        "negative" if row["paired_selection_difference"] < 0 else "zero"
        for row in amplitude_rows
    )
    condition_lookup = {row["condition_id"]: row for row in condition_rows}
    amplitude_triplets: dict[tuple[int, float, float], dict[float, float]] = defaultdict(dict)
    for row in positive_rows:
        amplitude_triplets[(row["n_samples"], row["period_s"], row["red_noise_alpha"])][row["qpp_fraction"]] = row["selection_rate"]
    monotonic_non_decreasing = 0
    monotonic_strict = 0
    for rates in amplitude_triplets.values():
        ordered = [rates[q] for q in (0.01, 0.02, 0.04)]
        monotonic_non_decreasing += ordered[0] <= ordered[1] <= ordered[2]
        monotonic_strict += ordered[0] < ordered[1] < ordered[2]

    period_rows = [row for row in paired_rows if row["contrast_type"] == "period"]
    period_signs = Counter(
        "positive" if row["paired_selection_difference"] > 0 else
        "negative" if row["paired_selection_difference"] < 0 else "zero"
        for row in period_rows
    )

    selected_positive = [row for row in primary_rows if row["ground_truth"] == POSITIVE_LABEL and row["qpp_selected"]]
    nonselected_positive = [row for row in primary_rows if row["ground_truth"] == POSITIVE_LABEL and not row["qpp_selected"]]
    all_positive = [row for row in primary_rows if row["ground_truth"] == POSITIVE_LABEL]
    selected_signed = [row["period_error_s"] for row in selected_positive]
    selected_abs = [row["period_absolute_error_s"] for row in selected_positive]
    selected_rel = [row["period_relative_error_percent"] for row in selected_positive]
    formal_signed = [row["period_error_s"] for row in all_positive]
    formal_abs = [row["period_absolute_error_s"] for row in all_positive]
    nonselected_abs = [row["period_absolute_error_s"] for row in nonselected_positive]

    decision_change_count = sum(row["any_decision_change"] for row in stability_rows)
    m2_flag_count = sum(row["m2_multiple_solution_flag"] for row in stability_rows)
    largest_m2 = sorted(stability_rows, key=lambda row: row["m2_bic_range"], reverse=True)[:3]

    diagnostics = {
        (row["analysis_scope"], row["model_id"]): row
        for row in diagnostic_rows if row["grouping"] == "global"
    }
    primary_m0 = diagnostics[("primary", "M0")]
    primary_m1 = diagnostics[("primary", "M1")]
    primary_m2 = diagnostics[("primary", "M2")]
    stability_m2 = diagnostics[("stability", "M2")]
    by_n = {
        (row["analysis_scope"], row["n_samples"], row["model_id"]): row
        for row in diagnostic_rows if row["grouping"] == "by_n_samples"
    }

    null_table = "\n".join(
        f"| {int(row['n_samples'])} | {int(row['red_noise_alpha'])} | "
        f"{row['n_selected']}/40 | {rate_text(row['selection_rate'])} | "
        f"[{rate_text(row['selection_rate_ci95_lower'])}, {rate_text(row['selection_rate_ci95_upper'])}] |"
        for row in null_rows
    )
    upper_examples = sorted(positive_rows, key=lambda row: (-row["selection_rate"], row["condition_id"]))[:8]
    upper_table = "\n".join(
        f"| {row['condition_id']} | {int(row['n_samples'])} | {int(row['period_s'])} | "
        f"{int(row['red_noise_alpha'])} | {row['qpp_fraction']:.2f} | "
        f"{row['n_selected']}/40 | {rate_text(row['selection_rate'])} |"
        for row in upper_examples
    )
    m2_table = "\n".join(
        f"| {row['condition_id']} | {row['m2_bic_range']:.6f} | "
        f"{row['n_selected_optimizer_seeds']}/10 |"
        for row in largest_m2
    )

    report = f"""# Fase 1 — Tarea 1.6

## Auditoría y análisis prerregistrado del benchmark núcleo

**Estado:** `CORE_BENCHMARK_ANALYSIS_COMPLETE`

## 1. Alcance e integridad

El análisis utilizó exclusivamente los resultados completos congelados en F1.5. Se compararon las 16.317 filas del CSV con SQLite, incluidos identificadores, metadatos, estados, likelihood, BIC y parámetros. Se recalcularon las 5.439 decisiones con tolerancia absoluta de `5e-12` y tolerancia relativa cero. No hubo discrepancias, duplicados ni decisiones inválidas. El checkpoint, los resultados y las decisiones conservaron sus hashes antes y después. AFINO no se ejecutó y no se incorporó el canary.

Los términos de este informe son deliberadamente sintéticos: `synthetic false selection` y `synthetic detection` describen únicamente este generador y este protocolo. El rendimiento observacional no se estima y la verdad física de QPP no queda establecida.

## 2. Selección sintética en nulos

M1 no fue seleccionado en ninguna de las 480 realizaciones nulas primarias: **{null_selected}/480**. Cada una de las doce condiciones tuvo 0/40 selecciones. Los intervalos de Wilson son descriptivos y no constituyen una corrección por multiplicidad ni una prueba de hipótesis.

| N | alpha | Seleccionadas | Tasa sintética | Wilson 95% |
|---:|---:|---:|---:|---:|
{null_table}

Este resultado es una tasa de selección sintética bajo el nulo construido; no es una tasa observacional de falsos positivos.

## 3. Detección sintética en positivos

Las 99 condiciones positivas abarcaron tasas entre **{rate_text(min(positive_rates))}** y **{rate_text(max(positive_rates))}**, con mediana por condición de **{rate_text(float(np.median(positive_rates)))}**. Hubo {len(positive_zero)} condiciones con 0/40 y {len(positive_nonzero)} con al menos una selección. No se asigna una categoría de éxito o fracaso porque F1.1 no fijó un umbral global.

En el extremo inferior, todas las condiciones con N=15 y N=30 quedaron en 0/40. Con N=60 solo aparecieron selecciones para P=50 s y q=0.04: 2/40 con alpha=0, 7/40 con alpha=1 y 20/40 con alpha=2. Con N=120 apareció el dominio de mayor selección: los periodos de 50 y 80 s alcanzaron 40/40 en varias combinaciones de amplitud y pendiente, mientras que P=140 s solo produjo selecciones con q=0.04, desde 7/40 hasta 27/40 según alpha. Las comparaciones de N y alpha son descriptivas y totalmente estratificadas; no son contrastes emparejados porque usan bloques de ruido distintos.

| Condición en el extremo superior | N | P (s) | alpha | q | Seleccionadas | Tasa |
|---|---:|---:|---:|---:|---:|---:|
{upper_table}

La amplitud mostró un patrón no decreciente en los **{monotonic_non_decreasing}/33** estratos completos (N, P, alpha). Solo {monotonic_strict}/33 aumentaron estrictamente en los tres pasos, porque muchas tasas permanecieron empatadas en cero o saturadas. Entre los 99 contrastes emparejados de amplitud, {amplitude_signs['positive']} tuvieron diferencia positiva, {amplitude_signs['zero']} diferencia cero y {amplitude_signs['negative']} negativa. Por tanto, no se observó una reversión de la tasa al aumentar q dentro de los bloques compartidos.

Para periodo, la diferencia se definió como periodo largo menos periodo corto. De los 90 contrastes, {period_signs['negative']} fueron negativos, {period_signs['zero']} cero y {period_signs['positive']} positivos. En las regiones donde existió detección, los periodos más cortos fueron iguales o más favorables. La figura 2 conserva la estratificación completa y evita una tasa marginal ingenua por N; N=15 no incluye P=140 s.

## 4. Periodo seleccionado y centro formal de M1

M1 fue seleccionado en {len(selected_positive)} de las 3.960 ejecuciones positivas primarias. Entre esas selecciones, el error firmado mediano fue **{median(selected_signed):.3f} s**, el error absoluto mediano **{median(selected_abs):.3f} s**, el percentil 90 del error absoluto **{quantile90(selected_abs):.3f} s** y el error relativo firmado mediano **{median(selected_rel):.3f}%**.

Al considerar el centro formal de M1 en todas las ejecuciones positivas válidas, incluidas las no seleccionadas, el error firmado mediano fue **{median(formal_signed):.3f} s**, el absoluto mediano **{median(formal_abs):.3f} s** y su percentil 90 **{quantile90(formal_abs):.3f} s**. En las {len(nonselected_positive)} ejecuciones no seleccionadas, el error absoluto mediano fue {median(nonselected_abs):.3f} s. La diferencia es grande: el centro de M1 está mucho mejor localizado cuando el modelo supera ambos umbrales BIC. Fuera de esa selección se conserva la etiqueta `formal_m1_center_not_selected`; no se denomina periodo recuperado.

## 5. Semilla del optimizador y multiplicidad de M2

Ninguna de las 111 condiciones cambió su decisión binaria entre las semillas externas 0–9. En consecuencia, `optimizer_seed_decision_discordance` fue cero en todas las condiciones. Esta estabilidad de clasificación no implica unicidad numérica: **{m2_flag_count}/111** condiciones superaron el criterio prerregistrado `M2_BIC_range > 0.001`.

| Mayores rangos de BIC de M2 | Rango | Semillas seleccionadas |
|---|---:|---:|
{m2_table}

El indicador de M2 señala multiplicidad según el criterio operativo de BIC; no establece por sí solo soluciones físicas distintas.

## 6. Bounds, warnings y fallos numéricos

No hubo fallos numéricos: las 16.317 llamadas fueron `OK` y las 5.439 decisiones `VALID`. En las 4.440 llamadas primarias por modelo, M0 tuvo {primary_m0['bound_hit_calls']} bounds ({rate_text(primary_m0['bound_hit_rate'])}), M1 {primary_m1['bound_hit_calls']} ({rate_text(primary_m1['bound_hit_rate'])}) y M2 {primary_m2['bound_hit_calls']} ({rate_text(primary_m2['bound_hit_rate'])}). Los warnings se concentraron exclusivamente en M2: {primary_m2['warning_calls']} llamadas primarias ({rate_text(primary_m2['warning_rate'])}) y {stability_m2['warning_calls']} de estabilidad ({rate_text(stability_m2['warning_rate'])}).

Por tamaño, los bounds primarios de M1 aumentaron desde {rate_text(by_n[('primary', 15, 'M1')]['bound_hit_rate'])} en N=15 hasta {rate_text(by_n[('primary', 120, 'M1')]['bound_hit_rate'])} en N=120. Los warnings primarios de M2 fueron más frecuentes en N=60 ({rate_text(by_n[('primary', 60, 'M2')]['warning_rate'])}) y N=120 ({rate_text(by_n[('primary', 120, 'M2')]['warning_rate'])}). Estos diagnósticos deben acompañar la interpretación de BIC y periodos, pero no invalidan automáticamente una llamada `OK`.

## 7. Dominio de funcionamiento y límites

Dentro de este generador, la selección sintética fue nula en los doce nulos y se concentró en positivos con ventanas largas, amplitudes mayores y periodos más cortos. La amplitud fue no decreciente en todos los estratos emparejados, mientras que ampliar el periodo nunca mejoró la tasa en los contrastes observados. La decisión fue estable frente a la semilla externa, aunque M2 mostró variación de BIC en la mayoría de condiciones y los bounds de M1 fueron frecuentes.

Estas conclusiones son válidas únicamente para flares sintéticos con QPP estacionaria, ruido rojo generado por el procedimiento congelado, cadencia de 20 s, grid y protocolo AFINO prerregistrados. No estiman desempeño en curvas TESS reales, no prueban la presencia física de QPP y no autorizan extrapolaciones a otras envolventes, damping, gaps, detrending o distribuciones de ruido.

## Conclusión

`CORE_BENCHMARK_ANALYSIS_COMPLETE`
"""
    return report


def validate_output_rows(
    primary_rows: list[dict[str, Any]],
    condition_rows: list[dict[str, Any]],
    paired_rows: list[dict[str, Any]],
    stability_rows: list[dict[str, Any]],
    diagnostic_rows: list[dict[str, Any]],
) -> None:
    expected = {
        "primary": (len(primary_rows), 4440),
        "condition": (len(condition_rows), 111),
        "paired": (len(paired_rows), 288),
        "stability": (len(stability_rows), 111),
        "diagnostics": (len(diagnostic_rows), 30),
    }
    for name, (observed, target) in expected.items():
        if observed != target:
            raise AnalysisError(f"{name} row count mismatch: {observed} != {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit and analyze the frozen F1.5 core benchmark.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output-dir", type=Path, default=None)
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    output_dir = (arguments.output_dir or root).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    script_path = Path(__file__).resolve()
    ensure_output_directory_clean(output_dir, script_path)

    pre_hashes = verify_input_hashes(root)
    prereg = load_preregistration(root)
    design_rows, design_by_id = load_design(root)
    _, manifest_by_series, manifest_by_condition_seed = load_manifest(root, design_by_id)
    execution_audit = validate_execution_audit(root)
    sqlite_rows, checkpoint_metadata, invocations = load_sqlite_results(root)
    results, _, sqlite_csv_mismatches = compare_csv_and_sqlite(root, sqlite_rows)
    decisions, decision_by_key, decision_mismatches = load_and_recalculate_decisions(
        root, results, manifest_by_series
    )
    verify_no_canary_provenance(execution_audit, checkpoint_metadata, invocations)

    result_index = index_results(results)
    primary_rows = build_primary_rows(decisions, result_index, manifest_by_series)
    condition_rows = build_condition_summary(design_rows, primary_rows)
    paired_rows = build_paired_contrasts(
        design_rows, primary_rows, manifest_by_condition_seed
    )
    stability_rows = build_optimizer_stability(
        design_rows, decision_by_key, result_index, manifest_by_condition_seed
    )
    diagnostic_rows = build_model_diagnostics(results)
    validate_output_rows(primary_rows, condition_rows, paired_rows, stability_rows, diagnostic_rows)

    write_csv(output_dir / OUTPUT_NAMES[0], PRIMARY_FIELDS, primary_rows)
    write_csv(output_dir / OUTPUT_NAMES[1], CONDITION_FIELDS, condition_rows)
    write_csv(output_dir / OUTPUT_NAMES[2], PAIRED_FIELDS, paired_rows)
    write_csv(output_dir / OUTPUT_NAMES[3], STABILITY_FIELDS, stability_rows)
    write_csv(output_dir / OUTPUT_NAMES[4], DIAGNOSTIC_FIELDS, diagnostic_rows)
    create_figures(output_dir, condition_rows, primary_rows, stability_rows, diagnostic_rows)

    report_path = output_dir / "fase1_tarea06_core_benchmark_analysis.md"
    report_path.write_text(
        build_report(condition_rows, primary_rows, paired_rows, stability_rows, diagnostic_rows),
        encoding="utf-8",
    )

    post_hashes = verify_input_hashes(root)
    if pre_hashes != post_hashes:
        raise AnalysisError("One or more frozen inputs changed during F1.6.")

    analysis_output_names = [name for name in OUTPUT_NAMES if name != "fase1_tarea06_analysis_audit.json"]
    output_hashes = {
        name: sha256(output_dir / name) for name in analysis_output_names
    }
    output_hashes["fase1_tarea06_analyze_core_benchmark.py"] = sha256(script_path)

    amplitude_signs = Counter(
        "positive" if row["paired_selection_difference"] > 0 else
        "negative" if row["paired_selection_difference"] < 0 else "zero"
        for row in paired_rows if row["contrast_type"] == "amplitude"
    )
    period_signs = Counter(
        "positive" if row["paired_selection_difference"] > 0 else
        "negative" if row["paired_selection_difference"] < 0 else "zero"
        for row in paired_rows if row["contrast_type"] == "period"
    )
    null_rows = [row for row in condition_rows if row["ground_truth"] == NULL_LABEL]
    positive_rows = [row for row in condition_rows if row["ground_truth"] == POSITIVE_LABEL]
    selected_positive = [row for row in primary_rows if row["ground_truth"] == POSITIVE_LABEL and row["qpp_selected"]]
    audit = {
        "generated_at_utc": utc_now(),
        "execution_status": "CORE_BENCHMARK_ANALYSIS_COMPLETE",
        "analysis_protocol": {
            "decision_abs_tolerance": ABS_TOLERANCE,
            "decision_relative_tolerance": REL_TOLERANCE,
            "wilson_z": WILSON_Z,
            "quantile_method": "linear",
            "m2_multiple_solution_threshold": 0.001,
        },
        "environment": {
            "python_version": platform.python_version(),
            "python_full": sys.version,
            "platform": platform.platform(),
            "numpy_version": np.__version__,
            "matplotlib_version": matplotlib.__version__,
        },
        "input_hashes_pre": pre_hashes,
        "input_hashes_post": post_hashes,
        "preflight": {
            "f1_1_preregistration_status": prereg["preregistration_status"],
            "f1_5_execution_status": execution_audit["execution_status"],
            "results": len(results),
            "decisions": len(decisions),
            "all_model_statuses_ok": all(row["status"] == "OK" for row in results),
            "all_decision_statuses_valid": all(row["decision_status"] == "VALID" for row in decisions),
            "canary_provenance_absent": True,
        },
        "independent_audit": {
            "sqlite_csv_mismatches": sqlite_csv_mismatches,
            "decision_recalculation_mismatches": decision_mismatches,
            "duplicate_result_job_ids": len(results) - len({row["job_id"] for row in results}),
            "duplicate_result_scientific_keys": len(results) - len({
                (row["series_id"], row["external_optimizer_seed"], row["model_id"])
                for row in results
            }),
            "duplicate_decision_keys": len(decisions) - len({
                (row["series_id"], row["external_optimizer_seed"])
                for row in decisions
            }),
            "primary_valid_decisions": sum(
                row["job_class"] == "primary" and row["decision_status"] == "VALID"
                for row in decisions
            ),
            "stability_valid_decisions": sum(
                row["job_class"] == "stability" and row["decision_status"] == "VALID"
                for row in decisions
            ),
        },
        "output_row_counts": {
            "primary_series_rows": len(primary_rows),
            "condition_summary_rows": len(condition_rows),
            "paired_contrast_rows": len(paired_rows),
            "optimizer_stability_rows": len(stability_rows),
            "model_diagnostic_rows": len(diagnostic_rows),
        },
        "descriptive_results": {
            "null_selected": sum(row["n_selected"] for row in null_rows),
            "null_planned": sum(row["n_planned"] for row in null_rows),
            "positive_condition_rate_min": min(row["selection_rate"] for row in positive_rows),
            "positive_condition_rate_median": float(np.median([row["selection_rate"] for row in positive_rows])),
            "positive_condition_rate_max": max(row["selection_rate"] for row in positive_rows),
            "positive_selected_primary_runs": len(selected_positive),
            "amplitude_contrast_difference_signs": dict(amplitude_signs),
            "period_contrast_difference_signs": dict(period_signs),
            "optimizer_conditions_with_decision_change": sum(row["any_decision_change"] for row in stability_rows),
            "m2_multiple_solution_conditions": sum(row["m2_multiple_solution_flag"] for row in stability_rows),
        },
        "output_hashes": output_hashes,
        "confirmations": {
            "afino_executed": False,
            "raw_results_modified": False,
            "raw_decisions_modified": False,
            "checkpoint_modified": False,
            "series_removed": False,
            "conditions_removed": False,
            "post_result_thresholds_added": False,
            "canary_included": False,
            "unbalanced_marginal_rates_presented": False,
            "observational_performance_claimed": False,
        },
    }
    audit_path = output_dir / "fase1_tarea06_analysis_audit.json"
    audit_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    print("F1.6 analysis complete")
    print("execution_status: CORE_BENCHMARK_ANALYSIS_COMPLETE")
    print(f"primary_series_rows: {len(primary_rows)}")
    print(f"condition_summary_rows: {len(condition_rows)}")
    print(f"paired_contrast_rows: {len(paired_rows)}")
    print(f"optimizer_stability_rows: {len(stability_rows)}")
    print(f"model_diagnostic_rows: {len(diagnostic_rows)}")
    print(f"primary_valid_decisions: {audit['independent_audit']['primary_valid_decisions']}")
    print(f"stability_valid_decisions: {audit['independent_audit']['stability_valid_decisions']}")
    print(f"decision_recalculation_mismatches: {decision_mismatches}")
    print(f"sqlite_csv_mismatches: {sqlite_csv_mismatches}")
    print(f"audit: {audit_path.name}")
    print(f"report: {report_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
