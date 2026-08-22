from __future__ import annotations

"""
Phase 3B.5 single-use HELDOUT materializer.

The scientific generator is the byte-pinned F3B.2 generator.

The dataset orchestration is mechanically derived at runtime from the
byte-pinned F3B.2 DEVELOPMENT materialize_dataset() implementation.
Only the split boundary is changed:

    DEVELOPMENT rows       -> HELDOUT rows
    HELDOUT firewall       -> DEVELOPMENT firewall
    split literal          -> HELDOUT

No generator mechanics, RNG namespaces, period transform, signal model,
masking, serialization, hashing, admissibility logic, or truth logic are
reimplemented here.

This task DOES NOT import or execute AFINO, apply the final rule, compute
held-out metrics, fit a candidate, or mutate thresholds.
"""

import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


EXPECTED_HEAD = (
    "5e9f62eacfd2c82cc4db5e3c3df48fc3bd6e7565"
)

EXPECTED_AUTH_SHA = (
    "9244c772a88e163d927098fdf0f9b1e44a8814fb7d1cbe1923a57452ed0a7925"
)

EXPECTED_SPLIT_SHA = (
    "2316e09ba061910d360ba0d11aa4a766a3b657f56182bb6ba1c455d2b8120c93"
)

EXPECTED_BINDING_SHA = (
    "b6519f84c0e6aa6b0c86cbd7a66dd79c1de1758e313d96ea4d750ebb212d9946"
)

EXPECTED_GENERATOR_SHA = (
    "d538d53c7845916e29c4dd351b85ae91076d5a342acb5619898788ef5d825d11"
)

EXPECTED_DEV_MATERIALIZER_SHA = (
    "9624db78a8685f042b868ef90b2210a5ccb4e935ed27599e8fa18336333eed44"
)

EXPECTED_MATERIALIZE_FUNCTION_SHA = (
    "a1c89c2b05e85b89b458d7f82e04b94a665d6849781306bd63963e23ed6f1295"
)

EXPECTED_FREEZE_SHA = (
    "e2faffdbb15d6e0fec52ff166e81a2ed58f5665d7d3f9dc43cb8b78f5c0a198c"
)


ARRAY_FILES = (
    "background_noise.npy",
    "background_offsets.npy",
    "latent_flux.npy",
    "latent_offsets.npy",
    "retained_time_s.npy",
    "retained_flux.npy",
    "retained_native_index.npy",
    "retained_offsets.npy",
)


TABLE_MAPPING = {
    "background_manifest": (
        "f3b2_development_background_manifest.csv",
        "f3b5_heldout_background_manifest.csv",
    ),
    "series_manifest": (
        "f3b2_development_series_manifest.csv",
        "f3b5_heldout_series_manifest.csv",
    ),
    "truth_ledger": (
        "f3b2_development_truth_ledger.csv",
        "f3b5_heldout_truth_ledger.csv",
    ),
    "admissibility": (
        "f3b2_development_admissibility.csv",
        "f3b5_heldout_admissibility.csv",
    ),
    "payload_manifest": (
        "f3b2_development_payload_manifest.csv",
        "f3b5_heldout_payload_manifest.csv",
    ),
}


def sha256_file(
    path: Path,
) -> str:

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def sha256_bytes(
    data: bytes,
) -> str:

    return hashlib.sha256(
        data
    ).hexdigest()


def read_csv(
    path: Path,
) -> list[dict[str, str]]:

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        return list(
            csv.DictReader(f)
        )


def csv_fields(
    path: Path,
) -> list[str]:

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        fields = list(
            reader.fieldnames
            or []
        )

    if not fields:
        raise RuntimeError(
            f"No CSV fields in {path}"
        )

    return fields


def load_module(
    path: Path,
    name: str,
):

    spec = (
        importlib.util
        .spec_from_file_location(
            name,
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            f"Unable to load module spec: {path}"
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    sys.modules[name] = module

    spec.loader.exec_module(
        module
    )

    return module


def extract_top_level_function(
    path: Path,
    name: str,
) -> str:

    source = path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source,
        filename=str(path),
    )

    nodes = [
        node
        for node in tree.body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name == name
        )
    ]

    if len(nodes) != 1:
        raise RuntimeError(
            f"Expected exactly one {name}; "
            f"found {len(nodes)}"
        )

    node = nodes[0]

    lines = source.splitlines(
        keepends=True
    )

    return "".join(
        lines[
            node.lineno - 1:
            node.end_lineno
        ]
    )


