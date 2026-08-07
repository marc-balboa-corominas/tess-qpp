from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import importlib.util
import json
import math
import os
import platform
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
    "fase1_tarea09_nested_generator.py":
        "9c708af7fd9c6a07eb9b52aa91c8ff34d0aef7e534b485ffb793d6e0713124f2",
    "fase1_tarea09_parent_block_manifest.csv":
        "20f0b1aa1ebfe1747aa44962002a03d41f9eb16ee89956bacc1ad0b48fb18d19",
    "fase1_tarea09_parent_flux_manifest.csv":
        "2dccc2db6c82ea356f849cf5c4bcbdc06015bc6930203d8a3edc5585b8ed3488",
    "fase1_tarea09_child_prefix_manifest.csv":
        "39a4a85413b879e6dd614f4a930d82437b109aacd997d543cd455e05dc252969",
    "fase1_tarea09_nested_time_manifest.csv":
        "93c213d1ad186b14d7c7619eb1dc8f2c8bf564d0124350f226644abcc7cfbcb7",
    "fase1_tarea09_nested_generator_validation_audit.json":
        "38f5579c3f1ad2732a4523cbdb42ebb1ba509391585114898985c6b09c125a6d",
    "fase1_tarea02_synthetic_generator.py":
        "743005e580f20be331408d9165522932a289d256cef0efbe4c4f24fcb38c54bd",
    "fase1_tarea02_noise_block_manifest.csv":
        "898a47f697b3de765f2b73b4bc01181f031c485df5875b0a88e6216591e7883d",
    "fase1_tarea02_generator_validation_audit.json":
        "3e4d588110dbe535038dc0e85ec08a60e47de946d438c05b121b379ee0c02f11",
    "fase1_tarea01_core_benchmark_preregistration.json":
        "dd80346172290e014d73f78240b3e31f135bcc7e4f075963e7e20d8456de3401",
}

SERIES_FIELDS = [
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
    "time_vector_id",
    "flux_start_offset",
    "flux_end_offset",
    "flux_sha256",
    "time_sha256",
    "noise_prefix_sha256",
    "phase_float64_sha256",
    "parent_flux_sha256",
    "parent_n120_series_id",
    "parent_n120_flux_start_offset",
    "parent_n120_flux_end_offset",
    "exact_parent_prefix_match",
    "all_finite",
    "flux_mean",
    "flux_std_ddof1",
    "noise_mean",
    "noise_std_ddof1",
    "materialization_status",
    "error",
]

TIME_FIELDS = [
    "time_vector_id",
    "n_samples",
    "duration_s",
    "cadence_s",
    "start_offset",
    "end_offset",
    "time_sha256",
    "all_finite",
    "strictly_increasing",
    "exact_f1_9_hash_match",
]


