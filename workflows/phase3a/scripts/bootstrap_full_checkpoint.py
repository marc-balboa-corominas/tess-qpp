#!/usr/bin/env python3
"""
F3A.4 — initialize the full-plan checkpoint and import the 102 validated
F3A.3 canary results without re-running them.

The frozen F3A.3 runner is not modified. Because that runner intentionally binds
repo-root HEAD to the frozen canary-plan commit, this bootstrap creates/verifies
a detached shadow worktree at that commit and copies only the frozen external
payload arrays into it. The runner itself is executed byte-exact from the main
repository, while the full checkpoint remains in the main repository runtime.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

F3A2_COMMIT = "6bf9beca8fa8016495693575f8c86a2dec5fecb1"
F3A2_TAG = "phase3a-execution-plan-v1"
F3A3_CANARY_PLAN_COMMIT = "b66764db49f7b823f6d7e3e21ce0da66476479bd"
F3A3_RUNNER_COMMIT = "0738b1cc132598119dcbbc27b4113c93ae9d2733"
F3A3_RUNNER_TAG = "phase3a-runner-v1"

EXPECTED_RUNNER_SHA256 = (
    "0de4b1b3745e7c7b237ff82680dd8f6cb8e2bf1288c58fd07d1624ca034558db"
)
EXPECTED_FULL_PLAN_SHA256 = (
    "d190a4f5e70339b05fd42b2d0cda9c51dd180c10e885c27fdfa43323c8dc1c6f"
)
EXPECTED_PAYLOAD_MANIFEST_SHA256 = (
    "fa5bdfa20eaf499e5354caf159221577633de92f43ec31f48be31e16cd84c148"
)
EXPECTED_F3A2_SUMS_SHA256 = (
    "52d9cd40890a4d1e0e74ec8b5b2062840eceb968aecd4d3c4a8eea8255e5c08f"
)
EXPECTED_CANARY_CHECKPOINT_SHA256 = (
    "9781b13889d2a66e33be973f555b081f5d4de6d97c155a73fd93f5118d2073ca"
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

AUTH_REL = Path("workflows/phase3a/config/f3a4_full_execution_authorization.json")
RUNNER_REL = Path("workflows/phase3a/scripts/run_afino_checkpointed.py")
FULL_PLAN_REL = Path("workflows/phase3a/evidence/tables/f3a2_exact_afino_plan.csv")
PAYLOAD_MANIFEST_REL = Path("workflows/phase3a/evidence/tables/f3a2_payload_manifest.csv")
F3A2_SUMS_REL = Path("workflows/phase3a/evidence/f3a2_SHA256SUMS.txt")
PAYLOAD_DIR_REL = Path("data/interim/phase3a/f3a2_payloads")
CANARY_CHECKPOINT_REL = Path("runtime/phase3a/f3a3/canary_checkpoint.sqlite")
FULL_CHECKPOINT_REL = Path("runtime/phase3a/f3a4/full_checkpoint.sqlite")
BOOTSTRAP_AUDIT_REL = Path(
    "workflows/phase3a/evidence/tables/f3a4_canary_bootstrap_audit.csv"
)

AUDIT_FIELDS = [
    "job_id",
    "planned_decision_id",
    "variant_id",
    "external_optimizer_seed",
    "model_id",
    "full_plan_match",
    "payload_match",
    "scientific_key_match",
    "canary_result_core_sha256",
    "imported_result_core_sha256",
    "result_core_match",
    "source_checkpoint_sha256",
    "bootstrap_status",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=fields, extrasaction="raise", lineterminator="\n"
        )
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def require_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"Missing {label}: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label} hash mismatch: {actual} != {expected}")


def load_authorization(repo: Path) -> dict[str, Any]:
    auth = json.loads((repo / AUTH_REL).read_text(encoding="utf-8"))
    required = {
        "authorization_status":
            "FULL_FROZEN_PLAN_EXECUTION_AUTHORIZED_WITHOUT_SCIENTIFIC_ANALYSIS",
        "authorized_plan_sha256": EXPECTED_FULL_PLAN_SHA256,
        "f3a2_commit": F3A2_COMMIT,
        "f3a2_tag": F3A2_TAG,
        "f3a3_runner_commit": F3A3_RUNNER_COMMIT,
        "f3a3_runner_tag": F3A3_RUNNER_TAG,
        "runner_sha256": EXPECTED_RUNNER_SHA256,
        "planned_decisions": 7466,
        "planned_model_jobs": 22398,
        "validated_canary_jobs": 102,
        "remaining_new_jobs": 22296,
        "canary_checkpoint_sha256": EXPECTED_CANARY_CHECKPOINT_SHA256,
        "reuse_validated_canary_results": True,
        "rerun_canary_jobs": False,
        "scientific_analysis_authorized": False,
        "baseline_reference_comparison_authorized": False,
        "candidate_discovery_authorized": False,
    }
    for key, value in required.items():
        if auth.get(key) != value:
            raise RuntimeError(
                f"Authorization mismatch {key}: {auth.get(key)!r} != {value!r}"
            )
    return auth


def verify_main_repo(repo: Path) -> None:
    runner_tag_commit = git(repo, "rev-parse", f"{F3A3_RUNNER_TAG}^{{}}").stdout.strip()
    if runner_tag_commit != F3A3_RUNNER_COMMIT:
        raise RuntimeError("F3A.3 runner tag identity changed.")

    f3a2_tag_commit = git(repo, "rev-parse", f"{F3A2_TAG}^{{}}").stdout.strip()
    if f3a2_tag_commit != F3A2_COMMIT:
        raise RuntimeError("F3A.2 execution-plan tag identity changed.")

    if git(
        repo, "merge-base", "--is-ancestor", F3A3_RUNNER_COMMIT, "HEAD",
        check=False
    ).returncode != 0:
        raise RuntimeError("Current HEAD is not a descendant of phase3a-runner-v1.")

    require_hash(repo / RUNNER_REL, EXPECTED_RUNNER_SHA256, "frozen runner")
    require_hash(repo / FULL_PLAN_REL, EXPECTED_FULL_PLAN_SHA256, "full plan")
    require_hash(
        repo / PAYLOAD_MANIFEST_REL,
        EXPECTED_PAYLOAD_MANIFEST_SHA256,
        "payload manifest",
    )
    require_hash(repo / F3A2_SUMS_REL, EXPECTED_F3A2_SUMS_SHA256, "F3A.2 sums")
    require_hash(
        repo / CANARY_CHECKPOINT_REL,
        EXPECTED_CANARY_CHECKPOINT_SHA256,
        "F3A.3 canary checkpoint",
    )
    for name, expected in PAYLOAD_PHYSICAL_HASHES.items():
        require_hash(repo / PAYLOAD_DIR_REL / name, expected, f"payload {name}")


def prepare_execution_root(repo: Path, execution_root: Path) -> None:
    if execution_root.exists():
        head = git(execution_root, "rev-parse", "HEAD", check=False)
        if head.returncode != 0:
            raise RuntimeError(
                f"Execution root exists but is not a Git worktree: {execution_root}"
            )
        if head.stdout.strip() != F3A3_CANARY_PLAN_COMMIT:
            raise RuntimeError(
                f"Existing execution root HEAD mismatch: {head.stdout.strip()}"
            )
        if git(execution_root, "status", "--porcelain").stdout.strip():
            # Payload arrays are ignored/untracked by policy; tracked changes are the issue.
            tracked = git(execution_root, "diff", "--quiet", check=False).returncode
            staged = git(
                execution_root, "diff", "--cached", "--quiet", check=False
            ).returncode
            if tracked != 0 or staged != 0:
                raise RuntimeError("Execution worktree contains tracked/staged changes.")
    else:
        execution_root.parent.mkdir(parents=True, exist_ok=True)
        cp = git(
            repo,
            "worktree",
            "add",
            "--detach",
            str(execution_root),
            F3A3_CANARY_PLAN_COMMIT,
            check=False,
        )
        if cp.returncode != 0:
            raise RuntimeError(
                "Unable to create detached execution worktree:\n"
                + cp.stdout + "\n" + cp.stderr
            )

    # External payload bytes are copied, never regenerated.
    target_payload_dir = execution_root / PAYLOAD_DIR_REL
    target_payload_dir.mkdir(parents=True, exist_ok=True)
    for name, expected in PAYLOAD_PHYSICAL_HASHES.items():
        src = repo / PAYLOAD_DIR_REL / name
        dst = target_payload_dir / name
        if not dst.is_file() or sha256_file(dst) != expected:
            shutil.copy2(src, dst)
        require_hash(dst, expected, f"execution-root payload {name}")


def checkpoint_rows(path: Path) -> int:
    con = sqlite3.connect(path)
    try:
        return int(con.execute("SELECT COUNT(*) FROM results").fetchone()[0])
    finally:
        con.close()


def duplicate_counts(path: Path) -> tuple[int, int]:
    con = sqlite3.connect(path)
    try:
        dup_jobs = int(
            con.execute(
                "SELECT COUNT(*) - COUNT(DISTINCT job_id) FROM results"
            ).fetchone()[0]
        )
        dup_keys = int(
            con.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT variant_id,external_optimizer_seed,model_id,COUNT(*) c
                    FROM results
                    GROUP BY variant_id,external_optimizer_seed,model_id
                    HAVING c > 1
                )
                """
            ).fetchone()[0]
        )
        return dup_jobs, dup_keys
    finally:
        con.close()


