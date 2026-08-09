#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, json, os, re, subprocess, sys, tempfile, time
import urllib.error, urllib.parse, urllib.request, xml.etree.ElementTree as ET, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML required: python -m pip install pyyaml") from exc

SCRIPT_VERSION = "1.1.0"
AUDIT_ID = "tess_qpp_bibliographic_audit_ii_v1"
DESIGN_TAG = "bibliographic-audit-ii-design-v2"
DESIGN_COMMIT = "a53ea8c5935e686df1fe8680b9c36bdf5111d05e"
BAII = Path("docs/literature/bibliographic_audit_ii")
SEARCH_PLAN = BAII / "search_plan.yaml"

NORMATIVE_HASHES = {
    BAII / "protocol.md": "75b7d372c778364882047d859ad90598c8fd553cbb1e70ddfae39c3d35e21927",
    BAII / "search_plan.yaml": "a76420e4603baeda95d70c8d3308bc614458d09d9769979d327ef79bf9a52f28",
    BAII / "screening_schema.csv": "0c9031aae2d9f5c674c5e4c3e0f4201af81cc0fabdc3e325fb863cebe8f69d0f",
    BAII / "audit_preregistration.json": "64f182980f8494b2242a7743151441718ca8a50d177ceb6442b8e5540742ae84",
    BAII / "amendments" / "BAII_DESIGN_V1_1_0.md": "ec076cc629ebc46c35253a1a0670023523700a0dc3c6b7f68baeb06f876ef514",
}
QUERY_IDS = [
    "Q01_DIRECT_TESS_QPP",
    "Q02_TESS_STELLAR_FLARE_PERIODICITY",
    "Q03_TESS_QPP_CATALOG",
    "Q04_QPP_DETECTION_METHOD",
    "Q05_INJECTION_RECOVERY_SELECTION",
    "Q06_AFINO_RELATED",
]
ADS_ENDPOINT = "https://scixplorer.org/v1/search/query"
ARXIV_ENDPOINT = "https://export.arxiv.org/api/query"
ADS_PAGE_SIZE, ARXIV_PAGE_SIZE, ARXIV_DELAY = 200, 100, 3.1
TIMEOUT = 120
ADS_FIELDS = [
    "id","bibcode","alternate_bibcode","title","author","date","pubdate","doi","eid",
    "abstract","pub","property","doctype","year","arxiv_class","entry_date",
    "metadata_mtime","indexstamp"
]
EXEC_FIELDS = [
    "execution_id","query_id","source_database","exact_query_string","execution_start_utc",
    "execution_end_utc","date_start","date_end","reported_total_results","records_retrieved",
    "page_count","page_size","first_source_record_id","last_source_record_id",
    "raw_payload_directory","raw_payload_file_count","raw_payload_combined_sha256",
    "execution_status","error"
]
LEDGER_FIELDS = [
    "raw_hit_id","execution_id","query_id","source_database","source_rank","source_record_id",
    "title","authors_raw","source_date","publication_date_raw","updated_date_raw","doi_raw",
    "arxiv_id_raw","bibcode_raw","journal_reference_raw","publication_status_raw",
    "abstract_available","abstract_sha256","provider_metadata_json","raw_payload_filename",
    "raw_payload_record_locator","retrieval_status","error"
]
ATOM, OPEN, ARX = "http://www.w3.org/2005/Atom", "http://a9.com/-/spec/opensearch/1.1/", "http://arxiv.org/schemas/atom"
NS = {"atom": ATOM, "opensearch": OPEN, "arxiv": ARX}
USER_AGENT = f"tess-qpp-baii2/{SCRIPT_VERSION}"

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for c in iter(lambda:f.read(1024*1024), b""): h.update(c)
    return h.hexdigest()

def cjson(v): return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",",":"))
def ws(s): return re.sub(r"\s+"," ",s or "").strip()
def raw(v):
    if v is None: return ""
    return cjson(v) if isinstance(v,(list,dict)) else str(v)