def derive_heldout_materializer_source(
    development_materializer: Path,
) -> tuple[str, str]:

    source = extract_top_level_function(
        development_materializer,
        "materialize_dataset",
    )

    observed_sha = sha256_bytes(
        source.encode("utf-8")
    )

    if (
        observed_sha
        != EXPECTED_MATERIALIZE_FUNCTION_SHA
    ):
        raise RuntimeError(
            "Frozen DEVELOPMENT materialize_dataset "
            "source hash changed"
        )

    replacements = [
        (
            "def materialize_dataset(",
            "def materialize_heldout_dataset(",
            1,
        ),
        (
            "development_rows",
            "heldout_rows",
            3,
        ),
        (
            "heldout_backgrounds",
            "development_backgrounds",
            2,
        ),
        (
            '"split": "DEVELOPMENT"',
            '"split": "HELDOUT"',
            3,
        ),
        (
            'raise RuntimeError("HELDOUT ID reached DEVELOPMENT materializer.")',
            'raise RuntimeError("DEVELOPMENT ID reached HELDOUT materializer.")',
            1,
        ),
        (
            "Any redraw blocks F3B.2 immediately.",
            "Any redraw blocks F3B.5 immediately.",
            1,
        ),
    ]

    transformed = source

    for old, new, expected_count in replacements:

        actual_count = (
            transformed.count(old)
        )

        if (
            actual_count
            != expected_count
        ):
            raise RuntimeError(
                "Frozen split-boundary source "
                f"replacement mismatch for {old!r}: "
                f"{actual_count} != {expected_count}"
            )

        transformed = (
            transformed.replace(
                old,
                new,
            )
        )

    if (
        "development_rows"
        in transformed
    ):
        raise RuntimeError(
            "DEVELOPMENT rows remain in HELDOUT materializer"
        )

    if (
        "heldout_backgrounds"
        in transformed
    ):
        raise RuntimeError(
            "Old HELDOUT firewall variable remains"
        )

    if (
        '"split": "DEVELOPMENT"'
        in transformed
    ):
        raise RuntimeError(
            "DEVELOPMENT split literal remains"
        )

    if (
        transformed.count(
            '"split": "HELDOUT"'
        )
        != 3
    ):
        raise RuntimeError(
            "HELDOUT split literal count != 3"
        )

    ast.parse(
        transformed
    )

    transformed_sha = (
        sha256_bytes(
            transformed.encode(
                "utf-8"
            )
        )
    )

    return (
        transformed,
        transformed_sha,
    )


def afino_loaded() -> bool:

    return any(
        name == "afino"
        or name.startswith("afino.")
        for name in sys.modules
    )


def verify_environment() -> None:

    if (
        sys.version.split()[0]
        != "3.13.13"
    ):
        raise RuntimeError(
            "Python version != 3.13.13"
        )

    if (
        np.__version__
        != "2.3.5"
    ):
        raise RuntimeError(
            "NumPy version != 2.3.5"
        )

    if (
        sys.byteorder
        != "little"
    ):
        raise RuntimeError(
            "byteorder != little"
        )

    if (
        np.dtype(np.float64).str
        != "<f8"
    ):
        raise RuntimeError(
            "float64 canonical dtype mismatch"
        )

    if (
        np.dtype(np.int64).str
        != "<i8"
    ):
        raise RuntimeError(
            "int64 canonical dtype mismatch"
        )

    if (
        np.dtype(np.bool_).str
        != "|b1"
    ):
        raise RuntimeError(
            "bool canonical dtype mismatch"
        )


def verify_hash(
    path: Path,
    expected: str,
) -> None:

    if not path.is_file():
        raise RuntimeError(
            f"Missing normative file: {path}"
        )

    observed = sha256_file(
        path
    )

    if observed != expected:
        raise RuntimeError(
            f"SHA mismatch: {path}\n"
            f"observed={observed}\n"
            f"expected={expected}"
        )