def initialize_full_checkpoint(
    repo: Path,
    execution_root: Path,
    afino_repo: Path,
    full_checkpoint: Path,
) -> None:
    if full_checkpoint.exists():
        raise RuntimeError(
            f"Full checkpoint already exists: {full_checkpoint}. "
            "Bootstrap never overwrites an existing execution checkpoint."
        )
    full_checkpoint.parent.mkdir(parents=True, exist_ok=True)

    runner = repo / RUNNER_REL
    full_plan = execution_root / FULL_PLAN_REL
    command = [
        sys.executable,
        str(runner),
        "--repo-root", str(execution_root),
        "--afino-repo", str(afino_repo),
        "--checkpoint", str(full_checkpoint),
        "--canary-job-manifest", str(full_plan),
        "--max-new-jobs", "0",
        "--authorize-full-plan",
    ]
    cp = subprocess.run(command, capture_output=True, text=True)
    print(cp.stdout, end="")
    if cp.returncode != 0:
        raise RuntimeError(
            "Frozen runner failed during full checkpoint initialization:\n"
            + cp.stderr
        )

    con = sqlite3.connect(full_checkpoint)
    try:
        metadata = dict(con.execute("SELECT key,value FROM metadata").fetchall())
        invocations = con.execute(
            """
            SELECT existing_before,new_jobs,total_after,pending_after
            FROM invocations ORDER BY invocation_id
            """
        ).fetchall()
        rows = int(con.execute("SELECT COUNT(*) FROM results").fetchone()[0])
    finally:
        con.close()

    if metadata.get("plan_kind") != "full":
        raise RuntimeError("Full checkpoint plan_kind is not 'full'.")
    if metadata.get("canary_manifest_sha256") != EXPECTED_FULL_PLAN_SHA256:
        raise RuntimeError("Full checkpoint is not bound to the full plan hash.")
    if metadata.get("runner_sha256") != EXPECTED_RUNNER_SHA256:
        raise RuntimeError("Full checkpoint runner hash mismatch.")
    if rows != 0:
        raise RuntimeError("Initialization unexpectedly executed model jobs.")
    if invocations != [(0, 0, 0, 22398)]:
        raise RuntimeError(
            f"Unexpected initialization invocation record: {invocations}"
        )


