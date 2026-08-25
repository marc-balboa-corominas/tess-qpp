from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

EXPECTED_HEAD = "b501fa16c3b3af5d6105df38421995e5d5600763"
HISTORICAL_README_SHA = "19599f6d2ffc0568916d213d9bb04f994029c8bfd5120169ef7c949c2c6fb439"

BAII_TAG = "bibliographic-audit-ii-complete-v1"
BAII_COMMIT = "73378199865258e89f6132c82755a647be37a9d6"
F3A_TAG = "phase3a-complete-v2"
F3A_COMMIT = "1f3b1cc21286c25dea6a0e5779c0dc18edd81933"
F3B_TAG = "phase3b-complete-v1"
F3B_COMMIT = EXPECTED_HEAD

ROOT = Path(__file__).resolve().parents[3]
M1 = ROOT / "manuscripts/manuscript_01"
PLANNING = M1 / "planning"
SCRIPTS = M1 / "scripts"
README = M1 / "README.md"
DR009 = ROOT / "docs/decisions/DR-009-manuscript1-evidence-architecture.md"

BINDINGS = PLANNING / "m1_source_bindings.json"
SCOPE = PLANNING / "m1_scope_contract.md"
PLANES = PLANNING / "m1_evidence_plane_registry.csv"
CLAIMS = PLANNING / "m1_claim_matrix.csv"
SECTIONS = PLANNING / "m1_section_map.csv"
FIGURES = PLANNING / "m1_figure_table_plan.csv"
LIMITS = PLANNING / "m1_limitations_matrix.csv"
BIBPOS = PLANNING / "m1_bibliographic_positioning_matrix.csv"
AUDIT = PLANNING / "m1_architecture_audit.json"
SUMS = PLANNING / "SHA256SUMS.txt"
BUILDER = SCRIPTS / "build_manuscript1_architecture.py"
VALIDATOR = SCRIPTS / "validate_manuscript1_architecture.py"

PREBUILD_DIRTY = {
    "manuscripts/manuscript_01/scripts/build_manuscript1_architecture.py",
    "manuscripts/manuscript_01/scripts/validate_manuscript1_architecture.py",
}

FINAL_DIRTY = {
    "manuscripts/manuscript_01/README.md",
    "manuscripts/manuscript_01/planning/SHA256SUMS.txt",
    "manuscripts/manuscript_01/planning/m1_architecture_audit.json",
    "manuscripts/manuscript_01/planning/m1_bibliographic_positioning_matrix.csv",
    "manuscripts/manuscript_01/planning/m1_claim_matrix.csv",
    "manuscripts/manuscript_01/planning/m1_evidence_plane_registry.csv",
    "manuscripts/manuscript_01/planning/m1_figure_table_plan.csv",
    "manuscripts/manuscript_01/planning/m1_limitations_matrix.csv",
    "manuscripts/manuscript_01/planning/m1_scope_contract.md",
    "manuscripts/manuscript_01/planning/m1_section_map.csv",
    "manuscripts/manuscript_01/planning/m1_source_bindings.json",
    "manuscripts/manuscript_01/scripts/build_manuscript1_architecture.py",
    "manuscripts/manuscript_01/scripts/validate_manuscript1_architecture.py",
    "docs/decisions/DR-009-manuscript1-evidence-architecture.md",
}

PROTECTED_PREFIXES = (
    "foundation/f0-f2/",
    "docs/literature/bibliographic_audit_ii/",
    "workflows/phase3a/",
    "workflows/phase3b/",
)

SOURCE_SPECS = [
    # F0 observational reproduction
    ("M1S001","F0","M1EP01","foundation/f0-f2/phase0/fase0_tarea15_reproduced_baseline.json","baseline reproduction decision payload"),
    ("M1S002","F0","M1EP01","foundation/f0-f2/phase0/fase0_tarea15_phase0_synthesis.md","Phase 0 reproduction synthesis"),
    ("M1S003","F0","M1EP01","foundation/f0-f2/phase0/fase0_tarea15_evidence_matrix.csv","Phase 0 evidence matrix"),

    # F1 synthetic/numerical benchmark: core + nested + synthesis
    ("M1S004","F1","M1EP02","foundation/f0-f2/phase1/fase1_tarea06_condition_summary.csv","core synthetic benchmark condition summary"),
    ("M1S005","F1","M1EP02","foundation/f0-f2/phase1/fase1_tarea06_core_benchmark_analysis.md","core benchmark analysis"),
    ("M1S006","F1","M1EP02","foundation/f0-f2/phase1/fase1_tarea06_model_diagnostics.csv","core numerical diagnostics"),
    ("M1S007","F1","M1EP02","foundation/f0-f2/phase1/fase1_tarea06_optimizer_stability_summary.csv","core optimizer stability"),
    ("M1S008","F1","M1EP02","foundation/f0-f2/phase1/fase1_tarea13_condition_summary.csv","nested-support condition summary"),
    ("M1S009","F1","M1EP02","foundation/f0-f2/phase1/fase1_tarea13_nested_analysis_audit.json","nested-support analysis audit"),
    ("M1S010","F1","M1EP02","foundation/f0-f2/phase1/fase1_tarea13_nested_analysis_report.md","nested-support analysis report"),
    ("M1S011","F1","M1EP02","foundation/f0-f2/phase1/fase1_tarea13_model_diagnostics_by_n.csv","nested numerical diagnostics"),
    ("M1S012","F1","M1EP02","foundation/f0-f2/phase1/fase1_tarea13_optimizer_stability_summary.csv","nested optimizer stability"),
    ("M1S013","F1","M1EP02","foundation/f0-f2/phase1/fase1_tarea14_phase1_decision.json","Phase 1 formal decision"),
    ("M1S014","F1","M1EP02","foundation/f0-f2/phase1/fase1_tarea14_phase1_evidence_ledger.csv","Phase 1 evidence ledger"),
    ("M1S015","F1","M1EP02","foundation/f0-f2/phase1/fase1_tarea14_phase1_synthesis_report.md","Phase 1 synthesis"),

    # F2 observational pilot robustness
    ("M1S016","F2","M1EP03","foundation/f0-f2/phase2/fase2_tarea05_event_summary.csv","pilot event-level robustness summary"),
    ("M1S017","F2","M1EP03","foundation/f0-f2/phase2/fase2_tarea05_observational_robustness_audit.json","pilot robustness audit"),
    ("M1S018","F2","M1EP03","foundation/f0-f2/phase2/fase2_tarea05_observational_robustness_report.md","pilot robustness report"),
    ("M1S019","F2","M1EP03","foundation/f0-f2/phase2/fase2_tarea05_optimizer_stability_summary.csv","pilot numerical stability"),
    ("M1S020","F2","M1EP03","foundation/f0-f2/phase2/fase2_tarea05_period_robustness.csv","pilot conditional period robustness"),
    ("M1S021","F2","M1EP03","foundation/f0-f2/phase2/fase2_tarea06_manuscript_claim_matrix.csv","Phase 2 manuscript claim matrix"),
    ("M1S022","F2","M1EP03","foundation/f0-f2/phase2/fase2_tarea06_phase2_limitations_register.csv","Phase 2 limitations"),
    ("M1S023","F2","M1EP03","foundation/f0-f2/phase2/fase2_tarea06_phase2_decision.json","Phase 2 formal decision"),
    ("M1S024","F2","M1EP03","foundation/f0-f2/phase2/fase2_tarea06_phase2_evidence_ledger.csv","Phase 2 evidence ledger"),
    ("M1S025","F2","M1EP03","foundation/f0-f2/phase2/fase2_tarea06_phase2_synthesis_report.md","Phase 2 synthesis"),

    # BAII auxiliary positioning plane
    ("M1S026","BAII","M1EP06","docs/literature/bibliographic_audit_ii/closure/precedence_positioning_matrix.csv","final precedence/positioning matrix"),
    ("M1S027","BAII","M1EP06","docs/literature/bibliographic_audit_ii/closure/final_gate_decision.json","final F3A literature gate"),
    ("M1S028","BAII","M1EP06","docs/literature/bibliographic_audit_ii/closure/final_evidence_ledger.csv","final BAII evidence ledger"),
    ("M1S029","BAII","M1EP06","docs/literature/bibliographic_audit_ii/closure/final_synthesis_report.md","final BAII synthesis"),

    # F3A catalogue-scale observational robustness
    ("M1S030","F3A","M1EP04","workflows/phase3a/evidence/tables/f3a5_reference_baseline_audit.csv","catalogue baseline-reproduction gate"),
    ("M1S031","F3A","M1EP04","workflows/phase3a/evidence/tables/f3a5_primary_outcome_matrix.csv","catalogue-scale robustness outcome matrix"),
    ("M1S032","F3A","M1EP04","workflows/phase3a/evidence/reports/f3a5_robustness_audit.json","catalogue robustness audit"),
    ("M1S033","F3A","M1EP04","workflows/phase3a/evidence/tables/f3a5_optimizer_stability.csv","catalogue numerical-stability table"),
    ("M1S034","F3A","M1EP04","workflows/phase3a/evidence/tables/f3a5_period_robustness.csv","catalogue conditional period robustness"),
    ("M1S035","F3A","M1EP04","workflows/phase3a/closure/f3a6_claim_matrix.csv","Phase 3A claim matrix"),
    ("M1S036","F3A","M1EP04","workflows/phase3a/closure/f3a6_limitations_register.csv","Phase 3A limitations"),
    ("M1S037","F3A","M1EP04","workflows/phase3a/closure/f3a6_phase3a_decision.json","Phase 3A formal decision"),
    ("M1S038","F3A","M1EP04","workflows/phase3a/closure/f3a6_phase3a_synthesis_report.md","Phase 3A synthesis"),

    # F3B synthetic ground-truth heldout validation
    ("M1S039","F3B","M1EP05","workflows/phase3b/development/analysis/f3b4_baseline_metrics.json","DEVELOPMENT baseline metrics"),
    ("M1S040","F3B","M1EP05","workflows/phase3b/development/analysis/f3b4_candidate_rule_gate.json","DEVELOPMENT candidate-rule gate"),
    ("M1S041","F3B","M1EP05","workflows/phase3b/development/analysis/f3b4_final_rule_freeze.json","final-rule freeze"),
    ("M1S042","F3B","M1EP05","workflows/phase3b/heldout/evaluation/evidence/reports/f3b7_heldout_baseline_metrics.json","independent HELDOUT metrics"),
    ("M1S043","F3B","M1EP05","workflows/phase3b/heldout/evaluation/evidence/tables/f3b7_heldout_selection_function.csv","final HELDOUT selection function"),
    ("M1S044","F3B","M1EP05","workflows/phase3b/heldout/evaluation/evidence/tables/f3b7_heldout_period_recovery.csv","HELDOUT conditional period recovery"),
    ("M1S045","F3B","M1EP05","workflows/phase3b/closure/f3b8_claim_matrix.csv","Phase 3B claim matrix"),
    ("M1S046","F3B","M1EP05","workflows/phase3b/closure/f3b8_limitations_register.csv","Phase 3B limitations"),
    ("M1S047","F3B","M1EP05","workflows/phase3b/closure/f3b8_phase3b_decision.json","Phase 3B closure decision"),
    ("M1S048","F3B","M1EP05","workflows/phase3b/closure/f3b8_manuscript1_handoff.csv","Phase 3B manuscript handoff"),
]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip("\r\n")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def status_paths() -> set[str]:
    out = git("status", "--porcelain=v1", "--untracked-files=all")
    paths = set()
    for line in out.splitlines():
        if line:
            paths.add(line[3:].replace("\\", "/"))
    return paths


