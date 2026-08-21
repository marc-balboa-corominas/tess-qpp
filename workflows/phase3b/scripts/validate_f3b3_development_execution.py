#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import shutil
import sqlite3
import statistics
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

AUTHORIZATION_COMMIT = "ed48da39bcd31e2c829e0aecd5dfa25d9bea44fa"
FINAL_CHECKPOINT_SHA256 = "41247f0c05cae443d4e58ecf13ee8217e747c45e5fec2541d47d73cf3b704d32"
CANARY_CHECKPOINT_SHA256 = "4c073a8f699f12c9ed7f7f3953d1161cdeacfb2c4e8c71be4f6b1ffa9c0876a3"
BOOTSTRAP_AUDIT_SHA256 = "fb2aee87e78a5cb935c641ef78b9763da3784c37302224c2f934691cbeaba36d"
RUNNER_SHA256 = "4d5b68cdda60abd7f3a4380abf63d1b0b5e9f4e5889caf22ff85f95b31d813bc"
FULL_PLAN_SHA256 = "180446352dc055132989cfb562e28c3df4730f2de8f38be767c6a79cc83cf600"
F3B2_COMMIT = "7550679a8b0ea1f028987a38cfbe7ac7671fb8ce"
F3B2_TAG = "phase3b-development-materialization-v1"
CANARY_FREEZE_COMMIT = "763a40b4ec4a2ace90fe6c0c500c2c94440534f3"
AFINO_COMMIT = "6aceac9518fc8056052807e666da9d0c8bebb010"
AFINO_VERSION = "0.5"

RUNNER_REL = Path("workflows/phase3b/scripts/run_f3b_development_checkpointed.py")
SELF_REL = Path("workflows/phase3b/scripts/validate_f3b3_development_execution.py")
PLAN_REL = Path("workflows/phase3b/development/evidence/tables/f3b3_blinded_execution_plan.csv")
AUTH_REL = Path("workflows/phase3b/development/config/f3b3_full_development_execution_authorization.json")
DEV_CHECKPOINT_REL = Path("runtime/phase3b/f3b3/development_checkpoint.sqlite")
CANARY_CHECKPOINT_REL = Path("runtime/phase3b/f3b3/canary_checkpoint.sqlite")
BOOTSTRAP_RUNTIME_REL = Path("runtime/phase3b/f3b3/f3b3_canary_bootstrap_audit.csv")

RESULTS_REL = Path("workflows/phase3b/development/evidence/tables/f3b3_development_results.csv")
DECISIONS_REL = Path("workflows/phase3b/development/evidence/tables/f3b3_development_decisions.csv")
TEMPORAL_REL = Path("workflows/phase3b/development/evidence/tables/f3b3_development_temporal_contract.csv")
BOOTSTRAP_EVIDENCE_REL = Path("workflows/phase3b/development/evidence/tables/f3b3_canary_bootstrap_audit.csv")
EXEC_AUDIT_REL = Path("workflows/phase3b/development/evidence/reports/f3b3_development_execution_audit.json")
REPORT_REL = Path("workflows/phase3b/development/evidence/reports/f3b3_development_execution_report.md")
SUMS_REL = Path("workflows/phase3b/development/evidence/f3b3_SHA256SUMS.txt")
HELDOUT_AUDIT_REL = Path("workflows/phase3b/development/evidence/reports/f3b3_heldout_nonaccess_audit.json")
CANARY_AUDIT_REL = Path("workflows/phase3b/development/evidence/reports/f3b3_runner_canary_audit.json")
ENV_REL = Path("workflows/phase3b/development/evidence/reports/f3b3_execution_environment.json")
CANARY_RESULTS_REL = Path("workflows/phase3b/development/evidence/tables/f3b3_canary_results.csv")
CANARY_DECISIONS_REL = Path("workflows/phase3b/development/evidence/tables/f3b3_canary_decisions.csv")
CANARY_TEMPORAL_REL = Path("workflows/phase3b/development/evidence/tables/f3b3_canary_temporal_contract.csv")
CANARY_REPLAY_REL = Path("workflows/phase3b/development/evidence/tables/f3b3_canary_exact_replay_audit.csv")

