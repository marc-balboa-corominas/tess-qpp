from __future__ import annotations

"""
Phase 3B.4 candidate-rule utilities and read-only frozen-result audit.

The one-shot DEVELOPMENT search has already been consumed and frozen.
The CLI therefore NEVER reruns the scientific search.

Pure helper functions are retained so the frozen algorithm can be unit
tested: threshold-axis construction, optimization ordering, promotion
logic and final-rule branch selection.
"""

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np


ALLOWED_FEATURES = (
    "delta_BIC01",
    "delta_BIC21",
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


def build_threshold_axis(
    values,
) -> np.ndarray:
    """
    Frozen F3B.4 threshold-axis construction.

    finite float64 values
    + adjacent midpoints
    + baseline threshold 10
    -> ascending unique finite float64 axis
    """

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
        raise ValueError(
            "Threshold-axis input contains no finite values"
        )

    midpoints = (
        unique[:-1]
        + (
            unique[1:]
            - unique[:-1]
        )
        / np.float64(2.0)
    )

    axis = np.unique(
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

    if not np.all(
        np.isfinite(axis)
    ):
        raise RuntimeError(
            "Non-finite threshold produced"
        )

    if np.any(
        axis[1:] <= axis[:-1]
    ):
        raise RuntimeError(
            "Threshold axis is not strictly ascending"
        )

    return axis


def candidate_order_key(
    row: dict[str, float],
) -> tuple[float, ...]:
    """
    Lower tuple is better.

    Frozen order:
    1 maximize balanced accuracy
    2 maximize min(sensitivity, specificity)
    3 minimize FPR
    4 minimize L1 distance to (10,10)
    5 maximize t01
    6 maximize t21
    """

    return (
        -float(
            row[
                "balanced_accuracy"
            ]
        ),
        -float(
            row[
                "min_sensitivity_specificity"
            ]
        ),
        float(
            row["FPR"]
        ),
        float(
            row[
                "l1_distance_to_10_10"
            ]
        ),
        -float(
            row["t01"]
        ),
        -float(
            row["t21"]
        ),
    )


def promotion_gate(
    *,
    point_ba_improvement: float,
    lower_delta_ba: float,
    lower_delta_sensitivity: float,
    lower_delta_specificity: float,
) -> tuple[bool, tuple[bool, bool, bool, bool]]:

    criteria = (
        float(
            point_ba_improvement
        ) >= 0.025,

        float(
            lower_delta_ba
        ) > 0.0,

        float(
            lower_delta_sensitivity
        ) > -0.025,

        float(
            lower_delta_specificity
        ) > -0.025,
    )

    return (
        bool(
            all(criteria)
        ),
        criteria,
    )


def choose_final_rule(
    *,
    candidate_promoted: bool,
    candidate_t01: float,
    candidate_t21: float,
) -> dict[str, object]:

    if candidate_promoted:

        return {
            "freeze_state":
                "FINAL_RULE_FREEZE_CANDIDATE",

            "rule_type":
                "TWO_THRESHOLD_BIC_CONJUNCTION",

            "t01":
                float(candidate_t01),

            "t21":
                float(candidate_t21),

            "candidate_rule_promoted":
                True,
        }

    return {
        "freeze_state":
            "FINAL_RULE_FREEZE_BASELINE_ONLY",

        "rule_type":
            "AFINO_0_5_BASELINE",

        "t01":
            10.0,

        "t21":
            10.0,

        "candidate_rule_promoted":
            False,

        "correction_claim":
            "NOT_ESTABLISHED",
    }


def main() -> int:

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo-root",
        default=".",
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
    )

    args = parser.parse_args()

    repo = Path(
        args.repo_root
    ).resolve()

    analysis = (
        repo
        / "workflows"
        / "phase3b"
        / "development"
        / "analysis"
    )

    candidate_rows = read_csv(
        analysis
        / "f3b4_candidate_rule_development.csv"
    )

    gate = json.loads(
        (
            analysis
            / "f3b4_candidate_rule_gate.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    if len(candidate_rows) != 1:
        raise RuntimeError(
            "Candidate CSV rows != 1"
        )

    candidate = candidate_rows[0]

    if (
        candidate[
            "candidate_id"
        ]
        != "DEVELOPMENT_OPTIMUM_001"
    ):
        raise RuntimeError(
            "Unexpected candidate ID"
        )

    allowed = tuple(
        json.loads(
            candidate[
                "allowed_features_json"
            ]
        )
    )

    if allowed != ALLOWED_FEATURES:
        raise RuntimeError(
            "Frozen candidate feature set changed"
        )

    if (
        candidate[
            "comparison_operator"
        ]
        != "STRICT_GREATER_THAN"
    ):
        raise RuntimeError(
            "Frozen candidate comparison changed"
        )

    if (
        candidate[
            "runner_up_rescue"
        ]
        != "FORBIDDEN"
    ):
        raise RuntimeError(
            "Runner-up rescue is not forbidden"
        )

    if int(
        candidate[
            "runner_up_rows_written"
        ]
    ) != 0:
        raise RuntimeError(
            "Runner-up candidate unexpectedly exists"
        )

    if (
        gate["status"]
        != "CANDIDATE_NOT_PROMOTED"
    ):
        raise RuntimeError(
            "Frozen promotion status changed"
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
            "alternate_candidate_search"
        ]
        != "FORBIDDEN"
    ):
        raise RuntimeError(
            "Alternate candidate search is not forbidden"
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
            "HELDOUT exists during candidate validation"
        )

    print(
        "F3B4_CANDIDATE_DEVELOPMENT_READ_ONLY_PASS"
    )

    print(
        "candidate_id = DEVELOPMENT_OPTIMUM_001"
    )

    print(
        "allowed_features = delta_BIC01|delta_BIC21"
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
        "candidate_search_rerun = false"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
