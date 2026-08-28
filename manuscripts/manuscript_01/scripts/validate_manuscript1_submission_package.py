#!/usr/bin/env python3
from pathlib import Path
import csv,json,hashlib,re,sys
root=Path(__file__).resolve().parents[3]
final=root/'manuscripts/manuscript_01/submission/final'
def fail(s): print('M1_7_VALIDATION_FAIL:',s); raise SystemExit(1)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
req=['README.md','manuscript/manuscript_apj.tex','manuscript/references_apj.bib','metadata/m1_7_submission_metadata.json','metadata/m1_7_uat_corridor_decision.json','evidence/m1_7_scientific_identity_audit.csv','evidence/m1_7_numeric_identity_audit.csv','evidence/m1_7_reference_identity_audit.csv','evidence/m1_7_visual_identity_audit.csv','evidence/m1_7_requirement_preflight.csv','evidence/m1_7_compile_audit.json','evidence/m1_7_submission_audit.json']
for r in req:
    if not (final/r).exists(): fail('missing '+r)
tex=(final/'manuscript/manuscript_apj.tex').read_text()
if '\\documentclass[manuscript,linenumbers]{aastex702}' not in tex: fail('AASTeX 7.0.2/linenumbers class line missing')
for s in ['Marc Balboa Corominas','0009-0006-7571-9193','Independent Researcher, Spain','m.balboacorominas.research@gmail.com','\\correspondingauthor{Marc Balboa Corominas}']:
    if s not in tex: fail('author metadata missing '+s)
claims=set(re.findall(r'M1C\d{3}',tex))
if len(claims)!=27: fail(f'claims {len(claims)} != 27')
nums=list(csv.DictReader((final/'evidence/m1_7_numeric_identity_audit.csv').open(encoding='utf-8-sig')))
if len(nums)!=120 or any(r['scientific_numeric_change_m1_7']!='false' for r in nums): fail('numeric identity')
refs=list(csv.DictReader((final/'evidence/m1_7_reference_identity_audit.csv').open(encoding='utf-8-sig')))
if len(refs)!=8 or any(r['new_scientific_work']!='false' for r in refs): fail('reference identity')
vis=list(csv.DictReader((final/'evidence/m1_7_visual_identity_audit.csv').open(encoding='utf-8-sig')))
if len(vis)!=9 or any(r['status']!='PASS' for r in vis): fail('visual identity')
for r in vis:
    p=root/r['m1_7_flat_path']
    if not p.exists() or sha(p)!=r['m1_7_sha256']: fail('visual bytes '+r['artifact_id'])
pre=list(csv.DictReader((final/'evidence/m1_7_requirement_preflight.csv').open(encoding='utf-8-sig')))
allowed={'PASS','NOT_APPLICABLE','PORTAL_ACTION_REQUIRED','AUTHOR_ADMINISTRATIVE_ACTION_REQUIRED'}
if len(pre)!=30 or any(r['m1_7_status'] not in allowed or r['decision_unresolved']!='false' for r in pre): fail('requirements')
meta=json.loads((final/'metadata/m1_7_submission_metadata.json').read_text())
if meta['journal']!='The Astrophysical Journal' or meta['article_type']!='Article': fail('target')
if meta['topical_corridor']!='Stars and Stellar Physics' or len(meta['uat_concepts'])!=6: fail('corridor/UAT')
ca=json.loads((final/'evidence/m1_7_compile_audit.json').read_text())
if ca['flat_portal_compile']=='PASS' and ca['arxiv_source_compile']=='PASS' and ca.get('canonical_pdf_created'):
    if ca['pdf_visual_inspection']=='PASS':
        print('MANUSCRIPT1_SUBMISSION_PACKAGE_VALIDATION_PASS')
    else:
        print('M1_7_TECHNICAL_PREFLIGHT_PASS')
        print('M1_7_PDF_VISUAL_REVIEW_REQUIRED')
else:
    print('M1_7_STATIC_IDENTITY_PREFLIGHT_PASS')
    print('M1_7_LOCAL_AASTEX_MATERIALIZATION_REQUIRED')
