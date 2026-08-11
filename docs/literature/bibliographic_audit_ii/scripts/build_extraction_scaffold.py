#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

EXPECTED = {
    "screened_works.csv": "143aa10bb942780e250f6b5cb9489acfa8bbc2a05b633624a4856d4d245533e2",
    "screening_decision_log.csv": "b80b2a01e488b4ebe7f4c833a58f192de5d55e216bdeb66b9e2ed896d2bc16cb",
    "work_registry.csv": "eacaa8ad6f0ba78a91adf9bf8327d1727c6e045a0f7771ba32837c0eaf089661",
    "version_registry.csv": "33d2ef5e00bd3d343a01184b08b93aa8128ed739bb98ce86472dac93c12c6cdc",
    "screening_manifest.json": "b8d53cc6f51cfbf33ba3fd5d32a5651c0db772842d9fdab678d70f0f15ef7dba",
    "f3_overlap_reference.json": "1b6be4a17d23457d3164b23c4b16557467e84ae44bbb35df57064b7c9566639e",
}

IDENTITY_FIELDS = [
    "work_id", "preferred_version_id", "title", "first_public_date",
    "publication_date", "doi", "arxiv_id", "bibcode", "peer_review_status",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Deterministically rebuild the BAII.4 40-work extraction identity scaffold."
    )
    ap.add_argument("--repo-root", type=Path, default=Path("."))
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--allow-overwrite", action="store_true")
    args = ap.parse_args()

    baii = args.repo_root / "docs/literature/bibliographic_audit_ii"
    screening = baii / "screening"
    extraction = baii / "extraction"

    for name in [
        "screened_works.csv", "screening_decision_log.csv", "work_registry.csv",
        "version_registry.csv", "screening_manifest.json",
    ]:
        observed = sha256(screening / name)
        if observed != EXPECTED[name]:
            raise SystemExit(f"NORMATIVE_HASH_MISMATCH {name}: {observed}")

    observed_ref = sha256(extraction / "f3_overlap_reference.json")
    if observed_ref != EXPECTED["f3_overlap_reference.json"]:
        raise SystemExit(f"F3_REFERENCE_HASH_MISMATCH: {observed_ref}")

    screened = read_csv(screening / "screened_works.csv")
    works = {r["work_id"]: r for r in read_csv(screening / "work_registry.csv")}
    versions = {r["version_id"]: r for r in read_csv(screening / "version_registry.csv")}
    included = [r["work_id"] for r in screened if r["screening_decision"] == "INCLUDE_FOR_BAII4"]

    if len(included) != 40 or len(set(included)) != 40:
        raise SystemExit(f"INCLUDED_WORK_COUNT_INVALID: {len(included)}")

    out = args.output_dir / "included_work_identity_scaffold.csv"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if out.exists() and not args.allow_overwrite:
        raise SystemExit(f"REFUSING_TO_OVERWRITE {out}")

    rows = []
    for work_id in included:
        work = works[work_id]
        version_id = work["preferred_version_id"]
        version = versions[version_id]
        if version["work_id"] != work_id or version["is_preferred_version"].lower() != "true":
            raise SystemExit(f"PREFERRED_VERSION_INVALID {work_id} {version_id}")
        rows.append({
            "work_id": work_id,
            "preferred_version_id": version_id,
            "title": version["title"],
            "first_public_date": version["first_public_date"] or "NOT_REPORTED",
            "publication_date": version["version_public_date"] or "NOT_REPORTED",
            "doi": version["doi"] or "NOT_APPLICABLE",
            "arxiv_id": version["arxiv_id"] or "NOT_APPLICABLE",
            "bibcode": version["bibcode"] or "NOT_APPLICABLE",
            "peer_review_status": version["peer_review_status"] or "NOT_REPORTED",
        })

    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=IDENTITY_FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    print("BAII4_EXTRACTION_SCAFFOLD_REBUILT")
    print(f"included_works={len(rows)}")
    print(f"output={out}")
    print(f"sha256={sha256(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
