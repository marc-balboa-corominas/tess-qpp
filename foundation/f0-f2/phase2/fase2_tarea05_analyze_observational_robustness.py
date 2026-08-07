#!/usr/bin/env python3
"""F2.5 — Frozen observational cohort robustness analysis.

This script:
- does not import or execute AFINO;
- does not import Astropy or open FITS;
- does not regenerate variants or repeat preprocessing;
- uses only frozen CSV/JSON outputs from F2.1, F2.2 and F2.4;
- publishes outputs only after all structural validations pass.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


# =============================================================================
# Frozen inputs and output names
# =============================================================================

FROZEN_HASHES = {
    "fase2_tarea01_observational_robustness_preregistration.json":
        "ed37166ad6917b54711c3ce7ac9f3aeffdaaba9477672a9b1e5d506c07f427d7",
    "fase2_tarea01_frozen_observational_cohort.csv":
        "34f4a5ce53e7fb16ee16c976d5b06af524d6cacda4a4bc303a5d580193745cc1",
    "fase2_tarea01_window_perturbations.csv":
        "4e0a602e89f17594afe4624ae0d48781cfde7c17a17a1cc129002aeb0c45f130",
    "fase2_tarea01_processing_profiles.csv":
        "232af6bdc6fa09851cd1039c5b159849f2f675803ea6ff1f53f51e7a4a7629e0",
    "fase2_tarea02_observational_variant_manifest.csv":
        "e89f33d433a48217feb44c07efae33b984377a205c218253553a604df71c5093",
    "fase2_tarea02_resolved_decision_grid.csv":
        "2150657765dff06fb69272c4c11b7bcea656dce2d3fd8faa15b35821dec944dd",
    "fase2_tarea04_observational_full_results.csv":
        "791e071df6e05749937070a31ed4c344b95e10f09abd83a392093ccf2c85a9f8",
    "fase2_tarea04_observational_full_decisions.csv":
        "f4c6940f8c67c5a5bdfbabaf6f540fc07538f2a09acddd56edebf3a894f225f0",
    "fase2_tarea04_full_execution_audit.json":
        "9c406be909cbdccbf7dff196c309568d228973ed5dbb3fae4e06573e8ada5b07",
}

OUTPUT_NAMES = [
    "fase2_tarea05_primary_robustness_enriched.csv",
    "fase2_tarea05_event_summary.csv",
    "fase2_tarea05_pair_summary.csv",
    "fase2_tarea05_window_profile_summary.csv",
    "fase2_tarea05_window_contrasts.csv",
    "fase2_tarea05_processing_profile_contrasts.csv",
    "fase2_tarea05_optimizer_stability_summary.csv",
    "fase2_tarea05_period_robustness.csv",
    "fase2_tarea05_model_diagnostics_summary.csv",
    "fase2_tarea05_primary_outcome_matrix.png",
    "fase2_tarea05_baseline_transitions.png",
    "fase2_tarea05_processing_contrasts.png",
    "fase2_tarea05_optimizer_and_period_stability.png",
    "fase2_tarea05_observational_robustness_audit.json",
    "fase2_tarea05_observational_robustness_report.md",
]

ANALYSIS_CONCLUSION = (
    "FROZEN_COHORT_ROBUSTNESS_CHARACTERIZED_WITH_LIMITATIONS"
)
ABS_TOLERANCE = 5e-12
REL_TOLERANCE = 0.0

ROLE_ORDER = [
    "PUBLISHED_QPP_REPRODUCED",
    "MATCHED_NOT_SELECTED",
]

PRIMARY_OUTCOMES = {
    "SELECTED",
    "NOT_SELECTED",
    "INPUT_INADMISSIBLE",
    "INCOMPLETE_NUMERICAL",
}

BASELINE_COMPARISON_STATUSES = {
    "SELECTED_RETAINED",
    "SELECTION_LOST",
    "NOT_SELECTED_RETAINED",
    "SELECTION_GAINED",
    "INPUT_INADMISSIBLE",
    "INCOMPLETE_NUMERICAL",
}

COMPARABILITY_STATUSES = {
    "BOTH_ELIGIBLE",
    "REFERENCE_INADMISSIBLE",
    "VARIANT_INADMISSIBLE",
    "BOTH_INADMISSIBLE",
    "INCOMPLETE_NUMERICAL",
}

PROCESSING_CONTRASTS = [
    ("FLUX_FINITE", "P00", "P01"),
    ("QUALITY_PDCSAP", "P00", "P02"),
    ("QUALITY_SAP", "P01", "P03"),
    ("DETREND_PDCSAP", "P00", "P04"),
    ("DETREND_SAP", "P01", "P05"),
    ("FLUX_Q0", "P02", "P03"),
]


# =============================================================================
# Utilities
# =============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Iterable[dict[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(fieldnames),
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    raise ValueError(f"Not a boolean: {value!r}")


def optional_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    return None if text == "" else float(text)


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    return value


def is_close(left: float, right: float) -> bool:
    return math.isclose(
        float(left),
        float(right),
        abs_tol=ABS_TOLERANCE,
        rel_tol=REL_TOLERANCE,
    )


def describe(values: Sequence[float]) -> dict[str, Any]:
    array = np.asarray(list(values), dtype=np.float64)
    if array.size == 0:
        return {
            "n": 0,
            "minimum": None,
            "q1": None,
            "median": None,
            "q3": None,
            "maximum": None,
        }
    return {
        "n": int(array.size),
        "minimum": float(np.min(array)),
        "q1": float(np.quantile(array, 0.25, method="linear")),
        "median": float(np.quantile(array, 0.50, method="linear")),
        "q3": float(np.quantile(array, 0.75, method="linear")),
        "maximum": float(np.max(array)),
    }


def range_value(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return float(max(values) - min(values))


def sorted_join(
    values: Iterable[str],
    order: Sequence[str] | None = None,
) -> str:
    unique = set(values)
    if order is None:
        chosen = sorted(unique)
    else:
        chosen = [value for value in order if value in unique]
    return "|".join(chosen)


def transition(left: bool, right: bool) -> str:
    return f"{int(left)}→{int(right)}"


def compare_rows(
    reference: dict[str, Any],
    variant: dict[str, Any],
) -> dict[str, Any]:
    left_outcome = reference["primary_outcome"]
    right_outcome = variant["primary_outcome"]

    if (
        left_outcome == "INCOMPLETE_NUMERICAL"
        or right_outcome == "INCOMPLETE_NUMERICAL"
    ):
        status = "INCOMPLETE_NUMERICAL"
    elif (
        left_outcome == "INPUT_INADMISSIBLE"
        and right_outcome == "INPUT_INADMISSIBLE"
    ):
        status = "BOTH_INADMISSIBLE"
    elif left_outcome == "INPUT_INADMISSIBLE":
        status = "REFERENCE_INADMISSIBLE"
    elif right_outcome == "INPUT_INADMISSIBLE":
        status = "VARIANT_INADMISSIBLE"
    else:
        status = "BOTH_ELIGIBLE"

    output = {
        "comparability_status": status,
        "selection_transition": "",
        "change_delta_bic_0_1": "",
        "change_delta_bic_2_1": "",
        "change_joint_margin": "",
    }
    if status == "BOTH_ELIGIBLE":
        left_selected = parse_bool(reference["qpp_selected"])
        right_selected = parse_bool(variant["qpp_selected"])
        output["selection_transition"] = transition(
            left_selected,
            right_selected,
        )
        output["change_delta_bic_0_1"] = (
            float(variant["delta_bic_0_1"])
            - float(reference["delta_bic_0_1"])
        )
        output["change_delta_bic_2_1"] = (
            float(variant["delta_bic_2_1"])
            - float(reference["delta_bic_2_1"])
        )
        output["change_joint_margin"] = (
            float(variant["joint_margin"])
            - float(reference["joint_margin"])
        )
    return output


def source_hashes(root: Path) -> dict[str, str]:
    observed = {}
    for filename, expected in FROZEN_HASHES.items():
        path = root / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        observed[filename] = actual
        if actual != expected:
            raise RuntimeError(
                f"Frozen hash mismatch for {filename}: "
                f"{actual} != {expected}"
            )
    return observed


# =============================================================================
# Main analysis
# =============================================================================

def run_analysis(input_dir: Path, output_dir: Path) -> None:
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()

    for name in OUTPUT_NAMES:
        if (output_dir / name).exists():
            raise FileExistsError(
                f"Refusing to overwrite final output: {name}"
            )

    input_hashes_before = source_hashes(input_dir)

    prereg = json.loads(
        (
            input_dir
            / "fase2_tarea01_observational_robustness_preregistration.json"
        ).read_text(encoding="utf-8")
    )
    cohort = read_csv(
        input_dir / "fase2_tarea01_frozen_observational_cohort.csv"
    )
    windows = read_csv(
        input_dir / "fase2_tarea01_window_perturbations.csv"
    )
    profiles = read_csv(
        input_dir / "fase2_tarea01_processing_profiles.csv"
    )
    manifest = read_csv(
        input_dir / "fase2_tarea02_observational_variant_manifest.csv"
    )
    resolved_grid = read_csv(
        input_dir / "fase2_tarea02_resolved_decision_grid.csv"
    )
    results = read_csv(
        input_dir / "fase2_tarea04_observational_full_results.csv"
    )
    decisions = read_csv(
        input_dir / "fase2_tarea04_observational_full_decisions.csv"
    )
    f24_audit = json.loads(
        (
            input_dir / "fase2_tarea04_full_execution_audit.json"
        ).read_text(encoding="utf-8")
    )

    # ---------------------------------------------------------------------
    # Normative preflight
    # ---------------------------------------------------------------------

    if f24_audit.get("execution_status") != (
        "FULL_OBSERVATIONAL_PLAN_EXECUTION_COMPLETE"
    ):
        raise RuntimeError("F2.4 execution status is not complete.")
    if f24_audit.get("result_status_counts") != {"OK": 2784}:
        raise RuntimeError("F2.4 does not contain 2,784 OK results.")
    if f24_audit.get("decision_status_counts") != {"VALID": 928}:
        raise RuntimeError("F2.4 does not contain 928 VALID decisions.")

    if len(cohort) != 10:
        raise RuntimeError(f"Cohort rows: {len(cohort)} != 10.")
    if len(windows) != 13:
        raise RuntimeError(f"Window rows: {len(windows)} != 13.")
    if len(profiles) != 6:
        raise RuntimeError(f"Profile rows: {len(profiles)} != 6.")
    if len(manifest) != 780:
        raise RuntimeError(f"Manifest rows: {len(manifest)} != 780.")
    if len(resolved_grid) != 1320:
        raise RuntimeError(
            f"Resolved decision grid rows: {len(resolved_grid)} != 1320."
        )
    if len(results) != 2784:
        raise RuntimeError(f"Result rows: {len(results)} != 2784.")
    if len(decisions) != 928:
        raise RuntimeError(f"Decision rows: {len(decisions)} != 928.")

    event_order = [row["event_id"] for row in cohort]
    window_order = [row["window_variant_id"] for row in windows]
    profile_order = [row["processing_profile_id"] for row in profiles]
    pair_order = []
    for row in cohort:
        if row["pair_id"] not in pair_order:
            pair_order.append(row["pair_id"])

    if Counter(row["observational_role"] for row in cohort) != {
        "PUBLISHED_QPP_REPRODUCED": 5,
        "MATCHED_NOT_SELECTED": 5,
    }:
        raise RuntimeError("Frozen role composition changed.")

    expected_primary_keys = {
        (event_id, window_id, profile_id)
        for event_id in event_order
        for window_id in window_order
        for profile_id in profile_order
    }
    manifest_keys = {
        (
            row["event_id"],
            row["window_variant_id"],
            row["processing_profile_id"],
        )
        for row in manifest
    }
    if manifest_keys != expected_primary_keys:
        raise RuntimeError("The manifest is not the complete 10×13×6 grid.")

    duplicate_primary_variant_ids = (
        len(manifest)
        - len({row["variant_id"] for row in manifest})
    )
    if duplicate_primary_variant_ids != 0:
        raise RuntimeError("Duplicate primary variant IDs.")

    resolved_primary = [
        row for row in resolved_grid
        if row["decision_class"] == "primary"
    ]
    resolved_stability = [
        row for row in resolved_grid
        if row["decision_class"] == "stability"
    ]
    if len(resolved_primary) != 780 or len(resolved_stability) != 540:
        raise RuntimeError("Resolved primary/stability design changed.")

    primary_decisions = [
        row for row in decisions
        if row["decision_class"] == "primary"
    ]
    stability_decisions = [
        row for row in decisions
        if row["decision_class"] == "stability"
    ]
    if len(primary_decisions) != 514:
        raise RuntimeError("Primary decision count is not 514.")
    if len(stability_decisions) != 414:
        raise RuntimeError("Stability decision count is not 414.")

    decision_by_variant_seed = {
        (row["variant_id"], int(row["external_optimizer_seed"])): row
        for row in decisions
    }
    if len(decision_by_variant_seed) != 928:
        raise RuntimeError("Duplicate decision variant/seed keys.")

    result_by_variant_seed_model = {
        (
            row["variant_id"],
            int(row["external_optimizer_seed"]),
            row["model_id"],
        ): row
        for row in results
    }
    if len(result_by_variant_seed_model) != 2784:
        raise RuntimeError("Duplicate result scientific keys.")

    cohort_by_event = {row["event_id"]: row for row in cohort}
    manifest_by_key = {
        (
            row["event_id"],
            row["window_variant_id"],
            row["processing_profile_id"],
        ): row
        for row in manifest
    }

    # Recalculate all 928 classifications.
    decision_recalculation_mismatches = 0
    for decision in decisions:
        if decision["decision_status"] != "VALID":
            continue
        delta01 = float(decision["bic_m0"]) - float(decision["bic_m1"])
        delta21 = float(decision["bic_m2"]) - float(decision["bic_m1"])
        selected = bool(delta01 > 10.0 and delta21 > 10.0)
        if not is_close(delta01, float(decision["delta_bic_0_1"])):
            decision_recalculation_mismatches += 1
        if not is_close(delta21, float(decision["delta_bic_2_1"])):
            decision_recalculation_mismatches += 1
        if selected != parse_bool(decision["qpp_selected"]):
            decision_recalculation_mismatches += 1
    if decision_recalculation_mismatches != 0:
        raise RuntimeError("Decision recalculation mismatch.")

    # ---------------------------------------------------------------------
    # Baseline verification
    # ---------------------------------------------------------------------

    baseline_by_event: dict[str, dict[str, Any]] = {}
    baseline_records = []
    baseline_classification_mismatches = 0
    baseline_numeric_mismatches = 0
    baseline_period_label_mismatches = 0

    cohort_fields = set(cohort[0])
    frozen_bic_fields_available = all(
        field in cohort_fields
        for field in ("baseline_bic_m0", "baseline_bic_m1", "baseline_bic_m2")
    )

    for event_id in event_order:
        frozen = cohort_by_event[event_id]
        variant = manifest_by_key[(event_id, "W00", "P00")]
        decision = decision_by_variant_seed.get((variant["variant_id"], 0))
        if decision is None:
            raise RuntimeError(f"Missing baseline decision for {event_id}.")

        frozen_selected = parse_bool(frozen["baseline_qpp_selected"])
        observed_selected = parse_bool(decision["qpp_selected"])
        if frozen_selected != observed_selected:
            baseline_classification_mismatches += 1

        field_mismatches = []
        numeric_pairs = [
            (
                "delta_bic_0_1",
                float(frozen["baseline_delta_bic_0_1"]),
                float(decision["delta_bic_0_1"]),
            ),
            (
                "delta_bic_2_1",
                float(frozen["baseline_delta_bic_2_1"]),
                float(decision["delta_bic_2_1"]),
            ),
            (
                "formal_m1_period_s",
                float(frozen["baseline_estimated_period_s"]),
                float(decision["formal_m1_period_s"]),
            ),
        ]
        for field, expected, observed in numeric_pairs:
            if not is_close(expected, observed):
                baseline_numeric_mismatches += 1
                field_mismatches.append(field)

        # The label is derived from frozen baseline_qpp_selected and the
        # frozen preregistered period-label semantics, never from role.
        if frozen["baseline_estimated_period_s"] == "":
            expected_label = "unavailable_incomplete_numerical"
        elif frozen_selected:
            expected_label = "recovered_period_selected"
        else:
            expected_label = "formal_m1_center_not_selected"
        if decision["period_label"] != expected_label:
            baseline_period_label_mismatches += 1
            field_mismatches.append("period_label")

        record = {
            "event_id": event_id,
            "variant_id": variant["variant_id"],
            "frozen_qpp_selected": frozen_selected,
            "observed_qpp_selected": observed_selected,
            "frozen_delta_bic_0_1":
                float(frozen["baseline_delta_bic_0_1"]),
            "observed_delta_bic_0_1":
                float(decision["delta_bic_0_1"]),
            "frozen_delta_bic_2_1":
                float(frozen["baseline_delta_bic_2_1"]),
            "observed_delta_bic_2_1":
                float(decision["delta_bic_2_1"]),
            "frozen_formal_m1_period_s":
                float(frozen["baseline_estimated_period_s"]),
            "observed_formal_m1_period_s":
                float(decision["formal_m1_period_s"]),
            "expected_period_label": expected_label,
            "observed_period_label": decision["period_label"],
            "frozen_bic_reference_available":
                frozen_bic_fields_available,
            "observed_bic_m0": float(decision["bic_m0"]),
            "observed_bic_m1": float(decision["bic_m1"]),
            "observed_bic_m2": float(decision["bic_m2"]),
            "comparison_status":
                "EXACT_WITHIN_TOLERANCE"
                if not field_mismatches
                and frozen_selected == observed_selected
                else "MISMATCH",
            "field_mismatches": field_mismatches,
        }
        baseline_records.append(record)
        baseline_by_event[event_id] = {
            "qpp_selected": frozen_selected,
            "formal_m1_period_s":
                float(frozen["baseline_estimated_period_s"]),
            "period_label": expected_label,
            "current_decision": decision,
        }

    if baseline_classification_mismatches != 0:
        raise RuntimeError("Baseline classification mismatch blocks F2.5.")
    if baseline_numeric_mismatches != 0:
        raise RuntimeError("Baseline frozen numeric mismatch.")
    if baseline_period_label_mismatches != 0:
        raise RuntimeError("Baseline period-label mismatch.")

    # ---------------------------------------------------------------------
    # Primary enriched table
    # ---------------------------------------------------------------------

    enriched_rows: list[dict[str, Any]] = []
    enriched_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}

    for manifest_row in sorted(
        manifest,
        key=lambda row: int(row["variant_order"]),
    ):
        event_id = manifest_row["event_id"]
        baseline = baseline_by_event[event_id]
        admissible = (
            manifest_row["admissibility_status"] == "ELIGIBLE_FOR_AFINO"
        )
        decision = (
            decision_by_variant_seed.get((manifest_row["variant_id"], 0))
            if admissible else None
        )

        if not admissible:
            primary_outcome = "INPUT_INADMISSIBLE"
            baseline_status = "INPUT_INADMISSIBLE"
            values = {
                "bic_m0": "",
                "bic_m1": "",
                "bic_m2": "",
                "delta_bic_0_1": "",
                "delta_bic_2_1": "",
                "qpp_selected": "",
                "formal_m1_period_s": "",
                "period_label": "",
                "margin_vs_m0": "",
                "margin_vs_m2": "",
                "joint_margin": "",
            }
        elif decision is None or decision["decision_status"] != "VALID":
            primary_outcome = "INCOMPLETE_NUMERICAL"
            baseline_status = "INCOMPLETE_NUMERICAL"
            values = {
                "bic_m0": "" if decision is None else decision["bic_m0"],
                "bic_m1": "" if decision is None else decision["bic_m1"],
                "bic_m2": "" if decision is None else decision["bic_m2"],
                "delta_bic_0_1": "",
                "delta_bic_2_1": "",
                "qpp_selected": "",
                "formal_m1_period_s": "",
                "period_label": "",
                "margin_vs_m0": "",
                "margin_vs_m2": "",
                "joint_margin": "",
            }
        else:
            selected = parse_bool(decision["qpp_selected"])
            primary_outcome = "SELECTED" if selected else "NOT_SELECTED"
            if baseline["qpp_selected"]:
                baseline_status = (
                    "SELECTED_RETAINED" if selected else "SELECTION_LOST"
                )
            else:
                baseline_status = (
                    "SELECTION_GAINED"
                    if selected else "NOT_SELECTED_RETAINED"
                )
            delta01 = float(decision["delta_bic_0_1"])
            delta21 = float(decision["delta_bic_2_1"])
            margin01 = delta01 - 10.0
            margin21 = delta21 - 10.0
            values = {
                "bic_m0": float(decision["bic_m0"]),
                "bic_m1": float(decision["bic_m1"]),
                "bic_m2": float(decision["bic_m2"]),
                "delta_bic_0_1": delta01,
                "delta_bic_2_1": delta21,
                "qpp_selected": selected,
                "formal_m1_period_s":
                    optional_float(decision["formal_m1_period_s"]),
                "period_label": decision["period_label"],
                "margin_vs_m0": margin01,
                "margin_vs_m2": margin21,
                "joint_margin": min(margin01, margin21),
            }

        row = {
            "planned_decision_id":
                manifest_row["primary_planned_decision_id"],
            "variant_id": manifest_row["variant_id"],
            "event_id": event_id,
            "pair_id": manifest_row["pair_id"],
            "observational_role": manifest_row["observational_role"],
            "window_variant_id": manifest_row["window_variant_id"],
            "processing_profile_id":
                manifest_row["processing_profile_id"],
            "admissibility_status":
                manifest_row["admissibility_status"],
            "inadmissibility_reason":
                manifest_row["admissibility_reason"],
            "primary_outcome": primary_outcome,
            **values,
            "baseline_qpp_selected": baseline["qpp_selected"],
            "baseline_formal_m1_period_s":
                baseline["formal_m1_period_s"],
            "baseline_comparison_status": baseline_status,
        }
        if row["primary_outcome"] not in PRIMARY_OUTCOMES:
            raise RuntimeError("Invalid primary outcome.")
        if (
            row["baseline_comparison_status"]
            not in BASELINE_COMPARISON_STATUSES
        ):
            raise RuntimeError("Invalid baseline comparison status.")
        enriched_rows.append(row)
        enriched_by_key[(
            row["event_id"],
            row["window_variant_id"],
            row["processing_profile_id"],
        )] = row

    primary_counts = Counter(
        row["primary_outcome"] for row in enriched_rows
    )
    if primary_counts["INPUT_INADMISSIBLE"] != 266:
        raise RuntimeError("Primary inadmissible count is not 266.")
    if (
        primary_counts["SELECTED"]
        + primary_counts["NOT_SELECTED"]
        + primary_counts["INCOMPLETE_NUMERICAL"]
        != 514
    ):
        raise RuntimeError("Primary evaluated count is not 514.")

    inadmissible_status_counts = Counter(
        row["admissibility_status"]
        for row in enriched_rows
        if row["primary_outcome"] == "INPUT_INADMISSIBLE"
    )
    expected_inadmissibility = {
        "IRREGULAR_SAMPLING": 142,
        "TOO_FEW_CADENCES": 98,
        "PEAK_REMOVED_BY_QUALITY": 26,
    }
    if dict(inadmissible_status_counts) != expected_inadmissibility:
        raise RuntimeError(
            f"Unexpected inadmissibility counts: "
            f"{inadmissible_status_counts}"
        )

    # ---------------------------------------------------------------------
    # Period robustness
    # ---------------------------------------------------------------------

    period_rows = []
    formal_nonselected_centers = []
    for row in enriched_rows:
        if (
            row["baseline_qpp_selected"] is True
            and row["primary_outcome"] == "SELECTED"
            and row["baseline_formal_m1_period_s"] != ""
            and row["formal_m1_period_s"] != ""
        ):
            baseline_period = float(
                row["baseline_formal_m1_period_s"]
            )
            variant_period = float(row["formal_m1_period_s"])
            signed = variant_period - baseline_period
            period_rows.append({
                "planned_decision_id": row["planned_decision_id"],
                "variant_id": row["variant_id"],
                "event_id": row["event_id"],
                "pair_id": row["pair_id"],
                "observational_role": row["observational_role"],
                "window_variant_id": row["window_variant_id"],
                "processing_profile_id":
                    row["processing_profile_id"],
                "baseline_formal_m1_period_s": baseline_period,
                "variant_formal_m1_period_s": variant_period,
                "signed_period_change_s": signed,
                "absolute_period_change_s": abs(signed),
                "relative_period_change":
                    abs(signed) / abs(baseline_period),
                "period_label": "recovered_period_selected",
            })
        elif (
            row["primary_outcome"] == "NOT_SELECTED"
            and row["formal_m1_period_s"] != ""
        ):
            if row["period_label"] != "formal_m1_center_not_selected":
                raise RuntimeError(
                    "Non-selected formal center has an invalid label."
                )
            formal_nonselected_centers.append({
                "event_id": row["event_id"],
                "observational_role": row["observational_role"],
                "window_variant_id": row["window_variant_id"],
                "processing_profile_id":
                    row["processing_profile_id"],
                "formal_m1_period_s":
                    float(row["formal_m1_period_s"]),
                "period_label": row["period_label"],
            })

    # ---------------------------------------------------------------------
    # Event summary
    # ---------------------------------------------------------------------

    event_summary_rows = []
    period_by_event = defaultdict(list)
    for row in period_rows:
        period_by_event[row["event_id"]].append(
            row["absolute_period_change_s"]
        )

    for event_id in event_order:
        rows = [
            row for row in enriched_rows
            if row["event_id"] == event_id
        ]
        status_counts = Counter(
            row["baseline_comparison_status"] for row in rows
        )
        margin_values = [
            float(row["joint_margin"])
            for row in rows
            if row["joint_margin"] != ""
        ]
        period_stats = describe(period_by_event[event_id])
        changed_rows = [
            row for row in rows
            if row["baseline_comparison_status"]
            in {"SELECTION_LOST", "SELECTION_GAINED"}
        ]
        event_summary_rows.append({
            "event_id": event_id,
            "pair_id": rows[0]["pair_id"],
            "observational_role": rows[0]["observational_role"],
            "baseline_qpp_selected":
                baseline_by_event[event_id]["qpp_selected"],
            "planned_variants": 78,
            "eligible_variants": sum(
                row["primary_outcome"]
                not in {"INPUT_INADMISSIBLE"}
                for row in rows
            ),
            "inadmissible_variants": sum(
                row["primary_outcome"] == "INPUT_INADMISSIBLE"
                for row in rows
            ),
            "selected_variants": sum(
                row["primary_outcome"] == "SELECTED"
                for row in rows
            ),
            "not_selected_variants": sum(
                row["primary_outcome"] == "NOT_SELECTED"
                for row in rows
            ),
            "incomplete_numerical_variants": sum(
                row["primary_outcome"] == "INCOMPLETE_NUMERICAL"
                for row in rows
            ),
            "selected_retained_n":
                status_counts["SELECTED_RETAINED"],
            "selection_lost_n": status_counts["SELECTION_LOST"],
            "not_selected_retained_n":
                status_counts["NOT_SELECTED_RETAINED"],
            "selection_gained_n": status_counts["SELECTION_GAINED"],
            "irregular_sampling_n": sum(
                row["admissibility_status"] == "IRREGULAR_SAMPLING"
                for row in rows
            ),
            "too_few_cadences_n": sum(
                row["admissibility_status"] == "TOO_FEW_CADENCES"
                for row in rows
            ),
            "peak_removed_by_quality_n": sum(
                row["admissibility_status"]
                == "PEAK_REMOVED_BY_QUALITY"
                for row in rows
            ),
            "profiles_with_classification_changes":
                sorted_join(
                    (
                        row["processing_profile_id"]
                        for row in changed_rows
                    ),
                    profile_order,
                ),
            "windows_with_classification_changes":
                sorted_join(
                    (row["window_variant_id"] for row in changed_rows),
                    window_order,
                ),
            "joint_margin_min":
                csv_value(min(margin_values) if margin_values else None),
            "joint_margin_max":
                csv_value(max(margin_values) if margin_values else None),
            "periods_comparable_n": period_stats["n"],
            "absolute_period_change_min_s":
                csv_value(period_stats["minimum"]),
            "absolute_period_change_median_s":
                csv_value(period_stats["median"]),
            "absolute_period_change_max_s":
                csv_value(period_stats["maximum"]),
        })

    # ---------------------------------------------------------------------
    # Pair summary
    # ---------------------------------------------------------------------

    event_summary_by_event = {
        row["event_id"]: row for row in event_summary_rows
    }
    pair_summary_rows = []
    for pair_id in pair_order:
        pair_cohort = [
            row for row in cohort if row["pair_id"] == pair_id
        ]
        published = next(
            row for row in pair_cohort
            if row["observational_role"]
            == "PUBLISHED_QPP_REPRODUCED"
        )
        control = next(
            row for row in pair_cohort
            if row["observational_role"]
            == "MATCHED_NOT_SELECTED"
        )
        pub_summary = event_summary_by_event[published["event_id"]]
        ctl_summary = event_summary_by_event[control["event_id"]]

        both_eligible = 0
        both_inadmissible = 0
        one_inadmissible = 0
        same_selection = 0
        different_selection = 0
        for window_id in window_order:
            for profile_id in profile_order:
                left = enriched_by_key[(
                    published["event_id"],
                    window_id,
                    profile_id,
                )]
                right = enriched_by_key[(
                    control["event_id"],
                    window_id,
                    profile_id,
                )]
                left_inad = (
                    left["primary_outcome"] == "INPUT_INADMISSIBLE"
                )
                right_inad = (
                    right["primary_outcome"] == "INPUT_INADMISSIBLE"
                )
                if left_inad and right_inad:
                    both_inadmissible += 1
                elif left_inad or right_inad:
                    one_inadmissible += 1
                elif (
                    left["primary_outcome"] == "INCOMPLETE_NUMERICAL"
                    or right["primary_outcome"] == "INCOMPLETE_NUMERICAL"
                ):
                    continue
                else:
                    both_eligible += 1
                    if (
                        parse_bool(left["qpp_selected"])
                        == parse_bool(right["qpp_selected"])
                    ):
                        same_selection += 1
                    else:
                        different_selection += 1

        pair_summary_rows.append({
            "pair_id": pair_id,
            "published_event_id": published["event_id"],
            "published_baseline_qpp_selected":
                pub_summary["baseline_qpp_selected"],
            "published_planned_variants":
                pub_summary["planned_variants"],
            "published_eligible_variants":
                pub_summary["eligible_variants"],
            "published_inadmissible_variants":
                pub_summary["inadmissible_variants"],
            "published_selected_variants":
                pub_summary["selected_variants"],
            "published_not_selected_variants":
                pub_summary["not_selected_variants"],
            "published_selection_retained_n":
                pub_summary["selected_retained_n"],
            "published_selection_lost_n":
                pub_summary["selection_lost_n"],
            "control_event_id": control["event_id"],
            "control_baseline_qpp_selected":
                ctl_summary["baseline_qpp_selected"],
            "control_planned_variants":
                ctl_summary["planned_variants"],
            "control_eligible_variants":
                ctl_summary["eligible_variants"],
            "control_inadmissible_variants":
                ctl_summary["inadmissible_variants"],
            "control_selected_variants":
                ctl_summary["selected_variants"],
            "control_not_selected_variants":
                ctl_summary["not_selected_variants"],
            "control_not_selected_retained_n":
                ctl_summary["not_selected_retained_n"],
            "control_selection_gained_n":
                ctl_summary["selection_gained_n"],
            "same_variant_both_eligible_n": both_eligible,
            "same_variant_both_inadmissible_n": both_inadmissible,
            "same_variant_one_inadmissible_n": one_inadmissible,
            "same_variant_selection_same_n": same_selection,
            "same_variant_selection_different_n": different_selection,
            "pair_metric_interpretation":
                "descriptive_members_kept_separate",
        })

    # ---------------------------------------------------------------------
    # Window/profile summary
    # ---------------------------------------------------------------------

    window_profile_summary_rows = []
    for role in ROLE_ORDER:
        role_events = [
            row["event_id"] for row in cohort
            if row["observational_role"] == role
        ]
        if len(role_events) != 5:
            raise RuntimeError("Each role must contain five events.")
        for window_id in window_order:
            for profile_id in profile_order:
                rows = [
                    enriched_by_key[(event_id, window_id, profile_id)]
                    for event_id in role_events
                ]
                eligible = [
                    row for row in rows
                    if row["primary_outcome"]
                    not in {"INPUT_INADMISSIBLE"}
                ]
                valid_eligible = [
                    row for row in eligible
                    if row["primary_outcome"]
                    != "INCOMPLETE_NUMERICAL"
                ]
                selected_n = sum(
                    row["primary_outcome"] == "SELECTED"
                    for row in valid_eligible
                )
                not_selected_n = sum(
                    row["primary_outcome"] == "NOT_SELECTED"
                    for row in valid_eligible
                )
                concordant_n = sum(
                    row["baseline_comparison_status"]
                    in {
                        "SELECTED_RETAINED",
                        "NOT_SELECTED_RETAINED",
                    }
                    for row in valid_eligible
                )
                discordant_n = sum(
                    row["baseline_comparison_status"]
                    in {"SELECTION_LOST", "SELECTION_GAINED"}
                    for row in valid_eligible
                )
                eligible_n = len(valid_eligible)
                window_profile_summary_rows.append({
                    "observational_role": role,
                    "window_variant_id": window_id,
                    "processing_profile_id": profile_id,
                    "planned_n": 5,
                    "eligible_n": eligible_n,
                    "inadmissible_n": sum(
                        row["primary_outcome"]
                        == "INPUT_INADMISSIBLE"
                        for row in rows
                    ),
                    "incomplete_numerical_n": sum(
                        row["primary_outcome"]
                        == "INCOMPLETE_NUMERICAL"
                        for row in rows
                    ),
                    "selected_n": selected_n,
                    "not_selected_n": not_selected_n,
                    "baseline_concordant_n": concordant_n,
                    "baseline_discordant_n": discordant_n,
                    "eligibility_fraction": eligible_n / 5.0,
                    "selection_fraction_among_eligible":
                        "" if eligible_n == 0
                        else selected_n / eligible_n,
                    "baseline_concordance_among_eligible":
                        "" if eligible_n == 0
                        else concordant_n / eligible_n,
                })

    if len(window_profile_summary_rows) != 156:
        raise RuntimeError("Window/profile summary does not have 156 rows.")

    # ---------------------------------------------------------------------
    # Temporal window contrasts
    # ---------------------------------------------------------------------

    window_contrast_rows = []
    for event_id in event_order:
        cohort_row = cohort_by_event[event_id]
        for profile_id in profile_order:
            reference = enriched_by_key[(event_id, "W00", profile_id)]
            for window_id in window_order:
                if window_id == "W00":
                    continue
                variant = enriched_by_key[(
                    event_id,
                    window_id,
                    profile_id,
                )]
                comparison = compare_rows(reference, variant)
                if (
                    comparison["comparability_status"]
                    not in COMPARABILITY_STATUSES
                ):
                    raise RuntimeError("Invalid comparability status.")
                window_contrast_rows.append({
                    "event_id": event_id,
                    "pair_id": cohort_row["pair_id"],
                    "observational_role":
                        cohort_row["observational_role"],
                    "processing_profile_id": profile_id,
                    "reference_window_variant_id": "W00",
                    "variant_window_variant_id": window_id,
                    "reference_variant_id": reference["variant_id"],
                    "variant_id": variant["variant_id"],
                    "reference_primary_outcome":
                        reference["primary_outcome"],
                    "variant_primary_outcome":
                        variant["primary_outcome"],
                    "reference_admissibility_status":
                        reference["admissibility_status"],
                    "variant_admissibility_status":
                        variant["admissibility_status"],
                    "reference_inadmissibility_reason":
                        reference["inadmissibility_reason"],
                    "variant_inadmissibility_reason":
                        variant["inadmissibility_reason"],
                    **comparison,
                })

    if len(window_contrast_rows) != 720:
        raise RuntimeError("Window contrast table does not have 720 rows.")

    window_contrast_summary = []
    for role in ROLE_ORDER:
        for profile_id in profile_order:
            for window_id in window_order:
                if window_id == "W00":
                    continue
                rows = [
                    row for row in window_contrast_rows
                    if row["observational_role"] == role
                    and row["processing_profile_id"] == profile_id
                    and row["variant_window_variant_id"] == window_id
                ]
                transitions = Counter(
                    row["selection_transition"]
                    for row in rows
                    if row["comparability_status"] == "BOTH_ELIGIBLE"
                )
                statuses = Counter(
                    row["comparability_status"] for row in rows
                )
                window_contrast_summary.append({
                    "observational_role": role,
                    "processing_profile_id": profile_id,
                    "variant_window_variant_id": window_id,
                    "planned_events": 5,
                    "both_eligible_n": statuses["BOTH_ELIGIBLE"],
                    "reference_inadmissible_n":
                        statuses["REFERENCE_INADMISSIBLE"],
                    "variant_inadmissible_n":
                        statuses["VARIANT_INADMISSIBLE"],
                    "both_inadmissible_n":
                        statuses["BOTH_INADMISSIBLE"],
                    "incomplete_numerical_n":
                        statuses["INCOMPLETE_NUMERICAL"],
                    "transition_0_to_0": transitions["0→0"],
                    "transition_0_to_1": transitions["0→1"],
                    "transition_1_to_0": transitions["1→0"],
                    "transition_1_to_1": transitions["1→1"],
                })

    # ---------------------------------------------------------------------
    # Processing-profile contrasts
    # ---------------------------------------------------------------------

    processing_contrast_rows = []
    for event_id in event_order:
        cohort_row = cohort_by_event[event_id]
        for window_id in window_order:
            for contrast_id, left_profile, right_profile in (
                PROCESSING_CONTRASTS
            ):
                left = enriched_by_key[(
                    event_id,
                    window_id,
                    left_profile,
                )]
                right = enriched_by_key[(
                    event_id,
                    window_id,
                    right_profile,
                )]
                comparison = compare_rows(left, right)
                processing_contrast_rows.append({
                    "contrast_id": contrast_id,
                    "event_id": event_id,
                    "pair_id": cohort_row["pair_id"],
                    "observational_role":
                        cohort_row["observational_role"],
                    "window_variant_id": window_id,
                    "left_processing_profile_id": left_profile,
                    "right_processing_profile_id": right_profile,
                    "left_variant_id": left["variant_id"],
                    "right_variant_id": right["variant_id"],
                    "left_primary_outcome": left["primary_outcome"],
                    "right_primary_outcome": right["primary_outcome"],
                    "left_admissibility_status":
                        left["admissibility_status"],
                    "right_admissibility_status":
                        right["admissibility_status"],
                    "left_inadmissibility_reason":
                        left["inadmissibility_reason"],
                    "right_inadmissibility_reason":
                        right["inadmissibility_reason"],
                    **comparison,
                })

    if len(processing_contrast_rows) != 780:
        raise RuntimeError(
            "Processing contrast table does not have 780 rows."
        )

    processing_contrast_summary = []
    for role in ROLE_ORDER:
        for contrast_id, _, _ in PROCESSING_CONTRASTS:
            rows = [
                row for row in processing_contrast_rows
                if row["observational_role"] == role
                and row["contrast_id"] == contrast_id
            ]
            statuses = Counter(
                row["comparability_status"] for row in rows
            )
            transitions = Counter(
                row["selection_transition"]
                for row in rows
                if row["comparability_status"] == "BOTH_ELIGIBLE"
            )
            processing_contrast_summary.append({
                "observational_role": role,
                "contrast_id": contrast_id,
                "planned_comparisons": 65,
                "both_eligible_n": statuses["BOTH_ELIGIBLE"],
                "reference_inadmissible_n":
                    statuses["REFERENCE_INADMISSIBLE"],
                "variant_inadmissible_n":
                    statuses["VARIANT_INADMISSIBLE"],
                "both_inadmissible_n":
                    statuses["BOTH_INADMISSIBLE"],
                "incomplete_numerical_n":
                    statuses["INCOMPLETE_NUMERICAL"],
                "transition_0_to_0": transitions["0→0"],
                "transition_0_to_1": transitions["0→1"],
                "transition_1_to_0": transitions["1→0"],
                "transition_1_to_1": transitions["1→1"],
            })

    # ---------------------------------------------------------------------
    # Optimizer stability
    # ---------------------------------------------------------------------

    w00_eligible = [
        row for row in manifest
        if row["window_variant_id"] == "W00"
        and row["admissibility_status"] == "ELIGIBLE_FOR_AFINO"
    ]
    w00_eligible.sort(
        key=lambda row: (
            event_order.index(row["event_id"]),
            profile_order.index(row["processing_profile_id"]),
        )
    )
    if len(w00_eligible) != 46:
        raise RuntimeError("Eligible W00 variant count is not 46.")

    optimizer_rows = []
    for variant in w00_eligible:
        variant_id = variant["variant_id"]
        ten_decisions = [
            decision_by_variant_seed.get((variant_id, seed))
            for seed in range(10)
        ]
        if any(item is None for item in ten_decisions):
            raise RuntimeError(
                f"Missing seed 0–9 decision for {variant_id}."
            )
        ten_decisions = [item for item in ten_decisions if item is not None]
        if len(ten_decisions) != 10:
            raise RuntimeError("Stability decision count is not ten.")

        classifications = [
            parse_bool(item["qpp_selected"]) for item in ten_decisions
        ]
        seed0_classification = classifications[0]
        selected_periods = [
            float(item["formal_m1_period_s"])
            for item in ten_decisions
            if parse_bool(item["qpp_selected"])
            and item["formal_m1_period_s"] != ""
        ]
        all_formal_periods = [
            float(item["formal_m1_period_s"])
            for item in ten_decisions
            if item["formal_m1_period_s"] != ""
        ]

        model_results = {
            model: [
                result_by_variant_seed_model[(variant_id, seed, model)]
                for seed in range(10)
            ]
            for model in ("M0", "M1", "M2")
        }

        optimizer_rows.append({
            "variant_id": variant_id,
            "event_id": variant["event_id"],
            "pair_id": variant["pair_id"],
            "observational_role": variant["observational_role"],
            "processing_profile_id":
                variant["processing_profile_id"],
            "decision_count": 10,
            "selected_seed_count": sum(classifications),
            "not_selected_seed_count":
                10 - sum(classifications),
            "decision_discordance":
                len(set(classifications)) > 1,
            "seed0_agreement_count": sum(
                value == seed0_classification
                for value in classifications
            ),
            "bic_m0_range": range_value([
                float(item["bic_m0"]) for item in ten_decisions
            ]),
            "bic_m1_range": range_value([
                float(item["bic_m1"]) for item in ten_decisions
            ]),
            "bic_m2_range": range_value([
                float(item["bic_m2"]) for item in ten_decisions
            ]),
            "formal_m1_period_range_s":
                csv_value(range_value(all_formal_periods)),
            "selected_period_seed_count": len(selected_periods),
            "recovered_period_range_selected_seeds_s":
                csv_value(range_value(selected_periods)),
            "m0_unique_parameter_payloads": len({
                item["parameters_json"]
                for item in model_results["M0"]
            }),
            "m1_unique_parameter_payloads": len({
                item["parameters_json"]
                for item in model_results["M1"]
            }),
            "m2_unique_parameter_payloads": len({
                item["parameters_json"]
                for item in model_results["M2"]
            }),
            "warning_seed_count_m0": sum(
                int(item["warning_count"]) > 0
                for item in model_results["M0"]
            ),
            "warning_seed_count_m1": sum(
                int(item["warning_count"]) > 0
                for item in model_results["M1"]
            ),
            "warning_seed_count_m2": sum(
                int(item["warning_count"]) > 0
                for item in model_results["M2"]
            ),
            "bound_seed_count_m0": sum(
                parse_bool(item["parameter_at_bound"])
                for item in model_results["M0"]
            ),
            "bound_seed_count_m1": sum(
                parse_bool(item["parameter_at_bound"])
                for item in model_results["M1"]
            ),
            "bound_seed_count_m2": sum(
                parse_bool(item["parameter_at_bound"])
                for item in model_results["M2"]
            ),
        })

    if len(optimizer_rows) != 46:
        raise RuntimeError("Optimizer summary does not have 46 rows.")
    if sum(row["decision_count"] for row in optimizer_rows) != 460:
        raise RuntimeError("Optimizer seed 0–9 decision count is not 460.")

    # ---------------------------------------------------------------------
    # Model diagnostics
    # ---------------------------------------------------------------------

    model_diagnostic_rows = []
    for model in ("M0", "M1", "M2"):
        for profile_id in profile_order:
            for role in ROLE_ORDER:
                rows = [
                    row for row in results
                    if row["model_id"] == model
                    and row["processing_profile_id"] == profile_id
                    and row["observational_role"] == role
                ]
                runtimes = [
                    float(row["runtime_seconds"]) for row in rows
                ]
                status_counts = Counter(row["status"] for row in rows)
                convergence_counts = Counter(
                    row["convergence_status"] for row in rows
                )
                model_diagnostic_rows.append({
                    "model_id": model,
                    "processing_profile_id": profile_id,
                    "observational_role": role,
                    "call_count": len(rows),
                    "warning_call_count": sum(
                        int(row["warning_count"]) > 0
                        for row in rows
                    ),
                    "warning_total": sum(
                        int(row["warning_count"]) for row in rows
                    ),
                    "bound_hit_call_count": sum(
                        parse_bool(row["parameter_at_bound"])
                        for row in rows
                    ),
                    "ok_call_count": status_counts["OK"],
                    "error_call_count":
                        len(rows) - status_counts["OK"],
                    "runtime_total_seconds": sum(runtimes),
                    "runtime_median_seconds":
                        float(np.median(runtimes)) if runtimes else "",
                    "convergence_status_counts_json":
                        json.dumps(
                            dict(convergence_counts),
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                })

    if len(model_diagnostic_rows) != 36:
        raise RuntimeError("Model diagnostics do not have 36 rows.")

    diagnostics_by_model_window = []
    for model in ("M0", "M1", "M2"):
        for window_id in window_order:
            rows = [
                row for row in results
                if row["model_id"] == model
                and row["window_variant_id"] == window_id
            ]
            diagnostics_by_model_window.append({
                "model_id": model,
                "window_variant_id": window_id,
                "call_count": len(rows),
                "warning_call_count": sum(
                    int(row["warning_count"]) > 0
                    for row in rows
                ),
                "warning_total": sum(
                    int(row["warning_count"]) for row in rows
                ),
                "bound_hit_call_count": sum(
                    parse_bool(row["parameter_at_bound"])
                    for row in rows
                ),
            })

    # ---------------------------------------------------------------------
    # Stage outputs
    # ---------------------------------------------------------------------

    staging = Path(tempfile.mkdtemp(
        prefix=".fase2_tarea05_staging_",
        dir=output_dir,
    ))

    try:
        enriched_fields = [
            "planned_decision_id", "variant_id", "event_id", "pair_id",
            "observational_role", "window_variant_id",
            "processing_profile_id", "admissibility_status",
            "inadmissibility_reason", "primary_outcome", "bic_m0",
            "bic_m1", "bic_m2", "delta_bic_0_1", "delta_bic_2_1",
            "qpp_selected", "formal_m1_period_s", "period_label",
            "margin_vs_m0", "margin_vs_m2", "joint_margin",
            "baseline_qpp_selected", "baseline_formal_m1_period_s",
            "baseline_comparison_status",
        ]
        write_csv(
            staging / OUTPUT_NAMES[0],
            enriched_fields,
            enriched_rows,
        )
        write_csv(
            staging / OUTPUT_NAMES[1],
            list(event_summary_rows[0]),
            event_summary_rows,
        )
        write_csv(
            staging / OUTPUT_NAMES[2],
            list(pair_summary_rows[0]),
            pair_summary_rows,
        )
        write_csv(
            staging / OUTPUT_NAMES[3],
            list(window_profile_summary_rows[0]),
            window_profile_summary_rows,
        )
        write_csv(
            staging / OUTPUT_NAMES[4],
            list(window_contrast_rows[0]),
            window_contrast_rows,
        )
        write_csv(
            staging / OUTPUT_NAMES[5],
            list(processing_contrast_rows[0]),
            processing_contrast_rows,
        )
        write_csv(
            staging / OUTPUT_NAMES[6],
            list(optimizer_rows[0]),
            optimizer_rows,
        )
        period_fields = [
            "planned_decision_id", "variant_id", "event_id", "pair_id",
            "observational_role", "window_variant_id",
            "processing_profile_id", "baseline_formal_m1_period_s",
            "variant_formal_m1_period_s", "signed_period_change_s",
            "absolute_period_change_s", "relative_period_change",
            "period_label",
        ]
        write_csv(
            staging / OUTPUT_NAMES[7],
            period_fields,
            period_rows,
        )
        write_csv(
            staging / OUTPUT_NAMES[8],
            list(model_diagnostic_rows[0]),
            model_diagnostic_rows,
        )

        # -----------------------------------------------------------------
        # Figures: one axes per figure, no subplots
        # -----------------------------------------------------------------

        # 1. Primary outcome matrix
        state_code = {
            "SELECTED": 0,
            "NOT_SELECTED": 1,
            "INPUT_INADMISSIBLE": 2,
            "INCOMPLETE_NUMERICAL": 3,
        }
        matrix = np.zeros((10, 78), dtype=np.int64)
        for event_index, event_id in enumerate(event_order):
            column = 0
            for window_id in window_order:
                for profile_id in profile_order:
                    matrix[event_index, column] = state_code[
                        enriched_by_key[(
                            event_id,
                            window_id,
                            profile_id,
                        )]["primary_outcome"]
                    ]
                    column += 1

        fig, ax = plt.subplots(figsize=(24, 6))
        image = ax.imshow(
            matrix,
            aspect="auto",
            vmin=0,
            vmax=3,
            interpolation="nearest",
        )
        ax.set_yticks(range(len(event_order)))
        ax.set_yticklabels(event_order, fontsize=8)
        centers = [
            index * len(profile_order) + (len(profile_order) - 1) / 2
            for index in range(len(window_order))
        ]
        ax.set_xticks(centers)
        ax.set_xticklabels(window_order, rotation=45, ha="right")
        for index in range(1, len(window_order)):
            ax.axvline(
                index * len(profile_order) - 0.5,
                linewidth=0.5,
            )
        ax.set_xlabel(
            "Ventanas en orden congelado; dentro de cada ventana P00–P05"
        )
        ax.set_ylabel("Eventos en orden congelado F2.1")
        ax.set_title(
            "Estados de las 780 variantes primarias "
            "(inadmisibilidad separada de no selección)"
        )
        colorbar = fig.colorbar(image, ax=ax, ticks=[0, 1, 2, 3])
        colorbar.ax.set_yticklabels([
            "SELECTED",
            "NOT_SELECTED",
            "INPUT_INADMISSIBLE",
            "INCOMPLETE_NUMERICAL",
        ])
        fig.tight_layout()
        fig.savefig(
            staging / OUTPUT_NAMES[9],
            dpi=180,
            bbox_inches="tight",
        )
        plt.close(fig)

        # 2. Baseline transitions by role
        categories = [
            "SELECTED_RETAINED",
            "SELECTION_LOST",
            "NOT_SELECTED_RETAINED",
            "SELECTION_GAINED",
            "INPUT_INADMISSIBLE",
            "INCOMPLETE_NUMERICAL",
        ]
        role_counts = {
            role: Counter(
                row["baseline_comparison_status"]
                for row in enriched_rows
                if row["observational_role"] == role
            )
            for role in ROLE_ORDER
        }
        fig, ax = plt.subplots(figsize=(11, 7))
        x = np.arange(len(ROLE_ORDER))
        bottoms = np.zeros(len(ROLE_ORDER), dtype=float)
        for category in categories:
            heights = np.asarray([
                role_counts[role][category] for role in ROLE_ORDER
            ], dtype=float)
            bars = ax.bar(
                x,
                heights,
                bottom=bottoms,
                label=category,
            )
            for bar, height, bottom in zip(bars, heights, bottoms):
                if height > 0:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bottom + height / 2,
                        str(int(height)),
                        ha="center",
                        va="center",
                        fontsize=8,
                    )
            bottoms += heights
        ax.set_xticks(x)
        ax.set_xticklabels(ROLE_ORDER)
        ax.set_ylabel("Variantes primarias (n)")
        ax.set_title(
            "Cambios de clasificación respecto al baseline, "
            "separados por rol observacional"
        )
        ax.legend(loc="upper right", fontsize=8)
        fig.tight_layout()
        fig.savefig(
            staging / OUTPUT_NAMES[10],
            dpi=180,
            bbox_inches="tight",
        )
        plt.close(fig)

        # 3. Processing contrast comparability
        contrast_ids = [item[0] for item in PROCESSING_CONTRASTS]
        summary_lookup = {
            (row["observational_role"], row["contrast_id"]): row
            for row in processing_contrast_summary
        }
        fig, ax = plt.subplots(figsize=(13, 7))
        x = np.arange(len(contrast_ids))
        width = 0.36
        for role_index, role in enumerate(ROLE_ORDER):
            offset = (role_index - 0.5) * width
            values = [
                summary_lookup[(role, contrast_id)]["both_eligible_n"]
                for contrast_id in contrast_ids
            ]
            bars = ax.bar(
                x + offset,
                values,
                width=width,
                label=role,
            )
            for bar, contrast_id in zip(bars, contrast_ids):
                summary = summary_lookup[(role, contrast_id)]
                changes = (
                    summary["transition_0_to_1"]
                    + summary["transition_1_to_0"]
                )
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 1,
                    f"n={int(bar.get_height())}\nchg={changes}",
                    ha="center",
                    va="bottom",
                    fontsize=7,
                )
        ax.set_xticks(x)
        ax.set_xticklabels(contrast_ids, rotation=25, ha="right")
        ax.set_ylabel("Comparaciones BOTH_ELIGIBLE")
        ax.set_title(
            "Contrastes de procesamiento: pares comparables "
            "y cambios de clasificación"
        )
        ax.legend()
        fig.tight_layout()
        fig.savefig(
            staging / OUTPUT_NAMES[11],
            dpi=180,
            bbox_inches="tight",
        )
        plt.close(fig)

        # 4. Optimizer and recovered-period stability
        selected_optimizer_rows = [
            row for row in optimizer_rows
            if row["selected_period_seed_count"] > 0
        ]
        fig, ax = plt.subplots(figsize=(12, 7))
        event_offsets = {
            event_id:
                (index - (len(event_order) - 1) / 2) * 0.035
            for index, event_id in enumerate(event_order)
        }
        marker_by_role = {
            "PUBLISHED_QPP_REPRODUCED": "o",
            "MATCHED_NOT_SELECTED": "s",
        }
        for role in ROLE_ORDER:
            rows = [
                row for row in selected_optimizer_rows
                if row["observational_role"] == role
            ]
            if not rows:
                continue
            x_values = [
                profile_order.index(row["processing_profile_id"])
                + event_offsets[row["event_id"]]
                for row in rows
            ]
            y_values = [
                float(row["recovered_period_range_selected_seeds_s"])
                for row in rows
            ]
            ax.scatter(
                x_values,
                y_values,
                marker=marker_by_role[role],
                label=role,
            )
        ax.set_xticks(range(len(profile_order)))
        ax.set_xticklabels(profile_order)
        ax.set_ylabel(
            "Rango del periodo recuperado entre seeds seleccionadas (s)"
        )
        ax.set_xlabel("Perfil de procesamiento W00")
        discordant_n = sum(
            parse_bool(row["decision_discordance"])
            for row in optimizer_rows
        )
        always_selected_n = sum(
            int(row["selected_seed_count"]) == 10
            for row in optimizer_rows
        )
        never_selected_n = sum(
            int(row["selected_seed_count"]) == 0
            for row in optimizer_rows
        )
        ax.set_title(
            "Estabilidad frente a seed y dispersión del periodo "
            "solo para decisiones seleccionadas"
        )
        ax.text(
            0.02,
            0.98,
            (
                f"Discordancia de clasificación: {discordant_n}/46\n"
                f"10/10 seleccionadas: {always_selected_n}; "
                f"0/10 seleccionadas: {never_selected_n}\n"
                "Los centros M1 no seleccionados no se representan "
                "como periodos recuperados."
            ),
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=9,
        )
        ax.legend()
        ax.ticklabel_format(
            axis="y",
            style="sci",
            scilimits=(-3, 3),
        )
        fig.tight_layout()
        fig.savefig(
            staging / OUTPUT_NAMES[12],
            dpi=180,
            bbox_inches="tight",
        )
        plt.close(fig)

        # -----------------------------------------------------------------
        # Audit and report
        # -----------------------------------------------------------------

        baseline_status_counts = Counter(
            row["baseline_comparison_status"]
            for row in enriched_rows
        )
        window_comparability_counts = Counter(
            row["comparability_status"] for row in window_contrast_rows
        )
        window_transition_counts = Counter(
            row["selection_transition"]
            for row in window_contrast_rows
            if row["comparability_status"] == "BOTH_ELIGIBLE"
        )
        processing_comparability_counts = Counter(
            row["comparability_status"]
            for row in processing_contrast_rows
        )
        processing_transition_counts = Counter(
            row["selection_transition"]
            for row in processing_contrast_rows
            if row["comparability_status"] == "BOTH_ELIGIBLE"
        )
        optimizer_selected_counts = Counter(
            int(row["selected_seed_count"]) for row in optimizer_rows
        )
        period_change_stats = describe([
            float(row["absolute_period_change_s"])
            for row in period_rows
        ])
        optimizer_selected_period_ranges = describe([
            float(row["recovered_period_range_selected_seeds_s"])
            for row in optimizer_rows
            if row["recovered_period_range_selected_seeds_s"] != ""
        ])
        nonselected_center_counts = Counter(
            row["observational_role"]
            for row in formal_nonselected_centers
        )

        input_hashes_after = source_hashes(input_dir)
        if input_hashes_before != input_hashes_after:
            raise RuntimeError("Frozen inputs changed during F2.5.")

        preliminary_outputs = [
            staging / name for name in OUTPUT_NAMES[:13]
        ]
        preliminary_hashes = {
            path.name: sha256(path) for path in preliminary_outputs
        }

        audit = {
            "date_utc": utc_now(),
            "analysis_conclusion": ANALYSIS_CONCLUSION,
            "cohort_events": 10,
            "cohort_pairs": 5,
            "published_reproduced_events": 5,
            "matched_not_selected_events": 5,
            "primary_planned_variants": 780,
            "primary_eligible_variants": 514,
            "primary_inadmissible_variants": 266,
            "primary_decisions_linked": 514,
            "primary_outcome_counts": dict(primary_counts),
            "inadmissibility_status_counts":
                dict(inadmissible_status_counts),
            "stability_variants": 46,
            "stability_decisions_seed_0_to_9": 460,
            "stability_decisions_seed_1_to_9": 414,
            "stability_selected_seed_count_distribution":
                dict(sorted(optimizer_selected_counts.items())),
            "stability_decision_discordant_variants": sum(
                parse_bool(row["decision_discordance"])
                for row in optimizer_rows
            ),
            "baseline_rows": 10,
            "baseline_classification_mismatches":
                baseline_classification_mismatches,
            "baseline_numeric_mismatches":
                baseline_numeric_mismatches,
            "baseline_period_label_mismatches":
                baseline_period_label_mismatches,
            "baseline_bic_reference_fields_available":
                frozen_bic_fields_available,
            "baseline_bic_comparison_status":
                (
                    "COMPARED"
                    if frozen_bic_fields_available
                    else "NOT_AVAILABLE_IN_FROZEN_COHORT_FIELDS"
                ),
            "baseline_verification_records": baseline_records,
            "decision_recalculation_mismatches":
                decision_recalculation_mismatches,
            "duplicate_primary_variant_ids":
                duplicate_primary_variant_ids,
            "baseline_comparison_status_counts":
                dict(baseline_status_counts),
            "window_contrast_rows": len(window_contrast_rows),
            "window_contrast_comparability_counts":
                dict(window_comparability_counts),
            "window_contrast_transition_counts":
                dict(window_transition_counts),
            "window_contrast_summary_by_role_profile_window":
                window_contrast_summary,
            "processing_contrast_rows":
                len(processing_contrast_rows),
            "processing_contrast_comparability_counts":
                dict(processing_comparability_counts),
            "processing_contrast_transition_counts":
                dict(processing_transition_counts),
            "processing_contrast_summary_by_role_and_contrast":
                processing_contrast_summary,
            "period_robustness_rows": len(period_rows),
            "period_absolute_change_summary": period_change_stats,
            "formal_m1_center_not_selected_count":
                len(formal_nonselected_centers),
            "formal_m1_center_not_selected_counts_by_role":
                dict(nonselected_center_counts),
            "optimizer_recovered_period_range_selected_seeds_summary":
                optimizer_selected_period_ranges,
            "model_diagnostics_by_model_window":
                diagnostics_by_model_window,
            "statistical_scope": {
                "allowed": [
                    "explicit counts and denominators",
                    "descriptive proportions",
                    "median",
                    "Q1 and Q3",
                    "minimum and maximum",
                    "paired transition tables",
                ],
                "not_used": [
                    "p-values",
                    "confidence intervals over 780 repeated variants",
                    "inferential regression",
                    "global independence assumption",
                    "accuracy",
                    "sensitivity",
                    "specificity",
                    "false positive rate",
                    "false negative rate",
                ],
                "observational_unit": "event",
                "repeated_measures":
                    ["windows", "processing profiles", "optimizer seeds"],
            },
            "input_hashes_before": input_hashes_before,
            "input_hashes_after": input_hashes_after,
            "input_hashes_unchanged": True,
            "output_hashes_before_audit_and_report":
                preliminary_hashes,
            "confirmations": {
                "afino_executed": False,
                "fits_opened": False,
                "variants_regenerated": False,
                "quality_reapplied": False,
                "detrending_recomputed": False,
                "interpolation_performed": False,
                "new_candidates_added": False,
                "candidate_discovery_authorized": False,
                "observational_ground_truth_established": False,
                "sensitivity_estimated": False,
                "specificity_estimated": False,
                "observational_false_positive_rate_estimated": False,
                "physical_qpp_truth_inferred": False,
                "robustness_threshold_added": False,
                "events_removed": False,
                "inadmissible_variants_removed": False,
            },
            "limitations": [
                "The frozen cohort contains ten events and five matched pairs.",
                "Windows, profiles and seeds are repeated measures within events.",
                "The F2.1 frozen cohort does not contain individual baseline BIC_M0, BIC_M1 and BIC_M2 fields; current baseline BICs are recorded but not treated as independently frozen references.",
                "Input inadmissibility is substantial and remains separate from non-selection.",
                "Formal M1 centers of non-selected decisions are not interpreted as recovered periods.",
                "Parameter multiplicity is a numerical diagnostic only.",
            ],
        }

        report = f"""# Fase 2 — Tarea 2.5

