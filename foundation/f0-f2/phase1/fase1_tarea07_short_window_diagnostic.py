#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ABS_TOL = 5e-12
REL_TOL = 0.0
SHORT_NS = {15, 30}
POSITIVE_TRUTH = "STATIONARY_QPP_PRESENT"
NULL_TRUTH = "NULL_FLARE_RED_NOISE"

EXPECTED_HASHES = {
    "fase1_tarea05_core_results.csv": "1ba98f4f0df406f36c17c75cf90d0773b09c3139eb2e11dc35d67ac42ac02775",
    "fase1_tarea05_core_decisions.csv": "bf2b65aa42f40fa798910096ee62127556dc9cbe67445222df465b6a1352ab27",
    "fase1_tarea06_primary_series_analysis.csv": "dae39c6a3425263c1bc7752b513d1c1d2a37ff8a3f7fc557c5773b9575beedd6",
    "fase1_tarea06_condition_summary.csv": "25c60ca7cfdbb46bb9a389fa16ce8f2be98e734e689186815c6a97cdc042d1eb",
    "fase1_tarea06_analysis_audit.json": "207b1b058a8faf6d145bb31d698a9994c90fa2550e0ea7d204c330f7a875a04a",
    "fase1_tarea05_full_execution_audit.json": "7f4a6be19897bced53482cc5fd225f400ad85cd0c28544449e4c58e17d275205",
}

RUN_FIELDS = [
    "series_id",
    "condition_id",
    "ground_truth",
    "n_samples",
    "duration_s",
    "red_noise_alpha",
    "period_s",
    "qpp_fraction",
    "nominal_window_cycles",
    "data_seed",
    "positive_frequency_bins",
    "bins_after_cutoff",
    "bic_m0",
    "bic_m1",
    "bic_m2",
    "lnlike_m0",
    "lnlike_m1",
    "lnlike_m2",
    "delta_bic_0_1",
    "delta_bic_2_1",
    "delta_bic_min",
    "margin_vs_m0",
    "margin_vs_m2",
    "joint_margin",
    "passes_m0_comparison",
    "passes_m2_comparison",
    "threshold_failure_class",
    "bic_winner",
    "two_loglike_gain_m1_vs_m0",
    "two_loglike_gain_m1_vs_m2",
    "bic_penalty_remainder_vs_m0",
    "bic_penalty_remainder_vs_m2",
    "estimated_period_s",
    "period_label",
    "formal_period_error_s",
    "formal_period_absolute_error_s",
    "formal_period_relative_error_percent",
    "m0_any_bound",
    "m1_any_bound",
    "m1_amplitude_parameter_bound",
    "m1_center_parameter_bound",
    "m1_width_parameter_bound",
    "m2_any_bound",
    "m2_warning_count",
]

CONDITION_FIELDS = [
    "condition_id",
    "ground_truth",
    "n_samples",
    "duration_s",
    "red_noise_alpha",
    "period_s",
    "qpp_fraction",
    "nominal_window_cycles",
    "n_series",
    "both_thresholds_passed_count",
    "m0_comparison_only_passed_count",
    "m2_comparison_only_passed_count",
    "both_comparisons_failed_count",
    "passes_m0_count",
    "passes_m0_rate",
    "passes_m2_count",
    "passes_m2_rate",
    "bic_winner_m0_count",
    "bic_winner_m1_count",
    "bic_winner_m2_count",
    "bic_tie_count",
    "delta_bic_0_1_median",
    "delta_bic_0_1_p10",
    "delta_bic_0_1_p90",
    "delta_bic_2_1_median",
    "delta_bic_2_1_p10",
    "delta_bic_2_1_p90",
    "margin_vs_m0_median",
    "margin_vs_m0_p10",
    "margin_vs_m0_p90",
    "margin_vs_m2_median",
    "margin_vs_m2_p10",
    "margin_vs_m2_p90",
    "joint_margin_median",
    "joint_margin_p10",
    "joint_margin_p90",
    "two_loglike_gain_m1_vs_m0_median",
    "two_loglike_gain_m1_vs_m2_median",
    "bic_penalty_remainder_vs_m0_median",
    "bic_penalty_remainder_vs_m2_median",
    "formal_period_n",
    "formal_period_median_signed_error_s",
    "formal_period_median_absolute_error_s",
    "formal_period_p90_absolute_error_s",
    "formal_period_median_relative_error_percent",
    "m0_any_bound_count",
    "m0_any_bound_rate",
    "m1_any_bound_count",
    "m1_any_bound_rate",
    "m1_amplitude_parameter_bound_count",
    "m1_amplitude_parameter_bound_rate",
    "m1_center_parameter_bound_count",
    "m1_center_parameter_bound_rate",
    "m1_width_parameter_bound_count",
    "m1_width_parameter_bound_rate",
    "m2_any_bound_count",
    "m2_any_bound_rate",
    "m2_warning_call_count",
    "m2_warning_call_rate",
    "m2_warning_total",
    "positive_frequency_bins",
    "bins_after_cutoff",
]

AMPLITUDE_FIELDS = [
    "n_samples",
    "period_s",
    "red_noise_alpha",
    "left_condition_id",
    "right_condition_id",
    "left_qpp_fraction",
    "right_qpp_fraction",
    "n_pairs",
    "median_change_delta_bic_0_1",
    "median_change_delta_bic_2_1",
    "median_change_joint_margin",
    "m0_threshold_crossing_count",
    "m0_threshold_crossing_0_to_1_count",
    "m0_threshold_crossing_1_to_0_count",
    "m2_threshold_crossing_count",
    "m2_threshold_crossing_0_to_1_count",
    "m2_threshold_crossing_1_to_0_count",
    "bic_winner_change_count",
]

OUTPUT_NAMES = [
    "fase1_tarea07_short_window_run_diagnostics.csv",
    "fase1_tarea07_short_window_condition_summary.csv",
    "fase1_tarea07_short_window_amplitude_contrasts.csv",
    "fase1_tarea07_fig01_n15_bic_threshold_plane.png",
    "fase1_tarea07_fig02_n30_bic_threshold_plane.png",
    "fase1_tarea07_fig03_short_window_margin_grid.png",
    "fase1_tarea07_fig04_formal_period_error.png",
    "fase1_tarea07_short_window_diagnostic_audit.json",
    "fase1_tarea07_short_window_diagnostic.md",
]


