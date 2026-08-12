#!/usr/bin/env python3
"""
F3A.4 independent structural validator.

Does not import AFINO and does not open FITS. It validates one-to-one plan,
checkpoint and CSV identity; canary preservation; 7,466 reconstructed decisions;
the effective temporal contract; operational diagnostics by model only; and
scientific-boundary flags.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import sqlite3
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import scipy

F3A2_COMMIT = "6bf9beca8fa8016495693575f8c86a2dec5fecb1"
F3A3_RUNNER_COMMIT = "0738b1cc132598119dcbbc27b4113c93ae9d2733"
EXPECTED_RUNNER_SHA = (
    "0de4b1b3745e7c7b237ff82680dd8f6cb8e2bf1288c58fd07d1624ca034558db"
)
EXPECTED_PLAN_SHA = (
    "d190a4f5e70339b05fd42b2d0cda9c51dd180c10e885c27fdfa43323c8dc1c6f"
)
EXPECTED_PAYLOAD_MANIFEST_SHA = (
    "fa5bdfa20eaf499e5354caf159221577633de92f43ec31f48be31e16cd84c148"
)
EXPECTED_CANARY_CHECKPOINT_SHA = (
    "9781b13889d2a66e33be973f555b081f5d4de6d97c155a73fd93f5118d2073ca"
)
EXPECTED_AFINO_COMMIT = "6aceac9518fc8056052807e666da9d0c8bebb010"
ABS_TOL = 5.0e-12

PAYLOAD_HASHES = {
    "time_seconds.npy":
        "8302d2d9527ee358bfe3b809d1d91f88022f47411d08f6cdf2fc2a0e0c2113fa",
    "flux.npy":
        "aae865acd94446072e89175057ce2c6d49bb3fe294b14ae8c0a095eb42d280fa",
    "native_index.npy":
        "abe2c5b23bfcade8000c992b64067ee933c514a577deca8a870ea13ba562e52a",
    "offsets.npy":
        "72d87c7ca15ce446bdefa79651e70836cfd77826630f9c870119c80f80956a68",
}

AUTH_REL = Path("workflows/phase3a/config/f3a4_full_execution_authorization.json")
RUNNER_REL = Path("workflows/phase3a/scripts/run_afino_checkpointed.py")
BOOTSTRAP_REL = Path("workflows/phase3a/scripts/bootstrap_full_checkpoint.py")
ASSEMBLER_REL = Path("workflows/phase3a/scripts/assemble_full_decisions.py")
VALIDATOR_REL = Path("workflows/phase3a/scripts/validate_full_execution.py")
TEST_REL = Path("workflows/phase3a/tests/test_f3a4_full_execution_contract.py")

PLAN_REL = Path("workflows/phase3a/evidence/tables/f3a2_exact_afino_plan.csv")
GRID_REL = Path("workflows/phase3a/evidence/tables/f3a2_resolved_decision_grid.csv")
PAYLOAD_MANIFEST_REL = Path(
    "workflows/phase3a/evidence/tables/f3a2_payload_manifest.csv"
)
PAYLOAD_DIR_REL = Path("data/interim/phase3a/f3a2_payloads")

BOOTSTRAP_AUDIT_REL = Path(
    "workflows/phase3a/evidence/tables/f3a4_canary_bootstrap_audit.csv"
)
RESULTS_REL = Path("workflows/phase3a/evidence/tables/f3a4_full_results.csv")
DECISIONS_REL = Path("workflows/phase3a/evidence/tables/f3a4_full_decisions.csv")
TEMPORAL_REL = Path(
    "workflows/phase3a/evidence/tables/f3a4_temporal_contract_diagnostic.csv"
)
ENV_REL = Path(
    "workflows/phase3a/evidence/reports/f3a4_execution_environment.json"
)
AUDIT_REL = Path(
    "workflows/phase3a/evidence/reports/f3a4_full_execution_audit.json"
)
REPORT_REL = Path(
    "workflows/phase3a/evidence/reports/f3a4_full_execution_report.md"
)
SUMS_REL = Path("workflows/phase3a/evidence/f3a4_SHA256SUMS.txt")

CANARY_CHECKPOINT_REL = Path("runtime/phase3a/f3a3/canary_checkpoint.sqlite")
FULL_CHECKPOINT_REL = Path("runtime/phase3a/f3a4/full_checkpoint.sqlite")

GIT_OUTPUTS = [
    AUTH_REL,
    BOOTSTRAP_REL,
    ASSEMBLER_REL,
    VALIDATOR_REL,
    TEST_REL,
    BOOTSTRAP_AUDIT_REL,
    RESULTS_REL,
    DECISIONS_REL,
    TEMPORAL_REL,
    ENV_REL,
    AUDIT_REL,
    REPORT_REL,
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


def git(repo: Path, *args: str, check=True):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def connect_ro(path: Path):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def close_float(a: Any, b: Any) -> bool:
    if a in (None, "") or b in (None, ""):
        return a in (None, "") and b in (None, "")
    return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=ABS_TOL)


def bool_text(value: Any) -> bool:
    return str(value).lower() in {"true", "1"}


def expected_invocations():
    return [
        (0, 0, 0, 22398),      # initialization before canary import
        (102, 3000, 3102, 19296),
        (3102, 3000, 6102, 16296),
        (6102, 3000, 9102, 13296),
        (9102, 3000, 12102, 10296),
        (12102, 3000, 15102, 7296),
        (15102, 3000, 18102, 4296),
        (18102, 3000, 21102, 1296),
        (21102, 1296, 22398, 0),
        (22398, 0, 22398, 0),
    ]


def verify_checkpoint_metadata(metadata: dict[str, str]) -> None:
    required = {
        "plan_kind": "full",
        "f3a2_commit": F3A2_COMMIT,
        "full_plan_sha256": EXPECTED_PLAN_SHA,
        "payload_manifest_sha256": EXPECTED_PAYLOAD_MANIFEST_SHA,
        "runner_sha256": EXPECTED_RUNNER_SHA,
        "afino_version": "0.5",
        "afino_commit": EXPECTED_AFINO_COMMIT,
    }
    for key, expected in required.items():
        if metadata.get(key) != expected:
            raise RuntimeError(
                f"Full checkpoint metadata mismatch {key}: "
                f"{metadata.get(key)!r} != {expected!r}"
            )
    # Historical runner stores the selected manifest hash under this legacy key.
    if metadata.get("canary_manifest_sha256") != EXPECTED_PLAN_SHA:
        raise RuntimeError("Full checkpoint selected-manifest hash mismatch.")


def checkpoint_content(path: Path):
    con = connect_ro(path)
    try:
        metadata = dict(con.execute("SELECT key,value FROM metadata").fetchall())
        results = [
            dict(r) for r in con.execute("SELECT * FROM results ORDER BY job_order")
        ]
        invocations = [
            tuple(r) for r in con.execute(
                """
                SELECT existing_before,new_jobs,total_after,pending_after
                FROM invocations ORDER BY invocation_id
                """
            ).fetchall()
        ]
    finally:
        con.close()
    return metadata, results, invocations


def decision_recalculation(results, frozen_grid, decisions):
    grouped = defaultdict(dict)
    for r in results:
        key = (
            r["planned_decision_id"],
            r["variant_id"],
            int(r["external_optimizer_seed"]),
        )
        grouped[key][r["model_id"]] = r

    decision_by_key = {
        (
            r["planned_decision_id"],
            r["variant_id"],
            int(r["external_optimizer_seed"]),
        ): r
        for r in decisions
    }
    grid_by_key = {
        (
            r["planned_decision_id"],
            r["variant_id"],
            int(r["external_optimizer_seed"]),
        ): r
        for r in frozen_grid
    }

    mismatches = 0
    for key, trio in grouped.items():
        if set(trio) != {"M0", "M1", "M2"}:
            mismatches += 1
            continue
        out = decision_by_key.get(key)
        frozen = grid_by_key.get(key)
        if out is None or frozen is None:
            mismatches += 1
            continue
        b0 = float(trio["M0"]["bic"])
        b1 = float(trio["M1"]["bic"])
        b2 = float(trio["M2"]["bic"])
        d01 = b0 - b1
        d21 = b2 - b1
        selected = (d01 > 10.0 and d21 > 10.0)

        if not close_float(out["bic_m0"], b0):
            mismatches += 1
        if not close_float(out["bic_m1"], b1):
            mismatches += 1
        if not close_float(out["bic_m2"], b2):
            mismatches += 1
        if not close_float(out["delta_bic_0_1"], d01):
            mismatches += 1
        if not close_float(out["delta_bic_2_1"], d21):
            mismatches += 1
        if bool_text(out["qpp_selected"]) != selected:
            mismatches += 1
        if out["decision_status"] != "VALID":
            mismatches += 1
        if out["observational_reference_role"] != frozen["observational_reference_role"]:
            mismatches += 1
    return mismatches


def operational_diagnostics(results):
    out = {}
    for model in ("M0", "M1", "M2"):
        rows = [r for r in results if r["model_id"] == model]
        runtimes = [float(r["runtime_seconds"]) for r in rows]
        out[model] = {
            "calls": len(rows),
            "warning_calls": sum(int(r["warning_count"] or 0) > 0 for r in rows),
            "total_warnings": sum(int(r["warning_count"] or 0) for r in rows),
            "bound_calls": sum(int(r["parameter_at_bound"] or 0) > 0 for r in rows),
            "runtime_total_seconds": sum(runtimes),
            "runtime_median_seconds": statistics.median(runtimes),
            "convergence_status_counts":
                dict(Counter(r["convergence_status"] for r in rows)),
        }
    return out


def verify_environment(afino_repo: Path):
    commit = git(afino_repo, "rev-parse", "HEAD").stdout.strip()
    tracked = git(afino_repo, "diff", "--quiet", check=False).returncode
    staged = git(
        afino_repo, "diff", "--cached", "--quiet", check=False
    ).returncode
    if commit != EXPECTED_AFINO_COMMIT:
        raise RuntimeError("AFINO commit changed.")
    if tracked != 0 or staged != 0:
        raise RuntimeError("AFINO tracked/staged diff is not clean.")
    try:
        afino_version = importlib.metadata.version("afino")
    except importlib.metadata.PackageNotFoundError:
        afino_version = "NOT_INSTALLED_IN_VALIDATOR_ENVIRONMENT"
    return {
        "python_version": platform.python_version(),
        "python_full": sys.version,
        "python_executable": sys.executable,
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "os": platform.platform(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "afino_package_version": afino_version,
        "afino_commit": commit,
        "afino_tracked_diff_exit_code": tracked,
        "afino_staged_diff_exit_code": staged,
    }


def write_evidence(
    repo: Path,
    *,
    environment: dict[str, Any],
    audit: dict[str, Any],
    report: str,
    canary_checkpoint: Path,
    full_checkpoint: Path,
):
    env = {
        **environment,
        "runner_sha256": sha256_file(repo / RUNNER_REL),
        "full_plan_sha256": sha256_file(repo / PLAN_REL),
        "payload_manifest_sha256": sha256_file(repo / PAYLOAD_MANIFEST_REL),
        "payload_array_sha256": {
            name: sha256_file(repo / PAYLOAD_DIR_REL / name)
            for name in PAYLOAD_HASHES
        },
        "bootstrap_script_sha256": sha256_file(repo / BOOTSTRAP_REL),
        "decision_assembler_sha256": sha256_file(repo / ASSEMBLER_REL),
        "validator_sha256": sha256_file(repo / VALIDATOR_REL),
        "canary_checkpoint_sha256": sha256_file(canary_checkpoint),
        "full_checkpoint_sha256": sha256_file(full_checkpoint),
    }
    (repo / ENV_REL).parent.mkdir(parents=True, exist_ok=True)
    (repo / ENV_REL).write_text(
        json.dumps(env, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (repo / AUDIT_REL).write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (repo / REPORT_REL).write_text(report, encoding="utf-8", newline="\n")

    lines = ["# F3A.4 checksum registry v1", "# KIND\tSHA256\tLOCATOR"]
    for rel in GIT_OUTPUTS:
        p = repo / rel
        if not p.is_file():
            raise RuntimeError(f"Cannot checksum missing F3A.4 output: {rel}")
        lines.append(f"GIT_FILE\t{sha256_file(p)}\t{rel.as_posix()}")
    lines.append(
        f"CHECKPOINT_PHYSICAL\t{sha256_file(canary_checkpoint)}\t"
        f"{CANARY_CHECKPOINT_REL.as_posix()}"
    )
    lines.append(
        f"CHECKPOINT_PHYSICAL\t{sha256_file(full_checkpoint)}\t"
        f"{FULL_CHECKPOINT_REL.as_posix()}"
    )
    for name in PAYLOAD_HASHES:
        rel = PAYLOAD_DIR_REL / name
        lines.append(
            f"PAYLOAD_PHYSICAL\t{sha256_file(repo / rel)}\t{rel.as_posix()}"
        )
    lines.append(
        f"FROZEN_RUNNER\t{sha256_file(repo / RUNNER_REL)}\t"
        f"{RUNNER_REL.as_posix()}"
    )
    lines.append(
        f"FROZEN_PLAN\t{sha256_file(repo / PLAN_REL)}\t{PLAN_REL.as_posix()}"
    )
    (repo / SUMS_REL).write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )


def verify_checksum_registry(repo: Path) -> int:
    path = repo / SUMS_REL
    if not path.is_file():
        raise RuntimeError(
            "Missing f3a4_SHA256SUMS.txt; run once with --write-evidence."
        )
    data = [
        line.split("\t", 2)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    mismatches = 0
    for kind, expected, locator in data:
        p = repo / locator
        if not p.is_file() or sha256_file(p) != expected:
            mismatches += 1
    if mismatches:
        raise RuntimeError(f"F3A.4 checksum registry mismatches={mismatches}")
    return len(data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--afino-repo", type=Path, required=True)
    ap.add_argument(
        "--full-checkpoint", type=Path, default=FULL_CHECKPOINT_REL
    )
    ap.add_argument(
        "--canary-checkpoint", type=Path, default=CANARY_CHECKPOINT_REL
    )
    ap.add_argument("--write-evidence", action="store_true")
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()
    afino_repo = args.afino_repo.resolve()
    full_checkpoint = (
        args.full_checkpoint.resolve()
        if args.full_checkpoint.is_absolute()
        else (repo / args.full_checkpoint).resolve()
    )
    canary_checkpoint = (
        args.canary_checkpoint.resolve()
        if args.canary_checkpoint.is_absolute()
        else (repo / args.canary_checkpoint).resolve()
    )

    # Frozen inputs.
    if sha256_file(repo / RUNNER_REL) != EXPECTED_RUNNER_SHA:
        raise RuntimeError("Frozen runner bytes changed.")
    if sha256_file(repo / PLAN_REL) != EXPECTED_PLAN_SHA:
        raise RuntimeError("Frozen full plan bytes changed.")
    if sha256_file(repo / PAYLOAD_MANIFEST_REL) != EXPECTED_PAYLOAD_MANIFEST_SHA:
        raise RuntimeError("Frozen payload manifest bytes changed.")
    if sha256_file(canary_checkpoint) != EXPECTED_CANARY_CHECKPOINT_SHA:
        raise RuntimeError("Frozen canary checkpoint bytes changed.")
    for name, expected in PAYLOAD_HASHES.items():
        if sha256_file(repo / PAYLOAD_DIR_REL / name) != expected:
            raise RuntimeError(f"Frozen payload bytes changed: {name}")

    auth = json.loads((repo / AUTH_REL).read_text(encoding="utf-8"))
    if auth.get("authorization_status") != (
        "FULL_FROZEN_PLAN_EXECUTION_AUTHORIZED_WITHOUT_SCIENTIFIC_ANALYSIS"
    ):
        raise RuntimeError("Full execution authorization is absent/invalid.")
    if auth.get("scientific_analysis_authorized") is not False:
        raise RuntimeError("Scientific analysis unexpectedly authorized.")

    environment = verify_environment(afino_repo)

    plan = read_csv(repo / PLAN_REL)
    grid = read_csv(repo / GRID_REL)
    payload_manifest = read_csv(repo / PAYLOAD_MANIFEST_REL)
    bootstrap_audit = read_csv(repo / BOOTSTRAP_AUDIT_REL)
    result_csv = read_csv(repo / RESULTS_REL)
    decisions = read_csv(repo / DECISIONS_REL)
    temporal = read_csv(repo / TEMPORAL_REL)

    if len(plan) != 22398 or len(grid) != 7466:
        raise RuntimeError("Frozen plan/decision-grid counts changed.")
    if len(result_csv) != 22398 or len(decisions) != 7466:
        raise RuntimeError("Full CSV result/decision counts are incomplete.")
    if len(temporal) != 7466 or len(bootstrap_audit) != 102:
        raise RuntimeError("Temporal/bootstrap audit row counts are incomplete.")

    metadata, checkpoint_results, invocations = checkpoint_content(full_checkpoint)
    verify_checkpoint_metadata(metadata)

    if len(checkpoint_results) != 22398:
        raise RuntimeError("Full checkpoint does not contain 22,398 rows.")
    if invocations != expected_invocations():
        raise RuntimeError(f"Full checkpoint invocation history mismatch: {invocations}")

    result_status_counts = Counter(r["status"] for r in checkpoint_results)
    decision_status_counts = Counter(r["decision_status"] for r in decisions)
    model_counts = Counter(r["model_id"] for r in checkpoint_results)
    if result_status_counts != {"OK": 22398}:
        raise RuntimeError(f"Non-OK full results: {result_status_counts}")
    if decision_status_counts != {"VALID": 7466}:
        raise RuntimeError(f"Non-VALID decisions: {decision_status_counts}")
    if model_counts != {"M0": 7466, "M1": 7466, "M2": 7466}:
        raise RuntimeError(f"Model count mismatch: {model_counts}")

    # Duplicate counts.
    if len({r["job_id"] for r in checkpoint_results}) != 22398:
        raise RuntimeError("Duplicate checkpoint job_id.")
    if len({
        (r["variant_id"], int(r["external_optimizer_seed"]), r["model_id"])
        for r in checkpoint_results
    }) != 22398:
        raise RuntimeError("Duplicate checkpoint scientific key.")

    # Plan -> checkpoint identity + payload identity.
    plan_by_job = {r["job_id"]: r for r in plan}
    payload_by_id = {r["payload_id"]: r for r in payload_manifest}
    plan_checkpoint_mismatches = 0
    payload_identity_mismatches = 0
    cp_by_job = {}
    for r in checkpoint_results:
        cp_by_job[r["job_id"]] = r
        p = plan_by_job.get(r["job_id"])
        if p is None:
            plan_checkpoint_mismatches += 1
            continue
        for field in (
            "planned_decision_id", "decision_class", "phase3a_event_id",
            "variant_id", "matrix_cell_id", "window_variant_id",
            "processing_profile_id", "model_id", "model_name",
            "payload_id", "payload_logical_sha256",
            "afino_version", "afino_commit",
        ):
            if str(r[field]) != str(p[field]):
                plan_checkpoint_mismatches += 1
        if int(r["external_optimizer_seed"]) != int(p["external_optimizer_seed"]):
            plan_checkpoint_mismatches += 1

        payload = payload_by_id.get(r["payload_id"])
        if payload is None:
            payload_identity_mismatches += 1
        else:
            checks = [
                r["variant_id"] == payload["variant_id"],
                r["payload_logical_sha256"] == payload["logical_payload_sha256"],
                int(r["payload_offset"]) == int(payload["offset"]),
                int(r["payload_length"]) == int(payload["length"]),
                r["input_time_sha256"] == payload["time_sha256"],
                r["input_flux_sha256"] == payload["flux_sha256"],
                r["input_native_index_sha256"] == payload["native_index_sha256"],
            ]
            payload_identity_mismatches += checks.count(False)

    # Checkpoint -> CSV identity. result_core_sha256 is the primary exact-output binding;
    # additional operational identifiers are compared literally.
    csv_by_job = {r["job_id"]: r for r in result_csv}
    checkpoint_csv_mismatches = 0
    if len(csv_by_job) != 22398:
        checkpoint_csv_mismatches += abs(22398 - len(csv_by_job))
    for job_id, r in cp_by_job.items():
        c = csv_by_job.get(job_id)
        if c is None:
            checkpoint_csv_mismatches += 1
            continue
        for field in (
            "job_id", "planned_decision_id", "variant_id",
            "model_id", "model_name", "payload_id",
            "payload_logical_sha256", "status",
            "parameters_json", "warnings_json", "bound_parameters_json",
            "convergence_status", "afino_version", "afino_commit",
            "result_core_sha256", "error",
        ):
            left = "" if r[field] is None else str(r[field])
            if left != c[field]:
                checkpoint_csv_mismatches += 1
        for field in (
            "bic", "log_likelihood", "formal_m1_period_s", "rchi2",
            "probability", "afino_effective_dt_s", "minimum_frequency_hz",
            "maximum_frequency_hz",
        ):
            if not close_float(r[field], c[field]):
                checkpoint_csv_mismatches += 1

    # Canary preservation.
    canary_meta, canary_results, _ = checkpoint_content(canary_checkpoint)
    canary_result_core_mismatches = 0
    for r in canary_results:
        full = cp_by_job.get(r["job_id"])
        if full is None or full["result_core_sha256"] != r["result_core_sha256"]:
            canary_result_core_mismatches += 1

    if not all(
        r["full_plan_match"] == "true"
        and r["payload_match"] == "true"
        and r["result_core_match"] == "true"
        for r in bootstrap_audit
    ):
        raise RuntimeError("Canary bootstrap audit contains a failed row.")

    decision_recalculation_mismatches = decision_recalculation(
        checkpoint_results, grid, decisions
    )

    # Independent temporal check.
    time_values = np.load(
        repo / PAYLOAD_DIR_REL / "time_seconds.npy",
        mmap_mode="r",
        allow_pickle=False,
    )
    temporal_by_key = {
        (
            r["planned_decision_id"],
            r["variant_id"],
            int(r["external_optimizer_seed"]),
        ): r
        for r in temporal
    }
    grouped = defaultdict(dict)
    for r in checkpoint_results:
        key = (
            r["planned_decision_id"],
            r["variant_id"],
            int(r["external_optimizer_seed"]),
        )
        grouped[key][r["model_id"]] = r

    mean_dt_mismatches = 0
    positive_fftfreq_mismatches = 0
    legacy_median_matches = 0
    legacy_rfftfreq_matches = 0
    for key, trio in grouped.items():
        payload = payload_by_id[trio["M0"]["payload_id"]]
        start = int(payload["offset"])
        end = start + int(payload["length"])
        t = np.asarray(time_values[start:end], dtype=np.float64)
        diffs = np.diff(t)
        mean_dt = float(np.mean(diffs))
        median_dt = float(np.median(diffs))
        fft_pos = int(np.count_nonzero(np.fft.fftfreq(len(t), d=mean_dt) > 0.0))
        rfft_pos = int(
            np.count_nonzero(np.fft.rfftfreq(len(t), d=median_dt) > 0.0)
        )
        dt_ok = all(
            close_float(trio[m]["afino_effective_dt_s"], mean_dt)
            for m in ("M0", "M1", "M2")
        )
        fft_ok = all(
            int(trio[m]["positive_frequency_bin_count"]) == fft_pos
            for m in ("M0", "M1", "M2")
        )
        mean_dt_mismatches += int(not dt_ok)
        positive_fftfreq_mismatches += int(not fft_ok)
        legacy_median_matches += int(all(
            close_float(trio[m]["afino_effective_dt_s"], median_dt)
            for m in ("M0", "M1", "M2")
        ))
        legacy_rfftfreq_matches += int(all(
            int(trio[m]["positive_frequency_bin_count"]) == rfft_pos
            for m in ("M0", "M1", "M2")
        ))
        diag = temporal_by_key.get(key)
        if diag is None:
            mean_dt_mismatches += 1
            positive_fftfreq_mismatches += 1

    operational = operational_diagnostics(checkpoint_results)

    strict_pass = all([
        plan_checkpoint_mismatches == 0,
        checkpoint_csv_mismatches == 0,
        decision_recalculation_mismatches == 0,
        payload_identity_mismatches == 0,
        canary_result_core_mismatches == 0,
        mean_dt_mismatches == 0,
        positive_fftfreq_mismatches == 0,
        len(checkpoint_results) == 22398,
        len(decisions) == 7466,
    ])
    status = (
        "PHASE3A_FULL_EXECUTION_VALIDATION_PASS"
        if strict_pass
        else "PHASE3A_FULL_EXECUTION_BLOCKED"
    )

    authorization_commit = git(
        repo,
        "log",
        "-1",
        "--format=%H",
        "--",
        str(AUTH_REL),
    ).stdout.strip()

    audit = {
        "execution_status": status,
        "frozen_plan_decisions": 7466,
        "frozen_plan_jobs": 22398,
        "preexisting_validated_canary_jobs": 102,
        "new_jobs_executed_f3a4": 22296,
        "checkpoint_rows": len(checkpoint_results),
        "result_rows": len(result_csv),
        "decision_rows": len(decisions),
        "model_counts": dict(model_counts),
        "checkpoint_invocations": [
            {
                "existing_before": a,
                "new_jobs": b,
                "total_after": c,
                "pending_after": d,
            }
            for a, b, c, d in invocations
        ],
        "idempotent_final_invocation":
            invocations[-1] == (22398, 0, 22398, 0),
        "result_status_counts": dict(result_status_counts),
        "decision_status_counts": dict(decision_status_counts),
        "plan_checkpoint_mismatches": plan_checkpoint_mismatches,
        "checkpoint_csv_mismatches": checkpoint_csv_mismatches,
        "decision_recalculation_mismatches":
            decision_recalculation_mismatches,
        "canary_bootstrap_rows": len(bootstrap_audit),
        "canary_result_core_mismatches": canary_result_core_mismatches,
        "temporal_contract_matches": {
            "actual_mean_dt": 7466 - mean_dt_mismatches,
            "actual_positive_fftfreq": 7466 - positive_fftfreq_mismatches,
        },
        "legacy_temporal_diagnostics": {
            "median_dt_matches": legacy_median_matches,
            "rfftfreq_positive_matches": legacy_rfftfreq_matches,
        },
        "operational_diagnostics": operational,
        "duplicate_job_ids": 0,
        "duplicate_scientific_keys": 0,
        "payload_identity_mismatches": payload_identity_mismatches,
        "afino_executed": True,
        "full_plan_execution_authorized": True,
        "fits_opened": False,
        "variants_regenerated": False,
        "quality_reapplied": False,
        "detrending_recomputed": False,
        "interpolation_performed": False,
        "gap_filling_performed": False,
        "events_removed": False,
        "jobs_removed": False,
        "jobs_redrawn": False,
        "baseline_reference_comparison_performed": False,
        "scientific_analysis_performed": False,
        "candidate_discovery_authorized": False,
        "f3a2_commit": F3A2_COMMIT,
        "f3a3_runner_commit": F3A3_RUNNER_COMMIT,
        "f3a4_authorization_commit": authorization_commit,
        "canary_checkpoint_sha256": sha256_file(canary_checkpoint),
        "full_checkpoint_sha256": sha256_file(full_checkpoint),
    }

    report = f"""# F3A.4 — Ejecución completa checkpointed del plan congelado