def verify_registry(
    split_path: Path,
) -> tuple[
    list[dict[str, str]],
    list[dict[str, str]],
    set[str],
    set[str],
]:

    rows = read_csv(
        split_path
    )

    if len(rows) != 8640:
        raise RuntimeError(
            "Split registry rows != 8640"
        )

    split_counts = Counter(
        row["split"]
        for row in rows
    )

    if split_counts != Counter(
        {
            "DEVELOPMENT":
                4320,

            "HELDOUT":
                4320,
        }
    ):
        raise RuntimeError(
            "Split topology mismatch"
        )

    development_rows = [
        row
        for row in rows
        if row["split"]
        == "DEVELOPMENT"
    ]

    heldout_rows = [
        row
        for row in rows
        if row["split"]
        == "HELDOUT"
    ]

    dev_bg = {
        row[
            "background_realization_id"
        ]
        for row
        in development_rows
    }

    held_bg = {
        row[
            "background_realization_id"
        ]
        for row
        in heldout_rows
    }

    if (
        len(dev_bg) != 1800
        or len(held_bg) != 1800
    ):
        raise RuntimeError(
            "Background split topology mismatch"
        )

    if dev_bg & held_bg:
        raise RuntimeError(
            "DEVELOPMENT/HELDOUT background leakage"
        )

    if len({
        row["simulation_unit_id"]
        for row in heldout_rows
    }) != 4320:
        raise RuntimeError(
            "HELDOUT simulation IDs not unique"
        )

    truth_counts = Counter(
        row["truth_state"]
        for row in heldout_rows
    )

    if truth_counts != Counter(
        {
            "SYNTHETIC_QPP_PRESENT":
                2160,

            "SYNTHETIC_QPP_ABSENT":
                2160,
        }
    ):
        raise RuntimeError(
            "HELDOUT truth topology mismatch"
        )

    plane_counts = Counter(
        row["evidence_plane"]
        for row in heldout_rows
    )

    if plane_counts != Counter(
        {
            "SYNTHETIC_GROUND_TRUTH_CLASSIFICATION":
                3600,

            "INPUT_ADMISSIBILITY":
                720,
        }
    ):
        raise RuntimeError(
            "HELDOUT evidence-plane topology mismatch"
        )

    regime_counts = Counter(
        row["gap_quality_regime"]
        for row in heldout_rows
    )

    if regime_counts != Counter(
        {
            "CONTIGUOUS_ALL_GOOD":
                3600,

            "ONE_INTERNAL_NONPEAK_SAMPLE_MASKED":
                360,

            "PEAK_SAMPLE_MASKED":
                360,
        }
    ):
        raise RuntimeError(
            "HELDOUT regime topology mismatch"
        )

    bg_sizes = Counter(
        Counter(
            row[
                "background_realization_id"
            ]
            for row
            in heldout_rows
        ).values()
    )

    if bg_sizes != Counter(
        {
            2:
                1620,

            6:
                180,
        }
    ):
        raise RuntimeError(
            "HELDOUT shared-background topology mismatch"
        )

    return (
        development_rows,
        heldout_rows,
        dev_bg,
        held_bg,
    )