def git(root,*args,check=True):
    cp=subprocess.run(["git",*args],cwd=root,text=True,capture_output=True)
    if check and cp.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed\n{cp.stdout}\n{cp.stderr}")
    return cp

def repo_root():
    cp=subprocess.run(["git","rev-parse","--show-toplevel"],text=True,capture_output=True)
    if cp.returncode: raise RuntimeError("Run from inside the tess-qpp Git repository.")
    return Path(cp.stdout.strip()).resolve()

def verify(root):
    observed={}
    for rel, expected in NORMATIVE_HASHES.items():
        path=root/rel
        if not path.is_file(): raise RuntimeError(f"Missing normative input: {rel}")
        actual=sha_file(path); observed[rel.as_posix()]=actual
        if actual != expected:
            raise RuntimeError(f"NORMATIVE HASH MISMATCH: {rel}\nexpected={expected}\nobserved={actual}")
    tagged=git(root,"rev-parse",f"{DESIGN_TAG}^{{}}").stdout.strip()
    if tagged != DESIGN_COMMIT:
        raise RuntimeError(f"Design tag mismatch: {tagged} != {DESIGN_COMMIT}")
    for rel in ["foundation/f0-f2/","workflows/phase3a/","workflows/phase3b/"]:
        out=git(root,"status","--short","--",rel).stdout.strip()
        if out: raise RuntimeError(f"Protected scope modified: {rel}\n{out}")
    return observed

def load_plan(root):
    data=yaml.safe_load((root/SEARCH_PLAN).read_text(encoding="utf-8"))
    qs=data.get("queries",[])
    if len(qs)!=6 or [q.get("query_id") for q in qs] != QUERY_IDS:
        raise RuntimeError("Frozen six-query order does not match BAII.1.")
    return data

def specs(plan, provider):
    out=[]; n=0
    for q in plan["queries"]:
        for prov in ("ads","arxiv"):
            n+=1
            if provider not in ("all",prov): continue
            out.append({
                "execution_id":f"BAII2E{n:03d}",
                "query_id":q["query_id"], "provider":prov,
                "query":q["scix_ads_query"] if prov=="ads" else q["arxiv_query"],
                "date_start":str(q["date_start"]), "date_end":str(q["date_end"])
            })
    return out

def request_bytes(url,params,headers=None):
    req=urllib.request.Request(
        url+"?"+urllib.parse.urlencode(params),
        headers={"User-Agent":USER_AGENT, **(headers or {})}
    )
    try:
        with urllib.request.urlopen(req,timeout=TIMEOUT) as r: return r.read()
    except urllib.error.HTTPError as e:
        excerpt=e.read()[:3000].decode("utf-8","replace")
        raise RuntimeError(f"HTTP {e.code}: {excerpt}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}") from e

def combined(paths):
    h=hashlib.sha256()
    for p in sorted(paths):
        h.update(Path(p).read_bytes())
    return h.hexdigest()

def receipt_path(raw_root,prov,qid):
    d="ads_scix" if prov=="ads" else "arxiv"
    return raw_root/d/qid/"execution_receipt.json"

