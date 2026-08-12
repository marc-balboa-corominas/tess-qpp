#!/usr/bin/env python3
"""
F3A.4 — assemble the complete frozen execution output into 7,466 decisions and
a 7,466-row temporal-contract diagnostic. No scientific summaries are computed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

EXPECTED_RESULTS = 22398
EXPECTED_DECISIONS = 7466
ABS_TOL = 5.0e-12

FULL_RESULTS_REL = Path("workflows/phase3a/evidence/tables/f3a4_full_results.csv")
DECISION_GRID_REL = Path(
    "workflows/phase3a/evidence/tables/f3a2_resolved_decision_grid.csv"
)
PAYLOAD_MANIFEST_REL = Path(
    "workflows/phase3a/evidence/tables/f3a2_payload_manifest.csv"
)
PAYLOAD_DIR_REL = Path("data/interim/phase3a/f3a2_payloads")

OUTPUT_DECISIONS_REL = Path(
    "workflows/phase3a/evidence/tables/f3a4_full_decisions.csv"
)
OUTPUT_TEMPORAL_REL = Path(
    "workflows/phase3a/evidence/tables/f3a4_temporal_contract_diagnostic.csv"
)

PAYLOAD_PHYSICAL_HASHES = {
    "time_seconds.npy":
        "8302d2d9527ee358bfe3b809d1d91f88022f47411d08f6cdf2fc2a0e0c2113fa",
    "flux.npy":
        "aae865acd94446072e89175057ce2c6d49bb3fe294b14ae8c0a095eb42d280fa",
    "native_index.npy":
        "abe2c5b23bfcade8000c992b64067ee933c514a577deca8a870ea13ba562e52a",
    "offsets.npy":
        "72d87c7ca15ce446bdefa79651e70836cfd77826630f9c870119c80f80956a68",
}

DECISION_FIELDS = [
    "planned_decision_id",
    "decision_order",
    "decision_class",
    "phase3a_event_id",
    "pair_id",
    "observational_reference_role",
    "variant_id",
    "matrix_cell_id",
    "window_variant_id",
    "processing_profile_id",
    "external_optimizer_seed",
    "payload_id",
    "payload_logical_sha256",
    "input_n_samples",
    "bic_m0",
    "bic_m1",
    "bic_m2",
    "delta_bic_0_1",
    "delta_bic_2_1",
    "qpp_selected",
    "formal_m1_period_s",
    "period_label",
    "decision_status",
]

TEMPORAL_FIELDS = [
    "planned_decision_id",
    "decision_order",
    "variant_id",
    "external_optimizer_seed",
    "payload_id",
    "n_samples",
    "mean_dt_external",
    "median_dt_external",
    "afino_dt_m0",
    "afino_dt_m1",
    "afino_dt_m2",
    "mean_dt_match_m0",
    "mean_dt_match_m1",
    "mean_dt_match_m2",
    "positive_fftfreq_bin_count_external",
    "rfftfreq_positive_bin_count_external",
    "afino_bin_count_m0",
    "afino_bin_count_m1",
    "afino_bin_count_m2",
    "fftfreq_positive_match",
    "legacy_median_dt_match",
    "legacy_rfftfreq_match",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()


def read_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=fields, extrasaction="raise", lineterminator="\n"
        )
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def selection_rule(b0: float, b1: float, b2: float) -> bool:
    return bool((b0 - b1 > 10.0) and (b2 - b1 > 10.0))


def close(a: float, b: float) -> bool:
    return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=ABS_TOL)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()
    repo = Path(args.repo_root).resolve()

    results = read_csv(repo / FULL_RESULTS_REL)
    decision_grid = read_csv(repo / DECISION_GRID_REL)
    payload_rows = read_csv(repo / PAYLOAD_MANIFEST_REL)

    if len(results) != EXPECTED_RESULTS:
        raise RuntimeError(f"Expected 22,398 results, got {len(results)}")
    if Counter(r["model_id"] for r in results) != {
        "M0": 7466, "M1": 7466, "M2": 7466
    }:
        raise RuntimeError("Result model counts are not 7466/7466/7466.")
    if any(r["status"] != "OK" for r in results):
        raise RuntimeError("At least one full result is not OK.")
    if len(decision_grid) != EXPECTED_DECISIONS:
        raise RuntimeError("Frozen decision grid row count mismatch.")

    grid_by_key = {
        (
            r["planned_decision_id"],
            r["variant_id"],
            int(r["external_optimizer_seed"]),
        ): r
        for r in decision_grid
    }
    if len(grid_by_key) != EXPECTED_DECISIONS:
        raise RuntimeError("Duplicate frozen decision scientific key.")

    payload_by_id = {r["payload_id"]: r for r in payload_rows}
    if len(payload_by_id) != 6422:
        raise RuntimeError("Duplicate payload_id in payload manifest.")

    payload_dir = repo / PAYLOAD_DIR_REL
    for name, expected in PAYLOAD_PHYSICAL_HASHES.items():
        if sha256_file(payload_dir / name) != expected:
            raise RuntimeError(f"Frozen payload hash mismatch: {name}")

    time_values = np.load(
        payload_dir / "time_seconds.npy", mmap_mode="r", allow_pickle=False
    )
    offsets = np.load(
        payload_dir / "offsets.npy", mmap_mode="r", allow_pickle=False
    )

    grouped = defaultdict(dict)
    first_job_order = {}
    for r in results:
        key = (
            r["planned_decision_id"],
            r["variant_id"],
            int(r["external_optimizer_seed"]),
        )
        if r["model_id"] in grouped[key]:
            raise RuntimeError(f"Duplicate model in decision {key}")
        grouped[key][r["model_id"]] = r
        first_job_order.setdefault(key, int(r["job_order"]))

    if len(grouped) != EXPECTED_DECISIONS:
        raise RuntimeError(f"Expected 7,466 decision groups, got {len(grouped)}")

    decision_rows = []
    temporal_rows = []

    for key in sorted(grouped, key=lambda k: first_job_order[k]):
        trio = grouped[key]
        if set(trio) != {"M0", "M1", "M2"}:
            raise RuntimeError(f"Incomplete model trio: {key}")
        frozen = grid_by_key.get(key)
        if frozen is None:
            raise RuntimeError(f"Decision absent from frozen grid: {key}")

        b0 = float(trio["M0"]["bic"])
        b1 = float(trio["M1"]["bic"])
        b2 = float(trio["M2"]["bic"])
        if not all(math.isfinite(x) for x in (b0, b1, b2)):
            raise RuntimeError(f"Non-finite BIC in {key}")

        d01 = b0 - b1
        d21 = b2 - b1
        selected = selection_rule(b0, b1, b2)

        formal_raw = trio["M1"]["formal_m1_period_s"]
        formal = float(formal_raw) if formal_raw not in ("", None) else ""
        label = (
            "recovered_period_selected"
            if selected
            else "formal_m1_center_not_selected"
        )

        payload_id = frozen["payload_id"]
        payload = payload_by_id[payload_id]
        if payload["variant_id"] != frozen["variant_id"]:
            raise RuntimeError(f"Frozen payload/variant mismatch: {key}")

        decision_rows.append({
            "planned_decision_id": frozen["planned_decision_id"],
            "decision_order": frozen["decision_order"],
            "decision_class": frozen["decision_class"],
            "phase3a_event_id": frozen["phase3a_event_id"],
            "pair_id": frozen["pair_id"],
            "observational_reference_role":
                frozen["observational_reference_role"],
            "variant_id": frozen["variant_id"],
            "matrix_cell_id": frozen["matrix_cell_id"],
            "window_variant_id": frozen["window_variant_id"],
            "processing_profile_id": frozen["processing_profile_id"],
            "external_optimizer_seed": frozen["external_optimizer_seed"],
            "payload_id": payload_id,
            "payload_logical_sha256": frozen["payload_logical_sha256"],
            "input_n_samples": frozen["input_n_samples"],
            "bic_m0": b0,
            "bic_m1": b1,
            "bic_m2": b2,
            "delta_bic_0_1": d01,
            "delta_bic_2_1": d21,
            "qpp_selected": str(selected).lower(),
            "formal_m1_period_s": formal,
            "period_label": label,
            "decision_status": "VALID",
        })

        start = int(payload["offset"])
        length = int(payload["length"])
        end = start + length
        if int(offsets[int(payload["payload_id"].replace("F3APAY", "")) - 1]) != start:
            # The manifest remains authoritative; this is an additional structural check.
            raise RuntimeError(f"Payload offset ordering mismatch: {payload_id}")
        t = np.asarray(time_values[start:end], dtype=np.float64)
        if len(t) != length or len(t) < 2:
            raise RuntimeError(f"Temporal payload length invalid: {key}")
        diffs = np.diff(t)
        mean_dt = float(np.mean(diffs))
        median_dt = float(np.median(diffs))
        fft_pos = int(np.count_nonzero(np.fft.fftfreq(len(t), d=mean_dt) > 0.0))
        rfft_pos = int(
            np.count_nonzero(np.fft.rfftfreq(len(t), d=median_dt) > 0.0)
        )

        model_dt = {
            m: float(trio[m]["afino_effective_dt_s"])
            for m in ("M0", "M1", "M2")
        }
        model_bins = {
            m: int(trio[m]["positive_frequency_bin_count"])
            for m in ("M0", "M1", "M2")
        }
        mean_matches = {m: close(model_dt[m], mean_dt) for m in model_dt}
        fft_matches = {m: model_bins[m] == fft_pos for m in model_bins}
        legacy_median = all(close(model_dt[m], median_dt) for m in model_dt)
        legacy_rfft = all(model_bins[m] == rfft_pos for m in model_bins)

        temporal_rows.append({
            "planned_decision_id": frozen["planned_decision_id"],
            "decision_order": frozen["decision_order"],
            "variant_id": frozen["variant_id"],
            "external_optimizer_seed": frozen["external_optimizer_seed"],
            "payload_id": payload_id,
            "n_samples": len(t),
            "mean_dt_external": mean_dt,
            "median_dt_external": median_dt,
            "afino_dt_m0": model_dt["M0"],
            "afino_dt_m1": model_dt["M1"],
            "afino_dt_m2": model_dt["M2"],
            "mean_dt_match_m0": str(mean_matches["M0"]).lower(),
            "mean_dt_match_m1": str(mean_matches["M1"]).lower(),
            "mean_dt_match_m2": str(mean_matches["M2"]).lower(),
            "positive_fftfreq_bin_count_external": fft_pos,
            "rfftfreq_positive_bin_count_external": rfft_pos,
            "afino_bin_count_m0": model_bins["M0"],
            "afino_bin_count_m1": model_bins["M1"],
            "afino_bin_count_m2": model_bins["M2"],
            "fftfreq_positive_match":
                str(all(fft_matches.values())).lower(),
            "legacy_median_dt_match": str(legacy_median).lower(),
            "legacy_rfftfreq_match": str(legacy_rfft).lower(),
        })

    if len(decision_rows) != 7466 or len(temporal_rows) != 7466:
        raise RuntimeError("Full decision/temporal output row count mismatch.")

    actual_dt_matches = sum(
        r["mean_dt_match_m0"] == "true"
        and r["mean_dt_match_m1"] == "true"
        and r["mean_dt_match_m2"] == "true"
        for r in temporal_rows
    )
    actual_fft_matches = sum(
        r["fftfreq_positive_match"] == "true"
        for r in temporal_rows
    )
    if actual_dt_matches != 7466 or actual_fft_matches != 7466:
        raise RuntimeError(
            f"Actual temporal contract mismatch: "
            f"mean_dt={actual_dt_matches}/7466 "
            f"fftfreq={actual_fft_matches}/7466"
        )

    write_csv(repo / OUTPUT_DECISIONS_REL, decision_rows, DECISION_FIELDS)
    write_csv(repo / OUTPUT_TEMPORAL_REL, temporal_rows, TEMPORAL_FIELDS)

    print("PHASE3A_F3A4_FULL_DECISION_ASSEMBLY_PASS")
    print("full_result_rows=22398")
    print("full_decision_rows=7466")
    print("m0_rows=7466")
    print("m1_rows=7466")
    print("m2_rows=7466")
    print("decision_status_valid=7466")
    print(f"actual_mean_dt_contract_matches={actual_dt_matches}/7466")
    print(f"actual_positive_fftfreq_contract_matches={actual_fft_matches}/7466")
    print("scientific_summary_computed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
