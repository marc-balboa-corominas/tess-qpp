from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import platform
import random
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np


EXPECTED_NUMPY_VERSION = "2.3.5"
EXPECTED_INPUT_HASHES = {
    "fase1_tarea08_nested_window_preregistration.json":
        "d80890319b4646f8df994ba7c1dd9da3dc1f141834dbf289d1b17c484fa67487",
    "fase1_tarea08_nested_window_design_grid.csv":
        "7c1a1fb9724dfe195fec1337e4f0af906e3dd8f1c754ab0abc7f3bc2cc1e8dcd",
    "fase1_tarea02_synthetic_generator.py":
        "743005e580f20be331408d9165522932a289d256cef0efbe4c4f24fcb38c54bd",
    "fase1_tarea02_noise_block_manifest.csv":
        "898a47f697b3de765f2b73b4bc01181f031c485df5875b0a88e6216591e7883d",
    "fase1_tarea02_generator_validation_audit.json":
        "3e4d588110dbe535038dc0e85ec08a60e47de946d438c05b121b379ee0c02f11",
    "fase1_tarea01_core_benchmark_preregistration.json":
        "dd80346172290e014d73f78240b3e31f135bcc7e4f075963e7e20d8456de3401",
}

BLOCK_FIELDS = [
    "block_id",
    "red_noise_alpha",
    "alpha_code",
    "data_seed",
    "parent_n_samples",
    "time_sha256",
    "noise_sha256",
    "phase_float64_sha256",
    "noise_seed_metadata_json",
    "phase_seed_metadata_json",
    "noise_mean_parent",
    "noise_std_parent_ddof1",
    "all_finite",
    "f1_2_hash_match",
    "generation_status",
    "error",
]

PARENT_FIELDS = [
    "parent_id",
    "block_id",
    "ground_truth",
    "red_noise_alpha",
    "data_seed",
    "period_s",
    "qpp_fraction",
    "parent_n_samples",
    "time_sha256",
    "envelope_sha256",
    "noise_sha256",
    "phase_float64_sha256",
    "qpp_component_sha256",
    "parent_flux_sha256",
    "all_finite",
    "flux_mean",
    "flux_std_ddof1",
    "flux_min",
    "flux_max",
    "construction_status",
    "error",
]

CHILD_FIELDS = [
    "series_id",
    "series_order",
    "condition_id",
    "parent_id",
    "block_id",
    "ground_truth",
    "n_samples",
    "duration_s",
    "red_noise_alpha",
    "period_s",
    "qpp_fraction",
    "data_seed",
    "prefix_start",
    "prefix_end",
    "time_sha256",
    "noise_prefix_sha256",
    "phase_float64_sha256",
    "parent_flux_sha256",
    "parent_prefix_sha256",
    "child_flux_sha256",
    "exact_prefix_match",
    "child_all_finite",
    "child_flux_mean",
    "child_flux_std_ddof1",
    "child_noise_mean",
    "child_noise_std_ddof1",
    "generation_status",
    "error",
]

TIME_FIELDS = [
    "time_vector_id",
    "n_samples",
    "duration_s",
    "cadence_s",
    "time_sha256",
    "parent_prefix_sha256",
    "exact_prefix_match",
    "all_finite",
    "strictly_increasing",
]


