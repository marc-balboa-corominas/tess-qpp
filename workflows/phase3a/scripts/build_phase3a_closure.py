#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, io, json, re, subprocess
from pathlib import Path
from collections import Counter

F3A5_COMMIT = "06a1785d5a45453911044f19590d78f9a0fdad5f"
F3A5_TAG = "phase3a-robustness-v1"
F2_IMPORT_COMMIT = "28c97e220ebdd74d05fd76ad9527fe7d11c686ca"
F2_WITNESS_TAG = "phase3a-design-v1"
F2_WITNESS_TAG_COMMIT = "6f7d4b03a16dbf4d4fa44dec0f67bd06ec5b9d85"

BINDINGS_REL = Path("workflows/phase3a/closure/f3a6_source_bindings.json")
CLOSURE_DIR = Path("workflows/phase3a/closure")
README_REL = Path("workflows/phase3a/README.md")
DR_REL = Path("docs/decisions/DR-005-phase3a-closure-and-f3b-entry.md")

EXPECTED_BASELINE = {
    "REFERENCE_CONCORDANT": 65,
    "REFERENCE_BASELINE_MISMATCH": 51,
    "INPUT_INADMISSIBLE": 6,
    "INCOMPLETE_NUMERICAL": 0,
}
EXPECTED_QPP_BASELINE = {
    "REFERENCE_CONCORDANT": 8,
    "REFERENCE_BASELINE_MISMATCH": 51,
    "INPUT_INADMISSIBLE": 2,
}
EXPECTED_CONTROL_BASELINE = {
    "REFERENCE_CONCORDANT": 57,
    "REFERENCE_BASELINE_MISMATCH": 0,
    "INPUT_INADMISSIBLE": 4,
}
EXPECTED_TRANSITIONS = {
    "SELECTED_RETAINED": 295,
    "SELECTION_LOST": 171,
    "NOT_SELECTED_RETAINED": 3178,
    "SELECTION_GAINED": 0,
}
EXPECTED_F2_TRANSITIONS = {
    "SELECTED_RETAINED": 140,
    "SELECTION_LOST": 136,
    "NOT_SELECTED_RETAINED": 238,
    "SELECTION_GAINED": 0,
    "INPUT_INADMISSIBLE": 266,
}
PLANES = [
    "OBSERVATIONAL_REFERENCE_REPRODUCTION",
    "INPUT_ADMISSIBILITY",
    "CLASSIFICATION_ROBUSTNESS",
    "NUMERICAL_STABILITY",
    "PERIOD_ROBUSTNESS",
    "F2_TO_F3A_COMPARISON",
    "INTERPRETATION_LIMITS",
]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1024*1024), b""):
            h.update(c)
    return h.hexdigest()

def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git","-C",str(repo),*args], text=True).strip()

