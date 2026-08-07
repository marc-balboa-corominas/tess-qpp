from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import csv
import hashlib
import json
import math
import re


ROOT = Path(__file__).resolve().parent
F013_ROOT = ROOT / "fase0_tarea13_review"

OUTPUT_NAMES = [
    "fase2_tarea01_observational_robustness_preregistration.json",
    "fase2_tarea01_frozen_observational_cohort.csv",
    "fase2_tarea01_window_perturbations.csv",
    "fase2_tarea01_processing_profiles.csv",
    "fase2_tarea01_planned_decision_grid.csv",
    "fase2_tarea01_preregistration_audit.json",
    "fase2_tarea01_preregistration_report.md",
]

REQUIRED_DIRECT_HASHES = {
    "fase0_tarea15_reproduced_baseline.json":
        "4c0bf97f875b9beb2bd2d619b26fa77b083fb946a05d3ee48c32896046690dc7",
    "fase1_tarea14_phase1_decision.json":
        "356504bce1df734bfd5cf01cf1e84211fc5a458f6bf81ddb5458ef0a9166ef1a",
    "fase1_tarea14_phase2_entry_requirements.csv":
        "a2472a525cca398494faf876af1f7894bb0b625067bd750f156095eedd5cc298",
    "fase1_tarea14_phase1_synthesis_audit.json":
        "0255843af4b5f935aa6ff75398e695d3b8f5bf8bf20b57d4ee463eb741be22a7",
}

EXPECTED_PHASE1_DECISION = (
    "PHASE1_COMPLETE_PROCEED_TO_OBSERVATIONAL_ROBUSTNESS_WITH_LIMITATIONS"
)

WINDOW_ROWS = [
    {
        "window_variant_id": "W00",
        "delta_start_cadences": 0,
        "delta_end_cadences": 0,
        "is_baseline": True,
        "perturbation_family": "baseline",
        "description": "baseline",
    },
    {
        "window_variant_id": "WSm2",
        "delta_start_cadences": -2,
        "delta_end_cadences": 0,
        "is_baseline": False,
        "perturbation_family": "start_only",
        "description": "inicio dos cadencias antes",
    },
    {
        "window_variant_id": "WSm1",
        "delta_start_cadences": -1,
        "delta_end_cadences": 0,
        "is_baseline": False,
        "perturbation_family": "start_only",
        "description": "inicio una cadencia antes",
    },
    {
        "window_variant_id": "WSp1",
        "delta_start_cadences": 1,
        "delta_end_cadences": 0,
        "is_baseline": False,
        "perturbation_family": "start_only",
        "description": "inicio una cadencia después",
    },
    {
        "window_variant_id": "WSp2",
        "delta_start_cadences": 2,
        "delta_end_cadences": 0,
        "is_baseline": False,
        "perturbation_family": "start_only",
        "description": "inicio dos cadencias después",
    },
    {
        "window_variant_id": "WEm2",
        "delta_start_cadences": 0,
        "delta_end_cadences": -2,
        "is_baseline": False,
        "perturbation_family": "end_only",
        "description": "final dos cadencias antes",
    },
    {
        "window_variant_id": "WEm1",
        "delta_start_cadences": 0,
        "delta_end_cadences": -1,
        "is_baseline": False,
        "perturbation_family": "end_only",
        "description": "final una cadencia antes",
    },
    {
        "window_variant_id": "WEp1",
        "delta_start_cadences": 0,
        "delta_end_cadences": 1,
        "is_baseline": False,
        "perturbation_family": "end_only",
        "description": "final una cadencia después",
    },
    {
        "window_variant_id": "WEp2",
        "delta_start_cadences": 0,
        "delta_end_cadences": 2,
        "is_baseline": False,
        "perturbation_family": "end_only",
        "description": "final dos cadencias después",
    },
    {
        "window_variant_id": "WX1",
        "delta_start_cadences": -1,
        "delta_end_cadences": 1,
        "is_baseline": False,
        "perturbation_family": "symmetric_extension",
        "description": "extensión simétrica de una cadencia",
    },
    {
        "window_variant_id": "WC1",
        "delta_start_cadences": 1,
        "delta_end_cadences": -1,
        "is_baseline": False,
        "perturbation_family": "symmetric_contraction",
        "description": "contracción simétrica de una cadencia",
    },
    {
        "window_variant_id": "WX2",
        "delta_start_cadences": -2,
        "delta_end_cadences": 2,
        "is_baseline": False,
        "perturbation_family": "symmetric_extension",
        "description": "extensión simétrica de dos cadencias",
    },
    {
        "window_variant_id": "WC2",
        "delta_start_cadences": 2,
        "delta_end_cadences": -2,
        "is_baseline": False,
        "perturbation_family": "symmetric_contraction",
        "description": "contracción simétrica de dos cadencias",
    },
]