## Análisis de robustez de la cohorte observacional congelada

**Conclusión:** `{ANALYSIS_CONCLUSION}`

### 1. Admisibilidad de los inputs

El análisis reconstruyó las 780 variantes primarias previstas: diez eventos,
trece ventanas y seis perfiles. De ellas, 514 fueron evaluadas por AFINO en
F2.4 y 266 permanecieron como `INPUT_INADMISSIBLE`. Estas últimas no se
convirtieron en no selecciones ni se retiraron de los denominadores
planificados. Las razones estructurales fueron 142 casos de
`IRREGULAR_SAMPLING`, 98 de `TOO_FEW_CADENCES` y 26 de
`PEAK_REMOVED_BY_QUALITY`. Entre las 514 decisiones evaluables hubo
{primary_counts['SELECTED']} selecciones,
{primary_counts['NOT_SELECTED']} no selecciones y
{primary_counts['INCOMPLETE_NUMERICAL']} resultados numéricamente
incompletos. Por tanto, toda proporción de selección se calculó únicamente
entre inputs elegibles y conserva su denominador explícito.

### 2. Estabilidad de clasificación respecto al baseline

Las diez filas W00/P00 con seed 0 reprodujeron exactamente la clasificación
congelada F2.1. También coincidieron, con tolerancia absoluta de 5×10⁻¹², los
dos deltas BIC y el centro formal de M1; las etiquetas de periodo se
reconstruyeron desde `baseline_qpp_selected` y la regla prerregistrada, no
desde el rol observacional. La cohorte F2.1 no contiene BIC individuales de
M0, M1 y M2, por lo que esos tres valores actuales se registraron pero no se
presentaron como una comparación independiente congelada.

