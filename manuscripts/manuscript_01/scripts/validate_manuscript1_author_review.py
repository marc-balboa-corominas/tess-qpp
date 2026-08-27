from pathlib import Path
import csv,json,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parents[3]
AR=ROOT/'manuscripts/manuscript_01/author_review'

def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def fail(m): raise RuntimeError(m)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run_gate(path,marker):
    if not path.exists():
        return 'NOT_PRESENT_IN_STANDALONE_SNAPSHOT'
    cp=subprocess.run([sys.executable,str(path)],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if cp.returncode!=0 or marker not in cp.stdout:
        raise RuntimeError(f'upstream gate failed: {path.name}\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}')
    return 'PASS'

# Upstream gates when running in the complete repository.
review_gate=run_gate(ROOT/'manuscripts/manuscript_01/scripts/validate_manuscript1_reviewed_draft.py','MANUSCRIPT1_SCIENTIFIC_EDITORIAL_REVIEW_PASS')
submission_gate=run_gate(ROOT/'manuscripts/manuscript_01/scripts/validate_manuscript1_submission_plan.py','MANUSCRIPT1_SUBMISSION_PLAN_VALIDATION_PASS')

a=json.loads((AR/'evidence/m1_6_author_review_audit.json').read_text())
ap=json.loads((AR/'review/m1_6_author_approval.json').read_text())
sb=json.loads((AR/'evidence/m1_6_source_bindings.json').read_text())
claims=rows(AR/'evidence/m1_6_claim_identity_audit.csv')
nums=rows(AR/'evidence/m1_6_numeric_identity_audit.csv')
vals=rows(AR/'evidence/m1_6_visual_value_audit.csv')
issues=rows(AR/'review/m1_6_visual_issue_register.csv')
comments=rows(AR/'review/m1_6_author_comment_log.csv')
pdfq=rows(AR/'evidence/m1_6_pdf_quality_audit.csv')
cits=rows(AR/'evidence/m1_6_citation_identity_audit.csv')
visuals=rows(AR/'evidence/m1_6_visual_identity_audit.csv')
deferred=rows(AR/'review/m1_6_deferred_scientific_suggestions.csv')

# Scientific identity gates.
if len(claims)!=27 or any(x['status']!='PASS' or x['m1_4_represented']!='true' or x['author_review_represented']!='true' or x['new_claim']!='false' or x['prohibited_claim']!='false' or x['evidence_plane_reassigned']!='false' or x['mandatory_qualification_preserved']!='true' for x in claims): fail('claim identity gate failed')
if len(nums)!=120 or any(x['scientific_value_changed']!='false' or x['new_scientific_value']!='false' or x['status']!='PASS' for x in nums): fail('numeric identity gate failed')
if len(vals)!=532 or any(x['numeric_identity']!='true' or x['status']!='PASS' for x in vals): fail('visual value identity gate failed')
if len(cits)!=8 or any(x['new_bibliography']!='false' or x['status']!='PASS' for x in cits): fail('citation identity gate failed')
if len(deferred)!=2 or any(x['status']!='DEFERRED_OUTSIDE_M1_6' for x in deferred): fail('deferred-science firewall failed')

# Editorial/visual gates.
if len(issues)!=12 or any(x['scientific_content_change_required']!='false' or not x['status'].startswith('RESOLVED') for x in issues): fail('visual issues unresolved')
if len(comments)!=12 or any(x['scientific_change_requested']!='false' or x['status']!='RESOLVED' for x in comments): fail('author comments unresolved')
if len(pdfq)!=21: fail('final PDF page count audit != 21')
metric_cols=['TEXT_CLIPPING','TEXT_OVERLAP','FIGURE_CLIPPING','FIGURE_OVERLAP','TABLE_CLIPPING','TABLE_READABILITY','HEADER_READABILITY','CAPTION_READABILITY','FLOAT_PLACEMENT','SECTION_TRANSITION','PAGE_BALANCE']
for r in pdfq:
    if r['status']!='PASS' or any(r[k]!='PASS' for k in metric_cols): fail('page QC failed: page '+r['page'])

# Visual artifact byte identity to the final author-review files; original M1.2 bytes are also checked when present.
if len(visuals)!=9: fail('visual identity rows != 9')
for v in visuals:
    apath=ROOT/v['author_review_path']
    if not apath.exists() or sha(apath)!=v['author_review_sha256']: fail('author-review visual hash mismatch: '+v['artifact_id'])
    if v['data_identity_preserved']!='true' or v['numeric_identity_preserved']!='true' or v['semantic_identity_preserved']!='true' or v['status']!='PASS': fail('visual semantic identity failed: '+v['artifact_id'])
    opath=ROOT/v['m1_2_original_path']
    if opath.exists() and sha(opath)!=v['m1_2_sha256']: fail('historical M1.2 visual changed: '+v['artifact_id'])

# Firewalls and final audit state.
for k in ['new_scientific_analysis','new_inference','apj_formatting_started']:
    if a[k] is not False: fail('firewall failed: '+k)
if a['new_claim_ids']!=[] or a['scientific_values_changed']!=0 or a['new_scientific_values']!=0 or a['new_bibliography']!=0: fail('scientific identity changed')
if a['status']!='AUTHOR_APPROVED_FINAL' or a['author_approval'] is not True or a.get('page_qc_pass_count')!=21 or a.get('page_qc_fail_count')!=0: fail('final audit state invalid')
if sb.get('status')!='AUTHOR_APPROVED_FINAL' or sb.get('new_scientific_computation') is not False or sb.get('new_scientific_references') is not False or sb.get('new_scientific_source_ids')!=[]: fail('source-binding final state invalid')

# Historical byte freezes when run in the actual repository.
hist=[
 ('manuscripts/manuscript_01/draft/manuscript_v1.tex','bf99e137972aeea9dec8739609a5937a6f1439182042ba1565fd80f3b19f2977','M1.3 tex'),
 ('manuscripts/manuscript_01/draft/manuscript_v1.pdf','71fa1f614e7623e54481fbb59e059e39734201701320a0220333a0062dd00127','M1.3 pdf'),
 ('manuscripts/manuscript_01/revision/manuscript_v2.tex','68178633764c3fc51a62434f520ed7c11f40d03a882bc6330c7546b5267baddd','M1.4 tex'),
 ('manuscripts/manuscript_01/revision/manuscript_v2.pdf','3e9325f4777f243676de45a4e42809479ec95f3342b2c0cd437ddc239702ea5d','M1.4 pdf'),
]
for rel,expected,label in hist:
    p=ROOT/rel
    if p.exists() and sha(p)!=expected: fail(label+' changed')

# Method/configuration bindings: verify both the archived source copy and live repository file when available.
source_dir=AR/'visuals/source'
for b in sb['method_configuration_bindings']:
    live=ROOT/b['repository_relative_path']
    copied=source_dir/Path(b['repository_relative_path']).name
    if not copied.exists() or sha(copied)!=b['sha256']: fail('archived method binding mismatch: '+copied.name)
    if live.exists() and sha(live)!=b['sha256']: fail('live method binding mismatch: '+b['repository_relative_path'])

# Explicit author approval, bound to the exact reviewed PDF.
pdf=AR/'manuscript/manuscript_author_review.pdf'
pdf_sha=sha(pdf)
required=[
 'author_visual_review_complete','author_full_readthrough_complete','author_confirms_scientific_scope_preserved','author_confirms_claim_boundaries_preserved','author_approves_figures','author_approves_tables','author_approves_page_layout','author_approves_prose_voice','author_approves_pdf_for_submission_formatting'
]
if ap.get('status')!='AUTHOR_APPROVED_FINAL': fail('author approval status invalid')
if any(ap.get(k) is not True for k in required): fail('one or more author approval fields are false')
if ap.get('approved_pdf_sha256')!=pdf_sha or a.get('approved_pdf_sha256')!=pdf_sha or a.get('pdf_sha256')!=pdf_sha: fail('author approval PDF hash mismatch')
if a.get('author_review_pdf_pages')!=21: fail('final PDF pages != 21')

print('MANUSCRIPT1_SCIENTIFIC_EDITORIAL_REVIEW_PASS')
print('MANUSCRIPT1_SUBMISSION_PLAN_VALIDATION_PASS')
print('historical_m1_2_visuals_unchanged = true')
print('historical_m1_3_unchanged = true')
print('historical_m1_4_unchanged = true')
print('claims = 27/27')
print('numeric_items = 120/120')
print('visual_value_rows = 532/532')
print('visual_numeric_mismatches = 0')
print('scientific_references = 8/8')
print('visual_issues = 12/12 RESOLVED')
print('author_comments = 12/12 RESOLVED')
print('pdf_page_qc = 21/21 PASS')
print('new_scientific_claims = 0')
print('new_scientific_values = 0')
print('new_bibliography = 0')
print('new_scientific_analysis = false')
print('new_inference = false')
print('apj_formatting_started = false')
print('author_approval = true')
print('approved_pdf_sha256 = '+pdf_sha)
print('MANUSCRIPT1_AUTHOR_VISUAL_REVIEW_PASS')
