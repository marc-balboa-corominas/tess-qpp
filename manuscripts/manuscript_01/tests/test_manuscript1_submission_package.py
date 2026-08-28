from pathlib import Path
import csv,json,re,hashlib
ROOT=Path(__file__).resolve().parents[3]
FINAL=ROOT/'manuscripts/manuscript_01/submission/final'
def test_target():
 m=json.loads((FINAL/'metadata/m1_7_submission_metadata.json').read_text()); assert m['journal']=='The Astrophysical Journal'; assert m['article_type']=='Article'
def test_author():
 t=(FINAL/'manuscript/manuscript_apj.tex').read_text(); assert 'Marc Balboa Corominas' in t and '0009-0006-7571-9193' in t and '\\correspondingauthor{Marc Balboa Corominas}' in t
def test_claims(): assert len(set(re.findall(r'M1C\d{3}',(FINAL/'manuscript/manuscript_apj.tex').read_text())))==27
def test_numerics():
 r=list(csv.DictReader((FINAL/'evidence/m1_7_numeric_identity_audit.csv').open())); assert len(r)==120; assert not any(x['scientific_numeric_change_m1_7']=='true' for x in r)
def test_references(): assert len(list(csv.DictReader((FINAL/'evidence/m1_7_reference_identity_audit.csv').open())))==8
def test_visuals():
 r=list(csv.DictReader((FINAL/'evidence/m1_7_visual_identity_audit.csv').open())); assert len(r)==9
 figs=[x for x in r if x['artifact_type']=='FIGURE']; tabs=[x for x in r if x['artifact_type']=='TABLE']
 assert len(figs)==5 and all(x['content_hash_identity']=='EXACT' for x in figs)
 allowed={'EXACT','AASTEX_WRAPPER_ONLY_SCIENTIFIC_CONTENT_PRESERVED'}
 assert len(tabs)==4 and all(x['content_hash_identity'] in allowed for x in tabs)
 assert all(x['scientific_content_changed']=='false' and x['status']=='PASS' for x in r)
def test_requirements():
 r=list(csv.DictReader((FINAL/'evidence/m1_7_requirement_preflight.csv').open())); assert len(r)==30; assert all(x['decision_unresolved']=='false' for x in r)
def test_uat(): assert len(json.loads((FINAL/'metadata/m1_7_uat_corridor_decision.json').read_text())['uat_concepts'])==6
def test_no_submission():
 a=json.loads((FINAL/'evidence/m1_7_submission_audit.json').read_text()); assert a['actual_journal_submission_performed'] is False and a['actual_arxiv_upload_performed'] is False
def test_approved_figures():
 for i in range(1,6): assert (FINAL/f'portal_bundle/fig{i}.pdf').read_bytes()==(FINAL/f'arxiv_bundle/fig{i}.pdf').read_bytes()