DECISION_FIELDS = [
    "planned_decision_id", "decision_class", "simulation_unit_id",
    "external_optimizer_seed", "payload_logical_sha256", "decision_status",
    "valid_models", "bic_m0", "bic_m1", "bic_m2", "delta_bic_0_1",
    "delta_bic_2_1", "qpp_selected", "formal_m1_period_s", "period_label",
    "result_core_m0_sha256", "result_core_m1_sha256", "result_core_m2_sha256",
]
TEMPORAL_FIELDS = [
    "planned_decision_id", "decision_class", "simulation_unit_id",
    "external_optimizer_seed", "n_samples", "mean_dt_external_s",
    "median_dt_external_s", "afino_dt_m0_s", "afino_dt_m1_s",
    "afino_dt_m2_s", "mean_dt_match_m0", "mean_dt_match_m1",
    "mean_dt_match_m2", "mean_dt_contract_match",
    "positive_fftfreq_bin_count_external", "rfftfreq_positive_bin_count_external",
    "afino_positive_bin_count_m0", "afino_positive_bin_count_m1",
    "afino_positive_bin_count_m2", "positive_fftfreq_match_m0",
    "positive_fftfreq_match_m1", "positive_fftfreq_match_m2",
    "positive_fftfreq_contract_match", "legacy_rfftfreq_match_m0",
    "legacy_rfftfreq_match_m1", "legacy_rfftfreq_match_m2",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_text(repo: Path, *args: str) -> str:
    cp = subprocess.run(["git", "-C", str(repo), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if cp.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {cp.stderr.strip()}")
    return cp.stdout.strip()


def import_runner(path: Path):
    if sha256_file(path) != RUNNER_SHA256:
        raise RuntimeError("Frozen runner SHA mismatch")
    spec = importlib.util.spec_from_file_location("f3b3_frozen_runner_for_finalization", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to import frozen runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="raise", lineterminator="\n")
        w.writeheader(); w.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fetch_results(path: Path) -> list[dict[str, Any]]:
    con = sqlite3.connect(path); con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute("SELECT * FROM results ORDER BY job_order")]
    finally:
        con.close()


def fetch_invocations(path: Path) -> list[dict[str, Any]]:
    con = sqlite3.connect(path); con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute("""
            SELECT invocation_id, plan_kind, resume_requested, max_new_jobs,
                   existing_before, new_jobs, total_after, pending_after
            FROM invocations ORDER BY invocation_id
        """)]
    finally:
        con.close()


def expected_invocations() -> list[dict[str, Any]]:
    return [
        {"invocation_id":1,"plan_kind":"full","resume_requested":1,"max_new_jobs":3000,"existing_before":648,"new_jobs":3000,"total_after":3648,"pending_after":9096},
        {"invocation_id":2,"plan_kind":"full","resume_requested":1,"max_new_jobs":3000,"existing_before":3648,"new_jobs":3000,"total_after":6648,"pending_after":6096},
        {"invocation_id":3,"plan_kind":"full","resume_requested":1,"max_new_jobs":3000,"existing_before":6648,"new_jobs":3000,"total_after":9648,"pending_after":3096},
        {"invocation_id":4,"plan_kind":"full","resume_requested":1,"max_new_jobs":3000,"existing_before":9648,"new_jobs":3000,"total_after":12648,"pending_after":96},
        {"invocation_id":5,"plan_kind":"full","resume_requested":1,"max_new_jobs":96,"existing_before":12648,"new_jobs":96,"total_after":12744,"pending_after":0},
        {"invocation_id":6,"plan_kind":"full","resume_requested":1,"max_new_jobs":0,"existing_before":12744,"new_jobs":0,"total_after":12744,"pending_after":0},
    ]


def build_decisions(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str,int], dict[str,dict[str,Any]]] = defaultdict(dict)
    for r in results:
        groups[(str(r["simulation_unit_id"]), int(r["external_optimizer_seed"]))][str(r["model_id"])] = r
    out = []
    for key in sorted(groups):
        m = groups[key]
        if set(m) != {"M0","M1","M2"} or any(m[x]["status"] != "OK" for x in m):
            raise RuntimeError(f"Incomplete/non-OK decision: {key}")
        b0,b1,b2 = (float(m[x]["bic"]) for x in ("M0","M1","M2"))
        d01,d21 = b0-b1,b2-b1
        selected = bool(d01 > 10.0 and d21 > 10.0)
        period = m["M1"]["formal_m1_period_s"]
        e = m["M0"]
        out.append({
            "planned_decision_id": e["planned_decision_id"], "decision_class": e["decision_class"],
            "simulation_unit_id": key[0], "external_optimizer_seed": key[1],
            "payload_logical_sha256": e["payload_logical_sha256"], "decision_status": "VALID",
            "valid_models": 3, "bic_m0": b0, "bic_m1": b1, "bic_m2": b2,
            "delta_bic_0_1": d01, "delta_bic_2_1": d21, "qpp_selected": selected,
            "formal_m1_period_s": "" if period is None else float(period),
            "period_label": "unavailable_incomplete_numerical" if period is None else ("recovered_period_selected" if selected else "formal_m1_center_not_selected"),
            "result_core_m0_sha256": m["M0"]["result_core_sha256"],
            "result_core_m1_sha256": m["M1"]["result_core_sha256"],
            "result_core_m2_sha256": m["M2"]["result_core_sha256"],
        })
    return out


