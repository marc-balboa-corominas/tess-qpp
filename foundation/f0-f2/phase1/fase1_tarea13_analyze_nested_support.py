from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable
import csv
import hashlib
import json
import math
import re
import zipfile

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent

INPUT_HASHES = {
    "fase1_tarea12_nested_full_checkpoint.sqlite":
        "298309ef8f666bae7ee7dacd74667455ca8586af47ebaa2c23cc340304848876",
    "fase1_tarea12_nested_full_results.csv":
        "7fc80e5341b9fb44ab88ff8d97a70248dbbd8e3b9487896c02809a3ad2f44dd1",
    "fase1_tarea12_nested_full_decisions.csv":
        "83da090c9fc2145476f5b1d1bafeafa63de7f1382ccdec1ac4be803448781ce3",
    "fase1_tarea12_nested_full_execution_audit.json":
        "89f6772f2db4643db2d2719ae60c69c0d271a6d6b1853f33f918ecee10ca136a",
    "fase1_tarea08_nested_window_preregistration.json":
        "d80890319b4646f8df994ba7c1dd9da3dc1f141834dbf289d1b17c484fa67487",
}

OUTPUT_NAMES = [
    "fase1_tarea13_primary_decisions_enriched.csv",
    "fase1_tarea13_condition_summary.csv",
    "fase1_tarea13_nested_trajectory_summary.csv",
    "fase1_tarea13_nested_transition_contrasts.csv",
    "fase1_tarea13_optimizer_stability_summary.csv",
    "fase1_tarea13_model_diagnostics_by_n.csv",
    "fase1_tarea13_selection_by_n.png",
    "fase1_tarea13_support_contrast.png",
    "fase1_tarea13_threshold_crossings.png",
    "fase1_tarea13_period_error_by_n.png",
    "fase1_tarea13_nested_analysis_audit.json",
    "fase1_tarea13_nested_analysis_report.md",
]

TOLERANCE = 5e-12
N_SEQUENCE = [15, 30, 45, 60, 90, 120]
TRANSITIONS = list(zip(N_SEQUENCE[:-1], N_SEQUENCE[1:]))
NULL_LABEL = "NULL_FLARE_RED_NOISE"
POSITIVE_LABEL = "STATIONARY_QPP_PRESENT"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_float(value: str) -> float | None:
    if value == "":
        return None
    return float(value)


def parse_int(value: str) -> int:
    return int(value)


def parse_bool(value: str) -> bool:
    if value == "True":
        return True
    if value == "False":
        return False
    raise ValueError(f"Unexpected Boolean value: {value!r}")


def clean_float(value: float | None) -> str | float:
    if value is None or not math.isfinite(value):
        return ""
    return float(value)


def quantile(values: Iterable[float], probability: float) -> float | None:
    materialized = np.asarray(list(values), dtype=float)
    if materialized.size == 0:
        return None
    return float(np.quantile(materialized, probability, method="linear"))


def median(values: Iterable[float]) -> float | None:
    return quantile(values, 0.5)


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total == 0:
        return (math.nan, math.nan)
    p = successes / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denominator
    half = (
        z
        * math.sqrt(
            p * (1.0 - p) / total
            + z * z / (4.0 * total * total)
        )
        / denominator
    )
    return center - half, center + half


def winner_label(bic_m0: float, bic_m1: float, bic_m2: float) -> str:
    values = {"M0": bic_m0, "M1": bic_m1, "M2": bic_m2}
    best = min(values.values())
    winners = [
        model for model, value in values.items()
        if abs(value - best) <= TOLERANCE
    ]
    return winners[0] if len(winners) == 1 else "TIE"


def limiting_model(delta_01: float, delta_21: float) -> str:
    if delta_01 < delta_21 - TOLERANCE:
        return "M0"
    if delta_21 < delta_01 - TOLERANCE:
        return "M2"
    return "TIE"


def support_sign(value: float) -> str:
    if value > TOLERANCE:
        return "POSITIVE"
    if value < -TOLERANCE:
        return "NEGATIVE"
    return "ZERO"


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


for output_name in OUTPUT_NAMES:
    output_path = ROOT / output_name
    if output_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite frozen or provisional artifact: {output_name}"
        )

input_hashes_before = {}
for filename, expected in INPUT_HASHES.items():
    path = ROOT / filename
    if not path.is_file():
        raise FileNotFoundError(path)
    observed = sha256(path)
    if observed != expected:
        raise RuntimeError(
            f"Input hash mismatch for {filename}: {observed} != {expected}"
        )
    input_hashes_before[filename] = observed

preregistration = json.loads(
    (ROOT / "fase1_tarea08_nested_window_preregistration.json").read_text(
        encoding="utf-8"
    )
)
execution_audit = json.loads(
    (ROOT / "fase1_tarea12_nested_full_execution_audit.json").read_text(
        encoding="utf-8"
    )
)

if preregistration["benchmark_id"] != "afino_nested_window_support_v1":
    raise RuntimeError("Unexpected F1.8 benchmark identifier.")
if preregistration["benchmark_version"] != "1.0.0":
    raise RuntimeError("Unexpected F1.8 benchmark version.")
if execution_audit["execution_status"] != "FULL_NESTED_BENCHMARK_EXECUTION_COMPLETE":
    raise RuntimeError("F1.12 execution is not complete.")
if execution_audit["pending_jobs"] != 0:
    raise RuntimeError("F1.12 still has pending jobs.")

raw_decisions = read_csv(
    ROOT / "fase1_tarea12_nested_full_decisions.csv"
)
raw_results = read_csv(
    ROOT / "fase1_tarea12_nested_full_results.csv"
)

decisions: list[dict[str, Any]] = []
for row in raw_decisions:
    decisions.append({
        "series_id": row["series_id"],
        "condition_id": row["condition_id"],
        "parent_id": row["parent_id"],
        "block_id": row["block_id"],
        "ground_truth": row["ground_truth"],
        "n_samples": parse_int(row["n_samples"]),
        "duration_s": float(row["duration_s"]),
        "red_noise_alpha": float(row["red_noise_alpha"]),
        "period_s": parse_float(row["period_s"]),
        "qpp_fraction": parse_float(row["qpp_fraction"]),
        "data_seed": parse_int(row["data_seed"]),
        "external_optimizer_seed": parse_int(
            row["external_optimizer_seed"]
        ),
        "decision_status": row["decision_status"],
        "valid_models": parse_int(row["valid_models"]),
        "bic_m0": float(row["bic_m0"]),
        "bic_m1": float(row["bic_m1"]),
        "bic_m2": float(row["bic_m2"]),
        "delta_bic_0_1": float(row["delta_bic_0_1"]),
        "delta_bic_2_1": float(row["delta_bic_2_1"]),
        "qpp_selected": parse_bool(row["qpp_selected"]),
        "estimated_period_s": parse_float(row["estimated_period_s"]),
        "source_period_label": row["period_label"],
    })

