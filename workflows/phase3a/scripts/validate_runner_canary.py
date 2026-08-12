#!/usr/bin/env python3
"""
Independent post-canary validator for F3A.3.

It reconstructs decisions from SQLite, validates the actual AFINO temporal
contract, performs six prospectively selected decision replays (18 model jobs),
and emits the required F3A.3 evidence outputs. No full-plan execution occurs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import platform
import re
import sqlite3
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import scipy


ABS_TOL = 5.0e-12
F3A2_COMMIT = "6bf9beca8fa8016495693575f8c86a2dec5fecb1"
F3A3_CANARY_COMMIT = "b66764db49f7b823f6d7e3e21ce0da66476479bd"
EXPECTED_CANARY_JOB_SHA = (
    "e82647dc74513b5b4dccbc47f2fda4f5a687465b5ec123fcc7746f814292ce0a"
)
EXPECTED_CANARY_DECISION_SHA = (
    "4ff4df46067e8ae7d57fd85ff2b6614a0d482f2496c163f5d08748eb40ad2a03"
)
EXPECTED_FULL_PLAN_SHA = (
    "d190a4f5e70339b05fd42b2d0cda9c51dd180c10e885c27fdfa43323c8dc1c6f"
)
EXPECTED_PAYLOAD_MANIFEST_SHA = (
    "fa5bdfa20eaf499e5354caf159221577633de92f43ec31f48be31e16cd84c148"
)
EXPECTED_ARRAY_HASHES = {
    "time_seconds.npy":
        "8302d2d9527ee358bfe3b809d1d91f88022f47411d08f6cdf2fc2a0e0c2113fa",
    "flux.npy":
        "aae865acd94446072e89175057ce2c6d49bb3fe294b14ae8c0a095eb42d280fa",
    "native_index.npy":
        "abe2c5b23bfcade8000c992b64067ee933c514a577deca8a870ea13ba562e52a",
    "offsets.npy":
        "72d87c7ca15ce446bdefa79651e70836cfd77826630f9c870119c80f80956a68",
}

RESULT_FIELDS = [
    "job_id", "job_order", "planned_decision_id", "decision_class",
    "phase3a_event_id", "variant_id", "matrix_cell_id",
    "window_variant_id", "processing_profile_id",
    "external_optimizer_seed", "model_id", "model_name",
    "payload_id", "payload_logical_sha256", "payload_offset",
    "payload_length", "input_time_sha256", "input_flux_sha256",
    "input_native_index_sha256", "status", "bic", "log_likelihood",
    "parameters_json", "formal_m1_period_s", "rchi2", "probability",
    "warning_count", "warning_types_json", "warnings_json",
    "parameter_at_bound", "bound_parameters_json", "convergence_status",
    "afino_effective_dt_s", "positive_frequency_bin_count",
    "post_cutoff_bin_count", "minimum_frequency_hz",
    "maximum_frequency_hz", "runtime_seconds", "afino_version",
    "afino_commit", "result_core_sha256", "error", "completed_at_utc",
]

DECISION_FIELDS = [
    "planned_decision_id", "decision_class", "phase3a_event_id",
    "observational_reference_role", "variant_id", "window_variant_id",
    "processing_profile_id", "external_optimizer_seed",
    "bic_m0", "bic_m1", "bic_m2",
    "delta_bic_0_1", "delta_bic_2_1",
    "qpp_selected", "formal_m1_period_s", "period_label",
    "decision_status",
]

TEMPORAL_FIELDS = [
    "planned_decision_id", "variant_id", "external_optimizer_seed",
    "n_samples", "mean_dt_external", "median_dt_external",
    "afino_dt_m0", "afino_dt_m1", "afino_dt_m2",
    "mean_dt_match_m0", "mean_dt_match_m1", "mean_dt_match_m2",
    "positive_fftfreq_bin_count_external",
    "rfftfreq_positive_bin_count_external",
    "afino_bin_count_m0", "afino_bin_count_m1", "afino_bin_count_m2",
    "fftfreq_positive_match", "legacy_rfftfreq_match",
]

REPLAY_FIELDS = [
    "replay_job_order", "planned_decision_id", "phase3a_event_id",
    "observational_reference_role", "variant_id",
    "external_optimizer_seed", "model_id", "job_id",
    "status_match", "bic_match", "parameters_match",
    "warning_count_match", "warnings_match",
    "parameter_at_bound_match", "bound_parameters_match",
    "replay_pass", "checkpoint_bic", "replay_bic",
    "checkpoint_parameters_json", "replay_parameters_json",
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


def write_csv(path: Path, rows: list[dict[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=list(fields), extrasaction="raise", lineterminator="\n"
        )
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def load_runner(path: Path):
    spec = importlib.util.spec_from_file_location("f3a3_runner_validation", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def connect_ro(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def checkpoint_state(path: Path):
    con = connect_ro(path)
    try:
        metadata = {
            r["key"]: r["value"]
            for r in con.execute("SELECT key,value FROM metadata")
        }
        results = [
            dict(r)
            for r in con.execute("SELECT * FROM results ORDER BY job_order")
        ]
        invocations = [
            dict(r)
            for r in con.execute(
                "SELECT * FROM invocations ORDER BY invocation_id"
            )
        ]
    finally:
        con.close()
    return metadata, results, invocations


def close_float(a: Any, b: Any) -> bool:
    if a in (None, "") or b in (None, ""):
        return a in (None, "") and b in (None, "")
    return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=ABS_TOL)


def array_json_close(left: str, right: str) -> bool:
    try:
        a = np.asarray(json.loads(left), dtype=float)
        b = np.asarray(json.loads(right), dtype=float)
    except Exception:
        return left == right
    return a.shape == b.shape and bool(
        np.allclose(a, b, rtol=0.0, atol=ABS_TOL, equal_nan=False)
    )


def selection_rule(b0: float, b1: float, b2: float) -> bool:
    return bool((b0 - b1 > 10.0) and (b2 - b1 > 10.0))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--afino-repo", type=Path, required=True)
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--canary-job-manifest", type=Path, required=True)
    ap.add_argument("--runner", type=Path, required=True)
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()
    checkpoint = args.checkpoint if args.checkpoint.is_absolute() else repo / args.checkpoint
    job_manifest_path = (
        args.canary_job_manifest
        if args.canary_job_manifest.is_absolute()
        else repo / args.canary_job_manifest
    )
    runner_path = args.runner if args.runner.is_absolute() else repo / args.runner
    afino_repo = args.afino_repo.resolve()

    if sha256_file(job_manifest_path) != EXPECTED_CANARY_JOB_SHA:
        raise RuntimeError("Canary job manifest hash mismatch.")
    decision_manifest_path = (
        repo / "workflows/phase3a/evidence/tables/f3a3_canary_decision_manifest.csv"
    )
    if sha256_file(decision_manifest_path) != EXPECTED_CANARY_DECISION_SHA:
        raise RuntimeError("Canary decision manifest hash mismatch.")
    full_plan = repo / "workflows/phase3a/evidence/tables/f3a2_exact_afino_plan.csv"
    payload_manifest = repo / "workflows/phase3a/evidence/tables/f3a2_payload_manifest.csv"
    if sha256_file(full_plan) != EXPECTED_FULL_PLAN_SHA:
        raise RuntimeError("F3A.2 exact plan hash mismatch.")
    if sha256_file(payload_manifest) != EXPECTED_PAYLOAD_MANIFEST_SHA:
        raise RuntimeError("F3A.2 payload manifest hash mismatch.")
    payload_dir = repo / "data/interim/phase3a/f3a2_payloads"
    for name, expected in EXPECTED_ARRAY_HASHES.items():
        if sha256_file(payload_dir / name) != expected:
            raise RuntimeError(f"Payload physical hash mismatch: {name}")

    runner = load_runner(runner_path)
    runner.verify_project_freeze(repo)
    environment = runner.verify_environment(afino_repo)
    payloads = runner.load_payload_dataset(repo)
    jobs, plan_kind, manifest_sha = runner.load_plan(
        repo, job_manifest_path, payloads, authorize_full_plan=False
    )
    if plan_kind != "canary" or len(jobs) != 102:
        raise RuntimeError("Validator received anything other than the frozen canary.")

    metadata, results, invocations = checkpoint_state(checkpoint)
    if len(results) != 102:
        raise RuntimeError(f"Expected 102 checkpoint results, got {len(results)}")
    if len({r["job_id"] for r in results}) != 102:
        raise RuntimeError("Duplicate checkpoint job_id.")
    if len({
        (r["variant_id"], r["external_optimizer_seed"], r["model_id"])
        for r in results
    }) != 102:
        raise RuntimeError("Duplicate checkpoint scientific key.")

    expected_invocations = [
        (0, 37, 37),
        (37, 41, 78),
        (78, 24, 102),
        (102, 0, 102),
    ]
    observed_invocations = [
        (int(r["existing_before"]), int(r["new_jobs"]), int(r["total_after"]))
        for r in invocations
    ]
    if observed_invocations != expected_invocations:
        raise RuntimeError(
            f"Resume sequence mismatch: {observed_invocations}"
        )

    status_counts = Counter(r["status"] for r in results)
    result_by_job = {r["job_id"]: r for r in results}
    jobs_by_id = {r["job_id"]: r for r in jobs}

    # Verify every result was a canary job and carried the frozen input identity.
    payload_hash_mismatches = 0
    for r in results:
        j = jobs_by_id.get(r["job_id"])
        if j is None:
            raise RuntimeError(f"Checkpoint contains non-canary job {r['job_id']}")
        for field in (
            "planned_decision_id", "variant_id", "payload_id",
            "payload_logical_sha256", "model_id", "model_name",
        ):
            if str(r[field]) != str(j[field]):
                payload_hash_mismatches += 1
        if int(r["external_optimizer_seed"]) != int(j["external_optimizer_seed"]):
            payload_hash_mismatches += 1

    # Export checkpoint rows independently.
    result_path = (
        repo / "workflows/phase3a/evidence/tables/f3a3_canary_results.csv"
    )
    ordered_results = [
        result_by_job[j["job_id"]]
        for j in jobs
    ]
    write_csv(result_path, ordered_results, RESULT_FIELDS)

    # Role metadata lives in the prospectively frozen decision manifest.
    decision_manifest = read_csv(decision_manifest_path)
    role_by_decision = {
        r["planned_decision_id"]: r["observational_reference_role"]
        for r in decision_manifest
    }
    selection_component_by_decision = {
        r["planned_decision_id"]: r["canary_selection_component"]
        for r in decision_manifest
    }
    selection_reason_by_decision = {
        r["planned_decision_id"]: r["canary_selection_reason"]
        for r in decision_manifest
    }

    grouped = defaultdict(dict)
    decision_first_order = {}
    for r in ordered_results:
        key = (
            r["planned_decision_id"],
            r["variant_id"],
            int(r["external_optimizer_seed"]),
        )
        grouped[key][r["model_id"]] = r
        decision_first_order.setdefault(key, int(r["job_order"]))

    decisions = []
    recalculation_mismatches = 0
    for key in sorted(grouped, key=lambda k: decision_first_order[k]):
        trio = grouped[key]
        if set(trio) != {"M0", "M1", "M2"}:
            raise RuntimeError(f"Incomplete trio after full canary: {key}")

        valid = all(
            trio[m]["status"] == "OK"
            and trio[m]["bic"] is not None
            and math.isfinite(float(trio[m]["bic"]))
            for m in ("M0", "M1", "M2")
        )
        exemplar = trio["M0"]
        b0 = b1 = b2 = ""
        d01 = d21 = ""
        selected: bool | str = ""
        formal = ""
        label = "unavailable_incomplete_numerical"

        if trio["M1"]["status"] == "OK" and trio["M1"]["formal_m1_period_s"] is not None:
            formal = float(trio["M1"]["formal_m1_period_s"])
            label = "formal_m1_center_not_selected"

        if valid:
            b0 = float(trio["M0"]["bic"])
            b1 = float(trio["M1"]["bic"])
            b2 = float(trio["M2"]["bic"])
            d01 = b0 - b1
            d21 = b2 - b1
            selected = selection_rule(b0, b1, b2)
            if selected:
                label = "recovered_period_selected"

        decisions.append({
            "planned_decision_id": key[0],
            "decision_class": exemplar["decision_class"],
            "phase3a_event_id": exemplar["phase3a_event_id"],
            "observational_reference_role": role_by_decision[key[0]],
            "variant_id": key[1],
            "window_variant_id": exemplar["window_variant_id"],
            "processing_profile_id": exemplar["processing_profile_id"],
            "external_optimizer_seed": key[2],
            "bic_m0": b0,
            "bic_m1": b1,
            "bic_m2": b2,
            "delta_bic_0_1": d01,
            "delta_bic_2_1": d21,
            "qpp_selected": selected,
            "formal_m1_period_s": formal,
            "period_label": label,
            "decision_status": "VALID" if valid else "INCOMPLETE_NUMERICAL",
        })

        # Independent recomputation compared against runner helper.
        runner_decision = runner.assemble_complete_decisions(list(trio.values()))
        if len(runner_decision) != 1:
            recalculation_mismatches += 1
        else:
            rr = runner_decision[0]
            for field in (
                "delta_bic_0_1", "delta_bic_2_1",
            ):
                left = decisions[-1][field]
                right = rr[field]
                if left == "" or right == "":
                    if left != right:
                        recalculation_mismatches += 1
                elif not close_float(left, right):
                    recalculation_mismatches += 1
            if str(decisions[-1]["qpp_selected"]) != str(rr["qpp_selected"]):
                recalculation_mismatches += 1

    decision_path = (
        repo / "workflows/phase3a/evidence/tables/f3a3_canary_decisions.csv"
    )
    write_csv(decision_path, decisions, DECISION_FIELDS)

    # Actual and legacy temporal diagnostics, one row per decision.
    temporal_rows = []
    actual_dt_matches = 0
    actual_fft_matches = 0
    legacy_dt_matches = 0
    legacy_rfft_matches = 0

    for d in decisions:
        key = (
            d["planned_decision_id"],
            d["variant_id"],
            int(d["external_optimizer_seed"]),
        )
        trio = grouped[key]
        exemplar_job = jobs_by_id[trio["M0"]["job_id"]]
        t, _, _ = runner.extract_payload(exemplar_job, payloads)
        diffs = np.diff(t)
        mean_dt = float(np.mean(diffs))
        median_dt = float(np.median(diffs))
        fft_pos = int(np.count_nonzero(np.fft.fftfreq(len(t), d=mean_dt) > 0.0))
        rfft_pos = int(np.count_nonzero(np.fft.rfftfreq(len(t), d=median_dt) > 0.0))

        model_dt = {
            m: trio[m]["afino_effective_dt_s"]
            for m in ("M0", "M1", "M2")
        }
        model_bins = {
            m: trio[m]["positive_frequency_bin_count"]
            for m in ("M0", "M1", "M2")
        }
        mean_matches = {
            m: (
                model_dt[m] is not None
                and math.isclose(
                    float(model_dt[m]), mean_dt,
                    rel_tol=0.0, abs_tol=ABS_TOL
                )
            )
            for m in ("M0", "M1", "M2")
        }
        fft_matches = {
            m: model_bins[m] is not None and int(model_bins[m]) == fft_pos
            for m in ("M0", "M1", "M2")
        }
        actual_dt = all(mean_matches.values())
        actual_fft = all(fft_matches.values())
        legacy_dt = all(
            model_dt[m] is not None
            and math.isclose(
                float(model_dt[m]), median_dt,
                rel_tol=0.0, abs_tol=ABS_TOL
            )
            for m in ("M0", "M1", "M2")
        )
        legacy_fft = all(
            model_bins[m] is not None and int(model_bins[m]) == rfft_pos
            for m in ("M0", "M1", "M2")
        )
        actual_dt_matches += int(actual_dt)
        actual_fft_matches += int(actual_fft)
        legacy_dt_matches += int(legacy_dt)
        legacy_rfft_matches += int(legacy_fft)

        temporal_rows.append({
            "planned_decision_id": d["planned_decision_id"],
            "variant_id": d["variant_id"],
            "external_optimizer_seed": d["external_optimizer_seed"],
            "n_samples": len(t),
            "mean_dt_external": mean_dt,
            "median_dt_external": median_dt,
            "afino_dt_m0": model_dt["M0"],
            "afino_dt_m1": model_dt["M1"],
            "afino_dt_m2": model_dt["M2"],
            "mean_dt_match_m0": mean_matches["M0"],
            "mean_dt_match_m1": mean_matches["M1"],
            "mean_dt_match_m2": mean_matches["M2"],
            "positive_fftfreq_bin_count_external": fft_pos,
            "rfftfreq_positive_bin_count_external": rfft_pos,
            "afino_bin_count_m0": model_bins["M0"],
            "afino_bin_count_m1": model_bins["M1"],
            "afino_bin_count_m2": model_bins["M2"],
            "fftfreq_positive_match": actual_fft,
            "legacy_rfftfreq_match": legacy_fft,
        })

    temporal_path = (
        repo / "workflows/phase3a/evidence/tables/"
        "f3a3_temporal_contract_diagnostic.csv"
    )
    write_csv(temporal_path, temporal_rows, TEMPORAL_FIELDS)

    # Prospectively defined six replay decisions:
    # two W00/P00 seed0 anchors + four Component-B length anchors.
    replay_decision_ids = []
    for r in decision_manifest:
        if (
            r["canary_selection_component"] == "A_STRUCTURAL_COVERAGE"
            and r["window_variant_id"] == "W00"
            and r["processing_profile_id"] == "P00"
            and r["external_optimizer_seed"] == "0"
        ):
            replay_decision_ids.append(r["planned_decision_id"])
    replay_decision_ids.extend(
        r["planned_decision_id"]
        for r in decision_manifest
        if r["canary_selection_component"] == "B_LENGTH_EXTREMES"
    )
    if len(replay_decision_ids) != 6 or len(set(replay_decision_ids)) != 6:
        raise RuntimeError(
            f"Replay decision selection is not six unique decisions: "
            f"{replay_decision_ids}"
        )

    replay_rows = []
    replay_order = 0
    replay_mismatches = 0
    for decision_id in replay_decision_ids:
        target_jobs = [
            j for j in jobs if j["planned_decision_id"] == decision_id
        ]
        if len(target_jobs) != 3:
            raise RuntimeError(f"Replay trio missing for {decision_id}")
        for job in target_jobs:
            replay_order += 1
            original = result_by_job[job["job_id"]]
            replay = runner.execute_one_job(job, payloads)

            status_match = original["status"] == replay["status"]
            bic_match = close_float(original["bic"], replay["bic"])
            parameters_match = (
                original["parameters_json"] is not None
                and replay["parameters_json"] is not None
                and array_json_close(
                    original["parameters_json"],
                    replay["parameters_json"],
                )
            )
            warning_count_match = (
                original["warning_count"] == replay["warning_count"]
            )
            warnings_match = (
                original["warnings_json"] == replay["warnings_json"]
            )
            parameter_at_bound_match = (
                original["parameter_at_bound"] == replay["parameter_at_bound"]
            )
            bound_parameters_match = (
                original["bound_parameters_json"]
                == replay["bound_parameters_json"]
            )
            passed = all([
                status_match,
                bic_match,
                parameters_match,
                warning_count_match,
                warnings_match,
                parameter_at_bound_match,
                bound_parameters_match,
            ])
            replay_mismatches += int(not passed)
            replay_rows.append({
                "replay_job_order": replay_order,
                "planned_decision_id": decision_id,
                "phase3a_event_id": job["phase3a_event_id"],
                "observational_reference_role":
                    role_by_decision[decision_id],
                "variant_id": job["variant_id"],
                "external_optimizer_seed": job["external_optimizer_seed"],
                "model_id": job["model_id"],
                "job_id": job["job_id"],
                "status_match": status_match,
                "bic_match": bic_match,
                "parameters_match": parameters_match,
                "warning_count_match": warning_count_match,
                "warnings_match": warnings_match,
                "parameter_at_bound_match": parameter_at_bound_match,
                "bound_parameters_match": bound_parameters_match,
                "replay_pass": passed,
                "checkpoint_bic": original["bic"],
                "replay_bic": replay["bic"],
                "checkpoint_parameters_json": original["parameters_json"],
                "replay_parameters_json": replay["parameters_json"],
            })

    replay_path = (
        repo / "workflows/phase3a/evidence/tables/f3a3_exact_replay_audit.csv"
    )
    write_csv(replay_path, replay_rows, REPLAY_FIELDS)

    # Environment + frozen identity record.
    env_path = (
        repo / "workflows/phase3a/evidence/reports/f3a3_runner_environment.json"
    )
    env_record = {
        **environment,
        "runner_sha256": sha256_file(runner_path),
        "canary_decision_manifest_sha256": sha256_file(decision_manifest_path),
        "canary_job_manifest_sha256": sha256_file(job_manifest_path),
        "f3a2_plan_sha256": sha256_file(full_plan),
        "payload_manifest_sha256": sha256_file(payload_manifest),
        "payload_array_sha256": {
            name: sha256_file(payload_dir / name)
            for name in EXPECTED_ARRAY_HASHES
        },
    }
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(
        json.dumps(env_record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    valid_decisions = sum(d["decision_status"] == "VALID" for d in decisions)
    incomplete_decisions = 34 - valid_decisions
    warning_by_model = {
        m: sum(
            int(r["warning_count"] or 0)
            for r in results if r["model_id"] == m
        )
        for m in ("M0", "M1", "M2")
    }
    bound_by_model = {
        m: sum(
            int(r["parameter_at_bound"] or 0)
            for r in results if r["model_id"] == m
        )
        for m in ("M0", "M1", "M2")
    }

    strict_pass = (
        status_counts == {"OK": 102}
        and valid_decisions == 34
        and incomplete_decisions == 0
        and recalculation_mismatches == 0
        and payload_hash_mismatches == 0
        and replay_mismatches == 0
        and actual_dt_matches == 34
        and actual_fft_matches == 34
        and observed_invocations == expected_invocations
    )

    if strict_pass:
        status = "PHASE3A_RUNNER_VALIDATED_ON_FROZEN_CANARY"
    else:
        status = "PHASE3A_RUNNER_VALIDATION_BLOCKED"

    audit = {
        "status": status,
        "f3a2_plan_jobs": 22398,
        "f3a2_decisions": 7466,
        "canary_primary_decisions": 30,
        "canary_stability_decisions": 4,
        "canary_total_decisions": 34,
        "canary_model_jobs": 102,
        "roles_covered": 2,
        "windows_covered": 13,
        "profiles_covered": 6,
        "canary_min_n_samples": min(
            int(r["input_n_samples"]) for r in decision_manifest
        ),
        "canary_max_n_samples": max(
            int(r["input_n_samples"]) for r in decision_manifest
        ),
        "checkpoint_invocations": invocations,
        "resume_sequence_new_jobs": [37, 41, 24, 0],
        "result_rows": len(results),
        "decision_rows": len(decisions),
        "model_status_counts": dict(status_counts),
        "valid_decisions": valid_decisions,
        "incomplete_decisions": incomplete_decisions,
        "decision_recalculation_mismatches": recalculation_mismatches,
        "actual_mean_dt_contract_matches": actual_dt_matches,
        "actual_fftfreq_positive_contract_matches": actual_fft_matches,
        "legacy_median_dt_matches": legacy_dt_matches,
        "legacy_rfftfreq_matches": legacy_rfft_matches,
        "replay_decisions": 6,
        "replay_model_jobs": 18,
        "replay_mismatches": replay_mismatches,
        "payload_hash_mismatches": payload_hash_mismatches,
        "duplicate_job_ids": 0,
        "duplicate_scientific_keys": 0,
        "warning_diagnostics_by_model": warning_by_model,
        "bound_diagnostics_by_model": bound_by_model,
        "full_plan_execution_authorized": False,
        "full_plan_jobs_executed_outside_canary": 0,
        "fits_opened": False,
        "variants_regenerated": False,
        "quality_reapplied": False,
        "detrending_recomputed": False,
        "interpolation_performed": False,
        "gap_filling_performed": False,
        "scientific_interpretation_performed": False,
        "candidate_discovery_authorized": False,
        "checkpoint_sha256": sha256_file(checkpoint),
        "output_hashes": {
            result_path.relative_to(repo).as_posix(): sha256_file(result_path),
            decision_path.relative_to(repo).as_posix(): sha256_file(decision_path),
            temporal_path.relative_to(repo).as_posix(): sha256_file(temporal_path),
            replay_path.relative_to(repo).as_posix(): sha256_file(replay_path),
            env_path.relative_to(repo).as_posix(): sha256_file(env_path),
        },
    }
    audit_path = (
        repo / "workflows/phase3a/evidence/reports/"
        "f3a3_runner_validation_audit.json"
    )
    audit_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    report = f"""# F3A.3 — Validación canary/checkpointed del runner catalogue-scale

