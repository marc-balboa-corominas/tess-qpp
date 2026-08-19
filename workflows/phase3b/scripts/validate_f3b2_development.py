#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

EXPECTED_HEAD = "467abe9d5fc8379e342f7c98d735aae12ad56ea1"
F3B1_COMMIT = "b8680934644be1bfec196e2009311b3060968f0a"
F3B1_TAG = "phase3b-design-v1"

EXPECTED_ENV = {
    "python_major_minor": (3, 13),
    "numpy_version": "2.3.5",
    "byteorder": "little",
}

EXPECTED_KEY_HASHES = {
    "workflows/phase3b/scripts/f3b_synthetic_generator.py":
        "d538d53c7845916e29c4dd351b85ae91076d5a342acb5619898788ef5d825d11",
    "workflows/phase3b/scripts/build_f3b2_generator_canary.py":
        "04508c681ba686d6fc8c70bcfdbb3211d99aeed7299e4e8b81e1fb9da27e91e2",
    "workflows/phase3b/scripts/materialize_f3b_development.py":
        "9624db78a8685f042b868ef90b2210a5ccb4e935ed27599e8fa18336333eed44",
    "workflows/phase3b/scripts/build_f3b2_development_plan.py":
        "fa706f32f3142546cfa45341fc0505b332967b89948ae0837a1e027ba433ad6d",
    "workflows/phase3b/development/config/f3b2_generator_implementation_binding.json":
        "b6519f84c0e6aa6b0c86cbd7a66dd79c1de1758e313d96ea4d750ebb212d9946",
    "workflows/phase3b/development/evidence/tables/f3b2_development_decision_grid.csv":
        "e3bb6c99647af5b8776ceb638868fdf88dd2d930cadd968126016cc47d319289",
    "workflows/phase3b/development/evidence/tables/f3b2_development_exact_afino_plan.csv":
        "7cb503b0c43c1251c28d828aa71707208ebca8fced4680f13662cb91ab2a2daf",
    "workflows/phase3b/development/evidence/reports/f3b2_development_materialization_report.md":
        "d750bbf83ef0f0228df792c0ff414a501b3fc7146cbbfca2c2994f9645fb1d43",
    "workflows/phase3b/tests/test_f3b2_generator_and_materialization.py":
        "1d7ed9d4af83d1052db04621c5679ad8ea1799c97e24c9d599a4ecf166381d66",
}

EXPECTED_PREVALIDATION_AUDIT_SHA = "cf1d1bd4b6695f1f16b1b93f05e1aee7789243dadb9cd2cea1e591772fc58f7b"
EXPECTED_PREVALIDATION_REGISTRY_SHA = "19e4ba5d93d39017e2843d2c06a2729369d0f06231f3838eed9be1d26dbabf83"
EXPECTED_HELDOUT_README_SHA = "9bd5944971a918a9bf5a3305d263a7ca39fedc83797704d62727942808e9184f"

MAT_AUDIT = Path(
    "workflows/phase3b/development/evidence/reports/"
    "f3b2_development_materialization_audit.json"
)
HELD_AUDIT = Path(
    "workflows/phase3b/development/evidence/reports/"
    "f3b2_heldout_nonmaterialization_audit.json"
)
LEAK_AUDIT = Path(
    "workflows/phase3b/development/evidence/reports/"
    "f3b2_development_leakage_audit.json"
)
BG_MANIFEST = Path(
    "workflows/phase3b/development/evidence/tables/"
    "f3b2_development_background_manifest.csv"
)
SERIES_MANIFEST = Path(
    "workflows/phase3b/development/evidence/tables/"
    "f3b2_development_series_manifest.csv"
)
TRUTH_LEDGER = Path(
    "workflows/phase3b/development/evidence/tables/"
    "f3b2_development_truth_ledger.csv"
)
ADMISSIBILITY = Path(
    "workflows/phase3b/development/evidence/tables/"
    "f3b2_development_admissibility.csv"
)
DECISION_GRID = Path(
    "workflows/phase3b/development/evidence/tables/"
    "f3b2_development_decision_grid.csv"
)
EXACT_PLAN = Path(
    "workflows/phase3b/development/evidence/tables/"
    "f3b2_development_exact_afino_plan.csv"
)
SHA_REGISTRY = Path(
    "workflows/phase3b/development/evidence/f3b2_SHA256SUMS.txt"
)
TEST_FILE = Path(
    "workflows/phase3b/tests/test_f3b2_generator_and_materialization.py"
)
VALIDATOR_FILE = Path(
    "workflows/phase3b/scripts/validate_f3b2_development.py"
)
ARRAY_DIR = Path("data/interim/phase3b/f3b2_development")
HELDOUT_ARRAY_DIR = Path("data/interim/phase3b/heldout")
HELDOUT_README = Path("workflows/phase3b/heldout/README.md")

