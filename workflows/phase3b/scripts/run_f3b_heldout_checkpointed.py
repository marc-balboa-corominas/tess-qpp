from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any


EXPECTED_F3B5_COMMIT = (
    "690b54212ffc91d5d396da02db2bcd883b359e6b"
)

EXPECTED_F3B5_TAG = (
    "phase3b-heldout-materialization-v1"
)

EXPECTED_F3B3_RUNNER_SHA = (
    "4d5b68cdda60abd7f3a4380abf63d1b0b5e9f4e5889caf22ff85f95b31d813bc"
)

EXPECTED_F3B3_BINDING_SHA = (
    "1105199deead4782b76008d4a7c1ba636f7b3898a4808bb76585909d1bbe85c9"
)

EXPECTED_REPLAY_SHA = (
    "ad2c3a22c6f97fcfef26cd462f844fa893656432dc2d53e67a780bfe0d8a4b37"
)

EXPECTED_PAYLOAD_SHA = (
    "d20b0dac662cf809eb86d5e87d96f35e236b6ff2fbfb0fa86eeb4da8a49af8b4"
)

EXPECTED_DECISION_SHA = (
    "09419a4d5d968d5305f262b5aefe28cd29bc01cdcf67b53d91e1732c0e15aa34"
)

EXPECTED_PLAN_SHA = (
    "0b59e2f4ab4e1f3a1064b2281a9a428b117a7b258102e237702deee86171f2f9"
)

EXPECTED_FREEZE_SHA = (
    "e2faffdbb15d6e0fec52ff166e81a2ed58f5665d7d3f9dc43cb8b78f5c0a198c"
)


EXPECTED_RETAINED_ARRAY_HASHES = {
    "retained_time_s.npy":
        "573527515b71d29eadfe20d0b6eb87296f38f8ec188419a1a4b5fc95dab1d050",

    "retained_flux.npy":
        "f8e8fa86f9a307ef78bd34b153752078110b9461d8d172b7ec0d3e9425edebc6",

    "retained_native_index.npy":
        "c0b19f204fecad603c0d8b63bfe0a0643cb57ea74694d4f8849e443786072e4c",

    "retained_offsets.npy":
        "5fd86ec64fe858b3ed665f11a06f4ca7f054e83c51c6e21cb3339693cb99da64",
}


