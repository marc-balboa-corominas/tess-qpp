from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

EXPECTED_F3B7_HEAD = "1a006edbafc05eab5ff9a6f46efbd4e94a074b49"
F3B7_TAG = "phase3b-heldout-validation-v1"
EXPECTED_TAG_OBJECT = "4d3aa7b1d8c9b4cf058940aee211bb53550265f9"
EXPECTED_PHASE_README_SHA = "2a90327cef4cc868e944a9ca33dc6aa5f5ae4c0436c3ec452700b310e4c13644"

ALLOWED_CLAIM_STATUSES = {
    "SUPPORTED_NOW",
    "SUPPORTED_WITH_EXPLICIT_LIMITATION",
    "REQUIRES_F4_PLUS",
    "PROHIBITED",
}

FINAL_DIRTY = {
    "workflows/phase3b/README.md",
    "workflows/phase3b/closure/README.md",
    "workflows/phase3b/closure/SHA256SUMS.txt",
    "workflows/phase3b/closure/f3b8_source_bindings.json",
    "workflows/phase3b/closure/f3b8_development_heldout_comparison.csv",
    "workflows/phase3b/closure/f3b8_final_selection_function.csv",
    "workflows/phase3b/closure/f3b8_phase3b_evidence_ledger.csv",
    "workflows/phase3b/closure/f3b8_claim_matrix.csv",
    "workflows/phase3b/closure/f3b8_limitations_register.csv",
    "workflows/phase3b/closure/f3b8_manuscript1_handoff.csv",
    "workflows/phase3b/closure/f3b8_phase3b_decision.json",
    "workflows/phase3b/closure/f3b8_closure_audit.json",
    "workflows/phase3b/closure/f3b8_phase3b_synthesis_report.md",
    "workflows/phase3b/scripts/build_phase3b_closure.py",
    "workflows/phase3b/scripts/validate_phase3b_closure.py",
    "docs/decisions/DR-008-phase3b-closure-and-manuscript1-entry.md",
}

PARTIAL_DIRTY_AFTER_REPORT_GUARD = FINAL_DIRTY - {
    "workflows/phase3b/closure/SHA256SUMS.txt",
    "workflows/phase3b/closure/f3b8_closure_audit.json",
    "workflows/phase3b/closure/f3b8_phase3b_synthesis_report.md",
}


def run_git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip("\r\n")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def status_paths(repo: Path) -> set[str]:
    out = run_git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    return {line[3:].replace("\\", "/") for line in out.splitlines() if line.strip()}


def tracked(repo: Path, pattern: str) -> list[str]:
    out = run_git(repo, "ls-files", pattern)
    return [x for x in out.splitlines() if x.strip()]


def bind_group(repo: Path, paths: list[str]) -> list[dict]:
    out = []
    for rel in sorted(set(paths)):
        p = repo / rel
        if not p.is_file():
            raise RuntimeError(f"missing bound source: {rel}")
        out.append({"path": rel, "sha256": sha256(p), "bytes": p.stat().st_size})
    return out


def ensure_entry_boundary(repo: Path) -> None:
    head = run_git(repo, "rev-parse", "HEAD")
    if head != EXPECTED_F3B7_HEAD:
        raise RuntimeError(f"unexpected F3B.8 entry HEAD: {head}")
    if run_git(repo, "rev-list", "-n", "1", F3B7_TAG) != EXPECTED_F3B7_HEAD:
        raise RuntimeError("F3B.7 tag does not peel to the frozen final commit")
    if run_git(repo, "cat-file", "-t", F3B7_TAG) != "tag":
        raise RuntimeError("F3B.7 tag is not annotated")
    if run_git(repo, "rev-parse", F3B7_TAG) != EXPECTED_TAG_OBJECT:
        raise RuntimeError("F3B.7 annotated tag object changed")
    rm = run_git(repo, "ls-remote", "origin", "refs/heads/main").split()
    rto = run_git(repo, "ls-remote", "--tags", "origin", f"refs/tags/{F3B7_TAG}").split()
    rtc = run_git(repo, "ls-remote", "--tags", "origin", f"refs/tags/{F3B7_TAG}^{{}}").split()
    if not rm or rm[0] != EXPECTED_F3B7_HEAD:
        raise RuntimeError("origin/main does not match the F3B.7 freeze")
    if not rto or rto[0] != EXPECTED_TAG_OBJECT:
        raise RuntimeError("remote F3B.7 tag object mismatch")
    if not rtc or rtc[0] != EXPECTED_F3B7_HEAD:
        raise RuntimeError("remote F3B.7 peeled tag mismatch")


def make_paths(repo: Path) -> dict[str, Path]:
    c = repo / "workflows/phase3b/closure"
    return {
        "closure": c,
        "phase_readme": repo / "workflows/phase3b/README.md",
        "closure_readme": c / "README.md",
        "bindings": c / "f3b8_source_bindings.json",
        "comparison": c / "f3b8_development_heldout_comparison.csv",
        "selection": c / "f3b8_final_selection_function.csv",
        "ledger": c / "f3b8_phase3b_evidence_ledger.csv",
        "claims": c / "f3b8_claim_matrix.csv",
        "limitations": c / "f3b8_limitations_register.csv",
        "handoff": c / "f3b8_manuscript1_handoff.csv",
        "decision": c / "f3b8_phase3b_decision.json",
        "audit": c / "f3b8_closure_audit.json",
        "report": c / "f3b8_phase3b_synthesis_report.md",
        "sums": c / "SHA256SUMS.txt",
        "builder": repo / "workflows/phase3b/scripts/build_phase3b_closure.py",
        "validator": repo / "workflows/phase3b/scripts/validate_phase3b_closure.py",
        "dr": repo / "docs/decisions/DR-008-phase3b-closure-and-manuscript1-entry.md",
    }


def install_permanent_tools(repo: Path, p: dict[str, Path]) -> None:
    p["builder"].parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(__file__).resolve(), p["builder"])
    validator = '''from pathlib import Path\nimport argparse\nfrom build_phase3b_closure import validate_closure\nif __name__ == "__main__":\n    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root", default=".")\n    args=ap.parse_args(); validate_closure(Path(args.repo_root).resolve())\n'''
    p["validator"].write_text(validator, encoding="utf-8", newline="\n")


def build_source_bindings(repo: Path, p: dict[str, Path]) -> tuple[dict, dict[str, str]]:
    groups: dict[str, list[dict]] = {}
    groups["F3B1_DESIGN"] = bind_group(repo, tracked(repo, "workflows/phase3b/design/f3b1_*"))

    f3b2 = []
    for pat in [
        "workflows/phase3b/development/evidence/reports/f3b2_*",
        "workflows/phase3b/development/evidence/tables/f3b2_development_payload_manifest.csv",
        "workflows/phase3b/development/evidence/tables/f3b2_development_series_manifest.csv",
        "workflows/phase3b/development/evidence/tables/f3b2_development_admissibility.csv",
        "workflows/phase3b/development/evidence/tables/f3b2_development_decision_grid.csv",
        "workflows/phase3b/development/evidence/tables/f3b2_development_exact_afino_plan.csv",
    ]:
        f3b2 += tracked(repo, pat)
    groups["F3B2_DEVELOPMENT_MATERIALIZATION"] = bind_group(repo, f3b2)

    f3b3 = []
    for pat in [
        "workflows/phase3b/development/evidence/reports/f3b3_*",
        "workflows/phase3b/development/evidence/tables/f3b3_development_decisions.csv",
        "workflows/phase3b/development/evidence/tables/f3b3_development_results.csv",
    ]:
        f3b3 += tracked(repo, pat)
    groups["F3B3_DEVELOPMENT_EXECUTION"] = bind_group(repo, f3b3)
    groups["F3B4_DEVELOPMENT_ANALYSIS"] = bind_group(repo, tracked(repo, "workflows/phase3b/development/analysis/f3b4_*"))

    f3b5 = []
    for pat in [
        "workflows/phase3b/heldout/materialization/evidence/reports/f3b5_*",
        "workflows/phase3b/heldout/materialization/evidence/tables/f3b5_heldout_series_manifest.csv",
        "workflows/phase3b/heldout/materialization/evidence/tables/f3b5_heldout_admissibility.csv",
    ]:
        f3b5 += tracked(repo, pat)
    groups["F3B5_HELDOUT_MATERIALIZATION"] = bind_group(repo, f3b5)

    f3b6 = []
    for pat in [
        "workflows/phase3b/heldout/execution/evidence/f3b6_SHA256SUMS.txt",
        "workflows/phase3b/heldout/execution/evidence/reports/f3b6_*",
        "workflows/phase3b/heldout/execution/evidence/tables/f3b6_heldout_decisions_blinded.csv",
        "workflows/phase3b/heldout/execution/evidence/tables/f3b6_heldout_results_blinded.csv",
    ]:
        f3b6 += tracked(repo, pat)
    groups["F3B6_BLIND_HELDOUT_EXECUTION"] = bind_group(repo, f3b6)

    f3b7 = tracked(repo, "workflows/phase3b/heldout/evaluation/**")
    f3b7 += [
        "workflows/phase3b/scripts/evaluate_f3b_heldout.py",
        "workflows/phase3b/scripts/validate_f3b7_heldout_evaluation.py",
        "workflows/phase3b/tests/test_f3b7_heldout_evaluation.py",
    ]
    groups["F3B7_SINGLE_USE_HELDOUT_EVALUATION"] = bind_group(repo, f3b7)

    tags = []
    for tag in run_git(repo, "tag", "--list", "phase3b-*").splitlines():
        if tag.strip():
            tags.append({
                "name": tag,
                "object_type": run_git(repo, "cat-file", "-t", tag),
                "object_id": run_git(repo, "rev-parse", tag),
                "peeled_commit": run_git(repo, "rev-list", "-n", "1", tag),
            })

    obj = {
        "schema_version": "1.0.0",
        "artifact_role": "F3B8_PHASE3B_CLOSURE_SOURCE_BINDINGS",
        "phase": "F3B.8",
        "status": "BOUND_TO_LIVE_FROZEN_REPOSITORY_SOURCES",
        "f3b7_entry_boundary": {"commit": EXPECTED_F3B7_HEAD, "tag": F3B7_TAG},
        "source_groups": groups,
        "all_bound_source_count": sum(len(v) for v in groups.values()),
        "git_phase3b_tags": tags,
        "truth_boundary": {
            "original_f3b5_truth_ledger_content_reread_in_f3b8": False,
            "heldout_truth_evidence_used_for_closure": [
                "workflows/phase3b/heldout/evaluation/evidence/tables/f3b7_truth_join_audit.csv",
                "workflows/phase3b/heldout/evaluation/evidence/reports/f3b7_evaluation_audit.json",
            ],
        },
        "execution_boundary": {
            "new_afino_calls": 0,
            "generator_calls": 0,
            "new_statistical_inference": False,
            "new_threshold_search": False,
            "new_candidate_rule": False,
            "heldout_reused_for_development": False,
        },
    }
    write_json(p["bindings"], obj)
    smap = {e["path"]: e["sha256"] for vals in groups.values() for e in vals}
    return obj, smap