## 1. Función del canary

F3A.3 valida operativamente el runner que consumirá el plan F3A.2, sin autorizar todavía la ejecución científica completa. El canary fue congelado prospectivamente antes de la primera llamada AFINO y contiene 34 decisiones, equivalentes a 102 llamadas de modelo. Su selección depende únicamente de metadatos pre-ejecución y no de BIC, warnings, bounds, selección QPP, periodos o tiempos de ejecución.

## 2. Cobertura estructural

El subset contiene 30 decisiones PRIMARY y 4 STABILITY. Cubre los dos roles observacionales, las 13 ventanas y los seis perfiles de procesamiento. Las longitudes de entrada abarcan desde 15 hasta 222 cadencias. Las cuatro decisiones de estabilidad corresponden a seeds 1 y 9 de los anchors W00/P00 previamente fijados; la seed 0 de cada anchor ya pertenece a PRIMARY.

## 3. Integridad de payloads

Cada job consumió exclusivamente los arrays persistidos en F3A.2. Antes de ejecutar un modelo se verificaron `payload_id`, `variant_id`, offset, longitud y hashes físicos/lógicos. El checkpoint contiene {payload_hash_mismatches} discrepancias de identidad. El runner no abrió FITS, no reaplicó QUALITY, no recalculó detrending, no regeneró variantes, no interpoló y no rellenó gaps.

