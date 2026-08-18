from __future__ import annotations
import csv, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
D=ROOT/"workflows/phase3b/design"

def rows(name):
    with (D/name).open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))
def j(name):
    return json.loads((D/name).read_text(encoding="utf-8"))

def test_18_entry_requirements_resolved():
    r=rows("f3b1_entry_requirement_resolution.csv")
    assert len(r)==18
    assert len({x["requirement_id"] for x in r})==18
    assert all(x["resolution_status"]=="RESOLVED_FOR_F3B_DESIGN" for x in r)

def test_simulation_ids_unique_and_backgrounds_do_not_cross_splits():
    r=rows("f3b1_split_registry.csv")
    assert len(r)==8640
    assert len({x["simulation_unit_id"] for x in r})==8640
    bg={}
    for x in r: bg.setdefault(x["background_realization_id"],set()).add(x["split"])
    assert len(bg)==3600
    assert all(len(v)==1 for v in bg.values())

def test_positive_null_pairs_stay_together():
    r=rows("f3b1_split_registry.csv")
    pairs={}
    for x in r:
        k=(x["background_realization_id"],x["gap_quality_regime"])
        pairs.setdefault(k,set()).add(x["truth_state"])
    assert all(v=={"SYNTHETIC_QPP_PRESENT","SYNTHETIC_QPP_ABSENT"} for v in pairs.values())

def test_parameters_within_frozen_discrete_domain():
    r=rows("f3b1_split_registry.csv")
    assert {x["n_samples"] for x in r}<={"15","30","60","120"}
    assert {x["red_noise_alpha"] for x in r}<={"0.0","1.0","2.0"}
    assert {x["positive_pair_qpp_fraction"] for x in r}<={"0.01","0.02","0.04"}

def test_truth_labels_known_and_observation_not_truth():
    r=rows("f3b1_split_registry.csv")
    assert {x["truth_state"] for x in r}=={"SYNTHETIC_QPP_PRESENT","SYNTHETIC_QPP_ABSENT"}
    t=j("f3b1_truth_label_contract.json")
    assert t["ground_truth_policy"]["observational_reference_ground_truth"] is False
    assert t["ground_truth_policy"]["real_observational_background_allowed_as_primary_null"] is False

def test_heldout_frozen_but_not_materialized():
    r=rows("f3b1_split_registry.csv")
    h=[x for x in r if x["split"]=="HELDOUT"]
    assert len(h)==4320
    assert all(x["synthetic_series_materialized"]=="false" for x in h)
    assert all(x["background_noise_materialized"]=="false" for x in h)
    assert all(x["true_period_materialized"]=="false" for x in h)
    assert all(x["heldout_access_allowed_now"]=="false" for x in h)

def test_metric_denominators_and_known_null_specificity():
    m=j("f3b1_metrics_contract.json")
    assert m["scope"]["input_inadmissible_as_fn_or_tn"] is False
    assert "TP/(TP+FN)" in m["primary_classification_metrics"]["sensitivity_TPR"]
    assert "TN/(TN+FP)" in m["primary_classification_metrics"]["specificity_TNR"]
    assert "FP/(FP+TN)" in m["primary_classification_metrics"]["false_positive_rate_FPR"]
    assert m["truth_mapping"]["negative"]=="SYNTHETIC_QPP_ABSENT"

def test_period_recovery_separate_from_classification():
    p=j("f3b1_metrics_contract.json")["period_recovery"]
    assert p["classification_separate"] is True
    assert p["nonselected_m1_center_is_period_recovery"] is False
    assert p["period_recovered_within_X_percent_threshold"]=="NOT_USED"

def test_candidate_policy_cannot_access_heldout():
    c=j("f3b1_candidate_rule_policy.json")
    assert c["development_data_only"] is True
    assert c["heldout_access_for_development"]=="PROHIBITED"
    assert c["correction_rule_mandatory"] is False

def test_single_use_heldout():
    h=j("f3b1_heldout_access_policy.json")
    assert h["heldout_is_single_use"] is True
    assert h["heldout_generated_before_rule_freeze"] is False
    assert h["heldout_access_before_rule_freeze"]=="PROHIBITED"
    assert h["failure_policy"]["second_attempt_on_same_heldout"] is False

def test_comparators_resolved_before_development():
    c=rows("f3b1_comparator_resolution.csv")
    assert len(c)==6
    allowed={"IMPLEMENT_IN_DEVELOPMENT","IMPLEMENT_AS_HELDOUT_COMPARATOR",
             "CITATION_ONLY","NOT_APPLICABLE_WITH_RATIONALE",
             "UNAVAILABLE_WITH_DOCUMENTED_REASON"}
    assert all(x["final_f3b1_status"] in allowed for x in c)
    assert all(x["resolution_status"]=="RESOLVED_BEFORE_DEVELOPMENT" for x in c)

def test_zero_injections_and_zero_execution_outputs():
    p=j("f3b1_preregistration.json")
    assert p["injections_generated"] is False
    assert p["afino_executed"] is False
    assert p["scientific_results_computed"] is False
    assert p["development_generated"] is False
    assert p["heldout_generated"] is False
    assert p["heldout_accessed"] is False
    assert [x.name for x in (ROOT/"workflows/phase3b/development").iterdir()]==["README.md"]
    assert [x.name for x in (ROOT/"workflows/phase3b/heldout").iterdir()]==["README.md"]

def test_numerical_stability_is_separate_and_not_unique_optimum_claim():
    n=j("f3b1_numerical_stability_protocol.json")
    assert n["scope"]["heldout_series"]==0
    assert n["optimizer_seed_protocol"]["external_optimizer_seeds"]==list(range(10))
    assert n["interpretation_guard"]["classification_stability_implies_unique_optimum"] is False