Respecto a cada baseline, hubo
{baseline_status_counts['SELECTED_RETAINED']} variantes con selección
retenida, {baseline_status_counts['SELECTION_LOST']} pérdidas de selección,
{baseline_status_counts['NOT_SELECTED_RETAINED']} no selecciones retenidas y
{baseline_status_counts['SELECTION_GAINED']} ganancias de selección. A ello
se añaden las 266 inadmisibles. Estos términos describen transiciones internas
de la cohorte, no aciertos, errores ni verdad física. Los resúmenes por
evento mantienen las 78 variantes previstas para cada observación y muestran
por separado cuántas fueron elegibles, inadmisibles, seleccionadas o no
seleccionadas. También identifican las ventanas y perfiles concretos en los
que la clasificación se apartó del baseline y conservan el rango de
`joint_margin`. Este nivel de presentación evita que un evento con muchas
variantes admisibles domine silenciosamente la descripción frente a otro con
más pérdidas por calidad o irregularidad temporal.

La tabla por pareja conserva igualmente dos bloques independientes, uno para
cada miembro. Solo añade conteos descriptivos de variantes homólogas en las
que ambos miembros fueron elegibles, ambos inadmisibles o solo uno de ellos
fue inadmisible. La coincidencia o diferencia entre clasificaciones de los
dos miembros no se interpreta como una medida de pareja correcta, porque los
roles observacionales no constituyen etiquetas físicas verdaderas.

