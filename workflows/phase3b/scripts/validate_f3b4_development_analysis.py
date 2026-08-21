from __future__ import annotations

"""
Independent read-only Phase 3B.4 DEVELOPMENT closure validator.

No scientific output is generated or overwritten.

The validator reconstructs:
- exact synthetic classifier population and confusion matrix;
- standard Wilson intervals;
- end-to-end/admissibility separation;
- empirical selection-function topology;
- period-recovery semantics;
- optimizer/stability identity;
- frozen candidate feature family and threshold axes;
- paired-background PCG64 bootstrap stream;
- promotion gate;
- irreversible final-rule freeze.

It rejects HELDOUT materialization and all known leakage/post-hoc paths.
"""

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


Z_95 = 1.959963984540054

EXPECTED_GLOBAL_DRAW_SHA = (
    "6e37f0c99c8dbc018d9be25e7530cf1aa4c6c1cf3edc0df9e6075214232cac2c"
)

EXPECTED_FIRST_DRAW_SHA = (
    "6ef60371ee2655f876ed64f5b730236c237b580dc9ba7b0155e9200e21ce4b79"
)

EXPECTED_LAST_DRAW_SHA = (
    "54995f548d002db3e47a1fdb616153daefb28975d0f623d0d594167918d358c8"
)


def read_csv(
    path: Path,
) -> list[dict[str, str]]:

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        return list(
            csv.DictReader(f)
        )


def read_json(
    path: Path,
):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def parse_bool(
    value: object,
) -> bool:

    text = str(
        value
    ).strip().lower()

    if text == "true":
        return True

    if text == "false":
        return False

    raise RuntimeError(
        f"Unexpected boolean representation: {value!r}"
    )


def wilson(
    numerator: int,
    denominator: int,
    z: float = Z_95,
) -> dict[str, float | int]:

    if denominator <= 0:
        raise ValueError(
            "Wilson denominator must be positive"
        )

    k = int(numerator)
    n = int(denominator)

    p = k / n
    z2 = z * z

    denom = (
        1.0
        + z2 / n
    )

    center = (
        p
        + z2
        / (
            2.0
            * n
        )
    ) / denom

    half = (
        z
        * math.sqrt(
            (
                p
                * (
                    1.0
                    - p
                )
                + z2
                / (
                    4.0
                    * n
                )
            )
            / n
        )
        / denom
    )

    return {
        "numerator":
            k,

        "denominator":
            n,

        "point_estimate":
            p,

        "wilson_95_lower":
            max(
                0.0,
                center - half,
            ),

        "wilson_95_upper":
            min(
                1.0,
                center + half,
            ),
    }


def close(
    a: float,
    b: float,
    tol: float = 1e-15,
) -> bool:

    return bool(
        abs(
            float(a)
            - float(b)
        )
        <= tol
    )


def assert_binomial_metric(
    stored: dict,
    expected: dict,
) -> None:

    for key in (
        "numerator",
        "denominator",
    ):

        if int(
            stored[key]
        ) != int(
            expected[key]
        ):
            raise RuntimeError(
                f"Metric {key} mismatch"
            )

    for key in (
        "point_estimate",
        "wilson_95_lower",
        "wilson_95_upper",
    ):

        if not close(
            stored[key],
            expected[key],
        ):
            raise RuntimeError(
                f"Metric {key} mismatch"
            )


def classify(
    truth_state: str,
    selected: bool,
) -> str:

    if (
        truth_state
        == "SYNTHETIC_QPP_PRESENT"
    ):
        return (
            "TP"
            if selected
            else "FN"
        )

    if (
        truth_state
        == "SYNTHETIC_QPP_ABSENT"
    ):
        return (
            "FP"
            if selected
            else "TN"
        )

    raise ValueError(
        f"Unexpected truth state: {truth_state}"
    )


def build_threshold_axis(
    values,
) -> np.ndarray:

    arr = np.asarray(
        list(values),
        dtype=np.float64,
    )

    arr = arr[
        np.isfinite(arr)
    ]

    unique = np.unique(
        arr
    )

    if unique.size == 0:
        raise RuntimeError(
            "No finite threshold-axis values"
        )

    midpoints = (
        unique[:-1]
        + (
            unique[1:]
            - unique[:-1]
        )
        / np.float64(2.0)
    )

    return np.unique(
        np.concatenate(
            (
                unique,
                midpoints,
                np.asarray(
                    [10.0],
                    dtype=np.float64,
                ),
            )
        )
    ).astype(
        np.float64,
        copy=False,
    )


def analysis_dir(
    repo: Path,
) -> Path:

    return (
        repo
        / "workflows"
        / "phase3b"
        / "development"
        / "analysis"
    )


def load_bootstrap_pairing(
    repo: Path,
):

    analysis = analysis_dir(
        repo
    )

    evaluation = read_csv(
        analysis
        / "f3b4_baseline_evaluation.csv"
    )

    candidate_rows = read_csv(
        analysis
        / "f3b4_candidate_rule_development.csv"
    )

    if len(candidate_rows) != 1:
        raise RuntimeError(
            "Candidate row count != 1"
        )

    candidate = candidate_rows[0]

    t01 = np.float64(
        float(
            candidate["t01"]
        )
    )

    t21 = np.float64(
        float(
            candidate["t21"]
        )
    )

    by_background = defaultdict(
        list
    )

    for row in evaluation:

        by_background[
            row[
                "background_realization_id"
            ]
        ].append(
            row
        )

    if len(
        by_background
    ) != 1800:
        raise RuntimeError(
            "Unique background count != 1800"
        )

    strata = defaultdict(
        list
    )

    pair_data = {}

    for background in sorted(
        by_background
    ):

        members = by_background[
            background
        ]

        if len(members) != 2:
            raise RuntimeError(
                "Background does not contain exactly POS+NULL"
            )

        pos = [
            row
            for row in members
            if (
                row[
                    "truth_state"
                ]
                == "SYNTHETIC_QPP_PRESENT"
            )
        ]

        nul = [
            row
            for row in members
            if (
                row[
                    "truth_state"
                ]
                == "SYNTHETIC_QPP_ABSENT"
            )
        ]

        if (
            len(pos) != 1
            or len(nul) != 1
        ):
            raise RuntimeError(
                "Background pairing is not exactly POS+NULL"
            )

        pos = pos[0]
        nul = nul[0]

        n_samples = int(
            pos[
                "n_samples"
            ]
        )

        alpha = float(
            pos[
                "red_noise_alpha"
            ]
        )

        qpp_fraction = float(
            pos[
                "qpp_fraction"
            ]
        )

        if int(
            nul[
                "n_samples"
            ]
        ) != n_samples:
            raise RuntimeError(
                "Paired n_samples mismatch"
            )

        if float(
            nul[
                "red_noise_alpha"
            ]
        ) != alpha:
            raise RuntimeError(
                "Paired red_noise_alpha mismatch"
            )

        def candidate_selected(
            row,
        ) -> int:

            return int(
                np.float64(
                    float(
                        row[
                            "delta_bic_0_1"
                        ]
                    )
                )
                > t01
                and
                np.float64(
                    float(
                        row[
                            "delta_bic_2_1"
                        ]
                    )
                )
                > t21
            )

        pair_data[
            background
        ] = (
            int(
                parse_bool(
                    pos[
                        "qpp_selected"
                    ]
                )
            ),
            candidate_selected(
                pos
            ),
            int(
                parse_bool(
                    nul[
                        "qpp_selected"
                    ]
                )
            ),
            candidate_selected(
                nul
            ),
        )

        strata[
            (
                n_samples,
                alpha,
                qpp_fraction,
            )
        ].append(
            background
        )

    expected_strata = [
        (
            n,
            alpha,
            qfrac,
        )
        for n in (
            15,
            30,
            60,
            120,
        )
        for alpha in (
            0.0,
            1.0,
            2.0,
        )
        for qfrac in (
            0.01,
            0.02,
            0.04,
        )
    ]

    if sorted(
        strata
    ) != expected_strata:
        raise RuntimeError(
            "Bootstrap strata do not match frozen 36-stratum topology"
        )

    arrays = []

    for key in expected_strata:

        backgrounds = sorted(
            strata[key]
        )

        if len(
            backgrounds
        ) != 50:
            raise RuntimeError(
                f"Bootstrap stratum {key} does not contain 50 backgrounds"
            )

        arrays.append(
            tuple(
                np.asarray(
                    [
                        pair_data[
                            background
                        ][column]
                        for background
                        in backgrounds
                    ],
                    dtype=np.int64,
                )
                for column in range(4)
            )
        )

    return arrays


