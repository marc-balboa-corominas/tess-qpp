#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np


EXPECTED_PRODUCER_HASHES = {'workflows/phase3a/config/f3a2_primary_catalogue_binding.json': '4c273cc174c4f3b6f961fb79735990e1f08a4984d250b3370c460530483a105b', 'workflows/phase3a/config/f3a2_tess_product_binding_policy.json': '07d45dd226d34ee706a3f2b51c2c090b66f2eb5a42394ca520ca341f35eb816a', 'workflows/phase3a/evidence/tables/f3a2_source_schema.csv': '3a76d0d1b48eb8499b86883730f2409cd467203cad1930c26d9cd3b4a7da4c62', 'workflows/phase3a/evidence/tables/f3a2_source_provenance_audit.csv': 'e19c8adafa025e73a49da174aead00dc8ff77fb410be25f83f6afcbe77f214f5', 'workflows/phase3a/evidence/tables/f3a2_source_event_index.csv': '8d857c9ab04de7b37296da537dc187c437f53377cb398eb106da66abfa829726', 'workflows/phase3a/evidence/tables/f3a2_cohort_manifest.csv': '03c2ecd52abe0a9b78897aae4c4238160eb0b0d051c8ccc1139913b604c813e8', 'workflows/phase3a/evidence/tables/f3a2_matching_audit.csv': 'a1a93836a5d0284358ed9a4f50ae669930dc70e13cb090815d9fc236bc99217d', 'workflows/phase3a/scripts/materialize_catalogue_cohort.py': '21e00f9548ace7a00e197d6a9a7ddcf2e44710cdb621c92165aaa302dc232ecc', 'workflows/phase3a/scripts/bind_and_download_tess_products.py': '3941e81569a0c40f9b0048b3b5c4dfc3b85b441ce13cfd598021fcb728194e70', 'workflows/phase3a/evidence/tables/f3a2_tess_product_manifest.csv': 'e62d6e2d504b474275027bb86a0ffd6344c451d2fd332710baa488f3380c90bd', 'workflows/phase3a/evidence/tables/f3a2_time_mapping_audit.csv': '3b424767b7a676d712750c1c6bbe2d2bb776b70040a3486521f9fe516e50ad68', 'workflows/phase3a/scripts/materialize_primary_variants.py': '3478933f12cf8c10d9637c5d70b42e5feeffb400114b541460990698b0a0abf8', 'workflows/phase3a/evidence/tables/f3a2_primary_variant_manifest.csv': 'fc60d846bd1328692f90cd31dea91f7f16aff88b4917ff13579907b88ce88467', 'workflows/phase3a/evidence/tables/f3a2_payload_manifest.csv': 'fa5bdfa20eaf499e5354caf159221577633de92f43ec31f48be31e16cd84c148', 'workflows/phase3a/evidence/tables/f3a2_resolved_decision_grid.csv': '6d2292070332a5ca68ccd2c2d9a0673ec56657d6185845adf8dbc316d12557de', 'workflows/phase3a/evidence/tables/f3a2_exact_afino_plan.csv': 'd190a4f5e70339b05fd42b2d0cda9c51dd180c10e885c27fdfa43323c8dc1c6f'}
EXPECTED_STATIC_HASHES = {'workflows/phase3a/README.md': '963407a0d4438018ddc664669d4dc65372bc8aecb2eeb348bea18418f1d1100a', 'workflows/phase3a/evidence/reports/f3a2_materialization_audit.json': '9881ae84d55fd09bd4dba2ee02f7850a10c6d7bbd5728c8151913747cd00e851', 'workflows/phase3a/evidence/reports/f3a2_materialization_report.md': '1742360cd90121195d17971244705b96cd13e9470b080996e5fbf8ef9f57e8d2'}

F3A1_HASHES = {
    "workflows/phase3a/design/phase3a_protocol.md":
        "b0c790ad9a5234ff8a02ebb181770afa54e7dfbe4114460b34f6e66dd0023ef0",
    "workflows/phase3a/design/cohort_contract.yaml":
        "613267b13bdcfbcb89859ee9f2ed7f072d161b43c295574b718a0d3061d48c86",
    "workflows/phase3a/design/reference_label_policy.json":
        "e139db5e335eb6ae059a25166e08918c9fa5f7ae2d9a7f6d406ef5c52e2412f0",
    "workflows/phase3a/design/robustness_matrix.csv":
        "2412c686b91a287361865347f8159fb48fabae809eee783222dbbc190f0d3590",
    "workflows/phase3a/design/outcomes_denominators.json":
        "59b5513c763e6fba0859ddd139ca9c746374b75c0682dfa8e6c474ed47d3234c",
    "workflows/phase3a/design/numerical_stability_protocol.json":
        "c7869210a9d7d75532d285349a39f62be108e72acb53dd4143e2e4891b66686a",
    "workflows/phase3a/design/preregistration.json":
        "b37741f058b6cc133014b52bef6621ee34ddfc9cc671d80113c2ec7b76094ba5",
    "workflows/phase3a/ENTRY_CONTRACT.md":
        "fed87a63b1afc8221d7be175648955141664195eba253ffb05cafe8071db760a",
    "workflows/phase3a/FROZEN_INPUTS.json":
        "57e2ac1ad9185fb6cba057723a2bf97199dbb4f24091a7cf03df560e8093eda7",
}

