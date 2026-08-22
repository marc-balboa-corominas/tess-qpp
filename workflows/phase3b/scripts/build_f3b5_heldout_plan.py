from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter
from pathlib import Path


EXPECTED_SERIES_SHA = (
    "3b98e31137b3f1d3cc67c2a7eead70414879891556be16196f954e4682410336"
)

EXPECTED_PAYLOAD_SHA = (
    "d20b0dac662cf809eb86d5e87d96f35e236b6ff2fbfb0fa86eeb4da8a49af8b4"
)


DECISION_FIELDS = [
    "planned_decision_id",
    "decision_order",
    "decision_class",
    "simulation_unit_id",
    "background_realization_id",
    "external_optimizer_seed",
    "payload_logical_sha256",
    "input_state",
    "gap_quality_regime",
    "planned_model_calls",
    "execution_status",
]


PLAN_FIELDS = [
    "job_id",
    "job_order",
    "planned_decision_id",
    "simulation_unit_id",
    "background_realization_id",
    "external_optimizer_seed",
    "model_id",
    "payload_logical_sha256",
    "afino_version",
    "afino_commit",
    "low_frequency_cutoff_hz",
    "execution_status",
]


FORBIDDEN_OUTPUT_COLUMNS = {
    "truth_state",
    "true_period_s",
    "qpp_fraction",
    "red_noise_alpha",
    "qpp_phase_rad",
    "signal_family",
    "qpp_selected",
    "delta_bic_0_1",
    "delta_bic_2_1",
    "candidate_rule",
    "candidate_threshold",
}


def sha(path: Path) -> str:

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def read_csv(path: Path):

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        return (
            list(reader),
            list(reader.fieldnames or []),
        )


def write_csv(
    path: Path,
    rows,
    fields,
) -> None:

    if path.exists():
        raise RuntimeError(
            f"Refusing overwrite: {path}"
        )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="raise",
            lineterminator="\n",
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