def replay_bootstrap(
    repo: Path,
    *,
    replicate_limit: int = 10000,
) -> dict[str, object]:

    if not (
        1
        <= replicate_limit
        <= 10000
    ):
        raise ValueError(
            "replicate_limit must be between 1 and 10000"
        )

    analysis = analysis_dir(
        repo
    )

    binding = read_json(
        repo
        / "workflows"
        / "phase3b"
        / "development"
        / "config"
        / "f3b4_analysis_implementation_binding.json"
    )

    bootstrap = read_csv(
        analysis
        / "f3b4_paired_bootstrap.csv"
    )

    if len(
        bootstrap
    ) != 10000:
        raise RuntimeError(
            "Stored bootstrap row count != 10000"
        )

    pb = binding[
        "paired_bootstrap"
    ]

    entropy = int(
        pb[
            "entropy_integer"
        ]
    )

    if entropy != (
        270880692324125375585783153936804922864
    ):
        raise RuntimeError(
            "Frozen bootstrap entropy changed"
        )

    if (
        pb[
            "bit_generator"
        ]
        != "numpy.random.PCG64"
    ):
        raise RuntimeError(
            "Frozen bootstrap BitGenerator changed"
        )

    if (
        pb[
            "sampling_unit"
        ]
        != "background_realization_id"
    ):
        raise RuntimeError(
            "Frozen bootstrap sampling unit changed"
        )

    arrays = load_bootstrap_pairing(
        repo
    )

    rng = np.random.Generator(
        np.random.PCG64(
            entropy
        )
    )

    global_digest = (
        hashlib.sha256()
    )

    first_sha = None
    last_sha = None

    for replicate in range(
        replicate_limit
    ):

        base_tp = 0
        cand_tp = 0
        base_fp = 0
        cand_fp = 0

        rep_digest = (
            hashlib.sha256()
        )

        for (
            pos_base,
            pos_cand,
            nul_base,
            nul_cand,
        ) in arrays:

            draw = rng.integers(
                0,
                50,
                size=50,
                endpoint=False,
                dtype=np.int64,
            )

            raw = (
                draw.astype(
                    "<i8",
                    copy=False,
                )
                .tobytes(
                    order="C"
                )
            )

            rep_digest.update(
                raw
            )

            global_digest.update(
                raw
            )

            base_tp += int(
                np.sum(
                    pos_base[
                        draw
                    ],
                    dtype=np.int64,
                )
            )

            cand_tp += int(
                np.sum(
                    pos_cand[
                        draw
                    ],
                    dtype=np.int64,
                )
            )

            base_fp += int(
                np.sum(
                    nul_base[
                        draw
                    ],
                    dtype=np.int64,
                )
            )

            cand_fp += int(
                np.sum(
                    nul_cand[
                        draw
                    ],
                    dtype=np.int64,
                )
            )

        rep_sha = (
            rep_digest.hexdigest()
        )

        stored = bootstrap[
            replicate
        ]

        if int(
            stored[
                "replicate_index"
            ]
        ) != replicate:
            raise RuntimeError(
                "Bootstrap replicate order mismatch"
            )

        if (
            int(
                stored[
                    "strata_count"
                ]
            ) != 36
            or
            int(
                stored[
                    "sampled_background_draws"
                ]
            ) != 1800
        ):
            raise RuntimeError(
                "Bootstrap replicate topology mismatch"
            )

        if (
            stored[
                "draw_indices_sha256"
            ]
            != rep_sha
        ):
            raise RuntimeError(
                f"Bootstrap draw SHA mismatch at replicate {replicate}"
            )

        expected_counts = {
            "baseline_TP":
                base_tp,

            "baseline_FN":
                1800
                - base_tp,

            "baseline_TN":
                1800
                - base_fp,

            "baseline_FP":
                base_fp,

            "candidate_TP":
                cand_tp,

            "candidate_FN":
                1800
                - cand_tp,

            "candidate_TN":
                1800
                - cand_fp,

            "candidate_FP":
                cand_fp,
        }

        for field, expected in (
            expected_counts.items()
        ):

            if int(
                stored[field]
            ) != expected:
                raise RuntimeError(
                    f"Bootstrap {field} mismatch at replicate {replicate}"
                )

        base_sens = (
            base_tp
            / 1800.0
        )

        cand_sens = (
            cand_tp
            / 1800.0
        )

        base_spec = (
            (
                1800
                - base_fp
            )
            / 1800.0
        )

        cand_spec = (
            (
                1800
                - cand_fp
            )
            / 1800.0
        )

        base_ba = (
            0.5
            * (
                base_sens
                + base_spec
            )
        )

        cand_ba = (
            0.5
            * (
                cand_sens
                + cand_spec
            )
        )

        metric_expectations = {
            "candidate_minus_baseline_sensitivity":
                cand_sens
                - base_sens,

            "candidate_minus_baseline_specificity":
                cand_spec
                - base_spec,

            "candidate_minus_baseline_balanced_accuracy":
                cand_ba
                - base_ba,
        }

        for field, expected in (
            metric_expectations.items()
        ):

            if not close(
                stored[field],
                expected,
            ):
                raise RuntimeError(
                    f"Bootstrap {field} mismatch at replicate {replicate}"
                )

        if replicate == 0:
            first_sha = (
                rep_sha
            )

        last_sha = rep_sha

    return {
        "replicates_replayed":
            replicate_limit,

        "first_replicate_sha256":
            first_sha,

        "last_replicate_sha256":
            last_sha,

        "global_draw_stream_sha256":
            global_digest.hexdigest(),
    }