results: list[dict[str, Any]] = []
for row in raw_results:
    results.append({
        **row,
        "n_samples": parse_int(row["n_samples"]),
        "data_seed": parse_int(row["data_seed"]),
        "external_optimizer_seed": parse_int(
            row["external_optimizer_seed"]
        ),
        "warning_count": parse_int(row["warning_count"]),
        "parameter_at_bound": parse_bool(row["parameter_at_bound"]),
        "runtime_seconds": float(row["runtime_seconds"]),
    })

primary = [
    row for row in decisions
    if row["external_optimizer_seed"] == 0
    and row["decision_status"] == "VALID"
]
if len(primary) != 2160:
    raise RuntimeError(f"Primary decision count mismatch: {len(primary)}")
if Counter(row["ground_truth"] for row in primary) != {
    NULL_LABEL: 720,
    POSITIVE_LABEL: 1440,
}:
    raise RuntimeError("Primary ground-truth counts are incorrect.")

enriched: list[dict[str, Any]] = []
for row in primary:
    joint_margin = (
        min(row["delta_bic_0_1"], row["delta_bic_2_1"]) - 10.0
    )
    period = row["period_s"]
    estimate = row["estimated_period_s"]
    signed_error = None
    absolute_error = None
    relative_signed = None
    relative_absolute = None
    population_label = ""
    if row["ground_truth"] == POSITIVE_LABEL:
        if period is None or estimate is None:
            raise RuntimeError("Positive decision lacks period metadata.")
        signed_error = estimate - period
        absolute_error = abs(signed_error)
        relative_signed = signed_error / period
        relative_absolute = absolute_error / period
        population_label = (
            "recovered_period_selected"
            if row["qpp_selected"]
            else "formal_m1_center_not_selected"
        )

    enriched.append({
        **row,
        "joint_margin": joint_margin,
        "margin_limiting_model": limiting_model(
            row["delta_bic_0_1"],
            row["delta_bic_2_1"],
        ),
        "bic_winner": winner_label(
            row["bic_m0"],
            row["bic_m1"],
            row["bic_m2"],
        ),
        "signed_period_error_s": signed_error,
        "absolute_period_error_s": absolute_error,
        "relative_signed_error": relative_signed,
        "relative_absolute_error": relative_absolute,
        "period_population_label": population_label,
    })

enriched_fields = [
    "series_id",
    "condition_id",
    "parent_id",
    "block_id",
    "ground_truth",
    "n_samples",
    "duration_s",
    "red_noise_alpha",
    "period_s",
    "qpp_fraction",
    "data_seed",
    "external_optimizer_seed",
    "decision_status",
    "bic_m0",
    "bic_m1",
    "bic_m2",
    "delta_bic_0_1",
    "delta_bic_2_1",
    "joint_margin",
    "margin_limiting_model",
    "bic_winner",
    "qpp_selected",
    "estimated_period_s",
    "period_population_label",
    "signed_period_error_s",
    "absolute_period_error_s",
    "relative_signed_error",
    "relative_absolute_error",
]
write_csv(
    ROOT / "fase1_tarea13_primary_decisions_enriched.csv",
    enriched,
    enriched_fields,
)

enriched_by_condition: dict[str, list[dict[str, Any]]] = defaultdict(list)
for row in enriched:
    enriched_by_condition[row["condition_id"]].append(row)

condition_rows: list[dict[str, Any]] = []
condition_order = [
    condition["condition_id"]
    for condition in preregistration["design_grid"]["conditions"]
]
for condition_id in condition_order:
    group = enriched_by_condition[condition_id]
    if len(group) != 40:
        raise RuntimeError(
            f"Condition {condition_id} has {len(group)} primary decisions."
        )
    first = group[0]
    selected = sum(row["qpp_selected"] for row in group)
    ci_low, ci_high = wilson_interval(selected, len(group))
    limit_counts = Counter(
        row["margin_limiting_model"] for row in group
    )
    winner_counts = Counter(row["bic_winner"] for row in group)

    selected_period_rows = [
        row for row in group
        if row["ground_truth"] == POSITIVE_LABEL
        and row["qpp_selected"]
    ]
    formal_period_rows = [
        row for row in group
        if row["ground_truth"] == POSITIVE_LABEL
    ]

    condition_rows.append({
        "condition_id": condition_id,
        "ground_truth": first["ground_truth"],
        "n_samples": first["n_samples"],
        "duration_s": first["duration_s"],
        "red_noise_alpha": first["red_noise_alpha"],
        "period_s": first["period_s"],
        "qpp_fraction": first["qpp_fraction"],
        "primary_decision_count": len(group),
        "selection_count": selected,
        "selection_rate": selected / len(group),
        "wilson_ci_low": ci_low,
        "wilson_ci_high": ci_high,
        "median_delta_bic_0_1": median(
            row["delta_bic_0_1"] for row in group
        ),
        "median_delta_bic_2_1": median(
            row["delta_bic_2_1"] for row in group
        ),
        "median_joint_margin": median(
            row["joint_margin"] for row in group
        ),
        "limiting_m0_count": limit_counts["M0"],
        "limiting_m2_count": limit_counts["M2"],
        "limiting_tie_count": limit_counts["TIE"],
        "bic_winner_m0_count": winner_counts["M0"],
        "bic_winner_m1_count": winner_counts["M1"],
        "bic_winner_m2_count": winner_counts["M2"],
        "bic_winner_tie_count": winner_counts["TIE"],
        "selected_period_count": len(selected_period_rows),
        "selected_signed_period_error_median_s": median(
            row["signed_period_error_s"]
            for row in selected_period_rows
        ),
        "selected_absolute_period_error_median_s": median(
            row["absolute_period_error_s"]
            for row in selected_period_rows
        ),
        "formal_period_count": len(formal_period_rows),
        "formal_signed_period_error_median_s": median(
            row["signed_period_error_s"]
            for row in formal_period_rows
        ),
        "formal_absolute_period_error_median_s": median(
            row["absolute_period_error_s"]
            for row in formal_period_rows
        ),
    })