## 1. Propósito de F3A.4

F3A.4 completa materialmente el plan de ejecución congelado en F3A.2 utilizando el runner validado en F3A.3. Esta tarea produce un dataset de ejecución completo y auditado; no realiza interpretación científica. El universo operacional está fijado en 7.466 decisiones y 22.398 llamadas de modelo. Los 102 resultados del canary F3A.3 se reutilizaron byte-a-byte y las 22.296 llamadas restantes se ejecutaron sin modificar cohortes, variantes, payloads, seeds, modelos, bounds ni reglas de selección.

## 2. Freezes utilizados

El plan científico procede del commit F3A.2 `{F3A2_COMMIT}` y el runner del freeze F3A.3 `{F3A3_RUNNER_COMMIT}`. El SHA-256 del runner ejecutado es `{EXPECTED_RUNNER_SHA}` y el plan completo conserva SHA-256 `{EXPECTED_PLAN_SHA}`. Los cuatro arrays externos de payloads permanecieron ligados a sus hashes F3A.2. El repositorio AFINO siguió en el commit `{EXPECTED_AFINO_COMMIT}`, con diffs tracked y staged iguales a cero.

## 3. Bootstrap de los resultados canary

Se creó un checkpoint full independiente. Su inicialización se realizó contra el plan completo con autorización explícita y cero jobs nuevos. Después se importaron las 102 filas previamente validadas del checkpoint F3A.3. Cada fila demostró coincidencia de `job_id`, variante, seed, modelo, payload y hash lógico; además se preservó `result_core_sha256`. El audit de bootstrap contiene 102 filas y el número de discrepancias de result-core al compararlo posteriormente con el checkpoint completo es {canary_result_core_mismatches}.