FORBIDDEN_EXECUTION_FIELDS = {
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


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fields: list[str],
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="raise",
            lineterminator="\n",
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


def git(
    repo: Path,
    *args: str,
) -> str:

    return subprocess.check_output(
        [
            "git",
            *args,
        ],
        cwd=repo,
        text=True,
    ).strip()


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
            f"Cannot load module: {path}"
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    sys.modules[
        name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def afino_loaded() -> bool:

    return any(
        name == "afino"
        or name.startswith(
            "afino."
        )
        for name
        in sys.modules
    )


def frozen_paths(
    repo: Path,
) -> dict[str, Path]:

    return {
        "runner":
            repo
            / "workflows/phase3b/scripts/"
              "run_f3b_development_checkpointed.py",

        "f3b3_binding":
            repo
            / "workflows/phase3b/development/config/"
              "f3b3_afino_execution_environment_binding.json",

        "replay":
            repo
            / "workflows/phase3b/development/evidence/tables/"
              "f3b3_canary_exact_replay_audit.csv",

        "canary_results":
            repo
            / "workflows/phase3b/development/evidence/tables/"
              "f3b3_canary_results.csv",

        "development_plan":
            repo
            / "workflows/phase3b/development/evidence/tables/"
              "f3b3_blinded_execution_plan.csv",

        "payload":
            repo
            / "workflows/phase3b/heldout/materialization/"
              "evidence/tables/"
              "f3b5_heldout_payload_manifest.csv",

        "decision":
            repo
            / "workflows/phase3b/heldout/materialization/"
              "evidence/tables/"
              "f3b5_heldout_decision_grid.csv",

        "heldout_plan":
            repo
            / "workflows/phase3b/heldout/materialization/"
              "evidence/tables/"
              "f3b5_heldout_exact_afino_plan.csv",

        "freeze":
            repo
            / "workflows/phase3b/development/analysis/"
              "f3b4_final_rule_freeze.json",

        "arrays":
            repo
            / "data/interim/phase3b/f3b5_heldout",

        "binding":
            repo
            / "workflows/phase3b/heldout/execution/config/"
              "f3b6_execution_input_binding.json",
    }


def verify_frozen_inputs(
    repo: Path,
) -> dict[str, Path]:

    paths = frozen_paths(
        repo
    )

    expected = {
        paths["runner"]:
            EXPECTED_F3B3_RUNNER_SHA,

        paths["f3b3_binding"]:
            EXPECTED_F3B3_BINDING_SHA,

        paths["replay"]:
            EXPECTED_REPLAY_SHA,

        paths["payload"]:
            EXPECTED_PAYLOAD_SHA,

        paths["decision"]:
            EXPECTED_DECISION_SHA,

        paths["heldout_plan"]:
            EXPECTED_PLAN_SHA,

        paths["freeze"]:
            EXPECTED_FREEZE_SHA,
    }


    for path, digest in (
        expected.items()
    ):

        if not path.is_file():
            raise RuntimeError(
                f"Missing frozen F3B.6 input: {path}"
            )

        if sha256_file(
            path
        ) != digest:
            raise RuntimeError(
                f"Frozen F3B.6 input changed: {path}"
            )


    for filename, digest in (
        EXPECTED_RETAINED_ARRAY_HASHES.items()
    ):

        path = (
            paths["arrays"]
            / filename
        )

        if not path.is_file():
            raise RuntimeError(
                f"Missing retained HELDOUT array: {filename}"
            )

        if sha256_file(
            path
        ) != digest:
            raise RuntimeError(
                f"Retained HELDOUT array changed: {filename}"
            )


    freeze = json.loads(
        paths["freeze"].read_text(
            encoding="utf-8"
        )
    )

    rule = freeze[
        "final_rule"
    ]


    if (
        freeze[
            "freeze_state"
        ]
        !=
        "FINAL_RULE_FREEZE_BASELINE_ONLY"
        or
        rule[
            "rule_type"
        ]
        !=
        "AFINO_0_5_BASELINE"
        or
        float(
            rule["t01"]
        )
        != 10.0
        or
        float(
            rule["t21"]
        )
        != 10.0
        or
        rule[
            "candidate_rule_promoted"
        ]
        is not False
    ):

        raise RuntimeError(
            "Frozen final rule changed"
        )


    return paths


def load_frozen_runner(
    repo: Path,
):

    paths = verify_frozen_inputs(
        repo
    )

    runner = load_module(
        paths["runner"],
        "_f3b3_frozen_runner_for_f3b6",
    )

    if afino_loaded():
        raise RuntimeError(
            "Importing frozen runner unexpectedly imported AFINO"
        )

    return runner


def extract_top_level_function_source(
    path: Path,
    name: str,
) -> str:

    source = path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source,
        filename=str(
            path
        ),
    )

    matches = [
        node
        for node in tree.body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name
            == name
        )
    ]

    if len(
        matches
    ) != 1:
        raise RuntimeError(
            f"Expected one {name}; "
            f"found {len(matches)}"
        )

    node = matches[0]

    lines = source.splitlines(
        keepends=True
    )

    return "".join(
        lines[
            node.lineno - 1:
            node.end_lineno
        ]
    )


def _replace_development_path_text(
    value: str,
) -> str:

    replacements = (
        (
            "workflows/phase3b/development/evidence/tables",
            "workflows/phase3b/heldout/materialization/evidence/tables",
        ),
        (
            "f3b2_development_payload_manifest.csv",
            "f3b5_heldout_payload_manifest.csv",
        ),
        (
            "data/interim/phase3b/f3b2_development",
            "data/interim/phase3b/f3b5_heldout",
        ),
    )

    result = value

    for old, new in replacements:

        result = result.replace(
            old,
            new,
        )

    return result


