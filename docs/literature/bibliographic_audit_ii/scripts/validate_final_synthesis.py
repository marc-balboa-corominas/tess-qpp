from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

GATE_VOCAB = {
    "NO_CHANGE_TO_F3A",
    "POSITIONING_UPDATE_ONLY",
    "F3A_DESIGN_ADJUSTMENT_REQUIRED",
    "F3A_DESIGN_RECONSIDERATION_REQUIRED",
}
EXPECTED_HISTORICAL_HASHES = {'docs/literature/bibliographic_audit_ii/AUDIT_MATRIX.csv': 'ef1723c53d09f6fe95aa2f1f127d329b1a29ea389a9e75e4c77ec735ec4e10c5',
 'docs/literature/bibliographic_audit_ii/SEED_SOURCES.csv': '05690c0f57a684c77b681510e4b18dcde163848a6eabcad3a735b9a3bccd8838',
 'docs/literature/bibliographic_audit_ii/amendments/BAII_DESIGN_V1_1_0.md': 'ec076cc629ebc46c35253a1a0670023523700a0dc3c6b7f68baeb06f876ef514',
 'docs/literature/bibliographic_audit_ii/audit_preregistration.json': '64f182980f8494b2242a7743151441718ca8a50d177ceb6442b8e5540742ae84',
 'docs/literature/bibliographic_audit_ii/extraction/README.md': 'd518759133282379cfd0fad7d707874aeab8c30098071106754c0af57167713e',
 'docs/literature/bibliographic_audit_ii/extraction/SHA256SUMS.txt': '818c6e042fbacc1c8a64307d7ff190f4533fa3df34fdc2276cdd3c2ee9ee5c44',
 'docs/literature/bibliographic_audit_ii/extraction/SHA256SUMS_REFERENCE_FREEZE.txt': '5e938dd96b63a92607094cf9fa00b64113cf322db2f0ccad7be7f923f9e6632b',
 'docs/literature/bibliographic_audit_ii/extraction/extraction_evidence_log.csv': '2c90080fb8779fc38de4c7fdd8c8126de00f97e48f4655d6988e089fd7fbb55c',
 'docs/literature/bibliographic_audit_ii/extraction/extraction_manifest.json': '4de9ffac6ccd78e15690ab674c15af91529788fc7b05f63966f6fb79880b1581',
 'docs/literature/bibliographic_audit_ii/extraction/extraction_report.md': 'c8e0feb5c3ab2bb875f74aa23062e9b50b16b36bf2e75fcd03dcca3c2fe94b59',
 'docs/literature/bibliographic_audit_ii/extraction/f3_overlap_reference.json': '1b6be4a17d23457d3164b23c4b16557467e84ae44bbb35df57064b7c9566639e',
 'docs/literature/bibliographic_audit_ii/extraction/included_work_extraction.csv': 'a5c8b5ba13da94e01fdc18ed95bea2abf036e481c695415ae276e89eb4fa047c',
 'docs/literature/bibliographic_audit_ii/extraction/overlap_assessment.csv': '6585149e956f22060186a67750ccfa8402ee558a00b10c3341c3979480fbb768',
 'docs/literature/bibliographic_audit_ii/extraction/overlap_dimension_evidence.csv': '114ac1d5e330ad0beacd002ae913d3ad11a132ecf0b2142b6f14b3d48a315552',
 'docs/literature/bibliographic_audit_ii/extraction/source_access_log.csv': 'c3f67df0dbb2a2dd3c03f1de6ecac5873c3927f7c9d39a408a66c594d4107035',
 'docs/literature/bibliographic_audit_ii/protocol.md': '75b7d372c778364882047d859ad90598c8fd553cbb1e70ddfae39c3d35e21927',
 'docs/literature/bibliographic_audit_ii/retrieval/README.md': 'fe16746c3513066a3992cd51d2e9c241853c6005b5d766ca4ff5249be2c31d54',
 'docs/literature/bibliographic_audit_ii/retrieval/SHA256SUMS.txt': '4c54368647ef93b3b7b5694eb49651320665d048b3d43f7f354c490229ff0ef3',
 'docs/literature/bibliographic_audit_ii/retrieval/raw_hit_ledger.csv': '716c57663e90f4a7cc3f7d762620cbebe51a11d411ea10a97d9646a640b45dbd',
 'docs/literature/bibliographic_audit_ii/retrieval/retrieval_manifest.json': '819de2c50a2b8921e9e69c16e40e896ae387d39e73fefca084500ef25435c97e',
 'docs/literature/bibliographic_audit_ii/retrieval/search_execution_log.csv': '8778bc78a4bebde2751560807d6b990ebf971ff6acd3af76e32d6eb9453a4370',
 'docs/literature/bibliographic_audit_ii/screening/README.md': '194e9ff3c31b112ee194e027ff201bbebe70f7407c708d768938fc4335709048',
 'docs/literature/bibliographic_audit_ii/screening/SHA256SUMS.txt': '9fd5698e17b947953b60cdb96d46af3130086e8e79599b7f1057d629f73a464d',
 'docs/literature/bibliographic_audit_ii/screening/auto_work_candidates.csv': 'ffbb71847522361076c82dc24e16da94292f9016f20d47af249f0ee860e5f7c0',
 'docs/literature/bibliographic_audit_ii/screening/manual_adjudications.csv': '98ea1f5dd7f8815dd3599bf2b8db6661e731bc373971e0cf6555bc7f2d29a03b',
 'docs/literature/bibliographic_audit_ii/screening/raw_hit_to_work_map.csv': '2d9ac5f37507cbd3b9e79481fa74edf582fc5f44bcf942e7d890586dcceca55e',
 'docs/literature/bibliographic_audit_ii/screening/screened_works.csv': '143aa10bb942780e250f6b5cb9489acfa8bbc2a05b633624a4856d4d245533e2',
 'docs/literature/bibliographic_audit_ii/screening/screening_decision_log.csv': 'b80b2a01e488b4ebe7f4c833a58f192de5d55e216bdeb66b9e2ed896d2bc16cb',
 'docs/literature/bibliographic_audit_ii/screening/screening_manifest.json': 'b8d53cc6f51cfbf33ba3fd5d32a5651c0db772842d9fdab678d70f0f15ef7dba',
 'docs/literature/bibliographic_audit_ii/screening/screening_report.md': 'f63e3b1160bcf5f8d1da3fe03b33bbbf6f12ad0081e52ebbbb7d2eacfeca7bb9',
 'docs/literature/bibliographic_audit_ii/screening/verification_lookup_log.csv': '63fc3317c2cd0a962e145c6034c08b7e1871b0e69e9fe0a91534993961b6f850',
 'docs/literature/bibliographic_audit_ii/screening/version_registry.csv': '33d2ef5e00bd3d343a01184b08b93aa8128ed739bb98ce86472dac93c12c6cdc',
 'docs/literature/bibliographic_audit_ii/screening/work_registry.csv': 'eacaa8ad6f0ba78a91adf9bf8327d1727c6e045a0f7771ba32837c0eaf089661',
 'docs/literature/bibliographic_audit_ii/screening_schema.csv': '0c9031aae2d9f5c674c5e4c3e0f4201af81cc0fabdc3e325fb863cebe8f69d0f',
 'docs/literature/bibliographic_audit_ii/scripts/build_extraction_scaffold.py': '2214860582b7a717955cbf887cb1ba77a825a968b0fcb893ccfd240f6483f92f',
 'docs/literature/bibliographic_audit_ii/scripts/build_work_resolution.py': 'e14670757b94de8732a8b6648b9f1a7c412e1b116e1ba792e2142b919736d0b4',
 'docs/literature/bibliographic_audit_ii/scripts/retrieve_raw_corpus.py': '7f5535cd7edbb57082158c6e80eac86b9f73ce16b2163989d4f67e6ddebf204a',
 'docs/literature/bibliographic_audit_ii/scripts/validate_extraction.py': 'f7d90def3e74950fba3d1fbe10bb7d8bb8d37988437142295478fb321c1de7ff',
 'docs/literature/bibliographic_audit_ii/scripts/validate_screening.py': '5913768f99ace63161d954b7830874455c5fd81df1e04978863706eee5a7b0e2',
 'docs/literature/bibliographic_audit_ii/search_plan.yaml': 'a76420e4603baeda95d70c8d3308bc614458d09d9769979d327ef79bf9a52f28'}
