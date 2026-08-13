#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, json, re, subprocess
from collections import Counter
from pathlib import Path

F3A5_COMMIT="06a1785d5a45453911044f19590d78f9a0fdad5f"
F3A5_TAG="phase3a-robustness-v1"
F2_WITNESS_TAG="phase3a-design-v1"
F2_WITNESS_TAG_COMMIT="6f7d4b03a16dbf4d4fa44dec0f67bd06ec5b9d85"

BIND=Path("workflows/phase3a/closure/f3a6_source_bindings.json")
CLOS=Path("workflows/phase3a/closure")
README=Path("workflows/phase3a/README.md")
DR=Path("docs/decisions/DR-005-phase3a-closure-and-f3b-entry.md")
PROTECTED=[
 "foundation/f0-f2","docs/literature/bibliographic_audit_ii","workflows/phase3a/design",
 "workflows/phase3a/config/f3a2_primary_catalogue_binding.json",
 "workflows/phase3a/config/f3a2_tess_product_binding_policy.json",
 "workflows/phase3a/config/f3a4_full_execution_authorization.json",
 "workflows/phase3a/config/f3a5_analysis_contract.json",
 "workflows/phase3a/evidence","workflows/phase3b"
]
EXPECTED_TRANS={"SELECTED_RETAINED":295,"SELECTION_LOST":171,"NOT_SELECTED_RETAINED":3178,"SELECTION_GAINED":0}
PROHIBITED_BAD=[
  ("observational false-positive rate is zero", "FPR=0"),
  ("51 false QPP", "51 false QPP"),
  ("F3A proves F2", "F3A proves F2"),
  ("AFINO is observationally validated", "AFINO is observationally validated")
]

def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()

def git(repo,*args):
    return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()

def read_csv(p):
    with p.open("r",encoding="utf-8",newline="") as f:return list(csv.DictReader(f))