class MaterializationError(RuntimeError):
    """Raised when a frozen input or materialization invariant fails."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_float64_sha256(array: Any) -> str:
    canonical = np.ascontiguousarray(array, dtype="<f8")
    return hashlib.sha256(canonical.tobytes(order="C")).hexdigest()


def canonical_int64_sha256(array: Any) -> str:
    canonical = np.ascontiguousarray(array, dtype="<i8")
    return hashlib.sha256(canonical.tobytes(order="C")).hexdigest()


def float_text(value: float) -> str:
    return format(float(value), ".17g")


def bool_text(value: bool) -> str:
    return "True" if value else "False"


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    return fields, rows


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    if path.exists():
        raise FileExistsError(path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise MaterializationError(f"Cannot import module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def preflight(root: Path) -> dict[str, Any]:
    if np.__version__ != EXPECTED_NUMPY_VERSION:
        raise MaterializationError(
            f"NumPy {np.__version__} != required {EXPECTED_NUMPY_VERSION}"
        )

    observed: dict[str, str] = {}
    for filename, expected in EXPECTED_INPUT_HASHES.items():
        path = root / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        digest = file_sha256(path)
        if digest != expected:
            raise MaterializationError(
                f"Hash mismatch for {filename}: {digest} != {expected}"
            )
        observed[filename] = digest

    f1_9_audit = json.loads(
        (root / "fase1_tarea09_nested_generator_validation_audit.json").read_text(
            encoding="utf-8"
        )
    )
    if f1_9_audit.get("validation_conclusion") != "NESTED_GENERATOR_VALIDATED":
        raise MaterializationError("F1.9 is not NESTED_GENERATOR_VALIDATED.")
    if f1_9_audit.get("environment", {}).get("numpy_version") != EXPECTED_NUMPY_VERSION:
        raise MaterializationError("F1.9 was not validated with NumPy 2.3.5.")

    f1_2_audit = json.loads(
        (root / "fase1_tarea02_generator_validation_audit.json").read_text(
            encoding="utf-8"
        )
    )
    if f1_2_audit.get("validation_conclusion") != "GENERATOR_VALIDATED":
        raise MaterializationError("F1.2 generator is not validated.")

    return {
        "input_hashes": observed,
        "f1_9_validation_conclusion": f1_9_audit["validation_conclusion"],
        "f1_2_validation_conclusion": f1_2_audit["validation_conclusion"],
        "numpy_version_required": EXPECTED_NUMPY_VERSION,
        "numpy_version_observed": np.__version__,
    }


def validate_f1_9_manifests(root: Path) -> dict[str, Any]:
    _, block_rows = load_csv(root / "fase1_tarea09_parent_block_manifest.csv")
    _, parent_rows = load_csv(root / "fase1_tarea09_parent_flux_manifest.csv")
    _, child_rows = load_csv(root / "fase1_tarea09_child_prefix_manifest.csv")
    _, time_rows = load_csv(root / "fase1_tarea09_nested_time_manifest.csv")

    if len(block_rows) != 120:
        raise MaterializationError(f"F1.9 block rows: {len(block_rows)} != 120")
    if len(parent_rows) != 360:
        raise MaterializationError(f"F1.9 parent rows: {len(parent_rows)} != 360")
    if len(child_rows) != 2160:
        raise MaterializationError(f"F1.9 child rows: {len(child_rows)} != 2160")
    if len(time_rows) != 6:
        raise MaterializationError(f"F1.9 time rows: {len(time_rows)} != 6")

    orders = [int(row["series_order"]) for row in child_rows]
    ids = [row["series_id"] for row in child_rows]
    if orders != list(range(1, 2161)):
        raise MaterializationError("F1.9 child rows are not in normative series order.")
    if ids != [f"NWS{value:06d}" for value in range(1, 2161)]:
        raise MaterializationError("F1.9 child identifiers are not normative.")
    if len(set(ids)) != 2160:
        raise MaterializationError("F1.9 child identifiers are not unique.")
    if child_rows[0]["series_id"] != "NWS000001":
        raise MaterializationError("Unexpected first F1.9 series.")
    if child_rows[-1]["series_id"] != "NWS002160":
        raise MaterializationError("Unexpected final F1.9 series.")

    expected_time_ids = [
        "NT_N015", "NT_N030", "NT_N045",
        "NT_N060", "NT_N090", "NT_N120",
    ]
    if [row["time_vector_id"] for row in time_rows] != expected_time_ids:
        raise MaterializationError("F1.9 time-vector ordering is not normative.")

    if len({row["block_id"] for row in block_rows}) != 120:
        raise MaterializationError("F1.9 block IDs are not unique.")
    if len({row["parent_id"] for row in parent_rows}) != 360:
        raise MaterializationError("F1.9 parent IDs are not unique.")

    return {
        "block_rows": block_rows,
        "parent_rows": parent_rows,
        "child_rows": child_rows,
        "time_rows": time_rows,
        "block_lookup": {row["block_id"]: row for row in block_rows},
        "parent_lookup": {row["parent_id"]: row for row in parent_rows},
        "time_lookup": {row["time_vector_id"]: row for row in time_rows},
    }


def regenerate_and_validate(
    root: Path,
    nested: Any,
    specification: dict[str, Any],
    grid_rows: list[dict[str, str]],
    manifests: dict[str, Any],
) -> dict[str, Any]:
    frozen_generator = load_module(
        root / "fase1_tarea02_synthetic_generator.py",
        "fase1_tarea02_synthetic_generator_for_f110",
    )
    frozen_f1_1 = frozen_generator.load_preregistration(
        root / "fase1_tarea01_core_benchmark_preregistration.json",
        expected_sha256=EXPECTED_INPUT_HASHES[
            "fase1_tarea01_core_benchmark_preregistration.json"
        ],
    )

    envelope = nested.build_fixed_parent_envelope(specification)
    parent_time = np.ascontiguousarray(envelope["time_s"], dtype="<f8")
    if parent_time.shape != (120,):
        raise MaterializationError("Unexpected parent time shape.")

    f1_2_fields, f1_2_rows = load_csv(root / "fase1_tarea02_noise_block_manifest.csv")
    del f1_2_fields
    f1_2_lookup = {
        (float(row["red_noise_alpha"]), int(row["data_seed"])): row
        for row in f1_2_rows
        if int(row["n_samples"]) == 120
    }
    if len(f1_2_lookup) != 120:
        raise MaterializationError("F1.2 N=120 lookup is incomplete.")

    block_objects: dict[tuple[float, int], dict[str, Any]] = {}
    block_by_id: dict[str, dict[str, Any]] = {}
    block_match_count = 0
    alphas = [float(value) for value in specification["parent_noise_and_phase"]["red_noise_alpha"]]
    seed_start = int(specification["parent_noise_and_phase"]["data_seed_start"])
    seed_end = int(specification["parent_noise_and_phase"]["data_seed_end"])

    for alpha in alphas:
        for data_seed in range(seed_start, seed_end + 1):
            block = nested.generate_parent_block(
                alpha,
                data_seed,
                specification,
                frozen_generator=frozen_generator,
                frozen_f1_1_specification=frozen_f1_1,
            )
            block_id = nested._block_id(block["alpha_code"], data_seed)
            observed = {
                "time_sha256": canonical_float64_sha256(parent_time),
                "noise_sha256": canonical_float64_sha256(block["noise"]),
                "phase_float64_sha256": canonical_float64_sha256(block["phase_rad"]),
            }
            f1_9_row = manifests["block_lookup"].get(block_id)
            f1_2_row = f1_2_lookup.get((alpha, data_seed))
            if f1_9_row is None or f1_2_row is None:
                raise MaterializationError(f"Missing block metadata for {block_id}.")
            for field, digest in observed.items():
                if digest != f1_9_row[field] or digest != f1_2_row[field]:
                    raise MaterializationError(
                        f"Block hash mismatch for {block_id}, {field}."
                    )
            if not np.all(np.isfinite(block["noise"])):
                raise MaterializationError(f"Non-finite block noise: {block_id}")
            block_objects[(alpha, data_seed)] = block
            block_by_id[block_id] = block
            block_match_count += 1

    if block_match_count != 120:
        raise MaterializationError("120/120 blocks were not validated.")

    parent_objects: dict[str, np.ndarray] = {}
    parent_match_count = 0
    for alpha in alphas:
        for data_seed in range(seed_start, seed_end + 1):
            block = block_objects[(alpha, data_seed)]
            constructed = nested.build_parent_fluxes(block, envelope, specification)
            for type_code, item in constructed.items():
                parent_id = nested._parent_id(block["alpha_code"], data_seed, type_code)
                flux = np.ascontiguousarray(item["flux"], dtype="<f8")
                if flux.shape != (120,) or not np.all(np.isfinite(flux)):
                    raise MaterializationError(f"Invalid parent flux: {parent_id}")
                expected = manifests["parent_lookup"].get(parent_id)
                if expected is None:
                    raise MaterializationError(f"Missing F1.9 parent row: {parent_id}")
                digest = canonical_float64_sha256(flux)
                if digest != expected["parent_flux_sha256"]:
                    raise MaterializationError(f"Parent hash mismatch: {parent_id}")
                parent_objects[parent_id] = flux
                parent_match_count += 1

    if parent_match_count != 360 or len(parent_objects) != 360:
        raise MaterializationError("360/360 parents were not validated.")

    time_vectors: dict[int, np.ndarray] = {}
    time_match_count = 0
    for n_raw in specification["nested_windows"]["n_samples"]:
        n_samples = int(n_raw)
        vector = nested.extract_exact_prefix(parent_time, n_samples)
        vector_id = f"NT_N{n_samples:03d}"
        expected = manifests["time_lookup"].get(vector_id)
        if expected is None:
            raise MaterializationError(f"Missing F1.9 time row: {vector_id}")
        digest = canonical_float64_sha256(vector)
        if digest != expected["time_sha256"]:
            raise MaterializationError(f"Time hash mismatch: {vector_id}")
        time_vectors[n_samples] = vector
        time_match_count += 1
    if time_match_count != 6:
        raise MaterializationError("6/6 time vectors were not validated.")

    child_arrays: list[np.ndarray] = []
    noise_arrays: list[np.ndarray] = []
    child_match_count = 0
    for row in manifests["child_rows"]:
        n_samples = int(row["n_samples"])
        parent_id = row["parent_id"]
        block_id = row["block_id"]
        parent = parent_objects[parent_id]
        block = block_by_id[block_id]
        child = nested.extract_exact_prefix(parent, n_samples)
        noise = nested.extract_exact_prefix(block["noise"], n_samples)
        if canonical_float64_sha256(child) != row["child_flux_sha256"]:
            raise MaterializationError(f"Child hash mismatch: {row['series_id']}")
        if canonical_float64_sha256(parent) != row["parent_flux_sha256"]:
            raise MaterializationError(f"Parent-link hash mismatch: {row['series_id']}")
        if canonical_float64_sha256(noise) != row["noise_prefix_sha256"]:
            raise MaterializationError(f"Noise-prefix hash mismatch: {row['series_id']}")
        if canonical_float64_sha256(time_vectors[n_samples]) != row["time_sha256"]:
            raise MaterializationError(f"Time-link hash mismatch: {row['series_id']}")
        if child.tobytes(order="C") != parent[:n_samples].astype("<f8", copy=False).tobytes(order="C"):
            raise MaterializationError(f"Child is not exact parent prefix: {row['series_id']}")
        if not np.all(np.isfinite(child)):
            raise MaterializationError(f"Non-finite child: {row['series_id']}")
        child_arrays.append(child)
        noise_arrays.append(noise)
        child_match_count += 1

    if child_match_count != 2160:
        raise MaterializationError("2160/2160 children were not validated.")

    # The grid and F1.9 manifest must define the same series population.
    grid_series = sum(int(row["planned_series_count"]) for row in grid_rows)
    if grid_series != 2160:
        raise MaterializationError(f"Grid series count: {grid_series} != 2160")

    return {
        "envelope": envelope,
        "parent_time": parent_time,
        "block_objects": block_objects,
        "block_by_id": block_by_id,
        "parent_objects": parent_objects,
        "time_vectors": time_vectors,
        "child_arrays": child_arrays,
        "noise_arrays": noise_arrays,
        "prewrite_comparisons": {
            "f1_2_and_f1_9_blocks_matched": block_match_count,
            "f1_9_parents_matched": parent_match_count,
            "f1_9_children_matched": child_match_count,
            "f1_9_time_vectors_matched": time_match_count,
        },
    }


def save_npy_exact(path: Path, array: np.ndarray) -> None:
    if path.exists():
        raise FileExistsError(path)
    with path.open("wb") as handle:
        np.save(handle, array, allow_pickle=False)


def environment_info() -> dict[str, Any]:
    return {
        "python_version": platform.python_version(),
        "python_full": sys.version,
        "python_executable": sys.executable,
        "numpy_version": np.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "byteorder": sys.byteorder,
    }


def write_report(path: Path, audit: dict[str, Any]) -> None:
    logical = audit["logical_hashes"]
    counts = audit["counts"]
    roundtrip = audit["round_trip"]
    nested = audit["persisted_nested_invariants"]
    text = f"""# Fase 1 — Tarea 1.10