def save_receipt(path,d):
    path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def retrieve_ads(s,raw_root,token):
    target=raw_root/"ads_scix"/s["query_id"]; target.mkdir(parents=True)
    start_t=now(); pages=[]; total=None; got=0; start=0; err=""
    try:
        while True:
            body=request_bytes(ADS_ENDPOINT,{
                "q":s["query"],"fl":",".join(ADS_FIELDS),"rows":ADS_PAGE_SIZE,"start":start
            },{"Authorization":f"Bearer {token}"})
            page=target/f"page_{len(pages)+1:04d}.json"; page.write_bytes(body); pages.append(page)
            obj=json.loads(body.decode("utf-8")); response=obj["response"]; docs=response.get("docs",[])
            n=int(response.get("numFound",0))
            if total is None: total=n
            elif n!=total: raise RuntimeError(f"numFound changed {total}->{n}")
            got+=len(docs); start+=len(docs)
            if got>=total: break
            if not docs: raise RuntimeError(f"zero-doc page before total reached ({got}/{total})")
        status="COMPLETE" if got==total else "PARTIAL"
        if got!=total: err=f"reported={total}; retrieved={got}"
    except Exception as e:
        status="FAILED" if got==0 else "PARTIAL"; err=f"{type(e).__name__}: {e}"
    r={
        "execution_id":s["execution_id"],"query_id":s["query_id"],"source_database":"ADS_SCIX",
        "exact_query_string":s["query"],"execution_start_utc":start_t,"execution_end_utc":now(),
        "date_start":s["date_start"],"date_end":s["date_end"],"reported_total_results":total,
        "records_retrieved":got,"page_count":len(pages),"page_size":ADS_PAGE_SIZE,
        "raw_payload_directory":(Path("local_archive/bibliographic_audit_ii/baii2_raw")/"ads_scix"/s["query_id"]).as_posix(),"raw_payload_file_count":len(pages),
        "raw_payload_combined_sha256":combined(pages) if pages else "",
        "execution_status":status,"error":err
    }
    save_receipt(target/"execution_receipt.json",r); return r

class Limiter:
    def __init__(self): self.last=None
    def wait(self):
        if self.last is not None:
            remain=ARXIV_DELAY-(time.monotonic()-self.last)
            if remain>0: time.sleep(remain)
        self.last=time.monotonic()

def parse_arxiv(body):
    root=ET.fromstring(body)
    t=root.find("opensearch:totalResults",NS)
    if t is None or t.text is None: raise RuntimeError("missing arXiv totalResults")
    return int(t.text.strip()), root.findall("atom:entry",NS)

def retrieve_arxiv(s,raw_root,limiter):
    target=raw_root/"arxiv"/s["query_id"]; target.mkdir(parents=True)
    start_t=now(); pages=[]; total=None; got=0; start=0; err=""
    try:
        while True:
            limiter.wait()
            body=request_bytes(ARXIV_ENDPOINT,{"search_query":s["query"],"start":start,"max_results":ARXIV_PAGE_SIZE})
            page=target/f"page_{len(pages)+1:04d}.xml"; page.write_bytes(body); pages.append(page)
            n,entries=parse_arxiv(body)
            if total is None:
                total=n
                if total>30000: raise RuntimeError(f"arXiv total {total} exceeds API retrieval limit")
            elif n!=total: raise RuntimeError(f"totalResults changed {total}->{n}")
            got+=len(entries); start+=len(entries)
            if got>=total: break
            if not entries: raise RuntimeError(f"zero-entry page before total reached ({got}/{total})")
        status="COMPLETE" if got==total else "PARTIAL"
        if got!=total: err=f"reported={total}; retrieved={got}"
    except Exception as e:
        status="FAILED" if got==0 else "PARTIAL"; err=f"{type(e).__name__}: {e}"
    r={
        "execution_id":s["execution_id"],"query_id":s["query_id"],"source_database":"ARXIV",
        "exact_query_string":s["query"],"execution_start_utc":start_t,"execution_end_utc":now(),
        "date_start":s["date_start"],"date_end":s["date_end"],"reported_total_results":total,
        "records_retrieved":got,"page_count":len(pages),"page_size":ARXIV_PAGE_SIZE,
        "raw_payload_directory":(Path("local_archive/bibliographic_audit_ii/baii2_raw")/"arxiv"/s["query_id"]).as_posix(),"raw_payload_file_count":len(pages),
        "raw_payload_combined_sha256":combined(pages) if pages else "",
        "execution_status":status,"error":err
    }
    save_receipt(target/"execution_receipt.json",r); return r

def page_files(raw_root,s):
    d="ads_scix" if s["provider"]=="ads" else "arxiv"
    ext="json" if s["provider"]=="ads" else "xml"
    return sorted((raw_root/d/s["query_id"]).glob(f"page_*.{ext}"))

