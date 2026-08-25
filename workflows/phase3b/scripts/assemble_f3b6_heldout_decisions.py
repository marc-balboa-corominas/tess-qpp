from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


EXPECTED_HEAD = (
    "faf688a2b8c260cdee0d92c181971d0154df4532"
)

EXPECTED_RESULTS_SHA256 = (
    "2a55963e4b916a997efa5db5893e1b49"
    "f6a091b536fa6b98099da7733af7fe30"
)

EXPECTED_DECISION_GRID_SHA256 = (
    "09419a4d5d968d5305f262b5aefe28cd"
    "29bc01cdcf67b53d91e1732c0e15aa34"
)

EXPECTED_FINAL_RULE_SHA256 = (
    "e2faffdbb15d6e0fec52ff166e81a2ed"
    "58f5665d7d3f9dc43cb8b78f5c0a198c"
)

RESULTS_REL = Path(
    "workflows/phase3b/heldout/execution/evidence/tables/"
    "f3b6_heldout_results_blinded.csv"
)

DECISIONS_REL = Path(
    "workflows/phase3b/heldout/execution/evidence/tables/"
    "f3b6_heldout_decisions_blinded.csv"
)

DECISION_GRID_REL = Path(
    "workflows/phase3b/heldout/materialization/evidence/tables/"
    "f3b5_heldout_decision_grid.csv"
)

FINAL_RULE_REL = Path(
    "workflows/phase3b/development/analysis/"
    "f3b4_final_rule_freeze.json"
)


FORBIDDEN_COLUMNS = {
    "truth_state",
    "true_period_s",
    "qpp_fraction",
    "red_noise_alpha",
    "qpp_phase_rad",
    "signal_family",
    "candidate_rule",
    "candidate_threshold",
    "tp",
    "tn",
    "fp",
    "fn",
    "sensitivity",
    "specificity",
    "balanced_accuracy",
    "fpr",
}


DECISION_FIELDS = [
    "planned_decision_id",
    "decision_order",
    "decision_class",
    "simulation_unit_id",
    "background_realization_id",
    "external_optimizer_seed",
    "payload_logical_sha256",
    "decision_status",
    "valid_models",
    "bic_m0",
    "bic_m1",
    "bic_m2",
    "delta_bic_0_1",
    "delta_bic_2_1",
    "qpp_selected",
    "formal_m1_period_s",
    "period_label",
    "result_core_m0_sha256",
    "result_core_m1_sha256",
    "result_core_m2_sha256",
]


def sha256_file(path: Path) -> str:

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def git_text(
    repo: Path,
    *args: str,
) -> str:

    cp = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            *args,
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if cp.returncode != 0:
        raise RuntimeError(
            "git failed: "
            + cp.stderr.strip()
        )

    return cp.stdout.strip()


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


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:

    if path.exists():
        raise RuntimeError(
            f"Refusing overwrite: {path}"
        )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = path.with_suffix(
        path.suffix + ".tmp"
    )

    with tmp.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=DECISION_FIELDS,
            extrasaction="raise",
            lineterminator="\n",
        )

        writer.writeheader()
        writer.writerows(rows)

    tmp.replace(path)


def finite_float(
    value: Any,
    label: str,
) -> float:

    x = float(value)

    if not math.isfinite(x):
        raise RuntimeError(
            f"Non-finite {label}: {value!r}"
        )

    return x