## Materialización y congelación del dataset anidado

**Estado:** `{audit['materialization_status']}`

Se materializaron exactamente **{counts['series_count']:,} series** en el orden
normativo `NWS000001`–`NWS002160`, sin reordenarlas después de construir el
payload. Las {counts['null_series_count']:,} series nulas y las
{counts['positive_series_count']:,} positivas ocupan en conjunto
{counts['total_flux_values']:,} valores `float64`. Antes de escribirlos se
regeneraron mediante el generador congelado de F1.9 y coincidieron
{audit['prewrite_comparisons']['f1_2_and_f1_9_blocks_matched']}/120 bloques,
{audit['prewrite_comparisons']['f1_9_parents_matched']}/360 padres,
{audit['prewrite_comparisons']['f1_9_children_matched']}/2160 hijos y
{audit['prewrite_comparisons']['f1_9_time_vectors_matched']}/6 tiempos.

Los cuatro arrays se escribieron sin pickle y se cerraron antes de recargarlos
con `np.load(..., allow_pickle=False)`. El ciclo completo de escritura y lectura
reprodujo exactamente {roundtrip['child_series_exact']}/2160 hashes de flujo y
{roundtrip['time_vectors_exact']}/6 hashes temporales. Los offsets comienzan en
cero, terminan en 129.600 y conservan la longitud declarada de cada serie. Los
seis tiempos persistidos suman 360 valores y permanecerán en segundos; el
futuro runner deberá leerlos directamente y no reconstruirlos.

