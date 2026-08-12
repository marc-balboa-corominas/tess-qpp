#!/usr/bin/env python3
"""
F3A.3 — build the frozen catalogue-runner canary strictly from the frozen F3A.2
resolved decision grid and exact AFINO plan.

This script:
- does NOT import or execute AFINO;
- does NOT inspect any F3A result/outcome;
- does NOT open FITS;
- does NOT regenerate variants or payloads;
- selects the canary prospectively from frozen pre-execution metadata only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import subprocess
from pathlib import Path
from collections import Counter, defaultdict

F3A2_COMMIT = "6bf9beca8fa8016495693575f8c86a2dec5fecb1"
F3A2_TAG = "phase3a-execution-plan-v1"

FROZEN_INPUT_HASHES = {
    "workflows/phase3a/evidence/tables/f3a2_cohort_manifest.csv":
        "03c2ecd52abe0a9b78897aae4c4238160eb0b0d051c8ccc1139913b604c813e8",
    "workflows/phase3a/evidence/tables/f3a2_payload_manifest.csv":
        "fa5bdfa20eaf499e5354caf159221577633de92f43ec31f48be31e16cd84c148",
    "workflows/phase3a/evidence/tables/f3a2_resolved_decision_grid.csv":
        "6d2292070332a5ca68ccd2c2d9a0673ec56657d6185845adf8dbc316d12557de",
    "workflows/phase3a/evidence/tables/f3a2_exact_afino_plan.csv":
        "d190a4f5e70339b05fd42b2d0cda9c51dd180c10e885c27fdfa43323c8dc1c6f",
    "workflows/phase3a/evidence/f3a2_SHA256SUMS.txt":
        "52d9cd40890a4d1e0e74ec8b5b2062840eceb968aecd4d3c4a8eea8255e5c08f",
}

DECISION_REL = Path(
    "workflows/phase3a/evidence/tables/f3a2_resolved_decision_grid.csv"
)
PLAN_REL = Path(
    "workflows/phase3a/evidence/tables/f3a2_exact_afino_plan.csv"
)
CANARY_DECISION_REL = Path(
    "workflows/phase3a/evidence/tables/f3a3_canary_decision_manifest.csv"
)
CANARY_JOB_REL = Path(
    "workflows/phase3a/evidence/tables/f3a3_canary_job_manifest.csv"
)

ROLES = [
    "PUBLISHED_QPP_REFERENCE",
    "PUBLISHED_NOT_SELECTED_REFERENCE",
]

WINDOW_ORDER = [
    "W00",
    "WSm2",
    "WSm1",
    "WSp1",
    "WSp2",
    "WEm2",
    "WEm1",
    "WEp1",
    "WEp2",
    "WX1",
    "WC1",
    "WX2",
    "WC2",
]

CYCLIC_PROFILES = [
    "P00",
    "P01",
    "P02",
    "P03",
    "P04",
    "P05",
    "P00",
    "P01",
    "P02",
    "P03",
    "P04",
    "P05",
    "P00",
]

EXPECTED_PRIMARY = 30
EXPECTED_STABILITY = 4
EXPECTED_DECISIONS = 34
EXPECTED_JOBS = 102
EXPECTED_MIN_N = 15
EXPECTED_MAX_N = 222

DECISION_EXTRA_FIELDS = [
    "canary_selection_component",
    "canary_selection_reason",
]

JOB_EXTRA_FIELDS = [
    "canary_selection_component",
    "canary_selection_reason",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(
    path: Path,
    rows: list[dict[str, str]],
    fieldnames: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=repo,
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def verify_f3a2_freeze(repo: Path) -> None:
    tag_commit = git(repo, "rev-parse", f"{F3A2_TAG}^{{}}")
    if tag_commit != F3A2_COMMIT:
        raise RuntimeError(
            f"{F3A2_TAG} does not dereference to the frozen F3A.2 commit: "
            f"{tag_commit} != {F3A2_COMMIT}"
        )

    for rel, expected in FROZEN_INPUT_HASHES.items():
        path = repo / rel
        if not path.is_file():
            raise RuntimeError(f"Missing frozen F3A.2 input: {rel}")
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(
                f"Frozen F3A.2 hash mismatch: {rel}\n"
                f"expected={expected}\nactual={actual}"
            )


def component_a(
    primary: list[dict[str, str]],
) -> list[tuple[dict[str, str], str, str]]:
    selected = []

    for role in ROLES:
        for window, profile in zip(WINDOW_ORDER, CYCLIC_PROFILES):
            candidates = [
                d for d in primary
                if d["observational_reference_role"] == role
                and d["window_variant_id"] == window
                and d["processing_profile_id"] == profile
            ]
            candidates.sort(
                key=lambda d: (
                    d["phase3a_event_id"],
                    d["planned_decision_id"],
                )
            )
            if not candidates:
                raise RuntimeError(
                    f"No READY primary decision for {role} {window} {profile}"
                )
            chosen = candidates[0]
            selected.append((
                chosen,
                "A_STRUCTURAL_COVERAGE",
                (
                    f"role={role};window={window};assigned_profile={profile};"
                    "lexicographically_smallest_phase3a_event_id"
                ),
            ))

    if len(selected) != 26:
        raise RuntimeError(f"Component A produced {len(selected)} decisions, expected 26.")
    return selected


def component_b(
    primary: list[dict[str, str]],
    selected_ids: set[str],
) -> list[tuple[dict[str, str], str, str]]:
    selected = []

    for role in ROLES:
        available = [
            d for d in primary
            if d["observational_reference_role"] == role
            and d["planned_decision_id"] not in selected_ids
        ]
        if not available:
            raise RuntimeError(f"No Component B candidates for role {role}")

        min_n = min(int(d["input_n_samples"]) for d in available)
        min_candidates = sorted(
            [
                d for d in available
                if int(d["input_n_samples"]) == min_n
            ],
            key=lambda d: d["planned_decision_id"],
        )
        shortest = min_candidates[0]
        selected.append((
            shortest,
            "B_LENGTH_EXTREMES",
            (
                f"role={role};primary_min_input_n_samples={min_n};"
                "planned_decision_id_lexicographic_tiebreak"
            ),
        ))
        selected_ids.add(shortest["planned_decision_id"])

        available = [
            d for d in primary
            if d["observational_reference_role"] == role
            and d["planned_decision_id"] not in selected_ids
        ]
        max_n = max(int(d["input_n_samples"]) for d in available)
        max_candidates = sorted(
            [
                d for d in available
                if int(d["input_n_samples"]) == max_n
            ],
            key=lambda d: d["planned_decision_id"],
        )
        longest = max_candidates[0]
        selected.append((
            longest,
            "B_LENGTH_EXTREMES",
            (
                f"role={role};primary_max_input_n_samples={max_n};"
                "planned_decision_id_lexicographic_tiebreak"
            ),
        ))
        selected_ids.add(longest["planned_decision_id"])

    if len(selected) != 4:
        raise RuntimeError(f"Component B produced {len(selected)} decisions, expected 4.")
    return selected


def component_c(
    primary: list[dict[str, str]],
    all_decisions: list[dict[str, str]],
    selected_primary_ids: set[str],
) -> list[tuple[dict[str, str], str, str]]:
    selected = []

    for role in ROLES:
        anchors = [
            d for d in primary
            if d["observational_reference_role"] == role
            and d["window_variant_id"] == "W00"
            and d["processing_profile_id"] == "P00"
        ]
        anchors.sort(
            key=lambda d: (
                d["phase3a_event_id"],
                d["planned_decision_id"],
            )
        )
        if not anchors:
            raise RuntimeError(f"No W00/P00 primary anchor for role {role}")
        anchor = anchors[0]

        if anchor["planned_decision_id"] not in selected_primary_ids:
            raise RuntimeError(
                f"Frozen rule expected seed-0 W00/P00 anchor to be in Component A: "
                f"{role} {anchor['planned_decision_id']}"
            )

        for seed in ("1", "9"):
            matches = [
                d for d in all_decisions
                if d["decision_class"] == "STABILITY"
                and d["observational_reference_role"] == role
                and d["variant_id"] == anchor["variant_id"]
                and d["window_variant_id"] == "W00"
                and d["processing_profile_id"] == "P00"
                and d["external_optimizer_seed"] == seed
                and d["resolved_decision_status"] == "READY_FOR_AFINO"
            ]
            if len(matches) != 1:
                raise RuntimeError(
                    f"Expected one stability decision for role={role}, "
                    f"variant={anchor['variant_id']}, seed={seed}; got {len(matches)}"
                )
            selected.append((
                matches[0],
                "C_SEED_CHECKPOINT",
                (
                    f"role={role};w00_p00_lexicographically_smallest_event="
                    f"{anchor['phase3a_event_id']};same_variant_as_seed0_anchor;"
                    f"external_optimizer_seed={seed}"
                ),
            ))

    if len(selected) != 4:
        raise RuntimeError(f"Component C produced {len(selected)} decisions, expected 4.")
    return selected


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()
    verify_f3a2_freeze(repo)

    decisions = read_csv(repo / DECISION_REL)
    plan = read_csv(repo / PLAN_REL)

    if len(decisions) != 7466:
        raise RuntimeError(f"Expected 7466 frozen F3A.2 decisions, got {len(decisions)}")
    if len(plan) != 22398:
        raise RuntimeError(f"Expected 22398 frozen F3A.2 jobs, got {len(plan)}")

    primary = [
        d for d in decisions
        if d["decision_class"] == "PRIMARY"
        and d["resolved_decision_status"] == "READY_FOR_AFINO"
        and d["external_optimizer_seed"] == "0"
    ]
    if len(primary) != 6422:
        raise RuntimeError(f"Expected 6422 READY primary decisions, got {len(primary)}")

    chosen = component_a(primary)
    selected_primary_ids = {d["planned_decision_id"] for d, _, _ in chosen}

    b_rows = component_b(primary, set(selected_primary_ids))
    chosen.extend(b_rows)
    selected_primary_ids.update(d["planned_decision_id"] for d, _, _ in b_rows)

    c_rows = component_c(
        primary,
        decisions,
        selected_primary_ids,
    )
    chosen.extend(c_rows)

    if len(chosen) != EXPECTED_DECISIONS:
        raise RuntimeError(
            f"Canary has {len(chosen)} decisions, expected {EXPECTED_DECISIONS}"
        )

    decision_ids = [d["planned_decision_id"] for d, _, _ in chosen]
    if len(set(decision_ids)) != EXPECTED_DECISIONS:
        raise RuntimeError("Duplicate planned_decision_id in canary.")

    primary_count = sum(d["decision_class"] == "PRIMARY" for d, _, _ in chosen)
    stability_count = sum(d["decision_class"] == "STABILITY" for d, _, _ in chosen)
    if primary_count != EXPECTED_PRIMARY or stability_count != EXPECTED_STABILITY:
        raise RuntimeError(
            f"Canary class counts invalid: PRIMARY={primary_count}, "
            f"STABILITY={stability_count}"
        )

    selection_meta = {
        d["planned_decision_id"]: (component, reason)
        for d, component, reason in chosen
    }

    # Decision manifest preserves every frozen decision column exactly and
    # appends only canary-selection metadata.
    decision_fieldnames = list(decisions[0].keys()) + DECISION_EXTRA_FIELDS
    decision_rows = []
    for d, component, reason in chosen:
        row = dict(d)
        row["canary_selection_component"] = component
        row["canary_selection_reason"] = reason
        decision_rows.append(row)

    # Job manifest is an exact subset of F3A.2 scientific columns. File order is
    # the original frozen F3A.2 job_order, not outcome- or runtime-dependent.
    canary_id_set = set(decision_ids)
    selected_jobs = [
        row for row in plan
        if row["planned_decision_id"] in canary_id_set
    ]
    selected_jobs.sort(key=lambda row: int(row["job_order"]))

    if len(selected_jobs) != EXPECTED_JOBS:
        raise RuntimeError(
            f"Canary has {len(selected_jobs)} jobs, expected {EXPECTED_JOBS}"
        )

    jobs_by_decision = Counter(row["planned_decision_id"] for row in selected_jobs)
    if set(jobs_by_decision.values()) != {3} or len(jobs_by_decision) != 34:
        raise RuntimeError("Canary does not have exactly three model jobs per decision.")

    model_counts = Counter(row["model_id"] for row in selected_jobs)
    if model_counts != {"M0": 34, "M1": 34, "M2": 34}:
        raise RuntimeError(f"Canary model counts invalid: {model_counts}")

    if any(row["execution_status"] != "NOT_EXECUTED" for row in selected_jobs):
        raise RuntimeError("Canary includes a job not frozen as NOT_EXECUTED.")

    job_fieldnames = list(plan[0].keys()) + JOB_EXTRA_FIELDS
    job_rows = []
    for row in selected_jobs:
        out = dict(row)
        component, reason = selection_meta[row["planned_decision_id"]]
        out["canary_selection_component"] = component
        out["canary_selection_reason"] = reason
        job_rows.append(out)

    # Prospective-coverage contract.
    primary_rows = [r for r in decision_rows if r["decision_class"] == "PRIMARY"]
    roles_covered = {r["observational_reference_role"] for r in primary_rows}
    windows_covered = {r["window_variant_id"] for r in primary_rows}
    profiles_covered = {r["processing_profile_id"] for r in primary_rows}
    n_values = [int(r["input_n_samples"]) for r in decision_rows]

    if roles_covered != set(ROLES):
        raise RuntimeError(f"Role coverage invalid: {roles_covered}")
    if windows_covered != set(WINDOW_ORDER):
        raise RuntimeError(f"Window coverage invalid: {windows_covered}")
    if profiles_covered != set(CYCLIC_PROFILES):
        raise RuntimeError(f"Profile coverage invalid: {profiles_covered}")
    if min(n_values) != EXPECTED_MIN_N or max(n_values) != EXPECTED_MAX_N:
        raise RuntimeError(
            f"Canary length range invalid: {min(n_values)}..{max(n_values)}"
        )

    # Component C exact seed anchors.
    c_decisions = [
        r for r in decision_rows
        if r["canary_selection_component"] == "C_SEED_CHECKPOINT"
    ]
    if Counter(r["external_optimizer_seed"] for r in c_decisions) != {"1": 2, "9": 2}:
        raise RuntimeError("Component C is not exactly two seed-1 and two seed-9 decisions.")

    # No scientific result/output columns should exist in the frozen F3A.2 plan.
    forbidden = {
        "bic", "bic_m0", "bic_m1", "bic_m2", "qpp_selected",
        "formal_m1_period_s", "estimated_period_s",
        "decision_status", "result_status",
    }
    if forbidden.intersection(plan[0].keys()):
        raise RuntimeError(
            f"Frozen plan unexpectedly contains outcome fields: "
            f"{sorted(forbidden.intersection(plan[0].keys()))}"
        )

    write_csv(
        repo / CANARY_DECISION_REL,
        decision_rows,
        decision_fieldnames,
    )
    write_csv(
        repo / CANARY_JOB_REL,
        job_rows,
        job_fieldnames,
    )

    decision_sha = sha256_file(repo / CANARY_DECISION_REL)
    job_sha = sha256_file(repo / CANARY_JOB_REL)

    # Useful deterministic anchors for later replay selection.
    anchors = {}
    for role in ROLES:
        seed0 = [
            r for r in primary_rows
            if r["canary_selection_component"] == "A_STRUCTURAL_COVERAGE"
            and r["observational_reference_role"] == role
            and r["window_variant_id"] == "W00"
            and r["processing_profile_id"] == "P00"
        ]
        if len(seed0) != 1:
            raise RuntimeError(f"Expected one W00/P00 seed-0 anchor for {role}")
        anchors[f"{role}:W00/P00:seed0"] = seed0[0]["planned_decision_id"]

    print("PHASE3A_F3A3_CANARY_PLAN_BUILD_PASS")
    print(f"f3a2_freeze_commit={F3A2_COMMIT}")
    print(f"f3a2_plan_jobs={len(plan)}")
    print(f"f3a2_decisions={len(decisions)}")
    print(f"canary_primary_decisions={primary_count}")
    print(f"canary_stability_decisions={stability_count}")
    print(f"canary_total_decisions={len(decision_rows)}")
    print(f"canary_model_jobs={len(job_rows)}")
    print(f"roles_covered={len(roles_covered)}")
    print(f"windows_covered={len(windows_covered)}")
    print(f"profiles_covered={len(profiles_covered)}")
    print(f"canary_min_n_samples={min(n_values)}")
    print(f"canary_max_n_samples={max(n_values)}")
    print(f"m0_jobs={model_counts['M0']}")
    print(f"m1_jobs={model_counts['M1']}")
    print(f"m2_jobs={model_counts['M2']}")
    print(f"canary_decision_manifest_sha256={decision_sha}")
    print(f"canary_job_manifest_sha256={job_sha}")
    for key in sorted(anchors):
        print(f"anchor[{key}]={anchors[key]}")
    print("afino_imported=false")
    print("afino_executed=false")
    print("scientific_results_observed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
