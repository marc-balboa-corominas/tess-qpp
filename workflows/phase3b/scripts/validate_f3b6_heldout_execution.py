from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sqlite3
import subprocess

from collections import Counter
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


EXPECTED_HEAD = (
    "faf688a2b8c260cdee0d92c181971d0154df4532"
)

EXPECTED_CHECKPOINT_SHA = (
    "f652555516bf830b82a23c1911a47d8c"
    "e72e2851b11b97b11614c23c6f944945"
)

EXPECTED_RESULTS_SHA = (
    "2a55963e4b916a997efa5db5893e1b49"
    "f6a091b536fa6b98099da7733af7fe30"
)

EXPECTED_DECISIONS_SHA = (
    "bc7c8720d9cdeed249301f986bcf960e"
    "f46c2d75ec4e38356a0dfa42ee3b3ab1"
)

EXPECTED_TEMPORAL_SHA = (
    "1f15cc39f147e923d89697d400d3979a"
    "73e168ab3096daaac5678e7f30da715f"
)

EXPECTED_ADAPTER_SHA = (
    "dc270bcc8576f7eb82e5efb013ab95c7"
    "c975712ef4274f446f82d208f690c719"
)

EXPECTED_ASSEMBLER_SHA = (
    "f69e602f0925db750cdbaa6140cb8a1d"
    "5e42137d7e0d3a2a43835852bebd7fe5"
)

EXPECTED_TEMPORAL_SCRIPT_SHA = (
    "234cc51faac18b84d9be91476a6b21cd"
    "0e31d4a1d155108721af019ad819f0c7"
)

EXPECTED_BINDING_SHA = (
    "23c897ef0ea24f45c32cb3b382da98e8"
    "c914018c1438ba6ea725a848510219bd"
)

EXPECTED_AUTH_SHA = (
    "4924a1589932e67d132b79321c55c6d8"
    "1b124afc790a65ac7c8883c55fd8daa5"
)

EXPECTED_INCIDENT_SHA = (
    "966ee1ad8540a1f60e0f84828596cd2d"
    "ca0137242433aaef8991ce814fbaf7c9"
)

EXPECTED_PLAN_SHA = (
    "0b59e2f4ab4e1f3a1064b2281a9a428b"
    "117a7b258102e237702deee86171f2f9"
)

EXPECTED_GRID_SHA = (
    "09419a4d5d968d5305f262b5aefe28cd"
    "29bc01cdcf67b53d91e1732c0e15aa34"
)

EXPECTED_PAYLOAD_SHA = (
    "d20b0dac662cf809eb86d5e87d96f35"
    "e236b6ff2fbfb0fa86eeb4da8a49af8b4"
)

EXPECTED_FINAL_RULE_SHA = (
    "e2faffdbb15d6e0fec52ff166e81a2ed"
    "58f5665d7d3f9dc43cb8b78f5c0a198c"
)

EXPECTED_F3B3_RUNNER_SHA = (
    "4d5b68cdda60abd7f3a4380abf63d1b0"
    "b5e9f4e5889caf22ff85f95b31d813bc"
)

EXPECTED_F3B3_BINDING_SHA = (
    "1105199deead4782b76008d4a7c1ba63"
    "6f7b3898a4808bb76585909d1bbe85c9"
)

EXPECTED_DEV_REGRESSION_SHA = (
    "3c9b383207271ee5edb16a06bb473d4d2"
    "af48bba0e7f27ae0df9e8402c6981bc"
)

EXPECTED_F3B5_COMMIT = (
    "690b54212ffc91d5d396da02db2bcd883b359e6b"
)

EXPECTED_DERIVED_LOADER_SHA = (
    "49c49f58fb34cac1607581c01103c880"
    "07686a69a43ec630933c2bf4c5280488"
)

EXPECTED_AFINO_VERSION = "0.5"

EXPECTED_AFINO_COMMIT = (
    "6aceac9518fc8056052807e666da9d0c8bebb010"
)

EXPECTED_CUTOFF = 0.025


ARRAY_SHA = {

    "background_noise.npy":
        "26dc41dc0a280d92b45ed116f79060d547b7c1bc3d5673df6abb9def9bb8f794",

    "background_offsets.npy":
        "8e0f77105f1fd3a13580adcd2c4dcbf5b09de5e32dbfd906795014a9d8f0be2c",

    "latent_flux.npy":
        "5cdaff08c31f10c717de4b55f148c8af2e2333711fdaf0715e213403d8ce9758",

    "latent_offsets.npy":
        "aba31f5bf921b48a046037b8ab09474edcd3136c2b405ed84b0f6e011867dd5c",

    "retained_flux.npy":
        "f8e8fa86f9a307ef78bd34b153752078110b9461d8d172b7ec0d3e9425edebc6",

    "retained_native_index.npy":
        "c0b19f204fecad603c0d8b63bfe0a0643cb57ea74694d4f8849e443786072e4c",

    "retained_offsets.npy":
        "5fd86ec64fe858b3ed665f11a06f4ca7f054e83c51c6e21cb3339693cb99da64",

    "retained_time_s.npy":
        "573527515b71d29eadfe20d0b6eb87296f38f8ec188419a1a4b5fc95dab1d050",
}


MODEL_NAMES = {
    "M0": "pow_const",
    "M1": "pow_const_gauss",
    "M2": "bpow_const",
}


CORE_FIELDS = [
    "job_id",
    "job_order",
    "planned_decision_id",
    "decision_class",
    "simulation_unit_id",
    "background_realization_id",
    "external_optimizer_seed",
    "model_id",
    "model_name",
    "payload_logical_sha256",
    "status",
    "bic",
    "log_likelihood",
    "parameters_json",
    "formal_m1_period_s",
    "rchi2",
    "probability",
    "warning_count",
    "warning_types_json",
    "warnings_json",
    "parameter_at_bound",
    "bound_parameters_json",
    "convergence_status",
    "afino_effective_dt_s",
    "positive_frequency_bin_count",
    "post_cutoff_bin_count",
    "minimum_frequency_hz",
    "maximum_frequency_hz",
    "afino_version",
    "afino_commit",
    "error",
]


