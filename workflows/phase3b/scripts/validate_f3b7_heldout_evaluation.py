#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

F3B6_COMMIT = "7776676aab1e4d2922902f4046495500864f7ca1"
PROCEDURE_SUBJECT = "ops(phase3b): freeze single-use heldout unblinding procedure"
POS = "SYNTHETIC_QPP_PRESENT"
NEG = "SYNTHETIC_QPP_ABSENT"
Z = 1.959963984540054

EVAL = Path("workflows/phase3b/heldout/evaluation")
AUTH = EVAL / "config/f3b7_single_use_unblinding_authorization.json"
BIND = EVAL / "config/f3b7_evaluation_input_binding.json"
REG = EVAL / "evidence/reports/f3b7_development_evaluator_regression_audit.json"
BASE = EVAL / "evidence/tables/f3b7_heldout_baseline_evaluation.csv"
JOIN = EVAL / "evidence/tables/f3b7_truth_join_audit.csv"
SEL = EVAL / "evidence/tables/f3b7_heldout_selection_function.csv"
PER = EVAL / "evidence/tables/f3b7_heldout_period_recovery.csv"
MET = EVAL / "evidence/reports/f3b7_heldout_baseline_metrics.json"
PS = EVAL / "evidence/reports/f3b7_heldout_period_recovery_summary.json"
GATE = EVAL / "evidence/reports/f3b7_heldout_validation_gate.json"
SINGLE = EVAL / "evidence/reports/f3b7_single_use_evaluation_audit.json"
AUDIT = EVAL / "evidence/reports/f3b7_evaluation_audit.json"
REPORT = EVAL / "evidence/reports/f3b7_heldout_evaluation_report.md"
SUMS = EVAL / "evidence/f3b7_SHA256SUMS.txt"

BLIND = Path("workflows/phase3b/heldout/execution/evidence/tables/f3b6_heldout_decisions_blinded.csv")
TRUTH = Path("workflows/phase3b/heldout/materialization/evidence/tables/f3b5_heldout_truth_ledger.csv")


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout.strip()


def rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def boolv(v):
    return str(v).strip().lower() == "true"


def wilson(k, n):
    p = k / n
    z2 = Z * Z
    den = 1 + z2 / n
    center = (p + z2 / (2*n)) / den
    half = Z * math.sqrt(p*(1-p)/n + z2/(4*n*n)) / den
    return p, center-half, center+half


def pretruth(repo):
    if git(repo, "rev-parse", "HEAD") != F3B6_COMMIT:
        raise RuntimeError("pretruth validator expects frozen F3B.6 HEAD")
    reg = json.loads((repo / REG).read_text(encoding="utf-8"))
    if reg["result"] != "F3B7_DEVELOPMENT_EVALUATOR_REGRESSION_PASS":
        raise RuntimeError("DEVELOPMENT evaluator regression did not pass")
    d = reg["development"]
    expected = {
        "TP": 143, "FN": 1657, "TN": 1799, "FP": 1,
        "selection_function_rows": 156, "STRUCTURAL_NO_EXPOSURE": 9,
        "period_rows": 143,
    }
    for k, v in expected.items():
        if d[k] != v:
            raise RuntimeError(f"regression field mismatch: {k}")

    auth = json.loads((repo / AUTH).read_text(encoding="utf-8"))
    p = auth["permissions"]
    if auth["status"] != "AUTHORIZED_AFTER_PROCEDURE_FREEZE_COMMIT":
        raise RuntimeError("authorization status mismatch")
    for k in ["truth_join_authorized", "heldout_metrics_authorized", "heldout_selection_function_authorized", "heldout_period_metrics_authorized"]:
        if p[k] is not True:
            raise RuntimeError(f"permission should be true: {k}")
    for k in ["new_afino_execution_authorized", "generator_execution_authorized", "candidate_search_authorized", "threshold_mutation_authorized", "rule_refitting_authorized", "development_retuning_authorized", "heldout_optimizer_stability_authorized"]:
        if p[k] is not False:
            raise RuntimeError(f"permission should be false: {k}")

    final_outputs = [BASE, JOIN, SEL, PER, MET, PS, GATE, SINGLE, AUDIT, REPORT, SUMS]
    if any((repo / x).exists() for x in final_outputs):
        raise RuntimeError("HELDOUT evaluation output exists before procedure freeze")

    print("F3B7_PRETRUTH_PROCEDURE_VALIDATION_PASS")
    print("development_regression = PASS")
    print("heldout_truth_content_read = false")
    print("truth_join_performed = false")
    print("heldout_metrics_computed = false")
    print("new_afino_calls = 0")
    print("generator_calls = 0")