def find_ads_arxiv_id(doc):
    vals=doc.get("eid",[]); vals=vals if isinstance(vals,list) else [vals]
    for v in vals:
        x=str(v)
        if re.fullmatch(r"(?:arXiv:)?\d{4}\.\d{4,5}(?:v\d+)?",x) or re.fullmatch(r"[a-z-]+/\d{7}(?:v\d+)?",x):
            return x
    return ""

def norm_ads(body,s,name,start_rank):
    docs=json.loads(body.decode("utf-8")).get("response",{}).get("docs",[])
    rows=[]
    for i,d in enumerate(docs):
        ab=d.get("abstract") if isinstance(d.get("abstract"),str) else ""
        title=d.get("title",[""]); title=title[0] if isinstance(title,list) and title else title if isinstance(title,str) else ""
        authors=d.get("author",[]); authors=authors if isinstance(authors,list) else [authors]
        bib=raw(d.get("bibcode")); sid=bib or raw(d.get("id"))
        meta={k:v for k,v in d.items() if k!="abstract"}
        rows.append({
            "execution_id":s["execution_id"],"query_id":s["query_id"],"source_database":"ADS_SCIX",
            "source_rank":str(start_rank+i),"source_record_id":sid,"title":ws(title),"authors_raw":cjson(authors),
            "source_date":raw(d.get("date") or d.get("pubdate")),"publication_date_raw":raw(d.get("pubdate") or d.get("date")),
            "updated_date_raw":raw(d.get("metadata_mtime")),"doi_raw":raw(d.get("doi")),
            "arxiv_id_raw":find_ads_arxiv_id(d),"bibcode_raw":bib,"journal_reference_raw":raw(d.get("pub")),
            "publication_status_raw":raw(d.get("property")),"abstract_available":"true" if ab else "false",
            "abstract_sha256":sha_bytes(ab.encode()) if ab else "","provider_metadata_json":cjson(meta),
            "raw_payload_filename":name,"raw_payload_record_locator":f"response.docs[{i}]",
            "retrieval_status":"RETRIEVED","error":""
        })
    return rows

def tx(entry,path):
    e=entry.find(path,NS); return e.text if e is not None and e.text is not None else ""

def norm_arxiv(body,s,name,start_rank):
    root=ET.fromstring(body); rows=[]
    for i,e in enumerate(root.findall("atom:entry",NS)):
        eid=tx(e,"atom:id"); aid=eid.rsplit("/",1)[-1] if eid else ""; summary=tx(e,"atom:summary")
        authors=[a.findtext(f"{{{ATOM}}}name") or "" for a in e.findall("atom:author",NS)]
        pc=e.find("arxiv:primary_category",NS)
        meta={
            "id":eid,"published":tx(e,"atom:published"),"updated":tx(e,"atom:updated"),"title":tx(e,"atom:title"),
            "authors":authors,"doi":tx(e,"arxiv:doi"),"journal_ref":tx(e,"arxiv:journal_ref"),
            "comment":tx(e,"arxiv:comment"),"primary_category":pc.attrib.get("term","") if pc is not None else "",
            "categories":[x.attrib.get("term","") for x in e.findall("atom:category",NS)],
            "links":[dict(sorted(x.attrib.items())) for x in e.findall("atom:link",NS)]
        }
        rows.append({
            "execution_id":s["execution_id"],"query_id":s["query_id"],"source_database":"ARXIV",
            "source_rank":str(start_rank+i),"source_record_id":aid,"title":ws(meta["title"]),"authors_raw":cjson(authors),
            "source_date":meta["published"],"publication_date_raw":meta["published"],"updated_date_raw":meta["updated"],
            "doi_raw":meta["doi"],"arxiv_id_raw":aid,"bibcode_raw":"","journal_reference_raw":ws(meta["journal_ref"]),
            "publication_status_raw":"","abstract_available":"true" if summary else "false",
            "abstract_sha256":sha_bytes(summary.encode()) if summary else "","provider_metadata_json":cjson(meta),
            "raw_payload_filename":name,"raw_payload_record_locator":f"feed/entry[{i+1}]",
            "retrieval_status":"RETRIEVED","error":""
        })
    return rows

