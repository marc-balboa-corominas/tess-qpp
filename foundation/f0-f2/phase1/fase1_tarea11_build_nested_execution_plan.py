from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parent
PREREGISTRATION_JSON = ROOT / "fase1_tarea08_nested_window_preregistration.json"
DESIGN_GRID_CSV = ROOT / "fase1_tarea08_nested_window_design_grid.csv"
SERIES_MANIFEST_CSV = ROOT / "fase1_tarea10_nested_series_manifest.csv"
TIME_MANIFEST_CSV = ROOT / "fase1_tarea10_nested_time_manifest.csv"
DEFAULT_FULL_PLAN = ROOT / "fase1_tarea11_nested_full_execution_plan.csv"
DEFAULT_CANARY_PLAN = ROOT / "fase1_tarea11_nested_canary_plan.csv"

EXPECTED_INPUT_HASHES = {
    PREREGISTRATION_JSON.name: "d80890319b4646f8df994ba7c1dd9da3dc1f141834dbf289d1b17c484fa67487",
    DESIGN_GRID_CSV.name: "7c1a1fb9724dfe195fec1337e4f0af906e3dd8f1c754ab0abc7f3bc2cc1e8dcd",
    SERIES_MANIFEST_CSV.name: "cc9f44c710dade51e91fe0c2d30b193c621c7b9905764c6fe69fcf1c94c395a5",
    TIME_MANIFEST_CSV.name: "cfc1b66b0e949acb2611f73823074faaa1259bcf9a458d687506fb361cb89ed4",
}

MODEL_SPECS = (("M0", "pow_const"), ("M1", "pow_const_gauss"), ("M2", "bpow_const"))
NESTED_LENGTHS = (15, 30, 45, 60, 90, 120)