BAII_HASHES = {
    "docs/literature/bibliographic_audit_ii/closure/final_gate_decision.json":
        "3bd6872cdf558889769d245ba86d7cd924bd333db1fe117a9a591e9755ba8c1c",
    "docs/literature/bibliographic_audit_ii/closure/f3a_gate_requirements.csv":
        "0437def01a1021fa0ca77035936eb56e002215abe2c7f52160621e393cd92b1a",
    "docs/literature/bibliographic_audit_ii/closure/comparator_consideration_matrix.csv":
        "34bb2e7b105f51b94c334aa3ec0fec90307fa2240ddab18c29b4e3d21e87bb86",
    "docs/literature/bibliographic_audit_ii/closure/final_evidence_ledger.csv":
        "09f7d73f97773672b90552cfe7fc73d8bd0fa4e67a8a0460bb3c6dbd4f63ab0a",
    "docs/decisions/DR-003-bibliographic-audit-ii-f3a-gate.md":
        "87b10926d36a45cfcf4ed574b76f13b62c860093cac3754e7ea239c15b065fc6",
}

F0F2_HASHES = {
    "foundation/f0-f2/phase2/fase2_tarea06_phase2_evidence_ledger.csv":
        "eb6eb383839d5360ad9b843d61b682a808f49c6f5932bea1c30d0c47a4aaa225",
    "foundation/f0-f2/phase2/fase2_tarea06_phase2_limitations_register.csv":
        "5379501c84162ff18b4c1dfc7d576e9051a214c885a2ab0ce10faf684d67c07a",
    "foundation/f0-f2/phase2/fase2_tarea06_manuscript_claim_matrix.csv":
        "070c7cb4eb85345c6222ecc476d527007abdfff940d80b2fd3a1b009286e57b0",
    "foundation/f0-f2/phase2/fase2_tarea06_phase3_entry_requirements.csv":
        "b3155e16beed5917d3fdc3416eace0b5d97a55ea84a7b3d3a91c27eb6846e657",
    "foundation/f0-f2/phase2/fase2_tarea06_phase2_decision.json":
        "6ac1962077833b08d979b715a52a75a99b1d3a169430ca7abc46d17926eb3ab2",
    "foundation/f0-f2/phase2/fase2_tarea06_phase2_synthesis_audit.json":
        "de7093044e5d1ea4f32d17926cdb52c59614db0eb8af1982703fe650782b7cdd",
    "foundation/f0-f2/phase2/fase2_tarea06_phase2_synthesis_report.md":
        "b2c693c40fd8d29227e4d03837e1901e488624b1dc60d87ca8b5b5461a93303e",
}

SOURCE_HASHES = {
    "local_archive/phase3a/f3a2_source_catalogue/QPPs-in-TESS-flares/Flare_detections.csv":
        "866c7ebf0d2d3a6f024b55bd112e7d91491518dfd18a57b26a3f999c5d66faa4",
    "local_archive/phase3a/f3a2_source_catalogue/QPPs-in-TESS-flares/QPP_detections.csv":
        "4f9d6c07fc722917fa432989b2d7c20b9b8da7cef4227a44187b55b6ddcfbe8e",
    "local_archive/phase3a/f3a2_source_catalogue/TESS_FFI_observation_times.csv":
        "e7c937a06e941f3ee7af150132f135ccb3c9636fda78d30cc0f8e343fd138768",
}

PAYLOAD_PHYSICAL_HASHES = {
    "data/interim/phase3a/f3a2_payloads/time_seconds.npy":
        "8302d2d9527ee358bfe3b809d1d91f88022f47411d08f6cdf2fc2a0e0c2113fa",
    "data/interim/phase3a/f3a2_payloads/flux.npy":
        "aae865acd94446072e89175057ce2c6d49bb3fe294b14ae8c0a095eb42d280fa",
    "data/interim/phase3a/f3a2_payloads/native_index.npy":
        "abe2c5b23bfcade8000c992b64067ee933c514a577deca8a870ea13ba562e52a",
    "data/interim/phase3a/f3a2_payloads/offsets.npy":
        "72d87c7ca15ce446bdefa79651e70836cfd77826630f9c870119c80f80956a68",
}

ALLOWED_INADMISSIBILITY = {
    "MISSING_PRODUCT",
    "WINDOW_OUT_OF_RANGE",
    "PEAK_OUTSIDE_WINDOW",
    "PEAK_REMOVED_BY_QUALITY",
    "TOO_FEW_CADENCES",
    "NONFINITE_INPUT",
    "IRREGULAR_SAMPLING",
    "DETREND_FAILURE",
    "SOURCE_TIME_MAPPING_UNRESOLVED",
}