EXPECTED_DIRTY_PATHS = {
    "workflows/phase3b/README.md",
    "workflows/phase3b/development/README.md",
    "workflows/phase3b/tests/test_f3b2_generator_and_materialization.py",
    "workflows/phase3b/development/evidence/f3b2_SHA256SUMS.txt",
    "workflows/phase3b/development/evidence/reports/f3b2_development_leakage_audit.json",
    "workflows/phase3b/development/evidence/reports/f3b2_development_materialization_audit.json",
    "workflows/phase3b/development/evidence/reports/f3b2_development_materialization_report.md",
    "workflows/phase3b/development/evidence/reports/f3b2_generator_validation_audit.json",
    "workflows/phase3b/development/evidence/reports/f3b2_heldout_nonmaterialization_audit.json",
    "workflows/phase3b/development/evidence/tables/f3b2_development_admissibility.csv",
    "workflows/phase3b/development/evidence/tables/f3b2_development_background_manifest.csv",
    "workflows/phase3b/development/evidence/tables/f3b2_development_decision_grid.csv",
    "workflows/phase3b/development/evidence/tables/f3b2_development_exact_afino_plan.csv",
    "workflows/phase3b/development/evidence/tables/f3b2_development_payload_manifest.csv",
    "workflows/phase3b/development/evidence/tables/f3b2_development_series_manifest.csv",
    "workflows/phase3b/development/evidence/tables/f3b2_development_truth_ledger.csv",
    "workflows/phase3b/development/evidence/tables/f3b2_generator_canary_manifest.csv",
    "workflows/phase3b/scripts/build_f3b2_development_plan.py",
    "workflows/phase3b/scripts/build_f3b2_generator_canary.py",
    "workflows/phase3b/scripts/materialize_f3b_development.py",
    "workflows/phase3b/scripts/validate_f3b2_development.py",
}


def run(repo: Path, *args: str, check: bool = True):
    cp = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and cp.returncode:
        raise RuntimeError(
            "git " + " ".join(args) + " failed: "
            + cp.stderr.decode(errors="replace").strip()
        )
    return cp


def gt(repo: Path, *args: str) -> str:
    return run(repo, *args).stdout.decode("utf-8", errors="replace").strip()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def verify_registry(repo: Path) -> int:
    evidence_root = repo / "workflows/phase3b/development/evidence"
    lines = (repo / SHA_REGISTRY).read_text(encoding="ascii").splitlines()
    if len(lines) != 13:
        raise RuntimeError(f"Evidence registry entry count {len(lines)} != 13.")
    for line in lines:
        digest, rel = line.split("  ", 1)
        path = evidence_root / rel
        if not path.is_file() or sha_file(path) != digest:
            raise RuntimeError("Evidence checksum mismatch: " + rel)
    return len(lines)


