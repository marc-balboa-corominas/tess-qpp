#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
from collections import Counter
from pathlib import Path

import numpy as np

F3B6_COMMIT = "7776676aab1e4d2922902f4046495500864f7ca1"
F3B6_TAG = "phase3b-heldout-execution-v1"
F3B7_PROCEDURE_FREEZE_COMMIT = "19436932aaaf39e07e176f35753a12a6385818e0"
PROCEDURE_COMMIT_SUBJECT = "ops(phase3b): freeze single-use heldout unblinding procedure"
PRETRUTH_REPAIR_COMMIT_SUBJECT = "fix(phase3b): repair pre-unblinding report contract"

EXPECTED = {
    "workflows/phase3b/design/f3b1_metrics_contract.json":
        "4ff43df03a0b895944c78382b864ace92c66967e760238ffb4f83367bf9dfb22",
    "workflows/phase3b/design/f3b1_selection_function_contract.json":
        "ae2cc931d239ee25b4d5eb4c7eaf65dd00d3d2f1daaf43d96c7e8b77b33cfc51",
    "workflows/phase3b/design/f3b1_success_failure_gate.json":
        "23d65ce7dc281799a484012c19a883f27ce17fbf5af0022c856bd7b946b6bfab",
    "workflows/phase3b/design/f3b1_heldout_access_policy.json":
        "4f7276fdfec55a887e06adc5146a42e0974c9e2ca0650622972e66f593f417f3",
    "workflows/phase3b/development/analysis/f3b4_final_rule_freeze.json":
        "e2faffdbb15d6e0fec52ff166e81a2ed58f5665d7d3f9dc43cb8b78f5c0a198c",
    "workflows/phase3b/heldout/materialization/evidence/tables/f3b5_heldout_truth_ledger.csv":
        "2270ef77926c6e95a8df97b292ba6ae0a64cb081e683a1e42cf238360232c708",
    "workflows/phase3b/heldout/materialization/evidence/tables/f3b5_heldout_series_manifest.csv":
        "3b98e31137b3f1d3cc67c2a7eead70414879891556be16196f954e4682410336",
    "workflows/phase3b/heldout/materialization/evidence/tables/f3b5_heldout_admissibility.csv":
        "dfd79a20616f333f4e3f1cb0a0f0a03e46e537233554a956fa3547262af07ffe",
    "workflows/phase3b/heldout/execution/evidence/tables/f3b6_heldout_decisions_blinded.csv":
        "bc7c8720d9cdeed249301f986bcf960ef46c2d75ec4e38356a0dfa42ee3b3ab1",
    "workflows/phase3b/heldout/execution/evidence/tables/f3b6_heldout_results_blinded.csv":
        "2a55963e4b916a997efa5db5893e1b49f6a091b536fa6b98099da7733af7fe30",

    "workflows/phase3b/development/evidence/tables/f3b2_development_truth_ledger.csv":
        "a0111af78e1545507d54dcb50f7532a10b266ffe8af8f956f70c1bdf9876a820",
    "workflows/phase3b/development/evidence/tables/f3b2_development_series_manifest.csv":
        "1fc68051e3c43a9acaac5d861234fb1824d689e5e64bed5ef5810ffd0c4a6535",
    "workflows/phase3b/development/evidence/tables/f3b2_development_admissibility.csv":
        "e834f5a9635354ea8b8907ef00e707a90a23a0d78cd1e7160117a3b583b35933",
    "workflows/phase3b/development/evidence/tables/f3b3_development_decisions.csv":
        "8143bfdc87909ba6559fa5a6534107e49741ba186861d939fa89883c5c022a39",
    "workflows/phase3b/development/analysis/f3b4_baseline_evaluation.csv":
        "01e6651a7805b46d321cf4551b31b833cd73ec62cf5fbacad73bd5b83a8d44bb",
    "workflows/phase3b/development/analysis/f3b4_baseline_metrics.json":
        "718f1a03af218da8a3bc52cdea9f8007f7b3dffc3477038a5577eef0f162250c",
    "workflows/phase3b/development/analysis/f3b4_end_to_end_metrics.csv":
        "7024035e9b923040597bbef675911e194888ecd32e4e60c2492aeb0f986aab45",
    "workflows/phase3b/development/analysis/f3b4_selection_function.csv":
        "4ddd79d8a6c8778c56f3f7c78ce89e1f80d9404bc43e3e7cb892c8caf2fa2933",
    "workflows/phase3b/development/analysis/f3b4_period_recovery.csv":
        "b3a138fe9ca2c32c618b8e0d3622f9c2503fe78e955a18f60f524dc99609f65b",
    "workflows/phase3b/development/analysis/f3b4_period_recovery_summary.json":
        "1e860ddc04598b8e7adaede9d5b6d2067a0249e29fdfa91276271815eca65534",
}

EVAL_DIR = Path("workflows/phase3b/heldout/evaluation")
CONFIG_DIR = EVAL_DIR / "config"
TABLE_DIR = EVAL_DIR / "evidence/tables"
REPORT_DIR = EVAL_DIR / "evidence/reports"

BINDING = CONFIG_DIR / "f3b7_evaluation_input_binding.json"
AUTH = CONFIG_DIR / "f3b7_single_use_unblinding_authorization.json"
REGRESSION = REPORT_DIR / "f3b7_development_evaluator_regression_audit.json"

TRUTH_JOIN = TABLE_DIR / "f3b7_truth_join_audit.csv"
BASELINE_EVAL = TABLE_DIR / "f3b7_heldout_baseline_evaluation.csv"
E2E = TABLE_DIR / "f3b7_end_to_end_metrics.csv"
SELECTION = TABLE_DIR / "f3b7_heldout_selection_function.csv"
PERIOD = TABLE_DIR / "f3b7_heldout_period_recovery.csv"

METRICS = REPORT_DIR / "f3b7_heldout_baseline_metrics.json"
PERIOD_SUMMARY = REPORT_DIR / "f3b7_heldout_period_recovery_summary.json"
GATE = REPORT_DIR / "f3b7_heldout_validation_gate.json"
SINGLE_USE = REPORT_DIR / "f3b7_single_use_evaluation_audit.json"
EVALUATION_AUDIT = REPORT_DIR / "f3b7_evaluation_audit.json"
REPORT = REPORT_DIR / "f3b7_heldout_evaluation_report.md"
SUMS = EVAL_DIR / "evidence/f3b7_SHA256SUMS.txt"

FINAL_OUTPUTS = [
    TRUTH_JOIN, BASELINE_EVAL, E2E, SELECTION, PERIOD,
    METRICS, PERIOD_SUMMARY, GATE, SINGLE_USE, EVALUATION_AUDIT,
    REPORT, SUMS,
]

Z = 1.959963984540054
POS = "SYNTHETIC_QPP_PRESENT"
NEG = "SYNTHETIC_QPP_ABSENT"
PRIMARY_PLANE = "SYNTHETIC_GROUND_TRUTH_CLASSIFICATION"
CHALLENGE_PLANE = "INPUT_ADMISSIBILITY"
ELIGIBLE = "ELIGIBLE_FOR_AFINO"
PRIMARY_GAP = "CONTIGUOUS_ALL_GOOD"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(repo: Path, *args: str) -> str:
    cp = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return cp.stdout.strip()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )


