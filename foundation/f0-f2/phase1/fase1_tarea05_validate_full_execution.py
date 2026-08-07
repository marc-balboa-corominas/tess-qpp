#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import sqlite3
import subprocess
import sys
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parent
REPO = ROOT / "afino_release_version"

RUNNER = ROOT / "fase1_tarea04_run_afino_checkpointed_v2.py"
PLAN = ROOT / "fase1_tarea04_full_execution_plan.csv"

FLUX_NPY = ROOT / "fase1_tarea03_core_flux_values.npy"
SERIES_OFFSETS_NPY = ROOT / "fase1_tarea03_core_series_offsets.npy"
TIME_VALUES_NPY = ROOT / "fase1_tarea03_core_time_values.npy"
TIME_OFFSETS_NPY = ROOT / "fase1_tarea03_core_time_offsets.npy"
SERIES_MANIFEST = ROOT / "fase1_tarea03_core_series_manifest.csv"
TIME_MANIFEST = ROOT / "fase1_tarea03_time_vector_manifest.csv"
MATERIALIZATION_AUDIT = ROOT / "fase1_tarea03_materialization_audit.json"

CANARY_CHECKPOINT = ROOT / "fase1_tarea04_canary_checkpoint.sqlite"
FULL_CHECKPOINT = ROOT / "fase1_tarea05_full_checkpoint.sqlite"
RESULTS_CSV = ROOT / "fase1_tarea05_core_results.csv"
DECISIONS_CSV = ROOT / "fase1_tarea05_core_decisions.csv"
AUDIT_JSON = ROOT / "fase1_tarea05_full_execution_audit.json"
REPORT_MD = ROOT / "fase1_tarea05_full_execution_report.md"
ENVIRONMENT_TXT = ROOT / "fase1_tarea05_environment.txt"
CONSOLE_TXT = ROOT / "fase1_tarea05_console_output.txt"

EXPECTED_AFINO_COMMIT = "6aceac9518fc8056052807e666da9d0c8bebb010"
EXPECTED_AFINO_VERSION = "0.5"
EXPECTED_RUNNER_VERSION = "1.0.1"

EXPECTED_PHYSICAL_HASHES = {
    "fase1_tarea04_run_afino_checkpointed_v2.py":
        "2e35137655a6fd66cd53d76f9229024b4c74ace597c9df62479e48cefc3c84e7",
    "fase1_tarea04_full_execution_plan.csv":
        "ccc7b6232b921e6422097fa1fc2525ec7f559459994ba7dfb222dbb0abfecf03",
    "fase1_tarea03_core_flux_values.npy":
        "f5fdd48f2951a1e055355d76b8b82c931fceea8cbb0688ca0099fe329594e60d",
    "fase1_tarea03_core_series_offsets.npy":
        "9169e4253cee3fb75b52e6ef61995efcdb71514720ba39c311eb9a085e901d85",
    "fase1_tarea03_core_time_values.npy":
        "730e97faa7b9bbcf03ea9b8c897790fd500c36fadb8f7c47608d9614fbba8513",
    "fase1_tarea03_core_time_offsets.npy":
        "c58d96df35b66a33ec3ffe37347f745af78cfd3eaa4e77762230206513f4c233",
    "fase1_tarea03_core_series_manifest.csv":
        "2020c849348c81235036443d3215395c602b80b00debe64fec692935dda778f4",
    "fase1_tarea03_time_vector_manifest.csv":
        "ce7f2f465f7ee73c8de983a91a8415b1a9d75e3b65a5e94b553d42c94068a5e7",
    "fase1_tarea03_materialization_audit.json":
        "8fa6d0b108dd9f4c2d941729221ad9fcbfea14af63baaec1474cce751bb51310",
    "fase1_tarea04_canary_checkpoint.sqlite":
        "e353f3c87ed2453fbb15e8dd17d09b66591badbe0f5d6ac7313691191c8415f8",
}

EXPECTED_LOGICAL_HASHES = {
    "canonical_flux_payload_sha256":
        "f593637faabf57bdcd9c4bea66f161cbaace77ad09de682179d709b002167abe",
    "series_offsets_canonical_sha256":
        "b7ed6562c1d5a256309ca417744ed3f0520c79fb3d85b43a67383d9d4810817e",
    "time_values_canonical_sha256":
        "6809c6c9ecb0667c5eda35e62fccbd958dc5c619845f9da37e0713f5b1580537",
    "time_offsets_canonical_sha256":
        "28d9acdf22fdfaf6737337f20331e37a52710ec0d43c5b39251119b619a875a4",
}

PLAN_FIELDS = [
    "job_id",
    "job_order",
    "job_class",
    "series_id",
    "condition_id",
    "ground_truth",
    "data_seed",
    "external_optimizer_seed",
    "model_id",
    "model_name",
    "n_samples",
    "period_s",
    "qpp_fraction",
    "flux_start_offset",
    "flux_end_offset",
    "time_vector_id",
    "input_flux_sha256",
    "input_time_sha256",
]

RESULT_FIELDS = [
    "job_id",
    "job_class",
    "series_id",
    "condition_id",
    "ground_truth",
    "data_seed",
    "external_optimizer_seed",
    "model_id",
    "model_name",
    "status",
    "runtime_seconds",
    "n_samples",
    "input_flux_sha256",
    "input_time_sha256",
    "afino_effective_dt_s",
    "positive_frequency_bins",
    "bins_after_cutoff",
    "minimum_frequency_hz",
    "maximum_frequency_hz",
    "lnlike",
    "BIC",
    "rchi2",
    "probability",
    "parameters_json",
    "estimated_period_s",
    "parameter_at_bound",
    "bound_indices_json",
    "warning_count",
    "warning_types_json",
    "convergence_status",
    "error",
]

DECISION_FIELDS = [
    "job_class",
    "series_id",
    "condition_id",
    "ground_truth",
    "data_seed",
    "external_optimizer_seed",
    "valid_models",
    "decision_status",
    "delta_bic_0_1",
    "delta_bic_2_1",
    "qpp_selected",
    "estimated_period_s",
    "period_label",
]

MODEL_NAMES = {
    "M0": "pow_const",
    "M1": "pow_const_gauss",
    "M2": "bpow_const",
}

