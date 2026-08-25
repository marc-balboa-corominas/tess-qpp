from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
M1 = ROOT/"manuscripts/manuscript_01"
VIS = M1/"visuals"
PLAN = M1/"planning/m1_figure_table_plan.csv"
ARCH_VALIDATOR = M1/"scripts/validate_manuscript1_architecture.py"

CONFIG = VIS/"config/m1_2_visual_rendering_contract.json"
VBIND = VIS/"evidence/m1_2_visual_source_bindings.json"
MANIFEST = VIS/"evidence/m1_2_visual_manifest.csv"
VALUES = VIS/"evidence/m1_2_rendered_value_audit.csv"
AUDIT = VIS/"evidence/m1_2_visual_audit.json"
SUMS = VIS/"evidence/SHA256SUMS.txt"

ENTRY_COMMIT="52024ec3728eeda25f9d640d8f1395a87671c541"
ENTRY_TAG="manuscript1-architecture-v1"


def git(*args):
    return subprocess.run(["git","-C",str(ROOT),*args],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.rstrip("\r\n")


def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def rows(path):
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


# Architecture must remain valid.
proc=subprocess.run([sys.executable,str(ARCH_VALIDATOR)],cwd=str(ROOT))
if proc.returncode != 0:
    raise RuntimeError("MANUSCRIPT1_ARCHITECTURE_VALIDATION_PASS prerequisite failed")

if git("rev-list","-n","1",ENTRY_TAG)!=ENTRY_COMMIT:
    raise RuntimeError("M1.1 architecture tag changed")

# M1.1 planning tree and prior frozen sources may never be modified after entry.
head=git("rev-parse","HEAD")
if head!=ENTRY_COMMIT:
    changed=[x for x in git("diff","--name-only",f"{ENTRY_COMMIT}..{head}").splitlines() if x]
    for rel in changed:
        if rel.startswith((
            "foundation/f0-f2/",
            "docs/literature/bibliographic_audit_ii/",
            "workflows/phase3a/",
            "workflows/phase3b/",
            "manuscripts/manuscript_01/planning/",
        )):
            raise RuntimeError(f"protected frozen source modified after M1.1: {rel}")

contract=json.loads(CONFIG.read_text(encoding="utf-8"))
if contract["entry_architecture_commit"]!=ENTRY_COMMIT:
    raise RuntimeError("visual contract entry mismatch")
for k in ["new_scientific_computation","new_statistical_inference","new_source_artifact"]:
    if contract[k] is not False:
        raise RuntimeError(f"rendering contract firewall violated: {k}")
if contract["primary_figure_format"]!="PDF" or contract["preview_figure_format"]!="PNG":
    raise RuntimeError("figure format contract changed")
if contract["minimum_png_dpi"]!=300:
    raise RuntimeError("PNG DPI contract changed")
if contract["vector_text_required"] is not True:
    raise RuntimeError("vector-text contract changed")
if contract["color_only_encoding_forbidden"] is not True:
    raise RuntimeError("color-only firewall changed")
if contract["missing_or_structural_no_exposure_must_not_be_rendered_as_zero"] is not True:
    raise RuntimeError("structural no-exposure contract changed")

plan=rows(PLAN)
plan_map={r["artifact_id"]:r for r in plan}
expected_ids=[f"M1F0{i}" for i in range(1,6)]+[f"M1T0{i}" for i in range(1,5)]
if [r["artifact_id"] for r in plan]!=expected_ids:
    raise RuntimeError("M1.1 visual plan IDs changed")

bindings=json.loads(VBIND.read_text(encoding="utf-8"))
source_map={r["source_id"]:r for r in bindings["sources"]}
for sid,b in source_map.items():
    p=ROOT/b["repository_relative_path"]
    if not p.is_file() or sha(p)!=b["sha256"] or p.stat().st_size!=b["bytes"]:
        raise RuntimeError(f"visual source binding mismatch: {sid}")

manifest=rows(MANIFEST)
if len(manifest)!=18:
    raise RuntimeError("visual manifest rows != 18")
counts=Counter((r["artifact_id"],r["format"]) for r in manifest)
for aid in expected_ids:
    expected_formats={"PDF","PNG"} if aid.startswith("M1F") else {"CSV","TEX"}
    got={fmt for (a,fmt),n in counts.items() if a==aid and n==1}
    if got!=expected_formats:
        raise RuntimeError(f"rendered formats wrong for {aid}: {got}")
    for r in [x for x in manifest if x["artifact_id"]==aid]:
        # Normative M1.1 source/claim IDs must remain exactly unchanged in the manifest.
        if r["source_ids"]!=plan_map[aid]["source_ids"]:
            raise RuntimeError(f"normative source IDs changed in manifest: {aid}")
        if r["claim_ids"]!=plan_map[aid]["claim_ids"]:
            raise RuntimeError(f"normative claim IDs changed in manifest: {aid}")
        p=ROOT/r["rendered_path"]
        if not p.is_file() or sha(p)!=r["sha256"] or p.stat().st_size!=int(r["bytes"]):
            raise RuntimeError(f"rendered artifact identity mismatch: {r['rendered_path']}")

# PDFs and PNGs.
for r in manifest:
    p=ROOT/r["rendered_path"]
    if r["format"]=="PDF":
        data=p.read_bytes()
        if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
            raise RuntimeError(f"invalid PDF structure: {p}")
        if b"/Font" not in data:
            raise RuntimeError(f"PDF lacks font resource / vector-text evidence: {p}")
    elif r["format"]=="PNG":
        with Image.open(p) as im:
            im.verify()
        with Image.open(p) as im:
            dpi=im.info.get("dpi",(0,0))
            if min(dpi)<299:
                raise RuntimeError(f"PNG DPI below target: {p} dpi={dpi}")
            if im.width<1200 or im.height<900:
                raise RuntimeError(f"PNG pixel dimensions unexpectedly small: {p} {im.size}")

# Rendered-value audit.
vals=rows(VALUES)
if not vals:
    raise RuntimeError("rendered-value audit empty")
if len({r["rendered_value_id"] for r in vals})!=len(vals):
    raise RuntimeError("duplicate rendered-value IDs")
allowed_status={
    "EXACT_SOURCE_VALUE","DIRECT_CATEGORICAL_COUNT","DETERMINISTIC_LABEL_FORMAT",
    "EXACT_SOURCE_PAIR","STRUCTURAL_NO_EXPOSURE_PRESERVED",
}
if any(r["exact_match_status"] not in allowed_status for r in vals):
    raise RuntimeError("rendered-value audit contains FAIL/unknown status")
if any(r["source_id"] not in source_map for r in vals):
    raise RuntimeError("rendered-value audit uses source outside frozen visual bindings")

struct=[r for r in vals if r["artifact_id"]=="M1F04" and r["exact_match_status"]=="STRUCTURAL_NO_EXPOSURE_PRESERVED"]
if len(struct)!=9:
    raise RuntimeError(f"STRUCTURAL_NO_EXPOSURE audit rows != 9: {len(struct)}")
if any(r["displayed_value"]=="0" or r["source_value"]=="0" for r in struct):
    raise RuntimeError("STRUCTURAL_NO_EXPOSURE mapped to zero")

sf=rows(ROOT/source_map["M1S043"]["repository_relative_path"])
if len(sf)!=156 or sum(r["exposure_status"]=="STRUCTURAL_NO_EXPOSURE" for r in sf)!=9:
    raise RuntimeError("frozen selection-function identity changed")

pr=rows(ROOT/source_map["M1S044"]["repository_relative_path"])
if len(pr)!=152:
    raise RuntimeError("period recovery rows != 152")

# Table-specific interpretation guards.
t03=(VIS/"tables/M1T03_synthetic_performance.csv").read_text(encoding="utf-8")
if "Synthetic-ground-truth performance within the frozen design. No observational performance inference." not in t03:
    raise RuntimeError("M1T03 synthetic-only interpretation footer/scope missing")
if "DEVELOPMENT" not in t03 or "HELDOUT" not in t03:
    raise RuntimeError("M1T03 split-specific structure missing")

t02=(VIS/"tables/M1T02_f3a_robustness_counts.csv").read_text(encoding="utf-8")
if "295 / 171" not in t02 or "3178 / 0" not in t02:
    raise RuntimeError("F3A transition counts missing")
for forbidden in ["true positive","true negative","false positive","false negative"]:
    if forbidden in t02.lower():
        raise RuntimeError("F3A observational table uses confusion-matrix terminology")

audit=json.loads(AUDIT.read_text(encoding="utf-8"))
if audit["status"]!="M1_VISUAL_PACKAGE_VALIDATION_PASS":
    raise RuntimeError("visual audit status mismatch")
if (audit["figures"],audit["tables"],audit["figure_pdf"],audit["figure_png"],audit["table_csv"],audit["table_tex"])!=(5,4,5,5,4,4):
    raise RuntimeError("visual audit file counts mismatch")
if audit["all_source_bindings_verified"] is not True or audit["all_visible_scientific_values_source_mapped"] is not True:
    raise RuntimeError("visual audit traceability failed")
if audit["f3a_frozen_counts"]["qpp_baseline_mismatch"]!="51/61":
    raise RuntimeError("F3A mismatch identity changed")
if audit["f3a_frozen_counts"]["transitions"]!="295/171/3178/0":
    raise RuntimeError("F3A transitions identity changed")
if audit["f3b_frozen_counts"]!={
    "development_confusion":"143/1657/1799/1",
    "heldout_confusion":"152/1648/1800/0",
    "selection_function_rows":156,
    "structural_no_exposure":9,
    "period_rows":152,
}:
    raise RuntimeError("F3B visual audit identities changed")
for k in ["new_scientific_computation","new_statistical_inference","new_bibliographic_search","new_afino_execution","new_synthetic_generation","manuscript_full_prose_started"]:
    if audit[k] is not False:
        raise RuntimeError(f"visual audit firewall violated: {k}")
if audit["interpretation_firewalls"]["f2_f3a_denominators_pooled"] is not False:
    raise RuntimeError("F2/F3A pooling firewall violated")
if audit["interpretation_firewalls"]["development_heldout_pooled"] is not False:
    raise RuntimeError("DEVELOPMENT/HELDOUT pooling firewall violated")
if audit["interpretation_firewalls"]["f3a_observational_confusion_labels_used"] is not False:
    raise RuntimeError("F3A confusion-label firewall violated")
if audit["interpretation_firewalls"]["heldout_fp_zero_described_as_population_fpr_zero"] is not False:
    raise RuntimeError("HELDOUT FP interpretation firewall violated")

# 28-entry M1.2 checksum registry.
sum_lines=[x for x in SUMS.read_text(encoding="utf-8").splitlines() if x.strip()]
if len(sum_lines)!=28:
    raise RuntimeError(f"M1.2 checksum entries != 28: {len(sum_lines)}")
for line in sum_lines:
    expected,rel=line.split("  ",1)
    p=ROOT/rel
    if not p.is_file() or sha(p)!=expected:
        raise RuntimeError(f"M1.2 checksum mismatch: {rel}")

# Required README status.
readme=(VIS/"README.md").read_text(encoding="utf-8")
if "STATUS:\nDEFINITIVE FIGURE / TABLE PACKAGE FROZEN —\nFULL MANUSCRIPT PROSE NOT STARTED" not in readme:
    raise RuntimeError("visual README status block missing")

# No full manuscript prose.
for name in ["manuscript.tex","main.md","abstract.md","introduction.md","discussion.md","results.md","conclusions.md"]:
    if list(M1.rglob(name)):
        raise RuntimeError(f"full manuscript prose file exists: {name}")

# Run independent tests.
test_path=M1/"tests/test_manuscript1_visual_package.py"
proc=subprocess.run([sys.executable,"-m","pytest","-q",str(test_path)],cwd=str(ROOT))
if proc.returncode!=0:
    raise RuntimeError("M1.2 visual package pytest failed")

print("M1_VISUAL_PACKAGE_VALIDATION_PASS")
print("figures = 5")
print("tables = 4")
print("figure_pdf = 5")
print("figure_png = 5")
print("table_csv = 4")
print("table_tex = 4")
print("visual_manifest_rows = 18")
print("rendered_value_audit_rows =",len(vals))
print("all_source_bindings_verified = true")
print("all_visible_scientific_values_source_mapped = true")
print("M1F04_selection_rows = 156")
print("M1F04_structural_no_exposure = 9")
print("M1F05_period_rows = 152")
print("new_scientific_computation = false")
print("new_statistical_inference = false")
print("new_bibliographic_search = false")
print("new_afino_execution = false")
print("new_synthetic_generation = false")
print("manuscript_full_prose_started = false")
