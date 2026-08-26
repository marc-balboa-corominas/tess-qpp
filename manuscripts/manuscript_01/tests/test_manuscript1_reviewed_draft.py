from pathlib import Path
import csv, json, re, subprocess, sys

ROOT=Path(__file__).resolve().parents[3]
REV=ROOT/"manuscripts/manuscript_01/revision"
EV=REV/"evidence"
VALIDATOR=ROOT/"manuscripts/manuscript_01/scripts/validate_manuscript1_reviewed_draft.py"

def rows(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def test_final_validator_marker():
    cp=subprocess.run([sys.executable,str(VALIDATOR)],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert cp.returncode==0, cp.stdout+"\n"+cp.stderr
    assert "MANUSCRIPT1_SCIENTIFIC_EDITORIAL_REVIEW_PASS" in cp.stdout

def test_all_five_gates_complete():
    c=json.loads((EV/"m1_4_review_contract.json").read_text(encoding="utf-8"))
    assert all("COMPLETE" in v for v in c["gates"].values())

def test_issue_register_resolved():
    rs=rows(EV/"m1_4_issue_register.csv")
    assert len(rs)==10
    assert all(r["status"].startswith("RESOLVED_") for r in rs)

def test_semantic_language_zero_revise():
    rs=rows(EV/"m1_4_claim_language_audit.csv")
    assert len(rs)==155
    assert all(r["status"]=="PASS" for r in rs)
    assert all(r["scope_explicit"]=="true" and r["qualification_present"]=="true" for r in rs if r["term"]=="VALIDATION")

def test_numeric_traceability_120():
    rs=rows(EV/"m1_4_numeric_traceability.csv")
    assert len(rs)==120
    assert all(r["revision_status"]=="UNCHANGED_NUMERAL_MAPPING_REVERIFIED" for r in rs)

def test_citations_frozen_eight():
    rs=rows(EV/"m1_4_citation_audit.csv")
    assert len(rs)==8
    assert all(r["new_bibliographic_search"]=="false" for r in rs)

def test_visuals_all_pass():
    rs=rows(EV/"m1_4_visual_layout_audit.csv")
    assert len(rs)==9
    status={r["artifact_id"]:r["revised_status"] for r in rs}
    assert all(v=="PASS" for v in status.values())
    assert status["M1T01"]=="PASS"
    assert status["M1T04"]=="PASS"

def test_revision_log_no_science():
    rs=rows(EV/"m1_4_revision_log.csv")
    assert len(rs)==10
    assert all(r["scientific_effect"]=="NONE" for r in rs)

def test_referee_attack_twelve_pass():
    text=(EV/"m1_4_referee_audit.md").read_text(encoding="utf-8")
    ids=re.findall(r"^## (M14R\d{2}) — ",text,flags=re.M)
    assert ids==[f"M14R{i:02d}" for i in range(1,13)]
    assert text.count("PASS_BOUNDED_BY_FROZEN_CLAIMS")>=12

def test_no_new_claim_or_source_ids():
    a=json.loads((EV/"m1_4_revision_audit.json").read_text(encoding="utf-8"))
    assert a["new_claim_ids"]==[]
    assert a["new_source_ids"]==[]
    assert a["claim_ids_used_count"]==27

def test_final_pdf_and_table_readability():
    a=json.loads((EV/"m1_4_revision_audit.json").read_text(encoding="utf-8"))
    assert a["v2_pdf_pages"]==22
    assert a["pdf_render_inspection"]=="PASS"
    assert a["table1_readability"]=="PASS"
    assert a["table4_readability"]=="PASS"

def test_firewalls_and_submission_boundary():
    a=json.loads((EV/"m1_4_revision_audit.json").read_text(encoding="utf-8"))
    for k in [
        "new_scientific_computation","new_statistical_inference","new_bibliographic_search",
        "new_afino_execution","new_synthetic_generation","new_confidence_intervals",
        "new_scientific_figures_tables","new_threshold_search","visual_regeneration",
    ]:
        assert a[k] is False
    assert a["target_journal_formatting_started"] is False