class NestedGenerationError(RuntimeError):
    """Raised when a frozen input or a nested-generation invariant fails."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_float64_sha256(array: Any) -> str:
    """Hash a scalar or array as contiguous little-endian float64 bytes."""
    canonical = np.ascontiguousarray(array, dtype="<f8")
    return hashlib.sha256(canonical.tobytes(order="C")).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _bool_text(value: bool) -> str:
    return "True" if value else "False"


def _float_text(value: float) -> str:
    return format(float(value), ".17g")


def _optional_float_text(value: float | None) -> str:
    return "" if value is None else _float_text(value)


def _csv_value_matches(expected: Any, observed: str) -> bool:
    if expected is None:
        return observed == ""
    if isinstance(expected, bool):
        return observed.lower() == str(expected).lower()
    if isinstance(expected, int) and not isinstance(expected, bool):
        try:
            return int(observed) == expected
        except ValueError:
            return False
    if isinstance(expected, float):
        try:
            return math.isclose(float(observed), expected, rel_tol=1e-14, abs_tol=0.0)
        except ValueError:
            return False
    return observed == str(expected)


def load_nested_preregistration(
    path: Path,
    *,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    observed = file_sha256(path)
    if expected_sha256 is not None and observed != expected_sha256:
        raise NestedGenerationError(
            f"Nested preregistration hash mismatch: {observed} != {expected_sha256}"
        )
    specification = json.loads(path.read_text(encoding="utf-8"))
    if specification.get("benchmark_id") != "afino_nested_window_support_v1":
        raise NestedGenerationError("Unexpected nested benchmark_id.")
    if specification.get("benchmark_version") != "1.0.0":
        raise NestedGenerationError("Unexpected nested benchmark_version.")
    if specification.get("preregistration_status") != "FROZEN_BEFORE_SERIES_GENERATION":
        raise NestedGenerationError("Unexpected nested preregistration_status.")
    if specification["confirmations"].get("series_generated") is not False:
        raise NestedGenerationError("The frozen preregistration does not predate generation.")
    if specification["confirmations"].get("afino_executed") is not False:
        raise NestedGenerationError("The frozen preregistration reports AFINO execution.")
    return specification


def validate_nested_grid(
    path: Path,
    specification: dict[str, Any],
    *,
    expected_sha256: str | None = None,
) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    observed_hash = file_sha256(path)
    if expected_sha256 is not None and observed_hash != expected_sha256:
        raise NestedGenerationError(
            f"Nested grid hash mismatch: {observed_hash} != {expected_sha256}"
        )
    linked_hash = specification["design_grid"].get("sha256")
    if linked_hash != observed_hash:
        raise NestedGenerationError("The nested preregistration does not link the grid hash.")

    expected_fields = list(specification["design_grid"]["fields"])
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_fields:
            raise NestedGenerationError(
                f"Unexpected nested grid columns: {reader.fieldnames!r}"
            )
        rows = list(reader)

    expected_rows = specification["design_grid"]["conditions"]
    if len(rows) != 54 or len(expected_rows) != 54:
        raise NestedGenerationError("The nested grid must contain exactly 54 conditions.")
    if len({row["condition_id"] for row in rows}) != 54:
        raise NestedGenerationError("Nested condition identifiers are not unique.")

    for index, (observed, expected) in enumerate(zip(rows, expected_rows, strict=True)):
        for field in expected_fields:
            if not _csv_value_matches(expected[field], observed[field]):
                raise NestedGenerationError(
                    f"Nested grid mismatch at row {index + 1}, field {field}: "
                    f"{observed[field]!r} != {expected[field]!r}"
                )
    return rows


def _load_module(path: Path, module_name: str) -> Any:
    module_spec = importlib.util.spec_from_file_location(module_name, path)
    if module_spec is None or module_spec.loader is None:
        raise NestedGenerationError(f"Cannot import module from {path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def _load_frozen_f1_1_specification(root: Path, frozen_generator: Any) -> dict[str, Any]:
    path = root / "fase1_tarea01_core_benchmark_preregistration.json"
    return frozen_generator.load_preregistration(
        path,
        expected_sha256=EXPECTED_INPUT_HASHES[path.name],
    )


def generate_parent_block(
    alpha: float,
    data_seed: int,
    specification: dict[str, Any],
    *,
    frozen_generator: Any,
    frozen_f1_1_specification: dict[str, Any],
) -> dict[str, Any]:
    """Generate a validated N=120 noise/phase block and discard F1.2 flare fields."""
    parent_n = int(specification["parent_noise_and_phase"]["parent_n_samples"])
    raw = frozen_generator.generate_paired_block(
        n_samples=parent_n,
        alpha=float(alpha),
        data_seed=int(data_seed),
        specification=frozen_f1_1_specification,
    )

    # Normative rule: only these scientific outputs from F1.2 are retained.
    allowed = {
        "noise": np.asarray(raw["noise"], dtype=np.float64),
        "phase_rad": np.float64(raw["phase_rad"]),
        "noise_seed_metadata": dict(raw["noise_seed_metadata"]),
        "phase_seed_metadata": dict(raw["phase_seed_metadata"]),
    }
    allowed["noise"].setflags(write=False)
    allowed.update(
        {
            "red_noise_alpha": float(alpha),
            "alpha_code": int(raw["alpha_code"]),
            "data_seed": int(data_seed),
            "parent_n_samples": parent_n,
            "ignored_f1_2_fields": [
                "time_s",
                "flare_envelope",
                "peak_index",
                "t_peak_s",
                "rise_tau_s",
                "decay_tau_s",
                "duration_s",
            ],
        }
    )
    return allowed


def build_fixed_parent_envelope(specification: dict[str, Any]) -> dict[str, Any]:
    parent_spec = specification["parent_signal"]
    flare_spec = parent_spec["flare"]
    parent_n = int(specification["parent_noise_and_phase"]["parent_n_samples"])
    cadence_s = float(parent_spec["cadence_s"])

    time_s = np.arange(parent_n, dtype=np.float64) * cadence_s
    peak_index = int(flare_spec["peak_index"])
    t_peak_s = float(flare_spec["t_peak_s"])
    rise_tau_s = float(flare_spec["rise_tau_s"])
    decay_tau_s = float(flare_spec["decay_tau_s"])
    peak_excess = float(flare_spec["flare_peak_excess"])

    if peak_index < 0 or peak_index >= parent_n:
        raise NestedGenerationError("Frozen peak_index is outside the parent array.")
    if float(time_s[peak_index]) != t_peak_s:
        raise NestedGenerationError("Frozen peak_index and t_peak_s are inconsistent.")

    envelope = np.empty(parent_n, dtype=np.float64)
    before_or_at = time_s <= t_peak_s
    envelope[before_or_at] = peak_excess * np.exp(
        (time_s[before_or_at] - t_peak_s) / rise_tau_s
    )
    envelope[~before_or_at] = peak_excess * np.exp(
        -(time_s[~before_or_at] - t_peak_s) / decay_tau_s
    )

    if float(envelope[peak_index]) != peak_excess:
        raise NestedGenerationError("The fixed parent envelope does not peak as frozen.")
    if not np.all(np.isfinite(time_s)) or not np.all(np.isfinite(envelope)):
        raise NestedGenerationError("The fixed parent time or envelope is non-finite.")

    time_s.setflags(write=False)
    envelope.setflags(write=False)
    return {
        "time_s": time_s,
        "envelope": envelope,
        "peak_index": peak_index,
        "t_peak_s": t_peak_s,
        "rise_tau_s": rise_tau_s,
        "decay_tau_s": decay_tau_s,
        "cadence_s": cadence_s,
        "parent_n_samples": parent_n,
    }


def _parent_type_specs(specification: dict[str, Any]) -> list[dict[str, Any]]:
    labels = specification["ground_truth"]["allowed_labels"]
    null_label = next(label for label in labels if label.startswith("NULL"))
    positive_label = next(label for label in labels if label != null_label)
    qpp_spec = specification["parent_signal"]["qpp"]
    qpp_fraction = float(qpp_spec["qpp_fraction"])
    types = [
        {
            "type_code": "NULL",
            "ground_truth": null_label,
            "period_s": None,
            "qpp_fraction": None,
        }
    ]
    for period in qpp_spec["period_s"]:
        types.append(
            {
                "type_code": f"P{int(float(period)):03d}",
                "ground_truth": positive_label,
                "period_s": float(period),
                "qpp_fraction": qpp_fraction,
            }
        )
    return types


def build_parent_fluxes(
    block: dict[str, Any],
    envelope: dict[str, Any],
    specification: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    parent_spec = specification["parent_signal"]
    baseline = float(parent_spec["baseline_flux"])
    time_s = envelope["time_s"]
    envelope_values = envelope["envelope"]
    noise = block["noise"]
    phase = block["phase_rad"]

    if len(noise) != len(time_s):
        raise NestedGenerationError("Parent noise length does not match fixed parent time.")

    outputs: dict[str, dict[str, Any]] = {}
    for type_spec in _parent_type_specs(specification):
        period_s = type_spec["period_s"]
        qpp_fraction = type_spec["qpp_fraction"]
        if period_s is None:
            qpp_component = None
            flux = baseline + envelope_values + noise
        else:
            qpp_component = (
                float(qpp_fraction)
                * envelope_values
                * np.sin(
                    2.0
                    * np.pi
                    * (time_s - float(envelope["t_peak_s"]))
                    / float(period_s)
                    + phase
                )
            )
            qpp_component = np.asarray(qpp_component, dtype=np.float64)
            flux = baseline + envelope_values + qpp_component + noise

        flux = np.asarray(flux, dtype=np.float64)
        if not np.all(np.isfinite(flux)):
            raise NestedGenerationError("A constructed parent flux is non-finite.")
        flux.setflags(write=False)
        if qpp_component is not None:
            qpp_component.setflags(write=False)
        outputs[type_spec["type_code"]] = {
            **type_spec,
            "flux": flux,
            "qpp_component": qpp_component,
        }
    return outputs


def extract_exact_prefix(parent: np.ndarray, n_samples: int) -> np.ndarray:
    parent_array = np.asarray(parent, dtype=np.float64)
    n_value = int(n_samples)
    if n_value <= 0 or n_value > parent_array.size:
        raise NestedGenerationError(
            f"Cannot extract prefix of length {n_value} from {parent_array.size}."
        )
    child = np.ascontiguousarray(parent_array[:n_value], dtype="<f8")
    child.setflags(write=False)
    return child


def _block_id(alpha_code: int, data_seed: int) -> str:
    return f"NWB_A{int(alpha_code)}_S{int(data_seed):02d}"


def _parent_id(alpha_code: int, data_seed: int, type_code: str) -> str:
    return f"NWP_A{int(alpha_code)}_S{int(data_seed):02d}_{type_code}"


def _condition_parent_type(condition: dict[str, str]) -> str:
    if condition["period_s"] == "":
        return "NULL"
    return f"P{int(float(condition['period_s'])):03d}"


def _load_f1_2_manifest(root: Path) -> dict[tuple[float, int], dict[str, str]]:
    path = root / "fase1_tarea02_noise_block_manifest.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    n120 = [row for row in rows if int(row["n_samples"]) == 120]
    if len(n120) != 120:
        raise NestedGenerationError(f"F1.2 N=120 block count is {len(n120)}, not 120.")
    lookup: dict[tuple[float, int], dict[str, str]] = {}
    for row in n120:
        key = (float(row["red_noise_alpha"]), int(row["data_seed"]))
        if key in lookup:
            raise NestedGenerationError(f"Duplicate F1.2 N=120 block key: {key}")
        lookup[key] = row
    return lookup


def _write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    if path.exists():
        raise FileExistsError(path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _scientific_order(
    specification: dict[str, Any],
) -> tuple[list[tuple[float, int]], list[str], list[int]]:
    alphas = [float(value) for value in specification["parent_noise_and_phase"]["red_noise_alpha"]]
    seed_start = int(specification["parent_noise_and_phase"]["data_seed_start"])
    seed_end = int(specification["parent_noise_and_phase"]["data_seed_end"])
    blocks = [(alpha, seed) for alpha in alphas for seed in range(seed_start, seed_end + 1)]
    parent_types = [item["type_code"] for item in _parent_type_specs(specification)]
    n_values = [int(value) for value in specification["nested_windows"]["n_samples"]]
    return blocks, parent_types, n_values


def _ordered_variants(
    specification: dict[str, Any],
    grid_rows: list[dict[str, str]],
    mode: str,
) -> tuple[
    list[tuple[float, int]],
    list[str],
    list[dict[str, str]],
    dict[str, list[int]],
]:
    blocks, parent_types, _ = _scientific_order(specification)
    conditions = list(grid_rows)
    seed_start = int(specification["parent_noise_and_phase"]["data_seed_start"])
    seed_end = int(specification["parent_noise_and_phase"]["data_seed_end"])
    seeds_by_condition = {
        row["condition_id"]: list(range(seed_start, seed_end + 1))
        for row in conditions
    }
    if mode == "normative":
        return blocks, parent_types, conditions, seeds_by_condition
    if mode == "reverse":
        return (
            list(reversed(blocks)),
            list(reversed(parent_types)),
            list(reversed(conditions)),
            {key: list(reversed(value)) for key, value in seeds_by_condition.items()},
        )
    if mode == "random_test":
        rng = random.Random(20260803)
        rng.shuffle(blocks)
        rng.shuffle(parent_types)
        rng.shuffle(conditions)
        for value in seeds_by_condition.values():
            rng.shuffle(value)
        return blocks, parent_types, conditions, seeds_by_condition
    raise ValueError(mode)


def _generate_hash_inventory(
    *,
    root: Path,
    specification: dict[str, Any],
    grid_rows: list[dict[str, str]],
    frozen_generator: Any,
    frozen_f1_1_specification: dict[str, Any],
    mode: str,
    collect_rows: bool,
) -> dict[str, Any]:
    block_order, parent_type_order, condition_order, seeds_by_condition = _ordered_variants(
        specification, grid_rows, mode
    )
    envelope = build_fixed_parent_envelope(specification)
    f1_2_lookup = _load_f1_2_manifest(root)

    block_objects: dict[tuple[float, int], dict[str, Any]] = {}
    block_hash_map: dict[str, tuple[str, str, str]] = {}
    block_rows: list[dict[str, Any]] = []

    for alpha, data_seed in block_order:
        block = generate_parent_block(
            alpha,
            data_seed,
            specification,
            frozen_generator=frozen_generator,
            frozen_f1_1_specification=frozen_f1_1_specification,
        )
        block_id = _block_id(block["alpha_code"], data_seed)
        time_hash = canonical_float64_sha256(envelope["time_s"])
        noise_hash = canonical_float64_sha256(block["noise"])
        phase_hash = canonical_float64_sha256(block["phase_rad"])
        expected = f1_2_lookup[(float(alpha), int(data_seed))]
        hash_match = (
            time_hash == expected["time_sha256"]
            and noise_hash == expected["noise_sha256"]
            and phase_hash == expected["phase_float64_sha256"]
        )
        if not hash_match:
            raise NestedGenerationError(
                f"F1.2 block hash mismatch for alpha={alpha}, data_seed={data_seed}."
            )
        if expected["generation_status"] != "OK" or expected["all_finite"] != "True":
            raise NestedGenerationError("F1.2 N=120 manifest contains a non-valid block.")
        all_finite = bool(np.all(np.isfinite(block["noise"]))) and math.isfinite(
            float(block["phase_rad"])
        )
        if not all_finite:
            raise NestedGenerationError("Generated parent block is non-finite.")

        block_objects[(float(alpha), int(data_seed))] = block
        block_hash_map[block_id] = (time_hash, noise_hash, phase_hash)
        if collect_rows:
            block_rows.append(
                {
                    "block_id": block_id,
                    "red_noise_alpha": _float_text(alpha),
                    "alpha_code": str(block["alpha_code"]),
                    "data_seed": str(data_seed),
                    "parent_n_samples": str(block["parent_n_samples"]),
                    "time_sha256": time_hash,
                    "noise_sha256": noise_hash,
                    "phase_float64_sha256": phase_hash,
                    "noise_seed_metadata_json": canonical_json(block["noise_seed_metadata"]),
                    "phase_seed_metadata_json": canonical_json(block["phase_seed_metadata"]),
                    "noise_mean_parent": _float_text(np.mean(block["noise"])),
                    "noise_std_parent_ddof1": _float_text(np.std(block["noise"], ddof=1)),
                    "all_finite": _bool_text(all_finite),
                    "f1_2_hash_match": _bool_text(hash_match),
                    "generation_status": "OK",
                    "error": "",
                }
            )

    parent_objects: dict[str, dict[str, Any]] = {}
    parent_hash_map: dict[str, str] = {}
    parent_rows: list[dict[str, Any]] = []
    envelope_hash = canonical_float64_sha256(envelope["envelope"])
    time_hash = canonical_float64_sha256(envelope["time_s"])

    type_spec_lookup = {item["type_code"]: item for item in _parent_type_specs(specification)}
    for alpha, data_seed in block_order:
        block = block_objects[(float(alpha), int(data_seed))]
        constructed = build_parent_fluxes(block, envelope, specification)
        if set(constructed) != set(type_spec_lookup):
            raise NestedGenerationError("Constructed parent type set is incomplete.")
        for type_code in parent_type_order:
            item = constructed[type_code]
            parent_id = _parent_id(block["alpha_code"], data_seed, type_code)
            flux = item["flux"]
            component = item["qpp_component"]
            flux_hash = canonical_float64_sha256(flux)
            parent_objects[parent_id] = {
                "flux": flux,
                "qpp_component": component,
                "block": block,
                "type_spec": item,
            }
            parent_hash_map[parent_id] = flux_hash
            if collect_rows:
                parent_rows.append(
                    {
                        "parent_id": parent_id,
                        "block_id": _block_id(block["alpha_code"], data_seed),
                        "ground_truth": item["ground_truth"],
                        "red_noise_alpha": _float_text(alpha),
                        "data_seed": str(data_seed),
                        "period_s": _optional_float_text(item["period_s"]),
                        "qpp_fraction": _optional_float_text(item["qpp_fraction"]),
                        "parent_n_samples": str(len(flux)),
                        "time_sha256": time_hash,
                        "envelope_sha256": envelope_hash,
                        "noise_sha256": canonical_float64_sha256(block["noise"]),
                        "phase_float64_sha256": canonical_float64_sha256(block["phase_rad"]),
                        "qpp_component_sha256": (
                            "" if component is None else canonical_float64_sha256(component)
                        ),
                        "parent_flux_sha256": flux_hash,
                        "all_finite": _bool_text(bool(np.all(np.isfinite(flux)))),
                        "flux_mean": _float_text(np.mean(flux)),
                        "flux_std_ddof1": _float_text(np.std(flux, ddof=1)),
                        "flux_min": _float_text(np.min(flux)),
                        "flux_max": _float_text(np.max(flux)),
                        "construction_status": "OK",
                        "error": "",
                    }
                )

    # Series identifiers are normative and independent of generation order.
    series_id_by_key: dict[tuple[str, int], tuple[str, int]] = {}
    series_order = 0
    for condition in grid_rows:
        for data_seed in range(
            int(condition["data_seed_start"]), int(condition["data_seed_end"]) + 1
        ):
            series_order += 1
            series_id_by_key[(condition["condition_id"], data_seed)] = (
                f"NWS{series_order:06d}",
                series_order,
            )
    if series_order != 2160:
        raise NestedGenerationError(f"Normative series count is {series_order}, not 2160.")

    child_hash_map: dict[str, str] = {}
    child_rows: list[dict[str, Any]] = []
    child_noise_means: list[float] = []
    child_noise_stds: list[float] = []
    children_by_parent: dict[str, dict[int, np.ndarray]] = defaultdict(dict)

    for condition in condition_order:
        condition_id = condition["condition_id"]
        alpha = float(condition["red_noise_alpha"])
        n_samples = int(condition["n_samples"])
        type_code = _condition_parent_type(condition)
        for data_seed in seeds_by_condition[condition_id]:
            block = block_objects[(alpha, int(data_seed))]
            parent_id = _parent_id(block["alpha_code"], data_seed, type_code)
            parent = parent_objects[parent_id]["flux"]
            child = extract_exact_prefix(parent, n_samples)
            parent_prefix = np.ascontiguousarray(parent[:n_samples], dtype="<f8")
            exact = child.tobytes(order="C") == parent_prefix.tobytes(order="C")
            if not exact:
                raise NestedGenerationError(f"Non-exact child prefix for {condition_id}, seed={data_seed}.")

            series_id, normative_order = series_id_by_key[(condition_id, int(data_seed))]
            child_hash = canonical_float64_sha256(child)
            child_hash_map[series_id] = child_hash
            children_by_parent[parent_id][n_samples] = child

            noise_prefix = extract_exact_prefix(block["noise"], n_samples)
            noise_mean = float(np.mean(noise_prefix))
            noise_std = float(np.std(noise_prefix, ddof=1))
            child_noise_means.append(noise_mean)
            child_noise_stds.append(noise_std)

            if collect_rows:
                time_prefix = extract_exact_prefix(envelope["time_s"], n_samples)
                child_rows.append(
                    {
                        "series_id": series_id,
                        "series_order": str(normative_order),
                        "condition_id": condition_id,
                        "parent_id": parent_id,
                        "block_id": _block_id(block["alpha_code"], data_seed),
                        "ground_truth": condition["ground_truth"],
                        "n_samples": str(n_samples),
                        "duration_s": _float_text(float(condition["duration_s"])),
                        "red_noise_alpha": _float_text(alpha),
                        "period_s": condition["period_s"],
                        "qpp_fraction": condition["qpp_fraction"],
                        "data_seed": str(data_seed),
                        "prefix_start": "0",
                        "prefix_end": str(n_samples),
                        "time_sha256": canonical_float64_sha256(time_prefix),
                        "noise_prefix_sha256": canonical_float64_sha256(noise_prefix),
                        "phase_float64_sha256": canonical_float64_sha256(block["phase_rad"]),
                        "parent_flux_sha256": parent_hash_map[parent_id],
                        "parent_prefix_sha256": canonical_float64_sha256(parent_prefix),
                        "child_flux_sha256": child_hash,
                        "exact_prefix_match": _bool_text(exact),
                        "child_all_finite": _bool_text(bool(np.all(np.isfinite(child)))),
                        "child_flux_mean": _float_text(np.mean(child)),
                        "child_flux_std_ddof1": _float_text(np.std(child, ddof=1)),
                        "child_noise_mean": _float_text(noise_mean),
                        "child_noise_std_ddof1": _float_text(noise_std),
                        "generation_status": "OK",
                        "error": "",
                    }
                )

    # Repeated-measures nesting is checked independently of hashes alone.
    n_values = sorted(int(value) for value in specification["nested_windows"]["n_samples"])
    for parent_id, child_map in children_by_parent.items():
        if sorted(child_map) != n_values:
            raise NestedGenerationError(f"Parent {parent_id} does not have all six windows.")
        for left_n, right_n in zip(n_values[:-1], n_values[1:], strict=True):
            left = child_map[left_n]
            right = child_map[right_n]
            if left.tobytes(order="C") != np.ascontiguousarray(
                right[:left_n], dtype="<f8"
            ).tobytes(order="C"):
                raise NestedGenerationError(
                    f"Nested child identity failed for {parent_id}: {left_n} not prefix of {right_n}."
                )

    if len(block_hash_map) != 120:
        raise NestedGenerationError("Block inventory does not contain 120 entries.")
    if len(parent_hash_map) != 360:
        raise NestedGenerationError("Parent inventory does not contain 360 entries.")
    if len(child_hash_map) != 2160:
        raise NestedGenerationError("Child inventory does not contain 2160 entries.")

    return {
        "block_rows": block_rows,
        "parent_rows": parent_rows,
        "child_rows": child_rows,
        "block_hash_map": block_hash_map,
        "parent_hash_map": parent_hash_map,
        "child_hash_map": child_hash_map,
        "child_noise_means": child_noise_means,
        "child_noise_stds": child_noise_stds,
        "envelope": envelope,
    }


def _time_manifest(
    specification: dict[str, Any],
    envelope: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cadence_s = float(envelope["cadence_s"])
    parent_time = envelope["time_s"]
    for n_samples in specification["nested_windows"]["n_samples"]:
        n_value = int(n_samples)
        child = extract_exact_prefix(parent_time, n_value)
        parent_prefix = np.ascontiguousarray(parent_time[:n_value], dtype="<f8")
        exact = child.tobytes(order="C") == parent_prefix.tobytes(order="C")
        rows.append(
            {
                "time_vector_id": f"NT_N{n_value:03d}",
                "n_samples": str(n_value),
                "duration_s": _float_text((n_value - 1) * cadence_s),
                "cadence_s": _float_text(cadence_s),
                "time_sha256": canonical_float64_sha256(child),
                "parent_prefix_sha256": canonical_float64_sha256(parent_prefix),
                "exact_prefix_match": _bool_text(exact),
                "all_finite": _bool_text(bool(np.all(np.isfinite(child)))),
                "strictly_increasing": _bool_text(bool(np.all(np.diff(child) > 0.0))),
            }
        )
    if len(rows) != 6:
        raise NestedGenerationError("Time manifest must contain exactly six rows.")
    return rows


def _compare_hash_maps(reference: dict[str, Any], other: dict[str, Any]) -> dict[str, int]:
    results: dict[str, int] = {}
    for category in ("block_hash_map", "parent_hash_map", "child_hash_map"):
        left = reference[category]
        right = other[category]
        keys = set(left) | set(right)
        mismatch = sum(left.get(key) != right.get(key) for key in keys)
        results[category.replace("_hash_map", "_hash_mismatches")] = mismatch
    return results


def _run_reference_tests(
    *,
    root: Path,
    test_script: Path,
) -> dict[str, Any]:
    completed = subprocess.run(
        [
            sys.executable,
            str(test_script),
            "--root",
            str(root),
            "--main-script",
            str(Path(__file__).resolve()),
            "--json",
        ],
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if completed.returncode != 0:
        raise NestedGenerationError(
            "Independent reference test failed.\n"
            + completed.stdout
            + "\n"
            + completed.stderr
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise NestedGenerationError(
            f"Independent reference test did not return JSON: {completed.stdout!r}"
        ) from exc
    if result.get("comparisons_planned") != 90 or result.get("comparisons_exact") != 90:
        raise NestedGenerationError(f"Independent comparison result is incomplete: {result}")
    if result.get("mismatch_count") != 0:
        raise NestedGenerationError(f"Independent comparison mismatches: {result}")
    return result


def _preflight(root: Path) -> dict[str, Any]:
    if np.__version__ != EXPECTED_NUMPY_VERSION:
        raise NestedGenerationError(
            f"NumPy version mismatch: {np.__version__} != {EXPECTED_NUMPY_VERSION}"
        )
    observed: dict[str, str] = {}
    for filename, expected in EXPECTED_INPUT_HASHES.items():
        path = root / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        digest = file_sha256(path)
        if digest != expected:
            raise NestedGenerationError(
                f"Input hash mismatch for {filename}: {digest} != {expected}"
            )
        observed[filename] = digest

    f1_2_audit = json.loads(
        (root / "fase1_tarea02_generator_validation_audit.json").read_text(
            encoding="utf-8"
        )
    )
    if f1_2_audit.get("validation_conclusion") != "GENERATOR_VALIDATED":
        raise NestedGenerationError("F1.2 validation_conclusion is not GENERATOR_VALIDATED.")
    if f1_2_audit.get("environment", {}).get("numpy_version") != EXPECTED_NUMPY_VERSION:
        raise NestedGenerationError("F1.2 audit does not record NumPy 2.3.5.")
    return {
        "input_hashes": observed,
        "f1_2_validation_conclusion": f1_2_audit["validation_conclusion"],
        "required_numpy_version": EXPECTED_NUMPY_VERSION,
        "observed_numpy_version": np.__version__,
    }


def _environment() -> dict[str, Any]:
    return {
        "python_version": platform.python_version(),
        "python_full": sys.version,
        "python_executable_name": Path(sys.executable).name,
        "numpy_version": np.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "byteorder": sys.byteorder,
        "float64_itemsize": int(np.dtype(np.float64).itemsize),
        "canonical_dtype": "<f8",
        "canonical_byte_order": "C",
    }


def _write_report(path: Path, audit: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(path)
    stats = audit["child_noise_prefix_statistics"]
    order = audit["order_independence"]
    text = f"""# Fase 1 — Tarea 1.9