def main() -> int:

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo-root",
        default=".",
    )

    args = parser.parse_args()

    repo = Path(
        args.repo_root
    ).resolve()


    tables = (
        repo
        / "workflows/phase3b/heldout/"
          "materialization/evidence/tables"
    )

    series_path = (
        tables
        / "f3b5_heldout_series_manifest.csv"
    )

    payload_path = (
        tables
        / "f3b5_heldout_payload_manifest.csv"
    )

    development_plan_path = (
        repo
        / "workflows/phase3b/development/evidence/tables/"
          "f3b2_development_exact_afino_plan.csv"
    )

    decision_path = (
        tables
        / "f3b5_heldout_decision_grid.csv"
    )

    plan_path = (
        tables
        / "f3b5_heldout_exact_afino_plan.csv"
    )


    if sha(
        series_path
    ) != EXPECTED_SERIES_SHA:
        raise RuntimeError(
            "Frozen HELDOUT series manifest changed"
        )

    if sha(
        payload_path
    ) != EXPECTED_PAYLOAD_SHA:
        raise RuntimeError(
            "Frozen HELDOUT payload manifest changed"
        )


    series_rows, _ = read_csv(
        series_path
    )

    payload_rows, _ = read_csv(
        payload_path
    )

    development_plan, _ = read_csv(
        development_plan_path
    )


    if len(series_rows) != 4320:
        raise RuntimeError(
            "HELDOUT series rows != 4320"
        )

    if len(payload_rows) != 4320:
        raise RuntimeError(
            "HELDOUT payload rows != 4320"
        )


    afino_contracts = {
        (
            row["afino_version"],
            row["afino_commit"],
            row["low_frequency_cutoff_hz"],
        )
        for row in development_plan
    }


    if len(
        afino_contracts
    ) != 1:
        raise RuntimeError(
            "Frozen AFINO operational contract is not unique"
        )


    (
        afino_version,
        afino_commit,
        cutoff,
    ) = next(
        iter(
            afino_contracts
        )
    )


    if float(
        cutoff
    ) != 0.025:
        raise RuntimeError(
            "Low-frequency cutoff changed"
        )


    payload_by_sid = {}


    for row in payload_rows:

        sid = row[
            "simulation_unit_id"
        ]

        if sid in payload_by_sid:
            raise RuntimeError(
                "Duplicate payload simulation_unit_id"
            )

        if (
            row[
                "materialization_status"
            ]
            != "MATERIALIZED"
        ):
            raise RuntimeError(
                "Non-materialized payload reached plan"
            )

        payload_by_sid[
            sid
        ] = row


    candidates = []


    # Preserve the already-frozen HELDOUT manifest ordering.
    for row in series_rows:

        if (
            row[
                "evidence_plane"
            ]
            !=
            "SYNTHETIC_GROUND_TRUTH_CLASSIFICATION"
        ):
            continue

        if (
            row[
                "gap_quality_regime"
            ]
            !=
            "CONTIGUOUS_ALL_GOOD"
        ):
            raise RuntimeError(
                "Primary row not CONTIGUOUS_ALL_GOOD"
            )

        if (
            row[
                "input_state"
            ]
            !=
            "ELIGIBLE_FOR_AFINO"
        ):
            continue

        if (
            row[
                "materialization_status"
            ]
            !=
            "MATERIALIZED"
        ):
            raise RuntimeError(
                "Eligible primary not materialized"
            )

        sid = row[
            "simulation_unit_id"
        ]

        payload = (
            payload_by_sid.get(
                sid
            )
        )

        if payload is None:
            raise RuntimeError(
                "Eligible primary lacks payload"
            )

        if (
            payload[
                "background_realization_id"
            ]
            !=
            row[
                "background_realization_id"
            ]
        ):
            raise RuntimeError(
                "Series/payload background mismatch"
            )

        if (
            payload[
                "logical_payload_sha256"
            ]
            !=
            row[
                "logical_payload_sha256"
            ]
        ):
            raise RuntimeError(
                "Series/payload logical hash mismatch"
            )


        candidates.append(
            {
                "simulation_unit_id":
                    sid,

                "background_realization_id":
                    row[
                        "background_realization_id"
                    ],

                "payload_logical_sha256":
                    row[
                        "logical_payload_sha256"
                    ],
            }
        )


    if len(
        candidates
    ) != 3600:
        raise RuntimeError(
            "Eligible primary decisions != 3600"
        )


    if len({
        row[
            "simulation_unit_id"
        ]
        for row in candidates
    }) != 3600:
        raise RuntimeError(
            "Eligible primary IDs not unique"
        )


    decisions = []

    jobs = []


    for decision_order, row in enumerate(
        candidates,
        start=1,
    ):

        decision_id = (
            f"F3B5_HO_D{decision_order:04d}"
        )


        decisions.append(
            {
                "planned_decision_id":
                    decision_id,

                "decision_order":
                    decision_order,

                "decision_class":
                    "BASELINE",

                "simulation_unit_id":
                    row[
                        "simulation_unit_id"
                    ],

                "background_realization_id":
                    row[
                        "background_realization_id"
                    ],

                "external_optimizer_seed":
                    0,

                "payload_logical_sha256":
                    row[
                        "payload_logical_sha256"
                    ],

                "input_state":
                    "ELIGIBLE_FOR_AFINO",

                "gap_quality_regime":
                    "CONTIGUOUS_ALL_GOOD",

                "planned_model_calls":
                    3,

                "execution_status":
                    "NOT_EXECUTED",
            }
        )


        for model_id in (
            "M0",
            "M1",
            "M2",
        ):

            job_order = (
                len(jobs)
                + 1
            )

            jobs.append(
                {
                    "job_id":
                        f"F3B5_HO_J{job_order:05d}",

                    "job_order":
                        job_order,

                    "planned_decision_id":
                        decision_id,

                    "simulation_unit_id":
                        row[
                            "simulation_unit_id"
                        ],

                    "background_realization_id":
                        row[
                            "background_realization_id"
                        ],

                    "external_optimizer_seed":
                        0,

                    "model_id":
                        model_id,

                    "payload_logical_sha256":
                        row[
                            "payload_logical_sha256"
                        ],

                    "afino_version":
                        afino_version,

                    "afino_commit":
                        afino_commit,

                    "low_frequency_cutoff_hz":
                        cutoff,

                    "execution_status":
                        "NOT_EXECUTED",
                }
            )


    if (
        FORBIDDEN_OUTPUT_COLUMNS
        & set(
            DECISION_FIELDS
        )
    ):
        raise RuntimeError(
            "Forbidden column in decision grid"
        )


    if (
        FORBIDDEN_OUTPUT_COLUMNS
        & set(
            PLAN_FIELDS
        )
    ):
        raise RuntimeError(
            "Forbidden column in exact plan"
        )


    if len(decisions) != 3600:
        raise RuntimeError(
            "Decision count != 3600"
        )

    if len(jobs) != 10800:
        raise RuntimeError(
            "AFINO job count != 10800"
        )


    if {
        row[
            "external_optimizer_seed"
        ]
        for row in decisions
    } != {0}:
        raise RuntimeError(
            "Decision grid contains nonzero seed"
        )


    if {
        row[
            "external_optimizer_seed"
        ]
        for row in jobs
    } != {0}:
        raise RuntimeError(
            "Exact plan contains nonzero seed"
        )


    if {
        row[
            "decision_class"
        ]
        for row in decisions
    } != {"BASELINE"}:
        raise RuntimeError(
            "Stability decision leaked into HELDOUT"
        )


    if Counter(
        row[
            "model_id"
        ]
        for row in jobs
    ) != Counter(
        {
            "M0":
                3600,

            "M1":
                3600,

            "M2":
                3600,
        }
    ):
        raise RuntimeError(
            "Model-call topology mismatch"
        )


    if {
        row[
            "execution_status"
        ]
        for row in decisions
    } != {"NOT_EXECUTED"}:
        raise RuntimeError(
            "Decision already executed"
        )


    if {
        row[
            "execution_status"
        ]
        for row in jobs
    } != {"NOT_EXECUTED"}:
        raise RuntimeError(
            "AFINO plan already executed"
        )


    write_csv(
        decision_path,
        decisions,
        DECISION_FIELDS,
    )

    write_csv(
        plan_path,
        jobs,
        PLAN_FIELDS,
    )


    print(
        "F3B5_BLINDED_HELDOUT_PLAN_PASS"
    )

    print(
        "heldout_decisions_planned = 3600"
    )

    print(
        "heldout_model_calls_planned = 10800"
    )

    print(
        "M0_planned = 3600"
    )

    print(
        "M1_planned = 3600"
    )

    print(
        "M2_planned = 3600"
    )

    print(
        "external_optimizer_seed_set = 0"
    )

    print(
        "stability_extra_decisions = 0"
    )

    print(
        "truth_columns_in_decision_grid = 0"
    )

    print(
        "truth_columns_in_exact_plan = 0"
    )

    print(
        "execution_status = NOT_EXECUTED"
    )

    print(
        "afino_version =",
        afino_version,
    )

    print(
        "afino_commit =",
        afino_commit,
    )

    print(
        "low_frequency_cutoff_hz =",
        cutoff,
    )

    print(
        "decision_grid_sha256 =",
        sha(
            decision_path
        ),
    )

    print(
        "exact_afino_plan_sha256 =",
        sha(
            plan_path
        ),
    )

    print(
        "afino_imported = false"
    )

    print(
        "afino_executed = false"
    )

    print(
        "heldout_metrics_computed = false"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
