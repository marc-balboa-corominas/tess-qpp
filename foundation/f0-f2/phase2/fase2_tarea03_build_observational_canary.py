#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FULL_PLAN = ROOT / "fase2_tarea02_exact_afino_execution_plan.csv"
CANARY_PLAN = ROOT / "fase2_tarea03_observational_canary_plan.csv"

EXPECTED_FULL_SHA256 = "96c26a49bda9c2485ef02ed6a6de12caf56b54b45a9d997d86fb144e33abeb97"
EXPECTED_CANARY_SHA256 = "54ea652f03943e2adce202343c39e074df88a1b0999faf57287d28d253c7dd1c"

P3_VARIANTS = {
    *(f"F2V{number:06d}" for number in range(469, 475)),
    *(f"F2V{number:06d}" for number in range(547, 553)),
}
P2_DECISIONS = {
    "F2D000379", "F2D000383", "F2D000457", "F2D000461",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def select_rows(full_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    selected = []
    for row in full_rows:
        include_p3 = (
            row["variant_id"] in P3_VARIANTS
            and int(row["external_optimizer_seed"]) in {0, 1}
        )
        include_p2 = (
            row["planned_decision_id"] in P2_DECISIONS
            and row["decision_class"] == "primary"
            and int(row["external_optimizer_seed"]) == 0
        )
        if include_p3 or include_p2:
            selected.append(dict(row))
    selected.sort(key=lambda row: int(row["job_order"]))
    for order, row in enumerate(selected, start=1):
        row["canary_order"] = str(order)
    return selected


def validate(rows: list[dict[str, str]]) -> None:
    if len(rows) != 84:
        raise RuntimeError(f"Canary rows: {len(rows)} != 84.")
    if [int(row["canary_order"]) for row in rows] != list(range(1, 85)):
        raise RuntimeError("canary_order does not preserve 1..84.")
    if [int(row["job_order"]) for row in rows] != sorted(
        int(row["job_order"]) for row in rows
    ):
        raise RuntimeError("Canary is not ordered by original job_order.")
    if len({row["job_id"] for row in rows}) != 84:
        raise RuntimeError("Duplicate canary job_id.")
    scientific = {
        (
            row["variant_id"],
            int(row["external_optimizer_seed"]),
            row["model_id"],
        )
        for row in rows
    }
    if len(scientific) != 84:
        raise RuntimeError("Duplicate canary scientific key.")
    variants = {row["variant_id"] for row in rows}
    decisions = {
        (
            row["planned_decision_id"],
            int(row["external_optimizer_seed"]),
        )
        for row in rows
    }
    primary = {
        key
        for key in decisions
        if next(
            row for row in rows
            if (
                row["planned_decision_id"],
                int(row["external_optimizer_seed"]),
            ) == key
        )["decision_class"] == "primary"
    }
    stability = decisions - primary
    if len(variants) != 16 or len(primary) != 16 or len(stability) != 12:
        raise RuntimeError("Canary variant/decision counts are incorrect.")
    if Counter(row["model_id"] for row in rows) != {
        "M0": 28, "M1": 28, "M2": 28,
    }:
        raise RuntimeError("Canary model counts are incorrect.")
    if {row["processing_profile_id"] for row in rows} != {
        "P00", "P01", "P02", "P03", "P04", "P05",
    }:
        raise RuntimeError("The six processing profiles are not covered.")
    if {row["observational_role"] for row in rows} != {
        "PUBLISHED_QPP_REPRODUCED", "MATCHED_NOT_SELECTED",
    }:
        raise RuntimeError("Both observational roles are not covered.")
    if {row["window_variant_id"] for row in rows} != {"W00", "WX2"}:
        raise RuntimeError("W00 and WX2 are not both covered.")


def serialized(rows: list[dict[str, str]], fields: list[str]) -> bytes:
    import io
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=fields,
        extrasaction="raise",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verify-existing",
        action="store_true",
        help="Verify the frozen canary already present.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Build the canary only when no output exists.",
    )
    args = parser.parse_args()
    if args.verify_existing == args.write:
        raise RuntimeError("Choose exactly one of --verify-existing or --write.")

    if not FULL_PLAN.is_file():
        raise FileNotFoundError(FULL_PLAN)
    if sha256(FULL_PLAN) != EXPECTED_FULL_SHA256:
        raise RuntimeError("F2.2 full plan hash mismatch.")
    full_rows = read_csv(FULL_PLAN)
    if len(full_rows) != 2784:
        raise RuntimeError("F2.2 full plan row count mismatch.")
    expected = select_rows(full_rows)
    validate(expected)
    fields = list(full_rows[0].keys()) + ["canary_order"]
    expected_bytes = serialized(expected, fields)

    if args.write:
        if CANARY_PLAN.exists():
            raise FileExistsError(CANARY_PLAN)
        CANARY_PLAN.write_bytes(expected_bytes)
    else:
        if not CANARY_PLAN.is_file():
            raise FileNotFoundError(CANARY_PLAN)
        if CANARY_PLAN.read_bytes() != expected_bytes:
            raise RuntimeError("Existing canary is not the literal subset.")
    observed = sha256(CANARY_PLAN)
    if observed != EXPECTED_CANARY_SHA256:
        raise RuntimeError(
            f"Canary hash mismatch: {observed} != {EXPECTED_CANARY_SHA256}."
        )
    print("F2.3 canary plan verified")
    print(f"canary_plan_rows: {len(expected)}")
    print("canary_unique_variants: 16")
    print("canary_primary_decisions: 16")
    print("canary_stability_decisions: 12")
    print("rows_per_model: 28")
    print(f"canary_plan_sha256: {observed}")


if __name__ == "__main__":
    main()