### 3. Perturbaciones temporales

Los 720 contrastes compararon cada ventana no-W00 con W00 del mismo evento y
perfil. Fueron comparables como `BOTH_ELIGIBLE`
{window_comparability_counts['BOTH_ELIGIBLE']} contrastes; en
{window_comparability_counts['REFERENCE_INADMISSIBLE']} la referencia era
inadmisible, en {window_comparability_counts['VARIANT_INADMISSIBLE']} lo era
la variante y en {window_comparability_counts['BOTH_INADMISSIBLE']} lo eran
ambas. Entre los comparables se observaron
{window_transition_counts['0→0']} transiciones 0→0,
{window_transition_counts['0→1']} transiciones 0→1,
{window_transition_counts['1→0']} transiciones 1→0 y
{window_transition_counts['1→1']} transiciones 1→1. Estos 720 contrastes no
son replicaciones independientes: las ventanas son medidas repetidas dentro
de diez eventos. Los resúmenes por rol, perfil y ventana conservan cinco
eventos planificados por celda.

### 4. Perfiles de procesamiento

Los 780 contrastes prerregistrados cubrieron exactamente `FLUX_FINITE`,
`QUALITY_PDCSAP`, `QUALITY_SAP`, `DETREND_PDCSAP`, `DETREND_SAP` y
`FLUX_Q0`. Resultaron `BOTH_ELIGIBLE`
{processing_comparability_counts['BOTH_ELIGIBLE']} comparaciones; el resto
mantuvo por separado la inadmisibilidad de la referencia, de la variante o de
ambas. Entre los pares comparables hubo
{processing_transition_counts['0→0']} transiciones 0→0,
{processing_transition_counts['0→1']} transiciones 0→1,
{processing_transition_counts['1→0']} transiciones 1→0 y
{processing_transition_counts['1→1']} transiciones 1→1. No se añadieron
combinaciones de q0 con detrending ni perfiles no congelados. Las diferencias
son descriptivas y no atribuyen causalidad al producto de flujo, QUALITY o
detrending.

