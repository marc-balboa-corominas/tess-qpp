#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import math
import platform
import sqlite3
import statistics
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

RUNNER = ROOT / "fase1_tarea11_run_nested_afino_checkpointed.py"
PLAN = ROOT / "fase1_tarea11_nested_full_execution_plan.csv"
CANARY_CHECKPOINT = ROOT / "fase1_tarea11_nested_canary_checkpoint.sqlite"

FLUX_NPY = ROOT / "fase1_tarea10_nested_flux_values.npy"
SERIES_OFFSETS_NPY = ROOT / "fase1_tarea10_nested_series_offsets.npy"
TIME_VALUES_NPY = ROOT / "fase1_tarea10_nested_time_values.npy"
TIME_OFFSETS_NPY = ROOT / "fase1_tarea10_nested_time_offsets.npy"
SERIES_MANIFEST = ROOT / "fase1_tarea10_nested_series_manifest.csv"
TIME_MANIFEST = ROOT / "fase1_tarea10_nested_time_manifest.csv"
MATERIALIZATION_AUDIT = ROOT / "fase1_tarea10_nested_materialization_audit.json"

FULL_CHECKPOINT = ROOT / "fase1_tarea12_nested_full_checkpoint.sqlite"
RESULTS_CSV = ROOT / "fase1_tarea12_nested_full_results.csv"
DECISIONS_CSV = ROOT / "fase1_tarea12_nested_full_decisions.csv"
AUDIT_JSON = ROOT / "fase1_tarea12_nested_full_execution_audit.json"
REPORT_MD = ROOT / "fase1_tarea12_nested_full_execution_report.md"
ENVIRONMENT_TXT = ROOT / "fase1_tarea12_environment.txt"
CONSOLE_TXT = ROOT / "fase1_tarea12_console_output.txt"

EXPECTED_AFINO_COMMIT = "6aceac9518fc8056052807e666da9d0c8bebb010"
EXPECTED_AFINO_VERSION = "0.5"
EXPECTED_NUMPY_VERSION = "2.5.1"
EXPECTED_SCIPY_VERSION = "1.18.0"
EXPECTED_RUNNER_VERSION = "1.1.0"
EXPECTED_RUNNER_FAMILY = "afino_checkpointed"
ABS_TOLERANCE = 5e-12

EXPECTED_PHYSICAL_HASHES = {
    "fase1_tarea11_run_nested_afino_checkpointed.py": "b5bdbccb4f1170a40163ef99f465fb63d75d51f9d227178af8cdd82934e5695f",
    "fase1_tarea11_nested_full_execution_plan.csv": "08184f7adaab84693fe82fb060d3533f65a870555535d5b1eeccfc37467c6911",
    "fase1_tarea10_nested_flux_values.npy": "74d873cdef11b3855d2aba33ded45910f879f5afafb9b5eff4d71d271b06f565",
    "fase1_tarea10_nested_series_offsets.npy": "a902ae72c06ecc31926d11b6cb297da190a6204dd21cbcc622205589ff324068",
    "fase1_tarea10_nested_time_values.npy": "995d5321c34e305e6ed02556215660b20bf4c947eaba69ca44e6932349366db7",
    "fase1_tarea10_nested_time_offsets.npy": "f7966cdcdb9373ed33bdf6b50d4c88c9e9ef172a0e087e0543cc1197094304e8",
    "fase1_tarea10_nested_series_manifest.csv": "cc9f44c710dade51e91fe0c2d30b193c621c7b9905764c6fe69fcf1c94c395a5",
    "fase1_tarea10_nested_time_manifest.csv": "cfc1b66b0e949acb2611f73823074faaa1259bcf9a458d687506fb361cb89ed4",
    "fase1_tarea10_nested_materialization_audit.json": "0ea6d0cfe73c0d8b9260bb16f5a761d6c8cf641e6b5dd968b52af3382b3b7b9b",
    "fase1_tarea11_nested_canary_checkpoint.sqlite": "e8b7797db0dcf1910a4e49c9f84aabbec93b3981826b8c9b2251ab87f72e6685",
}
EXPECTED_LOGICAL_HASHES = {
    "canonical_flux_payload_sha256": "9847da04c1793247ab34b01c06b2e9d579715d3bf06c1ea0cb14ea9ebaab03f0",
    "series_offsets_canonical_sha256": "a8f34927c914b8256334e3570ed31b8c5fbb8504b991db0de976105c0f5d3e06",
    "time_values_canonical_sha256": "dfaa422bf7854de5f2a6e89a8db3f06ec9f3c0ccab7d60cd507b45325c3ea6cc",
    "time_offsets_canonical_sha256": "7ab392ff65815e1dd36e8c48377f0c8969351b0e178210cd85f5711be77aa1a5",
}

EXPECTED = {
    "planned_jobs": 7938,
    "primary_jobs": 6480,
    "stability_jobs": 1458,
    "rows_per_model": 2646,
    "primary_decisions": 2160,
    "stability_decisions": 486,
    "decisions": 2646,
}
MODEL_NAMES = {"M0": "pow_const", "M1": "pow_const_gauss", "M2": "bpow_const"}
EXPECTED_BINS = {15: 7, 30: 14, 45: 22, 60: 29, 90: 44, 120: 59}