condition_fields = [
    "condition_id",
    "ground_truth",
    "n_samples",
    "duration_s",
    "red_noise_alpha",
    "period_s",
    "qpp_fraction",
    "primary_decision_count",
    "selection_count",
    "selection_rate",
    "wilson_ci_low",
    "wilson_ci_high",
    "median_delta_bic_0_1",
    "median_delta_bic_2_1",
    "median_joint_margin",
    "limiting_m0_count",
    "limiting_m2_count",
    "limiting_tie_count",
    "bic_winner_m0_count",
    "bic_winner_m1_count",
    "bic_winner_m2_count",
    "bic_winner_tie_count",
    "selected_period_count",
    "selected_signed_period_error_median_s",
    "selected_absolute_period_error_median_s",
    "formal_period_count",
    "formal_signed_period_error_median_s",
    "formal_absolute_period_error_median_s",
]
write_csv(
    ROOT / "fase1_tarea13_condition_summary.csv",
    condition_rows,
    condition_fields,
)

trajectory_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
for row in enriched:
    trajectory_groups[(row["parent_id"], row["block_id"])].append(row)

if len(trajectory_groups) != 360:
    raise RuntimeError(
        f"Trajectory count mismatch: {len(trajectory_groups)}"
    )

trajectory_rows: list[dict[str, Any]] = []
transition_rows: list[dict[str, Any]] = []

for (parent_id, block_id), group in sorted(
    trajectory_groups.items(),
    key=lambda item: item[0],
):
    group = sorted(group, key=lambda row: row["n_samples"])
    if [row["n_samples"] for row in group] != N_SEQUENCE:
        raise RuntimeError(
            f"Incomplete trajectory for {parent_id}/{block_id}"
        )
    if len({row["parent_id"] for row in group}) != 1:
        raise RuntimeError("Parent identity changed within trajectory.")
    if len({row["block_id"] for row in group}) != 1:
        raise RuntimeError("Block identity changed within trajectory.")

    first = group[0]
    selections = [row["qpp_selected"] for row in group]
    sequence = "".join("1" if selected else "0" for selected in selections)
    up_count = sum(
        (not selections[index]) and selections[index + 1]
        for index in range(5)
    )
    down_count = sum(
        selections[index] and (not selections[index + 1])
        for index in range(5)
    )
    first_selected_n = next(
        (
            N_SEQUENCE[index]
            for index, selected in enumerate(selections)
            if selected
        ),
        None,
    )
    stable_selection_from_n = next(
        (
            N_SEQUENCE[index]
            for index in range(len(selections))
            if selections[index]
            and all(selections[index:])
        ),
        None,
    )

    trajectory_rows.append({
        "parent_id": parent_id,
        "block_id": block_id,
        "ground_truth": first["ground_truth"],
        "period_s": first["period_s"],
        "qpp_fraction": first["qpp_fraction"],
        "red_noise_alpha": first["red_noise_alpha"],
        "data_seed": first["data_seed"],
        "n_sequence": "|".join(str(value) for value in N_SEQUENCE),
        "selection_sequence": sequence,
        "selection_interpretation": (
            "synthetic false selection"
            if first["ground_truth"] == NULL_LABEL
            else "injected QPP selection"
        ),
        "ever_selected": any(selections),
        "selected_n_count": sum(selections),
        "number_of_up_transitions": up_count,
        "number_of_down_transitions": down_count,
        "first_selected_n": first_selected_n,
        "stable_selection_from_n": stable_selection_from_n,
        "delta_bic_0_1_sequence_json": json.dumps(
            [row["delta_bic_0_1"] for row in group],
            separators=(",", ":"),
        ),
        "delta_bic_2_1_sequence_json": json.dumps(
            [row["delta_bic_2_1"] for row in group],
            separators=(",", ":"),
        ),
        "joint_margin_sequence_json": json.dumps(
            [row["joint_margin"] for row in group],
            separators=(",", ":"),
        ),
        "limiting_model_sequence": "|".join(
            row["margin_limiting_model"] for row in group
        ),
    })

    by_n = {row["n_samples"]: row for row in group}
    for n_from, n_to in TRANSITIONS:
        start = by_n[n_from]
        end = by_n[n_to]
        change_01 = (
            end["delta_bic_0_1"] - start["delta_bic_0_1"]
        )
        change_21 = (
            end["delta_bic_2_1"] - start["delta_bic_2_1"]
        )
        change_joint = end["joint_margin"] - start["joint_margin"]
        positive = first["ground_truth"] == POSITIVE_LABEL
        support = change_01 - change_21 if positive else None
        transition_rows.append({
            "parent_id": parent_id,
            "block_id": block_id,
            "ground_truth": first["ground_truth"],
            "period_s": first["period_s"],
            "qpp_fraction": first["qpp_fraction"],
            "red_noise_alpha": first["red_noise_alpha"],
            "data_seed": first["data_seed"],
            "transition": f"{n_from}_to_{n_to}",
            "n_from": n_from,
            "n_to": n_to,
            "delta_bic_0_1_from": start["delta_bic_0_1"],
            "delta_bic_0_1_to": end["delta_bic_0_1"],
            "delta_bic_2_1_from": start["delta_bic_2_1"],
            "delta_bic_2_1_to": end["delta_bic_2_1"],
            "joint_margin_from": start["joint_margin"],
            "joint_margin_to": end["joint_margin"],
            "paired_change_delta_bic_0_1": change_01,
            "paired_change_delta_bic_2_1": change_21,
            "paired_change_joint_margin": change_joint,
            "support_hypothesis_contrast": support,
            "support_contrast_sign": (
                support_sign(support) if support is not None else ""
            ),
            "cross_m0_up": (
                start["delta_bic_0_1"] <= 10.0
                and end["delta_bic_0_1"] > 10.0
            ),
            "cross_m0_down": (
                start["delta_bic_0_1"] > 10.0
                and end["delta_bic_0_1"] <= 10.0
            ),
            "cross_m2_up": (
                start["delta_bic_2_1"] <= 10.0
                and end["delta_bic_2_1"] > 10.0
            ),
            "cross_m2_down": (
                start["delta_bic_2_1"] > 10.0
                and end["delta_bic_2_1"] <= 10.0
            ),
            "qpp_selected_from": start["qpp_selected"],
            "qpp_selected_to": end["qpp_selected"],
            "joint_selection_up": (
                (not start["qpp_selected"])
                and end["qpp_selected"]
            ),
            "joint_selection_down": (
                start["qpp_selected"]
                and (not end["qpp_selected"])
            ),
        })