def derive_heldout_payload_loader(
    repo: Path,
    runner,
):

    paths = frozen_paths(
        repo
    )

    source = (
        extract_top_level_function_source(
            paths["runner"],
            "load_payload_dataset",
        )
    )

    if (
        source.count(
            "def load_payload_dataset("
        )
        != 1
    ):
        raise RuntimeError(
            "Frozen payload loader signature changed"
        )


    transformed = source.replace(
        "def load_payload_dataset(",
        "def load_heldout_payload_dataset(",
        1,
    )

    transformed = (
        _replace_development_path_text(
            transformed
        )
    )


    namespace = dict(
        runner.__dict__
    )


    for key, value in list(
        namespace.items()
    ):

        if isinstance(
            value,
            Path,
        ):

            text = (
                value.as_posix()
            )

            mapped = (
                _replace_development_path_text(
                    text
                )
            )

            if mapped != text:
                namespace[
                    key
                ] = Path(
                    mapped
                )

        elif isinstance(
            value,
            str,
        ):

            mapped = (
                _replace_development_path_text(
                    value
                )
            )

            if mapped != value:
                namespace[
                    key
                ] = mapped


    # F3B6-TOOL-002:
    # The frozen loader reads PAYLOAD_PHYSICAL_HASHES from
    # its global namespace. Path/string remapping above does
    # not transform that dict, so bind the already-frozen
    # HELDOUT retained-array hashes explicitly.
    namespace["PAYLOAD_PHYSICAL_HASHES"] = {
        "retained_time_s.npy":
            "573527515b71d29eadfe20d0b6eb87296f38f8ec188419a1a4b5fc95dab1d050",
        "retained_flux.npy":
            "f8e8fa86f9a307ef78bd34b153752078110b9461d8d172b7ec0d3e9425edebc6",
        "retained_native_index.npy":
            "c0b19f204fecad603c0d8b63bfe0a0643cb57ea74694d4f8849e443786072e4c",
        "retained_offsets.npy":
            "5fd86ec64fe858b3ed665f11a06f4ca7f054e83c51c6e21cb3339693cb99da64",
    }

    exec(
        compile(
            transformed,
            "<f3b6-heldout-payload-loader>",
            "exec",
        ),
        namespace,
    )


    loader = namespace.get(
        "load_heldout_payload_dataset"
    )

    if loader is None:
        raise RuntimeError(
            "Derived HELDOUT payload loader missing"
        )


    return (
        loader,
        hashlib.sha256(
            transformed.encode(
                "utf-8"
            )
        ).hexdigest(),
    )


def load_heldout_plan(
    repo: Path,
    runner,
) -> list[dict[str, Any]]:

    paths = verify_frozen_inputs(
        repo
    )

    plan_rows, plan_fields = (
        read_csv(
            paths[
                "heldout_plan"
            ]
        )
    )

    decision_rows, decision_fields = (
        read_csv(
            paths[
                "decision"
            ]
        )
    )


    if (
        FORBIDDEN_EXECUTION_FIELDS
        & set(
            plan_fields
        )
    ):
        raise RuntimeError(
            "Truth/outcome field in HELDOUT plan"
        )


    if (
        FORBIDDEN_EXECUTION_FIELDS
        & set(
            decision_fields
        )
    ):
        raise RuntimeError(
            "Truth/outcome field in HELDOUT decision grid"
        )


    if len(
        plan_rows
    ) != 10800:
        raise RuntimeError(
            "HELDOUT exact plan != 10800"
        )


    if len(
        decision_rows
    ) != 3600:
        raise RuntimeError(
            "HELDOUT decision grid != 3600"
        )


    if {
        row[
            "external_optimizer_seed"
        ]
        for row
        in plan_rows
    } != {"0"}:

        raise RuntimeError(
            "HELDOUT plan is not seed0-only"
        )


    if {
        row[
            "execution_status"
        ]
        for row
        in plan_rows
    } != {
        "NOT_EXECUTED"
    }:

        raise RuntimeError(
            "Frozen HELDOUT plan already contains execution"
        )


    decision_by_id = {
        row[
            "planned_decision_id"
        ]:
            row
        for row
        in decision_rows
    }


    if len(
        decision_by_id
    ) != 3600:
        raise RuntimeError(
            "Duplicate HELDOUT planned_decision_id"
        )


    jobs = []


    for row in plan_rows:

        decision_id = row[
            "planned_decision_id"
        ]

        decision = (
            decision_by_id.get(
                decision_id
            )
        )

        if decision is None:
            raise RuntimeError(
                f"Missing HELDOUT decision: {decision_id}"
            )


        if (
            decision[
                "decision_class"
            ]
            != "BASELINE"
        ):
            raise RuntimeError(
                "Non-baseline HELDOUT decision"
            )


        job = dict(
            row
        )

        # Frozen F3B.3 execute_one_job() expects the decision
        # class operational field.  This comes only from the
        # blinded F3B.5 decision grid.
        job[
            "decision_class"
        ] = "BASELINE"

        # Normalize every HELDOUT job through the frozen F3B.3
        # contract before it can reach execute_one_job().  This
        # converts integer fields and attaches model_name exactly
        # as DEVELOPMENT did.
        job = runner.validate_job(
            job
        )

        jobs.append(
            job
        )


    return jobs