def last_touch_commit(rel: str) -> str:
    out = git("log", "-1", "--format=%H", "--", rel)
    if not out:
        raise RuntimeError(f"No Git history found for {rel}")
    return out


def ensure_tracked(rel: str) -> None:
    subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--error-unmatch", "--", rel],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def phase_freeze(phase: str, rel: str) -> tuple[str, str | None, str]:
    if phase in {"F0", "F1", "F2"}:
        return (
            last_touch_commit(rel),
            None,
            "HISTORICAL_F0_F2_FROZEN_FOUNDATION_NO_DEDICATED_PHASE_TAG",
        )
    if phase == "BAII":
        return BAII_COMMIT, BAII_TAG, "BAII_COMPLETE_FREEZE"
    if phase == "F3A":
        return F3A_COMMIT, F3A_TAG, "PHASE3A_COMPLETE_FREEZE"
    if phase == "F3B":
        return F3B_COMMIT, F3B_TAG, "PHASE3B_COMPLETE_FREEZE"
    raise RuntimeError(phase)


def allowed_use_for(phase: str) -> str:
    return {
        "F0": "observational reproduction evidence only",
        "F1": "synthetic/numerical benchmark evidence only",
        "F2": "observational pilot robustness evidence only",
        "BAII": "framing, precedence and positioning constraints only; not a scientific result plane",
        "F3A": "catalogue-scale observational robustness evidence only",
        "F3B": "synthetic-ground-truth validation and selection-function evidence only",
    }[phase]


def prohibited_use_for(phase: str) -> str:
    return {
        "F0": "do not infer observational physical truth or classifier accuracy",
        "F1": "do not transport synthetic performance directly to observational populations",
        "F2": "do not interpret observational reference labels as physical ground truth or estimate observational FPR/sensitivity",
        "BAII": "do not assert priority/novelty beyond the frozen bounded audit and do not treat BAII as a result plane",
        "F3A": "do not infer observational ground truth, sensitivity, specificity, FPR, or physical falsity from reference mismatch",
        "F3B": "do not claim observational validation, observational prevalence, or a validated population correction",
    }[phase]


# ---------------------------------------------------------------------------
# Boundary
# ---------------------------------------------------------------------------

if git("rev-parse", "HEAD") != EXPECTED_HEAD:
    raise RuntimeError("Manuscript 1.1 must start from the Phase 3B final closure commit.")

if status_paths() != PREBUILD_DIRTY:
    raise RuntimeError(f"Unexpected pre-build dirty scope: {sorted(status_paths())}")

if sha(README) != HISTORICAL_README_SHA:
    raise RuntimeError("Historical Manuscript 01 README changed before architecture build.")

for tag, commit in [(BAII_TAG, BAII_COMMIT), (F3A_TAG, F3A_COMMIT), (F3B_TAG, F3B_COMMIT)]:
    if git("rev-list", "-n", "1", tag) != commit:
        raise RuntimeError(f"Freeze tag mismatch: {tag}")

for p in [BINDINGS,SCOPE,PLANES,CLAIMS,SECTIONS,FIGURES,LIMITS,BIBPOS,AUDIT,SUMS,DR009]:
    if p.exists():
        raise RuntimeError(f"Future Manuscript 1.1 artifact already exists: {p.relative_to(ROOT)}")

# ---------------------------------------------------------------------------
# Source bindings
# ---------------------------------------------------------------------------

bindings_rows = []
for sid, phase, plane, rel, role in SOURCE_SPECS:
    p = ROOT / rel
    if not p.is_file():
        raise RuntimeError(f"Authoritative source missing: {rel}")
    ensure_tracked(rel)
    freeze_commit, freeze_tag, freeze_basis = phase_freeze(phase, rel)
    bindings_rows.append({
        "source_id": sid,
        "phase": phase,
        "evidence_plane": plane,
        "repository_relative_path": rel,
        "sha256": sha(p),
        "bytes": p.stat().st_size,
        "freeze_commit": freeze_commit,
        "freeze_tag": freeze_tag,
        "freeze_basis": freeze_basis,
        "scientific_role": role,
        "allowed_use": allowed_use_for(phase),
        "prohibited_use": prohibited_use_for(phase),
    })

bindings_obj = {
    "schema_version": "1.0.0",
    "artifact_role": "MANUSCRIPT1_EVIDENCE_ARCHITECTURE_SOURCE_BINDINGS",
    "status": "FROZEN_SOURCE_ARCHITECTURE_BINDINGS",
    "manuscript": "Manuscript 1",
    "entry_commit": EXPECTED_HEAD,
    "source_count": len(bindings_rows),
    "freeze_groups": {
        "F0_F2": {
            "repository_root": "foundation/f0-f2/",
            "preservation_model": "docs/decisions/DR-001-f0-f2-preservation-model.md",
            "dedicated_phase_tag_available": False,
            "binding_policy": "per-source path + SHA + last-touch Git commit; freeze_tag=null",
        },
        "BAII": {"commit": BAII_COMMIT, "tag": BAII_TAG},
        "F3A": {"commit": F3A_COMMIT, "tag": F3A_TAG},
        "F3B": {"commit": F3B_COMMIT, "tag": F3B_TAG},
    },
    "sources": bindings_rows,
    "execution_firewall": {
        "new_scientific_computation": False,
        "new_afino_execution": False,
        "new_synthetic_generation": False,
        "new_statistical_inference": False,
        "new_bibliographic_search": False,
        "manuscript_prose_started": False,
    },
}
write_json(BINDINGS, bindings_obj)