def git_bytes(repo: Path, rev: str, rel: str):
    cp = subprocess.run(["git","-C",str(repo),"show",f"{rev}:{rel}"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return None if cp.returncode else cp.stdout

def read_csv(path: Path):
    with path.open("r",encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, fields, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n")
        w.writeheader(); w.writerows(rows)

def verify_sources(repo: Path, bindings: dict, verify_git: bool=True):
    if bindings["f3a5_freeze"] != {"commit":F3A5_COMMIT,"tag":F3A5_TAG}:
        raise RuntimeError("F3A.5 freeze binding mismatch")
    if bindings["f2_provenance"]["historical_import_commit"] != F2_IMPORT_COMMIT:
        raise RuntimeError("F2 import commit binding mismatch")
    if verify_git:
        if git(repo,"rev-parse",f"{F3A5_TAG}^{{}}") != F3A5_COMMIT:
            raise RuntimeError("Approved F3A.5 tag moved")
        if git(repo,"rev-parse",f"{F2_WITNESS_TAG}^{{}}") != F2_WITNESS_TAG_COMMIT:
            raise RuntimeError("F2 byte-exact witness tag moved")
    for src in bindings["sources"]:
        rel=src["repository_relative_path"]; p=repo/rel
        if not p.is_file(): raise RuntimeError(f"Missing source {rel}")
        if sha256(p)!=src["sha256"]: raise RuntimeError(f"Source hash mismatch {rel}")
        if verify_git and src["phase"].startswith("F2"):
            b=git_bytes(repo,F2_WITNESS_TAG,rel)
            if b is None or hashlib.sha256(b).hexdigest()!=src["sha256"]:
                raise RuntimeError(f"F2 witness-tag bytes mismatch {rel}")
    return True

def get_sources(bindings):
    return {s["source_id"]:s for s in bindings["sources"]}

def build(repo: Path, verify_git: bool=True):
    bind_path=repo/BINDINGS_REL
    bindings=json.loads(bind_path.read_text(encoding="utf-8"))
    verify_sources(repo,bindings,verify_git=verify_git)
    S=get_sources(bindings)

    f2audit=json.loads((repo/S["F2SRC001"]["repository_relative_path"]).read_text(encoding="utf-8"))
    f2decision=json.loads((repo/S["F2SRC006"]["repository_relative_path"]).read_text(encoding="utf-8"))
    base=read_csv(repo/S["F3A5SRC001"]["repository_relative_path"])
    outcomes=read_csv(repo/S["F3A5SRC002"]["repository_relative_path"])
    optimizer=read_csv(repo/S["F3A5SRC004"]["repository_relative_path"])
    periods=read_csv(repo/S["F3A5SRC005"]["repository_relative_path"])
    f3audit=json.loads((repo/S["F3A5SRC006"]["repository_relative_path"]).read_text(encoding="utf-8"))

    # Frozen-evidence reconstruction only.
    if f2audit["cohort_events"]!=10 or f2audit["cohort_pairs"]!=5: raise RuntimeError("F2 pilot scope mismatch")
    if (f2audit["primary_planned_variants"],f2audit["primary_eligible_variants"],f2audit["primary_inadmissible_variants"])!=(780,514,266):
        raise RuntimeError("F2 primary denominator mismatch")
    if f2audit["baseline_classification_mismatches"]!=0 or f2audit["baseline_rows"]!=10:
        raise RuntimeError("F2 baseline mismatch")
    f2trans=dict(f2audit["baseline_comparison_status_counts"])
    f2trans["SELECTION_GAINED"]=0
    if f2trans!=EXPECTED_F2_TRANSITIONS: raise RuntimeError(f"F2 transitions mismatch {f2trans}")
    if f2audit["stability_variants"]!=46 or f2audit["stability_decisions_seed_0_to_9"]!=460 or f2audit["stability_decision_discordant_variants"]!=0:
        raise RuntimeError("F2 optimizer scope mismatch")
    if f2audit["period_robustness_rows"]!=140: raise RuntimeError("F2 period mismatch")
    for k in ("observational_ground_truth_established","sensitivity_estimated","specificity_estimated","observational_false_positive_rate_estimated"):
        if f2audit["confirmations"][k] is not False: raise RuntimeError(f"F2 boundary mismatch {k}")

    if len(base)!=122 or Counter(r["observational_reference_role"] for r in base)!=Counter({"PUBLISHED_QPP_REFERENCE":61,"PUBLISHED_NOT_SELECTED_REFERENCE":61}):
        raise RuntimeError("F3A cohort/role mismatch")
    bcnt=dict(Counter(r["baseline_gate_state"] for r in base)); bcnt.setdefault("INCOMPLETE_NUMERICAL",0)
    if bcnt!=EXPECTED_BASELINE: raise RuntimeError(f"F3A baseline mismatch {bcnt}")
    qpp=dict(Counter(r["baseline_gate_state"] for r in base if r["observational_reference_role"]=="PUBLISHED_QPP_REFERENCE"))
    ctl=dict(Counter(r["baseline_gate_state"] for r in base if r["observational_reference_role"]=="PUBLISHED_NOT_SELECTED_REFERENCE"))
    qpp.setdefault("INPUT_INADMISSIBLE",0); qpp.setdefault("REFERENCE_BASELINE_MISMATCH",0)
    ctl.setdefault("INPUT_INADMISSIBLE",0); ctl.setdefault("REFERENCE_BASELINE_MISMATCH",0)
    if qpp!=EXPECTED_QPP_BASELINE: raise RuntimeError(f"QPP baseline split mismatch {qpp}")
    if ctl!=EXPECTED_CONTROL_BASELINE: raise RuntimeError(f"control baseline split mismatch {ctl}")

    if len(outcomes)!=9516: raise RuntimeError("F3A primary matrix mismatch")
    elig=sum(r["materialization_status"]=="ELIGIBLE_FOR_AFINO" for r in outcomes)
    inad=sum(r["materialization_status"]=="INPUT_INADMISSIBLE" for r in outcomes)
    if (elig,inad)!=(6422,3094): raise RuntimeError("F3A admissibility mismatch")
    trans=dict(Counter(r["classification_transition"] for r in outcomes if r["classification_transition"]))
    for k in EXPECTED_TRANSITIONS: trans.setdefault(k,0)
    if trans!=EXPECTED_TRANSITIONS: raise RuntimeError(f"F3A transition mismatch {trans}")
    if any(r["classification_transition"] and r["baseline_gate_state"]!="REFERENCE_CONCORDANT" for r in outcomes):
        raise RuntimeError("Transition with non-concordant baseline")
    if len(optimizer)!=116 or sum(int(r["seed_count"]) for r in optimizer)!=1160:
        raise RuntimeError("F3A optimizer denominator mismatch")
    if any(int(r["discordant_vs_seed0_count"])!=0 for r in optimizer):
        raise RuntimeError("F3A seed discordance mismatch")
    if any(int(r[f"unique_parameter_payloads_{m.lower()}"])!=10 for r in optimizer for m in ("M0","M1","M2")):
        raise RuntimeError("F3A parameter multiplicity mismatch")
    if len(periods)!=295: raise RuntimeError("F3A period denominator mismatch")
    if f3audit["period_comparable_rows"]!=295 or f3audit["seed_stable_events"]!=116 or f3audit["seed_discordant_events"]!=0:
        raise RuntimeError("F3A audit mismatch")
    for k in ("observational_ground_truth_established","sensitivity_computed","specificity_computed","observational_fpr_computed","candidate_discovery_authorized"):
        if f3audit["scientific_boundaries"][k] is not False: raise RuntimeError(f"F3A boundary mismatch {k}")

    closure=repo/CLOSURE_DIR; closure.mkdir(parents=True,exist_ok=True)

    cmp_rows=[
      ["CMP01","cohort scale","10 events / 5 pairs","Pilot observational robustness cohort.","F2SRC001;F2SRC007","122 events / 61+61 reference roles","Catalogue-scale observational cohort.","F3A5SRC001","SAME_CONCEPT_DIFFERENT_DENOMINATOR","F3A extends the same robustness question from a small pilot to catalogue scale.","Do not pool event or variant denominators across phases.","Do not claim F3A is a direct replication of the 10-event pilot."],
      ["CMP02","observational reference roles","5 PUBLISHED_QPP_REPRODUCED + 5 MATCHED_NOT_SELECTED","Roles are observational construction, not physical truth.","F2SRC001;F2SRC003","61 PUBLISHED_QPP_REFERENCE + 61 PUBLISHED_NOT_SELECTED_REFERENCE","Role symmetry is retained at catalogue scale.","F3A5SRC001","DIRECT_DESIGN_CONTINUITY","Both phases preserve QPP-reference and not-selected-reference observational roles.","Role names and denominators differ; neither role is ground truth.","Do not call either not-selected role a true-negative class."],
      ["CMP03","W00/P00 baseline reproduction","10/10 baseline classifications reproduced; 0 classification mismatches.","The pilot entered robustness with a fully reproduced frozen baseline.","F2SRC001;F2SRC002","65 concordant / 51 mismatch / 6 inadmissible; QPP role 8/51/2; not-selected role 57/0/4.","Catalogue scale reveals a material baseline-reproduction limitation concentrated in published QPP references.","F3A5SRC001;F3A5SRC006","F3A_NEW_LIMITATION","F3A baseline conditioning must be explicit in every transition claim.","The cause of the 51 QPP-reference mismatches is unresolved within F3A.","Do not recode 51 mismatches as false QPP detections."],
      ["CMP04","inherited 13×6 perturbation matrix","780 planned variants = 10×78.","Same 13 windows and 6 profiles were prospectively frozen.","F2SRC001;F2SRC007","9,516 planned variants = 122×78.","The catalogue-scale analysis retains the same 78-cell perturbation structure.","F3A5SRC002;F3A5SRC006","DIRECT_DESIGN_CONTINUITY","The perturbation design is directly continuous from pilot to scale-up.","Repeated measures remain nested within events.","Do not treat 780 or 9,516 variant rows as independent flares."],
      ["CMP05","input inadmissibility","266/780 inadmissible; 514 eligible.","Inadmissibility remained separate from non-selection.","F2SRC001;F2SRC003","3,094/9,516 inadmissible; 6,422 eligible.","The same methodological outcome remains explicit at catalogue scale.","F3A5SRC002;F3A5SRC006","SAME_CONCEPT_DIFFERENT_DENOMINATOR","Both phases show that admissibility is part of the robustness result.","Counts have different denominators and reason distributions.","Do not pool rates or recode inadmissibility as non-selection."],
      ["CMP06","QPP-reference selection losses","140 selected-retained and 136 selection-lost against each event's global W00/P00 baseline.","Losses occurred among the reproduced-QPP side of the pilot baseline.","F2SRC001;F2SRC002","295 selected-retained and 171 selection-lost, restricted to baseline-concordant QPP references.","Selection loss persists at catalogue scale among the much smaller reproduced-baseline QPP subset.","F3A5SRC002;F3A5SRC006","SAME_CONCEPT_DIFFERENT_DENOMINATOR","Methodological perturbations can alter retained QPP-reference classifications in both phases.","F3A transitions are conditional on only 8 baseline-concordant published-QPP references.","Do not infer a false-negative rate or claim all published QPPs are fragile."],
      ["CMP07","not-selected-reference selection gains","0 gains against the global W00/P00 baseline; 238 not-selected-retained.","Pilot controls were not physical negatives.","F2SRC001;F2SRC004","0 gains and 3,178 not-selected-retained within baseline-concordant transition-eligible not-selected references.","No gains were observed in the frozen F3A transition denominator.","F3A5SRC002;F3A5SRC006","SAME_CONCEPT_DIFFERENT_DENOMINATOR","No baseline-relative gains were observed in either frozen scope.","These are repeated perturbations of observational references, not independent ground-truth negatives.","Do not state observational FPR = 0."],
      ["CMP08","optimizer classification stability","46 W00 eligible variants; 460 seed decisions; 0 discordant variants.","Binary classification stable across seeds 0–9 in pilot stability scope.","F2SRC001;F2SRC002","116 W00/P00 eligible events; 1,160 seed decisions; 0 discordant events.","Binary classification stable across seeds 0–9 at catalogue scale.","F3A5SRC004;F3A5SRC006","SAME_CONCEPT_DIFFERENT_DENOMINATOR","Seed robustness of binary classification reappears at scale.","The stability scopes are not identical and cannot be pooled.","Do not claim optimizer convergence or universal stability."],
      ["CMP09","numerical multiplicity / warnings / bounds","Each F2 stability variant showed multiple parameter payloads; convergence NOT_AUDITABLE; M1/M2 bounds and M2 warnings were substantial.","Stable classification was explicitly separated from numerical uniqueness.","F2SRC002;F2SRC003","All 116 stability events show 10 unique parameter payloads for M0/M1/M2; convergence remains NOT_AUDITABLE; M2 warnings/bounds remain substantial.","The same classification-versus-numerical distinction persists at scale.","F3A5SRC004;F3A5SRC006","DIRECT_DESIGN_CONTINUITY","stable classification ≠ unique numerical solution in both phases.","Warnings/bounds are diagnostics, not established causes of transitions.","Do not claim a unique optimum or causal warning/bound mechanism."],
      ["CMP10","conditional period robustness","140 selected→selected comparable rows; median absolute change 0.244031 s; maximum 2.714694 s.","Period robustness was conditional on retained selection.","F2SRC001;F2SRC002","295 selected→selected comparable rows; median absolute change ≈0.216363 s; maximum ≈2.714694 s.","F3A retains the same conditioning rule with a larger comparable set.","F3A5SRC005;F3A5SRC006","SAME_CONCEPT_DIFFERENT_DENOMINATOR","Conditional period changes remain small in the selected→selected plane.","Lost selections and inadmissible variants are outside the period denominator.","Do not claim a true period or global period robustness."],
      ["CMP11","overall F2→F3A interpretation","Phase 2 concluded robustness manuscript viable; correction required a separate held-out Phase-3 route.","Pilot evidence supported internal robustness characterization but not validation.","F2SRC006;F2SRC007","F3A provides catalogue-scale observational robustness characterization with a new material baseline-reproduction limitation; validation/correction remain unresolved.","F3A expands robustness evidence but makes F3B more, not less, necessary.","F3A5SRC006;F3A5SRC007","NOT_POOLABLE","The qualitative procedural-sensitivity pattern appears at catalogue scale, subject to different denominators and baseline reproduction.","F3A cannot be reduced to a pooled replication of F2.","Do not write 'F3A proves F2' or 'F3A validates AFINO'."],
    ]
    cmp_fields=["comparison_id","dimension","f2_scope","f2_result","f2_source_artifacts","f3a_scope","f3a_result","f3a_source_artifacts","comparability_status","allowed_synthesis","required_qualification","prohibited_synthesis"]
    write_csv(closure/"f3a6_f2_f3a_comparison_matrix.csv",cmp_fields,[dict(zip(cmp_fields,r)) for r in cmp_rows])

    ledger=[
      ["E3A001","F2_TO_F3A_COMPARISON","The F2 pilot contained 10 events and 5 pairs.","F2SRC001",S["F2SRC001"]["sha256"],"cohort_events; cohort_pairs","F2 pilot scope","Phase 2 was a small observational robustness pilot.","Do not generalize it as a catalogue-scale estimate."],
      ["E3A002","INPUT_ADMISSIBILITY","F2 contained 780 planned variants: 514 eligible and 266 inadmissible.","F2SRC001",S["F2SRC001"]["sha256"],"primary_planned_variants; primary_eligible_variants; primary_inadmissible_variants","F2 primary matrix","Inadmissibility is a separate methodological outcome.","Do not recode 266 as non-selection."],
      ["E3A003","OBSERVATIONAL_REFERENCE_REPRODUCTION","All 10 F2 W00/P00 baseline classifications matched the frozen baseline.","F2SRC001",S["F2SRC001"]["sha256"],"baseline_rows; baseline_classification_mismatches","F2 baseline","The F2 robustness analysis began from an internally reproduced baseline.","Do not infer physical truth."],
      ["E3A004","CLASSIFICATION_ROBUSTNESS","F2 baseline-relative outcomes were 140 selected-retained, 136 selection-lost, 238 not-selected-retained and 0 selection-gained, plus 266 inadmissible.","F2SRC001",S["F2SRC001"]["sha256"],"baseline_comparison_status_counts","F2 repeated perturbations","F2 shows procedural classification sensitivity among reproduced published-QPP references.","Do not call losses false negatives or 0 gains FPR=0."],
      ["E3A005","NUMERICAL_STABILITY","F2 had 46 W00 stability variants, 460 seed decisions and 0 classification-discordant variants.","F2SRC001",S["F2SRC001"]["sha256"],"stability_variants; stability_decisions_seed_0_to_9; stability_decision_discordant_variants","F2 seed scope","Binary classification was stable across seeds 0–9 in the frozen pilot scope.","Do not infer unique optimizer convergence."],
      ["E3A006","PERIOD_ROBUSTNESS","F2 period robustness used 140 selected→selected rows; median absolute change 0.244031 s and maximum 2.714694 s.","F2SRC001",S["F2SRC001"]["sha256"],"period_robustness_rows; period_absolute_change_summary","F2 selected→selected period plane","Period robustness is conditional on retained selection.","Do not extend to losses or inadmissible inputs."],
      ["E3A007","INTERPRETATION_LIMITS","F2 did not establish observational ground truth, AFINO validation, sensitivity, specificity, observational FPR or a validated correction.","F2SRC006",S["F2SRC006"]["sha256"],"formal Phase-2 decision fields","F2 closure","Phase 2 supported a robustness manuscript while reserving correction for a held-out future route.","Do not upgrade prohibited F2 claims retrospectively."],
      ["E3A008","OBSERVATIONAL_REFERENCE_REPRODUCTION","F3A contains 122 events: 61 PUBLISHED_QPP_REFERENCE and 61 PUBLISHED_NOT_SELECTED_REFERENCE.","F3A5SRC001",S["F3A5SRC001"]["sha256"],"122 baseline rows; observational_reference_role","F3A catalogue cohort","F3A is catalogue-scale relative to F2.","Roles remain observational, not physical truth."],
      ["E3A009","INPUT_ADMISSIBILITY","F3A retained all 9,516 planned primary variants: 6,422 eligible and 3,094 inadmissible.","F3A5SRC002",S["F3A5SRC002"]["sha256"],"materialization_status over 9,516 rows","F3A primary matrix","Inadmissibility remains visible in the planned denominator.","Do not recode inadmissible rows as negative classifications."],
      ["E3A010","OBSERVATIONAL_REFERENCE_REPRODUCTION","F3A baseline gate is 65 concordant, 51 reference-baseline mismatch, 6 input-inadmissible and 0 incomplete-numerical.","F3A5SRC001",S["F3A5SRC001"]["sha256"],"baseline_gate_state over 122 rows","F3A baseline gate","Catalogue-scale transition claims must be conditioned on baseline reproduction.","Do not hide the 51 mismatches."],
      ["E3A011","OBSERVATIONAL_REFERENCE_REPRODUCTION","Within PUBLISHED_QPP_REFERENCE: 8 concordant, 51 mismatch and 2 inadmissible.","F3A5SRC001",S["F3A5SRC001"]["sha256"],"role=PUBLISHED_QPP_REFERENCE","F3A QPP-reference baseline","All 51 baseline mismatches are in the published-QPP reference role.","Mismatch is against the frozen observational state, not physical falsity."],
      ["E3A012","OBSERVATIONAL_REFERENCE_REPRODUCTION","Within PUBLISHED_NOT_SELECTED_REFERENCE: 57 concordant, 0 mismatch and 4 inadmissible.","F3A5SRC001",S["F3A5SRC001"]["sha256"],"role=PUBLISHED_NOT_SELECTED_REFERENCE","F3A not-selected baseline","Most not-selected references reproduce their observational state at baseline.","They are not physical true negatives."],
      ["E3A013","CLASSIFICATION_ROBUSTNESS","F3A transition counts are 295 SELECTED_RETAINED, 171 SELECTION_LOST, 3,178 NOT_SELECTED_RETAINED and 0 SELECTION_GAINED.","F3A5SRC002",S["F3A5SRC002"]["sha256"],"classification_transition","F3A baseline-concordant transition scope","Selection losses and retentions are present at catalogue scale.","Do not interpret as sensitivity/specificity/FPR."],
      ["E3A014","CLASSIFICATION_ROBUSTNESS","Every F3A transition row has REFERENCE_CONCORDANT baseline.","F3A5SRC002",S["F3A5SRC002"]["sha256"],"baseline_gate_state on transition rows","F3A transition denominator","Transition interpretation is explicitly conditional on reproduced baseline.","Do not mix mismatch/inadmissible events into transition rates."],
      ["E3A015","NUMERICAL_STABILITY","F3A optimizer scope contains 116 W00/P00 events and 1,160 seed decisions with 0 classification-discordant events.","F3A5SRC004",S["F3A5SRC004"]["sha256"],"116 rows; seed_count; discordant_vs_seed0_count","F3A seed scope","Binary classification is stable across seeds 0–9 in the frozen stability plane.","Do not infer universal optimizer stability."],
      ["E3A016","NUMERICAL_STABILITY","Each F3A stability event has 10 distinct parameter payloads for M0, M1 and M2 across seeds.","F3A5SRC004",S["F3A5SRC004"]["sha256"],"unique_parameter_payloads_m0/m1/m2","F3A seed scope","Classification stability coexists with numerical multiplicity.","Do not claim a unique numerical optimum."],
      ["E3A017","NUMERICAL_STABILITY","F3A convergence remains NOT_AUDITABLE; M2 retains substantial warnings and bounds.","F3A5SRC006",S["F3A5SRC006"]["sha256"],"numerical_diagnostics","F3A numerical diagnostics","Warnings/bounds remain interpretation limits.","Do not claim warnings or bounds cause classification transitions."],
      ["E3A018","PERIOD_ROBUSTNESS","F3A period plane contains 295 selected→selected comparisons; median absolute change is about 0.216363 s and maximum about 2.714694 s.","F3A5SRC005;F3A5SRC006",S["F3A5SRC005"]["sha256"]+";"+S["F3A5SRC006"]["sha256"],"295 rows; frozen period summary in F3A.5","F3A selected→selected period plane","Conditional period robustness persists at catalogue scale.","No true period is established."],
      ["E3A019","F2_TO_F3A_COMPARISON","The same 13×6 perturbation design underlies 780 F2 variants and 9,516 F3A variants.","F2SRC001;F3A5SRC002",S["F2SRC001"]["sha256"]+";"+S["F3A5SRC002"]["sha256"],"frozen planned matrices","Design continuity","F3A is a scale-up of the procedural stress test.","Do not pool denominators across phases."],
      ["E3A020","F2_TO_F3A_COMPARISON","QPP-reference selection losses occur in both F2 and F3A frozen transition scopes.","F2SRC001;F3A5SRC002",S["F2SRC001"]["sha256"]+";"+S["F3A5SRC002"]["sha256"],"F2 and F3A transition tables","Qualitative continuity","Procedural sensitivity appears at catalogue scale.","F3A does not prove F2 or validate AFINO."],
      ["E3A021","F2_TO_F3A_COMPARISON","Neither F2 nor F3A observed a baseline-relative SELECTION_GAINED transition in its frozen not-selected scope.","F2SRC001;F3A5SRC002",S["F2SRC001"]["sha256"]+";"+S["F3A5SRC002"]["sha256"],"global W00/P00 transition tables","Phase-specific observational reference scopes","No gains were observed within each defined scope.","Do not state observational FPR=0."],
      ["E3A022","INTERPRETATION_LIMITS","The cause of the 51 F3A QPP-reference baseline mismatches is unresolved within F3A.","F3A5SRC001;F3A5SRC007",S["F3A5SRC001"]["sha256"]+";"+S["F3A5SRC007"]["sha256"],"baseline mismatch records and F3A.5 limitations","F3A closure","The mismatch is a material methodological limitation requiring explicit reporting.","Do not invent a causal explanation or recode as false detections."],
      ["E3A023","INTERPRETATION_LIMITS","F2 and F3A denominators are not poolable.","F2SRC007;F3A5SRC007",S["F2SRC007"]["sha256"]+";"+S["F3A5SRC007"]["sha256"],"phase scopes and repeated-measures denominators","Cross-phase synthesis","Only qualitative/documentary comparison is permitted.","Do not calculate pooled rates, p-values or confidence intervals."],
      ["E3A024","INTERPRETATION_LIMITS","F3A does not establish observational ground truth, AFINO validation, sensitivity, specificity, observational FPR, correction or selection function.","F3A5SRC006",S["F3A5SRC006"]["sha256"],"scientific_boundaries","Phase-3A claim boundary","Robustness characterization is supported while performance validation remains open.","Do not imply validation from catalogue scale alone."],
      ["E3A025","INTERPRETATION_LIMITS","The robustness component of Manuscript 1 is supported; its validation/correction component is incomplete.","F2SRC006;F3A5SRC006",S["F2SRC006"]["sha256"]+";"+S["F3A5SRC006"]["sha256"],"Phase-2 route decision + F3A scientific boundaries","Manuscript planning","A robustness manuscript component is defensible with explicit limitations.","Do not present the manuscript as complete validation."],
      ["E3A026","INTERPRETATION_LIMITS","F3B is required for known ground truth, injection–recovery, development/held-out separation and validation of any correction or selection function.","F2SRC006;F2SRC007;F3A5SRC006",S["F2SRC006"]["sha256"]+";"+S["F2SRC007"]["sha256"]+";"+S["F3A5SRC006"]["sha256"],"held-out requirement and unresolved F3A validation claims","Entry to F3B","Phase 3A may close while validation continues in F3B.","Do not reuse F2/F3A observational events as independent held-out validation."],
      ["E3A027","INTERPRETATION_LIMITS","Candidate discovery remains outside the Phase-3A closure and F3B validation-design scope.","F2SRC006;F3A5SRC006",S["F2SRC006"]["sha256"]+";"+S["F3A5SRC006"]["sha256"],"candidate_discovery flags","Scope control","Closure and validation design remain separate from discovery.","Do not authorize candidate search by implication."],
    ]
    led_fields=["evidence_id","evidence_plane","claim","source_artifact","source_sha256","source_rows_or_locator","scope","allowed_interpretation","prohibited_interpretation"]
    write_csv(closure/"f3a6_phase3a_evidence_ledger.csv",led_fields,[dict(zip(led_fields,r)) for r in ledger])

    claims=[
      ["F3A001","122 observational reference events were evaluated under the frozen catalogue-scale design.","SUPPORTED_NOW","E3A008","Catalogue-scale observational cohort only.","F3A evaluated 122 observational reference events under the frozen design.","F3A evaluated 122 ground-truth events.",""],
      ["F3A002","The primary analysis retained all 9516 planned variants, including 3094 inadmissible inputs.","SUPPORTED_NOW","E3A009","Inadmissibility is not non-selection.","All 9,516 planned variants remain represented, including 3,094 inadmissible inputs.","The 3,094 inadmissible inputs were negative classifications.",""],
      ["F3A003","65/122 events reproduced their frozen observational reference state at W00/P00/seed0.","SUPPORTED_WITH_EXPLICIT_LIMITATION","E3A010","Also disclose 51 mismatches and 6 inadmissible baselines.","65 of 122 events were baseline-concordant; the remaining baseline states are reported separately.","Most published QPPs reproduced at baseline.",""],
      ["F3A004","51/61 PUBLISHED_QPP_REFERENCE events were REFERENCE_BASELINE_MISMATCH.","SUPPORTED_WITH_EXPLICIT_LIMITATION","E3A011;E3A022","Mismatch is against the frozen reference state, not physical falsity.","51 of 61 published-QPP references did not reproduce their frozen observational state at F3A baseline.","51 published QPP detections were false.",""],
      ["F3A005","Among PUBLISHED_NOT_SELECTED_REFERENCE events: 57 were baseline concordant, 0 mismatched and 4 inadmissible.","SUPPORTED_WITH_EXPLICIT_LIMITATION","E3A012","Not-selected references are not physical negatives.","The not-selected role had 57 concordant, 0 mismatch and 4 inadmissible baselines.","57 true negatives were reproduced.",""],
      ["F3A006","Catalogue-scale QPP-reference transitions include both selection retention and selection loss.","SUPPORTED_WITH_EXPLICIT_LIMITATION","E3A013;E3A014","Restricted to baseline-concordant transition-eligible QPP references.","Catalogue-scale QPP-reference transitions include retained selections and losses.","Published QPPs have a measured false-negative rate.",""],
      ["F3A007","No SELECTION_GAINED transitions occurred within the baseline-concordant, transition-eligible not-selected scope.","SUPPORTED_WITH_EXPLICIT_LIMITATION","E3A013;E3A014","Repeated perturbations of observational references; not ground-truth negatives.","No baseline-relative gains occurred in the defined not-selected transition scope.","The observational false-positive rate is zero.",""],
      ["F3A008","F3A007 does not establish an observational false-positive rate.","SUPPORTED_NOW","E3A021;E3A024","No independent observational ground truth exists.","Zero gains in the frozen scope are not an observational FPR estimate.","FPR=0.",""],
      ["F3A009","116/116 W00/P00 eligible events were classification-stable across seeds 0–9.","SUPPORTED_NOW","E3A015","Restricted to the frozen W00/P00 seed grid.","All 116 eligible W00/P00 events retained binary classification across seeds 0–9.","The optimizer is universally stable.",""],
      ["F3A010","Classification stability does not imply a unique numerical optimum.","SUPPORTED_NOW","E3A016;E3A017","Convergence is not auditable and parameter payloads differ.","Stable classification is distinct from numerical uniqueness.","Classification stability proves a unique optimum.",""],
      ["F3A011","Numerical multiplicity remains present despite binary classification stability.","SUPPORTED_WITH_EXPLICIT_LIMITATION","E3A016;E3A017","Different parameter payloads are numerical diagnostics, not proved distinct physical optima.","Ten parameter payloads per model coexist with stable binary classification.","Ten physical optima were found.",""],
      ["F3A012","Period robustness is conditional on retained selection and comprises 295 comparable rows.","SUPPORTED_WITH_EXPLICIT_LIMITATION","E3A018","Selected→selected only; lost/inadmissible cases excluded by design.","The period plane contains 295 selected→selected comparable rows.","Period was robust for all planned variants.",""],
      ["F3A013","The qualitative procedural-sensitivity pattern observed in F2 is also present at catalogue scale, subject to different denominators and baseline reproduction.","SUPPORTED_WITH_EXPLICIT_LIMITATION","E3A020;E3A023","Do not pool F2/F3A and disclose the 51/61 QPP baseline mismatch limitation.","Procedural sensitivity appears both in the pilot and at catalogue scale.","F3A proves F2.",""],
      ["F3A014","F2 and F3A denominators must not be pooled.","SUPPORTED_NOW","E3A023","Documentary comparison only.","F2 and F3A are compared qualitatively without pooled rates.","Pooled F2+F3A robustness rate.",""],
      ["F3A015","AFINO has not been observationally validated.","SUPPORTED_NOW","E3A007;E3A024","Robustness characterization is not performance validation.","Phase 3A does not establish observational validation of AFINO.","AFINO is observationally validated.","F3B validation program"],
      ["F3A016","Sensitivity, specificity and observational FPR are not established.","SUPPORTED_NOW","E3A007;E3A024","No independent observational ground truth.","No sensitivity, specificity or observational FPR claim is established.","Sensitivity/specificity/FPR are now known.","F3B known-ground-truth validation"],
      ["F3A017","Physical QPP truth is not established.","SUPPORTED_NOW","E3A007;E3A024","Observational roles are reference states only.","F3A does not establish physical QPP truth.","51 mismatches disprove physical QPPs.","Independent physical evidence outside F3A"],
      ["F3A018","A validated correction / selection function requires F3B.","REQUIRES_F3B","E3A026","Freeze development/held-out architecture before execution.","Correction/selection-function validation is deferred to F3B.","F3A already validated a correction.","F3B injection–recovery + held-out"],
      ["F3A019","Manuscript 1 retains a supported robustness component, while its validation/correction component remains pending F3B.","SUPPORTED_WITH_EXPLICIT_LIMITATION","E3A025;E3A026","Keep robustness and validation components distinct.","Manuscript 1 can retain the robustness component while validation remains pending.","Manuscript 1 is fully validated.","F3B"],
      ["F3A020","F3A proves F2.","PROHIBITED","E3A023","Different denominators and a new baseline limitation prevent that synthesis.","F3A extends the procedural stress test and shows a related qualitative pattern.","F3A proves F2.",""],
      ["F3A021","The observational false-positive rate is zero.","PROHIBITED","E3A021;E3A024","SELECTION_GAINED=0 is not a ground-truth performance metric.","No gains were observed in the defined observational-reference scope.","Observational FPR=0.",""],
      ["F3A022","The 51 QPP-reference baseline mismatches are false QPP detections.","PROHIBITED","E3A011;E3A022","Mismatch is against frozen reference state; cause and physical truth unresolved.","The 51 mismatches are a baseline-reproduction limitation.","51 false QPP detections.",""],
      ["F3A023","Catalogue scale validates AFINO.","PROHIBITED","E3A024;E3A026","Scale-up without ground truth is not validation.","Catalogue scale characterizes observational robustness and limitations.","Catalogue scale validates AFINO.","F3B"],
    ]
    claim_fields=["claim_id","claim","status","evidence_ids","required_qualification","allowed_wording","prohibited_wording","phase3b_dependency"]
    write_csv(closure/"f3a6_claim_matrix.csv",claim_fields,[dict(zip(claim_fields,r)) for r in claims])

    limitations=[
      ["L3A001","INTERPRETATION_LIMITS","Observational labels are not physical or observational ground truth.","F3A004;F3A005;F3A008;F3A015;F3A016;F3A017","Use reference-state terminology and keep performance metrics prohibited.","Performance interpretation remains blocked.","Robustness manuscript must avoid ground-truth language.","Known-ground-truth validation required."],
      ["L3A002","OBSERVATIONAL_REFERENCE_REPRODUCTION","51/61 published-QPP references are baseline mismatches.","F3A003;F3A004;F3A006;F3A013","Condition F3A transitions on REFERENCE_CONCORDANT baseline and report role split.","Major baseline-reproduction limitation remains.","Central limitation in abstract/results/discussion.","Represent baseline mismatch explicitly in F3B design."],
      ["L3A003","OBSERVATIONAL_REFERENCE_REPRODUCTION","6/122 events are baseline-input inadmissible.","F3A003;F3A005","Keep inadmissibility separate from mismatch and non-selection.","Baseline scope is incomplete for six events.","Report denominator explicitly.","Represent relevant inadmissibility regimes in F3B."],
      ["L3A004","CLASSIFICATION_ROBUSTNESS","Transition denominators are conditional on baseline reproduction.","F3A006;F3A007;F3A013","Only REFERENCE_CONCORDANT rows enter transition claims.","Transition counts are not population performance rates.","Describe conditional denominator.","Define prospective ground-truth metrics separately."],
      ["L3A005","OBSERVATIONAL_REFERENCE_REPRODUCTION","Only 8/61 QPP-reference events are baseline concordant.","F3A004;F3A006;F3A013","State the QPP baseline subset before discussing losses/retention.","Catalogue-scale QPP transition evidence is narrower than the published-QPP set.","Avoid generalization to all published QPP references.","Ground-truth validation must not rely on published labels."],
      ["L3A006","OBSERVATIONAL_REFERENCE_REPRODUCTION","57 not-selected references are baseline concordant but are not physical negatives.","F3A005;F3A007;F3A008","Use observational-reference language only.","Performance specificity/FPR remain unavailable.","No true-negative terminology.","Use known negatives/synthetic truth in F3B."],
      ["L3A007","INPUT_ADMISSIBILITY","3,094/9,516 planned variants are input-inadmissible.","F3A002;F3A013","Keep all planned variants visible and separate inadmissibility from classification.","Eligible denominators depend on structural input conditions.","Publish counts/reasons.","Represent gap/quality regimes where relevant."],
      ["L3A008","CLASSIFICATION_ROBUSTNESS","The 78 cells are repeated measures within events.","F3A006;F3A007;F3A013;F3A014","Do not treat variant rows as independent events.","Simple pooled inferential rates are invalid.","Keep event as repeated-measure unit.","Use appropriate prospective validation unit."],
      ["L3A009","INTERPRETATION_LIMITS","No formal hypothesis tests were preregistered or performed in F3A.","F3A013","Keep conclusions descriptive.","No inferential significance claim.","No p-values in Manuscript 1 robustness result.","Define F3B metrics prospectively."],
      ["L3A010","INTERPRETATION_LIMITS","No robustness threshold was preregistered.","F3A002;F3A013","Do not label events robust/not-robust post hoc.","No binary robustness classifier exists.","Use descriptive distributions.","Any future rule must be frozen before held-out access."],
      ["L3A011","NUMERICAL_STABILITY","Seed analysis is restricted to W00/P00 input-eligible events.","F3A009;F3A010;F3A011","State seed-scope restriction.","Seed result does not cover all 78 cells.","Restrict optimizer claims.","Retain numerical stability as a separate F3B plane."],
      ["L3A012","NUMERICAL_STABILITY","Classification stability does not establish a unique optimum.","F3A010;F3A011","Report parameter multiplicity and convergence limit.","Numerical uniqueness remains unresolved.","No unique-optimum language.","Add explicit convergence/multiplicity diagnostics if needed."],
      ["L3A013","NUMERICAL_STABILITY","Numerical convergence remains NOT_AUDITABLE.","F3A010;F3A011","Do not equate stable classification with demonstrated convergence.","Optimizer convergence claim unavailable.","Keep limitation explicit.","Instrument convergence prospectively if required."],
      ["L3A014","NUMERICAL_STABILITY","M2 warnings and bounds remain substantial at catalogue scale.","F3A011","Treat as diagnostics only.","Potential numerical fragility is not causally attributed.","Report without causal claim.","Investigate only in separate preregistered analysis if needed."],
      ["L3A015","PERIOD_ROBUSTNESS","Period analysis is selected→selected only.","F3A012","Condition every period claim on retained selection.","No period inference for lost/inadmissible cases.","State 295-row conditional scope.","Separate period recovery from classification in F3B."],
      ["L3A016","INTERPRETATION_LIMITS","F3A uses a single primary catalogue/source.","F3A001;F3A013","Restrict external generalization.","Source-specific limitations remain.","Avoid universal catalogue claims.","Use independent validation sources where appropriate."],
      ["L3A017","INTERPRETATION_LIMITS","Results are implementation-specific to frozen AFINO 0.5.","F3A009;F3A015;F3A018","Bind claims to the frozen implementation.","Other versions/configurations are untested.","State implementation identity.","Retain AFINO 0.5 baseline for F3B comparison."],
      ["L3A018","F2_TO_F3A_COMPARISON","No BAII external comparator was executed in F3A.","F3A013;F3A018","Keep F3A primary method only.","Comparator-based validation remains absent.","Do not imply comparative superiority.","Resolve deferred comparator decisions before F3B execution."],
      ["L3A019","F2_TO_F3A_COMPARISON","F2 and F3A denominators are not poolable.","F3A013;F3A014","Use documentary comparison only.","No pooled rate or inferential combined estimate.","Keep phases separated.","F3B uses its own prospective denominators."],
      ["L3A020","INTERPRETATION_LIMITS","Physical inference remains outside F3A.","F3A004;F3A017","Separate observational-reference robustness from physical interpretation.","Physical QPP truth unresolved.","No physical falsity/confirmation claim.","Physical validation would require separate evidence."],
      ["L3A021","OBSERVATIONAL_REFERENCE_REPRODUCTION","The cause of the 51 QPP-reference baseline mismatches is UNRESOLVED_WITHIN_F3A.","F3A004;F3A013","Do not invent a post-hoc explanation.","Mechanistic source of mismatch remains unknown.","State unresolved cause.","F3B should avoid using published label as truth and may stratify relevant regimes."],
      ["L3A022","INTERPRETATION_LIMITS","Candidate discovery remained outside F3A.","F3A001;F3A018","Keep robustness/validation separate from search.","No discovery performance evidence.","Do not imply candidate-finding capability.","Candidate discovery remains outside initial F3B validation scope."],
    ]
    lim_fields=["limitation_id","evidence_plane","description","affected_claims","mitigation","remaining_risk","manuscript1_implication","f3b_implication"]
    write_csv(closure/"f3a6_limitations_register.csv",lim_fields,[dict(zip(lim_fields,r)) for r in limitations])

    reqs=[
      ["F3BR001","GROUND_TRUTH","Use known synthetic ground truth for classification validation.","F3A016;F3A017;L3A001","true","true","Treat published observational labels as physical truth.","OPEN_FOR_F3B_DESIGN"],
      ["F3BR002","SIMULATION_REALISM","Freeze realistic flare/background/noise generation assumptions.","L3A016;L3A020","true","true","Tune generators after held-out results.","OPEN_FOR_F3B_DESIGN"],
      ["F3BR003","INJECTION_DOMAIN","Predefine injection–recovery parameter domain and sampling.","F3A018;L3A010","true","true","Choose domain after seeing validation outcomes.","OPEN_FOR_F3B_DESIGN"],
      ["F3BR004","DATA_SPLIT","Freeze a development dataset before rule development.","F3A018;E3A026","true","true","Use held-out examples during development.","OPEN_FOR_F3B_DESIGN"],
      ["F3BR005","DATA_SPLIT","Freeze an independent held-out dataset separately.","F3A018;E3A026","true","true","Reuse development data as confirmation.","OPEN_FOR_F3B_DESIGN"],
      ["F3BR006","DATA_SPLIT","Enforce development/held-out separation operationally.","F3A018;E3A026","true","true","Manual informal separation without audit.","OPEN_FOR_F3B_DESIGN"],
      ["F3BR007","RULE_FREEZE","Freeze the final classification/correction rule before held-out access.","F3A018;L3A010","true","true","Post-hoc threshold or rule adjustment on held-out data.","OPEN_FOR_F3B_DESIGN"],
      ["F3BR008","METRICS","Define classification metrics prospectively under known ground truth.","F3A016","true","true","Back-calculate metrics from observational reference roles.","OPEN_FOR_F3B_DESIGN"],
      ["F3BR009","SELECTION_FUNCTION","Define prospective selection-function characterization.","F3A018;L3A007","true","true","Infer selection function from F3A repeated observational perturbations.","OPEN_FOR_F3B_DESIGN"],
      ["F3BR010","PERIOD","Separate period-recovery metrics from classification metrics.","F3A012;L3A015","true","true","Use formal M1 centers from non-selected cases as recovered periods.","OPEN_FOR_F3B_DESIGN"],
      ["F3BR011","BASELINE","Retain frozen AFINO 0.5 as the baseline comparator.","L3A017","true","true","Silently change baseline implementation.","OPEN_FOR_F3B_DESIGN"],
      ["F3BR012","COMPARATORS","Resolve BAII-deferred comparator decisions before execution.","L3A018","true","true","Add comparators after observing F3B outcomes.","OPEN_FOR_F3B_DESIGN"],
      ["F3BR013","ADMISSIBILITY","Represent F3A inadmissibility/gap regimes where scientifically relevant.","L3A003;L3A007","false","true","Ignore structural input regimes revealed by F3A.","OPEN_FOR_F3B_DESIGN"],
      ["F3BR014","LABEL_POLICY","Do not use published observational labels as physical truth.","F3A004;F3A005;F3A017;L3A001","true","true","Treat PUBLISHED_QPP_REFERENCE as positive ground truth.","OPEN_FOR_F3B_DESIGN"],
      ["F3BR015","INDEPENDENCE","Do not reuse F2/F3A observational events as independent held-out validation.","E3A026;L3A019","true","true","Validate a new rule on the same events that motivated it.","OPEN_FOR_F3B_DESIGN"],
      ["F3BR016","NUMERICAL_STABILITY","Retain numerical stability as a separate evidence plane.","F3A009;F3A010;F3A011","false","true","Collapse seed/numerical behavior into classification accuracy.","OPEN_FOR_F3B_DESIGN"],
      ["F3BR017","DISCOVERY_SCOPE","Keep candidate discovery outside the initial F3B validation scope.","E3A027;L3A022","false","true","Search new observational candidates before validation architecture is frozen.","OPEN_FOR_F3B_DESIGN"],
      ["F3BR018","SUCCESS_CRITERIA","Freeze F3B success/failure and promotion criteria before execution.","F3A018;E3A026","true","true","Declare success after inspecting held-out performance.","OPEN_FOR_F3B_DESIGN"],
    ]
    req_fields=["requirement_id","requirement_category","requirement","evidence_basis","blocking_for_f3b_validation","must_freeze_before_execution","prohibited_shortcut","status"]
    write_csv(closure/"f3a6_phase3b_entry_requirements.csv",req_fields,[dict(zip(req_fields,r)) for r in reqs])

    # Decision is derived after the consistency gates above.
    phase_status = (
      "PHASE3A_COMPLETE_PROCEED_TO_F3B_WITH_LIMITATIONS"
      if bcnt==EXPECTED_BASELINE and qpp==EXPECTED_QPP_BASELINE and ctl==EXPECTED_CONTROL_BASELINE
      and trans==EXPECTED_TRANSITIONS and f2trans==EXPECTED_F2_TRANSITIONS
      else "PHASE3A_CLOSURE_BLOCKED"
    )
    decision={
      "phase":"Phase 3A",
      "phase_status":phase_status,
      "f2_f3a_comparison_completed":True,
      "catalogue_scale_robustness_characterized":True,
      "baseline_reproduction_limitation_material":True,
      "baseline_qpp_reference_mismatch_count":51,
      "classification_sensitivity_observed_at_catalogue_scale":True,
      "not_selected_reference_gains_observed":False,
      "optimizer_binary_classification_stable":True,
      "unique_optimum_established":False,
      "period_robustness_conditional":True,
      "observational_ground_truth_established":False,
      "afino_observationally_validated":False,
      "sensitivity_established":False,
      "specificity_established":False,
      "observational_fpr_established":False,
      "correction_claim_established":False,
      "selection_function_established":False,
      "manuscript1_robustness_component_supported":True,
      "manuscript1_validation_component_complete":False,
      "f3b_required":True,
      "candidate_discovery_authorized":False,
      "recommended_next_task":"F3B.1 — preregister injection–recovery, development/held-out split and validation architecture before generating any injection.",
      "decision_basis":[
        "F2 established a 10-event procedural-robustness pilot with baseline reproduction, classification losses, explicit inadmissibility, stable binary classification across seeds and no observational validation claim.",
        "F3A retained the same frozen 13×6 stress-test structure at 122-event catalogue scale and preserved all 9,516 planned variants.",
        "F3A reproduced only 65/122 frozen observational reference states at baseline; all 51 baseline mismatches occurred in PUBLISHED_QPP_REFERENCE and their cause remains unresolved within F3A.",
        "Among baseline-concordant transition-eligible rows, F3A contains 295 selected-retained, 171 selection-lost, 3,178 not-selected-retained and 0 selection-gained transitions.",
        "F3A seed classification is stable in 116/116 W00/P00 input-eligible events, while parameter multiplicity and non-auditable convergence prevent a unique-optimum claim.",
        "Neither F2 nor F3A establishes ground truth, sensitivity, specificity, observational FPR, observational validation, a correction claim or a selection function.",
        "Known-ground-truth injection–recovery with frozen development/held-out separation is therefore required in F3B."
      ]
    }
    (closure/"f3a6_phase3a_decision.json").write_text(json.dumps(decision,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")

    report = """# F3A.6 — Phase 3A synthesis and closure

## 1. Scientific role of Phase 3A

Phase 3A was designed as a catalogue-scale extension of the observational robustness question established in the Phase-2 pilot. Its purpose was not to decide whether AFINO is physically correct, nor to convert published QPP labels into ground truth. The defensible question is procedural: when an observational reference state is frozen in advance, how often does the binary classification remain the same under prospectively specified changes of temporal window and processing, which inputs become structurally inadmissible, what numerical stability is observed across optimizer seeds, and how stable is the recovered period when selection itself survives? The closure therefore keeps reference reproduction, input admissibility, classification robustness, numerical behavior and conditional period robustness as separate evidence planes.

F2 and F3A answer related questions at different scales. F2 was a ten-event pilot with five pairs. F3A expands the experiment to 122 observational reference events divided symmetrically into 61 published-QPP references and 61 not-selected references. This larger scope supports a stronger statement about the existence of procedural classification sensitivity at catalogue scale, but it does not create an observational validation dataset. The labels remain observational reference states, repeated perturbations remain nested within events, and no physical truth class is established.

## 2. Continuity from the F2 pilot

The strongest continuity is in design. F2 froze thirteen temporal windows and six processing profiles, creating 780 planned variants across ten events. F3A inherited the same 78-cell perturbation structure and applied it to 122 events, yielding 9,516 planned variants. Both phases kept inadmissible inputs visible rather than silently converting them into negative classifications. In F2, 514 variants were eligible and 266 inadmissible. In F3A, 6,422 were eligible and 3,094 inadmissible. These denominators are not poolable, but the methodological principle is identical: inadmissibility is part of the outcome of the stress test.

F2 also established the qualitative pattern that motivated scaling. Its ten W00/P00 baseline classifications reproduced the frozen baseline without classification mismatch. Relative to those baselines, the pilot recorded 140 selected-retained variants, 136 selection losses, 238 not-selected-retained variants and no baseline-relative selection gains, with 266 inadmissible variants kept separate. The correct interpretation was already narrow: published classifications could change under frozen methodological perturbations, while the matched not-selected role did not gain selection against the global baseline in that pilot. F2 explicitly prohibited reading these transitions as false negatives, true negatives or an observational false-positive rate.

## 3. Catalogue-scale baseline reproduction

The largest material change from F2 appears before the perturbation analysis itself. At F3A baseline, only 65 of 122 events reproduce their frozen observational reference state. Fifty-one are `REFERENCE_BASELINE_MISMATCH`, six are `INPUT_INADMISSIBLE`, and none is numerically incomplete. The role split is essential. Among the 61 `PUBLISHED_QPP_REFERENCE` events, only eight are baseline concordant, 51 are baseline mismatches and two are baseline-input inadmissible. Among the 61 `PUBLISHED_NOT_SELECTED_REFERENCE` events, 57 are concordant, none is a baseline mismatch and four are inadmissible.

All 51 baseline mismatches therefore arise in the published-QPP reference role. This is the central new limitation exposed by catalogue scale. It is not evidence that 51 published detections are physically false. It says that, under the frozen F3A W00/P00/seed0 implementation and input contract, those 51 events do not reproduce the frozen observational reference state. The cause is `UNRESOLVED_WITHIN_F3A`; the closure does not invent a mechanistic explanation. This limitation means that F3A cannot be presented as a simple replication of the F2 pilot, whose ten baseline states were reproduced.

## 4. Input admissibility

Input admissibility remains an independent methodological result. F3A preserves the full denominator of 9,516 planned variants even though 3,094 are inadmissible. The remaining 6,422 variants provide executable primary decisions. The distinction matters because an inadmissible input contains no valid negative decision and cannot be used as a zero in a selection fraction. The same principle was already present in F2, but catalogue scale reveals a substantially larger absolute burden and a broader set of structural reasons.

The closure therefore treats admissibility as part of the procedure's operating domain rather than as a nuisance to remove. This has direct implications for F3B: injection–recovery should represent relevant gap, quality and cadence regimes prospectively where scientifically appropriate, while preserving an explicit policy for cases that violate the input contract. It must not learn a correction by reclassifying F3A inadmissible rows after the fact.

## 5. Classification robustness

F3A transition claims are calculated only when the event baseline is `REFERENCE_CONCORDANT`. Within that restricted, transition-eligible scope, the catalogue-scale matrix contains 295 `SELECTED_RETAINED` transitions, 171 `SELECTION_LOST` transitions, 3,178 `NOT_SELECTED_RETAINED` transitions and no `SELECTION_GAINED` transitions. Every transition row satisfies the concordant-baseline gate.

The QPP-reference result reproduces the qualitative procedural-sensitivity pattern seen in F2: retained selections and selection losses coexist under prospectively frozen perturbations. This supports the statement that methodological choices can alter binary QPP classification among references whose baseline state is reproduced. It does not support a false-negative rate, because the QPP-reference label is not physical ground truth and the transition rows are repeated perturbations within a restricted subset.

Likewise, zero `SELECTION_GAINED` transitions in the not-selected reference scope is not an observational false-positive rate of zero. The denominator is a set of repeated perturbations of baseline-concordant observational references, not an independently labeled negative population. F2 made the same interpretive distinction, and F3A preserves it at larger scale.

## 6. Numerical stability

The optimizer stability plane contains 116 W00/P00 input-eligible events and 1,160 decisions across seeds zero through nine. All 116 events preserve their binary classification across the frozen seed grid; no event is seed-discordant. This is strong evidence that the binary decision is stable to the external optimizer seed within this specific stability scope.

At the same time, every event has ten distinct parameter payloads for each of M0, M1 and M2. Convergence remains `NOT_AUDITABLE`, and M2 continues to show substantial warnings and bound contacts. These facts make the correct numerical conclusion explicit: stable classification is not the same as a unique numerical solution. F3A therefore strengthens confidence in seed stability of the binary output without establishing unique optimizer convergence or a single privileged parameter solution.

## 7. Conditional period robustness

The period plane remains conditioned on retained selection. F3A contains 295 comparable rows for which the baseline is concordant and selected, the perturbed variant is selected, and both recovered M1 periods are finite. Within this restricted population, the absolute period change has a median of approximately 0.216363 s and a maximum of approximately 2.714694 s.

This result is consistent in form with F2, which contained 140 selected-to-selected comparisons with a median absolute change of 0.244031 s and a maximum of 2.714694 s. The two denominators must not be pooled and the similarity of the maxima is not interpreted inferentially. The scientifically defensible claim is simply that conditional period robustness remains observable when classification survives. Lost selections and inadmissible inputs remain outside the recovered-period denominator, and no “true period” is established.

## 8. What F3A reproduces from F2

F3A reproduces several qualitative features of the pilot. The same prospectively frozen 13×6 stress-test logic remains operational at much larger scale. Input inadmissibility remains scientifically relevant and distinct from non-selection. QPP-reference classifications can be retained or lost under frozen methodological perturbations. Baseline-relative gains are absent in the respective not-selected reference scopes. Binary classification remains stable across the frozen optimizer-seed grid while numerical parameter payloads vary. Period robustness remains conditional on retained selection.

These points support continuity of the methodological robustness story. They do not mean that F3A “proves F2.” The phases use different observational populations, different denominators and, most importantly, different baseline-reproduction behavior. The synthesis is therefore documentary and qualitative, not a pooled statistical analysis.

## 9. What materially changes from F2

The decisive change is the baseline gate. F2 entered robustness with ten of ten frozen baseline classifications reproduced. F3A instead finds only 65 concordant baseline events, alongside 51 mismatches and six inadmissible baselines. The mismatch is entirely concentrated in the published-QPP reference role, where only eight of 61 references are concordant. This makes the catalogue-scale QPP transition denominator far narrower than the published-QPP reference set itself.

That limitation changes the emphasis of the project. F3A still demonstrates catalogue-scale procedural sensitivity within reproduced baselines, but the more important methodological lesson is that baseline reproduction itself cannot be assumed when scaling. The closure therefore treats baseline reproduction as a first-class gate rather than as an administrative precondition.

## 10. Interpretation boundaries

Phase 3A does not establish observational ground truth, physical QPP truth, AFINO observational validation, sensitivity, specificity or observational FPR. It introduces no formal hypothesis test and no post-hoc robustness threshold. It does not establish a correction claim or a selection function. Candidate discovery remains outside scope. The absence of selection gains cannot be promoted into a performance metric, and the 51 QPP-reference mismatches cannot be promoted into false-detection counts.

Warnings, bounds and parameter multiplicity are numerical diagnostics, not demonstrated causes of classification change. Similarly, catalogue scale alone does not transform observational-reference labels into validated classes. These boundaries are not weaknesses to hide; they define exactly what evidence F3A supplies and what evidence must be created elsewhere.

## 11. Manuscript 1 implications

The robustness component of Manuscript 1 remains supported. A methods-and-results narrative can document the frozen perturbation design, explicit inadmissibility, baseline-gated transitions, seed stability, numerical multiplicity and conditional period behavior. The new catalogue-scale baseline limitation should be central rather than buried: 51 of 61 published-QPP references fail to reproduce their frozen reference state under the F3A baseline, while 57 of 61 not-selected references are concordant.

The validation/correction component is not complete. Manuscript wording must therefore separate “robustness characterization” from “validated performance.” F3A can support claims about procedural sensitivity and operating-domain limitations; it cannot support claims about true-positive or false-positive behavior.

## 12. Why F3B remains necessary

F3B is required to move from observational robustness to performance under known truth. The next program must freeze a realistic injection–recovery domain, separate development from held-out validation, define classification metrics prospectively, keep period recovery separate from classification, retain AFINO 0.5 as the baseline, and resolve deferred comparator decisions before execution. Any correction or selection function must be frozen before held-out access.

Published observational labels must not be used as physical truth, and the F2/F3A events that motivated the analysis must not be reused as independent held-out confirmation. Numerical stability remains a separate evidence plane. Candidate discovery remains outside the initial validation program.

## 13. Phase 3A closure decision

The evidence supports `PHASE3A_COMPLETE_PROCEED_TO_F3B_WITH_LIMITATIONS`. Phase 3A has completed its catalogue-scale robustness objective: it shows at catalogue scale that frozen methodological perturbations can alter retained QPP-reference classifications among baseline-reproduced references, while also revealing a material baseline-reproduction limitation in the published-QPP reference set. It does not complete observational validation or correction.

The next task is F3B.1: preregister the injection–recovery program, freeze the development/held-out split and validation architecture, define success criteria and metrics, and resolve comparator policy before generating a single injection. Phase 3A closes with a supported robustness component, explicit limitations and a clearly bounded handoff to validation under known ground truth.
"""
    # word count is intentionally validated, not hard-coded.
    wc=len(report.split())
    if not 1400 <= wc <= 1900: raise RuntimeError(f"Report word count {wc} outside 1400-1900")
    (closure/"f3a6_phase3a_synthesis_report.md").write_text(report,encoding="utf-8",newline="\n")

    closure_readme=f"""# Phase 3A closure — F3A.6

Status: `PHASE3A_COMPLETE_PROCEED_TO_F3B_WITH_LIMITATIONS`

Validation target: `PHASE3A_CLOSURE_VALIDATION_PASS`

This directory is exclusively documentary. It binds frozen F2/F3A sources, compares
F2→F3A without pooling denominators, maps factual evidence and claims, records
limitations, defines F3B entry requirements, and stores the formal Phase-3A decision.

No AFINO execution, FITS/NPY/SQLite access, new scientific statistics, figures,
thresholds or hypothesis tests are authorized in F3A.6.

The material catalogue-scale limitation is preserved: 51/61
`PUBLISHED_QPP_REFERENCE` events are `REFERENCE_BASELINE_MISMATCH`. Their cause is
`UNRESOLVED_WITHIN_F3A`; this state is not physical falsity.

Next task after approved closure: F3B.1 prereregistration of injection–recovery,
development/held-out separation, and validation architecture.
"""
    (closure/"README.md").write_text(closure_readme,encoding="utf-8",newline="\n")

    dr=f"""# DR-005 — Phase 3A closure and F3B entry

**Status:** Accepted
**Date:** 2026-08-13

## Decision

`PHASE3A_COMPLETE_PROCEED_TO_F3B_WITH_LIMITATIONS`

## F2→F3A continuity

The frozen 13×6 observational robustness experiment scales from the 10-event F2
pilot to the 122-event F3A catalogue cohort. Both phases preserve inadmissibility
as a separate outcome, show baseline-relative QPP-reference selection losses,
and show seed-stable binary classification in their frozen optimizer scopes.

## F3A baseline-reproduction limitation

F3A baseline reproduction is 65 concordant, 51 mismatch and 6 inadmissible. All
51 mismatches are in `PUBLISHED_QPP_REFERENCE`: 8 concordant / 51 mismatch / 2
inadmissible. The mismatch is against the frozen observational reference state;
its cause is `UNRESOLVED_WITHIN_F3A` and it is not evidence of 51 false QPPs.

## Robustness conclusion

Among baseline-concordant transition-eligible rows, F3A contains 295
`SELECTED_RETAINED`, 171 `SELECTION_LOST`, 3,178 `NOT_SELECTED_RETAINED` and 0
`SELECTION_GAINED`. Zero gains do not establish observational FPR=0.

## Numerical conclusion

116/116 W00/P00 input-eligible events retain binary classification across seeds
0–9, while each event has 10 parameter payloads for M0/M1/M2 and convergence
remains `NOT_AUDITABLE`. Stable classification does not establish a unique optimum.

## Period conclusion

Period robustness is conditional on retained selection and contains 295
selected→selected comparable rows.

## What F3A establishes

Catalogue-scale descriptive evidence of classification sensitivity to frozen
methodological perturbations, explicit input-admissibility limits, seed-stable
binary decisions in the frozen stability plane, and conditional period robustness.

## What F3A does not establish

Ground truth, physical QPP truth, observational validation of AFINO, sensitivity,
specificity, observational FPR, a validated correction, a selection function or
candidate-discovery performance.

## Manuscript 1 status

The robustness component is supported with explicit limitations. The
validation/correction component remains incomplete.

## Why F3B is required

F3B must introduce known ground truth, frozen injection–recovery domain,
development/held-out separation, prospective metrics and a final rule frozen
before held-out access.

## Next task

F3B.1 — preregister injection–recovery, development/held-out split and validation
architecture before generating a single injection.
"""
    drp=repo/DR_REL; drp.parent.mkdir(parents=True,exist_ok=True); drp.write_text(dr,encoding="utf-8",newline="\n")

    # Update only the explicit status block of the existing Phase-3A README.
    rp=repo/README_REL
    txt=rp.read_text(encoding="utf-8")
    pattern=r"## STATUS\s*\n\s*CATALOGUE-SCALE ROBUSTNESS CHARACTERIZED —\s*\nPHASE 3A CLOSURE NOT STARTED"
    replacement="## STATUS\n\nPHASE 3A CLOSED —\nCATALOGUE-SCALE ROBUSTNESS CHARACTERIZED WITH LIMITATIONS\nF3B NOT STARTED"
    new,n=re.subn(pattern,replacement,txt,count=1)
    if n==0:
        if "PHASE 3A CLOSED —" in txt and "CATALOGUE-SCALE ROBUSTNESS CHARACTERIZED WITH LIMITATIONS" in txt and "F3B NOT STARTED" in txt:
            new=txt
        else:
            raise RuntimeError("Could not locate either the exact F3A.5 status block or the exact F3A.6 closed status")
    rp.write_text(new,encoding="utf-8",newline="\n")

    audit={
      "validation_status":"PHASE3A_CLOSURE_VALIDATION_PASS",
      "phase3a_decision":phase_status,
      "f2_source_bindings_verified":True,
      "f3a5_source_bindings_verified":True,
      "comparison_dimensions":len(cmp_rows),
      "evidence_planes":PLANES,
      "evidence_rows":len(ledger),
      "claim_matrix_rows":len(claims),
      "all_claims_evidence_mapped":True,
      "unsupported_positive_claims":0,
      "limitations":len(limitations),
      "f3b_entry_requirements":len(reqs),
      "frozen_counts":{
        "f2_events":10,"f2_pairs":5,"f2_primary_variants":780,"f2_eligible":514,"f2_inadmissible":266,
        "f3a_events":122,"qpp_reference_events":61,"not_selected_reference_events":61,
        "baseline_gate":{"concordant":65,"mismatch":51,"inadmissible":6},
        "qpp_role":{"concordant":8,"mismatch":51,"inadmissible":2},
        "not_selected_role":{"concordant":57,"mismatch":0,"inadmissible":4},
        "f3a_primary_variants":9516,"f3a_eligible":6422,"f3a_inadmissible":3094,
        "transitions":{"selected_retained":295,"selection_lost":171,"not_selected_retained":3178,"selection_gained":0},
        "optimizer_events":116,"optimizer_seed_decisions":1160,"seed_discordant":0,
        "period_comparable":295
      },
      "qpp_baseline_mismatches_preserved":51,
      "baseline_mismatches_recoded":0,
      "events_removed":0,
      "f2_denominator_unchanged":True,
      "f3a_denominator_unchanged":True,
      "scientific_boundaries":{
        "new_afino_execution":False,"fits_opened":False,"payload_npy_opened":False,"sqlite_opened":False,
        "new_scientific_statistics_computed":False,"frozen_evidence_reconstruction_only":True,
        "new_figures_generated":False,"new_threshold_added":False,"formal_hypothesis_test_performed":False,
        "f0_f2_modified":False,"baii_modified":False,"f3a1_f3a5_modified":False,"f3b_modified":False,
        "observational_ground_truth_established":False,"candidate_discovery_authorized":False,
        "manuscript1_full_draft_started":False
      },
      "report_word_count":wc
    }
    (closure/"f3a6_closure_audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")

    # SHA256SUMS covers all closure files except itself.
    sums=closure/"SHA256SUMS.txt"
    members=sorted(p for p in closure.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt")
    sums.write_text("\n".join(f"{sha256(p)}  {p.name}" for p in members)+"\n",encoding="ascii",newline="\n")
    print("PHASE3A_CLOSURE_CHARACTERIZED")
    print("decision =",phase_status)
    print("comparison_dimensions =",len(cmp_rows))
    print("evidence_rows =",len(ledger))
    print("claim_rows =",len(claims))
    print("limitations =",len(limitations))
    print("f3b_requirements =",len(reqs))
    print("report_word_count =",wc)
    print("new_scientific_statistics_computed=false")
    print("new_afino_execution=false")
    print("new_figures_generated=false")
    return audit

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",default=".")
    args=ap.parse_args(); build(Path(args.repo_root).resolve(),verify_git=True)

if __name__=="__main__": main()