EXPECTED_INPUT_HASHES = {
    "docs/literature/bibliographic_audit_ii/screening/screening_manifest.json": "b8d53cc6f51cfbf33ba3fd5d32a5651c0db772842d9fdab678d70f0f15ef7dba",
    "docs/literature/bibliographic_audit_ii/extraction/extraction_manifest.json": "4de9ffac6ccd78e15690ab674c15af91529788fc7b05f63966f6fb79880b1581",
    "docs/literature/bibliographic_audit_ii/extraction/f3_overlap_reference.json": "1b6be4a17d23457d3164b23c4b16557467e84ae44bbb35df57064b7c9566639e",
}

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def split_ids(value: str) -> list[str]:
    return [x for x in value.split(";") if x and x not in {"NONE", "NOT_APPLICABLE", "NOT_REPORTED"}]

def assert_no_duplicates(rows: list[dict[str, str]], key: str, label: str) -> None:
    values = [r[key] for r in rows]
    if len(values) != len(set(values)):
        raise RuntimeError(f"Duplicate {label} values")

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    baii = repo / "docs/literature/bibliographic_audit_ii"
    closure = baii / "closure"

    for rel, expected in EXPECTED_INPUT_HASHES.items():
        observed = sha256_file(repo / rel)
        if observed != expected:
            raise RuntimeError(f"Frozen input changed: {rel}")
    for rel, expected in EXPECTED_HISTORICAL_HASHES.items():
        observed = sha256_file(repo / rel)
        if observed != expected:
            raise RuntimeError(f"Historical BAII artifact changed: {rel}")

    screened = read_csv(baii / "screening/screened_works.csv")
    extraction = read_csv(baii / "extraction/included_work_extraction.csv")
    extraction_evidence = read_csv(baii / "extraction/extraction_evidence_log.csv")
    overlap = read_csv(baii / "extraction/overlap_assessment.csv")

    critical = read_csv(closure / "critical_overlap_review.csv")
    positioning = read_csv(closure / "precedence_positioning_matrix.csv")
    comparators = read_csv(closure / "comparator_consideration_matrix.csv")
    f3b = read_csv(closure / "f3b_design_considerations.csv")
    supplemental = read_csv(closure / "supplemental_context_registry.csv")
    requirements = read_csv(closure / "f3a_gate_requirements.csv")
    limitations = read_csv(closure / "limitations_register.csv")
    final_evidence = read_csv(closure / "final_evidence_ledger.csv")
    gate = json.loads((closure / "final_gate_decision.json").read_text(encoding="utf-8"))
    audit = json.loads((closure / "final_synthesis_audit.json").read_text(encoding="utf-8"))

    included_ids = {r["work_id"] for r in screened if r["screening_decision"] == "INCLUDE_FOR_BAII4"}
    extraction_ids = {r["work_id"] for r in extraction}
    overlap_ids = {r["work_id"] for r in overlap}
    all_work_ids = {r["work_id"] for r in screened}
    all_evidence_ids = {r["evidence_id"] for r in extraction_evidence}

    if len(all_work_ids) != 190:
        raise RuntimeError("Systematic work count != 190")
    if len(included_ids) != 40 or extraction_ids != included_ids or overlap_ids != included_ids:
        raise RuntimeError("Primary 40-work denominator mismatch")
    if len(extraction_evidence) != 160:
        raise RuntimeError("Evidence row count != 160")

    impact_ids = {
        r["work_id"] for r in overlap
        if r["f3a_design_impact"] in {"F3A_REDRAFT_REQUIRED", "F3A_DESIGN_ADJUSTMENT_POSSIBLE"}
    }
    redraft_ids = {r["work_id"] for r in overlap if r["f3a_design_impact"] == "F3A_REDRAFT_REQUIRED"}
    f3b_impact_ids = {r["work_id"] for r in overlap if r["f3b_design_impact"] == "F3B_DESIGN_ADJUSTMENT_POSSIBLE"}
    comparator_ids = {r["work_id"] for r in overlap if r["comparator_candidate"].lower() == "true"}

    if len(critical) != 15 or {r["work_id"] for r in critical} != impact_ids:
        raise RuntimeError("15/15 critical F3A works not represented exactly")
    if len(redraft_ids) != 2 or redraft_ids != {"BAIIW0001", "BAIIW0003"}:
        raise RuntimeError("Unexpected redraft-required set")
    if not redraft_ids.issubset({r["work_id"] for r in critical}):
        raise RuntimeError("2/2 redraft-required works not reviewed")
    if len(comparators) != 11 or {r["work_id"] for r in comparators} != comparator_ids:
        raise RuntimeError("11/11 comparator candidates not represented")
    if len(f3b) != 9 or {r["source_work_ids"] for r in f3b} != f3b_impact_ids:
        raise RuntimeError("9/9 F3B impact works not represented")
    if len(supplemental) < 1:
        raise RuntimeError("Supplemental registry missing")
    for row in supplemental:
        if row["systematic_corpus_member"].lower() != "false" or row["systematic_denominator_effect"] != "NONE":
            raise RuntimeError("Supplemental citation altered systematic denominator")
    for row in comparators:
        if row["adoption_decision"] != "NOT_DECIDED_IN_BAII":
            raise RuntimeError("Comparator adoption decision was made inside BAII")

    if gate["f3a_gate_decision"] not in GATE_VOCAB:
        raise RuntimeError("Unknown final gate state")
    if gate["baii_status"] != "BIBLIOGRAPHIC_AUDIT_II_COMPLETE":
        raise RuntimeError("BAII not marked complete")
    if gate["novelty_assessed"] is not False or gate["priority_claim_authorized"] is not False:
        raise RuntimeError("Novelty/priority boundary violated")
    if gate["f3a_modified"] is not False or gate["f3b_modified"] is not False:
        raise RuntimeError("F3A/F3B modification boundary violated")

    confirmed_direct_redraft = [
        r for r in critical
        if r["baii4_f3a_overlap"] == "DIRECT"
        and r["baii4_f3a_impact"] == "F3A_REDRAFT_REQUIRED"
        and r["evidence_sufficient_for_gate"] == "YES"
        and r["baii4_assessment_status"] == "BAII4_ASSESSMENT_CONFIRMED"
    ]
    if confirmed_direct_redraft and gate["f3a_gate_decision"] in {"NO_CHANGE_TO_F3A", "POSITIONING_UPDATE_ONLY"}:
        raise RuntimeError("Gate hierarchy violated by confirmed direct redraft overlap")
    if not confirmed_direct_redraft:
        raise RuntimeError("No confirmed direct redraft gate trigger remains")
    if gate["f3a_gate_decision"] != "F3A_DESIGN_RECONSIDERATION_REQUIRED":
        raise RuntimeError("Hierarchy A should resolve to F3A_DESIGN_RECONSIDERATION_REQUIRED")

    # Validate every referenced work/evidence identifier.
    missing_work = []
    missing_evidence = []
    for row in critical:
        if row["work_id"] not in all_work_ids:
            missing_work.append(row["work_id"])
        for eid in split_ids(row["evidence_ids"]):
            if eid not in all_evidence_ids:
                missing_evidence.append(eid)
    for row in positioning:
        for wid in split_ids(row["supporting_work_ids"]):
            if wid not in all_work_ids:
                missing_work.append(wid)
        for eid in split_ids(row["supporting_evidence_ids"]):
            if eid not in all_evidence_ids:
                missing_evidence.append(eid)
    for row in comparators:
        if row["work_id"] not in all_work_ids:
            missing_work.append(row["work_id"])
        for eid in split_ids(row["evidence_ids"]):
            if eid not in all_evidence_ids:
                missing_evidence.append(eid)
    for row in f3b:
        for wid in split_ids(row["source_work_ids"]):
            if wid not in all_work_ids:
                missing_work.append(wid)
        for eid in split_ids(row["evidence_ids"]):
            if eid not in all_evidence_ids:
                missing_evidence.append(eid)
    for row in requirements:
        for wid in split_ids(row["source_work_ids"]):
            if wid not in all_work_ids:
                missing_work.append(wid)
        eids = split_ids(row["source_evidence_ids"])
        if row["must_resolve_before_f3a_freeze"] == "YES" and not eids:
            raise RuntimeError(f"Unsupported gate requirement {row['requirement_id']}")
        for eid in eids:
            if eid not in all_evidence_ids:
                missing_evidence.append(eid)
    for row in final_evidence:
        for wid in split_ids(row["source_work_ids"]):
            if wid not in all_work_ids:
                missing_work.append(wid)
        for eid in split_ids(row["source_evidence_ids"]):
            if eid not in all_evidence_ids:
                missing_evidence.append(eid)

    if missing_work:
        raise RuntimeError(f"Unknown work_ids: {sorted(set(missing_work))}")
    if missing_evidence:
        raise RuntimeError(f"Unknown evidence_ids: {sorted(set(missing_evidence))}")

    assert_no_duplicates(critical, "work_id", "critical work_id")
    assert_no_duplicates(comparators, "work_id", "comparator work_id")
    assert_no_duplicates(requirements, "requirement_id", "requirement_id")
    assert_no_duplicates(final_evidence, "claim_id", "claim_id")
    assert_no_duplicates(positioning, "positioning_claim_id", "positioning_claim_id")
    assert_no_duplicates(f3b, "consideration_id", "consideration_id")

    # Closure checksum manifest.
    sums = {}
    for line in (closure / "SHA256SUMS.txt").read_text(encoding="ascii").splitlines():
        digest, name = line.split("  ", 1)
        sums[name] = digest
    closure_files = sorted(p.name for p in closure.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt")
    if set(sums) != set(closure_files):
        raise RuntimeError("Closure checksum file set mismatch")
    for name, expected in sums.items():
        if sha256_file(closure / name) != expected:
            raise RuntimeError(f"Closure checksum mismatch: {name}")

    # Top-level checksum must bind current README.
    readme_hash = sha256_file(baii / "README.md")
    top_lines = (baii / "SHA256SUMS.txt").read_text(encoding="ascii").splitlines()
    readme_entries = [line for line in top_lines if line.endswith("  README.md")]
    if readme_entries != [f"{readme_hash}  README.md"]:
        raise RuntimeError("Top-level README checksum not updated")

    # Audit self-consistency.
    expected_audit = {
        "raw_systematic_works":190,
        "primary_extracted_works":40,
        "critical_f3a_works_reviewed":15,
        "redraft_required_reviewed":2,
        "comparators_assessed":11,
        "f3b_impact_works_represented":9,
        "gate_decision_count":1,
        "baii1_files_modified":0,
        "baii2_files_modified":0,
        "baii3_files_modified":0,
        "baii4_files_modified":0,
        "f0_f2_modified":0,
        "f3a_modified":0,
        "f3b_modified":0,
        "evidence_references_missing":0,
        "unknown_work_ids":0,
        "unknown_evidence_ids":0,
        "unsupported_gate_requirements":0,
        "priority_claims_asserted":0,
    }
    for key, value in expected_audit.items():
        if audit.get(key) != value:
            raise RuntimeError(f"Audit field mismatch: {key}")
    for key in [
        "new_systematic_search_executed","systematic_denominator_modified","screening_modified",
        "work_ids_modified","scientific_results_computed","candidate_discovery_authorized",
        "novelty_assessed","f3a_design_frozen","f3b_design_frozen"
    ]:
        if audit.get(key) is not False:
            raise RuntimeError(f"Audit boundary flag must be false: {key}")

    print("BAII5_FINAL_SYNTHESIS_VALIDATION_PASS")
    print("raw_systematic_works=190")
    print("primary_extracted_works=40")
    print("critical_f3a_works_reviewed=15")
    print("redraft_required_reviewed=2")
    print("comparators_assessed=11")
    print("f3b_impact_works_represented=9")
    print("gate_decision=F3A_DESIGN_RECONSIDERATION_REQUIRED")
    print("evidence_references_missing=0")
    print("unknown_work_ids=0")
    print("unknown_evidence_ids=0")
    print("priority_claims_asserted=0")
    print("historical_baii_files_verified=40")
    print("f3a_modified=false")
    print("f3b_modified=false")
    print("novelty_assessed=false")

if __name__ == "__main__":
    main()