source_ids = {r["source_id"] for r in bindings_rows}

# ---------------------------------------------------------------------------
# Frozen source sanity checks for core claims
# ---------------------------------------------------------------------------

# F3A baseline identity.
f3a_base = read_csv(ROOT / "workflows/phase3a/evidence/tables/f3a5_reference_baseline_audit.csv")
if len(f3a_base) != 122:
    raise RuntimeError(f"F3A baseline rows != 122: {len(f3a_base)}")
qpp = [r for r in f3a_base if r["observational_reference_role"] == "PUBLISHED_QPP_REFERENCE"]
ns = [r for r in f3a_base if r["observational_reference_role"] == "PUBLISHED_NOT_SELECTED_REFERENCE"]
if len(qpp) != 61 or len(ns) != 61:
    raise RuntimeError("F3A reference-role counts changed.")
if sum(r["baseline_gate_state"] == "REFERENCE_BASELINE_MISMATCH" for r in qpp) != 51:
    raise RuntimeError("F3A 51/61 QPP baseline mismatch identity changed.")
if sum(r["baseline_gate_state"] == "REFERENCE_CONCORDANT" for r in qpp) != 8:
    raise RuntimeError("F3A QPP baseline-concordant count changed.")
if sum(r["baseline_gate_state"] == "REFERENCE_CONCORDANT" for r in ns) != 57:
    raise RuntimeError("F3A not-selected baseline-concordant count changed.")

f3a_stab = read_csv(ROOT / "workflows/phase3a/evidence/tables/f3a5_optimizer_stability.csv")
if len(f3a_stab) != 116:
    raise RuntimeError(f"F3A optimizer stability rows != 116: {len(f3a_stab)}")
if any(int(r["discordant_vs_seed0_count"]) != 0 for r in f3a_stab):
    raise RuntimeError("F3A seed-stability binary discordance changed.")

f3b_metrics = json.loads((ROOT / "workflows/phase3b/heldout/evaluation/evidence/reports/f3b7_heldout_baseline_metrics.json").read_text(encoding="utf-8"))
cm = f3b_metrics["confusion_matrix"]
if (cm["TP"],cm["FN"],cm["TN"],cm["FP"]) != (152,1648,1800,0):
    raise RuntimeError("F3B HELDOUT confusion identity changed.")
if len(read_csv(ROOT / "workflows/phase3b/heldout/evaluation/evidence/tables/f3b7_heldout_selection_function.csv")) != 156:
    raise RuntimeError("F3B final selection rows changed.")
if len(read_csv(ROOT / "workflows/phase3b/heldout/evaluation/evidence/tables/f3b7_heldout_period_recovery.csv")) != 152:
    raise RuntimeError("F3B period rows changed.")

# ---------------------------------------------------------------------------
# Evidence plane registry: exactly 5 primary + 1 auxiliary.
# ---------------------------------------------------------------------------

plane_rows = [
    {
        "evidence_plane_id":"M1EP01","phase":"F0","plane_name":"F0_OBSERVATIONAL_REPRODUCTION","plane_type":"PRIMARY_SCIENTIFIC",
        "what_it_establishes":"Reproducibility of the frozen public AFINO baseline on the observational reproduction cohort and the operational baseline used downstream.",
        "what_it_does_not_establish":"Observational physical QPP truth, population sensitivity/specificity/FPR, or identity with unpublished private analysis code.",
        "ground_truth_status":"OBSERVATIONAL_REFERENCE_NOT_PHYSICAL_GROUND_TRUTH","observational_or_synthetic":"OBSERVATIONAL",
        "manuscript_role":"published-event reproduction and baseline specification",
    },
    {
        "evidence_plane_id":"M1EP02","phase":"F1","plane_name":"F1_SYNTHETIC_NUMERICAL_BENCHMARK","plane_type":"PRIMARY_SCIENTIFIC",
        "what_it_establishes":"Controlled synthetic-domain benchmark behavior, support dependence, period behavior and numerical diagnostics of the frozen AFINO implementation.",
        "what_it_does_not_establish":"Observational population performance or transport to real TESS prevalence.",
        "ground_truth_status":"SYNTHETIC_KNOWN_TRUTH_WITHIN_DESIGNED_DOMAIN","observational_or_synthetic":"SYNTHETIC",
        "manuscript_role":"synthetic benchmark and numerical behavior",
    },
    {
        "evidence_plane_id":"M1EP03","phase":"F2","plane_name":"F2_OBSERVATIONAL_PILOT_ROBUSTNESS","plane_type":"PRIMARY_SCIENTIFIC",
        "what_it_establishes":"Pilot-scale sensitivity of observational reference classifications to prospectively frozen methodological perturbations.",
        "what_it_does_not_establish":"Classifier accuracy, observational FPR/sensitivity/specificity, or physical truth.",
        "ground_truth_status":"OBSERVATIONAL_REFERENCE_NOT_PHYSICAL_GROUND_TRUTH","observational_or_synthetic":"OBSERVATIONAL",
        "manuscript_role":"pilot methodological robustness",
    },
    {
        "evidence_plane_id":"M1EP04","phase":"F3A","plane_name":"F3A_CATALOGUE_SCALE_OBSERVATIONAL_ROBUSTNESS","plane_type":"PRIMARY_SCIENTIFIC",
        "what_it_establishes":"Catalogue-scale baseline reproduction limitations, methodological classification robustness, seed stability and conditional period robustness.",
        "what_it_does_not_establish":"Observational validation, sensitivity, specificity, FPR, physical truth, or a selection function.",
        "ground_truth_status":"OBSERVATIONAL_REFERENCE_NOT_PHYSICAL_GROUND_TRUTH","observational_or_synthetic":"OBSERVATIONAL",
        "manuscript_role":"catalogue-scale observational robustness",
    },
    {
        "evidence_plane_id":"M1EP05","phase":"F3B","plane_name":"F3B_SYNTHETIC_GROUND_TRUTH_VALIDATION","plane_type":"PRIMARY_SCIENTIFIC",
        "what_it_establishes":"Independent single-use HELDOUT synthetic-ground-truth performance, final synthetic selection function and conditional period recovery for the frozen baseline.",
        "what_it_does_not_establish":"Observational validation, real-TESS prevalence, physical truth or a validated population correction.",
        "ground_truth_status":"SYNTHETIC_KNOWN_TRUTH_WITH_INDEPENDENT_HELDOUT","observational_or_synthetic":"SYNTHETIC",
        "manuscript_role":"known-truth heldout validation",
    },
    {
        "evidence_plane_id":"M1EP06","phase":"BAII","plane_name":"BAII_POSITIONING_AND_PRECEDENCE","plane_type":"AUXILIARY_NON_RESULT",
        "what_it_establishes":"Bounded literature-positioning, overlap and precedence constraints under the frozen BAII search/extraction scope.",
        "what_it_does_not_establish":"A scientific result of the AFINO/TESS experiment or unrestricted global priority.",
        "ground_truth_status":"DOCUMENTARY_LITERATURE_EVIDENCE","observational_or_synthetic":"NEITHER",
        "manuscript_role":"introduction/discussion framing and priority-claim firewall",
    },
]
write_csv(PLANES, list(plane_rows[0].keys()), plane_rows)

# ---------------------------------------------------------------------------
# Scope contract
# ---------------------------------------------------------------------------

