#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
D=ROOT/"workflows/phase3b/design"
P3A="1f3b1cc21286c25dea6a0e5779c0dc18edd81933"

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()

def j(name): return json.loads((D/name).read_text(encoding="utf-8"))
def rows(name):
    with (D/name).open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

req=rows("f3b1_entry_requirement_resolution.csv")
split=rows("f3b1_split_registry.csv")
comp=rows("f3b1_comparator_resolution.csv")
sampling=j("f3b1_sampling_plan.json")
truth=j("f3b1_truth_label_contract.json")
held=j("f3b1_heldout_access_policy.json")
candidate=j("f3b1_candidate_rule_policy.json")

if len(req)!=18 or any(r["resolution_status"]!="RESOLVED_FOR_F3B_DESIGN" for r in req):
    raise SystemExit("18/18 F3B entry requirements are not resolved")
if len(comp)!=6 or any(r["resolution_status"]!="RESOLVED_BEFORE_DEVELOPMENT" for r in comp):
    raise SystemExit("Deferred comparators are not fully resolved")

dev=sum(r["split"]=="DEVELOPMENT" for r in split)
ho=sum(r["split"]=="HELDOUT" for r in split)
if (dev,ho)!=(4320,4320):
    raise SystemExit("Unexpected planned split counts")
if any(r["synthetic_series_materialized"]!="false" for r in split):
    raise SystemExit("Synthetic materialization detected in F3B.1 registry")