def verify_heldout_payload_contract(
    repo: Path,
) -> str:

    runner = load_frozen_runner(
        repo
    )

    loader, loader_sha = (
        derive_heldout_payload_loader(
            repo,
            runner,
        )
    )

    payloads = loader(
        repo
    )

    jobs = load_heldout_plan(
        repo,
        runner,
    )


    required_job_fields = {
        "decision_class",
        "job_order",
        "external_optimizer_seed",
        "model_id",
        "model_name",
    }


    if not required_job_fields.issubset(
        jobs[0]
    ):
        raise RuntimeError(
            "HELDOUT normalized job contract incomplete"
        )


    # One extraction is enough to prove that the mechanically
    # derived loader returns the exact payload structure expected
    # by the frozen numerical core.  No AFINO call is made.
    runner.extract_payload(
        jobs[0],
        payloads,
    )


    if afino_loaded():
        raise RuntimeError(
            "HELDOUT payload preflight imported AFINO"
        )


    return loader_sha


def verify_afino_environment(
    repo: Path,
    afino_repo: Path,
    runner,
) -> None:

    paths = frozen_paths(
        repo
    )

    binding = json.loads(
        paths[
            "f3b3_binding"
        ].read_text(
            encoding="utf-8"
        )
    )

    runner.verify_environment(
        afino_repo,
        binding,
    )