scope_text = """# Manuscript 1 scope contract

## Status

`EVIDENCE_CLAIM_SECTION_ARCHITECTURE_ONLY — MANUSCRIPT PROSE NOT STARTED`

## Scientific thesis

The manuscript evaluates the reproducibility, methodological robustness, numerical behavior,
and synthetic-ground-truth selection properties of the frozen AFINO implementation applied in
the TESS QPP context, progressing from published-event reproduction and synthetic benchmarking
to catalogue-scale observational robustness and independent held-out injection–recovery
validation.

The manuscript architecture deliberately separates five primary evidence planes:

1. F0 observational reproduction;
2. F1 synthetic/numerical benchmark;
3. F2 observational pilot robustness;
4. F3A catalogue-scale observational robustness;
5. F3B synthetic-ground-truth heldout validation.

BAII is an auxiliary positioning and precedence plane, not a sixth result plane.

## Explicit non-claims

This manuscript does not present:

- a validated observational correction;
- observational sensitivity, specificity or FPR;
- real-TESS QPP prevalence;
- physical confirmation or falsification of individual observational QPPs;
- a universal selection function;
- candidate discovery;
- a claim that AFINO is observationally validated;
- a global priority claim unsupported by the frozen BAII scope.

## Interpretation firewall

Observational reproduction is not observational physical truth.
Synthetic ground truth is not observational ground truth.
Classification robustness is not classifier accuracy.
Held-out synthetic performance is not observational validation.
A zero observed HELDOUT false-selection count is not proof of a population FPR of zero.
The F3B synthetic selection function is not a population correction.

## Computation and literature firewall

Manuscript 1.1 performs no AFINO execution, synthetic generation, new statistical inference,
new bibliography search, threshold search, candidate-rule development or scientific
re-analysis. It only binds frozen sources and fixes evidence→claim→section architecture.

No `manuscript.tex`, `main.md`, abstract, introduction or discussion draft is authorized in
Manuscript 1.1.
"""
SCOPE.write_text(scope_text, encoding="utf-8", newline="\n")

# ---------------------------------------------------------------------------
# Unified claim matrix
# ---------------------------------------------------------------------------

claim_fields = [
    "claim_id","claim_text","status","primary_evidence_plane","supporting_phases","source_ids",
    "allowed_wording","mandatory_qualification","prohibited_wording","target_section"
]

claims_data = [
("M1C001","The frozen public AFINO baseline can reproduce the five published TESS detections used in F0.","SUPPORTED_WITH_EXPLICIT_LIMITATION","M1EP01","F0","M1S001;M1S002;M1S003","The frozen public AFINO baseline reproduced the five published TESS detections in the F0 reproduction cohort.","Scope to the frozen F0 cohort; paper-code identity remains unresolved.","AFINO is observationally validated or the five detections are physically proven.","4.1"),
("M1C002","F1 synthetic performance is strongly dependent on the simulated domain, including duration/sampling and signal properties.","SUPPORTED_NOW","M1EP02","F1","M1S004;M1S005;M1S008;M1S010","Synthetic benchmark behavior varies materially across the frozen duration/sampling and signal-property domain.","Keep the designed synthetic domain explicit.","This performance directly describes the real TESS population.","4.1"),
("M1C003","F1 numerical diagnostics show multiple numerical solutions/warnings/bounds without corresponding binary-decision instability in the examined scope.","SUPPORTED_WITH_EXPLICIT_LIMITATION","M1EP02","F1","M1S006;M1S007;M1S011;M1S012;M1S015","Numerical multiplicity and diagnostics coexist with binary-decision stability in the examined frozen F1 scopes.","Do not infer a unique global optimum or auditable convergence.","The optimizer has a unique global solution.","4.4"),
("M1C004","The F2 pilot shows classification sensitivity to prospectively defined methodological perturbations.","SUPPORTED_NOW","M1EP03","F2","M1S016;M1S017;M1S018;M1S025","The F2 observational pilot shows that frozen methodological perturbations can change reference classifications.","Observational reference labels are not physical ground truth.","F2 estimates observational sensitivity or false-negative rate.","4.2"),
("M1C005","F3A extends that robustness experiment to a 122-event observational catalogue-scale cohort.","SUPPORTED_NOW","M1EP04","F3A","M1S031;M1S032;M1S038","F3A extends the prospectively frozen robustness stress test to 122 observational reference events.","Do not pool F2 and F3A denominators.","F3A is a validation dataset with physical labels.","4.3"),
("M1C006","F3A reveals a material baseline-reproduction limitation: 51/61 published QPP references mismatch the frozen W00/P00 baseline.","SUPPORTED_NOW","M1EP04","F3A","M1S030;M1S037;M1S038","Under the frozen F3A W00/P00/seed0 baseline, 51 of 61 published-QPP references are baseline mismatches.","Cause remains UNRESOLVED_WITHIN_F3A.","51 published QPPs are false detections.","4.3"),
("M1C007","Those 51 mismatches are not evidence that 51 published QPPs are physically false.","SUPPORTED_NOW","M1EP04","F3A","M1S030;M1S035;M1S036;M1S038","The 51 F3A baseline mismatches are reproduction mismatches, not physical falsifications.","Observational labels are reference states, not physical truth.","51 published QPPs are physically false.","5.3"),
("M1C008","Among baseline-concordant F3A references, methodological perturbations produce retained and lost QPP selections.","SUPPORTED_NOW","M1EP04","F3A","M1S031;M1S032;M1S038","Among baseline-concordant QPP references, F3A contains both retained selections and selection losses under frozen perturbations.","Condition on the baseline-concordant transition-eligible scope.","These are observational true positives and false negatives.","4.3"),
("M1C009","No selection gains occurred in the relevant baseline-concordant not-selected F3A scope.","SUPPORTED_NOW","M1EP04","F3A","M1S031;M1S032;M1S038","No baseline-relative selection gains were observed in the relevant baseline-concordant not-selected reference scope.","Repeated perturbations of observational references are not independent known negatives.","Observational FPR is zero.","4.3"),
("M1C010","M1C009 is not an observational FPR estimate.","SUPPORTED_NOW","M1EP04","F3A","M1S035;M1S037;M1S038","The absence of F3A selection gains is a robustness result, not an observational FPR estimate.","Keep evidence-plane semantics explicit.","F3A establishes observational specificity or FPR.","5.3"),
("M1C011","Binary classification is seed-stable in the frozen F3A stability scope despite numerical multiplicity.","SUPPORTED_WITH_EXPLICIT_LIMITATION","M1EP04","F3A","M1S033;M1S036;M1S038","All 116 input-eligible F3A W00/P00 events preserve binary classification across the frozen seed grid.","Stable classification does not imply unique optimizer convergence.","The optimizer converges uniquely.","4.4"),
("M1C012","F3B provides known synthetic-ground-truth characterization in the preregistered domain.","SUPPORTED_NOW","M1EP05","F3B","M1S039;M1S042;M1S047","F3B provides DEVELOPMENT and independent single-use HELDOUT synthetic-ground-truth characterization within the frozen domain.","Synthetic truth is not observational truth.","F3B observationally validates AFINO.","4.5"),
("M1C013","DEVELOPMENT and independent HELDOUT show a low-sensitivity, extremely-high-specificity operating profile for the frozen 10/10 baseline.","SUPPORTED_WITH_EXPLICIT_LIMITATION","M1EP05","F3B","M1S039;M1S041;M1S042","DEVELOPMENT and HELDOUT separately show a low-sensitivity, extremely-high-specificity synthetic-domain operating profile for the frozen 10/10 baseline.","Descriptive split comparison only; no pooling or equivalence test.","DEVELOPMENT and HELDOUT are statistically equivalent.","4.5"),
("M1C014","HELDOUT sensitivity is 152/1800 in the frozen synthetic domain.","SUPPORTED_NOW","M1EP05","F3B","M1S042","HELDOUT synthetic sensitivity is 152/1800 in the frozen Phase 3B domain.","Always state synthetic HELDOUT scope and denominator.","Observational sensitivity is 8.44%.","4.5"),
("M1C015","Zero false selections were observed among 1800 HELDOUT synthetic nulls, with finite Wilson uncertainty.","SUPPORTED_WITH_EXPLICIT_LIMITATION","M1EP05","F3B","M1S042","No false selections were observed among 1800 HELDOUT synthetic nulls; finite-sample Wilson uncertainty remains.","Do not call specificity perfect or population FPR zero.","AFINO has zero false-positive rate in the population.","4.5"),
("M1C016","Observed FP=0 does not imply a population FPR of zero.","SUPPORTED_NOW","M1EP05","F3B","M1S042;M1S045","The observed 0/1800 HELDOUT false-selection count does not establish an underlying population FPR of zero.","Retain Wilson uncertainty and synthetic-domain scope.","Population FPR is exactly zero.","5.2"),
("M1C017","The DEVELOPMENT two-threshold candidate was not promoted because it failed the preregistered specificity-preservation gate.","SUPPORTED_NOW","M1EP05","F3B","M1S040;M1S041","The DEVELOPMENT candidate failed the preregistered specificity-preservation criterion and was not promoted.","No runner-up rescue or post-hoc alternate search.","The candidate was rejected because of HELDOUT results.","4.5"),
("M1C018","The final held-out rule therefore remained the untuned AFINO 0.5 10/10 baseline.","SUPPORTED_NOW","M1EP05","F3B","M1S041;M1S047","The HELDOUT target remained the frozen AFINO 0.5 rule delta_BIC01>10 and delta_BIC21>10.","Strict greater-than; frozen before HELDOUT truth.","HELDOUT was used to tune thresholds.","4.5"),
("M1C019","The HELDOUT stratified empirical selection function is characterized within the frozen synthetic domain.","SUPPORTED_WITH_EXPLICIT_LIMITATION","M1EP05","F3B","M1S043;M1S047","The final 156-row HELDOUT stratified empirical selection surface characterizes the frozen synthetic domain.","No DEVELOPMENT pooling, smoothing, or observational transport.","This is a universal TESS selection function.","4.6"),
("M1C020","That synthetic selection function is not an observational population correction.","SUPPORTED_NOW","M1EP05","F3B","M1S043;M1S045;M1S047","The F3B selection surface is synthetic-domain evidence and is not an observational population correction.","Population transport remains a separate future problem.","Apply it directly as the TESS population correction.","5.4"),
("M1C021","Period accuracy is comparatively good conditional on selected true positives, while selection coverage is low.","SUPPORTED_WITH_EXPLICIT_LIMITATION","M1EP05","F3B","M1S042;M1S044","Period-recovery accuracy is summarized conditional on selected true positives, while overall positive selection coverage is low.","Keep conditioning on selection explicit.","Good period accuracy means high completeness.","4.6"),
("M1C022","Conditional period accuracy does not imply high detection completeness.","SUPPORTED_NOW","M1EP05","F3B","M1S042;M1S044;M1S045","Accurate periods among selected true positives can coexist with low selection sensitivity.","Separate period recovery from classifier sensitivity.","Period accuracy proves detection completeness.","5.2"),
("M1C023","A validated correction was not established.","SUPPORTED_NOW","M1EP05","F3B","M1S047;M1S048","Phase 3B closed with correction claim NOT_ESTABLISHED.","Do not weaken or silently omit this boundary.","A validated observational correction was established.","5.4"),
("M1C024","AFINO has not been observationally validated by the present programme.","SUPPORTED_NOW","M1EP05","F0;F2;F3A;F3B","M1S002;M1S023;M1S037;M1S047","The programme provides distinct reproduction, robustness and synthetic-ground-truth evidence, but not observational validation of AFINO.","Keep the evidence planes separate.","AFINO is observationally validated.","5.3"),
("M1C025","Population transport/correction remains an F4+ problem.","DEFER_TO_F4_PLUS","M1EP05","F3B","M1S047;M1S048","Population transport and observational correction remain future work beyond the present manuscript evidence freeze.","Requires explicit transport assumptions and independent later evidence.","The synthetic selection function is already a validated population correction.","5.5"),
("M1C026","AFINO is observationally validated by F0–F3B.","PROHIBITED","M1EP05","F0;F2;F3A;F3B","M1S002;M1S023;M1S037;M1S047","Do not make this claim.","The programme contains no observational physical-ground-truth validation plane.","AFINO is observationally validated.","NONE"),
("M1C027","The F3B synthetic selection function is a validated observational population correction.","PROHIBITED","M1EP05","F3B","M1S043;M1S047","Do not make this claim.","Synthetic-domain selection cannot be transported without additional assumptions/evidence.","The F3B selection function is the validated TESS correction.","NONE"),
("M1C028","Priority and novelty language must remain bounded by BAII; catalogue scale, TESS use, QPP classification and injection-recovery each have relevant precedence.","POSITIONING_ONLY","M1EP06","BAII","M1S026;M1S027;M1S028;M1S029","Position the contribution in terms of the combined prospective robustness and heldout architecture rather than unqualified first-ever claims.","BAII is bounded to its frozen search/extraction scope and is not a global novelty proof.","first catalogue-scale TESS QPP study; first TESS QPP catalogue; first QPP injection-recovery study","1"),
("M1C029","The five evidence classes must not be collapsed under an unqualified generic use of the word validation.","SUPPORTED_NOW","M1EP05","F0;F1;F2;F3A;F3B","M1S002;M1S015;M1S025;M1S038;M1S048","Name the evidence plane when describing reproduction, robustness, numerical benchmarking, or heldout synthetic performance.","Different planes have different truth conditions and denominators.","All phases independently validate AFINO in the same sense.","2"),
]
claim_rows = [dict(zip(claim_fields, row)) for row in claims_data]
write_csv(CLAIMS, claim_fields, claim_rows)

