from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
F3B_GENERATOR_PATH = ROOT / "workflows/phase3b/scripts/f3b_synthetic_generator.py"
F1_GENERATOR_PATH = ROOT / "foundation/f0-f2/phase1/fase1_tarea02_synthetic_generator.py"
F1_PREREG_PATH = ROOT / "foundation/f0-f2/phase1/fase1_tarea01_core_benchmark_preregistration.json"
F1_AUDIT_PATH = ROOT / "foundation/f0-f2/phase1/fase1_tarea02_generator_validation_audit.json"

ABS_TOL = 5e-12
F1_REFERENCE_CASES = [
    (15, 0.0, 0),
    (15, 2.0, 39),
    (30, 1.0, 17),
    (60, 0.0, 39),
    (120, 2.0, 0),
]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


f3b = _load(F3B_GENERATOR_PATH, "f3b_synthetic_generator_test")
f1 = _load(F1_GENERATOR_PATH, "f1_generator_reference")


def _f1_spec():
    return json.loads(F1_PREREG_PATH.read_text(encoding="utf-8"))


def _alpha_code(specification, alpha: float) -> int:
    mapping = specification["generator"]["noise"]["alpha_code"]
    for key in [str(float(alpha)), format(float(alpha), ".1f"), str(alpha)]:
        if key in mapping:
            return int(mapping[key])
    raise AssertionError(f"Missing alpha code for {alpha}")


@pytest.mark.f1_continuity
@pytest.mark.parametrize("n_samples,alpha,data_seed", F1_REFERENCE_CASES)
def test_f1_generator_continuity_reference_cases(n_samples, alpha, data_seed):
    spec = _f1_spec()
    audit = json.loads(F1_AUDIT_PATH.read_text(encoding="utf-8"))
    cases = {
        (
            int(c["n_samples"]),
            float(c["red_noise_alpha"]),
            int(c["data_seed"]),
        )
        for c in audit["independent_reference"]["cases"]
    }
    assert (n_samples, alpha, data_seed) in cases

    reference = f1.generate_paired_block(n_samples, alpha, data_seed, spec)
    candidate = f3b.f1_compatible_block(
        n_samples,
        alpha,
        data_seed,
        master_seed=int(spec["rng_and_pairing"]["master_seed"]),
        alpha_code=_alpha_code(spec, alpha),
    )

    np.testing.assert_allclose(candidate["time_s"], reference["time_s"], rtol=0, atol=ABS_TOL)
    np.testing.assert_allclose(
        candidate["flare_envelope"], reference["flare_envelope"], rtol=0, atol=ABS_TOL
    )
    np.testing.assert_allclose(candidate["noise"], reference["noise"], rtol=0, atol=ABS_TOL)
    assert math.isclose(
        float(candidate["phase_rad"]),
        float(reference["phase_rad"]),
        rel_tol=0,
        abs_tol=ABS_TOL,
    )

    cand_null = f3b.materialize_null_latent(candidate)
    ref_null = f1.materialize_null(reference, spec)
    np.testing.assert_allclose(cand_null, ref_null, rtol=0, atol=ABS_TOL)

    # 50 s and qpp_fraction=0.02 are present in all five frozen reference cases.
    cand_pos, cand_component = f3b.f1_compatible_positive(candidate, 50.0, 0.02)
    ref_pos = f1.materialize_positive(reference, 50.0, 0.02, spec)
    np.testing.assert_allclose(cand_pos, ref_pos, rtol=0, atol=ABS_TOL)
    np.testing.assert_allclose(
        cand_pos - cand_null, cand_component, rtol=0, atol=ABS_TOL
    )


def test_predraw_binding_constants_do_not_initialize_rng():
    assert f3b.F3B1_BACKGROUND_NAMESPACE == "TESS-QPP:F3B1:v1"
    assert f3b.F3B1_PERIOD_NAMESPACE == "TESS-QPP:F3B1:PERIOD:v1"
    assert f3b.ALLOWED_N_SAMPLES == (15, 30, 60, 120)
    assert f3b.ALLOWED_RED_NOISE_ALPHA == (0.0, 1.0, 2.0)
    assert f3b.ALLOWED_QPP_FRACTION == (0.01, 0.02, 0.04)
    assert f3b.FLOAT64_DTYPE.str == "<f8"
    assert f3b.INT64_DTYPE.str == "<i8"
    assert f3b.BOOL_DTYPE.str == "|b1"