def verify(repo: Path, verify_git=True):
    checks={}
    b=json.loads((repo/BIND).read_text(encoding="utf-8"))
    if verify_git:
        checks["f3a5_tag"]=git(repo,"rev-parse",f"{F3A5_TAG}^{{}}")==F3A5_COMMIT
        checks["f2_witness_tag"]=git(repo,"rev-parse",f"{F2_WITNESS_TAG}^{{}}")==F2_WITNESS_TAG_COMMIT
    else:
        checks["f3a5_tag"]=checks["f2_witness_tag"]=True

    source_by_id={s["source_id"]:s for s in b["sources"]}
    for s in b["sources"]:
        p=repo/s["repository_relative_path"]
        if not p.is_file() or sha256(p)!=s["sha256"]: raise RuntimeError(f"source binding failed {s['source_id']}")
    checks["source_bindings"]=True

    f2=json.loads((repo/source_by_id["F2SRC001"]["repository_relative_path"]).read_text(encoding="utf-8"))
    f2decision=json.loads((repo/source_by_id["F2SRC006"]["repository_relative_path"]).read_text(encoding="utf-8"))
    base=read_csv(repo/source_by_id["F3A5SRC001"]["repository_relative_path"])
    out=read_csv(repo/source_by_id["F3A5SRC002"]["repository_relative_path"])
    opt=read_csv(repo/source_by_id["F3A5SRC004"]["repository_relative_path"])
    per=read_csv(repo/source_by_id["F3A5SRC005"]["repository_relative_path"])
    f3audit=json.loads((repo/source_by_id["F3A5SRC006"]["repository_relative_path"]).read_text(encoding="utf-8"))

    if (f2["cohort_events"],f2["cohort_pairs"])!=(10,5): raise RuntimeError("F2 scope mismatch")
    if (f2["primary_planned_variants"],f2["primary_eligible_variants"],f2["primary_inadmissible_variants"])!=(780,514,266): raise RuntimeError("F2 denominator mismatch")
    if f2["baseline_rows"]!=10 or f2["baseline_classification_mismatches"]!=0: raise RuntimeError("F2 baseline mismatch")
    if f2["stability_variants"]!=46 or f2["stability_decisions_seed_0_to_9"]!=460 or f2["stability_decision_discordant_variants"]!=0: raise RuntimeError("F2 optimizer mismatch")
    if f2["period_robustness_rows"]!=140: raise RuntimeError("F2 period mismatch")
    checks["f2_reconstruction"]=True

    if len(base)!=122: raise RuntimeError("F3A baseline rows mismatch")
    bc=dict(Counter(r["baseline_gate_state"] for r in base));bc.setdefault("INCOMPLETE_NUMERICAL",0)
    if bc!={"REFERENCE_CONCORDANT":65,"REFERENCE_BASELINE_MISMATCH":51,"INPUT_INADMISSIBLE":6,"INCOMPLETE_NUMERICAL":0}: raise RuntimeError(f"F3A baseline mismatch {bc}")
    q=dict(Counter(r["baseline_gate_state"] for r in base if r["observational_reference_role"]=="PUBLISHED_QPP_REFERENCE")); q.setdefault("INPUT_INADMISSIBLE",0);q.setdefault("REFERENCE_BASELINE_MISMATCH",0)
    c=dict(Counter(r["baseline_gate_state"] for r in base if r["observational_reference_role"]=="PUBLISHED_NOT_SELECTED_REFERENCE")); c.setdefault("INPUT_INADMISSIBLE",0);c.setdefault("REFERENCE_BASELINE_MISMATCH",0)
    if q!={"REFERENCE_CONCORDANT":8,"REFERENCE_BASELINE_MISMATCH":51,"INPUT_INADMISSIBLE":2}: raise RuntimeError("QPP role mismatch")
    if c!={"REFERENCE_CONCORDANT":57,"REFERENCE_BASELINE_MISMATCH":0,"INPUT_INADMISSIBLE":4}: raise RuntimeError("control role mismatch")
    if len(out)!=9516: raise RuntimeError("matrix mismatch")
    if sum(r["materialization_status"]=="ELIGIBLE_FOR_AFINO" for r in out)!=6422 or sum(r["materialization_status"]=="INPUT_INADMISSIBLE" for r in out)!=3094: raise RuntimeError("admissibility mismatch")
    tc=dict(Counter(r["classification_transition"] for r in out if r["classification_transition"]))
    for k in EXPECTED_TRANS:tc.setdefault(k,0)
    if tc!=EXPECTED_TRANS:raise RuntimeError(f"transition mismatch {tc}")
    if any(r["classification_transition"] and r["baseline_gate_state"]!="REFERENCE_CONCORDANT" for r in out):raise RuntimeError("nonconcordant transition")
    if len(opt)!=116 or sum(int(r["seed_count"]) for r in opt)!=1160 or any(int(r["discordant_vs_seed0_count"]) for r in opt):raise RuntimeError("optimizer mismatch")
    if len(per)!=295:raise RuntimeError("period mismatch")
    checks["f3a_reconstruction"]=True

    cmp=read_csv(repo/CLOS/"f3a6_f2_f3a_comparison_matrix.csv")
    led=read_csv(repo/CLOS/"f3a6_phase3a_evidence_ledger.csv")
    claims=read_csv(repo/CLOS/"f3a6_claim_matrix.csv")
    lim=read_csv(repo/CLOS/"f3a6_limitations_register.csv")
    req=read_csv(repo/CLOS/"f3a6_phase3b_entry_requirements.csv")
    dec=json.loads((repo/CLOS/"f3a6_phase3a_decision.json").read_text(encoding="utf-8"))
    aud=json.loads((repo/CLOS/"f3a6_closure_audit.json").read_text(encoding="utf-8"))
    report=(repo/CLOS/"f3a6_phase3a_synthesis_report.md").read_text(encoding="utf-8")
    dr=(repo/DR).read_text(encoding="utf-8")
    rdm=(repo/README).read_text(encoding="utf-8")

    if len(cmp)<11:raise RuntimeError("comparison dimensions <11")
    if {r["evidence_plane"] for r in led}!={"OBSERVATIONAL_REFERENCE_REPRODUCTION","INPUT_ADMISSIBILITY","CLASSIFICATION_ROBUSTNESS","NUMERICAL_STABILITY","PERIOD_ROBUSTNESS","F2_TO_F3A_COMPARISON","INTERPRETATION_LIMITS"}:raise RuntimeError("evidence planes mismatch")
    if len(claims)<19:raise RuntimeError("claims <19")
    evidence_ids={r["evidence_id"] for r in led}
    for cl in claims:
        if cl["status"]!="PROHIBITED":
            ids=[x for x in cl["evidence_ids"].split(";") if x]
            if not ids or any(x not in evidence_ids for x in ids):raise RuntimeError(f"unmapped claim {cl['claim_id']}")
    if len(lim)<20:raise RuntimeError("limitations <20")
    if len(req)<17:raise RuntimeError("F3B req <17")
    if any(r["status"]!="OPEN_FOR_F3B_DESIGN" for r in req):raise RuntimeError("F3B requirement status mismatch")
    checks["closure_tables"]=True

    if dec["phase_status"]!="PHASE3A_COMPLETE_PROCEED_TO_F3B_WITH_LIMITATIONS":raise RuntimeError("decision mismatch")
    required_false=["observational_ground_truth_established","afino_observationally_validated","sensitivity_established","specificity_established","observational_fpr_established","correction_claim_established","selection_function_established","manuscript1_validation_component_complete","candidate_discovery_authorized"]
    if any(dec[k] is not False for k in required_false):raise RuntimeError("decision boundary mismatch")
    if dec["f3b_required"] is not True or dec["manuscript1_robustness_component_supported"] is not True:raise RuntimeError("decision route mismatch")
    checks["decision"]=True

    if aud["validation_status"]!="PHASE3A_CLOSURE_VALIDATION_PASS":raise RuntimeError("audit gate mismatch")
    if aud["qpp_baseline_mismatches_preserved"]!=51 or aud["baseline_mismatches_recoded"]!=0 or aud["events_removed"]!=0:raise RuntimeError("mismatch preservation failed")
    if aud["frozen_counts"]["qpp_role"]!={"concordant":8,"mismatch":51,"inadmissible":2}:raise RuntimeError("audit QPP split mismatch")
    if aud["frozen_counts"]["not_selected_role"]!={"concordant":57,"mismatch":0,"inadmissible":4}:raise RuntimeError("audit control split mismatch")
    if aud["frozen_counts"]["transitions"]!={"selected_retained":295,"selection_lost":171,"not_selected_retained":3178,"selection_gained":0}:raise RuntimeError("audit transitions mismatch")
    if any(v is not False for k,v in aud["scientific_boundaries"].items() if k not in ("frozen_evidence_reconstruction_only",)) or aud["scientific_boundaries"]["frozen_evidence_reconstruction_only"] is not True:
        raise RuntimeError("closure scientific boundary mismatch")
    checks["closure_audit"]=True

    # Reject dangerous positive transformations through the formal claim matrix.
    claim_status={r["claim_id"]:r["status"] for r in claims}
    required_prohibited={
        "F3A020":"F3A proves F2.",
        "F3A021":"The observational false-positive rate is zero.",
        "F3A022":"The 51 QPP-reference baseline mismatches are false QPP detections.",
        "F3A023":"Catalogue scale validates AFINO.",
    }
    for cid in required_prohibited:
        if claim_status.get(cid)!="PROHIBITED":
            raise RuntimeError(f"Required prohibited claim not blocked: {cid}")
    # The narrative must explicitly preserve the two most consequential qualifications.
    report_low=report.lower()
    if "not an observational false-positive rate of zero" not in report_low:
        raise RuntimeError("Report does not explicitly reject FPR=0 transformation")
    if "not evidence that 51 published detections are physically false" not in report_low:
        raise RuntimeError("Report does not explicitly reject 51-false-QPP transformation")
    checks["prohibited_transformations"]=True

    wc=len(report.split())
    if not 1400<=wc<=1900:raise RuntimeError(f"report word count {wc}")
    if "PHASE 3A CLOSED" not in rdm or "F3B NOT STARTED" not in rdm:raise RuntimeError("README status mismatch")
    if "PHASE3A_COMPLETE_PROCEED_TO_F3B_WITH_LIMITATIONS" not in dr:raise RuntimeError("DR decision missing")
    checks["report_readme_dr"]=True

    sums=(repo/CLOS/"SHA256SUMS.txt").read_text(encoding="ascii").splitlines()
    expected={p.name for p in (repo/CLOS).iterdir() if p.is_file() and p.name!="SHA256SUMS.txt"}
    actual=set()
    for line in sums:
        dig,name=line.split("  ",1); actual.add(name)
        if sha256(repo/CLOS/name)!=dig:raise RuntimeError(f"checksum mismatch {name}")
    if actual!=expected:raise RuntimeError(f"closure checksum membership mismatch missing={expected-actual} extra={actual-expected}")
    checks["closure_checksums"]=True

    if verify_git:
        # No historical/protected scope may have changed relative to approved F3A.5.
        for scope in PROTECTED:
            diff=git(repo,"diff","--name-only",F3A5_TAG,"--",scope)
            status=git(repo,"status","--porcelain","--",scope)
            if diff or status:raise RuntimeError(f"protected scope modified: {scope}")
    checks["protected_scopes"]=True

    print("PHASE3A_CLOSURE_VALIDATION_PASS")
    for k in sorted(checks): print(k,"= PASS")
    print("f2_events = 10")
    print("f3a_events = 122")
    print("baseline = 65 / 51 / 6")
    print("qpp_role = 8 / 51 / 2")
    print("not_selected_role = 57 / 0 / 4")
    print("primary = 9516 / 6422 / 3094")
    print("transitions = 295 / 171 / 3178 / 0")
    print("optimizer = 116 events / 1160 decisions / 0 discordant")
    print("period_comparable = 295")
    print("comparison_dimensions =",len(cmp))
    print("claim_count =",len(claims))
    print("limitation_count =",len(lim))
    print("f3b_requirement_count =",len(req))
    print("decision =",dec["phase_status"])
    print("new_afino_execution = false")
    print("new_scientific_statistics_computed = false")
    print("observational_ground_truth_established = false")
    print("candidate_discovery_authorized = false")
    return checks

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=".")
    a=ap.parse_args();verify(Path(a.repo_root).resolve(),verify_git=True)
if __name__=="__main__":main()
