from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parent

FLUX_NPY = ROOT / "fase1_tarea03_core_flux_values.npy"
SERIES_OFFSETS_NPY = ROOT / "fase1_tarea03_core_series_offsets.npy"
TIME_VALUES_NPY = ROOT / "fase1_tarea03_core_time_values.npy"
TIME_OFFSETS_NPY = ROOT / "fase1_tarea03_core_time_offsets.npy"
SERIES_MANIFEST_CSV = ROOT / "fase1_tarea03_core_series_manifest.csv"
TIME_MANIFEST_CSV = ROOT / "fase1_tarea03_time_vector_manifest.csv"
MATERIALIZATION_AUDIT_JSON = ROOT / "fase1_tarea03_materialization_audit.json"

FULL_PLAN_CSV = ROOT / "fase1_tarea04_full_execution_plan.csv"
CANARY_PLAN_CSV = ROOT / "fase1_tarea04_canary_plan.csv"

EXPECTED_PHYSICAL_HASHES = {
    "fase1_tarea03_core_flux_values.npy": (
        "f5fdd48f2951a1e055355d76b8b82c931fceea8cbb0688ca0099fe329594e60d"
    ),
    "fase1_tarea03_core_series_offsets.npy": (
        "9169e4253cee3fb75b52e6ef61995efcdb71514720ba39c311eb9a085e901d85"
    ),
    "fase1_tarea03_core_time_values.npy": (
        "730e97faa7b9bbcf03ea9b8c897790fd500c36fadb8f7c47608d9614fbba8513"
    ),
    "fase1_tarea03_core_time_offsets.npy": (
        "c58d96df35b66a33ec3ffe37347f745af78cfd3eaa4e77762230206513f4c233"
    ),
    "fase1_tarea03_core_series_manifest.csv": (
        "2020c849348c81235036443d3215395c602b80b00debe64fec692935dda778f4"
    ),
    "fase1_tarea03_time_vector_manifest.csv": (
        "ce7f2f465f7ee73c8de983a91a8415b1a9d75e3b65a5e94b553d42c94068a5e7"
    ),
    "fase1_tarea03_materialization_audit.json": (
        "8fa6d0b108dd9f4c2d941729221ad9fcbfea14af63baaec1474cce751bb51310"
    ),
}

EXPECTED_LOGICAL_HASHES = {
    "canonical_flux_payload_sha256": (
        "f593637faabf57bdcd9c4bea66f161cbaace77ad09de682179d709b002167abe"
    ),
    "series_offsets_canonical_sha256": (
        "b7ed6562c1d5a256309ca417744ed3f0520c79fb3d85b43a67383d9d4810817e"
    ),
    "time_values_canonical_sha256": (
        "6809c6c9ecb0667c5eda35e62fccbd958dc5c619845f9da37e0713f5b1580537"
    ),
    "time_offsets_canonical_sha256": (
        "28d9acdf22fdfaf6737337f20331e37a52710ec0d43c5b39251119b619a875a4"
    ),
}

MODEL_SPECS = (
    ("M0", "pow_const"),
    ("M1", "pow_const_gauss"),
    ("M2", "bpow_const"),
)

CANARY_CONDITION_IDS = (
    "C001_NULL_N015_A0",
    "C030_QPP_N015_P080_A2_Q040",
    "C004_NULL_N030_A0",
    "C057_QPP_N030_P140_A2_Q040",
    "C007_NULL_N060_A0",
    "C084_QPP_N060_P140_A2_Q040",
    "C010_NULL_N120_A0",
    "C111_QPP_N120_P140_A2_Q040",
)

