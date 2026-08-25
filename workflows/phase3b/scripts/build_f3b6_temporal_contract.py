from __future__ import annotations

import argparse
import csv
import hashlib
import subprocess

from collections import Counter
from collections import defaultdict
from pathlib import Path

import numpy as np


EXPECTED_HEAD = (
    "faf688a2b8c260cdee0d92c181971d0154df4532"
)

EXPECTED_RESULTS_SHA = (
    "2a55963e4b916a997efa5db5893e1b49"
    "f6a091b536fa6b98099da7733af7fe30"
)

EXPECTED_DECISIONS_SHA = (
    "bc7c8720d9cdeed249301f986bcf960e"
    "f46c2d75ec4e38356a0dfa42ee3b3ab1"
)

EXPECTED_GRID_SHA = (
    "09419a4d5d968d5305f262b5aefe28cd"
    "29bc01cdcf67b53d91e1732c0e15aa34"
)

EXPECTED_PAYLOAD_SHA = (
    "d20b0dac662cf809eb86d5e87d96f35"
    "e236b6ff2fbfb0fa86eeb4da8a49af8b4"
)

EXPECTED_TIME_SHA = (
    "573527515b71d29eadfe20d0b6eb87296"
    "f38f8ec188419a1a4b5fc95dab1d050"
)

EXPECTED_OFFSETS_SHA = (
    "5fd86ec64fe858b3ed665f11a06f4ca7"
    "f054e83c51c6e21cb3339693cb99da64"
)


RESULTS = Path(
    "workflows/phase3b/heldout/execution/evidence/tables/"
    "f3b6_heldout_results_blinded.csv"
)

DECISIONS = Path(
    "workflows/phase3b/heldout/execution/evidence/tables/"
    "f3b6_heldout_decisions_blinded.csv"
)

GRID = Path(
    "workflows/phase3b/heldout/materialization/evidence/tables/"
    "f3b5_heldout_decision_grid.csv"
)

PAYLOAD = Path(
    "workflows/phase3b/heldout/materialization/evidence/tables/"
    "f3b5_heldout_payload_manifest.csv"
)

ARRAY_DIR = Path(
    "data/interim/phase3b/f3b5_heldout"
)

OUT = Path(
    "workflows/phase3b/heldout/execution/evidence/tables/"
    "f3b6_temporal_contract_diagnostic.csv"
)


