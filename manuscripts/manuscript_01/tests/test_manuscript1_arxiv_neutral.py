from pathlib import Path
import csv, json, re, hashlib

ROOT=Path.cwd(); T=ROOT/'manuscripts/manuscript_01/preprint/arxiv_neutral'; E=T/'evidence'; B=T/'bundle'; S=T/'source'; R=T/'review'

def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def test_m1_6_is_normative_and_m1_7_is_not():
    x=json.loads((E/'m1_8_source_bindings.json').read_text())
    assert x['m1_6_commit']=='d1007edcdbcf98b809ed46b0810fd62148f7b2af'
    assert x['m1_7_normative_for_scientific_content'] is False

def test_claims_and_numerics_preserved():
    c=rows(E/'m1_8_scientific_identity_audit.csv'); n=rows(E/'m1_8_numeric_identity_audit.csv')
    assert len(c)==27 and len(n)==120
    assert all(r['status']=='PASS' and r['scientific_content_changed']=='false' for r in c)
    assert all(r['status']=='PASS' and r['scientific_numeric_change_m1_8']=='false' for r in n)

def test_references_figures_tables_preserved():
    assert len(rows(E/'m1_8_reference_identity_audit.csv'))==8
    assert len(rows(E/'m1_8_visual_identity_audit.csv'))==5
    assert len(rows(E/'m1_8_table_identity_audit.csv'))==4
    assert all(r['byte_exact']=='true' for r in rows(E/'m1_8_visual_identity_audit.csv'))
    assert all(r['scientific_content_changed']=='false' for r in rows(E/'m1_8_table_identity_audit.csv'))

def test_neutrality_passes():
    assert all(r['status']=='PASS' for r in rows(E/'m1_8_neutrality_audit.csv'))

def test_bundle_is_minimal_flat_and_source_exact():
    names=sorted(p.name for p in B.iterdir() if p.is_file())
    expected=sorted(['manuscript_arxiv_neutral.tex','references.bib']+[f'fig0{i}.pdf' for i in range(1,6)]+[f'table0{i}.tex' for i in range(1,5)])
    assert names==expected
    assert all((S/n).read_bytes()==(B/n).read_bytes() for n in names)

def test_source_has_no_private_or_journal_scaffolding():
    t=(S/'manuscript_arxiv_neutral.tex').read_text()
    assert 'M1TRACE' not in t and 'M1VISUAL' not in t and 'author_review' not in t
    assert '../' not in t
    assert not re.search(r'\\submitjournal|\\received|\\revised|\\accepted|aastex|linenumbers|\\linenumbers|OJAp|theoj|PASA',t,re.I)

def test_clean_compile_passed():
    x=json.loads((E/'m1_8_compile_audit.json').read_text())
    assert x['clean_directory_compile']=='PASS'
    assert x['automated_pdf_status']=='PASS'
    assert x['undefined_citations']==0 and x['undefined_references']==0 and x['latex_errors']==0
    assert x['overfull_hbox']==0 and x['overfull_vbox']==0
    assert x['author_visual_status']=='PASS'

def test_author_visual_review_is_complete():
    v=rows(R/'m1_8_author_visual_review.csv')
    assert len(v)==22
    fields=('text_layout','figures','tables','section_starts','captions','legibility','overall')
    assert all(all(r[k]=='PASS' for k in fields) for r in v)
    assert all(r['final_review_status']=='PASS' for r in rows(R/'m1_8_author_revision_log.csv'))

def test_author_approval_authorizes_freeze_not_submission():
    a=json.loads((R/'m1_8_author_approval.json').read_text())
    assert a['author_approves_neutral_pdf'] is True
    assert a['author_visual_status']=='PASS'
    assert a['freeze_authorized'] is True and a['tag_creation_authorized'] is True and a['osf_snapshot_authorized'] is True
    assert a['arxiv_submission_authorized'] is False
    assert a['arxiv_metadata_frozen'] is False
    assert a['public_infrastructure_update_started'] is False
    assert a['formal_m1_8_closed'] is False

def test_visual_equivalence_audit_passes():
    x=json.loads((E/'m1_8_author_visual_equivalence_audit.json').read_text())
    assert x['render_comparison']['status']=='PASS'
    assert x['render_comparison']['identical_render_pages']=='22/22'
    assert x['canonical_freeze_pdf']['sha256']=='04e5fc3b4fad60a6877d46b349d9327ccbf7476391a930d1032d81e038db08a5'

def test_figure4_landscape_machinery_retained():
    t=(S/'manuscript_arxiv_neutral.tex').read_text()
    assert '\\begin{landscape}' in t and 'fig04.pdf' in t

def test_no_public_evidence_files_in_bundle():
    names=[p.name for p in B.iterdir() if p.is_file()]
    assert not any(n.endswith('.csv') or n.endswith('.json') for n in names)

def test_mentor_closure_gate():
    x=json.loads((E/'m1_8_mentor_closure_audit.json').read_text())
    assert x['status']=='TECHNICAL_CLOSURE_PASS_FREEZE_AUTHORIZED'
    assert x['authorization']['freeze_authorized'] is True
    assert x['authorization']['arxiv_submission_authorized'] is False
    assert x['authorization']['formal_m1_8_closed'] is False