def write_csv(path: Path, records: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for rec in records:
            w.writerow({k: rec.get(k, "") for k in fields})


def boolv(value) -> bool:
    return str(value).strip().lower() == "true"


def ffloat(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def close(a, b, atol=5e-12) -> bool:
    x, y = ffloat(a), ffloat(b)
    return (
        x is not None and y is not None
        and math.isclose(x, y, rel_tol=0.0, abs_tol=atol)
    )


def wilson(k: int, n: int) -> tuple[float | None, float | None, float | None]:
    if n == 0:
        return None, None, None
    p = k / n
    z2 = Z * Z
    den = 1 + z2 / n
    center = (p + z2 / (2 * n)) / den
    half = Z * math.sqrt((p * (1 - p) / n) + z2 / (4 * n * n)) / den
    return p, max(0.0, center - half), min(1.0, center + half)


def unique_index(records: list[dict[str, str]], key: str, label: str):
    out = {}
    for r in records:
        v = r[key]
        if v in out:
            raise RuntimeError(f"duplicate {label}: {v}")
        out[v] = r
    return out


def verify_hashes(repo: Path, include_heldout_content: bool = False) -> None:
    # Hashing is allowed before unblinding; this does not parse scientific content.
    for rel, expected in EXPECTED.items():
        path = repo / rel
        if not path.is_file():
            raise RuntimeError(f"missing frozen input: {rel}")
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"frozen SHA mismatch: {rel}: {actual}")


def load_decision_map(decision_rows: list[dict[str, str]], split: str):
    selected = {}
    for d in decision_rows:
        if d.get("decision_class") != "BASELINE":
            continue
        if int(d.get("external_optimizer_seed", "0")) != 0:
            continue
        sid = d["simulation_unit_id"]
        if sid in selected:
            raise RuntimeError(f"duplicate seed0 BASELINE decision: {sid}")
        if d.get("decision_status") != "VALID":
            raise RuntimeError(f"non-VALID decision in {split}: {sid}")
        if int(d.get("valid_models", "0")) != 3:
            raise RuntimeError(f"incomplete M0/M1/M2 decision in {split}: {sid}")
        d01 = float(d["delta_bic_0_1"])
        d21 = float(d["delta_bic_2_1"])
        recomputed = d01 > 10.0 and d21 > 10.0
        stored = boolv(d["qpp_selected"])
        if recomputed != stored:
            raise RuntimeError(f"frozen-rule disagreement in {split}: {sid}")
        selected[sid] = d
    return selected


def assemble_records(
    truth_rows: list[dict[str, str]],
    series_rows: list[dict[str, str]],
    admiss_rows: list[dict[str, str]],
    decision_rows: list[dict[str, str]],
    split: str,
):
    truth = unique_index(truth_rows, "simulation_unit_id", f"{split} truth id")
    series = unique_index(series_rows, "simulation_unit_id", f"{split} series id")
    admiss = unique_index(admiss_rows, "simulation_unit_id", f"{split} admiss id")
    decisions = load_decision_map(decision_rows, split)

    if set(truth) != set(series) or set(truth) != set(admiss):
        raise RuntimeError(f"{split} truth/series/admissibility identity mismatch")

    out = []
    for sid, t in truth.items():
        s = series[sid]
        a = admiss[sid]
        if t["truth_state"] != s["truth_state"] or t["truth_state"] != a["truth_state"]:
            raise RuntimeError(f"{split} truth-state mismatch: {sid}")
        if s["input_state"] != a["input_state"]:
            raise RuntimeError(f"{split} input-state mismatch: {sid}")

        primary = (
            s["evidence_plane"] == PRIMARY_PLANE
            and s["gap_quality_regime"] == PRIMARY_GAP
        )
        challenge = s["evidence_plane"] == CHALLENGE_PLANE
        d = decisions.get(sid)

        if primary and s["input_state"] == ELIGIBLE and d is None:
            raise RuntimeError(f"{split} eligible primary missing decision: {sid}")
        if challenge and d is not None:
            raise RuntimeError(f"{split} challenge has classifier decision: {sid}")

        rec = {
            "simulation_unit_id": sid,
            "truth": t,
            "series": s,
            "admissibility": a,
            "decision": d,
            "primary": primary,
            "challenge": challenge,
            "eligible": s["input_state"] == ELIGIBLE,
        }
        out.append(rec)
    return out


def primary_evaluation(records: list[dict], split: str):
    out = []
    for rec in records:
        if not rec["primary"] or not rec["eligible"]:
            continue
        t = rec["truth"]
        s = rec["series"]
        d = rec["decision"]
        if d is None:
            raise RuntimeError("missing decision")
        selected = boolv(d["qpp_selected"])
        truth_state = t["truth_state"]
        if truth_state == POS:
            outcome = "TP" if selected else "FN"
        elif truth_state == NEG:
            outcome = "FP" if selected else "TN"
        else:
            raise RuntimeError(f"unexpected primary truth state: {truth_state}")

        out.append({
            "simulation_unit_id": rec["simulation_unit_id"],
            "planned_decision_id": d["planned_decision_id"],
            "background_realization_id": s["background_realization_id"],
            "truth_state": truth_state,
            "qpp_selected": selected,
            "delta_bic_0_1": float(d["delta_bic_0_1"]),
            "delta_bic_2_1": float(d["delta_bic_2_1"]),
            "baseline_threshold_01": 10.0,
            "baseline_threshold_21": 10.0,
            "baseline_comparison": "STRICT_GREATER_THAN",
            "baseline_selected_recomputed": (
                float(d["delta_bic_0_1"]) > 10.0
                and float(d["delta_bic_2_1"]) > 10.0
            ),
            "baseline_rule_agreement": True,
            "classification_outcome": outcome,
            "input_state": s["input_state"],
            "n_samples": int(t["n_samples"]),
            "red_noise_alpha": float(t["red_noise_alpha"]),
            "qpp_fraction": t["qpp_fraction"],
            "true_period_s": t["true_period_s"],
            "truth_usage": "EVALUATION_TARGET_ONLY_NOT_RULE_FEATURE",
            "evaluation_scope": f"{split}_SYNTHETIC_GROUND_TRUTH",
            "formal_m1_period_s": d.get("formal_m1_period_s", ""),
            "period_label": d.get("period_label", ""),
        })
    return out


def confusion(eval_rows: list[dict]):
    c = Counter(r["classification_outcome"] for r in eval_rows)
    required = {"TP", "FN", "TN", "FP"}
    if set(c) - required:
        raise RuntimeError("unexpected classification outcome")
    return {k: int(c.get(k, 0)) for k in ["TP", "FN", "TN", "FP"]}


def metrics_object(eval_rows: list[dict], split: str):
    c = confusion(eval_rows)
    tp, fn, tn, fp = c["TP"], c["FN"], c["TN"], c["FP"]
    sens = wilson(tp, tp + fn)
    spec = wilson(tn, tn + fp)
    fpr = wilson(fp, fp + tn)
    ba = 0.5 * (sens[0] + spec[0])

    def m(k, n, vals):
        return {
            "numerator": k,
            "denominator": n,
            "point_estimate": vals[0],
            "interval": {
                "method": "CLOSED_FORM_STANDARD_WILSON_SCORE",
                "confidence_level": 0.95,
                "lower": vals[1],
                "upper": vals[2],
            },
        }

    return {
        "schema_version": "1.0.0",
        "artifact_role": "HELDOUT_BASELINE_CLASSIFICATION_METRICS" if split == "HELDOUT" else "DEVELOPMENT_EVALUATOR_REGRESSION_METRICS",
        "phase": "F3B.7" if split == "HELDOUT" else "F3B.7_PRETRUTH_REGRESSION",
        "interpretation": f"{split} synthetic-ground-truth performance of the frozen AFINO 0.5 baseline.",
        "scope": {
            "split": split,
            "synthetic_domain_only": True,
            "input_condition": ELIGIBLE,
            "gap_quality_regime": PRIMARY_GAP,
            "optimizer_seed": 0,
            "observational_performance_claim": False,
        },
        "baseline_rule": {
            "rule": "delta_BIC01 > 10 AND delta_BIC21 > 10",
            "comparison": "STRICT_GREATER_THAN",
            "t01": 10.0,
            "t21": 10.0,
        },
        "confusion_matrix": {**c, "total": len(eval_rows)},
        "primary_classification_metrics": {
            "sensitivity_TPR": m(tp, tp + fn, sens),
            "specificity_TNR": m(tn, tn + fp, spec),
            "false_positive_rate_FPR": m(fp, fp + tn, fpr),
        },
        "secondary_classification_summary": {
            "balanced_accuracy": {
                "formula": "0.5*(sensitivity_TPR+specificity_TNR)",
                "point_estimate": ba,
                "wilson_interval": "NOT_APPLICABLE_NOT_SINGLE_BINOMIAL_PROPORTION",
            }
        },
    }


def selection_candidates(records: list[dict]):
    out = []
    for rec in records:
        if not rec["primary"]:
            continue
        t = rec["truth"]
        d = rec["decision"]
        out.append({
            "simulation_unit_id": rec["simulation_unit_id"],
            "truth_state": t["truth_state"],
            "n_samples": int(t["n_samples"]),
            "red_noise_alpha": float(t["red_noise_alpha"]),
            "qpp_fraction": ffloat(t["qpp_fraction"]),
            "true_period_s": ffloat(t["true_period_s"]),
            "eligible": rec["eligible"],
            "selected": boolv(d["qpp_selected"]) if d is not None else False,
        })
    return out


def filter_for_template(candidates: list[dict], template: dict):
    truth = template["truth_state"]
    n = int(template["n_samples"])
    alpha = float(template["red_noise_alpha"])
    qf = ffloat(template.get("qpp_fraction", ""))
    bin_id = template.get("period_bin_id", "").strip()
    lo = ffloat(template.get("period_lower_s", ""))
    hi = ffloat(template.get("period_upper_s", ""))
    lo_inc = boolv(template.get("period_lower_inclusive", "false"))
    hi_inc = boolv(template.get("period_upper_inclusive", "false"))

    out = []
    for c in candidates:
        if c["truth_state"] != truth or c["n_samples"] != n:
            continue
        if not math.isclose(c["red_noise_alpha"], alpha, rel_tol=0.0, abs_tol=1e-12):
            continue
        if truth == POS:
            if qf is None or c["qpp_fraction"] is None or not math.isclose(c["qpp_fraction"], qf, rel_tol=0.0, abs_tol=1e-12):
                continue
            if bin_id:
                p = c["true_period_s"]
                if p is None:
                    continue
                lower_ok = p >= lo if lo_inc else p > lo
                upper_ok = p <= hi if hi_inc else p < hi
                if not (lower_ok and upper_ok):
                    continue
        out.append(c)
    return out


def metric_cells(k: int, n: int):
    p, lo, hi = wilson(k, n)
    if n == 0:
        return "", "", ""
    return p, lo, hi


def build_selection(records: list[dict], template_rows: list[dict]):
    candidates = selection_candidates(records)
    output = []
    for template in template_rows:
        group = filter_for_template(candidates, template)
        planned = len(group)
        eligible = sum(c["eligible"] for c in group)
        selected = sum(c["eligible"] and c["selected"] for c in group)

        structural_template = template["exposure_status"] == "STRUCTURAL_NO_EXPOSURE"
        if structural_template and planned != 0:
            raise RuntimeError("structural no-exposure topology changed")
        if not structural_template and planned == 0:
            raise RuntimeError("unexpected zero-exposure cell outside frozen structural topology")

        ip, ilo, ihi = metric_cells(eligible, planned)
        cp, clo, chi = metric_cells(selected, eligible)
        ep, elo, ehi = metric_cells(selected, planned)

        row = dict(template)
        row["exposure_status"] = "STRUCTURAL_NO_EXPOSURE" if planned == 0 else template["exposure_status"]
        row["exposure_count"] = eligible
        row["selected_count"] = selected
        row["input_eligibility_numerator"] = eligible
        row["input_eligibility_denominator"] = planned
        row["input_eligibility_point_estimate"] = ip
        row["input_eligibility_wilson_95_lower"] = ilo
        row["input_eligibility_wilson_95_upper"] = ihi
        row["conditional_selection_numerator"] = selected
        row["conditional_selection_denominator"] = eligible
        row["conditional_selection_point_estimate"] = cp
        row["conditional_selection_wilson_95_lower"] = clo
        row["conditional_selection_wilson_95_upper"] = chi
        row["end_to_end_selection_numerator"] = selected
        row["end_to_end_selection_denominator"] = planned
        row["end_to_end_selection_point_estimate"] = ep
        row["end_to_end_selection_wilson_95_lower"] = elo
        row["end_to_end_selection_wilson_95_upper"] = ehi
        row["primary_representation"] = "STRATIFIED_EMPIRICAL"
        row["probabilistic_model_fitted"] = False
        row["challenge_rows_included"] = 0
        output.append(row)
    return output


def compare_selection(recomputed: list[dict], frozen: list[dict]):
    if len(recomputed) != 156 or len(frozen) != 156:
        raise RuntimeError("selection-function row count mismatch")
    integer_fields = [
        "exposure_count", "selected_count",
        "input_eligibility_numerator", "input_eligibility_denominator",
        "conditional_selection_numerator", "conditional_selection_denominator",
        "end_to_end_selection_numerator", "end_to_end_selection_denominator",
    ]
    float_fields = [
        "input_eligibility_point_estimate",
        "input_eligibility_wilson_95_lower",
        "input_eligibility_wilson_95_upper",
        "conditional_selection_point_estimate",
        "conditional_selection_wilson_95_lower",
        "conditional_selection_wilson_95_upper",
        "end_to_end_selection_point_estimate",
        "end_to_end_selection_wilson_95_lower",
        "end_to_end_selection_wilson_95_upper",
    ]
    mismatches = 0
    for a, b in zip(recomputed, frozen):
        if a["stratum_order"] != b["stratum_order"]:
            mismatches += 1
            continue
        for field in integer_fields:
            if int(a[field]) != int(b[field]):
                mismatches += 1
                break
        else:
            for field in float_fields:
                av = ffloat(a[field])
                bv = ffloat(b[field])
                if av is None and bv is None:
                    continue
                if av is None or bv is None or not math.isclose(av, bv, rel_tol=0.0, abs_tol=5e-12):
                    mismatches += 1
                    break
    structural = sum(r["exposure_status"] == "STRUCTURAL_NO_EXPOSURE" for r in recomputed)
    return mismatches, structural


def build_period(eval_rows: list[dict]):
    out = []
    for r in eval_rows:
        if r["classification_outcome"] != "TP":
            continue
        true_p = ffloat(r["true_period_s"])
        recovered = ffloat(r["formal_m1_period_s"])
        if true_p is None or recovered is None or recovered <= 0:
            continue
        if not (40.0 <= recovered <= 300.0):
            continue
        ae = abs(recovered - true_p)
        re = ae / true_p
        lr = math.log(recovered / true_p)
        out.append({
            "simulation_unit_id": r["simulation_unit_id"],
            "planned_decision_id": r["planned_decision_id"],
            "background_realization_id": r["background_realization_id"],
            "n_samples": r["n_samples"],
            "red_noise_alpha": r["red_noise_alpha"],
            "qpp_fraction": r["qpp_fraction"],
            "true_period_s": true_p,
            "recovered_period_s": recovered,
            "absolute_period_error_s": ae,
            "relative_period_error": re,
            "log_period_ratio": lr,
            "classification_outcome": "TP",
            "period_label": r["period_label"],
            "period_recovery_status": "FINITE_SELECTED_TRUE_POSITIVE",
            "nonselected_m1_center_used": False,
        })
    return out


def period_summary(period_rows: list[dict], eval_rows: list[dict], split: str):
    positive = [r for r in eval_rows if r["truth_state"] == POS]
    tp = [r for r in eval_rows if r["classification_outcome"] == "TP"]
    n = len(period_rows)

    def dist(field):
        arr = np.asarray([float(r[field]) for r in period_rows], dtype=float)
        if len(arr) == 0:
            return {
                "n": 0,
                "median": None,
                "empirical_percentile_16": None,
                "empirical_percentile_84": None,
                "quantile_implementation": "numpy.quantile",
                "quantile_method": "linear",
            }
        return {
            "n": len(arr),
            "median": float(np.quantile(arr, 0.5, method="linear")),
            "empirical_percentile_16": float(np.quantile(arr, 0.16, method="linear")),
            "empirical_percentile_84": float(np.quantile(arr, 0.84, method="linear")),
            "quantile_implementation": "numpy.quantile",
            "quantile_method": "linear",
        }

    return {
        "schema_version": "1.0.0",
        "artifact_role": "HELDOUT_BASELINE_PERIOD_RECOVERY_SUMMARY" if split == "HELDOUT" else "DEVELOPMENT_EVALUATOR_PERIOD_REGRESSION",
        "phase": "F3B.7" if split == "HELDOUT" else "F3B.7_PRETRUTH_REGRESSION",
        "scope": {
            "split": split,
            "truth_state": POS,
            "input_condition": ELIGIBLE,
            "optimizer_seed": 0,
            "selected_only_for_recovered_period": True,
            "synthetic_domain_only": True,
            "observational_period_claim": False,
        },
        "population": {
            "eligible_positive_injections": len(positive),
            "baseline_true_positives": len(tp),
            "selected_true_positives_with_finite_period": n,
            "selected_true_positives_missing_finite_period": len(tp) - n,
        },
        "period_estimate_coverage_fraction": {
            "numerator": n,
            "denominator": len(positive),
            "denominator_definition": "ALL_ELIGIBLE_SYNTHETIC_QPP_PRESENT",
            "point_estimate": n / len(positive) if positive else None,
        },
        "selected_true_positive_error_distributions": {
            "absolute_period_error_s": dist("absolute_period_error_s"),
            "relative_period_error": dist("relative_period_error"),
            "log_period_ratio": dist("log_period_ratio"),
        },
        "period_semantics": {
            "period_recovered_within_X_percent_threshold": "NOT_USED",
            "nonselected_error_imputation": "PROHIBITED",
            "nonselected_m1_center_is_period_recovery": False,
        },
    }


def compare_period(recomputed: list[dict], frozen: list[dict], frozen_summary: dict):
    a = {r["simulation_unit_id"]: r for r in recomputed}
    b = {r["simulation_unit_id"]: r for r in frozen}
    if set(a) != set(b):
        return 1
    mismatches = 0
    for sid in a:
        for field in [
            "true_period_s", "recovered_period_s",
            "absolute_period_error_s", "relative_period_error", "log_period_ratio",
        ]:
            if not close(a[sid][field], b[sid][field]):
                mismatches += 1
    summary = period_summary(recomputed, [
        # Dummy eval population is not used below; compare distributions separately.
    ], "DEVELOPMENT")
    # Recompute directly to avoid dummy-population fields.
    for field in ["absolute_period_error_s", "relative_period_error", "log_period_ratio"]:
        arr = np.asarray([float(r[field]) for r in recomputed], dtype=float)
        expected = frozen_summary["selected_true_positive_error_distributions"][field]
        if len(arr) != int(expected["n"]):
            mismatches += 1
        for q, key in [(0.5, "median"), (0.16, "empirical_percentile_16"), (0.84, "empirical_percentile_84")]:
            v = float(np.quantile(arr, q, method="linear"))
            if not math.isclose(v, float(expected[key]), rel_tol=0.0, abs_tol=5e-12):
                mismatches += 1
    return mismatches


def development_regression(repo: Path, audit_path: Path):
    verify_hashes(repo)

    truth = rows(repo / "workflows/phase3b/development/evidence/tables/f3b2_development_truth_ledger.csv")
    series = rows(repo / "workflows/phase3b/development/evidence/tables/f3b2_development_series_manifest.csv")
    admiss = rows(repo / "workflows/phase3b/development/evidence/tables/f3b2_development_admissibility.csv")
    decisions = rows(repo / "workflows/phase3b/development/evidence/tables/f3b3_development_decisions.csv")

    records = assemble_records(truth, series, admiss, decisions, "DEVELOPMENT")
    ev = primary_evaluation(records, "DEVELOPMENT")
    if len(ev) != 3600:
        raise RuntimeError("DEVELOPMENT primary evaluation != 3600")

    m = metrics_object(ev, "DEVELOPMENT")
    frozen_m = load_json(repo / "workflows/phase3b/development/analysis/f3b4_baseline_metrics.json")

    c = m["confusion_matrix"]
    expected_c = frozen_m["confusion_matrix"]
    if any(int(c[k]) != int(expected_c[k]) for k in ["TP", "FN", "TN", "FP", "total"]):
        raise RuntimeError("DEVELOPMENT confusion matrix regression failed")

    metric_mismatches = 0
    for key in ["sensitivity_TPR", "specificity_TNR", "false_positive_rate_FPR"]:
        a = m["primary_classification_metrics"][key]
        b = frozen_m["primary_classification_metrics"][key]
        for field in ["numerator", "denominator", "point_estimate"]:
            if field in ["numerator", "denominator"]:
                if int(a[field]) != int(b[field]):
                    metric_mismatches += 1
            elif not close(a[field], b[field]):
                metric_mismatches += 1
        if not close(a["interval"]["lower"], b["wilson_95_lower"]):
            metric_mismatches += 1
        if not close(a["interval"]["upper"], b["wilson_95_upper"]):
            metric_mismatches += 1

    ba = m["secondary_classification_summary"]["balanced_accuracy"]["point_estimate"]
    if not close(ba, frozen_m["secondary_classification_summary"]["balanced_accuracy"]["point_estimate"]):
        metric_mismatches += 1

    frozen_selection = rows(repo / "workflows/phase3b/development/analysis/f3b4_selection_function.csv")
    recomputed_selection = build_selection(records, frozen_selection)
    selection_mismatches, structural = compare_selection(recomputed_selection, frozen_selection)

    frozen_period = rows(repo / "workflows/phase3b/development/analysis/f3b4_period_recovery.csv")
    frozen_ps = load_json(repo / "workflows/phase3b/development/analysis/f3b4_period_recovery_summary.json")
    recomputed_period = build_period(ev)
    period_mismatches = compare_period(recomputed_period, frozen_period, frozen_ps)

    frozen_e2e = rows(repo / "workflows/phase3b/development/analysis/f3b4_end_to_end_metrics.csv")
    if len(frozen_e2e) != 9:
        raise RuntimeError("frozen DEVELOPMENT end-to-end rows != 9")

    if metric_mismatches or selection_mismatches or period_mismatches:
        raise RuntimeError(
            f"DEVELOPMENT evaluator regression mismatch: metrics={metric_mismatches} "
            f"selection={selection_mismatches} period={period_mismatches}"
        )

    if structural != 9 or len(recomputed_period) != 143:
        raise RuntimeError("DEVELOPMENT selection/period structural contract failed")

    audit = {
        "schema_version": "1.0.0",
        "artifact_role": "F3B7_DEVELOPMENT_EVALUATOR_REGRESSION_AUDIT",
        "phase": "F3B.7_PRETRUTH",
        "status": "PASS",
        "heldout_truth_content_read": False,
        "heldout_series_content_read": False,
        "heldout_admissibility_content_read": False,
        "new_afino_calls": 0,
        "generator_calls": 0,
        "development": {
            "classifier_rows": 3600,
            "TP": c["TP"],
            "FN": c["FN"],
            "TN": c["TN"],
            "FP": c["FP"],
            "sensitivity": m["primary_classification_metrics"]["sensitivity_TPR"]["point_estimate"],
            "specificity": m["primary_classification_metrics"]["specificity_TNR"]["point_estimate"],
            "FPR": m["primary_classification_metrics"]["false_positive_rate_FPR"]["point_estimate"],
            "balanced_accuracy": ba,
            "wilson_95_exact": True,
            "selection_function_rows": len(recomputed_selection),
            "STRUCTURAL_NO_EXPOSURE": structural,
            "period_rows": len(recomputed_period),
            "metric_mismatches": metric_mismatches,
            "selection_function_mismatches": selection_mismatches,
            "period_recovery_mismatches": period_mismatches,
            "frozen_end_to_end_rows": len(frozen_e2e),
        },
        "result": "F3B7_DEVELOPMENT_EVALUATOR_REGRESSION_PASS",
    }
    if audit_path.exists():
        raise RuntimeError(f"refusing overwrite: {audit_path}")
    write_json(audit_path, audit)
    print("F3B7_DEVELOPMENT_EVALUATOR_REGRESSION_PASS")
    print("TP = 143")
    print("FN = 1657")
    print("TN = 1799")
    print("FP = 1")
    print("selection_function_rows = 156")
    print("STRUCTURAL_NO_EXPOSURE = 9")
    print("period_rows = 143")
    print("heldout_truth_content_read = false")
    print("new_afino_calls = 0")
    print("generator_calls = 0")


def truth_join_rows(records: list[dict]):
    out = []
    for rec in records:
        t, s, d = rec["truth"], rec["series"], rec["decision"]
        expected = rec["primary"] and rec["eligible"]
        out.append({
            "simulation_unit_id": rec["simulation_unit_id"],
            "background_realization_id": s["background_realization_id"],
            "truth_state": t["truth_state"],
            "evidence_plane": s["evidence_plane"],
            "gap_quality_regime": s["gap_quality_regime"],
            "input_state": s["input_state"],
            "materialization_status": s["materialization_status"],
            "classifier_decision_expected": expected,
            "classifier_decision_present": d is not None,
            "planned_decision_id": "" if d is None else d["planned_decision_id"],
            "decision_status": "" if d is None else d["decision_status"],
            "qpp_selected": "" if d is None else d["qpp_selected"],
            "truth_join_status": "JOINED_PRIMARY" if expected else "AUDITED_NONCLASSIFIER_CHALLENGE",
        })
    return out


def end_to_end_rows(records: list[dict], eval_rows: list[dict]):
    output = []
    primary = [r for r in records if r["primary"]]
    positive = [r for r in primary if r["truth"]["truth_state"] == POS]
    null = [r for r in primary if r["truth"]["truth_state"] == NEG]
    eligible_primary = sum(r["eligible"] for r in primary)
    tp = sum(r["classification_outcome"] == "TP" for r in eval_rows)
    fp = sum(r["classification_outcome"] == "FP" for r in eval_rows)

    def add(scope_id, plane, metric, k, n, denom_def, semantics):
        p, lo, hi = wilson(k, n)
        output.append({
            "scope_id": scope_id,
            "evidence_plane": plane,
            "design_interpretation": "SYNTHETIC_DESIGN_MIXTURE",
            "observational_prevalence": "NOT_OBSERVATIONAL_PREVALENCE",
            "metric": metric,
            "numerator": k,
            "denominator": n,
            "point_estimate": p,
            "wilson_95_lower": lo,
            "wilson_95_upper": hi,
            "denominator_definition": denom_def,
            "classification_metric_synonym": False,
            "input_inadmissible_recoded_as_FN_or_TN": False,
            "pipeline_semantics": semantics,
        })

    add("PRIMARY_ALL", PRIMARY_PLANE, "input_admissibility_fraction",
        eligible_primary, len(primary), "all planned primary series",
        "input admissibility is distinct from classification")
    add("PRIMARY_POSITIVE", PRIMARY_PLANE, "end_to_end_positive_recovery_fraction",
        tp, len(positive), "all planned synthetic-positive primary series",
        "selected positive / all planned positive")
    add("PRIMARY_NULL", PRIMARY_PLANE, "end_to_end_null_selection_fraction",
        fp, len(null), "all planned synthetic-null primary series",
        "selected null / all planned null")

    challenges = [r for r in records if r["challenge"]]
    add("CHALLENGE_ALL", CHALLENGE_PLANE, "input_admissibility_fraction",
        sum(r["eligible"] for r in challenges), len(challenges),
        "all planned INPUT_ADMISSIBILITY challenge series",
        "challenge admissibility only; never recoded as FN/TN")

    regimes = sorted({r["series"]["gap_quality_regime"] for r in challenges})
    for regime in regimes:
        rr = [r for r in challenges if r["series"]["gap_quality_regime"] == regime]
        add(f"CHALLENGE_{regime}", CHALLENGE_PLANE, "input_admissibility_fraction",
            sum(r["eligible"] for r in rr), len(rr),
            f"planned challenge series in {regime}",
            "challenge admissibility only; never prevalence-weighted observationally")
    return output


def report_text(metrics, e2e_rows, selection_rows, ps, gate):
    c = metrics["confusion_matrix"]
    pm = metrics["primary_classification_metrics"]
    ba = metrics["secondary_classification_summary"]["balanced_accuracy"]["point_estimate"]
    structural = sum(r["exposure_status"] == "STRUCTURAL_NO_EXPOSURE" for r in selection_rows)
    report = f"""# Phase 3B.7 — Single-use HELDOUT baseline evaluation

## 1. Single-use boundary

Phase 3B.7 is the first and only stage in which the frozen HELDOUT blind decisions are joined to the independently generated synthetic ground truth. The classification outputs were already frozen in Phase 3B.6 before any truth inspection. This evaluation does not execute AFINO, regenerate simulations, search candidate rules, modify thresholds, refit the decision rule, or reopen DEVELOPMENT for tuning. The HELDOUT dataset is consumed as a single-use validation set at the moment the authorized truth join is performed. Any future method change would require a new independent validation dataset and a new prospective freeze.

The inference rule remains the frozen AFINO 0.5 baseline: `delta_BIC01 > 10 AND delta_BIC21 > 10`, with strict greater-than semantics and thresholds t01=t21=10. The candidate developed in DEVELOPMENT was not promoted; consequently the HELDOUT branch is BASELINE_ONLY and no candidate-versus-baseline test is performed.

## 2. Evaluator regression before unblinding

Before opening HELDOUT truth, the final evaluator was exercised against the frozen DEVELOPMENT products. It reproduced the DEVELOPMENT confusion matrix TP=143, FN=1657, TN=1799 and FP=1; sensitivity, specificity, FPR and balanced accuracy; all Wilson 95% intervals; the 156-row empirical selection-function representation with nine STRUCTURAL_NO_EXPOSURE cells; and the 143 selected-true-positive period-recovery rows. The regression therefore demonstrated that the metric implementation was not being used for the first time on HELDOUT. The evaluator, input binding, authorization, validator and tests were then frozen in a dedicated Git commit before the truth join.

## 3. Truth join

The authorized join accounts for all 4,320 HELDOUT synthetic series. Exactly 3,600 belong to the primary CONTIGUOUS_ALL_GOOD classifier plane, split prospectively into 1,800 SYNTHETIC_QPP_PRESENT and 1,800 SYNTHETIC_QPP_ABSENT series. Each of those primary eligible series has exactly one frozen BASELINE seed-0 decision. The remaining 720 series belong to the INPUT_ADMISSIBILITY challenge plane and have no classifier decision by design. They are audited separately and are never converted into false negatives or true negatives. Missing truth rows, duplicated simulation identifiers, unexpected challenge decisions and missing primary decisions are all prohibited by the evaluation gate.

## 4. Baseline HELDOUT confusion matrix

The prospective HELDOUT confusion matrix of the frozen baseline is TP={c['TP']}, FN={c['FN']}, TN={c['TN']} and FP={c['FP']}. These counts sum to 1,800 synthetic-positive and 1,800 synthetic-null primary observations exactly. The result is a synthetic-ground-truth characterization of the frozen classifier in the preregistered simulation domain. It is not an observational sensitivity or specificity estimate, and it does not establish physical truth for the earlier observational catalogue labels.

## 5. Sensitivity, specificity and false-positive rate

HELDOUT sensitivity is {pm['sensitivity_TPR']['point_estimate']:.17g}, specificity is {pm['specificity_TNR']['point_estimate']:.17g}, FPR is {pm['false_positive_rate_FPR']['point_estimate']:.17g}, and balanced accuracy is {ba:.17g}. Sensitivity, specificity and FPR each report their numerator, denominator, point estimate and a separately calculated closed-form 95% Wilson score interval. Balanced accuracy is retained as the arithmetic mean of sensitivity and specificity and is not assigned a Wilson interval because it is not a single binomial proportion. Poor or strong performance cannot change the formal success branch: the preregistration explicitly treats baseline performance as a scientific result rather than an execution threshold.

## 6. End-to-end behavior and inadmissibility

Input admissibility remains separate from classifier performance. The end-to-end table reports the primary input-admissibility fraction, positive recovery fraction and null selection fraction with explicit denominators, and separately records admissibility for the 720 challenge series and their frozen gap-quality regimes. Challenge rows are not prevalence-weighted as observational frequencies. Any aggregate across the synthetic design is labelled SYNTHETIC_DESIGN_MIXTURE and NOT_OBSERVATIONAL_PREVALENCE. Numerical equality between conditional and end-to-end primary quantities can occur when all primary series are eligible, but their meanings remain distinct.

## 7. HELDOUT selection function

The primary selection function preserves the preregistered STRATIFIED_EMPIRICAL representation. It contains 36 positive base strata over n_samples, red_noise_alpha and qpp_fraction; 108 positive period-expanded strata using the frozen P40_63, P63_106 and P106_300 bins; and 12 null strata pooled only across the paired qpp_fraction label as prospectively specified. The resulting table therefore contains exactly 156 rows. Structural impossibility is retained explicitly: {structural} cells are marked STRUCTURAL_NO_EXPOSURE rather than being fabricated as zero rates. Every exposed empirical proportion records its numerator and denominator and uses a 95% Wilson interval. No probabilistic selection model is fitted and no predictor, bin or pooling rule is changed after HELDOUT inspection.

## 8. Period recovery

Period recovery is computed only for eligible SYNTHETIC_QPP_PRESENT series that were selected by the frozen baseline and have a finite in-support formal M1 period estimate. The coverage numerator is {ps['period_estimate_coverage_fraction']['numerator']} out of 1,800 eligible positive injections. Non-selected M1 centers are not imputed as recovered periods. For the finite selected true positives, absolute period error, relative period error and log period ratio are reported row by row; their summaries use the median and the 16th and 84th empirical percentiles under numpy.quantile with the frozen linear method. No within-X-percent recovery threshold is introduced.

## 9. HELDOUT validation gate

The predetermined branch is BASELINE_ONLY. Its success requirements are complete HELDOUT baseline characterization under the frozen metrics contract and absence of DEVELOPMENT retuning after HELDOUT generation. The evaluation records the formal state `{gate['status']}` and the correction claim `NOT_ESTABLISHED`. This conclusion does not depend on whether the numerical sensitivity is high or low. There is no HELDOUT candidate comparison because `candidate_rule_promoted=false`.

## 10. Limitations

These results apply to the synthetic family and parameter domain fixed prospectively in F3B.1. The positive and null proportions are controlled experimental allocations, not observational prevalence. The empirical selection function describes the sampled synthetic domain and its frozen strata; it is not a fitted population model. The input-admissibility challenges diagnose pipeline eligibility separately from classifier discrimination. Period recovery is conditional on true-positive selection and finite M1 period availability. Numerical optimizer stability is not rerun in HELDOUT: the extra-seed stability study remains a DEVELOPMENT-only diagnostic by design.

A second limitation concerns interpretation across controlled strata. The experiment deliberately balances positive and null allocations and samples nuisance parameters according to the frozen simulation plan; therefore the unconditional mixture in this report has no direct population-frequency meaning. Stratum-specific differences may nevertheless be scientifically informative within the simulated domain, especially where cadence length, red-noise slope, QPP fraction or period support alter eligibility or selection. Those differences should be carried forward descriptively into the final Phase 3B synthesis, without using the consumed HELDOUT outcomes to redesign thresholds, merge strata, introduce new predictors or choose a different representation.

## 11. Continuing prohibitions

The consumed HELDOUT set cannot be reused to invent or tune a new classification rule. No threshold tweak, feature addition, alternate candidate search, additional optimizer seeds, new AFINO execution, generator execution or DEVELOPMENT retuning is authorized. A revised method would require a new independent validation dataset and a new prospective freeze. Phase 3B.7 therefore closes with a frozen prospective baseline characterization, not with a claim that an observational correction has been established. The broader DEVELOPMENT-to-HELDOUT synthesis and final claim matrix belong to Phase 3B.8 rather than this report.
"""
    wc = len(report.split())
    if not 1100 <= wc <= 1500:
        raise RuntimeError(f"HELDOUT report word count outside 1100..1500: {wc}")
    return report


def heldout_evaluate(repo: Path):
    # Critical activation checks BEFORE opening HELDOUT scientific content.
    verify_hashes(repo)
    if git(repo, "rev-parse", "HEAD^") != F3B7_PROCEDURE_FREEZE_COMMIT:
        raise RuntimeError("active pretruth repair commit parent mismatch")
    if git(repo, "rev-parse", "HEAD^^") != F3B6_COMMIT:
        raise RuntimeError("procedure-freeze ancestry no longer descends from F3B.6")
    if git(repo, "log", "-1", "--pretty=%s", "HEAD^") != PROCEDURE_COMMIT_SUBJECT:
        raise RuntimeError("original procedure-freeze commit subject mismatch")
    if git(repo, "log", "-1", "--pretty=%s") != PRETRUTH_REPAIR_COMMIT_SUBJECT:
        raise RuntimeError("active pretruth repair commit subject mismatch")
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise RuntimeError("working tree must be clean before single-use unblinding")

    auth = load_json(repo / AUTH)
    if auth["status"] != "AUTHORIZED_AFTER_PRETRUTH_REPAIR_FREEZE_COMMIT":
        raise RuntimeError("unblinding authorization status mismatch")
    p = auth["permissions"]
    required_true = [
        "truth_join_authorized", "heldout_metrics_authorized",
        "heldout_selection_function_authorized", "heldout_period_metrics_authorized",
    ]
    required_false = [
        "new_afino_execution_authorized", "generator_execution_authorized",
        "candidate_search_authorized", "threshold_mutation_authorized",
        "rule_refitting_authorized", "development_retuning_authorized",
        "heldout_optimizer_stability_authorized",
    ]
    if any(p[k] is not True for k in required_true):
        raise RuntimeError("required evaluation permission missing")
    if any(p[k] is not False for k in required_false):
        raise RuntimeError("prohibited permission enabled")

    for path in FINAL_OUTPUTS:
        if (repo / path).exists():
            raise RuntimeError(f"single-use output already exists: {path}")

    runtime = repo / "runtime/phase3b/f3b7"
    runtime.mkdir(parents=True, exist_ok=True)
    marker = runtime / "HELDOUT_TRUTH_CONSUMED.json"
    if marker.exists():
        raise RuntimeError("HELDOUT truth-consumption marker already exists")

    marker_obj = {
        "phase": "F3B.7",
        "status": "TRUTH_OPEN_AUTHORIZED_SINGLE_USE_CONSUMED",
        "procedure_freeze_commit": F3B7_PROCEDURE_FREEZE_COMMIT,
        "pretruth_repair_commit": git(repo, "rev-parse", "HEAD"),
        "truth_sha256": EXPECTED["workflows/phase3b/heldout/materialization/evidence/tables/f3b5_heldout_truth_ledger.csv"],
        "new_afino_calls": 0,
        "generator_calls": 0,
    }
    write_json(marker, marker_obj)

    # First scientific HELDOUT truth-content read occurs here, after the marker.
    truth = rows(repo / "workflows/phase3b/heldout/materialization/evidence/tables/f3b5_heldout_truth_ledger.csv")
    series = rows(repo / "workflows/phase3b/heldout/materialization/evidence/tables/f3b5_heldout_series_manifest.csv")
    admiss = rows(repo / "workflows/phase3b/heldout/materialization/evidence/tables/f3b5_heldout_admissibility.csv")
    decisions = rows(repo / "workflows/phase3b/heldout/execution/evidence/tables/f3b6_heldout_decisions_blinded.csv")

    records = assemble_records(truth, series, admiss, decisions, "HELDOUT")
    if len(records) != 4320:
        raise RuntimeError("HELDOUT total series != 4320")

    primary = [r for r in records if r["primary"]]
    challenges = [r for r in records if r["challenge"]]
    if len(primary) != 3600 or len(challenges) != 720:
        raise RuntimeError("HELDOUT primary/challenge counts mismatch")
    if Counter(r["truth"]["truth_state"] for r in primary) != Counter({POS: 1800, NEG: 1800}):
        raise RuntimeError("HELDOUT primary truth balance mismatch")
    if any(not r["eligible"] for r in primary):
        raise RuntimeError("HELDOUT primary contains non-eligible series")
    if any(r["decision"] is None for r in primary):
        raise RuntimeError("HELDOUT primary missing blind decision")
    if any(r["decision"] is not None for r in challenges):
        raise RuntimeError("HELDOUT challenge has classifier decision")

    tj = truth_join_rows(records)
    ev = primary_evaluation(records, "HELDOUT")
    m = metrics_object(ev, "HELDOUT")
    e2e = end_to_end_rows(records, ev)

    template = rows(repo / "workflows/phase3b/development/analysis/f3b4_selection_function.csv")
    sel = build_selection(records, template)
    if len(sel) != 156:
        raise RuntimeError("HELDOUT selection rows != 156")
    if sum(r["exposure_status"] == "STRUCTURAL_NO_EXPOSURE" for r in sel) != 9:
        raise RuntimeError("HELDOUT structural no-exposure topology != 9")

    per = build_period(ev)
    ps = period_summary(per, ev, "HELDOUT")

    c = m["confusion_matrix"]
    if c["TP"] + c["FN"] != 1800 or c["TN"] + c["FP"] != 1800:
        raise RuntimeError("HELDOUT confusion denominators mismatch")

    gate = {
        "schema_version": "1.0.0",
        "artifact_role": "F3B7_HELDOUT_VALIDATION_GATE",
        "phase": "F3B.7",
        "branch": "BASELINE_ONLY",
        "criteria": {
            "complete_heldout_baseline_characterization": True,
            "no_development_retuning_after_heldout_generation": True,
        },
        "performance_threshold_required": False,
        "status": "HELDOUT_BASELINE_CHARACTERIZATION_SUCCESS",
        "correction_claim": "NOT_ESTABLISHED",
        "candidate_rule_promoted": False,
    }

    single = {
        "schema_version": "1.0.0",
        "artifact_role": "F3B7_SINGLE_USE_EVALUATION_AUDIT",
        "phase": "F3B.7",
        "heldout_materialized": True,
        "heldout_afino_executed": True,
        "heldout_blind_decisions_frozen_before_truth": True,
        "truth_join_performed": True,
        "heldout_metrics_computed": True,
        "heldout_selection_function_computed": True,
        "heldout_period_metrics_computed": True,
        "candidate_search_performed": False,
        "thresholds_modified": False,
        "rule_refitted": False,
        "development_reopened_for_tuning": False,
        "new_afino_calls": 0,
        "generator_calls": 0,
        "heldout_optimizer_stability": "NOT_EXECUTED_BY_DESIGN",
        "heldout_single_use_consumed": True,
        "procedure_freeze_commit": F3B7_PROCEDURE_FREEZE_COMMIT,
        "pretruth_repair_commit": git(repo, "rev-parse", "HEAD"),
        "blind_decisions_sha256": EXPECTED["workflows/phase3b/heldout/execution/evidence/tables/f3b6_heldout_decisions_blinded.csv"],
    }

    eval_audit = {
        "schema_version": "1.0.0",
        "artifact_role": "F3B7_HELDOUT_EVALUATION_AUDIT",
        "phase": "F3B.7",
        "status": "PASS",
        "counts": {
            "heldout_total_series": 4320,
            "primary_classifier_series": 3600,
            "positive_primary": 1800,
            "null_primary": 1800,
            "input_admissibility_challenges": 720,
            "baseline_evaluations": 3600,
            "selection_function_rows": 156,
            "structural_no_exposure": 9,
            "period_recovery_rows": len(per),
        },
        "confusion_matrix": c,
        "firewall": {
            "candidate_search": False,
            "threshold_mutation": False,
            "rule_refit": False,
            "new_afino": False,
            "generator_calls": False,
            "development_retuning": False,
        },
        "validation_target": "PHASE3B_HELDOUT_EVALUATION_VALIDATION_PASS",
    }

    report = report_text(m, e2e, sel, ps, gate)

    eval_fields = [
        "simulation_unit_id", "planned_decision_id", "background_realization_id",
        "truth_state", "qpp_selected", "delta_bic_0_1", "delta_bic_2_1",
        "baseline_threshold_01", "baseline_threshold_21", "baseline_comparison",
        "baseline_selected_recomputed", "baseline_rule_agreement",
        "classification_outcome", "input_state", "n_samples", "red_noise_alpha",
        "qpp_fraction", "true_period_s", "truth_usage", "evaluation_scope",
    ]
    truth_fields = [
        "simulation_unit_id", "background_realization_id", "truth_state",
        "evidence_plane", "gap_quality_regime", "input_state",
        "materialization_status", "classifier_decision_expected",
        "classifier_decision_present", "planned_decision_id", "decision_status",
        "qpp_selected", "truth_join_status",
    ]
    e2e_fields = [
        "scope_id", "evidence_plane", "design_interpretation",
        "observational_prevalence", "metric", "numerator", "denominator",
        "point_estimate", "wilson_95_lower", "wilson_95_upper",
        "denominator_definition", "classification_metric_synonym",
        "input_inadmissible_recoded_as_FN_or_TN", "pipeline_semantics",
    ]
    period_fields = [
        "simulation_unit_id", "planned_decision_id", "background_realization_id",
        "n_samples", "red_noise_alpha", "qpp_fraction", "true_period_s",
        "recovered_period_s", "absolute_period_error_s", "relative_period_error",
        "log_period_ratio", "classification_outcome", "period_label",
        "period_recovery_status", "nonselected_m1_center_used",
    ]

    write_csv(repo / TRUTH_JOIN, tj, truth_fields)
    write_csv(repo / BASELINE_EVAL, ev, eval_fields)
    write_csv(repo / E2E, e2e, e2e_fields)
    write_csv(repo / SELECTION, sel, list(template[0].keys()))
    write_csv(repo / PERIOD, per, period_fields)
    write_json(repo / METRICS, m)
    write_json(repo / PERIOD_SUMMARY, ps)
    write_json(repo / GATE, gate)
    write_json(repo / SINGLE_USE, single)
    write_json(repo / EVALUATION_AUDIT, eval_audit)
    (repo / REPORT).write_text(report, encoding="utf-8", newline="\n")

    checksum_targets = [
        BINDING, AUTH,
        Path("workflows/phase3b/scripts/evaluate_f3b_heldout.py"),
        Path("workflows/phase3b/scripts/validate_f3b7_heldout_evaluation.py"),
        Path("workflows/phase3b/tests/test_f3b7_heldout_evaluation.py"),
        REGRESSION,
        TRUTH_JOIN, BASELINE_EVAL, E2E, SELECTION, PERIOD,
        METRICS, PERIOD_SUMMARY, GATE, SINGLE_USE, EVALUATION_AUDIT, REPORT,
    ]
    lines = []
    for rel in checksum_targets:
        lines.append(f"{sha256_file(repo / rel)}  {rel.as_posix()}")
    (repo / SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    marker_obj["status"] = "TRUTH_JOIN_AND_EVALUATION_COMPLETE"
    marker_obj["heldout_metrics_computed"] = True
    write_json(marker, marker_obj)

    print("F3B7_HELDOUT_SINGLE_USE_EVALUATION_COMPLETE")
    print("heldout_total_series = 4320")
    print("primary_classifier_series = 3600")
    print("positive_primary = 1800")
    print("null_primary = 1800")
    print("input_admissibility_challenges = 720")
    print("TP =", c["TP"])
    print("FN =", c["FN"])
    print("TN =", c["TN"])
    print("FP =", c["FP"])
    print("selection_function_rows = 156")
    print("STRUCTURAL_NO_EXPOSURE = 9")
    print("period_recovery_rows =", len(per))
    print("candidate_search = false")
    print("threshold_mutation = false")
    print("rule_refit = false")
    print("new_afino_calls = 0")
    print("generator_calls = 0")
    print("heldout_single_use_consumed = true")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--mode", required=True, choices=["development-regression", "heldout-evaluate"])
    ap.add_argument("--audit")
    args = ap.parse_args()
    repo = Path(args.repo_root).resolve()

    if args.mode == "development-regression":
        if not args.audit:
            raise RuntimeError("--audit required for development-regression")
        development_regression(repo, Path(args.audit))
    else:
        heldout_evaluate(repo)


if __name__ == "__main__":
    main()