def ledger_from_raw(raw_root,spec_list):
    allrows=[]; hit=0
    for s in spec_list:
        rank=1; ex=[]
        for p in page_files(raw_root,s):
            rows=norm_ads(p.read_bytes(),s,p.name,rank) if s["provider"]=="ads" else norm_arxiv(p.read_bytes(),s,p.name,rank)
            ex+=rows; rank+=len(rows)
        if [int(r["source_rank"]) for r in ex] != list(range(1,len(ex)+1)):
            raise RuntimeError(f"non-contiguous source_rank {s['execution_id']}")
        for r in ex:
            hit+=1; allrows.append({"raw_hit_id":f"BAII2H{hit:06d}",**r})
    return allrows

def write_csv(path,fields,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n"); w.writeheader()
        for r in rows: w.writerow({k:r.get(k,"") for k in fields})

def log_from_raw(raw_root,spec_list,ledger):
    by={}
    for r in ledger: by.setdefault(r["execution_id"],[]).append(r)
    out=[]
    for s in spec_list:
        rp=receipt_path(raw_root,s["provider"],s["query_id"])
        rec=json.loads(rp.read_text(encoding="utf-8")); hits=by.get(s["execution_id"],[])
        rec["first_source_record_id"]=hits[0]["source_record_id"] if hits else ""
        rec["last_source_record_id"]=hits[-1]["source_record_id"] if hits else ""
        if int(rec.get("records_retrieved") or 0)!=len(hits):
            rec["execution_status"]="PARTIAL"; rec["error"]=(rec.get("error","")+"; normalization row mismatch").strip("; ")
        out.append(rec)
    return out

def exact_rebuild(raw_root,spec_list,ledger_path):
    rebuilt=ledger_from_raw(raw_root,spec_list)
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td)/"ledger.csv"; write_csv(tmp,LEDGER_FIELDS,rebuilt)
        if tmp.read_bytes()!=ledger_path.read_bytes(): raise RuntimeError("RAW_LEDGER_REBUILD_EXACT failed")
    return "RAW_LEDGER_REBUILD_EXACT"

def counts(ledger):
    bp,bq,bqp,uniq={},{},{},{}
    for r in ledger:
        p,q=r["source_database"],r["query_id"]; bp[p]=bp.get(p,0)+1; bq[q]=bq.get(q,0)+1
        bqp[f"{q}|{p}"]=bqp.get(f"{q}|{p}",0)+1; uniq.setdefault(p,set()).add(r["source_record_id"])
    return {
        "by_provider":dict(sorted(bp.items())),"by_query_id":{q:bq.get(q,0) for q in QUERY_IDS},
        "by_query_id_provider":dict(sorted(bqp.items())),
        "unique_source_record_ids_within_provider":{p:len(v) for p,v in sorted(uniq.items())}
    }