PLAN_FIELDNAMES = [
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

EXPECTED_SERIES_COUNT = 4440
EXPECTED_CONDITION_COUNT = 111
EXPECTED_FULL_PLAN_ROWS = 16317
EXPECTED_PRIMARY_PLAN_ROWS = 13320
EXPECTED_STABILITY_PLAN_ROWS = 2997
EXPECTED_CANARY_PLAN_ROWS = 48


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(array: np.ndarray, dtype: str) -> str:
    canonical = np.ascontiguousarray(array, dtype=dtype)
    return hashlib.sha256(canonical.tobytes(order="C")).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=PLAN_FIELDNAMES,
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def verify_hashes() -> dict[str, str]:
    observed: dict[str, str] = {}
    for filename, expected in EXPECTED_PHYSICAL_HASHES.items():
        path = ROOT / filename
        if not path.exists():
            raise FileNotFoundError(f"Falta el artefacto requerido: {path}")
        digest = sha256(path)
        observed[filename] = digest
        if digest != expected:
            raise RuntimeError(
                f"Hash físico incorrecto para {filename}.\n"
                f"Esperado: {expected}\nObservado: {digest}"
            )
    return observed


def load_and_verify_dataset() -> dict[str, Any]:
    physical_hashes = verify_hashes()

    audit = json.loads(MATERIALIZATION_AUDIT_JSON.read_text(encoding="utf-8"))
    if audit.get("materialization_status") != "DATASET_FROZEN_BEFORE_AFINO":
        raise RuntimeError("F1.3 no está congelada antes de AFINO.")
    if audit.get("confirmations", {}).get("afino_executed") is not False:
        raise RuntimeError("La auditoría F1.3 no confirma afino_executed=false.")

    flux_values = np.load(FLUX_NPY, allow_pickle=False)
    series_offsets = np.load(SERIES_OFFSETS_NPY, allow_pickle=False)
    time_values = np.load(TIME_VALUES_NPY, allow_pickle=False)
    time_offsets = np.load(TIME_OFFSETS_NPY, allow_pickle=False)

    if flux_values.dtype != np.dtype("<f8") or flux_values.ndim != 1:
        raise RuntimeError("core_flux_values.npy no es un vector <f8.")
    if series_offsets.dtype != np.dtype("<i8") or series_offsets.ndim != 1:
        raise RuntimeError("core_series_offsets.npy no es un vector <i8.")
    if time_values.dtype != np.dtype("<f8") or time_values.ndim != 1:
        raise RuntimeError("core_time_values.npy no es un vector <f8.")
    if time_offsets.dtype != np.dtype("<i8") or time_offsets.ndim != 1:
        raise RuntimeError("core_time_offsets.npy no es un vector <i8.")

    logical_hashes = {
        "canonical_flux_payload_sha256": canonical_sha256(flux_values, "<f8"),
        "series_offsets_canonical_sha256": canonical_sha256(series_offsets, "<i8"),
        "time_values_canonical_sha256": canonical_sha256(time_values, "<f8"),
        "time_offsets_canonical_sha256": canonical_sha256(time_offsets, "<i8"),
    }
    for name, expected in EXPECTED_LOGICAL_HASHES.items():
        observed = logical_hashes[name]
        if observed != expected:
            raise RuntimeError(
                f"Hash lógico incorrecto para {name}.\n"
                f"Esperado: {expected}\nObservado: {observed}"
            )

    series_rows = read_csv(SERIES_MANIFEST_CSV)
    time_rows = read_csv(TIME_MANIFEST_CSV)
    if len(series_rows) != EXPECTED_SERIES_COUNT:
        raise RuntimeError(f"El manifiesto contiene {len(series_rows)} series, no 4440.")
    if len(time_rows) != 4:
        raise RuntimeError("El manifiesto temporal no contiene cuatro vectores.")

    expected_series_ids = [f"S{index:06d}" for index in range(1, 4441)]
    if [row["series_id"] for row in series_rows] != expected_series_ids:
        raise RuntimeError("series_id no conserva S000001–S004440 en orden.")
    if [int(row["series_order"]) for row in series_rows] != list(range(1, 4441)):
        raise RuntimeError("series_order no conserva 1–4440.")

    condition_counts = Counter(row["condition_id"] for row in series_rows)
    if len(condition_counts) != EXPECTED_CONDITION_COUNT:
        raise RuntimeError("No existen exactamente 111 condiciones.")
    if set(condition_counts.values()) != {40}:
        raise RuntimeError("Alguna condición no aparece exactamente 40 veces.")

    time_by_id = {row["time_vector_id"]: row for row in time_rows}
    if set(time_by_id) != {"T_N015", "T_N030", "T_N060", "T_N120"}:
        raise RuntimeError("Identificadores temporales inesperados.")

    if len(series_offsets) != 4441 or int(series_offsets[0]) != 0:
        raise RuntimeError("Offsets de series inválidos.")
    if int(series_offsets[-1]) != len(flux_values) or len(flux_values) != 264600:
        raise RuntimeError("Longitud final de flujo u offset final inválido.")
    if len(time_offsets) != 5 or int(time_offsets[0]) != 0:
        raise RuntimeError("Offsets temporales inválidos.")
    if int(time_offsets[-1]) != len(time_values) or len(time_values) != 225:
        raise RuntimeError("Longitud temporal u offset final inválido.")

    for index, row in enumerate(series_rows):
        n_samples = int(row["n_samples"])
        start = int(row["flux_start_offset"])
        end = int(row["flux_end_offset"])
        if start != int(series_offsets[index]) or end != int(series_offsets[index + 1]):
            raise RuntimeError(f"Offsets discordantes en {row['series_id']}.")
        if end - start != n_samples:
            raise RuntimeError(f"Longitud discordante en {row['series_id']}.")
        flux = flux_values[start:end]
        if not np.all(np.isfinite(flux)):
            raise RuntimeError(f"Flujo no finito en {row['series_id']}.")
        if canonical_sha256(flux, "<f8") != row["flux_sha256"]:
            raise RuntimeError(f"Hash de flujo discordante en {row['series_id']}.")

        time_meta = time_by_id.get(row["time_vector_id"])
        if time_meta is None:
            raise RuntimeError(f"time_vector_id desconocido en {row['series_id']}.")
        if int(time_meta["n_samples"]) != n_samples:
            raise RuntimeError(f"N temporal discordante en {row['series_id']}.")

        if row["ground_truth"] == "NULL_FLARE_RED_NOISE":
            if any(row[field] != "" for field in ("period_s", "qpp_fraction", "minimum_cycles")):
                raise RuntimeError(f"Nulo con parámetro QPP ficticio en {row['series_id']}.")

    for time_index, row in enumerate(time_rows):
        start = int(row["start_offset"])
        end = int(row["end_offset"])
        if start != int(time_offsets[time_index]) or end != int(time_offsets[time_index + 1]):
            raise RuntimeError(f"Offsets temporales discordantes en {row['time_vector_id']}.")
        vector = time_values[start:end]
        if len(vector) != int(row["n_samples"]):
            raise RuntimeError(f"Longitud temporal discordante en {row['time_vector_id']}.")
        if canonical_sha256(vector, "<f8") != row["time_sha256"]:
            raise RuntimeError(f"Hash temporal discordante en {row['time_vector_id']}.")
        if not np.all(np.isfinite(vector)) or not np.all(np.diff(vector) > 0):
            raise RuntimeError(f"Vector temporal inválido en {row['time_vector_id']}.")
        if float(vector[0]) != 0.0:
            raise RuntimeError(f"El tiempo no comienza en cero en {row['time_vector_id']}.")

    return {
        "physical_hashes": physical_hashes,
        "logical_hashes": logical_hashes,
        "series_rows": series_rows,
        "time_rows": time_rows,
        "time_by_id": time_by_id,
    }


def plan_payload(
    *,
    job_order: int,
    job_class: str,
    series: dict[str, str],
    external_optimizer_seed: int,
    model_id: str,
    model_name: str,
    time_by_id: dict[str, dict[str, str]],
) -> dict[str, Any]:
    return {
        "job_id": f"J{job_order:06d}",
        "job_order": job_order,
        "job_class": job_class,
        "series_id": series["series_id"],
        "condition_id": series["condition_id"],
        "ground_truth": series["ground_truth"],
        "data_seed": int(series["data_seed"]),
        "external_optimizer_seed": external_optimizer_seed,
        "model_id": model_id,
        "model_name": model_name,
        "n_samples": int(series["n_samples"]),
        "period_s": series["period_s"],
        "qpp_fraction": series["qpp_fraction"],
        "flux_start_offset": int(series["flux_start_offset"]),
        "flux_end_offset": int(series["flux_end_offset"]),
        "time_vector_id": series["time_vector_id"],
        "input_flux_sha256": series["flux_sha256"],
        "input_time_sha256": time_by_id[series["time_vector_id"]]["time_sha256"],
    }


def build_full_plan(
    series_rows: list[dict[str, str]],
    time_by_id: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    job_order = 1

    # Primary calls: series order, then M0/M1/M2.
    for series in series_rows:
        for model_id, model_name in MODEL_SPECS:
            rows.append(
                plan_payload(
                    job_order=job_order,
                    job_class="primary",
                    series=series,
                    external_optimizer_seed=0,
                    model_id=model_id,
                    model_name=model_name,
                    time_by_id=time_by_id,
                )
            )
            job_order += 1

    # Stability calls: C001–C111, seeds 1–9, then M0/M1/M2.
    stability_series = [row for row in series_rows if int(row["data_seed"]) == 0]
    if len(stability_series) != 111:
        raise RuntimeError("No se encontraron exactamente 111 series data_seed=0.")
    condition_numbers = [int(row["condition_id"][1:4]) for row in stability_series]
    if condition_numbers != list(range(1, 112)):
        raise RuntimeError("Las series de estabilidad no siguen C001–C111.")

    for series in stability_series:
        for optimizer_seed in range(1, 10):
            for model_id, model_name in MODEL_SPECS:
                rows.append(
                    plan_payload(
                        job_order=job_order,
                        job_class="stability",
                        series=series,
                        external_optimizer_seed=optimizer_seed,
                        model_id=model_id,
                        model_name=model_name,
                        time_by_id=time_by_id,
                    )
                )
                job_order += 1

    return rows


def validate_full_plan(rows: list[dict[str, Any]]) -> None:
    if len(rows) != EXPECTED_FULL_PLAN_ROWS:
        raise RuntimeError(f"Plan completo con {len(rows)} filas, no 16317.")
    if [row["job_order"] for row in rows] != list(range(1, 16318)):
        raise RuntimeError("job_order no es 1–16317.")
    if [row["job_id"] for row in rows] != [f"J{i:06d}" for i in range(1, 16318)]:
        raise RuntimeError("job_id no es J000001–J016317.")

    primary = [row for row in rows if row["job_class"] == "primary"]
    stability = [row for row in rows if row["job_class"] == "stability"]
    if len(primary) != EXPECTED_PRIMARY_PLAN_ROWS:
        raise RuntimeError("Conteo primario incorrecto.")
    if len(stability) != EXPECTED_STABILITY_PLAN_ROWS:
        raise RuntimeError("Conteo de estabilidad incorrecto.")
    if rows[:EXPECTED_PRIMARY_PLAN_ROWS] != primary:
        raise RuntimeError("Las llamadas primarias no preceden a estabilidad.")

    keys = [
        (row["series_id"], row["external_optimizer_seed"], row["model_id"])
        for row in rows
    ]
    if len(set(keys)) != len(keys):
        raise RuntimeError("Clave (series_id, optimizer_seed, model_id) duplicada.")

    for row in primary:
        if row["external_optimizer_seed"] != 0:
            raise RuntimeError("Llamada primaria con seed distinto de cero.")
    for row in stability:
        if row["data_seed"] != 0 or not 1 <= row["external_optimizer_seed"] <= 9:
            raise RuntimeError("Llamada de estabilidad fuera del protocolo.")


def build_canary_plan(full_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {
        (
            row["condition_id"],
            row["data_seed"],
            row["external_optimizer_seed"],
            row["model_id"],
        ): row
        for row in full_rows
    }
    selected: list[dict[str, Any]] = []
    for condition_id in CANARY_CONDITION_IDS:
        for optimizer_seed in (0, 1):
            for model_id, _ in MODEL_SPECS:
                key = (condition_id, 0, optimizer_seed, model_id)
                if key not in by_key:
                    raise RuntimeError(f"No existe el trabajo canary {key}.")
                selected.append(dict(by_key[key]))
    return selected


def validate_canary_plan(rows: list[dict[str, Any]]) -> None:
    if len(rows) != EXPECTED_CANARY_PLAN_ROWS:
        raise RuntimeError("El canary no contiene 48 filas.")
    if len({row["job_id"] for row in rows}) != 48:
        raise RuntimeError("job_id duplicado en el canary.")
    keys = [
        (row["series_id"], row["external_optimizer_seed"], row["model_id"])
        for row in rows
    ]
    if len(set(keys)) != 48:
        raise RuntimeError("Clave científica duplicada en el canary.")
    conditions = []
    for row in rows:
        if row["condition_id"] not in conditions:
            conditions.append(row["condition_id"])
    if tuple(conditions) != CANARY_CONDITION_IDS:
        raise RuntimeError("El canary no conserva el orden predeclarado.")

    counts = Counter(row["condition_id"] for row in rows)
    if set(counts.values()) != {6}:
        raise RuntimeError("Cada condición canary debe aportar seis llamadas.")


def main() -> int:
    print("F1.4 — CONSTRUCCIÓN DEL PLAN NORMATIVO")
    print("AFINO ejecutado: no")
    dataset = load_and_verify_dataset()
    print("Hashes físicos y lógicos de F1.3: verificados")

    full_rows = build_full_plan(dataset["series_rows"], dataset["time_by_id"])
    validate_full_plan(full_rows)
    canary_rows = build_canary_plan(full_rows)
    validate_canary_plan(canary_rows)

    write_csv(FULL_PLAN_CSV, full_rows)
    write_csv(CANARY_PLAN_CSV, canary_rows)

    # Read back and validate row counts to catch serialization errors.
    if len(read_csv(FULL_PLAN_CSV)) != EXPECTED_FULL_PLAN_ROWS:
        raise RuntimeError("Round-trip del plan completo falló.")
    if len(read_csv(CANARY_PLAN_CSV)) != EXPECTED_CANARY_PLAN_ROWS:
        raise RuntimeError("Round-trip del canary falló.")

    print(f"full_plan_rows: {len(full_rows)}")
    print(f"primary_plan_rows: {sum(r['job_class'] == 'primary' for r in full_rows)}")
    print(f"stability_plan_rows: {sum(r['job_class'] == 'stability' for r in full_rows)}")
    print(f"canary_plan_rows: {len(canary_rows)}")
    print(f"{FULL_PLAN_CSV.name}: {sha256(FULL_PLAN_CSV)}")
    print(f"{CANARY_PLAN_CSV.name}: {sha256(CANARY_PLAN_CSV)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"PLAN_BUILD_BLOCKED: {exc}", file=sys.stderr)
        raise
