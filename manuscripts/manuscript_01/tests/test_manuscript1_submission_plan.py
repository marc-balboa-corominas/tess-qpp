from pathlib import Path
import csv
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
PLAN=ROOT/"manuscripts"/"manuscript_01"/"submission"/"planning"
VALIDATOR=ROOT/"manuscripts"/"manuscript_01"/"scripts"/"validate_manuscript1_submission_plan.py"

def rows(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def test_three_journal_candidates_only():
    assert len(rows(PLAN/"m1_5_journal_candidates.csv"))==3

def test_target_apj_article_is_unique():
    d=json.loads((PLAN/"m1_5_target_journal_decision.json").read_text(encoding="utf-8"))
    assert d["target_journal"]=="The Astrophysical Journal"
    assert d["article_type"]=="Article"
    assert d["status"]=="SELECTED_AND_METADATA_GATE_RESOLVED"
    assert d["acceptance_rate_speculation_used"] is False

def test_single_confirmed_author_and_corresponding_author():
    a=rows(PLAN/"m1_5_author_metadata.csv")
    assert len(a)==1
    assert a[0]["author_order"]=="1"
    assert a[0]["corresponding_author"]=="YES"
    assert a[0]["author_confirmed"]=="true"

def test_independent_researcher_affiliation_resolved_without_personal_address():
    a=rows(PLAN/"m1_5_affiliations.csv")
    assert len(a)==1
    assert a[0]["institution_name"]=="Independent Researcher"
    assert a[0]["country"]=="Spain"
    assert a[0]["postal_address"]=="NOT_APPLICABLE_PERSONAL_ADDRESS_WITHHELD"
    assert a[0]["author_confirmed"]=="true"

def test_dar_no_preprint_yes():
    a=json.loads((PLAN/"m1_5_submission_audit.json").read_text(encoding="utf-8"))
    assert a["dual_anonymous_review"]=="NO"
    assert a["preprint_arxiv_before_peer_review"]=="YES"

def test_eight_reference_universe_only():
    r=rows(PLAN/"m1_5_bibliographic_metadata_resolution.csv")
    assert len(r)==8
    assert all(x["scientific_reference_changed"]=="false" for x in r)
    assert all(x["new_reference_added"]=="false" for x in r)

def test_howard_same_work_doi_correction_recorded():
    r=rows(PLAN/"m1_5_bibliographic_metadata_resolution.csv")
    x=next(x for x in r if x["citation_key"]=="HowardMacGregor2022")
    assert "ac426e" in x["DOI_or_identifier"]
    assert x["scientific_reference_changed"]=="false"

def test_requirements_all_officially_sourced():
    r=rows(PLAN/"m1_5_submission_requirements.csv")
    assert len(r)==30
    assert all(x["official_source"].startswith("https://") for x in r)
    assert all(x["access_date"]=="2026-08-27" for x in r)

def test_formatting_not_started():
    c=json.loads((PLAN/"m1_5_submission_scope_contract.json").read_text(encoding="utf-8"))
    a=json.loads((PLAN/"m1_5_submission_audit.json").read_text(encoding="utf-8"))
    assert c["journal_formatting_started"] is False
    assert a["journal_formatting_started"] is False

def test_author_gate_resolved():
    c=json.loads((PLAN/"m1_5_submission_scope_contract.json").read_text(encoding="utf-8"))
    assert c["author_gate"]=="RESOLVED_AND_AUTHOR_CONFIRMED"
    assert c["status"]=="FINAL_FREEZE_CANDIDATE"

def test_scientific_firewalls():
    a=json.loads((PLAN/"m1_5_submission_audit.json").read_text(encoding="utf-8"))
    assert a["new_reference_added"] is False
    assert a["new_scientific_claims"] is False
    assert a["scientific_numerical_changes"] is False
    assert a["figure_table_regeneration"] is False

def test_final_validator_passes():
    cp=subprocess.run([sys.executable,str(VALIDATOR)],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert cp.returncode==0, cp.stdout+cp.stderr
    assert "MANUSCRIPT1_SCIENTIFIC_EDITORIAL_REVIEW_PASS" in cp.stdout
    assert "MANUSCRIPT1_SUBMISSION_PLAN_VALIDATION_PASS" in cp.stdout

def test_req009_title_and_author_state_resolved_confirmed():
    r=rows(PLAN/"m1_5_submission_requirements.csv")
    x=next(x for x in r if x["requirement_id"]=="REQ009")
    assert x["current_manuscript_status"]=="TITLE_FROZEN_AUTHORS_RESOLVED_CONFIRMED"
    assert x["blocking_for_submission"].lower()=="true"

def test_no_blocking_unresolved_requirement_except_explicit_m1_6_portal_defer():
    r=rows(PLAN/"m1_5_submission_requirements.csv")
    allowed={"REQ010"}
    offenders=[]
    for x in r:
        if x["blocking_for_submission"].lower()=="true" and "UNRESOLVED" in x["current_manuscript_status"]:
            if x["requirement_id"] not in allowed:
                offenders.append((x["requirement_id"],x["current_manuscript_status"]))
            else:
                action=x["action_required_in_m1_6"].lower()
                assert any(token in action for token in ("m1.6","portal","submission"))
    assert offenders==[]
