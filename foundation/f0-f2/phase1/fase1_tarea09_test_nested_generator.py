from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np


CASES = [
    (0.0, 0),
    (0.0, 39),
    (1.0, 17),
    (2.0, 0),
    (2.0, 39),
]


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reference_time_and_envelope(specification: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    parent = specification["parent_signal"]
    flare = parent["flare"]
    count = int(specification["parent_noise_and_phase"]["parent_n_samples"])
    cadence = float(parent["cadence_s"])
    time_s = np.arange(count, dtype=np.float64) * cadence
    peak_time = float(flare["t_peak_s"])
    peak = float(flare["flare_peak_excess"])
    rise = float(flare["rise_tau_s"])
    decay = float(flare["decay_tau_s"])
    envelope = np.where(
        time_s <= peak_time,
        peak * np.exp((time_s - peak_time) / rise),
        peak * np.exp(-(time_s - peak_time) / decay),
    ).astype(np.float64, copy=False)
    return time_s, envelope


def reference_parent_fluxes(
    noise: np.ndarray,
    phase_rad: np.float64,
    specification: dict[str, Any],
) -> dict[str, np.ndarray]:
    time_s, envelope = reference_time_and_envelope(specification)
    parent = specification["parent_signal"]
    baseline = float(parent["baseline_flux"])
    output: dict[str, np.ndarray] = {
        "NULL": np.asarray(baseline + envelope + noise, dtype=np.float64)
    }
    fraction = float(parent["qpp"]["qpp_fraction"])
    peak_time = float(parent["flare"]["t_peak_s"])
    for period_value in parent["qpp"]["period_s"]:
        period = float(period_value)
        component = fraction * envelope * np.sin(
            2.0 * np.pi * (time_s - peak_time) / period + phase_rad
        )
        output[f"P{int(period):03d}"] = np.asarray(
            baseline + envelope + component + noise,
            dtype=np.float64,
        )
    return output


def reference_prefix(parent: np.ndarray, n_samples: int) -> np.ndarray:
    # Independent literal extraction: allocate and copy element values explicitly.
    result = np.empty(int(n_samples), dtype="<f8")
    result[:] = np.asarray(parent, dtype=np.float64)[0:int(n_samples)]
    return result


def run_tests(root: Path, main_script: Path) -> dict[str, Any]:
    main = _load_module(main_script, "fase1_tarea09_nested_generator_under_test")
    specification = main.load_nested_preregistration(
        root / "fase1_tarea08_nested_window_preregistration.json",
        expected_sha256=main.EXPECTED_INPUT_HASHES[
            "fase1_tarea08_nested_window_preregistration.json"
        ],
    )
    main.validate_nested_grid(
        root / "fase1_tarea08_nested_window_design_grid.csv",
        specification,
        expected_sha256=main.EXPECTED_INPUT_HASHES[
            "fase1_tarea08_nested_window_design_grid.csv"
        ],
    )
    frozen = main._load_module(
        root / "fase1_tarea02_synthetic_generator.py",
        "fase1_tarea02_generator_for_independent_reference",
    )
    frozen_spec = main._load_frozen_f1_1_specification(root, frozen)

    n_values = [int(value) for value in specification["nested_windows"]["n_samples"]]
    mismatches: list[dict[str, Any]] = []
    exact = 0
    planned = len(CASES) * 3 * len(n_values)

    for alpha, data_seed in CASES:
        block = main.generate_parent_block(
            alpha,
            data_seed,
            specification,
            frozen_generator=frozen,
            frozen_f1_1_specification=frozen_spec,
        )
        main_envelope = main.build_fixed_parent_envelope(specification)
        actual_parents = main.build_parent_fluxes(block, main_envelope, specification)

        # This reference does not call the main envelope, signal or prefix functions.
        reference_parents = reference_parent_fluxes(
            np.asarray(block["noise"], dtype=np.float64),
            np.float64(block["phase_rad"]),
            specification,
        )

        for type_code in ("NULL", "P050", "P080"):
            actual_parent = actual_parents[type_code]["flux"]
            reference_parent = reference_parents[type_code]
            for n_samples in n_values:
                actual_child = main.extract_exact_prefix(actual_parent, n_samples)
                reference_child = reference_prefix(reference_parent, n_samples)
                bytes_equal = (
                    np.ascontiguousarray(actual_child, dtype="<f8").tobytes(order="C")
                    == np.ascontiguousarray(reference_child, dtype="<f8").tobytes(order="C")
                )
                if bytes_equal:
                    exact += 1
                else:
                    mismatches.append(
                        {
                            "alpha": alpha,
                            "data_seed": data_seed,
                            "type_code": type_code,
                            "n_samples": n_samples,
                        }
                    )

    return {
        "cases": [
            {"red_noise_alpha": alpha, "data_seed": seed}
            for alpha, seed in CASES
        ],
        "parent_types_per_case": 3,
        "windows_per_parent": len(n_values),
        "comparisons_planned": planned,
        "comparisons_exact": exact,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "statement": f"{exact}/{planned} independent-code-path comparisons exact",
        "independence_scope": (
            "The reference reuses validated F1.2 noise and phase but implements "
            "parent time, fixed envelope, null/QPP fluxes and prefix extraction "
            "without calling the main construction functions."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--main-script", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = run_tests(args.root.resolve(), args.main_script.resolve())
    if args.json:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        print(result["statement"])
    return 0 if result["mismatch_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