PLAN_FIELDNAMES = [
    "job_id",
    "job_order",
    "job_class",
    "series_id",
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
    "external_optimizer_seed",
    "model_id",
    "model_name",
    "flux_start_offset",
    "flux_end_offset",
    "time_vector_id",
    "input_flux_sha256",
    "input_time_sha256",
    "parent_n120_series_id",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def resolve_under_root(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def verify_inputs() -> None:
    for filename, expected in EXPECTED_INPUT_HASHES.items():
        path = ROOT / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = sha256(path)
        if observed != expected:
            raise RuntimeError(
                f"Hash incorrecto para {filename}.\n"
                f"Esperado: {expected}\nObservado: {observed}"
            )
    preregistration = json.loads(PREREGISTRATION_JSON.read_text(encoding="utf-8"))
    if preregistration.get("benchmark_id") != "afino_nested_window_support_v1":
        raise RuntimeError("benchmark_id inesperado en F1.8.")
    if preregistration.get("benchmark_version") != "1.0.0":
        raise RuntimeError("benchmark_version inesperado en F1.8.")
    if preregistration.get("preregistration_status") != "FROZEN_BEFORE_SERIES_GENERATION":
        raise RuntimeError("F1.8 no está congelada antes de generar series.")


def build_plans() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    verify_inputs()
    grid = read_csv(DESIGN_GRID_CSV)
    series = read_csv(SERIES_MANIFEST_CSV)
    times = read_csv(TIME_MANIFEST_CSV)
    if len(grid) != 54 or len(series) != 2160 or len(times) != 6:
        raise RuntimeError("Conteos de entrada incompatibles con F1.8/F1.10.")
    if list(grid[0]) != [
        "condition_id", "ground_truth", "n_samples", "duration_s",
        "red_noise_alpha", "period_s", "qpp_fraction", "parent_n_samples",
        "window_extraction", "data_seed_start", "data_seed_end",
        "data_seed_count", "planned_series_count", "primary_optimizer_seed",
        "stability_data_seed", "stability_optimizer_seed_start",
        "stability_optimizer_seed_end", "planned_primary_model_calls",
        "planned_stability_model_calls",
    ]:
        raise RuntimeError("Esquema inesperado del grid F1.8.")

    time_by_id = {row["time_vector_id"]: row for row in times}
    if len(time_by_id) != 6:
        raise RuntimeError("time_vector_id duplicado.")
    series_sorted = sorted(series, key=lambda row: int(row["series_order"]))
    if [int(row["series_order"]) for row in series_sorted] != list(range(1, 2161)):
        raise RuntimeError("series_order no es 1..2160.")
    series_by_condition_seed = {
        (row["condition_id"], int(row["data_seed"])): row for row in series
    }
    if len(series_by_condition_seed) != 2160:
        raise RuntimeError("Clave (condition_id, data_seed) duplicada.")

    full_rows: list[dict[str, Any]] = []

    def append_series_jobs(series_row: dict[str, str], job_class: str, seed: int) -> None:
        time_row = time_by_id[series_row["time_vector_id"]]
        for model_id, model_name in MODEL_SPECS:
            job_order = len(full_rows) + 1
            full_rows.append(
                {
                    "job_id": f"NWJ{job_order:06d}",
                    "job_order": job_order,
                    "job_class": job_class,
                    "series_id": series_row["series_id"],
                    "condition_id": series_row["condition_id"],
                    "parent_id": series_row["parent_id"],
                    "block_id": series_row["block_id"],
                    "ground_truth": series_row["ground_truth"],
                    "n_samples": series_row["n_samples"],
                    "duration_s": series_row["duration_s"],
                    "red_noise_alpha": series_row["red_noise_alpha"],
                    "period_s": series_row["period_s"],
                    "qpp_fraction": series_row["qpp_fraction"],
                    "data_seed": series_row["data_seed"],
                    "external_optimizer_seed": seed,
                    "model_id": model_id,
                    "model_name": model_name,
                    "flux_start_offset": series_row["flux_start_offset"],
                    "flux_end_offset": series_row["flux_end_offset"],
                    "time_vector_id": series_row["time_vector_id"],
                    "input_flux_sha256": series_row["flux_sha256"],
                    "input_time_sha256": time_row["time_sha256"],
                    "parent_n120_series_id": series_row["parent_n120_series_id"],
                }
            )

    for series_row in series_sorted:
        append_series_jobs(series_row, "primary", 0)
    for condition in grid:
        series_row = series_by_condition_seed[(condition["condition_id"], 0)]
        for seed in range(1, 10):
            append_series_jobs(series_row, "stability", seed)

    if len(full_rows) != 7938:
        raise RuntimeError(f"Plan completo: {len(full_rows)} != 7938.")
    if sum(row["job_class"] == "primary" for row in full_rows) != 6480:
        raise RuntimeError("Conteo primary incorrecto.")
    if sum(row["job_class"] == "stability" for row in full_rows) != 1458:
        raise RuntimeError("Conteo stability incorrecto.")
    for model_id, _ in MODEL_SPECS:
        if sum(row["model_id"] == model_id for row in full_rows) != 2646:
            raise RuntimeError(f"Conteo incorrecto para {model_id}.")
    if len({row["job_id"] for row in full_rows}) != 7938:
        raise RuntimeError("job_id duplicado en plan completo.")
    if len({
        (row["series_id"], int(row["external_optimizer_seed"]), row["model_id"])
        for row in full_rows
    }) != 7938:
        raise RuntimeError("Clave científica duplicada en plan completo.")

    by_scientific_key = {
        (row["series_id"], int(row["external_optimizer_seed"]), row["model_id"]): row
        for row in full_rows
    }

    def resolve_trajectory(
        ground_truth: str,
        alpha: float,
        period_s: float | None,
    ) -> list[dict[str, str]]:
        trajectory: list[dict[str, str]] = []
        for n_samples in NESTED_LENGTHS:
            matches = [
                row for row in series
                if int(row["data_seed"]) == 0
                and int(row["n_samples"]) == n_samples
                and row["ground_truth"] == ground_truth
                and float(row["red_noise_alpha"]) == alpha
                and (
                    period_s is None
                    or float(row["period_s"]) == period_s
                )
            ]
            if len(matches) != 1:
                raise RuntimeError(
                    f"Trayectoria no resoluble: gt={ground_truth}, alpha={alpha}, "
                    f"P={period_s}, N={n_samples}, coincidencias={len(matches)}."
                )
            trajectory.append(matches[0])
        return trajectory

    trajectory_a = resolve_trajectory("NULL_FLARE_RED_NOISE", 0.0, None)
    trajectory_b = resolve_trajectory("STATIONARY_QPP_PRESENT", 2.0, 80.0)
    canary_series = trajectory_a + trajectory_b
    if len({row["parent_id"] for row in canary_series}) != 2:
        raise RuntimeError("El canary no contiene exactamente dos parent_id.")
    if len({row["block_id"] for row in canary_series}) != 2:
        raise RuntimeError("El canary no contiene exactamente dos block_id.")

    canary_rows: list[dict[str, Any]] = []
    for series_row in canary_series:
        for seed in (0, 1):
            for model_id, _ in MODEL_SPECS:
                canary_rows.append(
                    by_scientific_key[(series_row["series_id"], seed, model_id)]
                )
    if len(canary_rows) != 72:
        raise RuntimeError("El canary no contiene 72 trabajos.")
    if len({row["series_id"] for row in canary_rows}) != 12:
        raise RuntimeError("El canary no contiene 12 series.")
    return full_rows, canary_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Construye y valida los planes normativos de F1.11."
    )
    parser.add_argument("--full-output", type=Path, default=DEFAULT_FULL_PLAN)
    parser.add_argument("--canary-output", type=Path, default=DEFAULT_CANARY_PLAN)
    parser.add_argument(
        "--verify-existing",
        action="store_true",
        help="Compara los bytes generados con planes ya existentes sin sobrescribirlos.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    full_output = resolve_under_root(args.full_output)
    canary_output = resolve_under_root(args.canary_output)
    full_rows, canary_rows = build_plans()

    if args.verify_existing:
        for path, rows in ((full_output, full_rows), (canary_output, canary_rows)):
            if not path.is_file():
                raise FileNotFoundError(path)
            temporary = path.with_name(path.name + ".verification.tmp")
            try:
                write_csv(temporary, rows)
                if temporary.read_bytes() != path.read_bytes():
                    raise RuntimeError(f"El plan existente no coincide: {path.name}.")
            finally:
                if temporary.exists():
                    temporary.unlink()
    else:
        for path in (full_output, canary_output):
            if path.exists():
                raise FileExistsError(
                    f"No se sobrescribe el plan existente: {path.name}. "
                    "Use --verify-existing para comprobarlo."
                )
        write_csv(full_output, full_rows)
        write_csv(canary_output, canary_rows)

    print("F1.11 nested execution plans validated")
    print(f"full_plan_rows: {len(full_rows)}")
    print(f"canary_plan_rows: {len(canary_rows)}")
    print(f"full_plan_sha256: {sha256(full_output)}")
    print(f"canary_plan_sha256: {sha256(canary_output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
