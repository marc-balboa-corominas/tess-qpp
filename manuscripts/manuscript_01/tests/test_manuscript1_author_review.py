from pathlib import Path
import csv,json,subprocess,sys,hashlib
ROOT=Path(__file__).resolve().parents[3]
AR=ROOT/'manuscripts/manuscript_01/author_review'
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def test_claims_27_exact():
    r=rows(AR/'evidence/m1_6_claim_identity_audit.csv'); assert len(r)==27; assert all(x['status']=='PASS' and x['new_claim']=='false' and x['prohibited_claim']=='false' for x in r)
def test_numerics_120_exact():
    r=rows(AR/'evidence/m1_6_numeric_identity_audit.csv'); assert len(r)==120; assert all(x['scientific_value_changed']=='false' and x['new_scientific_value']=='false' for x in r)
def test_visual_values_532_zero_mismatch():
    r=rows(AR/'evidence/m1_6_visual_value_audit.csv'); assert len(r)==532; assert all(x['numeric_identity']=='true' and x['status']=='PASS' for x in r)
def test_visual_identity_hashes_current():
    r=rows(AR/'evidence/m1_6_visual_identity_audit.csv'); assert len(r)==9
    for x in r:
        assert sha(ROOT/x['author_review_path'])==x['author_review_sha256']
def test_visual_issues_and_comments_resolved():
    i=rows(AR/'review/m1_6_visual_issue_register.csv'); c=rows(AR/'review/m1_6_author_comment_log.csv')
    assert len(i)==12 and all(x['status'].startswith('RESOLVED') and x['scientific_content_change_required']=='false' for x in i)
    assert len(c)==12 and all(x['status']=='RESOLVED' and x['scientific_change_requested']=='false' for x in c)
def test_pdf_qc_all_21_pass():
    r=rows(AR/'evidence/m1_6_pdf_quality_audit.csv'); assert len(r)==21; assert all(x['status']=='PASS' for x in r)
def test_no_new_bibliography_and_deferred_science_not_executed():
    assert all(x['new_bibliography']=='false' and x['status']=='PASS' for x in rows(AR/'evidence/m1_6_citation_identity_audit.csv'))
    d=rows(AR/'review/m1_6_deferred_scientific_suggestions.csv'); assert len(d)==2 and all(x['status']=='DEFERRED_OUTSIDE_M1_6' for x in d)
def test_author_approval_true_and_bound_to_pdf():
    a=json.loads((AR/'review/m1_6_author_approval.json').read_text()); p=AR/'manuscript/manuscript_author_review.pdf'
    assert a['status']=='AUTHOR_APPROVED_FINAL'; assert a['author_approves_pdf_for_submission_formatting'] is True; assert a['approved_pdf_sha256']==sha(p)
def test_no_apj_formatting_or_new_science():
    a=json.loads((AR/'evidence/m1_6_author_review_audit.json').read_text()); assert a['apj_formatting_started'] is False; assert a['new_scientific_analysis'] is False; assert a['new_inference'] is False; assert a['new_bibliography']==0; assert a['scientific_values_changed']==0
def test_validator_passes_after_author_approval():
    v=ROOT/'manuscripts/manuscript_01/scripts/validate_manuscript1_author_review.py'; cp=subprocess.run([sys.executable,str(v)],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE); assert cp.returncode==0,cp.stderr; assert 'MANUSCRIPT1_AUTHOR_VISUAL_REVIEW_PASS' in cp.stdout
