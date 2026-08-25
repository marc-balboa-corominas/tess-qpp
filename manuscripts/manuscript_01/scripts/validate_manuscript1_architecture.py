from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

EXPECTED_HEAD = "b501fa16c3b3af5d6105df38421995e5d5600763"

ROOT = Path(__file__).resolve().parents[3]
M1 = ROOT / "manuscripts/manuscript_01"
PLANNING = M1 / "planning"

README = M1 / "README.md"
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
DR009 = ROOT / "docs/decisions/DR-009-manuscript1-evidence-architecture.md"

ALLOWED_STATUSES = {
    "SUPPORTED_NOW",
    "SUPPORTED_WITH_EXPLICIT_LIMITATION",
    "POSITIONING_ONLY",
    "DEFER_TO_F4_PLUS",
    "PROHIBITED",
}
ALLOWED_FIG_STATUSES = {
    "REUSE_FROZEN_ARTIFACT",
    "RENDER_FROM_FROZEN_TABLE",
    "COMPOSITE_FROM_FROZEN_ARTIFACTS",
    "NOT_SELECTED",
}
REQUIRED_PRIMARY = {
    "M1EP01":"F0_OBSERVATIONAL_REPRODUCTION",
    "M1EP02":"F1_SYNTHETIC_NUMERICAL_BENCHMARK",
    "M1EP03":"F2_OBSERVATIONAL_PILOT_ROBUSTNESS",
    "M1EP04":"F3A_CATALOGUE_SCALE_OBSERVATIONAL_ROBUSTNESS",
    "M1EP05":"F3B_SYNTHETIC_GROUND_TRUTH_VALIDATION",
}
REQUIRED_AUX = {"M1EP06":"BAII_POSITIONING_AND_PRECEDENCE"}

def git(*args: str) -> str:
    return subprocess.run(
        ["git","-C",str(ROOT),*args],
        check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE
    ).stdout.rstrip("\r\n")

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def rows(path: Path):
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

# Entry boundary remains Phase 3B closure while precommit.
if git("rev-parse","HEAD") != EXPECTED_HEAD:
    # Permanent postcommit compatibility: current HEAD must descend from entry.
    subprocess.run(
        ["git","-C",str(ROOT),"merge-base","--is-ancestor",EXPECTED_HEAD,git("rev-parse","HEAD")],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL
    )

# Checksum registry.
sum_lines=[x for x in SUMS.read_text(encoding="utf-8").splitlines() if x.strip()]
if len(sum_lines)!=13:
    raise RuntimeError(f"architecture checksum entries != 13: {len(sum_lines)}")
for line in sum_lines:
    expected,rel=line.split("  ",1)
    p=ROOT/rel
    if not p.is_file() or sha(p)!=expected:
        raise RuntimeError(f"architecture checksum mismatch: {rel}")

# Source bindings.
bindings=json.loads(BINDINGS.read_text(encoding="utf-8"))
if bindings["source_count"] != 48 or len(bindings["sources"]) != 48:
    raise RuntimeError("source binding count != 48")
sid_map={r["source_id"]:r for r in bindings["sources"]}
if len(sid_map)!=48:
    raise RuntimeError("duplicate source IDs")
for sid,r in sid_map.items():
    p=ROOT/r["repository_relative_path"]
    if not p.is_file():
        raise RuntimeError(f"bound source missing: {sid}")
    if sha(p)!=r["sha256"] or p.stat().st_size!=r["bytes"]:
        raise RuntimeError(f"bound source identity changed: {sid}")
    if r["phase"] in {"F0","F1","F2"}:
        if r["freeze_tag"] is not None:
            raise RuntimeError(f"historical F0-F2 source unexpectedly assigned a dedicated tag: {sid}")
        last=git("log","-1","--format=%H","--",r["repository_relative_path"])
        if last!=r["freeze_commit"]:
            raise RuntimeError(f"historical source freeze commit changed: {sid}")
    else:
        if not r["freeze_tag"]:
            raise RuntimeError(f"missing freeze tag: {sid}")
        if git("rev-list","-n","1",r["freeze_tag"])!=r["freeze_commit"]:
            raise RuntimeError(f"freeze tag/commit mismatch: {sid}")