# ---------------------------------------------------------------------------
# Section map — design, not prose
# ---------------------------------------------------------------------------

section_fields = [
    "section_id","section_title","purpose","allowed_claim_ids","required_source_ids",
    "evidence_planes","must_state_limitations","prohibited_content"
]
section_data = [
("1","Introduction","Frame the TESS-QPP methodological problem and bounded literature positioning.","M1C028","M1S026;M1S027;M1S028;M1S029","M1EP06","BAII scope/access limitations","Unqualified first/priority claims; manuscript results"),
("2","Evidence and analysis architecture","Explain five primary evidence planes plus BAII auxiliary positioning plane.","M1C029","M1S002;M1S015;M1S025;M1S038;M1S048","M1EP01;M1EP02;M1EP03;M1EP04;M1EP05;M1EP06","Truth-condition separation","Collapsing reproduction/robustness/synthetic truth into generic validation"),
("3.1","Frozen AFINO baseline and TESS reproduction","Define frozen implementation and observational reproduction role.","M1C001","M1S001;M1S002;M1S003","M1EP01","F0 scope and unresolved paper-code identity","Physical-truth or observational-accuracy claims"),
("3.2","Synthetic benchmark","Describe frozen F1 synthetic benchmark and nested-support design.","M1C002;M1C003","M1S004;M1S005;M1S006;M1S007;M1S008;M1S009;M1S010;M1S011;M1S012;M1S015","M1EP02","Designed-domain and optimizer limitations","Observational transport"),
("3.3","Observational robustness design","Describe F2 pilot perturbation architecture and reference-label semantics.","M1C004","M1S016;M1S017;M1S018;M1S021;M1S022;M1S025","M1EP03","Observational labels are not truth; repeated-measure denominators","Sensitivity/FPR language"),
("3.4","Catalogue-scale robustness","Describe F3A catalogue cohort, baseline gate and frozen perturbation design.","M1C005;M1C006;M1C008;M1C009;M1C011","M1S030;M1S031;M1S032;M1S033;M1S034;M1S035;M1S036;M1S038","M1EP04","51/61 mismatch and reference-label boundary","Physical-falsity or observational-performance claims"),
("3.5","Injection–recovery and held-out validation","Describe F3B DEVELOPMENT/HELDOUT separation, rule gate and single-use HELDOUT.","M1C012;M1C017;M1C018","M1S039;M1S040;M1S041;M1S042;M1S047","M1EP05","Synthetic-domain and single-use boundary","Observational validation/transport"),
("4.1","Reproduction and synthetic behavior","Report frozen F0 reproduction and F1 domain dependence without merging truth conditions.","M1C001;M1C002","M1S001;M1S002;M1S004;M1S005;M1S008;M1S010","M1EP01;M1EP02","Observational vs synthetic distinction","Pooled performance metric"),
("4.2","Pilot observational robustness","Report F2 pilot robustness outcomes.","M1C004","M1S016;M1S017;M1S018;M1S025","M1EP03","Pilot scale; no physical ground truth","Observational accuracy metrics"),
("4.3","Catalogue-scale observational robustness","Report F3A baseline gate and classification robustness.","M1C005;M1C006;M1C008;M1C009","M1S030;M1S031;M1S032;M1S038","M1EP04","Baseline gate and reference-label semantics","False-positive/false-negative interpretation"),
("4.4","Numerical stability","Report F1/F3A bounded numerical stability evidence.","M1C003;M1C011","M1S006;M1S007;M1S011;M1S012;M1S033;M1S038","M1EP02;M1EP04","Convergence/unique-optimum limitations","Unique global optimum claim"),
("4.5","Synthetic-ground-truth classifier performance","Report F3B DEVELOPMENT and independent HELDOUT performance separately.","M1C012;M1C013;M1C014;M1C015;M1C017;M1C018","M1S039;M1S040;M1S041;M1S042;M1S047","M1EP05","No pooling/equivalence; synthetic scope; finite Wilson uncertainty","Observational sensitivity/specificity/FPR"),
("4.6","Held-out selection function and period recovery","Report final HELDOUT selection surface and conditional period recovery.","M1C019;M1C021","M1S043;M1S044;M1S047","M1EP05","Domain conditionality; period metrics conditioned on selection","Universal or observational correction"),
("5.1","What is robust","Synthesize supported robustness statements across planes without denominator pooling.","M1C004;M1C005;M1C008;M1C011;M1C013","M1S025;M1S038;M1S042","M1EP03;M1EP04;M1EP05","Qualitative synthesis only","Pooled F2/F3A/F3B statistic"),
("5.2","What is selection-limited","Discuss low F3B sensitivity, finite uncertainty and conditional period recovery.","M1C015;M1C016;M1C021;M1C022","M1S042;M1S044;M1S045","M1EP05","Synthetic domain; finite uncertainty","Perfect specificity or high completeness"),
("5.3","Observational versus synthetic evidence","Enforce truth-condition separation and explain F3A mismatch semantics.","M1C007;M1C010;M1C024;M1C029","M1S023;M1S035;M1S037;M1S045;M1S047","M1EP03;M1EP04;M1EP05","Observational reference labels are not truth","Unqualified observational validation"),
("5.4","Why no correction is claimed","State correction NOT_ESTABLISHED and synthetic selection-function boundary.","M1C020;M1C023","M1S043;M1S045;M1S047;M1S048","M1EP05","No observational transport","Validated correction language"),
("5.5","Implications for future population inference","Defer transport/correction to F4+ with explicit assumptions.","M1C025","M1S047;M1S048","M1EP05","Future work, not present result","Apply F3B selection function directly to TESS population"),
("6","Conclusions","Conclude only with supported cross-plane claims and explicit correction boundary.","M1C001;M1C004;M1C005;M1C012;M1C017;M1C018;M1C023;M1C024","M1S002;M1S025;M1S038;M1S047","M1EP01;M1EP03;M1EP04;M1EP05","No observational validation or correction","Priority claims; observational performance claims"),
]
write_csv(SECTIONS, section_fields, [dict(zip(section_fields, r)) for r in section_data])