if len(trajectory_rows) != 360:
    raise RuntimeError("Trajectory summary row count mismatch.")
if len(transition_rows) != 1800:
    raise RuntimeError("Transition row count mismatch.")
if Counter(row["ground_truth"] for row in trajectory_rows) != {
    NULL_LABEL: 120,
    POSITIVE_LABEL: 240,
}:
    raise RuntimeError("Trajectory population counts mismatch.")
if Counter(row["ground_truth"] for row in transition_rows) != {
    NULL_LABEL: 600,
    POSITIVE_LABEL: 1200,
}:
    raise RuntimeError("Transition population counts mismatch.")

trajectory_fields = [
    "parent_id",
    "block_id",
    "ground_truth",
    "period_s",
    "qpp_fraction",
    "red_noise_alpha",
    "data_seed",
    "n_sequence",
    "selection_sequence",
    "selection_interpretation",
    "ever_selected",
    "selected_n_count",
    "number_of_up_transitions",
    "number_of_down_transitions",
    "first_selected_n",
    "stable_selection_from_n",
    "delta_bic_0_1_sequence_json",
    "delta_bic_2_1_sequence_json",
    "joint_margin_sequence_json",
    "limiting_model_sequence",
]
write_csv(
    ROOT / "fase1_tarea13_nested_trajectory_summary.csv",
    trajectory_rows,
    trajectory_fields,
)

transition_fields = [
    "parent_id",
    "block_id",
    "ground_truth",
    "period_s",
    "qpp_fraction",
    "red_noise_alpha",
    "data_seed",
    "transition",
    "n_from",
    "n_to",
    "delta_bic_0_1_from",
    "delta_bic_0_1_to",
    "delta_bic_2_1_from",
    "delta_bic_2_1_to",
    "joint_margin_from",
    "joint_margin_to",
    "paired_change_delta_bic_0_1",
    "paired_change_delta_bic_2_1",
    "paired_change_joint_margin",
    "support_hypothesis_contrast",
    "support_contrast_sign",
    "cross_m0_up",
    "cross_m0_down",
    "cross_m2_up",
    "cross_m2_down",
    "qpp_selected_from",
    "qpp_selected_to",
    "joint_selection_up",
    "joint_selection_down",
]
write_csv(
    ROOT / "fase1_tarea13_nested_transition_contrasts.csv",
    transition_rows,
    transition_fields,
)

stability_population = [
    row for row in decisions
    if row["data_seed"] == 0
    and row["decision_status"] == "VALID"
    and 0 <= row["external_optimizer_seed"] <= 9
]
if len(stability_population) != 540:
    raise RuntimeError(
        f"Optimizer stability population mismatch: {len(stability_population)}"
    )

stability_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
for row in stability_population:
    stability_groups[row["condition_id"]].append(row)

if len(stability_groups) != 54:
    raise RuntimeError("Optimizer stability condition count mismatch.")

stability_rows: list[dict[str, Any]] = []
for condition_id in condition_order:
    group = sorted(
        stability_groups[condition_id],
        key=lambda row: row["external_optimizer_seed"],
    )
    seeds = [row["external_optimizer_seed"] for row in group]
    if seeds != list(range(10)):
        raise RuntimeError(
            f"Condition {condition_id} lacks optimizer seeds 0..9."
        )
    selected_flags = [row["qpp_selected"] for row in group]
    selected_count = sum(selected_flags)
    discordant_pairs = selected_count * (10 - selected_count)
    bic_range_m0 = max(row["bic_m0"] for row in group) - min(
        row["bic_m0"] for row in group
    )
    bic_range_m1 = max(row["bic_m1"] for row in group) - min(
        row["bic_m1"] for row in group
    )
    bic_range_m2 = max(row["bic_m2"] for row in group) - min(
        row["bic_m2"] for row in group
    )
    first = group[0]
    stability_rows.append({
        "condition_id": condition_id,
        "ground_truth": first["ground_truth"],
        "n_samples": first["n_samples"],
        "duration_s": first["duration_s"],
        "red_noise_alpha": first["red_noise_alpha"],
        "period_s": first["period_s"],
        "qpp_fraction": first["qpp_fraction"],
        "data_seed": 0,
        "decision_count": len(group),
        "optimizer_seeds": "0|1|2|3|4|5|6|7|8|9",
        "decision_sequence": "".join(
            "1" if value else "0" for value in selected_flags
        ),
        "selected_seed_count": selected_count,
        "primary_seed_selected": selected_flags[0],
        "stability_seeds_selected_count": sum(selected_flags[1:]),
        "optimizer_seed_decision_discordance": (
            discordant_pairs / 45.0
        ),
        "bic_range_m0": bic_range_m0,
        "bic_range_m1": bic_range_m1,
        "bic_range_m2": bic_range_m2,
        "m2_multiple_solution_flag": bic_range_m2 > 0.001,
        "all_decisions_valid": True,
    })

stability_fields = [
    "condition_id",
    "ground_truth",
    "n_samples",
    "duration_s",
    "red_noise_alpha",
    "period_s",
    "qpp_fraction",
    "data_seed",
    "decision_count",
    "optimizer_seeds",
    "decision_sequence",
    "selected_seed_count",
    "primary_seed_selected",
    "stability_seeds_selected_count",
    "optimizer_seed_decision_discordance",
    "bic_range_m0",
    "bic_range_m1",
    "bic_range_m2",
    "m2_multiple_solution_flag",
    "all_decisions_valid",
]
write_csv(
    ROOT / "fase1_tarea13_optimizer_stability_summary.csv",
    stability_rows,
    stability_fields,
)

primary_results = [
    row for row in results
    if row["job_class"] == "primary"
    and row["external_optimizer_seed"] == 0
]
if len(primary_results) != 6480:
    raise RuntimeError("Primary model-call population mismatch.")

diagnostic_groups: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
for row in primary_results:
    diagnostic_groups[
        (row["n_samples"], row["model_id"])
    ].append(row)

