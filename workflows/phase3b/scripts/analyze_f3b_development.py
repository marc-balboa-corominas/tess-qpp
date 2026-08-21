from __future__ import annotations

"""
Phase 3B.4 DEVELOPMENT analysis entry point.

This permanent script intentionally does NOT regenerate the frozen
F3B.4 scientific artifacts.

The authoritative DEVELOPMENT analysis was produced and frozen before
FINAL_RULE_FREEZE. This script exposes a read-only reconstruction /
validation entry point over those artifacts.

HELDOUT is explicitly out of scope.
"""

import argparse
import csv
import json
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


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

    evaluation = read_csv(
        analysis
        / "f3b4_baseline_evaluation.csv"
    )

    bootstrap = read_csv(
        analysis
        / "f3b4_paired_bootstrap.csv"
    )

    freeze = json.loads(
        (
            analysis
            / "f3b4_final_rule_freeze.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    if len(evaluation) != 3600:
        raise RuntimeError(
            "F3B.4 baseline evaluation rows != 3600"
        )

    if len(bootstrap) != 10000:
        raise RuntimeError(
            "F3B.4 paired bootstrap rows != 10000"
        )

    if (
        freeze["freeze_state"]
        != "FINAL_RULE_FREEZE_BASELINE_ONLY"
    ):
        raise RuntimeError(
            "Unexpected F3B.4 final freeze state"
        )

    if (
        freeze["final_rule"]["t01"] != 10.0
        or
        freeze["final_rule"]["t21"] != 10.0
    ):
        raise RuntimeError(
            "Frozen F3B.4 thresholds are not 10/10"
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
            "HELDOUT exists during DEVELOPMENT analysis validation"
        )

    print(
        "F3B4_DEVELOPMENT_ANALYSIS_READ_ONLY_PASS"
    )
    print(
        "baseline_evaluations = 3600"
    )
    print(
        "paired_bootstrap_replicates = 10000"
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
        "heldout_generated = false"
    )
    print(
        "heldout_accessed = false"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
