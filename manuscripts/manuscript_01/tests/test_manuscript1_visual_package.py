from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
M1 = ROOT/"manuscripts/manuscript_01"
VIS = M1/"visuals"


def rows(path):
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def test_complete_visual_artifact_set():
    manifest=rows(VIS/"evidence/m1_2_visual_manifest.csv")
    assert len(manifest)==18
    ids=Counter(r["artifact_id"] for r in manifest)
    for i in range(1,6):
        assert ids[f"M1F0{i}"]==2
    for i in range(1,5):
        assert ids[f"M1T0{i}"]==2


def test_figure_files_and_png_dpi():
    manifest=rows(VIS/"evidence/m1_2_visual_manifest.csv")
    pdfs=[r for r in manifest if r["format"]=="PDF"]
    pngs=[r for r in manifest if r["format"]=="PNG"]
    assert len(pdfs)==5
    assert len(pngs)==5
    for r in pdfs:
        data=(ROOT/r["rendered_path"]).read_bytes()
        assert data.startswith(b"%PDF-")
        assert b"%%EOF" in data[-2048:]
        assert b"/Font" in data
    for r in pngs:
        p=ROOT/r["rendered_path"]
        with Image.open(p) as im:
            assert min(im.info.get("dpi",(0,0)))>=299
            assert im.width>=1200 and im.height>=900


def test_table_files():
    manifest=rows(VIS/"evidence/m1_2_visual_manifest.csv")
    assert len([r for r in manifest if r["format"]=="CSV"])==4
    assert len([r for r in manifest if r["format"]=="TEX"])==4


def test_plan_ids_and_normative_bindings_unchanged():
    plan=rows(M1/"planning/m1_figure_table_plan.csv")
    plan_map={r["artifact_id"]:r for r in plan}
    manifest=rows(VIS/"evidence/m1_2_visual_manifest.csv")
    assert set(plan_map)=={f"M1F0{i}" for i in range(1,6)}|{f"M1T0{i}" for i in range(1,5)}
    for r in manifest:
        assert r["source_ids"]==plan_map[r["artifact_id"]]["source_ids"]
        assert r["claim_ids"]==plan_map[r["artifact_id"]]["claim_ids"]


def test_structural_no_exposure_preserved():
    vals=rows(VIS/"evidence/m1_2_rendered_value_audit.csv")
    struct=[r for r in vals if r["artifact_id"]=="M1F04" and r["exact_match_status"]=="STRUCTURAL_NO_EXPOSURE_PRESERVED"]
    assert len(struct)==9
    assert all(r["displayed_value"]=="N/E" for r in struct)
    assert all(r["source_value"]=="STRUCTURAL_NO_EXPOSURE" for r in struct)


def test_no_pooling_and_no_observational_confusion_language():
    audit=json.loads((VIS/"evidence/m1_2_visual_audit.json").read_text(encoding="utf-8"))
    fw=audit["interpretation_firewalls"]
    assert fw["f2_f3a_denominators_pooled"] is False
    assert fw["development_heldout_pooled"] is False
    assert fw["f3a_observational_confusion_labels_used"] is False
    assert fw["f3b_metrics_explicitly_synthetic"] is True
    assert fw["heldout_fp_zero_described_as_population_fpr_zero"] is False
    assert fw["selection_function_described_as_observational_correction"] is False
    assert fw["period_recovery_conditioned_on_selection"] is True

    t02=(VIS/"tables/M1T02_f3a_robustness_counts.csv").read_text(encoding="utf-8").lower()
    for forbidden in ["true positive","true negative","false positive","false negative"]:
        assert forbidden not in t02


def test_frozen_core_counts():
    audit=json.loads((VIS/"evidence/m1_2_visual_audit.json").read_text(encoding="utf-8"))
    assert audit["f3a_frozen_counts"]["qpp_baseline_mismatch"]=="51/61"
    assert audit["f3a_frozen_counts"]["transitions"]=="295/171/3178/0"
    assert audit["f3b_frozen_counts"]["development_confusion"]=="143/1657/1799/1"
    assert audit["f3b_frozen_counts"]["heldout_confusion"]=="152/1648/1800/0"
    assert audit["f3b_frozen_counts"]["selection_function_rows"]==156
    assert audit["f3b_frozen_counts"]["structural_no_exposure"]==9
    assert audit["f3b_frozen_counts"]["period_rows"]==152


def test_no_new_analysis_firewall():
    contract=json.loads((VIS/"config/m1_2_visual_rendering_contract.json").read_text(encoding="utf-8"))
    assert contract["new_scientific_computation"] is False
    assert contract["new_statistical_inference"] is False
    assert contract["new_source_artifact"] is False
    audit=json.loads((VIS/"evidence/m1_2_visual_audit.json").read_text(encoding="utf-8"))
    for k in ["new_scientific_computation","new_statistical_inference","new_bibliographic_search","new_afino_execution","new_synthetic_generation","manuscript_full_prose_started"]:
        assert audit[k] is False


def test_no_prohibited_full_manuscript_prose():
    for name in ["manuscript.tex","main.md","abstract.md","introduction.md","discussion.md","results.md","conclusions.md"]:
        assert not list(M1.rglob(name))