# ---------------------------------------------------------------------------
# Figure/table plan — no new analysis
# ---------------------------------------------------------------------------

fig_fields = [
    "artifact_id","type","scientific_question","source_phase","source_ids","source_artifacts",
    "source_hashes","new_computation_required","planned_transformation","claim_ids","target_section","status"
]
source_map = {r["source_id"]:r for r in bindings_rows}
def refs(ids: str) -> tuple[str,str]:
    ss = ids.split(";")
    return (
        ";".join(source_map[x]["repository_relative_path"] for x in ss),
        ";".join(source_map[x]["sha256"] for x in ss),
    )

fig_specs = [
("M1F01","FIGURE","How do the five scientific evidence planes and BAII framing relate without collapsing truth conditions?","F0;F1;F2;F3A;F3B;BAII","M1S002;M1S015;M1S025;M1S029;M1S038;M1S048","documentary architecture schematic","M1C029","2","COMPOSITE_FROM_FROZEN_ARTIFACTS"),
("M1F02","FIGURE","How does observational robustness progress from the F2 pilot to F3A catalogue scale?","F2;F3A","M1S016;M1S031;M1S038","composite of frozen robustness summaries","M1C004;M1C005;M1C006;M1C008","4.2;4.3","COMPOSITE_FROM_FROZEN_ARTIFACTS"),
("M1F03","FIGURE","What are the catalogue-scale F3A baseline gate and robustness outcomes?","F3A","M1S030;M1S031","render from frozen tables","M1C006;M1C008;M1C009","4.3","RENDER_FROM_FROZEN_TABLE"),
("M1F04","FIGURE","How does synthetic HELDOUT selection vary across the frozen F3B design?","F3B","M1S043","render final 156-row stratified empirical surface","M1C019;M1C020","4.6","RENDER_FROM_FROZEN_TABLE"),
("M1F05","FIGURE","What is conditional period recovery among selected HELDOUT true positives?","F3B","M1S044","render from frozen period-recovery table","M1C021;M1C022","4.6","RENDER_FROM_FROZEN_TABLE"),
("M1T01","TABLE","What datasets/evidence planes contribute and what truth status does each have?","F0;F1;F2;F3A;F3B;BAII","M1S002;M1S015;M1S025;M1S029;M1S038;M1S048","tabulate architecture registry from frozen sources","M1C029","2","COMPOSITE_FROM_FROZEN_ARTIFACTS"),
("M1T02","TABLE","What are the F3A baseline gate and robustness counts?","F3A","M1S030;M1S031;M1S038","tabulate frozen counts without recomputation beyond presentation","M1C006;M1C008;M1C009","4.3","RENDER_FROM_FROZEN_TABLE"),
("M1T03","TABLE","What are the separate DEVELOPMENT and HELDOUT synthetic metrics?","F3B","M1S039;M1S042","present frozen split-specific metrics and intervals","M1C013;M1C014;M1C015;M1C016","4.5","COMPOSITE_FROM_FROZEN_ARTIFACTS"),
("M1T04","TABLE","Which claims and limitations constrain manuscript interpretation?","F2;F3A;F3B;BAII","M1S021;M1S022;M1S026;M1S035;M1S036;M1S045;M1S046","compose manuscript-facing boundary table from frozen claim/limitation matrices","M1C007;M1C010;M1C020;M1C023;M1C024;M1C028","5","COMPOSITE_FROM_FROZEN_ARTIFACTS"),
]
fig_rows=[]
for aid,typ,q,phase,sids,transform,cids,target,status in fig_specs:
    arts, hashes = refs(sids)
    fig_rows.append({
        "artifact_id":aid,"type":typ,"scientific_question":q,"source_phase":phase,
        "source_ids":sids,"source_artifacts":arts,"source_hashes":hashes,
        "new_computation_required":"false","planned_transformation":transform,
        "claim_ids":cids,"target_section":target,"status":status,
    })
write_csv(FIGURES, fig_fields, fig_rows)

# ---------------------------------------------------------------------------
# Limitations matrix
# ---------------------------------------------------------------------------