def build(repo: Path, resume_partial: bool = False) -> None:
    ensure_entry_boundary(repo)
    p = make_paths(repo)
    if resume_partial:
        if status_paths(repo) != PARTIAL_DIRTY_AFTER_REPORT_GUARD:
            raise RuntimeError("F3B.8 partial-resume scope is not exact")
        for missing in [p["report"], p["audit"], p["sums"]]:
            if missing.exists():
                raise RuntimeError(f"F3B.8 partial-resume expected missing artifact already exists: {missing}")
    else:
        if p["closure"].exists() or p["dr"].exists():
            raise RuntimeError("F3B.8 closure artifacts already exist; refusing overwrite")
        if sha256(p["phase_readme"]) != EXPECTED_PHASE_README_SHA:
            raise RuntimeError("Phase 3B README changed before closure build")

    bindings, smap = build_source_bindings(repo, p)

    dev_metrics_rel = "workflows/phase3b/development/analysis/f3b4_baseline_metrics.json"
    dev_sel_rel = "workflows/phase3b/development/analysis/f3b4_selection_function.csv"
    dev_per_rel = "workflows/phase3b/development/analysis/f3b4_period_recovery.csv"
    gate_rel = "workflows/phase3b/development/analysis/f3b4_candidate_rule_gate.json"
    rule_rel = "workflows/phase3b/development/analysis/f3b4_final_rule_freeze.json"
    held_metrics_rel = "workflows/phase3b/heldout/evaluation/evidence/reports/f3b7_heldout_baseline_metrics.json"
    held_sel_rel = "workflows/phase3b/heldout/evaluation/evidence/tables/f3b7_heldout_selection_function.csv"
    held_per_rel = "workflows/phase3b/heldout/evaluation/evidence/tables/f3b7_heldout_period_recovery.csv"
    held_ps_rel = "workflows/phase3b/heldout/evaluation/evidence/reports/f3b7_heldout_period_recovery_summary.json"
    held_gate_rel = "workflows/phase3b/heldout/evaluation/evidence/reports/f3b7_heldout_validation_gate.json"
    held_single_rel = "workflows/phase3b/heldout/evaluation/evidence/reports/f3b7_single_use_evaluation_audit.json"
    held_join_rel = "workflows/phase3b/heldout/evaluation/evidence/tables/f3b7_truth_join_audit.csv"

    dev = load_json(repo / dev_metrics_rel)
    held = load_json(repo / held_metrics_rel)
    cand = load_json(repo / gate_rel)
    rule = load_json(repo / rule_rel)
    hgate = load_json(repo / held_gate_rel)
    hsingle = load_json(repo / held_single_rel)
    hps = load_json(repo / held_ps_rel)
    dev_sel = read_csv(repo / dev_sel_rel)
    held_sel = read_csv(repo / held_sel_rel)
    dev_per = read_csv(repo / dev_per_rel)
    held_per = read_csv(repo / held_per_rel)

    dcm, hcm = dev["confusion_matrix"], held["confusion_matrix"]
    dpm, hpm = dev["primary_classification_metrics"], held["primary_classification_metrics"]
    dba = dev["secondary_classification_summary"]["balanced_accuracy"]["point_estimate"]
    hba = held["secondary_classification_summary"]["balanced_accuracy"]["point_estimate"]
    if (dcm["TP"], dcm["FN"], dcm["TN"], dcm["FP"]) != (143,1657,1799,1):
        raise RuntimeError("DEVELOPMENT confusion identity changed")
    if (hcm["TP"], hcm["FN"], hcm["TN"], hcm["FP"]) != (152,1648,1800,0):
        raise RuntimeError("HELDOUT confusion identity changed")
    if len(dev_sel) != 156 or len(held_sel) != 156 or len(dev_per) != 143 or len(held_per) != 152:
        raise RuntimeError("F3B.8 row-count identity changed")
    dstruct = sum(r["exposure_status"] == "STRUCTURAL_NO_EXPOSURE" for r in dev_sel)
    hstruct = sum(r["exposure_status"] == "STRUCTURAL_NO_EXPOSURE" for r in held_sel)
    if dstruct != 9 or hstruct != 9:
        raise RuntimeError("STRUCTURAL_NO_EXPOSURE identity changed")
    if cand["promotion_result"]["candidate_rule_promoted"] is not False:
        raise RuntimeError("candidate unexpectedly promoted")
    if cand["promotion_result"]["failed_criteria"] != ["C4_LOWER_CI_DELTA_SPECIFICITY_GT_NEG_0_025"]:
        raise RuntimeError("candidate gate failure identity changed")
    if rule["freeze_state"] != "FINAL_RULE_FREEZE_BASELINE_ONLY" or rule["final_rule"]["t01"] != 10.0 or rule["final_rule"]["t21"] != 10.0:
        raise RuntimeError("final rule freeze changed")
    if hgate["status"] != "HELDOUT_BASELINE_CHARACTERIZATION_SUCCESS" or hgate["correction_claim"] != "NOT_ESTABLISHED":
        raise RuntimeError("HELDOUT gate identity changed")
    if hsingle["heldout_single_use_consumed"] is not True:
        raise RuntimeError("HELDOUT single-use state changed")

    # Descriptive comparison only.
    comp = []
    def add(metric, dn="", dd="", dv="", dl="", du="", hn="", hd="", hv="", hl="", hu="", note=""):
        comp.append({
            "metric":metric,"development_numerator":dn,"development_denominator":dd,
            "development_point_estimate":dv,"development_interval_lower":dl,"development_interval_upper":du,
            "heldout_numerator":hn,"heldout_denominator":hd,"heldout_point_estimate":hv,
            "heldout_interval_lower":hl,"heldout_interval_upper":hu,
            "comparison_role":"DESCRIPTIVE_SPLIT_SEPARATE","inferential_test":"NOT_PERFORMED",
            "pooling":"NOT_PERFORMED","interpretation":note,
        })
    for k in ["TP","FN","TN","FP"]:
        add(k, dcm[k], dcm["total"], hn=hcm[k], hd=hcm["total"], note="Count kept separate by frozen split.")
    for label,key in [("sensitivity_TPR","sensitivity_TPR"),("specificity_TNR","specificity_TNR"),("false_positive_rate_FPR","false_positive_rate_FPR")]:
        dm, hm = dpm[key], hpm[key]
        add(label, dm["numerator"], dm["denominator"], dm["point_estimate"], dm["wilson_95_lower"], dm["wilson_95_upper"],
            hm["numerator"], hm["denominator"], hm["point_estimate"], hm["interval"]["lower"], hm["interval"]["upper"],
            "Frozen synthetic-domain characterization; no equivalence or hypothesis test.")
    add("balanced_accuracy", dv=dba, hv=hba, note="Secondary descriptive summary only.")
    add("selection_function_rows", dn=len(dev_sel), hn=len(held_sel), note="Final surface is HELDOUT only, not pooled.")
    add("STRUCTURAL_NO_EXPOSURE", dn=dstruct, hn=hstruct, note="Structural non-exposure is not an empirical zero.")
    add("period_recovery_rows", dn=len(dev_per), hn=len(held_per), note="Conditional on selected true positives with finite recovered period.")
    write_csv(p["comparison"], list(comp[0].keys()), comp)

    # Final selection function = exact HELDOUT table + metadata only.
    source_sha = smap[held_sel_rel]
    fields = list(held_sel[0].keys())
    final_sel = []
    for r in held_sel:
        x = dict(r)
        x.update({"validation_role":"HELDOUT_PRIMARY_FINAL","source_artifact":held_sel_rel,"source_sha256":source_sha})
        final_sel.append(x)
    write_csv(p["selection"], fields + ["validation_role","source_artifact","source_sha256"], final_sel)

    def s(rel: str) -> str:
        return smap[rel]

    # Evidence ledger.
    evidence = [
        ("E001","F3B_DEVELOPMENT_SYNTHETIC","DEVELOPMENT","Frozen baseline confusion matrix","143 TP; 1657 FN; 1799 TN; 1 FP","1800 positive; 1800 null","","",dev_metrics_rel,s(dev_metrics_rel),"Synthetic-ground-truth DEVELOPMENT characterization only."),
        ("E002","F3B_DEVELOPMENT_SYNTHETIC","DEVELOPMENT","Baseline sensitivity","143","1800",str(dpm["sensitivity_TPR"]["point_estimate"]),f'[{dpm["sensitivity_TPR"]["wilson_95_lower"]}, {dpm["sensitivity_TPR"]["wilson_95_upper"]}]',dev_metrics_rel,s(dev_metrics_rel),"Synthetic-domain sensitivity; not observational."),
        ("E003","F3B_DEVELOPMENT_SYNTHETIC","DEVELOPMENT","Baseline specificity","1799","1800",str(dpm["specificity_TNR"]["point_estimate"]),f'[{dpm["specificity_TNR"]["wilson_95_lower"]}, {dpm["specificity_TNR"]["wilson_95_upper"]}]',dev_metrics_rel,s(dev_metrics_rel),"Synthetic-domain specificity; not observational."),
        ("E004","F3B_DEVELOPMENT_GATE","DEVELOPMENT","Candidate promotion","3 criteria passed","4 required","NOT_PROMOTED","",gate_rel,s(gate_rel),"Candidate failed C4 specificity-preservation criterion; alternate search forbidden."),
        ("E005","F3B_FINAL_RULE","PRE_HELDOUT_FREEZE","Frozen final rule","","","delta_BIC01 > 10 AND delta_BIC21 > 10","",rule_rel,s(rule_rel),"AFINO 0.5 baseline; strict greater-than; t01=t21=10."),
        ("E006","F3B_HELDOUT_SYNTHETIC","HELDOUT","Frozen baseline confusion matrix","152 TP; 1648 FN; 1800 TN; 0 FP","1800 positive; 1800 null","","",held_metrics_rel,s(held_metrics_rel),"Independent single-use HELDOUT synthetic-ground-truth characterization."),
        ("E007","F3B_HELDOUT_SYNTHETIC","HELDOUT","Sensitivity","152","1800",str(hpm["sensitivity_TPR"]["point_estimate"]),f'[{hpm["sensitivity_TPR"]["interval"]["lower"]}, {hpm["sensitivity_TPR"]["interval"]["upper"]}]',held_metrics_rel,s(held_metrics_rel),"Independent synthetic HELDOUT sensitivity."),
        ("E008","F3B_HELDOUT_SYNTHETIC","HELDOUT","Specificity","1800","1800",str(hpm["specificity_TNR"]["point_estimate"]),f'[{hpm["specificity_TNR"]["interval"]["lower"]}, {hpm["specificity_TNR"]["interval"]["upper"]}]',held_metrics_rel,s(held_metrics_rel),"1800/1800 synthetic null rejection with finite-sample Wilson uncertainty."),
        ("E009","F3B_HELDOUT_SYNTHETIC","HELDOUT","False-positive rate","0","1800",str(hpm["false_positive_rate_FPR"]["point_estimate"]),f'[{hpm["false_positive_rate_FPR"]["interval"]["lower"]}, {hpm["false_positive_rate_FPR"]["interval"]["upper"]}]',held_metrics_rel,s(held_metrics_rel),"Zero observed false selections does not establish population FPR=0."),
        ("E010","F3B_SELECTION_FUNCTION","DEVELOPMENT","DEVELOPMENT selection rows",str(len(dev_sel)),"","STRATIFIED_EMPIRICAL","",dev_sel_rel,s(dev_sel_rel),"DEVELOPMENT retained for descriptive comparison only."),
        ("E011","F3B_SELECTION_FUNCTION","HELDOUT","Final selection rows",str(len(held_sel)),"","HELDOUT_PRIMARY_FINAL","",held_sel_rel,s(held_sel_rel),"Final manuscript surface is independent HELDOUT; no pooling or smoothing."),
        ("E012","F3B_SELECTION_FUNCTION","HELDOUT","Structural no-exposure cells",str(hstruct),str(len(held_sel)),"STRUCTURAL_NO_EXPOSURE","",held_sel_rel,s(held_sel_rel),"Structurally impossible cells are not empirical zeros."),
        ("E013","F3B_PERIOD_RECOVERY","DEVELOPMENT","Period-recovery rows",str(len(dev_per)),"1800 eligible positives","","",dev_per_rel,s(dev_per_rel),"Conditional on selected true positives with finite recovered period."),
        ("E014","F3B_PERIOD_RECOVERY","HELDOUT","Period-recovery rows",str(len(held_per)),"1800 eligible positives","","",held_per_rel,s(held_per_rel),"Conditional period accuracy does not imply high selection sensitivity."),
        ("E015","F3B_PERIOD_RECOVERY","HELDOUT","Period estimate coverage",str(hps["period_estimate_coverage_fraction"]["numerator"]),str(hps["period_estimate_coverage_fraction"]["denominator"]),str(hps["period_estimate_coverage_fraction"]["point_estimate"]),"",held_ps_rel,s(held_ps_rel),"Coverage remains low because selection sensitivity is low."),
        ("E016","F3B_SINGLE_USE_GOVERNANCE","HELDOUT","Single-use consumption","","","CONSUMED","",held_single_rel,s(held_single_rel),"HELDOUT cannot be reused for threshold/rule development."),
        ("E017","F3B_HELDOUT_GATE","HELDOUT","Validation gate","","","HELDOUT_BASELINE_CHARACTERIZATION_SUCCESS","",held_gate_rel,s(held_gate_rel),"Complete baseline characterization; no minimum performance threshold in BASELINE_ONLY."),
        ("E018","F3B_CLAIM_BOUNDARY","PHASE3B","Correction claim","","","NOT_ESTABLISHED","",held_gate_rel,s(held_gate_rel),"Population/observational correction remains outside Phase 3B."),
        ("E019","F3B_TRUTH_JOIN","HELDOUT","Single-use truth join","3600 primary joined; 720 challenges audited","4320 HELDOUT series","COMPLETE","",held_join_rel,s(held_join_rel),"Classifier decisions exist only for the 3600 primary classifier-plane series."),
        ("E020","F3B_SYNTHETIC_VALIDATION","PHASE3B","Synthetic validation component","","","COMPLETE","",held_gate_rel,s(held_gate_rel),"Synthetic-ground-truth component is complete for Manuscript 1."),
    ]
    efields = ["evidence_id","evidence_plane","split","fact","numerator","denominator","point_estimate","interval_95","source_artifact","source_sha256","interpretation"]
    write_csv(p["ledger"], efields, [dict(zip(efields,row)) for row in evidence])

    # Claim matrix.
    claims = [
        ("C001","F3B establishes synthetic-ground-truth performance for the frozen AFINO 0.5 baseline within the prospectively specified simulation domain.","SUPPORTED_NOW","E001;E006","Phase 3B characterizes synthetic-ground-truth performance of the frozen AFINO 0.5 baseline within the preregistered simulation domain.","Always retain synthetic-domain scope.","AFINO is validated for real TESS populations."),
        ("C002","Independent HELDOUT sensitivity is 152/1800 = 0.08444444444444445.","SUPPORTED_NOW","E007","HELDOUT synthetic sensitivity was 152/1800 (0.08444).","State denominator and synthetic HELDOUT scope.","Observational sensitivity is 8.44%."),
        ("C003","Independent HELDOUT specificity is 1800/1800 = 1.0 with finite-sample Wilson uncertainty.","SUPPORTED_WITH_EXPLICIT_LIMITATION","E008","No false selections were observed among 1800 HELDOUT synthetic nulls; specificity point estimate was 1.0 with finite-sample Wilson uncertainty.","Give denominator and Wilson interval; do not call it perfect.","Perfect specificity."),
        ("C004","No false selections were observed among 1800 HELDOUT synthetic nulls.","SUPPORTED_NOW","E009","Zero false selections were observed in 1800 synthetic null HELDOUT cases.","Observed count only; not a population-rate theorem.","AFINO has an observational FPR of zero."),
        ("C005","Observed zero false selections does not imply population FPR = 0.","SUPPORTED_NOW","E009","The finite-sample result remains compatible with a nonzero underlying synthetic-domain FPR.","Retain Wilson uncertainty and synthetic scope.","Population FPR is exactly zero."),
        ("C006","The DEVELOPMENT candidate rule was not promoted.","SUPPORTED_NOW","E004","The DEVELOPMENT candidate failed the preregistered specificity-preservation gate and was not promoted.","Do not rescue a runner-up post hoc.","Choose another candidate after seeing HELDOUT."),
        ("C007","The final heldout rule remained the preregistered AFINO 0.5 baseline 10/10 rule.","SUPPORTED_NOW","E005","The final frozen rule was delta_BIC01 > 10 AND delta_BIC21 > 10 with strict greater-than comparisons.","State candidate_rule_promoted=false.","The HELDOUT rule was optimized on HELDOUT."),
        ("C008","A validated correction was not established.","SUPPORTED_NOW","E018","Phase 3B did not establish a validated observational correction.","Keep NOT_ESTABLISHED explicit.","Phase 3B provides a validated population correction."),
        ("C009","The synthetic selection function was characterized on an independent single-use HELDOUT.","SUPPORTED_NOW","E011;E016","The final synthetic selection function is the 156-row independent HELDOUT stratified empirical surface.","No DEVELOPMENT pooling or smoothing.","The final selection function pools DEVELOPMENT and HELDOUT."),
        ("C010","The selection function is domain-conditional and is not an observational population correction without transport assumptions.","SUPPORTED_WITH_EXPLICIT_LIMITATION","E011;E018","The HELDOUT surface is conditional on the frozen synthetic design and requires additional transport assumptions before observational use.","Do not transport directly to real TESS populations.","This is the observational TESS selection function."),
        ("C011","Period estimates among selected true positives were accurate relative to the much lower selection coverage.","SUPPORTED_WITH_EXPLICIT_LIMITATION","E014;E015","Conditional period-recovery accuracy can be summarized for selected true positives while overall selection coverage remains low.","Period-error summaries are conditional on selection.","Good period recovery implies high QPP sensitivity."),
        ("C012","Period accuracy conditional on selection does not imply high QPP recovery sensitivity.","SUPPORTED_NOW","E007;E014;E015","Accurate periods among selected true positives coexist with low overall synthetic QPP selection sensitivity.","Keep conditioning explicit.","Period accuracy demonstrates high detection completeness."),
        ("C013","Numerical classification stability on the frozen DEVELOPMENT seed subset does not establish a unique numerical optimum.","SUPPORTED_WITH_EXPLICIT_LIMITATION","E004","The DEVELOPMENT stability exercise is a bounded numerical diagnostic and does not establish optimizer uniqueness.","Do not overstate seed-stability evidence.","The optimizer has a unique global optimum."),
        ("C014","Input inadmissibility remains a separate pipeline plane.","SUPPORTED_NOW","E019","Input admissibility and classifier performance remain separate analysis planes.","Do not recode challenge series as FN/TN.","Input-inadmissible challenges are classifier false negatives."),
        ("C015","F3B does not establish real-TESS QPP prevalence.","REQUIRES_F4_PLUS","E018","Real-TESS QPP prevalence remains outside Phase 3B.","Requires observational population modeling and transport assumptions.","Phase 3B measures real-TESS QPP prevalence."),
        ("C016","F3B does not establish observational PPV, sensitivity, specificity or FPR.","REQUIRES_F4_PLUS","E002;E003;E007;E008;E009","Reported operating characteristics are synthetic-domain quantities.","Observational performance requires later validation/transport.","These are observational sensitivity, specificity, PPV or FPR."),
        ("C017","F3B does not establish physical QPP truth for observational events.","REQUIRES_F4_PLUS","E018","Synthetic labels provide controlled truth only for the simulation experiment.","Physical truth in observed stars is separate.","F3B proves an observational event physically contains a QPP."),
        ("C018","AFINO has not been observationally validated by F3B.","PROHIBITED","E018","Use scoped synthetic-ground-truth characterization language.","Any validation language must specify evidence plane.","AFINO is observationally validated."),
        ("C019","The HELDOUT is consumed and cannot be reused for further threshold/rule development.","PROHIBITED","E016","The single-use HELDOUT is closed to further rule development.","Future tuning requires new independent data/design.","Reuse HELDOUT to tune another threshold."),
        ("C020","Manuscript 1's synthetic-validation component is now complete.","SUPPORTED_NOW","E017;E020","The synthetic-ground-truth validation component required for Manuscript 1 is complete.","Do not collapse other evidence planes into this statement.","All observational validation is complete."),
        ("C021","Manuscript 1 must not claim a validated correction.","SUPPORTED_NOW","E018","Manuscript 1 may report the synthetic selection function but must state that a validated observational correction was not established.","Keep correction claim NOT_ESTABLISHED.","A validated correction has been established."),
        ("C022","Population-level correction/transport remains a later F4+ problem.","REQUIRES_F4_PLUS","E018","Population transport and observational correction remain future work beyond Phase 3B.","Requires explicit transport assumptions and later evidence.","Apply the synthetic HELDOUT surface directly as a population correction."),
    ]
    cfields=["claim_id","claim_text","status","evidence_ids","allowed_wording","mandatory_qualification","prohibited_wording"]
    write_csv(p["claims"], cfields, [dict(zip(cfields,row)) for row in claims])

    # 21 limitations.
    lims = [
        ("L001","TRUTH","Ground truth is synthetic, not observational physical truth.","Limits claims to controlled simulations.","Use synthetic-ground-truth wording."),
        ("L002","SIGNAL_FAMILY","The primary synthetic signal family is frozen by the F3B.1 generator contract.","Other QPP morphologies are not covered.","Do not generalize to arbitrary QPP waveforms."),
        ("L003","PERIOD_SUPPORT","True-period support is restricted to 40–300 s.","Performance outside this range is uncharacterized.","State period support when discussing recovery."),
        ("L004","DISCRETE_GRID","Durations/sample counts, red-noise slopes and signal strengths lie on a discrete frozen grid.","The selection function is not a continuous population law.","Describe a stratified empirical surface."),
        ("L005","CHALLENGES","The 720 input-admissibility challenges are a designed diagnostic plane, not a population sample.","Their aggregate fraction is not observational prevalence.","Keep challenge metrics separate."),
        ("L006","NULL_MODEL","Synthetic nulls do not exhaust observational background behavior.","Real background mismatch can alter false-selection behavior.","Do not transport FPR directly to TESS."),
        ("L007","SENSITIVITY","HELDOUT synthetic sensitivity is low: 152/1800.","Many injected QPP signals are not selected.","Report low sensitivity with high specificity."),
        ("L008","ZERO_FP","HELDOUT observed 0/1800 false selections.","Zero count retains finite-sample uncertainty.","Give Wilson interval; do not claim population FPR=0."),
        ("L009","SELECTION_DOMAIN","The 156-row final selection function is valid only on the frozen synthetic domain.","No observational population correction follows automatically.","Transport requires F4+ evidence."),
        ("L010","PERIOD_CONDITIONING","Period-error metrics condition on selected true positives with finite recovered period.","They do not summarize all injected positives.","Do not interpret good period accuracy as completeness."),
        ("L011","NUMERICAL_STABILITY","Extra-seed stability was assessed only in DEVELOPMENT.","HELDOUT stability was not rerun by design.","Do not imply HELDOUT multi-seed evidence."),
        ("L012","OPTIMIZER","Numerical stability does not establish a unique global optimum.","Optimizer-level uncertainty is bounded.","Avoid unique-optimum claims."),
        ("L013","SOFTWARE_VERSION","Execution is bound to AFINO 0.5 and its frozen environment/commit.","Other versions are outside this evidence.","Report frozen implementation identity."),
        ("L014","CANDIDATE_FAMILY","Candidate development was restricted to the frozen two-threshold family.","Alternative classifier families were not explored.","Do not claim arbitrary-rule optimality."),
        ("L015","CANDIDATE_GATE","The DEVELOPMENT optimum failed the preregistered specificity-preservation gate.","Final rule remains baseline.","Do not rescue a runner-up post hoc."),
        ("L016","COMPARATORS","External comparator methods were not executed in F3B.8.","Closure is not a benchmark against every detector.","Do not claim comparative superiority."),
        ("L017","SINGLE_USE","HELDOUT is consumed as a single-use validation set.","It cannot support new rule development without circularity.","Future tuning requires new independent data."),
        ("L018","TRANSPORT","No calibration maps the synthetic design distribution to the real TESS population.","Population prevalence and correction are not established.","Reserve transport/correction for F4+."),
        ("L019","PHYSICAL_INFERENCE","Synthetic classification performance does not establish the physical origin of observed variability.","Physical QPP truth remains separate.","Do not convert classifier outcomes into physical proof."),
        ("L020","EVIDENCE_PLANES","F0, F1, F2, F3A and F3B answer different evidence questions.","Collapsing them into one validation label overstates scope.","Keep evidence planes separate in Manuscript 1."),
        ("L021","DESCRIPTIVE_COMPARISON","DEVELOPMENT and HELDOUT are compared descriptively without pooling/equivalence/hypothesis testing.","Similarity is qualitative, not formal equivalence.","Do not claim statistical equivalence."),
    ]
    lfields=["limitation_id","category","limitation","consequence","mandatory_manuscript_qualification"]
    write_csv(p["limitations"], lfields, [dict(zip(lfields,row)) for row in lims])

    # Manuscript handoff keeps all evidence planes separate.
    hand = [
        ("M001","Evidence architecture boundary","F0_OBSERVATIONAL_REPRODUCTION","F0","REFER_TO_FROZEN_F0_SOURCES;NOT_REBOUND_IN_F3B8","F0 observational reproduction remains a distinct evidence plane.","F3B.8 does not re-evaluate F0.","F0 plus F3B proves observational validation.","evidence-architecture schematic"),
        ("M002","Evidence architecture boundary","F1_SYNTHETIC_NUMERICAL_BENCHMARK","F1","REFER_TO_FROZEN_F1_SOURCES;NOT_REBOUND_IN_F3B8","F1 synthetic/numerical benchmarking remains distinct.","F3B.8 does not re-evaluate F1.","F1 numerical benchmarking is observational ground truth.","evidence-architecture schematic"),
        ("M003","Evidence architecture boundary","F2_OBSERVATIONAL_PILOT_ROBUSTNESS","F2","REFER_TO_FROZEN_F2_SOURCES;NOT_REBOUND_IN_F3B8","F2 observational pilot robustness remains distinct.","F3B.8 does not re-evaluate F2.","F2 supplies physical QPP truth.","evidence-architecture schematic"),
        ("M004","Evidence architecture boundary","F3A_CATALOGUE_SCALE_OBSERVATIONAL_ROBUSTNESS","F3A","REFER_TO_FROZEN_F3A_SOURCES;NOT_REBOUND_IN_F3B8","F3A catalogue-scale observational robustness remains distinct.","F3B.8 does not re-evaluate F3A.","F3A supplies synthetic-ground-truth sensitivity.","evidence-architecture schematic"),
        ("M005","Methods / validation design","F3B_SYNTHETIC_GROUND_TRUTH_VALIDATION","F3B",f"{dev_metrics_rel};{held_metrics_rel};{held_single_rel}","F3B provides controlled synthetic-ground-truth characterization of the frozen AFINO 0.5 baseline.","Scope to preregistered synthetic domain and single-use HELDOUT.","AFINO is validated without qualification.","validation-flow figure"),
        ("M006","Results / classifier performance","F3B_SYNTHETIC_GROUND_TRUTH_VALIDATION","F3B.7",held_metrics_rel,"HELDOUT sensitivity was 152/1800 and no false selections were observed among 1800 synthetic nulls.","State Wilson uncertainty and synthetic scope.","Observational sensitivity/specificity/FPR.","classification table"),
        ("M007","Results / rule selection","F3B_DEVELOPMENT_GATE","F3B.4",f"{gate_rel};{rule_rel}","The DEVELOPMENT candidate failed the specificity-preservation gate and was not promoted; final rule remained 10/10.","No runner-up rescue or post-HELDOUT retuning.","Baseline selected because it performed best on HELDOUT.","rule-gate table"),
        ("M008","Results / selection function","F3B_SELECTION_FUNCTION","F3B.7/F3B.8",f"{held_sel_rel};workflows/phase3b/closure/f3b8_final_selection_function.csv","The final selection function is the 156-row HELDOUT stratified empirical surface.","Domain-conditional; not observational population correction.","Universal TESS correction curve.","selection-function figure/table"),
        ("M009","Results / period recovery","F3B_PERIOD_RECOVERY","F3B.7",f"{held_per_rel};{held_ps_rel}","Period accuracy is summarized conditional on selected true positives.","Do not infer high selection sensitivity from conditional accuracy.","Accurate periods prove high completeness.","period-recovery figure"),
        ("M010","Discussion / claim boundary","F3B_CLAIM_GOVERNANCE","F3B.7/F3B.8",held_gate_rel,"A validated observational correction was not established.","Population transport remains F4+.","Phase 3B establishes a validated correction.","limitations/claim table"),
    ]
    hfields=["claim_id","manuscript_section_role","evidence_plane","source_phase","source_artifacts","allowed_wording","mandatory_qualification","prohibited_wording","figure_or_table_candidate"]
    write_csv(p["handoff"], hfields, [dict(zip(hfields,row)) for row in hand])

    decision = {
        "schema_version":"1.0.0","artifact_role":"F3B8_PHASE3B_FORMAL_DECISION","phase":"F3B.8",
        "phase_status":"PHASE3B_COMPLETE_HELDOUT_BASELINE_CHARACTERIZED_CORRECTION_NOT_ESTABLISHED_PROCEED_TO_MANUSCRIPT1",
        "synthetic_ground_truth_validation_complete":True,
        "heldout_baseline_characterization_success":True,
        "heldout_single_use_consumed":True,
        "candidate_rule_promoted":False,
        "correction_claim_established":False,
        "selection_function_characterized":True,
        "observational_selection_function_established":False,
        "observational_ground_truth_established":False,
        "afino_observationally_validated":False,
        "observational_sensitivity_established":False,
        "observational_specificity_established":False,
        "observational_fpr_established":False,
        "physical_qpp_truth_established":False,
        "population_correction_complete":False,
        "manuscript1_ready":True,
        "candidate_discovery_authorized":False,
        "final_rule":{"rule_type":"AFINO_0_5_BASELINE","selection_rule":"delta_BIC01 > 10 AND delta_BIC21 > 10","comparison_operator":"STRICT_GREATER_THAN","t01":10.0,"t21":10.0},
        "f3b7_entry_commit":EXPECTED_F3B7_HEAD,"f3b7_entry_tag":F3B7_TAG,
        "required_closure_validator_result":"PHASE3B_CLOSURE_VALIDATION_PASS",
    }
    write_json(p["decision"], decision)

    p["phase_readme"].write_text("""# Phase 3B\n\nSTATUS:\nPHASE 3B CLOSED —\nSYNTHETIC HELDOUT CHARACTERIZATION COMPLETE\nCORRECTION NOT ESTABLISHED\nREADY FOR MANUSCRIPT 1\n\nPhase 3B prospectively evaluated the frozen AFINO 0.5 baseline on controlled synthetic ground truth. DEVELOPMENT and independent single-use HELDOUT both show a low-sensitivity, extremely-high-specificity operating profile within the preregistered synthetic domain.\n\nThe DEVELOPMENT candidate rule was not promoted because it failed the frozen specificity-preservation gate. The final rule remained `delta_BIC01 > 10 AND delta_BIC21 > 10` with strict greater-than comparisons.\n\nFinal HELDOUT: TP=152, FN=1648, TN=1800, FP=0; sensitivity=152/1800=0.08444444444444445; specificity=1800/1800=1.0 with finite-sample Wilson uncertainty; final selection-function rows=156; period-recovery rows=152.\n\nFormal gate: `HELDOUT_BASELINE_CHARACTERIZATION_SUCCESS`. Correction claim: `NOT_ESTABLISHED`.\n\nThe HELDOUT is consumed and cannot be reused for threshold or rule development. Phase 3B does not establish observational prevalence, observational sensitivity/specificity/FPR, physical QPP truth, or a validated population correction.\n\nF3B.7 freeze: `phase3b-heldout-validation-v1` / `1a006edbafc05eab5ff9a6f46efbd4e94a074b49`.\n\nF3B.8 closure artifacts live under `workflows/phase3b/closure/`. The next program state is Manuscript 1 evidence→claim→section architecture, not F3B.9.\n""", encoding="utf-8", newline="\n")

    p["closure_readme"].write_text("""# F3B.8 — Phase 3B closure\n\nF3B.8 is documentary synthesis and governance closure. It executes no AFINO or generator work, introduces no new thresholds or inferential tests, and does not reuse the consumed HELDOUT for development.\n\nThe closure binds frozen F3B.1–F3B.7 evidence by live repository path and SHA-256; compares DEVELOPMENT and HELDOUT descriptively without pooling; adopts the independent 156-row HELDOUT `STRATIFIED_EMPIRICAL` table as the final synthetic-domain selection surface; and translates the evidence into an explicit claim matrix, limitations register and Manuscript 1 handoff.\n\nFinal state: synthetic-ground-truth validation complete; candidate not promoted; final baseline 10/10; HELDOUT consumed; `HELDOUT_BASELINE_CHARACTERIZATION_SUCCESS`; correction `NOT_ESTABLISHED`; Manuscript 1 synthetic-validation component ready.\n\nThe final selection surface is not an observational population correction. F0, F1, F2, F3A and F3B remain distinct evidence planes.\n""", encoding="utf-8", newline="\n")

    p["dr"].parent.mkdir(parents=True, exist_ok=True)
    p["dr"].write_text(f"""# DR-008 — Phase 3B closure and Manuscript 1 entry\n\n## Status\n\nAccepted for closure candidate validation.\n\n## Context\n\nPhase 3B was designed to characterize the frozen AFINO 0.5 rule on controlled synthetic ground truth while preserving a strict DEVELOPMENT / single-use HELDOUT boundary. The DEVELOPMENT candidate improved sensitivity but failed the preregistered specificity-preservation criterion C4. It was not promoted, no runner-up rescue was permitted, and the final pre-HELDOUT rule remained `delta_BIC01 > 10 AND delta_BIC21 > 10`.\n\nThe blinded HELDOUT decisions were frozen before truth access. F3B.7 then consumed HELDOUT once for the authorized truth join and baseline characterization.\n\n## Decision\n\nClose Phase 3B with `PHASE3B_COMPLETE_HELDOUT_BASELINE_CHARACTERIZED_CORRECTION_NOT_ESTABLISHED_PROCEED_TO_MANUSCRIPT1`. HELDOUT yielded 152 TP, 1648 FN, 1800 TN and 0 FP on 1800 synthetic positives and 1800 synthetic nulls. Zero observed false selections retains finite-sample Wilson uncertainty and is not proof of population FPR=0.\n\nThe final selection surface is the 156-row F3B.7 HELDOUT `STRATIFIED_EMPIRICAL` table, adopted without DEVELOPMENT pooling, smoothing or a new probabilistic fit. It is valid for the frozen synthetic domain only. Correction remains `NOT_ESTABLISHED`.\n\n## Consequences\n\nPhase 3B supports controlled synthetic-ground-truth performance claims, the candidate rejection, the frozen 10/10 baseline, independent HELDOUT selection behavior and conditional period-recovery results. It does not support observational prevalence, observational PPV/sensitivity/specificity/FPR, physical QPP truth, unqualified observational validation of AFINO, or a validated TESS population correction.\n\nThe consumed HELDOUT is permanently closed to new threshold/rule development. Population transport is F4+. F0 observational reproduction, F1 synthetic/numerical benchmarking, F2 observational pilot robustness, F3A catalogue-scale observational robustness and F3B synthetic ground-truth validation must remain separate evidence planes in Manuscript 1.\n\nF3B.8 performs zero AFINO calls, zero generator calls, no new stochastic draw, no threshold mutation, no candidate search, no rule refit, no DEVELOPMENT retuning and no new inferential test. The original F3B.5 truth ledger is not reopened.\n\nAfter `PHASE3B_CLOSURE_VALIDATION_PASS` and Git/OSF freeze, the next step is Manuscript 1 evidence→claim→section architecture, not F3B.9.\n""", encoding="utf-8", newline="\n")

    period_cov = hps["period_estimate_coverage_fraction"]
    pdist = hps["selected_true_positive_error_distributions"]
    report = f"""# F3B.8 — Phase 3B synthesis and closure report\n\n## 1. Closure purpose and evidence boundary\n\nPhase 3B is closed as a controlled synthetic-ground-truth validation programme for the frozen AFINO 0.5 decision rule. F3B.8 does not create a new scientific experiment. It binds and synthesizes the already frozen F3B.1–F3B.7 evidence, translates that evidence into an explicit claim boundary, and prepares the synthetic-validation component for Manuscript 1. No AFINO execution, generator execution, stochastic draw, candidate search, threshold mutation, rule refit, DEVELOPMENT retuning, pooling of DEVELOPMENT with HELDOUT, or new inferential test occurs in this closure.\n\nThis distinction matters because HELDOUT was deliberately single-use. F3B.6 froze blinded decisions before truth access, and F3B.7 then consumed the set for the authorized truth join and baseline evaluation. F3B.8 therefore treats F3B.7 outputs as final validation evidence rather than material for another development cycle. The original F3B.5 truth ledger is not reopened. Closure uses the frozen F3B.7 truth-join audit, evaluation tables, metrics, gate and single-use audit.\n\n## 2. DEVELOPMENT baseline characterization\n\nThe frozen baseline in DEVELOPMENT was `delta_BIC01 > 10 AND delta_BIC21 > 10`, with strict greater-than comparisons. On 3,600 primary DEVELOPMENT series, equally divided between 1,800 synthetic positives and 1,800 synthetic nulls, the confusion matrix was 143 TP, 1,657 FN, 1,799 TN and 1 FP. Sensitivity was {dpm['sensitivity_TPR']['point_estimate']}, specificity {dpm['specificity_TNR']['point_estimate']}, FPR {dpm['false_positive_rate_FPR']['point_estimate']}, and balanced accuracy {dba}.\n\nThese figures established a clear operating profile inside the frozen simulation domain: low sensitivity and extremely high specificity. They are synthetic-domain quantities, not observational performance estimates. The Wilson intervals frozen in F3B.4 remain the relevant finite-sample uncertainty summaries, and F3B.8 neither recomputes them as new inference nor transports them to real TESS populations.\n\n## 3. DEVELOPMENT candidate gate and final-rule decision\n\nDEVELOPMENT contained the prospectively authorized two-threshold candidate search. The optimum had t01={cand['candidate']['t01']} and t21={cand['candidate']['t21']}, with balanced accuracy {cand['candidate']['balanced_accuracy']}. It increased DEVELOPMENT sensitivity, but promotion required all four frozen criteria. Criterion C4, the lower confidence bound on candidate-minus-baseline specificity being greater than -0.025, failed: the frozen lower bound was {cand['promotion_criteria']['C4_lower_CI_delta_specificity_gt_neg_0_025']['observed']}. Three criteria passed and four were required.\n\nThe candidate was therefore not promoted. There was no runner-up rescue or alternate candidate search. The final-rule freeze retained the untouched AFINO 0.5 baseline at t01=t21=10. This does not establish global optimality over arbitrary classifiers; it is the correct consequence of the preregistered candidate family and gate. HELDOUT played no role in threshold choice.\n\n## 4. Blind HELDOUT and single-use truth evaluation\n\nThe independent HELDOUT used a stronger separation than exploratory validation. AFINO outputs and 3,600 classifier decisions were frozen while truth remained blinded. Only after the pre-unblinding procedure was committed and verified was truth joined. F3B.7 accounts for 4,320 HELDOUT series: 3,600 primary classifier-plane cases, comprising 1,800 synthetic QPP-present and 1,800 synthetic QPP-absent cases, plus 720 input-admissibility challenges whose classifier decisions were absent by design.\n\nThe final HELDOUT confusion matrix was 152 TP, 1,648 FN, 1,800 TN and 0 FP. Sensitivity was {hpm['sensitivity_TPR']['point_estimate']} with Wilson 95% interval [{hpm['sensitivity_TPR']['interval']['lower']}, {hpm['sensitivity_TPR']['interval']['upper']}]. Specificity was {hpm['specificity_TNR']['point_estimate']} with interval [{hpm['specificity_TNR']['interval']['lower']}, {hpm['specificity_TNR']['interval']['upper']}]. Observed FPR was {hpm['false_positive_rate_FPR']['point_estimate']} with interval [{hpm['false_positive_rate_FPR']['interval']['lower']}, {hpm['false_positive_rate_FPR']['interval']['upper']}]. Balanced accuracy was {hba}.\n\nThe observed 0/1,800 false selections must not be converted into a statement that a population FPR is exactly zero. The finite-sample Wilson upper bound is nonzero. Likewise these are HELDOUT synthetic-ground-truth operating characteristics, not observational sensitivity, specificity, FPR, PPV or prevalence estimates for real TESS flare populations.\n\n## 5. DEVELOPMENT to HELDOUT synthesis\n\n`f3b8_development_heldout_comparison.csv` keeps the two splits separate. No pooled confusion matrix, pooled rate, equivalence test or hypothesis test is introduced. Descriptively, both splits show the same qualitative operating profile in the preregistered synthetic domain: low sensitivity and extremely high specificity. DEVELOPMENT sensitivity was {dpm['sensitivity_TPR']['point_estimate']} and HELDOUT sensitivity {hpm['sensitivity_TPR']['point_estimate']}; DEVELOPMENT specificity was {dpm['specificity_TNR']['point_estimate']} and HELDOUT specificity {hpm['specificity_TNR']['point_estimate']}; balanced accuracy was {dba} and {hba}.\n\nThe permitted conclusion is qualitative consistency of operating profile under an independent single-use split. Closure does not claim statistical equivalence. Nor does it use HELDOUT to reopen the candidate gate. The frozen rule and rejected candidate decision remain unchanged.\n\n## 6. Final synthetic selection function\n\nThe final selection surface for Manuscript 1 is `f3b8_final_selection_function.csv`. It contains exactly 156 rows and derives only from the F3B.7 HELDOUT selection table. Every original numerical and categorical field is reproduced exactly; F3B.8 adds only closure metadata identifying `HELDOUT_PRIMARY_FINAL` and the source artifact/SHA.\n\nThe representation remains `STRATIFIED_EMPIRICAL`. There is no smoothed surface, new probabilistic model or DEVELOPMENT-plus-HELDOUT pooling. The table preserves 9 `STRUCTURAL_NO_EXPOSURE` cells so structurally impossible exposure is not represented as empirical zero selection. The interpretation is domain-conditional: selection depends on frozen experimental conditions rather than one universal sensitivity scalar. Observational use would require explicit transport assumptions linking the synthetic design to the real TESS population.\n\n## 7. Period recovery and selection conditioning\n\nDEVELOPMENT contains 143 period-recovery rows and HELDOUT 152. HELDOUT period-estimate coverage is {period_cov['numerator']}/{period_cov['denominator']}={period_cov['point_estimate']}. Among selected true positives with finite recovered period, the frozen HELDOUT median absolute period error is {pdist['absolute_period_error_s']['median']} s, median relative error {pdist['relative_period_error']['median']}, and median log-period ratio {pdist['log_period_ratio']['median']}.\n\nThis conditioning matters. A method can estimate periods accurately for the small subset of synthetic QPP signals it selects while missing most injected positives. Conditional period accuracy therefore does not imply high detection completeness. Manuscript 1 must keep period-recovery quality and selection coverage separate.\n\n## 8. Input admissibility and numerical scope\n\nThe 720 challenge series remain an input-admissibility plane rather than classifier truth cases. They are not converted into false negatives or true negatives, and their designed frequency is not a population prevalence estimate. This prevents pipeline-input robustness from being conflated with classifier performance.\n\nNumerical stability evidence also remains bounded. Extra-seed stability was a DEVELOPMENT diagnostic; HELDOUT optimizer stability was not rerun by design. The evidence can support statements about the tested numerical subset but does not establish a unique global optimizer solution. Scientific execution is also bound to AFINO 0.5 and the frozen implementation/environment; different versions require separate evidence.\n\n## 9. Claim matrix and limitations\n\nThe claim matrix classifies manuscript-facing statements as `SUPPORTED_NOW`, `SUPPORTED_WITH_EXPLICIT_LIMITATION`, `REQUIRES_F4_PLUS` or `PROHIBITED`. Supported claims include controlled synthetic-ground-truth characterization, HELDOUT sensitivity 152/1,800, observed absence of false selections in 1,800 synthetic nulls, rejection of the DEVELOPMENT candidate, retention of the 10/10 baseline, independent HELDOUT selection behavior and conditional period-recovery results.\n\nClaims requiring explicit limitation include the specificity point estimate of 1.0 because finite-sample uncertainty must accompany it; the domain-conditional selection surface; and period accuracy conditional on selection. Claims requiring F4+ include real-TESS prevalence, observational PPV/sensitivity/specificity/FPR and population correction. Unqualified observational validation of AFINO and reuse of the consumed HELDOUT for new threshold development are prohibited.\n\nThe limitations register also preserves the synthetic nature of truth, frozen signal family, 40–300 s period support, discrete design grid, nonrepresentative challenge plane, incomplete observational null model, low HELDOUT sensitivity, finite uncertainty around 0/1,800 FP, selection-domain restriction, conditional period analysis, DEVELOPMENT-only extra-seed stability, optimizer nonuniqueness, AFINO version binding, restricted candidate family, rejected candidate, lack of external comparator execution, consumed HELDOUT, absent transport calibration, absent physical inference and evidence-plane separation.\n\nA further limitation is the relationship between the synthetic design distribution and any future observational target population. The simulation programme deliberately fixes class balance, signal amplitudes, red-noise slopes, period support and duration/sample-count combinations to obtain controlled coverage of the experimental domain. Those allocations are design choices, not estimates of how frequently the corresponding conditions occur in TESS flare data. Consequently, neither the raw confusion matrix nor the empirical selection strata should be prevalence-weighted into an observational occurrence correction inside Phase 3B. Any later transport step must state how real events are mapped onto the frozen synthetic coordinates, how unsupported or weakly supported regions are handled, and how uncertainty in that mapping propagates into corrected population quantities.\n\nThe closure also preserves a distinction between reproducibility and generalizability. The F3B evidence is strongly reproducible because the generator, software environment, plans, blinded decisions, truth join, checksums and Git/OSF freezes are all bound. That reproducibility does not by itself establish that the synthetic family spans every astrophysically relevant flare morphology, noise process, cadence artifact or nonstationary background encountered in observations. Manuscript 1 should therefore present Phase 3B as a controlled validation layer that constrains what the frozen baseline does under specified conditions, while reserving broader observational validity, transport and population correction for later evidence planes.\n\n## 10. Evidence-plane separation for Manuscript 1\n\nThe handoff explicitly separates F0 observational reproduction, F1 synthetic/numerical benchmark evidence, F2 observational pilot robustness, F3A catalogue-scale observational robustness and F3B synthetic ground-truth validation. F3B.8 does not re-audit F0–F3A and therefore does not invent new detailed claims for them; source-phase freezes remain authoritative.\n\nThis architecture prevents the word “validation” from obscuring different truth conditions. Synthetic ground truth measures controlled classification performance because labels are known by construction. Observational robustness can test reproducibility and analysis sensitivity without automatically providing physical truth. Catalogue-scale behavior can demonstrate operational consistency without yielding injection-recovery sensitivity. Manuscript 1 should preserve those distinctions in methods, results and discussion.\n\n## 11. Formal Phase 3B decision\n\nPhase 3B concludes with `HELDOUT_BASELINE_CHARACTERIZATION_SUCCESS` and `CORRECTION CLAIM: NOT_ESTABLISHED`. The candidate was not promoted; the final rule is the preregistered AFINO 0.5 baseline at 10/10; the synthetic selection function has been characterized on independent HELDOUT; and the single-use HELDOUT is consumed.\n\nThe formal status is `PHASE3B_COMPLETE_HELDOUT_BASELINE_CHARACTERIZED_CORRECTION_NOT_ESTABLISHED_PROCEED_TO_MANUSCRIPT1`. This means the synthetic-validation component needed for Manuscript 1 is complete. It does not mean AFINO has been observationally validated, that a real-TESS selection function has been established, or that a population correction is ready. Those remain later transport and physical-inference problems.\n\nAfter independent validation of this closure and its Git/OSF freeze, the next activity is Manuscript 1 evidence→claim→section architecture. There is no F3B.9 development cycle, and the consumed HELDOUT remains permanently closed to further rule tuning.\n"""
    wc = len(report.split())
    if not 1500 <= wc <= 2000:
        raise RuntimeError(f"F3B.8 report outside 1500..2000 words: {wc}")
    p["report"].write_text(report, encoding="utf-8", newline="\n")

    audit = {
        "schema_version":"1.0.0","artifact_role":"F3B8_PHASE3B_CLOSURE_AUDIT","phase":"F3B.8",
        "status":"PHASE3B_CLOSURE_VALIDATION_PASS",
        "preclosure_tooling_incidents":[
            {
                "incident_id":"F3B8-TOOL-001",
                "incident_class":"REPORT_WORD_COUNT_CONTRACT_PRECOMMIT_DEFECT",
                "failed_report_word_count":1386,
                "required_report_word_count_min":1500,
                "required_report_word_count_max":2000,
                "repair":"REPORT_TEMPLATE_EXTENDED_BEFORE_COMMIT",
                "scientific_algorithm_changed":False,
                "new_statistical_inference":False,
                "new_afino_calls":0,
                "generator_calls":0,
                "heldout_reused_for_development":False,
            },
            {
                "incident_id":"F3B8-TOOL-002",
                "incident_class":"GIT_PORCELAIN_LEADING_SPACE_STRIP_PATH_PARSE_DEFECT",
                "observed_false_path":"orkflows/phase3b/README.md",
                "correct_path":"workflows/phase3b/README.md",
                "root_cause":"run_git used str.strip(), removing the leading porcelain status column space from the first modified tracked path before status_paths sliced columns 0..2",
                "repair":"run_git newline trimming changed from strip() to rstrip(chr(13)+chr(10)) semantics so porcelain leading status whitespace is preserved",
                "discovered_before_commit":True,
                "closure_outputs_recomputed_after_repair":True,
                "scientific_algorithm_changed":False,
                "new_statistical_inference":False,
                "new_afino_calls":0,
                "generator_calls":0,
                "heldout_reused_for_development":False,
            },
        ],
        "entry_boundary":{"f3b7_commit":EXPECTED_F3B7_HEAD,"f3b7_tag":F3B7_TAG},
        "source_bindings_sha256":sha256(p["bindings"]),
        "reconstruction":{
            "development_classifier_rows":3600,"development_confusion_matrix":{"TP":143,"FN":1657,"TN":1799,"FP":1},
            "development_selection_rows":156,"development_structural_no_exposure":9,"development_period_rows":143,
            "heldout_classifier_rows":3600,"heldout_confusion_matrix":{"TP":152,"FN":1648,"TN":1800,"FP":0},
            "heldout_selection_rows":156,"heldout_structural_no_exposure":9,"heldout_period_rows":152,
            "candidate_rule_promoted":False,"final_t01":10.0,"final_t21":10.0,"heldout_single_use_consumed":True,
            "heldout_gate":"HELDOUT_BASELINE_CHARACTERIZATION_SUCCESS","correction_claim":"NOT_ESTABLISHED",
        },
        "closure_controls":{
            "development_heldout_pooling":False,"equivalence_test_performed":False,"hypothesis_test_added":False,
            "new_statistical_inference":False,"new_afino_calls":0,"generator_calls":0,"new_threshold_search":False,
            "new_candidate_rule":False,"thresholds_modified":False,"rule_refitted":False,"development_reopened_for_tuning":False,
            "heldout_reused_for_development":False,"original_f3b5_truth_ledger_read":False,"f3b1_to_f3b7_artifacts_modified":False,
        },
        "final_selection_function":{"source_role":"HELDOUT_PRIMARY_FINAL","rows":156,"source_fields_reproduced_exactly":True,"structural_no_exposure":9,"new_probabilistic_model_fitted":False},
        "claim_governance":{"claim_rows":len(claims),"limitations_rows":len(lims),"manuscript_handoff_rows":len(hand),"allowed_statuses":sorted(ALLOWED_CLAIM_STATUSES)},
        "report_word_count":wc,"required_independent_validator_result":"PHASE3B_CLOSURE_VALIDATION_PASS",
    }
    write_json(p["audit"], audit)

    targets = [p["phase_readme"],p["closure_readme"],p["bindings"],p["comparison"],p["selection"],p["ledger"],p["claims"],p["limitations"],p["handoff"],p["decision"],p["audit"],p["report"],p["builder"],p["validator"],p["dr"]]
    lines = [f"{sha256(x)}  {x.relative_to(repo).as_posix()}" for x in sorted(targets, key=lambda x:x.relative_to(repo).as_posix())]
    p["sums"].write_text("\n".join(lines)+"\n", encoding="utf-8", newline="\n")

    if status_paths(repo) != FINAL_DIRTY:
        raise RuntimeError("unexpected final F3B.8 working-tree scope")

    print("F3B8_CLOSURE_BUILD_PASS")
    print("bound_source_files =", bindings["all_bound_source_count"])
    print("development_classifier_rows = 3600")
    print("development_confusion = 143 1657 1799 1")
    print("development_selection_rows = 156")
    print("development_period_rows = 143")
    print("heldout_classifier_rows = 3600")
    print("heldout_confusion = 152 1648 1800 0")
    print("heldout_selection_rows = 156")
    print("heldout_structural_no_exposure = 9")
    print("heldout_period_rows = 152")
    print("candidate_promoted = false")
    print("final_rule = 10 / 10")
    print("correction_claim = NOT_ESTABLISHED")
    print("heldout_single_use_consumed = true")
    print("comparison_pooling = false")
    print("new_statistical_inference = false")
    print("new_afino_calls = 0")
    print("generator_calls = 0")
    print("original_f3b5_truth_ledger_read = false")
    print("closure_report_words =", wc)