def make_manifest(spec_list,logs,ledger,norm,rebuild):
    succ=sum(r["execution_status"]=="COMPLETE" for r in logs)
    part=sum(r["execution_status"]=="PARTIAL" for r in logs); fail=sum(r["execution_status"]=="FAILED" for r in logs)
    complete=len(spec_list)==12 and succ==12 and not part and not fail
    return {
        "audit_id":AUDIT_ID,"audit_version":"1.1.0","retrieval_task":"BAII.2",
        "retrieval_status":"RAW_BIBLIOGRAPHIC_CORPUS_RETRIEVED_PENDING_ARCHIVE" if complete else "RAW_BIBLIOGRAPHIC_CORPUS_RETRIEVAL_INCOMPLETE",
        "script_version":SCRIPT_VERSION,"design_tag":DESIGN_TAG,"design_commit":DESIGN_COMMIT,
        "design_amendment_version":"1.1.0","prior_design_tag":"bibliographic-audit-ii-design-v1","prior_design_commit":"24b3ddde7a9b7baf35f6b236d83e80ec20571c95",
        "normative_input_sha256":norm,"search_window_start":"2024-01-01","search_window_end":"2026-08-07",
        "query_count":6,"provider_count":2,"planned_executions":12,"attempted_executions_this_run":len(spec_list),
        "successful_executions":succ,"partial_executions":part,"failed_executions":fail,"raw_hit_rows":len(ledger),
        **counts(ledger),"raw_ledger_rebuild_status":rebuild,
        "screening_performed":False,"deduplication_performed":False,"work_ids_assigned":False,
        "inclusion_decisions_made":False,"design_impact_assessed":False,"novelty_assessed":False,
        "f3a_modified":False,"f3b_modified":False,"f0_f2_modified":False,
        "osf_snapshot_filename":"bibliographic_audit_ii_raw_corpus_v1.zip","osf_snapshot_sha256":None,
        "osf_snapshot_status":"PENDING_REVIEW_AND_ARCHIVAL"
    }

def retrieval_readme(complete):
    st="RAW CORPUS RETRIEVED — FREEZE PENDING REVIEW/OSF" if complete else "RAW CORPUS RETRIEVAL INCOMPLETE — SCREENING NOT STARTED"
    return f"""# Bibliographic Audit II — BAII.2 retrieval

**STATUS:** `{st}`

Duplicate hits are expected and preserved. Seed sources remain separate. No `work_id` exists yet.
No paper has been included or excluded. No design-impact or novelty judgment has been made.
Raw provider payloads remain outside Git under `local_archive/bibliographic_audit_ii/baii2_raw/`.

Final status `RAW CORPUS FROZEN — SCREENING NOT STARTED` is applied only after review, OSF archival,
final manifest hashing, Git commit and corpus tag.
"""

def sums(retrieval):
    names=["README.md","search_execution_log.csv","raw_hit_ledger.csv","retrieval_manifest.json"]
    (retrieval/"SHA256SUMS.txt").write_text("".join(f"{sha_file(retrieval/n)}  {n}\n" for n in names),encoding="ascii")

