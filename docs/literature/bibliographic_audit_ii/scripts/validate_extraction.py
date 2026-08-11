#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

EXPECTED = {
    "screened_works.csv": "143aa10bb942780e250f6b5cb9489acfa8bbc2a05b633624a4856d4d245533e2",
    "screening_decision_log.csv": "b80b2a01e488b4ebe7f4c833a58f192de5d55e216bdeb66b9e2ed896d2bc16cb",
    "work_registry.csv": "eacaa8ad6f0ba78a91adf9bf8327d1727c6e045a0f7771ba32837c0eaf089661",
    "version_registry.csv": "33d2ef5e00bd3d343a01184b08b93aa8128ed739bb98ce86472dac93c12c6cdc",
    "screening_manifest.json": "b8d53cc6f51cfbf33ba3fd5d32a5651c0db772842d9fdab678d70f0f15ef7dba",
    "f3_overlap_reference.json": "1b6be4a17d23457d3164b23c4b16557467e84ae44bbb35df57064b7c9566639e",
}
LABELS = {
    "DIRECT_F3A_OVERLAP", "DIRECT_F3B_OVERLAP", "CATALOG_RELEVANT",
    "DETECTION_METHOD_RELEVANT", "ROBUSTNESS_RELEVANT",
    "SELECTION_FUNCTION_RELEVANT", "PHYSICAL_CONTEXT", "BACKGROUND_ONLY",
}
F3A_IMPACTS = {"NO_DESIGN_IMPACT", "F3A_DESIGN_ADJUSTMENT_POSSIBLE", "F3A_REDRAFT_REQUIRED"}
F3B_IMPACTS = {"NO_DESIGN_IMPACT", "F3B_DESIGN_ADJUSTMENT_POSSIBLE"}
POSITIONING_IMPACTS = {"NO_DESIGN_IMPACT", "POSITIONING_ONLY"}
OVERLAP_LEVELS = {"DIRECT", "PARTIAL", "CONTEXT_ONLY", "NONE", "UNRESOLVED"}
EXTRACTION_STATUSES = {
    "COMPLETE", "COMPLETE_WITH_NOT_REPORTED_FIELDS",
    "COMPLETE_WITH_ACCESS_LIMITATION", "BLOCKED",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def split_values(value: str) -> list[str]:
    return [v for v in value.split(";") if v]


def main() -> int:
    ap = argparse.ArgumentParser(description="Offline BAII.4 extraction validator.")
    ap.add_argument("--repo-root", type=Path, default=Path("."))
    args = ap.parse_args()

    baii = args.repo_root / "docs/literature/bibliographic_audit_ii"
    screening = baii / "screening"
    extraction_dir = baii / "extraction"

    for name in [
        "screened_works.csv", "screening_decision_log.csv", "work_registry.csv",
        "version_registry.csv", "screening_manifest.json",
    ]:
        observed = sha256(screening / name)
        assert observed == EXPECTED[name], (name, observed)
    assert sha256(extraction_dir / "f3_overlap_reference.json") == EXPECTED["f3_overlap_reference.json"]

    screened = read_csv(screening / "screened_works.csv")
    works = {r["work_id"]: r for r in read_csv(screening / "work_registry.csv")}
    versions = {r["version_id"]: r for r in read_csv(screening / "version_registry.csv")}
    included = {r["work_id"] for r in screened if r["screening_decision"] == "INCLUDE_FOR_BAII4"}
    excluded_or_background = {
        r["work_id"] for r in screened if r["screening_decision"] != "INCLUDE_FOR_BAII4"
    }
    assert len(included) == 40

    extraction = read_csv(extraction_dir / "included_work_extraction.csv")
    overlap = read_csv(extraction_dir / "overlap_assessment.csv")
    evidence = read_csv(extraction_dir / "extraction_evidence_log.csv")
    dimension = read_csv(extraction_dir / "overlap_dimension_evidence.csv")
    access = read_csv(extraction_dir / "source_access_log.csv")
    manifest = json.loads((extraction_dir / "extraction_manifest.json").read_text(encoding="utf-8"))

    extraction_ids = [r["work_id"] for r in extraction]
    overlap_ids = [r["work_id"] for r in overlap]
    assert len(extraction) == 40 and len(overlap) == 40
    assert len(extraction_ids) == len(set(extraction_ids))
    assert len(overlap_ids) == len(set(overlap_ids))
    assert set(extraction_ids) == included == set(overlap_ids)
    assert not (set(extraction_ids) & excluded_or_background)

    for r in extraction:
        assert r["extraction_status"] in EXTRACTION_STATUSES
        assert r["extraction_status"] != "BLOCKED"
        wid = r["work_id"]
        vid = r["preferred_version_id"]
        assert wid in works and vid in versions
        assert works[wid]["preferred_version_id"] == vid
        assert versions[vid]["work_id"] == wid
        assert versions[vid]["is_preferred_version"].lower() == "true"

    evidence_ids = [r["evidence_id"] for r in evidence]
    assert len(evidence_ids) == len(set(evidence_ids))
    evidence_set = set(evidence_ids)
    evidence_work_ids = {r["work_id"] for r in evidence}
    assert evidence_work_ids == included

    dimension_ids = [r["overlap_evidence_id"] for r in dimension]
    assert len(dimension_ids) == len(set(dimension_ids))
    for r in dimension:
        assert r["work_id"] in included
        assert r["overlap_level"] in OVERLAP_LEVELS
        refs = split_values(r["evidence_ids"])
        assert refs and set(refs) <= evidence_set

    dimension_by_work_phase = Counter((r["work_id"], r["target_phase"]) for r in dimension)
    referenced_evidence = set()
    for r in overlap:
        wid = r["work_id"]
        labels = split_values(r["relevance_labels"])
        assert labels and set(labels) <= LABELS
        assert "BACKGROUND_ONLY" not in labels
        assert r["direct_f3a_overlap"] in OVERLAP_LEVELS
        assert r["direct_f3b_overlap"] in OVERLAP_LEVELS
        assert r["f3a_design_impact"] in F3A_IMPACTS
        assert r["f3b_design_impact"] in F3B_IMPACTS
        assert r["manuscript1_positioning_impact"] in POSITIONING_IMPACTS

        nonzero_impact = (
            r["f3a_design_impact"] != "NO_DESIGN_IMPACT"
            or r["f3b_design_impact"] != "NO_DESIGN_IMPACT"
            or r["manuscript1_positioning_impact"] != "NO_DESIGN_IMPACT"
        )
        if nonzero_impact:
            assert r["design_issue_description"] not in {"", "NOT_APPLICABLE"}
            refs = split_values(r["design_issue_evidence_ids"])
            assert refs and set(refs) <= evidence_set
            referenced_evidence.update(refs)

        if r["direct_f3a_overlap"] in {"DIRECT", "PARTIAL"}:
            assert dimension_by_work_phase[(wid, "F3A")] > 0
        if r["direct_f3b_overlap"] in {"DIRECT", "PARTIAL"}:
            assert dimension_by_work_phase[(wid, "F3B")] > 0

    for r in dimension:
        referenced_evidence.update(split_values(r["evidence_ids"]))
    assert referenced_evidence <= evidence_set

    # Every evidence row is either used by an overlap/dimensional claim or belongs to
    # a work whose complete four-row extraction evidence set is retained together.
    by_work = Counter(r["work_id"] for r in evidence)
    assert all(by_work[w] >= 1 for w in included)

    access_ids = [r["access_id"] for r in access]
    assert len(access_ids) == len(set(access_ids))
    assert {r["work_id"] for r in access} == included

    assert manifest["screening_work_count"] == 190
    assert manifest["included_work_count"] == 40
    assert manifest["extracted_work_count"] == 40
    assert manifest["overlap_assessment_rows"] == 40
    assert manifest["evidence_rows"] == len(evidence)
    assert manifest["overlap_dimension_rows"] == len(dimension)
    assert manifest["blocked_work_count"] == 0
    assert manifest["screening_modified"] is False
    assert manifest["work_ids_modified"] is False
    assert manifest["inclusion_decisions_modified"] is False
    assert manifest["f0_f2_modified"] is False
    assert manifest["f3a_modified"] is False
    assert manifest["f3b_modified"] is False
    assert manifest["candidate_discovery_authorized"] is False
    assert manifest["novelty_assessed"] is False
    assert manifest["final_f3a_gate_decision_made"] is False

    print("BAII4_EXTRACTION_VALIDATION_PASS")
    print("screening_included_works=40")
    print("extraction_rows=40")
    print("overlap_rows=40")
    print(f"evidence_rows={len(evidence)}")
    print(f"overlap_dimension_rows={len(dimension)}")
    print(f"access_rows={len(access)}")
    print("blocked_work_count=0")
    print("f3a_modified=false")
    print("f3b_modified=false")
    print("novelty_assessed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