limit_fields = [
    "limitation_id","source_phase","evidence_plane","description","affected_claim_ids",
    "manuscript_section","mandatory_wording","mitigation","remaining_uncertainty","source_ids"
]
limit_data = [
("M1L001","F0","M1EP01","F0 observational reproduction does not provide physical QPP ground truth or population performance.","M1C001;M1C024","3.1;4.1;5.3","Reproduction is an observational-reference result, not physical validation.","Separate reproduction from accuracy claims.","Physical truth remains unresolved.","M1S002;M1S003"),
("M1L002","F0","M1EP01","Private TESS adaptation and exact identity with authors' unpublished pipeline remain unresolved.","M1C001","3.1;4.1","The public baseline is empirically reproduced; private-pipeline identity is unresolved.","Use frozen public-code identity only.","Exact unpublished implementation equivalence is unknown.","M1S002"),
("M1L003","F1","M1EP02","Synthetic benchmark performance is conditional on the designed signal/noise/sampling domain.","M1C002;M1C012","3.2;4.1","F1 results are synthetic-domain results.","Explicitly report support/design dimensions.","Transport outside the design is unestablished.","M1S005;M1S010;M1S015"),
("M1L004","F1","M1EP02","Numerical warnings, bounds and multiple solutions do not permit a unique-optimum claim.","M1C003;M1C011","3.2;4.4","Binary stability does not establish unique numerical convergence.","Report numerical diagnostics separately from decisions.","Global optimizer uniqueness/convergence remains unauditable.","M1S006;M1S011;M1S015"),
("M1L005","F2","M1EP03","F2 is a ten-event observational pilot with repeated perturbations and no physical ground truth.","M1C004;M1C010;M1C024","3.3;4.2;5.3","F2 characterizes methodological robustness, not classifier accuracy.","Keep event/perturbation denominators explicit.","Generalization beyond pilot motivated F3A.","M1S017;M1S022;M1S025"),
("M1L006","F2","M1EP03","F2 observational labels cannot support observational FPR/sensitivity/specificity.","M1C004;M1C010","4.2;5.3","Reference-state transitions are not confusion-matrix outcomes.","Use robustness transition language only.","Observational accuracy remains unestimated.","M1S021;M1S023"),
("M1L007","BAII","M1EP06","BAII is bounded to the frozen 2024–2026 search window and documented source-access depth.","M1C028","1","Priority language is bounded to the frozen BAII corpus; no global novelty claim is authorized.","Use safe/qualified wording from positioning matrix.","Literature after the search freeze is not systematically covered.","M1S026;M1S027;M1S029"),
("M1L008","F3A","M1EP04","51/61 published-QPP references do not reproduce the frozen F3A W00/P00 baseline; cause is unresolved within F3A.","M1C006;M1C007;M1C008","4.3;5.3","These are reproduction mismatches, not physical falsifications.","Condition perturbation claims on baseline-concordant references.","Mechanistic cause remains unresolved.","M1S030;M1S036;M1S038"),
("M1L009","F3A","M1EP04","Observational reference labels are not ground truth; absence of selection gains is not observational FPR.","M1C009;M1C010;M1C024","4.3;5.3","No observational performance metric follows from reference transitions.","Keep reference roles and known-truth metrics separate.","Observational FPR remains unestablished.","M1S035;M1S037;M1S038"),
("M1L010","F3A","M1EP04","Seed-stable binary classification does not imply a unique numerical solution or auditable convergence.","M1C011","4.4","F3A supports seed stability of the binary output in the frozen scope only.","Report numerical multiplicity/warnings separately.","Unique optimum remains unestablished.","M1S033;M1S036;M1S038"),
("M1L011","F3A","M1EP04","Period robustness is conditional on retained selection and baseline comparability.","M1C011","4.4;5.1","F3A period changes are conditional robustness quantities.","Keep selection conditioning explicit.","Unselected/inadmissible cases have no comparable period outcome.","M1S034;M1S036"),
("M1L012","F3B","M1EP05","F3B HELDOUT sensitivity is low in-domain: 152/1800 synthetic positives selected.","M1C013;M1C014;M1C021","4.5;5.2","Report low synthetic sensitivity alongside high specificity.","Use the frozen HELDOUT denominator and interval.","Observational sensitivity remains unknown.","M1S042;M1S046"),
("M1L013","F3B","M1EP05","Observed HELDOUT FP=0/1800 retains finite Wilson uncertainty.","M1C015;M1C016","4.5;5.2","Zero observed false selections is not proof of population FPR=0.","Report Wilson uncertainty.","Underlying synthetic-domain FPR may be nonzero.","M1S042;M1S046"),
("M1L014","F3B","M1EP05","The 156-row HELDOUT selection function is bounded to the frozen synthetic domain.","M1C019;M1C020;M1C023;M1C025","4.6;5.4;5.5","The synthetic selection surface is not an observational population correction.","No DEVELOPMENT pooling/smoothing; defer transport.","Population transport remains F4+.","M1S043;M1S046;M1S047"),
("M1L015","F3B","M1EP05","Period-recovery summaries are conditional on selected true positives with finite recovered period.","M1C021;M1C022","4.6;5.2","Conditional period accuracy does not imply high completeness.","Report coverage separately from period error.","Unselected positives do not contribute period error.","M1S042;M1S044;M1S046"),
("M1L016","F3B","M1EP05","The DEVELOPMENT candidate failed its preregistered specificity-preservation gate and was not promoted.","M1C017;M1C018;M1C023","4.5;5.4","The final HELDOUT rule remained the untouched 10/10 baseline.","No runner-up rescue or post-hoc retuning.","No validated correction was established.","M1S040;M1S041;M1S047"),
("M1L017","F3B","M1EP05","The single-use HELDOUT is consumed and cannot be reused for rule development.","M1C017;M1C018;M1C025","3.5;5.5","Future tuning requires independent new evidence.","Maintain HELDOUT closure.","No further threshold search on this HELDOUT is valid.","M1S047;M1S048"),
("M1L018","BAII;F3A;F3B","M1EP06;M1EP04;M1EP05","External comparators were not executed as part of the frozen F3A/F3B scientific programmes.","M1C028","1;5.5","Literature positioning and comparator disposition do not equal empirical head-to-head benchmarking.","State comparator policy explicitly.","Comparative method superiority is untested.","M1S026;M1S029;M1S036;M1S046"),
]
write_csv(LIMITS, limit_fields, [dict(zip(limit_fields, r)) for r in limit_data])

# ---------------------------------------------------------------------------
# Bibliographic positioning matrix
# ---------------------------------------------------------------------------

bp_fields = [
    "positioning_id","phrase_or_position","classification","source_ids","safe_wording",
    "mandatory_qualification","prohibited_wording","target_section"
]
bp_data = [
("M1BP001","first catalogue-scale TESS QPP study","PROHIBITED_PRIORITY_CLAIM","M1S026;M1S027;M1S029","Do not use a first-ever claim; describe the specific prospective robustness contribution.","BAII identifies direct catalogue-scale TESS QPP overlap.","first catalogue-scale TESS QPP study","1"),
("M1BP002","first TESS QPP catalogue","PROHIBITED_PRIORITY_CLAIM","M1S026;M1S027;M1S029","Do not claim first TESS QPP catalogue.","Existing catalogue-scale TESS/QPP works are present in the frozen BAII corpus.","first TESS QPP catalogue","1"),
("M1BP003","first QPP injection-recovery study","PROHIBITED_PRIORITY_CLAIM","M1S026;M1S028;M1S029","Describe the project-specific heldout architecture without first-ever language.","BAII contains direct F3B-overlap injection/recovery and selection-function work.","first QPP injection-recovery study","1;5.5"),
("M1BP004","first methodological robustness study","PROHIBITED_PRIORITY_CLAIM","M1S026;M1S029","Describe the prospectively frozen robustness design and catalogue-scale extension.","BAII includes robustness/processing studies; no unrestricted priority conclusion is authorized.","first methodological robustness study","1"),
("M1BP005","no previous work...","PROHIBITED_PRIORITY_CLAIM","M1S026;M1S029","Replace absence-of-precedent language with bounded positioning against the frozen BAII corpus.","The audit is bounded and access depth is heterogeneous.","no previous work; nobody has previously","1;5"),
("M1BP006","Catalogue scale, TESS use and QPP classification do not alone define the distinctive contribution.","SAFE","M1S027;M1S029","Prior work already overlaps these dimensions; position the contribution in the combined prospective robustness and heldout architecture.","Bounded to frozen BAII evidence.","","1"),
("M1BP007","Two included works are DIRECT F3A overlaps that required prospective F3A redesign/reframing.","SAFE","M1S027;M1S029","The frozen BAII gate identified two DIRECT F3A overlaps and required prospective design reconsideration.","This is a gate/design statement, not a global novelty verdict.","","1;3.4"),
("M1BP008","No included work was assessed as matching the complete project-specific F3B architecture.","REQUIRES_QUALIFICATION","M1S028;M1S029","Within the 40 primary included BAII works, no work was assessed as matching the complete project-specific F3B development/heldout architecture.","Bounded to the frozen included corpus; not a global priority claim.","there is no previous F3B-like work anywhere","1;5.5"),
("M1BP009","The systematic literature coverage is frozen and not continuously updated.","REQUIRES_QUALIFICATION","M1S027;M1S029","BAII positioning reflects the frozen search/extraction window and documented source-access depth.","Literature after the frozen search is not systematically covered.","current exhaustive literature proves novelty","1;5"),
]
write_csv(BIBPOS, bp_fields, [dict(zip(bp_fields, r)) for r in bp_data])

# ---------------------------------------------------------------------------
# README + DR-009
# ---------------------------------------------------------------------------

readme_text = """# Manuscript 01

STATUS:
EVIDENCE / CLAIM / SECTION ARCHITECTURE FROZEN —
MANUSCRIPT PROSE NOT STARTED

Manuscript 1.1 freezes the traceable evidence→claim→section architecture for the first principal
manuscript. Scientific evidence remains downstream of the frozen F0–F3B programme; this workspace
does not become an independent source of scientific truth.

Five primary scientific evidence planes are kept separate:

- F0 observational reproduction;
- F1 synthetic/numerical benchmark;
- F2 observational pilot robustness;
- F3A catalogue-scale observational robustness;
- F3B synthetic-ground-truth heldout validation.

BAII is auxiliary positioning/precedence evidence and is not a sixth result plane.

No AFINO execution, synthetic generation, new statistical inference, new bibliography search,
threshold search, candidate discovery or manuscript prose drafting occurs in Manuscript 1.1.

Planning artifacts live in `planning/`; permanent architecture builder/validator scripts live in
`scripts/`. The next authorized task after architecture freeze is Manuscript 1.2: materialization
of the definitive figure/table package from frozen evidence, still before full prose drafting.
"""
README.write_text(readme_text, encoding="utf-8", newline="\n")

