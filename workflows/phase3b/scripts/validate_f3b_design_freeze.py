#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, re, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
D=ROOT/"workflows/phase3b/design"
DEV=ROOT/"workflows/phase3b/development"
HO=ROOT/"workflows/phase3b/heldout"
P3A="1f3b1cc21286c25dea6a0e5779c0dc18edd81933"
ALLOWED_COMP={
 "IMPLEMENT_IN_DEVELOPMENT","IMPLEMENT_AS_HELDOUT_COMPARATOR","CITATION_ONLY",
 "NOT_APPLICABLE_WITH_RATIONALE","UNAVAILABLE_WITH_DOCUMENTED_REASON"
}
EXPECTED_DESIGN={
 "README.md","SHA256SUMS.txt","f3b1_candidate_rule_policy.json",
 "f3b1_comparator_resolution.csv","f3b1_design_audit.json",
 "f3b1_entry_requirement_resolution.csv","f3b1_evidence_plane_contract.json",
 "f3b1_generator_contract.json","f3b1_heldout_access_policy.json",
 "f3b1_metrics_contract.json","f3b1_numerical_stability_protocol.json",
 "f3b1_preregistration.json","f3b1_protocol.md","f3b1_sampling_plan.json",
 "f3b1_selection_function_contract.json","f3b1_simulation_domain.csv",
 "f3b1_source_bindings.json","f3b1_split_registry.csv",
 "f3b1_success_failure_gate.json","f3b1_truth_label_contract.json"
}

def fail(msg): raise SystemExit("FAIL: "+msg)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
 return h.hexdigest()
def j(name): return json.loads((D/name).read_text(encoding="utf-8"))
def rows(name):
 with (D/name).open("r",encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))