def preflight(
    repo: Path,
) -> dict[str, Any]:

    verify_environment()

    auth_path = (
        repo
        / "workflows/phase3b/heldout/materialization/config/"
          "f3b5_heldout_materialization_authorization.json"
    )

    split_path = (
        repo
        / "workflows/phase3b/design/"
          "f3b1_split_registry.csv"
    )

    binding_path = (
        repo
        / "workflows/phase3b/development/config/"
          "f3b2_generator_implementation_binding.json"
    )

    generator_path = (
        repo
        / "workflows/phase3b/scripts/"
          "f3b_synthetic_generator.py"
    )

    development_materializer = (
        repo
        / "workflows/phase3b/scripts/"
          "materialize_f3b_development.py"
    )

    freeze_path = (
        repo
        / "workflows/phase3b/development/analysis/"
          "f3b4_final_rule_freeze.json"
    )

    array_dir = (
        repo
        / "data/interim/phase3b/"
          "f3b5_heldout"
    )

    legacy_array_dir = (
        repo
        / "data/interim/phase3b/"
          "heldout"
    )

    reference_table_dir = (
        repo
        / "workflows/phase3b/"
          "development/evidence/tables"
    )

    output_table_dir = (
        repo
        / "workflows/phase3b/heldout/"
          "materialization/evidence/tables"
    )

    verify_hash(
        auth_path,
        EXPECTED_AUTH_SHA,
    )

    verify_hash(
        split_path,
        EXPECTED_SPLIT_SHA,
    )

    verify_hash(
        binding_path,
        EXPECTED_BINDING_SHA,
    )

    verify_hash(
        generator_path,
        EXPECTED_GENERATOR_SHA,
    )

    verify_hash(
        development_materializer,
        EXPECTED_DEV_MATERIALIZER_SHA,
    )

    verify_hash(
        freeze_path,
        EXPECTED_FREEZE_SHA,
    )

    auth = json.loads(
        auth_path.read_text(
            encoding="utf-8"
        )
    )

    if (
        auth["status"]
        !=
        "AUTHORIZED_FOR_MATERIALIZATION_ONLY"
    ):
        raise RuntimeError(
            "Authorization status changed"
        )

    permissions = auth[
        "authorization"
    ]

    if (
        permissions[
            "heldout_materialization_authorized"
        ]
        is not True
        or
        permissions[
            "heldout_afino_execution_authorized"
        ]
        is not False
        or
        permissions[
            "heldout_metrics_authorized"
        ]
        is not False
        or
        permissions[
            "rule_refitting_authorized"
        ]
        is not False
        or
        permissions[
            "threshold_mutation_authorized"
        ]
        is not False
        or
        permissions[
            "candidate_search_authorized"
        ]
        is not False
    ):
        raise RuntimeError(
            "Authorization permission firewall changed"
        )

    freeze = json.loads(
        freeze_path.read_text(
            encoding="utf-8"
        )
    )

    rule = freeze[
        "final_rule"
    ]

    if (
        freeze["freeze_state"]
        !=
        "FINAL_RULE_FREEZE_BASELINE_ONLY"
        or
        rule["rule_type"]
        !=
        "AFINO_0_5_BASELINE"
        or
        float(rule["t01"])
        != 10.0
        or
        float(rule["t21"])
        != 10.0
        or
        rule["candidate_rule_promoted"]
        is not False
    ):
        raise RuntimeError(
            "Final rule changed before HELDOUT draw"
        )

    (
        development_rows,
        heldout_rows,
        development_backgrounds,
        heldout_backgrounds,
    ) = verify_registry(
        split_path
    )

    if array_dir.exists():
        raise RuntimeError(
            "Persistent HELDOUT array directory already exists"
        )

    if legacy_array_dir.exists():
        raise RuntimeError(
            "Legacy HELDOUT array directory exists"
        )

    table_fields: dict[
        str,
        list[str],
    ] = {}

    output_paths: dict[
        str,
        Path,
    ] = {}

    for (
        key,
        (
            reference_name,
            output_name,
        ),
    ) in TABLE_MAPPING.items():

        reference_path = (
            reference_table_dir
            / reference_name
        )

        if not reference_path.is_file():
            raise RuntimeError(
                f"Missing DEVELOPMENT schema reference: {reference_path}"
            )

        table_fields[key] = (
            csv_fields(
                reference_path
            )
        )

        output_path = (
            output_table_dir
            / output_name
        )

        if output_path.exists():
            raise RuntimeError(
                f"HELDOUT table already exists: {output_path}"
            )

        output_paths[key] = (
            output_path
        )

    (
        transformed_source,
        transformed_source_sha,
    ) = (
        derive_heldout_materializer_source(
            development_materializer
        )
    )

    if afino_loaded():
        raise RuntimeError(
            "AFINO unexpectedly imported during preflight"
        )

    return {
        "auth_path":
            auth_path,

        "split_path":
            split_path,

        "binding_path":
            binding_path,

        "generator_path":
            generator_path,

        "development_materializer":
            development_materializer,

        "freeze_path":
            freeze_path,

        "array_dir":
            array_dir,

        "reference_table_dir":
            reference_table_dir,

        "output_table_dir":
            output_table_dir,

        "output_paths":
            output_paths,

        "table_fields":
            table_fields,

        "development_rows":
            development_rows,

        "heldout_rows":
            heldout_rows,

        "development_backgrounds":
            development_backgrounds,

        "heldout_backgrounds":
            heldout_backgrounds,

        "transformed_source":
            transformed_source,

        "transformed_source_sha":
            transformed_source_sha,
    }


