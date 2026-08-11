from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

EXPECTED = {
    "docs/literature/bibliographic_audit_ii/closure/final_gate_decision.json": "3bd6872cdf558889769d245ba86d7cd924bd333db1fe117a9a591e9755ba8c1c",
    "docs/literature/bibliographic_audit_ii/closure/f3a_gate_requirements.csv": "0437def01a1021fa0ca77035936eb56e002215abe2c7f52160621e393cd92b1a",
    "docs/literature/bibliographic_audit_ii/closure/comparator_consideration_matrix.csv": "34bb2e7b105f51b94c334aa3ec0fec90307fa2240ddab18c29b4e3d21e87bb86",
    "docs/literature/bibliographic_audit_ii/closure/final_evidence_ledger.csv": "09f7d73f97773672b90552cfe7fc73d8bd0fa4e67a8a0460bb3c6dbd4f63ab0a",
    "docs/decisions/DR-003-bibliographic-audit-ii-f3a-gate.md": "87b10926d36a45cfcf4ed574b76f13b62c860093cac3754e7ea239c15b065fc6",
    "workflows/phase3a/ENTRY_CONTRACT.md": "fed87a63b1afc8221d7be175648955141664195eba253ffb05cafe8071db760a",
    "workflows/phase3a/FROZEN_INPUTS.json": "57e2ac1ad9185fb6cba057723a2bf97199dbb4f24091a7cf03df560e8093eda7",
    "workflows/phase3b/README.md": "c6e1dee3c4a35cd37b032ff7bcc466f47d0b83db58b8b8d47c59bc1f8c947d14",
}