def validate(
    repo: Path,
) -> dict[str, object]:

    if (
        sys.version.split()[0]
        != "3.13.13"
    ):
        raise RuntimeError(
            "F3B.4 validation Python version != 3.13.13"
        )

    if (
        np.__version__
        != "2.3.5"
    ):
        raise RuntimeError(
            "F3B.4 validation NumPy version != 2.3.5"
        )

    if (
        sys.byteorder
        != "little"
    ):
        raise RuntimeError(
            "F3B.4 validation byteorder != little"
        )

    heldout = (
        repo
        / "data"
        / "interim"
        / "phase3b"
        / "heldout"
    )

    if heldout.exists():
        raise RuntimeError(
            "HELDOUT materialization/access detected"
        )

    analysis = analysis_dir(
        repo
    )

    evaluation = read_csv(
        analysis
        / "f3b4_baseline_evaluation.csv"
    )

    metrics = read_json(
        analysis
        / "f3b4_baseline_metrics.json"
    )

    end_to_end = read_csv(
        analysis
        / "f3b4_end_to_end_metrics.csv"
    )

    selection = read_csv(
        analysis
        / "f3b4_selection_function.csv"
    )

    period = read_csv(
        analysis
        / "f3b4_period_recovery.csv"
    )

    period_summary = read_json(
        analysis
        / "f3b4_period_recovery_summary.json"
    )

    optimizer = read_csv(
        analysis
        / "f3b4_optimizer_stability.csv"
    )

    diagnostics = read_csv(
        analysis
        / "f3b4_seed_model_diagnostics.csv"
    )

    candidate_rows = read_csv(
        analysis
        / "f3b4_candidate_rule_development.csv"
    )

    bootstrap = read_csv(
        analysis
        / "f3b4_paired_bootstrap.csv"
    )

    gate = read_json(
        analysis
        / "f3b4_candidate_rule_gate.json"
    )

    freeze = read_json(
        analysis
        / "f3b4_final_rule_freeze.json"
    )

    # --------------------------------------------------------
    # A. BASELINE CLASSIFICATION + LEAKAGE FIREWALL
    # --------------------------------------------------------

    if len(
        evaluation
    ) != 3600:
        raise RuntimeError(
            "Baseline evaluation rows != 3600"
        )

    seen_ids = set()

    counts = Counter()

    delta01_values = []
    delta21_values = []

    for row in evaluation:

        sid = row[
            "simulation_unit_id"
        ]

        if sid in seen_ids:
            raise RuntimeError(
                "Duplicate baseline simulation_unit_id"
            )

        seen_ids.add(
            sid
        )

        if (
            row[
                "truth_usage"
            ]
            != "TARGET_OR_EVALUATION_AXIS_ONLY"
        ):
            raise RuntimeError(
                "Truth leakage semantics changed"
            )

        if (
            row[
                "evaluation_scope"
            ]
            != "DEVELOPMENT_BASELINE_SEED0"
        ):
            raise RuntimeError(
                "Evaluation scope changed"
            )

        if (
            row[
                "input_state"
            ]
            != "ELIGIBLE_FOR_AFINO"
        ):
            raise RuntimeError(
                "Inadmissible row entered classifier population"
            )

        if float(
            row[
                "baseline_threshold_01"
            ]
        ) != 10.0:
            raise RuntimeError(
                "Baseline t01 changed"
            )

        if float(
            row[
                "baseline_threshold_21"
            ]
        ) != 10.0:
            raise RuntimeError(
                "Baseline t21 changed"
            )

        if (
            row[
                "baseline_comparison"
            ]
            != "STRICT_GREATER_THAN"
        ):
            raise RuntimeError(
                "Baseline comparator changed"
            )

        d01 = float(
            row[
                "delta_bic_0_1"
            ]
        )

        d21 = float(
            row[
                "delta_bic_2_1"
            ]
        )

        if not (
            math.isfinite(
                d01
            )
            and math.isfinite(
                d21
            )
        ):
            raise RuntimeError(
                "Non-finite classifier feature"
            )

        selected = bool(
            d01 > 10.0
            and d21 > 10.0
        )

        if selected != parse_bool(
            row[
                "qpp_selected"
            ]
        ):
            raise RuntimeError(
                "Stored baseline rule differs from 10/10 strict rule"
            )

        if not parse_bool(
            row[
                "baseline_rule_agreement"
            ]
        ):
            raise RuntimeError(
                "Baseline-rule agreement false"
            )

        outcome = classify(
            row[
                "truth_state"
            ],
            selected,
        )

        if (
            outcome
            != row[
                "classification_outcome"
            ]
        ):
            raise RuntimeError(
                "Classification outcome mismatch"
            )

        counts[
            outcome
        ] += 1

        delta01_values.append(
            d01
        )

        delta21_values.append(
            d21
        )

    for key in (
        "TP",
        "FN",
        "TN",
        "FP",
    ):
        counts.setdefault(
            key,
            0,
        )

    if (
        counts["TP"],
        counts["FN"],
        counts["TN"],
        counts["FP"],
    ) != (
        143,
        1657,
        1799,
        1,
    ):
        raise RuntimeError(
            "Baseline confusion matrix mismatch"
        )

    if (
        metrics[
            "population"
        ][
            "numerical_stability_extra_in_confusion_matrix"
        ]
        != 0
    ):
        raise RuntimeError(
            "Stability-extra decisions entered classifier metrics"
        )

    if (
        metrics[
            "population"
        ][
            "input_inadmissible_in_confusion_matrix"
        ]
        != 0
    ):
        raise RuntimeError(
            "Challenge/inadmissible observations entered classifier metrics"
        )

    if (
        metrics[
            "execution_boundary"
        ][
            "truth_used_as_rule_feature"
        ]
        is not False
    ):
        raise RuntimeError(
            "Truth feature leakage recorded"
        )

    # --------------------------------------------------------
    # B. EXACT WILSON
    # --------------------------------------------------------

    if float(
        metrics[
            "wilson_interval"
        ][
            "z"
        ]
    ) != Z_95:
        raise RuntimeError(
            "Wilson z changed"
        )

    if (
        metrics[
            "wilson_interval"
        ][
            "implementation"
        ]
        != "CLOSED_FORM_STANDARD_WILSON_SCORE"
    ):
        raise RuntimeError(
            "Wilson implementation changed"
        )

    sensitivity = wilson(
        143,
        1800,
    )

    specificity = wilson(
        1799,
        1800,
    )

    fpr = wilson(
        1,
        1800,
    )

    assert_binomial_metric(
        metrics[
            "primary_classification_metrics"
        ][
            "sensitivity_TPR"
        ],
        sensitivity,
    )

    assert_binomial_metric(
        metrics[
            "primary_classification_metrics"
        ][
            "specificity_TNR"
        ],
        specificity,
    )

    assert_binomial_metric(
        metrics[
            "primary_classification_metrics"
        ][
            "false_positive_rate_FPR"
        ],
        fpr,
    )

    balanced_accuracy = (
        0.5
        * (
            sensitivity[
                "point_estimate"
            ]
            + specificity[
                "point_estimate"
            ]
        )
    )

    if not close(
        metrics[
            "secondary_classification_summary"
        ][
            "balanced_accuracy"
        ][
            "point_estimate"
        ],
        balanced_accuracy,
    ):
        raise RuntimeError(
            "Balanced accuracy mismatch"
        )

    # --------------------------------------------------------
    # C. END-TO-END / CLASSIFIER SEPARATION
    # --------------------------------------------------------

    if len(
        end_to_end
    ) != 9:
        raise RuntimeError(
            "End-to-end metric rows != 9"
        )

    expected_e2e = {
        (
            "PRIMARY_CLASSIFICATION_PLANE",
            "input_admissibility_fraction",
        ):
            (3600, 3600),

        (
            "PRIMARY_CLASSIFICATION_PLANE",
            "end_to_end_positive_recovery_fraction",
        ):
            (143, 1800),

        (
            "PRIMARY_CLASSIFICATION_PLANE",
            "end_to_end_null_selection_fraction",
        ):
            (1, 1800),

        (
            "CHALLENGE_INPUT_ADMISSIBILITY_PLANE",
            "input_admissibility_fraction",
        ):
            (0, 720),

        (
            "CHALLENGE_INPUT_ADMISSIBILITY_PLANE",
            "end_to_end_positive_recovery_fraction",
        ):
            (0, 360),

        (
            "CHALLENGE_INPUT_ADMISSIBILITY_PLANE",
            "end_to_end_null_selection_fraction",
        ):
            (0, 360),

        (
            "ALL_PLANNED_SYNTHETIC_DESIGN",
            "input_admissibility_fraction",
        ):
            (3600, 4320),

        (
            "ALL_PLANNED_SYNTHETIC_DESIGN",
            "end_to_end_positive_recovery_fraction",
        ):
            (143, 2160),

        (
            "ALL_PLANNED_SYNTHETIC_DESIGN",
            "end_to_end_null_selection_fraction",
        ):
            (1, 2160),
    }

    observed_e2e = {}

    for row in end_to_end:

        key = (
            row[
                "scope_id"
            ],
            row[
                "metric"
            ],
        )

        if key in observed_e2e:
            raise RuntimeError(
                "Duplicate end-to-end metric row"
            )

        observed_e2e[
            key
        ] = row

        if parse_bool(
            row[
                "classification_metric_synonym"
            ]
        ):
            raise RuntimeError(
                "End-to-end metric recoded as classifier synonym"
            )

        if parse_bool(
            row[
                "input_inadmissible_recoded_as_FN_or_TN"
            ]
        ):
            raise RuntimeError(
                "Inadmissible observation recoded as FN/TN"
            )

    if set(
        observed_e2e
    ) != set(
        expected_e2e
    ):
        raise RuntimeError(
            "End-to-end metric topology mismatch"
        )

    for key, (
        numerator,
        denominator,
    ) in expected_e2e.items():

        row = observed_e2e[
            key
        ]

        if (
            int(
                row[
                    "numerator"
                ]
            )
            != numerator
            or
            int(
                row[
                    "denominator"
                ]
            )
            != denominator
        ):
            raise RuntimeError(
                f"End-to-end numerator/denominator mismatch: {key}"
            )

        expected = wilson(
            numerator,
            denominator,
        )

        if not close(
            row[
                "point_estimate"
            ],
            expected[
                "point_estimate"
            ],
        ):
            raise RuntimeError(
                f"End-to-end point estimate mismatch: {key}"
            )

        if not close(
            row[
                "wilson_95_lower"
            ],
            expected[
                "wilson_95_lower"
            ],
        ):
            raise RuntimeError(
                f"End-to-end Wilson lower mismatch: {key}"
            )

        if not close(
            row[
                "wilson_95_upper"
            ],
            expected[
                "wilson_95_upper"
            ],
        ):
            raise RuntimeError(
                f"End-to-end Wilson upper mismatch: {key}"
            )

    # --------------------------------------------------------
    # D. STRATIFIED EMPIRICAL SELECTION FUNCTION
    # --------------------------------------------------------

    if len(
        selection
    ) != 156:
        raise RuntimeError(
            "Selection-function rows != 156"
        )

    family_counts = Counter(
        row[
            "stratum_family"
        ]
        for row in selection
    )

    if family_counts != Counter(
        {
            "POSITIVE_BASE":
                36,

            "POSITIVE_PERIOD_BIN":
                108,

            "NULL_POOLED":
                12,
        }
    ):
        raise RuntimeError(
            "Selection-function family topology mismatch"
        )

    expected_bins = {
        "P40_63":
            (
                40.0,
                63.245553203367585,
                True,
                False,
            ),

        "P63_106":
            (
                63.245553203367585,
                105.83005244258362,
                True,
                False,
            ),

        "P106_300":
            (
                105.83005244258362,
                300.0,
                True,
                True,
            ),
    }

    structural = []

    positive_base_exposure = 0
    positive_base_selected = 0

    positive_period_exposure = 0
    positive_period_selected = 0

    null_exposure = 0
    null_selected = 0

    for row in selection:

        if (
            row[
                "primary_representation"
            ]
            != "STRATIFIED_EMPIRICAL"
        ):
            raise RuntimeError(
                "Selection-function representation changed"
            )

        if parse_bool(
            row[
                "probabilistic_model_fitted"
            ]
        ):
            raise RuntimeError(
                "Unexpected probabilistic selection model"
            )

        if int(
            row[
                "challenge_rows_included"
            ]
        ) != 0:
            raise RuntimeError(
                "Challenge leakage into selection function"
            )

        family = row[
            "stratum_family"
        ]

        exposure = int(
            row[
                "exposure_count"
            ]
        )

        selected = int(
            row[
                "selected_count"
            ]
        )

        status = row[
            "exposure_status"
        ]

        if (
            status
            == "STRUCTURAL_NO_EXPOSURE"
        ):

            structural.append(
                row
            )

            if exposure != 0:
                raise RuntimeError(
                    "STRUCTURAL_NO_EXPOSURE has nonzero exposure"
                )

            for field in (
                "input_eligibility_point_estimate",
                "conditional_selection_point_estimate",
                "end_to_end_selection_point_estimate",
            ):

                if (
                    row[field]
                    != ""
                ):
                    raise RuntimeError(
                        "STRUCTURAL_NO_EXPOSURE contains fabricated estimate"
                    )

        elif (
            status
            != "EXPOSED"
        ):
            raise RuntimeError(
                "Unexpected selection-function exposure status"
            )

        if (
            family
            == "POSITIVE_BASE"
        ):

            positive_base_exposure += exposure
            positive_base_selected += selected

        elif (
            family
            == "POSITIVE_PERIOD_BIN"
        ):

            positive_period_exposure += exposure
            positive_period_selected += selected

            bin_id = row[
                "period_bin_id"
            ]

            if (
                bin_id
                not in expected_bins
            ):
                raise RuntimeError(
                    "Post-hoc/unregistered period bin"
                )

            (
                expected_lower,
                expected_upper,
                expected_lower_inclusive,
                expected_upper_inclusive,
            ) = expected_bins[
                bin_id
            ]

            if not close(
                row[
                    "period_lower_s"
                ],
                expected_lower,
                tol=1e-12,
            ):
                raise RuntimeError(
                    "Period-bin lower boundary mismatch"
                )

            if not close(
                row[
                    "period_upper_s"
                ],
                expected_upper,
                tol=1e-12,
            ):
                raise RuntimeError(
                    "Period-bin upper boundary mismatch"
                )

            if parse_bool(
                row[
                    "period_lower_inclusive"
                ]
            ) != (
                expected_lower_inclusive
            ):
                raise RuntimeError(
                    "Period-bin lower inclusion mismatch"
                )

            if parse_bool(
                row[
                    "period_upper_inclusive"
                ]
            ) != (
                expected_upper_inclusive
            ):
                raise RuntimeError(
                    "Period-bin upper inclusion mismatch"
                )

        elif (
            family
            == "NULL_POOLED"
        ):

            null_exposure += exposure
            null_selected += selected

            if not parse_bool(
                row[
                    "null_qpp_fraction_pooled"
                ]
            ):
                raise RuntimeError(
                    "NULL qpp_fraction is not pooled"
                )

        else:
            raise RuntimeError(
                "Unexpected selection-function family"
            )

    if len(
        structural
    ) != 9:
        raise RuntimeError(
            "STRUCTURAL_NO_EXPOSURE rows != 9"
        )

    for row in structural:

        if (
            row[
                "stratum_family"
            ]
            != "POSITIVE_PERIOD_BIN"
            or
            int(
                row[
                    "n_samples"
                ]
            )
            != 15
            or
            row[
                "period_bin_id"
            ]
            != "P106_300"
        ):
            raise RuntimeError(
                "Unexpected structural-no-exposure location"
            )

    if (
        positive_base_exposure,
        positive_base_selected,
    ) != (
        1800,
        143,
    ):
        raise RuntimeError(
            "Positive-base selection-function totals mismatch"
        )

    if (
        positive_period_exposure,
        positive_period_selected,
    ) != (
        1800,
        143,
    ):
        raise RuntimeError(
            "Positive-period selection-function totals mismatch"
        )

    if (
        null_exposure,
        null_selected,
    ) != (
        1800,
        1,
    ):
        raise RuntimeError(
            "Null selection-function totals mismatch"
        )

    # --------------------------------------------------------
    # E. PERIOD RECOVERY
    # --------------------------------------------------------

    if len(
        period
    ) != 143:
        raise RuntimeError(
            "Period-recovery rows != 143"
        )

    abs_errors = []
    rel_errors = []
    log_ratios = []

    period_ids = set()

    for row in period:

        sid = row[
            "simulation_unit_id"
        ]

        if sid in period_ids:
            raise RuntimeError(
                "Duplicate period-recovery simulation_unit_id"
            )

        period_ids.add(
            sid
        )

        if (
            row[
                "classification_outcome"
            ]
            != "TP"
        ):
            raise RuntimeError(
                "Period recovery includes non-TP observation"
            )

        if parse_bool(
            row[
                "nonselected_m1_center_used"
            ]
        ):
            raise RuntimeError(
                "Non-selected M1 center used as recovered period"
            )

        true_period = float(
            row[
                "true_period_s"
            ]
        )

        recovered = float(
            row[
                "recovered_period_s"
            ]
        )

        abs_error = float(
            row[
                "absolute_period_error_s"
            ]
        )

        rel_error = float(
            row[
                "relative_period_error"
            ]
        )

        log_ratio = float(
            row[
                "log_period_ratio"
            ]
        )

        if not all(
            math.isfinite(x)
            for x in (
                true_period,
                recovered,
                abs_error,
                rel_error,
                log_ratio,
            )
        ):
            raise RuntimeError(
                "Non-finite period-recovery value"
            )

        if not close(
            abs_error,
            abs(
                recovered
                - true_period
            ),
            tol=1e-12,
        ):
            raise RuntimeError(
                "Absolute period-error arithmetic mismatch"
            )

        if not close(
            rel_error,
            abs_error
            / true_period,
            tol=1e-12,
        ):
            raise RuntimeError(
                "Relative period-error arithmetic mismatch"
            )

        if not close(
            log_ratio,
            math.log(
                recovered
                / true_period
            ),
            tol=1e-12,
        ):
            raise RuntimeError(
                "Log-period-ratio arithmetic mismatch"
            )

        abs_errors.append(
            abs_error
        )

        rel_errors.append(
            rel_error
        )

        log_ratios.append(
            log_ratio
        )

    if (
        period_summary[
            "population"
        ][
            "eligible_positive_injections"
        ]
        != 1800
    ):
        raise RuntimeError(
            "Period eligible-positive denominator mismatch"
        )

    if (
        period_summary[
            "population"
        ][
            "baseline_true_positives"
        ]
        != 143
    ):
        raise RuntimeError(
            "Period TP count mismatch"
        )

    if (
        period_summary[
            "population"
        ][
            "baseline_false_negatives"
        ]
        != 1657
    ):
        raise RuntimeError(
            "Period FN count mismatch"
        )

    if (
        period_summary[
            "population"
        ][
            "selected_true_positives_missing_finite_period"
        ]
        != 0
    ):
        raise RuntimeError(
            "Selected TP missing finite period"
        )

    if (
        period_summary[
            "period_semantics"
        ][
            "nonselected_m1_center_is_period_recovery"
        ]
        is not False
    ):
        raise RuntimeError(
            "Non-selected M1 center permitted as recovery"
        )

    if (
        period_summary[
            "period_semantics"
        ][
            "nonselected_error_imputation"
        ]
        != "PROHIBITED"
    ):
        raise RuntimeError(
            "Non-selected period-error imputation permitted"
        )

    if (
        period_summary[
            "period_semantics"
        ][
            "period_recovered_within_X_percent_threshold"
        ]
        != "NOT_USED"
    ):
        raise RuntimeError(
            "Post-hoc period recovery threshold detected"
        )

    expected_period_quantiles = {
        "absolute":
            (
                0.23207739153627158,
                0.8555459988347351,
                2.0874258904619793,
            ),

        "relative":
            (
                0.0038890402253348583,
                0.014847583385661523,
                0.02965191669760797,
            ),

        "log":
            (
                -0.015425499319341989,
                0.005142490233852693,
                0.02468984706394365,
            ),
    }

    for key, values in (
        (
            "absolute",
            abs_errors,
        ),
        (
            "relative",
            rel_errors,
        ),
        (
            "log",
            log_ratios,
        ),
    ):

        observed = np.quantile(
            np.asarray(
                values,
                dtype=np.float64,
            ),
            np.asarray(
                [
                    0.16,
                    0.50,
                    0.84,
                ],
                dtype=np.float64,
            ),
            method="linear",
        )

        expected = (
            expected_period_quantiles[
                key
            ]
        )

        if not np.allclose(
            observed,
            np.asarray(
                expected,
                dtype=np.float64,
            ),
            rtol=0.0,
            atol=1e-12,
        ):
            raise RuntimeError(
                f"Period {key} quantile mismatch"
            )

    # --------------------------------------------------------
    # F. OPTIMIZER / NUMERICAL STABILITY
    # --------------------------------------------------------

    if len(
        optimizer
    ) != 72:
        raise RuntimeError(
            "Optimizer-stability series != 72"
        )

    if len(
        diagnostics
    ) != 3:
        raise RuntimeError(
            "Seed-model diagnostics rows != 3"
        )

    if len({
        row[
            "simulation_unit_id"
        ]
        for row in optimizer
    }) != 72:
        raise RuntimeError(
            "Duplicate optimizer-stability series"
        )

    if sum(
        int(
            row[
                "seed_count"
            ]
        )
        for row in optimizer
    ) != 720:
        raise RuntimeError(
            "Optimizer-stability decisions != 720"
        )

    if any(
        int(
            row[
                "seed_count"
            ]
        )
        != 10
        for row in optimizer
    ):
        raise RuntimeError(
            "Optimizer stability is not 10 seeds per series"
        )

    if any(
        int(
            row[
                "discordant_vs_seed0_count"
            ]
        )
        != 0
        for row in optimizer
    ):
        raise RuntimeError(
            "Classification seed discordance detected"
        )

    if sum(
        int(
            parse_bool(
                row[
                    "seed0_selected"
                ]
            )
        )
        for row in optimizer
    ) != 2:
        raise RuntimeError(
            "Seed-0 selected stability series != 2"
        )

    for row in optimizer:

        for field in (
            "unique_parameter_payloads_m0",
            "unique_parameter_payloads_m1",
            "unique_parameter_payloads_m2",
        ):

            if int(
                row[
                    field
                ]
            ) != 10:
                raise RuntimeError(
                    "Parameter-payload multiplicity changed"
                )

        if (
            "NOT_AUDITABLE"
            not in row[
                "convergence_status_set"
            ]
        ):
            raise RuntimeError(
                "Optimizer convergence status unexpectedly auditable"
            )

    diag = {
        row[
            "model_id"
        ]:
            row
        for row in diagnostics
    }

    if set(
        diag
    ) != {
        "M0",
        "M1",
        "M2",
    }:
        raise RuntimeError(
            "Seed-model diagnostic model set mismatch"
        )

    expected_diag = {
        "M0":
            (
                720,
                0,
                0,
                5,
            ),

        "M1":
            (
                720,
                0,
                0,
                400,
            ),

        "M2":
            (
                720,
                296,
                3158,
                311,
            ),
    }

    for model, expected in (
        expected_diag.items()
    ):

        row = diag[
            model
        ]

        observed = (
            int(
                row[
                    "calls"
                ]
            ),
            int(
                row[
                    "warning_calls"
                ]
            ),
            int(
                row[
                    "warning_count"
                ]
            ),
            int(
                row[
                    "bound_calls"
                ]
            ),
        )

        if observed != expected:
            raise RuntimeError(
                f"{model} optimizer diagnostic mismatch"
            )

        if (
            "NOT_AUDITABLE"
            not in row[
                "convergence_status_counts"
            ]
        ):
            raise RuntimeError(
                f"{model} convergence status mismatch"
            )

    # --------------------------------------------------------
    # G. CANDIDATE FEATURES / AXIS CONTRACT / POST-HOC FIREWALL
    # --------------------------------------------------------

    if len(
        candidate_rows
    ) != 1:
        raise RuntimeError(
            "Candidate rows != 1"
        )

    candidate = candidate_rows[
        0
    ]

    if (
        candidate[
            "candidate_id"
        ]
        != "DEVELOPMENT_OPTIMUM_001"
    ):
        raise RuntimeError(
            "Candidate identity changed"
        )

    if (
        candidate[
            "rule_family"
        ]
        != "TWO_THRESHOLD_BIC_CONJUNCTION"
    ):
        raise RuntimeError(
            "Candidate rule family changed"
        )

    allowed_features = (
        json.loads(
            candidate[
                "allowed_features_json"
            ]
        )
    )

    if allowed_features != [
        "delta_BIC01",
        "delta_BIC21",
    ]:
        raise RuntimeError(
            "Truth/nuisance feature leakage into candidate"
        )

    if (
        candidate[
            "truth_usage"
        ]
        != "TARGET_FOR_OBJECTIVE_ONLY_NOT_RULE_FEATURE"
    ):
        raise RuntimeError(
            "Candidate truth usage changed"
        )

    if parse_bool(
        candidate[
            "stability_diagnostics_used_as_candidate_features"
        ]
    ):
        raise RuntimeError(
            "Numerical stability diagnostics used as candidate features"
        )

    if (
        candidate[
            "comparison_operator"
        ]
        != "STRICT_GREATER_THAN"
    ):
        raise RuntimeError(
            "Candidate comparator changed"
        )

    if (
        candidate[
            "runner_up_rescue"
        ]
        != "FORBIDDEN"
    ):
        raise RuntimeError(
            "Runner-up rescue permitted"
        )

    if int(
        candidate[
            "runner_up_rows_written"
        ]
    ) != 0:
        raise RuntimeError(
            "Runner-up candidate exists"
        )

    axis01 = build_threshold_axis(
        delta01_values
    )

    axis21 = build_threshold_axis(
        delta21_values
    )

    if (
        axis01.size
        != 7200
        or axis21.size
        != 7200
    ):
        raise RuntimeError(
            "Candidate threshold-axis size mismatch"
        )

    if not (
        np.any(
            axis01
            == np.float64(
                10.0
            )
        )
        and
        np.any(
            axis21
            == np.float64(
                10.0
            )
        )
    ):
        raise RuntimeError(
            "Baseline threshold missing from candidate axes"
        )

    if (
        int(
            candidate[
                "axis01_count"
            ]
        )
        != 7200
        or
        int(
            candidate[
                "axis21_count"
            ]
        )
        != 7200
    ):
        raise RuntimeError(
            "Stored candidate axis count mismatch"
        )

    if (
        int(
            candidate[
                "full_axis_candidate_pairs"
            ]
        )
        != 51840000
    ):
        raise RuntimeError(
            "Full-axis candidate pair count changed"
        )

    if (
        int(
            candidate[
                "selection_state_pairs_evaluated"
            ]
        )
        != 12960000
    ):
        raise RuntimeError(
            "Selection-state candidate pair count changed"
        )

    if (
        float(
            candidate[
                "t01"
            ]
        )
        != -7.517054630023225
        or
        float(
            candidate[
                "t21"
            ]
        )
        != -4.4514075428899105
    ):
        raise RuntimeError(
            "Frozen DEVELOPMENT candidate thresholds changed"
        )

    if (
        int(
            candidate[
                "TP"
            ]
        ),
        int(
            candidate[
                "FN"
            ]
        ),
        int(
            candidate[
                "TN"
            ]
        ),
        int(
            candidate[
                "FP"
            ]
        ),
    ) != (
        1171,
        629,
        1115,
        685,
    ):
        raise RuntimeError(
            "Frozen candidate confusion matrix changed"
        )

    # --------------------------------------------------------
    # H. FIXED PCG64 PAIRED BACKGROUND BOOTSTRAP
    # --------------------------------------------------------

    if len(
        bootstrap
    ) != 10000:
        raise RuntimeError(
            "Bootstrap rows != 10000"
        )

    replay = replay_bootstrap(
        repo,
        replicate_limit=10000,
    )

    if (
        replay[
            "first_replicate_sha256"
        ]
        != EXPECTED_FIRST_DRAW_SHA
    ):
        raise RuntimeError(
            "First frozen bootstrap draw stream changed"
        )

    if (
        replay[
            "last_replicate_sha256"
        ]
        != EXPECTED_LAST_DRAW_SHA
    ):
        raise RuntimeError(
            "Last frozen bootstrap draw stream changed"
        )

    if (
        replay[
            "global_draw_stream_sha256"
        ]
        != EXPECTED_GLOBAL_DRAW_SHA
    ):
        raise RuntimeError(
            "Global frozen PCG64 draw stream changed"
        )

    # --------------------------------------------------------
    # I. PROMOTION GATE
    # --------------------------------------------------------

    delta_ba = np.asarray(
        [
            float(
                row[
                    "candidate_minus_baseline_balanced_accuracy"
                ]
            )
            for row in bootstrap
        ],
        dtype=np.float64,
    )

    delta_sens = np.asarray(
        [
            float(
                row[
                    "candidate_minus_baseline_sensitivity"
                ]
            )
            for row in bootstrap
        ],
        dtype=np.float64,
    )

    delta_spec = np.asarray(
        [
            float(
                row[
                    "candidate_minus_baseline_specificity"
                ]
            )
            for row in bootstrap
        ],
        dtype=np.float64,
    )

    delta_fpr = np.asarray(
        [
            float(
                row[
                    "candidate_minus_baseline_FPR"
                ]
            )
            for row in bootstrap
        ],
        dtype=np.float64,
    )

    ci_ba = np.quantile(
        delta_ba,
        [0.025, 0.975],
        method="linear",
    )

    ci_sens = np.quantile(
        delta_sens,
        [0.025, 0.975],
        method="linear",
    )

    ci_spec = np.quantile(
        delta_spec,
        [0.025, 0.975],
        method="linear",
    )

    ci_fpr = np.quantile(
        delta_fpr,
        [0.025, 0.975],
        method="linear",
    )

    expected_ci = {
        "ba":
            (
                0.08611111111111114,
                0.10472222222222227,
            ),

        "sens":
            (
                0.5533333333333333,
                0.5894444444444444,
            ),

        "spec":
            (
                -0.3933333333333333,
                -0.3672222222222222,
            ),

        "fpr":
            (
                0.3672222222222222,
                0.3933333333333333,
            ),
    }

    for observed, expected, name in (
        (
            ci_ba,
            expected_ci["ba"],
            "BA",
        ),
        (
            ci_sens,
            expected_ci["sens"],
            "sensitivity",
        ),
        (
            ci_spec,
            expected_ci["spec"],
            "specificity",
        ),
        (
            ci_fpr,
            expected_ci["fpr"],
            "FPR",
        ),
    ):

        if not np.allclose(
            observed,
            np.asarray(
                expected,
                dtype=np.float64,
            ),
            rtol=0.0,
            atol=1e-15,
        ):
            raise RuntimeError(
                f"Promotion bootstrap {name} interval mismatch"
            )

    point_improvement = float(
        candidate[
            "balanced_accuracy_improvement_vs_baseline"
        ]
    )

    criteria = (
        point_improvement
        >= 0.025,

        float(
            ci_ba[0]
        )
        > 0.0,

        float(
            ci_sens[0]
        )
        > -0.025,

        float(
            ci_spec[0]
        )
        > -0.025,
    )

    if criteria != (
        True,
        True,
        True,
        False,
    ):
        raise RuntimeError(
            "Promotion criterion reconstruction mismatch"
        )

    if (
        gate[
            "status"
        ]
        != "CANDIDATE_NOT_PROMOTED"
    ):
        raise RuntimeError(
            "Candidate gate status changed"
        )

    if int(
        gate[
            "promotion_result"
        ][
            "criteria_passed"
        ]
    ) != 3:
        raise RuntimeError(
            "Candidate promotion pass count changed"
        )

    if (
        gate[
            "promotion_result"
        ][
            "candidate_rule_promoted"
        ]
        is not False
    ):
        raise RuntimeError(
            "Candidate unexpectedly promoted"
        )

    if (
        gate[
            "promotion_result"
        ][
            "failed_criteria"
        ]
        != [
            "C4_LOWER_CI_DELTA_SPECIFICITY_GT_NEG_0_025"
        ]
    ):
        raise RuntimeError(
            "Candidate promotion failed-criterion changed"
        )

    if (
        gate[
            "promotion_result"
        ][
            "runner_up_rescue"
        ]
        != "FORBIDDEN"
    ):
        raise RuntimeError(
            "Runner-up rescue changed"
        )

    if (
        gate[
            "promotion_result"
        ][
            "alternate_candidate_search"
        ]
        != "FORBIDDEN"
    ):
        raise RuntimeError(
            "Alternate candidate search changed"
        )

    # --------------------------------------------------------
    # J. FINAL RULE FREEZE / HELDOUT FRONTIER
    # --------------------------------------------------------

    if (
        freeze[
            "freeze_state"
        ]
        != "FINAL_RULE_FREEZE_BASELINE_ONLY"
    ):
        raise RuntimeError(
            "Final freeze branch changed"
        )

    final_rule = freeze[
        "final_rule"
    ]

    if (
        final_rule[
            "rule_type"
        ]
        != "AFINO_0_5_BASELINE"
    ):
        raise RuntimeError(
            "Final frozen rule type changed"
        )

    if (
        final_rule[
            "selection_rule"
        ]
        != "delta_BIC01 > 10 AND delta_BIC21 > 10"
    ):
        raise RuntimeError(
            "Final frozen rule text changed"
        )

    if (
        final_rule[
            "comparison_operator"
        ]
        != "STRICT_GREATER_THAN"
    ):
        raise RuntimeError(
            "Final comparator changed"
        )

    if (
        float(
            final_rule[
                "t01"
            ]
        )
        != 10.0
        or
        float(
            final_rule[
                "t21"
            ]
        )
        != 10.0
    ):
        raise RuntimeError(
            "Final thresholds changed"
        )

    if (
        final_rule[
            "candidate_rule_promoted"
        ]
        is not False
    ):
        raise RuntimeError(
            "Final freeze unexpectedly promotes candidate"
        )

    if (
        final_rule[
            "correction_claim"
        ]
        != "NOT_ESTABLISHED"
    ):
        raise RuntimeError(
            "Correction claim changed"
        )

    for key in (
        "threshold_mutation_after_freeze",
        "runner_up_rescue",
        "alternate_candidate_search",
    ):

        if (
            final_rule[
                key
            ]
            != "FORBIDDEN"
        ):
            raise RuntimeError(
                f"Post-freeze firewall changed: {key}"
            )

    heldout_boundary = (
        freeze[
            "heldout_boundary"
        ]
    )

    if (
        heldout_boundary[
            "heldout_generated_at_freeze"
        ]
        is not False
        or
        heldout_boundary[
            "heldout_accessed_at_freeze"
        ]
        is not False
        or
        heldout_boundary[
            "heldout_used_for_rule_selection"
        ]
        is not False
    ):
        raise RuntimeError(
            "HELDOUT influenced final-rule freeze"
        )

    for boundary in (
        gate[
            "execution_boundary"
        ],
        freeze[
            "execution_boundary"
        ],
    ):

        if int(
            boundary[
                "new_afino_calls"
            ]
        ) != 0:
            raise RuntimeError(
                "New AFINO calls detected in F3B.4 boundary"
            )

        if int(
            boundary[
                "generator_calls"
            ]
        ) != 0:
            raise RuntimeError(
                "Generator calls detected in F3B.4 boundary"
            )

        if (
            boundary[
                "heldout_generated"
            ]
            is not False
            or
            boundary[
                "heldout_accessed"
            ]
            is not False
        ):
            raise RuntimeError(
                "HELDOUT boundary violated"
            )

    return {
        "TP":
            143,

        "FN":
            1657,

        "TN":
            1799,

        "FP":
            1,

        "sensitivity":
            sensitivity[
                "point_estimate"
            ],

        "specificity":
            specificity[
                "point_estimate"
            ],

        "FPR":
            fpr[
                "point_estimate"
            ],

        "balanced_accuracy":
            balanced_accuracy,

        "selection_rows":
            156,

        "structural_no_exposure":
            9,

        "period_rows":
            143,

        "stability_series":
            72,

        "stability_decisions":
            720,

        "bootstrap_replicates":
            10000,

        "bootstrap_global_draw_sha256":
            replay[
                "global_draw_stream_sha256"
            ],

        "candidate_promoted":
            False,

        "final_rule":
            "AFINO_0_5_BASELINE",
    }


