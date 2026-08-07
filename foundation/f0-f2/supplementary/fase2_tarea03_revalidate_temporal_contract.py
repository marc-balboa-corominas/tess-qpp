#!/usr/bin/env python3
"""Revalidate the F2.3 temporal contract without importing or executing AFINO.

This script is supplementary evidence. It reads only persisted F2.2 arrays,
the completed F2.3 checkpoint/CSVs and the original blocked audit. It verifies
that AFINO 0.5 effective cadence equals the arithmetic mean of persisted
intervals and that its positive-frequency convention excludes Nyquist for
even N.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import sqlite3
import numpy as np

ROOT = Path(__file__).resolve().parent
CUTOFF = 1.0 / 40.0
ATOL = 5e-12


def read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def canonical_hash(values, dtype):
    array = np.ascontiguousarray(values, dtype=np.dtype(dtype))
    return hashlib.sha256(array.tobytes(order="C")).hexdigest()


def main():
    time_values = np.load(
        ROOT / "fase2_tarea02_eligible_time_values.npy",
        allow_pickle=False,
    )
    flux_values = np.load(
        ROOT / "fase2_tarea02_eligible_flux_values.npy",
        allow_pickle=False,
    )
    index_values = np.load(
        ROOT / "fase2_tarea02_eligible_fits_index_values.npy",
        allow_pickle=False,
    )
    offsets = np.load(
        ROOT / "fase2_tarea02_eligible_variant_offsets.npy",
        allow_pickle=False,
    )
    manifest = read_csv(
        ROOT / "fase2_tarea02_observational_variant_manifest.csv"
    )
    results = read_csv(
        ROOT / "fase2_tarea03_observational_canary_results.csv"
    )
    audit = json.loads(
        (
            ROOT
            / "fase2_tarea03_observational_runner_validation_audit.json"
        ).read_text(encoding="utf-8")
    )

    eligible = [
        row for row in manifest
        if row["admissibility_status"] == "ELIGIBLE_FOR_AFINO"
    ]
    eligible.sort(key=lambda row: int(row["eligible_payload_order"]))
    payloads = {}
    for position, row in enumerate(eligible):
        start = int(offsets[position])
        end = int(offsets[position + 1])
        t = np.asarray(time_values[start:end], dtype=np.float64)
        f = np.asarray(flux_values[start:end], dtype=np.float64)
        idx = np.asarray(index_values[start:end], dtype=np.int64)
        assert canonical_hash(t, "<f8") == row["time_sha256"]
        assert canonical_hash(f, "<f8") == row["flux_sha256"]
        assert canonical_hash(idx, "<i8") == row["retained_indices_sha256"]
        payloads[row["variant_id"]] = t

    assert len(results) == 84
    assert {row["status"] for row in results} == {"OK"}
    assert audit["resume_test"]["completed_sequence"] == [31, 53, 0]
    assert audit["exact_replay"]["passed_count"] == 6

    dt_passed = 0
    bins_passed = 0
    for row in results:
        t = payloads[row["variant_id"]]
        mean_dt = float(np.mean(np.diff(t)))
        observed_dt = float(row["afino_effective_dt_s"])
        if math.isclose(
            observed_dt,
            mean_dt,
            rel_tol=0.0,
            abs_tol=ATOL,
        ):
            dt_passed += 1
        positive = np.fft.fftfreq(len(t), d=mean_dt)
        positive = positive[positive > 0.0]
        expected_bins = int(np.count_nonzero(positive < CUTOFF))
        if (
            int(row["positive_frequency_bin_count"]) == len(positive)
            and int(row["post_cutoff_bin_count"]) == expected_bins
        ):
            bins_passed += 1

    if dt_passed != 84 or bins_passed != 84:
        raise RuntimeError(
            f"Temporal revalidation failed: dt={dt_passed}, "
            f"bins={bins_passed}."
        )

    print("F2.3 temporal contract revalidated without AFINO")
    print("afino_imported: false")
    print("afino_executed: false")
    print("effective_dt_mean_matches: 84/84")
    print("positive_frequency_bin_matches: 84/84")
    print(
        "conclusion: "
        "OBSERVATIONAL_RUNNER_VALIDATED_WITH_DOCUMENTED_LIMITATION"
    )


if __name__ == "__main__":
    main()