def run_development_regression(
    repo: Path,
    afino_repo: Path,
    audit_path: Path,
) -> None:

    if audit_path.exists():
        raise RuntimeError(
            "Regression audit already exists"
        )


    runner = load_frozen_runner(
        repo
    )

    paths = frozen_paths(
        repo
    )


    verify_afino_environment(
        repo,
        afino_repo,
        runner,
    )


    replay_rows, replay_fields = (
        read_csv(
            paths[
                "replay"
            ]
        )
    )

    canary_rows, canary_fields = (
        read_csv(
            paths[
                "canary_results"
            ]
        )
    )

    development_plan, _ = (
        read_csv(
            paths[
                "development_plan"
            ]
        )
    )


    if len(
        replay_rows
    ) != 18:
        raise RuntimeError(
            "Frozen replay reference != 18 rows"
        )


    if (
        "job_id"
        not in replay_fields
        or
        "overall_match"
        not in replay_fields
    ):
        raise RuntimeError(
            "Frozen replay schema changed"
        )


    if sum(
        row[
            "overall_match"
        ]
        == "True"
        for row
        in replay_rows
    ) != 18:

        raise RuntimeError(
            "Frozen replay reference is not 18/18"
        )


    if (
        "result_core_sha256"
        not in canary_fields
    ):
        raise RuntimeError(
            "Frozen canary results lack result_core_sha256"
        )


    plan_by_job = {
        row[
            "job_id"
        ]:
            row
        for row
        in development_plan
    }

    canary_by_job = {
        row[
            "job_id"
        ]:
            row
        for row
        in canary_rows
    }


    if len(
        canary_by_job
    ) != len(
        canary_rows
    ):
        raise RuntimeError(
            "Duplicate frozen canary job_id"
        )


    payloads = (
        runner.load_payload_dataset(
            repo
        )
    )


    fields = [
        "anchor_id",
        "job_id",
        "planned_decision_id",
        "simulation_unit_id",
        "external_optimizer_seed",
        "model_id",
        "expected_status",
        "observed_status",
        "expected_result_core_sha256",
        "observed_result_core_sha256",
        "status_match",
        "result_core_match",
        "overall_match",
    ]


    audit_rows = []


    for anchor_index, replay in enumerate(
        replay_rows,
        start=1,
    ):

        job_id = replay[
            "job_id"
        ]


        job = (
            plan_by_job.get(
                job_id
            )
        )

        expected = (
            canary_by_job.get(
                job_id
            )
        )


        if (
            job is None
            or expected is None
        ):
            raise RuntimeError(
                f"Regression anchor missing: {job_id}"
            )


        # This is DEVELOPMENT only.
        if (
            "HELDOUT"
            in str(
                job
            )
        ):
            raise RuntimeError(
                "HELDOUT job reached DEVELOPMENT regression"
            )


        job = runner.validate_job(
            job
        )

        result = (
            runner.execute_one_job(
                job,
                payloads,
            )
        )


        observed_core = (
            runner.result_core_sha256(
                result
            )
        )

        expected_core = (
            expected[
                "result_core_sha256"
            ]
        )


        status_match = (
            str(
                result[
                    "status"
                ]
            )
            ==
            expected[
                "status"
            ]
        )

        result_core_match = (
            observed_core
            ==
            expected_core
        )

        overall = (
            status_match
            and result_core_match
        )


        audit_rows.append(
            {
                "anchor_id":
                    replay.get(
                        "anchor_id",
                        f"F3B6_REG_{anchor_index:02d}",
                    ),

                "job_id":
                    job_id,

                "planned_decision_id":
                    job[
                        "planned_decision_id"
                    ],

                "simulation_unit_id":
                    job[
                        "simulation_unit_id"
                    ],

                "external_optimizer_seed":
                    job[
                        "external_optimizer_seed"
                    ],

                "model_id":
                    job[
                        "model_id"
                    ],

                "expected_status":
                    expected[
                        "status"
                    ],

                "observed_status":
                    result[
                        "status"
                    ],

                "expected_result_core_sha256":
                    expected_core,

                "observed_result_core_sha256":
                    observed_core,

                "status_match":
                    str(
                        status_match
                    ),

                "result_core_match":
                    str(
                        result_core_match
                    ),

                "overall_match":
                    str(
                        overall
                    ),
            }
        )


        print(
            f"development_regression[{anchor_index:02d}] "
            f"{job_id} "
            f"seed={job['external_optimizer_seed']} "
            f"model={job['model_id']} "
            f"match={overall}"
        )


        if not overall:

            write_csv(
                audit_path,
                audit_rows,
                fields,
            )

            raise RuntimeError(
                f"DEVELOPMENT regression mismatch: {job_id}"
            )


    write_csv(
        audit_path,
        audit_rows,
        fields,
    )


    if sum(
        row[
            "overall_match"
        ]
        == "True"
        for row
        in audit_rows
    ) != 18:

        raise RuntimeError(
            "DEVELOPMENT regression != 18/18 exact"
        )


    print(
        "F3B6_DEVELOPMENT_RUNNER_REGRESSION_PASS"
    )

    print(
        "development_regression_jobs = 18"
    )

    print(
        "development_regression_exact = 18/18"
    )

    print(
        "heldout_jobs_executed = 0"
    )