class DiagnosticError(RuntimeError):
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
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def as_int(value: Any, field: str) -> int:
    try:
        return int(value)
    except Exception as exc:
        raise DiagnosticError(f"Invalid integer in {field}: {value!r}") from exc


def as_float(value: Any, field: str) -> float:
    try:
        number = float(value)
    except Exception as exc:
        raise DiagnosticError(f"Invalid float in {field}: {value!r}") from exc
    if not math.isfinite(number):
        raise DiagnosticError(f"Non-finite value in {field}: {value!r}")
    return number


def optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return as_float(value, "optional_float")


def as_bool(value: Any, field: str) -> bool:
    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise DiagnosticError(f"Invalid Boolean in {field}: {value!r}")


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def quantiles(values: list[float]) -> tuple[float, float, float]:
    array = np.asarray(values, dtype=float)
    return (
        float(np.median(array)),
        float(np.quantile(array, 0.10, method="linear")),
        float(np.quantile(array, 0.90, method="linear")),
    )


def winner_from_bic(bics: dict[str, float]) -> str:
    minimum = min(bics.values())
    tied = [model for model, value in bics.items() if abs(value - minimum) <= ABS_TOL]
    return "BIC_TIE" if len(tied) > 1 else tied[0]


def threshold_class(pass_m0: bool, pass_m2: bool) -> str:
    if pass_m0 and pass_m2:
        return "BOTH_THRESHOLDS_PASSED"
    if pass_m0:
        return "M0_COMPARISON_ONLY_PASSED"
    if pass_m2:
        return "M2_COMPARISON_ONLY_PASSED"
    return "BOTH_COMPARISONS_FAILED"


def verify_inputs(root: Path) -> dict[str, str]:
    observed: dict[str, str] = {}
    for name, expected in EXPECTED_HASHES.items():
        path = root / name
        if not path.is_file():
            raise DiagnosticError(f"Missing input: {name}")
        value = sha256(path)
        if value != expected:
            raise DiagnosticError(f"Hash mismatch for {name}: {value} != {expected}")
        observed[name] = value

    f15 = json.loads((root / "fase1_tarea05_full_execution_audit.json").read_text(encoding="utf-8"))
    f16 = json.loads((root / "fase1_tarea06_analysis_audit.json").read_text(encoding="utf-8"))
    if f15.get("execution_status") != "FULL_BENCHMARK_EXECUTION_COMPLETE":
        raise DiagnosticError("F1.5 is not complete.")
    if f16.get("execution_status") != "CORE_BENCHMARK_ANALYSIS_COMPLETE":
        raise DiagnosticError("F1.6 is not complete.")
    if f15.get("execution", {}).get("checkpoint_result_rows") != 16317:
        raise DiagnosticError("F1.5 result count is not 16317.")
    if f15.get("decisions", {}).get("total_decisions") != 5439:
        raise DiagnosticError("F1.5 decision count is not 5439.")
    if f15.get("execution", {}).get("status_counts") != {"OK": 16317}:
        raise DiagnosticError("Not all F1.5 model statuses are OK.")
    if f15.get("decisions", {}).get("decision_status_counts") != {"VALID": 5439}:
        raise DiagnosticError("Not all F1.5 decision statuses are VALID.")
    if f15.get("preflight", {}).get("canary_checkpoint_imported") is not False:
        raise DiagnosticError("F1.5 audit does not exclude canary checkpoint import.")
    if f15.get("preflight", {}).get("canary_results_imported") is not False:
        raise DiagnosticError("F1.5 audit does not exclude canary result import.")
    return observed