### 5. Estabilidad frente a seed externa

Las 46 variantes W00 elegibles se analizaron con seeds 0–9, para un total de
460 decisiones. No hubo discordancia de clasificación: 15 variantes fueron
seleccionadas con 10/10 seeds y 31 no fueron seleccionadas con 0/10 seeds.
Esto establece estabilidad de la decisión en este conjunto congelado, pero
no unicidad del resultado numérico. En los tres modelos, cada variante mostró
diez payloads de parámetros distintos entre las diez seeds. Por tanto,
`stable classification ≠ unique numerical optimum`: la multiplicidad de
parámetros se conserva como diagnóstico numérico, no como demostración de
óptimos físicos distintos.

### 6. Periodo recuperado y centro formal no seleccionado

La tabla de robustez del periodo contiene {len(period_rows)} filas en las que
el baseline estaba seleccionado, la variante también estaba seleccionada y
ambos periodos estaban disponibles. El cambio absoluto tuvo mediana de
{period_change_stats['median']:.6g} s, Q1 de
{period_change_stats['q1']:.6g} s, Q3 de
{period_change_stats['q3']:.6g} s y máximo de
{period_change_stats['maximum']:.6g} s. Entre las 15 variantes W00
seleccionadas por las diez seeds, el rango del periodo recuperado tuvo mediana
de {optimizer_selected_period_ranges['median']:.6g} s y máximo de
{optimizer_selected_period_ranges['maximum']:.6g} s.

