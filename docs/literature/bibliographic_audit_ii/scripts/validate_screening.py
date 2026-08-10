#!/usr/bin/env python3
"""Offline validator for BAII.3 frozen work resolution and screening."""
from __future__ import annotations
import argparse, csv, json
from collections import Counter, defaultdict
from pathlib import Path

EXPECTED_RAW_HITS = 322

def read_csv(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def fail(msg):
    raise RuntimeError(msg)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo-root",type=Path,default=Path.cwd())
    a=p.parse_args()
    repo=a.repo_root.resolve()
    base=repo/"docs/literature/bibliographic_audit_ii"
    retrieval=base/"retrieval"
    screening=base/"screening"

    raw=read_csv(retrieval/"raw_hit_ledger.csv")
    mapping=read_csv(screening/"raw_hit_to_work_map.csv")
    versions=read_csv(screening/"version_registry.csv")
    works=read_csv(screening/"work_registry.csv")
    screened=read_csv(screening/"screened_works.csv")
    decisions=read_csv(screening/"screening_decision_log.csv")
    manifest=json.loads((screening/"screening_manifest.json").read_text(encoding="utf-8"))

    if len(raw)!=EXPECTED_RAW_HITS: fail(f"raw hit rows {len(raw)} != {EXPECTED_RAW_HITS}")
    if len(mapping)!=EXPECTED_RAW_HITS: fail(f"mapping rows {len(mapping)} != {EXPECTED_RAW_HITS}")

    raw_ids=[r["raw_hit_id"] for r in raw]
    map_ids=[r["raw_hit_id"] for r in mapping]
    if len(set(raw_ids))!=EXPECTED_RAW_HITS: fail("duplicate raw_hit_id in frozen ledger")
    if len(set(map_ids))!=EXPECTED_RAW_HITS: fail("raw_hit_id duplicated in crosswalk")
    if set(raw_ids)!=set(map_ids): fail("raw hit loss/orphan in crosswalk")

    work_ids={r["work_id"] for r in works}
    version_ids={r["version_id"] for r in versions}
    if any(r["work_id"] not in work_ids for r in mapping): fail("mapping references missing work_id")
    if any(r["version_id"] not in version_ids for r in mapping): fail("mapping references missing version_id")
    if any(r["work_id"] not in work_ids for r in versions): fail("version references missing work_id")

    hit_count=Counter(r["work_id"] for r in mapping)
    if any(hit_count[w]<1 for w in work_ids): fail("work with zero raw hits")

    preferred=Counter(r["work_id"] for r in versions if r["is_preferred_version"].lower()=="true")
    if set(preferred)!=work_ids or any(preferred[w]!=1 for w in work_ids):
        fail("not exactly one preferred version per work")

    if len(screened)!=len(works): fail("screened_works row count != work_registry")
    if len(decisions)!=len(works): fail("screening_decision_log row count != work_registry")
    if {r["work_id"] for r in screened}!=work_ids: fail("screened_works work_id mismatch")
    if {r["work_id"] for r in decisions}!=work_ids: fail("decision log work_id mismatch")

    for d in decisions:
        final=d["final_screening_decision"]
        if final=="INCLUDE_FOR_BAII4" and not d["inclusion_criteria_met"].strip():
            fail(f"{d['work_id']} include lacks I criterion")
        if final=="EXCLUDE" and not d["primary_exclusion_criterion"].startswith("E"):
            fail(f"{d['work_id']} exclude lacks primary E criterion")
        if final=="BACKGROUND_ONLY" and not d["decision_evidence_text"].strip():
            fail(f"{d['work_id']} background lacks justification")
        if final=="UNRESOLVED_ACCESS_LIMITATION":
            if d["full_text_required"].lower()!="true" or not d["notes"].strip():
                fail(f"{d['work_id']} unresolved access not documented")

    forbidden_fields=["relevance_labels","f3a_design_impact","f3b_design_impact","manuscript1_positioning_impact"]
    populated=0
    for row in screened:
        for field in forbidden_fields:
            if row.get(field,"").strip():
                populated+=1
    if populated: fail(f"impact/relevance fields populated: {populated}")

    if manifest.get("novelty_assessed") is not False: fail("novelty_assessed must be false")
    if manifest.get("design_impact_assessed") is not False: fail("design_impact_assessed must be false")
    if manifest.get("relevance_labels_assigned") is not False: fail("relevance_labels_assigned must be false")
    if manifest.get("f0_f2_modified") is not False: fail("f0_f2_modified must be false")
    if manifest.get("f3a_modified") is not False or manifest.get("f3b_modified") is not False:
        fail("F3A/F3B modification flag not false")
    if manifest.get("raw_hits_lost")!=0 or manifest.get("raw_hits_multiply_mapped")!=0:
        fail("manifest reports lost/multiply mapped raw hits")

    outcomes=Counter(r["final_screening_decision"] for r in decisions)
    if outcomes["INCLUDE_FOR_BAII4"]!=manifest["include_for_baii4_count"]: fail("include count mismatch")
    if outcomes["BACKGROUND_ONLY"]!=manifest["background_only_count"]: fail("background count mismatch")
    if outcomes["EXCLUDE"]!=manifest["excluded_count"]: fail("exclude count mismatch")
    if outcomes["UNRESOLVED_ACCESS_LIMITATION"]!=manifest["unresolved_access_count"]: fail("unresolved count mismatch")

    print("BAII3_SCREENING_VALIDATION_PASS")
    print(f"raw_hits={len(raw)}")
    print(f"works={len(works)}")
    print(f"versions={len(versions)}")
    print(f"preferred_versions={sum(preferred.values())}")
    print("raw_hits_lost=0")
    print("raw_hits_multiply_mapped=0")
    print("impact_fields_populated=0")
    print("novelty_fields_populated=0")
    print("outcomes="+json.dumps(dict(sorted(outcomes.items())),sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