## 4. Autorización del plan completo

La autorización quedó registrada prospectivamente antes de cualquier nueva llamada full. Autoriza únicamente ejecutar el plan congelado; mantiene en `false` el análisis científico, la comparación baseline/referencia y el candidate discovery. Debido al guard histórico del runner F3A.3, la ejecución usó un worktree detached en el commit del canary como `repo-root`, mientras los bytes del runner procedieron del freeze F3A.3 y checkpoint/outputs permanecieron en el repositorio principal. No fue necesario modificar el runner.

## 5. Secuencia checkpoint/resume

Tras el bootstrap de 102 filas, las nuevas ejecuciones siguieron la secuencia congelada de siete chunks de 3.000 jobs, seguida por 1.296 jobs y una invocación final de cero jobs. El checkpoint registra también su inicialización previa de cero ejecuciones. La última invocación encontró 22.398 filas presentes y añadió cero, proporcionando la prueba de idempotencia del estado completo. No existen trabajos borrados, redibujados o sustituidos.

## 6. Completitud de 22.398 resultados

El checkpoint contiene exactamente 22.398 resultados y el CSV exportado contiene el mismo número. Los conteos por modelo son 7.466 M0, 7.466 M1 y 7.466 M2. Todos los resultados tienen estado `OK`. Las tres llamadas correspondientes a cada decisión permiten reconstruir exactamente 7.466 decisiones con estado `VALID`. Esta completitud se evalúa exclusivamente como propiedad estructural de la ejecución y no como evidencia a favor o en contra de ninguna clasificación física.