PROFILE_ROWS = [
    {
        "processing_profile_id": "P00",
        "flux_product": "PDCSAP",
        "quality_policy": "finite_all",
        "detrending": "none",
    },
    {
        "processing_profile_id": "P01",
        "flux_product": "SAP",
        "quality_policy": "finite_all",
        "detrending": "none",
    },
    {
        "processing_profile_id": "P02",
        "flux_product": "PDCSAP",
        "quality_policy": "q0_native",
        "detrending": "none",
    },
    {
        "processing_profile_id": "P03",
        "flux_product": "SAP",
        "quality_policy": "q0_native",
        "detrending": "none",
    },
    {
        "processing_profile_id": "P04",
        "flux_product": "PDCSAP",
        "quality_policy": "finite_all",
        "detrending": "linear_residual_plus_one",
    },
    {
        "processing_profile_id": "P05",
        "flux_product": "SAP",
        "quality_policy": "finite_all",
        "detrending": "linear_residual_plus_one",
    },
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fields: list[str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({
                field: row.get(field, "")
                for field in fields
            })


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def find_unique(
    rows: list[dict[str, str]],
    **criteria: str,
) -> dict[str, str]:
    matches = [
        row for row in rows
        if all(row.get(key) == value for key, value in criteria.items())
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one row for {criteria}; found {len(matches)}."
        )
    return matches[0]


def parse_bool(value: str) -> bool:
    if value == "True":
        return True
    if value == "False":
        return False
    raise ValueError(f"Unexpected Boolean: {value!r}")


for name in OUTPUT_NAMES:
    if (ROOT / name).exists():
        raise FileExistsError(
            f"Refusing to overwrite existing artifact: {name}"
        )

# Direct normative preflight.
source_hashes: dict[str, str] = {}
for filename, expected in REQUIRED_DIRECT_HASHES.items():
    path = ROOT / filename
    if not path.is_file():
        raise FileNotFoundError(path)
    observed = sha256(path)
    if observed != expected:
        raise RuntimeError(
            f"Normative hash mismatch for {filename}: "
            f"{observed} != {expected}"
        )
    source_hashes[filename] = observed

baseline = json.loads(
    (ROOT / "fase0_tarea15_reproduced_baseline.json").read_text(
        encoding="utf-8"
    )
)
phase1_decision = json.loads(
    (ROOT / "fase1_tarea14_phase1_decision.json").read_text(
        encoding="utf-8"
    )
)
phase1_requirements = read_csv(
    ROOT / "fase1_tarea14_phase2_entry_requirements.csv"
)
phase1_synthesis_audit = json.loads(
    (ROOT / "fase1_tarea14_phase1_synthesis_audit.json").read_text(
        encoding="utf-8"
    )
)

if phase1_decision["decision"] != EXPECTED_PHASE1_DECISION:
    raise RuntimeError("F1.14 phase decision does not authorize F2 robustness.")
if phase1_decision["candidate_discovery_allowed"] is not False:
    raise RuntimeError("Candidate discovery is not blocked in F1.14.")
if baseline["status"] != "EMPIRICALLY_REPRODUCED_BASELINE":
    raise RuntimeError("Unexpected F0.15 baseline status.")
if baseline["validated_events"]["published_qpp_reproduced"] != 5:
    raise RuntimeError("F0.15 does not contain five reproduced detections.")
if baseline["validated_events"]["matched_not_selected_retained"] != 5:
    raise RuntimeError("F0.15 does not contain five retained controls.")
if len(phase1_requirements) != 10:
    raise RuntimeError("Unexpected F1.14 entry-requirement count.")
if any(
    row["blocking_for_candidate_discovery"] != "True"
    for row in phase1_requirements
):
    raise RuntimeError("A F1.14 entry requirement does not block discovery.")
if phase1_synthesis_audit["phase_decision"] != EXPECTED_PHASE1_DECISION:
    raise RuntimeError("F1.14 synthesis audit and decision disagree.")

# Verify observational artifacts through the references frozen in F0.15.
artifact_references = baseline["artifact_references"]
reference_keys = {
    "fase0_tarea10_index_window_results.csv":
        "F0.10_calibration_results",
    "fase0_tarea10_execution_audit.json":
        "F0.10_calibration_audit",
    "fase0_tarea11_validation_cohort.csv":
        "F0.11_cohort",
    "fase0_tarea12_product_manifest.csv":
        "F0.12_product_manifest",
    "fase0_tarea12_event_reconstruction.csv":
        "F0.12_event_reconstruction",
    "fase0_tarea13_validation_input_manifest.csv":
        "F0.13_input_manifest",
    "fase0_tarea14_validation_decisions.csv":
        "F0.14_decisions",
    "fase0_tarea14_primary_cohort_summary.csv":
        "F0.14_primary_summary",
}

source_paths = {
    "fase0_tarea10_index_window_results.csv":
        ROOT / "fase0_tarea10_index_window_results.csv",
    "fase0_tarea10_execution_audit.json":
        ROOT / "fase0_tarea10_execution_audit.json",
    "fase0_tarea11_validation_cohort.csv":
        ROOT / "fase0_tarea11_validation_cohort.csv",
    "fase0_tarea12_product_manifest.csv":
        ROOT / "fase0_tarea12_product_manifest.csv",
    "fase0_tarea12_event_reconstruction.csv":
        ROOT / "fase0_tarea12_event_reconstruction.csv",
    "fase0_tarea13_validation_input_manifest.csv":
        F013_ROOT / "fase0_tarea13_validation_input_manifest.csv",
    "fase0_tarea14_validation_decisions.csv":
        ROOT / "fase0_tarea14_validation_decisions.csv",
    "fase0_tarea14_primary_cohort_summary.csv":
        ROOT / "fase0_tarea14_primary_cohort_summary.csv",
}

for filename, reference_key in reference_keys.items():
    expected = artifact_references[reference_key]["sha256"]
    path = source_paths[filename]
    if not path.is_file():
        raise FileNotFoundError(path)
    observed = sha256(path)
    if observed != expected:
        raise RuntimeError(
            f"F0.15-referenced hash mismatch for {filename}."
        )
    source_hashes[filename] = observed

f010_audit = json.loads(
    (ROOT / "fase0_tarea10_execution_audit.json").read_text(
        encoding="utf-8"
    )
)
f009_manifest_path = ROOT / f010_audit["manifest"]["filename"]
if sha256(f009_manifest_path) != f010_audit["manifest"]["sha256"]:
    raise RuntimeError("F0.9 calibration manifest differs from F0.10 audit.")
source_hashes[f009_manifest_path.name] = sha256(f009_manifest_path)

f009_manifest = read_csv(f009_manifest_path)
f010_results = read_csv(
    ROOT / "fase0_tarea10_index_window_results.csv"
)
f011_cohort = read_csv(
    ROOT / "fase0_tarea11_validation_cohort.csv"
)
f012_products = read_csv(
    ROOT / "fase0_tarea12_product_manifest.csv"
)
f012_reconstruction = read_csv(
    ROOT / "fase0_tarea12_event_reconstruction.csv"
)
f013_manifest = read_csv(
    F013_ROOT / "fase0_tarea13_validation_input_manifest.csv"
)
f014_decisions = read_csv(
    ROOT / "fase0_tarea14_validation_decisions.csv"
)
f014_summary = read_csv(
    ROOT / "fase0_tarea14_primary_cohort_summary.csv"
)

cohort_rows: list[dict[str, Any]] = []

# Calibration pair: identifiers and boundaries are read from F0.9/F0.10,
# while the pair identity and statuses are read from the F0.15 structure.
calibration_status = baseline["validated_events"]["calibration_pair"]
for event_role, variant_id, observational_role in [
    (
        "published_qpp",
        "published_qpp_pdcsap_all",
        "PUBLISHED_QPP_REPRODUCED",
    ),
    (
        "not_selected_qpp",
        "notselected_pdcsap_all",
        "MATCHED_NOT_SELECTED",
    ),
]:
    manifest_row = find_unique(
        f009_manifest,
        event_role=event_role,
        flux_type="PDCSAP_FLUX",
        quality_policy="finite_all",
    )
    decision_rows = [
        row for row in f010_results
        if row["variant_id"] == variant_id
        and row["optimizer_seed"] == "0"
    ]
    if len(decision_rows) != 3:
        raise RuntimeError(
            f"Calibration variant {variant_id} lacks one model trio."
        )
    m1_row = find_unique(decision_rows, model_id="M1")
    status_node = (
        calibration_status["published"]
        if event_role == "published_qpp"
        else calibration_status["matched_not_selected"]
    )
    baseline_selected = parse_bool(m1_row["qpp_selected"])
    expected_selected = event_role == "published_qpp"
    if baseline_selected != expected_selected:
        raise RuntimeError("Calibration classification differs from F0.15.")

    cohort_rows.append({
        "event_id": variant_id,
        "pair_id": "calibration_pair",
        "observational_role": observational_role,
        "published_classification": (
            "PUBLISHED_QPP"
            if event_role == "published_qpp"
            else "NOT_SELECTED_AS_QPP"
        ),
        "baseline_classification": (
            "QPP_SELECTED" if baseline_selected else "NOT_SELECTED"
        ),
        "tic_id": manifest_row["tic_id"],
        "sector": manifest_row["sector"],
        "cadence_s": manifest_row["cadence_median_s"],
        "source_fits_filename": manifest_row["source_filename"],
        "source_fits_sha256": manifest_row["source_sha256"],
        "lightcurve_product_identifier":
            "mast:TESS/product/" + manifest_row["source_filename"],
        "baseline_start_time": manifest_row["catalog_start_tbjd"],
        "baseline_peak_time": manifest_row["catalog_peak_tbjd"],
        "baseline_end_time": manifest_row["catalog_end_tbjd"],
        "baseline_start_index": manifest_row["start_fits_row_index"],
        "baseline_peak_index": manifest_row["peak_fits_row_index"],
        "baseline_end_index": manifest_row["end_fits_row_index"],
        "baseline_n_samples": manifest_row["n_rows_used"],
        "baseline_flux_product": "PDCSAP",
        "baseline_quality_policy": "finite_all",
        "baseline_external_optimizer_seed": 0,
        "baseline_delta_bic_0_1": m1_row["delta_bic_0_1"],
        "baseline_delta_bic_2_1": m1_row["delta_bic_2_1"],
        "baseline_qpp_selected": bool_text(baseline_selected),
        "baseline_estimated_period_s": m1_row["estimated_period_s"],
        "baseline_reproduction_status": status_node["status"],
    })

# Four blind-validation pairs.
for cohort_row in f011_cohort:
    pair_id = cohort_row["pair_id"]
    event_role = cohort_row["event_role"]
    observational_role = (
        "PUBLISHED_QPP_REPRODUCED"
        if event_role == "published_qpp"
        else "MATCHED_NOT_SELECTED"
    )

    reconstruction_row = find_unique(
        f012_reconstruction,
        pair_id=pair_id,
        event_role=event_role,
    )
    product_row = find_unique(
        f012_products,
        filename=reconstruction_row["filename"],
    )
    manifest_row = find_unique(
        f013_manifest,
        pair_id=pair_id,
        event_role=event_role,
        flux_type="PDCSAP_FLUX",
        quality_policy="finite_all",
    )
    decision_row = find_unique(
        f014_decisions,
        variant_id=manifest_row["variant_id"],
        optimizer_seed="0",
    )
    summary_row = find_unique(
        f014_summary,
        variant_id=manifest_row["variant_id"],
    )

    if decision_row["decision_status"] != "VALID":
        raise RuntimeError(
            f"Frozen baseline decision is invalid for {manifest_row['variant_id']}."
        )
    baseline_selected = parse_bool(decision_row["qpp_selected"])
    expected_selected = event_role == "published_qpp"
    if baseline_selected != expected_selected:
        raise RuntimeError(
            f"F0.14 classification mismatch for {manifest_row['variant_id']}."
        )
    if reconstruction_row["reconstruction_status"] != "RECONSTRUCTABLE":
        raise RuntimeError("A frozen cohort event is not reconstructable.")
    if manifest_row["n_rows_used"] != reconstruction_row["n_samples"]:
        raise RuntimeError("F0.12 and F0.13 baseline sample counts disagree.")

    cohort_rows.append({
        "event_id": manifest_row["variant_id"],
        "pair_id": pair_id,
        "observational_role": observational_role,
        "published_classification": (
            "PUBLISHED_QPP"
            if event_role == "published_qpp"
            else "NOT_SELECTED_AS_QPP"
        ),
        "baseline_classification": (
            "QPP_SELECTED" if baseline_selected else "NOT_SELECTED"
        ),
        "tic_id": cohort_row["tic_id"],
        "sector": reconstruction_row["sector"],
        "cadence_s": manifest_row["median_cadence_s"],
        "source_fits_filename": reconstruction_row["filename"],
        "source_fits_sha256": reconstruction_row["file_sha256"],
        "lightcurve_product_identifier": product_row["mast_uri"],
        "baseline_start_time": cohort_row["start_tbjd"],
        "baseline_peak_time": cohort_row["peak_tbjd"],
        "baseline_end_time": cohort_row["end_tbjd"],
        "baseline_start_index": reconstruction_row["start_fits_index"],
        "baseline_peak_index": reconstruction_row["peak_fits_index"],
        "baseline_end_index": reconstruction_row["end_fits_index"],
        "baseline_n_samples": reconstruction_row["n_samples"],
        "baseline_flux_product": "PDCSAP",
        "baseline_quality_policy": "finite_all",
        "baseline_external_optimizer_seed": 0,
        "baseline_delta_bic_0_1": decision_row["delta_bic_0_1"],
        "baseline_delta_bic_2_1": decision_row["delta_bic_2_1"],
        "baseline_qpp_selected": bool_text(baseline_selected),
        "baseline_estimated_period_s": decision_row["estimated_period_s"],
        "baseline_reproduction_status": summary_row["primary_status"],
    })

# Normative order: calibration pair, then P1–P4; reproduced row before control.
pair_order = {
    "calibration_pair": 0,
    "P1": 1,
    "P2": 2,
    "P3": 3,
    "P4": 4,
}
role_order = {
    "PUBLISHED_QPP_REPRODUCED": 0,
    "MATCHED_NOT_SELECTED": 1,
}
cohort_rows.sort(
    key=lambda row: (
        pair_order[row["pair_id"]],
        role_order[row["observational_role"]],
    )
)

if len(cohort_rows) != 10:
    raise RuntimeError(f"Frozen cohort has {len(cohort_rows)} rows.")
if len({row["event_id"] for row in cohort_rows}) != 10:
    raise RuntimeError("Frozen cohort event IDs are not unique.")
if Counter(row["observational_role"] for row in cohort_rows) != {
    "PUBLISHED_QPP_REPRODUCED": 5,
    "MATCHED_NOT_SELECTED": 5,
}:
    raise RuntimeError("Frozen cohort role counts are incorrect.")
pair_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
for row in cohort_rows:
    pair_groups[row["pair_id"]].append(row)
if len(pair_groups) != 5:
    raise RuntimeError("Frozen cohort does not contain five pairs.")
for pair_id, rows in pair_groups.items():
    if Counter(row["observational_role"] for row in rows) != {
        "PUBLISHED_QPP_REPRODUCED": 1,
        "MATCHED_NOT_SELECTED": 1,
    }:
        raise RuntimeError(f"Pair {pair_id} is not balanced.")

cohort_fields = [
    "event_id",
    "pair_id",
    "observational_role",
    "published_classification",
    "baseline_classification",
    "tic_id",
    "sector",
    "cadence_s",
    "source_fits_filename",
    "source_fits_sha256",
    "lightcurve_product_identifier",
    "baseline_start_time",
    "baseline_peak_time",
    "baseline_end_time",
    "baseline_start_index",
    "baseline_peak_index",
    "baseline_end_index",
    "baseline_n_samples",
    "baseline_flux_product",
    "baseline_quality_policy",
    "baseline_external_optimizer_seed",
    "baseline_delta_bic_0_1",
    "baseline_delta_bic_2_1",
    "baseline_qpp_selected",
    "baseline_estimated_period_s",
    "baseline_reproduction_status",
]
write_csv(
    ROOT / "fase2_tarea01_frozen_observational_cohort.csv",
    cohort_rows,
    cohort_fields,
)

window_fields = [
    "window_variant_id",
    "delta_start_cadences",
    "delta_end_cadences",
    "is_baseline",
    "perturbation_family",
    "description",
]
write_csv(
    ROOT / "fase2_tarea01_window_perturbations.csv",
    WINDOW_ROWS,
    window_fields,
)

profile_output_rows = []
for profile in PROFILE_ROWS:
    profile_output_rows.append({
        **profile,
        "quality_definition": (
            "np.isfinite(time) & np.isfinite(flux)"
            if profile["quality_policy"] == "finite_all"
            else (
                "np.isfinite(time) & np.isfinite(flux) "
                "& (QUALITY == 0)"
            )
        ),
        "detrending_definition": (
            "none"
            if profile["detrending"] == "none"
            else (
                "x=time_seconds-mean(time_seconds); "
                "X=[1,x]; beta=lstsq(X,flux); trend=X@beta; "
                "scale=median(flux); transformed=1+(flux-trend)/scale"
            )
        ),
        "interpolation_allowed": False,
        "gap_filling_allowed": False,
    })

profile_fields = [
    "processing_profile_id",
    "flux_product",
    "quality_policy",
    "detrending",
    "quality_definition",
    "detrending_definition",
    "interpolation_allowed",
    "gap_filling_allowed",
]
write_csv(
    ROOT / "fase2_tarea01_processing_profiles.csv",
    profile_output_rows,
    profile_fields,
)

planned_rows: list[dict[str, Any]] = []
planned_order = 0

# Primary: 10 × 13 × 6 × seed 0.
for event in cohort_rows:
    for window in WINDOW_ROWS:
        for profile in PROFILE_ROWS:
            planned_order += 1
            planned_rows.append({
                "planned_decision_id": f"F2D{planned_order:06d}",
                "planned_order": planned_order,
                "decision_class": "primary",
                "event_id": event["event_id"],
                "pair_id": event["pair_id"],
                "observational_role": event["observational_role"],
                "window_variant_id": window["window_variant_id"],
                "processing_profile_id":
                    profile["processing_profile_id"],
                "external_optimizer_seed": 0,
                "execute_only_if_eligible": "true",
                "planned_models": "M0|M1|M2",
                "candidate_discovery_use": "false",
            })

# Stability: W00 only, all six profiles, external seeds 1..9.
for event in cohort_rows:
    for profile in PROFILE_ROWS:
        for seed in range(1, 10):
            planned_order += 1
            planned_rows.append({
                "planned_decision_id": f"F2D{planned_order:06d}",
                "planned_order": planned_order,
                "decision_class": "stability",
                "event_id": event["event_id"],
                "pair_id": event["pair_id"],
                "observational_role": event["observational_role"],
                "window_variant_id": "W00",
                "processing_profile_id":
                    profile["processing_profile_id"],
                "external_optimizer_seed": seed,
                "execute_only_if_eligible": "true",
                "planned_models": "M0|M1|M2",
                "candidate_discovery_use": "false",
            })

if len(planned_rows) != 1320:
    raise RuntimeError("Planned decision-grid count is not 1320.")
if Counter(row["decision_class"] for row in planned_rows) != {
    "primary": 780,
    "stability": 540,
}:
    raise RuntimeError("Planned primary/stability counts are incorrect.")
if len({row["planned_decision_id"] for row in planned_rows}) != 1320:
    raise RuntimeError("Duplicate planned decision IDs.")
scientific_keys = {
    (
        row["event_id"],
        row["window_variant_id"],
        row["processing_profile_id"],
        row["external_optimizer_seed"],
    )
    for row in planned_rows
}
if len(scientific_keys) != 1320:
    raise RuntimeError("Duplicate planned scientific decision keys.")

planned_fields = [
    "planned_decision_id",
    "planned_order",
    "decision_class",
    "event_id",
    "pair_id",
    "observational_role",
    "window_variant_id",
    "processing_profile_id",
    "external_optimizer_seed",
    "execute_only_if_eligible",
    "planned_models",
    "candidate_discovery_use",
]
write_csv(
    ROOT / "fase2_tarea01_planned_decision_grid.csv",
    planned_rows,
    planned_fields,
)

admissibility_statuses = [
    "ELIGIBLE_FOR_AFINO",
    "MISSING_PRODUCT",
    "WINDOW_OUT_OF_RANGE",
    "PEAK_OUTSIDE_WINDOW",
    "PEAK_REMOVED_BY_QUALITY",
    "TOO_FEW_CADENCES",
    "NONFINITE_INPUT",
    "IRREGULAR_SAMPLING",
    "DETREND_FAILURE",
]

preregistration = {
    "study_id": "afino_tess_frozen_cohort_robustness_v1",
    "study_version": "1.0.0",
    "preregistration_status": "FROZEN_BEFORE_VARIANT_MATERIALIZATION",
    "candidate_discovery_allowed": False,
    "normative_links": {
        filename: {
            "sha256": observed,
            "verified": True,
        }
        for filename, observed in REQUIRED_DIRECT_HASHES.items()
    },
    "phase1_gate": {
        "required_decision": EXPECTED_PHASE1_DECISION,
        "observed_decision": phase1_decision["decision"],
        "candidate_discovery_allowed": False,
        "permitted_next_phase": phase1_decision["permitted_next_phase"],
    },
    "cohort": {
        "cohort_csv":
            "fase2_tarea01_frozen_observational_cohort.csv",
        "cohort_ordering":
            "calibration_pair, P1, P2, P3, P4; "
            "PUBLISHED_QPP_REPRODUCED before MATCHED_NOT_SELECTED",
        "event_count": 10,
        "pair_count": 5,
        "published_qpp_reproduced_count": 5,
        "matched_not_selected_count": 5,
        "event_ids_source":
            "Existing baseline variant_id values from F0.10 and F0.13/F0.14",
        "cohort_expansion_allowed": False,
        "event_substitution_allowed": False,
        "exclusion_after_variant_inspection_allowed": False,
        "labels": [
            "PUBLISHED_QPP_REPRODUCED",
            "MATCHED_NOT_SELECTED",
        ],
        "forbidden_labels": [
            "true_positive",
            "true_negative",
            "ground_truth",
        ],
    },
    "window_perturbations": {
        "csv": "fase2_tarea01_window_perturbations.csv",
        "count": 13,
        "index_convention": "inclusive FITS row indices",
        "delta_start_interpretation": {
            "negative": "earlier start",
            "positive": "later start",
        },
        "delta_end_interpretation": {
            "negative": "earlier end",
            "positive": "later end",
        },
        "frozen_peak_must_remain_inside_window": True,
        "automatic_boundary_compensation_allowed": False,
        "rows": WINDOW_ROWS,
    },
    "processing_profiles": {
        "csv": "fase2_tarea01_processing_profiles.csv",
        "count": 6,
        "rows": PROFILE_ROWS,
        "finite_all_definition":
            "np.isfinite(time) & np.isfinite(flux)",
        "q0_native_definition":
            "np.isfinite(time) & np.isfinite(flux) & (QUALITY == 0)",
        "q0_native_interpolation": False,
        "linear_residual_plus_one": {
            "x": "time_seconds - np.mean(time_seconds)",
            "X": "np.column_stack([np.ones(len(x)), x])",
            "beta": "np.linalg.lstsq(X, flux, rcond=None)[0]",
            "trend": "X @ beta",
            "scale": "np.median(flux)",
            "flux_transformed":
                "1.0 + (flux - trend) / scale",
            "requirements": [
                "scale finite",
                "scale != 0",
                "trend finite",
                "flux_transformed finite",
            ],
            "interpretation":
                "preprocessing sensitivity test, not a physical flare model",
        },
        "profiles_forbidden_after_freeze": [
            "q0 plus detrending",
            "interpolation",
            "gap filling",
            "Savitzky-Golay filters",
            "additional profile combinations",
        ],
    },
    "admissibility": {
        "statuses": admissibility_statuses,
        "status_precedence": [
            "MISSING_PRODUCT",
            "WINDOW_OUT_OF_RANGE",
            "PEAK_OUTSIDE_WINDOW",
            "PEAK_REMOVED_BY_QUALITY",
            "TOO_FEW_CADENCES",
            "NONFINITE_INPUT",
            "IRREGULAR_SAMPLING",
            "DETREND_FAILURE",
            "ELIGIBLE_FOR_AFINO",
        ],
        "eligible_requirements": [
            "requested product exists",
            "shifted inclusive indices are within the frozen FITS product",
            "frozen peak index belongs to the shifted raw window",
            "after quality filtering at least 15 cadences remain",
            "frozen peak row remains after quality filtering",
            "retained time is strictly increasing",
            "retained original FITS indices are consecutive",
            "retained time has no duplicates",
            "maximum interval deviation from median cadence <= 1e-3 s",
            "retained time and flux are finite",
            "detrending is valid when requested",
        ],
        "minimum_cadences": 15,
        "maximum_interval_deviation_from_median_s": 0.001,
        "interpolation_allowed": False,
        "gap_filling_allowed": False,
        "reindexing_to_hide_gaps_allowed": False,
        "inadmissible_as_not_selected_allowed": False,
        "silent_denominator_exclusion_allowed": False,
        "eligibility_resolution_task": "F2.2",
    },
    "planned_decision_grid": {
        "csv": "fase2_tarea01_planned_decision_grid.csv",
        "primary": {
            "event_count": 10,
            "window_count": 13,
            "profile_count": 6,
            "external_optimizer_seeds": [0],
            "planned_decisions": 780,
            "planned_model_calls": 2340,
        },
        "stability": {
            "event_count": 10,
            "window_variant_ids": ["W00"],
            "profile_count": 6,
            "external_optimizer_seeds": list(range(1, 10)),
            "planned_decisions": 540,
            "planned_model_calls": 1620,
        },
        "planned_decisions_maximum": 1320,
        "planned_model_calls_maximum": 3960,
        "inadmissible_rows_retained_in_grid": True,
        "calls_only_for_eligible_variants": True,
        "planned_models": ["M0", "M1", "M2"],
        "candidate_discovery_use": False,
        "exact_eligible_count_frozen_in_task": "F2.2",
    },
    "future_afino_protocol": {
        "models": {
            "M0": "pow_const",
            "M1": "pow_const_gauss",
            "M2": "bpow_const",
        },
        "low_frequency_cutoff_hz": 0.025,
        "low_frequency_cutoff_expression": "1.0 / 40.0",
        "m1_bounds": [
            [-10.0, 10.0],
            [-1.0, 6.0],
            [-20.0, 10.0],
            [-16.0, 5.0],
            ["np.log(1.0 / 300.0)", "np.log(1.0 / 40.0)"],
            [0.05, 0.25],
        ],
        "seed_reset":
            "np.random.seed(external_optimizer_seed) before each model",
        "selection_rule":
            "(BIC_M0 - BIC_M1 > 10.0) and "
            "(BIC_M2 - BIC_M1 > 10.0)",
        "threshold": 10.0,
        "post_result_protocol_changes_allowed": False,
    },
    "outcomes": {
        "eligible_variant_fields": [
            "decision_status",
            "qpp_selected",
            "delta_bic_0_1",
            "delta_bic_2_1",
            "joint_margin",
            "bic_winner",
            "classification_retained_vs_frozen_baseline",
            "estimated_period_s",
            "period_label",
            "warning_count_by_model",
            "bound_hit_by_model",
        ],
        "inadmissible_variant_contract": {
            "decision_status": "INPUT_INADMISSIBLE",
            "admissibility_reason": "required",
            "qpp_selected": None,
            "BIC": None,
        },
        "event_classification_robustness_fields": [
            "eligible_primary_variants",
            "baseline_classification_retained_count",
            "selection_loss_count",
            "selection_gain_count",
            "inadmissible_variant_count",
            "retention_fraction_among_eligible",
        ],
        "robustness_threshold": None,
        "period_shift_vs_baseline_s_rule":
            "compute only when frozen baseline and variant are both "
            "selected and both periods are available",
        "new_control_selection_period_label":
            "formal M1 center; not recovery of a true period",
        "pair_analysis":
            "same variant identifiers applied to both pair members; "
            "describe concordant or discordant changes only",
        "sensitivity_or_specificity_test": False,
    },
    "denominators": {
        "planned_primary_maximum": 780,
        "planned_stability_maximum": 540,
        "planned_total_maximum": 1320,
        "eligible_primary_denominator":
            "number of ELIGIBLE_FOR_AFINO primary variants per event",
        "inadmissible_variants":
            "reported separately and never counted as non-selection",
        "stability_denominator":
            "eligible W00 event-profile combinations × seeds 1..9",
        "pair_denominator":
            "pairs where both members have the same eligible variant; "
            "reported descriptively",
    },
    "prohibited_interpretations": {
        "observational_ground_truth_established": False,
        "sensitivity_estimated": False,
        "specificity_estimated": False,
        "observational_false_positive_rate_estimated": False,
        "afino_validated": False,
        "physical_qpp_truth_inferred": False,
        "candidate_discovery_allowed": False,
    },
    "prohibited_operations": [
        "post hoc significance tests",
        "selection of favorable variants",
        "averaging inadmissibility with non-selection",
        "cohort changes",
        "new robustness thresholds",
        "interpreting MATCHED_NOT_SELECTED as physical absence of QPP",
        "new event downloads",
        "candidate search",
    ],
    "next_task":
        "F2.2 — materialize 780 primary variants, resolve admissibility "
        "and freeze the exact execution plan before AFINO",
}

prereg_path = (
    ROOT / "fase2_tarea01_observational_robustness_preregistration.json"
)
prereg_path.write_text(
    json.dumps(
        preregistration,
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)

report = """# Fase 2 — Tarea 2.1

## Prerregistro de robustez observacional sobre la cohorte congelada

**Estado:** `OBSERVATIONAL_ROBUSTNESS_PREREGISTRATION_FROZEN`

La cohorte queda limitada a las diez observaciones cuya clasificación fue
congelada en F0.15: cinco eventos `PUBLISHED_QPP_REPRODUCED` y cinco
`MATCHED_NOT_SELECTED`. Existen cinco pares, cada uno formado por una
detección publicada reproducida y un evento emparejado no seleccionado. Los
identificadores, TIC, sectores, productos FITS, hashes, marcadores temporales,
índices inclusivos y resultados baseline se extrajeron de los artefactos
observacionales enlazados por F0.15. No se creó ningún evento, no se sustituyó
ningún caso problemático y no se inspeccionó todavía la elegibilidad de una
variante.

Las perturbaciones temporales se aplicarán simétricamente a los dos miembros
de cada par. Las trece ventanas incluyen el baseline, desplazamientos del
inicio o del final en una o dos cadencias, y extensiones o contracciones
simétricas. Todos los desplazamientos operan sobre los índices FITS inclusivos
congelados. El pico mantiene su índice original y debe permanecer dentro de la
ventana; un desplazamiento que lo excluya será inadmisible y no se corregirá
moviendo el otro límite. Esta simetría evita escoger ventanas distintas según
la clasificación previa del evento.

Los seis perfiles distinguen tres dimensiones. Se compararán PDCSAP y SAP;
`finite_all` y `q0_native`; y, para ambos productos bajo `finite_all`, una
transformación lineal `linear_residual_plus_one`. `finite_all` conserva tiempo
y flujo finitos sin filtrar por `QUALITY`. `q0_native` exige además
`QUALITY==0` y no interpola. La alternativa lineal sustrae una recta estimada
sobre las mismas cadencias y reescala el residuo alrededor de uno. Es una
prueba de sensibilidad al preprocesamiento, no un modelo físico del flare. No
se añadirán combinaciones q0 con detrending, filtros adicionales ni perfiles
elegidos después de observar resultados.

F2.2 resolverá la admisibilidad sin ejecutar AFINO. Una variante solo será
elegible si existe el producto, la ventana está dentro del FITS, conserva el
pico, mantiene al menos quince cadencias después de la política de calidad,
retiene el pico, tiene tiempos estrictamente crecientes, índices originales
consecutivos, ausencia de duplicados, desviación máxima de intervalos no
superior a 0,001 s y datos finitos. El detrending deberá producir escala,
tendencia y flujo transformado válidos. No se interpolarán gaps, no se
rellenarán cadencias y no se reindexará para ocultar irregularidad.

La inadmisibilidad no equivale a no selección. Las combinaciones inadmisibles
permanecerán en el grid con `decision_status=INPUT_INADMISSIBLE`, una razón
explícita y campos BIC y selección vacíos. Por tanto, el denominador de
retención de cada evento será únicamente el número de variantes primarias
elegibles. Las variantes inadmisibles se contarán por separado y no se
mezclarán con pérdidas de clasificación. No se fija un porcentaje mínimo de
robustez.

La clasificación y el periodo se analizarán como outcomes distintos. Para una
variante elegible se registrarán los dos deltas BIC, el margen conjunto, el
ganador BIC, la conservación de la clasificación baseline, warnings y bounds.
El desplazamiento de periodo frente al baseline solo se calculará cuando el
baseline y la variante estén seleccionados y ambos periodos existan. Una nueva
selección en un control podrá registrar el centro formal de M1, pero no se
denominará recuperación de un periodo verdadero.

El grid máximo contiene 780 decisiones primarias: diez eventos por trece
ventanas por seis perfiles con seed externa cero. La estabilidad añade 540
decisiones en W00: diez eventos por seis perfiles y seeds uno a nueve. El
máximo es de 1.320 decisiones y 3.960 llamadas de modelo. F2.2 congelará el
número exacto elegible antes de cualquier ejecución.

Esta fase no estimará sensibilidad, especificidad, tasa observacional de falsos
positivos ni ground truth físico. Los pares describirán cambios concordantes o
discordantes, no rendimiento poblacional. La búsqueda de candidatos permanece
bloqueada porque la autorización de F1.14 se limita a probar la robustez de las
diez clasificaciones conocidas. No se descargaron nuevos eventos, no se
materializaron curvas y no se ejecutó AFINO.

`OBSERVATIONAL_ROBUSTNESS_PREREGISTRATION_FROZEN`
"""

report_word_count = len(
    re.findall(r"\b[\wÁÉÍÓÚÜÑáéíóúüñ]+\b", report)
)
if not (500 <= report_word_count <= 800):
    raise RuntimeError(
        f"Preregistration report has {report_word_count} words."
    )

report_path = ROOT / "fase2_tarea01_preregistration_report.md"
report_path.write_text(report, encoding="utf-8")

# Verify normative sources remain unchanged after generation.
source_hashes_after = {}
for filename, expected in REQUIRED_DIRECT_HASHES.items():
    observed = sha256(ROOT / filename)
    if observed != expected:
        raise RuntimeError(f"Normative source changed: {filename}")
    source_hashes_after[filename] = observed
for filename, path in source_paths.items():
    observed = sha256(path)
    if observed != source_hashes[filename]:
        raise RuntimeError(f"Observational source changed: {filename}")
    source_hashes_after[filename] = observed
source_hashes_after[f009_manifest_path.name] = sha256(f009_manifest_path)
if source_hashes_after[f009_manifest_path.name] != (
    source_hashes[f009_manifest_path.name]
):
    raise RuntimeError("Calibration manifest changed during F2.1.")

output_hashes_excluding_audit = {
    name: sha256(ROOT / name)
    for name in OUTPUT_NAMES
    if name != "fase2_tarea01_preregistration_audit.json"
}

audit = {
    "preregistration_status":
        "OBSERVATIONAL_ROBUSTNESS_PREREGISTRATION_FROZEN",
    "study_id": "afino_tess_frozen_cohort_robustness_v1",
    "study_version": "1.0.0",
    "source_hashes_verified": {
        "before": source_hashes,
        "after": source_hashes_after,
        "all_match": source_hashes_after == source_hashes,
    },
    "script": {
        "filename": Path(__file__).name,
        "sha256": sha256(Path(__file__)),
    },
    "cohort_rows": 10,
    "published_qpp_rows": 5,
    "matched_not_selected_rows": 5,
    "pair_count": 5,
    "window_perturbation_rows": 13,
    "processing_profile_rows": 6,
    "primary_decision_rows": 780,
    "stability_decision_rows": 540,
    "total_planned_decision_rows": 1320,
    "maximum_planned_model_calls": 3960,
    "duplicate_event_ids": 0,
    "duplicate_planned_decision_ids": 0,
    "new_events_added": 0,
    "report_word_count": report_word_count,
    "output_hashes_excluding_audit": output_hashes_excluding_audit,
    "incidents": [],
    "confirmations": {
        "afino_executed": False,
        "fits_downloaded": False,
        "curves_materialized": False,
        "variant_eligibility_inspected": False,
        "scientific_results_observed": False,
        "candidate_discovery_authorized": False,
        "new_selection_threshold_added": False,
        "cohort_modified": False,
        "baseline_modified": False,
    },
}

audit_path = ROOT / "fase2_tarea01_preregistration_audit.json"
audit_path.write_text(
    json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

# Objective closure checks.
if len(read_csv(ROOT / "fase2_tarea01_frozen_observational_cohort.csv")) != 10:
    raise RuntimeError("Cohort CSV row count changed.")
if len(read_csv(ROOT / "fase2_tarea01_window_perturbations.csv")) != 13:
    raise RuntimeError("Window CSV row count changed.")
if len(read_csv(ROOT / "fase2_tarea01_processing_profiles.csv")) != 6:
    raise RuntimeError("Profile CSV row count changed.")
if len(read_csv(ROOT / "fase2_tarea01_planned_decision_grid.csv")) != 1320:
    raise RuntimeError("Decision-grid CSV row count changed.")
if preregistration["candidate_discovery_allowed"] is not False:
    raise RuntimeError("Candidate discovery was authorized.")
if preregistration["preregistration_status"] != (
    "FROZEN_BEFORE_VARIANT_MATERIALIZATION"
):
    raise RuntimeError("Incorrect preregistration freeze status.")

print("F2.1 observational robustness preregistration complete")
print("status: OBSERVATIONAL_ROBUSTNESS_PREREGISTRATION_FROZEN")
print(f"cohort_rows: {len(cohort_rows)}")
print("published_qpp_rows: 5")
print("matched_not_selected_rows: 5")
print("pair_count: 5")
print("window_perturbation_rows: 13")
print("processing_profile_rows: 6")
print("primary_decision_rows: 780")
print("stability_decision_rows: 540")
print("total_planned_decision_rows: 1320")
print("maximum_planned_model_calls: 3960")
print(f"report_word_count: {report_word_count}")
for name in OUTPUT_NAMES:
    print(f"{name}: {sha256(ROOT / name)}")