RESULT_FORBIDDEN = {
    "truth_state",
    "true_period_s",
    "qpp_fraction",
    "red_noise_alpha",
    "qpp_phase_rad",
    "signal_family",
    "qpp_selected",
    "delta_bic_0_1",
    "delta_bic_2_1",
    "candidate_rule",
    "candidate_threshold",
    "tp",
    "tn",
    "fp",
    "fn",
    "sensitivity",
    "specificity",
    "balanced_accuracy",
    "fpr",
    "selection_function",
    "period_recovery",
}


TRUTH_OR_METRIC_FORBIDDEN = {
    "truth_state",
    "true_period_s",
    "qpp_fraction",
    "red_noise_alpha",
    "qpp_phase_rad",
    "signal_family",
    "synthetic_ground_truth_known",
    "qpp_component_present",
    "truth_source",
    "truth_sha256",
    "tp",
    "tn",
    "fp",
    "fn",
    "sensitivity",
    "specificity",
    "balanced_accuracy",
    "fpr",
    "selection_function",
    "period_recovery",
    "candidate_rule",
    "candidate_threshold",
}


P = {

    "checkpoint":
        Path(
            "runtime/phase3b/f3b6/"
            "heldout_checkpoint.sqlite"
        ),

    "results":
        Path(
            "workflows/phase3b/heldout/execution/"
            "evidence/tables/"
            "f3b6_heldout_results_blinded.csv"
        ),

    "decisions":
        Path(
            "workflows/phase3b/heldout/execution/"
            "evidence/tables/"
            "f3b6_heldout_decisions_blinded.csv"
        ),

    "temporal":
        Path(
            "workflows/phase3b/heldout/execution/"
            "evidence/tables/"
            "f3b6_temporal_contract_diagnostic.csv"
        ),

    "adapter":
        Path(
            "workflows/phase3b/scripts/"
            "run_f3b_heldout_checkpointed.py"
        ),

    "assembler":
        Path(
            "workflows/phase3b/scripts/"
            "assemble_f3b6_heldout_decisions.py"
        ),

    "temporal_script":
        Path(
            "workflows/phase3b/scripts/"
            "build_f3b6_temporal_contract.py"
        ),

    "binding":
        Path(
            "workflows/phase3b/heldout/execution/config/"
            "f3b6_execution_input_binding.json"
        ),

    "authorization":
        Path(
            "workflows/phase3b/heldout/execution/config/"
            "f3b6_single_use_execution_authorization.json"
        ),

    "incident":
        Path(
            "workflows/phase3b/heldout/execution/"
            "evidence/reports/"
            "f3b6_tooling_incident_007_"
            "adapter_job_normalization.json"
        ),

    "plan":
        Path(
            "workflows/phase3b/heldout/materialization/"
            "evidence/tables/"
            "f3b5_heldout_exact_afino_plan.csv"
        ),

    "grid":
        Path(
            "workflows/phase3b/heldout/materialization/"
            "evidence/tables/"
            "f3b5_heldout_decision_grid.csv"
        ),

    "payload":
        Path(
            "workflows/phase3b/heldout/materialization/"
            "evidence/tables/"
            "f3b5_heldout_payload_manifest.csv"
        ),

    "rule":
        Path(
            "workflows/phase3b/development/analysis/"
            "f3b4_final_rule_freeze.json"
        ),

    "f3b3_runner":
        Path(
            "workflows/phase3b/scripts/"
            "run_f3b_development_checkpointed.py"
        ),

    "f3b3_binding":
        Path(
            "workflows/phase3b/development/config/"
            "f3b3_afino_execution_environment_binding.json"
        ),

    "dev_regression":
        Path(
            "workflows/phase3b/heldout/execution/"
            "evidence/tables/"
            "f3b6_development_runner_regression_audit.csv"
        ),

    "arrays":
        Path(
            "data/interim/phase3b/"
            "f3b5_heldout"
        ),

    "audit":
        Path(
            "workflows/phase3b/heldout/execution/"
            "evidence/reports/"
            "f3b6_validation_audit.json"
        ),
}


def sha256_file(
    path: Path,
) -> str:

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def read_csv(
    path: Path,
) -> tuple[
    list[dict[str, str]],
    list[str],
]:

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        return (
            list(reader),
            list(
                reader.fieldnames
                or []
            ),
        )


def git_text(
    repo: Path,
    *args: str,
) -> str:

    cp = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            *args,
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if cp.returncode != 0:

        raise RuntimeError(
            "git failed: "
            + cp.stderr.strip()
        )

    return cp.stdout.strip()


def json_compact(
    value: Any,
) -> str:

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def result_core_sha256(
    result: dict[str, Any],
) -> str:

    payload = {
        key:
            result.get(key)
        for key in CORE_FIELDS
    }

    return hashlib.sha256(
        json_compact(
            payload
        ).encode("utf-8")
    ).hexdigest()


def csv_render(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value)


def close_float(
    a: Any,
    b: Any,
    *,
    atol: float = 5e-12,
) -> bool:

    try:

        x = float(a)
        y = float(b)

    except (
        TypeError,
        ValueError,
    ):
        return False


    return (
        math.isfinite(x)
        and math.isfinite(y)
        and math.isclose(
            x,
            y,
            rel_tol=0.0,
            abs_tol=atol,
        )
    )