def review_bundle(root,raw_root,retrieval,out):
    if out.exists(): raise RuntimeError(f"review bundle already exists: {out}")
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
        for p in sorted(raw_root.rglob("*")):
            if p.is_file():
                z.write(p,(Path("local_archive/bibliographic_audit_ii/baii2_raw")/p.relative_to(raw_root)).as_posix())
        for p in sorted(retrieval.rglob("*")):
            if p.is_file(): z.write(p,p.relative_to(root).as_posix())
        z.write(root/SEARCH_PLAN,SEARCH_PLAN.as_posix())
        z.write(Path(__file__).resolve(),(BAII/"scripts/retrieve_raw_corpus.py").as_posix())
    with zipfile.ZipFile(out) as z:
        bad=z.testzip()
        if bad: raise RuntimeError(f"bad bundle member: {bad}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--provider",choices=["ads","arxiv","all"],default="all")
    ap.add_argument("--raw-output-root",type=Path,required=True)
    ap.add_argument("--git-output-root",type=Path,required=True)
    ap.add_argument("--review-bundle-output",type=Path)
    ap.add_argument("--preflight-only",action="store_true")
    a=ap.parse_args()
    root=repo_root(); norm=verify(root); plan=load_plan(root)
    print("===== BAII.2 PREFLIGHT =====")
    print("audit_version: 1.1.0")
    print("normative_hashes: OK"); print(f"design_tag: {DESIGN_TAG} -> {DESIGN_COMMIT}")
    print("query_families: 6"); print("providers: 2"); print("planned_executions: 12")
    print("ADS_endpoint:", ADS_ENDPOINT)
    print("ADS_DEV_KEY_present:", "YES" if os.environ.get("ADS_DEV_KEY", "").strip() else "NO")
    print("systematic_searches_executed_by_preflight: 0")
    if a.preflight_only: return 0
    ss=specs(plan,a.provider)
    token=os.environ.get("ADS_DEV_KEY","").strip()
    if a.provider in ("ads","all") and not token: raise RuntimeError("ADS_DEV_KEY not set; no network request made.")
    raw_root=(root/a.raw_output_root).resolve() if not a.raw_output_root.is_absolute() else a.raw_output_root.resolve()
    retrieval=(root/a.git_output_root).resolve() if not a.git_output_root.is_absolute() else a.git_output_root.resolve()
    if raw_root.exists() and any(raw_root.rglob("*")): raise RuntimeError(f"raw output not empty: {raw_root}")
    if retrieval.exists() and any((retrieval/n).exists() for n in ["README.md","search_execution_log.csv","raw_hit_ledger.csv","retrieval_manifest.json","SHA256SUMS.txt"]):
        raise RuntimeError(f"retrieval draft outputs already exist: {retrieval}")
    raw_root.mkdir(parents=True,exist_ok=True); retrieval.mkdir(parents=True,exist_ok=True)
    lim=Limiter()
    for s in ss:
        print(f"{s['execution_id']} | {s['query_id']} | {s['provider']}")
        r=retrieve_ads(s,raw_root,token) if s["provider"]=="ads" else retrieve_arxiv(s,raw_root,lim)
        print(f"  {r['execution_status']} total={r['reported_total_results']} retrieved={r['records_retrieved']} pages={r['page_count']}")
        if r["error"]: print("  error:",r["error"])
    ledger=ledger_from_raw(raw_root,ss); ledger_path=retrieval/"raw_hit_ledger.csv"; write_csv(ledger_path,LEDGER_FIELDS,ledger)
    logs=log_from_raw(raw_root,ss,ledger); write_csv(retrieval/"search_execution_log.csv",EXEC_FIELDS,logs)
    rebuild=exact_rebuild(raw_root,ss,ledger_path)
    complete=len(ss)==12 and all(r["execution_status"]=="COMPLETE" and int(r["reported_total_results"])==int(r["records_retrieved"]) for r in logs)
    (retrieval/"README.md").write_text(retrieval_readme(complete),encoding="utf-8")
    manifest=make_manifest(ss,logs,ledger,norm,rebuild)
    (retrieval/"retrieval_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); sums(retrieval)
    verify(root)
    out=a.review_bundle_output or Path("local_archive/bibliographic_audit_ii/baii2_review_bundle.zip")
    out=(root/out).resolve() if not out.is_absolute() else out.resolve()
    review_bundle(root,raw_root,retrieval,out)
    print("===== BAII.2 LOCAL SUMMARY =====")
    print("successful_executions:",sum(r["execution_status"]=="COMPLETE" for r in logs))
    print("partial_executions:",sum(r["execution_status"]=="PARTIAL" for r in logs))
    print("failed_executions:",sum(r["execution_status"]=="FAILED" for r in logs))
    print("raw_hit_rows:",len(ledger)); print("raw_ledger_rebuild_status:",rebuild)
    print("review_bundle:",out); print("review_bundle_sha256:",sha_file(out))
    print("screening_decisions: 0"); print("work_id_assignments: 0"); print("design_impact_assignments: 0"); print("novelty_assessments: 0"); print("F0-F2_modified: 0"); print("F3A_modified: 0"); print("F3B_modified: 0")
    if not complete:
        print("BAII.2 INCOMPLETE — DO NOT COMMIT, TAG, SCREEN OR UPLOAD TO OSF.")
        return 2
    print("BAII.2 RAW RETRIEVAL COMPLETE — FREEZE PENDING REVIEW.")
    print("DO NOT SCREEN, DEDUPLICATE, COMMIT, TAG OR UPLOAD TO OSF YET.")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as e:
        print(f"BAII.2 BLOCKED: {e}",file=sys.stderr)
        raise