def _jsonable(
    value: Any,
) -> Any:

    if isinstance(
        value,
        dict,
    ):

        return {
            str(key):
                _jsonable(
                    item
                )
            for key, item
            in value.items()
        }


    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):

        return [
            _jsonable(
                item
            )
            for item
            in value
        ]


    if hasattr(
        value,
        "item",
    ):

        try:
            return value.item()
        except Exception:
            pass


    return value


def verify_single_use_authorization(
    repo: Path,
    authorization_path: Path,
) -> dict[str, Any]:

    if not authorization_path.is_file():
        raise RuntimeError(
            "F3B6_SINGLE_USE_EXECUTION_AUTHORIZATION_REQUIRED"
        )


    relative = (
        authorization_path
        .resolve()
        .relative_to(
            repo.resolve()
        )
        .as_posix()
    )


    subprocess.run(
        [
            "git",
            "cat-file",
            "-e",
            f"HEAD:{relative}",
        ],
        cwd=repo,
        check=True,
    )


    auth = json.loads(
        authorization_path.read_text(
            encoding="utf-8"
        )
    )


    if (
        auth.get(
            "artifact_role"
        )
        !=
        "F3B6_SINGLE_USE_EXECUTION_AUTHORIZATION"
        or
        auth.get(
            "status"
        )
        !=
        "AUTHORIZED_FOR_SINGLE_USE_AFINO_EXECUTION"
    ):

        raise RuntimeError(
            "Invalid F3B.6 single-use execution authorization"
        )


    permissions = auth.get(
        "permissions",
        {},
    )


    required_true = {
        "heldout_afino_execution_authorized",
    }


    required_false = {
        "truth_join_authorized",
        "heldout_metrics_authorized",
        "rule_refitting_authorized",
        "threshold_mutation_authorized",
        "candidate_search_authorized",
    }


    for key in required_true:

        if permissions.get(
            key
        ) is not True:
            raise RuntimeError(
                f"Authorization missing true permission: {key}"
            )


    for key in required_false:

        if permissions.get(
            key
        ) is not False:
            raise RuntimeError(
                f"Authorization firewall violation: {key}"
            )


    frozen = auth.get(
        "frozen_inputs",
        {},
    )


    adapter_path = Path(
        __file__
    ).resolve()

    binding_path = (
        frozen_paths(
            repo
        )[
            "binding"
        ]
    )


    expected_pairs = {
        "adapter_sha256":
            sha256_file(
                adapter_path
            ),

        "execution_input_binding_sha256":
            sha256_file(
                binding_path
            ),

        "heldout_payload_manifest_sha256":
            EXPECTED_PAYLOAD_SHA,

        "heldout_decision_grid_sha256":
            EXPECTED_DECISION_SHA,

        "heldout_exact_afino_plan_sha256":
            EXPECTED_PLAN_SHA,

        "final_rule_freeze_sha256":
            EXPECTED_FREEZE_SHA,
    }


    for key, expected in (
        expected_pairs.items()
    ):

        if frozen.get(
            key
        ) != expected:
            raise RuntimeError(
                f"Execution authorization binding mismatch: {key}"
            )


    return auth


