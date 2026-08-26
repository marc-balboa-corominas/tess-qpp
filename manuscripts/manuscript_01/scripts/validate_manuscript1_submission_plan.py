from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
SUB = ROOT / "manuscripts" / "manuscript_01" / "submission"
PLAN = SUB / "planning"
REV = ROOT / "manuscripts" / "manuscript_01" / "revision"

EXPECTED_M14 = "10e4ac7017950f60e74a1f0fddb41f6004f7755d"
EXPECTED_M14_TEX_SHA = "68178633764c3fc51a62434f520ed7c11f40d03a882bc6330c7546b5267baddd"
EXPECTED_M14_PDF_SHA = "3e9325f4777f243676de45a4e42809479ec95f3342b2c0cd437ddc239702ea5d"
EXPECTED_KEYS = {
    "Inglis2016","Pugh2017","Broomhall2019","HowardMacGregor2022",
    "Belov2024","Joshi2025","Wang2025","Reale2026"
}
ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")

def rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fail(msg: str):
    raise RuntimeError(msg)

def main():
    contract=json.loads((PLAN/"m1_5_submission_scope_contract.json").read_text(encoding="utf-8"))
    decision=json.loads((PLAN/"m1_5_target_journal_decision.json").read_text(encoding="utf-8"))
    audit=json.loads((PLAN/"m1_5_submission_audit.json").read_text(encoding="utf-8"))
    journals=rows(PLAN/"m1_5_journal_candidates.csv")
    authors=rows(PLAN/"m1_5_author_metadata.csv")
    affs=rows(PLAN/"m1_5_affiliations.csv")
    bib=rows(PLAN/"m1_5_bibliographic_metadata_resolution.csv")
    req=rows(PLAN/"m1_5_submission_requirements.csv")
    assets=rows(PLAN/"m1_5_submission_asset_plan.csv")

    if contract["entry_freeze"]["m1_4_commit"]!=EXPECTED_M14:
        fail("M1.4 entry freeze mismatch")
    if contract["status"]!="FINAL_FREEZE_CANDIDATE":
        fail("scope contract is not final-freeze candidate")
    if contract["author_gate"]!="RESOLVED_AND_AUTHOR_CONFIRMED":
        fail("author gate unresolved")
    if contract["journal_formatting_started"] is not False:
        fail("journal formatting started during M1.5")

    # Frozen M1.4 scientific content remains byte exact when available.
    if (REV/"manuscript_v2.tex").is_file() and sha(REV/"manuscript_v2.tex")!=EXPECTED_M14_TEX_SHA:
        fail("M1.4 reviewed TeX changed")
    if (REV/"manuscript_v2.pdf").is_file() and sha(REV/"manuscript_v2.pdf")!=EXPECTED_M14_PDF_SHA:
        fail("M1.4 reviewed PDF changed")

    if len(journals)!=3:
        fail("journal candidate count must be 3")
    if decision["target_journal"]!="The Astrophysical Journal" or decision["article_type"]!="Article":
        fail("one target journal/article type not frozen")
    if decision["status"]!="SELECTED_AND_METADATA_GATE_RESOLVED":
        fail("target decision status unresolved")
    if decision["acceptance_rate_speculation_used"] is not False:
        fail("acceptance-rate speculation prohibited")
    if decision["dual_anonymous_review"]!="NO" or decision["preprint_arxiv_before_peer_review"]!="YES":
        fail("DAR/preprint decision mismatch")
    if decision["journal_formatting_started"] is not False:
        fail("target-journal formatting started too early")

    if len(bib)!=8 or {r["citation_key"] for r in bib}!=EXPECTED_KEYS:
        fail("exact eight-reference metadata universe violated")
    if any(r["scientific_reference_changed"]!="false" for r in bib):
        fail("scientific reference changed")
    if any(r["new_reference_added"]!="false" for r in bib):
        fail("new scientific reference added")
    hm=next(r for r in bib if r["citation_key"]=="HowardMacGregor2022")
    if "10.3847/1538-4357/ac426e" not in hm["DOI_or_identifier"]:
        fail("HowardMacGregor2022 corrected same-work DOI missing")

    if not req or any(not r["official_source"].startswith("https://") for r in req):
        fail("all journal requirements must be officially sourced")
    if any(r["access_date"]!="2026-08-27" for r in req):
        fail("requirement access-date audit failed")
    if len(assets)!=16:
        fail("submission asset plan count changed")

    # Exactly one explicitly confirmed author.
    if len(authors)!=1:
        fail("exactly one confirmed author expected")
    a=authors[0]
    if a["author_order"]!="1" or a["full_publication_name"]!="Marc Balboa Corominas":
        fail("author identity/order mismatch")
    if not ORCID_RE.match(a["ORCID"]):
        fail("ORCID format invalid")
    if "@" not in a["email"] or "." not in a["email"].split("@")[-1]:
        fail("email format invalid")
    if a["affiliation_ids"]!="AFF1":
        fail("author affiliation mapping mismatch")
    if a["corresponding_author"].upper()!="YES":
        fail("exactly one corresponding author not resolved")
    if a["author_confirmed"].lower()!="true":
        fail("author not explicitly confirmed")
    if "UNRESOLVED" in "|".join(a.values()):
        fail("unresolved author metadata remains")

    # One resolved independent-researcher affiliation; no personal address invented.
    if len(affs)!=1:
        fail("exactly one affiliation expected")
    af=affs[0]
    if af["affiliation_id"]!="AFF1" or af["institution_name"]!="Independent Researcher" or af["country"]!="Spain":
        fail("independent-researcher affiliation mismatch")
    if af["author_confirmed"].lower()!="true":
        fail("affiliation not confirmed")
    allowed_withheld="NOT_APPLICABLE_PERSONAL_ADDRESS_WITHHELD"
    for field in ["postal_address","city","region","postal_code"]:
        if af[field]!=allowed_withheld:
            fail(f"personal-address handling mismatch: {field}")
    if af["department_or_unit"]!="NONE":
        fail("independent researcher department must be NONE")

    # Administrative choices.
    if audit["status"]!="FINAL_FREEZE_CANDIDATE":
        fail("submission audit not final-freeze candidate")
    if audit["author_metadata_resolved"] is not True or audit["affiliations_resolved"] is not True:
        fail("author/affiliation resolution flags false")
    if audit["corresponding_author_resolved"] is not True or audit["corresponding_author_count"]!=1:
        fail("corresponding author unresolved")
    if audit["author_confirmation_complete"] is not True:
        fail("author confirmation incomplete")
    if audit["dual_anonymous_review"]!="NO" or audit["preprint_arxiv_before_peer_review"]!="YES":
        fail("DAR/preprint administrative choice mismatch")
    if audit["funding_statement"]!="This research received no external funding.":
        fail("funding statement mismatch")
    if audit["conflicts_of_interest"]!="The author declares no competing interests.":
        fail("conflict statement mismatch")
    if audit["excluded_or_conflicted_reviewers"]!="NONE":
        fail("excluded-reviewer state mismatch")
    if audit["apc_or_discount_route"]!="UNRESOLVED_UNTIL_SUBMISSION":
        fail("APC route should remain explicit nonblocking submission-time item")

    for field in [
        "new_reference_added","new_scientific_claims","scientific_numerical_changes",
        "figure_table_regeneration","journal_formatting_started"
    ]:
        if audit[field] is not False:
            fail(f"scientific/formatting firewall failed: {field}")

    # Critical journal-decision requirements resolved or explicitly deferred.
    req_by={r["requirement_id"]:r for r in req}
    required_statuses={
        "REQ006":"RESOLVED_ONE_CONFIRMED_AUTHOR_EMAIL",
        "REQ007":"RESOLVED_AUTHOR_ORDER_1_CORRESPONDING_AUTHOR_1",
        "REQ008":"RESOLVED_INDEPENDENT_RESEARCHER_SPAIN_PERSONAL_ADDRESS_WITHHELD",
        "REQ018":"RESOLVED_NO_EXTERNAL_FUNDING",
        "REQ020":"RESOLVED_DUAL_ANONYMOUS_REVIEW_NO",
        "REQ022":"RESOLVED_SINGLE_AUTHOR_CONTRIBUTION_ROLES_CONFIRMED",
        "REQ027":"RESOLVED_NONE_EXCLUDED_OR_CONFLICTED_REVIEWERS",
        "REQ029":"RESOLVED_PREPRINT_ARXIV_BEFORE_PEER_REVIEW_YES_DAR_NO",
    }
    for rid,status in required_statuses.items():
        if req_by[rid]["current_manuscript_status"]!=status:
            fail(f"submission requirement not resolved: {rid}")

    if audit["m1_4_scientific_editorial_review_marker"]!="MANUSCRIPT1_SCIENTIFIC_EDITORIAL_REVIEW_PASS":
        fail("M1.4 review marker missing")

    print("MANUSCRIPT1_SCIENTIFIC_EDITORIAL_REVIEW_PASS")
    print("one_target_journal = true")
    print("target_journal = The Astrophysical Journal")
    print("article_type = Article")
    print("journal_candidates = 3")
    print("journal_requirements_officially_sourced = true")
    print("existing_citations_metadata_audited = 8/8")
    print("authors_resolved_and_confirmed = true")
    print("author_count = 1")
    print("affiliations_resolved = true")
    print("corresponding_author_resolved = true")
    print("corresponding_author_count = 1")
    print("dual_anonymous_review = NO")
    print("preprint_arxiv_before_peer_review = YES")
    print("independent_researcher_personal_address_withheld = true")
    print("new_scientific_references = 0")
    print("new_scientific_claims = 0")
    print("scientific_numerical_changes = 0")
    print("figure_table_regeneration = 0")
    print("target_journal_formatting_started = false")
    print("MANUSCRIPT1_SUBMISSION_PLAN_VALIDATION_PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