def regenerate_registry(repo: Path) -> int:
    evidence_root = repo / "workflows/phase3b/development/evidence"
    registry = repo / SHA_REGISTRY
    files = sorted(
        p for p in evidence_root.rglob("*")
        if p.is_file() and p != registry
    )
    if len(files) != 13:
        raise RuntimeError(f"Expected 13 evidence files, got {len(files)}.")
    text = "\n".join(
        f"{sha_file(p)}  {p.relative_to(evidence_root).as_posix()}"
        for p in files
    ) + "\n"
    registry.write_text(text, encoding="ascii", newline="\n")
    return len(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()
    repo = Path(args.repo_root).resolve()

    if sys.version_info[:2] != EXPECTED_ENV["python_major_minor"]:
        raise RuntimeError("Final validator Python major/minor mismatch.")
    if np.__version__ != EXPECTED_ENV["numpy_version"]:
        raise RuntimeError("Final validator NumPy mismatch.")
    if sys.byteorder != EXPECTED_ENV["byteorder"]:
        raise RuntimeError("Final validator byteorder mismatch.")

    if gt(repo, "rev-parse", "HEAD") != EXPECTED_HEAD:
        raise RuntimeError("Unexpected HEAD for F3B.2 final validation.")
    if gt(repo, "rev-parse", F3B1_TAG + "^{}") != F3B1_COMMIT:
        raise RuntimeError("F3B.1 tag mismatch.")
    if gt(repo, "diff", "--cached", "--name-only"):
        raise RuntimeError("Staged changes exist before F3B.2 final validation.")

    status_lines = run(
        repo, "status", "--short", "--untracked-files=all"
    ).stdout.decode("utf-8", errors="replace").splitlines()
    dirty = {
        line[3:].strip().replace("\\", "/")
        for line in status_lines if line.strip()
    }
    if dirty != EXPECTED_DIRTY_PATHS:
        raise RuntimeError(
            "Unexpected F3B.2 final-validation working tree: "
            + repr(sorted(dirty))
        )

    for rel, expected_sha in EXPECTED_KEY_HASHES.items():
        path = repo / rel
        if not path.is_file() or sha_file(path) != expected_sha:
            raise RuntimeError("F3B.2 key artifact SHA mismatch: " + rel)

    if sha_file(repo / MAT_AUDIT) != EXPECTED_PREVALIDATION_AUDIT_SHA:
        raise RuntimeError("Pre-validation materialization audit SHA mismatch.")
    if sha_file(repo / SHA_REGISTRY) != EXPECTED_PREVALIDATION_REGISTRY_SHA:
        raise RuntimeError("Pre-validation evidence registry SHA mismatch.")
    verify_registry(repo)

    if sha_file(repo / HELDOUT_README) != EXPECTED_HELDOUT_README_SHA:
        raise RuntimeError("HELDOUT README is not byte-exact to F3B.1.")
    if (repo / HELDOUT_ARRAY_DIR).exists():
        raise RuntimeError("HELDOUT array directory exists.")
    if not (repo / ARRAY_DIR).is_dir():
        raise RuntimeError("DEVELOPMENT array directory missing.")

    mat = json.loads((repo / MAT_AUDIT).read_text(encoding="utf-8"))
    held = json.loads((repo / HELD_AUDIT).read_text(encoding="utf-8"))
    leak = json.loads((repo / LEAK_AUDIT).read_text(encoding="utf-8"))

    required = {
        "development_registry_rows": 4320,
        "development_backgrounds": 1800,
        "primary_planned": 3600,
        "challenge_planned": 720,
        "positive_total": 2160,
        "null_total": 2160,
        "materialized_series": 4320,
        "materialization_failures": 0,
        "primary_eligible": 3600,
        "primary_inadmissible": 0,
        "baseline_decisions_planned": 3600,
        "stability_extra_decisions_planned": 648,
        "total_development_decisions_planned": 4248,
        "exact_model_calls_planned": 12744,
        "m0_calls_planned": 4248,
        "m1_calls_planned": 4248,
        "m2_calls_planned": 4248,
        "heldout_registry_rows": 4320,
        "heldout_materialized_rows": 0,
        "heldout_noise_draws": 0,
        "heldout_period_draws": 0,
    }
    for key, value in required.items():
        if mat.get(key) != value:
            raise RuntimeError(f"Final materialization audit mismatch: {key}")

    if mat["status"] != "PHASE3B_DEVELOPMENT_GENERATOR_VALIDATED_AND_MATERIALIZED":
        raise RuntimeError("Unexpected final F3B.2 materialization status.")
    if mat.get("afino_plan_frozen") is not True:
        raise RuntimeError("Exact AFINO plan is not frozen.")
    if mat.get("all_plan_jobs_execution_status") != "NOT_EXECUTED":
        raise RuntimeError("Exact AFINO plan has non-NOT_EXECUTED state.")
    for key in [
        "afino_executed", "candidate_rule_fitted",
        "candidate_thresholds_generated", "scientific_metrics_computed",
    ]:
        if mat.get(key) is not False:
            raise RuntimeError("Forbidden F3B.2 outcome state: " + key)

    if held["heldout_generated"] is not False or held["heldout_accessed"] is not False:
        raise RuntimeError("HELDOUT state violation.")
    if leak["background_split_overlap"] != 0:
        raise RuntimeError("DEVELOPMENT/HELDOUT background leakage.")

    # Physical arrays remain exactly those frozen in the materialization audit.
    for filename, expected_sha in mat["arrays"]["files"].items():
        path = repo / ARRAY_DIR / filename
        if not path.is_file() or sha_file(path) != expected_sha:
            raise RuntimeError("DEVELOPMENT physical array hash mismatch: " + filename)

    # Core table invariants.
    bg = read_csv(repo / BG_MANIFEST)
    series = read_csv(repo / SERIES_MANIFEST)
    truth = read_csv(repo / TRUTH_LEDGER)
    adm = read_csv(repo / ADMISSIBILITY)
    decisions = read_csv(repo / DECISION_GRID)
    plan = read_csv(repo / EXACT_PLAN)

    if not (len(bg) == 1800 and len(series) == len(truth) == len(adm) == 4320):
        raise RuntimeError("F3B.2 materialization row-count invariant failed.")
    if len(decisions) != 4248 or len(plan) != 12744:
        raise RuntimeError("F3B.2 plan row-count invariant failed.")
    if any(r["execution_status"] != "NOT_EXECUTED" for r in decisions):
        raise RuntimeError("Decision grid contains executed decision.")
    if any(r["execution_status"] != "NOT_EXECUTED" for r in plan):
        raise RuntimeError("Exact AFINO plan contains executed job.")

    # Historical scopes must still be untouched.
    for scope in [
        "foundation/f0-f2",
        "docs/literature/bibliographic_audit_ii",
        "workflows/phase3a",
    ]:
        if gt(repo, "diff", "--name-only", F3B1_COMMIT, "--", scope):
            raise RuntimeError("Protected historical scope changed: " + scope)

    # Run the complete F3B.2 test contract before declaring closure validation.
    pytest_cmd = [
        sys.executable, "-m", "pytest",
        str(repo / TEST_FILE), "-q",
    ]
    cp = subprocess.run(
        pytest_cmd,
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print(cp.stdout, end="")
    if cp.returncode != 0:
        raise RuntimeError("F3B.2 pytest contract failed.")
    if "21 passed" not in cp.stdout:
        raise RuntimeError("Expected 21 passed tests in final F3B.2 contract.")

    # Only after all independent checks + pytest pass do we close the
    # materialization audit and regenerate its evidence checksum registry.
    mat["f3b2_closure_validation_pending"] = False
    mat["f3b2_closure_validation_result"] = (
        "PHASE3B_DEVELOPMENT_GENERATOR_VALIDATION_PASS"
    )
    mat["f3b2_closure_validation_environment"] = {
        "python_version": sys.version.split()[0],
        "python_major_minor": list(sys.version_info[:2]),
        "numpy_version": np.__version__,
        "byteorder": sys.byteorder,
    }
    mat["f3b2_closure_validator"] = {
        "path": VALIDATOR_FILE.as_posix(),
        "sha256": sha_file(repo / VALIDATOR_FILE),
    }
    mat["f3b2_test_contract"] = {
        "path": TEST_FILE.as_posix(),
        "sha256": sha_file(repo / TEST_FILE),
        "pytest_result": "21 passed",
    }
    mat["git_osf_freeze_pending"] = True
    mat["afino_executed"] = False
    mat["candidate_rule_fitted"] = False
    mat["candidate_thresholds_generated"] = False
    mat["scientific_metrics_computed"] = False

    (repo / MAT_AUDIT).write_text(
        json.dumps(mat, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    entries = regenerate_registry(repo)
    verify_registry(repo)

    print("PHASE3B_DEVELOPMENT_GENERATOR_VALIDATION_PASS")
    print("pytest = 21 passed")
    print("development_backgrounds = 1800")
    print("development_series = 4320")
    print("primary_eligible = 3600")
    print("challenge_input_inadmissible = 720")
    print("baseline_decisions_planned = 3600")
    print("stability_extra_decisions_planned = 648")
    print("total_development_decisions_planned = 4248")
    print("exact_model_calls_planned = 12744")
    print("all_plan_jobs_execution_status = NOT_EXECUTED")
    print("background_roundtrip_mismatches = 0")
    print("series_roundtrip_mismatches = 0")
    print("rematerialization_mismatches = 0")
    print("heldout_generated = false")
    print("heldout_accessed = false")
    print("heldout_stochastic_draws = 0")
    print("afino_executed = false")
    print("candidate_rule_fitted = false")
    print("scientific_metrics_computed = false")
    print("protected_scopes_modified = false")
    print("evidence_checksum_entries =", entries)
    print("materialization_audit_final_sha256 =", sha_file(repo / MAT_AUDIT))
    print("evidence_sha_registry_final_sha256 =", sha_file(repo / SHA_REGISTRY))
    print("git_osf_freeze_pending = true")
    print("NEXT = inspect final status; then explicit staging + final Git/OSF freeze")

if __name__ == "__main__":
    main()