def write_materialization_tables(
    *,
    dev: Any,
    result: dict[str, Any],
    context: dict[str, Any],
) -> None:

    output_table_dir = (
        context[
            "output_table_dir"
        ]
    )

    output_table_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for key in TABLE_MAPPING:

        rows = result[key]

        fields = (
            context[
                "table_fields"
            ][key]
        )

        output_path = (
            context[
                "output_paths"
            ][key]
        )

        payload = dev.csv_bytes(
            rows,
            fields,
        )

        output_path.write_bytes(
            payload
        )


def validate_materialized_structure(
    result: dict[str, Any],
) -> dict[str, Any]:

    backgrounds = (
        result[
            "background_manifest"
        ]
    )

    series = (
        result[
            "series_manifest"
        ]
    )

    truth = (
        result[
            "truth_ledger"
        ]
    )

    admissibility = (
        result[
            "admissibility"
        ]
    )

    payload = (
        result[
            "payload_manifest"
        ]
    )

    if len(backgrounds) != 1800:
        raise RuntimeError(
            "HELDOUT background manifest != 1800"
        )

    if len(series) != 4320:
        raise RuntimeError(
            "HELDOUT series manifest != 4320"
        )

    if len(truth) != 4320:
        raise RuntimeError(
            "HELDOUT truth ledger != 4320"
        )

    if len(admissibility) != 4320:
        raise RuntimeError(
            "HELDOUT admissibility != 4320"
        )

    if len(payload) != 4320:
        raise RuntimeError(
            "HELDOUT payload manifest != 4320"
        )

    if {
        row["split"]
        for row in backgrounds
    } != {"HELDOUT"}:
        raise RuntimeError(
            "Non-HELDOUT background materialized"
        )

    if {
        row["split"]
        for row in series
    } != {"HELDOUT"}:
        raise RuntimeError(
            "Non-HELDOUT series materialized"
        )

    truth_counts = Counter(
        row["truth_state"]
        for row in series
    )

    if truth_counts != Counter(
        {
            "SYNTHETIC_QPP_PRESENT":
                2160,

            "SYNTHETIC_QPP_ABSENT":
                2160,
        }
    ):
        raise RuntimeError(
            "Materialized HELDOUT truth counts mismatch"
        )

    plane_counts = Counter(
        row["evidence_plane"]
        for row in series
    )

    if plane_counts != Counter(
        {
            "SYNTHETIC_GROUND_TRUTH_CLASSIFICATION":
                3600,

            "INPUT_ADMISSIBILITY":
                720,
        }
    ):
        raise RuntimeError(
            "Materialized evidence-plane counts mismatch"
        )

    regime_counts = Counter(
        row["gap_quality_regime"]
        for row in series
    )

    if regime_counts != Counter(
        {
            "CONTIGUOUS_ALL_GOOD":
                3600,

            "ONE_INTERNAL_NONPEAK_SAMPLE_MASKED":
                360,

            "PEAK_SAMPLE_MASKED":
                360,
        }
    ):
        raise RuntimeError(
            "Materialized regime counts mismatch"
        )

    redraws = sum(
        int(
            row["redraw_count"]
        )
        for row
        in backgrounds
    )

    if redraws != 0:
        raise RuntimeError(
            "HELDOUT redraw_count > 0"
        )

    generation_failures = sum(
        row[
            "generation_status"
        ]
        != "MATERIALIZED"
        for row
        in backgrounds
    )

    input_counts = Counter(
        row["input_state"]
        for row
        in series
    )

    primary_rows = [
        row
        for row in series
        if (
            row["evidence_plane"]
            ==
            "SYNTHETIC_GROUND_TRUTH_CLASSIFICATION"
        )
    ]

    challenge_rows = [
        row
        for row in series
        if (
            row["evidence_plane"]
            ==
            "INPUT_ADMISSIBILITY"
        )
    ]

    primary_input_counts = Counter(
        row["input_state"]
        for row
        in primary_rows
    )

    challenge_input_counts = Counter(
        row["input_state"]
        for row
        in challenge_rows
    )

    reason_counts: Counter[str] = (
        Counter()
    )

    for row in admissibility:

        reasons = str(
            row[
                "all_triggered_reasons"
            ]
        ).strip()

        if not reasons:
            continue

        for reason in (
            reasons.split("|")
        ):
            if reason:
                reason_counts[
                    reason
                ] += 1

    return {
        "generation_failures":
            int(
                generation_failures
            ),

        "redraws":
            int(redraws),

        "input_counts":
            dict(
                sorted(
                    input_counts.items()
                )
            ),

        "primary_input_counts":
            dict(
                sorted(
                    primary_input_counts.items()
                )
            ),

        "challenge_input_counts":
            dict(
                sorted(
                    challenge_input_counts.items()
                )
            ),

        "inadmissibility_reason_counts":
            dict(
                sorted(
                    reason_counts.items()
                )
            ),
    }


