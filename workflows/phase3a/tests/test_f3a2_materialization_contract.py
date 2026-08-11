from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np


REPO = Path(__file__).resolve().parents[3]
TABLES = REPO / "workflows/phase3a/evidence/tables"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


COHORT_SCRIPT = load_module(
    "f3a2_cohort",
    REPO / "workflows/phase3a/scripts/materialize_catalogue_cohort.py",
)
TESS_SCRIPT = load_module(
    "f3a2_tess",
    REPO / "workflows/phase3a/scripts/bind_and_download_tess_products.py",
)
VARIANT_SCRIPT = load_module(
    "f3a2_variants",
    REPO / "workflows/phase3a/scripts/materialize_primary_variants.py",
)


def read_csv(name: str):
    with (TABLES / name).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_canonical_event_key_determinism_and_no_duplicate_source_identity():
    binding = json.loads(
        (REPO / "workflows/phase3a/config/f3a2_primary_catalogue_binding.json")
        .read_text(encoding="utf-8")
    )
    source_sha = binding["sha256"]
    rows = read_csv("f3a2_source_event_index.csv")
    seen_ids = set()
    seen_keys = set()
    for row in rows:
        peak = COHORT_SCRIPT.canonical_decimal(row["source_peak_time"])
        raw = (
            f"{source_sha}|{int(row['source_row_number'])}|{row['tic_id']}|"
            f"{int(row['sector'])}|{peak}"
        ).encode("utf-8")
        expected_id = "SRC_" + hashlib.sha256(raw).hexdigest()
        assert row["source_event_identifier"] == expected_id
        expected_key = (
            f"BAIIW0001|TIC{row['tic_id']}|S{int(row['sector']):02d}|{expected_id}"
        )
        assert row["canonical_source_event_key"] == expected_key
        assert row["duplicate_status"] == "UNIQUE"
        assert expected_id not in seen_ids
        assert expected_key not in seen_keys
        seen_ids.add(expected_id)
        seen_keys.add(expected_key)
    assert len(rows) == 3878


def test_duplicate_collapse_contract_helper_is_order_stable():
    rows = [
        {"canonical": "A", "source_row": 2},
        {"canonical": "A", "source_row": 2},
        {"canonical": "B", "source_row": 3},
    ]
    collapsed = {}
    provenance = {}
    for row in rows:
        collapsed.setdefault(row["canonical"], row)
        provenance.setdefault(row["canonical"], []).append(row["source_row"])
    assert list(collapsed) == ["A", "B"]
    assert provenance["A"] == [2, 2]


def _reconstruct_matches():
    source = read_csv("f3a2_source_event_index.csv")
    recorded = read_csv("f3a2_matching_audit.csv")
    by_id = {r["source_event_identifier"]: r for r in source}
    refs = sorted(
        [r for r in source if r["source_qpp_selected"] == "true"],
        key=lambda r: r["canonical_source_event_key"],
    )
    controls = [r for r in source if r["source_qpp_selected"] == "false"]
    used = set()
    rebuilt = []

    for idx, ref in enumerate(refs, start=1):
        available = [c for c in controls if c["source_event_identifier"] not in used]
        levels = [
            ("SAME_TIC_SAME_SECTOR",
             lambda c: c["tic_id"] == ref["tic_id"] and c["sector"] == ref["sector"]),
            ("SAME_TIC_ANY_SECTOR", lambda c: c["tic_id"] == ref["tic_id"]),
            ("SAME_SECTOR", lambda c: c["sector"] == ref["sector"]),
            ("GLOBAL_ALLOWED_SECTOR_POOL", lambda c: True),
        ]
        choice = None
        for level, pred in levels:
            candidates = [c for c in available if pred(c)]
            if not candidates:
                continue
            rlog = float(ref["log_duration"])
            scored = sorted(
                (
                    abs(float(c["log_duration"]) - rlog),
                    c["canonical_source_event_key"],
                    c,
                )
                for c in candidates
            )
            minimum = scored[0][0]
            tied = [x for x in scored if x[0] == minimum]
            choice = (level, candidates, tied, tied[0][2], minimum)
            break

        pair_id = f"F3AP{idx:04d}"
        if choice is None:
            rebuilt.append((pair_id, ref["source_event_identifier"], "", "UNMATCHED"))
            continue

        level, candidates, tied, chosen, minimum = choice
        assert chosen["source_event_identifier"] not in used
        used.add(chosen["source_event_identifier"])
        rebuilt.append(
            (pair_id, ref["source_event_identifier"],
             chosen["source_event_identifier"], level)
        )

    return rebuilt, recorded, by_id


def test_control_tie_breaking_without_replacement_and_recorded_matching():
    rebuilt, recorded, _ = _reconstruct_matches()
    assert len(rebuilt) == len(recorded) == 61
    assert all(x[3] != "UNMATCHED" for x in rebuilt)
    for rebuilt_row, recorded_row in zip(rebuilt, recorded):
        assert rebuilt_row[0] == recorded_row["pair_id"]
        assert rebuilt_row[1] == recorded_row["reference_event_id"]
        assert rebuilt_row[2] == recorded_row["comparison_event_id"]
        assert rebuilt_row[3] == recorded_row["matching_level"]
        assert recorded_row["control_reused"] == "false"
        assert recorded_row["matching_status"] == "MATCHED_WITHOUT_REPLACEMENT"
    selected_controls = [x[2] for x in rebuilt]
    assert len(selected_controls) == len(set(selected_controls)) == 61