Los padres no se duplicaron en un payload separado. Cada uno de los 360 padres
está representado por una única serie `N=120`. Usando exclusivamente los arrays
releídos, las {nested['parent_child_exact']:,}/2160 comparaciones padre–hijo
fueron byte a byte exactas. También se conservaron las
{nested['adjacent_prefix_exact']:,}/1800 relaciones adyacentes: 600 nulas y
1.200 positivas. Por tanto, la estructura de medidas repetidas sobrevivió la
serialización.

Los hashes lógicos congelados son:

```text
canonical_flux_payload_sha256:
{logical['canonical_flux_payload_sha256']}

series_offsets_canonical_sha256:
{logical['series_offsets_canonical_sha256']}

time_values_canonical_sha256:
{logical['time_values_canonical_sha256']}

time_offsets_canonical_sha256:
{logical['time_offsets_canonical_sha256']}

ordered_series_manifest_sha256:
{logical['ordered_series_manifest_sha256']}
```

No se ejecutó ni interpretó AFINO; no se calcularon BIC, periodos ajustados ni
decisiones. No se eliminaron series, no se redibujaron padres y no se normalizó
ningún hijo. Los momentos variables del ruido de los prefijos continúan siendo una
propiedad intencionada del diseño, mientras que la unidad independiente permanece
el bloque `(alpha, data_seed)`. La unicidad de los 2.160 hashes de flujo se registra
como control de contenido y no se interpreta como independencia científica.

El manifiesto enlaza cada serie con su condición, bloque, padre `N=120`, vector
temporal, offsets y hashes canónicos. De este modo, cualquier futura ejecución
puede verificar los inputs antes de ajustar modelos y detenerse ante una sola
discrepancia. El dataset queda congelado antes de AFINO y preparado para construir
un plan y un runner que consuman exclusivamente estos arrays persistidos.

## Conclusión