fw=bindings["execution_firewall"]
if any(fw[k] for k in [
    "new_scientific_computation","new_afino_execution","new_synthetic_generation",
    "new_statistical_inference","new_bibliographic_search","manuscript_prose_started"
]):
    raise RuntimeError("source-binding firewall violated")

# Evidence planes.
planes=rows(PLANES)
if len(planes)!=6:
    raise RuntimeError("evidence plane rows != 6")
by_id={r["evidence_plane_id"]:r for r in planes}
for pid,name in REQUIRED_PRIMARY.items():
    if pid not in by_id or by_id[pid]["plane_name"]!=name or by_id[pid]["plane_type"]!="PRIMARY_SCIENTIFIC":
        raise RuntimeError(f"primary evidence plane mismatch: {pid}")
for pid,name in REQUIRED_AUX.items():
    if pid not in by_id or by_id[pid]["plane_name"]!=name or by_id[pid]["plane_type"]!="AUXILIARY_NON_RESULT":
        raise RuntimeError("BAII auxiliary evidence plane mismatch")
if sum(r["plane_type"]=="PRIMARY_SCIENTIFIC" for r in planes)!=5:
    raise RuntimeError("primary evidence plane count != 5")

# Central semantic distinctions are structural, not dependent on one exact prose phrase.
expected_plane_semantics = {
    "M1EP01": ("OBSERVATIONAL_REFERENCE_NOT_PHYSICAL_GROUND_TRUTH", "OBSERVATIONAL"),
    "M1EP02": ("SYNTHETIC_KNOWN_TRUTH_WITHIN_DESIGNED_DOMAIN", "SYNTHETIC"),
    "M1EP03": ("OBSERVATIONAL_REFERENCE_NOT_PHYSICAL_GROUND_TRUTH", "OBSERVATIONAL"),
    "M1EP04": ("OBSERVATIONAL_REFERENCE_NOT_PHYSICAL_GROUND_TRUTH", "OBSERVATIONAL"),
    "M1EP05": ("SYNTHETIC_KNOWN_TRUTH_WITH_INDEPENDENT_HELDOUT", "SYNTHETIC"),
}
for pid, (truth_status, domain_kind) in expected_plane_semantics.items():
    if by_id[pid]["ground_truth_status"] != truth_status:
        raise RuntimeError(f"evidence-plane ground-truth status mismatch: {pid}")
    if by_id[pid]["observational_or_synthetic"] != domain_kind:
        raise RuntimeError(f"evidence-plane domain-kind mismatch: {pid}")

registry_text="\n".join(
    r["what_it_establishes"]+" "+r["what_it_does_not_establish"]+" "+r["ground_truth_status"]
    for r in planes
).lower()
for required in ["synthetic", "observational validation"]:
    if required not in registry_text:
        raise RuntimeError(f"evidence-plane semantic boundary missing: {required}")

# Claims.
claims=rows(CLAIMS)
if len(claims)!=29:
    raise RuntimeError(f"claim count != 29: {len(claims)}")
claim_map={r["claim_id"]:r for r in claims}
if len(claim_map)!=29:
    raise RuntimeError("duplicate claim IDs")
for r in claims:
    if r["status"] not in ALLOWED_STATUSES:
        raise RuntimeError(f"unauthorized claim status: {r['status']}")
    sids=[x for x in r["source_ids"].split(";") if x]
    if not sids:
        raise RuntimeError(f"claim without source IDs: {r['claim_id']}")
    if any(s not in sid_map for s in sids):
        raise RuntimeError(f"claim has unknown source ID: {r['claim_id']}")
    if r["status"].startswith("SUPPORTED") and not r["allowed_wording"]:
        raise RuntimeError(f"supported claim missing allowed wording: {r['claim_id']}")

if claim_map["M1C026"]["status"]!="PROHIBITED":
    raise RuntimeError("observational-validation positive claim not prohibited")
if claim_map["M1C027"]["status"]!="PROHIBITED":
    raise RuntimeError("observational-correction positive claim not prohibited")