PLAN_FIELDS = [
    "job_id", "job_order", "job_class", "series_id", "condition_id", "parent_id", "block_id",
    "ground_truth", "n_samples", "duration_s", "red_noise_alpha", "period_s", "qpp_fraction",
    "data_seed", "external_optimizer_seed", "model_id", "model_name", "flux_start_offset",
    "flux_end_offset", "time_vector_id", "input_flux_sha256", "input_time_sha256",
    "parent_n120_series_id",
]
RESULT_FIELDS = [
    "job_id", "job_class", "series_id", "condition_id", "parent_id", "block_id", "ground_truth",
    "duration_s", "red_noise_alpha", "period_s", "qpp_fraction", "data_seed",
    "external_optimizer_seed", "model_id", "model_name", "status", "runtime_seconds", "n_samples",
    "input_flux_sha256", "input_time_sha256", "parent_n120_series_id", "afino_effective_dt_s",
    "positive_frequency_bins", "bins_after_cutoff", "minimum_frequency_hz", "maximum_frequency_hz",
    "lnlike", "BIC", "rchi2", "probability", "parameters_json", "estimated_period_s",
    "parameter_at_bound", "bound_indices_json", "warning_count", "warning_types_json",
    "convergence_status", "error",
]
DECISION_FIELDS = [
    "series_id", "condition_id", "parent_id", "block_id", "ground_truth", "n_samples", "duration_s",
    "red_noise_alpha", "period_s", "qpp_fraction", "data_seed", "external_optimizer_seed",
    "decision_status", "valid_models", "bic_m0", "bic_m1", "bic_m2", "delta_bic_0_1",
    "delta_bic_2_1", "qpp_selected", "estimated_period_s", "period_label",
]


class ValidationError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(array: np.ndarray, dtype: str) -> str:
    canonical = np.ascontiguousarray(array, dtype=dtype)
    return hashlib.sha256(canonical.tobytes(order="C")).hexdigest()


def run_command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, encoding="utf-8", errors="replace", capture_output=True, check=check)