def main() -> int:

    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "--repo-root",
        default=".",
    )

    parser.add_argument(
        "--preflight-only",
        action="store_true",
    )

    args = parser.parse_args()

    repo = Path(
        args.repo_root
    ).resolve()

    context = preflight(
        repo
    )

    print(
        "F3B5_HELDOUT_MATERIALIZER_STATIC_PREFLIGHT_PASS"
    )

    print(
        "transformed_materialize_dataset_sha256 =",
        context[
            "transformed_source_sha"
        ],
    )

    print(
        "heldout_registry_rows =",
        len(
            context[
                "heldout_rows"
            ]
        ),
    )

    print(
        "heldout_backgrounds =",
        len(
            context[
                "heldout_backgrounds"
            ]
        ),
    )

    print(
        "generator_imported = false"
    )

    print(
        "stochastic_draws = 0"
    )

    print(
        "afino_imported = false"
    )

    if args.preflight_only:

        print(
            "F3B5_STATIC_PREFLIGHT_ONLY_STOP"
        )

        return 0

    # --------------------------------------------------------
    # AUTHORIZED IMPORTS.
    #
    # Still no AFINO.
    # First RNG use occurs only inside the derived
    # materialize_heldout_dataset call below.
    # --------------------------------------------------------

    dev = load_module(
        context[
            "development_materializer"
        ],
        "_f3b2_development_materializer_reference",
    )

    f3b = load_module(
        context[
            "generator_path"
        ],
        "_f3b2_frozen_generator_for_f3b5",
    )

    if afino_loaded():
        raise RuntimeError(
            "AFINO imported before HELDOUT materialization"
        )

    namespace = dict(
        dev.__dict__
    )

    exec(
        compile(
            context[
                "transformed_source"
            ],
            "<f3b5-derived-heldout-materializer>",
            "exec",
        ),
        namespace,
    )

    heldout_materialize = (
        namespace[
            "materialize_heldout_dataset"
        ]
    )

    print(
        "F3B5_FIRST_HELDOUT_DRAW_START"
    )

    print(
        "materialize_only_split = HELDOUT"
    )

    print(
        "generator_sha256 =",
        EXPECTED_GENERATOR_SHA,
    )

    print(
        "development_materializer_sha256 =",
        EXPECTED_DEV_MATERIALIZER_SHA,
    )

    print(
        "source_materialize_dataset_sha256 =",
        EXPECTED_MATERIALIZE_FUNCTION_SHA,
    )

    print(
        "derived_materializer_sha256 =",
        context[
            "transformed_source_sha"
        ],
    )

    # ========================================================
    # FIRST PERSISTENT HELDOUT STOCHASTIC MATERIALIZATION
    # ========================================================

    result = heldout_materialize(
        repo=repo,
        f3b=f3b,
        heldout_rows=
            context[
                "heldout_rows"
            ],
        development_backgrounds=
            context[
                "development_backgrounds"
            ],
        output_dir=
            context[
                "array_dir"
            ],
        write_arrays=True,
    )

    print(
        "F3B5_FIRST_HELDOUT_DRAW_COMPLETE"
    )

    # Persist the scientific manifests immediately.
    write_materialization_tables(
        dev=dev,
        result=result,
        context=context,
    )

    structure = (
        validate_materialized_structure(
            result
        )
    )

    # Exact inherited roundtrip validator, pointed only at
    # the new physical HELDOUT array directory.
    old_array_dir = dev.ARRAY_DIR

    try:

        dev.ARRAY_DIR = Path(
            "data/interim/phase3b/"
            "f3b5_heldout"
        )

        roundtrip = (
            dev.roundtrip_validate(
                repo=repo,
                f3b=f3b,
                result=result,
            )
        )

    finally:

        dev.ARRAY_DIR = (
            old_array_dir
        )

    counts = result[
        "counts"
    ]

    if (
        int(
            counts[
                "redraw_total"
            ]
        )
        != 0
    ):
        raise RuntimeError(
            "Persistent HELDOUT materialization consumed redraws"
        )

    if (
        int(
            counts[
                "background_rng_initializations"
            ]
        )
        != 1800
        or
        int(
            counts[
                "period_draws"
            ]
        )
        != 1800
        or
        int(
            counts[
                "phase_draws"
            ]
        )
        != 1800
        or
        int(
            counts[
                "noise_draws"
            ]
        )
        != 1800
    ):
        raise RuntimeError(
            "HELDOUT stochastic call counts mismatch"
        )

    if afino_loaded():
        raise RuntimeError(
            "AFINO imported during HELDOUT materialization"
        )

    print(
        "background_rng_initializations =",
        counts[
            "background_rng_initializations"
        ],
    )

    print(
        "period_draws =",
        counts[
            "period_draws"
        ],
    )

    print(
        "phase_draws =",
        counts[
            "phase_draws"
        ],
    )

    print(
        "noise_draws =",
        counts[
            "noise_draws"
        ],
    )

    print(
        "redraws =",
        structure[
            "redraws"
        ],
    )

    print(
        "generation_failures =",
        structure[
            "generation_failures"
        ],
    )

    print(
        "input_state_counts =",
        json.dumps(
            structure[
                "input_counts"
            ],
            sort_keys=True,
        ),
    )

    print(
        "primary_input_state_counts =",
        json.dumps(
            structure[
                "primary_input_counts"
            ],
            sort_keys=True,
        ),
    )

    print(
        "challenge_input_state_counts =",
        json.dumps(
            structure[
                "challenge_input_counts"
            ],
            sort_keys=True,
        ),
    )

    print(
        "inadmissibility_reason_counts =",
        json.dumps(
            structure[
                "inadmissibility_reason_counts"
            ],
            sort_keys=True,
        ),
    )

    print(
        "background_roundtrip_mismatches =",
        roundtrip[
            "background_roundtrip_mismatches"
        ],
    )

    print(
        "series_roundtrip_mismatches =",
        roundtrip[
            "series_roundtrip_mismatches"
        ],
    )

    print(
        "===== F3B5 CORE TABLE SHA256 ====="
    )

    for key in TABLE_MAPPING:

        path = (
            context[
                "output_paths"
            ][key]
        )

        print(
            path
            .relative_to(repo)
            .as_posix(),
            "=",
            sha256_file(path),
        )

    print(
        "===== F3B5 PHYSICAL ARRAY SHA256 ====="
    )

    for filename in ARRAY_FILES:

        path = (
            context[
                "array_dir"
            ]
            / filename
        )

        if not path.is_file():
            raise RuntimeError(
                f"Missing persistent array: {filename}"
            )

        arr = np.load(
            path,
            mmap_mode="r",
            allow_pickle=False,
        )

        print(
            filename,
            "sha256=",
            sha256_file(path),
            "shape=",
            arr.shape,
            "dtype=",
            arr.dtype.str,
        )

    if (
        roundtrip[
            "background_roundtrip_mismatches"
        ]
        != 0
        or
        roundtrip[
            "series_roundtrip_mismatches"
        ]
        != 0
    ):

        print(
            "F3B5_FIRST_DRAW_ROUNDTRIP_FAILURE_PRESERVED"
        )

        print(
            "DO_NOT_RERUN_FIRST_DRAW"
        )

        return 4

    if (
        structure[
            "generation_failures"
        ]
        != 0
    ):

        print(
            "F3B5_FIRST_DRAW_GENERATION_FAILURES_PRESERVED"
        )

        print(
            "DO_NOT_RERUN_FIRST_DRAW"
        )

        return 3

    print(
        "heldout_materialization_performed = true"
    )

    print(
        "heldout_stochastic_truth_generated = true"
    )

    print(
        "heldout_afino_executed = false"
    )

    print(
        "heldout_rule_applied = false"
    )

    print(
        "heldout_metrics_computed = false"
    )

    print(
        "candidate_search_performed = false"
    )

    print(
        "thresholds_modified = false"
    )

    print(
        "rule_refitted = false"
    )

    print(
        "development_reopened_for_tuning = false"
    )

    print(
        "F3B5_FIRST_PERSISTENT_HELDOUT_MATERIALIZATION_PASS"
    )

    print(
        "NEXT = freeze persistent bytes; full rematerialization and blind seed0 plan"
    )

    print(
        "STOP_AFTER_FIRST_HELDOUT_MATERIALIZATION"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