diagnostic_rows: list[dict[str, Any]] = []
for n_samples in N_SEQUENCE:
    for model_id in ["M0", "M1", "M2"]:
        group = diagnostic_groups[(n_samples, model_id)]
        if len(group) != 360:
            raise RuntimeError(
                f"Diagnostic group {n_samples}/{model_id} has {len(group)} calls."
            )
        warning_calls = sum(row["warning_count"] > 0 for row in group)
        warning_total = sum(row["warning_count"] for row in group)
        bound_calls = sum(row["parameter_at_bound"] for row in group)
        diagnostic_rows.append({
            "n_samples": n_samples,
            "model_id": model_id,
            "model_name": group[0]["model_name"],
            "call_count": len(group),
            "warning_call_count": warning_calls,
            "warning_total": warning_total,
            "bound_hit_call_count": bound_calls,
            "warning_rate": warning_calls / len(group),
            "bound_rate": bound_calls / len(group),
        })

diagnostic_fields = [
    "n_samples",
    "model_id",
    "model_name",
    "call_count",
    "warning_call_count",
    "warning_total",
    "bound_hit_call_count",
    "warning_rate",
    "bound_rate",
]
write_csv(
    ROOT / "fase1_tarea13_model_diagnostics_by_n.csv",
    diagnostic_rows,
    diagnostic_fields,
)

positive_transitions = [
    row for row in transition_rows
    if row["ground_truth"] == POSITIVE_LABEL
]
null_transitions = [
    row for row in transition_rows
    if row["ground_truth"] == NULL_LABEL
]
support_values = [
    row["support_hypothesis_contrast"]
    for row in positive_transitions
]
support_counts = Counter(
    row["support_contrast_sign"] for row in positive_transitions
)
support_summary = {
    "count": len(support_values),
    "median": median(support_values),
    "q1": quantile(support_values, 0.25),
    "q3": quantile(support_values, 0.75),
    "minimum": min(support_values),
    "maximum": max(support_values),
    "positive_count": support_counts["POSITIVE"],
    "zero_count": support_counts["ZERO"],
    "negative_count": support_counts["NEGATIVE"],
}

support_strata = []
for n_from, n_to in TRANSITIONS:
    for period_s in [50.0, 80.0]:
        for alpha in [0.0, 1.0, 2.0]:
            group = [
                row for row in positive_transitions
                if row["n_from"] == n_from
                and row["n_to"] == n_to
                and row["period_s"] == period_s
                and row["red_noise_alpha"] == alpha
            ]
            values = [
                row["support_hypothesis_contrast"] for row in group
            ]
            signs = Counter(
                row["support_contrast_sign"] for row in group
            )
            support_strata.append({
                "transition": f"{n_from}_to_{n_to}",
                "period_s": period_s,
                "red_noise_alpha": alpha,
                "count": len(group),
                "median": median(values),
                "q1": quantile(values, 0.25),
                "q3": quantile(values, 0.75),
                "minimum": min(values),
                "maximum": max(values),
                "positive_count": signs["POSITIVE"],
                "zero_count": signs["ZERO"],
                "negative_count": signs["NEGATIVE"],
            })

transition_support = {}
for n_from, n_to in TRANSITIONS:
    group = [
        row for row in positive_transitions
        if row["n_from"] == n_from
        and row["n_to"] == n_to
    ]
    values = [
        row["support_hypothesis_contrast"] for row in group
    ]
    transition_support[f"{n_from}_to_{n_to}"] = {
        "median_support_contrast": median(values),
        "q1": quantile(values, 0.25),
        "q3": quantile(values, 0.75),
        "median_change_delta_bic_0_1": median(
            row["paired_change_delta_bic_0_1"] for row in group
        ),
        "median_change_delta_bic_2_1": median(
            row["paired_change_delta_bic_2_1"] for row in group
        ),
        "positive_count": sum(
            row["support_contrast_sign"] == "POSITIVE"
            for row in group
        ),
        "zero_count": sum(
            row["support_contrast_sign"] == "ZERO"
            for row in group
        ),
        "negative_count": sum(
            row["support_contrast_sign"] == "NEGATIVE"
            for row in group
        ),
    }

positive_crossings = {
    key: sum(row[key] for row in positive_transitions)
    for key in [
        "cross_m0_up",
        "cross_m0_down",
        "cross_m2_up",
        "cross_m2_down",
        "joint_selection_up",
        "joint_selection_down",
    ]
}
null_crossings = {
    key: sum(row[key] for row in null_transitions)
    for key in [
        "cross_m0_up",
        "cross_m0_down",
        "cross_m2_up",
        "cross_m2_down",
        "joint_selection_up",
        "joint_selection_down",
    ]
}

positive_trajectories = [
    row for row in trajectory_rows
    if row["ground_truth"] == POSITIVE_LABEL
]
null_trajectories = [
    row for row in trajectory_rows
    if row["ground_truth"] == NULL_LABEL
]
positive_sequences = Counter(
    row["selection_sequence"] for row in positive_trajectories
)
null_sequences = Counter(
    row["selection_sequence"] for row in null_trajectories
)

null_selection_by_n = {}
positive_selection_by_n = {}
for n_samples in N_SEQUENCE:
    null_group = [
        row for row in enriched
        if row["ground_truth"] == NULL_LABEL
        and row["n_samples"] == n_samples
    ]
    positive_group = [
        row for row in enriched
        if row["ground_truth"] == POSITIVE_LABEL
        and row["n_samples"] == n_samples
    ]
    null_selection_by_n[str(n_samples)] = {
        "synthetic_false_selection_count": sum(
            row["qpp_selected"] for row in null_group
        ),
        "series_count": len(null_group),
    }
    positive_selection_by_n[str(n_samples)] = {
        "selection_count": sum(
            row["qpp_selected"] for row in positive_group
        ),
        "series_count": len(positive_group),
    }

positive_decisions = [
    row for row in enriched
    if row["ground_truth"] == POSITIVE_LABEL
]
selected_period_rows = [
    row for row in positive_decisions
    if row["period_population_label"] == "recovered_period_selected"
]
formal_period_rows = [
    row for row in positive_decisions
    if row["period_population_label"]
    == "formal_m1_center_not_selected"
]