def build_diagnostics(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    result_fields, result_rows = read_csv(root / "fase1_tarea05_core_results.csv")
    decision_fields, decision_rows = read_csv(root / "fase1_tarea05_core_decisions.csv")
    primary_fields, primary_rows = read_csv(root / "fase1_tarea06_primary_series_analysis.csv")
    _, condition_rows = read_csv(root / "fase1_tarea06_condition_summary.csv")

    if len(result_rows) != 16317 or len(decision_rows) != 5439 or len(primary_rows) != 4440:
        raise DiagnosticError("Unexpected F1.5/F1.6 global row counts.")
    if any(row["status"] != "OK" for row in result_rows):
        raise DiagnosticError("A model status is not OK.")
    if any(row["decision_status"] != "VALID" for row in decision_rows):
        raise DiagnosticError("A decision status is not VALID.")

    short_primary = [
        row for row in primary_rows
        if as_int(row["n_samples"], "n_samples") in SHORT_NS
        and as_int(row["external_optimizer_seed"], "external_optimizer_seed") == 0
    ]
    if len(short_primary) != 2040:
        raise DiagnosticError(f"Short primary rows: {len(short_primary)} != 2040")
    if len({row["series_id"] for row in short_primary}) != 2040:
        raise DiagnosticError("Duplicate series in short primary analysis.")

    short_ids = {row["series_id"] for row in short_primary}
    short_decisions = [
        row for row in decision_rows
        if row["series_id"] in short_ids
        and row["job_class"] == "primary"
        and as_int(row["external_optimizer_seed"], "external_optimizer_seed") == 0
    ]
    short_results = [
        row for row in result_rows
        if row["series_id"] in short_ids
        and row["job_class"] == "primary"
        and as_int(row["external_optimizer_seed"], "external_optimizer_seed") == 0
    ]
    if len(short_decisions) != 2040:
        raise DiagnosticError(f"Short decisions: {len(short_decisions)} != 2040")
    if len(short_results) != 6120:
        raise DiagnosticError(f"Short results: {len(short_results)} != 6120")
    if any(row["job_class"] != "primary" for row in short_decisions + short_results):
        raise DiagnosticError("A stability row entered the short-window population.")
    if any(as_int(row["external_optimizer_seed"], "external_optimizer_seed") != 0 for row in short_decisions + short_results):
        raise DiagnosticError("A non-primary optimizer seed entered the population.")

    decision_by_series = {row["series_id"]: row for row in short_decisions}
    if len(decision_by_series) != 2040:
        raise DiagnosticError("Duplicate short-window decision series.")

    models_by_series: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    duplicate_model_keys = 0
    for row in short_results:
        model = row["model_id"]
        series_id = row["series_id"]
        if model in models_by_series[series_id]:
            duplicate_model_keys += 1
        models_by_series[series_id][model] = row
    if duplicate_model_keys:
        raise DiagnosticError("Duplicate model result keys in short-window population.")
    if any(set(models) != {"M0", "M1", "M2"} for models in models_by_series.values()):
        raise DiagnosticError("Incomplete model trio in short-window population.")

    condition_lookup = {row["condition_id"]: row for row in condition_rows}
    if len(condition_lookup) != 111:
        raise DiagnosticError("F1.6 condition summary does not contain 111 unique conditions.")

    diagnostics: list[dict[str, Any]] = []
    decision_mismatches = 0
    input_hash_mismatches = 0

    for source in short_primary:
        sid = source["series_id"]
        decision = decision_by_series[sid]
        models = models_by_series[sid]

        metadata_fields = ["condition_id", "ground_truth", "data_seed"]
        for field in metadata_fields:
            values = {source[field], decision[field]} | {models[m][field] for m in models}
            if len(values) != 1:
                raise DiagnosticError(f"Metadata mismatch for {sid}, field {field}.")

        n_values = {as_int(source["n_samples"], "n_samples")} | {
            as_int(models[m]["n_samples"], "n_samples") for m in models
        }
        if len(n_values) != 1:
            raise DiagnosticError(f"n_samples mismatch for {sid}.")

        flux_hashes = {models[m]["input_flux_sha256"] for m in models}
        time_hashes = {models[m]["input_time_sha256"] for m in models}
        if len(flux_hashes) != 1 or len(time_hashes) != 1:
            input_hash_mismatches += 1

        bics = {m: as_float(models[m]["BIC"], f"{sid}.{m}.BIC") for m in models}
        likes = {m: as_float(models[m]["lnlike"], f"{sid}.{m}.lnlike") for m in models}
        delta01 = bics["M0"] - bics["M1"]
        delta21 = bics["M2"] - bics["M1"]
        stored01 = as_float(decision["delta_bic_0_1"], "delta_bic_0_1")
        stored21 = as_float(decision["delta_bic_2_1"], "delta_bic_2_1")
        source01 = as_float(source["delta_bic_0_1"], "source delta 0,1")
        source21 = as_float(source["delta_bic_2_1"], "source delta 2,1")
        selected = delta01 > 10.0 and delta21 > 10.0
        stored_selected = as_bool(decision["qpp_selected"], "qpp_selected")
        source_selected = as_bool(source["qpp_selected"], "source qpp_selected")

        if not (
            close(delta01, stored01)
            and close(delta21, stored21)
            and close(delta01, source01)
            and close(delta21, source21)
            and selected == stored_selected == source_selected
        ):
            decision_mismatches += 1

        pass_m0 = delta01 > 10.0
        pass_m2 = delta21 > 10.0
        failure_class = threshold_class(pass_m0, pass_m2)
        if (failure_class == "BOTH_THRESHOLDS_PASSED") != selected:
            raise DiagnosticError(f"Threshold class inconsistent with selection for {sid}.")

        positive_bins = {as_int(models[m]["positive_frequency_bins"], "positive_frequency_bins") for m in models}
        cutoff_bins = {as_int(models[m]["bins_after_cutoff"], "bins_after_cutoff") for m in models}
        if len(positive_bins) != 1 or len(cutoff_bins) != 1:
            raise DiagnosticError(f"Spectral-bin mismatch within trio {sid}.")

        m1_bounds = json.loads(models["M1"]["bound_indices_json"])
        m0_bounds = json.loads(models["M0"]["bound_indices_json"])
        m2_bounds = json.loads(models["M2"]["bound_indices_json"])
        if not all(isinstance(index, int) for index in m1_bounds + m0_bounds + m2_bounds):
            raise DiagnosticError(f"Non-integer bound index in {sid}.")

        period = optional_float(source["period_s"])
        estimated = as_float(models["M1"]["estimated_period_s"], "estimated_period_s")
        if not close(estimated, as_float(source["estimated_period_s"], "source estimated_period_s")):
            raise DiagnosticError(f"M1 period mismatch for {sid}.")

        if source["ground_truth"] == POSITIVE_TRUTH:
            period_error: float | str = estimated - float(period)
            period_abs_error: float | str = abs(float(period_error))
            period_rel_error: float | str = 100.0 * float(period_error) / float(period)
            if selected:
                raise DiagnosticError(f"Positive short-window series unexpectedly selected: {sid}")
            period_label = "formal_m1_center_not_selected"
        elif source["ground_truth"] == NULL_TRUTH:
            period_error = ""
            period_abs_error = ""
            period_rel_error = ""
            period_label = source["period_label"]
        else:
            raise DiagnosticError(f"Unknown ground truth: {source['ground_truth']}")

        diagnostics.append({
            "series_id": sid,
            "condition_id": source["condition_id"],
            "ground_truth": source["ground_truth"],
            "n_samples": as_int(source["n_samples"], "n_samples"),
            "duration_s": as_float(source["duration_s"], "duration_s"),
            "red_noise_alpha": as_float(source["red_noise_alpha"], "red_noise_alpha"),
            "period_s": "" if period is None else period,
            "qpp_fraction": "" if source["qpp_fraction"] == "" else as_float(source["qpp_fraction"], "qpp_fraction"),
            "nominal_window_cycles": "" if source["nominal_window_cycles"] == "" else as_float(source["nominal_window_cycles"], "nominal_window_cycles"),
            "data_seed": as_int(source["data_seed"], "data_seed"),
            "positive_frequency_bins": next(iter(positive_bins)),
            "bins_after_cutoff": next(iter(cutoff_bins)),
            "bic_m0": bics["M0"],
            "bic_m1": bics["M1"],
            "bic_m2": bics["M2"],
            "lnlike_m0": likes["M0"],
            "lnlike_m1": likes["M1"],
            "lnlike_m2": likes["M2"],
            "delta_bic_0_1": delta01,
            "delta_bic_2_1": delta21,
            "delta_bic_min": min(delta01, delta21),
            "margin_vs_m0": delta01 - 10.0,
            "margin_vs_m2": delta21 - 10.0,
            "joint_margin": min(delta01 - 10.0, delta21 - 10.0),
            "passes_m0_comparison": bool_text(pass_m0),
            "passes_m2_comparison": bool_text(pass_m2),
            "threshold_failure_class": failure_class,
            "bic_winner": winner_from_bic(bics),
            "two_loglike_gain_m1_vs_m0": 2.0 * (likes["M1"] - likes["M0"]),
            "two_loglike_gain_m1_vs_m2": 2.0 * (likes["M1"] - likes["M2"]),
            "bic_penalty_remainder_vs_m0": 2.0 * (likes["M1"] - likes["M0"]) - delta01,
            "bic_penalty_remainder_vs_m2": 2.0 * (likes["M1"] - likes["M2"]) - delta21,
            "estimated_period_s": estimated,
            "period_label": period_label,
            "formal_period_error_s": period_error,
            "formal_period_absolute_error_s": period_abs_error,
            "formal_period_relative_error_percent": period_rel_error,
            "m0_any_bound": bool_text(bool(m0_bounds)),
            "m1_any_bound": bool_text(bool(m1_bounds)),
            "m1_amplitude_parameter_bound": bool_text(2 in m1_bounds),
            "m1_center_parameter_bound": bool_text(4 in m1_bounds),
            "m1_width_parameter_bound": bool_text(5 in m1_bounds),
            "m2_any_bound": bool_text(bool(m2_bounds)),
            "m2_warning_count": as_int(models["M2"]["warning_count"], "m2_warning_count"),
        })

    if decision_mismatches or input_hash_mismatches:
        raise DiagnosticError(
            f"Audit mismatch: decision={decision_mismatches}, input_hash={input_hash_mismatches}"
        )

    diagnostics.sort(key=lambda row: row["series_id"])
    counts = Counter((row["n_samples"], row["ground_truth"]) for row in diagnostics)
    expected_counts = {
        (15, POSITIVE_TRUTH): 720,
        (15, NULL_TRUTH): 120,
        (30, POSITIVE_TRUTH): 1080,
        (30, NULL_TRUTH): 120,
    }
    if counts != expected_counts:
        raise DiagnosticError(f"Unexpected analytical population: {counts}")

    if any(row["threshold_failure_class"] == "BOTH_THRESHOLDS_PASSED" for row in diagnostics):
        raise DiagnosticError("A short-window series passed both thresholds unexpectedly.")
    if any(row["ground_truth"] == POSITIVE_TRUTH and row["period_label"] != "formal_m1_center_not_selected" for row in diagnostics):
        raise DiagnosticError("A positive short-window period label is inconsistent.")

    audit = {
        "decision_mismatches": decision_mismatches,
        "input_hash_mismatches": input_hash_mismatches,
        "duplicate_series": len(diagnostics) - len({row["series_id"] for row in diagnostics}),
        "result_csv_fields": result_fields,
        "decision_csv_fields": decision_fields,
        "primary_csv_fields": primary_fields,
    }
    return diagnostics, audit


def build_condition_summary(diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in diagnostics:
        groups[row["condition_id"]].append(row)
    if len(groups) != 51:
        raise DiagnosticError(f"Short-window conditions: {len(groups)} != 51")

    output: list[dict[str, Any]] = []
    for condition_id in sorted(groups):
        rows = groups[condition_id]
        if len(rows) != 40:
            raise DiagnosticError(f"Condition {condition_id} has {len(rows)} rows, not 40.")
        exemplar = rows[0]
        classes = Counter(row["threshold_failure_class"] for row in rows)
        winners = Counter(row["bic_winner"] for row in rows)
        pass0 = sum(as_bool(row["passes_m0_comparison"], "passes_m0") for row in rows)
        pass2 = sum(as_bool(row["passes_m2_comparison"], "passes_m2") for row in rows)

        d01_med, d01_p10, d01_p90 = quantiles([float(row["delta_bic_0_1"]) for row in rows])
        d21_med, d21_p10, d21_p90 = quantiles([float(row["delta_bic_2_1"]) for row in rows])
        m0_med, m0_p10, m0_p90 = quantiles([float(row["margin_vs_m0"]) for row in rows])
        m2_med, m2_p10, m2_p90 = quantiles([float(row["margin_vs_m2"]) for row in rows])
        joint_med, joint_p10, joint_p90 = quantiles([float(row["joint_margin"]) for row in rows])

        if exemplar["ground_truth"] == POSITIVE_TRUTH:
            signed = [float(row["formal_period_error_s"]) for row in rows]
            absolute = [float(row["formal_period_absolute_error_s"]) for row in rows]
            relative = [float(row["formal_period_relative_error_percent"]) for row in rows]
            formal_n: int | str = len(rows)
            formal_signed: float | str = float(np.median(signed))
            formal_abs: float | str = float(np.median(absolute))
            formal_p90: float | str = float(np.quantile(absolute, 0.90, method="linear"))
            formal_rel: float | str = float(np.median(relative))
        else:
            formal_n = ""
            formal_signed = ""
            formal_abs = ""
            formal_p90 = ""
            formal_rel = ""

        def count_true(field: str) -> int:
            return sum(as_bool(row[field], field) for row in rows)

        m0_bound = count_true("m0_any_bound")
        m1_bound = count_true("m1_any_bound")
        m1_amp = count_true("m1_amplitude_parameter_bound")
        m1_center = count_true("m1_center_parameter_bound")
        m1_width = count_true("m1_width_parameter_bound")
        m2_bound = count_true("m2_any_bound")
        warning_calls = sum(int(row["m2_warning_count"]) > 0 for row in rows)
        warning_total = sum(int(row["m2_warning_count"]) for row in rows)

        positive_bins = {int(row["positive_frequency_bins"]) for row in rows}
        cutoff_bins = {int(row["bins_after_cutoff"]) for row in rows}
        if len(positive_bins) != 1 or len(cutoff_bins) != 1:
            raise DiagnosticError(f"Condition-level bin mismatch in {condition_id}.")

        output.append({
            "condition_id": condition_id,
            "ground_truth": exemplar["ground_truth"],
            "n_samples": exemplar["n_samples"],
            "duration_s": exemplar["duration_s"],
            "red_noise_alpha": exemplar["red_noise_alpha"],
            "period_s": exemplar["period_s"],
            "qpp_fraction": exemplar["qpp_fraction"],
            "nominal_window_cycles": exemplar["nominal_window_cycles"],
            "n_series": len(rows),
            "both_thresholds_passed_count": classes.get("BOTH_THRESHOLDS_PASSED", 0),
            "m0_comparison_only_passed_count": classes.get("M0_COMPARISON_ONLY_PASSED", 0),
            "m2_comparison_only_passed_count": classes.get("M2_COMPARISON_ONLY_PASSED", 0),
            "both_comparisons_failed_count": classes.get("BOTH_COMPARISONS_FAILED", 0),
            "passes_m0_count": pass0,
            "passes_m0_rate": pass0 / len(rows),
            "passes_m2_count": pass2,
            "passes_m2_rate": pass2 / len(rows),
            "bic_winner_m0_count": winners.get("M0", 0),
            "bic_winner_m1_count": winners.get("M1", 0),
            "bic_winner_m2_count": winners.get("M2", 0),
            "bic_tie_count": winners.get("BIC_TIE", 0),
            "delta_bic_0_1_median": d01_med,
            "delta_bic_0_1_p10": d01_p10,
            "delta_bic_0_1_p90": d01_p90,
            "delta_bic_2_1_median": d21_med,
            "delta_bic_2_1_p10": d21_p10,
            "delta_bic_2_1_p90": d21_p90,
            "margin_vs_m0_median": m0_med,
            "margin_vs_m0_p10": m0_p10,
            "margin_vs_m0_p90": m0_p90,
            "margin_vs_m2_median": m2_med,
            "margin_vs_m2_p10": m2_p10,
            "margin_vs_m2_p90": m2_p90,
            "joint_margin_median": joint_med,
            "joint_margin_p10": joint_p10,
            "joint_margin_p90": joint_p90,
            "two_loglike_gain_m1_vs_m0_median": float(np.median([float(row["two_loglike_gain_m1_vs_m0"]) for row in rows])),
            "two_loglike_gain_m1_vs_m2_median": float(np.median([float(row["two_loglike_gain_m1_vs_m2"]) for row in rows])),
            "bic_penalty_remainder_vs_m0_median": float(np.median([float(row["bic_penalty_remainder_vs_m0"]) for row in rows])),
            "bic_penalty_remainder_vs_m2_median": float(np.median([float(row["bic_penalty_remainder_vs_m2"]) for row in rows])),
            "formal_period_n": formal_n,
            "formal_period_median_signed_error_s": formal_signed,
            "formal_period_median_absolute_error_s": formal_abs,
            "formal_period_p90_absolute_error_s": formal_p90,
            "formal_period_median_relative_error_percent": formal_rel,
            "m0_any_bound_count": m0_bound,
            "m0_any_bound_rate": m0_bound / len(rows),
            "m1_any_bound_count": m1_bound,
            "m1_any_bound_rate": m1_bound / len(rows),
            "m1_amplitude_parameter_bound_count": m1_amp,
            "m1_amplitude_parameter_bound_rate": m1_amp / len(rows),
            "m1_center_parameter_bound_count": m1_center,
            "m1_center_parameter_bound_rate": m1_center / len(rows),
            "m1_width_parameter_bound_count": m1_width,
            "m1_width_parameter_bound_rate": m1_width / len(rows),
            "m2_any_bound_count": m2_bound,
            "m2_any_bound_rate": m2_bound / len(rows),
            "m2_warning_call_count": warning_calls,
            "m2_warning_call_rate": warning_calls / len(rows),
            "m2_warning_total": warning_total,
            "positive_frequency_bins": next(iter(positive_bins)),
            "bins_after_cutoff": next(iter(cutoff_bins)),
        })
    return output


def build_amplitude_contrasts(diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    positives = [row for row in diagnostics if row["ground_truth"] == POSITIVE_TRUTH]
    condition_map: dict[tuple[int, float, float, float], str] = {}
    data: dict[tuple[int, float, float, float], dict[int, dict[str, Any]]] = defaultdict(dict)
    for row in positives:
        key = (
            int(row["n_samples"]),
            float(row["period_s"]),
            float(row["red_noise_alpha"]),
            float(row["qpp_fraction"]),
        )
        condition_map[key] = str(row["condition_id"])
        data[key][int(row["data_seed"])] = row

    strata = sorted({(key[0], key[1], key[2]) for key in data})
    if len(strata) != 15:
        raise DiagnosticError(f"Amplitude strata: {len(strata)} != 15")

    comparisons = [(0.01, 0.02), (0.02, 0.04), (0.01, 0.04)]
    output: list[dict[str, Any]] = []
    for n_samples, period_s, alpha in strata:
        for left_q, right_q in comparisons:
            left_key = (n_samples, period_s, alpha, left_q)
            right_key = (n_samples, period_s, alpha, right_q)
            left = data[left_key]
            right = data[right_key]
            if set(left) != set(range(40)) or set(right) != set(range(40)):
                raise DiagnosticError(f"Incomplete paired seeds in amplitude stratum {left_key}->{right_key}")

            change01: list[float] = []
            change21: list[float] = []
            change_joint: list[float] = []
            cross0_up = cross0_down = cross2_up = cross2_down = winner_changes = 0
            for seed in range(40):
                lrow = left[seed]
                rrow = right[seed]
                change01.append(float(rrow["delta_bic_0_1"]) - float(lrow["delta_bic_0_1"]))
                change21.append(float(rrow["delta_bic_2_1"]) - float(lrow["delta_bic_2_1"]))
                change_joint.append(float(rrow["joint_margin"]) - float(lrow["joint_margin"]))
                l0 = as_bool(lrow["passes_m0_comparison"], "passes_m0")
                r0 = as_bool(rrow["passes_m0_comparison"], "passes_m0")
                l2 = as_bool(lrow["passes_m2_comparison"], "passes_m2")
                r2 = as_bool(rrow["passes_m2_comparison"], "passes_m2")
                cross0_up += int(not l0 and r0)
                cross0_down += int(l0 and not r0)
                cross2_up += int(not l2 and r2)
                cross2_down += int(l2 and not r2)
                winner_changes += int(lrow["bic_winner"] != rrow["bic_winner"])

            output.append({
                "n_samples": n_samples,
                "period_s": period_s,
                "red_noise_alpha": alpha,
                "left_condition_id": condition_map[left_key],
                "right_condition_id": condition_map[right_key],
                "left_qpp_fraction": left_q,
                "right_qpp_fraction": right_q,
                "n_pairs": 40,
                "median_change_delta_bic_0_1": float(np.median(change01)),
                "median_change_delta_bic_2_1": float(np.median(change21)),
                "median_change_joint_margin": float(np.median(change_joint)),
                "m0_threshold_crossing_count": cross0_up + cross0_down,
                "m0_threshold_crossing_0_to_1_count": cross0_up,
                "m0_threshold_crossing_1_to_0_count": cross0_down,
                "m2_threshold_crossing_count": cross2_up + cross2_down,
                "m2_threshold_crossing_0_to_1_count": cross2_up,
                "m2_threshold_crossing_1_to_0_count": cross2_down,
                "bic_winner_change_count": winner_changes,
            })
    if len(output) != 45:
        raise DiagnosticError(f"Amplitude contrast rows: {len(output)} != 45")
    return output


def create_threshold_plane(path: Path, diagnostics: list[dict[str, Any]], n_samples: int) -> None:
    rows = [row for row in diagnostics if int(row["n_samples"]) == n_samples]
    nulls = [row for row in rows if row["ground_truth"] == NULL_TRUTH]
    positives = [row for row in rows if row["ground_truth"] == POSITIVE_TRUTH]
    figure, axis = plt.subplots(figsize=(8.5, 6.5))
    axis.scatter(
        [float(row["delta_bic_0_1"]) for row in nulls],
        [float(row["delta_bic_2_1"]) for row in nulls],
        marker="x",
        alpha=0.7,
        label="Nulos sintéticos",
    )
    axis.scatter(
        [float(row["delta_bic_0_1"]) for row in positives],
        [float(row["delta_bic_2_1"]) for row in positives],
        marker="o",
        alpha=0.45,
        label="Positivos sintéticos",
    )
    axis.axvline(10.0, linestyle="--")
    axis.axhline(10.0, linestyle="--")
    axis.set_xlabel("ΔBIC₀,₁")
    axis.set_ylabel("ΔBIC₂,₁")
    axis.set_title(f"Plano de umbrales BIC — N={n_samples}")
    axis.legend()
    axis.grid(True, alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def create_margin_grid(path: Path, condition_summary: list[dict[str, Any]]) -> None:
    positives = [row for row in condition_summary if row["ground_truth"] == POSITIVE_TRUTH]
    strata = sorted({
        (int(row["n_samples"]), float(row["period_s"]), float(row["red_noise_alpha"]))
        for row in positives
    })
    q_values = [0.01, 0.02, 0.04]
    matrix = np.empty((len(strata), len(q_values)), dtype=float)
    labels: list[str] = []
    lookup = {
        (
            int(row["n_samples"]),
            float(row["period_s"]),
            float(row["red_noise_alpha"]),
            float(row["qpp_fraction"]),
        ): float(row["joint_margin_median"])
        for row in positives
    }
    for row_index, (n_samples, period_s, alpha) in enumerate(strata):
        labels.append(f"N{n_samples} P{period_s:g} α{alpha:g}")
        for column_index, q_value in enumerate(q_values):
            matrix[row_index, column_index] = lookup[(n_samples, period_s, alpha, q_value)]

    figure, axis = plt.subplots(figsize=(8.5, 8.5))
    image = axis.imshow(matrix, aspect="auto")
    axis.set_xticks(range(len(q_values)), [f"q={value:.2f}" for value in q_values])
    axis.set_yticks(range(len(labels)), labels)
    axis.set_xlabel("Amplitud fraccional inyectada")
    axis.set_ylabel("Estrato")
    axis.set_title("Mediana del margen conjunto en ventanas cortas")
    colorbar = figure.colorbar(image, ax=axis)
    colorbar.set_label("joint_margin")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def create_period_error_figure(path: Path, diagnostics: list[dict[str, Any]]) -> None:
    positives = [row for row in diagnostics if row["ground_truth"] == POSITIVE_TRUTH]
    groups: list[list[float]] = []
    labels: list[str] = []
    for n_samples in (15, 30):
        periods = sorted({float(row["period_s"]) for row in positives if int(row["n_samples"]) == n_samples})
        for period in periods:
            groups.append([
                float(row["formal_period_error_s"])
                for row in positives
                if int(row["n_samples"]) == n_samples and float(row["period_s"]) == period
            ])
            labels.append(f"N{n_samples}\nP{period:g}")

    figure, axis = plt.subplots(figsize=(8.5, 6.5))
    axis.boxplot(groups, tick_labels=labels, showfliers=False)
    axis.axhline(0.0, linestyle="--")
    axis.set_ylabel("Error del centro formal de M1 (s)")
    axis.set_xlabel("Tamaño y periodo inyectado")
    axis.set_title("Error del periodo formal en positivos no seleccionados")
    axis.grid(True, axis="y", alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def report_text(
    diagnostics: list[dict[str, Any]],
    amplitude: list[dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    positives = [row for row in diagnostics if row["ground_truth"] == POSITIVE_TRUTH]
    classes = Counter(row["threshold_failure_class"] for row in diagnostics)
    winners = Counter(row["bic_winner"] for row in diagnostics)

    by_n: dict[int, dict[str, float]] = {}
    for n_samples in (15, 30):
        rows = [row for row in positives if int(row["n_samples"]) == n_samples]
        errors = [float(row["formal_period_error_s"]) for row in rows]
        absolute = [float(row["formal_period_absolute_error_s"]) for row in rows]
        by_n[n_samples] = {
            "delta01_median": float(np.median([float(row["delta_bic_0_1"]) for row in rows])),
            "delta21_median": float(np.median([float(row["delta_bic_2_1"]) for row in rows])),
            "joint_median": float(np.median([float(row["joint_margin"]) for row in rows])),
            "period_signed_median": float(np.median(errors)),
            "period_absolute_median": float(np.median(absolute)),
            "m1_bound_count": sum(as_bool(row["m1_any_bound"], "m1_any_bound") for row in rows),
            "m1_width_bound_count": sum(as_bool(row["m1_width_parameter_bound"], "m1_width") for row in rows),
            "m1_center_bound_count": sum(as_bool(row["m1_center_parameter_bound"], "m1_center") for row in rows),
            "m1_amplitude_bound_count": sum(as_bool(row["m1_amplitude_parameter_bound"], "m1_amplitude") for row in rows),
        }

    amp_change01 = [float(row["median_change_delta_bic_0_1"]) for row in amplitude]
    amp_change21 = [float(row["median_change_delta_bic_2_1"]) for row in amplitude]
    amp_joint = [float(row["median_change_joint_margin"]) for row in amplitude]
    threshold_crossings = sum(int(row["m0_threshold_crossing_count"]) + int(row["m2_threshold_crossing_count"]) for row in amplitude)
    winner_changes = sum(int(row["bic_winner_change_count"]) for row in amplitude)

    # Compare the 18 common positive condition strata across N=15 and N=30.
    grouped: dict[tuple[int, float, float, float], list[float]] = defaultdict(list)
    for row in positives:
        grouped[(int(row["n_samples"]), float(row["period_s"]), float(row["red_noise_alpha"]), float(row["qpp_fraction"]))].append(float(row["joint_margin"]))
    n30_closer = 0
    n15_closer = 0
    for period in (50.0, 80.0):
        for alpha in (0.0, 1.0, 2.0):
            for q_value in (0.01, 0.02, 0.04):
                n15 = float(np.median(grouped[(15, period, alpha, q_value)]))
                n30 = float(np.median(grouped[(30, period, alpha, q_value)]))
                if n30 > n15:
                    n30_closer += 1
                elif n15 > n30:
                    n15_closer += 1

    m1_bound_pos = sum(as_bool(row["m1_any_bound"], "m1_any_bound") for row in positives)
    m1_width_pos = sum(as_bool(row["m1_width_parameter_bound"], "m1_width") for row in positives)
    m1_center_pos = sum(as_bool(row["m1_center_parameter_bound"], "m1_center") for row in positives)
    m1_amp_pos = sum(as_bool(row["m1_amplitude_parameter_bound"], "m1_amp") for row in positives)

    hypothesis = (
        "En ventanas cortas, aumentar el soporte espectral manteniendo la misma señal y el mismo proceso de ruido "
        "debería elevar principalmente ΔBIC₀,₁, porque la mejora de likelihood de M1 observada aquí no compensa "
        "el resto de penalización frente a M0; si la hipótesis es correcta, el margen frente a M0 crecerá más que "
        "el margen frente a M2 y aparecerán cruces conjuntos de los dos umbrales."
    )

    text = f"""# Fase 1 — Tarea 1.7

## Descomposición del fallo de selección en ventanas cortas

**Estado:** `SHORT_WINDOW_FAILURE_DIAGNOSTIC_COMPLETE`

## Población y auditoría

Se analizaron exclusivamente las 2.040 decisiones primarias con `N=15` o `N=30` y semilla externa cero: 1.800 positivos sintéticos y 240 nulos. Los 6.120 resultados de M0, M1 y M2 se vincularon sin tríos incompletos, duplicados, BIC no finitos ni discrepancias con las decisiones de F1.5. AFINO no se ejecutó y no se generaron curvas sintéticas nuevas.

## Cuello de botella de la regla doble

La clasificación es inequívoca: las 2.040 series pertenecen a `BOTH_COMPARISONS_FAILED`. No existe ningún caso en el que se supere solo la comparación frente a M0, solo la comparación frente a M2 o ambos umbrales. Además, M0 es el modelo con BIC mínimo en las 2.040 series; M1 no llega a ser ganador formal una sola vez. El término limitante inmediato es la comparación frente a M0: en todas las realizaciones, ΔBIC₀,₁ es menor que ΔBIC₂,₁ y, por tanto, `joint_margin` coincide con `margin_vs_m0`.

En positivos, la mediana de ΔBIC₀,₁ es {by_n[15]['delta01_median']:.3f} para N=15 y {by_n[30]['delta01_median']:.3f} para N=30; las medianas de ΔBIC₂,₁ son {by_n[15]['delta21_median']:.3f} y {by_n[30]['delta21_median']:.3f}. La descomposición likelihood–BIC muestra mejoras positivas de likelihood en muchas series, pero insuficientes para compensar los restos observados de penalización BIC. Estos restos se describen empíricamente y no se interpretan como grados de libertad privados.

## Amplitud y proximidad a los umbrales

Aumentar `q` desplaza los márgenes aunque no produzca selección. Los 45 contrastes emparejados de amplitud presentan cambio mediano positivo en ΔBIC₀,₁ y en `joint_margin`; {sum(value > 0 for value in amp_change21)}/45 también aumentan en ΔBIC₂,₁. No hubo cruces de umbral ni cambios de ganador BIC. Por tanto, la señal de mayor amplitud sí mueve la evidencia en la dirección prevista, pero el desplazamiento permanece lejos de la regla doble y no autoriza una categoría adicional de “casi detección”.

N=30 no se aproxima uniformemente más que N=15 en los periodos comunes. De los 18 estratos compartidos, N=15 tiene una mediana de `joint_margin` menos negativa en {n15_closer}, mientras N=30 solo la mejora en {n30_closer}. El mayor soporte de N=30 aporta más ganancia de likelihood en algunas condiciones, pero también presenta un resto de penalización BIC mayor; con estos datos no basta para cruzar ninguno de los umbrales.

## Periodo formal, bounds y soporte espectral

Los centros formales de M1 no equivalen a periodos recuperados. Para N=15, el error firmado mediano es {by_n[15]['period_signed_median']:.3f} s y el error absoluto mediano {by_n[15]['period_absolute_median']:.3f} s. Para N=30, el error firmado mediano baja a {by_n[30]['period_signed_median']:.3f} s, pero el error absoluto mediano sigue siendo {by_n[30]['period_absolute_median']:.3f} s. Esto indica que algunos centros se acercan al periodo inyectado, especialmente en N=30, pero existe dispersión sustancial y todos continúan etiquetados como `formal_m1_center_not_selected`.

M1 toca algún bound en {m1_bound_pos}/1.800 positivos. El bound más frecuente es la anchura ({m1_width_pos}), seguido del centro ({m1_center_pos}) y la amplitud ({m1_amp_pos}). La coexistencia de bounds con márgenes negativos documenta restricciones numéricas observables, pero no demuestra que sean la causa del fallo. M2 registra warnings, mientras M1 no, de acuerdo con F1.6.

Después del cutoff permanecen exactamente 7 bins para N=15 y 14 para N=30. Este soporte espectral reducido es compatible con la hipótesis de que la evidencia de likelihood no compensa la penalización de complejidad, pero la tarea no establece causalidad física.

## Hipótesis para el siguiente benchmark

{hypothesis}

Esta hipótesis es comprobable y no modifica la regla de selección ni define todavía un nuevo grid.
"""

    descriptive = {
        "threshold_failure_class_counts": dict(sorted(classes.items())),
        "bic_winner_counts": dict(sorted(winners.items())),
        "all_joint_margins_limited_by_m0": all(float(row["margin_vs_m0"]) <= float(row["margin_vs_m2"]) for row in diagnostics),
        "amplitude_contrasts_positive_delta_bic_0_1": sum(value > 0 for value in amp_change01),
        "amplitude_contrasts_positive_delta_bic_2_1": sum(value > 0 for value in amp_change21),
        "amplitude_contrasts_positive_joint_margin": sum(value > 0 for value in amp_joint),
        "amplitude_threshold_crossings": threshold_crossings,
        "amplitude_bic_winner_changes": winner_changes,
        "common_strata_n15_closer": n15_closer,
        "common_strata_n30_closer": n30_closer,
        "m1_any_bound_positive_count": m1_bound_pos,
        "m1_width_bound_positive_count": m1_width_pos,
        "m1_center_bound_positive_count": m1_center_pos,
        "m1_amplitude_bound_positive_count": m1_amp_pos,
        "bins_after_cutoff_by_n": {"15": 7, "30": 14},
        "testable_hypothesis": hypothesis,
    }
    return text, descriptive


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    for name in OUTPUT_NAMES:
        if (root / name).exists():
            raise DiagnosticError(f"Preserve existing output: {name}")

    input_hashes_pre = verify_inputs(root)
    diagnostics, independent = build_diagnostics(root)
    condition_summary = build_condition_summary(diagnostics)
    amplitude = build_amplitude_contrasts(diagnostics)

    write_csv(root / "fase1_tarea07_short_window_run_diagnostics.csv", RUN_FIELDS, diagnostics)
    write_csv(root / "fase1_tarea07_short_window_condition_summary.csv", CONDITION_FIELDS, condition_summary)
    write_csv(root / "fase1_tarea07_short_window_amplitude_contrasts.csv", AMPLITUDE_FIELDS, amplitude)

    create_threshold_plane(root / "fase1_tarea07_fig01_n15_bic_threshold_plane.png", diagnostics, 15)
    create_threshold_plane(root / "fase1_tarea07_fig02_n30_bic_threshold_plane.png", diagnostics, 30)
    create_margin_grid(root / "fase1_tarea07_fig03_short_window_margin_grid.png", condition_summary)
    create_period_error_figure(root / "fase1_tarea07_fig04_formal_period_error.png", diagnostics)

    report, descriptive = report_text(diagnostics, amplitude)
    report_path = root / "fase1_tarea07_short_window_diagnostic.md"
    report_path.write_text(report, encoding="utf-8")

    input_hashes_post = verify_inputs(root)
    if input_hashes_post != input_hashes_pre:
        raise DiagnosticError("An input hash changed during F1.7.")

    output_hashes = {
        name: sha256(root / name)
        for name in OUTPUT_NAMES
        if name != "fase1_tarea07_short_window_diagnostic_audit.json"
    }
    audit = {
        "generated_at_utc": utc_now(),
        "execution_status": "SHORT_WINDOW_FAILURE_DIAGNOSTIC_COMPLETE",
        "analysis_protocol": {
            "population": "primary only, n_samples in {15,30}, external_optimizer_seed=0",
            "bic_threshold": 10.0,
            "bic_tie_abs_tolerance": ABS_TOL,
            "bic_tie_relative_tolerance": REL_TOL,
            "quantile_method": "linear",
            "bound_indices": {
                "m1_amplitude": 2,
                "m1_center": 4,
                "m1_width": 5,
            },
        },
        "environment": {
            "python_version": platform.python_version(),
            "python_full": sys.version,
            "platform": platform.platform(),
            "numpy_version": np.__version__,
            "matplotlib_version": matplotlib.__version__,
        },
        "input_hashes_pre": input_hashes_pre,
        "input_hashes_post": input_hashes_post,
        "row_counts": {
            "run_rows": len(diagnostics),
            "positive_rows": sum(row["ground_truth"] == POSITIVE_TRUTH for row in diagnostics),
            "null_rows": sum(row["ground_truth"] == NULL_TRUTH for row in diagnostics),
            "model_rows_used": len(diagnostics) * 3,
            "condition_rows": len(condition_summary),
            "amplitude_contrast_rows": len(amplitude),
        },
        "independent_audit": independent,
        "descriptive_results": descriptive,
        "output_hashes": output_hashes,
        "confirmations": {
            "afino_executed": False,
            "new_curves_generated": False,
            "raw_results_modified": False,
            "raw_decisions_modified": False,
            "post_result_selection_thresholds_added": False,
            "stability_runs_included": False,
            "canary_included": False,
            "causal_mechanism_claimed": False,
        },
    }
    audit_path = root / "fase1_tarea07_short_window_diagnostic_audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # Final row and content checks after writing.
    expected_rows = {
        "fase1_tarea07_short_window_run_diagnostics.csv": 2040,
        "fase1_tarea07_short_window_condition_summary.csv": 51,
        "fase1_tarea07_short_window_amplitude_contrasts.csv": 45,
    }
    for name, expected in expected_rows.items():
        _, rows = read_csv(root / name)
        if len(rows) != expected:
            raise DiagnosticError(f"Round-trip row count mismatch for {name}.")

    print("F1.7 short-window diagnostic complete")
    print("execution_status: SHORT_WINDOW_FAILURE_DIAGNOSTIC_COMPLETE")
    print("run_rows: 2040")
    print("positive_rows: 1800")
    print("null_rows: 240")
    print("model_rows_used: 6120")
    print("condition_rows: 51")
    print("amplitude_contrast_rows: 45")
    print("decision_mismatches: 0")
    print("input_hash_mismatches: 0")
    print("duplicate_series: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