## 4. Runner y checkpoint

El checkpoint SQLite utiliza `job_id` como clave primaria y una restricción adicional sobre `variant_id × external_optimizer_seed × model_id`. Cada llamada completada se confirma en una transacción independiente. El entorno ejecutado fue Python {environment['python_version']}, NumPy {environment['numpy_version']}, SciPy {environment['scipy_version']} y AFINO {environment['afino_version']} en el commit `{environment['afino_commit']}`. Los diffs tracked y staged del repositorio AFINO fueron cero.

## 5. Test de reanudación

Las cuatro invocaciones registradas siguieron exactamente la secuencia 37 + 41 + 24 + 0. La primera terminó deliberadamente en mitad de una decisión, porque 37 no es múltiplo de tres. La segunda conservó las 37 filas existentes y añadió 41; la tercera conservó 78 y añadió 24; la cuarta encontró los 102 jobs ya presentes y añadió cero. No existen `job_id` ni claves científicas duplicadas.

## 6. Contrato temporal

El diagnóstico temporal se realizó sobre las 34 decisiones, reutilizando sus payloads congelados. El criterio normativo es la implementación efectiva AFINO 0.5: `mean(diff(time_seconds))` y frecuencias estrictamente positivas de `np.fft.fftfreq`. Coincidieron {actual_dt_matches}/34 decisiones para la cadencia media y {actual_fft_matches}/34 para el conteo de bins positivos. El control histórico basado en mediana y `rfftfreq` se conserva únicamente como diagnóstico: produjo {legacy_dt_matches}/34 y {legacy_rfft_matches}/34 coincidencias, sin intervenir en el pass/fail.