def import_canary(
    repo: Path,
    full_checkpoint: Path,
    source_checkpoint: Path,
) -> list[dict[str, Any]]:
    full_plan = read_csv(repo / FULL_PLAN_REL)
    payload_manifest = read_csv(repo / PAYLOAD_MANIFEST_REL)

    if len(full_plan) != 22398:
        raise RuntimeError("Frozen full plan does not contain 22,398 jobs.")
    full_by_job = {r["job_id"]: r for r in full_plan}
    if len(full_by_job) != 22398:
        raise RuntimeError("Duplicate job_id in frozen full plan.")

    payload_by_id = {r["payload_id"]: r for r in payload_manifest}
    if len(payload_by_id) != 6422:
        raise RuntimeError("Duplicate payload_id in frozen payload manifest.")

    source = sqlite3.connect(
        f"file:{source_checkpoint}?mode=ro", uri=True
    )
    source.row_factory = sqlite3.Row
    try:
        source_rows = [
            dict(r) for r in source.execute(
                "SELECT * FROM results ORDER BY job_order"
            )
        ]
    finally:
        source.close()

    if len(source_rows) != 102:
        raise RuntimeError(f"Expected 102 canary rows, got {len(source_rows)}")
    if any(r["status"] != "OK" for r in source_rows):
        raise RuntimeError("At least one validated canary row is not OK.")

    target = sqlite3.connect(full_checkpoint)
    target.row_factory = sqlite3.Row
    try:
        result_columns = [
            r[1] for r in target.execute("PRAGMA table_info(results)").fetchall()
        ]
        placeholders = ",".join("?" for _ in result_columns)
        cols = ",".join(result_columns)

        audit_rows = []
        target.execute("BEGIN IMMEDIATE")

        for row in source_rows:
            plan = full_by_job.get(row["job_id"])
            full_plan_match = bool(plan)
            if not full_plan_match:
                raise RuntimeError(f"Canary job absent from full plan: {row['job_id']}")

            scientific_key_match = (
                row["variant_id"] == plan["variant_id"]
                and str(row["external_optimizer_seed"])
                    == str(plan["external_optimizer_seed"])
                and row["model_id"] == plan["model_id"]
            )
            payload = payload_by_id.get(row["payload_id"])
            payload_match = bool(
                payload
                and row["payload_id"] == plan["payload_id"]
                and row["payload_logical_sha256"]
                    == plan["payload_logical_sha256"]
                and row["payload_logical_sha256"]
                    == payload["logical_payload_sha256"]
                and row["variant_id"] == payload["variant_id"]
                and row["input_time_sha256"] == payload["time_sha256"]
                and row["input_flux_sha256"] == payload["flux_sha256"]
                and row["input_native_index_sha256"]
                    == payload["native_index_sha256"]
            )

            literal_fields = [
                "planned_decision_id",
                "decision_class",
                "phase3a_event_id",
                "variant_id",
                "matrix_cell_id",
                "window_variant_id",
                "processing_profile_id",
                "model_id",
                "model_name",
                "payload_id",
                "payload_logical_sha256",
                "afino_version",
                "afino_commit",
            ]
            literal_match = all(str(row[f]) == str(plan[f]) for f in literal_fields)
            if not (scientific_key_match and payload_match and literal_match):
                raise RuntimeError(
                    f"Canary/full-plan identity mismatch: {row['job_id']}"
                )

            values = [row[c] for c in result_columns]
            target.execute(
                f"INSERT INTO results ({cols}) VALUES ({placeholders})",
                values,
            )

            imported_core = target.execute(
                "SELECT result_core_sha256 FROM results WHERE job_id=?",
                (row["job_id"],),
            ).fetchone()[0]
            core_match = imported_core == row["result_core_sha256"]
            if not core_match:
                raise RuntimeError(
                    f"result_core_sha256 changed during import: {row['job_id']}"
                )

            audit_rows.append({
                "job_id": row["job_id"],
                "planned_decision_id": row["planned_decision_id"],
                "variant_id": row["variant_id"],
                "external_optimizer_seed": row["external_optimizer_seed"],
                "model_id": row["model_id"],
                "full_plan_match": "true",
                "payload_match": "true",
                "scientific_key_match": "true",
                "canary_result_core_sha256": row["result_core_sha256"],
                "imported_result_core_sha256": imported_core,
                "result_core_match": "true",
                "source_checkpoint_sha256": EXPECTED_CANARY_CHECKPOINT_SHA256,
                "bootstrap_status": "IMPORTED_VALIDATED_CANARY_RESULT",
            })

        target.commit()
    except Exception:
        target.rollback()
        raise
    finally:
        target.close()

    return audit_rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--afino-repo", type=Path, required=True)
    ap.add_argument("--execution-root", type=Path, required=True)
    ap.add_argument(
        "--full-checkpoint",
        type=Path,
        default=FULL_CHECKPOINT_REL,
    )
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()
    afino_repo = args.afino_repo.resolve()
    execution_root = args.execution_root.resolve()
    full_checkpoint = (
        args.full_checkpoint.resolve()
        if args.full_checkpoint.is_absolute()
        else (repo / args.full_checkpoint).resolve()
    )

    load_authorization(repo)
    verify_main_repo(repo)
    prepare_execution_root(repo, execution_root)

    initialize_full_checkpoint(
        repo,
        execution_root,
        afino_repo,
        full_checkpoint,
    )

    source_checkpoint = repo / CANARY_CHECKPOINT_REL
    audit_rows = import_canary(repo, full_checkpoint, source_checkpoint)
    write_csv(repo / BOOTSTRAP_AUDIT_REL, audit_rows, AUDIT_FIELDS)

    rows = checkpoint_rows(full_checkpoint)
    dup_jobs, dup_keys = duplicate_counts(full_checkpoint)

    if rows != 102:
        raise RuntimeError(f"Full checkpoint rows after bootstrap={rows}, expected 102.")
    if dup_jobs != 0 or dup_keys != 0:
        raise RuntimeError(
            f"Bootstrap duplicates: job_id={dup_jobs}, scientific_keys={dup_keys}"
        )
    if len(audit_rows) != 102:
        raise RuntimeError("Bootstrap audit does not contain 102 rows.")
    if not all(
        r["full_plan_match"] == "true"
        and r["payload_match"] == "true"
        and r["result_core_match"] == "true"
        for r in audit_rows
    ):
        raise RuntimeError("Bootstrap audit contains a failed row.")

    print("PHASE3A_F3A4_FULL_CHECKPOINT_BOOTSTRAP_PASS")
    print(f"execution_root={execution_root}")
    print(f"execution_root_head={F3A3_CANARY_PLAN_COMMIT}")
    print(f"full_checkpoint={full_checkpoint}")
    print("full_plan_jobs=22398")
    print("validated_canary_rows_imported=102")
    print("new_afino_calls_during_bootstrap=0")
    print("checkpoint_result_rows=102")
    print("remaining_new_jobs=22296")
    print("full_plan_match=102/102")
    print("payload_match=102/102")
    print("result_core_match=102/102")
    print(f"duplicate_job_ids={dup_jobs}")
    print(f"duplicate_scientific_keys={dup_keys}")
    print(f"source_canary_checkpoint_sha256={EXPECTED_CANARY_CHECKPOINT_SHA256}")
    print(f"full_checkpoint_sha256={sha256_file(full_checkpoint)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