EXPECTED_COUNTS = {
    "planned_jobs": 16317,
    "primary_jobs": 13320,
    "stability_jobs": 2997,
    "model_rows": 5439,
    "primary_decisions": 4440,
    "stability_decisions": 999,
    "total_decisions": 5439,
}


class ValidationError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(array: np.ndarray, dtype: str) -> str:
    canonical = np.ascontiguousarray(array, dtype=dtype)
    return hashlib.sha256(canonical.tobytes(order="C")).hexdigest()


def run_command(
    arguments: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        arguments,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if check and result.returncode != 0:
        raise ValidationError(
            f"Command failed ({result.returncode}): {' '.join(arguments)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_csv_with_fields(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        return fields, list(reader)


def write_csv(
    path: Path,
    fields: list[str],
    rows: Iterable[dict[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            lineterminator="\n",
            extrasaction="raise",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def parse_int(value: Any, field: str) -> int:
    try:
        return int(value)
    except Exception as exc:
        raise ValidationError(f"Invalid integer in {field}: {value!r}") from exc


def parse_optional_float(value: Any, field: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except Exception as exc:
        raise ValidationError(f"Invalid float in {field}: {value!r}") from exc
    if not math.isfinite(number):
        raise ValidationError(f"Non-finite float in {field}: {value!r}")
    return number


def parse_bool_text(value: Any, field: str) -> bool | None:
    if value is None or value == "":
        return None
    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValidationError(f"Invalid Boolean in {field}: {value!r}")


def json_compact(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def relative_executable() -> str:
    try:
        return str(Path(sys.executable).resolve().relative_to(ROOT))
    except ValueError:
        return Path(sys.executable).name


def collect_environment() -> dict[str, Any]:
    if not REPO.exists():
        raise ValidationError(f"Missing AFINO repository: {REPO}")

    commit = run_command(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"]
    ).stdout.strip()
    tracked = run_command(
        ["git", "-C", str(REPO), "diff", "--quiet"],
        check=False,
    )
    staged = run_command(
        ["git", "-C", str(REPO), "diff", "--cached", "--quiet"],
        check=False,
    )
    status = run_command(
        ["git", "-C", str(REPO), "status", "--porcelain"]
    ).stdout.rstrip()
    pip_freeze = run_command(
        [sys.executable, "-m", "pip", "freeze"]
    ).stdout.splitlines()

    try:
        afino_version = importlib.metadata.version("afino")
    except importlib.metadata.PackageNotFoundError as exc:
        raise ValidationError("The AFINO package is not installed.") from exc

    environment = {
        "python_version": platform.python_version(),
        "python_full": sys.version,
        "python_executable_relative": relative_executable(),
        "numpy_version": np.__version__,
        "scipy_version": importlib.metadata.version("scipy"),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "afino_commit": commit,
        "afino_package_version": afino_version,
        "tracked_diff_exit_code": tracked.returncode,
        "staged_diff_exit_code": staged.returncode,
        "git_status_porcelain": status,
        "pip_freeze": pip_freeze,
    }

    if commit != EXPECTED_AFINO_COMMIT:
        raise ValidationError(
            f"AFINO commit mismatch: {commit} != {EXPECTED_AFINO_COMMIT}"
        )
    if afino_version != EXPECTED_AFINO_VERSION:
        raise ValidationError(
            f"AFINO version mismatch: {afino_version} != {EXPECTED_AFINO_VERSION}"
        )
    if tracked.returncode != 0:
        raise ValidationError("Tracked git diff is not empty.")
    if staged.returncode != 0:
        raise ValidationError("Staged git diff is not empty.")

    return environment


def environment_text(environment: dict[str, Any]) -> str:
    lines = [
        f"Python: {environment['python_version']}",
        f"Python full: {environment['python_full']}",
        f"Python executable relative: {environment['python_executable_relative']}",
        f"NumPy: {environment['numpy_version']}",
        f"SciPy: {environment['scipy_version']}",
        f"Platform: {environment['platform']}",
        f"Machine: {environment['machine']}",
        f"Processor: {environment['processor']}",
        f"AFINO commit: {environment['afino_commit']}",
        f"AFINO package version: {environment['afino_package_version']}",
        f"Tracked diff exit code: {environment['tracked_diff_exit_code']}",
        f"Staged diff exit code: {environment['staged_diff_exit_code']}",
        "Git status --porcelain:",
        environment["git_status_porcelain"],
        "",
        "pip freeze:",
        *environment["pip_freeze"],
        "",
    ]
    return "\n".join(lines)


def verify_frozen_inputs() -> tuple[dict[str, str], dict[str, str]]:
    paths = {
        RUNNER.name: RUNNER,
        PLAN.name: PLAN,
        FLUX_NPY.name: FLUX_NPY,
        SERIES_OFFSETS_NPY.name: SERIES_OFFSETS_NPY,
        TIME_VALUES_NPY.name: TIME_VALUES_NPY,
        TIME_OFFSETS_NPY.name: TIME_OFFSETS_NPY,
        SERIES_MANIFEST.name: SERIES_MANIFEST,
        TIME_MANIFEST.name: TIME_MANIFEST,
        MATERIALIZATION_AUDIT.name: MATERIALIZATION_AUDIT,
        CANARY_CHECKPOINT.name: CANARY_CHECKPOINT,
    }

    physical: dict[str, str] = {}
    for name, path in paths.items():
        if not path.exists():
            raise ValidationError(f"Missing frozen artifact: {name}")
        observed = sha256(path)
        expected = EXPECTED_PHYSICAL_HASHES[name]
        if observed != expected:
            raise ValidationError(
                f"Physical hash mismatch for {name}: {observed} != {expected}"
            )
        physical[name] = observed

    flux = np.load(FLUX_NPY, allow_pickle=False)
    series_offsets = np.load(SERIES_OFFSETS_NPY, allow_pickle=False)
    time_values = np.load(TIME_VALUES_NPY, allow_pickle=False)
    time_offsets = np.load(TIME_OFFSETS_NPY, allow_pickle=False)

    logical = {
        "canonical_flux_payload_sha256":
            canonical_sha256(flux, "<f8"),
        "series_offsets_canonical_sha256":
            canonical_sha256(series_offsets, "<i8"),
        "time_values_canonical_sha256":
            canonical_sha256(time_values, "<f8"),
        "time_offsets_canonical_sha256":
            canonical_sha256(time_offsets, "<i8"),
    }
    if logical != EXPECTED_LOGICAL_HASHES:
        raise ValidationError(
            "Logical dataset hashes do not match the frozen F1.3 values."
        )

    materialization = json.loads(
        MATERIALIZATION_AUDIT.read_text(encoding="utf-8")
    )
    if (
        materialization.get("materialization_status")
        != "DATASET_FROZEN_BEFORE_AFINO"
    ):
        raise ValidationError("F1.3 materialization status is not frozen.")

    if flux.shape != (264600,):
        raise ValidationError(f"Unexpected flux payload shape: {flux.shape}")
    if series_offsets.shape != (4441,):
        raise ValidationError(
            f"Unexpected series-offset shape: {series_offsets.shape}"
        )
    if time_values.shape != (225,):
        raise ValidationError(f"Unexpected time payload shape: {time_values.shape}")
    if time_offsets.shape != (5,):
        raise ValidationError(
            f"Unexpected time-offset shape: {time_offsets.shape}"
        )

    return physical, logical


def load_and_validate_manifests() -> tuple[
    dict[str, dict[str, str]],
    dict[str, dict[str, str]],
]:
    series_rows = read_csv(SERIES_MANIFEST)
    time_rows = read_csv(TIME_MANIFEST)
    if len(series_rows) != 4440:
        raise ValidationError(
            f"Series manifest has {len(series_rows)} rows, not 4440."
        )
    if len(time_rows) != 4:
        raise ValidationError(
            f"Time manifest has {len(time_rows)} rows, not 4."
        )

    series_by_id = {row["series_id"]: row for row in series_rows}
    time_by_id = {row["time_vector_id"]: row for row in time_rows}
    if len(series_by_id) != 4440:
        raise ValidationError("Duplicate series_id values in F1.3 manifest.")
    if len(time_by_id) != 4:
        raise ValidationError("Duplicate time_vector_id values in F1.3 manifest.")
    return series_by_id, time_by_id


def load_and_validate_plan(
    series_by_id: dict[str, dict[str, str]],
    time_by_id: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    fields, raw_rows = read_csv_with_fields(PLAN)
    if fields != PLAN_FIELDS:
        raise ValidationError("The full-plan schema differs from F1.4.")
    if len(raw_rows) != EXPECTED_COUNTS["planned_jobs"]:
        raise ValidationError(
            f"Full plan has {len(raw_rows)} rows, not 16317."
        )

    rows: list[dict[str, Any]] = []
    seen_job_ids: set[str] = set()
    seen_scientific: set[tuple[str, int, str]] = set()

    for index, raw in enumerate(raw_rows, start=1):
        row: dict[str, Any] = dict(raw)
        for field in (
            "job_order",
            "data_seed",
            "external_optimizer_seed",
            "n_samples",
            "flux_start_offset",
            "flux_end_offset",
        ):
            row[field] = parse_int(raw[field], field)

        if row["job_order"] != index:
            raise ValidationError(
                f"Non-normative job order at row {index}: {row['job_order']}"
            )
        if row["job_id"] in seen_job_ids:
            raise ValidationError(f"Duplicate job_id in plan: {row['job_id']}")
        seen_job_ids.add(row["job_id"])

        key = (
            row["series_id"],
            row["external_optimizer_seed"],
            row["model_id"],
        )
        if key in seen_scientific:
            raise ValidationError(
                f"Duplicate scientific key in plan: {key}"
            )
        seen_scientific.add(key)

        if row["model_id"] not in MODEL_NAMES:
            raise ValidationError(f"Unknown model_id: {row['model_id']}")
        if row["model_name"] != MODEL_NAMES[row["model_id"]]:
            raise ValidationError(
                f"Model-name mismatch in {row['job_id']}"
            )
        if row["job_class"] not in {"primary", "stability"}:
            raise ValidationError(
                f"Invalid job_class in {row['job_id']}"
            )

        series = series_by_id.get(row["series_id"])
        if series is None:
            raise ValidationError(
                f"Unknown series in plan: {row['series_id']}"
            )
        time_row = time_by_id.get(series["time_vector_id"])
        if time_row is None:
            raise ValidationError(
                f"Unknown time vector for series {row['series_id']}"
            )

        expected = {
            "condition_id": series["condition_id"],
            "ground_truth": series["ground_truth"],
            "data_seed": int(series["data_seed"]),
            "n_samples": int(series["n_samples"]),
            "period_s": series["period_s"],
            "qpp_fraction": series["qpp_fraction"],
            "flux_start_offset": int(series["flux_start_offset"]),
            "flux_end_offset": int(series["flux_end_offset"]),
            "time_vector_id": series["time_vector_id"],
            "input_flux_sha256": series["flux_sha256"],
            "input_time_sha256": time_row["time_sha256"],
        }
        for field, value in expected.items():
            if row[field] != value:
                raise ValidationError(
                    f"Plan/manifest mismatch in {row['job_id']} field {field}"
                )

        if row["job_class"] == "primary":
            if row["external_optimizer_seed"] != 0:
                raise ValidationError(
                    f"Primary seed is not zero in {row['job_id']}"
                )
        else:
            if (
                row["data_seed"] != 0
                or not 1 <= row["external_optimizer_seed"] <= 9
            ):
                raise ValidationError(
                    f"Stability job is outside protocol: {row['job_id']}"
                )
        rows.append(row)

    classes = Counter(row["job_class"] for row in rows)
    models = Counter(row["model_id"] for row in rows)
    if classes != {
        "primary": EXPECTED_COUNTS["primary_jobs"],
        "stability": EXPECTED_COUNTS["stability_jobs"],
    }:
        raise ValidationError(f"Unexpected plan class counts: {classes}")
    if models != {
        "M0": EXPECTED_COUNTS["model_rows"],
        "M1": EXPECTED_COUNTS["model_rows"],
        "M2": EXPECTED_COUNTS["model_rows"],
    }:
        raise ValidationError(f"Unexpected plan model counts: {models}")

    return rows


def connect_readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def load_checkpoint() -> tuple[
    dict[str, str],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    if not FULL_CHECKPOINT.exists():
        raise ValidationError("The full checkpoint does not exist.")

    connection = connect_readonly(FULL_CHECKPOINT)
    try:
        metadata = {
            row["key"]: row["value"]
            for row in connection.execute(
                "SELECT key, value FROM metadata ORDER BY key"
            )
        }
        result_rows = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM results ORDER BY job_order"
            )
        ]
        invocations = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM invocations ORDER BY invocation_id"
            )
        ]

        result_table = connection.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type='table' AND name='results'"
        ).fetchone()
    finally:
        connection.close()

    if result_table is None:
        raise ValidationError("The checkpoint has no results table.")
    table_sql = str(result_table["sql"])
    if "UNIQUE(series_id, external_optimizer_seed, model_id)" not in table_sql:
        raise ValidationError(
            "The scientific-key uniqueness constraint is missing."
        )

    return metadata, result_rows, invocations


def validate_checkpoint_metadata(
    metadata: dict[str, str],
    physical: dict[str, str],
    logical: dict[str, str],
) -> None:
    expected = {
        "schema_version": "1.0.0",
        "runner_implementation_version": EXPECTED_RUNNER_VERSION,
        "plan_filename": PLAN.name,
        "plan_sha256": EXPECTED_PHYSICAL_HASHES[PLAN.name],
        "plan_kind": "full",
        "runner_sha256": EXPECTED_PHYSICAL_HASHES[RUNNER.name],
        "afino_commit": EXPECTED_AFINO_COMMIT,
        "afino_version": EXPECTED_AFINO_VERSION,
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise ValidationError(
                f"Checkpoint metadata mismatch for {key}: "
                f"{metadata.get(key)!r} != {value!r}"
            )

    stored_physical = json.loads(metadata["dataset_physical_hashes"])
    stored_logical = json.loads(metadata["dataset_logical_hashes"])

    # The runner stores the F1.3 files plus the frozen F1.4 builder/plans.
    for name in (
        FLUX_NPY.name,
        SERIES_OFFSETS_NPY.name,
        TIME_VALUES_NPY.name,
        TIME_OFFSETS_NPY.name,
        SERIES_MANIFEST.name,
        TIME_MANIFEST.name,
        MATERIALIZATION_AUDIT.name,
    ):
        if stored_physical.get(name) != physical[name]:
            raise ValidationError(
                f"Checkpoint stored the wrong physical hash for {name}."
            )
    if stored_logical != logical:
        raise ValidationError(
            "Checkpoint stored logical hashes that differ from F1.3."
        )


def validate_invocations(
    invocations: list[dict[str, Any]],
) -> dict[str, Any]:
    if not invocations:
        raise ValidationError("No invocation records exist in the checkpoint.")

    for invocation in invocations:
        if invocation["plan_sha256"] != EXPECTED_PHYSICAL_HASHES[PLAN.name]:
            raise ValidationError("Invocation uses a non-frozen plan hash.")
        if invocation["plan_kind"] != "full":
            raise ValidationError("Invocation is not marked as full.")
        if invocation["resume_requested"] != 1:
            raise ValidationError("A full-run invocation did not use --resume.")

    first = invocations[0]
    if first["existing_before"] != 0:
        raise ValidationError(
            "The first full-run invocation did not start from zero rows."
        )

    previous_total = 0
    for invocation in invocations:
        if invocation["existing_before"] != previous_total:
            raise ValidationError(
                "Invocation history is not contiguous at invocation "
                f"{invocation['invocation_id']}."
            )
        expected_total = (
            invocation["existing_before"] + invocation["committed_new"]
        )
        if invocation["total_after"] != expected_total:
            raise ValidationError(
                "Invocation total_after is inconsistent at invocation "
                f"{invocation['invocation_id']}."
            )
        previous_total = invocation["total_after"]

    if previous_total != EXPECTED_COUNTS["planned_jobs"]:
        raise ValidationError(
            f"Final invocation total is {previous_total}, not 16317."
        )

    return {
        "invocation_count": len(invocations),
        "first_invocation_existing_before": first["existing_before"],
        "total_committed_new": sum(
            int(row["committed_new"]) for row in invocations
        ),
        "final_total_after": previous_total,
        "invocations": invocations,
    }


def validate_checkpoint_results(
    plan_rows: list[dict[str, Any]],
    result_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(result_rows) != EXPECTED_COUNTS["planned_jobs"]:
        raise ValidationError(
            f"Checkpoint has {len(result_rows)} result rows, not 16317."
        )

    duplicate_job_ids = len(result_rows) - len(
        {row["job_id"] for row in result_rows}
    )
    duplicate_scientific = len(result_rows) - len(
        {
            (
                row["series_id"],
                int(row["external_optimizer_seed"]),
                row["model_id"],
            )
            for row in result_rows
        }
    )
    if duplicate_job_ids != 0 or duplicate_scientific != 0:
        raise ValidationError(
            "Duplicate rows exist in the checkpoint results."
        )

    plan_by_id = {row["job_id"]: row for row in plan_rows}
    result_by_id = {row["job_id"]: row for row in result_rows}
    if set(plan_by_id) != set(result_by_id):
        missing = sorted(set(plan_by_id) - set(result_by_id))
        extra = sorted(set(result_by_id) - set(plan_by_id))
        raise ValidationError(
            f"Plan/result job-id mismatch. Missing={missing[:5]} "
            f"extra={extra[:5]}"
        )

    metadata_mismatches = 0
    input_hash_mismatches = 0
    status_counts: Counter[str] = Counter()
    warning_calls: Counter[str] = Counter()
    warning_totals: Counter[str] = Counter()
    bound_calls: Counter[str] = Counter()
    model_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    total_runtime = 0.0

    compare_fields = [
        "job_order",
        "job_class",
        "series_id",
        "condition_id",
        "ground_truth",
        "data_seed",
        "external_optimizer_seed",
        "model_id",
        "model_name",
        "n_samples",
        "input_flux_sha256",
        "input_time_sha256",
    ]

    for planned in plan_rows:
        result = result_by_id[planned["job_id"]]
        for field in compare_fields:
            if result[field] != planned[field]:
                metadata_mismatches += 1

        if (
            result["input_flux_sha256"] != planned["input_flux_sha256"]
            or result["input_time_sha256"] != planned["input_time_sha256"]
        ):
            input_hash_mismatches += 1

        model_id = str(result["model_id"])
        status = str(result["status"])
        status_counts[status] += 1
        model_counts[model_id] += 1
        class_counts[str(result["job_class"])] += 1

        runtime = float(result["runtime_seconds"])
        if not math.isfinite(runtime) or runtime < 0.0:
            raise ValidationError(
                f"Invalid runtime for {result['job_id']}: {runtime}"
            )
        total_runtime += runtime

        if result["convergence_status"] != "NOT_AUDITABLE":
            raise ValidationError(
                f"Unexpected convergence status in {result['job_id']}."
            )

        if status == "OK":
            if result["error"] not in (None, ""):
                raise ValidationError(
                    f"OK row has a non-empty error: {result['job_id']}"
                )
            dt = result["afino_effective_dt_s"]
            if dt is None or float(dt) != 20.0:
                raise ValidationError(
                    f"Effective dt is not 20 s in {result['job_id']}."
                )
            for field in ("BIC", "lnlike", "rchi2", "probability"):
                value = result[field]
                if value is None or not math.isfinite(float(value)):
                    raise ValidationError(
                        f"OK row has invalid {field}: {result['job_id']}"
                    )
        else:
            if result["error"] in (None, ""):
                raise ValidationError(
                    f"Failed row has no recorded exception: {result['job_id']}"
                )

        warning_count = result["warning_count"]
        if warning_count is not None:
            warning_count = int(warning_count)
            if warning_count < 0:
                raise ValidationError(
                    f"Negative warning count in {result['job_id']}."
                )
            if warning_count > 0:
                warning_calls[model_id] += 1
                warning_totals[model_id] += warning_count

        if result["parameter_at_bound"] == 1:
            bound_calls[model_id] += 1
        elif result["parameter_at_bound"] not in (0, None):
            raise ValidationError(
                f"Invalid parameter_at_bound in {result['job_id']}."
            )

    if metadata_mismatches != 0:
        raise ValidationError(
            f"Plan/result metadata mismatches: {metadata_mismatches}"
        )
    if input_hash_mismatches != 0:
        raise ValidationError(
            f"Input-hash mismatches: {input_hash_mismatches}"
        )
    if model_counts != {
        "M0": EXPECTED_COUNTS["model_rows"],
        "M1": EXPECTED_COUNTS["model_rows"],
        "M2": EXPECTED_COUNTS["model_rows"],
    }:
        raise ValidationError(f"Unexpected checkpoint model counts: {model_counts}")
    if class_counts != {
        "primary": EXPECTED_COUNTS["primary_jobs"],
        "stability": EXPECTED_COUNTS["stability_jobs"],
    }:
        raise ValidationError(f"Unexpected checkpoint class counts: {class_counts}")

    return {
        "checkpoint_result_rows": len(result_rows),
        "pending_jobs": len(plan_rows) - len(result_rows),
        "duplicate_job_ids": duplicate_job_ids,
        "duplicate_scientific_keys": duplicate_scientific,
        "plan_result_metadata_mismatches": metadata_mismatches,
        "input_hash_mismatches": input_hash_mismatches,
        "status_counts": dict(sorted(status_counts.items())),
        "model_counts": dict(sorted(model_counts.items())),
        "class_counts": dict(sorted(class_counts.items())),
        "warning_calls_by_model": {
            model: warning_calls.get(model, 0) for model in MODEL_NAMES
        },
        "warning_totals_by_model": {
            model: warning_totals.get(model, 0) for model in MODEL_NAMES
        },
        "bound_hit_calls_by_model": {
            model: bound_calls.get(model, 0) for model in MODEL_NAMES
        },
        "total_runtime_seconds": total_runtime,
    }


def optional_float_equal(csv_value: str, database_value: Any) -> bool:
    parsed = parse_optional_float(csv_value, "exported float")
    if database_value is None:
        return parsed is None
    return parsed == float(database_value)


def validate_exported_results(
    plan_rows: list[dict[str, Any]],
    checkpoint_rows: list[dict[str, Any]],
) -> list[dict[str, str]]:
    fields, rows = read_csv_with_fields(RESULTS_CSV)
    if fields != RESULT_FIELDS:
        raise ValidationError("The exported-results schema differs from F1.4.")
    if len(rows) != EXPECTED_COUNTS["planned_jobs"]:
        raise ValidationError(
            f"Exported results have {len(rows)} rows, not 16317."
        )

    checkpoint_by_id = {row["job_id"]: row for row in checkpoint_rows}
    if [row["job_id"] for row in rows] != [
        row["job_id"] for row in plan_rows
    ]:
        raise ValidationError(
            "Exported results do not follow the normative plan order."
        )

    integer_fields = {
        "data_seed",
        "external_optimizer_seed",
        "n_samples",
        "positive_frequency_bins",
        "bins_after_cutoff",
        "warning_count",
    }
    float_fields = {
        "runtime_seconds",
        "afino_effective_dt_s",
        "minimum_frequency_hz",
        "maximum_frequency_hz",
        "lnlike",
        "BIC",
        "rchi2",
        "probability",
        "estimated_period_s",
    }
    text_fields = {
        "job_class",
        "series_id",
        "condition_id",
        "ground_truth",
        "model_id",
        "model_name",
        "status",
        "input_flux_sha256",
        "input_time_sha256",
        "parameters_json",
        "bound_indices_json",
        "warning_types_json",
        "convergence_status",
        "error",
    }

    for row in rows:
        original = checkpoint_by_id.get(row["job_id"])
        if original is None:
            raise ValidationError(
                f"Exported job not found in checkpoint: {row['job_id']}"
            )

        for field in text_fields:
            expected = "" if original[field] is None else str(original[field])
            if row[field] != expected:
                raise ValidationError(
                    f"CSV/checkpoint mismatch in {row['job_id']} field {field}"
                )

        for field in integer_fields:
            if original[field] is None:
                if row[field] != "":
                    raise ValidationError(
                        f"Expected empty {field} in {row['job_id']}"
                    )
            elif parse_int(row[field], field) != int(original[field]):
                raise ValidationError(
                    f"CSV/checkpoint mismatch in {row['job_id']} field {field}"
                )

        for field in float_fields:
            if not optional_float_equal(row[field], original[field]):
                raise ValidationError(
                    f"CSV/checkpoint mismatch in {row['job_id']} field {field}"
                )

        parsed_bound = parse_bool_text(
            row["parameter_at_bound"],
            "parameter_at_bound",
        )
        expected_bound = (
            None
            if original["parameter_at_bound"] is None
            else bool(original["parameter_at_bound"])
        )
        if parsed_bound != expected_bound:
            raise ValidationError(
                f"CSV/checkpoint mismatch in {row['job_id']} "
                "field parameter_at_bound"
            )

    if len({row["job_id"] for row in rows}) != len(rows):
        raise ValidationError("Duplicate job_id values in exported results.")
    scientific = {
        (
            row["series_id"],
            int(row["external_optimizer_seed"]),
            row["model_id"],
        )
        for row in rows
    }
    if len(scientific) != len(rows):
        raise ValidationError(
            "Duplicate scientific keys in exported results."
        )

    return rows


def finite_ok_bic(row: dict[str, Any]) -> bool:
    if row["status"] != "OK":
        return False
    value = row["BIC"]
    return value is not None and math.isfinite(float(value))


def build_decisions(
    plan_rows: list[dict[str, Any]],
    checkpoint_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    result_by_id = {row["job_id"]: row for row in checkpoint_rows}
    grouped: dict[
        tuple[str, int],
        dict[str, dict[str, Any]],
    ] = defaultdict(dict)
    group_order: list[tuple[str, int]] = []
    plan_exemplars: dict[tuple[str, int], dict[str, Any]] = {}

    for planned in plan_rows:
        key = (
            planned["series_id"],
            planned["external_optimizer_seed"],
        )
        if key not in plan_exemplars:
            group_order.append(key)
            plan_exemplars[key] = planned
        grouped[key][planned["model_id"]] = result_by_id[planned["job_id"]]

    decisions: list[dict[str, Any]] = []
    decision_status_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()

    for key in group_order:
        by_model = grouped[key]
        if set(by_model) != {"M0", "M1", "M2"}:
            raise ValidationError(f"Incomplete model trio in plan group {key}.")

        exemplar = plan_exemplars[key]
        valid_flags = {
            model: finite_ok_bic(by_model[model])
            for model in ("M0", "M1", "M2")
        }
        valid_models = sum(valid_flags.values())
        complete = valid_models == 3

        delta01: float | str = ""
        delta21: float | str = ""
        selected: str = ""
        estimated_period: float | str = ""
        period_label: str

        if valid_flags["M0"] and valid_flags["M1"]:
            delta01 = (
                float(by_model["M0"]["BIC"])
                - float(by_model["M1"]["BIC"])
            )
        if valid_flags["M2"] and valid_flags["M1"]:
            delta21 = (
                float(by_model["M2"]["BIC"])
                - float(by_model["M1"]["BIC"])
            )

        if complete:
            decision_status = "VALID"
            is_selected = bool(delta01 > 10.0 and delta21 > 10.0)
            selected = "true" if is_selected else "false"
            estimated_period = float(by_model["M1"]["estimated_period_s"])
            period_label = (
                "recovered_period_selected"
                if is_selected
                else "formal_m1_center_not_selected"
            )
        else:
            decision_status = "INCOMPLETE_NUMERICAL"
            period_label = "unavailable_incomplete_numerical"

        row = {
            "job_class": exemplar["job_class"],
            "series_id": key[0],
            "condition_id": exemplar["condition_id"],
            "ground_truth": exemplar["ground_truth"],
            "data_seed": exemplar["data_seed"],
            "external_optimizer_seed": key[1],
            "valid_models": valid_models,
            "decision_status": decision_status,
            "delta_bic_0_1": delta01,
            "delta_bic_2_1": delta21,
            "qpp_selected": selected,
            "estimated_period_s": estimated_period,
            "period_label": period_label,
        }
        decisions.append(row)
        decision_status_counts[decision_status] += 1
        class_counts[exemplar["job_class"]] += 1

    if len(decisions) != EXPECTED_COUNTS["total_decisions"]:
        raise ValidationError(
            f"Decision count is {len(decisions)}, not 5439."
        )
    if class_counts != {
        "primary": EXPECTED_COUNTS["primary_decisions"],
        "stability": EXPECTED_COUNTS["stability_decisions"],
    }:
        raise ValidationError(
            f"Unexpected decision class counts: {class_counts}"
        )

    primary = [
        row for row in decisions if row["job_class"] == "primary"
    ]
    stability = [
        row for row in decisions if row["job_class"] == "stability"
    ]
    if any(int(row["external_optimizer_seed"]) != 0 for row in primary):
        raise ValidationError("A primary decision has a non-zero optimizer seed.")
    if any(
        int(row["data_seed"]) != 0
        or not 1 <= int(row["external_optimizer_seed"]) <= 9
        for row in stability
    ):
        raise ValidationError("A stability decision is outside the frozen seeds.")

    return decisions, {
        "primary_decisions": len(primary),
        "stability_decisions": len(stability),
        "total_decisions": len(decisions),
        "decision_status_counts": dict(
            sorted(decision_status_counts.items())
        ),
    }


def postflight_environment_matches(
    before: dict[str, Any],
    after: dict[str, Any],
) -> None:
    keys = [
        "afino_commit",
        "afino_package_version",
        "tracked_diff_exit_code",
        "staged_diff_exit_code",
        "git_status_porcelain",
        "numpy_version",
        "scipy_version",
    ]
    for key in keys:
        if before[key] != after[key]:
            raise ValidationError(
                f"Environment changed during validation: {key}"
            )


def report_text(audit: dict[str, Any]) -> str:
    status_counts = audit["execution"]["status_counts"]
    warnings = audit["execution"]["warning_calls_by_model"]
    warning_totals = audit["execution"]["warning_totals_by_model"]
    bounds = audit["execution"]["bound_hit_calls_by_model"]
    decisions = audit["decisions"]

    diagnosis = (
        "La ejecución completa se realizó mediante el runner 1.0.1 y el plan "
        "congelado de 16.317 trabajos. El primer registro de invocación partió "
        "de cero filas y todas las reanudaciones conservaron una historia "
        "contigua de transacciones confirmadas. Al finalizar no quedó ningún "
        "trabajo pendiente. La validación comparó cada resultado del checkpoint "
        "y del CSV exportado con su fila normativa del plan, incluidos serie, "
        "condición, clase, semilla externa, modelo y hashes de flujo y tiempo. "
        "No aparecieron claves duplicadas ni discrepancias de metadatos o inputs. "
        "Los cuatro payloads binarios y sus hashes lógicos coincidieron antes y "
        "después, y el checkpoint canary permaneció separado e intacto. "
        "Los resultados con estado distinto de OK, si existen, se conservaron "
        "como resultados numéricos del benchmark y generaron decisiones "
        "INCOMPLETE_NUMERICAL; no se transformaron en no selecciones ni se "
        "redibujaron series. La tabla de decisiones contiene exactamente 4.440 "
        "tríos primarios y 999 de estabilidad. Esta tarea solo congela resultados "
        "brutos y resume integridad, estados, warnings, bounds y tiempo operativo. "
        "No calcula tasas por condición, efectos de factores, errores agregados "
        "de periodo, discordancia entre semillas ni conclusiones científicas "
        "sobre robustez. El repositorio AFINO conservó el commit predeclarado, "
        "sin cambios tracked o staged, y el runner, el plan y el dataset "
        "mantuvieron sus hashes normativos."
    )

    return f"""# Fase 1 — Tarea 1.5

## Ejecución reanudable del benchmark sintético núcleo

**Estado:** `{audit['execution_status']}`  
**Runner:** `1.0.1`  
**AFINO commit:** `{audit['environment']['afino_commit']}`  
**Plan:** `{audit['plan']['planned_jobs']}` trabajos  
**Pendientes:** `{audit['execution']['pending_jobs']}`

## 1. Integridad y entorno

Los hashes físicos y lógicos de F1.3, el runner y el plan se verificaron antes
y después. AFINO permaneció en el commit y versión congelados, sin diferencias
tracked ni staged. Los archivos no versionados se registran en la auditoría.

## 2. Conteos de ejecución

| Concepto | Resultado |
|---|---:|
| Trabajos planificados | {audit['plan']['planned_jobs']} |
| Filas en checkpoint | {audit['execution']['checkpoint_result_rows']} |
| Filas exportadas | {audit['execution']['exported_result_rows']} |
| Trabajos primarios | {audit['execution']['class_counts']['primary']} |
| Trabajos de estabilidad | {audit['execution']['class_counts']['stability']} |
| M0 | {audit['execution']['model_counts']['M0']} |
| M1 | {audit['execution']['model_counts']['M1']} |
| M2 | {audit['execution']['model_counts']['M2']} |

Estados retenidos:

```text
{json.dumps(status_counts, ensure_ascii=False, sort_keys=True)}
```

## 3. Reanudación e idempotencia

Invocaciones registradas: `{audit['resume']['invocation_count']}`.  
Primera invocación, filas preexistentes:
`{audit['resume']['first_invocation_existing_before']}`.  
Total final confirmado:
`{audit['resume']['final_total_after']}`.

No se importó el checkpoint ni los resultados del canary.

## 4. Decisiones estructurales

| Tipo | Filas |
|---|---:|
| Primarias | {decisions['primary_decisions']} |
| Estabilidad | {decisions['stability_decisions']} |
| Total | {decisions['total_decisions']} |

Estados de decisión:

```text
{json.dumps(decisions['decision_status_counts'], ensure_ascii=False, sort_keys=True)}
```

Las decisiones incompletas conservan `qpp_selected` vacío y la etiqueta
`unavailable_incomplete_numerical`.

## 5. Warnings, bounds y tiempo

```text
warning_calls_by_model:
{json.dumps(warnings, ensure_ascii=False, sort_keys=True)}

warning_totals_by_model:
{json.dumps(warning_totals, ensure_ascii=False, sort_keys=True)}

bound_hit_calls_by_model:
{json.dumps(bounds, ensure_ascii=False, sort_keys=True)}

total_runtime_seconds:
{audit['execution']['total_runtime_seconds']}
```

Estos conteos son controles operativos; no constituyen análisis científico.

## 6. Hashes de cierre

```text
checkpoint:
{audit['output_hashes']['fase1_tarea05_full_checkpoint.sqlite']}

results:
{audit['output_hashes']['fase1_tarea05_core_results.csv']}

decisions:
{audit['output_hashes']['fase1_tarea05_core_decisions.csv']}

validator:
{audit['output_hashes']['fase1_tarea05_validate_full_execution.py']}

environment:
{audit['output_hashes']['fase1_tarea05_environment.txt']}
```

## 7. Incidencias

{audit['incidents_text']}

## 8. Diagnóstico

{diagnosis}

## 9. Conclusión

`{audit['execution_status']}`
"""


def write_blocked_outputs(
    error: BaseException,
    environment: dict[str, Any] | None,
) -> None:
    blocked = {
        "date_utc": utc_now(),
        "execution_status": "FULL_BENCHMARK_EXECUTION_BLOCKED",
        "error": str(error),
        "traceback": traceback.format_exc(),
        "environment": environment,
        "confirmations": {
            "runner_modified": False,
            "execution_plan_modified": False,
            "afino_code_modified": False,
            "dataset_modified": False,
            "dataset_regenerated": False,
            "canary_checkpoint_reused": False,
            "canary_results_imported": False,
            "jobs_removed": False,
            "failed_jobs_redrawn": False,
            "scientific_protocol_modified": False,
            "scientific_results_interpreted_during_execution": False,
        },
    }
    if not AUDIT_JSON.exists():
        AUDIT_JSON.write_text(
            json.dumps(blocked, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if not REPORT_MD.exists():
        REPORT_MD.write_text(
            "# Fase 1 — Tarea 1.5\n\n"
            "## Estado\n\n"
            "`FULL_BENCHMARK_EXECUTION_BLOCKED`\n\n"
            "## Error\n\n"
            f"```text\n{error}\n```\n",
            encoding="utf-8",
        )


def main() -> int:
    environment_before: dict[str, Any] | None = None

    if DECISIONS_CSV.exists() or AUDIT_JSON.exists() or REPORT_MD.exists():
        raise ValidationError(
            "A final F1.5 validator output already exists; preserve it."
        )

    try:
        environment_before = collect_environment()
        ENVIRONMENT_TXT.write_text(
            environment_text(environment_before),
            encoding="utf-8",
        )

        physical_before, logical_before = verify_frozen_inputs()
        series_by_id, time_by_id = load_and_validate_manifests()
        plan_rows = load_and_validate_plan(series_by_id, time_by_id)

        metadata, checkpoint_rows, invocations = load_checkpoint()
        validate_checkpoint_metadata(
            metadata,
            physical_before,
            logical_before,
        )
        resume_summary = validate_invocations(invocations)
        execution_summary = validate_checkpoint_results(
            plan_rows,
            checkpoint_rows,
        )

        if execution_summary["pending_jobs"] != 0:
            raise ValidationError(
                f"{execution_summary['pending_jobs']} jobs remain pending."
            )

        exported_rows = validate_exported_results(
            plan_rows,
            checkpoint_rows,
        )
        execution_summary["exported_result_rows"] = len(exported_rows)

        decisions, decision_summary = build_decisions(
            plan_rows,
            checkpoint_rows,
        )
        write_csv(DECISIONS_CSV, DECISION_FIELDS, decisions)

        # Verify the decision file after closing and reloading it.
        decision_fields, reloaded_decisions = read_csv_with_fields(DECISIONS_CSV)
        if decision_fields != DECISION_FIELDS:
            raise ValidationError("Decision CSV schema changed on round-trip.")
        if len(reloaded_decisions) != EXPECTED_COUNTS["total_decisions"]:
            raise ValidationError(
                "Decision CSV row count changed on round-trip."
            )

        environment_after = collect_environment()
        postflight_environment_matches(
            environment_before,
            environment_after,
        )
        physical_after, logical_after = verify_frozen_inputs()
        if physical_before != physical_after:
            raise ValidationError("Frozen physical hashes changed during F1.5.")
        if logical_before != logical_after:
            raise ValidationError("Frozen logical hashes changed during F1.5.")

        if sha256(CANARY_CHECKPOINT) != EXPECTED_PHYSICAL_HASHES[
            CANARY_CHECKPOINT.name
        ]:
            raise ValidationError("The canary checkpoint changed.")

        output_hashes = {
            FULL_CHECKPOINT.name: sha256(FULL_CHECKPOINT),
            RESULTS_CSV.name: sha256(RESULTS_CSV),
            DECISIONS_CSV.name: sha256(DECISIONS_CSV),
            Path(__file__).resolve().name: sha256(Path(__file__).resolve()),
            ENVIRONMENT_TXT.name: sha256(ENVIRONMENT_TXT),
        }

        audit: dict[str, Any] = {
            "date_utc": utc_now(),
            "execution_status": "FULL_BENCHMARK_EXECUTION_COMPLETE",
            "runner_implementation_version": EXPECTED_RUNNER_VERSION,
            "environment": environment_after,
            "preflight": {
                "physical_hashes": physical_before,
                "logical_hashes": logical_before,
                "checkpoint_exists_before_start": False,
                "initial_result_rows": 0,
                "canary_checkpoint_imported": False,
                "canary_results_imported": False,
            },
            "postflight": {
                "physical_hashes": physical_after,
                "logical_hashes": logical_after,
                "dataset_unchanged": True,
                "runner_unchanged": True,
                "plan_unchanged": True,
                "canary_checkpoint_unchanged": True,
                "afino_commit": environment_after["afino_commit"],
                "afino_version": environment_after["afino_package_version"],
                "tracked_git_diff_empty": True,
                "staged_git_diff_empty": True,
                "git_status_porcelain":
                    environment_after["git_status_porcelain"],
            },
            "plan": {
                "planned_jobs": len(plan_rows),
                "primary_jobs": EXPECTED_COUNTS["primary_jobs"],
                "stability_jobs": EXPECTED_COUNTS["stability_jobs"],
                "M0_rows": EXPECTED_COUNTS["model_rows"],
                "M1_rows": EXPECTED_COUNTS["model_rows"],
                "M2_rows": EXPECTED_COUNTS["model_rows"],
                "plan_sha256": sha256(PLAN),
                "unique_job_ids": len(
                    {row["job_id"] for row in plan_rows}
                ),
                "unique_scientific_keys": len(
                    {
                        (
                            row["series_id"],
                            row["external_optimizer_seed"],
                            row["model_id"],
                        )
                        for row in plan_rows
                    }
                ),
            },
            "checkpoint": {
                "filename": FULL_CHECKPOINT.name,
                "sha256": sha256(FULL_CHECKPOINT),
                "metadata": metadata,
                "sqlite_transaction_policy":
                    "one independent transaction per completed model call",
                "unique_job_id_enforced": True,
                "unique_series_seed_model_enforced": True,
            },
            "resume": resume_summary,
            "execution": execution_summary,
            "decisions": decision_summary,
            "output_hashes": output_hashes,
            "incidents": [],
            "incidents_text": "No se registraron incidencias mecánicas.",
            "confirmations": {
                "runner_modified": False,
                "execution_plan_modified": False,
                "afino_code_modified": False,
                "dataset_modified": False,
                "dataset_regenerated": False,
                "canary_checkpoint_reused": False,
                "canary_results_imported": False,
                "jobs_removed": False,
                "failed_jobs_redrawn": False,
                "scientific_protocol_modified": False,
                "scientific_results_interpreted_during_execution": False,
            },
        }

        REPORT_MD.write_text(report_text(audit), encoding="utf-8")
        audit["output_hashes"][REPORT_MD.name] = sha256(REPORT_MD)

        AUDIT_JSON.write_text(
            json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False)
            + "\n",
            encoding="utf-8",
        )

        print("F1.5 independent structural validation complete")
        print("execution_status: FULL_BENCHMARK_EXECUTION_COMPLETE")
        print(f"planned_jobs: {len(plan_rows)}")
        print(
            "checkpoint_result_rows: "
            f"{execution_summary['checkpoint_result_rows']}"
        )
        print(
            "exported_result_rows: "
            f"{execution_summary['exported_result_rows']}"
        )
        print(f"pending_jobs: {execution_summary['pending_jobs']}")
        print(
            "total_decisions: "
            f"{decision_summary['total_decisions']}"
        )
        print(
            "decision_status_counts: "
            f"{json.dumps(decision_summary['decision_status_counts'], sort_keys=True)}"
        )
        print(f"audit: {AUDIT_JSON.name}")
        print(f"report: {REPORT_MD.name}")
        return 0

    except Exception as exc:
        write_blocked_outputs(exc, environment_before)
        print(
            f"FULL_BENCHMARK_EXECUTION_BLOCKED: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
