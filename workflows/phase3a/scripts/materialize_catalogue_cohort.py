#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

JD_UNIX_EPOCH = Decimal("2440587.5")
SECONDS_PER_DAY = Decimal("86400")
ONE_CADENCE_DAYS = Decimal(20) / SECONDS_PER_DAY


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(f"Cannot parse decimal value: {value!r}") from exc


def canonical_decimal(value: Any) -> str:
    d = dec(value).normalize()
    return format(d, "f")


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header: {path}")
        return list(reader.fieldnames), rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def iso_utc_to_tbjd_proxy(value: str) -> Decimal:
    # Calendar proxy used only for source-level sector partitioning.
    # Exact source/native TESS timing is deferred to the FITS binding stage.
    dt = datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    unix_seconds = Decimal(str(dt.timestamp()))
    jd_utc = JD_UNIX_EPOCH + unix_seconds / SECONDS_PER_DAY
    return jd_utc - Decimal("2457000")


def infer_simple_type(values: list[str]) -> str:
    cleaned = [v.strip() for v in values if v is not None and v.strip() != ""]
    if not cleaned:
        return "empty"
    try:
        for v in cleaned:
            int(v)
        return "integer"
    except Exception:
        pass
    try:
        for v in cleaned:
            Decimal(v)
        return "decimal"
    except Exception:
        return "string"


def build_sector_partitions(
    sector_rows: list[dict[str, str]],
    allowed_min: int,
    allowed_max: int,
) -> tuple[dict[int, Decimal], list[tuple[int, Decimal, Decimal]]]:
    starts: dict[int, Decimal] = {}
    contacts: list[tuple[int, Decimal, Decimal]] = []
    for row in sector_rows:
        try:
            sector = int(row["Sector"].strip())
        except Exception:
            continue
        if not (allowed_min <= sector <= allowed_max + 1):
            continue
        start = iso_utc_to_tbjd_proxy(row["Start Time"])
        end = iso_utc_to_tbjd_proxy(row["End Time"])
        starts[sector] = min(start, starts.get(sector, start))
        if allowed_min <= sector <= allowed_max:
            contacts.append((sector, start, end))

    required = set(range(allowed_min, allowed_max + 2))
    missing = sorted(required - set(starts))
    if missing:
        raise ValueError(f"Missing sector-start boundaries: {missing}")

    return starts, contacts


def sector_for_peak(
    peak_tbjd: Decimal,
    starts: dict[int, Decimal],
    allowed_min: int,
    allowed_max: int,
) -> tuple[int, Decimal]:
    possible = [s for s in range(allowed_min, allowed_max + 1) if starts[s] <= peak_tbjd]
    if not possible:
        raise ValueError(f"Peak before first allowed sector: {peak_tbjd}")
    sector = max(possible)
    if not (peak_tbjd < starts[sector + 1]):
        raise ValueError(f"Peak not inside chronological sector partition: {peak_tbjd}")
    margin = min(peak_tbjd - starts[sector], starts[sector + 1] - peak_tbjd)
    return sector, margin