def initialize_checkpoint(
    path: Path,
    metadata: dict[str, str],
) -> sqlite3.Connection:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    connection = sqlite3.connect(
        path
    )


    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS results (
            job_id TEXT PRIMARY KEY,
            job_order INTEGER NOT NULL,
            planned_decision_id TEXT NOT NULL,
            simulation_unit_id TEXT NOT NULL,
            external_optimizer_seed INTEGER NOT NULL,
            model_id TEXT NOT NULL,
            status TEXT NOT NULL,
            result_core_sha256 TEXT NOT NULL,
            result_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS invocations (
            invocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            max_new_jobs INTEGER NOT NULL,
            existing_before INTEGER NOT NULL,
            new_jobs INTEGER NOT NULL,
            pending_after INTEGER NOT NULL
        );
        """
    )


    existing = {
        row[0]:
            row[1]
        for row
        in connection.execute(
            "SELECT key,value FROM metadata"
        )
    }


    if existing:

        if existing != metadata:
            raise RuntimeError(
                "F3B.6 checkpoint metadata mismatch"
            )

    else:

        connection.executemany(
            "INSERT INTO metadata(key,value) VALUES (?,?)",
            list(
                metadata.items()
            ),
        )

        connection.commit()


    return connection


def export_blinded_results(
    connection: sqlite3.Connection,
    path: Path,
) -> None:

    rows = [
        json.loads(
            row[0]
        )
        for row
        in connection.execute(
            """
            SELECT result_json
            FROM results
            ORDER BY job_order
            """
        )
    ]


    if not rows:
        raise RuntimeError(
            "No F3B.6 results to export"
        )


    fields = list(
        rows[0].keys()
    )


    if (
        FORBIDDEN_EXECUTION_FIELDS
        & set(
            fields
        )
    ):
        raise RuntimeError(
            "Truth/outcome target field leaked into blinded results"
        )


    write_csv(
        path,
        rows,
        fields,
    )


def execute_heldout(
    *,
    repo: Path,
    afino_repo: Path,
    authorization_path: Path,
    checkpoint_path: Path,
    max_new_jobs: int,
    resume: bool,
    export_path: Path | None,
) -> None:

    verify_single_use_authorization(
        repo,
        authorization_path,
    )


    paths = verify_frozen_inputs(
        repo
    )

    runner = load_frozen_runner(
        repo
    )


    verify_afino_environment(
        repo,
        afino_repo,
        runner,
    )


    jobs = load_heldout_plan(
        repo,
        runner,
    )


    loader, loader_sha = (
        derive_heldout_payload_loader(
            repo,
            runner,
        )
    )

    payloads = loader(
        repo
    )


    if not resume:

        if checkpoint_path.exists():
            raise RuntimeError(
                "HELDOUT checkpoint exists; use --resume"
            )

    else:

        if not checkpoint_path.exists():
            raise RuntimeError(
                "--resume requested but HELDOUT checkpoint is absent"
            )


    metadata = {
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
            loader_sha,

        "authorization_sha256":
            sha256_file(
                authorization_path
            ),

        "execution_input_binding_sha256":
            sha256_file(
                paths[
                    "binding"
                ]
            ),
    }


    connection = initialize_checkpoint(
        checkpoint_path,
        metadata,
    )


    try:

        existing = {
            row[0]
            for row
            in connection.execute(
                "SELECT job_id FROM results"
            )
        }


        unknown = (
            existing
            - {
                job[
                    "job_id"
                ]
                for job
                in jobs
            }
        )


        if unknown:

            raise RuntimeError(
                "Checkpoint contains unknown HELDOUT job"
            )


        pending = [
            job
            for job
            in jobs
            if job[
                "job_id"
            ]
            not in existing
        ]


        existing_before = len(
            existing
        )


        selected = pending[
            :max_new_jobs
        ]


        new_jobs = 0


        for job in selected:

            result = (
                runner.execute_one_job(
                    job,
                    payloads,
                )
            )


            core_sha = (
                runner.result_core_sha256(
                    result
                )
            )


            result[
                "result_core_sha256"
            ] = core_sha


            result_json = json.dumps(
                _jsonable(
                    result
                ),
                sort_keys=True,
                separators=(
                    ",",
                    ":",
                ),
                ensure_ascii=False,
                allow_nan=False,
            )


            connection.execute(
                """
                INSERT INTO results(
                    job_id,
                    job_order,
                    planned_decision_id,
                    simulation_unit_id,
                    external_optimizer_seed,
                    model_id,
                    status,
                    result_core_sha256,
                    result_json
                )
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    job[
                        "job_id"
                    ],
                    int(
                        job[
                            "job_order"
                        ]
                    ),
                    job[
                        "planned_decision_id"
                    ],
                    job[
                        "simulation_unit_id"
                    ],
                    int(
                        job[
                            "external_optimizer_seed"
                        ]
                    ),
                    job[
                        "model_id"
                    ],
                    str(
                        result[
                            "status"
                        ]
                    ),
                    core_sha,
                    result_json,
                ),
            )

            connection.commit()

            new_jobs += 1


            if (
                result[
                    "status"
                ]
                != "OK"
            ):

                raise RuntimeError(
                    "PHASE3B_HELDOUT_EXECUTION_BLOCKED: "
                    "numerical job status != OK"
                )


        total_after = connection.execute(
            "SELECT COUNT(*) FROM results"
        ).fetchone()[0]

        pending_after = (
            len(
                jobs
            )
            - total_after
        )


        connection.execute(
            """
            INSERT INTO invocations(
                max_new_jobs,
                existing_before,
                new_jobs,
                pending_after
            )
            VALUES (?,?,?,?)
            """,
            (
                max_new_jobs,
                existing_before,
                new_jobs,
                pending_after,
            ),
        )

        connection.commit()


        if export_path is not None:

            export_blinded_results(
                connection,
                export_path,
            )


        print(
            "F3B6_HELDOUT_INVOCATION_COMPLETE"
        )

        print(
            "existing_before =",
            existing_before,
        )

        print(
            "new_jobs =",
            new_jobs,
        )

        print(
            "total_after =",
            total_after,
        )

        print(
            "pending_after =",
            pending_after,
        )

        print(
            "truth_join_performed = false"
        )

        print(
            "heldout_metrics_computed = false"
        )


    finally:

        connection.close()