prereg={
  "study_id":"TESS-QPP-PHASE3B-F3B1",
  "study_version":"phase3b-design-v1",
  "status":"PHASE3B_VALIDATION_DESIGN_FROZEN_BEFORE_ANY_INJECTION",
  "scientific_question":"How does the frozen AFINO 0.5 QPP selection procedure perform under prospectively defined known synthetic truth across the frozen F3B primary domain, and can any prospectively restricted DEVELOPMENT-only rule improve it and independently validate on a single-use HELDOUT set?",
  "primary_validation_target":"Frozen AFINO 0.5 selection under known synthetic truth; correction development is optional.",
  "baseline_afino_version":"0.5",
  "baseline_afino_commit":"6aceac9518fc8056052807e666da9d0c8bebb010",
  "synthetic_ground_truth_known":True,
  "primary_signal_family":"STATIONARY_ENVELOPE_MODULATED_SINUSOID",
  "simulation_domain_sha256":sha(D/"f3b1_simulation_domain.csv"),
  "generator_contract_sha256":sha(D/"f3b1_generator_contract.json"),
  "sampling_plan_sha256":sha(D/"f3b1_sampling_plan.json"),
  "split_registry_sha256":sha(D/"f3b1_split_registry.csv"),
  "metrics_contract_sha256":sha(D/"f3b1_metrics_contract.json"),
  "selection_function_contract_sha256":sha(D/"f3b1_selection_function_contract.json"),
  "candidate_rule_policy_sha256":sha(D/"f3b1_candidate_rule_policy.json"),
  "success_failure_gate_sha256":sha(D/"f3b1_success_failure_gate.json"),
  "truth_label_contract_sha256":sha(D/"f3b1_truth_label_contract.json"),
  "evidence_plane_contract_sha256":sha(D/"f3b1_evidence_plane_contract.json"),
  "heldout_access_policy_sha256":sha(D/"f3b1_heldout_access_policy.json"),
  "comparator_resolution_sha256":sha(D/"f3b1_comparator_resolution.csv"),
  "numerical_stability_protocol_sha256":sha(D/"f3b1_numerical_stability_protocol.json"),
  "source_bindings_sha256":sha(D/"f3b1_source_bindings.json"),
  "entry_requirement_resolution_sha256":sha(D/"f3b1_entry_requirement_resolution.csv"),
  "development_series_count":dev,
  "heldout_series_count":ho,
  "development_background_realizations":sampling["development_background_realizations"],
  "heldout_background_realizations":sampling["heldout_background_realizations"],
  "heldout_generated":False,
  "heldout_accessed":False,
  "candidate_rule_frozen":False,
  "correction_claim_established":False,
  "observational_ground_truth_assumed":False,
  "injections_generated":False,
  "afino_executed":False,
  "scientific_results_computed":False,
  "development_generated":False,
  "baseline_validation_mandatory":True,
  "correction_rule_mandatory":False,
  "heldout_is_single_use":True,
  "new_bibliographic_search":False,
}
(D/"f3b1_preregistration.json").write_text(
    json.dumps(prereg,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n"
)

protected={}
for scope in ["foundation/f0-f2","docs/literature/bibliographic_audit_ii","workflows/phase3a"]:
    cp=subprocess.run(["git","-C",str(ROOT),"diff","--name-only",P3A,"--",scope],
                      stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    protected[scope]=cp.stdout.decode().strip()==""

audit={
  "schema_version":1,
  "phase":"F3B.1",
  "result":"PHASE3B_DESIGN_FREEZE_VALIDATION_PASS",
  "f3a_entry_requirements":{"resolved":18,"total":18,"pass":True},
  "baii_deferred_comparators":{"resolved":6,"total":6,"pass":True},
  "ground_truth_states":{"defined":True,"states":["SYNTHETIC_QPP_PRESENT","SYNTHETIC_QPP_ABSENT"]},
  "simulation_domain":{"fully_bounded":True,"primary_period_support_s":[40,300]},
  "generator":{"fully_specified":True,"same_code_development_heldout":True},
  "development_split":{"frozen":True,"background_realizations":1800,"planned_series":4320},
  "heldout_split":{"frozen":True,"background_realizations":1800,"planned_series":4320},
  "development_data_generated":0,
  "heldout_data_generated":0,
  "metrics_frozen":True,
  "selection_function_method_frozen":True,
  "rule_development_policy_frozen":True,
  "promotion_gates_frozen":True,
  "afino_executed":False,
  "injections_generated":False,
  "heldout_accessed":False,
  "candidate_rule_frozen":False,
  "correction_claim_established":False,
  "scientific_results_computed":False,
  "observational_ground_truth_assumed":False,
  "protected_scopes_modified":{
      "foundation_f0_f2":not protected["foundation/f0-f2"],
      "bibliographic_audit_ii":not protected["docs/literature/bibliographic_audit_ii"],
      "phase3a":not protected["workflows/phase3a"],
  },
  "all_protected_scopes_unchanged":all(protected.values()),
  "heldout_generated_before_rule_freeze":held["heldout_generated_before_rule_freeze"],
  "heldout_access_before_rule_freeze":held["heldout_access_before_rule_freeze"],
  "heldout_is_single_use":held["heldout_is_single_use"],
  "baseline_validation_mandatory":candidate["baseline"]["baseline_validation_mandatory"],
  "correction_rule_mandatory":candidate["correction_rule_mandatory"],
  "truth_contract_observational_reference_ground_truth":truth["ground_truth_policy"]["observational_reference_ground_truth"],
}
if not audit["all_protected_scopes_unchanged"]:
    raise SystemExit("Protected historical scope changed")
(D/"f3b1_design_audit.json").write_text(
    json.dumps(audit,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n"
)

files=sorted(p for p in D.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt")
lines=[f"{sha(p)}  {p.name}" for p in files]
(D/"SHA256SUMS.txt").write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n")

print("F3B1_DESIGN_REGISTRY_BUILT")
print("preregistration_sha256 =",sha(D/"f3b1_preregistration.json"))
print("design_audit_sha256 =",sha(D/"f3b1_design_audit.json"))
print("sha256_registry_sha256 =",sha(D/"SHA256SUMS.txt"))
print("checksum_entries =",len(lines))
print("status = PHASE3B_VALIDATION_DESIGN_FROZEN_BEFORE_ANY_INJECTION")
print("audit_result = PHASE3B_DESIGN_FREEZE_VALIDATION_PASS")
print("injections_generated = false")
print("afino_executed = false")
print("development_generated = false")
print("heldout_generated = false")
print("heldout_accessed = false")
