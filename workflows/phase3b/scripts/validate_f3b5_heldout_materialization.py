from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np


EXPECTED_HEAD = (
    "5e9f62eacfd2c82cc4db5e3c3df48fc3bd6e7565"
)

EXPECTED_GENERATOR_SHA = (
    "d538d53c7845916e29c4dd351b85ae91076d5a342acb5619898788ef5d825d11"
)

EXPECTED_BINDING_SHA = (
    "b6519f84c0e6aa6b0c86cbd7a66dd79c1de1758e313d96ea4d750ebb212d9946"
)

EXPECTED_FREEZE_SHA = (
    "e2faffdbb15d6e0fec52ff166e81a2ed58f5665d7d3f9dc43cb8b78f5c0a198c"
)

EXPECTED_AUTH_SHA = (
    "9244c772a88e163d927098fdf0f9b1e44a8814fb7d1cbe1923a57452ed0a7925"
)

EXPECTED_HELDOUT_MATERIALIZER_SHA = (
    "6b1b883990bb1a9f59c40f550db4f0f8642f4b5f2be5983efeb22f1aa254c66d"
)

EXPECTED_PLAN_BUILDER_SHA = (
    "9a3c07ced1bdf6d6601904fbe2bb24b1faab6b3135093525aafe68df7e5e3c9b"
)

EXPECTED_REMAT_SHA = (
    "e1342d57b1c3d88d22ad656a5df059061657209e54a217286e58185521297f24"
)

EXPECTED_DECISION_SHA = (
    "09419a4d5d968d5305f262b5aefe28cd29bc01cdcf67b53d91e1732c0e15aa34"
)

EXPECTED_PLAN_SHA = (
    "0b59e2f4ab4e1f3a1064b2281a9a428b117a7b258102e237702deee86171f2f9"
)


EXPECTED_TABLE_HASHES = {
    "f3b5_heldout_background_manifest.csv":
        "ef76d7fd0646c20bf9466a32e74a3412ad63e203a3fa520322633507cca333e6",

    "f3b5_heldout_series_manifest.csv":
        "3b98e31137b3f1d3cc67c2a7eead70414879891556be16196f954e4682410336",

    "f3b5_heldout_truth_ledger.csv":
        "2270ef77926c6e95a8df97b292ba6ae0a64cb081e683a1e42cf238360232c708",

    "f3b5_heldout_admissibility.csv":
        "dfd79a20616f333f4e3f1cb0a0f0a03e46e537233554a956fa3547262af07ffe",

    "f3b5_heldout_payload_manifest.csv":
        "d20b0dac662cf809eb86d5e87d96f35e236b6ff2fbfb0fa86eeb4da8a49af8b4",
}


EXPECTED_ARRAY_HASHES = {
    "background_noise.npy":
        "26dc41dc0a280d92b45ed116f79060d547b7c1bc3d5673df6abb9def9bb8f794",

    "background_offsets.npy":
        "8e0f77105f1fd3a13580adcd2c4dcbf5b09de5e32dbfd906795014a9d8f0be2c",

    "latent_flux.npy":
        "5cdaff08c31f10c717de4b55f148c8af2e2333711fdaf0715e213403d8ce9758",

    "latent_offsets.npy":
        "aba31f5bf921b48a046037b8ab09474edcd3136c2b405ed84b0f6e011867dd5c",

    "retained_time_s.npy":
        "573527515b71d29eadfe20d0b6eb87296f38f8ec188419a1a4b5fc95dab1d050",

    "retained_flux.npy":
        "f8e8fa86f9a307ef78bd34b153752078110b9461d8d172b7ec0d3e9425edebc6",

    "retained_native_index.npy":
        "c0b19f204fecad603c0d8b63bfe0a0643cb57ea74694d4f8849e443786072e4c",

    "retained_offsets.npy":
        "5fd86ec64fe858b3ed665f11a06f4ca7f054e83c51c6e21cb3339693cb99da64",
}