def build_temporal(runner, payloads, jobs_by_key, results):
    groups: dict[tuple[str,int], dict[str,dict[str,Any]]] = defaultdict(dict)
    for r in results:
        groups[(str(r["simulation_unit_id"]), int(r["external_optimizer_seed"]))][str(r["model_id"])] = r
    out=[]; mean_pass=0; fft_pass=0
    for (sid,seed), m in sorted(groups.items()):
        t,_,_ = runner.extract_payload(jobs_by_key[(sid,seed,"M0")], payloads)
        mean_dt=float(np.mean(np.diff(t))); median_dt=float(np.median(np.diff(t)))
        pos=int(np.sum(np.fft.fftfreq(len(t), d=mean_dt) > 0.0)); rpos=int(np.sum(np.fft.rfftfreq(len(t), d=mean_dt) > 0.0))
        dt={x:bool(np.isclose(float(m[x]["afino_effective_dt_s"]),mean_dt,atol=5e-12,rtol=0.0)) for x in ("M0","M1","M2")}
        ff={x:int(m[x]["positive_frequency_bin_count"])==pos for x in ("M0","M1","M2")}
        lg={x:int(m[x]["positive_frequency_bin_count"])==rpos for x in ("M0","M1","M2")}
        da=all(dt.values()); fa=all(ff.values()); mean_pass+=int(da); fft_pass+=int(fa); e=m["M0"]
        out.append({
            "planned_decision_id":e["planned_decision_id"],"decision_class":e["decision_class"],"simulation_unit_id":sid,"external_optimizer_seed":seed,
            "n_samples":len(t),"mean_dt_external_s":mean_dt,"median_dt_external_s":median_dt,
            "afino_dt_m0_s":m["M0"]["afino_effective_dt_s"],"afino_dt_m1_s":m["M1"]["afino_effective_dt_s"],"afino_dt_m2_s":m["M2"]["afino_effective_dt_s"],
            "mean_dt_match_m0":dt["M0"],"mean_dt_match_m1":dt["M1"],"mean_dt_match_m2":dt["M2"],"mean_dt_contract_match":da,
            "positive_fftfreq_bin_count_external":pos,"rfftfreq_positive_bin_count_external":rpos,
            "afino_positive_bin_count_m0":m["M0"]["positive_frequency_bin_count"],"afino_positive_bin_count_m1":m["M1"]["positive_frequency_bin_count"],"afino_positive_bin_count_m2":m["M2"]["positive_frequency_bin_count"],
            "positive_fftfreq_match_m0":ff["M0"],"positive_fftfreq_match_m1":ff["M1"],"positive_fftfreq_match_m2":ff["M2"],"positive_fftfreq_contract_match":fa,
            "legacy_rfftfreq_match_m0":lg["M0"],"legacy_rfftfreq_match_m1":lg["M1"],"legacy_rfftfreq_match_m2":lg["M2"],
        })
    return out,mean_pass,fft_pass


def assemble(repo: Path, afino_repo: Path, self_source: Path) -> None:
    if git_text(repo,"rev-parse","HEAD") != AUTHORIZATION_COMMIT: raise RuntimeError("Unexpected HEAD")
    if git_text(repo,"status","--porcelain"): raise RuntimeError("Working tree must be clean before assemble")
    if (repo/"data/interim/phase3b/heldout").exists(): raise RuntimeError("HELDOUT path exists")
    checks={repo/RUNNER_REL:RUNNER_SHA256,repo/PLAN_REL:FULL_PLAN_SHA256,repo/DEV_CHECKPOINT_REL:FINAL_CHECKPOINT_SHA256,repo/CANARY_CHECKPOINT_REL:CANARY_CHECKPOINT_SHA256,repo/BOOTSTRAP_RUNTIME_REL:BOOTSTRAP_AUDIT_SHA256}
    for p,e in checks.items():
        if not p.is_file() or sha256_file(p)!=e: raise RuntimeError(f"Frozen input SHA mismatch: {p}")
    for rel in (RESULTS_REL,DECISIONS_REL,TEMPORAL_REL,BOOTSTRAP_EVIDENCE_REL,SELF_REL):
        if (repo/rel).exists(): raise RuntimeError(f"Refusing overwrite: {rel}")
    runner=import_runner(repo/RUNNER_REL)
    binding=runner.verify_project_freeze(repo); runner.verify_environment(afino_repo,binding); runner.validate_full_authorization(repo/AUTH_REL)
    payloads=runner.load_payload_dataset(repo)
    jobs,kind,manifest_sha=runner.load_plan(repo,repo/PLAN_REL,authorization_path=repo/AUTH_REL)
    if kind!="full" or len(jobs)!=12744 or manifest_sha!=FULL_PLAN_SHA256: raise RuntimeError("Plan identity mismatch")
    results=runner.fetch_results(repo/DEV_CHECKPOINT_REL)
    if len(results)!=12744 or any(r["status"]!="OK" for r in results): raise RuntimeError("Checkpoint not 12744/12744 OK")
    if fetch_invocations(repo/DEV_CHECKPOINT_REL)!=expected_invocations(): raise RuntimeError("Six-invocation ledger mismatch")
    if Counter(r["model_id"] for r in results)!=Counter({"M0":4248,"M1":4248,"M2":4248}): raise RuntimeError("Model count mismatch")
    decisions=build_decisions(results)
    if Counter(d["decision_class"] for d in decisions)!=Counter({"BASELINE":3600,"NUMERICAL_STABILITY_EXTRA":648}): raise RuntimeError("Decision-class mismatch")
    jobs_by_key={(j["simulation_unit_id"],int(j["external_optimizer_seed"]),j["model_id"]):j for j in jobs}
    temporal,mp,fp=build_temporal(runner,payloads,jobs_by_key,results)
    if len(decisions)!=4248 or len(temporal)!=4248 or mp!=4248 or fp!=4248: raise RuntimeError("Decision/temporal gate failed")
    write_csv(repo/RESULTS_REL,list(runner.RESULT_COLUMNS),results); write_csv(repo/DECISIONS_REL,DECISION_FIELDS,decisions); write_csv(repo/TEMPORAL_REL,TEMPORAL_FIELDS,temporal)
    (repo/BOOTSTRAP_EVIDENCE_REL).parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(repo/BOOTSTRAP_RUNTIME_REL,repo/BOOTSTRAP_EVIDENCE_REL)
    if sha256_file(repo/BOOTSTRAP_EVIDENCE_REL)!=BOOTSTRAP_AUDIT_SHA256: raise RuntimeError("Bootstrap copy mismatch")
    (repo/SELF_REL).parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(self_source,repo/SELF_REL)
    dirty={x[3:].replace('\\','/').strip() for x in git_text(repo,"status","--porcelain","--untracked-files=all").splitlines() if x.strip()}
    expected={RESULTS_REL.as_posix(),DECISIONS_REL.as_posix(),TEMPORAL_REL.as_posix(),BOOTSTRAP_EVIDENCE_REL.as_posix(),SELF_REL.as_posix()}
    if dirty!=expected: raise RuntimeError(f"Unexpected assemble scope: {sorted(dirty)}")
    print("F3B3_FULL_EVIDENCE_CANDIDATE_READY"); print("results = 12744/12744 OK"); print("decisions = 4248/4248"); print("temporal = 4248/4248"); print("M0/M1/M2 = 4248/4248/4248"); print("BASELINE = 3600"); print("NUMERICAL_STABILITY_EXTRA = 648"); print("mean_dt_temporal_contract = 4248/4248 PASS"); print("positive_fftfreq_temporal_contract = 4248/4248 PASS"); print("bootstrap_audit_copy = byte-exact"); print("new_files = 5")
    for rel in (RESULTS_REL,DECISIONS_REL,TEMPORAL_REL,BOOTSTRAP_EVIDENCE_REL,SELF_REL): print(f"{rel.as_posix()} sha256={sha256_file(repo/rel)}")
    print("NEXT = run --validate; do not commit yet")


