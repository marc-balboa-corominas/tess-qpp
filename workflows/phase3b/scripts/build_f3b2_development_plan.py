#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path
from typing import Any

EXPECTED_HEAD = "467abe9d5fc8379e342f7c98d735aae12ad56ea1"
F3B1_COMMIT = "b8680934644be1bfec196e2009311b3060968f0a"
F3B1_TAG = "phase3b-design-v1"

EXPECTED_CURRENT_HASHES = {
    "workflows/phase3b/scripts/build_f3b2_generator_canary.py":
        "04508c681ba686d6fc8c70bcfdbb3211d99aeed7299e4e8b81e1fb9da27e91e2",
    "workflows/phase3b/scripts/materialize_f3b_development.py":
        "9624db78a8685f042b868ef90b2210a5ccb4e935ed27599e8fa18336333eed44",
    "workflows/phase3b/development/evidence/tables/f3b2_generator_canary_manifest.csv":
        "6f1b42bfd1d7ae5dd58888c5821d120b0ffb1cedd3bf870099bc1dfe93c981a1",
    "workflows/phase3b/development/evidence/reports/f3b2_generator_validation_audit.json":
        "e17ed74394c8cc0f78c65dc72a7385168fda626402a794a3b84be18383bec9f7",
    "workflows/phase3b/development/evidence/tables/f3b2_development_background_manifest.csv":
        "601c38abbe47f942845b395db905fc2a372fd7a96d496f9a4070817caed3186e",
    "workflows/phase3b/development/evidence/tables/f3b2_development_series_manifest.csv":
        "1fc68051e3c43a9acaac5d861234fb1824d689e5e64bed5ef5810ffd0c4a6535",
    "workflows/phase3b/development/evidence/tables/f3b2_development_truth_ledger.csv":
        "a0111af78e1545507d54dcb50f7532a10b266ffe8af8f956f70c1bdf9876a820",
    "workflows/phase3b/development/evidence/tables/f3b2_development_admissibility.csv":
        "e834f5a9635354ea8b8907ef00e707a90a23a0d78cd1e7160117a3b583b35933",
    "workflows/phase3b/development/evidence/tables/f3b2_development_payload_manifest.csv":
        "fcfc9b20d111ba711fc4e05de28f340bed9046efe40e6877efbd991c410df6c6",
    "workflows/phase3b/development/evidence/reports/f3b2_development_materialization_audit.json":
        "4ae93eda9635950cf5a4d1b9d54674a949cb5bfac8099f26ff49d7f152d52724",
    "workflows/phase3b/development/evidence/reports/f3b2_heldout_nonmaterialization_audit.json":
        "1386daece4ff68bc007587a379102d86b854ce38dc8142a346944c119d96f8fa",
    "workflows/phase3b/development/evidence/reports/f3b2_development_leakage_audit.json":
        "3c32e59431c3aebd38ab24ab950c4c6a921a41bce2b335b6e8e74d2e03a235f9",
}

EXPECTED_DIRTY_PATHS = set(EXPECTED_CURRENT_HASHES)

NUMSTAB_PATH = Path(
    "workflows/phase3b/design/f3b1_numerical_stability_protocol.json"
)
SERIES_PATH = Path(
    "workflows/phase3b/development/evidence/tables/"
    "f3b2_development_series_manifest.csv"
)
MATERIALIZATION_AUDIT = Path(
    "workflows/phase3b/development/evidence/reports/"
    "f3b2_development_materialization_audit.json"
)
HELDOUT_AUDIT = Path(
    "workflows/phase3b/development/evidence/reports/"
    "f3b2_heldout_nonmaterialization_audit.json"
)
LEAKAGE_AUDIT = Path(
    "workflows/phase3b/development/evidence/reports/"
    "f3b2_development_leakage_audit.json"
)
DECISION_GRID = Path(
    "workflows/phase3b/development/evidence/tables/"
    "f3b2_development_decision_grid.csv"
)
EXACT_PLAN = Path(
    "workflows/phase3b/development/evidence/tables/"
    "f3b2_development_exact_afino_plan.csv"
)
REPORT = Path(
    "workflows/phase3b/development/evidence/reports/"
    "f3b2_development_materialization_report.md"
)
SHA_REGISTRY = Path(
    "workflows/phase3b/development/evidence/f3b2_SHA256SUMS.txt"
)
REPO_SCRIPT = Path(
    "workflows/phase3b/scripts/build_f3b2_development_plan.py"
)
ROOT_README = Path("workflows/phase3b/README.md")
DEV_README = Path("workflows/phase3b/development/README.md")
HELDOUT_README = Path("workflows/phase3b/heldout/README.md")