def direct_contact_sector(
    peak_tbjd: Decimal,
    contacts: list[tuple[int, Decimal, Decimal]],
) -> int | None:
    matches = [sector for sector, start, end in contacts if start <= peak_tbjd <= end]
    if len(matches) > 1:
        raise ValueError(f"Peak maps to multiple contact intervals: {peak_tbjd} -> {matches}")
    return matches[0] if matches else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument(
        "--source-root",
        default="local_archive/phase3a/f3a2_source_catalogue/QPPs-in-TESS-flares",
    )
    ap.add_argument(
        "--sector-times",
        default="local_archive/phase3a/f3a2_source_catalogue/TESS_FFI_observation_times.csv",
    )
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()
    source_root = (repo / args.source_root).resolve()
    sector_times = (repo / args.sector_times).resolve()

    design = repo / "workflows/phase3a/design"
    binding_path = repo / "workflows/phase3a/config/f3a2_primary_catalogue_binding.json"
    binding = load_json(binding_path)
    cohort_contract = load_json(design / "cohort_contract.yaml")
    label_policy = load_json(design / "reference_label_policy.json")

    expected_design_hashes = {
        "cohort_contract.yaml": "613267b13bdcfbcb89859ee9f2ed7f072d161b43c295574b718a0d3061d48c86",
        "reference_label_policy.json": "e139db5e335eb6ae059a25166e08918c9fa5f7ae2d9a7f6d406ef5c52e2412f0",
    }
    for name, expected in expected_design_hashes.items():
        actual = sha256_file(design / name)
        if actual != expected:
            raise ValueError(f"Frozen design hash mismatch: {name}: {actual}")

    if binding["provenance_status"] != "PRIMARY_CATALOGUE_PROVENANCE_VERIFIED":
        raise ValueError("Primary catalogue provenance is not verified.")
    if binding["source_work_id"] != "BAIIW0001":
        raise ValueError("Unexpected primary source work.")
    if cohort_contract["parent_catalogue"]["source_work_id"] != "BAIIW0001":
        raise ValueError("Cohort contract source mismatch.")
    if label_policy["primary_reference_source_work_id"] != "BAIIW0001":
        raise ValueError("Reference label source mismatch.")

    flare_path = source_root / "Flare_detections.csv"
    qpp_path = source_root / "QPP_detections.csv"
    expected_flare_sha = binding["sha256"]
    expected_qpp_sha = next(
        x["sha256"]
        for x in binding["related_artifacts"]
        if x["role"] == "SOURCE_QPP_SELECTED_TABLE"
    )
    expected_sector_sha = next(
        x["sha256"]
        for x in binding["related_artifacts"]
        if x["role"] == "OFFICIAL_TESS_SECTOR_START_PARTITION_REFERENCE"
    )
    checks = {
        "Flare_detections.csv": (flare_path, expected_flare_sha),
        "QPP_detections.csv": (qpp_path, expected_qpp_sha),
        "TESS_FFI_observation_times.csv": (sector_times, expected_sector_sha),
    }
    for name, (path, expected) in checks.items():
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"Physical source hash mismatch: {name}: {actual}")

    flare_cols, flare_rows = read_csv_rows(flare_path)
    qpp_cols, qpp_rows = read_csv_rows(qpp_path)
    sector_cols, sector_rows = read_csv_rows(sector_times)

    if len(flare_rows) != 3878 or len(qpp_rows) != 61:
        raise ValueError(f"Unexpected source counts: flares={len(flare_rows)}, qpps={len(qpp_rows)}")

    allowed_min = int(cohort_contract["allowed_sectors"]["minimum"])
    allowed_max = int(cohort_contract["allowed_sectors"]["maximum"])
    starts, contacts = build_sector_partitions(sector_rows, allowed_min, allowed_max)

    # Parent-event lookup used only for source-QPP label mapping.
    parent_by_start_key: dict[tuple[str, str], int] = {}
    for i, row in enumerate(flare_rows, start=1):
        key = (row["TIC_ID"].strip(), canonical_decimal(row["Start_time (TBJD)"]))
        if key in parent_by_start_key:
            raise ValueError(f"Ambiguous parent start identity: {key}")
        parent_by_start_key[key] = i

    qpp_parent_rows: dict[int, int] = {}
    qpp_tics: list[str] = []
    qpp_extension_residuals_s: list[float] = []
    for qpp_i, row in enumerate(qpp_rows, start=1):
        key = (row["TIC_ID"].strip(), canonical_decimal(row["Start_Time (TBJD)"]))
        parent_i = parent_by_start_key.get(key)
        if parent_i is None:
            raise ValueError(f"QPP row does not map to parent flare: qpp_row={qpp_i} key={key}")
        if parent_i in qpp_parent_rows:
            raise ValueError(f"Multiple QPP rows map to same parent flare: {parent_i}")
        qpp_parent_rows[parent_i] = qpp_i
        qpp_tics.append(row["TIC_ID"].strip())

        parent = flare_rows[parent_i - 1]
        observed_extension = dec(row["End_Time (TBJD)"]) - dec(parent["End_time (TBJD)"])
        expected_extension = dec(row["Tau"]) * dec(parent["Duration (days)"]) / Decimal(2)
        qpp_extension_residuals_s.append(
            float((observed_extension - expected_extension) * SECONDS_PER_DAY)
        )

    if len(qpp_parent_rows) != 61:
        raise ValueError("Expected 61 uniquely mapped source-QPP rows.")

    # Source schema
    schema_rows: list[dict[str, Any]] = []
    schema_specs = [
        ("SRC_FLARES", "Flare_detections.csv", flare_cols, flare_rows),
        ("SRC_QPPS", "QPP_detections.csv", qpp_cols, qpp_rows),
        ("TESS_SECTOR_SCHEDULE", "TESS_FFI_observation_times.csv", sector_cols, sector_rows),
    ]
    for artifact_id, table, cols, rows in schema_specs:
        for order, col in enumerate(cols, start=1):
            schema_rows.append(
                {
                    "artifact_id": artifact_id,
                    "table_name": table,
                    "column_order": order,
                    "column_name": col,
                    "inferred_type": infer_simple_type([r.get(col, "") for r in rows]),
                }
            )

    tables_dir = repo / "workflows/phase3a/evidence/tables"
    write_csv(
        tables_dir / "f3a2_source_schema.csv",
        ["artifact_id", "table_name", "column_order", "column_name", "inferred_type"],
        schema_rows,
    )

    provenance_rows = [
        {
            "component_id": "SRC_REPOSITORY",
            "component_role": "AUTHOR_REPOSITORY_COMMIT",
            "origin": binding["artifact_origin"],
            "identifier": binding["artifact_url_or_identifier"],
            "local_raw_filename": "",
            "size_bytes": "",
            "sha256": binding["source_repository"]["commit"],
            "row_count": "",
            "column_count": "",
            "verification_status": "VERIFIED",
            "notes": "Commit identity is frozen independently from file byte hashes.",
        },
        {
            "component_id": "SRC_FLARES",
            "component_role": "PARENT_FLARE_UNIVERSE",
            "origin": binding["artifact_origin"],
            "identifier": binding["artifact_url_or_identifier"] + ":Flare_detections.csv",
            "local_raw_filename": binding["local_raw_filename"],
            "size_bytes": flare_path.stat().st_size,
            "sha256": sha256_file(flare_path),
            "row_count": len(flare_rows),
            "column_count": len(flare_cols),
            "verification_status": "VERIFIED",
            "notes": "3878 source flare rows; 1285 unique TIC IDs.",
        },
        {
            "component_id": "SRC_QPPS",
            "component_role": "SOURCE_QPP_SELECTED_EVENTS",
            "origin": binding["artifact_origin"],
            "identifier": binding["artifact_url_or_identifier"] + ":QPP_detections.csv",
            "local_raw_filename": next(
                x["local_raw_filename"]
                for x in binding["related_artifacts"]
                if x["role"] == "SOURCE_QPP_SELECTED_TABLE"
            ),
            "size_bytes": qpp_path.stat().st_size,
            "sha256": sha256_file(qpp_path),
            "row_count": len(qpp_rows),
            "column_count": len(qpp_cols),
            "verification_status": "VERIFIED_WITH_DOCUMENTED_SOURCE_TEXT_COUNT_INCONSISTENCY",
            "notes": "61/61 rows map uniquely to parent flares by TIC_ID + Start_Time; 56 unique TIC IDs although manuscript reports 57 stars.",
        },
        {
            "component_id": "TESS_SECTOR_SCHEDULE",
            "component_role": "SOURCE_LEVEL_SECTOR_PARTITION_REFERENCE",
            "origin": "MIT_TESS",
            "identifier": "TESS_FFI_observation_times.csv",
            "local_raw_filename": next(
                x["local_raw_filename"]
                for x in binding["related_artifacts"]
                if x["role"] == "OFFICIAL_TESS_SECTOR_START_PARTITION_REFERENCE"
            ),
            "size_bytes": sector_times.stat().st_size,
            "sha256": sha256_file(sector_times),
            "row_count": len([r for r in sector_rows if r.get("Sector", "").strip().isdigit()]),
            "column_count": len(sector_cols),
            "verification_status": "VERIFIED_FOR_SOURCE_LEVEL_SECTOR_PARTITION",
            "notes": "Used only to derive deterministic source-level sector strata. MAST product metadata/native FITS timing remain authoritative later.",
        },
    ]
    write_csv(
        tables_dir / "f3a2_source_provenance_audit.csv",
        [
            "component_id",
            "component_role",
            "origin",
            "identifier",
            "local_raw_filename",
            "size_bytes",
            "sha256",
            "row_count",
            "column_count",
            "verification_status",
            "notes",
        ],
        provenance_rows,
    )

    source_events: list[dict[str, Any]] = []
    sector_partition_margins_s: list[float] = []
    direct_contact_count = 0
    between_contact_count = 0

    source_sha = expected_flare_sha
    for rownum, row in enumerate(flare_rows, start=1):
        tic = row["TIC_ID"].strip()
        start = dec(row["Start_time (TBJD)"])
        peak = dec(row["Peak_time (TBJD)"])
        end = dec(row["End_time (TBJD)"])
        if not (start <= peak <= end):
            raise ValueError(f"Invalid source temporal ordering at row {rownum}")

        sector, margin_days = sector_for_peak(peak, starts, allowed_min, allowed_max)
        margin_s = float(margin_days * SECONDS_PER_DAY)
        sector_partition_margins_s.append(margin_s)
        contact_sector = direct_contact_sector(peak, contacts)
        if contact_sector is not None:
            if contact_sector != sector:
                raise ValueError(
                    f"Sector partition/contact disagreement at row {rownum}: {sector} vs {contact_sector}"
                )
            sector_evidence = "CONTACT_INTERVAL_CROSSCHECK"
            direct_contact_count += 1
        else:
            sector_evidence = "CHRONOLOGICAL_SECTOR_START_PARTITION_ONLY"
            between_contact_count += 1

        peak_canon = canonical_decimal(row["Peak_time (TBJD)"])
        raw_identity = (
            f"{source_sha}|{rownum}|{tic}|{sector}|{peak_canon}".encode("utf-8")
        )
        identity_hash = hashlib.sha256(raw_identity).hexdigest()
        source_event_identifier = f"SRC_{identity_hash}"
        canonical_key = (
            f"BAIIW0001|TIC{tic}|S{sector:02d}|{source_event_identifier}"
        )

        duration_days = max(end - start, ONE_CADENCE_DAYS)
        log_duration = math.log(float(duration_days))
        is_qpp = rownum in qpp_parent_rows

        source_events.append(
            {
                "source_row_number": rownum,
                "source_event_identifier": source_event_identifier,
                "canonical_source_event_key": canonical_key,
                "tic_id": tic,
                "sector": sector,
                "source_start_time": canonical_decimal(start),
                "source_peak_time": canonical_decimal(peak),
                "source_end_time": canonical_decimal(end),
                "source_duration": canonical_decimal(duration_days),
                "log_duration": format(log_duration, ".17g"),
                "source_qpp_selected": str(bool(is_qpp)).lower(),
                "source_reference_role": (
                    "PUBLISHED_QPP_REFERENCE"
                    if is_qpp
                    else "PUBLISHED_NOT_SELECTED_REFERENCE"
                ),
                "duplicate_status": "UNIQUE",
                "source_identity_status": "DETERMINISTIC_FALLBACK_HASH",
                "sector_assignment_evidence": sector_evidence,
                "sector_partition_margin_s": format(margin_s, ".12g"),
            }
        )

    event_ids = [r["source_event_identifier"] for r in source_events]
    canonical_keys = [r["canonical_source_event_key"] for r in source_events]
    if len(event_ids) != len(set(event_ids)) or len(canonical_keys) != len(set(canonical_keys)):
        raise ValueError("Duplicate deterministic source identities.")

    write_csv(
        tables_dir / "f3a2_source_event_index.csv",
        [
            "source_row_number",
            "source_event_identifier",
            "canonical_source_event_key",
            "tic_id",
            "sector",
            "source_start_time",
            "source_peak_time",
            "source_end_time",
            "source_duration",
            "log_duration",
            "source_qpp_selected",
            "source_reference_role",
            "duplicate_status",
            "source_identity_status",
            "sector_assignment_evidence",
            "sector_partition_margin_s",
        ],
        source_events,
    )

    event_by_id = {r["source_event_identifier"]: r for r in source_events}
    references = sorted(
        [r for r in source_events if r["source_qpp_selected"] == "true"],
        key=lambda r: r["canonical_source_event_key"],
    )
    comparisons = [
        r for r in source_events if r["source_qpp_selected"] == "false"
    ]

    used_comparisons: set[str] = set()
    match_rows: list[dict[str, Any]] = []
    selected_pairs: list[tuple[dict[str, Any], dict[str, Any], str, int]] = []

    for pair_order, ref in enumerate(references, start=1):
        available = [
            c for c in comparisons if c["source_event_identifier"] not in used_comparisons
        ]
        levels = [
            (
                "SAME_TIC_SAME_SECTOR",
                lambda c: c["tic_id"] == ref["tic_id"] and c["sector"] == ref["sector"],
            ),
            (
                "SAME_TIC_ANY_SECTOR",
                lambda c: c["tic_id"] == ref["tic_id"],
            ),
            ("SAME_SECTOR", lambda c: c["sector"] == ref["sector"]),
            ("GLOBAL_ALLOWED_SECTOR_POOL", lambda c: True),
        ]

        choice = None
        for level, pred in levels:
            candidates = [c for c in available if pred(c)]
            if not candidates:
                continue
            ref_log = float(ref["log_duration"])
            scored = [
                (abs(float(c["log_duration"]) - ref_log), c["canonical_source_event_key"], c)
                for c in candidates
            ]
            min_diff = min(score[0] for score in scored)
            tied = sorted(
                [score for score in scored if score[0] == min_diff],
                key=lambda x: x[1],
            )
            chosen = tied[0][2]
            choice = (level, candidates, tied, chosen, min_diff)
            break

        pair_id = f"F3AP{pair_order:04d}"
        if choice is None:
            match_rows.append(
                {
                    "pair_id": pair_id,
                    "reference_event_id": ref["source_event_identifier"],
                    "comparison_event_id": "",
                    "matching_level": "UNMATCHED",
                    "reference_log_duration": ref["log_duration"],
                    "comparison_log_duration": "",
                    "absolute_log_duration_difference": "",
                    "candidate_count_at_chosen_level": 0,
                    "tie_count": 0,
                    "control_reused": "false",
                    "matching_status": "UNMATCHED_REFERENCE",
                }
            )
            continue

        level, candidates, tied, chosen, min_diff = choice
        if chosen["source_event_identifier"] in used_comparisons:
            raise ValueError("Control reuse detected before assignment.")
        used_comparisons.add(chosen["source_event_identifier"])
        selected_pairs.append((ref, chosen, pair_id, pair_order))
        match_rows.append(
            {
                "pair_id": pair_id,
                "reference_event_id": ref["source_event_identifier"],
                "comparison_event_id": chosen["source_event_identifier"],
                "matching_level": level,
                "reference_log_duration": ref["log_duration"],
                "comparison_log_duration": chosen["log_duration"],
                "absolute_log_duration_difference": format(min_diff, ".17g"),
                "candidate_count_at_chosen_level": len(candidates),
                "tie_count": len(tied),
                "control_reused": "false",
                "matching_status": "MATCHED_WITHOUT_REPLACEMENT",
            }
        )

    write_csv(
        tables_dir / "f3a2_matching_audit.csv",
        [
            "pair_id",
            "reference_event_id",
            "comparison_event_id",
            "matching_level",
            "reference_log_duration",
            "comparison_log_duration",
            "absolute_log_duration_difference",
            "candidate_count_at_chosen_level",
            "tie_count",
            "control_reused",
            "matching_status",
        ],
        match_rows,
    )

    cohort_rows: list[dict[str, Any]] = []
    cohort_counter = 0
    for ref, comp, pair_id, pair_order in selected_pairs:
        cohort_counter += 1
        ref_phase_id = f"F3AE{cohort_counter:06d}"
        cohort_counter += 1
        comp_phase_id = f"F3AE{cohort_counter:06d}"

        common_ref = {
            "phase3a_event_id": ref_phase_id,
            "pair_id": pair_id,
            "source_work_id": "BAIIW0001",
            "source_row_number": ref["source_row_number"],
            "source_event_identifier": ref["source_event_identifier"],
            "canonical_source_event_key": ref["canonical_source_event_key"],
            "tic_id": ref["tic_id"],
            "sector": ref["sector"],
            "source_start_time": ref["source_start_time"],
            "source_peak_time": ref["source_peak_time"],
            "source_end_time": ref["source_end_time"],
            "observational_reference_role": "PUBLISHED_QPP_REFERENCE",
            "matching_level": next(
                m["matching_level"] for m in match_rows if m["pair_id"] == pair_id
            ),
            "matched_partner_event_id": comp_phase_id,
            "membership_status": "FROZEN_MEMBER",
            "membership_reason": "ALL_SOURCE_QPP_REFERENCES",
        }
        common_comp = {
            "phase3a_event_id": comp_phase_id,
            "pair_id": pair_id,
            "source_work_id": "BAIIW0001",
            "source_row_number": comp["source_row_number"],
            "source_event_identifier": comp["source_event_identifier"],
            "canonical_source_event_key": comp["canonical_source_event_key"],
            "tic_id": comp["tic_id"],
            "sector": comp["sector"],
            "source_start_time": comp["source_start_time"],
            "source_peak_time": comp["source_peak_time"],
            "source_end_time": comp["source_end_time"],
            "observational_reference_role": "PUBLISHED_NOT_SELECTED_REFERENCE",
            "matching_level": next(
                m["matching_level"] for m in match_rows if m["pair_id"] == pair_id
            ),
            "matched_partner_event_id": ref_phase_id,
            "membership_status": "FROZEN_MEMBER",
            "membership_reason": "DETERMINISTIC_1_TO_1_MATCH_WITHOUT_REPLACEMENT",
        }
        cohort_rows.extend([common_ref, common_comp])

    write_csv(
        tables_dir / "f3a2_cohort_manifest.csv",
        [
            "phase3a_event_id",
            "pair_id",
            "source_work_id",
            "source_row_number",
            "source_event_identifier",
            "canonical_source_event_key",
            "tic_id",
            "sector",
            "source_start_time",
            "source_peak_time",
            "source_end_time",
            "observational_reference_role",
            "matching_level",
            "matched_partner_event_id",
            "membership_status",
            "membership_reason",
        ],
        cohort_rows,
    )

    ref_count = sum(r["observational_reference_role"] == "PUBLISHED_QPP_REFERENCE" for r in cohort_rows)
    comp_count = sum(r["observational_reference_role"] == "PUBLISHED_NOT_SELECTED_REFERENCE" for r in cohort_rows)
    reused = len(used_comparisons) != comp_count
    level_counts = Counter(r["matching_level"] for r in match_rows)

    # Selected cohort members must all have direct contact-interval sector crosscheck.
    selected_source_ids = {
        r["source_event_identifier"] for r in cohort_rows
    }
    selected_between_contacts = sum(
        event_by_id[eid]["sector_assignment_evidence"] != "CONTACT_INTERVAL_CROSSCHECK"
        for eid in selected_source_ids
    )

    summary = {
        "status": "PRIMARY_CATALOGUE_PROVENANCE_VERIFIED_AND_COHORT_MATERIALIZED_BEFORE_TESS_FITS",
        "source_parent_rows": len(flare_rows),
        "source_parent_unique_tics": len({r["TIC_ID"].strip() for r in flare_rows}),
        "source_qpp_rows": len(qpp_rows),
        "source_qpp_unique_tics_observed": len(set(qpp_tics)),
        "source_qpp_reported_star_count": binding["reported_qpp_star_count"],
        "qpp_parent_unique_mapping": len(qpp_parent_rows),
        "qpp_extension_consistency_max_abs_residual_s": max(abs(x) for x in qpp_extension_residuals_s),
        "sector_rows_resolved": len(source_events),
        "sector_contact_interval_crosscheck": direct_contact_count,
        "sector_between_contact_intervals": between_contact_count,
        "minimum_sector_partition_margin_s": min(sector_partition_margins_s),
        "reference_events_frozen": ref_count,
        "comparison_events_frozen": comp_count,
        "unmatched_reference_events": sum(r["matching_status"] == "UNMATCHED_REFERENCE" for r in match_rows),
        "total_cohort_events": len(cohort_rows),
        "controls_reused": reused,
        "matching_level_counts": dict(sorted(level_counts.items())),
        "selected_cohort_members_without_contact_interval_crosscheck": selected_between_contacts,
        "tess_light_curves_downloaded": False,
        "fits_opened": False,
        "afino_executed": False,
        "scientific_results_computed": False,
    }

    if ref_count != 61 or comp_count != 61 or len(cohort_rows) != 122:
        raise ValueError(f"Unexpected cohort counts: {summary}")
    if reused or summary["unmatched_reference_events"] != 0:
        raise ValueError(f"Matching contract failed: {summary}")
    if selected_between_contacts != 0:
        raise ValueError(
            "A frozen cohort member lacks direct contact-interval sector crosscheck."
        )

    print("PHASE3A_SOURCE_PROVENANCE_AND_COHORT_MATERIALIZATION_PASS")
    for key, value in summary.items():
        if isinstance(value, dict):
            print(f"{key}={json.dumps(value, sort_keys=True)}")
        else:
            print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