WINDOWS = {
    "W00": (0, 0), "WSm2": (-2, 0), "WSm1": (-1, 0), "WSp1": (1, 0), "WSp2": (2, 0),
    "WEm2": (0, -2), "WEm1": (0, -1), "WEp1": (0, 1), "WEp2": (0, 2),
    "WX1": (-1, 1), "WC1": (1, -1), "WX2": (-2, 2), "WC2": (2, -2),
}
PROFILES = {
    "P00": ("PDCSAP", "finite_all", "none"),
    "P01": ("SAP", "finite_all", "none"),
    "P02": ("PDCSAP", "q0_native", "none"),
    "P03": ("SAP", "q0_native", "none"),
    "P04": ("PDCSAP", "finite_all", "linear_residual_plus_one"),
    "P05": ("SAP", "finite_all", "linear_residual_plus_one"),
}
COMPARATOR_IDS = {
    "BAIIW0004","BAIIW0023","BAIIW0024","BAIIW0037","BAIIW0098","BAIIW0145",
    "BAIIW0147","BAIIW0149","BAIIW0154","BAIIW0156","BAIIW0168"
}
ALLOWED_COMPARATOR_DECISIONS = {
    "IMPLEMENT_F3A_SECONDARY","CITATION_AND_POSITIONING_ONLY","DEFER_TO_F3B",
    "NOT_APPLICABLE_TO_F3A","UNAVAILABLE_WITH_DOCUMENTED_REASON"
}
CLASS_STATES = {
    "SELECTED_RETAINED","SELECTION_LOST","NOT_SELECTED_RETAINED","SELECTION_GAINED",
    "INPUT_INADMISSIBLE","INCOMPLETE_NUMERICAL","REFERENCE_BASELINE_MISMATCH"
}
ALLOWED_PHASE3A_FILES = {
    "README.md","ENTRY_CONTRACT.md","FROZEN_INPUTS.json",
    "design/README.md","design/phase3a_protocol.md","design/gate_resolution_matrix.csv",
    "design/catalogue_source_decision.csv","design/cohort_contract.yaml",
    "design/reference_label_policy.json","design/robustness_matrix.csv",
    "design/outcomes_denominators.json","design/numerical_stability_protocol.json",
    "design/comparator_decisions.csv","design/preregistration.json","design/design_audit.json",
    "design/SHA256SUMS.txt","scripts/validate_design_freeze.py"
}

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def fail(msg: str) -> None:
    raise SystemExit("PHASE3A_DESIGN_FREEZE_VALIDATION_FAIL: " + msg)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    phase = root / "workflows/phase3a"
    design = phase / "design"

    for rel, expected in EXPECTED.items():
        p = root / rel
        if not p.is_file():
            fail(f"missing normative file: {rel}")
        observed = sha256_file(p)
        if observed != expected:
            fail(f"normative hash mismatch: {rel}: {observed} != {expected}")

    frozen_inputs = json.loads((phase / "FROZEN_INPUTS.json").read_text(encoding="utf-8"))
    for item in frozen_inputs["files"]:
        p = root / item["path"]
        if not p.is_file():
            fail(f"missing frozen F0-F2 input: {item['path']}")
        if sha256_file(p) != item["sha256"]:
            fail(f"frozen F0-F2 input changed: {item['path']}")

    actual_phase_files = {
        p.relative_to(phase).as_posix() for p in phase.rglob("*") if p.is_file()
    }
    unexpected = actual_phase_files - ALLOWED_PHASE3A_FILES
    missing = ALLOWED_PHASE3A_FILES - actual_phase_files
    if unexpected:
        fail("unexpected Phase3A files before cohort materialization: " + ";".join(sorted(unexpected)))
    if missing:
        fail("missing Phase3A design files: " + ";".join(sorted(missing)))

    if "SCIENTIFIC DESIGN FROZEN" not in (phase / "README.md").read_text(encoding="utf-8"):
        fail("Phase3A README status not updated")

    gate = read_csv(design / "gate_resolution_matrix.csv")
    if len(gate) != 10:
        fail(f"gate requirements rows={len(gate)} != 10")
    expected_ids = [f"F3AR{i:03d}" for i in range(1, 11)]
    if [r["requirement_id"] for r in gate] != expected_ids:
        fail("gate requirement IDs/order mismatch")
    for i, row in enumerate(gate, 1):
        expected_status = "RESOLVED_POSITIONING_ONLY" if i == 10 else "RESOLVED_FOR_F3A_DESIGN"
        if row["resolution_status"] != expected_status:
            fail(f"{row['requirement_id']} status={row['resolution_status']} != {expected_status}")
        if not row["design_resolution"] or not row["resolution_artifact"] or not row["scientific_rationale"]:
            fail(f"unsupported gate resolution: {row['requirement_id']}")

    sources = read_csv(design / "catalogue_source_decision.csv")
    primary = [r for r in sources if r["decision"] == "PRIMARY_COHORT_SOURCE"]
    if len(primary) != 1 or primary[0]["source_work_id"] != "BAIIW0001":
        fail("exactly one primary catalogue source BAIIW0001 required")
    if not {"BAIIW0001","BAIIW0003"}.issubset({r["source_work_id"] for r in sources}):
        fail("BAIIW0001/BAIIW0003 source review missing")

    cohort = json.loads((design / "cohort_contract.yaml").read_text(encoding="utf-8"))
    if cohort["parent_catalogue"]["source_work_id"] != "BAIIW0001":
        fail("cohort parent catalogue mismatch")
    if cohort["candidate_discovery_authorized"] is not False:
        fail("candidate discovery must be false")
    if cohort["comparison_sampling_policy"]["ratio"] != 1:
        fail("comparison matching ratio changed")
    if cohort["cohort_materialized"] is not False:
        fail("cohort must not be materialized in F3A.1")

    labels = json.loads((design / "reference_label_policy.json").read_text(encoding="utf-8"))
    if labels["observational_reference_label_is_ground_truth"] is not False:
        fail("observational ground truth incorrectly asserted")
    if labels["physical_qpp_truth_established"] is not False:
        fail("physical QPP truth incorrectly asserted")
    required_roles = {
        "PUBLISHED_QPP_REFERENCE","PUBLISHED_NOT_SELECTED_REFERENCE",
        "OTHER_EXTERNAL_CLASSIFIER_REFERENCE","REFERENCE_LABEL_CONFLICT"
    }
    if set(labels["allowed_project_reference_roles"]) != required_roles:
        fail("reference role vocabulary mismatch")

    matrix = read_csv(design / "robustness_matrix.csv")
    if len(matrix) != 78:
        fail(f"primary robustness rows={len(matrix)} != 78")
    pairs = {(r["window_variant_id"], r["processing_profile_id"]) for r in matrix}
    expected_pairs = {(w,p) for w in WINDOWS for p in PROFILES}
    if pairs != expected_pairs:
        fail("78-cell window/profile Cartesian product mismatch")
    if len({r["matrix_cell_id"] for r in matrix}) != 78:
        fail("duplicate matrix_cell_id")
    for r in matrix:
        w, p = r["window_variant_id"], r["processing_profile_id"]
        if int(r["delta_start_cadences"]) != WINDOWS[w][0] or int(r["delta_end_cadences"]) != WINDOWS[w][1]:
            fail(f"window definition changed: {w}")
        expected_profile = PROFILES[p]
        observed_profile = (r["flux_product"], r["quality_policy"], r["detrending"])
        if observed_profile != expected_profile:
            fail(f"processing profile changed: {p}")
        if r["primary_or_secondary"] != "PRIMARY" or r["f2_definition_inherited"] != "TRUE":
            fail(f"non-primary/uninherited matrix cell: {r['matrix_cell_id']}")
        if r["changes_from_f2"] != "NONE" or int(r["external_optimizer_seed"]) != 0:
            fail(f"F2 primary definition changed: {r['matrix_cell_id']}")

    outcomes = json.loads((design / "outcomes_denominators.json").read_text(encoding="utf-8"))
    if set(outcomes["classification_outcome_states"]) != CLASS_STATES:
        fail("classification outcome vocabulary mismatch")
    if outcomes["robustness_descriptive"]["robustness_threshold"] is not None:
        fail("robustness threshold introduced")
    if outcomes["robustness_descriptive"]["binary_robust_not_robust_label_authorized"] is not False:
        fail("binary robustness label unexpectedly authorized")
    prohibited = {"accuracy","sensitivity","specificity","observational_false_positive_rate","physical_truth_rate"}
    if set(outcomes["prohibited_metrics"]) != prohibited:
        fail("prohibited metric contract changed")

    numerical = json.loads((design / "numerical_stability_protocol.json").read_text(encoding="utf-8"))
    if numerical["scope"]["window_variant_id"] != "W00" or numerical["scope"]["processing_profile_id"] != "P00":
        fail("numerical stability scope changed")
    if numerical["external_optimizer_seeds"] != list(range(10)) or numerical["primary_optimizer_seed"] != 0:
        fail("numerical seed policy changed")
    if numerical["stable_classification_implies_unique_optimum"] is not False:
        fail("optimizer uniqueness incorrectly inferred")

    comps = read_csv(design / "comparator_decisions.csv")
    if len(comps) != 11 or {r["work_id"] for r in comps} != COMPARATOR_IDS:
        fail("11/11 BAII comparators not represented exactly")
    for r in comps:
        if r["decision"] not in ALLOWED_COMPARATOR_DECISIONS:
            fail(f"invalid comparator decision: {r['work_id']} {r['decision']}")
        if not r["rationale"] or not r["secondary_analysis_role"]:
            fail(f"comparator not resolved: {r['work_id']}")

    prereg = json.loads((design / "preregistration.json").read_text(encoding="utf-8"))
    if prereg["status"] not in {
        "PHASE3A_SCIENTIFIC_DESIGN_FROZEN_BEFORE_COHORT_MATERIALIZATION",
        "PHASE3A_SCIENTIFIC_DESIGN_FROZEN_WITH_DOCUMENTED_LIMITATION",
    }:
        fail("invalid preregistration freeze status")
    false_fields = [
        "candidate_discovery_authorized","observational_ground_truth_assumed",
        "correction_claim_authorized","sensitivity_estimation_authorized",
        "specificity_estimation_authorized","observational_fpr_estimation_authorized",
        "priority_claim_authorized","cohort_materialized","tess_light_curves_downloaded",
        "tess_light_curves_opened","afino_executed","scientific_results_computed"
    ]
    for field in false_fields:
        if prereg[field] is not False:
            fail(f"preregistration boundary must be false: {field}")
    hash_fields = {
        "gate_resolution_matrix_sha256":"gate_resolution_matrix.csv",
        "catalogue_source_decision_sha256":"catalogue_source_decision.csv",
        "cohort_contract_sha256":"cohort_contract.yaml",
        "reference_label_policy_sha256":"reference_label_policy.json",
        "robustness_matrix_sha256":"robustness_matrix.csv",
        "outcomes_denominators_sha256":"outcomes_denominators.json",
        "numerical_stability_protocol_sha256":"numerical_stability_protocol.json",
        "comparator_decisions_sha256":"comparator_decisions.csv",
    }
    for field, filename in hash_fields.items():
        if prereg[field] != sha256_file(design / filename):
            fail(f"preregistration hash mismatch: {filename}")

    audit = json.loads((design / "design_audit.json").read_text(encoding="utf-8"))
    for field in ["candidate_discovery","new_systematic_search","cohort_materialized",
                  "tess_light_curves_downloaded","tess_light_curves_opened","afino_executed",
                  "scientific_results_computed","f0_f2_modified","baii_modified","f3b_modified"]:
        if audit[field] is not False:
            fail(f"design audit boundary must be false: {field}")
    if audit["baii_gate_requirements"]["resolved"] != 10 or audit["comparators"]["addressed"] != 11:
        fail("design audit counts invalid")

    sums = {}
    with (design / "SHA256SUMS.txt").open(encoding="ascii") as f:
        for line in f:
            digest, rel = line.rstrip("\n").split("  ", 1)
            sums[rel] = digest
    expected_design_files = {
        p.name for p in design.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt"
    }
    if set(sums) != expected_design_files:
        fail("design SHA256SUMS inventory mismatch")
    for rel, expected in sums.items():
        if sha256_file(design / rel) != expected:
            fail(f"design checksum mismatch: {rel}")

    protocol_words = len((design / "phase3a_protocol.md").read_text(encoding="utf-8").split())
    if not (1400 <= protocol_words <= 2000):
        fail(f"phase3a_protocol word count out of requested range: {protocol_words}")

    print("PHASE3A_DESIGN_FREEZE_VALIDATION_PASS")
    print("baii_gate_requirements_resolved=10")
    print("catalogue_primary_sources=1")
    print("primary_catalogue_source=BAIIW0001")
    print("primary_robustness_cells=78")
    print("comparators_addressed=11")
    print("stability_scope=W00/P00")
    print("stability_seeds=0..9")
    print(f"preregistration_status={prereg['status']}")
    print("candidate_discovery=false")
    print("observational_ground_truth=false")
    print("cohort_materialized=false")
    print("tess_light_curves_opened=false")
    print("afino_executed=false")
    print("scientific_results_computed=false")

if __name__ == "__main__":
    main()