if claim_map["M1C025"]["status"]!="DEFER_TO_F4_PLUS":
    raise RuntimeError("population transport not deferred to F4+")

# Section map.
sections=rows(SECTIONS)
section_ids={r["section_id"] for r in sections}
for r in sections:
    cids=[x for x in r["allowed_claim_ids"].split(";") if x]
    sids=[x for x in r["required_source_ids"].split(";") if x]
    if any(c not in claim_map for c in cids):
        raise RuntimeError(f"section references unknown claim: {r['section_id']}")
    if any(s not in sid_map for s in sids):
        raise RuntimeError(f"section references unknown source: {r['section_id']}")
    if r["section_id"].startswith("4.") and not sids:
        raise RuntimeError(f"Results subsection has no source binding: {r['section_id']}")
    if any(claim_map[c]["status"]=="PROHIBITED" for c in cids):
        raise RuntimeError(f"section authorizes prohibited claim: {r['section_id']}")

# Figure/table plan.
figs=rows(FIGURES)
if len(figs)!=9:
    raise RuntimeError("figure/table plan rows != 9")
for r in figs:
    if r["status"] not in ALLOWED_FIG_STATUSES:
        raise RuntimeError(f"invalid figure/table status: {r['status']}")
    if r["status"]=="NEW_ANALYSIS_REQUIRED":
        raise RuntimeError("NEW_ANALYSIS_REQUIRED is forbidden")
    if r["new_computation_required"].lower()!="false":
        raise RuntimeError(f"new computation requested: {r['artifact_id']}")
    for cid in [x for x in r["claim_ids"].split(";") if x]:
        if cid not in claim_map:
            raise RuntimeError(f"figure/table references unknown claim: {r['artifact_id']}")
    for sid in [x for x in r["source_ids"].split(";") if x]:
        if sid not in sid_map:
            raise RuntimeError(f"figure/table references unknown source: {r['artifact_id']}")

# Limitations and BAII positioning.
limits=rows(LIMITS)
if len(limits)<9:
    raise RuntimeError("limitations matrix too small")
for r in limits:
    if not r["source_ids"]:
        raise RuntimeError(f"limitation missing provenance: {r['limitation_id']}")
    if any(s not in sid_map for s in r["source_ids"].split(";")):
        raise RuntimeError(f"limitation unknown source: {r['limitation_id']}")

bp=rows(BIBPOS)
if len(bp)<9:
    raise RuntimeError("BAII positioning matrix too small")
required_prohibited={
    "first catalogue-scale TESS QPP study",
    "first TESS QPP catalogue",
    "first QPP injection-recovery study",
    "first methodological robustness study",
    "no previous work...",
}
actual_prohibited={r["phrase_or_position"] for r in bp if r["classification"]=="PROHIBITED_PRIORITY_CLAIM"}
if not required_prohibited.issubset(actual_prohibited):
    raise RuntimeError("required BAII prohibited priority claims missing")
if any(r["classification"] not in {"SAFE","REQUIRES_QUALIFICATION","PROHIBITED_PRIORITY_CLAIM"} for r in bp):
    raise RuntimeError("invalid BAII positioning classification")

# Core frozen numerical identities are checked from sources, not invented.
f3a_base=rows(ROOT/"workflows/phase3a/evidence/tables/f3a5_reference_baseline_audit.csv")
qpp=[r for r in f3a_base if r["observational_reference_role"]=="PUBLISHED_QPP_REFERENCE"]
ns=[r for r in f3a_base if r["observational_reference_role"]=="PUBLISHED_NOT_SELECTED_REFERENCE"]
if len(f3a_base)!=122 or len(qpp)!=61 or len(ns)!=61:
    raise RuntimeError("F3A event identities changed")
if sum(r["baseline_gate_state"]=="REFERENCE_BASELINE_MISMATCH" for r in qpp)!=51:
    raise RuntimeError("F3A 51/61 mismatch identity changed")
if sum(r["baseline_gate_state"]=="REFERENCE_CONCORDANT" for r in ns)!=57:
    raise RuntimeError("F3A not-selected concordance identity changed")