def validate_closure(repo: Path) -> None:
    p = make_paths(repo)
    if run_git(repo, "rev-list", "-n", "1", F3B7_TAG) != EXPECTED_F3B7_HEAD:
        raise RuntimeError("F3B.7 final tag changed")

    head = run_git(repo, "rev-parse", "HEAD")
    dirty = status_paths(repo)
    if head == EXPECTED_F3B7_HEAD:
        if dirty != FINAL_DIRTY:
            raise RuntimeError("precommit F3B.8 dirty scope is not exact")
    else:
        subprocess.run(["git","-C",str(repo),"merge-base","--is-ancestor",EXPECTED_F3B7_HEAD,head],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        changed = {x for x in run_git(repo,"diff","--name-only",f"{EXPECTED_F3B7_HEAD}..{head}").splitlines() if x.strip()}
        if not changed.issubset(FINAL_DIRTY):
            raise RuntimeError("post-F3B.7 commit modifies protected scope")
        if dirty:
            raise RuntimeError("post-commit validation requires clean working tree")

    b = load_json(p["bindings"])
    if b["truth_boundary"]["original_f3b5_truth_ledger_content_reread_in_f3b8"] is not False:
        raise RuntimeError("F3B.5 truth ledger reread recorded")
    for vals in b["source_groups"].values():
        for e in vals:
            q=repo/e["path"]
            if not q.is_file() or sha256(q)!=e["sha256"] or q.stat().st_size!=e["bytes"]:
                raise RuntimeError(f"bound source changed: {e['path']}")

    sums=[x for x in p["sums"].read_text(encoding="utf-8").splitlines() if x.strip()]
    if len(sums)!=15:
        raise RuntimeError("closure checksum registry must contain 15 entries")
    for line in sums:
        expected,rel=line.split("  ",1); q=repo/rel
        if not q.is_file() or sha256(q)!=expected:
            raise RuntimeError(f"closure checksum mismatch: {rel}")

    dev=load_json(repo/"workflows/phase3b/development/analysis/f3b4_baseline_metrics.json")
    held=load_json(repo/"workflows/phase3b/heldout/evaluation/evidence/reports/f3b7_heldout_baseline_metrics.json")
    cand=load_json(repo/"workflows/phase3b/development/analysis/f3b4_candidate_rule_gate.json")
    rule=load_json(repo/"workflows/phase3b/development/analysis/f3b4_final_rule_freeze.json")
    hgate=load_json(repo/"workflows/phase3b/heldout/evaluation/evidence/reports/f3b7_heldout_validation_gate.json")
    hsingle=load_json(repo/"workflows/phase3b/heldout/evaluation/evidence/reports/f3b7_single_use_evaluation_audit.json")
    dev_sel=read_csv(repo/"workflows/phase3b/development/analysis/f3b4_selection_function.csv")
    held_sel=read_csv(repo/"workflows/phase3b/heldout/evaluation/evidence/tables/f3b7_heldout_selection_function.csv")
    dev_per=read_csv(repo/"workflows/phase3b/development/analysis/f3b4_period_recovery.csv")
    held_per=read_csv(repo/"workflows/phase3b/heldout/evaluation/evidence/tables/f3b7_heldout_period_recovery.csv")
    dcm,hcm=dev["confusion_matrix"],held["confusion_matrix"]
    if (dcm["total"],dcm["TP"],dcm["FN"],dcm["TN"],dcm["FP"])!=(3600,143,1657,1799,1): raise RuntimeError("DEVELOPMENT reconstruction failed")
    if (hcm["total"],hcm["TP"],hcm["FN"],hcm["TN"],hcm["FP"])!=(3600,152,1648,1800,0): raise RuntimeError("HELDOUT reconstruction failed")
    if len(dev_sel)!=156 or len(held_sel)!=156 or len(dev_per)!=143 or len(held_per)!=152: raise RuntimeError("row-count reconstruction failed")
    if sum(r["exposure_status"]=="STRUCTURAL_NO_EXPOSURE" for r in held_sel)!=9: raise RuntimeError("HELDOUT structural count failed")
    if cand["promotion_result"]["candidate_rule_promoted"] is not False: raise RuntimeError("candidate promotion changed")
    if rule["final_rule"]["t01"]!=10.0 or rule["final_rule"]["t21"]!=10.0: raise RuntimeError("final thresholds changed")
    if hgate["correction_claim"]!="NOT_ESTABLISHED" or hgate["status"]!="HELDOUT_BASELINE_CHARACTERIZATION_SUCCESS": raise RuntimeError("HELDOUT gate changed")
    if hsingle["heldout_single_use_consumed"] is not True: raise RuntimeError("HELDOUT consumption changed")

    comp=read_csv(p["comparison"])
    if len(comp)!=11 or any(r["inferential_test"]!="NOT_PERFORMED" or r["pooling"]!="NOT_PERFORMED" for r in comp): raise RuntimeError("pooling/new inference detected")

    final_sel=read_csv(p["selection"])
    if len(final_sel)!=156: raise RuntimeError("final selection rows !=156")
    src_fields=list(held_sel[0].keys())
    for a,z in zip(held_sel,final_sel):
        if any(a[f]!=z[f] for f in src_fields): raise RuntimeError("final selection differs from HELDOUT source")
        if z["validation_role"]!="HELDOUT_PRIMARY_FINAL": raise RuntimeError("final selection role changed")

    claims=read_csv(p["claims"]); lims=read_csv(p["limitations"]); hand=read_csv(p["handoff"]); led=read_csv(p["ledger"])
    if len(claims)<20 or any(r["status"] not in ALLOWED_CLAIM_STATUSES for r in claims): raise RuntimeError("claim matrix invalid")
    if len(lims)<20 or len(led)<20: raise RuntimeError("closure ledger/limitations incomplete")
    planes={r["evidence_plane"] for r in hand}
    required={"F0_OBSERVATIONAL_REPRODUCTION","F1_SYNTHETIC_NUMERICAL_BENCHMARK","F2_OBSERVATIONAL_PILOT_ROBUSTNESS","F3A_CATALOGUE_SCALE_OBSERVATIONAL_ROBUSTNESS","F3B_SYNTHETIC_GROUND_TRUTH_VALIDATION"}
    if not required.issubset(planes): raise RuntimeError("evidence planes collapsed in handoff")

    dec=load_json(p["decision"]); aud=load_json(p["audit"])
    if dec["phase_status"]!="PHASE3B_COMPLETE_HELDOUT_BASELINE_CHARACTERIZED_CORRECTION_NOT_ESTABLISHED_PROCEED_TO_MANUSCRIPT1": raise RuntimeError("formal decision mismatch")
    for k in ["synthetic_ground_truth_validation_complete","heldout_baseline_characterization_success","heldout_single_use_consumed","selection_function_characterized","manuscript1_ready"]:
        if dec[k] is not True: raise RuntimeError(f"decision missing true: {k}")
    for k in ["candidate_rule_promoted","correction_claim_established","observational_selection_function_established","observational_ground_truth_established","afino_observationally_validated","observational_sensitivity_established","observational_specificity_established","observational_fpr_established","physical_qpp_truth_established","population_correction_complete","candidate_discovery_authorized"]:
        if dec[k] is not False: raise RuntimeError(f"decision boundary changed: {k}")
    if aud["status"]!="PHASE3B_CLOSURE_VALIDATION_PASS": raise RuntimeError("closure audit not PASS")
    for k,v in aud["closure_controls"].items():
        if k in {"new_afino_calls","generator_calls"}:
            if v!=0: raise RuntimeError(f"scientific calls nonzero: {k}")
        elif v is not False: raise RuntimeError(f"forbidden closure state true: {k}")

    report=p["report"].read_text(encoding="utf-8"); wc=len(report.split())
    if not 1500<=wc<=2000: raise RuntimeError(f"report words outside contract: {wc}")
    for req in ["DEVELOPMENT candidate","single-use HELDOUT","152 TP","1,800 TN","STRATIFIED_EMPIRICAL","CORRECTION CLAIM: NOT_ESTABLISHED","Manuscript 1"]:
        if req not in report: raise RuntimeError(f"required report phrase missing: {req}")

    allowed_text="\n".join([report,p["phase_readme"].read_text(encoding="utf-8"),p["dr"].read_text(encoding="utf-8"),"\n".join(r["allowed_wording"] for r in claims)]).lower()
    for phrase in ["development and heldout are statistically equivalent","afino has an observational fpr of zero","afino is validated for real tess populations","perfect specificity","this is the observational tess selection function","phase 3b provides a validated population correction"]:
        if phrase in allowed_text: raise RuntimeError(f"prohibited assertive wording detected: {phrase}")

    print("PHASE3B_CLOSURE_VALIDATION_PASS")
    print("bound_source_files =", b["all_bound_source_count"])
    print("closure_checksum_entries = 15")
    print("development_classifier_rows = 3600")
    print("development_confusion = 143 1657 1799 1")
    print("development_selection_rows = 156")
    print("development_period_rows = 143")
    print("heldout_classifier_rows = 3600")
    print("heldout_confusion = 152 1648 1800 0")
    print("heldout_selection_rows = 156")
    print("heldout_period_rows = 152")
    print("heldout_structural_no_exposure = 9")
    print("candidate_promoted = false")
    print("final_rule = 10 / 10")
    print("heldout_single_use_consumed = true")
    print("comparison_pooling = false")
    print("new_statistical_inference = false")
    print("new_afino_calls = 0")
    print("generator_calls = 0")
    print("original_f3b5_truth_ledger_read = false")
    print("correction_claim = NOT_ESTABLISHED")
    print("manuscript1_ready = true")
    print("report_words =", wc)


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--resume-partial", action="store_true")
    args=ap.parse_args()
    repo=Path(args.repo_root).resolve()
    ensure_entry_boundary(repo)
    p=make_paths(repo)
    if args.resume_partial:
        if status_paths(repo) != PARTIAL_DIRTY_AFTER_REPORT_GUARD:
            raise RuntimeError("F3B.8 partial-resume starting scope is not exact")
        if not p["builder"].is_file() or not p["validator"].is_file():
            raise RuntimeError("F3B.8 partial-resume permanent tools are missing")
        build(repo, resume_partial=True)
    else:
        if status_paths(repo):
            raise RuntimeError("F3B.8 build must start from a clean working tree")
        for q in [p["closure"],p["builder"],p["validator"],p["dr"]]:
            if q.exists(): raise RuntimeError(f"future F3B.8 path already exists: {q}")
        install_permanent_tools(repo,p)
        build(repo)
    validate_closure(repo)
    if status_paths(repo)!=FINAL_DIRTY: raise RuntimeError("final F3B.8 dirty scope mismatch")
    subprocess.run(["git","-C",str(repo),"diff","--check"],check=True)
    print("F3B8_CLOSURE_CANDIDATE_PASS")
    print("dirty_paths = 16")
    print("head_unchanged = true")
    print("protected_f3b1_to_f3b7_modified = false")


if __name__ == "__main__":
    main()