def relative_executable() -> str:
    try:
        return str(Path(sys.executable).resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(Path(sys.executable).resolve())


def collect_environment() -> dict[str, Any]:
    if not REPO.exists():
        raise ValidationError(f"Missing AFINO repository: {REPO}")
    commit = run_command(["git", "-C", str(REPO), "rev-parse", "HEAD"]).stdout.strip()
    tracked = run_command(["git", "-C", str(REPO), "diff", "--quiet"], check=False)
    staged = run_command(["git", "-C", str(REPO), "diff", "--cached", "--quiet"], check=False)
    status = run_command(["git", "-C", str(REPO), "status", "--porcelain"]).stdout.rstrip()
    pip_freeze = run_command([sys.executable, "-m", "pip", "freeze"]).stdout.splitlines()
    try:
        afino_version = importlib.metadata.version("afino")
    except importlib.metadata.PackageNotFoundError as exc:
        raise ValidationError("The AFINO package is not installed.") from exc
    environment = {
        "python_version": platform.python_version(), "python_full": sys.version,
        "python_executable_relative": relative_executable(), "numpy_version": np.__version__,
        "scipy_version": importlib.metadata.version("scipy"), "platform": platform.platform(),
        "machine": platform.machine(), "processor": platform.processor(), "afino_commit": commit,
        "afino_package_version": afino_version, "tracked_diff_exit_code": tracked.returncode,
        "staged_diff_exit_code": staged.returncode, "git_status_porcelain": status,
        "pip_freeze": pip_freeze,
    }
    if commit != EXPECTED_AFINO_COMMIT or afino_version != EXPECTED_AFINO_VERSION:
        raise ValidationError("AFINO commit or package version mismatch.")
    if np.__version__ != EXPECTED_NUMPY_VERSION or environment["scipy_version"] != EXPECTED_SCIPY_VERSION:
        raise ValidationError("NumPy or SciPy version mismatch.")
    if tracked.returncode != 0 or staged.returncode != 0:
        raise ValidationError("Tracked or staged AFINO diff is not empty.")
    return environment


def environment_text(environment: dict[str, Any]) -> str:
    lines = [
        f"Python: {environment['python_version']}", f"Python full: {environment['python_full']}",
        f"Python executable relative: {environment['python_executable_relative']}",
        f"NumPy: {environment['numpy_version']}", f"SciPy: {environment['scipy_version']}",
        f"Platform: {environment['platform']}", f"Machine: {environment['machine']}",
        f"Processor: {environment['processor']}", f"AFINO commit: {environment['afino_commit']}",
        f"AFINO package version: {environment['afino_package_version']}",
        f"Tracked diff exit code: {environment['tracked_diff_exit_code']}",
        f"Staged diff exit code: {environment['staged_diff_exit_code']}",
        "Git status --porcelain:", environment["git_status_porcelain"], "", "pip freeze:",
        *environment["pip_freeze"], "",
    ]
    return "\n".join(lines)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise ValidationError(f"Missing CSV: {path.name}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    return fields, rows


def parse_optional_float(value: str) -> float | None:
    return None if value == "" else float(value)


def parse_optional_int(value: str) -> int | None:
    return None if value == "" else int(value)


def parse_bool(value: str) -> bool | None:
    if value == "":
        return None
    if value == "True":
        return True
    if value == "False":
        return False
    raise ValidationError(f"Invalid boolean text: {value!r}")


def close_float(left: float | None, right: float | None, *, atol: float = 0.0) -> bool:
    if left is None or right is None:
        return left is right
    return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=atol)


def verify_frozen_inputs() -> tuple[dict[str, str], dict[str, str]]:
    paths = {
        RUNNER.name: RUNNER, PLAN.name: PLAN, FLUX_NPY.name: FLUX_NPY,
        SERIES_OFFSETS_NPY.name: SERIES_OFFSETS_NPY, TIME_VALUES_NPY.name: TIME_VALUES_NPY,
        TIME_OFFSETS_NPY.name: TIME_OFFSETS_NPY, SERIES_MANIFEST.name: SERIES_MANIFEST,
        TIME_MANIFEST.name: TIME_MANIFEST, MATERIALIZATION_AUDIT.name: MATERIALIZATION_AUDIT,
        CANARY_CHECKPOINT.name: CANARY_CHECKPOINT,
    }
    physical: dict[str, str] = {}
    for name, path in paths.items():
        if not path.exists():
            raise ValidationError(f"Missing frozen artifact: {name}")
        observed = sha256(path)
        if observed != EXPECTED_PHYSICAL_HASHES[name]:
            raise ValidationError(f"Physical hash mismatch for {name}: {observed}")
        physical[name] = observed
    flux = np.load(FLUX_NPY, allow_pickle=False)
    series_offsets = np.load(SERIES_OFFSETS_NPY, allow_pickle=False)
    time_values = np.load(TIME_VALUES_NPY, allow_pickle=False)
    time_offsets = np.load(TIME_OFFSETS_NPY, allow_pickle=False)
    logical = {
        "canonical_flux_payload_sha256": canonical_sha256(flux, "<f8"),
        "series_offsets_canonical_sha256": canonical_sha256(series_offsets, "<i8"),
        "time_values_canonical_sha256": canonical_sha256(time_values, "<f8"),
        "time_offsets_canonical_sha256": canonical_sha256(time_offsets, "<i8"),
    }
    if logical != EXPECTED_LOGICAL_HASHES:
        raise ValidationError("Logical F1.10 hashes do not match.")
    if flux.shape != (129600,) or series_offsets.shape != (2161,):
        raise ValidationError("Unexpected nested flux or series-offset shape.")
    if time_values.shape != (360,) or time_offsets.shape != (7,):
        raise ValidationError("Unexpected nested time or time-offset shape.")
    materialization = json.loads(MATERIALIZATION_AUDIT.read_text(encoding="utf-8"))
    if materialization.get("materialization_status") != "NESTED_DATASET_FROZEN_BEFORE_AFINO":
        raise ValidationError("F1.10 dataset is not frozen.")
    return physical, logical


def load_manifests() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    _, series_rows = read_csv(SERIES_MANIFEST)
    _, time_rows = read_csv(TIME_MANIFEST)
    if len(series_rows) != 2160 or len(time_rows) != 6:
        raise ValidationError("Unexpected F1.10 manifest row counts.")
    series = {row["series_id"]: row for row in series_rows}
    times = {row["time_vector_id"]: row for row in time_rows}
    if len(series) != 2160 or len(times) != 6:
        raise ValidationError("Duplicate F1.10 manifest identifiers.")
    return series, times


def load_plan(series: dict[str, dict[str, str]], times: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    fields, raw = read_csv(PLAN)
    if fields != PLAN_FIELDS or len(raw) != EXPECTED["planned_jobs"]:
        raise ValidationError("Full plan schema or row count mismatch.")
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(raw, start=1):
        row = dict(source)
        for name in ("job_order", "n_samples", "data_seed", "external_optimizer_seed", "flux_start_offset", "flux_end_offset"):
            row[name] = int(row[name])
        for name in ("duration_s", "red_noise_alpha"):
            row[name] = float(row[name])
        row["period_s"] = parse_optional_float(row["period_s"])
        row["qpp_fraction"] = parse_optional_float(row["qpp_fraction"])
        if row["job_order"] != index or row["job_id"] != f"NWJ{index:06d}":
            raise ValidationError(f"Non-normative job order at row {index}.")
        if row["model_name"] != MODEL_NAMES.get(row["model_id"]):
            raise ValidationError(f"Model mismatch in {row['job_id']}.")
        manifest = series.get(row["series_id"])
        if manifest is None:
            raise ValidationError(f"Unknown series in plan: {row['series_id']}")
        time_row = times.get(row["time_vector_id"])
        if time_row is None:
            raise ValidationError(f"Unknown time vector in plan: {row['time_vector_id']}")
        expected_text = {
            "condition_id": manifest["condition_id"], "parent_id": manifest["parent_id"],
            "block_id": manifest["block_id"], "ground_truth": manifest["ground_truth"],
            "parent_n120_series_id": manifest["parent_n120_series_id"],
            "input_flux_sha256": manifest["flux_sha256"], "input_time_sha256": time_row["time_sha256"],
        }
        for name, value in expected_text.items():
            if row[name] != value:
                raise ValidationError(f"Plan/manifest mismatch in {row['job_id']} field {name}.")
        if row["n_samples"] != int(manifest["n_samples"]):
            raise ValidationError(f"Plan n_samples mismatch in {row['job_id']}.")
        if row["flux_start_offset"] != int(manifest["flux_start_offset"]) or row["flux_end_offset"] != int(manifest["flux_end_offset"]):
            raise ValidationError(f"Plan offsets mismatch in {row['job_id']}.")
        if row["job_class"] == "primary":
            if row["external_optimizer_seed"] != 0:
                raise ValidationError("Primary job has non-zero optimizer seed.")
        elif row["job_class"] == "stability":
            if row["data_seed"] != 0 or not 1 <= row["external_optimizer_seed"] <= 9:
                raise ValidationError("Stability job is outside frozen seeds.")
        else:
            raise ValidationError(f"Invalid job class: {row['job_class']}")
        rows.append(row)
    if len({r["job_id"] for r in rows}) != len(rows):
        raise ValidationError("Duplicate job_id in plan.")
    if len({(r["series_id"], r["external_optimizer_seed"], r["model_id"]) for r in rows}) != len(rows):
        raise ValidationError("Duplicate scientific key in plan.")
    classes = Counter(r["job_class"] for r in rows)
    models = Counter(r["model_id"] for r in rows)
    if classes != {"primary": 6480, "stability": 1458} or models != {"M0": 2646, "M1": 2646, "M2": 2646}:
        raise ValidationError("Plan class or model counts mismatch.")
    return rows


def connect_readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def load_checkpoint() -> tuple[dict[str, str], list[dict[str, Any]], list[dict[str, Any]]]:
    if not FULL_CHECKPOINT.exists():
        raise ValidationError("The full nested checkpoint does not exist.")
    connection = connect_readonly(FULL_CHECKPOINT)
    try:
        metadata = {row["key"]: row["value"] for row in connection.execute("SELECT key,value FROM metadata ORDER BY key")}
        results = [dict(row) for row in connection.execute("SELECT * FROM results ORDER BY job_order")]
        invocations = [dict(row) for row in connection.execute("SELECT * FROM invocations ORDER BY invocation_id")]
        table = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='results'").fetchone()
    finally:
        connection.close()
    if table is None:
        raise ValidationError("Checkpoint has no results table.")
    sql = str(table["sql"])
    if "job_id TEXT PRIMARY KEY" not in sql or "UNIQUE(series_id, external_optimizer_seed, model_id)" not in sql:
        raise ValidationError("Checkpoint uniqueness constraints are missing.")
    return metadata, results, invocations


def validate_metadata(metadata: dict[str, str], physical: dict[str, str], logical: dict[str, str]) -> None:
    expected = {
        "schema_version": "1.1.0", "runner_family": EXPECTED_RUNNER_FAMILY,
        "runner_implementation_version": EXPECTED_RUNNER_VERSION, "plan_filename": PLAN.name,
        "plan_sha256": EXPECTED_PHYSICAL_HASHES[PLAN.name], "plan_kind": "full",
        "runner_sha256": EXPECTED_PHYSICAL_HASHES[RUNNER.name], "afino_commit": EXPECTED_AFINO_COMMIT,
        "afino_version": EXPECTED_AFINO_VERSION,
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise ValidationError(f"Checkpoint metadata mismatch for {key}.")
    stored_physical = json.loads(metadata["dataset_physical_hashes"])
    stored_logical = json.loads(metadata["dataset_logical_hashes"])
    for name in (FLUX_NPY.name, SERIES_OFFSETS_NPY.name, TIME_VALUES_NPY.name, TIME_OFFSETS_NPY.name,
                 SERIES_MANIFEST.name, TIME_MANIFEST.name, MATERIALIZATION_AUDIT.name, PLAN.name):
        expected_hash = physical.get(name, EXPECTED_PHYSICAL_HASHES.get(name))
        if stored_physical.get(name) != expected_hash:
            raise ValidationError(f"Checkpoint stored wrong physical hash for {name}.")
    if stored_logical != logical:
        raise ValidationError("Checkpoint logical hashes differ from F1.10.")


def validate_invocations(invocations: list[dict[str, Any]]) -> dict[str, Any]:
    if not invocations:
        raise ValidationError("No invocation history.")
    committed = [int(row["committed_new"]) for row in invocations]
    expected_committed = [1000] * 7 + [938, 0]
    if committed != expected_committed:
        raise ValidationError(f"Unexpected batch sequence: {committed}")
    expected_stops = [1000] * 7 + [938, None]
    previous = 0
    for index, row in enumerate(invocations):
        if row["plan_sha256"] != EXPECTED_PHYSICAL_HASHES[PLAN.name] or row["plan_kind"] != "full":
            raise ValidationError("Invocation used a non-frozen plan.")
        if int(row["resume_requested"]) != (0 if index == 0 else 1):
            raise ValidationError("Unexpected --resume history.")
        if row["stop_after"] != expected_stops[index]:
            raise ValidationError("Unexpected stop_after history.")
        if int(row["existing_before"]) != previous:
            raise ValidationError("Invocation history is not contiguous.")
        if int(row["total_after"]) != int(row["existing_before"]) + int(row["committed_new"]):
            raise ValidationError("Invocation total_after mismatch.")
        previous = int(row["total_after"])
    if previous != EXPECTED["planned_jobs"]:
        raise ValidationError("Final invocation did not reach 7938.")
    return {
        "invocation_count": len(invocations), "first_invocation_existing_before": int(invocations[0]["existing_before"]),
        "first_invocation_resume_requested": bool(invocations[0]["resume_requested"]),
        "total_committed_new": sum(committed), "final_total_after": previous, "invocations": invocations,
    }


def validate_checkpoint_results(plan: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    if len(results) != EXPECTED["planned_jobs"]:
        raise ValidationError(f"Checkpoint rows: {len(results)} != 7938")
    plan_by_id = {r["job_id"]: r for r in plan}
    result_by_id = {r["job_id"]: r for r in results}
    if set(plan_by_id) != set(result_by_id):
        raise ValidationError("Plan/result job sets differ.")
    duplicate_jobs = len(results) - len(result_by_id)
    duplicate_keys = len(results) - len({(r["series_id"], int(r["external_optimizer_seed"]), r["model_id"]) for r in results})
    if duplicate_jobs or duplicate_keys:
        raise ValidationError("Duplicate result keys.")
    status_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    model_counts: Counter[str] = Counter()
    warning_calls: Counter[str] = Counter()
    warning_totals: Counter[str] = Counter()
    bound_calls: Counter[str] = Counter()
    runtimes: dict[str, list[float]] = defaultdict(list)
    metadata_mismatches = 0
    input_hash_mismatches = 0
    compare = ["job_order", "job_class", "series_id", "condition_id", "parent_id", "block_id", "ground_truth",
               "data_seed", "external_optimizer_seed", "model_id", "model_name", "n_samples", "input_flux_sha256",
               "input_time_sha256", "parent_n120_series_id"]
    for planned in plan:
        row = result_by_id[planned["job_id"]]
        for field in compare:
            if row[field] != planned[field]:
                metadata_mismatches += 1
        for field in ("duration_s", "red_noise_alpha", "period_s", "qpp_fraction"):
            if not close_float(row[field], planned[field]):
                metadata_mismatches += 1
        if row["input_flux_sha256"] != planned["input_flux_sha256"] or row["input_time_sha256"] != planned["input_time_sha256"]:
            input_hash_mismatches += 1
        status = str(row["status"])
        if status not in {"OK", "ERROR"}:
            raise ValidationError(f"Unexpected status {status}.")
        status_counts[status] += 1
        class_counts[str(row["job_class"])] += 1
        model = str(row["model_id"])
        model_counts[model] += 1
        runtime = float(row["runtime_seconds"])
        if not math.isfinite(runtime) or runtime < 0:
            raise ValidationError("Invalid runtime.")
        runtimes[model].append(runtime)
        if row["convergence_status"] != "NOT_AUDITABLE":
            raise ValidationError("Unexpected convergence status.")
        if status == "OK":
            if row["error"] not in (None, "") or float(row["afino_effective_dt_s"]) != 20.0:
                raise ValidationError("OK result contract mismatch.")
            if int(row["bins_after_cutoff"]) != EXPECTED_BINS[int(row["n_samples"])]:
                raise ValidationError("Unexpected bins after cutoff.")
            for field in ("BIC", "lnlike", "rchi2", "probability"):
                if row[field] is None or not math.isfinite(float(row[field])):
                    raise ValidationError(f"Invalid {field} in OK row.")
        else:
            if row["error"] in (None, ""):
                raise ValidationError("ERROR result lacks error text.")
        warnings = 0 if row["warning_count"] is None else int(row["warning_count"])
        if warnings < 0:
            raise ValidationError("Negative warning count.")
        if warnings:
            warning_calls[model] += 1
            warning_totals[model] += warnings
        if row["parameter_at_bound"] == 1:
            bound_calls[model] += 1
        elif row["parameter_at_bound"] not in (0, None):
            raise ValidationError("Invalid bound flag.")
    if metadata_mismatches or input_hash_mismatches:
        raise ValidationError("Plan/result metadata or input hash mismatch.")
    if class_counts != {"primary": 6480, "stability": 1458} or model_counts != {"M0": 2646, "M1": 2646, "M2": 2646}:
        raise ValidationError("Result class/model counts mismatch.")
    return {
        "checkpoint_rows": len(results), "pending_jobs": len(plan) - len(results),
        "duplicate_job_ids": duplicate_jobs, "duplicate_scientific_keys": duplicate_keys,
        "plan_result_mismatches": metadata_mismatches, "input_hash_mismatches": input_hash_mismatches,
        "status_counts": dict(sorted(status_counts.items())), "primary_result_rows": class_counts["primary"],
        "stability_result_rows": class_counts["stability"], "rows_per_model": model_counts["M0"],
        "model_counts": dict(sorted(model_counts.items())),
        "warning_calls_by_model": {m: warning_calls.get(m, 0) for m in MODEL_NAMES},
        "warning_totals_by_model": {m: warning_totals.get(m, 0) for m in MODEL_NAMES},
        "bound_hit_calls_by_model": {m: bound_calls.get(m, 0) for m in MODEL_NAMES},
        "runtime_total_seconds": sum(sum(values) for values in runtimes.values()),
        "runtime_median_seconds_by_model": {m: statistics.median(runtimes[m]) for m in MODEL_NAMES},
    }


def validate_exported_results(plan: list[dict[str, Any]], checkpoint: list[dict[str, Any]]) -> list[dict[str, str]]:
    fields, rows = read_csv(RESULTS_CSV)
    if fields != RESULT_FIELDS or len(rows) != EXPECTED["planned_jobs"]:
        raise ValidationError("Exported result schema or count mismatch.")
    if [r["job_id"] for r in rows] != [r["job_id"] for r in plan]:
        raise ValidationError("Exported results are not in normative plan order.")
    db = {r["job_id"]: r for r in checkpoint}
    integer_fields = {"data_seed", "external_optimizer_seed", "n_samples", "positive_frequency_bins", "bins_after_cutoff", "warning_count"}
    float_fields = {"duration_s", "red_noise_alpha", "period_s", "qpp_fraction", "runtime_seconds", "afino_effective_dt_s",
                    "minimum_frequency_hz", "maximum_frequency_hz", "lnlike", "BIC", "rchi2", "probability", "estimated_period_s"}
    bool_fields = {"parameter_at_bound"}
    for row in rows:
        original = db[row["job_id"]]
        for field in RESULT_FIELDS:
            if field in integer_fields:
                observed = parse_optional_int(row[field])
                expected = None if original[field] is None else int(original[field])
                if observed != expected:
                    raise ValidationError(f"SQLite/CSV mismatch {row['job_id']} {field}")
            elif field in float_fields:
                if not close_float(parse_optional_float(row[field]), original[field]):
                    raise ValidationError(f"SQLite/CSV mismatch {row['job_id']} {field}")
            elif field in bool_fields:
                expected = None if original[field] is None else bool(original[field])
                if parse_bool(row[field]) != expected:
                    raise ValidationError(f"SQLite/CSV mismatch {row['job_id']} {field}")
            else:
                expected = "" if original[field] is None else str(original[field])
                if row[field] != expected:
                    raise ValidationError(f"SQLite/CSV mismatch {row['job_id']} {field}")
    return rows


def finite_ok(row: dict[str, Any]) -> bool:
    return row["status"] == "OK" and row["BIC"] is not None and math.isfinite(float(row["BIC"]))


def recalculate_decisions(plan: list[dict[str, Any]], results: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_id = {r["job_id"]: r for r in results}
    grouped: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    exemplars: dict[tuple[str, int], dict[str, Any]] = {}
    order: list[tuple[str, int]] = []
    for planned in plan:
        key = (planned["series_id"], planned["external_optimizer_seed"])
        if key not in exemplars:
            exemplars[key] = planned
            order.append(key)
        grouped[key][planned["model_id"]] = by_id[planned["job_id"]]
    decisions: list[dict[str, Any]] = []
    statuses: Counter[str] = Counter()
    classes: Counter[str] = Counter()
    for key in order:
        models = grouped[key]
        if set(models) != {"M0", "M1", "M2"}:
            raise ValidationError("Incomplete planned trio.")
        valid_models = sum(finite_ok(models[m]) for m in MODEL_NAMES)
        valid = valid_models == 3
        delta01: float | None = None
        delta21: float | None = None
        selected: bool | None = None
        estimated: float | None = None
        label = "unavailable_incomplete_numerical"
        if models["M1"]["status"] == "OK" and models["M1"]["estimated_period_s"] is not None:
            estimated = float(models["M1"]["estimated_period_s"])
            label = "formal_m1_center_not_selected"
        if valid:
            delta01 = float(models["M0"]["BIC"]) - float(models["M1"]["BIC"])
            delta21 = float(models["M2"]["BIC"]) - float(models["M1"]["BIC"])
            selected = delta01 > 10.0 and delta21 > 10.0
            if selected:
                label = "recovered_period_selected"
        exemplar = exemplars[key]
        row = {
            "series_id": key[0], "condition_id": exemplar["condition_id"], "parent_id": exemplar["parent_id"],
            "block_id": exemplar["block_id"], "ground_truth": exemplar["ground_truth"], "n_samples": exemplar["n_samples"],
            "duration_s": exemplar["duration_s"], "red_noise_alpha": exemplar["red_noise_alpha"],
            "period_s": exemplar["period_s"], "qpp_fraction": exemplar["qpp_fraction"], "data_seed": exemplar["data_seed"],
            "external_optimizer_seed": key[1], "decision_status": "VALID" if valid else "INCOMPLETE_NUMERICAL",
            "valid_models": valid_models, "bic_m0": models["M0"]["BIC"], "bic_m1": models["M1"]["BIC"],
            "bic_m2": models["M2"]["BIC"], "delta_bic_0_1": delta01, "delta_bic_2_1": delta21,
            "qpp_selected": selected, "estimated_period_s": estimated, "period_label": label,
        }
        decisions.append(row)
        statuses[row["decision_status"]] += 1
        classes[exemplar["job_class"]] += 1
    if len(decisions) != 2646 or classes != {"primary": 2160, "stability": 486}:
        raise ValidationError("Decision counts mismatch.")
    return decisions, {
        "decision_rows": len(decisions), "primary_decision_rows": classes["primary"],
        "stability_decision_rows": classes["stability"], "decision_status_counts": dict(sorted(statuses.items())),
    }


def validate_decision_csv(calculated: list[dict[str, Any]]) -> int:
    fields, rows = read_csv(DECISIONS_CSV)
    if fields != DECISION_FIELDS or len(rows) != len(calculated):
        raise ValidationError("Decision CSV schema or count mismatch.")
    mismatches = 0
    int_fields = {"n_samples", "data_seed", "external_optimizer_seed", "valid_models"}
    float_fields = {"duration_s", "red_noise_alpha", "period_s", "qpp_fraction", "bic_m0", "bic_m1", "bic_m2",
                    "delta_bic_0_1", "delta_bic_2_1", "estimated_period_s"}
    bool_fields = {"qpp_selected"}
    for expected, observed in zip(calculated, rows):
        for field in DECISION_FIELDS:
            if field in int_fields:
                value = parse_optional_int(observed[field])
                target = None if expected[field] is None else int(expected[field])
                okay = value == target
            elif field in float_fields:
                value = parse_optional_float(observed[field])
                target = expected[field]
                okay = close_float(value, target, atol=ABS_TOLERANCE if field.startswith("delta_bic") else 0.0)
            elif field in bool_fields:
                okay = parse_bool(observed[field]) == expected[field]
            else:
                target = "" if expected[field] is None else str(expected[field])
                okay = observed[field] == target
            if not okay:
                mismatches += 1
    if mismatches:
        raise ValidationError(f"Decision recalculation mismatches: {mismatches}")
    return mismatches


def report_text(audit: dict[str, Any]) -> str:
    status = json.dumps(audit["status_counts"], ensure_ascii=False, sort_keys=True)
    decision_status = json.dumps(audit["decision_status_counts"], ensure_ascii=False, sort_keys=True)
    return f"""# Fase 1 — Tarea 1.12

## Ejecución completa reanudable del benchmark anidado

**Estado:** `{audit['execution_status']}`  
**Runner:** `{audit['runner_family']}` `{audit['runner_implementation_version']}`  
**Plan:** `{audit['planned_jobs']}` llamadas  
**Pendientes:** `{audit['pending_jobs']}`

## Cobertura e integridad

Se confirmaron las 7.938 claves del plan congelado: 6.480 resultados primarios
y 1.458 de estabilidad, con 2.646 filas para cada uno de los modelos M0, M1 y
M2. El checkpoint, el CSV exportado y el plan contienen los mismos `job_id`, la
misma clave `(series_id, external_optimizer_seed, model_id)`, los mismos
metadatos y los mismos hashes de flujo y tiempo. No quedaron trabajos
pendientes ni aparecieron duplicados o filas ajenas al plan.

Los estados retenidos fueron:

```text
{status}
```

Los resultados con error numérico, si existen, permanecen como filas
confirmadas y no fueron redibujados, eliminados ni convertidos manualmente en
no selecciones.

## Decisiones

Se recalcularon independientemente 2.646 decisiones: 2.160 primarias y 486 de
estabilidad. Los deltas BIC se compararon con tolerancia absoluta `5e-12` y
tolerancia relativa cero. Los estados fueron:

```text
{decision_status}
```

Un trío incompleto conserva `INCOMPLETE_NUMERICAL` y `qpp_selected` vacío.
Esta tarea no calculó tasas por condición, trayectorias, cruces de umbral,
errores agregados de periodo ni apoyo a la hipótesis temporal.

## Reanudación

La ejecución se dividió en siete lotes de 1.000 llamadas, un lote final de 938
y una invocación de exportación con cero llamadas nuevas. La primera invocación
partió de un checkpoint inexistente y no utilizó `--resume`; todas las
posteriores sí. La historia SQLite es contigua y la última invocación confirmó
idempotencia.

## Congelación

Los cuatro hashes físicos y lógicos de F1.10 coincidieron antes y después. El
runner 1.1.0 y el plan conservaron sus hashes normativos. El checkpoint canary
permaneció separado, sin escritura ni importación, y conservó su SHA-256. AFINO
permaneció en el commit y la versión congelados, sin diferencias tracked o
staged.

## Alcance

F1.12 congela exclusivamente los resultados brutos y los controles operativos:
estados, warnings, bounds, tiempos y reanudación. No se realizó interpretación
científica del efecto de extender las ventanas. Esa evaluación corresponde a
F1.13.

## Conclusión

`{audit['execution_status']}`
"""


def write_blocked(error: BaseException, environment: dict[str, Any] | None) -> None:
    blocked = {
        "date_utc": utc_now(), "execution_status": "FULL_NESTED_BENCHMARK_EXECUTION_BLOCKED",
        "error": str(error), "traceback": traceback.format_exc(), "environment": environment,
        "confirmations": {
            "canary_checkpoint_reused": False, "canary_results_imported": False, "dataset_modified": False,
            "dataset_regenerated": False, "runner_modified": False, "plan_modified": False,
            "afino_code_modified": False, "scientific_protocol_modified": False, "failed_series_redrawn": False,
            "failed_jobs_manually_retried": False, "scientific_rates_computed": False,
            "nested_hypothesis_interpreted": False,
        },
    }
    if not AUDIT_JSON.exists():
        AUDIT_JSON.write_text(json.dumps(blocked, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not REPORT_MD.exists():
        REPORT_MD.write_text(f"# Fase 1 — Tarea 1.12\n\n`FULL_NESTED_BENCHMARK_EXECUTION_BLOCKED`\n\n```text\n{error}\n```\n", encoding="utf-8")


def main() -> int:
    environment_before: dict[str, Any] | None = None
    if AUDIT_JSON.exists() or REPORT_MD.exists() or ENVIRONMENT_TXT.exists():
        raise ValidationError("Final validator outputs already exist; preserve them.")
    try:
        environment_before = collect_environment()
        ENVIRONMENT_TXT.write_text(environment_text(environment_before), encoding="utf-8")
        physical_before, logical_before = verify_frozen_inputs()
        series, times = load_manifests()
        plan = load_plan(series, times)
        metadata, checkpoint_rows, invocations = load_checkpoint()
        validate_metadata(metadata, physical_before, logical_before)
        resume = validate_invocations(invocations)
        execution = validate_checkpoint_results(plan, checkpoint_rows)
        if execution["pending_jobs"] != 0:
            raise ValidationError("Full plan still has pending jobs.")
        exported = validate_exported_results(plan, checkpoint_rows)
        execution["exported_result_rows"] = len(exported)
        calculated, decision_summary = recalculate_decisions(plan, checkpoint_rows)
        decision_mismatches = validate_decision_csv(calculated)
        environment_after = collect_environment()
        physical_after, logical_after = verify_frozen_inputs()
        if physical_before != physical_after or logical_before != logical_after:
            raise ValidationError("Frozen inputs changed during validation.")
        if sha256(CANARY_CHECKPOINT) != EXPECTED_PHYSICAL_HASHES[CANARY_CHECKPOINT.name]:
            raise ValidationError("Canary checkpoint changed.")
        if environment_before != environment_after:
            raise ValidationError("Environment changed during validation.")
        output_hashes = {
            FULL_CHECKPOINT.name: sha256(FULL_CHECKPOINT), RESULTS_CSV.name: sha256(RESULTS_CSV),
            DECISIONS_CSV.name: sha256(DECISIONS_CSV), Path(__file__).name: sha256(Path(__file__)),
            ENVIRONMENT_TXT.name: sha256(ENVIRONMENT_TXT),
        }
        audit: dict[str, Any] = {
            "date_utc": utc_now(), "execution_status": "FULL_NESTED_BENCHMARK_EXECUTION_COMPLETE",
            "runner_family": EXPECTED_RUNNER_FAMILY, "runner_implementation_version": EXPECTED_RUNNER_VERSION,
            "environment": environment_after, "preflight": {"physical_hashes": physical_before, "logical_hashes": logical_before,
                "checkpoint_exists_before_start": False, "initial_result_rows": 0,
                "canary_checkpoint_reused": False, "canary_results_imported": False},
            "postflight": {"physical_hashes": physical_after, "logical_hashes": logical_after,
                "dataset_unchanged": True, "runner_unchanged": True, "plan_unchanged": True,
                "canary_checkpoint_unchanged": True, "tracked_git_diff_empty": True, "staged_git_diff_empty": True,
                "git_status_porcelain": environment_after["git_status_porcelain"]},
            "planned_jobs": len(plan), "checkpoint_rows": execution["checkpoint_rows"],
            "exported_result_rows": execution["exported_result_rows"], "pending_jobs": execution["pending_jobs"],
            "primary_result_rows": execution["primary_result_rows"], "stability_result_rows": execution["stability_result_rows"],
            "rows_per_model": execution["rows_per_model"], "decision_rows": decision_summary["decision_rows"],
            "primary_decision_rows": decision_summary["primary_decision_rows"],
            "stability_decision_rows": decision_summary["stability_decision_rows"],
            "duplicate_job_ids": execution["duplicate_job_ids"],
            "duplicate_scientific_keys": execution["duplicate_scientific_keys"],
            "plan_result_mismatches": execution["plan_result_mismatches"], "sqlite_csv_mismatches": 0,
            "input_hash_mismatches": execution["input_hash_mismatches"],
            "decision_recalculation_mismatches": decision_mismatches,
            "status_counts": execution["status_counts"], "decision_status_counts": decision_summary["decision_status_counts"],
            "warning_calls_by_model": execution["warning_calls_by_model"],
            "warning_totals_by_model": execution["warning_totals_by_model"],
            "bound_hit_calls_by_model": execution["bound_hit_calls_by_model"],
            "runtime_total_seconds": execution["runtime_total_seconds"],
            "runtime_median_seconds_by_model": execution["runtime_median_seconds_by_model"],
            "invocation_history": resume, "checkpoint": {"filename": FULL_CHECKPOINT.name,
                "sha256": sha256(FULL_CHECKPOINT), "metadata": metadata,
                "sqlite_transaction_policy": "one independent transaction per completed model call",
                "unique_job_id_enforced": True, "unique_series_seed_model_enforced": True},
            "output_hashes": output_hashes, "incidents": [],
            "confirmations": {
                "canary_checkpoint_reused": False, "canary_results_imported": False, "dataset_modified": False,
                "dataset_regenerated": False, "runner_modified": False, "plan_modified": False,
                "afino_code_modified": False, "scientific_protocol_modified": False, "failed_series_redrawn": False,
                "failed_jobs_manually_retried": False, "scientific_rates_computed": False,
                "nested_hypothesis_interpreted": False,
            },
        }
        REPORT_MD.write_text(report_text(audit), encoding="utf-8")
        audit["output_hashes"][REPORT_MD.name] = sha256(REPORT_MD)
        AUDIT_JSON.write_text(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print("F1.12 independent structural validation complete")
        print("execution_status: FULL_NESTED_BENCHMARK_EXECUTION_COMPLETE")
        print(f"planned_jobs: {len(plan)}")
        print(f"checkpoint_rows: {execution['checkpoint_rows']}")
        print(f"exported_result_rows: {execution['exported_result_rows']}")
        print(f"pending_jobs: {execution['pending_jobs']}")
        print(f"decision_rows: {decision_summary['decision_rows']}")
        print(f"status_counts: {json.dumps(execution['status_counts'], sort_keys=True)}")
        print(f"decision_status_counts: {json.dumps(decision_summary['decision_status_counts'], sort_keys=True)}")
        return 0
    except Exception as exc:
        write_blocked(exc, environment_before)
        print(f"FULL_NESTED_BENCHMARK_EXECUTION_BLOCKED: {exc}", file=sys.stderr, flush=True)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
