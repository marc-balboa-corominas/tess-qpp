#!/usr/bin/env python3
from pathlib import Path
import argparse, json, hashlib, csv, re

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def jread(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def jwrite(p,o): Path(p).write_text(json.dumps(o,indent=2,sort_keys=True)+'\n',encoding='utf-8')

def checksum_tree(final):
    evid=final/'evidence'; out=evid/'SHA256SUMS.txt'; rows=[]
    for p in sorted(final.rglob('*')):
        if p.is_file() and p != out:
            rows.append(f"{sha(p)}  {p.relative_to(final).as_posix()}")
    out.write_text('\n'.join(rows)+'\n',encoding='utf-8')
    return len(rows)

def finalize(repo, distro, cls, bst):
    final=repo/'manuscripts/manuscript_01/submission/final'; meta=final/'metadata/m1_7_submission_metadata.json'; ev=final/'evidence'
    m=jread(meta); m['status']='LOCAL_AASTEX_MATERIALIZED_COMPILE_PENDING'; m['aastex']['distribution_sha256']=sha(distro); m['aastex']['class_sha256']=sha(cls); m['aastex']['bst_sha256']=sha(bst); jwrite(meta,m)
    manifest=ev/'m1_7_submission_asset_manifest.csv'; rows=list(csv.DictReader(manifest.open(encoding='utf-8-sig')))
    for r in rows:
        if r['asset']=='aastex702.cls': r['sha256']=sha(cls); r['status']='MATERIALIZED_OFFICIAL_AAS'
        if r['asset']=='aasjournalv7.1.bst': r['sha256']=sha(bst); r['status']='MATERIALIZED_OFFICIAL_AAS'
    with manifest.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    checksum_tree(final)

def postcompile(repo, portal_ok, arxiv_ok, pdf_path, portal_log, arxiv_log):
    final=repo/'manuscripts/manuscript_01/submission/final'; ev=final/'evidence'; meta=final/'metadata/m1_7_submission_metadata.json'
    pl=Path(portal_log).read_text(errors='replace'); al=Path(arxiv_log).read_text(errors='replace')
    undefined=bool(re.search(r'undefined references|Citation .* undefined|There were undefined',pl,re.I) or re.search(r'undefined references|Citation .* undefined|There were undefined',al,re.I))
    errors=bool(re.search(r'^! ',pl,re.M) or re.search(r'^! ',al,re.M))
    ca=jread(ev/'m1_7_compile_audit.json'); ca.update({'status':'TECHNICAL_COMPILE_PASS_VISUAL_REVIEW_REQUIRED' if portal_ok and arxiv_ok and not errors and not undefined else 'COMPILE_FAIL','flat_portal_compile':'PASS' if portal_ok else 'FAIL','arxiv_source_compile':'PASS' if arxiv_ok else 'FAIL','canonical_pdf_created':Path(pdf_path).exists(),'canonical_pdf_sha256':sha(pdf_path) if Path(pdf_path).exists() else None,'latex_errors':0 if not errors else 'NONZERO','undefined_references':0 if not undefined else 'NONZERO','undefined_citations':0 if not undefined else 'NONZERO','pdf_visual_inspection':'PENDING','pdf_visual_inspection_required':True}); jwrite(ev/'m1_7_compile_audit.json',ca)
    sa=jread(ev/'m1_7_submission_audit.json'); tech=portal_ok and arxiv_ok and not errors and not undefined and Path(pdf_path).exists(); sa.update({'status':'TECHNICAL_PREFLIGHT_PASS_VISUAL_REVIEW_REQUIRED' if tech else 'TECHNICAL_PREFLIGHT_FAIL','journal_format_complete':tech,'submission_bundle_complete':tech,'arxiv_package_complete':arxiv_ok,'submission_ready':False,'blocking_reason':'PDF_VISUAL_REVIEW_REQUIRED' if tech else 'TECHNICAL_COMPILE_FAILURE'}); jwrite(ev/'m1_7_submission_audit.json',sa)
    m=jread(meta); m['status']='TECHNICAL_PREFLIGHT_PASS_VISUAL_REVIEW_REQUIRED' if tech else 'TECHNICAL_PREFLIGHT_FAIL'; m['submission_pdf_sha256']=sha(pdf_path) if Path(pdf_path).exists() else None; jwrite(meta,m)
    checksum_tree(final)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True); ap.add_argument('--finalize',action='store_true'); ap.add_argument('--postcompile',action='store_true'); ap.add_argument('--distro'); ap.add_argument('--classfile'); ap.add_argument('--bst'); ap.add_argument('--portal-ok',action='store_true'); ap.add_argument('--arxiv-ok',action='store_true'); ap.add_argument('--pdf'); ap.add_argument('--portal-log'); ap.add_argument('--arxiv-log'); a=ap.parse_args(); repo=Path(a.repo)
    if a.finalize: finalize(repo,a.distro,a.classfile,a.bst)
    elif a.postcompile: postcompile(repo,a.portal_ok,a.arxiv_ok,a.pdf,a.portal_log,a.arxiv_log)
    else: raise SystemExit('choose --finalize or --postcompile')
