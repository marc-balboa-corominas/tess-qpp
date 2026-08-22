from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO = (
    Path(__file__)
    .resolve()
    .parents[3]
)

VALIDATOR_PATH = (
    REPO
    / "workflows/phase3b/scripts/"
      "validate_f3b5_heldout_materialization.py"
)


spec = (
    importlib.util
    .spec_from_file_location(
        "_f3b5_validator_under_test",
        VALIDATOR_PATH,
    )
)

if (
    spec is None
    or spec.loader is None
):
    raise RuntimeError(
        "Unable to load F3B.5 validator"
    )

validator = (
    importlib.util
    .module_from_spec(
        spec
    )
)

sys.modules[
    spec.name
] = validator

spec.loader.exec_module(
    validator
)


@pytest.fixture(
    scope="session"
)
def summary():

    return validator.validate(
        REPO
    )


def test_validation_status(
    summary,
):

    assert (
        summary[
            "status"
        ]
        ==
        "PHASE3B_HELDOUT_MATERIALIZATION_VALIDATION_PASS"
    )


def test_generator_and_binding_exact(
    summary,
):

    assert summary[
        "generator_sha_exact"
    ]

    assert summary[
        "binding_sha_exact"
    ]


def test_final_rule_was_frozen_pre_draw(
    summary,
):

    assert summary[
        "final_rule_freeze_before_draws"
    ]


def test_only_heldout_was_materialized(
    summary,
):

    assert summary[
        "only_heldout_materialized"
    ]

    assert (
        summary[
            "development_materializations"
        ]
        == 0
    )


def test_population_topology(
    summary,
):

    assert summary[
        "heldout_backgrounds"
    ] == 1800

    assert summary[
        "heldout_series"
    ] == 4320

    assert summary[
        "challenge_series"
    ] == 720


def test_primary_truth_topology(
    summary,
):

    assert summary[
        "primary_positive"
    ] == 1800

    assert summary[
        "primary_null"
    ] == 1800

    assert summary[
        "positive_total"
    ] == 2160

    assert summary[
        "null_total"
    ] == 2160


def test_positive_null_share_background(
    summary,
):

    assert summary[
        "positive_null_shared_background"
    ]


def test_period_support(
    summary,
):

    assert summary[
        "period_support_valid"
    ]

    assert summary[
        "minimum_three_cycles"
    ]


def test_zero_redraws(
    summary,
):

    assert summary[
        "redraws"
    ] == 0


def test_admissibility_topology(
    summary,
):

    assert summary[
        "primary_eligible"
    ] == 3600

    assert summary[
        "primary_inadmissible"
    ] == 0

    assert summary[
        "challenge_inadmissible"
    ] == 720


def test_challenge_mask_preserves_latent_flux(
    summary,
):

    assert (
        summary[
            "challenge_latent_mismatches"
        ]
        == 0
    )


def test_independent_roundtrip_exact(
    summary,
):

    assert (
        summary[
            "background_roundtrip_mismatches"
        ]
        == 0
    )

    assert (
        summary[
            "payload_roundtrip_mismatches"
        ]
        == 0
    )


def test_full_rematerialization_exact(
    summary,
):

    assert summary[
        "rematerialization_exact"
    ]

    assert (
        summary[
            "rematerialization_mismatches"
        ]
        == 0
    )


def test_seed0_without_stability_extras(
    summary,
):

    assert summary[
        "seed0_only"
    ]

    assert (
        summary[
            "stability_extra_decisions"
        ]
        == 0
    )


def test_blinded_execution_plan(
    summary,
):

    assert (
        summary[
            "truth_columns_in_execution_plan"
        ]
        == 0
    )

    assert summary[
        "future_jobs_not_executed"
    ]


def test_exact_model_call_topology(
    summary,
):

    assert summary[
        "heldout_decisions_planned"
    ] == 3600

    assert summary[
        "heldout_model_calls_planned"
    ] == 10800

    assert summary[
        "m0_planned"
    ] == 3600

    assert summary[
        "m1_planned"
    ] == 3600

    assert summary[
        "m2_planned"
    ] == 3600


def test_no_afino_metrics_or_tuning(
    summary,
):

    assert (
        summary[
            "heldout_afino_executed"
        ]
        is False
    )

    assert (
        summary[
            "heldout_metrics_computed"
        ]
        is False
    )

    assert (
        summary[
            "rule_tuning_performed"
        ]
        is False
    )


def test_no_third_materialization(
    summary,
):

    assert (
        summary[
            "third_materialization_performed"
        ]
        is False
    )