def final(repo):
    if git(repo, "rev-parse", "HEAD^") != F3B6_COMMIT:
        raise RuntimeError("final validator procedure commit parent mismatch")
    if git(repo, "log", "-1", "--pretty=%s") != PROCEDURE_SUBJECT:
        raise RuntimeError("final validator procedure commit subject mismatch")

    required = [BASE, JOIN, SEL, PER, MET, PS, GATE, SINGLE, AUDIT, REPORT, SUMS]
    for rel in required:
        if not (repo / rel).is_file():
            raise RuntimeError(f"missing final artifact: {rel}")

    join = rows(repo / JOIN)
    ev = rows(repo / BASE)
    sel = rows(repo / SEL)
    per = rows(repo / PER)
    if len(join) != 4320 or len(ev) != 3600 or len(sel) != 156:
        raise RuntimeError("final row-count contract failed")

    truth_states = {r["simulation_unit_id"]: r["truth_state"] for r in rows(repo / TRUTH)}
    blind = {r["simulation_unit_id"]: r for r in rows(repo / BLIND) if r["decision_class"] == "BASELINE" and int(r["external_optimizer_seed"]) == 0}
    if len(blind) != 3600:
        raise RuntimeError("blind seed0 baseline decisions != 3600")

    c = {"TP": 0, "FN": 0, "TN": 0, "FP": 0}
    for r in ev:
        sid = r["simulation_unit_id"]
        t = truth_states[sid]
        d = blind[sid]
        selected = float(d["delta_bic_0_1"]) > 10.0 and float(d["delta_bic_2_1"]) > 10.0
        outcome = "TP" if t == POS and selected else "FN" if t == POS else "FP" if selected else "TN"
        if outcome != r["classification_outcome"]:
            raise RuntimeError(f"row-level outcome mismatch: {sid}")
        c[outcome] += 1

    if c["TP"] + c["FN"] != 1800 or c["TN"] + c["FP"] != 1800:
        raise RuntimeError("confusion denominator mismatch")

    met = json.loads((repo / MET).read_text(encoding="utf-8"))
    if met["confusion_matrix"]["TP"] != c["TP"] or met["confusion_matrix"]["FN"] != c["FN"] or met["confusion_matrix"]["TN"] != c["TN"] or met["confusion_matrix"]["FP"] != c["FP"]:
        raise RuntimeError("metrics confusion mismatch")

    for key, k, n in [
        ("sensitivity_TPR", c["TP"], c["TP"]+c["FN"]),
        ("specificity_TNR", c["TN"], c["TN"]+c["FP"]),
        ("false_positive_rate_FPR", c["FP"], c["FP"]+c["TN"]),
    ]:
        p, lo, hi = wilson(k, n)
        obj = met["primary_classification_metrics"][key]
        if obj["numerator"] != k or obj["denominator"] != n:
            raise RuntimeError(f"metric denominator mismatch: {key}")
        if not math.isclose(obj["point_estimate"], p, rel_tol=0, abs_tol=5e-12):
            raise RuntimeError(f"metric point mismatch: {key}")
        if not math.isclose(obj["interval"]["lower"], lo, rel_tol=0, abs_tol=5e-12):
            raise RuntimeError(f"Wilson lower mismatch: {key}")
        if not math.isclose(obj["interval"]["upper"], hi, rel_tol=0, abs_tol=5e-12):
            raise RuntimeError(f"Wilson upper mismatch: {key}")

    structural = sum(r["exposure_status"] == "STRUCTURAL_NO_EXPOSURE" for r in sel)
    if structural != 9:
        raise RuntimeError("STRUCTURAL_NO_EXPOSURE != 9")

    selected_positive_finite = 0
    for sid, d in blind.items():
        if truth_states[sid] != POS:
            continue
        selected = float(d["delta_bic_0_1"]) > 10.0 and float(d["delta_bic_2_1"]) > 10.0
        if not selected:
            continue
        try:
            p = float(d["formal_m1_period_s"])
        except (TypeError, ValueError):
            continue
        if math.isfinite(p) and 40.0 <= p <= 300.0:
            selected_positive_finite += 1
    if len(per) != selected_positive_finite:
        raise RuntimeError("period eligibility mismatch")

    gate = json.loads((repo / GATE).read_text(encoding="utf-8"))
    if gate["branch"] != "BASELINE_ONLY" or gate["status"] != "HELDOUT_BASELINE_CHARACTERIZATION_SUCCESS" or gate["correction_claim"] != "NOT_ESTABLISHED":
        raise RuntimeError("HELDOUT gate mismatch")

    single = json.loads((repo / SINGLE).read_text(encoding="utf-8"))
    for k in ["truth_join_performed", "heldout_metrics_computed", "heldout_selection_function_computed", "heldout_period_metrics_computed", "heldout_single_use_consumed"]:
        if single[k] is not True:
            raise RuntimeError(f"single-use audit missing true: {k}")
    for k in ["candidate_search_performed", "thresholds_modified", "rule_refitted", "development_reopened_for_tuning"]:
        if single[k] is not False:
            raise RuntimeError(f"single-use audit forbidden true: {k}")
    if single["new_afino_calls"] != 0 or single["generator_calls"] != 0:
        raise RuntimeError("unexpected new scientific execution")

    wc = len((repo / REPORT).read_text(encoding="utf-8").split())
    if not 1100 <= wc <= 1500:
        raise RuntimeError(f"report word count outside contract: {wc}")

    mismatches = 0
    for line in (repo / SUMS).read_text(encoding="utf-8").splitlines():
        expected, rel = line.split("  ", 1)
        if sha(repo / rel) != expected:
            mismatches += 1
    if mismatches:
        raise RuntimeError(f"SHA registry mismatches: {mismatches}")

    print("PHASE3B_HELDOUT_EVALUATION_VALIDATION_PASS")
    print("heldout_total_series = 4320")
    print("primary_classifier_series = 3600")
    print("positive_primary = 1800")
    print("null_primary = 1800")
    print("baseline_evaluations = 3600")
    print("TP + FN = 1800")
    print("TN + FP = 1800")
    print("selection_function_rows = 156")
    print("STRUCTURAL_NO_EXPOSURE = 9")
    print("period_eligibility_exact = true")
    print("candidate_search = false")
    print("threshold_mutation = false")
    print("rule_refit = false")
    print("new_afino = false")
    print("development_retuning = false")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--mode", required=True, choices=["pretruth", "final"])
    args = ap.parse_args()
    repo = Path(args.repo_root).resolve()
    if args.mode == "pretruth":
        pretruth(repo)
    else:
        final(repo)


if __name__ == "__main__":
    main()