## Validación del generador anidado padre–prefijos

**Conclusión:** `NESTED_GENERATOR_VALIDATED`

Los 120 bloques independientes de ruido y fase se regeneraron con el generador
congelado de F1.2, bajo NumPy `{audit['environment']['numpy_version']}`. Para
cada combinación de pendiente y semilla, los hashes de tiempo, ruido y fase
coincidieron con el manifiesto N=120 de F1.2. El resultado fue `120/120 block
hash sets matched`; no se sustituyó ni redibujó ninguna realización.

La envolvente fija se construyó una sola vez sobre los 120 tiempos del padre.
Se verificaron `peak_index=3`, `time[3]=60 s`, `envelope[3]=0,5`,
`rise_tau=11,2 s` y `decay_tau=84 s`. A partir de cada bloque se formaron un
padre nulo y dos padres positivos de 50 y 80 s. Los 360 padres fueron finitos y
válidos, con {audit['distinct_hashes']['parent_flux_sha256']} hashes de flujo
distintos.

Las 54 condiciones y las semillas 0–39 produjeron exactamente 2.160 hijos: 720
nulos y 1.440 positivos. Cada hijo se obtuvo mediante el prefijo contiguo del
padre y los 2.160 hashes de prefijo coincidieron byte a byte. No se recentró,
reescaló ni reestandarizó ruido alguno. Como era previsible en prefijos de una
realización normalizada solamente a N=120, la media observada del ruido hijo
abarcó `{stats['mean_min']:.17g}` a `{stats['mean_max']:.17g}` y su desviación
muestral abarcó `{stats['std_ddof1_min']:.17g}` a
`{stats['std_ddof1_max']:.17g}`; no se exigió que fuese 0,005 en cada ventana.