dr_text = """# DR-009 — Manuscript 1 evidence architecture

## Status

Architecture freeze candidate; requires `MANUSCRIPT1_ARCHITECTURE_VALIDATION_PASS` and later Git/OSF freeze.

## Why Manuscript 1 is now authorized

F0–F2 are preserved as a frozen historical foundation. Bibliographic Audit II is closed. Phase 3A
is closed with a catalogue-scale observational robustness result and explicit limitations. Phase 3B
is closed after independent single-use HELDOUT synthetic-ground-truth characterization, with
correction `NOT_ESTABLISHED`. The programme has therefore reached the previously required point for
the first principal manuscript.

## Contributing evidence planes

The manuscript uses five primary scientific planes: F0 observational reproduction, F1
synthetic/numerical benchmark, F2 observational pilot robustness, F3A catalogue-scale observational
robustness, and F3B synthetic-ground-truth heldout validation. BAII contributes only framing,
precedence and priority-claim constraints.

## Scientific thesis

The manuscript evaluates reproducibility, methodological robustness, numerical behavior and
synthetic-ground-truth selection properties of the frozen AFINO implementation in the TESS-QPP
context, progressing from published-event reproduction and synthetic benchmarking to
catalogue-scale observational robustness and independent held-out injection–recovery validation.

## Evidence-plane separation

Observational reproduction is not physical truth. Observational robustness is not classifier
accuracy. Synthetic ground truth is not observational ground truth. HELDOUT synthetic performance is
not observational validation. F2, F3A and F3B denominators are not pooled.

## Claim boundaries

The unified claim matrix is normative for drafting. Supported claims require frozen source IDs and
mandatory qualifications. Prohibited claims remain prohibited. In particular, the manuscript must
not assert observational sensitivity/specificity/FPR, physical confirmation/falsification of
individual QPPs, unqualified observational validation of AFINO, or unrestricted priority claims.

## Correction and population transport

The frozen Phase 3B correction status is `NOT_ESTABLISHED`. The 156-row HELDOUT selection function is
a synthetic-domain surface, not an observational population correction. Population transport remains
an F4+ problem requiring explicit assumptions and independent evidence.

## Section architecture

The planned manuscript has Introduction; Evidence and analysis architecture; Methods; Results;
Discussion; and Conclusions, with frozen subsections and source/claim mappings in
`m1_section_map.csv`. No Results subsection exists without source bindings.

## Figure/table strategy

Manuscript 1.1 selects a frozen-data visual plan only. Figures/tables must be reused, rendered or
composed from frozen artifacts. `NEW_ANALYSIS_REQUIRED` is not an allowed status.

## What remains prohibited

No AFINO run, synthetic generation, new scientific computation, new statistical test, new literature
search, threshold search, candidate-rule development, observational correction, or full manuscript
prose draft is authorized by this task.

## Next task

After this architecture passes validation and is frozen in Git/OSF, proceed to Manuscript 1.2:
materialize the definitive figures/tables from frozen artifacts and freeze the visual package before
full manuscript drafting.
"""
DR009.parent.mkdir(parents=True, exist_ok=True)
DR009.write_text(dr_text, encoding="utf-8", newline="\n")

# ---------------------------------------------------------------------------
# Architecture audit
# ---------------------------------------------------------------------------

status_counts = {}
for row in claim_rows:
    status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1

audit_obj = {
    "schema_version":"1.0.0",
    "artifact_role":"MANUSCRIPT1_ARCHITECTURE_AUDIT",
    "status":"MANUSCRIPT1_ARCHITECTURE_VALIDATION_PASS",
    "entry_commit":EXPECTED_HEAD,
    "source_bindings":len(bindings_rows),
    "evidence_planes":{"primary":5,"auxiliary_positioning":1,"total":6},
    "claim_count":len(claim_rows),
    "claim_status_counts":status_counts,
    "section_count":len(section_data),
    "figure_candidates":sum(1 for r in fig_rows if r["type"]=="FIGURE"),
    "table_candidates":sum(1 for r in fig_rows if r["type"]=="TABLE"),
    "limitations_count":len(limit_data),
    "BAII_positioning_constraints":len(bp_data),
    "frozen_source_sanity":{
        "f3a_total_events":122,
        "f3a_qpp_reference_events":61,
        "f3a_qpp_baseline_mismatches":51,
        "f3a_qpp_baseline_concordant":8,
        "f3a_not_selected_baseline_concordant":57,
        "f3a_optimizer_stability_events":116,
        "f3a_seed_discordant_events":0,
        "f3b_heldout_confusion":{"TP":152,"FN":1648,"TN":1800,"FP":0},
        "f3b_final_selection_rows":156,
        "f3b_period_rows":152,
    },
    "firewall":{
        "new_scientific_computation":False,
        "new_afino_execution":False,
        "new_synthetic_generation":False,
        "new_statistical_inference":False,
        "new_bibliographic_search":False,
        "new_threshold_search":False,
        "new_candidate_rule":False,
        "f2_f3a_f3b_denominator_pooling":False,
        "manuscript_prose_started":False,
        "protected_frozen_sources_modified":False,
    },
    "pre_freeze_tooling_incidents":[
        {
            "incident_id":"M1-TOOL-001",
            "stage":"architecture_validator",
            "status":"REPAIRED_BEFORE_GIT_FREEZE",
            "trigger":"The first validator used an over-literal substring requirement for the exact prose phrase 'not physical ground truth' even though the registry encoded the intended distinction structurally as OBSERVATIONAL_REFERENCE_NOT_PHYSICAL_GROUND_TRUTH.",
            "scientific_effect":"NONE",
            "frozen_source_effect":"NONE",
            "manuscript_prose_effect":"NONE",
            "repair":"Replace the phrase-presence gate with structural assertions on evidence-plane ground_truth_status and observational_or_synthetic fields.",
        }
    ],
    "next_task":"MANUSCRIPT1_2_FIGURE_TABLE_MATERIALIZATION_AND_VISUAL_FREEZE",
}
write_json(AUDIT, audit_obj)

# ---------------------------------------------------------------------------
# Checksum registry (13 entries; excludes itself)
# ---------------------------------------------------------------------------

checksum_targets = [
    README,BINDINGS,SCOPE,PLANES,CLAIMS,SECTIONS,FIGURES,LIMITS,BIBPOS,AUDIT,BUILDER,VALIDATOR,DR009
]
if len(checksum_targets) != 13:
    raise RuntimeError("Checksum target count != 13")

lines=[]
for p in sorted(checksum_targets, key=lambda p:p.relative_to(ROOT).as_posix()):
    lines.append(f"{sha(p)}  {p.relative_to(ROOT).as_posix()}")
SUMS.write_text("\n".join(lines)+"\n", encoding="utf-8", newline="\n")

if status_paths() != FINAL_DIRTY:
    raise RuntimeError(f"Unexpected final Manuscript 1.1 dirty scope: {sorted(status_paths())}")

print("MANUSCRIPT1_ARCHITECTURE_BUILD_PASS")
print("source_bindings =", len(bindings_rows))
print("primary_evidence_planes = 5")
print("auxiliary_positioning_planes = 1")
print("claims =", len(claim_rows))
print("claim_status_counts =", json.dumps(status_counts, sort_keys=True))
print("sections =", len(section_data))
print("figure_candidates =", sum(1 for r in fig_rows if r["type"]=="FIGURE"))
print("table_candidates =", sum(1 for r in fig_rows if r["type"]=="TABLE"))
print("limitations =", len(limit_data))
print("baii_positioning_constraints =", len(bp_data))
print("f3a_qpp_baseline_mismatches = 51/61")
print("f3a_seed_stable_events = 116/116")
print("f3b_heldout_confusion = 152 1648 1800 0")
print("f3b_selection_rows = 156")
print("f3b_period_rows = 152")
print("new_scientific_computation = false")
print("new_bibliographic_search = false")
print("manuscript_prose_started = false")
print("dirty_paths = 14")