`{audit['materialization_status']}`
"""
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    root = args.root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    output_names = {
        "flux": "fase1_tarea10_nested_flux_values.npy",
        "series_offsets": "fase1_tarea10_nested_series_offsets.npy",
        "time_values": "fase1_tarea10_nested_time_values.npy",
        "time_offsets": "fase1_tarea10_nested_time_offsets.npy",
        "series_manifest": "fase1_tarea10_nested_series_manifest.csv",
        "time_manifest": "fase1_tarea10_nested_time_manifest.csv",
        "audit": "fase1_tarea10_nested_materialization_audit.json",
        "report": "fase1_tarea10_nested_materialization_report.md",
    }
    final_paths = {key: output_dir / name for key, name in output_names.items()}
    for path in final_paths.values():
        if path.exists():
            raise FileExistsError(path)

    preflight_result = preflight(root)
    manifests = validate_f1_9_manifests(root)
    nested = load_module(
        root / "fase1_tarea09_nested_generator.py",
        "fase1_tarea09_nested_generator_for_f110",
    )
    specification = nested.load_nested_preregistration(
        root / "fase1_tarea08_nested_window_preregistration.json",
        expected_sha256=EXPECTED_INPUT_HASHES[
            "fase1_tarea08_nested_window_preregistration.json"
        ],
    )
    grid_rows = nested.validate_nested_grid(
        root / "fase1_tarea08_nested_window_design_grid.csv",
        specification,
        expected_sha256=EXPECTED_INPUT_HASHES[
            "fase1_tarea08_nested_window_design_grid.csv"
        ],
    )

    regenerated = regenerate_and_validate(
        root,
        nested,
        specification,
        grid_rows,
        manifests,
    )

    child_arrays = regenerated["child_arrays"]
    noise_arrays = regenerated["noise_arrays"]
    child_rows = manifests["child_rows"]
    time_vectors = regenerated["time_vectors"]

    lengths = np.asarray([int(row["n_samples"]) for row in child_rows], dtype="<i8")
    series_offsets = np.empty(2161, dtype="<i8")
    series_offsets[0] = 0
    np.cumsum(lengths, dtype=np.int64, out=series_offsets[1:])
    flux_values = np.ascontiguousarray(np.concatenate(child_arrays), dtype="<f8")

    n_values = [int(value) for value in specification["nested_windows"]["n_samples"]]
    time_lengths = np.asarray(n_values, dtype="<i8")
    time_offsets = np.empty(7, dtype="<i8")
    time_offsets[0] = 0
    np.cumsum(time_lengths, dtype=np.int64, out=time_offsets[1:])
    time_values = np.ascontiguousarray(
        np.concatenate([time_vectors[n] for n in n_values]), dtype="<f8"
    )

    if flux_values.dtype != np.dtype("<f8") or flux_values.ndim != 1:
        raise MaterializationError("Flux payload dtype or dimension is invalid.")
    if flux_values.size != 129600:
        raise MaterializationError(f"Flux payload length: {flux_values.size} != 129600")
    if series_offsets.dtype != np.dtype("<i8") or series_offsets.size != 2161:
        raise MaterializationError("Series offsets dtype or length is invalid.")
    if int(series_offsets[0]) != 0 or int(series_offsets[-1]) != 129600:
        raise MaterializationError("Series offsets endpoints are invalid.")
    if not np.array_equal(np.diff(series_offsets), lengths):
        raise MaterializationError("Series offset increments do not match n_samples.")
    if time_values.dtype != np.dtype("<f8") or time_values.size != 360:
        raise MaterializationError("Time payload dtype or length is invalid.")
    if time_offsets.dtype != np.dtype("<i8") or time_offsets.size != 7:
        raise MaterializationError("Time offsets dtype or length is invalid.")
    if int(time_offsets[0]) != 0 or int(time_offsets[-1]) != 360:
        raise MaterializationError("Time offsets endpoints are invalid.")
    if not np.array_equal(np.diff(time_offsets), time_lengths):
        raise MaterializationError("Time offset increments are invalid.")

    # One N=120 series must represent each parent exactly once.
    parent_n120_rows: dict[str, dict[str, str]] = {}
    for row in child_rows:
        if int(row["n_samples"]) == 120:
            parent_id = row["parent_id"]
            if parent_id in parent_n120_rows:
                raise MaterializationError(f"Duplicate N=120 series for {parent_id}")
            if row["child_flux_sha256"] != row["parent_flux_sha256"]:
                raise MaterializationError(f"N=120 child hash differs from parent: {parent_id}")
            parent_n120_rows[parent_id] = row
    if len(parent_n120_rows) != 360:
        raise MaterializationError("There is not exactly one N=120 series per parent.")

    parent_count = len({row["parent_id"] for row in child_rows})
    if parent_count != 360:
        raise MaterializationError(f"Parent count: {parent_count} != 360")

    # Write temporary NumPy files only after every pre-write comparison succeeds.
    temp_paths = {
        key: output_dir / (name + ".partial")
        for key, name in output_names.items()
        if key in {"flux", "series_offsets", "time_values", "time_offsets"}
    }
    for path in temp_paths.values():
        if path.exists():
            raise FileExistsError(path)

    save_npy_exact(temp_paths["flux"], flux_values)
    save_npy_exact(temp_paths["series_offsets"], series_offsets)
    save_npy_exact(temp_paths["time_values"], time_values)
    save_npy_exact(temp_paths["time_offsets"], time_offsets)

    # Drop generation payload references before mandatory reload.
    del flux_values, series_offsets, time_values, time_offsets, child_arrays
    gc.collect()

    loaded_flux = np.load(temp_paths["flux"], allow_pickle=False)
    loaded_offsets = np.load(temp_paths["series_offsets"], allow_pickle=False)
    loaded_time = np.load(temp_paths["time_values"], allow_pickle=False)
    loaded_time_offsets = np.load(temp_paths["time_offsets"], allow_pickle=False)

    if loaded_flux.dtype != np.dtype("<f8") or loaded_flux.shape != (129600,):
        raise MaterializationError("Reloaded flux payload is invalid.")
    if loaded_offsets.dtype != np.dtype("<i8") or loaded_offsets.shape != (2161,):
        raise MaterializationError("Reloaded series offsets are invalid.")
    if loaded_time.dtype != np.dtype("<f8") or loaded_time.shape != (360,):
        raise MaterializationError("Reloaded time payload is invalid.")
    if loaded_time_offsets.dtype != np.dtype("<i8") or loaded_time_offsets.shape != (7,):
        raise MaterializationError("Reloaded time offsets are invalid.")

    persisted_series: dict[str, np.ndarray] = {}
    roundtrip_child_exact = 0
    for index, row in enumerate(child_rows):
        start = int(loaded_offsets[index])
        end = int(loaded_offsets[index + 1])
        series = np.ascontiguousarray(loaded_flux[start:end], dtype="<f8")
        if end - start != int(row["n_samples"]):
            raise MaterializationError(f"Reloaded length mismatch: {row['series_id']}")
        digest = canonical_float64_sha256(series)
        if digest != row["child_flux_sha256"]:
            raise MaterializationError(f"Round-trip child mismatch: {row['series_id']}")
        persisted_series[row["series_id"]] = series
        roundtrip_child_exact += 1
    if roundtrip_child_exact != 2160:
        raise MaterializationError("2160/2160 child round trips were not exact.")

    persisted_times: dict[int, np.ndarray] = {}
    roundtrip_time_exact = 0
    for index, n_samples in enumerate(n_values):
        start = int(loaded_time_offsets[index])
        end = int(loaded_time_offsets[index + 1])
        vector = np.ascontiguousarray(loaded_time[start:end], dtype="<f8")
        row = manifests["time_lookup"][f"NT_N{n_samples:03d}"]
        if canonical_float64_sha256(vector) != row["time_sha256"]:
            raise MaterializationError(f"Round-trip time mismatch: N={n_samples}")
        persisted_times[n_samples] = vector
        roundtrip_time_exact += 1
    if roundtrip_time_exact != 6:
        raise MaterializationError("6/6 time-vector round trips were not exact.")

    # Use only the reloaded arrays for all nested-invariant checks.
    parent_n120_by_parent: dict[str, tuple[dict[str, str], np.ndarray]] = {}
    for parent_id, row in parent_n120_rows.items():
        parent_series = persisted_series[row["series_id"]]
        if canonical_float64_sha256(parent_series) != row["parent_flux_sha256"]:
            raise MaterializationError(f"Persisted N=120 parent mismatch: {parent_id}")
        parent_n120_by_parent[parent_id] = (row, parent_series)

    parent_child_exact = 0
    for row in child_rows:
        child = persisted_series[row["series_id"]]
        parent = parent_n120_by_parent[row["parent_id"]][1]
        n_samples = int(row["n_samples"])
        if child.tobytes(order="C") != parent[:n_samples].tobytes(order="C"):
            raise MaterializationError(f"Persisted parent-prefix mismatch: {row['series_id']}")
        parent_child_exact += 1
    if parent_child_exact != 2160:
        raise MaterializationError("2160/2160 parent-prefix checks were not exact.")

    rows_by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in child_rows:
        rows_by_parent[row["parent_id"]].append(row)
    if len(rows_by_parent) != 360:
        raise MaterializationError("Persisted parent grouping is incomplete.")

    adjacent_exact = 0
    adjacent_positive = 0
    adjacent_null = 0
    for parent_id, rows in rows_by_parent.items():
        ordered = sorted(rows, key=lambda item: int(item["n_samples"]))
        if [int(row["n_samples"]) for row in ordered] != n_values:
            raise MaterializationError(f"Incomplete nested sequence: {parent_id}")
        for left, right in zip(ordered[:-1], ordered[1:], strict=True):
            left_series = persisted_series[left["series_id"]]
            right_series = persisted_series[right["series_id"]]
            if left_series.tobytes(order="C") != right_series[: left_series.size].tobytes(order="C"):
                raise MaterializationError(
                    f"Adjacent persisted prefix mismatch: {left['series_id']} -> {right['series_id']}"
                )
            adjacent_exact += 1
            if left["ground_truth"] == "NULL_FLARE_RED_NOISE":
                adjacent_null += 1
            else:
                adjacent_positive += 1
    if (adjacent_exact, adjacent_null, adjacent_positive) != (1800, 600, 1200):
        raise MaterializationError(
            f"Adjacent counts are invalid: {(adjacent_exact, adjacent_null, adjacent_positive)}"
        )

    # Create manifests from the persisted arrays.
    n120_offsets: dict[str, tuple[int, int, str]] = {}
    for parent_id, row in parent_n120_rows.items():
        index = int(row["series_order"]) - 1
        n120_offsets[parent_id] = (
            int(loaded_offsets[index]),
            int(loaded_offsets[index + 1]),
            row["series_id"],
        )

    series_manifest_rows: list[dict[str, Any]] = []
    for index, row in enumerate(child_rows):
        start = int(loaded_offsets[index])
        end = int(loaded_offsets[index + 1])
        series = persisted_series[row["series_id"]]
        parent_start, parent_end, parent_series_id = n120_offsets[row["parent_id"]]
        parent = parent_n120_by_parent[row["parent_id"]][1]
        n_samples = int(row["n_samples"])
        exact = series.tobytes(order="C") == parent[:n_samples].tobytes(order="C")
        if not exact:
            raise MaterializationError("Manifest parent-prefix assertion failed.")
        series_manifest_rows.append(
            {
                "series_id": row["series_id"],
                "series_order": row["series_order"],
                "condition_id": row["condition_id"],
                "parent_id": row["parent_id"],
                "block_id": row["block_id"],
                "ground_truth": row["ground_truth"],
                "n_samples": row["n_samples"],
                "duration_s": row["duration_s"],
                "red_noise_alpha": row["red_noise_alpha"],
                "period_s": row["period_s"],
                "qpp_fraction": row["qpp_fraction"],
                "data_seed": row["data_seed"],
                "time_vector_id": f"NT_N{n_samples:03d}",
                "flux_start_offset": str(start),
                "flux_end_offset": str(end),
                "flux_sha256": canonical_float64_sha256(series),
                "time_sha256": canonical_float64_sha256(persisted_times[n_samples]),
                "noise_prefix_sha256": row["noise_prefix_sha256"],
                "phase_float64_sha256": row["phase_float64_sha256"],
                "parent_flux_sha256": row["parent_flux_sha256"],
                "parent_n120_series_id": parent_series_id,
                "parent_n120_flux_start_offset": str(parent_start),
                "parent_n120_flux_end_offset": str(parent_end),
                "exact_parent_prefix_match": bool_text(exact),
                "all_finite": bool_text(bool(np.all(np.isfinite(series)))),
                "flux_mean": float_text(np.mean(series)),
                "flux_std_ddof1": float_text(np.std(series, ddof=1)),
                "noise_mean": float_text(np.mean(noise_arrays[index])),
                "noise_std_ddof1": float_text(np.std(noise_arrays[index], ddof=1)),
                "materialization_status": "OK",
                "error": "",
            }
        )

    time_manifest_rows: list[dict[str, Any]] = []
    for index, n_samples in enumerate(n_values):
        start = int(loaded_time_offsets[index])
        end = int(loaded_time_offsets[index + 1])
        vector = persisted_times[n_samples]
        expected = manifests["time_lookup"][f"NT_N{n_samples:03d}"]
        time_manifest_rows.append(
            {
                "time_vector_id": f"NT_N{n_samples:03d}",
                "n_samples": str(n_samples),
                "duration_s": expected["duration_s"],
                "cadence_s": expected["cadence_s"],
                "start_offset": str(start),
                "end_offset": str(end),
                "time_sha256": canonical_float64_sha256(vector),
                "all_finite": bool_text(bool(np.all(np.isfinite(vector)))),
                "strictly_increasing": bool_text(bool(np.all(np.diff(vector) > 0.0))),
                "exact_f1_9_hash_match": bool_text(
                    canonical_float64_sha256(vector) == expected["time_sha256"]
                ),
            }
        )

    write_csv(final_paths["series_manifest"], SERIES_FIELDS, series_manifest_rows)
    write_csv(final_paths["time_manifest"], TIME_FIELDS, time_manifest_rows)

    ordered_manifest_hash = file_sha256(final_paths["series_manifest"])
    time_manifest_hash = file_sha256(final_paths["time_manifest"])

    # Rename validated temporary arrays to their final frozen names.
    loaded_flux = None
    loaded_offsets = None
    loaded_time = None
    loaded_time_offsets = None
    gc.collect()
    for key in ("flux", "series_offsets", "time_values", "time_offsets"):
        os.replace(temp_paths[key], final_paths[key])

    # Reopen final files once more to verify renaming did not alter content.
    final_flux = np.load(final_paths["flux"], allow_pickle=False)
    final_offsets = np.load(final_paths["series_offsets"], allow_pickle=False)
    final_time = np.load(final_paths["time_values"], allow_pickle=False)
    final_time_offsets = np.load(final_paths["time_offsets"], allow_pickle=False)
    if canonical_float64_sha256(final_flux) != canonical_float64_sha256(
        np.concatenate([persisted_series[row["series_id"]] for row in child_rows])
    ):
        raise MaterializationError("Final flux logical hash changed after rename.")
    if not np.array_equal(final_offsets, np.asarray(
        [0] + [int(row["flux_end_offset"]) for row in series_manifest_rows], dtype="<i8"
    )):
        raise MaterializationError("Final series offsets changed after rename.")
    if canonical_float64_sha256(final_time) != canonical_float64_sha256(
        np.concatenate([persisted_times[n] for n in n_values])
    ):
        raise MaterializationError("Final time logical hash changed after rename.")
    if not np.array_equal(final_time_offsets, np.asarray(
        [0] + [int(row["end_offset"]) for row in time_manifest_rows], dtype="<i8"
    )):
        raise MaterializationError("Final time offsets changed after rename.")

    counts = {
        "series_count": 2160,
        "null_series_count": sum(
            row["ground_truth"] == "NULL_FLARE_RED_NOISE" for row in child_rows
        ),
        "positive_series_count": sum(
            row["ground_truth"] == "STATIONARY_QPP_PRESENT" for row in child_rows
        ),
        "condition_count": len({row["condition_id"] for row in child_rows}),
        "independent_block_count": len({row["block_id"] for row in child_rows}),
        "parent_count": len({row["parent_id"] for row in child_rows}),
        "series_per_condition_values": sorted(Counter(
            row["condition_id"] for row in child_rows
        ).values()),
        "series_per_n": {
            str(n): sum(int(row["n_samples"]) == n for row in child_rows)
            for n in n_values
        },
        "total_flux_values": int(final_flux.size),
        "series_offsets_count": int(final_offsets.size),
        "time_vector_count": len(n_values),
        "total_time_values": int(final_time.size),
        "time_offsets_count": int(final_time_offsets.size),
        "n120_series_count": len(parent_n120_rows),
    }
    expected_counts = {
        "series_count": 2160,
        "null_series_count": 720,
        "positive_series_count": 1440,
        "condition_count": 54,
        "independent_block_count": 120,
        "parent_count": 360,
        "total_flux_values": 129600,
        "series_offsets_count": 2161,
        "time_vector_count": 6,
        "total_time_values": 360,
        "time_offsets_count": 7,
        "n120_series_count": 360,
    }
    for key, expected in expected_counts.items():
        if counts[key] != expected:
            raise MaterializationError(f"Count mismatch for {key}: {counts[key]} != {expected}")
    if set(counts["series_per_condition_values"]) != {40}:
        raise MaterializationError("Not every condition has exactly 40 series.")
    if set(counts["series_per_n"].values()) != {360}:
        raise MaterializationError("Not every N has exactly 360 series.")

    physical_hashes = {
        path.name: file_sha256(path)
        for path in (
            final_paths["flux"],
            final_paths["series_offsets"],
            final_paths["time_values"],
            final_paths["time_offsets"],
            final_paths["series_manifest"],
            final_paths["time_manifest"],
        )
    }
    logical_hashes = {
        "canonical_flux_payload_sha256": canonical_float64_sha256(final_flux),
        "series_offsets_canonical_sha256": canonical_int64_sha256(final_offsets),
        "time_values_canonical_sha256": canonical_float64_sha256(final_time),
        "time_offsets_canonical_sha256": canonical_int64_sha256(final_time_offsets),
        "ordered_series_manifest_sha256": ordered_manifest_hash,
        "nested_time_manifest_sha256": time_manifest_hash,
    }

    distinct_flux_hashes = len({row["flux_sha256"] for row in series_manifest_rows})
    if distinct_flux_hashes != 2160:
        raise MaterializationError("Unexpected duplicate persisted flux contents.")

    script_path = Path(__file__).resolve()
    audit: dict[str, Any] = {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "materialization_status": "NESTED_DATASET_FROZEN_BEFORE_AFINO",
        "benchmark_id": specification["benchmark_id"],
        "benchmark_version": specification["benchmark_version"],
        "environment": environment_info(),
        "script": {
            "filename": script_path.name,
            "sha256": file_sha256(script_path),
        },
        "preflight": preflight_result,
        "normative_input_hashes": preflight_result["input_hashes"],
        "prewrite_comparisons": regenerated["prewrite_comparisons"],
        "counts": counts,
        "array_contract": {
            "flux_values": {"dtype": "<f8", "ndim": 1, "length": 129600, "order": "C"},
            "series_offsets": {"dtype": "<i8", "length": 2161},
            "time_values": {"dtype": "<f8", "length": 360, "order": "C"},
            "time_offsets": {"dtype": "<i8", "length": 7},
            "allow_pickle": False,
            "time_unit": "seconds",
        },
        "physical_hashes": physical_hashes,
        "logical_hashes": logical_hashes,
        "round_trip": {
            "child_series_planned": 2160,
            "child_series_exact": roundtrip_child_exact,
            "child_series_mismatches": 2160 - roundtrip_child_exact,
            "time_vectors_planned": 6,
            "time_vectors_exact": roundtrip_time_exact,
            "time_vector_mismatches": 6 - roundtrip_time_exact,
            "loader": "np.load(path, allow_pickle=False)",
        },
        "persisted_parent_representation": {
            "distinct_parent_ids": 360,
            "n120_series": 360,
            "one_to_one_verified": True,
            "separate_parent_payload_written": False,
            "n120_hash_matches_parent_flux_sha256": 360,
        },
        "persisted_nested_invariants": {
            "parent_child_planned": 2160,
            "parent_child_exact": parent_child_exact,
            "parent_child_mismatches": 2160 - parent_child_exact,
            "adjacent_prefix_planned": 1800,
            "adjacent_prefix_exact": adjacent_exact,
            "adjacent_prefix_mismatches": 1800 - adjacent_exact,
            "positive_adjacent_transitions": adjacent_positive,
            "null_adjacent_transitions": adjacent_null,
            "checks_used_only_reloaded_arrays": True,
        },
        "distinct_contents": {
            "persisted_flux_sha256": distinct_flux_hashes,
            "scientific_independence_inferred_from_uniqueness": False,
        },
        "child_noise_prefix_statistics": {
            "mean_min": float(min(float(row["noise_mean"]) for row in series_manifest_rows)),
            "mean_max": float(max(float(row["noise_mean"]) for row in series_manifest_rows)),
            "std_ddof1_min": float(min(float(row["noise_std_ddof1"]) for row in series_manifest_rows)),
            "std_ddof1_max": float(max(float(row["noise_std_ddof1"]) for row in series_manifest_rows)),
            "exact_0_005_required": False,
        },
        "incidents": [],
        "confirmations": {
            "afino_executed": False,
            "bic_computed": False,
            "model_selection_computed": False,
            "period_fit_computed": False,
            "dataset_visually_selected": False,
            "failed_parents_redrawn": False,
            "series_removed": False,
            "child_noise_recentered": False,
            "child_noise_rescaled": False,
            "child_noise_restandardized": False,
            "preregistration_modified": False,
            "nested_generator_modified": False,
        },
    }

    final_paths["audit"].write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    write_report(final_paths["report"], audit)

    # Postflight: every frozen input must remain unchanged.
    for filename, expected in EXPECTED_INPUT_HASHES.items():
        observed = file_sha256(root / filename)
        if observed != expected:
            raise MaterializationError(
                f"Frozen input changed during F1.10: {filename}: {observed} != {expected}"
            )

    print("F1.10 nested dataset materialization complete")
    print("materialization_status: NESTED_DATASET_FROZEN_BEFORE_AFINO")
    print("series_count: 2160")
    print("total_flux_values: 129600")
    print("child_round_trip_exact: 2160/2160")
    print("time_round_trip_exact: 6/6")
    print("persisted_parent_prefix_exact: 2160/2160")
    print("persisted_adjacent_prefix_exact: 1800/1800")
    print(f"audit: {final_paths['audit'].name}")
    print(f"report: {final_paths['report'].name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