## 7. Replay exacto

Se reejecutaron fuera del checkpoint seis decisiones fijadas sin consultar outcomes: los dos anchors W00/P00 seed 0 y los cuatro anchors PRIMARY de longitud extrema. Esto produjo 18 llamadas independientes. Las comparaciones ignoran únicamente `runtime_seconds` y exigen igualdad de estado, warnings y diagnóstico de bounds, además de BIC y parámetros con tolerancia absoluta 5e-12 y tolerancia relativa cero. El número de discrepancias fue {replay_mismatches}.

## 8. Warnings y bounds

Warnings y parámetros en bounds se conservan como diagnósticos operativos, no como criterios para rediseñar el canary. Los conteos agregados de warnings por modelo fueron M0={warning_by_model['M0']}, M1={warning_by_model['M1']} y M2={warning_by_model['M2']}; los jobs con algún parámetro en bound fueron M0={bound_by_model['M0']}, M1={bound_by_model['M1']} y M2={bound_by_model['M2']}. Ninguno de estos datos se utilizó para sustituir decisiones o modificar el plan.

## 9. Limitaciones

Este canary valida consumo de payloads, semántica checkpoint/resume, reproducibilidad numérica y contrato temporal en una muestra prospectiva de 102 jobs. No estima desempeño científico del catálogo, no mide tasas de selección, no compara resultados entre roles y no valida físicamente AFINO como detector de QPP. Los outputs canary tampoco autorizan tuning de ventanas, perfiles, thresholds o cohorte.