def same_float(a: Any,b: Any)->bool:
    if a in (None,"") and b in (None,""): return True
    try: x,y=float(a),float(b)
    except Exception: return False
    return math.isfinite(x) and math.isfinite(y) and bool(np.isclose(x,y,atol=5e-12,rtol=0.0))


def operational_summary(results):
    out={}
    for model in ("M0","M1","M2"):
        rows=[r for r in results if r["model_id"]==model]; runt=[float(r["runtime_seconds"]) for r in rows]
        out[model]={"calls":len(rows),"warning_calls":sum(int(r["warning_count"])>0 for r in rows),"warning_count":sum(int(r["warning_count"]) for r in rows),"bound_calls":sum(bool(int(r["parameter_at_bound"])) for r in rows),"runtime_total_seconds":float(sum(runt)),"runtime_median_seconds":float(statistics.median(runt)),"convergence_status_counts":dict(sorted(Counter(str(r["convergence_status"]) for r in rows).items()))}
    return out


def report_text(audit):
    o=audit["operational_summary_by_model"]
    text=f"""# F3B.3 DEVELOPMENT AFINO execution report

## Provenance and scope

F3B.3 executed the frozen DEVELOPMENT-only AFINO plan derived from the approved F3B.2 materialization at commit `{F3B2_COMMIT}` and tag `{F3B2_TAG}`. No synthetic series were regenerated during this phase. The execution consumed only the retained DEVELOPMENT payloads frozen in F3B.2, while HELDOUT remained outside the authorized scope. The separation between the generator environment and the AFINO execution environment was preserved throughout.

## AFINO environment and blinded plan

The AFINO stack remained bound to version {AFINO_VERSION} at commit `{AFINO_COMMIT}`, using Python 3.13.13, NumPy 2.5.1 and SciPy 1.18.0. The frozen runner SHA-256 was `{RUNNER_SHA256}`. The blinded plan contained exactly 12,744 jobs representing 4,248 decisions evaluated with M0, M1 and M2. Decision classes were exactly 3,600 `BASELINE` and 648 `NUMERICAL_STABILITY_EXTRA`. Ground-truth labels and scientific strata were excluded from inference inputs.

## Prospective canary

Before full authorization, the runner was frozen and validated on 216 canary decisions and 648 model jobs. The deliberately non-multiple-of-three resume sequence was 211 + 223 + 214 + 0, demonstrating safe resume through partial decisions. All 648 jobs were OK and all 216 decisions were VALID. The canary temporal contract passed 216/216, and six prospectively selected decisions were replayed across eighteen model jobs with absolute tolerance 5e-12 and relative tolerance zero. The replay produced 18/18 matches and zero mismatches. Those 648 canary jobs were reused in the full checkpoint rather than rerun.

## Full checkpoint and execution sequence

The full DEVELOPMENT checkpoint was created separately, initialized with full-plan metadata, and bootstrapped with the 648 validated canary results. Job identity, payload identity and `result_core_sha256` preservation were checked during bootstrap. The remaining 12,096 jobs were executed in the frozen sequence +3000, +3000, +3000, +3000 and +96. A final +0 invocation demonstrated idempotence. The completed checkpoint contains exactly 12,744/12,744 OK results and 4,248/4,248 complete decisions, with zero partial decisions and zero duplicate job identifiers or scientific keys.

## Output integrity

The exported results table contains 12,744 rows, the decision table 4,248 rows, and the temporal diagnostic 4,248 rows. M0, M1 and M2 each contribute exactly 4,248 calls. Independent validation found zero plan-to-checkpoint mismatches, zero checkpoint-to-CSV mismatches, zero frozen-payload mismatches, zero result-core recalculation mismatches and zero decision recalculation mismatches. The 648 imported canary results remained present with zero result-core mismatches. Decision assembly used only blinded AFINO outputs and execution identity. No confusion matrix or truth-conditioned performance table was created.

## Temporal and numerical diagnostics

For every DEVELOPMENT decision, the effective temporal contract used `mean(diff(time_seconds))` and positive frequencies from `np.fft.fftfreq`. All 4,248 decisions matched the AFINO effective cadence, and all 4,248 matched the positive-frequency-bin contract. Median cadence and positive `rfftfreq` counts were retained only as legacy diagnostics. Operational summaries were restricted to model level. M0 had {o['M0']['calls']} calls, {o['M0']['warning_calls']} warning calls, {o['M0']['warning_count']} total warnings, {o['M0']['bound_calls']} bound calls and median runtime {o['M0']['runtime_median_seconds']:.6f} s. M1 had {o['M1']['calls']} calls, {o['M1']['warning_calls']} warning calls, {o['M1']['warning_count']} total warnings, {o['M1']['bound_calls']} bound calls and median runtime {o['M1']['runtime_median_seconds']:.6f} s. M2 had {o['M2']['calls']} calls, {o['M2']['warning_calls']} warning calls, {o['M2']['warning_count']} total warnings, {o['M2']['bound_calls']} bound calls and median runtime {o['M2']['runtime_median_seconds']:.6f} s. These diagnostics were not stratified by truth state, QPP fraction, red-noise alpha or sample count.

## Auditability and reproducibility controls

The completed execution preserves a direct audit chain from every blinded plan row to one checkpoint result and one exported result row. Each scientific key consists of `simulation_unit_id`, external optimizer seed and model identity, and that key is unique across all 12,744 calls. Frozen payload hashes remain attached to both plan and result identities. The independent validator also recalculates every stored result-core hash rather than trusting the database field alone, and reconstructs all 4,248 decisions from the three model rows before comparing them with the exported decision table. An initial pre-commit validator candidate was blocked by a comparison bug that treated plan-only AFINO provenance fields as if they were duplicated in each SQLite result row; it produced no scientific bytes or final reports, and the corrected validator checks those fields through the frozen plan and checkpoint metadata instead. The bootstrap audit is copied byte-for-byte from runtime evidence so that canary reuse remains inspectable in the final evidence set. Checksum evidence includes the runner, tests, blinded plan, canary artifacts, bootstrap audit, full outputs, reports and both runtime checkpoints. These controls establish provenance and mechanical reproducibility only; they do not reinterpret the AFINO outputs or introduce post-hoc filtering. No failed case was removed, no optimizer seed was changed, no payload was substituted, and no adaptive retry policy was introduced after observing outcomes.

## HELDOUT non-access and scientific boundary

HELDOUT remains ungenerated and unaccessed. Its registry contains 4,320 planned rows, while noise draws, period draws, phase draws, flux arrays, payloads and AFINO HELDOUT jobs remain zero. No HELDOUT dataset directory exists. The generator was not imported for inference, synthetic arrays were not regenerated, and truth was not used as an inference feature. F3B.3 therefore closes only the blinded AFINO execution layer on DEVELOPMENT.

## Validation state

The independent validation result is `PHASE3B_DEVELOPMENT_EXECUTION_VALIDATION_PASS`. This status establishes consistency among the frozen plan, checkpoint, exported tables, temporal contract, canary reuse and non-access constraints. It is not a statement of sensitivity, specificity, false-positive rate, balanced accuracy or any selection-function estimate. Scientific ground-truth metrics remain deliberately uncomputed, no candidate rule has been fitted, and no selection function has been estimated. Those analyses belong to F3B.4, where DEVELOPMENT outputs may be rejoined to known truth while HELDOUT remains prohibited.
"""
    wc=len(text.split())
    if not 800<=wc<=1100: raise RuntimeError(f"Report word count {wc} outside 800-1100")
    return text


