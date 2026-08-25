from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EVAL = REPO / "workflows/phase3b/heldout/evaluation"
AUTH = EVAL / "config/f3b7_single_use_unblinding_authorization.json"
BIND = EVAL / "config/f3b7_evaluation_input_binding.json"
REG = EVAL / "evidence/reports/f3b7_development_evaluator_regression_audit.json"
FINAL_GATE = EVAL / "evidence/reports/f3b7_heldout_validation_gate.json"
SINGLE = EVAL / "evidence/reports/f3b7_single_use_evaluation_audit.json"

class TestF3B7HeldoutEvaluation(unittest.TestCase):
    def test_binding_and_authorization(self):
        bind = json.loads(BIND.read_text(encoding="utf-8"))
        auth = json.loads(AUTH.read_text(encoding="utf-8"))
        self.assertEqual(bind["phase"], "F3B.7")
        self.assertTrue(bind["blind_execution_freeze_verified"])
        self.assertTrue(bind["final_rule_freeze_verified"])
        self.assertEqual(bind["final_rule"]["t01"], 10)
        self.assertEqual(bind["final_rule"]["t21"], 10)
        p = auth["permissions"]
        self.assertTrue(p["truth_join_authorized"])
        self.assertTrue(p["heldout_metrics_authorized"])
        self.assertFalse(p["new_afino_execution_authorized"])
        self.assertFalse(p["generator_execution_authorized"])
        self.assertFalse(p["candidate_search_authorized"])
        self.assertFalse(p["threshold_mutation_authorized"])
        self.assertFalse(p["rule_refitting_authorized"])
        self.assertFalse(p["development_retuning_authorized"])

    def test_development_regression(self):
        audit = json.loads(REG.read_text(encoding="utf-8"))
        self.assertEqual(audit["result"], "F3B7_DEVELOPMENT_EVALUATOR_REGRESSION_PASS")
        d = audit["development"]
        self.assertEqual((d["TP"], d["FN"], d["TN"], d["FP"]), (143, 1657, 1799, 1))
        self.assertEqual(d["selection_function_rows"], 156)
        self.assertEqual(d["STRUCTURAL_NO_EXPOSURE"], 9)
        self.assertEqual(d["period_rows"], 143)
        self.assertEqual(d["metric_mismatches"], 0)
        self.assertEqual(d["selection_function_mismatches"], 0)
        self.assertEqual(d["period_recovery_mismatches"], 0)
        self.assertFalse(audit["heldout_truth_content_read"])
        self.assertEqual(audit["new_afino_calls"], 0)
        self.assertEqual(audit["generator_calls"], 0)

    def test_code_firewall(self):
        src = (REPO / "workflows/phase3b/scripts/evaluate_f3b_heldout.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("import afino", src)
        self.assertNotIn("f3b_synthetic_generator", src)
        self.assertIn("heldout_truth_consumed.json", src)
        self.assertIn("development-regression", src)
        self.assertIn("heldout-evaluate", src)

    def test_final_gate_if_present(self):
        if not FINAL_GATE.exists():
            self.skipTest("HELDOUT not unblinded yet")
        gate = json.loads(FINAL_GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["branch"], "BASELINE_ONLY")
        self.assertEqual(gate["status"], "HELDOUT_BASELINE_CHARACTERIZATION_SUCCESS")
        self.assertEqual(gate["correction_claim"], "NOT_ESTABLISHED")

    def test_single_use_audit_if_present(self):
        if not SINGLE.exists():
            self.skipTest("HELDOUT not unblinded yet")
        audit = json.loads(SINGLE.read_text(encoding="utf-8"))
        self.assertTrue(audit["heldout_single_use_consumed"])
        self.assertEqual(audit["new_afino_calls"], 0)
        self.assertEqual(audit["generator_calls"], 0)
        self.assertFalse(audit["candidate_search_performed"])
        self.assertFalse(audit["thresholds_modified"])
        self.assertFalse(audit["rule_refitted"])

if __name__ == "__main__":
    unittest.main()