def git(*args):
 cp=subprocess.run(["git","-C",str(ROOT),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if cp.returncode: fail("git "+" ".join(args)+" -> "+cp.stderr.decode(errors="replace"))
 return cp.stdout.decode().strip()

if {p.name for p in D.iterdir() if p.is_file()} != EXPECTED_DESIGN:
 fail("design file set mismatch")

reg={}
for line in (D/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
 h,name=line.split("  ",1); reg[name]=h
if set(reg)!=EXPECTED_DESIGN-{"SHA256SUMS.txt"}: fail("SHA registry entry set mismatch")
for name,h in reg.items():
 if sha(D/name)!=h: fail("SHA mismatch: "+name)

req=rows("f3b1_entry_requirement_resolution.csv")
if len(req)!=18 or len({r["requirement_id"] for r in req})!=18: fail("entry requirement rows")
if any(r["resolution_status"]!="RESOLVED_FOR_F3B_DESIGN" for r in req): fail("entry requirement unresolved")

split=rows("f3b1_split_registry.csv")
if len(split)!=8640: fail("split registry row count")
sim=[r["simulation_unit_id"] for r in split]
if len(set(sim))!=len(sim): fail("duplicate simulation_unit_id")
bg={}
for r in split: bg.setdefault(r["background_realization_id"],set()).add(r["split"])
if len(bg)!=3600 or any(len(v)!=1 for v in bg.values()): fail("background split leakage")
pairs={}
for r in split:
 key=(r["background_realization_id"],r["gap_quality_regime"])
 pairs.setdefault(key,set()).add(r["truth_state"])
if any(v!={"SYNTHETIC_QPP_PRESENT","SYNTHETIC_QPP_ABSENT"} for v in pairs.values()):
 fail("positive/null pair mismatch")
if {r["truth_state"] for r in split}!={"SYNTHETIC_QPP_PRESENT","SYNTHETIC_QPP_ABSENT"}:
 fail("invalid truth state")
if any(r["synthetic_series_materialized"]!="false" for r in split): fail("materialized synthetic series")
if any(r["background_noise_materialized"]!="false" for r in split): fail("materialized background")
if any(r["true_period_materialized"]!="false" for r in split): fail("materialized true period")
if any(r["afino_execution_allowed_now"]!="false" for r in split): fail("AFINO execution authorized prematurely")
if any(r["heldout_access_allowed_now"]!="false" for r in split if r["split"]=="HELDOUT"):
 fail("heldout access authorized")

domain=rows("f3b1_simulation_domain.csv")
dm={r["parameter_name"]:r for r in domain}
if float(dm["true_period_s"]["minimum"])!=40 or float(dm["true_period_s"]["maximum"])!=300:
 fail("period domain")
if any(r["n_samples"] not in {"15","30","60","120"} for r in split): fail("n_samples outside domain")
if any(r["red_noise_alpha"] not in {"0.0","1.0","2.0"} for r in split): fail("red_noise_alpha outside domain")
if any(r["positive_pair_qpp_fraction"] not in {"0.01","0.02","0.04"} for r in split):
 fail("qpp fraction stratum outside domain")

truth=j("f3b1_truth_label_contract.json")
if truth["ground_truth_policy"]["observational_reference_ground_truth"] is not False: fail("observational truth leakage")
if truth["ground_truth_policy"]["real_observational_background_allowed_as_primary_null"] is not False: fail("observational background primary null")

metrics=j("f3b1_metrics_contract.json")
if metrics["scope"]["input_inadmissible_as_fn_or_tn"] is not False: fail("inadmissible confusion matrix")
if "SYNTHETIC_QPP_ABSENT" not in metrics["truth_mapping"]["negative"]: fail("known-null restriction")
if metrics["period_recovery"]["classification_separate"] is not True: fail("period recovery not separate")
if metrics["period_recovery"]["nonselected_m1_center_is_period_recovery"] is not False:
 fail("nonselected M1 center misused")

held=j("f3b1_heldout_access_policy.json")
if held["heldout_generated_before_rule_freeze"] is not False: fail("heldout pre-generation")
if held["heldout_access_before_rule_freeze"]!="PROHIBITED": fail("heldout access policy")
if held["heldout_is_single_use"] is not True: fail("heldout single-use")

cand=j("f3b1_candidate_rule_policy.json")
if cand["development_data_only"] is not True: fail("candidate not development-only")
if cand["heldout_access_for_development"]!="PROHIBITED": fail("candidate can access heldout")
if cand["correction_rule_mandatory"] is not False: fail("correction mandatory")

comp=rows("f3b1_comparator_resolution.csv")
if len(comp)!=6 or len({r["work_id"] for r in comp})!=6: fail("comparator resolution count")
if any(r["final_f3b1_status"] not in ALLOWED_COMP for r in comp): fail("comparator status")
if any(r["resolution_status"]!="RESOLVED_BEFORE_DEVELOPMENT" for r in comp): fail("comparator unresolved")

num=j("f3b1_numerical_stability_protocol.json")
if num["scope"]["heldout_series"]!=0: fail("heldout numerical stability")
if num["optimizer_seed_protocol"]["external_optimizer_seeds"]!=list(range(10)): fail("optimizer seed protocol")
if num["interpretation_guard"]["classification_stability_implies_unique_optimum"] is not False:
 fail("unique-optimum guard")

pre=j("f3b1_preregistration.json")
if pre["status"]!="PHASE3B_VALIDATION_DESIGN_FROZEN_BEFORE_ANY_INJECTION": fail("prereg status")
for k in ["heldout_generated","heldout_accessed","candidate_rule_frozen",
          "correction_claim_established","observational_ground_truth_assumed",
          "injections_generated","afino_executed","scientific_results_computed",
          "development_generated"]:
 if pre[k] is not False: fail("prereg state not false: "+k)
if pre["development_series_count"]!=4320 or pre["heldout_series_count"]!=4320: fail("prereg split counts")

audit=j("f3b1_design_audit.json")
if audit["result"]!="PHASE3B_DESIGN_FREEZE_VALIDATION_PASS": fail("audit result")
if audit["f3a_entry_requirements"]["resolved"]!=18: fail("audit requirements")
if audit["baii_deferred_comparators"]["resolved"]!=6: fail("audit comparators")
if audit["development_data_generated"]!=0 or audit["heldout_data_generated"]!=0: fail("audit generated data")
if audit["afino_executed"] is not False or audit["injections_generated"] is not False: fail("audit execution state")
if audit["heldout_accessed"] is not False: fail("audit heldout access")
if audit["all_protected_scopes_unchanged"] is not True: fail("audit protected scope")

for scope in ["foundation/f0-f2","docs/literature/bibliographic_audit_ii","workflows/phase3a"]:
 if git("diff","--name-only",P3A,"--",scope): fail("protected scope modified: "+scope)

for directory in [DEV,HO]:
 files=[p for p in directory.rglob("*") if p.is_file()]
 if len(files)!=1 or files[0].name!="README.md": fail("guard directory contains data: "+str(directory))

protocol=(D/"f3b1_protocol.md").read_text(encoding="utf-8")
wc=len(re.findall(r"\b[\wΔ≥–-]+(?:['’][\w]+)?\b",protocol,flags=re.UNICODE))
if not 1800 <= wc <= 2500: fail(f"protocol word count {wc} outside 1800..2500")

root=(ROOT/"workflows/phase3b/README.md").read_text(encoding="utf-8")
for phrase in ["VALIDATION DESIGN FROZEN —","NO INJECTIONS GENERATED",
               "DEVELOPMENT NOT STARTED","HELDOUT NOT GENERATED"]:
 if phrase not in root: fail("root README status missing: "+phrase)

print("PHASE3B_DESIGN_FREEZE_VALIDATION_PASS")
print("entry_requirements = 18/18")
print("deferred_comparators = 6/6")
print("simulation_units = 8640")
print("background_realizations = 3600")
print("development_series = 4320")
print("heldout_series = 4320")
print("duplicate_simulation_unit_id = 0")
print("background_split_leakage = 0")
print("heldout_materialized = 0")
print("development_materialized = 0")
print("afino_executed = false")
print("injections_generated = false")
print("heldout_accessed = false")
print("protected_scopes_modified = false")
print("protocol_word_count =",wc)
print("checksum_entries =",len(reg))