def validate(repo: Path) -> None:
    if git_text(repo,"rev-parse","HEAD")!=AUTHORIZATION_COMMIT: raise RuntimeError("Unexpected HEAD")
    expected_pre={RESULTS_REL.as_posix(),DECISIONS_REL.as_posix(),TEMPORAL_REL.as_posix(),BOOTSTRAP_EVIDENCE_REL.as_posix(),SELF_REL.as_posix()}
    dirty={x[3:].replace('\\','/').strip() for x in git_text(repo,"status","--porcelain","--untracked-files=all").splitlines() if x.strip()}
    if dirty!=expected_pre: raise RuntimeError(f"Unexpected pre-validation scope: {sorted(dirty)}")
    for rel in (EXEC_AUDIT_REL,REPORT_REL,SUMS_REL):
        if (repo/rel).exists(): raise RuntimeError(f"Refusing overwrite: {rel}")
    checks={repo/RUNNER_REL:RUNNER_SHA256,repo/PLAN_REL:FULL_PLAN_SHA256,repo/DEV_CHECKPOINT_REL:FINAL_CHECKPOINT_SHA256,repo/CANARY_CHECKPOINT_REL:CANARY_CHECKPOINT_SHA256,repo/BOOTSTRAP_RUNTIME_REL:BOOTSTRAP_AUDIT_SHA256,repo/BOOTSTRAP_EVIDENCE_REL:BOOTSTRAP_AUDIT_SHA256}
    for p,e in checks.items():
        if not p.is_file() or sha256_file(p)!=e: raise RuntimeError(f"Frozen/evidence SHA mismatch: {p}")
    if (repo/"data/interim/phase3b/heldout").exists(): raise RuntimeError("HELDOUT path exists")
    runner=import_runner(repo/RUNNER_REL); payloads=runner.load_payload_dataset(repo)
    plan=read_csv(repo/PLAN_REL)
    jobs,plan_kind,manifest_sha=runner.load_plan(repo,repo/PLAN_REL,authorization_path=repo/AUTH_REL)
    results_csv=read_csv(repo/RESULTS_REL); decisions_csv=read_csv(repo/DECISIONS_REL); temporal_csv=read_csv(repo/TEMPORAL_REL); cp=fetch_results(repo/DEV_CHECKPOINT_REL); canary=fetch_results(repo/CANARY_CHECKPOINT_REL)
    if plan_kind!="full" or manifest_sha!=FULL_PLAN_SHA256 or len(jobs)!=12744: raise RuntimeError("Frozen full-plan load mismatch")
    if (len(plan),len(cp),len(results_csv),len(decisions_csv),len(temporal_csv))!=(12744,12744,12744,4248,4248): raise RuntimeError("Final output counts mismatch")
    forbidden={"truth_state","true_period_s","qpp_fraction","ground_truth_label"}
    for name,rows in (("plan",plan),("results",results_csv),("decisions",decisions_csv),("temporal",temporal_csv)):
        if rows and forbidden.intersection(rows[0].keys()): raise RuntimeError(f"Forbidden truth column in {name}")

    # The blinded CSV deliberately carries plan-level execution metadata
    # (AFINO version/commit/cutoff/execution_status). Those fields are not
    # duplicated in every SQLite result row: AFINO provenance is bound in the
    # checkpoint metadata and the frozen plan hash. Validate them in their
    # native locations rather than treating an absent result-column value as
    # a scientific identity mismatch.
    plan_contract_mm=0
    for p in plan:
        if (
            p.get("afino_version")!=AFINO_VERSION
            or p.get("afino_commit")!=AFINO_COMMIT
            or not same_float(p.get("low_frequency_cutoff_hz"),0.025)
            or p.get("execution_status")!="NOT_EXECUTED"
        ):
            plan_contract_mm+=1
    if plan_contract_mm!=0: raise RuntimeError(f"Frozen blinded-plan execution-contract mismatches: {plan_contract_mm}")

    metadata=runner.checkpoint_metadata(repo/DEV_CHECKPOINT_REL)
    metadata_expected={
        "blinded_plan_sha256":FULL_PLAN_SHA256,
        "manifest_sha256":FULL_PLAN_SHA256,
        "afino_version":AFINO_VERSION,
        "afino_commit":AFINO_COMMIT,
        "split":"DEVELOPMENT",
        "plan_kind":"full",
    }
    metadata_mm={k:{"observed":metadata.get(k),"expected":v} for k,v in metadata_expected.items() if metadata.get(k)!=v}
    if metadata_mm: raise RuntimeError("Checkpoint metadata mismatch: "+json.dumps(metadata_mm,sort_keys=True))

    plan_by={r["job_id"]:r for r in jobs}; cp_by={r["job_id"]:r for r in cp}; csv_by={r["job_id"]:r for r in results_csv}
    plan_mm=0
    idf=["job_order","planned_decision_id","decision_class","simulation_unit_id","background_realization_id","external_optimizer_seed","model_id","model_name","payload_logical_sha256"]
    numeric_fields={"job_order","external_optimizer_seed"}
    for jid,p in plan_by.items():
        c=cp_by.get(jid)
        if c is None: plan_mm+=1; continue
        for f in idf:
            if f in numeric_fields:
                try: ok=int(p.get(f))==int(c.get(f))
                except Exception: ok=False
            else:
                ok=str(p.get(f,""))==("" if c.get(f) is None else str(c.get(f)))
            if not ok: plan_mm+=1; break
    csv_mm=0
    for jid,c in cp_by.items():
        r=csv_by.get(jid)
        if r is None: csv_mm+=1; continue
        for f,v in c.items():
            if f not in r or str(r[f])!=("" if v is None else str(v)): csv_mm+=1; break
    core_mm=sum(runner.result_core_sha256(r)!=r["result_core_sha256"] for r in cp)
    jobs_by={(r["simulation_unit_id"],int(r["external_optimizer_seed"]),r["model_id"]):r for r in plan}
    payload_mm=0
    for sid,seed in sorted({(r["simulation_unit_id"],int(r["external_optimizer_seed"])) for r in cp}):
        try: runner.extract_payload(jobs_by[(sid,seed,"M0")],payloads)
        except Exception: payload_mm+=1
    expected_dec=build_decisions(cp); observed_dec={(r["simulation_unit_id"],int(r["external_optimizer_seed"])):r for r in decisions_csv}; dec_mm=0
    for d in expected_dec:
        o=observed_dec.get((d["simulation_unit_id"],int(d["external_optimizer_seed"])))
        if o is None: dec_mm+=1; continue
        for f,v in d.items():
            if f in {"bic_m0","bic_m1","bic_m2","delta_bic_0_1","delta_bic_2_1","formal_m1_period_s"}: ok=same_float(v,o.get(f,""))
            else: ok=str(v)==str(o.get(f,""))
            if not ok: dec_mm+=1; break
    model_counts=Counter(r["model_id"] for r in cp); dc=Counter(d["decision_class"] for d in expected_dec)
    if model_counts!=Counter({"M0":4248,"M1":4248,"M2":4248}) or dc!=Counter({"BASELINE":3600,"NUMERICAL_STABILITY_EXTRA":648}): raise RuntimeError("Model/decision-class counts mismatch")
    can_by={r["job_id"]:r for r in canary}; can_import=sum(j in cp_by for j in can_by); can_core=sum(cp_by.get(j,{}).get("result_core_sha256")!=r["result_core_sha256"] for j,r in can_by.items())
    temp_by={(r["simulation_unit_id"],int(r["external_optimizer_seed"])):r for r in temporal_csv}; groups=defaultdict(dict)
    for r in cp: groups[(r["simulation_unit_id"],int(r["external_optimizer_seed"]))][r["model_id"]]=r
    mean_pass=fft_pass=temp_mm=0
    for (sid,seed),m in sorted(groups.items()):
        t,_,_=runner.extract_payload(jobs_by[(sid,seed,"M0")],payloads); mean_dt=float(np.mean(np.diff(t))); pos=int(np.sum(np.fft.fftfreq(len(t),d=mean_dt)>0.0)); row=temp_by.get((sid,seed))
        dt_ok=all(same_float(m[x]["afino_effective_dt_s"],mean_dt) for x in ("M0","M1","M2")); ff_ok=all(int(m[x]["positive_frequency_bin_count"])==pos for x in ("M0","M1","M2")); mean_pass+=int(dt_ok); fft_pass+=int(ff_ok)
        if row is None or row.get("mean_dt_contract_match")!="True" or row.get("positive_fftfreq_contract_match")!="True" or not same_float(row.get("mean_dt_external_s"),mean_dt) or int(row.get("positive_fftfreq_bin_count_external","-1"))!=pos: temp_mm+=1
    dup_jobs=12744-len(cp_by); dup_keys=12744-len({(r["simulation_unit_id"],int(r["external_optimizer_seed"]),r["model_id"]) for r in cp})
    if fetch_invocations(repo/DEV_CHECKPOINT_REL)!=expected_invocations(): raise RuntimeError("Invocation ledger mismatch")
    held=json.loads((repo/HELDOUT_AUDIT_REL).read_text(encoding="utf-8"))
    if held.get("heldout_registry_rows")!=4320 or held.get("heldout_generated") is not False or held.get("heldout_accessed") is not False: raise RuntimeError("HELDOUT audit mismatch")
    for k in ("heldout_noise_draws","heldout_period_draws","heldout_phase_draws","heldout_flux_arrays","heldout_payloads","afino_heldout_jobs"):
        if held.get(k)!=0: raise RuntimeError(f"HELDOUT activity {k}={held.get(k)}")
    can_a=json.loads((repo/CANARY_AUDIT_REL).read_text(encoding="utf-8"))
    if can_a.get("status")!="PHASE3B_DEVELOPMENT_RUNNER_VALIDATED_ON_FROZEN_CANARY" or can_a.get("exact_replay_matches")!=18 or can_a.get("exact_replay_mismatches")!=0: raise RuntimeError("Canary audit mismatch")
    observed={"plan_checkpoint_mismatches":plan_mm,"checkpoint_csv_mismatches":csv_mm,"payload_mismatches":payload_mm,"result_core_mismatches":core_mm,"decision_recalculation_mismatches":dec_mm,"temporal_csv_mismatches":temp_mm,"canary_imported":can_import,"canary_result_core_mismatches":can_core,"duplicate_job_ids":dup_jobs,"duplicate_scientific_keys":dup_keys,"mean_dt_temporal_contract_pass":mean_pass,"positive_fftfreq_temporal_contract_pass":fft_pass}
    expected={"plan_checkpoint_mismatches":0,"checkpoint_csv_mismatches":0,"payload_mismatches":0,"result_core_mismatches":0,"decision_recalculation_mismatches":0,"temporal_csv_mismatches":0,"canary_imported":648,"canary_result_core_mismatches":0,"duplicate_job_ids":0,"duplicate_scientific_keys":0,"mean_dt_temporal_contract_pass":4248,"positive_fftfreq_temporal_contract_pass":4248}
    if observed!=expected: raise RuntimeError(json.dumps({"observed":observed,"expected":expected},indent=2,sort_keys=True))
    ops=operational_summary(cp)
    audit={"phase":"F3B.3","status":"PHASE3B_DEVELOPMENT_EXECUTION_VALIDATION_PASS","scope":"DEVELOPMENT_ONLY","f3b2_commit":F3B2_COMMIT,"f3b2_tag":F3B2_TAG,"f3b3_canary_freeze_commit":CANARY_FREEZE_COMMIT,"f3b3_authorization_commit":AUTHORIZATION_COMMIT,"afino_version":AFINO_VERSION,"afino_commit":AFINO_COMMIT,"runner_sha256":RUNNER_SHA256,"blinded_plan_sha256":FULL_PLAN_SHA256,"development_checkpoint_sha256":FINAL_CHECKPOINT_SHA256,"frozen_plan_jobs":12744,"checkpoint_jobs":12744,"results_csv_rows":12744,"decisions_rows":4248,"temporal_rows":4248,"model_counts":dict(model_counts),"decision_class_counts":dict(dc),**observed,"canary_decisions":216,"canary_jobs":648,"canary_exact_replay_jobs":18,"canary_exact_replay_matches":18,"full_checkpoint_sequence_new_jobs":[3000,3000,3000,3000,96,0],"generator_imported":False,"synthetic_arrays_regenerated":False,"truth_used_as_inference_feature":False,"heldout_registry_rows":4320,"heldout_generated":False,"heldout_accessed":False,"heldout_stochastic_draws":0,"afino_heldout_jobs":0,"scientific_metrics_computed":False,"candidate_rule_fitted":False,"selection_function_estimated":False,"validator_incidents":[{"incident_id":"F3B3-TOOL-002","failed_validator_sha256":"77c5e5cb0589aa88a094f246a49509b2d51c490f76986d988526ed46e08e65af","classification":"VALIDATOR_COMPARISON_BUG_NO_SCIENTIFIC_BYTES_CHANGED","detail":"The first final-validator candidate compared plan-only AFINO version/commit/cutoff fields against SQLite result rows where those fields are intentionally not persisted per row. All other independent checks were zero-mismatch/pass. The corrected validator checks per-row scientific/execution identity against runner-normalized jobs and validates AFINO provenance through frozen plan fields plus checkpoint metadata."}],"operational_summary_by_model":ops,"output_sha256":{RESULTS_REL.name:sha256_file(repo/RESULTS_REL),DECISIONS_REL.name:sha256_file(repo/DECISIONS_REL),TEMPORAL_REL.name:sha256_file(repo/TEMPORAL_REL),BOOTSTRAP_EVIDENCE_REL.name:sha256_file(repo/BOOTSTRAP_EVIDENCE_REL)}}
    (repo/EXEC_AUDIT_REL).parent.mkdir(parents=True,exist_ok=True); (repo/EXEC_AUDIT_REL).write_text(json.dumps(audit,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n"); (repo/REPORT_REL).write_text(report_text(audit),encoding="utf-8",newline="\n")
    checksum_paths=[Path("workflows/phase3b/development/config/f3b3_afino_execution_environment_binding.json"),AUTH_REL,PLAN_REL,Path("workflows/phase3b/development/evidence/tables/f3b3_canary_decision_manifest.csv"),Path("workflows/phase3b/development/evidence/tables/f3b3_canary_job_manifest.csv"),CANARY_RESULTS_REL,CANARY_DECISIONS_REL,CANARY_TEMPORAL_REL,CANARY_REPLAY_REL,BOOTSTRAP_EVIDENCE_REL,RESULTS_REL,DECISIONS_REL,TEMPORAL_REL,ENV_REL,CANARY_AUDIT_REL,HELDOUT_AUDIT_REL,EXEC_AUDIT_REL,REPORT_REL,RUNNER_REL,SELF_REL,Path("workflows/phase3b/tests/test_f3b3_development_runner.py"),DEV_CHECKPOINT_REL,CANARY_CHECKPOINT_REL,BOOTSTRAP_RUNTIME_REL]
    lines=[]
    for rel in checksum_paths:
        p=repo/rel
        if not p.is_file(): raise FileNotFoundError(p)
        lines.append(f"{sha256_file(p)}  {rel.as_posix()}")
    (repo/SUMS_REL).parent.mkdir(parents=True,exist_ok=True); (repo/SUMS_REL).write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n")
    expected_after=expected_pre|{EXEC_AUDIT_REL.as_posix(),REPORT_REL.as_posix(),SUMS_REL.as_posix()}; dirty_after={x[3:].replace('\\','/').strip() for x in git_text(repo,"status","--porcelain","--untracked-files=all").splitlines() if x.strip()}
    if dirty_after!=expected_after: raise RuntimeError(f"Unexpected final dirty scope: {sorted(dirty_after)}")
    print("PHASE3B_DEVELOPMENT_EXECUTION_VALIDATION_PASS"); print("frozen_plan = 12744/12744"); print("checkpoint = 12744/12744 OK"); print("results_csv = 12744/12744"); print("decisions = 4248/4248"); print("temporal = 4248/4248"); print("M0/M1/M2 = 4248/4248/4248"); print("BASELINE = 3600"); print("NUMERICAL_STABILITY_EXTRA = 648"); print("plan_checkpoint_mismatches = 0"); print("checkpoint_csv_mismatches = 0"); print("payload_mismatches = 0"); print("result_core_mismatches = 0"); print("decision_recalculation_mismatches = 0"); print("canary_imported = 648"); print("canary_result_core_mismatches = 0"); print("duplicate_job_ids = 0"); print("duplicate_scientific_keys = 0"); print("mean_dt_temporal_contract = 4248/4248 PASS"); print("positive_fftfreq_temporal_contract = 4248/4248 PASS"); print("generator_imported = false"); print("synthetic_arrays_regenerated = false"); print("truth_used_as_inference_feature = false"); print("heldout_generated = false"); print("heldout_accessed = false"); print("heldout_stochastic_draws = 0"); print("scientific_metrics_computed = false"); print("candidate_rule_fitted = false"); print("selection_function_estimated = false"); print("development_execution_audit_sha256 =",sha256_file(repo/EXEC_AUDIT_REL)); print("development_execution_report_sha256 =",sha256_file(repo/REPORT_REL)); print("f3b3_SHA256SUMS_sha256 =",sha256_file(repo/SUMS_REL)); print("final_dirty_scope = 8 files"); print("STOP_BEFORE_FINAL_COMMIT")


def main():
    ap=argparse.ArgumentParser(); mode=ap.add_mutually_exclusive_group(required=True); mode.add_argument("--assemble",action="store_true"); mode.add_argument("--validate",action="store_true"); ap.add_argument("--repo-root",default="."); ap.add_argument("--afino-repo"); args=ap.parse_args(); repo=Path(args.repo_root).resolve()
    if args.assemble:
        if not args.afino_repo: raise SystemExit("--afino-repo is required with --assemble")
        assemble(repo,Path(args.afino_repo).resolve(),Path(__file__).resolve())
    else: validate(repo)

if __name__=="__main__": main()
