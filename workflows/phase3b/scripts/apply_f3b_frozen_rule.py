from __future__ import annotations

"""
Frozen F3B rule implementation.

This module contains only the immutable rule that was authorized by
FINAL_RULE_FREEZE.

It does not materialize HELDOUT and does not call AFINO.
"""

import argparse
import math


FINAL_T01 = 10.0
FINAL_T21 = 10.0


def apply_frozen_rule(
    delta_bic_0_1: float,
    delta_bic_2_1: float,
) -> bool:

    d01 = float(delta_bic_0_1)
    d21 = float(delta_bic_2_1)

    if not (
        math.isfinite(d01)
        and math.isfinite(d21)
    ):
        raise ValueError(
            "Frozen-rule inputs must be finite"
        )

    return bool(
        d01 > FINAL_T01
        and d21 > FINAL_T21
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--delta-bic-0-1",
        type=float,
        required=True,
    )
    parser.add_argument(
        "--delta-bic-2-1",
        type=float,
        required=True,
    )
    args = parser.parse_args()

    selected = apply_frozen_rule(
        args.delta_bic_0_1,
        args.delta_bic_2_1,
    )

    print(
        "qpp_selected =",
        str(selected).lower(),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