Además, se conservaron {len(formal_nonselected_centers)} centros formales M1
de decisiones no seleccionadas con la etiqueta
`formal_m1_center_not_selected`. No se incluyeron como periodos recuperados
ni en la tabla ni en la figura de estabilidad del periodo.

### 7. Warnings y bounds

Los diagnósticos se resumieron por modelo, perfil y rol, y adicionalmente por
modelo y ventana. Se registraron número de llamadas, llamadas con warnings,
warnings totales y llamadas con parámetros en bounds. No se utilizó la
presencia de warnings o bounds para explicar transiciones de clasificación,
ni se estableció una relación causal. `convergence_status` permanece como
`NOT_AUDITABLE`, por lo que la estabilidad de clasificación no equivale a
convergencia demostrada.

### 8. Alcance observacional

El resultado caracteriza estabilidad interna en una cohorte de diez eventos
y cinco parejas congeladas. No estima sensibilidad, especificidad, tasa
observacional de falsos positivos, accuracy ni verdad física de QPP. El rol
`PUBLISHED_QPP_REPRODUCED` y el rol `MATCHED_NOT_SELECTED` describen la
construcción de la cohorte, no ground truth. No se ejecutó AFINO, no se abrió
ningún FITS, no se regeneraron variantes y no se repitió QUALITY, detrending,
interpolación o relleno de gaps. Tampoco se añadieron candidatos, eventos ni
umbrales de robustez.

