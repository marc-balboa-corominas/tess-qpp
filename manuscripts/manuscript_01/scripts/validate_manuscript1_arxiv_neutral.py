from pathlib import Path
import csv, json, hashlib, re

ROOT=Path.cwd()
T=ROOT/'manuscripts/manuscript_01/preprint/arxiv_neutral'
E=T/'evidence'; S=T/'source'; B=T/'bundle'; R=T/'review'; BUILD=T/'build'

def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(cond,msg):
    if not cond: raise RuntimeError(msg)

require(T.exists(),'target tree missing')
readme=(T/'README.md').read_text(encoding='utf-8')
require('AUTHOR-APPROVED / FREEZE AUTHORIZED' in readme,'author-approved status missing')

bindings=json.loads((E/'m1_8_source_bindings.json').read_text())
require(bindings['normative_scientific_source']=='M1.6 author_review','M1.6 not normative')
require(bindings['m1_7_normative_for_scientific_content'] is False,'M1.7 incorrectly normative')

claims=rows(E/'m1_8_scientific_identity_audit.csv')
nums=rows(E/'m1_8_numeric_identity_audit.csv')
refs=rows(E/'m1_8_reference_identity_audit.csv')
figs=rows(E/'m1_8_visual_identity_audit.csv')
tabs=rows(E/'m1_8_table_identity_audit.csv')
neutral=rows(E/'m1_8_neutrality_audit.csv')
hyg=rows(E/'m1_8_source_hygiene_audit.csv')
pdfpre=rows(E/'m1_8_pdf_preflight.csv')
visual=rows(R/'m1_8_author_visual_review.csv')
revision=rows(R/'m1_8_author_revision_log.csv')
compile_audit=json.loads((E/'m1_8_compile_audit.json').read_text())
approval=json.loads((R/'m1_8_author_approval.json').read_text())
mentor=json.loads((E/'m1_8_mentor_closure_audit.json').read_text())
visual_eq=json.loads((E/'m1_8_author_visual_equivalence_audit.json').read_text())

require(len(claims)==27 and all(r['status']=='PASS' and r['scientific_content_changed']=='false' and r['new_claim']=='false' and r['prohibited_claim']=='false' for r in claims),'claim identity')
require(len(nums)==120 and all(r['status']=='PASS' and r['scientific_numeric_change_m1_8']=='false' and r['new_scientific_value']=='false' and r['missing_in_m1_8']=='false' for r in nums),'numeric identity')
require(len(refs)==8 and all(r['status']=='PASS' and r['new_scientific_work']=='false' and r['removed_scientific_work']=='false' for r in refs),'reference identity')
require(len(figs)==5 and all(r['status']=='PASS' and r['byte_exact']=='true' and r['scientific_content_changed']=='false' for r in figs),'figure identity')
require(len(tabs)==4 and all(r['status']=='PASS' and r['scientific_content_changed']=='false' for r in tabs),'table identity')
require(all(r['status']=='PASS' for r in neutral),'neutrality')
require(all(r['status']=='PASS' for r in hyg),'source hygiene')
require(compile_audit['clean_directory_compile']=='PASS' and compile_audit['automated_pdf_status']=='PASS','compile audit')
require(compile_audit['undefined_citations']==0 and compile_audit['undefined_references']==0 and compile_audit['latex_errors']==0,'compile diagnostics')
require(compile_audit['overfull_hbox']==0 and compile_audit['overfull_vbox']==0,'compile overflow diagnostics')
require(compile_audit['author_visual_status']=='PASS','compile audit author visual status')
require(all(r['status']=='PASS' for r in pdfpre),'pdf preflight')
require(len(visual)==22 and all(r['overall']=='PASS' and all(r[k]=='PASS' for k in ('text_layout','figures','tables','section_starts','captions','legibility')) for r in visual),'author visual review')
require(all(r['final_review_status']=='PASS' for r in revision),'author revision closure')
require(approval['author_visual_status']=='PASS' and approval['author_approves_neutral_pdf'] is True,'author approval missing')
require(approval['freeze_authorized'] is True and approval['tag_creation_authorized'] is True and approval['osf_snapshot_authorized'] is True,'freeze authorization missing')
require(approval['arxiv_submission_authorized'] is False,'arXiv submission must remain unauthorized')
require(approval['arxiv_metadata_frozen'] is False,'arXiv metadata must remain deferred')
require(approval['public_infrastructure_update_started'] is False,'public infrastructure must remain deferred')
require(approval['formal_m1_8_closed'] is False,'formal closure must await Git/OSF verification')
require(mentor['status']=='TECHNICAL_CLOSURE_PASS_FREEZE_AUTHORIZED','mentor closure audit')
require(visual_eq['render_comparison']['status']=='PASS' and visual_eq['render_comparison']['identical_render_pages']=='22/22','visual equivalence audit')

bundle_files=sorted(p.name for p in B.iterdir() if p.is_file())
require(len(bundle_files)==11,'bundle must contain 11 files')
expected=sorted(['manuscript_arxiv_neutral.tex','references.bib']+[f'fig0{i}.pdf' for i in range(1,6)]+[f'table0{i}.tex' for i in range(1,5)])
require(bundle_files==expected,'bundle universe mismatch')
require(not any(x.endswith(('.aux','.log','.out','.toc','.synctex.gz','.bbl','.bcf','.blg','.run.xml')) for x in bundle_files),'build outputs in bundle')
require((BUILD/'manuscript_arxiv_neutral.pdf').exists(),'canonical PDF missing')
require(sha(BUILD/'manuscript_arxiv_neutral.pdf')==approval['canonical_freeze_pdf_sha256'],'canonical PDF hash mismatch')

for f in bundle_files:
    require((S/f).exists() and (S/f).read_bytes()==(B/f).read_bytes(),'source/bundle byte mismatch '+f)

sum_lines=[x for x in (E/'SHA256SUMS.txt').read_text().splitlines() if x.strip()]
for line in sum_lines:
    exp,rel=line.split('  ',1)
    p=T/rel
    require(p.exists() and sha(p)==exp,'checksum mismatch '+rel)

print('MANUSCRIPT1_ARXIV_NEUTRAL_AUTHOR_APPROVED_VALIDATION_PASS')
print('claims = 27/27')
print('numeric_items = 120/120')
print('scientific_references = 8/8')
print('figures = 5/5 byte-exact M1.6')
print('tables = 4/4')
print('clean_directory_compile = PASS')
print('automated_pdf_status = PASS')
print('author_visual_status = 22/22 PASS')
print('freeze_authorized = true')
print('arxiv_submission_authorized = false')
print('formal_m1_8_closed = false')