def build_parser():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo-root",
        default=".",
    )

    parser.add_argument(
        "--afino-repo",
    )

    parser.add_argument(
        "--preflight-only",
        action="store_true",
    )

    parser.add_argument(
        "--development-regression",
        action="store_true",
    )

    parser.add_argument(
        "--regression-audit",
    )

    parser.add_argument(
        "--authorization",
    )

    parser.add_argument(
        "--checkpoint",
    )

    parser.add_argument(
        "--max-new-jobs",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--resume",
        action="store_true",
    )

    parser.add_argument(
        "--export-results",
    )

    return parser


def main(
    argv=None,
) -> int:

    args = (
        build_parser()
        .parse_args(
            argv
        )
    )

    repo = Path(
        args.repo_root
    ).resolve()


    verify_frozen_inputs(
        repo
    )


    if args.preflight_only:

        loader_sha = (
            verify_heldout_payload_contract(
                repo
            )
        )

        print(
            "F3B6_HELDOUT_ADAPTER_PREFLIGHT_PASS"
        )

        print(
            "derived_heldout_payload_loader_sha256 =",
            loader_sha,
        )

        print(
            "heldout_plan_jobs = 10800"
        )

        print(
            "heldout_jobs_executed = 0"
        )

        print(
            "afino_executed = false"
        )

        return 0


    if args.development_regression:

        if not args.afino_repo:
            raise RuntimeError(
                "--development-regression requires --afino-repo"
            )

        if not args.regression_audit:
            raise RuntimeError(
                "--development-regression requires --regression-audit"
            )

        run_development_regression(
            repo,
            Path(
                args.afino_repo
            ).resolve(),
            Path(
                args.regression_audit
            ).resolve(),
        )

        return 0


    if not args.authorization:
        raise RuntimeError(
            "HELDOUT execution requires committed F3B.6 authorization"
        )

    if not args.afino_repo:
        raise RuntimeError(
            "HELDOUT execution requires --afino-repo"
        )

    if not args.checkpoint:
        raise RuntimeError(
            "HELDOUT execution requires --checkpoint"
        )

    if args.max_new_jobs <= 0:
        raise RuntimeError(
            "--max-new-jobs must be > 0"
        )


    execute_heldout(
        repo=repo,
        afino_repo=Path(
            args.afino_repo
        ).resolve(),
        authorization_path=Path(
            args.authorization
        ).resolve(),
        checkpoint_path=Path(
            args.checkpoint
        ).resolve(),
        max_new_jobs=args.max_new_jobs,
        resume=args.resume,
        export_path=(
            Path(
                args.export_results
            ).resolve()
            if args.export_results
            else None
        ),
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