`{ANALYSIS_CONCLUSION}`
"""
        report_word_count = len(
            re.findall(
                r"\b[\wÁÉÍÓÚÜÑáéíóúüñ]+\b",
                report,
            )
        )
        if not 900 <= report_word_count <= 1300:
            raise RuntimeError(
                f"Report word count {report_word_count} outside 900–1300."
            )
        audit["report_word_count"] = report_word_count

        (staging / OUTPUT_NAMES[13]).write_text(
            json.dumps(
                audit,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            ) + "\n",
            encoding="utf-8",
        )
        (staging / OUTPUT_NAMES[14]).write_text(
            report,
            encoding="utf-8",
        )

        # -----------------------------------------------------------------
        # Final independent structural validation
        # -----------------------------------------------------------------

        expected_rows = {
            OUTPUT_NAMES[0]: 780,
            OUTPUT_NAMES[1]: 10,
            OUTPUT_NAMES[2]: 5,
            OUTPUT_NAMES[3]: 156,
            OUTPUT_NAMES[4]: 720,
            OUTPUT_NAMES[5]: 780,
            OUTPUT_NAMES[6]: 46,
            OUTPUT_NAMES[7]: len(period_rows),
            OUTPUT_NAMES[8]: 36,
        }
        for filename, expected_count in expected_rows.items():
            observed_count = len(read_csv(staging / filename))
            if observed_count != expected_count:
                raise RuntimeError(
                    f"{filename}: {observed_count} != {expected_count}."
                )

        for filename in OUTPUT_NAMES[9:13]:
            path = staging / filename
            if not path.is_file() or path.stat().st_size < 10_000:
                raise RuntimeError(f"Figure missing or too small: {filename}")

        final_audit = json.loads(
            (staging / OUTPUT_NAMES[13]).read_text(encoding="utf-8")
        )
        if final_audit["analysis_conclusion"] not in {
            "FROZEN_COHORT_ROBUSTNESS_CHARACTERIZED",
            "FROZEN_COHORT_ROBUSTNESS_CHARACTERIZED_WITH_LIMITATIONS",
            "OBSERVATIONAL_ROBUSTNESS_ANALYSIS_BLOCKED",
        }:
            raise RuntimeError("Invalid analysis conclusion.")

        for key, value in final_audit["confirmations"].items():
            if value is not False:
                raise RuntimeError(
                    f"Required confirmation is not false: {key}"
                )

        # Publish only after complete validation.
        for name in OUTPUT_NAMES:
            source = staging / name
            target = output_dir / name
            os.replace(source, target)
        staging.rmdir()

        final_hashes = {
            name: sha256(output_dir / name)
            for name in OUTPUT_NAMES
        }
        print("F2.5 OBSERVATIONAL ROBUSTNESS ANALYSIS COMPLETE")
        print(f"analysis_conclusion: {ANALYSIS_CONCLUSION}")
        print("primary_variants: 780")
        print("primary_eligible: 514")
        print("primary_inadmissible: 266")
        print("baseline_matches: 10/10")
        print("optimizer_stability_variants: 46")
        print("optimizer_seed_decisions: 460")
        print("afino_executed: false")
        print("fits_opened: false")
        print(f"report_word_count: {report_word_count}")
        for name in OUTPUT_NAMES:
            print(f"{name}: {final_hashes[name]}")
    except Exception:
        print(
            f"F2.5 ANALYSIS STOPPED; preserve staging directory: {staging}",
            file=sys.stderr,
        )
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_analysis(args.input_dir, args.output_dir)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"OBSERVATIONAL_ROBUSTNESS_ANALYSIS_BLOCKED: {exc}",
            file=sys.stderr,
        )
        raise