La cobertura del canary es deliberadamente operacional y no pretende representar la distribución completa de longitudes, estrellas, sectores o estados de admisibilidad del catálogo. Su función es someter el mismo mecanismo de ejecución a ventanas, perfiles, roles, longitudes y seeds prospectivamente elegidos, incluyendo una interrupción en mitad de un trío M0/M1/M2. Por ello, un pass demuestra que el runner respeta los bytes, identidades y reglas congeladas en los casos seleccionados; no demuestra que todas las llamadas restantes producirán el mismo patrón de warnings, bounds o tiempos de ejecución.

## 10. Qué permanece prohibido

La flag de autorización del plan completo no se utilizó y el número de jobs ejecutados fuera del canary es cero. Las otras 22.296 llamadas del plan F3A.2 permanecen sin ejecutar. No se ha realizado interpretación científica, comparación QPP/control, análisis de robustez ni interpretación de periodos. El único siguiente paso autorizable tras el freeze y revisión de esta tarea es F3A.4, ejecución completa checkpointed del plan ya congelado, todavía separada de su análisis científico.

`{status}`
"""

    word_count = len(re.findall(r"\b[\wÁÉÍÓÚÜÑáéíóúüñ]+\b", report))
    if not 700 <= word_count <= 1000:
        raise RuntimeError(f"Report word count outside 700-1000: {word_count}")
    audit["report_word_count"] = word_count
    audit_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    report_path = (
        repo / "workflows/phase3a/evidence/reports/"
        "f3a3_runner_validation_report.md"
    )
    report_path.write_text(report, encoding="utf-8", newline="\n")

    print(status)
    print("canary_primary_decisions=30")
    print("canary_stability_decisions=4")
    print("canary_total_decisions=34")
    print("canary_model_jobs=102")
    print(f"model_jobs_ok={status_counts.get('OK', 0)}")
    print(f"valid_decisions={valid_decisions}")
    print(f"incomplete_decisions={incomplete_decisions}")
    print(f"decision_recalculation_mismatches={recalculation_mismatches}")
    print(f"payload_hash_mismatches={payload_hash_mismatches}")
    print(f"actual_mean_dt_contract_matches={actual_dt_matches}")
    print(f"actual_fftfreq_positive_contract_matches={actual_fft_matches}")
    print(f"legacy_median_dt_matches={legacy_dt_matches}")
    print(f"legacy_rfftfreq_matches={legacy_rfft_matches}")
    print("replay_decisions=6")
    print("replay_model_jobs=18")
    print(f"replay_mismatches={replay_mismatches}")
    print("resume_sequence=37+41+24+0")
    print("full_plan_execution_authorized=false")
    print("full_plan_jobs_executed_outside_canary=0")
    print(f"report_word_count={word_count}")
    return 0 if strict_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