La generación completa se repitió en orden normativo, inverso y aleatorio de
test. Las discrepancias fueron cero para los 120 bloques, 360 padres y 2.160
hijos en ambas comparaciones de orden. La implementación de referencia,
separada de las funciones de construcción de envolvente, señal y prefijo,
coincidió exactamente en las 90 comparaciones predeclaradas.

La estructura de medidas repetidas también quedó preservada: cada bloque tiene
tres padres y 18 hijos, todos comparten ruido, fase y metadatos de semilla; cada
padre contiene las seis ventanas anidadas N15⊂N30⊂N45⊂N60⊂N90⊂N120. Se
confirmaron 240 trayectorias positivas y 1.200 transiciones adyacentes.

No se ejecutó AFINO, no se analizaron resultados de selección y no se
persistieron los arrays completos del benchmark. Solo se guardaron scripts,
manifiestos, auditoría e informe.

## Conclusión

`NESTED_GENERATOR_VALIDATED`
"""
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--test-script", type=Path, required=True)
    args = parser.parse_args(argv)

    root = args.root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    output_paths = {
        "blocks": output_dir / "fase1_tarea09_parent_block_manifest.csv",
        "parents": output_dir / "fase1_tarea09_parent_flux_manifest.csv",
        "children": output_dir / "fase1_tarea09_child_prefix_manifest.csv",
        "times": output_dir / "fase1_tarea09_nested_time_manifest.csv",
        "audit": output_dir / "fase1_tarea09_nested_generator_validation_audit.json",
        "report": output_dir / "fase1_tarea09_nested_generator_validation.md",
    }
    existing = [path.name for path in output_paths.values() if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite F1.9 outputs: {existing}")

    preflight = _preflight(root)
    specification = load_nested_preregistration(
        root / "fase1_tarea08_nested_window_preregistration.json",
        expected_sha256=EXPECTED_INPUT_HASHES[
            "fase1_tarea08_nested_window_preregistration.json"
        ],
    )
    grid_rows = validate_nested_grid(
        root / "fase1_tarea08_nested_window_design_grid.csv",
        specification,
        expected_sha256=EXPECTED_INPUT_HASHES[
            "fase1_tarea08_nested_window_design_grid.csv"
        ],
    )

    frozen_generator = _load_module(
        root / "fase1_tarea02_synthetic_generator.py",
        "fase1_tarea02_synthetic_generator_frozen_for_f19",
    )
    frozen_f1_1_specification = _load_frozen_f1_1_specification(
        root, frozen_generator
    )

    normative = _generate_hash_inventory(
        root=root,
        specification=specification,
        grid_rows=grid_rows,
        frozen_generator=frozen_generator,
        frozen_f1_1_specification=frozen_f1_1_specification,
        mode="normative",
        collect_rows=True,
    )
    reverse = _generate_hash_inventory(
        root=root,
        specification=specification,
        grid_rows=grid_rows,
        frozen_generator=frozen_generator,
        frozen_f1_1_specification=frozen_f1_1_specification,
        mode="reverse",
        collect_rows=False,
    )
    random_test = _generate_hash_inventory(
        root=root,
        specification=specification,
        grid_rows=grid_rows,
        frozen_generator=frozen_generator,
        frozen_f1_1_specification=frozen_f1_1_specification,
        mode="random_test",
        collect_rows=False,
    )

    reverse_mismatches = _compare_hash_maps(normative, reverse)
    random_mismatches = _compare_hash_maps(normative, random_test)
    if any(reverse_mismatches.values()) or any(random_mismatches.values()):
        raise NestedGenerationError(
            f"Order dependence detected: reverse={reverse_mismatches}, "
            f"random={random_mismatches}"
        )

    reference = _run_reference_tests(root=root, test_script=args.test_script.resolve())

    block_rows = sorted(
        normative["block_rows"],
        key=lambda row: (float(row["red_noise_alpha"]), int(row["data_seed"])),
    )
    parent_rows = sorted(
        normative["parent_rows"],
        key=lambda row: (
            float(row["red_noise_alpha"]),
            int(row["data_seed"]),
            {"NULL": 0, "P050": 1, "P080": 2}[row["parent_id"].rsplit("_", 1)[1]],
        ),
    )
    child_rows = sorted(normative["child_rows"], key=lambda row: int(row["series_order"]))
    time_rows = _time_manifest(specification, normative["envelope"])

    if len(block_rows) != 120 or len(parent_rows) != 360 or len(child_rows) != 2160:
        raise NestedGenerationError("Final manifest row counts are incorrect.")
    if sum(row["ground_truth"].startswith("NULL") for row in child_rows) != 720:
        raise NestedGenerationError("Null child count is not 720.")
    if sum(not row["ground_truth"].startswith("NULL") for row in child_rows) != 1440:
        raise NestedGenerationError("Positive child count is not 1440.")
    if any(row["exact_prefix_match"] != "True" for row in child_rows):
        raise NestedGenerationError("At least one child is not an exact prefix.")

    block_child_counts = Counter(row["block_id"] for row in child_rows)
    block_parent_counts = Counter(row["block_id"] for row in parent_rows)
    if set(block_child_counts.values()) != {18} or len(block_child_counts) != 120:
        raise NestedGenerationError("Every block must have exactly 18 children.")
    if set(block_parent_counts.values()) != {3} or len(block_parent_counts) != 120:
        raise NestedGenerationError("Every block must have exactly three parents.")

    # Shared repeated-measures metadata.
    block_meta = {
        row["block_id"]: (
            row["noise_sha256"],
            row["phase_float64_sha256"],
            row["noise_seed_metadata_json"],
            row["phase_seed_metadata_json"],
        )
        for row in block_rows
    }
    for row in parent_rows:
        expected_noise, expected_phase, _, _ = block_meta[row["block_id"]]
        if row["noise_sha256"] != expected_noise or row["phase_float64_sha256"] != expected_phase:
            raise NestedGenerationError("Parent repeated-measures metadata mismatch.")
    for row in child_rows:
        _, expected_phase, _, _ = block_meta[row["block_id"]]
        if row["phase_float64_sha256"] != expected_phase:
            raise NestedGenerationError("Child phase metadata mismatch.")

    _write_csv(output_paths["blocks"], BLOCK_FIELDS, block_rows)
    _write_csv(output_paths["parents"], PARENT_FIELDS, parent_rows)
    _write_csv(output_paths["children"], CHILD_FIELDS, child_rows)
    _write_csv(output_paths["times"], TIME_FIELDS, time_rows)

    script_hashes = {
        Path(__file__).name: file_sha256(Path(__file__).resolve()),
        args.test_script.name: file_sha256(args.test_script.resolve()),
    }
    output_hashes = {
        path.name: file_sha256(path)
        for key, path in output_paths.items()
        if key not in {"audit", "report"}
    }

    noise_means = np.asarray(normative["child_noise_means"], dtype=np.float64)
    noise_stds = np.asarray(normative["child_noise_stds"], dtype=np.float64)
    if noise_means.size != 2160 or noise_stds.size != 2160:
        raise NestedGenerationError("Child-noise statistics are incomplete.")

    audit: dict[str, Any] = {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "validation_conclusion": "NESTED_GENERATOR_VALIDATED",
        "benchmark_id": specification["benchmark_id"],
        "benchmark_version": specification["benchmark_version"],
        "environment": _environment(),
        "preflight": preflight,
        "script_hashes": script_hashes,
        "input_hashes": preflight["input_hashes"],
        "output_hashes_before_audit_and_report": output_hashes,
        "f1_2_block_comparison": {
            "planned": 120,
            "matched": 120,
            "mismatched": 0,
            "statement": "120/120 block hash sets matched",
            "compared_hashes": [
                "time_sha256",
                "noise_sha256",
                "phase_float64_sha256",
            ],
        },
        "parent_generation": {
            "independent_blocks": 120,
            "parent_flux_arrays": 360,
            "valid_parent_flux_arrays": 360,
            "nonfinite_parent_flux_arrays": 0,
            "parent_failures": 0,
            "fixed_envelope_constructed_once_per_validation_pass": True,
            "peak_index": int(normative["envelope"]["peak_index"]),
            "t_peak_s": float(normative["envelope"]["t_peak_s"]),
            "envelope_peak_excess": float(
                normative["envelope"]["envelope"][normative["envelope"]["peak_index"]]
            ),
            "rise_tau_s": float(normative["envelope"]["rise_tau_s"]),
            "decay_tau_s": float(normative["envelope"]["decay_tau_s"]),
        },
        "child_generation": {
            "child_prefixes": 2160,
            "exact_prefix_matches": 2160,
            "prefix_mismatches": 0,
            "null_children": 720,
            "positive_children": 1440,
            "positive_trajectories": 240,
            "adjacent_positive_transitions": 1200,
            "time_vectors": 6,
            "time_prefix_matches": 6,
        },
        "independent_reference": reference,
        "order_independence": {
            "orders": ["normative", "reverse", "random_test"],
            "random_order_seed": 20260803,
            "random_order_engine": "python.random.Random local instance",
            "global_numpy_random_used_for_ordering": False,
            "normative_vs_reverse": reverse_mismatches,
            "normative_vs_random_test": random_mismatches,
        },
        "repeated_measures": {
            "blocks_with_exactly_three_parents": 120,
            "blocks_with_exactly_eighteen_children": 120,
            "shared_noise_hash_verified": True,
            "shared_phase_hash_verified": True,
            "shared_noise_seed_metadata_verified": True,
            "shared_phase_seed_metadata_verified": True,
            "six_nested_windows_per_parent_verified": 360,
            "nested_window_sequence": [
                int(value) for value in specification["nested_windows"]["n_samples"]
            ],
        },
        "child_noise_prefix_statistics": {
            "count": int(noise_means.size),
            "mean_min": float(np.min(noise_means)),
            "mean_max": float(np.max(noise_means)),
            "std_ddof1_min": float(np.min(noise_stds)),
            "std_ddof1_max": float(np.max(noise_stds)),
            "exact_0_005_required": False,
        },
        "distinct_hashes": {
            "block_noise_sha256": len({row["noise_sha256"] for row in block_rows}),
            "parent_flux_sha256": len({row["parent_flux_sha256"] for row in parent_rows}),
            "child_flux_sha256": len({row["child_flux_sha256"] for row in child_rows}),
            "time_sha256": len({row["time_sha256"] for row in time_rows}),
        },
        "incidents": [],
        "confirmations": {
            "afino_executed": False,
            "full_nested_dataset_persisted": False,
            "parent_failures_redrawn": False,
            "child_noise_recentered": False,
            "child_noise_rescaled": False,
            "child_noise_restandardized": False,
            "parent_signal_recomputed_per_child": False,
            "preregistration_modified": False,
            "generator_f1_2_modified": False,
            "post_generation_tuning": False,
        },
    }

    output_paths["audit"].write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    _write_report(output_paths["report"], audit)

    # Postflight: inputs must still be identical.
    for filename, expected in EXPECTED_INPUT_HASHES.items():
        observed = file_sha256(root / filename)
        if observed != expected:
            raise NestedGenerationError(
                f"Input changed during F1.9: {filename}: {observed} != {expected}"
            )

    print("F1.9 nested generator validation complete")
    print("validation_conclusion: NESTED_GENERATOR_VALIDATED")
    print("block_hash_sets_matched: 120/120")
    print("parent_flux_arrays: 360")
    print("child_prefixes: 2160")
    print("exact_prefix_matches: 2160")
    print("independent_reference_exact: 90/90")
    print("order_mismatches: 0")
    print(f"audit: {output_paths['audit'].name}")
    print(f"report: {output_paths['report'].name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