def is_true(
    value: Any,
) -> bool:

    return (
        str(value)
        .strip()
        .lower()
        == "true"
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


    # --------------------------------------------------------
    # Git + immutable artifact hashes
    # --------------------------------------------------------

    if (
        git_text(
            repo,
            "rev-parse",
            "HEAD",
        )
        != EXPECTED_HEAD
    ):
        raise RuntimeError(
            "Unexpected Git HEAD"
        )


    expected_hashes = {

        P["checkpoint"]:
            EXPECTED_CHECKPOINT_SHA,

        P["results"]:
            EXPECTED_RESULTS_SHA,

        P["decisions"]:
            EXPECTED_DECISIONS_SHA,

        P["temporal"]:
            EXPECTED_TEMPORAL_SHA,

        P["adapter"]:
            EXPECTED_ADAPTER_SHA,

        P["assembler"]:
            EXPECTED_ASSEMBLER_SHA,

        P["temporal_script"]:
            EXPECTED_TEMPORAL_SCRIPT_SHA,

        P["binding"]:
            EXPECTED_BINDING_SHA,

        P["authorization"]:
            EXPECTED_AUTH_SHA,

        P["incident"]:
            EXPECTED_INCIDENT_SHA,

        P["plan"]:
            EXPECTED_PLAN_SHA,

        P["grid"]:
            EXPECTED_GRID_SHA,

        P["payload"]:
            EXPECTED_PAYLOAD_SHA,

        P["rule"]:
            EXPECTED_FINAL_RULE_SHA,

        P["f3b3_runner"]:
            EXPECTED_F3B3_RUNNER_SHA,

        P["f3b3_binding"]:
            EXPECTED_F3B3_BINDING_SHA,

        P["dev_regression"]:
            EXPECTED_DEV_REGRESSION_SHA,
    }


    for rel, expected in (
        expected_hashes.items()
    ):

        path = repo / rel

        if not path.is_file():

            raise RuntimeError(
                f"Missing required artifact: "
                f"{rel}"
            )


        actual = sha256_file(
            path
        )


        if actual != expected:

            raise RuntimeError(
                f"SHA mismatch: {rel}: "
                f"{actual}"
            )


    for name, expected in (
        ARRAY_SHA.items()
    ):

        path = (
            repo
            / P["arrays"]
            / name
        )


        if (
            not path.is_file()
            or
            sha256_file(path)
            != expected
        ):

            raise RuntimeError(
                "Persistent-array "
                f"mismatch: {name}"
            )


    if (
        repo
        / P["audit"]
    ).exists():

        raise RuntimeError(
            "Refusing overwrite: "
            f"{P['audit']}"
        )


    # --------------------------------------------------------
    # Frozen final rule
    # --------------------------------------------------------

    rule = json.loads(
        (
            repo
            / P["rule"]
        ).read_text(
            encoding="utf-8"
        )
    )


    final_rule = rule.get(
        "final_rule",
        {},
    )


    if (
        rule.get(
            "freeze_state"
        )
        !=
        "FINAL_RULE_FREEZE_BASELINE_ONLY"
        or
        rule.get(
            "status"
        )
        !=
        "FINAL_RULE_FROZEN"
    ):

        raise RuntimeError(
            "Final rule freeze state changed"
        )


    if (
        final_rule.get(
            "rule_type"
        )
        != "AFINO_0_5_BASELINE"
        or
        final_rule.get(
            "comparison_operator"
        )
        != "STRICT_GREATER_THAN"
    ):

        raise RuntimeError(
            "Final rule identity changed"
        )


    if (
        final_rule.get(
            "selection_rule"
        )
        !=
        "delta_BIC01 > 10 AND "
        "delta_BIC21 > 10"
    ):

        raise RuntimeError(
            "Final rule expression changed"
        )


    t01 = float(
        final_rule.get("t01")
    )

    t21 = float(
        final_rule.get("t21")
    )


    if (
        t01 != 10.0
        or
        t21 != 10.0
    ):

        raise RuntimeError(
            "Frozen thresholds changed"
        )


    # --------------------------------------------------------
    # Authorization firewall
    # --------------------------------------------------------

    auth = json.loads(
        (
            repo
            / P["authorization"]
        ).read_text(
            encoding="utf-8"
        )
    )


    if (
        auth.get(
            "authorization_id"
        )
        !=
        "F3B6_SINGLE_USE_EXECUTION_"
        "AUTHORIZATION_V3"
    ):

        raise RuntimeError(
            "Unexpected authorization ID"
        )


    if (
        auth.get(
            "artifact_role"
        )
        !=
        "F3B6_SINGLE_USE_EXECUTION_"
        "AUTHORIZATION"
        or
        auth.get(
            "status"
        )
        !=
        "AUTHORIZED_FOR_SINGLE_USE_"
        "AFINO_EXECUTION"
    ):

        raise RuntimeError(
            "Invalid authorization state"
        )


    permissions = auth.get(
        "permissions",
        {},
    )


    if (
        permissions.get(
            "heldout_afino_execution_"
            "authorized"
        )
        is not True
    ):

        raise RuntimeError(
            "HELDOUT execution "
            "was not authorized"
        )


    for key in [
        "truth_join_authorized",
        "heldout_metrics_authorized",
        "rule_refitting_authorized",
        "threshold_mutation_authorized",
        "candidate_search_authorized",
    ]:

        if (
            permissions.get(key)
            is not False
        ):

            raise RuntimeError(
                "Authorization firewall "
                f"violation: {key}"
            )


    frozen = auth.get(
        "frozen_inputs",
        {},
    )


    expected_frozen = {

        "adapter_sha256":
            EXPECTED_ADAPTER_SHA,

        "execution_input_binding_sha256":
            EXPECTED_BINDING_SHA,

        "heldout_payload_manifest_sha256":
            EXPECTED_PAYLOAD_SHA,

        "heldout_decision_grid_sha256":
            EXPECTED_GRID_SHA,

        "heldout_exact_afino_plan_sha256":
            EXPECTED_PLAN_SHA,

        "final_rule_freeze_sha256":
            EXPECTED_FINAL_RULE_SHA,
    }


    for key, expected in (
        expected_frozen.items()
    ):

        if frozen.get(key) != expected:

            raise RuntimeError(
                "Authorization frozen-input "
                f"mismatch: {key}"
            )


    # --------------------------------------------------------
    # DEVELOPMENT regression
    # --------------------------------------------------------

    dev_regression, _ = read_csv(
        repo
        / P["dev_regression"]
    )


    if (
        len(dev_regression) != 18
        or
        sum(
            row.get(
                "overall_match"
            )
            == "True"
            for row
            in dev_regression
        )
        != 18
    ):

        raise RuntimeError(
            "DEVELOPMENT regression "
            "is not 18/18 exact"
        )


    # --------------------------------------------------------
    # Read blinded artifacts
    # --------------------------------------------------------

    plan, plan_fields = read_csv(
        repo / P["plan"]
    )

    grid, grid_fields = read_csv(
        repo / P["grid"]
    )

    payload, payload_fields = read_csv(
        repo / P["payload"]
    )

    results, result_fields = read_csv(
        repo / P["results"]
    )

    decisions, decision_fields = read_csv(
        repo / P["decisions"]
    )

    temporal, temporal_fields = read_csv(
        repo / P["temporal"]
    )


    if (
        len(plan) != 10800
        or
        len(grid) != 3600
        or
        len(payload) != 4320
        or
        len(results) != 10800
        or
        len(decisions) != 3600
        or
        len(temporal) != 3600
    ):

        raise RuntimeError(
            "Artifact row-count "
            "contract failed"
        )


    if (
        RESULT_FORBIDDEN
        & set(result_fields)
    ):

        raise RuntimeError(
            "Forbidden truth/outcome "
            "columns in blinded results"
        )


    for label, fields in [
        ("plan", plan_fields),
        ("grid", grid_fields),
        ("payload", payload_fields),
        ("decisions", decision_fields),
        ("temporal", temporal_fields),
    ]:

        leaked = (
            TRUTH_OR_METRIC_FORBIDDEN
            & set(fields)
        )


        if leaked:

            raise RuntimeError(
                "Truth/metric columns leaked "
                f"into {label}: "
                f"{sorted(leaked)}"
            )


    # --------------------------------------------------------
    # Frozen plan/grid uniqueness
    # --------------------------------------------------------

    if Counter(
        row["model_id"]
        for row in plan
    ) != Counter({
        "M0": 3600,
        "M1": 3600,
        "M2": 3600,
    }):

        raise RuntimeError(
            "Frozen plan model "
            "counts mismatch"
        )


    if {
        row[
            "external_optimizer_seed"
        ]
        for row in plan
    } != {"0"}:

        raise RuntimeError(
            "Frozen plan is not seed0-only"
        )


    if {
        row[
            "execution_status"
        ]
        for row in plan
    } != {"NOT_EXECUTED"}:

        raise RuntimeError(
            "Frozen plan execution "
            "state changed"
        )


    if {
        row["afino_version"]
        for row in plan
    } != {
        EXPECTED_AFINO_VERSION
    }:

        raise RuntimeError(
            "Frozen AFINO version changed"
        )


    if {
        row["afino_commit"]
        for row in plan
    } != {
        EXPECTED_AFINO_COMMIT
    }:

        raise RuntimeError(
            "Frozen AFINO commit changed"
        )


    if any(
        float(
            row[
                "low_frequency_cutoff_hz"
            ]
        )
        != EXPECTED_CUTOFF
        for row in plan
    ):

        raise RuntimeError(
            "Frozen cutoff changed"
        )


    plan_by_job = {}

    plan_scientific = set()


    for row in plan:

        job_id = row["job_id"]


        if job_id in plan_by_job:

            raise RuntimeError(
                "Duplicate plan job_id"
            )


        plan_by_job[
            job_id
        ] = row


        key = (
            row[
                "simulation_unit_id"
            ],
            row[
                "external_optimizer_seed"
            ],
            row["model_id"],
        )


        if key in plan_scientific:

            raise RuntimeError(
                "Duplicate frozen "
                "scientific key"
            )


        plan_scientific.add(
            key
        )


    grid_by_id = {}


    for row in grid:

        did = row[
            "planned_decision_id"
        ]


        if did in grid_by_id:

            raise RuntimeError(
                "Duplicate frozen "
                "decision ID"
            )


        if (
            row[
                "decision_class"
            ]
            != "BASELINE"
            or
            row[
                "planned_model_calls"
            ]
            != "3"
            or
            row[
                "execution_status"
            ]
            != "NOT_EXECUTED"
        ):

            raise RuntimeError(
                "Frozen decision-grid "
                "contract changed"
            )


        grid_by_id[
            did
        ] = row


    if {
        row[
            "planned_decision_id"
        ]
        for row in plan
    } != set(
        grid_by_id
    ):

        raise RuntimeError(
            "Plan/grid decision IDs differ"
        )


    payload_by_sid = {}

    payload_index = {}


    for i, row in enumerate(
        payload
    ):

        sid = row[
            "simulation_unit_id"
        ]


        if sid in payload_by_sid:

            raise RuntimeError(
                "Duplicate payload "
                "simulation_unit_id"
            )


        payload_by_sid[
            sid
        ] = row

        payload_index[
            sid
        ] = i


    # --------------------------------------------------------
    # Strict read-only checkpoint
    # --------------------------------------------------------

    cp_uri = (
        (
            repo
            / P["checkpoint"]
        )
        .resolve()
        .as_uri()
        + "?mode=ro"
    )


    con = sqlite3.connect(
        cp_uri,
        uri=True,
    )


    try:

        integrity = con.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]


        if integrity != "ok":

            raise RuntimeError(
                "Checkpoint integrity "
                "check failed"
            )


        metadata = {
            str(key):
                str(value)
            for key, value
            in con.execute(
                "SELECT key,value "
                "FROM metadata"
            )
        }


        expected_metadata = {

            "phase":
                "F3B.6",

            "plan_kind":
                "HELDOUT_SINGLE_USE_BLINDED",

            "f3b5_commit":
                EXPECTED_F3B5_COMMIT,

            "f3b3_runner_sha256":
                EXPECTED_F3B3_RUNNER_SHA,

            "heldout_plan_sha256":
                EXPECTED_PLAN_SHA,

            "payload_manifest_sha256":
                EXPECTED_PAYLOAD_SHA,

            "derived_payload_loader_sha256":
                EXPECTED_DERIVED_LOADER_SHA,

            "authorization_sha256":
                EXPECTED_AUTH_SHA,

            "execution_input_binding_sha256":
                EXPECTED_BINDING_SHA,
        }


        if metadata != expected_metadata:

            raise RuntimeError(
                "Checkpoint metadata "
                "contract mismatch"
            )


        invocations = [
            tuple(row)
            for row
            in con.execute(
                """
                SELECT
                    invocation_id,
                    max_new_jobs,
                    existing_before,
                    new_jobs,
                    pending_after
                FROM invocations
                ORDER BY invocation_id
                """
            )
        ]


        expected_invocations = [
            (1, 3000,     0, 3000, 7800),
            (2, 3000,  3000, 3000, 4800),
            (3, 3000,  6000, 3000, 1800),
            (4, 1800,  9000, 1800,    0),
            (5, 3000, 10800,    0,    0),
        ]


        if (
            invocations
            != expected_invocations
        ):

            raise RuntimeError(
                "Invocation sequence mismatch: "
                f"{invocations}"
            )


        cp_rows = list(
            con.execute(
                """
                SELECT
                    job_id,
                    job_order,
                    planned_decision_id,
                    simulation_unit_id,
                    external_optimizer_seed,
                    model_id,
                    status,
                    result_core_sha256,
                    result_json
                FROM results
                ORDER BY job_order
                """
            )
        )


    finally:

        con.close()


    if len(cp_rows) != 10800:

        raise RuntimeError(
            "Checkpoint results != 10800"
        )


    # --------------------------------------------------------
    # Plan -> checkpoint + result-core verification
    # --------------------------------------------------------

    cp_by_job = {}

    cp_scientific = set()

    plan_checkpoint_mismatches = 0

    result_core_mismatches = 0


    for stored in cp_rows:

        (
            stored_job_id,
            stored_order,
            stored_did,
            stored_sid,
            stored_seed,
            stored_model,
            stored_status,
            stored_core,
            result_json,
        ) = stored


        result = json.loads(
            result_json
        )


        job_id = str(
            result["job_id"]
        )


        if job_id in cp_by_job:

            raise RuntimeError(
                "Duplicate checkpoint job_id"
            )


        cp_by_job[
            job_id
        ] = result


        key = (
            str(
                result[
                    "simulation_unit_id"
                ]
            ),
            str(
                result[
                    "external_optimizer_seed"
                ]
            ),
            str(
                result[
                    "model_id"
                ]
            ),
        )


        if key in cp_scientific:

            raise RuntimeError(
                "Duplicate checkpoint "
                "scientific key"
            )


        cp_scientific.add(
            key
        )


        if (
            RESULT_FORBIDDEN
            & set(result)
        ):

            raise RuntimeError(
                "Forbidden field in "
                "checkpoint result_json"
            )


        if (
            str(stored_job_id)
            != job_id
            or
            int(stored_order)
            != int(
                result["job_order"]
            )
            or
            str(stored_did)
            != str(
                result[
                    "planned_decision_id"
                ]
            )
            or
            str(stored_sid)
            != str(
                result[
                    "simulation_unit_id"
                ]
            )
            or
            int(stored_seed)
            != int(
                result[
                    "external_optimizer_seed"
                ]
            )
            or
            str(stored_model)
            != str(
                result["model_id"]
            )
            or
            str(stored_status)
            != str(
                result["status"]
            )
            or
            str(stored_core)
            != str(
                result[
                    "result_core_sha256"
                ]
            )
        ):

            raise RuntimeError(
                "Checkpoint storage/"
                "result_json mismatch: "
                f"{job_id}"
            )


        recomputed_core = (
            result_core_sha256(
                result
            )
        )


        if (
            recomputed_core
            != str(
                result[
                    "result_core_sha256"
                ]
            )
        ):

            result_core_mismatches += 1


        plan_row = plan_by_job.get(
            job_id
        )


        if plan_row is None:

            plan_checkpoint_mismatches += 1
            continue


        identity_pairs = {

            "job_order": (
                str(
                    result[
                        "job_order"
                    ]
                ),
                plan_row[
                    "job_order"
                ],
            ),

            "planned_decision_id": (
                str(
                    result[
                        "planned_decision_id"
                    ]
                ),
                plan_row[
                    "planned_decision_id"
                ],
            ),

            "simulation_unit_id": (
                str(
                    result[
                        "simulation_unit_id"
                    ]
                ),
                plan_row[
                    "simulation_unit_id"
                ],
            ),

            "background_realization_id": (
                str(
                    result[
                        "background_realization_id"
                    ]
                ),
                plan_row[
                    "background_realization_id"
                ],
            ),

            "external_optimizer_seed": (
                str(
                    result[
                        "external_optimizer_seed"
                    ]
                ),
                plan_row[
                    "external_optimizer_seed"
                ],
            ),

            "model_id": (
                str(
                    result[
                        "model_id"
                    ]
                ),
                plan_row[
                    "model_id"
                ],
            ),

            "payload_logical_sha256": (
                str(
                    result[
                        "payload_logical_sha256"
                    ]
                ),
                plan_row[
                    "payload_logical_sha256"
                ],
            ),

            "afino_version": (
                str(
                    result[
                        "afino_version"
                    ]
                ),
                plan_row[
                    "afino_version"
                ],
            ),

            "afino_commit": (
                str(
                    result[
                        "afino_commit"
                    ]
                ),
                plan_row[
                    "afino_commit"
                ],
            ),
        }


        if (
            any(
                a != b
                for a, b
                in identity_pairs.values()
            )
            or
            result.get(
                "decision_class"
            )
            != "BASELINE"
            or
            result.get(
                "model_name"
            )
            != MODEL_NAMES[
                plan_row[
                    "model_id"
                ]
            ]
        ):

            plan_checkpoint_mismatches += 1


        if (
            result.get(
                "status"
            )
            != "OK"
            or
            result.get(
                "error"
            )
            is not None
        ):

            raise RuntimeError(
                "Non-OK checkpoint "
                f"result: {job_id}"
            )


    if (
        result_core_mismatches != 0
        or
        plan_checkpoint_mismatches
        != 0
        or
        set(cp_by_job)
        != set(plan_by_job)
    ):

        raise RuntimeError(
            "Checkpoint identity/core "
            "mismatches: "
            f"core={result_core_mismatches} "
            f"plan={plan_checkpoint_mismatches}"
        )


    # --------------------------------------------------------
    # Checkpoint -> exported CSV
    # --------------------------------------------------------

    results_by_job = {}

    checkpoint_csv_mismatches = 0


    for row in results:

        job_id = row["job_id"]


        if job_id in results_by_job:

            raise RuntimeError(
                "Duplicate results CSV job_id"
            )


        results_by_job[
            job_id
        ] = row


        cp = cp_by_job.get(
            job_id
        )


        if cp is None:

            checkpoint_csv_mismatches += 1
            continue


        for field in result_fields:

            if (
                row[field]
                != csv_render(
                    cp.get(field)
                )
            ):

                checkpoint_csv_mismatches += 1
                break


    if (
        checkpoint_csv_mismatches
        != 0
        or
        set(results_by_job)
        != set(cp_by_job)
    ):

        raise RuntimeError(
            "Checkpoint/CSV mismatches = "
            f"{checkpoint_csv_mismatches}"
        )


    if Counter(
        row["status"]
        for row in results
    ) != Counter({
        "OK": 10800,
    }):

        raise RuntimeError(
            "Results CSV status "
            "contract failed"
        )


    if Counter(
        row["model_id"]
        for row in results
    ) != Counter({
        "M0": 3600,
        "M1": 3600,
        "M2": 3600,
    }):

        raise RuntimeError(
            "Results CSV model "
            "contract failed"
        )


    # --------------------------------------------------------
    # Payload identity
    # --------------------------------------------------------

    payload_identity_mismatches = 0


    for frozen_row in grid:

        sid = frozen_row[
            "simulation_unit_id"
        ]

        manifest = (
            payload_by_sid.get(
                sid
            )
        )


        if (
            manifest is None
            or
            manifest[
                "logical_payload_sha256"
            ]
            !=
            frozen_row[
                "payload_logical_sha256"
            ]
        ):

            payload_identity_mismatches += 1


    for row in plan:

        manifest = (
            payload_by_sid.get(
                row[
                    "simulation_unit_id"
                ]
            )
        )


        if (
            manifest is None
            or
            manifest[
                "logical_payload_sha256"
            ]
            !=
            row[
                "payload_logical_sha256"
            ]
        ):

            payload_identity_mismatches += 1


    if (
        payload_identity_mismatches
        != 0
    ):

        raise RuntimeError(
            "Payload identity "
            "mismatches = "
            f"{payload_identity_mismatches}"
        )


    # --------------------------------------------------------
    # Independent blind-decision recalculation
    # --------------------------------------------------------

    results_by_decision = (
        defaultdict(dict)
    )


    for row in results:

        did = row[
            "planned_decision_id"
        ]

        model = row[
            "model_id"
        ]


        if (
            model
            in results_by_decision[
                did
            ]
        ):

            raise RuntimeError(
                "Duplicate result model "
                "within decision: "
                f"{did} {model}"
            )


        results_by_decision[
            did
        ][
            model
        ] = row


    decisions_by_id = {}

    decision_recalc_mismatches = 0


    for row in decisions:

        did = row[
            "planned_decision_id"
        ]


        if did in decisions_by_id:

            raise RuntimeError(
                "Duplicate blinded decision ID"
            )


        decisions_by_id[
            did
        ] = row


        frozen_row = (
            grid_by_id.get(
                did
            )
        )

        models = (
            results_by_decision.get(
                did,
                {},
            )
        )


        if (
            frozen_row is None
            or
            set(models)
            != {
                "M0",
                "M1",
                "M2",
            }
        ):

            decision_recalc_mismatches += 1
            continue


        if (
            row[
                "decision_status"
            ]
            != "VALID"
            or
            row[
                "valid_models"
            ]
            != "3"
            or
            row[
                "decision_class"
            ]
            != "BASELINE"
        ):

            decision_recalc_mismatches += 1
            continue


        for field in [
            "planned_decision_id",
            "decision_order",
            "decision_class",
            "simulation_unit_id",
            "background_realization_id",
            "external_optimizer_seed",
            "payload_logical_sha256",
        ]:

            if (
                row[field]
                !=
                frozen_row[field]
            ):

                decision_recalc_mismatches += 1
                break


        b0 = float(
            models[
                "M0"
            ][
                "bic"
            ]
        )

        b1 = float(
            models[
                "M1"
            ][
                "bic"
            ]
        )

        b2 = float(
            models[
                "M2"
            ][
                "bic"
            ]
        )


        d01 = b0 - b1

        d21 = b2 - b1


        selected = bool(
            d01 > t01
            and
            d21 > t21
        )


        if not (
            close_float(
                row["bic_m0"],
                b0,
            )
            and
            close_float(
                row["bic_m1"],
                b1,
            )
            and
            close_float(
                row["bic_m2"],
                b2,
            )
            and
            close_float(
                row[
                    "delta_bic_0_1"
                ],
                d01,
            )
            and
            close_float(
                row[
                    "delta_bic_2_1"
                ],
                d21,
            )
        ):

            decision_recalc_mismatches += 1


        if (
            row[
                "qpp_selected"
            ]
            != (
                "True"
                if selected
                else "False"
            )
        ):

            decision_recalc_mismatches += 1


        m1_period = (
            models[
                "M1"
            ].get(
                "formal_m1_period_s",
                "",
            )
        )


        if m1_period == "":

            if (
                row[
                    "formal_m1_period_s"
                ]
                != ""
                or
                row[
                    "period_label"
                ]
                !=
                "unavailable_"
                "incomplete_numerical"
            ):

                decision_recalc_mismatches += 1


        else:

            if (
                not close_float(
                    row[
                        "formal_m1_period_s"
                    ],
                    m1_period,
                )
                or
                row[
                    "period_label"
                ]
                != (
                    "recovered_period_selected"
                    if selected
                    else
                    "formal_m1_center_"
                    "not_selected"
                )
            ):

                decision_recalc_mismatches += 1


        for model, field in [
            (
                "M0",
                "result_core_m0_sha256",
            ),
            (
                "M1",
                "result_core_m1_sha256",
            ),
            (
                "M2",
                "result_core_m2_sha256",
            ),
        ]:

            if (
                row[field]
                !=
                models[
                    model
                ][
                    "result_core_sha256"
                ]
            ):

                decision_recalc_mismatches += 1


    if (
        decision_recalc_mismatches
        != 0
        or
        set(decisions_by_id)
        != set(grid_by_id)
    ):

        raise RuntimeError(
            "Decision recalculation "
            "mismatches = "
            f"{decision_recalc_mismatches}"
        )


    if Counter(
        row[
            "decision_status"
        ]
        for row in decisions
    ) != Counter({
        "VALID": 3600,
    }):

        raise RuntimeError(
            "Decision status "
            "contract failed"
        )


    # --------------------------------------------------------
    # Independent temporal recalculation
    # --------------------------------------------------------

    temporal_by_id = {}


    for row in temporal:

        did = row[
            "planned_decision_id"
        ]


        if did in temporal_by_id:

            raise RuntimeError(
                "Duplicate temporal "
                "decision ID"
            )


        temporal_by_id[
            did
        ] = row


    if (
        set(temporal_by_id)
        != set(grid_by_id)
    ):

        raise RuntimeError(
            "Temporal/grid "
            "decision IDs differ"
        )


    retained_time = np.load(
        repo
        / P["arrays"]
        / "retained_time_s.npy",
        mmap_mode="r",
        allow_pickle=False,
    )


    retained_offsets = np.load(
        repo
        / P["arrays"]
        / "retained_offsets.npy",
        mmap_mode="r",
        allow_pickle=False,
    )


    if len(
        retained_offsets
    ) != 4321:

        raise RuntimeError(
            "retained_offsets "
            "length != 4321"
        )


    temporal_mismatches = 0

    mean_dt_matches = 0

    positive_fftfreq_matches = 0


    for frozen_row in grid:

        did = frozen_row[
            "planned_decision_id"
        ]

        sid = frozen_row[
            "simulation_unit_id"
        ]


        tr = temporal_by_id[
            did
        ]

        manifest = payload_by_sid[
            sid
        ]

        idx = payload_index[
            sid
        ]


        offset = int(
            manifest[
                "retained_offset"
            ]
        )

        n = int(
            manifest[
                "retained_length"
            ]
        )

        end = offset + n


        if (
            int(
                retained_offsets[idx]
            )
            != offset
            or
            int(
                retained_offsets[
                    idx + 1
                ]
            )
            != end
        ):

            temporal_mismatches += 1
            continue


        time_seconds = np.asarray(
            retained_time[
                offset:end
            ],
            dtype=float,
        )


        if (
            len(time_seconds) != n
            or
            n < 2
            or
            not np.all(
                np.isfinite(
                    time_seconds
                )
            )
        ):

            temporal_mismatches += 1
            continue


        dt = np.diff(
            time_seconds
        )


        mean_dt = float(
            np.mean(dt)
        )

        median_dt = float(
            np.median(dt)
        )


        positive_bins = int(
            np.count_nonzero(
                np.fft.fftfreq(
                    n,
                    d=mean_dt,
                )
                > 0.0
            )
        )


        legacy_bins = int(
            np.count_nonzero(
                np.fft.rfftfreq(
                    n,
                    d=mean_dt,
                )
                > 0.0
            )
        )


        models = (
            results_by_decision[
                did
            ]
        )


        dt_ok = all(
            close_float(
                models[
                    model
                ][
                    "afino_effective_dt_s"
                ],
                mean_dt,
            )
            for model in [
                "M0",
                "M1",
                "M2",
            ]
        )


        fft_ok = all(
            int(
                models[
                    model
                ][
                    "positive_frequency_"
                    "bin_count"
                ]
            )
            == positive_bins
            for model in [
                "M0",
                "M1",
                "M2",
            ]
        )


        mean_dt_matches += int(
            dt_ok
        )

        positive_fftfreq_matches += int(
            fft_ok
        )


        row_ok = (
            tr[
                "simulation_unit_id"
            ]
            == sid
            and
            tr[
                "payload_logical_sha256"
            ]
            ==
            frozen_row[
                "payload_logical_sha256"
            ]
            and
            int(
                tr["n_samples"]
            )
            == n
            and
            close_float(
                tr[
                    "mean_dt_external_s"
                ],
                mean_dt,
            )
            and
            close_float(
                tr[
                    "median_dt_external_s"
                ],
                median_dt,
            )
            and
            int(
                tr[
                    "positive_fftfreq_"
                    "bin_count_external"
                ]
            )
            == positive_bins
            and
            int(
                tr[
                    "rfftfreq_positive_"
                    "bin_count_external"
                ]
            )
            == legacy_bins
            and
            is_true(
                tr[
                    "mean_dt_contract_match"
                ]
            )
            == dt_ok
            and
            is_true(
                tr[
                    "positive_fftfreq_"
                    "contract_match"
                ]
            )
            == fft_ok
        )


        for model, suffix in [
            ("M0", "m0"),
            ("M1", "m1"),
            ("M2", "m2"),
        ]:

            row_ok = (
                row_ok
                and
                close_float(
                    tr[
                        f"afino_dt_{suffix}_s"
                    ],
                    models[
                        model
                    ][
                        "afino_effective_dt_s"
                    ],
                )
            )


            row_ok = (
                row_ok
                and
                int(
                    tr[
                        "afino_positive_"
                        f"bin_count_{suffix}"
                    ]
                )
                ==
                int(
                    models[
                        model
                    ][
                        "positive_frequency_"
                        "bin_count"
                    ]
                )
            )


            row_ok = (
                row_ok
                and
                is_true(
                    tr[
                        f"mean_dt_match_{suffix}"
                    ]
                )
                ==
                close_float(
                    models[
                        model
                    ][
                        "afino_effective_dt_s"
                    ],
                    mean_dt,
                )
            )


            row_ok = (
                row_ok
                and
                is_true(
                    tr[
                        "positive_fftfreq_"
                        f"match_{suffix}"
                    ]
                )
                ==
                (
                    int(
                        models[
                            model
                        ][
                            "positive_frequency_"
                            "bin_count"
                        ]
                    )
                    == positive_bins
                )
            )


        if not row_ok:

            temporal_mismatches += 1


    if (
        temporal_mismatches != 0
        or
        mean_dt_matches != 3600
        or
        positive_fftfreq_matches
        != 3600
    ):

        raise RuntimeError(
            "Temporal contract failed: "
            f"mismatches={temporal_mismatches} "
            f"mean={mean_dt_matches} "
            f"fft={positive_fftfreq_matches}"
        )


    # --------------------------------------------------------
    # Blinding firewall static checks
    # --------------------------------------------------------

    truth_filename = (
        "f3b5_heldout_truth_ledger.csv"
    )


    for rel in [
        P["adapter"],
        P["assembler"],
        P["temporal_script"],
    ]:

        source = (
            repo
            / rel
        ).read_text(
            encoding="utf-8-sig"
        )


        if truth_filename in source:

            raise RuntimeError(
                "Truth ledger filename "
                "referenced by F3B.6 "
                f"operational source: {rel}"
            )


    forbidden_artifact_tokens = [
        "truth_join",
        "heldout_metrics",
        "selection_function",
        "period_recovery",
    ]


    execution_root = (
        repo
        / "workflows/phase3b/"
          "heldout/execution"
    )


    forbidden_artifacts = []


    for path in execution_root.rglob(
        "*"
    ):

        if path.is_file():

            low = path.name.lower()


            if any(
                token in low
                for token
                in forbidden_artifact_tokens
            ):

                forbidden_artifacts.append(
                    path
                    .relative_to(repo)
                    .as_posix()
                )


    if forbidden_artifacts:

        raise RuntimeError(
            "Forbidden unblinding/"
            "metric artifacts exist: "
            + ",".join(
                forbidden_artifacts
            )
        )


    # --------------------------------------------------------
    # Write validation audit
    # No selection aggregate is calculated.
    # --------------------------------------------------------

    audit = {

        "artifact_role":
            "F3B6_HELDOUT_BLINDED_"
            "EXECUTION_VALIDATION_AUDIT",

        "phase":
            "F3B.6",

        "status":
            "PASS",

        "git_head":
            EXPECTED_HEAD,

        "single_use_execution": {

            "invocation_sequence": [
                3000,
                3000,
                3000,
                1800,
                0,
            ],

            "checkpoint_results":
                10800,

            "checkpoint_status_ok":
                10800,

            "M0":
                3600,

            "M1":
                3600,

            "M2":
                3600,

            "duplicate_job_id":
                0,

            "duplicate_scientific_keys":
                0,

            "plan_checkpoint_mismatches":
                0,

            "checkpoint_csv_mismatches":
                0,

            "result_core_mismatches":
                0,
        },

        "blind_decisions": {

            "rows":
                3600,

            "status_valid":
                3600,

            "decision_recalculation_mismatches":
                0,

            "qpp_selected_aggregate":
                "NOT_COMPUTED",

            "final_rule":
                "delta_BIC01 > 10 AND "
                "delta_BIC21 > 10",

            "comparison_operator":
                "STRICT_GREATER_THAN",

            "t01":
                10.0,

            "t21":
                10.0,
        },

        "payload_identity": {
            "mismatches":
                0,
        },

        "temporal_contract": {

            "rows":
                3600,

            "mean_dt_matches":
                3600,

            "positive_fftfreq_matches":
                3600,

            "legacy_rfftfreq":
                "DIAGNOSTIC_ONLY",

            "mismatches":
                0,
        },

        "development_runner_regression": {
            "exact_matches":
                18,
            "jobs":
                18,
        },

        "blinding_firewall": {

            "truth_ledger_accessed":
                False,

            "truth_columns_in_results":
                0,

            "truth_columns_in_decisions":
                0,

            "truth_columns_in_temporal":
                0,

            "candidate_search_performed":
                False,

            "thresholds_modified":
                False,

            "rule_refitted":
                False,

            "heldout_metrics_computed":
                False,

            "heldout_selection_function_computed":
                False,

            "heldout_period_metrics_computed":
                False,

            "heldout_outcomes_scientifically_inspected":
                False,
        },

        "hashes": {

            "checkpoint_sha256":
                EXPECTED_CHECKPOINT_SHA,

            "results_csv_sha256":
                EXPECTED_RESULTS_SHA,

            "decisions_csv_sha256":
                EXPECTED_DECISIONS_SHA,

            "temporal_csv_sha256":
                EXPECTED_TEMPORAL_SHA,

            "adapter_sha256":
                EXPECTED_ADAPTER_SHA,

            "assembler_sha256":
                EXPECTED_ASSEMBLER_SHA,

            "temporal_script_sha256":
                EXPECTED_TEMPORAL_SCRIPT_SHA,

            "binding_sha256":
                EXPECTED_BINDING_SHA,

            "authorization_sha256":
                EXPECTED_AUTH_SHA,

            "final_rule_sha256":
                EXPECTED_FINAL_RULE_SHA,

            "plan_sha256":
                EXPECTED_PLAN_SHA,

            "decision_grid_sha256":
                EXPECTED_GRID_SHA,

            "payload_manifest_sha256":
                EXPECTED_PAYLOAD_SHA,
        },

        "validation_result":
            "PHASE3B_HELDOUT_BLINDED_"
            "EXECUTION_VALIDATION_PASS",
    }


    audit_path = (
        repo
        / P["audit"]
    )


    audit_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    audit_path.write_text(
        json.dumps(
            audit,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


    print("frozen_plan = 10800")
    print("checkpoint = 10800")
    print("results_csv = 10800")

    print("M0 = 3600")
    print("M1 = 3600")
    print("M2 = 3600")

    print("blind_decisions = 3600")

    print("status_OK = 10800")
    print("decision_status_VALID = 3600")

    print("duplicate_job_id = 0")
    print("duplicate_scientific_keys = 0")

    print(
        "plan_checkpoint_mismatches = 0"
    )

    print(
        "checkpoint_csv_mismatches = 0"
    )

    print(
        "payload_identity_mismatches = 0"
    )

    print(
        "decision_recalculation_mismatches = 0"
    )

    print("mean_dt_mismatches = 0")

    print(
        "positive_fftfreq_mismatches = 0"
    )

    print(
        "development_runner_regression = "
        "18/18 exact"
    )

    print(
        "truth_ledger_accessed = false"
    )

    print(
        "truth_columns_in_results = 0"
    )

    print(
        "truth_columns_in_decisions = 0"
    )

    print(
        "truth_columns_in_temporal = 0"
    )

    print("candidate_search = false")

    print(
        "threshold_mutation = false"
    )

    print("heldout_metrics = false")

    print(
        "qpp_selected_aggregate = "
        "NOT_COMPUTED"
    )

    print(
        "validation_audit_sha256 =",
        sha256_file(
            audit_path
        ),
    )

    print(
        "PHASE3B_HELDOUT_BLINDED_"
        "EXECUTION_VALIDATION_PASS"
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