FORBIDDEN_PLAN_FIELDS = {
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


def sha(
    path: Path,
) -> str:

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def read_csv(
    path: Path,
) -> tuple[
    list[dict[str, str]],
    list[str],
]:

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        return (
            list(reader),
            list(
                reader.fieldnames
                or []
            ),
        )


def load_module(
    path: Path,
    name: str,
):

    spec = (
        importlib.util
        .spec_from_file_location(
            name,
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            f"Unable to import {path}"
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    sys.modules[
        name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def afino_loaded() -> bool:

    return any(
        name == "afino"
        or name.startswith(
            "afino."
        )
        for name
        in sys.modules
    )


def assert_hash(
    path: Path,
    expected: str,
) -> None:

    if not path.is_file():
        raise RuntimeError(
            f"Missing frozen artifact: {path}"
        )

    observed = sha(
        path
    )

    if observed != expected:

        raise RuntimeError(
            f"SHA mismatch for {path}\n"
            f"observed={observed}\n"
            f"expected={expected}"
        )


def validate(
    repo: Path,
) -> dict[str, Any]:

    repo = repo.resolve()


    # --------------------------------------------------------
    # Environment / immutable frontier
    # --------------------------------------------------------

    if (
        sys.version.split()[0]
        != "3.13.13"
    ):
        raise RuntimeError(
            "Python version != 3.13.13"
        )

    if (
        np.__version__
        != "2.3.5"
    ):
        raise RuntimeError(
            "NumPy version != 2.3.5"
        )

    if (
        sys.byteorder
        != "little"
    ):
        raise RuntimeError(
            "byteorder != little"
        )


    head = subprocess.check_output(
        [
            "git",
            "rev-parse",
            "HEAD",
        ],
        cwd=repo,
        text=True,
    ).strip().lower()


    if head != EXPECTED_HEAD:
        raise RuntimeError(
            "Unexpected F3B.5 authorization HEAD"
        )


    generator = (
        repo
        / "workflows/phase3b/scripts/"
          "f3b_synthetic_generator.py"
    )

    binding = (
        repo
        / "workflows/phase3b/development/config/"
          "f3b2_generator_implementation_binding.json"
    )

    freeze_path = (
        repo
        / "workflows/phase3b/development/analysis/"
          "f3b4_final_rule_freeze.json"
    )

    auth_path = (
        repo
        / "workflows/phase3b/heldout/materialization/config/"
          "f3b5_heldout_materialization_authorization.json"
    )

    heldout_materializer = (
        repo
        / "workflows/phase3b/scripts/"
          "materialize_f3b_heldout.py"
    )

    plan_builder = (
        repo
        / "workflows/phase3b/scripts/"
          "build_f3b5_heldout_plan.py"
    )

    remat_path = (
        repo
        / "workflows/phase3b/heldout/materialization/"
          "evidence/reports/"
          "f3b5_heldout_rematerialization_audit.json"
    )

    boundary_path = (
        repo
        / "workflows/phase3b/heldout/materialization/"
          "evidence/reports/"
          "f3b5_single_use_boundary_audit.json"
    )

    tables = (
        repo
        / "workflows/phase3b/heldout/materialization/"
          "evidence/tables"
    )

    arrays = (
        repo
        / "data/interim/phase3b/f3b5_heldout"
    )

    split_path = (
        repo
        / "workflows/phase3b/design/"
          "f3b1_split_registry.csv"
    )


    for path, expected in (
        (
            generator,
            EXPECTED_GENERATOR_SHA,
        ),
        (
            binding,
            EXPECTED_BINDING_SHA,
        ),
        (
            freeze_path,
            EXPECTED_FREEZE_SHA,
        ),
        (
            auth_path,
            EXPECTED_AUTH_SHA,
        ),
        (
            heldout_materializer,
            EXPECTED_HELDOUT_MATERIALIZER_SHA,
        ),
        (
            plan_builder,
            EXPECTED_PLAN_BUILDER_SHA,
        ),
        (
            remat_path,
            EXPECTED_REMAT_SHA,
        ),
    ):

        assert_hash(
            path,
            expected,
        )


    decision_path = (
        tables
        / "f3b5_heldout_decision_grid.csv"
    )

    plan_path = (
        tables
        / "f3b5_heldout_exact_afino_plan.csv"
    )


    assert_hash(
        decision_path,
        EXPECTED_DECISION_SHA,
    )

    assert_hash(
        plan_path,
        EXPECTED_PLAN_SHA,
    )


    for filename, expected in (
        EXPECTED_TABLE_HASHES.items()
    ):

        assert_hash(
            tables
            / filename,
            expected,
        )


    for filename, expected in (
        EXPECTED_ARRAY_HASHES.items()
    ):

        assert_hash(
            arrays
            / filename,
            expected,
        )


    # --------------------------------------------------------
    # FINAL_RULE_FREEZE existed before first draw
    # --------------------------------------------------------

    freeze = json.loads(
        freeze_path.read_text(
            encoding="utf-8"
        )
    )

    rule = freeze[
        "final_rule"
    ]


    if (
        freeze[
            "freeze_state"
        ]
        !=
        "FINAL_RULE_FREEZE_BASELINE_ONLY"
        or
        rule[
            "rule_type"
        ]
        != "AFINO_0_5_BASELINE"
        or
        float(
            rule[
                "t01"
            ]
        )
        != 10.0
        or
        float(
            rule[
                "t21"
            ]
        )
        != 10.0
        or
        rule[
            "candidate_rule_promoted"
        ]
        is not False
    ):
        raise RuntimeError(
            "Frozen final-rule state changed"
        )


    if (
        rule[
            "threshold_mutation_after_freeze"
        ]
        != "FORBIDDEN"
        or
        rule[
            "runner_up_rescue"
        ]
        != "FORBIDDEN"
        or
        rule[
            "alternate_candidate_search"
        ]
        != "FORBIDDEN"
    ):
        raise RuntimeError(
            "Final-rule post-freeze firewall changed"
        )


    auth = json.loads(
        auth_path.read_text(
            encoding="utf-8"
        )
    )


    if (
        auth[
            "status"
        ]
        !=
        "AUTHORIZED_FOR_MATERIALIZATION_ONLY"
    ):
        raise RuntimeError(
            "Materialization authorization changed"
        )


    pre_draw = auth[
        "pre_draw_boundary"
    ]


    if (
        int(
            pre_draw[
                "stochastic_draws_before_authorization"
            ]
        )
        != 0
        or
        pre_draw[
            "generator_imported_before_authorization"
        ]
        is not False
        or
        pre_draw[
            "afino_executed_before_authorization"
        ]
        is not False
        or
        pre_draw[
            "heldout_materialization_performed_before_authorization"
        ]
        is not False
    ):
        raise RuntimeError(
            "Pre-draw authorization boundary changed"
        )


    # --------------------------------------------------------
    # Split registry and materialization isolation
    # --------------------------------------------------------

    registry, _ = read_csv(
        split_path
    )


    if len(
        registry
    ) != 8640:
        raise RuntimeError(
            "Split registry rows != 8640"
        )


    dev_registry = [
        row
        for row in registry
        if row[
            "split"
        ]
        == "DEVELOPMENT"
    ]

    heldout_registry = [
        row
        for row in registry
        if row[
            "split"
        ]
        == "HELDOUT"
    ]


    if (
        len(
            dev_registry
        )
        != 4320
        or
        len(
            heldout_registry
        )
        != 4320
    ):
        raise RuntimeError(
            "Split registry topology mismatch"
        )


    heldout_ids = {
        row[
            "simulation_unit_id"
        ]
        for row in heldout_registry
    }

    development_ids = {
        row[
            "simulation_unit_id"
        ]
        for row in dev_registry
    }


    background_rows, _ = read_csv(
        tables
        / "f3b5_heldout_background_manifest.csv"
    )

    series_rows, _ = read_csv(
        tables
        / "f3b5_heldout_series_manifest.csv"
    )

    truth_rows, _ = read_csv(
        tables
        / "f3b5_heldout_truth_ledger.csv"
    )

    admissibility_rows, _ = read_csv(
        tables
        / "f3b5_heldout_admissibility.csv"
    )

    payload_rows, _ = read_csv(
        tables
        / "f3b5_heldout_payload_manifest.csv"
    )


    if len(
        background_rows
    ) != 1800:
        raise RuntimeError(
            "HELDOUT backgrounds != 1800"
        )


    for rows, label in (
        (
            series_rows,
            "series",
        ),
        (
            truth_rows,
            "truth",
        ),
        (
            admissibility_rows,
            "admissibility",
        ),
        (
            payload_rows,
            "payload",
        ),
    ):

        if len(
            rows
        ) != 4320:
            raise RuntimeError(
                f"HELDOUT {label} rows != 4320"
            )


    if {
        row[
            "split"
        ]
        for row
        in background_rows
    } != {"HELDOUT"}:
        raise RuntimeError(
            "Non-HELDOUT background materialized"
        )


    if {
        row[
            "split"
        ]
        for row
        in series_rows
    } != {"HELDOUT"}:
        raise RuntimeError(
            "Non-HELDOUT series materialized"
        )


    materialized_ids = {
        row[
            "simulation_unit_id"
        ]
        for row
        in series_rows
    }


    if (
        materialized_ids
        != heldout_ids
    ):
        raise RuntimeError(
            "Materialized IDs are not exactly HELDOUT IDs"
        )


    if (
        materialized_ids
        & development_ids
    ):
        raise RuntimeError(
            "DEVELOPMENT row materialized into F3B.5"
        )


    for rows, label in (
        (
            truth_rows,
            "truth ledger",
        ),
        (
            admissibility_rows,
            "admissibility",
        ),
        (
            payload_rows,
            "payload manifest",
        ),
    ):

        ids = {
            row[
                "simulation_unit_id"
            ]
            for row
            in rows
        }

        if ids != heldout_ids:
            raise RuntimeError(
                f"{label} does not cover exact HELDOUT IDs"
            )


    # --------------------------------------------------------
    # Primary / challenge topology
    # --------------------------------------------------------

    primary = [
        row
        for row in series_rows
        if row[
            "evidence_plane"
        ]
        ==
        "SYNTHETIC_GROUND_TRUTH_CLASSIFICATION"
    ]

    challenges = [
        row
        for row in series_rows
        if row[
            "evidence_plane"
        ]
        ==
        "INPUT_ADMISSIBILITY"
    ]


    if (
        len(
            primary
        )
        != 3600
        or
        len(
            challenges
        )
        != 720
    ):
        raise RuntimeError(
            "Primary/challenge topology mismatch"
        )


    primary_truth_counts = Counter(
        row[
            "truth_state"
        ]
        for row in primary
    )


    if primary_truth_counts != Counter(
        {
            "SYNTHETIC_QPP_PRESENT":
                1800,

            "SYNTHETIC_QPP_ABSENT":
                1800,
        }
    ):
        raise RuntimeError(
            "Primary positive/null topology mismatch"
        )


    total_truth_counts = Counter(
        row[
            "truth_state"
        ]
        for row in series_rows
    )


    if total_truth_counts != Counter(
        {
            "SYNTHETIC_QPP_PRESENT":
                2160,

            "SYNTHETIC_QPP_ABSENT":
                2160,
        }
    ):
        raise RuntimeError(
            "Total positive/null topology mismatch"
        )


    challenge_truth = Counter(
        row[
            "truth_state"
        ]
        for row in challenges
    )


    if challenge_truth != Counter(
        {
            "SYNTHETIC_QPP_PRESENT":
                360,

            "SYNTHETIC_QPP_ABSENT":
                360,
        }
    ):
        raise RuntimeError(
            "Challenge truth topology mismatch"
        )


    # --------------------------------------------------------
    # Positive/null shared backgrounds
    # --------------------------------------------------------

    primary_by_bg: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(
        list
    )


    for row in primary:

        primary_by_bg[
            row[
                "background_realization_id"
            ]
        ].append(
            row
        )


    if len(
        primary_by_bg
    ) != 1800:
        raise RuntimeError(
            "Primary background count != 1800"
        )


    for bg, rows in (
        primary_by_bg.items()
    ):

        if len(
            rows
        ) != 2:
            raise RuntimeError(
                f"Primary background does not contain pair: {bg}"
            )

        if {
            row[
                "truth_state"
            ]
            for row in rows
        } != {
            "SYNTHETIC_QPP_PRESENT",
            "SYNTHETIC_QPP_ABSENT",
        }:
            raise RuntimeError(
                f"Positive/null pair missing on background {bg}"
            )


    group_sizes = Counter(
        Counter(
            row[
                "background_realization_id"
            ]
            for row
            in series_rows
        ).values()
    )


    if group_sizes != Counter(
        {
            2:
                1620,

            6:
                180,
        }
    ):
        raise RuntimeError(
            "Shared-background group-size topology mismatch"
        )


    # --------------------------------------------------------
    # Period support, cycles and redraws
    # --------------------------------------------------------

    redraws = 0


    for row in background_rows:

        if (
            row[
                "generation_status"
            ]
            != "MATERIALIZED"
        ):
            raise RuntimeError(
                "Background generation failure present"
            )

        redraws += int(
            row[
                "redraw_count"
            ]
        )

        period = float(
            row[
                "true_period_s"
            ]
        )

        upper = float(
            row[
                "period_upper_bound_s"
            ]
        )

        cycles = float(
            row[
                "cycles_in_window"
            ]
        )


        if not (
            math.isfinite(
                period
            )
            and
            math.isfinite(
                upper
            )
            and
            math.isfinite(
                cycles
            )
        ):
            raise RuntimeError(
                "Non-finite period-support value"
            )


        if (
            period <= 0.0
            or
            upper <= 0.0
            or
            period > upper
        ):
            raise RuntimeError(
                "Frozen period outside support"
            )


        if cycles < 3.0:
            raise RuntimeError(
                "Frozen period violates >=3-cycle contract"
            )


    if redraws != 0:
        raise RuntimeError(
            "HELDOUT redraw_count > 0"
        )


    # --------------------------------------------------------
    # Input admissibility
    # --------------------------------------------------------

    input_counts = Counter(
        row[
            "input_state"
        ]
        for row in series_rows
    )


    if input_counts != Counter(
        {
            "ELIGIBLE_FOR_AFINO":
                3600,

            "INPUT_INADMISSIBLE":
                720,
        }
    ):
        raise RuntimeError(
            "HELDOUT input-state topology mismatch"
        )


    if {
        row[
            "input_state"
        ]
        for row in primary
    } != {
        "ELIGIBLE_FOR_AFINO"
    }:
        raise RuntimeError(
            "Primary HELDOUT contains inadmissible input"
        )


    if {
        row[
            "input_state"
        ]
        for row in challenges
    } != {
        "INPUT_INADMISSIBLE"
    }:
        raise RuntimeError(
            "Challenge HELDOUT contains eligible input"
        )


    reason_counts: Counter[str] = (
        Counter()
    )


    for row in admissibility_rows:

        reasons = row[
            "all_triggered_reasons"
        ].strip()

        if not reasons:
            continue

        for reason in (
            reasons.split("|")
        ):

            if reason:
                reason_counts[
                    reason
                ] += 1


    expected_reasons = Counter(
        {
            "IRREGULAR_SAMPLING":
                720,

            "PEAK_REMOVED_BY_QUALITY":
                360,

            "TOO_FEW_CADENCES":
                180,
        }
    )


    if reason_counts != expected_reasons:
        raise RuntimeError(
            "Frozen inadmissibility-reason counts changed"
        )


    # --------------------------------------------------------
    # Independent physical roundtrip / payload integrity
    # --------------------------------------------------------

    if afino_loaded():
        raise RuntimeError(
            "AFINO imported before payload validation"
        )


    f3b = load_module(
        generator,
        "_f3b5_validator_frozen_generator",
    )


    if afino_loaded():
        raise RuntimeError(
            "AFINO imported with frozen generator"
        )


    background_noise = np.load(
        arrays
        / "background_noise.npy",
        mmap_mode="r",
        allow_pickle=False,
    )

    background_offsets = np.load(
        arrays
        / "background_offsets.npy",
        mmap_mode="r",
        allow_pickle=False,
    )

    latent_flux = np.load(
        arrays
        / "latent_flux.npy",
        mmap_mode="r",
        allow_pickle=False,
    )

    latent_offsets = np.load(
        arrays
        / "latent_offsets.npy",
        mmap_mode="r",
        allow_pickle=False,
    )

    retained_time = np.load(
        arrays
        / "retained_time_s.npy",
        mmap_mode="r",
        allow_pickle=False,
    )

    retained_flux = np.load(
        arrays
        / "retained_flux.npy",
        mmap_mode="r",
        allow_pickle=False,
    )

    retained_index = np.load(
        arrays
        / "retained_native_index.npy",
        mmap_mode="r",
        allow_pickle=False,
    )

    retained_offsets = np.load(
        arrays
        / "retained_offsets.npy",
        mmap_mode="r",
        allow_pickle=False,
    )


    if len(
        background_offsets
    ) != 1801:
        raise RuntimeError(
            "background_offsets length != 1801"
        )


    if (
        len(
            latent_offsets
        )
        != 4321
        or
        len(
            retained_offsets
        )
        != 4321
    ):
        raise RuntimeError(
            "Series offset-vector topology mismatch"
        )


    background_roundtrip_mismatches = 0


    for index, row in enumerate(
        background_rows
    ):

        start = int(
            row[
                "noise_offset"
            ]
        )

        length = int(
            row[
                "noise_length"
            ]
        )

        end = (
            start
            + length
        )


        if (
            int(
                background_offsets[
                    index
                ]
            )
            != start
            or
            int(
                background_offsets[
                    index + 1
                ]
            )
            != end
        ):
            background_roundtrip_mismatches += 1
            continue


        noise = (
            background_noise[
                start:end
            ]
        )


        if (
            f3b
            .canonical_float64_sha256(
                noise
            )
            !=
            row[
                "noise_sha256"
            ]
        ):
            background_roundtrip_mismatches += 1


    payload_by_sid = {
        row[
            "simulation_unit_id"
        ]:
            row
        for row in payload_rows
    }


    payload_roundtrip_mismatches = 0


    for index, row in enumerate(
        series_rows
    ):

        l0 = int(
            row[
                "latent_offset"
            ]
        )

        llen = int(
            row[
                "latent_length"
            ]
        )

        l1 = (
            l0
            + llen
        )

        r0 = int(
            row[
                "retained_offset"
            ]
        )

        rlen = int(
            row[
                "retained_length"
            ]
        )

        r1 = (
            r0
            + rlen
        )


        if (
            int(
                latent_offsets[
                    index
                ]
            )
            != l0
            or
            int(
                latent_offsets[
                    index + 1
                ]
            )
            != l1
            or
            int(
                retained_offsets[
                    index
                ]
            )
            != r0
            or
            int(
                retained_offsets[
                    index + 1
                ]
            )
            != r1
        ):
            payload_roundtrip_mismatches += 1
            continue


        latent = (
            latent_flux[
                l0:l1
            ]
        )

        rt = (
            retained_time[
                r0:r1
            ]
        )

        rf = (
            retained_flux[
                r0:r1
            ]
        )

        ri = (
            retained_index[
                r0:r1
            ]
        )


        checks = [
            (
                f3b
                .canonical_float64_sha256(
                    latent
                )
                ==
                row[
                    "latent_flux_sha256"
                ]
            ),
            (
                f3b
                .canonical_float64_sha256(
                    rt
                )
                ==
                row[
                    "retained_time_sha256"
                ]
            ),
            (
                f3b
                .canonical_float64_sha256(
                    rf
                )
                ==
                row[
                    "retained_flux_sha256"
                ]
            ),
            (
                f3b
                .canonical_int64_sha256(
                    ri
                )
                ==
                row[
                    "retained_native_index_sha256"
                ]
            ),
            (
                f3b
                .logical_payload_sha256(
                    row[
                        "simulation_unit_id"
                    ],
                    rt,
                    rf,
                    ri,
                )
                ==
                row[
                    "logical_payload_sha256"
                ]
            ),
        ]


        payload = payload_by_sid[
            row[
                "simulation_unit_id"
            ]
        ]


        checks.extend(
            [
                (
                    payload[
                        "latent_flux_sha256"
                    ]
                    ==
                    row[
                        "latent_flux_sha256"
                    ]
                ),
                (
                    payload[
                        "retained_time_sha256"
                    ]
                    ==
                    row[
                        "retained_time_sha256"
                    ]
                ),
                (
                    payload[
                        "retained_flux_sha256"
                    ]
                    ==
                    row[
                        "retained_flux_sha256"
                    ]
                ),
                (
                    payload[
                        "retained_native_index_sha256"
                    ]
                    ==
                    row[
                        "retained_native_index_sha256"
                    ]
                ),
                (
                    payload[
                        "logical_payload_sha256"
                    ]
                    ==
                    row[
                        "logical_payload_sha256"
                    ]
                ),
            ]
        )


        if not all(
            checks
        ):
            payload_roundtrip_mismatches += 1


    if (
        background_roundtrip_mismatches
        != 0
        or
        payload_roundtrip_mismatches
        != 0
    ):
        raise RuntimeError(
            "Independent physical roundtrip mismatch"
        )


    # --------------------------------------------------------
    # Challenge masking must not modify latent truth
    # --------------------------------------------------------

    primary_latent = {
        (
            row[
                "background_realization_id"
            ],
            row[
                "truth_state"
            ],
        ):
            row[
                "latent_flux_sha256"
            ]
        for row in primary
    }


    challenge_latent_mismatches = 0


    for row in challenges:

        key = (
            row[
                "background_realization_id"
            ],
            row[
                "truth_state"
            ],
        )

        if (
            primary_latent.get(
                key
            )
            !=
            row[
                "latent_flux_sha256"
            ]
        ):
            challenge_latent_mismatches += 1


    if challenge_latent_mismatches != 0:
        raise RuntimeError(
            "Challenge quality mask changed latent flux"
        )


    # --------------------------------------------------------
    # Full deterministic rematerialization
    # --------------------------------------------------------

    remat = json.loads(
        remat_path.read_text(
            encoding="utf-8"
        )
    )


    if (
        remat[
            "status"
        ]
        !=
        "F3B5_HELDOUT_REMATERIALIZATION_EXACT"
        or
        remat[
            "persistent_first_materialization_rerun"
        ]
        is not False
        or
        remat[
            "temporary_second_materialization_performed"
        ]
        is not True
    ):
        raise RuntimeError(
            "Full-rematerialization audit state mismatch"
        )


    if any(
        int(
            value
        )
        != 0
        for value
        in remat[
            "comparison"
        ].values()
    ):
        raise RuntimeError(
            "Full rematerialization contains mismatch"
        )


    if (
        int(
            remat[
                "second_materialization_rng_counts"
            ][
                "redraw_total"
            ]
        )
        != 0
    ):
        raise RuntimeError(
            "Second materialization redraw_count > 0"
        )


    if (
        remat[
            "persistent_table_sha256"
        ]
        !=
        remat[
            "second_table_sha256"
        ]
    ):
        raise RuntimeError(
            "Persistent/second table SHA maps differ"
        )


    if (
        remat[
            "persistent_array_sha256"
        ]
        !=
        remat[
            "second_array_sha256"
        ]
    ):
        raise RuntimeError(
            "Persistent/second array SHA maps differ"
        )


    # --------------------------------------------------------
    # Blinded seed0 future plan
    # --------------------------------------------------------

    decisions, decision_fields = (
        read_csv(
            decision_path
        )
    )

    plan, plan_fields = (
        read_csv(
            plan_path
        )
    )


    if len(
        decisions
    ) != 3600:
        raise RuntimeError(
            "HELDOUT decisions != 3600"
        )


    if len(
        plan
    ) != 10800:
        raise RuntimeError(
            "HELDOUT model jobs != 10800"
        )


    if (
        FORBIDDEN_PLAN_FIELDS
        & set(
            decision_fields
        )
    ):
        raise RuntimeError(
            "Truth/outcome field in HELDOUT decision grid"
        )


    if (
        FORBIDDEN_PLAN_FIELDS
        & set(
            plan_fields
        )
    ):
        raise RuntimeError(
            "Truth/outcome field in HELDOUT exact AFINO plan"
        )


    if {
        row[
            "external_optimizer_seed"
        ]
        for row in decisions
    } != {"0"}:
        raise RuntimeError(
            "HELDOUT decisions not seed0-only"
        )


    if {
        row[
            "external_optimizer_seed"
        ]
        for row in plan
    } != {"0"}:
        raise RuntimeError(
            "HELDOUT jobs not seed0-only"
        )


    if {
        row[
            "decision_class"
        ]
        for row in decisions
    } != {"BASELINE"}:
        raise RuntimeError(
            "Stability-extra decision exists in HELDOUT"
        )


    model_counts = Counter(
        row[
            "model_id"
        ]
        for row in plan
    )


    if model_counts != Counter(
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
            "HELDOUT model topology mismatch"
        )


    if {
        row[
            "execution_status"
        ]
        for row in decisions
    } != {
        "NOT_EXECUTED"
    }:
        raise RuntimeError(
            "HELDOUT decision already executed"
        )


    if {
        row[
            "execution_status"
        ]
        for row in plan
    } != {
        "NOT_EXECUTED"
    }:
        raise RuntimeError(
            "HELDOUT AFINO job already executed"
        )


    jobs_per_decision = Counter(
        row[
            "planned_decision_id"
        ]
        for row in plan
    )


    if set(
        jobs_per_decision.values()
    ) != {3}:
        raise RuntimeError(
            "HELDOUT decision does not map to exactly three models"
        )


    # --------------------------------------------------------
    # Single-use boundary
    # --------------------------------------------------------

    if not boundary_path.is_file():
        raise RuntimeError(
            "Single-use boundary audit missing"
        )


    boundary = json.loads(
        boundary_path.read_text(
            encoding="utf-8"
        )
    )


    required_false = (
        "heldout_afino_executed",
        "heldout_rule_applied",
        "heldout_metrics_computed",
        "heldout_outcomes_inspected",
        "candidate_search_performed",
        "thresholds_modified",
        "rule_refitted",
        "development_reopened_for_tuning",
    )


    if (
        boundary[
            "heldout_materialization_performed"
        ]
        is not True
        or
        boundary[
            "heldout_stochastic_truth_generated"
        ]
        is not True
    ):
        raise RuntimeError(
            "Single-use materialization boundary flags invalid"
        )


    for key in required_false:

        if (
            boundary[
                key
            ]
            is not False
        ):
            raise RuntimeError(
                f"Single-use boundary violated: {key}"
            )


    # --------------------------------------------------------
    # No AFINO / metrics / tuning artifacts
    # --------------------------------------------------------

    forbidden_dirs = [
        repo
        / "workflows/phase3b/heldout/execution",

        repo
        / "workflows/phase3b/heldout/analysis",

        repo
        / "data/interim/phase3b/heldout",
    ]


    for path in forbidden_dirs:

        if path.exists():
            raise RuntimeError(
                f"Premature HELDOUT downstream state exists: {path}"
            )


    if afino_loaded():
        raise RuntimeError(
            "AFINO imported during F3B.5 closure validation"
        )


    summary = {
        "status":
            "PHASE3B_HELDOUT_MATERIALIZATION_VALIDATION_PASS",

        "generator_sha_exact":
            True,

        "binding_sha_exact":
            True,

        "final_rule_freeze_before_draws":
            True,

        "only_heldout_materialized":
            True,

        "development_materializations":
            0,

        "heldout_backgrounds":
            1800,

        "heldout_series":
            4320,

        "primary_positive":
            1800,

        "primary_null":
            1800,

        "challenge_series":
            720,

        "positive_total":
            2160,

        "null_total":
            2160,

        "positive_null_shared_background":
            True,

        "period_support_valid":
            True,

        "minimum_three_cycles":
            True,

        "redraws":
            0,

        "primary_eligible":
            3600,

        "primary_inadmissible":
            0,

        "challenge_inadmissible":
            720,

        "inadmissibility_reason_counts":
            dict(
                sorted(
                    reason_counts.items()
                )
            ),

        "background_roundtrip_mismatches":
            0,

        "payload_roundtrip_mismatches":
            0,

        "challenge_latent_mismatches":
            0,

        "rematerialization_exact":
            True,

        "rematerialization_mismatches":
            0,

        "heldout_decisions_planned":
            3600,

        "heldout_model_calls_planned":
            10800,

        "m0_planned":
            3600,

        "m1_planned":
            3600,

        "m2_planned":
            3600,

        "seed0_only":
            True,

        "stability_extra_decisions":
            0,

        "truth_columns_in_execution_plan":
            0,

        "future_jobs_not_executed":
            True,

        "heldout_afino_executed":
            False,

        "heldout_metrics_computed":
            False,

        "rule_tuning_performed":
            False,

        "third_materialization_performed":
            False,
    }


    return summary


def main() -> int:

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo-root",
        default=".",
    )

    args = parser.parse_args()

    summary = validate(
        Path(
            args.repo_root
        )
    )


    print(
        "PHASE3B_HELDOUT_MATERIALIZATION_VALIDATION_PASS"
    )

    for key in (
        "heldout_backgrounds",
        "heldout_series",
        "primary_positive",
        "primary_null",
        "challenge_series",
        "positive_total",
        "null_total",
        "redraws",
        "primary_eligible",
        "primary_inadmissible",
        "challenge_inadmissible",
        "background_roundtrip_mismatches",
        "payload_roundtrip_mismatches",
        "challenge_latent_mismatches",
        "rematerialization_mismatches",
        "heldout_decisions_planned",
        "heldout_model_calls_planned",
        "m0_planned",
        "m1_planned",
        "m2_planned",
    ):

        print(
            key,
            "=",
            summary[
                key
            ],
        )


    print(
        "inadmissibility_reason_counts =",
        json.dumps(
            summary[
                "inadmissibility_reason_counts"
            ],
            sort_keys=True,
        ),
    )

    print(
        "seed0_only = true"
    )

    print(
        "stability_extra_decisions = 0"
    )

    print(
        "truth_columns_in_execution_plan = 0"
    )

    print(
        "all_future_jobs = NOT_EXECUTED"
    )

    print(
        "heldout_afino_executed = false"
    )

    print(
        "heldout_rule_applied = false"
    )

    print(
        "heldout_metrics_computed = false"
    )

    print(
        "rule_tuning_performed = false"
    )

    print(
        "third_materialization_performed = false"
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