period_summary_selected = []
period_summary_formal = []
for n_samples in N_SEQUENCE:
    for period_s in [50.0, 80.0]:
        selected_group = [
            row for row in selected_period_rows
            if row["n_samples"] == n_samples
            and row["period_s"] == period_s
        ]
        formal_group = [
            row for row in positive_decisions
            if row["n_samples"] == n_samples
            and row["period_s"] == period_s
        ]
        period_summary_selected.append({
            "n_samples": n_samples,
            "period_s": period_s,
            "count": len(selected_group),
            "median_signed_error_s": median(
                row["signed_period_error_s"] for row in selected_group
            ),
            "median_absolute_error_s": median(
                row["absolute_period_error_s"] for row in selected_group
            ),
            "median_relative_signed_error": median(
                row["relative_signed_error"] for row in selected_group
            ),
            "median_relative_absolute_error": median(
                row["relative_absolute_error"] for row in selected_group
            ),
        })
        period_summary_formal.append({
            "n_samples": n_samples,
            "period_s": period_s,
            "count": len(formal_group),
            "selected_count": sum(
                row["qpp_selected"] for row in formal_group
            ),
            "median_signed_error_s": median(
                row["signed_period_error_s"] for row in formal_group
            ),
            "median_absolute_error_s": median(
                row["absolute_period_error_s"] for row in formal_group
            ),
            "median_relative_signed_error": median(
                row["relative_signed_error"] for row in formal_group
            ),
            "median_relative_absolute_error": median(
                row["relative_absolute_error"] for row in formal_group
            ),
        })

optimizer_decision_changes = sum(
    row["selected_seed_count"] not in (0, 10)
    for row in stability_rows
)
m2_multiple_solution_count = sum(
    row["m2_multiple_solution_flag"] for row in stability_rows
)

limiting_counts_positive = Counter(
    row["margin_limiting_model"] for row in positive_decisions
)

# Figure 1: selection by N, separated into null/P50/P80.
plt.figure(figsize=(8.5, 5.5))
for label, ground_truth, period_s in [
    ("Nulo sintético", NULL_LABEL, None),
    ("QPP P=50 s", POSITIVE_LABEL, 50.0),
    ("QPP P=80 s", POSITIVE_LABEL, 80.0),
]:
    rates = []
    for n_samples in N_SEQUENCE:
        group = [
            row for row in enriched
            if row["ground_truth"] == ground_truth
            and row["n_samples"] == n_samples
            and (
                period_s is None
                or row["period_s"] == period_s
            )
        ]
        rates.append(
            sum(row["qpp_selected"] for row in group) / len(group)
        )
    plt.plot(N_SEQUENCE, rates, marker="o", label=label)
plt.xlabel("Número de muestras N")
plt.ylabel("Proporción seleccionada")
plt.title("Selección primaria por longitud de ventana")
plt.xticks(N_SEQUENCE)
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig(
    ROOT / "fase1_tarea13_selection_by_n.png",
    dpi=180,
)
plt.close()

# Figure 2: support contrast distributions by transition.
plt.figure(figsize=(9.0, 5.8))
support_box_data = []
support_box_labels = []
for n_from, n_to in TRANSITIONS:
    support_box_data.append([
        row["support_hypothesis_contrast"]
        for row in positive_transitions
        if row["n_from"] == n_from
        and row["n_to"] == n_to
    ])
    support_box_labels.append(f"{n_from}→{n_to}")
plt.boxplot(support_box_data, tick_labels=support_box_labels)
plt.axhline(0.0, linewidth=1.0)
plt.xlabel("Transición anidada")
plt.ylabel("C_support = ΔΔ01 − ΔΔ21")
plt.title("Contraste de apoyo temporal en transiciones positivas")
plt.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(
    ROOT / "fase1_tarea13_support_contrast.png",
    dpi=180,
)
plt.close()

# Figure 3: threshold crossings in positive transitions.
plt.figure(figsize=(10.0, 5.8))
crossing_fields = [
    ("cross_m0_up", "M0 arriba"),
    ("cross_m0_down", "M0 abajo"),
    ("cross_m2_up", "M2 arriba"),
    ("cross_m2_down", "M2 abajo"),
    ("joint_selection_up", "Selección arriba"),
    ("joint_selection_down", "Selección abajo"),
]
x = np.arange(len(TRANSITIONS), dtype=float)
width = 0.12
for index, (field, label) in enumerate(crossing_fields):
    counts = []
    for n_from, n_to in TRANSITIONS:
        counts.append(sum(
            row[field]
            for row in positive_transitions
            if row["n_from"] == n_from
            and row["n_to"] == n_to
        ))
    positions = x + (index - 2.5) * width
    plt.bar(positions, counts, width=width, label=label)
plt.xticks(x, [f"{a}→{b}" for a, b in TRANSITIONS])
plt.xlabel("Transición anidada")
plt.ylabel("Número de cruces")
plt.title("Cruces ascendentes y descendentes en positivos")
plt.legend(ncol=2)
plt.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(
    ROOT / "fase1_tarea13_threshold_crossings.png",
    dpi=180,
)
plt.close()

# Figure 4: selected and formal M1 period errors remain separate lines.
plt.figure(figsize=(9.0, 5.8))
for population, period_s, label in [
    ("selected", 50.0, "Seleccionado P=50 s"),
    ("selected", 80.0, "Seleccionado P=80 s"),
    ("formal", 50.0, "Centro formal P=50 s"),
    ("formal", 80.0, "Centro formal P=80 s"),
]:
    values = []
    for n_samples in N_SEQUENCE:
        if population == "selected":
            match = next(
                row for row in period_summary_selected
                if row["n_samples"] == n_samples
                and row["period_s"] == period_s
            )
        else:
            match = next(
                row for row in period_summary_formal
                if row["n_samples"] == n_samples
                and row["period_s"] == period_s
            )
        value = match["median_absolute_error_s"]
        values.append(np.nan if value is None else value)
    plt.plot(N_SEQUENCE, values, marker="o", label=label)
plt.xlabel("Número de muestras N")
plt.ylabel("Mediana del error absoluto del periodo (s)")
plt.title("Error de periodo: seleccionados frente a centro formal de M1")
plt.xticks(N_SEQUENCE)
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig(
    ROOT / "fase1_tarea13_period_error_by_n.png",
    dpi=180,
)
plt.close()