FIELDS = [
    "planned_decision_id",
    "decision_order",
    "decision_class",
    "simulation_unit_id",
    "external_optimizer_seed",
    "payload_logical_sha256",
    "n_samples",
    "mean_dt_external_s",
    "median_dt_external_s",
    "afino_dt_m0_s",
    "afino_dt_m1_s",
    "afino_dt_m2_s",
    "mean_dt_match_m0",
    "mean_dt_match_m1",
    "mean_dt_match_m2",
    "mean_dt_contract_match",
    "positive_fftfreq_bin_count_external",
    "rfftfreq_positive_bin_count_external",
    "afino_positive_bin_count_m0",
    "afino_positive_bin_count_m1",
    "afino_positive_bin_count_m2",
    "positive_fftfreq_match_m0",
    "positive_fftfreq_match_m1",
    "positive_fftfreq_match_m2",
    "positive_fftfreq_contract_match",
    "legacy_rfftfreq_match_m0",
    "legacy_rfftfreq_match_m1",
    "legacy_rfftfreq_match_m2",
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


def read_csv(path: Path):

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        return list(
            csv.DictReader(f)
        )


def same_float(a, b) -> bool:

    return bool(
        np.isclose(
            float(a),
            float(b),
            atol=5e-12,
            rtol=0.0,
        )
    )


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


    head = subprocess.check_output(
        [
            "git",
            "-C",
            str(repo),
            "rev-parse",
            "HEAD",
        ],
        text=True,
    ).strip()


    if head != EXPECTED_HEAD:
        raise RuntimeError(
            "Unexpected Git HEAD"
        )


    checks = {
        RESULTS:
            EXPECTED_RESULTS_SHA,

        DECISIONS:
            EXPECTED_DECISIONS_SHA,

        GRID:
            EXPECTED_GRID_SHA,

        PAYLOAD:
            EXPECTED_PAYLOAD_SHA,

        ARRAY_DIR / "retained_time_s.npy":
            EXPECTED_TIME_SHA,

        ARRAY_DIR / "retained_offsets.npy":
            EXPECTED_OFFSETS_SHA,
    }


    for rel, expected in checks.items():

        path = repo / rel

        if not path.is_file():
            raise RuntimeError(
                f"Missing frozen input: {rel}"
            )

        actual = sha256_file(
            path
        )

        if actual != expected:
            raise RuntimeError(
                f"Frozen input SHA mismatch: {rel}"
            )


    out = repo / OUT

    if out.exists():
        raise RuntimeError(
            f"Refusing overwrite: {OUT}"
        )


    results = read_csv(
        repo / RESULTS
    )

    decisions = read_csv(
        repo / DECISIONS
    )

    grid = read_csv(
        repo / GRID
    )

    payload = read_csv(
        repo / PAYLOAD
    )


    if len(results) != 10800:
        raise RuntimeError(
            "results != 10800"
        )

    if len(decisions) != 3600:
        raise RuntimeError(
            "decisions != 3600"
        )

    if len(grid) != 3600:
        raise RuntimeError(
            "decision grid != 3600"
        )

    if len(payload) != 4320:
        raise RuntimeError(
            "payload manifest != 4320"
        )


    if Counter(
        row["status"]
        for row in results
    ) != Counter({
        "OK": 10800,
    }):
        raise RuntimeError(
            "Non-OK result exists"
        )


    payload_by_sid = {
        row["simulation_unit_id"]:
            row
        for row in payload
    }


    if len(payload_by_sid) != 4320:
        raise RuntimeError(
            "Duplicate payload simulation_unit_id"
        )


    payload_index = {
        row["simulation_unit_id"]:
            i
        for i, row in enumerate(
            payload
        )
    }


    retained_time = np.load(
        repo
        / ARRAY_DIR
        / "retained_time_s.npy",
        mmap_mode="r",
        allow_pickle=False,
    )

    retained_offsets = np.load(
        repo
        / ARRAY_DIR
        / "retained_offsets.npy",
        mmap_mode="r",
        allow_pickle=False,
    )


    if len(retained_offsets) != 4321:
        raise RuntimeError(
            "retained_offsets length != 4321"
        )


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
                f"Duplicate model: {did} {model}"
            )

        groups[did][model] = row


    temporal_rows = []

    mean_dt_pass = 0
    fft_pass = 0


    for frozen in sorted(
        grid,
        key=lambda row:
            int(
                row["decision_order"]
            ),
    ):

        did = frozen[
            "planned_decision_id"
        ]

        sid = frozen[
            "simulation_unit_id"
        ]

        models = groups.get(
            did,
            {},
        )


        if set(models) != {
            "M0",
            "M1",
            "M2",
        }:
            raise RuntimeError(
                f"Incomplete model trio: {did}"
            )


        manifest = payload_by_sid.get(
            sid
        )

        if manifest is None:
            raise RuntimeError(
                f"Missing payload: {sid}"
            )


        if (
            manifest[
                "logical_payload_sha256"
            ]
            != frozen[
                "payload_logical_sha256"
            ]
        ):
            raise RuntimeError(
                f"Payload/grid hash mismatch: {did}"
            )


        for model in (
            "M0",
            "M1",
            "M2",
        ):

            result = models[
                model
            ]

            if (
                result[
                    "payload_logical_sha256"
                ]
                != frozen[
                    "payload_logical_sha256"
                ]
            ):
                raise RuntimeError(
                    f"Result payload mismatch: {did} {model}"
                )

            if (
                result[
                    "simulation_unit_id"
                ]
                != sid
            ):
                raise RuntimeError(
                    f"Result SID mismatch: {did} {model}"
                )


        offset = int(
            manifest[
                "retained_offset"
            ]
        )

        n_samples = int(
            manifest[
                "retained_length"
            ]
        )

        end = (
            offset
            + n_samples
        )

        index = payload_index[
            sid
        ]


        if (
            int(
                retained_offsets[
                    index
                ]
            )
            != offset
            or
            int(
                retained_offsets[
                    index + 1
                ]
            )
            != end
        ):
            raise RuntimeError(
                f"Offset topology mismatch: {sid}"
            )


        time_seconds = np.asarray(
            retained_time[
                offset:end
            ],
            dtype=float,
        )


        if (
            len(time_seconds)
            != n_samples
            or
            n_samples < 2
            or
            not np.all(
                np.isfinite(
                    time_seconds
                )
            )
        ):
            raise RuntimeError(
                f"Invalid time payload: {sid}"
            )


        dt = np.diff(
            time_seconds
        )

        mean_dt = float(
            np.mean(dt)
        )

        median_dt = float(
            np.median(dt)
        )


        if (
            not np.isfinite(
                mean_dt
            )
            or
            mean_dt <= 0.0
        ):
            raise RuntimeError(
                f"Invalid mean dt: {sid}"
            )


        positive_bins = int(
            np.count_nonzero(
                np.fft.fftfreq(
                    n_samples,
                    d=mean_dt,
                )
                > 0.0
            )
        )


        legacy_rfft_bins = int(
            np.count_nonzero(
                np.fft.rfftfreq(
                    n_samples,
                    d=mean_dt,
                )
                > 0.0
            )
        )


        dt_match = {
            model:
                same_float(
                    models[
                        model
                    ][
                        "afino_effective_dt_s"
                    ],
                    mean_dt,
                )
            for model in (
                "M0",
                "M1",
                "M2",
            )
        }


        fft_match = {
            model:
                int(
                    models[
                        model
                    ][
                        "positive_frequency_bin_count"
                    ]
                )
                == positive_bins
            for model in (
                "M0",
                "M1",
                "M2",
            )
        }


        legacy_match = {
            model:
                int(
                    models[
                        model
                    ][
                        "positive_frequency_bin_count"
                    ]
                )
                == legacy_rfft_bins
            for model in (
                "M0",
                "M1",
                "M2",
            )
        }


        mean_contract = all(
            dt_match.values()
        )

        fft_contract = all(
            fft_match.values()
        )


        mean_dt_pass += int(
            mean_contract
        )

        fft_pass += int(
            fft_contract
        )


        temporal_rows.append({
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
                sid,

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

            "n_samples":
                n_samples,

            "mean_dt_external_s":
                mean_dt,

            "median_dt_external_s":
                median_dt,

            "afino_dt_m0_s":
                models[
                    "M0"
                ][
                    "afino_effective_dt_s"
                ],

            "afino_dt_m1_s":
                models[
                    "M1"
                ][
                    "afino_effective_dt_s"
                ],

            "afino_dt_m2_s":
                models[
                    "M2"
                ][
                    "afino_effective_dt_s"
                ],

            "mean_dt_match_m0":
                dt_match[
                    "M0"
                ],

            "mean_dt_match_m1":
                dt_match[
                    "M1"
                ],

            "mean_dt_match_m2":
                dt_match[
                    "M2"
                ],

            "mean_dt_contract_match":
                mean_contract,

            "positive_fftfreq_bin_count_external":
                positive_bins,

            "rfftfreq_positive_bin_count_external":
                legacy_rfft_bins,

            "afino_positive_bin_count_m0":
                models[
                    "M0"
                ][
                    "positive_frequency_bin_count"
                ],

            "afino_positive_bin_count_m1":
                models[
                    "M1"
                ][
                    "positive_frequency_bin_count"
                ],

            "afino_positive_bin_count_m2":
                models[
                    "M2"
                ][
                    "positive_frequency_bin_count"
                ],

            "positive_fftfreq_match_m0":
                fft_match[
                    "M0"
                ],

            "positive_fftfreq_match_m1":
                fft_match[
                    "M1"
                ],

            "positive_fftfreq_match_m2":
                fft_match[
                    "M2"
                ],

            "positive_fftfreq_contract_match":
                fft_contract,

            "legacy_rfftfreq_match_m0":
                legacy_match[
                    "M0"
                ],

            "legacy_rfftfreq_match_m1":
                legacy_match[
                    "M1"
                ],

            "legacy_rfftfreq_match_m2":
                legacy_match[
                    "M2"
                ],
        })


    if len(temporal_rows) != 3600:
        raise RuntimeError(
            "temporal rows != 3600"
        )


    if mean_dt_pass != 3600:
        raise RuntimeError(
            f"mean-dt contract = {mean_dt_pass}/3600"
        )


    if fft_pass != 3600:
        raise RuntimeError(
            f"positive-fftfreq contract = {fft_pass}/3600"
        )


    out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    with out.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=FIELDS,
            extrasaction="raise",
            lineterminator="\n",
        )

        writer.writeheader()
        writer.writerows(
            temporal_rows
        )


    print(
        "F3B6_TEMPORAL_CONTRACT_PASS"
    )

    print(
        "temporal_rows = 3600"
    )

    print(
        "mean_dt_contract = 3600/3600 PASS"
    )

    print(
        "positive_fftfreq_contract = 3600/3600 PASS"
    )

    print(
        "legacy_rfftfreq = DIAGNOSTIC_ONLY"
    )

    print(
        "truth_join_performed = false"
    )

    print(
        "heldout_metrics_computed = false"
    )

    print(
        "temporal_csv_sha256 =",
        sha256_file(
            out
        ),
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