stab=rows(ROOT/"workflows/phase3a/evidence/tables/f3a5_optimizer_stability.csv")
if len(stab)!=116 or any(int(r["discordant_vs_seed0_count"])!=0 for r in stab):
    raise RuntimeError("F3A seed-stability identity changed")

held=json.loads((ROOT/"workflows/phase3b/heldout/evaluation/evidence/reports/f3b7_heldout_baseline_metrics.json").read_text(encoding="utf-8"))
cm=held["confusion_matrix"]
if (cm["TP"],cm["FN"],cm["TN"],cm["FP"])!=(152,1648,1800,0):
    raise RuntimeError("F3B HELDOUT confusion identity changed")
if len(rows(ROOT/"workflows/phase3b/heldout/evaluation/evidence/tables/f3b7_heldout_selection_function.csv"))!=156:
    raise RuntimeError("F3B selection rows changed")
if len(rows(ROOT/"workflows/phase3b/heldout/evaluation/evidence/tables/f3b7_heldout_period_recovery.csv"))!=152:
    raise RuntimeError("F3B period rows changed")

# Audit.
audit=json.loads(AUDIT.read_text(encoding="utf-8"))
if audit["status"]!="MANUSCRIPT1_ARCHITECTURE_VALIDATION_PASS":
    raise RuntimeError("architecture audit status mismatch")
if audit["evidence_planes"]!={"primary":5,"auxiliary_positioning":1,"total":6}:
    raise RuntimeError("audit evidence-plane counts mismatch")
if audit["claim_count"]!=29 or audit["section_count"]!=len(sections):
    raise RuntimeError("audit row counts mismatch")
if audit["figure_candidates"]!=5 or audit["table_candidates"]!=4:
    raise RuntimeError("audit figure/table counts mismatch")
if audit["limitations_count"]!=len(limits) or audit["BAII_positioning_constraints"]!=len(bp):
    raise RuntimeError("audit limitations/BAII counts mismatch")
for k,v in audit["firewall"].items():
    if v is not False:
        raise RuntimeError(f"architecture firewall violated: {k}")

# Scope/README/DR no manuscript prose and claim firewall.
surface="\n".join([
    README.read_text(encoding="utf-8"),
    SCOPE.read_text(encoding="utf-8"),
    DR009.read_text(encoding="utf-8"),
]).lower()
for required in [
    "manuscript prose not started",
    "not observational",
    "correction",
]:
    if required not in surface:
        raise RuntimeError(f"architecture surface missing boundary: {required}")

for name in ["manuscript.tex","main.md","abstract.md","introduction.md","discussion.md"]:
    if list(M1.rglob(name)):
        raise RuntimeError(f"prohibited manuscript prose file exists: {name}")

# No protected frozen source modified relative to entry commit in any post-entry commit.
head=git("rev-parse","HEAD")
if head!=EXPECTED_HEAD:
    changed=[x for x in git("diff","--name-only",f"{EXPECTED_HEAD}..{head}").splitlines() if x]
    for rel in changed:
        if rel.startswith(("foundation/f0-f2/","docs/literature/bibliographic_audit_ii/","workflows/phase3a/","workflows/phase3b/")):
            raise RuntimeError(f"protected frozen source modified after entry: {rel}")

print("MANUSCRIPT1_ARCHITECTURE_VALIDATION_PASS")
print("source_bindings = 48")
print("primary_evidence_planes = 5")
print("auxiliary_positioning_planes = 1")
print("claims = 29")
print("sections =", len(sections))
print("figure_candidates = 5")
print("table_candidates = 4")
print("limitations =", len(limits))
print("baii_positioning_constraints =", len(bp))
print("f3a_qpp_baseline_mismatches = 51/61")
print("f3a_seed_stable_events = 116/116")
print("f3b_heldout_confusion = 152 1648 1800 0")
print("f3b_selection_rows = 156")
print("f3b_period_rows = 152")
print("new_scientific_computation = false")
print("new_afino_execution = false")
print("new_synthetic_generation = false")
print("new_statistical_inference = false")
print("new_bibliographic_search = false")
print("f2_f3a_f3b_denominator_pooling = false")
print("manuscript_prose_started = false")