# Compose the report from frozen outputs only.
def format_number(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def transition_text(key: str) -> str:
    return key.replace("_to_", "→")


report = f"""# Fase 1 — Tarea 1.13

## Análisis prerregistrado del efecto de extensión de ventanas anidadas

**Conclusión:** `NESTED_SUPPORT_HYPOTHESIS_MIXED`

El análisis utilizó exclusivamente las 2.160 decisiones primarias válidas de
F1.12, con `external_optimizer_seed=0`: 720 nulas y 1.440 positivas. Las
decisiones de estabilidad y el canary quedaron fuera de las tasas primarias.
Se reconstruyeron 360 trayectorias mediante la pareja normativa
`(parent_id, block_id)`, todas con N=15, 30, 45, 60, 90 y 120, y 1.800
transiciones adyacentes. No se ejecutó AFINO, no se regeneraron curvas y los
hashes de F1.8 y F1.12 permanecieron invariantes.

## Evidencia frente a M0 y M2

En positivos, la mediana de Δ01 fue -5,449 en N=15, -6,337 en N=30,
-6,487 en N=45, -6,131 en N=60, -6,337 en N=90 y -5,598 en N=120.
La mediana de Δ21 evolucionó de -1,891 a -1,491, -1,039, -0,304,
-0,038 y 1,205. Por tanto, la evidencia relativa frente a M2 aumentó con
mayor claridad que la evidencia frente a M0. M0 limitó el margen conjunto en
{limiting_counts_positive["M0"]} de las 1.440 decisiones positivas; M2 lo
limitó en solo {limiting_counts_positive["M2"]}.

El contraste C_support se calculó en las 1.200 transiciones positivas. Su
mediana fue {format_number(support_summary["median"])}, con Q1
{format_number(support_summary["q1"])}, Q3
{format_number(support_summary["q3"])}, mínimo
{format_number(support_summary["minimum"])} y máximo
{format_number(support_summary["maximum"])}. Fue positivo en
{support_summary["positive_count"]} transiciones, cero en
{support_summary["zero_count"]} y negativo en
{support_summary["negative_count"]}. Las medianas por transición fueron:
15→30 {format_number(transition_support["15_to_30"]["median_support_contrast"])},
30→45 {format_number(transition_support["30_to_45"]["median_support_contrast"])},
45→60 {format_number(transition_support["45_to_60"]["median_support_contrast"])},
60→90 {format_number(transition_support["60_to_90"]["median_support_contrast"])}
y 90→120 {format_number(transition_support["90_to_120"]["median_support_contrast"])}.
Los dos periodos mostraron medianas casi iguales, ambas negativas. Con alpha=2
los contrastes tardíos fueron menos negativos y 60→90 tuvo mediana ligeramente
positiva, pero no apareció un patrón uniforme entre todos los estratos.

## Cruces, secuencias y reversiones

Sí aparecieron cruces conjuntos, aunque fueron escasos. En positivos hubo
{positive_crossings["joint_selection_up"]} transiciones False→True y
{positive_crossings["joint_selection_down"]} True→False. Los cruces
individuales fueron {positive_crossings["cross_m0_up"]} ascendentes y
{positive_crossings["cross_m0_down"]} descendentes frente a M0, y
{positive_crossings["cross_m2_up"]} ascendentes y
{positive_crossings["cross_m2_down"]} descendentes frente a M2. Las
trayectorias no fueron monotónicas: 236/240 positivas siguieron `000000`,
dos siguieron `000100` y dos `000001`. Las dos selecciones de N=60 se
revirtieron en N=90; las dos de N=120 aparecieron únicamente en la última
ventana. No hubo una trayectoria positiva que permaneciera seleccionada desde
N=60 o N=90 hasta el final.

## Nulo sintético

Bajo el nulo hubo cero synthetic false selections en N=15, N=30 y N=45;
una en N=60, cero en N=90 y una en N=120. Dos de las 120 trayectorias nulas
fueron seleccionadas alguna vez. Sus secuencias fueron 118 veces `000000`,
una vez `000100` y una vez `000001`. Se registraron
{null_crossings["joint_selection_up"]} transiciones nulas False→True y
{null_crossings["joint_selection_down"]} True→False. Estas cifras describen
exclusivamente synthetic false selection en el generador congelado y no una
tasa observacional de falsos positivos.

## Periodo formal y selección

Solo cuatro decisiones positivas fueron seleccionadas: una por cada combinación
N=60/P=50, N=60/P=80, N=120/P=50 y N=120/P=80. Sus errores firmados fueron,
respectivamente, +17,251 s, -12,154 s, +11,108 s y -18,625 s. Al existir una
sola observación por estrato, no puede inferirse una tendencia robusta del
periodo condicionado a selección. En las 1.440 ejecuciones válidas, el centro
formal de M1 se mantuvo separado de la recuperación seleccionada. La mediana
del error absoluto fue menor en N=30 —3,857 s para P=50 y 12,490 s para P=80—
y aumentó en N=120 hasta 40,952 s y 29,303 s. Tampoco aquí la extensión produjo
una mejora monotónica.

## Optimizador y diagnósticos

Las 54 condiciones de estabilidad contuvieron exactamente diez seeds externas.
Ninguna cambió la decisión: `selected_seed_count=0` en las 54 y discordancia
cero. Sin embargo, M2 presentó `m2_multiple_solution_flag` en
{m2_multiple_solution_count}/54 condiciones. Debe conservarse la distinción
`stable classification ≠ unique numerical optimum`.

En llamadas primarias, M0 y M1 no emitieron warnings. Los warnings de M2
afectaron al 12,8 % de llamadas en N=15 y al 93,1 % en N=120. Los bounds de
M1 afectaron entre el 48,6 % y el 65,0 % según N; los de M2 aumentaron hasta
81,1 % en N=120. Estos diagnósticos se presentan como controles descriptivos,
no como explicación causal de los cambios de selección.

## Interpretación

La hipótesis queda **mixta**. Está apoyada la parte que anticipaba la posible
aparición de cruces conjuntos y reversiones al extender prefijos. No está
apoyada, como tendencia dominante, la proposición de que aumentaría
principalmente la evidencia de M1 frente a M0: C_support fue negativo en
{support_summary["negative_count"]}/1.200 transiciones y Δ21 mejoró más que
Δ01. Además, el benchmark identifica el efecto total de extender la
observación. No permite atribuirlo causalmente al número de bins, porque
también cambian la cola observada, los momentos del ruido del prefijo, la
normalización interna, la ventana de Hann y la cuadrícula FFT.

`NESTED_SUPPORT_HYPOTHESIS_MIXED`
"""

report_path = ROOT / "fase1_tarea13_nested_analysis_report.md"
report_path.write_text(report, encoding="utf-8")
report_word_count = len(
    re.findall(r"\b[\wÁÉÍÓÚÜÑáéíóúüñ]+\b", report)
)
if not (700 <= report_word_count <= 1000):
    raise RuntimeError(
        f"Report word count out of range: {report_word_count}"
    )

# Verify source hashes again after all analysis products are complete.
input_hashes_after = {
    filename: sha256(ROOT / filename)
    for filename in INPUT_HASHES
}
if input_hashes_after != input_hashes_before:
    raise RuntimeError("A frozen input changed during F1.13.")

output_hashes_before_audit = {
    name: sha256(ROOT / name)
    for name in OUTPUT_NAMES
    if name != "fase1_tarea13_nested_analysis_audit.json"
}

audit = {
    "analysis_status": "NESTED_ANALYSIS_COMPLETE",
    "analysis_conclusion": "NESTED_SUPPORT_HYPOTHESIS_MIXED",
    "benchmark_id": preregistration["benchmark_id"],
    "benchmark_version": preregistration["benchmark_version"],
    "absolute_tolerance": TOLERANCE,
    "input_hashes_before": input_hashes_before,
    "input_hashes_after": input_hashes_after,
    "script": {
        "filename": Path(__file__).name,
        "sha256": sha256(Path(__file__)),
    },
    "populations": {
        "primary_decisions": 2160,
        "primary_null_decisions": 720,
        "primary_positive_decisions": 1440,
        "stability_decisions": 540,
        "stability_conditions": 54,
        "optimizer_seeds_per_stability_condition": 10,
        "canary_rows_included": 0,
    },
    "nested_structure": {
        "total_trajectories": 360,
        "null_trajectories": 120,
        "positive_trajectories": 240,
        "total_transitions": 1800,
        "null_transitions": 600,
        "positive_transitions": 1200,
        "all_trajectories_complete": True,
        "all_transitions_share_parent_and_block": True,
    },
    "support_hypothesis_contrast": {
        "overall": support_summary,
        "by_transition": transition_support,
        "fully_stratified_by_transition_period_alpha": support_strata,
        "minimum_favorable_fraction_required": None,
        "post_hoc_success_threshold_added": False,
    },
    "crossings": {
        "positive": positive_crossings,
        "null": null_crossings,
    },
    "trajectory_sequences": {
        "positive": dict(sorted(positive_sequences.items())),
        "null_synthetic_false_selection": dict(
            sorted(null_sequences.items())
        ),
    },
    "selection_by_n": {
        "positive": positive_selection_by_n,
        "null_synthetic_false_selection": null_selection_by_n,
        "positive_trajectories_ever_selected": sum(
            row["ever_selected"] for row in positive_trajectories
        ),
        "null_trajectories_ever_selected": sum(
            row["ever_selected"] for row in null_trajectories
        ),
    },
    "period_recovery": {
        "recovered_period_selected": period_summary_selected,
        "all_valid_formal_m1_centers": period_summary_formal,
        "selected_execution_count": len(selected_period_rows),
        "formal_m1_center_not_selected_count": len(formal_period_rows),
    },
    "optimizer_stability": {
        "condition_count": len(stability_rows),
        "conditions_with_decision_discordance": optimizer_decision_changes,
        "m2_multiple_solution_flag_count": m2_multiple_solution_count,
        "rule": "bic_range_m2 > 0.001",
        "interpretive_guardrail":
            "stable classification ≠ unique numerical optimum",
    },
    "model_diagnostics": diagnostic_rows,
    "output_hashes_excluding_audit": output_hashes_before_audit,
    "report_word_count": report_word_count,
    "incidents": [],
    "confirmations": {
        "afino_executed": False,
        "new_curves_generated": False,
        "f1_8_to_f1_12_modified": False,
        "primary_and_stability_mixed": False,
        "canary_included": False,
        "nested_windows_treated_as_independent": False,
        "causal_bin_effect_claimed": False,
        "post_hoc_success_threshold_added": False,
        "scientific_protocol_modified": False,
    },
}

audit_path = ROOT / "fase1_tarea13_nested_analysis_audit.json"
audit_path.write_text(
    json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False)
    + "\n",
    encoding="utf-8",
)