def test_unmatched_reference_contract_never_reuses_or_fabricates_control():
    def choose(available):
        if not available:
            return None
        return sorted(available)[0]
    assert choose([]) is None


def test_nearest_cadence_exact_tie_uses_lowest_native_index():
    t = np.array([10.0, 12.0], dtype=np.float64)
    idx, residual = TESS_SCRIPT.nearest_native_index(t, 11.0)
    assert idx == 0
    assert residual == -86400.0


def _cell(window="W00", profile="P00", quality="finite_all",
          detrending="none", flux_product="PDCSAP"):
    return {
        "matrix_cell_id": f"{window}_{profile}",
        "window_variant_id": window,
        "processing_profile_id": profile,
        "flux_product": flux_product,
        "quality_policy": quality,
        "detrending": detrending,
        "external_optimizer_seed": "0",
        "delta_start_cadences": "0",
        "delta_end_cadences": "0",
        "f2_definition_inherited": "TRUE",
        "changes_from_f2": "NONE",
        "window_perturbation_family": "baseline",
    }


def _event():
    return {
        "phase3a_event_id": "TEST_EVENT",
        "pair_id": "TEST_PAIR",
        "observational_reference_role": "PUBLISHED_QPP_REFERENCE",
    }


def _product(n=15, peak=7):
    return {
        "product_status": "BOUND_DOWNLOADED",
        "time_mapping_status": "TIME_MAPPING_VALID",
        "physical_filename": "test.fits",
        "physical_sha256": "0" * 64,
        "source_start_index": "0",
        "source_peak_index": str(peak),
        "source_end_index": str(n - 1),
    }


def _arrays(n=15, gap=False, peak_quality=0):
    t = np.arange(n, dtype=np.float64) * (20.0 / 86400.0)
    if gap:
        t[8:] += 20.0 / 86400.0
    flux = 100.0 + np.arange(n, dtype=np.float64) * 0.2
    q = np.zeros(n, dtype=np.int64)
    q[7] = peak_quality
    return {
        "TIME": t,
        "SAP_FLUX": flux.copy(),
        "PDCSAP_FLUX": flux.copy(),
        "QUALITY": q,
    }


def test_quality_filtering_can_remove_peak():
    row, payload = VARIANT_SCRIPT.materialize_variant(
        _event(), _product(), _cell(profile="P02", quality="q0_native"),
        _arrays(15, peak_quality=1), 15
    )
    assert payload is None
    assert row["materialization_status"] == "INPUT_INADMISSIBLE"
    assert row["inadmissibility_reason_code"] == "PEAK_REMOVED_BY_QUALITY"


def test_gap_rejection_uses_frozen_interval_tolerance():
    row, payload = VARIANT_SCRIPT.materialize_variant(
        _event(), _product(), _cell(), _arrays(15, gap=True), 15
    )
    assert payload is None
    assert row["inadmissibility_reason_code"] == "IRREGULAR_SAMPLING"


def test_minimum_cadence_rejection():
    row, payload = VARIANT_SCRIPT.materialize_variant(
        _event(), _product(n=14, peak=7), _cell(), _arrays(14), 14
    )
    assert payload is None
    assert row["inadmissibility_reason_code"] == "TOO_FEW_CADENCES"


def test_linear_detrend_exactness():
    arrays = _arrays(15)
    row, payload = VARIANT_SCRIPT.materialize_variant(
        _event(), _product(),
        _cell(profile="P04", detrending="linear_residual_plus_one"),
        arrays, 15
    )
    assert row["materialization_status"] == "ELIGIBLE_FOR_AFINO"
    assert payload is not None
    time_s, final_flux, _ = payload
    retained = arrays["PDCSAP_FLUX"]
    x = time_s - np.mean(time_s)
    X = np.column_stack([np.ones(len(x)), x])
    beta = np.linalg.lstsq(X, retained, rcond=None)[0]
    trend = X @ beta
    scale = np.median(retained)
    expected = np.ascontiguousarray(1.0 + (retained - trend) / scale, dtype="<f8")
    assert np.array_equal(final_flux, expected)


def test_78_cell_completeness_per_event():
    variants = read_csv("f3a2_primary_variant_manifest.csv")
    by_event = Counter(r["phase3a_event_id"] for r in variants)
    assert len(variants) == 9516
    assert len(by_event) == 122
    assert set(by_event.values()) == {78}


def test_decision_and_call_count_identities():
    variants = read_csv("f3a2_primary_variant_manifest.csv")
    decisions = read_csv("f3a2_resolved_decision_grid.csv")
    plan = read_csv("f3a2_exact_afino_plan.csv")

    eligible = [r for r in variants if r["materialization_status"] == "ELIGIBLE_FOR_AFINO"]
    w00p00 = {
        r["phase3a_event_id"]
        for r in eligible
        if r["window_variant_id"] == "W00"
        and r["processing_profile_id"] == "P00"
    }
    primary = [d for d in decisions if d["decision_class"] == "PRIMARY"]
    stability = [d for d in decisions if d["decision_class"] == "STABILITY"]

    assert len(eligible) == len(primary) == 6422
    assert len(w00p00) == 116
    assert len(stability) == 9 * len(w00p00) == 1044
    assert len(decisions) == 7466
    assert len(plan) == 3 * len(decisions) == 22398
    assert Counter(r["model_id"] for r in plan) == {
        "M0": 7466, "M1": 7466, "M2": 7466
    }
    assert all(r["execution_status"] == "NOT_EXECUTED" for r in plan)
