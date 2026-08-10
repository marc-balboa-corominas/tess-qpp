#!/usr/bin/env python3
"""
BAII.3 — deterministic bibliographic work/version resolution.

Layer A only. This script does not make scientific screening decisions.

Inputs:
- frozen BAII.2 raw_hit_ledger.csv
- explicit manual_adjudications.csv

Outputs:
- auto_work_candidates.csv
- raw_hit_to_work_map.csv
- version_registry.csv
- work_registry.csv

Automatic merges are limited to:
AUTO_EXACT_DOI
AUTO_EXACT_ARXIV
AUTO_EXACT_PROVIDER_RECORD
AUTO_EXPLICIT_CROSSLINK

Fuzzy matching only generates candidates. Manual SAME/DISTINCT decisions live in
manual_adjudications.csv and are never hard-coded into this program.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

EXPECTED_LEDGER_SHA256 = "716c57663e90f4a7cc3f7d762620cbebe51a11d411ea10a97d9646a640b45dbd"
EXPECTED_RAW_HITS = 322

AUTO_CANDIDATE_FIELDS = [
    "candidate_id",
    "left_auto_component_min_raw_hit",
    "right_auto_component_min_raw_hit",
    "left_title",
    "right_title",
    "left_first_author",
    "right_first_author",
    "left_year",
    "right_year",
    "title_similarity",
    "candidate_basis",
]

MAP_FIELDS = [
    "raw_hit_id",
    "execution_id",
    "query_id",
    "source_database",
    "source_record_id",
    "work_id",
    "version_id",
    "mapping_basis",
    "mapping_confidence",
    "manual_adjudication_required",
    "manual_adjudication_status",
    "title",
    "doi_normalized",
    "arxiv_id_normalized",
    "bibcode",
    "is_preferred_version",
    "mapping_status",
    "error",
]

VERSION_FIELDS = [
    "version_id",
    "work_id",
    "version_type",
    "title",
    "authors",
    "first_public_date",
    "version_public_date",
    "latest_version_date",
    "doi",
    "arxiv_id",
    "bibcode",
    "journal",
    "peer_review_status",
    "source_databases",
    "raw_hit_ids",
    "is_preferred_version",
    "preferred_version_reason",
    "version_resolution_status",
    "verification_source",
    "notes",
]

WORK_FIELDS = [
    "work_id",
    "minimum_raw_hit_id",
    "title",
    "authors",
    "first_public_date",
    "latest_version_date",
    "doi",
    "arxiv_id",
    "bibcode",
    "source_databases",
    "query_ids_found",
    "raw_hit_ids",
    "version_ids",
    "preferred_version_id",
    "preferred_citation_version",
    "peer_review_status",
    "automatic_mapping_bases",
    "manual_adjudication_status",
    "resolution_status",
    "notes",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def parse_jsonish(value: str) -> Any:
    if value is None or value == "":
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


def parse_jsonish_list(value: str) -> list[str]:
    parsed = parse_jsonish(value)
    if parsed is None:
        return []
    if isinstance(parsed, list):
        return [str(x) for x in parsed if x is not None and str(x).strip()]
    return [str(parsed)]


def normalize_doi(value: str) -> str:
    if not value:
        return ""
    s = str(value).strip().lower()
    s = re.sub(r"^\s*(https?://(dx\.)?doi\.org/|doi:\s*)", "", s)
    return s.rstrip(" .;,")


def is_arxiv_doi(doi: str) -> bool:
    return normalize_doi(doi).startswith("10.48550/arxiv.")


def arxiv_from_doi(doi: str) -> str:
    d = normalize_doi(doi)
    if d.startswith("10.48550/arxiv."):
        return d.split("10.48550/arxiv.", 1)[1]
    return ""


def normalize_arxiv(value: str) -> str:
    if not value:
        return ""
    s = str(value).strip()
    s = re.sub(r"^(https?://arxiv\.org/(abs|pdf)/|arxiv:\s*)", "", s, flags=re.I)
    s = re.sub(r"\.pdf$", "", s, flags=re.I)
    s = re.sub(r"v\d+$", "", s)
    return s


def normalize_title(value: str) -> str:
    s = unicodedata.normalize("NFKD", value or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def first_author(authors_raw: str) -> str:
    parsed = parse_jsonish(authors_raw)
    if isinstance(parsed, list) and parsed:
        return str(parsed[0]).split(",")[0].strip().lower()
    if isinstance(parsed, str):
        return parsed.split(";")[0].split(",")[0].strip().lower()
    return ""


def authors_text(authors_raw: str) -> str:
    parsed = parse_jsonish(authors_raw)
    if isinstance(parsed, list):
        return "; ".join(str(x) for x in parsed)
    return str(parsed or "")


def arxiv_from_alternate_bibcode(value: str) -> str:
    m = re.search(r"arXiv(\d{4})(\d{5})", value or "")
    if m:
        return f"{m.group(1)}.{m.group(2)}"
    return ""


def arxiv_month(value: str) -> str:
    m = re.match(r"(\d{2})(\d{2})\.\d{4,5}", value or "")
    if not m:
        return ""
    yy, mm = int(m.group(1)), int(m.group(2))
    year = 2000 + yy if yy < 90 else 1900 + yy
    return f"{year:04d}-{mm:02d}"


def clean_date(value: str) -> str:
    if not value:
        return ""
    s = str(value)
    if "T" in s:
        return s.split("T", 1)[0]
    return s.replace("-00", "").strip()


class UnionFind:
    def __init__(self, items: list[tuple[str, str]]):
        self.parent = {x: x for x in items}

    def find(self, x: tuple[str, str]) -> tuple[str, str]:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: tuple[str, str], b: tuple[str, str]) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def load_ledger(path: Path) -> list[dict[str, str]]:
    if sha256_file(path) != EXPECTED_LEDGER_SHA256:
        raise RuntimeError("Frozen raw_hit_ledger.csv hash mismatch; BAII.3 must stop.")
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != EXPECTED_RAW_HITS:
        raise RuntimeError(f"Expected {EXPECTED_RAW_HITS} raw hits; observed {len(rows)}.")
    ids = [r["raw_hit_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError("raw_hit_id is not unique in frozen ledger.")
    return rows


def build_nodes(rows: list[dict[str, str]]) -> tuple[dict, dict]:
    nodes: dict[tuple[str, str], dict[str, Any]] = {}
    raw_to_node: dict[str, tuple[str, str]] = {}
    for r in rows:
        key = (r["source_database"], r["source_record_id"])
        metadata = parse_jsonish(r["provider_metadata_json"]) or {}
        if not isinstance(metadata, dict):
            metadata = {}
        if key not in nodes:
            doi_values = [normalize_doi(x) for x in parse_jsonish_list(r["doi_raw"])]
            provider_dois = metadata.get("doi", [])
            if not isinstance(provider_dois, list):
                provider_dois = [provider_dois] if provider_dois else []
            for d in provider_dois:
                nd = normalize_doi(str(d))
                if nd and nd not in doi_values:
                    doi_values.append(nd)

            arxiv_ids = set()
            for d in doi_values:
                a = normalize_arxiv(arxiv_from_doi(d))
                if a:
                    arxiv_ids.add(a)
            if r.get("arxiv_id_raw"):
                arxiv_ids.add(normalize_arxiv(r["arxiv_id_raw"]))
            if r["source_database"] == "ARXIV":
                arxiv_ids.add(normalize_arxiv(r["source_record_id"]))

            alternate = metadata.get("alternate_bibcode", [])
            if not isinstance(alternate, list):
                alternate = [alternate] if alternate else []
            for alt in alternate:
                a = arxiv_from_alternate_bibcode(str(alt))
                if a:
                    arxiv_ids.add(a)

            nodes[key] = {
                "key": key,
                "source_database": r["source_database"],
                "source_record_id": r["source_record_id"],
                "title": r["title"],
                "title_norm": normalize_title(r["title"]),
                "authors_raw": r["authors_raw"],
                "first_author": first_author(r["authors_raw"]),
                "source_date": r["source_date"],
                "publication_date_raw": r["publication_date_raw"],
                "updated_date_raw": r["updated_date_raw"],
                "doi_all": [x for x in doi_values if x],
                "journal_dois": [x for x in doi_values if x and not is_arxiv_doi(x)],
                "arxiv_ids": sorted(x for x in arxiv_ids if x),
                "bibcode": r["bibcode_raw"],
                "metadata": metadata,
                "rows": [],
                "raw_hit_ids": [],
            }
        nodes[key]["rows"].append(r)
        nodes[key]["raw_hit_ids"].append(r["raw_hit_id"])
        raw_to_node[r["raw_hit_id"]] = key
    return nodes, raw_to_node


def automatic_components(nodes: dict) -> tuple[UnionFind, dict, dict]:
    keys = list(nodes)
    uf = UnionFind(keys)
    edge_basis: dict[tuple[tuple[str, str], tuple[str, str]], set[str]] = defaultdict(set)

    doi_map: dict[str, list] = defaultdict(list)
    arxiv_map: dict[str, list] = defaultdict(list)

    for key, n in nodes.items():
        for doi in n["journal_dois"]:
            doi_map[doi].append(key)
        for arx in n["arxiv_ids"]:
            arxiv_map[arx].append(key)

    for members in doi_map.values():
        members = sorted(set(members))
        for a, b in zip(members, members[1:]):
            uf.union(a, b)
            edge_basis[(a, b)].add("AUTO_EXACT_DOI")

    for members in arxiv_map.values():
        members = sorted(set(members))
        for a, b in zip(members, members[1:]):
            uf.union(a, b)
            edge_basis[(a, b)].add("AUTO_EXACT_ARXIV")

    for key, n in nodes.items():
        if n["source_database"] != "ADS_SCIX":
            continue
        alternate = n["metadata"].get("alternate_bibcode", [])
        if not isinstance(alternate, list):
            alternate = [alternate] if alternate else []
        for alt in alternate:
            target = ("ADS_SCIX", str(alt))
            if target in nodes:
                uf.union(key, target)
                edge_basis[(key, target)].add("AUTO_EXPLICIT_CROSSLINK")

    components: dict[tuple[str, str], list] = defaultdict(list)
    for key in keys:
        components[uf.find(key)].append(key)
    return uf, components, edge_basis


def component_min_raw(component: list, nodes: dict) -> str:
    return min(hit for key in component for hit in nodes[key]["raw_hit_ids"])


def representative_node(component: list, nodes: dict) -> dict:
    minimum = component_min_raw(component, nodes)
    for key in component:
        if minimum in nodes[key]["raw_hit_ids"]:
            return nodes[key]
    raise AssertionError(minimum)


def generate_auto_candidates(components: dict, nodes: dict) -> list[dict[str, str]]:
    infos = []
    for component in sorted(components.values(), key=lambda c: component_min_raw(c, nodes)):
        rep = representative_node(component, nodes)
        metadata = rep["metadata"]
        year = str(
            metadata.get("year")
            or str(metadata.get("published", ""))[:4]
            or str(rep.get("source_date", ""))[:4]
        )
        infos.append(
            {
                "minimum": component_min_raw(component, nodes),
                "title": rep["title"],
                "title_norm": rep["title_norm"],
                "first_author": rep["first_author"],
                "year": year,
            }
        )

    out = []
    for i, left in enumerate(infos):
        for right in infos[i + 1 :]:
            sim = SequenceMatcher(None, left["title_norm"], right["title_norm"]).ratio()
            same_author_year = (
                left["first_author"]
                and left["first_author"] == right["first_author"]
                and left["year"]
                and left["year"] == right["year"]
            )
            basis = ""
            if sim >= 0.80:
                basis = "FUZZY_TITLE_HIGH_SIMILARITY"
            elif same_author_year and sim >= 0.60:
                basis = "FUZZY_TITLE_SAME_FIRST_AUTHOR_YEAR"
            if basis:
                out.append(
                    {
                        "left_auto_component_min_raw_hit": left["minimum"],
                        "right_auto_component_min_raw_hit": right["minimum"],
                        "left_title": left["title"],
                        "right_title": right["title"],
                        "left_first_author": left["first_author"],
                        "right_first_author": right["first_author"],
                        "left_year": left["year"],
                        "right_year": right["year"],
                        "title_similarity": f"{sim:.6f}",
                        "candidate_basis": basis,
                    }
                )
    out.sort(key=lambda r: (r["left_auto_component_min_raw_hit"], r["right_auto_component_min_raw_hit"]))
    for i, row in enumerate(out, 1):
        row["candidate_id"] = f"BAII3C{i:03d}"
    return out


def load_manual_adjudications(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    allowed = {
        "MANUAL_CONFIRMED_SAME_WORK",
        "MANUAL_CONFIRMED_DISTINCT_WORKS",
        "AMBIGUOUS_UNRESOLVED",
    }
    for r in rows:
        if r["adjudication_status"] not in allowed:
            raise RuntimeError(f"Invalid manual adjudication: {r}")
    return rows


def version_type_for_node(n: dict) -> str:
    if n["source_database"] == "ARXIV":
        return "ARXIV_PREPRINT"

    metadata = n["metadata"]
    pub = str(metadata.get("pub", "") or "").lower()
    doctype = str(metadata.get("doctype", "") or "").lower()
    props = metadata.get("property", [])
    if not isinstance(props, list):
        props = [props] if props else []
    props_u = {str(x).upper() for x in props}
    bib = n["bibcode"].lower()

    if "arxiv" in pub or "arxiv" in bib:
        return "ARXIV_PREPRINT"
    if "vizier" in pub or "ycat" in bib or doctype == "dataset":
        return "OTHER"

    conference_markers = (
        "meeting abstracts",
        "general assembly",
        "bulletin of the american astronomical society",
        "conference",
        "symposium",
        "annual meeting",
    )
    if doctype in {"inproceedings", "abstract"} or any(x in pub for x in conference_markers):
        return "CONFERENCE_ABSTRACT"

    if doctype in {"proposal", "software"} or "nsf award" in pub:
        return "OTHER"

    if "REFEREED" in props_u or "ARTICLE" in props_u or n["journal_dois"]:
        return "JOURNAL_ARTICLE"

    return "OTHER"


def node_public_date(n: dict) -> str:
    if n["source_database"] == "ARXIV":
        return clean_date(str(n["metadata"].get("published", "")))
    return clean_date(str(n["metadata"].get("date") or n["publication_date_raw"] or n["source_date"] or ""))


def node_latest_date(n: dict) -> str:
    if n["source_database"] == "ARXIV":
        return clean_date(str(n["metadata"].get("updated", "")))
    return clean_date(str(n["metadata"].get("metadata_mtime") or n["updated_date_raw"] or n["source_date"] or ""))


def build_versions_for_work(work_id: str, component: list, nodes: dict) -> list[dict[str, Any]]:
    versions: dict[tuple[str, str], dict[str, Any]] = {}

    for key in component:
        n = nodes[key]
        vtype = version_type_for_node(n)
        if vtype == "ARXIV_PREPRINT":
            ident = n["arxiv_ids"][0] if n["arxiv_ids"] else normalize_arxiv(n["source_record_id"])
        elif vtype == "JOURNAL_ARTICLE":
            ident = n["journal_dois"][0] if n["journal_dois"] else (n["bibcode"] or n["source_record_id"])
        else:
            ident = n["bibcode"] or n["source_record_id"]
        vkey = (vtype, ident)
        versions.setdefault(vkey, {"version_type": vtype, "nodes": [], "synthetic": False})
        versions[vkey]["nodes"].append(key)

    known_arxiv = {ident for vtype, ident in versions if vtype == "ARXIV_PREPRINT"}
    for key in component:
        n = nodes[key]
        for arx in n["arxiv_ids"]:
            if arx and arx not in known_arxiv:
                versions[("ARXIV_PREPRINT", arx)] = {
                    "version_type": "ARXIV_PREPRINT",
                    "nodes": [],
                    "synthetic": True,
                    "source_node": key,
                    "arxiv_id": arx,
                }
                known_arxiv.add(arx)

    known_journal_doi = {
        ident for vtype, ident in versions if vtype == "JOURNAL_ARTICLE" and ident.startswith("10.")
    }
    for key in component:
        n = nodes[key]
        if n["source_database"] != "ARXIV":
            continue
        journal_ref = str(n["metadata"].get("journal_ref", "") or "")
        if not journal_ref:
            continue
        for doi in n["journal_dois"]:
            if doi and doi not in known_journal_doi:
                versions[("JOURNAL_ARTICLE", doi)] = {
                    "version_type": "JOURNAL_ARTICLE",
                    "nodes": [],
                    "synthetic": True,
                    "source_node": key,
                    "journal_doi": doi,
                    "journal_ref": journal_ref,
                }
                known_journal_doi.add(doi)

    resolved = []
    for (vtype, ident), item in versions.items():
        if not item["synthetic"]:
            ns = [nodes[k] for k in item["nodes"]]
            ns.sort(key=lambda n: min(n["raw_hit_ids"]))
            rep = ns[0]
            public_dates = sorted(x for x in (node_public_date(n) for n in ns) if x)
            latest_dates = sorted(x for x in (node_latest_date(n) for n in ns) if x)
            doi = ""
            arxiv_id = ""
            bibcode = rep["bibcode"]
            journal = ""
            if vtype == "ARXIV_PREPRINT":
                arxiv_id = rep["arxiv_ids"][0] if rep["arxiv_ids"] else normalize_arxiv(rep["source_record_id"])
            elif vtype == "JOURNAL_ARTICLE":
                doi = rep["journal_dois"][0] if rep["journal_dois"] else ""
                journal = str(rep["metadata"].get("pub", "") or rep["metadata"].get("journal_ref", "") or "")
            else:
                journal = str(rep["metadata"].get("pub", "") or "")
            props = []
            for n in ns:
                p = n["metadata"].get("property", [])
                if not isinstance(p, list):
                    p = [p] if p else []
                props.extend(str(x).upper() for x in p)
            if vtype == "JOURNAL_ARTICLE":
                peer = "PEER_REVIEWED" if "REFEREED" in props else "PUBLISHED_JOURNAL"
            elif vtype == "ARXIV_PREPRINT":
                peer = "PREPRINT"
            elif vtype == "CONFERENCE_ABSTRACT":
                peer = "NOT_PEER_REVIEWED"
            else:
                peer = "NOT_APPLICABLE"

            resolved.append(
                {
                    "work_id": work_id,
                    "version_type": vtype,
                    "title": rep["title"],
                    "authors": authors_text(rep["authors_raw"]),
                    "version_public_date": public_dates[0] if public_dates else "",
                    "latest_version_date": latest_dates[-1] if latest_dates else (public_dates[0] if public_dates else ""),
                    "doi": doi,
                    "arxiv_id": arxiv_id,
                    "bibcode": bibcode,
                    "journal": journal,
                    "peer_review_status": peer,
                    "source_databases": ";".join(sorted({n["source_database"] for n in ns})),
                    "raw_hit_ids": ";".join(sorted(h for n in ns for h in n["raw_hit_ids"])),
                    "synthetic": False,
                    "verification_source": "RAW_PROVIDER_METADATA",
                    "notes": "",
                    "_key": (vtype, ident),
                }
            )
        else:
            source = nodes[item["source_node"]]
            if vtype == "ARXIV_PREPRINT":
                arx = item["arxiv_id"]
                resolved.append(
                    {
                        "work_id": work_id,
                        "version_type": vtype,
                        "title": source["title"],
                        "authors": authors_text(source["authors_raw"]),
                        "version_public_date": arxiv_month(arx),
                        "latest_version_date": arxiv_month(arx),
                        "doi": "",
                        "arxiv_id": arx,
                        "bibcode": "",
                        "journal": "",
                        "peer_review_status": "PREPRINT",
                        "source_databases": source["source_database"],
                        "raw_hit_ids": "",
                        "synthetic": True,
                        "verification_source": "ADS_EXPLICIT_ARXIV_CROSSLINK",
                        "notes": "SYNTHETIC_METADATA_ONLY_VERSION; public month inferred from arXiv identifier; no additional systematic hit added",
                        "_key": (vtype, ident),
                    }
                )
            else:
                resolved.append(
                    {
                        "work_id": work_id,
                        "version_type": vtype,
                        "title": source["title"],
                        "authors": authors_text(source["authors_raw"]),
                        "version_public_date": "",
                        "latest_version_date": "",
                        "doi": item["journal_doi"],
                        "arxiv_id": "",
                        "bibcode": "",
                        "journal": item.get("journal_ref", ""),
                        "peer_review_status": "PUBLISHED_JOURNAL",
                        "source_databases": source["source_database"],
                        "raw_hit_ids": "",
                        "synthetic": True,
                        "verification_source": "ARXIV_EXPLICIT_JOURNAL_LINK",
                        "notes": "SYNTHETIC_METADATA_ONLY_VERSION; explicit arXiv journal/DOI link; no additional systematic hit added",
                        "_key": (vtype, ident),
                    }
                )

    dates = [v["version_public_date"] for v in resolved if v["version_public_date"]]
    first_public = min(dates) if dates else ""
    for v in resolved:
        v["first_public_date"] = first_public

    preference_rank = {
        "JOURNAL_ARTICLE": 0,
        "ARXIV_PREPRINT": 1,
        "CONFERENCE_ABSTRACT": 2,
        "OTHER": 3,
    }
    best_rank = min(preference_rank[v["version_type"]] for v in resolved)
    preferred_pool = [v for v in resolved if preference_rank[v["version_type"]] == best_rank]
    raw_pool = [v for v in preferred_pool if not v["synthetic"]] or preferred_pool
    preferred = max(raw_pool, key=lambda v: (v["version_public_date"] or "", v["latest_version_date"] or "", v["title"]))

    for v in resolved:
        v["is_preferred_version"] = "true" if v is preferred else "false"
        if v is preferred:
            if v["version_type"] == "JOURNAL_ARTICLE":
                reason = "journal version available and substantively current"
            elif v["version_type"] == "ARXIV_PREPRINT":
                reason = "no journal version available; latest available arXiv/preprint version"
            else:
                reason = "only recoverable material version for this work"
            v["preferred_version_reason"] = reason
        else:
            v["preferred_version_reason"] = ""
        v["version_resolution_status"] = "RESOLVED"
    return resolved


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, default=Path.cwd())
    p.add_argument(
        "--ledger",
        type=Path,
        default=Path("docs/literature/bibliographic_audit_ii/retrieval/raw_hit_ledger.csv"),
    )
    p.add_argument(
        "--manual-adjudications",
        type=Path,
        default=Path("docs/literature/bibliographic_audit_ii/screening/manual_adjudications.csv"),
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/literature/bibliographic_audit_ii/screening"),
    )
    p.add_argument("--auto-candidates-only", action="store_true")
    args = p.parse_args()

    repo = args.repo_root.resolve()
    ledger_path = args.ledger if args.ledger.is_absolute() else repo / args.ledger
    output = args.output_dir if args.output_dir.is_absolute() else repo / args.output_dir
    manual_path = args.manual_adjudications if args.manual_adjudications.is_absolute() else repo / args.manual_adjudications

    rows = load_ledger(ledger_path)
    nodes, raw_to_node = build_nodes(rows)
    auto_uf, auto_components, edge_basis = automatic_components(nodes)

    auto_candidates = generate_auto_candidates(auto_components, nodes)
    write_csv(output / "auto_work_candidates.csv", AUTO_CANDIDATE_FIELDS, auto_candidates)
    if args.auto_candidates_only:
        print(f"auto_component_count={len(auto_components)}")
        print(f"auto_candidate_pairs={len(auto_candidates)}")
        print(f"auto_candidate_sha256={sha256_file(output / 'auto_work_candidates.csv')}")
        return 0

    manual = load_manual_adjudications(manual_path)

    # Manual layer acts on the auto components. SAME merges are explicit; DISTINCT never merge.
    final_uf = UnionFind(list(nodes))
    for component in auto_components.values():
        for a, b in zip(component, component[1:]):
            final_uf.union(a, b)

    manual_status_by_node: dict[tuple[str, str], set[str]] = defaultdict(set)
    manual_merge_node_pairs = []
    unresolved_count = 0

    for adjudication in manual:
        left_raw = adjudication["left_raw_hit_id"]
        right_raw = adjudication["right_raw_hit_id"]
        if left_raw not in raw_to_node or right_raw not in raw_to_node:
            raise RuntimeError(f"Manual adjudication references unknown raw hit: {adjudication}")
        left = raw_to_node[left_raw]
        right = raw_to_node[right_raw]
        status = adjudication["adjudication_status"]
        manual_status_by_node[left].add(status)
        manual_status_by_node[right].add(status)
        if status == "MANUAL_CONFIRMED_SAME_WORK":
            final_uf.union(left, right)
            manual_merge_node_pairs.append((left, right))
        elif status == "AMBIGUOUS_UNRESOLVED":
            unresolved_count += 1

    final_components: dict[tuple[str, str], list] = defaultdict(list)
    for key in nodes:
        final_components[final_uf.find(key)].append(key)

    sorted_components = sorted(final_components.values(), key=lambda c: component_min_raw(c, nodes))
    work_id_for_node = {}
    components_by_work = {}
    for index, component in enumerate(sorted_components, 1):
        work_id = f"BAIIW{index:04d}"
        components_by_work[work_id] = component
        for key in component:
            work_id_for_node[key] = work_id

    all_versions: list[dict[str, Any]] = []
    versions_by_work: dict[str, list[dict[str, Any]]] = {}
    for work_id in sorted(components_by_work):
        vs = build_versions_for_work(work_id, components_by_work[work_id], nodes)
        versions_by_work[work_id] = vs
        all_versions.extend(vs)

    # Assign deterministic BAIIV IDs by work then public-date/type/identity order.
    type_order = {"JOURNAL_ARTICLE": 0, "ARXIV_PREPRINT": 1, "CONFERENCE_ABSTRACT": 2, "OTHER": 3}
    all_versions.sort(
        key=lambda v: (
            int(v["work_id"].replace("BAIIW", "")),
            v["version_public_date"] or "9999",
            type_order[v["version_type"]],
            v["doi"] or v["arxiv_id"] or v["bibcode"] or v["title"],
        )
    )
    version_id_by_key = {}
    for i, v in enumerate(all_versions, 1):
        v["version_id"] = f"BAIIV{i:04d}"
        version_id_by_key[(v["work_id"], v["_key"])] = v["version_id"]

    # Build node -> version mapping using the same key logic.
    node_version: dict[tuple[str, str], str] = {}
    for work_id, component in components_by_work.items():
        for key in component:
            n = nodes[key]
            vtype = version_type_for_node(n)
            if vtype == "ARXIV_PREPRINT":
                ident = n["arxiv_ids"][0] if n["arxiv_ids"] else normalize_arxiv(n["source_record_id"])
            elif vtype == "JOURNAL_ARTICLE":
                ident = n["journal_dois"][0] if n["journal_dois"] else (n["bibcode"] or n["source_record_id"])
            else:
                ident = n["bibcode"] or n["source_record_id"]
            node_version[key] = version_id_by_key[(work_id, (vtype, ident))]

    preferred_version_by_work = {
        v["work_id"]: v["version_id"] for v in all_versions if v["is_preferred_version"] == "true"
    }

    # Automatic mapping basis for each node.
    node_auto_basis: dict[tuple[str, str], set[str]] = defaultdict(set)
    for key, n in nodes.items():
        node_auto_basis[key].add("AUTO_EXACT_PROVIDER_RECORD")
    for (a, b), bases in edge_basis.items():
        for base in bases:
            node_auto_basis[a].add(base)
            node_auto_basis[b].add(base)

    manual_same_work_ids = set()
    for left, right in manual_merge_node_pairs:
        manual_same_work_ids.add(work_id_for_node[left])
        manual_same_work_ids.add(work_id_for_node[right])

    map_rows = []
    for r in rows:
        key = raw_to_node[r["raw_hit_id"]]
        work_id = work_id_for_node[key]
        version_id = node_version[key]
        manual_status = sorted(manual_status_by_node.get(key, set()))
        if work_id in manual_same_work_ids:
            bases = sorted(node_auto_basis[key] | {"MANUAL_CONFIRMED_SAME_WORK"})
        else:
            bases = sorted(node_auto_basis[key])
        doi_values = [normalize_doi(x) for x in parse_jsonish_list(r["doi_raw"])]
        journal_doi = next((x for x in doi_values if x and not is_arxiv_doi(x)), "")
        arxiv_id = normalize_arxiv(r.get("arxiv_id_raw", ""))
        if not arxiv_id:
            arxiv_id = next(
                (normalize_arxiv(arxiv_from_doi(x)) for x in doi_values if is_arxiv_doi(x)),
                "",
            )
        if not arxiv_id and r["source_database"] == "ARXIV":
            arxiv_id = normalize_arxiv(r["source_record_id"])

        map_rows.append(
            {
                "raw_hit_id": r["raw_hit_id"],
                "execution_id": r["execution_id"],
                "query_id": r["query_id"],
                "source_database": r["source_database"],
                "source_record_id": r["source_record_id"],
                "work_id": work_id,
                "version_id": version_id,
                "mapping_basis": ";".join(bases),
                "mapping_confidence": "HIGH_AFTER_MANUAL_ADJUDICATION" if work_id in manual_same_work_ids else "HIGH",
                "manual_adjudication_required": "true" if manual_status or work_id in manual_same_work_ids else "false",
                "manual_adjudication_status": ";".join(manual_status) if manual_status else (
                    "MANUAL_CONFIRMED_SAME_WORK" if work_id in manual_same_work_ids else ""
                ),
                "title": r["title"],
                "doi_normalized": journal_doi,
                "arxiv_id_normalized": arxiv_id,
                "bibcode": r["bibcode_raw"],
                "is_preferred_version": "true" if version_id == preferred_version_by_work[work_id] else "false",
                "mapping_status": "RESOLVED",
                "error": "",
            }
        )

    # Version rows for output.
    version_rows = []
    for v in all_versions:
        version_rows.append(
            {
                "version_id": v["version_id"],
                "work_id": v["work_id"],
                "version_type": v["version_type"],
                "title": v["title"],
                "authors": v["authors"],
                "first_public_date": v["first_public_date"],
                "version_public_date": v["version_public_date"],
                "latest_version_date": v["latest_version_date"],
                "doi": v["doi"],
                "arxiv_id": v["arxiv_id"],
                "bibcode": v["bibcode"],
                "journal": v["journal"],
                "peer_review_status": v["peer_review_status"],
                "source_databases": v["source_databases"],
                "raw_hit_ids": v["raw_hit_ids"],
                "is_preferred_version": v["is_preferred_version"],
                "preferred_version_reason": v["preferred_version_reason"],
                "version_resolution_status": v["version_resolution_status"],
                "verification_source": v["verification_source"],
                "notes": v["notes"],
            }
        )

    # Work rows.
    work_rows = []
    raw_rows_by_work: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in map_rows:
        raw_rows_by_work[r["work_id"]].append(r)
    versions_by_id = {v["version_id"]: v for v in version_rows}

    for work_id in sorted(components_by_work, key=lambda x: int(x.replace("BAIIW", ""))):
        hits = sorted(raw_rows_by_work[work_id], key=lambda x: x["raw_hit_id"])
        vids = [v["version_id"] for v in version_rows if v["work_id"] == work_id]
        preferred_id = preferred_version_by_work[work_id]
        preferred = versions_by_id[preferred_id]
        work_versions = [versions_by_id[v] for v in vids]
        latest = max((v["latest_version_date"] for v in work_versions if v["latest_version_date"]), default="")
        manual_status = sorted(
            {
                s
                for key in components_by_work[work_id]
                for s in manual_status_by_node.get(key, set())
            }
        )
        automatic = sorted(
            {
                b
                for key in components_by_work[work_id]
                for b in node_auto_basis.get(key, set())
            }
        )
        work_rows.append(
            {
                "work_id": work_id,
                "minimum_raw_hit_id": hits[0]["raw_hit_id"],
                "title": preferred["title"],
                "authors": preferred["authors"],
                "first_public_date": preferred["first_public_date"],
                "latest_version_date": latest,
                "doi": preferred["doi"],
                "arxiv_id": preferred["arxiv_id"],
                "bibcode": preferred["bibcode"],
                "source_databases": ";".join(sorted({h["source_database"] for h in hits})),
                "query_ids_found": ";".join(sorted({h["query_id"] for h in hits})),
                "raw_hit_ids": ";".join(h["raw_hit_id"] for h in hits),
                "version_ids": ";".join(vids),
                "preferred_version_id": preferred_id,
                "preferred_citation_version": preferred_id,
                "peer_review_status": preferred["peer_review_status"],
                "automatic_mapping_bases": ";".join(automatic),
                "manual_adjudication_status": ";".join(manual_status),
                "resolution_status": "RESOLVED" if not any("AMBIGUOUS" in s for s in manual_status) else "AMBIGUOUS_UNRESOLVED",
                "notes": "",
            }
        )

    write_csv(output / "raw_hit_to_work_map.csv", MAP_FIELDS, map_rows)
    write_csv(output / "version_registry.csv", VERSION_FIELDS, version_rows)
    write_csv(output / "work_registry.csv", WORK_FIELDS, work_rows)

    print(f"raw_hits={len(rows)}")
    print(f"auto_components={len(auto_components)}")
    print(f"manual_same_work_adjudications={sum(r['adjudication_status']=='MANUAL_CONFIRMED_SAME_WORK' for r in manual)}")
    print(f"manual_distinct_work_adjudications={sum(r['adjudication_status']=='MANUAL_CONFIRMED_DISTINCT_WORKS' for r in manual)}")
    print(f"manual_unresolved_adjudications={unresolved_count}")
    print(f"final_work_count={len(work_rows)}")
    print(f"version_count={len(version_rows)}")
    print(f"preferred_version_count={sum(r['is_preferred_version']=='true' for r in version_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