# Final closure checks.
expected_rows = {
    "fase1_tarea13_primary_decisions_enriched.csv": 2160,
    "fase1_tarea13_condition_summary.csv": 54,
    "fase1_tarea13_nested_trajectory_summary.csv": 360,
    "fase1_tarea13_nested_transition_contrasts.csv": 1800,
    "fase1_tarea13_optimizer_stability_summary.csv": 54,
    "fase1_tarea13_model_diagnostics_by_n.csv": 18,
}
for filename, expected in expected_rows.items():
    actual = len(read_csv(ROOT / filename))
    if actual != expected:
        raise RuntimeError(
            f"{filename} has {actual} rows; expected {expected}."
        )

if len([
    row for row in transition_rows
    if row["support_hypothesis_contrast"] is not None
]) != 1200:
    raise RuntimeError("Positive support-contrast count mismatch.")

print("F1.13 nested analysis complete")
print("analysis_conclusion: NESTED_SUPPORT_HYPOTHESIS_MIXED")
print(f"primary_decisions: {len(enriched)}")
print(f"trajectories: {len(trajectory_rows)}")
print(f"transitions: {len(transition_rows)}")
print(f"support_positive_zero_negative: "
      f"{support_summary['positive_count']}/"
      f"{support_summary['zero_count']}/"
      f"{support_summary['negative_count']}")
print(f"joint_crossings_positive_up_down: "
      f"{positive_crossings['joint_selection_up']}/"
      f"{positive_crossings['joint_selection_down']}")
print(f"synthetic_false_selection_total: "
      f"{sum(v['synthetic_false_selection_count'] for v in null_selection_by_n.values())}")
print(f"optimizer_decision_discordant_conditions: {optimizer_decision_changes}")
print(f"m2_multiple_solution_conditions: {m2_multiple_solution_count}")
print(f"report_word_count: {report_word_count}")
for name in OUTPUT_NAMES:
    print(f"{name}: {sha256(ROOT / name)}")