ARRAY_DIR = Path("data/interim/phase3b/f3b2_development")
HELDOUT_ARRAY_DIR = Path("data/interim/phase3b/heldout")

EXPECTED_README_HASHES = {
    "workflows/phase3b/README.md":
        "986c0356872193af3a6955e261648a17f67b581513edc0365b3924dfe8a8d956",
    "workflows/phase3b/development/README.md":
        "5ce69e12618f642033912ca37b7e1fc2f2ceea8b0659ccbbc5b095a669d29cb1",
    "workflows/phase3b/heldout/README.md":
        "9bd5944971a918a9bf5a3305d263a7ca39fedc83797704d62727942808e9184f",
}

AFINO_VERSION = "0.5"
AFINO_COMMIT = "6aceac9518fc8056052807e666da9d0c8bebb010"
CUTOFF_HZ = 0.025
MODELS = ("M0", "M1", "M2")


def run(repo: Path, *args: str, check: bool = True):
    cp = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and cp.returncode:
        raise RuntimeError(
            "git " + " ".join(args) + " failed: "
            + cp.stderr.decode(errors="replace").strip()
        )
    return cp


def gt(repo: Path, *args: str) -> str:
    return run(repo, *args).stdout.decode("utf-8", errors="replace").strip()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def csv_bytes(rows: list[dict[str, Any]], fields: list[str]) -> bytes:
    sio = io.StringIO(newline="")
    writer = csv.DictWriter(sio, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return sio.getvalue().encode("utf-8")


def write_json(path: Path, obj: Any):
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\wΔ≥–-]+(?:['’][\w]+)?\b", text, flags=re.UNICODE))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()
    repo = Path(args.repo_root).resolve()

    if gt(repo, "rev-parse", "HEAD") != EXPECTED_HEAD:
        raise RuntimeError("Unexpected HEAD before DEVELOPMENT plan freeze.")
    if gt(repo, "rev-parse", F3B1_TAG + "^{}") != F3B1_COMMIT:
        raise RuntimeError("F3B.1 tag mismatch.")
    if gt(repo, "diff", "--cached", "--name-only"):
        raise RuntimeError("Staged changes exist before plan freeze.")

    status_lines = run(
        repo, "status", "--short", "--untracked-files=all"
    ).stdout.decode("utf-8", errors="replace").splitlines()
    dirty = {
        line[3:].strip().replace("\\", "/")
        for line in status_lines if line.strip()
    }
    if dirty != EXPECTED_DIRTY_PATHS:
        raise RuntimeError(
            "Unexpected working-tree state before plan freeze: "
            + repr(sorted(dirty))
        )

    for rel, expected_sha in EXPECTED_CURRENT_HASHES.items():
        path = repo / rel
        if not path.is_file() or sha_file(path) != expected_sha:
            raise RuntimeError("Reviewed materialization SHA mismatch: " + rel)

    for rel, expected_sha in EXPECTED_README_HASHES.items():
        path = repo / rel
        if not path.is_file() or sha_file(path) != expected_sha:
            raise RuntimeError("Pre-plan README/guard SHA mismatch: " + rel)

    if not (repo / ARRAY_DIR).is_dir():
        raise RuntimeError("Frozen DEVELOPMENT array directory missing.")
    if (repo / HELDOUT_ARRAY_DIR).exists():
        raise RuntimeError("HELDOUT array directory exists.")

    mat = json.loads((repo / MATERIALIZATION_AUDIT).read_text(encoding="utf-8"))
    held = json.loads((repo / HELDOUT_AUDIT).read_text(encoding="utf-8"))
    leak = json.loads((repo / LEAKAGE_AUDIT).read_text(encoding="utf-8"))

    required_mat = {
        "development_registry_rows": 4320,
        "development_backgrounds": 1800,
        "primary_planned": 3600,
        "challenge_planned": 720,
        "positive_total": 2160,
        "null_total": 2160,
        "materialized_series": 4320,
        "materialization_failures": 0,
        "primary_eligible": 3600,
        "primary_inadmissible": 0,
        "heldout_registry_rows": 4320,
        "heldout_materialized_rows": 0,
        "heldout_noise_draws": 0,
        "heldout_period_draws": 0,
    }
    for key, value in required_mat.items():
        if mat.get(key) != value:
            raise RuntimeError(f"Materialization audit mismatch: {key}")

    if mat["rematerialization"]["status"] != \
            "F3B2_DEVELOPMENT_REMATERIALIZATION_EXACT":
        raise RuntimeError("Rematerialization is not exact.")
    if any(
        mat["rematerialization"][key] != 0
        for key in [
            "background_hash_mismatches",
            "latent_hash_mismatches",
            "retained_payload_hash_mismatches",
            "truth_record_mismatches",
            "array_file_byte_mismatches",
        ]
    ):
        raise RuntimeError("Nonzero rematerialization mismatch.")
    if mat.get("afino_executed") is not False:
        raise RuntimeError("AFINO already executed before plan freeze.")
    if mat.get("scientific_metrics_computed") is not False:
        raise RuntimeError("Scientific metrics exist before plan freeze.")
    if held.get("heldout_generated") is not False or \
            held.get("heldout_accessed") is not False:
        raise RuntimeError("HELDOUT state violation.")
    if leak.get("background_split_overlap") != 0:
        raise RuntimeError("Split leakage detected.")
    if leak.get("afino_executed") is not False:
        raise RuntimeError("Leakage audit reports AFINO execution.")

    # Verify every persistent array against the physical hash frozen by the
    # materialization audit.
    array_hashes = mat["arrays"]["files"]
    for filename, expected_sha in array_hashes.items():
        path = repo / ARRAY_DIR / filename
        if not path.is_file() or sha_file(path) != expected_sha:
            raise RuntimeError("Frozen DEVELOPMENT array hash mismatch: " + filename)

    # Refuse overwrite of plan/finalization artifacts.
    for rel in [REPO_SCRIPT, DECISION_GRID, EXACT_PLAN, REPORT, SHA_REGISTRY]:
        if (repo / rel).exists():
            raise RuntimeError("Refusing overwrite: " + rel.as_posix())

    # Copy the exact executed planner to the repository.
    source = Path(__file__).read_bytes()
    repo_script = repo / REPO_SCRIPT
    repo_script.parent.mkdir(parents=True, exist_ok=True)
    repo_script.write_bytes(source)
    if sha_file(repo_script) != hashlib.sha256(source).hexdigest():
        raise RuntimeError("Repository planner copy mismatch.")

    series = read_csv(repo / SERIES_PATH)
    if len(series) != 4320:
        raise RuntimeError("Series manifest does not have 4320 rows.")
    by_sid = {r["simulation_unit_id"]: r for r in series}
    if len(by_sid) != 4320:
        raise RuntimeError("Duplicate simulation_unit_id in series manifest.")

    primary_eligible = sorted(
        [
            r for r in series
            if r["evidence_plane"] == "SYNTHETIC_GROUND_TRUTH_CLASSIFICATION"
            and r["gap_quality_regime"] == "CONTIGUOUS_ALL_GOOD"
            and r["input_state"] == "ELIGIBLE_FOR_AFINO"
            and r["materialization_status"] == "MATERIALIZED"
        ],
        key=lambda r: r["simulation_unit_id"],
    )
    if len(primary_eligible) != 3600:
        raise RuntimeError(
            f"Expected 3600 eligible primary series, got {len(primary_eligible)}."
        )

    challenge_rows = [
        r for r in series if r["evidence_plane"] == "INPUT_ADMISSIBILITY"
    ]
    if len(challenge_rows) != 720:
        raise RuntimeError("Challenge row count != 720.")
    if any(r["input_state"] != "INPUT_INADMISSIBLE" for r in challenge_rows):
        raise RuntimeError("An admissibility challenge unexpectedly reached classifier.")
    if any(r["logical_payload_sha256"] == "" for r in primary_eligible):
        raise RuntimeError("Eligible primary series lacks payload hash.")

    numstab = json.loads((repo / NUMSTAB_PATH).read_text(encoding="utf-8"))
    selected = numstab["selected_backgrounds"]
    stability_sids = sorted(
        sid
        for item in selected
        for sid in item["simulation_unit_ids"]
    )
    if len(stability_sids) != 72 or len(set(stability_sids)) != 72:
        raise RuntimeError("Frozen numerical-stability subset != 72 unique series.")
    for sid in stability_sids:
        if sid not in by_sid:
            raise RuntimeError("Frozen stability series absent from materialization: " + sid)
        row = by_sid[sid]
        if not (
            row["evidence_plane"] == "SYNTHETIC_GROUND_TRUTH_CLASSIFICATION"
            and row["gap_quality_regime"] == "CONTIGUOUS_ALL_GOOD"
            and row["input_state"] == "ELIGIBLE_FOR_AFINO"
            and row["materialization_status"] == "MATERIALIZED"
        ):
            raise RuntimeError("Frozen stability series is not eligible primary: " + sid)

    decision_rows: list[dict[str, Any]] = []

    # Baseline seed 0: every eligible primary series exactly once.
    for row in primary_eligible:
        decision_rows.append(
            {
                "decision_class": "BASELINE",
                "simulation_unit_id": row["simulation_unit_id"],
                "background_realization_id": row["background_realization_id"],
                "truth_state": row["truth_state"],
                "external_optimizer_seed": 0,
                "payload_logical_sha256": row["logical_payload_sha256"],
                "input_state": row["input_state"],
                "gap_quality_regime": row["gap_quality_regime"],
                "planned_model_calls": 3,
                "execution_status": "NOT_EXECUTED",
            }
        )

    # Numerical stability adds only seeds 1..9 to the frozen 72 series.
    for sid in stability_sids:
        row = by_sid[sid]
        for seed in range(1, 10):
            decision_rows.append(
                {
                    "decision_class": "NUMERICAL_STABILITY_EXTRA",
                    "simulation_unit_id": sid,
                    "background_realization_id": row["background_realization_id"],
                    "truth_state": row["truth_state"],
                    "external_optimizer_seed": seed,
                    "payload_logical_sha256": row["logical_payload_sha256"],
                    "input_state": row["input_state"],
                    "gap_quality_regime": row["gap_quality_regime"],
                    "planned_model_calls": 3,
                    "execution_status": "NOT_EXECUTED",
                }
            )

    if len(decision_rows) != 4248:
        raise RuntimeError(f"Exact DEVELOPMENT decisions != 4248: {len(decision_rows)}")
    if sum(r["decision_class"] == "BASELINE" for r in decision_rows) != 3600:
        raise RuntimeError("Baseline decision count != 3600.")
    if sum(
        r["decision_class"] == "NUMERICAL_STABILITY_EXTRA"
        for r in decision_rows
    ) != 648:
        raise RuntimeError("Stability-extra decision count != 648.")

    decision_keys = [
        (r["simulation_unit_id"], int(r["external_optimizer_seed"]))
        for r in decision_rows
    ]
    if len(set(decision_keys)) != len(decision_keys):
        raise RuntimeError("Duplicate simulation-unit/optimizer-seed decision.")

    # Stable, frozen IDs/orders.
    for idx, row in enumerate(decision_rows, start=1):
        row["decision_order"] = idx
        row["planned_decision_id"] = f"F3B2D{idx:06d}"

    decision_fields = [
        "planned_decision_id", "decision_order", "decision_class",
        "simulation_unit_id", "background_realization_id", "truth_state",
        "external_optimizer_seed", "payload_logical_sha256",
        "input_state", "gap_quality_regime",
        "planned_model_calls", "execution_status",
    ]
    decision_bytes = csv_bytes(decision_rows, decision_fields)
    (repo / DECISION_GRID).parent.mkdir(parents=True, exist_ok=True)
    (repo / DECISION_GRID).write_bytes(decision_bytes)

    plan_rows: list[dict[str, Any]] = []
    job_order = 0
    for decision in decision_rows:
        for model_id in MODELS:
            job_order += 1
            plan_rows.append(
                {
                    "job_id": f"F3B2J{job_order:07d}",
                    "job_order": job_order,
                    "planned_decision_id": decision["planned_decision_id"],
                    "decision_class": decision["decision_class"],
                    "simulation_unit_id": decision["simulation_unit_id"],
                    "background_realization_id":
                        decision["background_realization_id"],
                    "truth_state": decision["truth_state"],
                    "external_optimizer_seed":
                        decision["external_optimizer_seed"],
                    "model_id": model_id,
                    "payload_logical_sha256":
                        decision["payload_logical_sha256"],
                    "afino_version": AFINO_VERSION,
                    "afino_commit": AFINO_COMMIT,
                    "low_frequency_cutoff_hz": CUTOFF_HZ,
                    "execution_status": "NOT_EXECUTED",
                }
            )

    if len(plan_rows) != 12744:
        raise RuntimeError(f"Exact model-call plan != 12744: {len(plan_rows)}")
    if any(r["execution_status"] != "NOT_EXECUTED" for r in plan_rows):
        raise RuntimeError("Plan contains executed job.")
    if any(r["model_id"] not in MODELS for r in plan_rows):
        raise RuntimeError("Unexpected model ID in exact plan.")
    if any(
        by_sid[r["simulation_unit_id"]]["evidence_plane"]
        == "INPUT_ADMISSIBILITY"
        for r in plan_rows
    ):
        raise RuntimeError("Challenge series leaked into exact AFINO plan.")

    plan_fields = [
        "job_id", "job_order", "planned_decision_id", "decision_class",
        "simulation_unit_id", "background_realization_id", "truth_state",
        "external_optimizer_seed", "model_id", "payload_logical_sha256",
        "afino_version", "afino_commit", "low_frequency_cutoff_hz",
        "execution_status",
    ]
    plan_bytes = csv_bytes(plan_rows, plan_fields)
    (repo / EXACT_PLAN).write_bytes(plan_bytes)

    # Finalize the materialization audit now that the future AFINO plan exists.
    mat["status"] = "PHASE3B_DEVELOPMENT_GENERATOR_VALIDATED_AND_MATERIALIZED"
    mat["final_f3b2_status_not_yet_declared"] = False
    mat["afino_plan_frozen"] = True
    mat["f3b2_closure_validation_pending"] = True
    mat["baseline_decisions_planned"] = 3600
    mat["stability_extra_decisions_planned"] = 648
    mat["total_development_decisions_planned"] = 4248
    mat["exact_model_calls_planned"] = 12744
    mat["m0_calls_planned"] = 4248
    mat["m1_calls_planned"] = 4248
    mat["m2_calls_planned"] = 4248
    mat["all_plan_jobs_execution_status"] = "NOT_EXECUTED"
    mat["decision_grid"] = {
        "path": DECISION_GRID.as_posix(),
        "sha256": hashlib.sha256(decision_bytes).hexdigest(),
        "rows": 4248,
    }
    mat["exact_afino_plan"] = {
        "path": EXACT_PLAN.as_posix(),
        "sha256": hashlib.sha256(plan_bytes).hexdigest(),
        "rows": 12744,
        "afino_version": AFINO_VERSION,
        "afino_commit": AFINO_COMMIT,
        "low_frequency_cutoff_hz": CUTOFF_HZ,
    }
    mat["afino_executed"] = False
    mat["candidate_rule_fitted"] = False
    mat["candidate_thresholds_generated"] = False
    mat["scientific_metrics_computed"] = False
    mat["next_required_block"] = (
        "validate complete F3B.2 closure; freeze Git/OSF; "
        "only then authorize F3B.3 runner work"
    )
    write_json(repo / MATERIALIZATION_AUDIT, mat)

    # Required human-readable report. It intentionally reports only structural
    # generator/materialization/plan facts, never classifier-performance metrics.
    report = f"""# F3B.2 — DEVELOPMENT generator/materialization report

## 1. Frozen F3B.1 inputs

F3B.2 was executed downstream of the immutable F3B.1 design freeze
`{F3B1_TAG}` at commit `{F3B1_COMMIT}`. The frozen split registry defines
4,320 DEVELOPMENT and 4,320 HELDOUT simulation units, with the split made at
the `background_realization_id` level. No F3B.1 scientific or design artifact
was edited during this task. The frozen generator family, parameter support,
quality-mask regimes, truth labels, numerical-stability subset and HELDOUT
single-use policy therefore remain authoritative.

## 2. Implementation RNG binding

Before any accepted F3B.2 stochastic evidence, the implementation binding was
committed at `{EXPECTED_HEAD}`. Accepted generation uses Python 3.13,
NumPy 2.3.5, little-endian execution, PCG64, the frozen background namespace,
`SeedSequence(...).spawn(2)` for noise and phase, and the separately namespaced
period RNG. The first attempted canary under NumPy 2.5.1 was invalidated as
`F3B2-ENV-001`, archived, removed from the active evidence set and never used
as scientific evidence. A later helper-only `py_compile` NameError was recorded
as `F3B2-TOOL-001`; it occurred before full-DEVELOPMENT RNG initialization and
generated no scientific bytes.

## 3. F1 generator continuity

The accepted environment re-ran the five frozen F1 regression cases. Time
grid, asymmetric flare envelope, Fourier red-noise realization, phase pairing,
null flux, stationary QPP component and positive flux remained continuous with
the validated F1 implementation at absolute tolerance 5e-12 and relative
tolerance zero. The accepted status is
`F3B2_F1_GENERATOR_CONTINUITY_PASS`. This establishes implementation
continuity for inherited generator mechanics; it is not an empirical-realism
claim.

## 4. F3B generator canary

The valid 88-series canary used 36 frozen DEVELOPMENT backgrounds from the
numerical-stability protocol, producing 72 primary paired series, plus four
deterministically selected DEVELOPMENT challenge backgrounds producing 16
challenge series. The canary passed time-grid, flare-envelope, red-noise,
pairing, period, phase and mask-invariance checks with zero redraws. No HELDOUT
identity entered a background, period, phase or noise stochastic call.

## 5. DEVELOPMENT backgrounds

Full DEVELOPMENT materialization generated exactly 1,800 frozen nuisance
background realizations. Every background retained redraw count zero. The
period draw attached to the positive member of each pair remained inside the
frozen 40–300 s support and every accepted positive period satisfied at least
three cycles within the native window. All 1,800 persisted background slices
passed physical-array roundtrip hash reconstruction.

## 6. Synthetic truth

The DEVELOPMENT registry contains 2,160 `SYNTHETIC_QPP_PRESENT` and 2,160
`SYNTHETIC_QPP_ABSENT` series when primary and challenge units are combined.
Synthetic truth is known by construction and remains explicitly distinct from
observational reference labels. Positive series carry the stationary
envelope-modulated sinusoid, true period, amplitude fraction and phase. Null
series record the QPP component and true period as not applicable at the
series-truth level.

## 7. Primary series

All 3,600 primary contiguous-all-good series materialized successfully and all
3,600 satisfy the frozen AFINO input-admissibility contract. There were zero
generation failures and zero primary inadmissible series. This is a structural
input result only. No AFINO model has been called, so no selection decision or
classification-performance quantity exists at F3B.2.

## 8. Admissibility challenges

All 720 prospectively assigned challenge series are
`INPUT_INADMISSIBLE`. The audit retains every simultaneously triggered reason
rather than collapsing each row to one explanation. Across all triggered
reasons, `IRREGULAR_SAMPLING` occurs 720 times,
`PEAK_REMOVED_BY_QUALITY` 360 times and `TOO_FEW_CADENCES` 180 times.
Under the inherited technical precedence, the primary reason counts are
270 irregular-sampling, 360 peak-removed and 90 too-few-cadences cases. These
challenge frequencies are design stress-test frequencies, not estimates of
observed TESS data-quality prevalence.

## 9. Payload integrity

The eight persistent DEVELOPMENT arrays are stored under
`data/interim/phase3b/f3b2_development/` and are excluded from ordinary Git
tracking. All 4,320 series can be reconstructed from their offsets and hashes:
the first physical roundtrip is 1,800/1,800 backgrounds and 4,320/4,320 series
with zero mismatches. A second complete temporary materialization reproduced
all background hashes, latent hashes, retained-payload hashes, truth-record
hashes and physical `.npy` files byte-for-byte. The status is
`F3B2_DEVELOPMENT_REMATERIALIZATION_EXACT`.

## 10. Exact future AFINO plan

AFINO remains unexecuted. F3B.2 freezes the future DEVELOPMENT worklist from
the materialized inputs. The baseline contains 3,600 decisions at external
optimizer seed 0, one for each eligible primary series. The pre-registered
72-series numerical-stability subset adds only seeds 1–9, producing 648 extra
decisions. The exact total is therefore 4,248 decisions. Each decision has
three planned model calls, M0, M1 and M2, for 12,744 exact future jobs. Every
job is pinned to AFINO 0.5, commit `{AFINO_COMMIT}`, the 0.025 Hz cutoff and
its frozen logical payload SHA-256. Every job remains `NOT_EXECUTED`.

## 11. HELDOUT non-materialization and leakage controls

The HELDOUT registry still contains 4,320 planned rows and 1,800 frozen
background identities, but no HELDOUT materialization directory exists. The
recorded counts remain zero for HELDOUT background RNG initializations, period
draws, noise draws, phase draws, flux arrays and payloads. The F3B.1 HELDOUT
README guard remains byte-exact. Truth was used to construct synthetic
positive/null series but has not been used as an AFINO inference feature.
Observational labels were not substituted for synthetic truth.

## 12. Limitations and task boundary

F3B.2 validates deterministic generator implementation, exact DEVELOPMENT
materialization, truth bookkeeping, admissibility handling, payload integrity
and the future execution plan. It does not report sensitivity, specificity,
FPR, balanced accuracy, a selection function, candidate thresholds or AFINO
outcomes because none yet exist. AFINO execution and rule development belong
to later tasks. HELDOUT remains ungenerated and unaccessed. The next permitted
step is closure validation and Git/OSF freezing of F3B.2; only after that
freeze may F3B.3 begin DEVELOPMENT runner validation and baseline execution.
"""
    wc = word_count(report)
    if not 900 <= wc <= 1300:
        raise RuntimeError(f"F3B.2 report word count {wc} outside 900..1300.")
    (repo / REPORT).write_text(report, encoding="utf-8", newline="\n")

    # Required README states. HELDOUT README is deliberately untouched.
    dev_readme = """# DEVELOPMENT

STATUS:
DEVELOPMENT MATERIALIZED AND FROZEN —
AFINO NOT STARTED

F3B.2 validated the frozen generator and materialized DEVELOPMENT only.
The exact persistent payload arrays are stored outside ordinary Git under
`data/interim/phase3b/f3b2_development/`.

The future DEVELOPMENT AFINO plan is frozen but every job remains
`NOT_EXECUTED`. HELDOUT remains ungenerated and unaccessed.
"""
    root_readme = """# Phase 3B

STATUS:
DEVELOPMENT MATERIALIZED —
AFINO EXECUTION NOT STARTED
HELDOUT NOT GENERATED

F3B.1 design freeze:
`phase3b-design-v1`
`b8680934644be1bfec196e2009311b3060968f0a`

F3B.2 implementation binding:
`467abe9d5fc8379e342f7c98d735aae12ad56ea1`

F3B.2 has validated the frozen generator, materialized 1,800 DEVELOPMENT
backgrounds / 4,320 DEVELOPMENT series, verified exact roundtrip and complete
rematerialization, and frozen the exact future AFINO worklist.

AFINO has not been executed. No sensitivity, specificity, FPR, selection
function estimate, candidate threshold or classifier outcome exists yet.

HELDOUT remains ungenerated, unaccessed and protected by its byte-exact F3B.1
guard. F3B.3 may begin only after F3B.2 closure validation plus Git/OSF freeze.
"""
    (repo / DEV_README).write_text(dev_readme, encoding="utf-8", newline="\n")
    (repo / ROOT_README).write_text(root_readme, encoding="utf-8", newline="\n")

    # HELDOUT guard must remain byte-exact.
    if sha_file(repo / HELDOUT_README) != EXPECTED_README_HASHES[
        "workflows/phase3b/heldout/README.md"
    ]:
        raise RuntimeError("HELDOUT README changed during plan freeze.")

    # Evidence SHA registry excludes itself.
    evidence_root = repo / "workflows/phase3b/development/evidence"
    evidence_files = sorted(
        p for p in evidence_root.rglob("*")
        if p.is_file() and p != repo / SHA_REGISTRY
    )
    sums = "\n".join(
        f"{sha_file(p)}  {p.relative_to(evidence_root).as_posix()}"
        for p in evidence_files
    ) + "\n"
    (repo / SHA_REGISTRY).write_text(sums, encoding="ascii", newline="\n")

    # Final internal plan checks.
    if len(read_csv(repo / DECISION_GRID)) != 4248:
        raise RuntimeError("Decision-grid reread row count mismatch.")
    reread_plan = read_csv(repo / EXACT_PLAN)
    if len(reread_plan) != 12744:
        raise RuntimeError("Exact-plan reread row count mismatch.")
    if any(r["execution_status"] != "NOT_EXECUTED" for r in reread_plan):
        raise RuntimeError("Exact-plan reread contains executed job.")

    # Protected historical scopes remain unchanged.
    for scope in [
        "foundation/f0-f2",
        "docs/literature/bibliographic_audit_ii",
        "workflows/phase3a",
    ]:
        if gt(repo, "diff", "--name-only", F3B1_COMMIT, "--", scope):
            raise RuntimeError("Protected historical scope changed: " + scope)

    print("F3B2_DEVELOPMENT_EXACT_AFINO_PLAN_FROZEN")
    print("planner_sha256 =", sha_file(repo / REPO_SCRIPT))
    print("decision_grid_sha256 =", sha_file(repo / DECISION_GRID))
    print("exact_afino_plan_sha256 =", sha_file(repo / EXACT_PLAN))
    print("materialization_audit_updated_sha256 =",
          sha_file(repo / MATERIALIZATION_AUDIT))
    print("materialization_report_sha256 =", sha_file(repo / REPORT))
    print("evidence_sha_registry_sha256 =", sha_file(repo / SHA_REGISTRY))
    print("evidence_checksum_entries =", len(evidence_files))
    print("report_word_count =", wc)
    print("baseline_decisions_planned = 3600")
    print("stability_extra_decisions_planned = 648")
    print("total_development_decisions_planned = 4248")
    print("m0_calls_planned = 4248")
    print("m1_calls_planned = 4248")
    print("m2_calls_planned = 4248")
    print("exact_model_calls_planned = 12744")
    print("all_plan_jobs_execution_status = NOT_EXECUTED")
    print("challenge_classifier_jobs = 0")
    print("heldout_registry_rows = 4320")
    print("heldout_generated = false")
    print("heldout_accessed = false")
    print("afino_executed = false")
    print("candidate_rule_fitted = false")
    print("scientific_metrics_computed = false")
    print("heldout_readme_byte_exact = true")
    print("NEXT = run final F3B.2 validator/tests before Git/OSF freeze")

if __name__ == "__main__":
    main()
