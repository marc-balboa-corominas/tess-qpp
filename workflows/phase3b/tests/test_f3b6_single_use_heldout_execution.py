from __future__ import annotations

import csv
import json
import math
import unittest

from collections import defaultdict
from pathlib import Path


REPO = (
    Path(__file__)
    .resolve()
    .parents[3]
)

RESULTS = (
    REPO
    / "workflows/phase3b/heldout/execution/evidence/tables/"
      "f3b6_heldout_results_blinded.csv"
)

DECISIONS = (
    REPO
    / "workflows/phase3b/heldout/execution/evidence/tables/"
      "f3b6_heldout_decisions_blinded.csv"
)

TEMPORAL = (
    REPO
    / "workflows/phase3b/heldout/execution/evidence/tables/"
      "f3b6_temporal_contract_diagnostic.csv"
)

AUTH = (
    REPO
    / "workflows/phase3b/heldout/execution/config/"
      "f3b6_single_use_execution_authorization.json"
)

RULE = (
    REPO
    / "workflows/phase3b/development/analysis/"
      "f3b4_final_rule_freeze.json"
)

VALIDATION = (
    REPO
    / "workflows/phase3b/heldout/execution/evidence/reports/"
      "f3b6_validation_audit.json"
)

BOUNDARY = (
    REPO
    / "workflows/phase3b/heldout/execution/evidence/reports/"
      "f3b6_single_use_boundary_audit.json"
)


def rows(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


class TestF3B6SingleUseHeldoutExecution(
    unittest.TestCase
):

    def test_authorization_firewall(self):

        auth = json.loads(
            AUTH.read_text(
                encoding="utf-8"
            )
        )

        p = auth["permissions"]

        self.assertTrue(
            p[
                "heldout_afino_execution_authorized"
            ]
        )

        self.assertFalse(
            p["truth_join_authorized"]
        )

        self.assertFalse(
            p["heldout_metrics_authorized"]
        )

        self.assertFalse(
            p["rule_refitting_authorized"]
        )

        self.assertFalse(
            p["threshold_mutation_authorized"]
        )

        self.assertFalse(
            p["candidate_search_authorized"]
        )


    def test_blinded_result_contract(self):

        rr = rows(RESULTS)

        self.assertEqual(
            len(rr),
            10800,
        )

        self.assertTrue(
            all(
                r["status"] == "OK"
                for r in rr
            )
        )

        forbidden = {
            "truth_state",
            "true_period_s",
            "qpp_fraction",
            "tp",
            "fn",
            "tn",
            "fp",
            "sensitivity",
            "specificity",
            "fpr",
        }

        self.assertFalse(
            forbidden
            & set(rr[0])
        )


    def test_decision_recalculation(self):

        rr = rows(RESULTS)
        dd = rows(DECISIONS)

        rule = json.loads(
            RULE.read_text(
                encoding="utf-8"
            )
        )[
            "final_rule"
        ]

        self.assertEqual(
            float(rule["t01"]),
            10.0,
        )

        self.assertEqual(
            float(rule["t21"]),
            10.0,
        )

        grouped = defaultdict(dict)

        for r in rr:
            grouped[
                r["planned_decision_id"]
            ][
                r["model_id"]
            ] = r

        self.assertEqual(
            len(dd),
            3600,
        )

        for d in dd:

            models = grouped[
                d["planned_decision_id"]
            ]

            self.assertEqual(
                set(models),
                {"M0", "M1", "M2"},
            )

            b0 = float(
                models["M0"]["bic"]
            )

            b1 = float(
                models["M1"]["bic"]
            )

            b2 = float(
                models["M2"]["bic"]
            )

            d01 = b0 - b1
            d21 = b2 - b1

            expected = (
                d01 > 10.0
                and d21 > 10.0
            )

            self.assertTrue(
                math.isclose(
                    float(
                        d[
                            "delta_bic_0_1"
                        ]
                    ),
                    d01,
                    rel_tol=0.0,
                    abs_tol=5e-12,
                )
            )

            self.assertTrue(
                math.isclose(
                    float(
                        d[
                            "delta_bic_2_1"
                        ]
                    ),
                    d21,
                    rel_tol=0.0,
                    abs_tol=5e-12,
                )
            )

            self.assertEqual(
                d["qpp_selected"],
                (
                    "True"
                    if expected
                    else "False"
                ),
            )

            self.assertEqual(
                d["decision_status"],
                "VALID",
            )


    def test_temporal_contract(self):

        tt = rows(TEMPORAL)

        self.assertEqual(
            len(tt),
            3600,
        )

        self.assertTrue(
            all(
                r[
                    "mean_dt_contract_match"
                ]
                == "True"
                for r in tt
            )
        )

        self.assertTrue(
            all(
                r[
                    "positive_fftfreq_contract_match"
                ]
                == "True"
                for r in tt
            )
        )


    def test_validation_audit(self):

        audit = json.loads(
            VALIDATION.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            audit["status"],
            "PASS",
        )

        self.assertEqual(
            audit["validation_result"],
            "PHASE3B_HELDOUT_BLINDED_"
            "EXECUTION_VALIDATION_PASS",
        )

        firewall = audit[
            "blinding_firewall"
        ]

        self.assertFalse(
            firewall[
                "truth_ledger_accessed"
            ]
        )

        self.assertFalse(
            firewall[
                "heldout_metrics_computed"
            ]
        )

        self.assertEqual(
            audit[
                "blind_decisions"
            ][
                "qpp_selected_aggregate"
            ],
            "NOT_COMPUTED",
        )


    def test_single_use_boundary(self):

        audit = json.loads(
            BOUNDARY.read_text(
                encoding="utf-8"
            )
        )

        self.assertTrue(
            audit[
                "heldout_afino_executed"
            ]
        )

        self.assertTrue(
            audit[
                "heldout_rule_applied_blind"
            ]
        )

        self.assertFalse(
            audit[
                "heldout_truth_join_performed"
            ]
        )

        self.assertFalse(
            audit[
                "heldout_metrics_computed"
            ]
        )

        self.assertFalse(
            audit[
                "candidate_search_performed"
            ]
        )

        self.assertFalse(
            audit[
                "thresholds_modified"
            ]
        )

        self.assertFalse(
            audit[
                "rule_refitted"
            ]
        )

        self.assertEqual(
            audit[
                "qpp_selected_aggregate"
            ],
            "NOT_COMPUTED",
        )


if __name__ == "__main__":
    unittest.main()