def main() -> int:

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo-root",
        default=".",
    )

    args = parser.parse_args()

    result = validate(
        Path(
            args.repo_root
        ).resolve()
    )

    print(
        "PHASE3B_DEVELOPMENT_ANALYSIS_VALIDATION_PASS"
    )

    print(
        "baseline_evaluations = 3600"
    )

    print(
        "positive = 1800"
    )

    print(
        "null = 1800"
    )

    for key in (
        "TP",
        "FN",
        "TN",
        "FP",
        "sensitivity",
        "specificity",
        "FPR",
        "balanced_accuracy",
    ):
        print(
            f"{key} = {result[key]}"
        )

    print(
        "wilson_intervals_reconstructed = true"
    )

    print(
        "end_to_end_rows = 9"
    )

    print(
        "inadmissible_recoded_as_FN_or_TN = 0"
    )

    print(
        "selection_function_rows = 156"
    )

    print(
        "selection_function_topology = 36|108|12"
    )

    print(
        "STRUCTURAL_NO_EXPOSURE = 9"
    )

    print(
        "period_recovery_rows = 143"
    )

    print(
        "optimizer_stability_series = 72"
    )

    print(
        "optimizer_stability_decisions = 720"
    )

    print(
        "classification_seed_discordance = 0"
    )

    print(
        "candidate_features = delta_BIC01|delta_BIC21"
    )

    print(
        "candidate_axes = 7200|7200"
    )

    print(
        "bootstrap_replicates = 10000"
    )

    print(
        "bootstrap_pairing_preserved = true"
    )

    print(
        "bootstrap_fixed_rng_replay = true"
    )

    print(
        "bootstrap_global_draw_stream_sha256 =",
        result[
            "bootstrap_global_draw_sha256"
        ],
    )

    print(
        "promotion_criteria = PASS|PASS|PASS|FAIL"
    )

    print(
        "candidate_rule_promoted = false"
    )

    print(
        "runner_up_rescue = FORBIDDEN"
    )

    print(
        "alternate_candidate_search = FORBIDDEN"
    )

    print(
        "final_rule = AFINO_0_5_BASELINE"
    )

    print(
        "final_t01 = 10"
    )

    print(
        "final_t21 = 10"
    )

    print(
        "correction_claim = NOT_ESTABLISHED"
    )

    print(
        "truth_feature_leakage = 0"
    )

    print(
        "stability_extra_classifier_observations = 0"
    )

    print(
        "challenge_classifier_observations = 0"
    )

    print(
        "posthoc_thresholds = 0"
    )

    print(
        "posthoc_bins = 0"
    )

    print(
        "posthoc_comparators = 0"
    )

    print(
        "new_afino_calls = 0"
    )

    print(
        "generator_calls = 0"
    )

    print(
        "heldout_generated = false"
    )

    print(
        "heldout_accessed = false"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