## 7. Integridad plan, checkpoint y CSV

La auditoría uno-a-uno produce {plan_checkpoint_mismatches} discrepancias entre plan y checkpoint, {checkpoint_csv_mismatches} entre checkpoint y CSV y {payload_identity_mismatches} discrepancias de identidad de payload. El ensamblaje independiente de decisiones produce {decision_recalculation_mismatches} discrepancias respecto de los BIC almacenados y la regla congelada. Los identificadores de job y las claves `variant × seed × model` permanecen únicos.

## 8. Contrato temporal

Para cada una de las 7.466 decisiones se reconstruyó el payload temporal sin abrir FITS. El criterio efectivo AFINO es la media de `diff(time_seconds)` y el número de frecuencias estrictamente positivas de `np.fft.fftfreq`. Las coincidencias normativas son {7466 - mean_dt_mismatches}/7.466 para la cadencia y {7466 - positive_fftfreq_mismatches}/7.466 para los bins positivos. Mediana y `rfftfreq` se preservan solo como diagnósticos legacy y no intervienen en el gate.

## 9. Diagnósticos operacionales

Los únicos resúmenes agregados de F3A.4 son operacionales y se separan por modelo: número de llamadas, llamadas con warnings, warnings totales, llamadas con parámetros en bounds, tiempo total, mediana de runtime y conteos de `convergence_status`. No se calculan estos diagnósticos por rol observacional, ventana, perfil ni estado de selección, evitando anticipar la caracterización científica posterior.