EXPECTED_INADMISSIBILITY_COUNTS = {
    "IRREGULAR_SAMPLING": 1824,
    "PEAK_OUTSIDE_WINDOW": 138,
    "PEAK_REMOVED_BY_QUALITY": 282,
    "TOO_FEW_CADENCES": 844,
    "WINDOW_OUT_OF_RANGE": 6,
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_array(values: Any, dtype: str) -> np.ndarray:
    return np.ascontiguousarray(values, dtype=np.dtype(dtype))


def canonical_array_hash(values: Any, dtype: str) -> str:
    return sha256_bytes(canonical_array(values, dtype).tobytes(order="C"))


def logical_payload_hash(t, f, idx) -> str:
    h = hashlib.sha256()
    h.update(b"F3A2_LOGICAL_PAYLOAD_V1\0")
    h.update(canonical_array(t, "<f8").tobytes(order="C"))
    h.update(b"\0")
    h.update(canonical_array(f, "<f8").tobytes(order="C"))
    h.update(b"\0")
    h.update(canonical_array(idx, "<i8").tobytes(order="C"))
    return h.hexdigest()


def read_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def require_hashes(repo: Path, mapping: dict[str, str], label: str) -> None:
    for rel, expected in mapping.items():
        p = repo / rel
        if not p.is_file():
            raise RuntimeError(f"{label}: missing {rel}")
        actual = sha256_file(p)
        if actual != expected:
            raise RuntimeError(
                f"{label}: hash mismatch {rel}\nexpected={expected}\nactual={actual}"
            )


def verify_protected_history(repo: Path) -> None:
    require_hashes(repo, F3A1_HASHES, "F3A.1")
    require_hashes(repo, BAII_HASHES, "BAII")
    require_hashes(repo, F0F2_HASHES, "F0-F2")
    protected = [
        "foundation/f0-f2",
        "docs/literature/bibliographic_audit_ii",
        "workflows/phase3b",
        "workflows/phase3a/design",
        "workflows/phase3a/ENTRY_CONTRACT.md",
        "workflows/phase3a/FROZEN_INPUTS.json",
    ]
    cmd = ["git", "diff", "--quiet", "phase3a-design-v1", "--", *protected]
    cp = subprocess.run(cmd, cwd=repo)
    if cp.returncode != 0:
        raise RuntimeError("Protected historical scopes differ from phase3a-design-v1.")


def verify_source(repo: Path):
    require_hashes(repo, SOURCE_HASHES, "SOURCE")
    flare = read_csv(repo / next(k for k in SOURCE_HASHES if k.endswith("Flare_detections.csv")))
    qpp = read_csv(repo / next(k for k in SOURCE_HASHES if k.endswith("QPP_detections.csv")))
    if len(flare) != 3878 or len({r["TIC_ID"].strip() for r in flare}) != 1285:
        raise RuntimeError("Parent source counts are not 3878/1285.")
    if len(qpp) != 61 or len({r["TIC_ID"].strip() for r in qpp}) != 56:
        raise RuntimeError("QPP machine-readable counts are not 61 rows / 56 TICs.")
    parent = {}
    for i, r in enumerate(flare, start=1):
        key = (r["TIC_ID"].strip(), r["Start_time (TBJD)"].strip().rstrip("0").rstrip("."))
        if key in parent:
            raise RuntimeError(f"Ambiguous parent source start key: {key}")
        parent[key] = i
    matched = set()
    for r in qpp:
        key = (r["TIC_ID"].strip(), r["Start_Time (TBJD)"].strip().rstrip("0").rstrip("."))
        if key not in parent:
            raise RuntimeError(f"QPP source row lacks parent: {key}")
        if parent[key] in matched:
            raise RuntimeError(f"Two QPP rows map to one parent: {key}")
        matched.add(parent[key])
    if len(matched) != 61:
        raise RuntimeError("QPP-to-parent unique mapping is not 61.")
    return flare, qpp


def reconstruct_matching(source_rows):
    refs = sorted(
        [r for r in source_rows if r["source_qpp_selected"] == "true"],
        key=lambda r: r["canonical_source_event_key"],
    )
    comparisons = [r for r in source_rows if r["source_qpp_selected"] == "false"]
    used = set()
    out = []
    for idx, ref in enumerate(refs, start=1):
        available = [
            c for c in comparisons
            if c["source_event_identifier"] not in used
        ]
        levels = [
            ("SAME_TIC_SAME_SECTOR",
             lambda c: c["tic_id"] == ref["tic_id"] and c["sector"] == ref["sector"]),
            ("SAME_TIC_ANY_SECTOR", lambda c: c["tic_id"] == ref["tic_id"]),
            ("SAME_SECTOR", lambda c: c["sector"] == ref["sector"]),
            ("GLOBAL_ALLOWED_SECTOR_POOL", lambda c: True),
        ]
        choice = None
        for level, pred in levels:
            candidates = [c for c in available if pred(c)]
            if not candidates:
                continue
            rlog = float(ref["log_duration"])
            scored = sorted(
                (
                    abs(float(c["log_duration"]) - rlog),
                    c["canonical_source_event_key"],
                    c,
                )
                for c in candidates
            )
            minimum = scored[0][0]
            tied = [x for x in scored if x[0] == minimum]
            chosen = tied[0][2]
            choice = (level, len(candidates), len(tied), chosen, minimum)
            break
        pair_id = f"F3AP{idx:04d}"
        if choice is None:
            out.append({
                "pair_id": pair_id,
                "reference_event_id": ref["source_event_identifier"],
                "comparison_event_id": "",
                "matching_level": "UNMATCHED",
                "matching_status": "UNMATCHED_REFERENCE",
            })
            continue
        level, candidate_count, tie_count, chosen, minimum = choice
        if chosen["source_event_identifier"] in used:
            raise RuntimeError("Independent reconstruction attempted control reuse.")
        used.add(chosen["source_event_identifier"])
        out.append({
            "pair_id": pair_id,
            "reference_event_id": ref["source_event_identifier"],
            "comparison_event_id": chosen["source_event_identifier"],
            "matching_level": level,
            "reference_log_duration": ref["log_duration"],
            "comparison_log_duration": chosen["log_duration"],
            "absolute_log_duration_difference": format(minimum, ".17g"),
            "candidate_count_at_chosen_level": str(candidate_count),
            "tie_count": str(tie_count),
            "control_reused": "false",
            "matching_status": "MATCHED_WITHOUT_REPLACEMENT",
        })
    return refs, out


def verify_cohort(repo: Path):
    tables = repo / "workflows/phase3a/evidence/tables"
    source = read_csv(tables / "f3a2_source_event_index.csv")
    cohort = read_csv(tables / "f3a2_cohort_manifest.csv")
    recorded_matches = read_csv(tables / "f3a2_matching_audit.csv")

    if len(source) != 3878 or len(cohort) != 122 or len(recorded_matches) != 61:
        raise RuntimeError("Source/cohort/matching row counts are invalid.")
    if len({r["phase3a_event_id"] for r in cohort}) != 122:
        raise RuntimeError("Duplicate phase3a_event_id.")
    if any(r["control_reused"] != "false" for r in recorded_matches):
        raise RuntimeError("Control reuse recorded.")

    refs, rebuilt = reconstruct_matching(source)
    if len(refs) != 61 or len(rebuilt) != 61:
        raise RuntimeError("Independent matching reconstruction count failed.")

    for expected, observed in zip(rebuilt, recorded_matches):
        for field in (
            "pair_id", "reference_event_id", "comparison_event_id",
            "matching_level", "matching_status",
        ):
            if str(observed.get(field, "")) != str(expected.get(field, "")):
                raise RuntimeError(
                    f"Matching reconstruction mismatch {expected['pair_id']} field={field}"
                )

    source_by_id = {r["source_event_identifier"]: r for r in source}
    expected_cohort = []
    counter = 0
    for match in rebuilt:
        if match["matching_status"] == "UNMATCHED_REFERENCE":
            continue
        ref = source_by_id[match["reference_event_id"]]
        comp = source_by_id[match["comparison_event_id"]]
        counter += 1
        ref_phase = f"F3AE{counter:06d}"
        counter += 1
        comp_phase = f"F3AE{counter:06d}"
        expected_cohort.extend([
            {
                "phase3a_event_id": ref_phase,
                "pair_id": match["pair_id"],
                "source_event_identifier": ref["source_event_identifier"],
                "canonical_source_event_key": ref["canonical_source_event_key"],
                "tic_id": ref["tic_id"],
                "sector": ref["sector"],
                "observational_reference_role": "PUBLISHED_QPP_REFERENCE",
                "matched_partner_event_id": comp_phase,
            },
            {
                "phase3a_event_id": comp_phase,
                "pair_id": match["pair_id"],
                "source_event_identifier": comp["source_event_identifier"],
                "canonical_source_event_key": comp["canonical_source_event_key"],
                "tic_id": comp["tic_id"],
                "sector": comp["sector"],
                "observational_reference_role": "PUBLISHED_NOT_SELECTED_REFERENCE",
                "matched_partner_event_id": ref_phase,
            },
        ])

    for expected, observed in zip(expected_cohort, cohort):
        for field, value in expected.items():
            if observed[field] != value:
                raise RuntimeError(
                    f"Cohort re-materialization mismatch {observed['phase3a_event_id']} "
                    f"field={field}"
                )

    roles = Counter(r["observational_reference_role"] for r in cohort)
    if roles != {
        "PUBLISHED_QPP_REFERENCE": 61,
        "PUBLISHED_NOT_SELECTED_REFERENCE": 61,
    }:
        raise RuntimeError(f"Unexpected cohort roles: {roles}")
    if len({r["tic_id"] for r in cohort}) != 63:
        raise RuntimeError("Unexpected frozen cohort TIC count.")
    if len({r["sector"] for r in cohort}) != 35:
        raise RuntimeError("Unexpected frozen cohort sector count.")
    return cohort, recorded_matches


def verify_tess(repo: Path):
    tables = repo / "workflows/phase3a/evidence/tables"
    products = read_csv(tables / "f3a2_tess_product_manifest.csv")
    times = read_csv(tables / "f3a2_time_mapping_audit.csv")
    if len(products) != 122 or len(times) != 122:
        raise RuntimeError("TESS product/time relationship count is not 122.")
    if any(r["product_status"] != "BOUND_DOWNLOADED" for r in products):
        raise RuntimeError("At least one frozen event does not have a bound product.")
    if any(r["time_mapping_status"] != "TIME_MAPPING_VALID" for r in products):
        raise RuntimeError("Product manifest contains non-valid time mapping.")
    if any(r["time_mapping_status"] != "TIME_MAPPING_VALID" for r in times):
        raise RuntimeError("Time audit contains non-valid mapping.")

    unique = {}
    for r in products:
        key = r["physical_filename"]
        record = (r["physical_sha256"], int(r["size_bytes"]))
        if key in unique and unique[key] != record:
            raise RuntimeError(f"Conflicting physical identity for {key}")
        unique[key] = record
    if len(unique) != 87:
        raise RuntimeError(f"Expected 87 unique FITS, got {len(unique)}")

    raw = repo / "data/raw/phase3a/tess"
    for filename, (expected, _) in unique.items():
        p = raw / filename
        if not p.is_file():
            raise RuntimeError(f"Missing frozen FITS: {filename}")
        actual = sha256_file(p)
        if actual != expected:
            raise RuntimeError(
                f"FITS physical hash mismatch {filename}: {actual} != {expected}"
            )
    return products, times, unique


def verify_variants_payloads_plan(repo: Path):
    tables = repo / "workflows/phase3a/evidence/tables"
    variants = read_csv(tables / "f3a2_primary_variant_manifest.csv")
    payloads = read_csv(tables / "f3a2_payload_manifest.csv")
    decisions = read_csv(tables / "f3a2_resolved_decision_grid.csv")
    plan = read_csv(tables / "f3a2_exact_afino_plan.csv")

    if len(variants) != 9516:
        raise RuntimeError(f"Expected 9516 primary variants, got {len(variants)}")
    if len({r["variant_id"] for r in variants}) != 9516:
        raise RuntimeError("Duplicate variant IDs.")
    by_event = Counter(r["phase3a_event_id"] for r in variants)
    if len(by_event) != 122 or set(by_event.values()) != {78}:
        raise RuntimeError("Exactly 78 primary matrix rows/event not satisfied.")

    matrix_sets = defaultdict(set)
    for r in variants:
        matrix_sets[r["phase3a_event_id"]].add(
            (r["window_variant_id"], r["processing_profile_id"])
        )
    if any(len(v) != 78 for v in matrix_sets.values()):
        raise RuntimeError("At least one event lacks 78 unique window/profile cells.")

    eligible = [r for r in variants if r["materialization_status"] == "ELIGIBLE_FOR_AFINO"]
    inad = [r for r in variants if r["materialization_status"] == "INPUT_INADMISSIBLE"]
    if len(eligible) != 6422 or len(inad) != 3094:
        raise RuntimeError("Eligible/inadmissible counts differ from frozen materialization.")
    reason_counts = Counter(r["inadmissibility_reason_code"] for r in inad)
    if dict(reason_counts) != EXPECTED_INADMISSIBILITY_COUNTS:
        raise RuntimeError(f"Inadmissibility counts mismatch: {reason_counts}")
    if any(r["inadmissibility_reason_code"] not in ALLOWED_INADMISSIBILITY for r in inad):
        raise RuntimeError("Invalid inadmissibility reason.")
    if any(r["inadmissibility_reason_code"] for r in eligible):
        raise RuntimeError("Eligible variant has inadmissibility reason.")

    if len(payloads) != len(eligible) or len(payloads) != 6422:
        raise RuntimeError("Eligible payload count != payload manifest count.")
    if len({r["payload_id"] for r in payloads}) != len(payloads):
        raise RuntimeError("Duplicate payload ID.")
    if len({r["variant_id"] for r in payloads}) != len(payloads):
        raise RuntimeError("A variant has multiple payloads.")

    require_hashes(repo, PAYLOAD_PHYSICAL_HASHES, "PAYLOAD_NPY")
    base = repo / "data/interim/phase3a/f3a2_payloads"
    t = np.load(base / "time_seconds.npy", mmap_mode="r", allow_pickle=False)
    f = np.load(base / "flux.npy", mmap_mode="r", allow_pickle=False)
    idx = np.load(base / "native_index.npy", mmap_mode="r", allow_pickle=False)
    offsets = np.load(base / "offsets.npy", mmap_mode="r", allow_pickle=False)
    if len(offsets) != len(payloads) + 1 or int(offsets[0]) != 0:
        raise RuntimeError("Payload offsets structure invalid.")
    if not (len(t) == len(f) == len(idx) == int(offsets[-1])):
        raise RuntimeError("Concatenated payload physical lengths disagree.")

    roundtrip_mismatches = 0
    payload_by_variant = {}
    for order, p in enumerate(payloads):
        start = int(p["offset"])
        length = int(p["length"])
        end = start + length
        if int(offsets[order]) != start or int(offsets[order + 1]) != end:
            roundtrip_mismatches += 1
        if canonical_array_hash(t[start:end], "<f8") != p["time_sha256"]:
            roundtrip_mismatches += 1
        if canonical_array_hash(f[start:end], "<f8") != p["flux_sha256"]:
            roundtrip_mismatches += 1
        if canonical_array_hash(idx[start:end], "<i8") != p["native_index_sha256"]:
            roundtrip_mismatches += 1
        if logical_payload_hash(
            t[start:end], f[start:end], idx[start:end]
        ) != p["logical_payload_sha256"]:
            roundtrip_mismatches += 1
        payload_by_variant[p["variant_id"]] = p
    if roundtrip_mismatches != 0:
        raise RuntimeError(f"Payload roundtrip mismatches={roundtrip_mismatches}")

    w00p00 = {
        r["phase3a_event_id"]: r
        for r in eligible
        if r["window_variant_id"] == "W00"
        and r["processing_profile_id"] == "P00"
    }
    if len(w00p00) != 116:
        raise RuntimeError("W00/P00 eligible event count is not 116.")

    primary = [d for d in decisions if d["decision_class"] == "PRIMARY"]
    stability = [d for d in decisions if d["decision_class"] == "STABILITY"]
    if len(primary) != 6422 or len(stability) != 1044 or len(decisions) != 7466:
        raise RuntimeError("Resolved decision counts are invalid.")

    eligible_variant_ids = {r["variant_id"] for r in eligible}
    if {d["variant_id"] for d in primary} != eligible_variant_ids:
        raise RuntimeError("Primary decisions do not map one-to-one to eligible variants.")
    if any(int(d["external_optimizer_seed"]) != 0 for d in primary):
        raise RuntimeError("Primary decision seed is not 0.")

    stability_by_event = defaultdict(set)
    for d in stability:
        if d["window_variant_id"] != "W00" or d["processing_profile_id"] != "P00":
            raise RuntimeError("Stability decision outside W00/P00.")
        stability_by_event[d["phase3a_event_id"]].add(int(d["external_optimizer_seed"]))
    if set(stability_by_event) != set(w00p00):
        raise RuntimeError("Stability event scope != eligible W00/P00 event scope.")
    if any(seeds != set(range(1, 10)) for seeds in stability_by_event.values()):
        raise RuntimeError("Each stability event must contain exactly seeds 1..9.")

    if len(plan) != 22398 or len(plan) != 3 * len(decisions):
        raise RuntimeError("Exact AFINO call count != 3 × decisions.")
    if len({r["job_id"] for r in plan}) != len(plan):
        raise RuntimeError("Duplicate job IDs.")
    model_counts = Counter(r["model_id"] for r in plan)
    if model_counts != {"M0": 7466, "M1": 7466, "M2": 7466}:
        raise RuntimeError(f"Unequal model call counts: {model_counts}")
    expected_names = {"M0": "pow_const", "M1": "pow_const_gauss", "M2": "bpow_const"}
    for r in plan:
        if r["execution_status"] != "NOT_EXECUTED":
            raise RuntimeError("A plan row is not NOT_EXECUTED.")
        if r["model_name"] != expected_names[r["model_id"]]:
            raise RuntimeError("Model name mismatch.")
        if r["afino_version"] != "0.5":
            raise RuntimeError("AFINO version mismatch.")
        if r["afino_commit"] != "6aceac9518fc8056052807e666da9d0c8bebb010":
            raise RuntimeError("AFINO commit mismatch.")
        if not math.isclose(float(r["low_frequency_cutoff_hz"]), 0.025):
            raise RuntimeError("Low-frequency cutoff mismatch.")

    forbidden_columns = {
        "bic", "bic_m0", "bic_m1", "bic_m2", "qpp_selected",
        "estimated_period_s", "decision_status", "result_status",
        "formal_m1_period_s",
    }
    if forbidden_columns.intersection(plan[0].keys()):
        raise RuntimeError("AFINO result/output fields are populated in the frozen plan.")

    return (
        variants, payloads, decisions, plan,
        roundtrip_mismatches, reason_counts, model_counts,
    )


def verify_audit_and_report(repo: Path):
    audit_path = repo / "workflows/phase3a/evidence/reports/f3a2_materialization_audit.json"
    report_path = repo / "workflows/phase3a/evidence/reports/f3a2_materialization_report.md"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    required = {
        "status": "PHASE3A_COHORT_AND_EXECUTION_PLAN_FROZEN_WITH_DOCUMENTED_LIMITATION",
        "primary_source_provenance_status": "PRIMARY_CATALOGUE_PROVENANCE_VERIFIED",
        "source_parent_rows": 3878,
        "source_qpp_rows": 61,
        "source_qpp_unique_events": 61,
        "reference_events_frozen": 61,
        "comparison_events_frozen": 61,
        "unmatched_reference_events": 0,
        "total_cohort_events": 122,
        "unique_tic_count": 63,
        "sector_count": 35,
        "event_product_relationships": 122,
        "unique_physical_fits": 87,
        "primary_planned_variants": 9516,
        "primary_eligible_variants": 6422,
        "primary_inadmissible_variants": 3094,
        "w00_p00_eligible_events": 116,
        "primary_executable_decisions": 6422,
        "stability_extra_decisions": 1044,
        "total_executable_decisions": 7466,
        "exact_model_calls": 22398,
        "m0_calls": 7466,
        "m1_calls": 7466,
        "m2_calls": 7466,
        "payload_roundtrip_mismatches": 0,
        "duplicate_event_ids": 0,
        "duplicate_variant_ids": 0,
        "duplicate_job_ids": 0,
        "controls_reused": False,
        "afino_executed": False,
        "scientific_results_computed": False,
        "baseline_classifications_observed": False,
    }
    for k, v in required.items():
        if audit.get(k) != v:
            raise RuntimeError(f"Audit mismatch {k}: {audit.get(k)!r} != {v!r}")
    if audit.get("inadmissibility_counts") != EXPECTED_INADMISSIBILITY_COUNTS:
        raise RuntimeError("Audit inadmissibility counts mismatch.")
    words = report_path.read_text(encoding="utf-8").split()
    if not 800 <= len(words) <= 1200:
        raise RuntimeError(f"F3A.2 report word count out of range: {len(words)}")
    return audit, len(words)


def git_output_paths(repo: Path) -> list[Path]:
    paths = [repo / "workflows/phase3a/README.md"]
    paths += sorted((repo / "workflows/phase3a/config").glob("f3a2_*.json"))
    paths += [
        repo / "workflows/phase3a/scripts/materialize_catalogue_cohort.py",
        repo / "workflows/phase3a/scripts/bind_and_download_tess_products.py",
        repo / "workflows/phase3a/scripts/materialize_primary_variants.py",
        repo / "workflows/phase3a/scripts/validate_materialization_and_plan.py",
        repo / "workflows/phase3a/tests/test_f3a2_materialization_contract.py",
    ]
    paths += sorted((repo / "workflows/phase3a/evidence/tables").glob("f3a2_*.csv"))
    paths += [
        repo / "workflows/phase3a/evidence/reports/f3a2_materialization_audit.json",
        repo / "workflows/phase3a/evidence/reports/f3a2_materialization_report.md",
    ]
    unique = []
    seen = set()
    for p in paths:
        p = p.resolve()
        if p not in seen:
            unique.append(p)
            seen.add(p)
    return unique


def write_checksums(repo: Path, products, payloads) -> Path:
    out = repo / "workflows/phase3a/evidence/f3a2_SHA256SUMS.txt"
    lines = [
        "# F3A.2 checksum registry v1",
        "# KIND\\tSHA256\\tLOCATOR",
    ]
    for p in sorted(git_output_paths(repo), key=lambda x: x.relative_to(repo).as_posix()):
        if not p.is_file():
            raise RuntimeError(f"Cannot checksum missing Git output: {p}")
        lines.append(
            f"GIT_FILE\t{sha256_file(p)}\t{p.relative_to(repo).as_posix()}"
        )

    for rel in sorted(SOURCE_HASHES):
        p = repo / rel
        lines.append(f"SOURCE_PHYSICAL\t{sha256_file(p)}\t{rel}")

    for rel in sorted(PAYLOAD_PHYSICAL_HASHES):
        p = repo / rel
        lines.append(f"PAYLOAD_PHYSICAL\t{sha256_file(p)}\t{rel}")

    unique_fits = {}
    for r in products:
        unique_fits[r["physical_filename"]] = r["physical_sha256"]
    for filename in sorted(unique_fits):
        rel = f"data/raw/phase3a/tess/{filename}"
        lines.append(f"FITS_PHYSICAL\t{unique_fits[filename]}\t{rel}")

    for p in payloads:
        lines.append(
            f"PAYLOAD_LOGICAL\t{p['logical_payload_sha256']}\t{p['payload_id']}"
        )

    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return out


def verify_checksums(repo: Path, products, payloads):
    path = repo / "workflows/phase3a/evidence/f3a2_SHA256SUMS.txt"
    if not path.is_file():
        raise RuntimeError(
            "Missing f3a2_SHA256SUMS.txt. Run validator once with --write-checksums."
        )
    lines = [
        line for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    parsed = [line.split("\t", 2) for line in lines]
    if any(len(x) != 3 for x in parsed):
        raise RuntimeError("Malformed f3a2_SHA256SUMS.txt line.")

    git_expected = {
        p.relative_to(repo).as_posix(): sha256_file(p)
        for p in git_output_paths(repo)
    }
    source_expected = {
        rel: sha256_file(repo / rel) for rel in SOURCE_HASHES
    }
    payload_physical_expected = {
        rel: sha256_file(repo / rel) for rel in PAYLOAD_PHYSICAL_HASHES
    }
    fits_expected = {
        f"data/raw/phase3a/tess/{r['physical_filename']}": r["physical_sha256"]
        for r in products
    }
    logical_expected = {
        p["payload_id"]: p["logical_payload_sha256"]
        for p in payloads
    }

    groups = defaultdict(dict)
    for kind, digest, locator in parsed:
        if locator in groups[kind]:
            raise RuntimeError(f"Duplicate checksum locator: {kind} {locator}")
        groups[kind][locator] = digest

    expected_groups = {
        "GIT_FILE": git_expected,
        "SOURCE_PHYSICAL": source_expected,
        "PAYLOAD_PHYSICAL": payload_physical_expected,
        "FITS_PHYSICAL": fits_expected,
        "PAYLOAD_LOGICAL": logical_expected,
    }
    for kind, expected in expected_groups.items():
        observed = groups.get(kind, {})
        if observed != expected:
            missing = sorted(set(expected) - set(observed))
            extra = sorted(set(observed) - set(expected))
            mismatched = sorted(
                k for k in set(expected) & set(observed)
                if expected[k] != observed[k]
            )
            raise RuntimeError(
                f"Checksum registry mismatch {kind}: "
                f"missing={len(missing)} extra={len(extra)} mismatched={len(mismatched)}"
            )
    return {
        "git_files": len(git_expected),
        "source_physical": len(source_expected),
        "payload_physical": len(payload_physical_expected),
        "fits_physical": len(fits_expected),
        "payload_logical": len(logical_expected),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--write-checksums", action="store_true")
    args = ap.parse_args()
    repo = Path(args.repo_root).resolve()

    require_hashes(repo, EXPECTED_PRODUCER_HASHES, "F3A.2 PRODUCER OUTPUT")
    require_hashes(repo, EXPECTED_STATIC_HASHES, "F3A.2 STATIC OUTPUT")
    verify_protected_history(repo)
    verify_source(repo)
    cohort, matching = verify_cohort(repo)
    products, times, unique_fits = verify_tess(repo)
    (
        variants, payloads, decisions, plan,
        roundtrip, reason_counts, model_counts,
    ) = verify_variants_payloads_plan(repo)
    audit, report_words = verify_audit_and_report(repo)

    if args.write_checksums:
        checksum_path = write_checksums(repo, products, payloads)
        print(f"f3a2_sha256sums_written={checksum_path.relative_to(repo).as_posix()}")

    checksum_counts = verify_checksums(repo, products, payloads)

    print("PHASE3A_MATERIALIZATION_AND_PLAN_VALIDATION_PASS")
    print("primary_source_provenance_status=PRIMARY_CATALOGUE_PROVENANCE_VERIFIED")
    print("source_parent_rows=3878")
    print("source_qpp_rows=61")
    print("reference_events_frozen=61")
    print("comparison_events_frozen=61")
    print("unmatched_reference_events=0")
    print("total_cohort_events=122")
    print("event_product_relationships=122")
    print("unique_physical_fits=87")
    print("time_mapping_valid=122")
    print("primary_planned_variants=9516")
    print("primary_eligible_variants=6422")
    print("primary_inadmissible_variants=3094")
    print("inadmissibility_counts=" + json.dumps(
        dict(sorted(reason_counts.items())), sort_keys=True
    ))
    print("w00_p00_eligible_events=116")
    print("primary_executable_decisions=6422")
    print("stability_extra_decisions=1044")
    print("total_executable_decisions=7466")
    print("exact_model_calls=22398")
    print("m0_calls=7466")
    print("m1_calls=7466")
    print("m2_calls=7466")
    print(f"payload_roundtrip_mismatches={roundtrip}")
    print(f"report_word_count={report_words}")
    for k, v in checksum_counts.items():
        print(f"checksum_{k}={v}")
    print("afino_executed=false")
    print("scientific_results_computed=false")
    print("baseline_classifications_observed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
