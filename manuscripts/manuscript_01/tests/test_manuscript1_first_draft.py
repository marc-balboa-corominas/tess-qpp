from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "manuscripts/manuscript_01/scripts/validate_manuscript1_first_draft.py"

spec = importlib.util.spec_from_file_location("m13_validator", VALIDATOR)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def test_static_validation_passes():
    result = mod.validate_static()
    assert result["main_text_word_count"] == 5725
    assert result["abstract_word_count"] == 212


def test_traceability_counts():
    result = mod.validate_static()
    assert result["scientific_paragraphs"] == 71
    assert result["figure_captions"] == 5
    assert result["claim_usage_rows"] == 76
    assert result["claims_used"] == 27


def test_numeric_traceability_complete():
    result = mod.validate_static()
    assert result["numeric_items"] == 120


def test_bibliography_is_frozen_and_used():
    result = mod.validate_static()
    assert result["citations"] == 8


def test_frozen_visuals_are_integrated_directly():
    result = mod.validate_static()
    assert result["figures"] == 5
    assert result["tables"] == 4


def test_compiled_preprint_is_present():
    result = mod.validate_static()
    assert result["pdf_pages"] == 22


def test_no_prohibited_claim_ids_are_used():
    usage = mod.rows(mod.CLAIM_USAGE)
    used = {c for r in usage for c in mod.split_ids(r["claim_ids"])}
    assert "M1C026" not in used
    assert "M1C027" not in used


def test_correction_and_observational_validation_boundaries():
    audit = mod.json.loads(mod.DRAFT_AUDIT.read_text(encoding="utf-8"))
    assert audit["correction_claim_established"] is False
    assert audit["observational_validation_claimed"] is False


def test_firewalls_remain_closed():
    audit = mod.json.loads(mod.DRAFT_AUDIT.read_text(encoding="utf-8"))
    for key in [
        "new_scientific_computation",
        "new_statistical_inference",
        "new_bibliographic_search",
        "new_afino_execution",
        "new_synthetic_generation",
        "visual_regeneration",
    ]:
        assert audit[key] is False


def test_checksum_registry_covers_exact_m13_universe():
    result = mod.validate_static()
    assert result["claim_usage_rows"] == 76

def test_heldout_validation_scope_is_explicit():
    tex = mod.TEX.read_text(encoding="utf-8")
    assert (
        r"\subsection{Synthetic injection--recovery and synthetic-ground-truth held-out validation}"
        in tex
    )
    assert r"\subsection{Synthetic injection--recovery and held-out validation}" not in tex


def test_pre_freeze_review_incident_is_recorded():
    audit = mod.json.loads(mod.DRAFT_AUDIT.read_text(encoding="utf-8"))
    assert audit["pre_freeze_review_incidents"] == ["M1D-REV-001"]
    assert audit["pre_freeze_review_status"] == "SCOPING_QUALIFIER_REPAIRED_BEFORE_GIT_FREEZE"