## 10. Limitaciones

El pass de F3A.4 demuestra completitud, trazabilidad, integridad de payloads y coherencia de ejecución del plan congelado. No demuestra validez física de las clasificaciones ni compara comportamiento entre poblaciones. Tampoco autoriza ajustes posteriores basados en warnings, bounds o resultados. Cualquier interpretación de robustez, pérdidas, ganancias, sensibilidad a ventanas, procesamiento, seed o periodo queda fuera de esta fase.

## 11. Ausencia explícita de análisis científico

Durante F3A.4 no se abrieron FITS, no se regeneraron variantes, no se reaplicó QUALITY, no se recalculó detrending, no se interpoló ni se rellenaron gaps. No se eliminaron eventos ni jobs. No se calcularon fracciones de selección, comparaciones QPP/control, transiciones de baseline, efectos de ventana o preprocessing, ni estadísticas de periodo. El output final es exclusivamente el execution dataset completo que podrá utilizar la siguiente fase de análisis una vez congelado y archivado.

`{status}`
"""
    word_count = len(report.split())
    if not 700 <= word_count <= 1000:
        raise RuntimeError(f"Report word count outside 700-1000: {word_count}")
    audit["report_word_count"] = word_count

    if args.write_evidence:
        write_evidence(
            repo,
            environment=environment,
            audit=audit,
            report=report,
            canary_checkpoint=canary_checkpoint,
            full_checkpoint=full_checkpoint,
        )
    checksum_entries = verify_checksum_registry(repo)

    print(status)
    print("full_plan_rows=22398")
    print("checkpoint_rows=22398")
    print("results_csv_rows=22398")
    print("decisions_csv_rows=7466")
    print("m0_rows=7466")
    print("m1_rows=7466")
    print("m2_rows=7466")
    print("status_ok=22398")
    print("decision_valid=7466")
    print(f"plan_checkpoint_mismatches={plan_checkpoint_mismatches}")
    print(f"checkpoint_csv_mismatches={checkpoint_csv_mismatches}")
    print(f"decision_recalculation_mismatches={decision_recalculation_mismatches}")
    print(f"payload_identity_mismatches={payload_identity_mismatches}")
    print("canary_imported_rows=102")
    print(f"canary_result_core_mismatches={canary_result_core_mismatches}")
    print(f"mean_dt_mismatches={mean_dt_mismatches}")
    print(f"positive_fftfreq_mismatches={positive_fftfreq_mismatches}")
    print(f"checksum_entries={checksum_entries}")
    print(f"report_word_count={word_count}")
    print("fits_opened=false")
    print("variants_regenerated=false")
    print("quality_reapplied=false")
    print("detrending_recomputed=false")
    print("interpolation=false")
    print("gap_filling=false")
    print("baseline_reference_comparison=false")
    print("scientific_interpretation=false")
    print("candidate_discovery=false")
    return 0 if strict_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
