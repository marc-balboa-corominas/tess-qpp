from __future__ import annotations

import csv
import importlib.util
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pytest


REPO = Path(
    __file__
).resolve().parents[3]

SCRIPTS = (
    REPO
    / "workflows"
    / "phase3b"
    / "scripts"
)

ANALYSIS = (
    REPO
    / "workflows"
    / "phase3b"
    / "development"
    / "analysis"
)


def load_module(
    name: str,
    path: Path,
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
            f"Could not load {path}"
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    spec.loader.exec_module(
        module
    )

    return module


def read_csv(
    path: Path,
):

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        return list(
            csv.DictReader(f)
        )


@pytest.fixture(
    scope="module"
)
def frozen_rule():

    return load_module(
        "apply_f3b_frozen_rule",
        SCRIPTS
        / "apply_f3b_frozen_rule.py",
    )


@pytest.fixture(
    scope="module"
)
def develop():

    return load_module(
        "develop_f3b_candidate_rule",
        SCRIPTS
        / "develop_f3b_candidate_rule.py",
    )


@pytest.fixture(
    scope="module"
)
def validator():

    return load_module(
        "validate_f3b4_development_analysis",
        SCRIPTS
        / "validate_f3b4_development_analysis.py",
    )


def test_truth_join_exactness():

    truth = read_csv(
        ANALYSIS
        / "f3b4_truth_join_audit.csv"
    )

    evaluation = read_csv(
        ANALYSIS
        / "f3b4_baseline_evaluation.csv"
    )

    assert len(
        truth
    ) == 3600

    assert len(
        evaluation
    ) == 3600

    truth_ids = {
        row[
            "simulation_unit_id"
        ]
        for row in truth
    }

    evaluation_ids = {
        row[
            "simulation_unit_id"
        ]
        for row in evaluation
    }

    assert len(
        truth_ids
    ) == 3600

    assert (
        truth_ids
        == evaluation_ids
    )


def test_confusion_matrix_mapping(
    validator,
):

    assert (
        validator.classify(
            "SYNTHETIC_QPP_PRESENT",
            True,
        )
        == "TP"
    )

    assert (
        validator.classify(
            "SYNTHETIC_QPP_PRESENT",
            False,
        )
        == "FN"
    )

    assert (
        validator.classify(
            "SYNTHETIC_QPP_ABSENT",
            False,
        )
        == "TN"
    )

    assert (
        validator.classify(
            "SYNTHETIC_QPP_ABSENT",
            True,
        )
        == "FP"
    )


def test_wilson_intervals(
    validator,
):

    metric = validator.wilson(
        143,
        1800,
    )

    assert (
        metric[
            "numerator"
        ]
        == 143
    )

    assert (
        metric[
            "denominator"
        ]
        == 1800
    )

    assert metric[
        "point_estimate"
    ] == pytest.approx(
        0.07944444444444444,
        abs=1e-15,
    )

    assert (
        metric[
            "wilson_95_lower"
        ]
        < metric[
            "point_estimate"
        ]
        < metric[
            "wilson_95_upper"
        ]
    )


def test_inadmissibility_excluded_from_classifier_metrics():

    metrics = json.loads(
        (
            ANALYSIS
            / "f3b4_baseline_metrics.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        metrics[
            "population"
        ][
            "input_inadmissible_in_confusion_matrix"
        ]
        == 0
    )

    assert (
        metrics[
            "population"
        ][
            "numerical_stability_extra_in_confusion_matrix"
        ]
        == 0
    )


def test_end_to_end_classifier_separation():

    rows = read_csv(
        ANALYSIS
        / "f3b4_end_to_end_metrics.csv"
    )

    assert len(
        rows
    ) == 9

    assert {
        row[
            "scope_id"
        ]
        for row in rows
    } == {
        "PRIMARY_CLASSIFICATION_PLANE",
        "CHALLENGE_INPUT_ADMISSIBILITY_PLANE",
        "ALL_PLANNED_SYNTHETIC_DESIGN",
    }

    assert all(
        row[
            "classification_metric_synonym"
        ].lower()
        == "false"
        for row in rows
    )

    assert all(
        row[
            "input_inadmissible_recoded_as_FN_or_TN"
        ].lower()
        == "false"
        for row in rows
    )


def test_positive_and_null_selection_strata():

    rows = read_csv(
        ANALYSIS
        / "f3b4_selection_function.csv"
    )

    counts = Counter(
        row[
            "stratum_family"
        ]
        for row in rows
    )

    assert counts == {
        "POSITIVE_BASE":
            36,

        "POSITIVE_PERIOD_BIN":
            108,

        "NULL_POOLED":
            12,
    }

    null_rows = [
        row
        for row in rows
        if (
            row[
                "stratum_family"
            ]
            == "NULL_POOLED"
        )
    ]

    assert all(
        row[
            "null_qpp_fraction_pooled"
        ].lower()
        == "true"
        for row in null_rows
    )


def test_period_bin_boundaries():

    rows = [
        row
        for row in read_csv(
            ANALYSIS
            / "f3b4_selection_function.csv"
        )
        if (
            row[
                "stratum_family"
            ]
            == "POSITIVE_PERIOD_BIN"
        )
    ]

    observed = {
        (
            row[
                "period_bin_id"
            ],
            float(
                row[
                    "period_lower_s"
                ]
            ),
            float(
                row[
                    "period_upper_s"
                ]
            ),
            row[
                "period_lower_inclusive"
            ].lower(),
            row[
                "period_upper_inclusive"
            ].lower(),
        )
        for row in rows
    }

    assert observed == {
        (
            "P40_63",
            40.0,
            63.245553203367585,
            "true",
            "false",
        ),
        (
            "P63_106",
            63.245553203367585,
            105.83005244258362,
            "true",
            "false",
        ),
        (
            "P106_300",
            105.83005244258362,
            300.0,
            "true",
            "true",
        ),
    }


def test_structural_no_exposure():

    rows = read_csv(
        ANALYSIS
        / "f3b4_selection_function.csv"
    )

    structural = [
        row
        for row in rows
        if (
            row[
                "exposure_status"
            ]
            == "STRUCTURAL_NO_EXPOSURE"
        )
    ]

    assert len(
        structural
    ) == 9

    assert all(
        int(
            row[
                "n_samples"
            ]
        )
        == 15
        and
        row[
            "period_bin_id"
        ]
        == "P106_300"
        and
        int(
            row[
                "exposure_count"
            ]
        )
        == 0
        for row in structural
    )


def test_period_eligibility():

    rows = read_csv(
        ANALYSIS
        / "f3b4_period_recovery.csv"
    )

    summary = json.loads(
        (
            ANALYSIS
            / "f3b4_period_recovery_summary.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert len(
        rows
    ) == 143

    assert all(
        row[
            "classification_outcome"
        ]
        == "TP"
        for row in rows
    )

    assert (
        summary[
            "population"
        ][
            "eligible_positive_injections"
        ]
        == 1800
    )

    assert (
        summary[
            "population"
        ][
            "baseline_true_positives"
        ]
        == 143
    )

    assert (
        summary[
            "population"
        ][
            "baseline_false_negatives"
        ]
        == 1657
    )


def test_72_by_10_stability_identity():

    rows = read_csv(
        ANALYSIS
        / "f3b4_optimizer_stability.csv"
    )

    diagnostics = read_csv(
        ANALYSIS
        / "f3b4_seed_model_diagnostics.csv"
    )

    assert len(
        rows
    ) == 72

    assert sum(
        int(
            row[
                "seed_count"
            ]
        )
        for row in rows
    ) == 720

    assert all(
        int(
            row[
                "seed_count"
            ]
        )
        == 10
        for row in rows
    )

    assert all(
        int(
            row[
                "discordant_vs_seed0_count"
            ]
        )
        == 0
        for row in rows
    )

    assert len(
        diagnostics
    ) == 3


def test_threshold_axis_generation(
    develop,
):

    axis = (
        develop
        .build_threshold_axis(
            [
                1.0,
                3.0,
                3.0,
                float("nan"),
            ]
        )
    )

    assert np.array_equal(
        axis,
        np.asarray(
            [
                1.0,
                2.0,
                3.0,
                10.0,
            ],
            dtype=np.float64,
        ),
    )

    evaluation = read_csv(
        ANALYSIS
        / "f3b4_baseline_evaluation.csv"
    )

    axis01 = (
        develop
        .build_threshold_axis(
            float(
                row[
                    "delta_bic_0_1"
                ]
            )
            for row in evaluation
        )
    )

    axis21 = (
        develop
        .build_threshold_axis(
            float(
                row[
                    "delta_bic_2_1"
                ]
            )
            for row in evaluation
        )
    )

    assert axis01.size == 7200
    assert axis21.size == 7200


def test_strict_greater_than(
    frozen_rule,
):

    assert (
        frozen_rule
        .apply_frozen_rule(
            10.0,
            11.0,
        )
        is False
    )

    assert (
        frozen_rule
        .apply_frozen_rule(
            11.0,
            10.0,
        )
        is False
    )

    assert (
        frozen_rule
        .apply_frozen_rule(
            10.0000001,
            10.0000001,
        )
        is True
    )


def test_nonfinite_rejected(
    frozen_rule,
):

    with pytest.raises(
        ValueError
    ):

        frozen_rule.apply_frozen_rule(
            float("nan"),
            20.0,
        )


def test_all_candidate_optimization_order_stages(
    develop,
):

    base = {
        "balanced_accuracy":
            0.60,

        "min_sensitivity_specificity":
            0.50,

        "FPR":
            0.20,

        "l1_distance_to_10_10":
            5.0,

        "t01":
            1.0,

        "t21":
            2.0,
    }

    def better(
        **changes,
    ):

        row = dict(
            base
        )

        row.update(
            changes
        )

        return row

    # 1. maximize BA
    assert (
        develop.candidate_order_key(
            better(
                balanced_accuracy=0.61
            )
        )
        <
        develop.candidate_order_key(
            base
        )
    )

    # 2. maximize min(sensitivity, specificity)
    assert (
        develop.candidate_order_key(
            better(
                min_sensitivity_specificity=0.51
            )
        )
        <
        develop.candidate_order_key(
            base
        )
    )

    # 3. minimize FPR
    assert (
        develop.candidate_order_key(
            better(
                FPR=0.19
            )
        )
        <
        develop.candidate_order_key(
            base
        )
    )

    # 4. minimize L1 distance
    assert (
        develop.candidate_order_key(
            better(
                l1_distance_to_10_10=4.0
            )
        )
        <
        develop.candidate_order_key(
            base
        )
    )

    # 5. maximize t01
    assert (
        develop.candidate_order_key(
            better(
                t01=2.0
            )
        )
        <
        develop.candidate_order_key(
            base
        )
    )

    # 6. maximize t21
    assert (
        develop.candidate_order_key(
            better(
                t21=3.0
            )
        )
        <
        develop.candidate_order_key(
            base
        )
    )


def test_paired_background_bootstrap_fixed_rng_replay(
    validator,
):

    replay = validator.replay_bootstrap(
        REPO,
        replicate_limit=1,
    )

    assert (
        replay[
            "first_replicate_sha256"
        ]
        ==
        "6ef60371ee2655f876ed64f5b730236c237b580dc9ba7b0155e9200e21ce4b79"
    )

    assert (
        replay[
            "replicates_replayed"
        ]
        == 1
    )


def test_promotion_gate_pass(
    develop,
):

    promoted, criteria = (
        develop.promotion_gate(
            point_ba_improvement=0.03,
            lower_delta_ba=0.001,
            lower_delta_sensitivity=-0.01,
            lower_delta_specificity=-0.01,
        )
    )

    assert promoted is True

    assert criteria == (
        True,
        True,
        True,
        True,
    )


def test_promotion_gate_fail(
    develop,
):

    promoted, criteria = (
        develop.promotion_gate(
            point_ba_improvement=0.0955555555555555,
            lower_delta_ba=0.08611111111111114,
            lower_delta_sensitivity=0.5533333333333333,
            lower_delta_specificity=-0.3933333333333333,
        )
    )

    assert promoted is False

    assert criteria == (
        True,
        True,
        True,
        False,
    )


def test_no_runner_up_rescue():

    gate = json.loads(
        (
            ANALYSIS
            / "f3b4_candidate_rule_gate.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        gate[
            "promotion_result"
        ][
            "runner_up_rescue"
        ]
        == "FORBIDDEN"
    )

    assert (
        gate[
            "promotion_result"
        ][
            "alternate_candidate_search"
        ]
        == "FORBIDDEN"
    )


def test_baseline_only_final_freeze():

    freeze = json.loads(
        (
            ANALYSIS
            / "f3b4_final_rule_freeze.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        freeze[
            "freeze_state"
        ]
        == "FINAL_RULE_FREEZE_BASELINE_ONLY"
    )

    assert (
        freeze[
            "final_rule"
        ][
            "rule_type"
        ]
        == "AFINO_0_5_BASELINE"
    )

    assert (
        freeze[
            "final_rule"
        ][
            "t01"
        ]
        == 10.0
    )

    assert (
        freeze[
            "final_rule"
        ][
            "t21"
        ]
        == 10.0
    )


def test_candidate_final_freeze_branch(
    develop,
):

    branch = (
        develop.choose_final_rule(
            candidate_promoted=True,
            candidate_t01=-1.0,
            candidate_t21=2.0,
        )
    )

    assert (
        branch[
            "freeze_state"
        ]
        == "FINAL_RULE_FREEZE_CANDIDATE"
    )

    assert (
        branch[
            "rule_type"
        ]
        == "TWO_THRESHOLD_BIC_CONJUNCTION"
    )

    assert (
        branch[
            "t01"
        ]
        == -1.0
    )

    assert (
        branch[
            "t21"
        ]
        == 2.0
    )


def test_truth_and_nuisance_not_candidate_features():

    row = read_csv(
        ANALYSIS
        / "f3b4_candidate_rule_development.csv"
    )[0]

    assert json.loads(
        row[
            "allowed_features_json"
        ]
    ) == [
        "delta_BIC01",
        "delta_BIC21",
    ]

    forbidden = {
        "truth_state",
        "true_period_s",
        "qpp_fraction",
        "red_noise_alpha",
    }

    assert forbidden.isdisjoint(
        set(
            json.loads(
                row[
                    "allowed_features_json"
                ]
            )
        )
    )


def test_heldout_guard():

    heldout = (
        REPO
        / "data"
        / "interim"
        / "phase3b"
        / "heldout"
    )

    assert not heldout.exists()