def load_rule(
    path: Path,
) -> tuple[float, float]:

    if (
        sha256_file(path)
        != EXPECTED_FINAL_RULE_SHA256
    ):
        raise RuntimeError(
            "Frozen final-rule SHA mismatch"
        )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if (
        payload.get("freeze_state")
        != "FINAL_RULE_FREEZE_BASELINE_ONLY"
    ):
        raise RuntimeError(
            "Final-rule freeze state changed"
        )

    if (
        payload.get("status")
        != "FINAL_RULE_FROZEN"
    ):
        raise RuntimeError(
            "Final-rule status changed"
        )

    rule = payload.get(
        "final_rule",
        {},
    )

    if (
        rule.get("rule_type")
        != "AFINO_0_5_BASELINE"
    ):
        raise RuntimeError(
            "Final-rule type changed"
        )

    if (
        rule.get("comparison_operator")
        != "STRICT_GREATER_THAN"
    ):
        raise RuntimeError(
            "Final-rule comparator changed"
        )

    if (
        rule.get("selection_rule")
        !=
        "delta_BIC01 > 10 AND "
        "delta_BIC21 > 10"
    ):
        raise RuntimeError(
            "Final-rule expression changed"
        )

    t01 = finite_float(
        rule.get("t01"),
        "t01",
    )

    t21 = finite_float(
        rule.get("t21"),
        "t21",
    )

    if (
        t01 != 10.0
        or t21 != 10.0
    ):
        raise RuntimeError(
            "Frozen thresholds changed"
        )

    return t01, t21


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

    if (
        git_text(
            repo,
            "rev-parse",
            "HEAD",
        )
        != EXPECTED_HEAD
    ):
        raise RuntimeError(
            "Unexpected Git HEAD"
        )

    results_path = (
        repo / RESULTS_REL
    )

    decisions_path = (
        repo / DECISIONS_REL
    )

    grid_path = (
        repo / DECISION_GRID_REL
    )

    rule_path = (
        repo / FINAL_RULE_REL
    )

    if (
        sha256_file(results_path)
        != EXPECTED_RESULTS_SHA256
    ):
        raise RuntimeError(
            "Blinded-results SHA mismatch"
        )

    if (
        sha256_file(grid_path)
        != EXPECTED_DECISION_GRID_SHA256
    ):
        raise RuntimeError(
            "Frozen decision-grid SHA mismatch"
        )

    t01, t21 = load_rule(
        rule_path
    )

    results, result_fields = (
        read_csv(
            results_path
        )
    )

    grid, _ = read_csv(
        grid_path
    )

    leaked = (
        FORBIDDEN_COLUMNS
        & set(result_fields)
    )

    if leaked:
        raise RuntimeError(
            "Forbidden columns in results: "
            + ",".join(
                sorted(leaked)
            )
        )

    if len(results) != 10800:
        raise RuntimeError(
            "Blinded results != 10800"
        )

    if len(grid) != 3600:
        raise RuntimeError(
            "Decision grid != 3600"
        )

    if Counter(
        row["status"]
        for row in results
    ) != Counter({
        "OK": 10800,
    }):
        raise RuntimeError(
            "Results are not 10800/10800 OK"
        )

    if Counter(
        row["model_id"]
        for row in results
    ) != Counter({
        "M0": 3600,
        "M1": 3600,
        "M2": 3600,
    }):
        raise RuntimeError(
            "Model counts mismatch"
        )

    grid_by_id = {}

    for row in grid:

        did = row[
            "planned_decision_id"
        ]

        if did in grid_by_id:
            raise RuntimeError(
                "Duplicate decision-grid ID"
            )

        if (
            row["decision_class"]
            != "BASELINE"
        ):
            raise RuntimeError(
                "Non-BASELINE HELDOUT decision"
            )

        if (
            row["planned_model_calls"]
            != "3"
        ):
            raise RuntimeError(
                "planned_model_calls != 3"
            )

        if (
            row["execution_status"]
            != "NOT_EXECUTED"
        ):
            raise RuntimeError(
                "Frozen grid mutated"
            )

        grid_by_id[did] = row

    groups = defaultdict(dict)

    for row in results:

        did = row[
            "planned_decision_id"
        ]

        model = row[
            "model_id"
        ]

        if model in groups[did]:
            raise RuntimeError(
                f"Duplicate {model} in {did}"
            )

        groups[did][model] = row

    if (
        set(groups)
        != set(grid_by_id)
    ):
        raise RuntimeError(
            "Result/grid decision IDs differ"
        )

    decisions = []

    for frozen in sorted(
        grid,
        key=lambda row:
            int(
                row[
                    "decision_order"
                ]
            ),
    ):

        did = frozen[
            "planned_decision_id"
        ]

        models = groups[did]

        if set(models) != {
            "M0",
            "M1",
            "M2",
        }:
            raise RuntimeError(
                f"Incomplete models: {did}"
            )

        for model in (
            "M0",
            "M1",
            "M2",
        ):

            row = models[model]

            for field in (
                "planned_decision_id",
                "decision_class",
                "simulation_unit_id",
                "background_realization_id",
                "external_optimizer_seed",
                "payload_logical_sha256",
            ):

                if (
                    row[field]
                    != frozen[field]
                ):
                    raise RuntimeError(
                        f"Grid/result mismatch: "
                        f"{did} {model} {field}"
                    )

        b0 = finite_float(
            models["M0"]["bic"],
            f"{did} M0 BIC",
        )

        b1 = finite_float(
            models["M1"]["bic"],
            f"{did} M1 BIC",
        )

        b2 = finite_float(
            models["M2"]["bic"],
            f"{did} M2 BIC",
        )

        d01 = b0 - b1
        d21 = b2 - b1

        selected = bool(
            d01 > t01
            and d21 > t21
        )

        period_raw = (
            models["M1"]
            .get(
                "formal_m1_period_s",
                "",
            )
        )

        if period_raw in (
            None,
            "",
        ):

            period = ""

            period_label = (
                "unavailable_"
                "incomplete_numerical"
            )

        else:

            period = finite_float(
                period_raw,
                f"{did} formal period",
            )

            period_label = (
                "recovered_period_selected"
                if selected
                else
                "formal_m1_center_not_selected"
            )

        decisions.append({
            "planned_decision_id":
                did,

            "decision_order":
                int(
                    frozen[
                        "decision_order"
                    ]
                ),

            "decision_class":
                frozen[
                    "decision_class"
                ],

            "simulation_unit_id":
                frozen[
                    "simulation_unit_id"
                ],

            "background_realization_id":
                frozen[
                    "background_realization_id"
                ],

            "external_optimizer_seed":
                int(
                    frozen[
                        "external_optimizer_seed"
                    ]
                ),

            "payload_logical_sha256":
                frozen[
                    "payload_logical_sha256"
                ],

            "decision_status":
                "VALID",

            "valid_models":
                3,

            "bic_m0":
                b0,

            "bic_m1":
                b1,

            "bic_m2":
                b2,

            "delta_bic_0_1":
                d01,

            "delta_bic_2_1":
                d21,

            "qpp_selected":
                selected,

            "formal_m1_period_s":
                period,

            "period_label":
                period_label,

            "result_core_m0_sha256":
                models[
                    "M0"
                ][
                    "result_core_sha256"
                ],

            "result_core_m1_sha256":
                models[
                    "M1"
                ][
                    "result_core_sha256"
                ],

            "result_core_m2_sha256":
                models[
                    "M2"
                ][
                    "result_core_sha256"
                ],
        })

    if len(decisions) != 3600:
        raise RuntimeError(
            "Blind decisions != 3600"
        )

    if Counter(
        row["decision_status"]
        for row in decisions
    ) != Counter({
        "VALID": 3600,
    }):
        raise RuntimeError(
            "Not 3600/3600 VALID"
        )

    if (
        FORBIDDEN_COLUMNS
        & set(
            DECISION_FIELDS
        )
    ):
        raise RuntimeError(
            "Forbidden decision schema"
        )

    write_csv(
        decisions_path,
        decisions,
    )

    reread, fields = read_csv(
        decisions_path
    )

    if (
        len(reread) != 3600
        or fields != DECISION_FIELDS
    ):
        raise RuntimeError(
            "Decision CSV round-trip mismatch"
        )

    print(
        "F3B6_BLINDED_DECISION_ASSEMBLY_PASS"
    )

    print(
        "blind_decisions = 3600"
    )

    print(
        "decision_status_VALID = 3600"
    )

    print(
        "valid_models_per_decision = 3"
    )

    print(
        "final_rule_freeze = "
        "FINAL_RULE_FREEZE_BASELINE_ONLY"
    )

    print(
        "comparison = "
        "STRICT_GREATER_THAN"
    )

    print("t01 = 10.0")
    print("t21 = 10.0")

    # Deliberately do not aggregate qpp_selected.
    print(
        "qpp_selected_aggregate = "
        "NOT_COMPUTED"
    )

    print(
        "truth_columns_in_decisions = 0"
    )

    print(
        "truth_join_performed = false"
    )

    print(
        "heldout_metrics_computed = false"
    )

    print(
        "decisions_csv_sha256 =",
        sha256_file(
            decisions_path
        ),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
