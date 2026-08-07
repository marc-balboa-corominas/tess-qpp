#!/usr/bin/env python3
"""F2.6 — Phase 2 synthesis and manuscript-route decision.

Documentary-only synthesis. This script:
- verifies frozen packages, manifests and normative source hashes;
- does not import or execute AFINO;
- does not import Astropy or open FITS;
- does not regenerate variants or compute new scientific statistics;
- writes only documentary ledgers, requirements, decisions and a report.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


PHASE2_DECISION = (
    "PHASE2_COMPLETE_ROBUSTNESS_MANUSCRIPT_VIABLE_"
    "CORRECTION_REQUIRES_PHASE3"
)

PACKAGE_EXPECTATIONS = {
    "fase1_tarea14_entregables_mentor.zip": {
        "sha256":
            "60056d0e114c6bb5231225e23150c77c3e8fcf7368facd8a5ccee49ae990e757",
        "manifest_field": "status",
        "manifest_value":
            "PHASE1_COMPLETE_PROCEED_TO_OBSERVATIONAL_ROBUSTNESS_WITH_LIMITATIONS",
    },
    "fase2_tarea01_entregables_mentor.zip": {
        "sha256":
            "6596c78f7cef1045b4205ed0611372e38c161b500b8b43fb15ab14fb7c9424c6",
        "manifest_field": "status",
        "manifest_value":
            "OBSERVATIONAL_ROBUSTNESS_PREREGISTRATION_FROZEN",
    },
    "fase2_tarea02_entregables_mentor.zip": {
        "sha256":
            "b667477a3c060f1713ca333cd82b30138dcff40a7ee694bdadc413bf55b511cf",
        "manifest_field": "status",
        "manifest_value":
            "OBSERVATIONAL_VARIANTS_AND_EXACT_PLAN_FROZEN_BEFORE_AFINO",
    },
    "fase2_tarea03_entregables_mentor.zip": {
        "sha256":
            "9394f6adf17e23ccb10139e11e51f1374042878c7e80ec72be46716f0d568a77",
        "manifest_field": "validation_conclusion",
        "manifest_value":
            "OBSERVATIONAL_RUNNER_VALIDATED_WITH_DOCUMENTED_LIMITATION",
    },
    "fase2_tarea04_entregables_mentor.zip": {
        "sha256":
            "15fc8cc4b6d9d33504403fed42af23a9afb83e869b648baeac5f1c0dff24fdb5",
        "manifest_field": "execution_status",
        "manifest_value":
            "FULL_OBSERVATIONAL_PLAN_EXECUTION_COMPLETE",
    },
    "fase2_tarea05_entregables_mentor.zip": {
        "sha256":
            "a63159ecbbad4fbfe39f3489f444ff0663be472f4841bcb86086b36ef5fad06b",
        "manifest_field": "analysis_conclusion",
        "manifest_value":
            "FROZEN_COHORT_ROBUSTNESS_CHARACTERIZED_WITH_LIMITATIONS",
    },
}

DIRECT_HASHES = {
    "fase1_tarea14_phase1_decision.json":
        "356504bce1df734bfd5cf01cf1e84211fc5a458f6bf81ddb5458ef0a9166ef1a",
    "fase1_tarea14_phase1_evidence_ledger.csv":
        "ab471a68016c19abb6672be7ab29f1f890d9b9c67dfdf750edfb224afbae975a",
    "fase1_tarea14_phase1_synthesis_report.md":
        "5d748476630023ec6b0f4a11c0851711f34b5b5c7a20a2e30fce1b1138a6c466",
    "fase2_tarea01_observational_robustness_preregistration.json":
        "ed37166ad6917b54711c3ce7ac9f3aeffdaaba9477672a9b1e5d506c07f427d7",
    "fase2_tarea01_preregistration_audit.json":
        "1111b5e060abc4f619f6c7ac01306d423bbc73ae520d8c15e7c31317afdfcf55",
    "fase2_tarea01_frozen_observational_cohort.csv":
        "34f4a5ce53e7fb16ee16c976d5b06af524d6cacda4a4bc303a5d580193745cc1",
    "fase2_tarea01_window_perturbations.csv":
        "4e0a602e89f17594afe4624ae0d48781cfde7c17a17a1cc129002aeb0c45f130",
    "fase2_tarea01_processing_profiles.csv":
        "232af6bdc6fa09851cd1039c5b159849f2f675803ea6ff1f53f51e7a4a7629e0",
    "fase2_tarea02_observational_variant_manifest.csv":
        "e89f33d433a48217feb44c07efae33b984377a205c218253553a604df71c5093",
    "fase2_tarea02_resolved_decision_grid.csv":
        "2150657765dff06fb69272c4c11b7bcea656dce2d3fd8faa15b35821dec944dd",
    "fase2_tarea02_variant_materialization_audit.json":
        "2264522b38cb6ea336518369200b3bce1370876bbe3b63273825cbaba3f7991b",
    "fase2_tarea03_observational_runner_validation_audit_v2.json":
        "56fc2eb4eec927b6032a991c2c96dc1867da394ef08129f7a774d58f5c417d7c",
    "fase2_tarea04_observational_full_results.csv":
        "791e071df6e05749937070a31ed4c344b95e10f09abd83a392093ccf2c85a9f8",
    "fase2_tarea04_observational_full_decisions.csv":
        "f4c6940f8c67c5a5bdfbabaf6f540fc07538f2a09acddd56edebf3a894f225f0",
    "fase2_tarea04_full_execution_audit.json":
        "9c406be909cbdccbf7dff196c309568d228973ed5dbb3fae4e06573e8ada5b07",
    "fase2_tarea05_observational_robustness_audit.json":
        "be80d4bcb56199624787bc49ad15a59648cc541d44907c975229967ef74ca3d1",
    "fase2_tarea05_observational_robustness_report.md":
        "0b9b2451be1fbe46418ad810591d6c54c8ddf6a2cb93e2b67dfd65196dc530aa",
    "fase2_tarea05_primary_robustness_enriched.csv":
        "31877d98de4012d1a8927afdc94c7de18f7176700f04841345a977c261e5eddb",
}

OUTPUT_NAMES = [
    "fase2_tarea06_phase2_evidence_ledger.csv",
    "fase2_tarea06_phase2_limitations_register.csv",
    "fase2_tarea06_manuscript_claim_matrix.csv",
    "fase2_tarea06_phase3_entry_requirements.csv",
    "fase2_tarea06_phase2_decision.json",
    "fase2_tarea06_phase2_synthesis_audit.json",
    "fase2_tarea06_phase2_synthesis_report.md",
]

MANDATORY_EVIDENCE_PLANES = {
    "OBSERVATIONAL_BASELINE_REPRODUCTION",
    "INPUT_ADMISSIBILITY",
    "CLASSIFICATION_ROBUSTNESS",
    "OPTIMIZER_NUMERICAL_STABILITY",
    "PERIOD_ROBUSTNESS",
    "OPERATIONAL_DIAGNOSTICS",
    "INTERPRETATION_LIMITS",
}

CLAIM_STATUSES = {
    "SUPPORTED_NOW",
    "SUPPORTED_WITH_EXPLICIT_LIMITATION",
    "NOT_SUPPORTED",
    "REQUIRES_PHASE3",
    "PROHIBITED",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def member_sha256(archive: zipfile.ZipFile, member: str) -> str:
    return hashlib.sha256(archive.read(member)).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Iterable[dict[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(fieldnames),
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def manifest_file_records(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("files", "official_files", "official_deliverables"):
        records = manifest.get(key)
        if isinstance(records, list):
            return records
    return []


def verify_packages(root: Path) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    verified = []
    manifests = {}
    for filename, expectation in PACKAGE_EXPECTATIONS.items():
        path = root / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        observed_zip_hash = sha256(path)
        if observed_zip_hash != expectation["sha256"]:
            raise RuntimeError(
                f"Package hash mismatch for {filename}: "
                f"{observed_zip_hash} != {expectation['sha256']}"
            )
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                raise RuntimeError(
                    f"Corrupt member in {filename}: {bad_member}"
                )
            manifest = json.loads(
                archive.read("PACKAGE_MANIFEST.json")
            )
            field = expectation["manifest_field"]
            if manifest.get(field) != expectation["manifest_value"]:
                raise RuntimeError(
                    f"{filename} manifest {field} mismatch."
                )

            checked_members = 0
            member_mismatches = []
            for record in manifest_file_records(manifest):
                member = record.get("filename")
                expected_hash = record.get("sha256")
                if (
                    not isinstance(member, str)
                    or not isinstance(expected_hash, str)
                    or member not in archive.namelist()
                ):
                    continue
                checked_members += 1
                observed_member_hash = member_sha256(archive, member)
                if observed_member_hash != expected_hash:
                    member_mismatches.append({
                        "member": member,
                        "expected": expected_hash,
                        "observed": observed_member_hash,
                    })
            if member_mismatches:
                raise RuntimeError(
                    f"Package member hash mismatch: {member_mismatches}"
                )

        manifests[filename] = manifest
        verified.append({
            "package": filename,
            "package_sha256": observed_zip_hash,
            "task": manifest.get("task", ""),
            "review_status": manifest.get("review_status", ""),
            "status_field": field,
            "status_value": manifest.get(field),
            "manifest_members_verified": checked_members,
        })
    return verified, manifests


def verify_direct_sources(root: Path) -> dict[str, str]:
    observed = {}
    for filename, expected in DIRECT_HASHES.items():
        path = root / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        observed[filename] = actual
        if actual != expected:
            raise RuntimeError(
                f"Direct source hash mismatch for {filename}: "
                f"{actual} != {expected}"
            )
    return observed


def make_claim(
    claim_id: str,
    evidence_plane: str,
    claim_text: str,
    source_phase: str,
    source_artifact: str,
    source_locator: str,
    source_sha256: str,
    evidence_class: str,
    scope: str,
    allowed_interpretation: str,
    prohibited_interpretation: str,
) -> dict[str, str]:
    return {
        "claim_id": claim_id,
        "evidence_plane": evidence_plane,
        "claim_text": claim_text,
        "source_phase": source_phase,
        "source_artifact": source_artifact,
        "source_locator": source_locator,
        "source_sha256": source_sha256,
        "evidence_class": evidence_class,
        "scope": scope,
        "allowed_interpretation": allowed_interpretation,
        "prohibited_interpretation": prohibited_interpretation,
    }


def build_outputs(root: Path, output_dir: Path) -> None:
    output_dir = output_dir.resolve()
    for name in OUTPUT_NAMES:
        if (output_dir / name).exists():
            raise FileExistsError(
                f"Refusing to overwrite final output: {name}"
            )

    source_packages_verified, package_manifests = verify_packages(root)
    direct_hashes = verify_direct_sources(root)

    # ------------------------------------------------------------------
    # Verify normative phase states and source facts
    # ------------------------------------------------------------------

    f114_decision = json.loads(
        (root / "fase1_tarea14_phase1_decision.json").read_text(
            encoding="utf-8"
        )
    )
    f21_prereg = json.loads(
        (
            root
            / "fase2_tarea01_observational_robustness_preregistration.json"
        ).read_text(encoding="utf-8")
    )
    f21_audit = json.loads(
        (root / "fase2_tarea01_preregistration_audit.json").read_text(
            encoding="utf-8"
        )
    )
    f22_audit = json.loads(
        (
            root / "fase2_tarea02_variant_materialization_audit.json"
        ).read_text(encoding="utf-8")
    )
    f23_audit = json.loads(
        (
            root
            / "fase2_tarea03_observational_runner_validation_audit_v2.json"
        ).read_text(encoding="utf-8")
    )
    f24_audit = json.loads(
        (root / "fase2_tarea04_full_execution_audit.json").read_text(
            encoding="utf-8"
        )
    )
    f25_audit = json.loads(
        (
            root
            / "fase2_tarea05_observational_robustness_audit.json"
        ).read_text(encoding="utf-8")
    )

    expected_states = {
        "F1.14": (
            f114_decision.get("decision"),
            "PHASE1_COMPLETE_PROCEED_TO_OBSERVATIONAL_ROBUSTNESS_WITH_LIMITATIONS",
        ),
        "F2.1": (
            f21_audit.get("preregistration_status"),
            "OBSERVATIONAL_ROBUSTNESS_PREREGISTRATION_FROZEN",
        ),
        "F2.2": (
            f22_audit.get("materialization_status"),
            "OBSERVATIONAL_VARIANTS_AND_EXACT_PLAN_FROZEN_BEFORE_AFINO",
        ),
        "F2.3": (
            f23_audit.get("validation_conclusion"),
            "OBSERVATIONAL_RUNNER_VALIDATED_WITH_DOCUMENTED_LIMITATION",
        ),
        "F2.4": (
            f24_audit.get("execution_status"),
            "FULL_OBSERVATIONAL_PLAN_EXECUTION_COMPLETE",
        ),
        "F2.5": (
            f25_audit.get("analysis_conclusion"),
            "FROZEN_COHORT_ROBUSTNESS_CHARACTERIZED_WITH_LIMITATIONS",
        ),
    }
    for phase, (observed, expected) in expected_states.items():
        if observed != expected:
            raise RuntimeError(
                f"{phase} state mismatch: {observed} != {expected}"
            )

    required_facts = [
        (f21_audit["cohort_rows"], 10, "F2.1 cohort_rows"),
        (f21_audit["pair_count"], 5, "F2.1 pair_count"),
        (f21_audit["window_perturbation_rows"], 13, "F2.1 windows"),
        (f21_audit["processing_profile_rows"], 6, "F2.1 profiles"),
        (f21_audit["primary_decision_rows"], 780, "F2.1 primary rows"),
        (f22_audit["primary_variant_rows"], 780, "F2.2 variants"),
        (f22_audit["eligible_primary_variants"], 514, "F2.2 eligible"),
        (f22_audit["inadmissible_primary_variants"], 266, "F2.2 inadmissible"),
        (f22_audit["baseline_w00_p00_exact_matches"], 10, "F2.2 baseline"),
        (f23_audit["canary_result_rows"], 84, "F2.3 canary results"),
        (f23_audit["exact_replay_passed"], 6, "F2.3 replays"),
        (f24_audit["planned_jobs"], 2784, "F2.4 jobs"),
        (f24_audit["decision_rows"], 928, "F2.4 decisions"),
        (f25_audit["primary_planned_variants"], 780, "F2.5 planned"),
        (f25_audit["primary_eligible_variants"], 514, "F2.5 eligible"),
        (f25_audit["primary_inadmissible_variants"], 266, "F2.5 inadmissible"),
        (f25_audit["stability_variants"], 46, "F2.5 stability variants"),
        (
            f25_audit["stability_decisions_seed_0_to_9"],
            460,
            "F2.5 stability decisions",
        ),
        (
            f25_audit["baseline_classification_mismatches"],
            0,
            "F2.5 baseline classification mismatches",
        ),
    ]
    for observed, expected, label in required_facts:
        if observed != expected:
            raise RuntimeError(
                f"{label}: {observed} != {expected}"
            )

    if f24_audit.get("result_status_counts") != {"OK": 2784}:
        raise RuntimeError("F2.4 result status count changed.")
    if f24_audit.get("decision_status_counts") != {"VALID": 928}:
        raise RuntimeError("F2.4 decision status count changed.")

    h = direct_hashes

    # ------------------------------------------------------------------
    # Evidence ledger
    # ------------------------------------------------------------------

    claims = [
        make_claim(
            "E001",
            "INTERPRETATION_LIMITS",
            "La Fase 1 autorizó robustez observacional limitada sobre diez observaciones congeladas y mantuvo bloqueado el descubrimiento.",
            "F1.14",
            "fase1_tarea14_phase1_decision.json",
            "decision; permitted_next_phase; candidate_discovery_allowed",
            h["fase1_tarea14_phase1_decision.json"],
            "PHASE_GATE",
            "Paso de benchmark sintético y baseline efectivo a robustez de la cohorte existente.",
            "La Fase 2 podía estudiar perturbaciones simétricas sobre la cohorte congelada.",
            "La decisión no validaba AFINO ni autorizaba ampliar la cohorte.",
        ),
        make_claim(
            "E002",
            "OBSERVATIONAL_BASELINE_REPRODUCTION",
            "El baseline observacional efectivo había reproducido cinco detecciones publicadas y conservado cinco controles emparejados no seleccionados.",
            "F1.14",
            "fase1_tarea14_phase1_evidence_ledger.csv",
            "claim_id=C001 y claim_id=C002",
            h["fase1_tarea14_phase1_evidence_ledger.csv"],
            "OBSERVATIONAL_REPRODUCTION",
            "Cinco detecciones y cinco controles examinados; no el catálogo completo.",
            "Existe una cohorte conocida y reproducible para estudiar robustez.",
            "No equivale a reproducir el pipeline privado completo ni a estimar rendimiento poblacional.",
        ),
        make_claim(
            "E003",
            "INPUT_ADMISSIBILITY",
            "F2.1 congeló antes de materializar variantes una cohorte de 10 eventos, 5 parejas, 13 ventanas y 6 perfiles.",
            "F2.1",
            "fase2_tarea01_preregistration_audit.json",
            "cohort_rows; pair_count; window_perturbation_rows; processing_profile_rows",
            h["fase2_tarea01_preregistration_audit.json"],
            "PREREGISTERED_DESIGN",
            "Diseño observacional cerrado y simétrico.",
            "Las dimensiones analizadas estaban definidas antes de observar los resultados F2.4.",
            "No se pueden presentar perfiles o ventanas posteriores como confirmatorios.",
        ),
        make_claim(
            "E004",
            "INTERPRETATION_LIMITS",
            "F2.1 congeló 780 decisiones primarias y separó explícitamente las decisiones de estabilidad.",
            "F2.1",
            "fase2_tarea01_preregistration_audit.json",
            "primary_decision_rows; stability_decision_rows; total_planned_decision_rows",
            h["fase2_tarea01_preregistration_audit.json"],
            "PREREGISTERED_DENOMINATORS",
            "Outcomes primarios y estabilidad del optimizador con poblaciones separadas.",
            "Los denominadores principales y de seed son trazables.",
            "Las 414 decisiones de estabilidad no deben mezclarse con las 780 variantes primarias.",
        ),
        make_claim(
            "E005",
            "INPUT_ADMISSIBILITY",
            "F2.2 materializó las 780 variantes primarias y congeló el plan exacto antes de ejecutar AFINO.",
            "F2.2",
            "fase2_tarea02_variant_materialization_audit.json",
            "materialization_status; primary_variant_rows; exact_executable_decisions",
            h["fase2_tarea02_variant_materialization_audit.json"],
            "STRUCTURAL_MATERIALIZATION",
            "Materialización reproducible de la cohorte y del plan.",
            "Los resultados posteriores proceden de inputs y trabajos congelados.",
            "No autoriza regenerar variantes tras observar clasificaciones.",
        ),
        make_claim(
            "E006",
            "INPUT_ADMISSIBILITY",
            "De 780 variantes primarias, 514 fueron elegibles y 266 inadmisibles.",
            "F2.2/F2.5",
            "fase2_tarea02_variant_materialization_audit.json; fase2_tarea05_observational_robustness_audit.json",
            "eligible_primary_variants; inadmissible_primary_variants; primary_eligible_variants; primary_inadmissible_variants",
            (
                h["fase2_tarea02_variant_materialization_audit.json"]
                + ";"
                + h["fase2_tarea05_observational_robustness_audit.json"]
            ),
            "INPUT_ADMISSIBILITY_RESULT",
            "Cohorte primaria completa con estado explícito por variante.",
            "La elegibilidad debe preceder a cualquier denominador de selección.",
            "Inadmisibilidad no puede recodificarse como no selección.",
        ),
        make_claim(
            "E007",
            "INPUT_ADMISSIBILITY",
            "Las 266 inadmisibles se distribuyeron en 142 IRREGULAR_SAMPLING, 98 TOO_FEW_CADENCES y 26 PEAK_REMOVED_BY_QUALITY.",
            "F2.5",
            "fase2_tarea05_observational_robustness_audit.json",
            "inadmissibility_status_counts",
            h["fase2_tarea05_observational_robustness_audit.json"],
            "DESCRIPTIVE_COUNTS",
            "Razones estructurales conservadas para las variantes no ejecutables.",
            "La admisibilidad forma parte del resultado metodológico.",
            "No debe tratarse ninguna razón como evidencia de ausencia física de QPP.",
        ),
        make_claim(
            "E008",
            "OBSERVATIONAL_BASELINE_REPRODUCTION",
            "Las diez filas W00/P00 seed 0 coincidieron con la clasificación baseline congelada.",
            "F2.5",
            "fase2_tarea05_observational_robustness_audit.json",
            "baseline_rows; baseline_classification_mismatches",
            h["fase2_tarea05_observational_robustness_audit.json"],
            "BASELINE_VERIFICATION",
            "Diez observaciones de la cohorte F2.1.",
            "El análisis de robustez parte de un baseline internamente consistente.",
            "No demuestra equivalencia documental completa con el pipeline de los autores.",
        ),
        make_claim(
            "E009",
            "INTERPRETATION_LIMITS",
            "F2.1 no congeló BIC individuales de M0, M1 y M2 para el baseline.",
            "F2.5",
            "fase2_tarea05_observational_robustness_audit.json",
            "baseline_bic_reference_fields_available; baseline_bic_comparison_status",
            h["fase2_tarea05_observational_robustness_audit.json"],
            "DOCUMENTARY_LIMITATION",
            "Comparación baseline de clasificación, deltas BIC, centro formal M1 y etiqueta.",
            "Los BIC actuales pueden registrarse como resultados F2.4.",
            "No deben presentarse como valores individuales independientemente congelados en F2.1.",
        ),
        make_claim(
            "E010",
            "OPERATIONAL_DIAGNOSTICS",
            "El runner observacional 1.2.0 superó el canary con 84 resultados, reanudación 31+53+0 y seis replays exactos.",
            "F2.3",
            "fase2_tarea03_observational_runner_validation_audit.json dentro de fase2_tarea03_entregables_mentor.zip",
            "canary_result_rows; resume_test.completed_sequence; exact_replay.passed_count",
            "56fc2eb4eec927b6032a991c2c96dc1867da394ef08129f7a774d58f5c417d7c",
            "RUNNER_VALIDATION",
            "Contrato observacional congelado y subconjunto canary.",
            "El runner es reanudable, idempotente y reproduce exactamente las llamadas auditadas.",
            "El canary no es análisis científico ni autoriza tuning.",
        ),
        make_claim(
            "E011",
            "OPERATIONAL_DIAGNOSTICS",
            "El control externo mediana/rfftfreq no coincidió con la convención efectiva de AFINO 0.5, basada en media/fftfreq positivo.",
            "F2.3/F2.4",
            "fase2_tarea03_observational_runner_validation_audit.json dentro del paquete F2.3; fase2_tarea04_full_execution_audit.json",
            "temporal_contract_resolution; temporal_validation_status; temporal_contract",
            (
                "56fc2eb4eec927b6032a991c2c96dc1867da394ef08129f7a774d58f5c417d7c"
                + ";"
                + h["fase2_tarea04_full_execution_audit.json"]
            ),
            "DOCUMENTED_VALIDATION_LIMITATION",
            "Contrato temporal de la implementación congelada AFINO 0.5.",
            "La ejecución es coherente con la convención observada de AFINO 0.5.",
            "No debe afirmarse que AFINO 0.5 cumple el control prerregistrado mediana/rfftfreq.",
        ),
        make_claim(
            "E012",
            "OPERATIONAL_DIAGNOSTICS",
            "F2.4 completó exactamente 2.784 llamadas y 928 decisiones válidas sin trabajos pendientes.",
            "F2.4",
            "fase2_tarea04_full_execution_audit.json",
            "execution_status; planned_jobs; decision_rows; result_status_counts; decision_status_counts; pending_jobs",
            h["fase2_tarea04_full_execution_audit.json"],
            "COMPLETE_EXECUTION",
            "Plan observacional exacto F2.2.",
            "La base de resultados usada en F2.5 es estructuralmente completa.",
            "Completitud operativa no equivale a validez científica.",
        ),
        make_claim(
            "E013",
            "CLASSIFICATION_ROBUSTNESS",
            "Las 780 variantes primarias quedaron en 140 SELECTED, 374 NOT_SELECTED y 266 INPUT_INADMISSIBLE.",
            "F2.5",
            "fase2_tarea05_observational_robustness_audit.json",
            "primary_outcome_counts",
            h["fase2_tarea05_observational_robustness_audit.json"],
            "FROZEN_COHORT_DESCRIPTIVE_RESULT",
            "Diez eventos con medidas repetidas de ventana y procesamiento.",
            "La cohorte muestra heterogeneidad de clasificación y de admisibilidad.",
            "No es una estimación poblacional ni una tasa global independiente.",
        ),
        make_claim(
            "E014",
            "CLASSIFICATION_ROBUSTNESS",
            "Respecto a W00/P00 hubo 140 selecciones retenidas, 136 pérdidas, 238 no selecciones retenidas y 0 ganancias.",
            "F2.5",
            "fase2_tarea05_observational_robustness_audit.json",
            "baseline_comparison_status_counts",
            h["fase2_tarea05_observational_robustness_audit.json"],
            "BASELINE_TRANSITION_TABLE",
            "Comparación de cada variante con el baseline global de su evento.",
            "Las clasificaciones publicadas reproducidas no permanecieron seleccionadas bajo todas las variantes; los controles no ganaron selección respecto a W00/P00.",
            "Pérdida no significa falso negativo y retención del control no significa verdadero negativo.",
        ),
        make_claim(
            "E015",
            "CLASSIFICATION_ROBUSTNESS",
            "SELECTION_GAINED=0 respecto a W00/P00 no contradice las transiciones locales 0→1 de ventana o procesamiento.",
            "F2.5",
            "fase2_tarea05_observational_robustness_report.md",
            "§2 comparación con baseline; §3 perturbaciones temporales; §4 perfiles de procesamiento",
            h["fase2_tarea05_observational_robustness_report.md"],
            "REFERENCE_FRAME_CLARIFICATION",
            "Tres comparaciones con referencias distintas.",
            "El baseline global usa W00/P00; los contrastes locales usan W00 del mismo perfil o el perfil izquierdo.",
            "No se deben mezclar transiciones definidas contra referencias distintas.",
        ),
        make_claim(
            "E016",
            "CLASSIFICATION_ROBUSTNESS",
            "Los contrastes temporales incluyeron 468 pares BOTH_ELIGIBLE con 302 transiciones 0→0, 4 de 0→1, 41 de 1→0 y 121 de 1→1.",
            "F2.5",
            "fase2_tarea05_observational_robustness_audit.json",
            "window_contrast_comparability_counts; window_contrast_transition_counts",
            h["fase2_tarea05_observational_robustness_audit.json"],
            "PAIRED_WINDOW_CONTRASTS",
            "Ventanas no-W00 comparadas con W00 del mismo evento y perfil.",
            "La clasificación depende de la ventana en parte de la cohorte.",
            "Los 720 contrastes no son 720 observaciones independientes.",
        ),
        make_claim(
            "E017",
            "CLASSIFICATION_ROBUSTNESS",
            "Los contrastes de procesamiento incluyeron 429 pares BOTH_ELIGIBLE con 292 transiciones 0→0, 1 de 0→1, 44 de 1→0 y 92 de 1→1.",
            "F2.5",
            "fase2_tarea05_observational_robustness_audit.json",
            "processing_contrast_comparability_counts; processing_contrast_transition_counts",
            h["fase2_tarea05_observational_robustness_audit.json"],
            "PAIRED_PROCESSING_CONTRASTS",
            "Seis contrastes prerregistrados dentro del mismo evento y ventana.",
            "La clasificación depende del perfil de procesamiento en parte de la cohorte.",
            "No demuestra causalidad de PDCSAP, SAP, QUALITY o detrending.",
        ),
        make_claim(
            "E018",
            "OPTIMIZER_NUMERICAL_STABILITY",
            "Las 46 variantes W00 elegibles mantuvieron la misma clasificación en seeds 0–9.",
            "F2.5",
            "fase2_tarea05_observational_robustness_audit.json",
            "stability_variants; stability_selected_seed_count_distribution; stability_decision_discordant_variants",
            h["fase2_tarea05_observational_robustness_audit.json"],
            "SEED_CLASSIFICATION_STABILITY",
            "46 variantes W00, diez seeds por variante.",
            "La clasificación fue estable frente a la seed externa en este subconjunto.",
            "No demuestra convergencia ni unicidad numérica.",
        ),
        make_claim(
            "E019",
            "OPTIMIZER_NUMERICAL_STABILITY",
            "Cada variante de estabilidad presentó múltiples payloads de parámetros entre seeds.",
            "F2.5",
            "fase2_tarea05_observational_robustness_report.md",
            "§5 estabilidad frente a seed externa",
            h["fase2_tarea05_observational_robustness_report.md"],
            "PARAMETER_MULTIPLICITY_DIAGNOSTIC",
            "Payloads serializados de M0, M1 y M2 para las diez seeds.",
            "stable classification ≠ unique numerical optimum.",
            "Payloads distintos no demuestran óptimos físicos o estadísticos distintos.",
        ),
        make_claim(
            "E020",
            "CLASSIFICATION_ROBUSTNESS",
            "En el benchmark sintético principal no hubo selección en 0/480 realizaciones nulas.",
            "F1.14",
            "fase1_tarea14_phase1_evidence_ledger.csv",
            "claim_id=C005",
            h["fase1_tarea14_phase1_evidence_ledger.csv"],
            "SYNTHETIC_GROUND_TRUTH",
            "Nulo sintético estacionario congelado.",
            "No hubo synthetic false selection en ese generador y diseño.",
            "No es una tasa observacional de falsos positivos.",
        ),
        make_claim(
            "E021",
            "CLASSIFICATION_ROBUSTNESS",
            "Las condiciones positivas sintéticas fueron fuertemente estratificadas: 21/99 tuvieron alguna selección y 78/99 ninguna.",
            "F1.14",
            "fase1_tarea14_phase1_evidence_ledger.csv",
            "claim_id=C006",
            h["fase1_tarea14_phase1_evidence_ledger.csv"],
            "SYNTHETIC_GROUND_TRUTH",
            "Grid sintético estacionario F1.1.",
            "La detectabilidad depende de longitud, periodo, ruido y amplitud.",
            "No define una sensibilidad global ni extrapolable a TESS real.",
        ),
        make_claim(
            "E022",
            "CLASSIFICATION_ROBUSTNESS",
            "En las 2.040 decisiones sintéticas cortas fallaron ambas comparaciones y M0 fue el ganador BIC.",
            "F1.14",
            "fase1_tarea14_phase1_synthesis_report.md",
            "§ Ground truth sintético y dominio de funcionamiento",
            h["fase1_tarea14_phase1_synthesis_report.md"],
            "SHORT_WINDOW_SYNTHETIC_DIAGNOSTIC",
            "Condiciones N=15 y N=30 del benchmark congelado.",
            "Las ventanas cortas probadas fueron desfavorables frente a M0 y M2.",
            "No demuestra que AFINO nunca pueda detectar QPP en ventanas cortas.",
        ),
        make_claim(
            "E023",
            "CLASSIFICATION_ROBUSTNESS",
            "El benchmark anidado mostró cruces ascendentes y descendentes; la selección no fue monotónica con la extensión temporal.",
            "F1.14",
            "fase1_tarea14_phase1_synthesis_report.md",
            "§ Aporte y límites del benchmark anidado",
            h["fase1_tarea14_phase1_synthesis_report.md"],
            "NESTED_SYNTHETIC_DIAGNOSTIC",
            "Prefijos anidados con cambios conjuntos de cola, normalización, Hann y FFT.",
            "La sensibilidad a ventana justificó el análisis observacional F2.",
            "No establece un efecto causal puro del número de bins.",
        ),
        make_claim(
            "E024",
            "PERIOD_ROBUSTNESS",
            "La robustez del periodo contiene 140 filas condicionadas a baseline y variante seleccionados con periodos disponibles.",
            "F2.5",
            "fase2_tarea05_observational_robustness_audit.json",
            "period_robustness_rows; period_absolute_change_summary",
            h["fase2_tarea05_observational_robustness_audit.json"],
            "CONDITIONAL_PERIOD_RESULT",
            "Variantes cuya selección sobrevivió.",
            "El cambio absoluto mediano fue 0,244031 s y el máximo 2,714694 s dentro de esa población condicionada.",
            "No caracteriza las 136 pérdidas ni las 266 inadmisibles.",
        ),
        make_claim(
            "E025",
            "PERIOD_ROBUSTNESS",
            "Los 374 centros formales M1 de decisiones no seleccionadas permanecieron separados del periodo recuperado.",
            "F2.5",
            "fase2_tarea05_observational_robustness_audit.json",
            "formal_m1_center_not_selected_count",
            h["fase2_tarea05_observational_robustness_audit.json"],
            "PERIOD_LABEL_SEPARATION",
            "Decisiones primarias no seleccionadas con centro formal disponible.",
            "El centro formal puede auditarse como output M1.",
            "No puede presentarse como periodo recuperado.",
        ),
        make_claim(
            "E026",
            "OPERATIONAL_DIAGNOSTICS",
            "M1 registró bounds en 632/928 llamadas y M2 warnings en 555/928, 4.690 warnings totales y bounds en 827/928.",
            "F2.4",
            "fase2_tarea04_full_execution_audit.json",
            "operational_diagnostics.M1; operational_diagnostics.M2",
            h["fase2_tarea04_full_execution_audit.json"],
            "NUMERICAL_DIAGNOSTIC",
            "Plan completo observacional, desglosado por modelo.",
            "Warnings y bounds deben acompañar la lectura metodológica.",
            "No explican causalmente los cambios de clasificación.",
        ),
        make_claim(
            "E027",
            "OPERATIONAL_DIAGNOSTICS",
            "convergence_status permaneció NOT_AUDITABLE en las 2.784 llamadas.",
            "F2.4",
            "fase2_tarea04_full_execution_audit.json",
            "operational_diagnostics.*.convergence_status_counts",
            h["fase2_tarea04_full_execution_audit.json"],
            "CONVERGENCE_LIMITATION",
            "M0, M1 y M2 en el plan completo.",
            "La convergencia formal no fue auditada.",
            "Estabilidad de clasificación no puede equipararse a convergencia demostrada.",
        ),
        make_claim(
            "E028",
            "INTERPRETATION_LIMITS",
            "La cohorte contiene diez eventos y cinco parejas con ventanas, perfiles y seeds como medidas repetidas.",
            "F2.5",
            "fase2_tarea05_observational_robustness_audit.json",
            "cohort_events; cohort_pairs; statistical_scope",
            h["fase2_tarea05_observational_robustness_audit.json"],
            "SCOPE_LIMITATION",
            "Unidad observacional: evento.",
            "Los resultados describen estabilidad interna de esta cohorte.",
            "No se deben tratar 780 variantes como observaciones independientes.",
        ),
        make_claim(
            "E029",
            "INTERPRETATION_LIMITS",
            "No se estableció ground truth observacional o físico.",
            "F2.5",
            "fase2_tarea05_observational_robustness_audit.json",
            "confirmations.observational_ground_truth_established; confirmations.physical_qpp_truth_inferred",
            h["fase2_tarea05_observational_robustness_audit.json"],
            "GROUND_TRUTH_NOT_ESTABLISHED",
            "Roles publicados y controles emparejados.",
            "Los roles describen la construcción de la cohorte.",
            "PUBLISHED_QPP_REPRODUCED no significa QPP física demostrada y MATCHED_NOT_SELECTED no significa verdadero negativo.",
        ),
        make_claim(
            "E030",
            "INTERPRETATION_LIMITS",
            "No se estimaron sensibilidad, especificidad ni tasa observacional de falsos positivos.",
            "F2.5",
            "fase2_tarea05_observational_robustness_audit.json",
            "confirmations.sensitivity_estimated; confirmations.specificity_estimated; confirmations.observational_false_positive_rate_estimated",
            h["fase2_tarea05_observational_robustness_audit.json"],
            "PERFORMANCE_NOT_ESTIMATED",
            "Cohorte congelada sin ground truth independiente.",
            "El resultado es robustez descriptiva.",
            "No se permite lenguaje de accuracy, sensibilidad, especificidad, FPR o FNR.",
        ),
        make_claim(
            "E031",
            "INTERPRETATION_LIMITS",
            "El descubrimiento de candidatos permaneció bloqueado durante toda la Fase 2.",
            "F1.14/F2.1–F2.5",
            "fase1_tarea14_phase1_decision.json; auditorías F2.1–F2.5",
            "candidate_discovery_allowed/authorized=false",
            (
                h["fase1_tarea14_phase1_decision.json"]
                + ";"
                + h["fase2_tarea05_observational_robustness_audit.json"]
            ),
            "PROTOCOL_CONSTRAINT",
            "Diez observaciones congeladas.",
            "La Fase 2 no amplió la población ni exploró nuevos eventos.",
            "No autoriza claims de descubrimiento.",
        ),
        make_claim(
            "E032",
            "INTERPRETATION_LIMITS",
            "Toda la evidencia observacional procede de AFINO 0.5 en un único commit congelado.",
            "F2.4",
            "fase2_tarea04_full_execution_audit.json",
            "environment.afino_commit; environment.afino_package_version",
            h["fase2_tarea04_full_execution_audit.json"],
            "IMPLEMENTATION_SCOPE",
            "Commit 6aceac9518fc8056052807e666da9d0c8bebb010, paquete 0.5.",
            "Las conclusiones se aplican a esa implementación congelada.",
            "No se generalizan automáticamente a otras versiones o configuraciones.",
        ),
        make_claim(
            "E033",
            "INTERPRETATION_LIMITS",
            "Un manuscrito metodológico de reproducción y robustez es defendible con limitaciones explícitas.",
            "F1.14+F2.5",
            "fase1_tarea14_phase1_decision.json; fase2_tarea05_observational_robustness_audit.json",
            "decision_basis; analysis_conclusion; limitations",
            (
                h["fase1_tarea14_phase1_decision.json"]
                + ";"
                + h["fase2_tarea05_observational_robustness_audit.json"]
            ),
            "DOCUMENTARY_SYNTHESIS_DECISION",
            "Reproducción efectiva, benchmarks sintéticos, cohorte F2 congelada y análisis descriptivo.",
            "Puede defenderse un artículo sobre robustez interna, admisibilidad y diagnósticos numéricos.",
            "No debe presentarse como validación observacional general de AFINO.",
        ),
        make_claim(
            "E034",
            "INTERPRETATION_LIMITS",
            "No se desarrolló ni validó una corrección del procedimiento de selección.",
            "F2.5",
            "fase2_tarea05_observational_robustness_audit.json",
            "confirmations.robustness_threshold_added=false; limitations",
            h["fase2_tarea05_observational_robustness_audit.json"],
            "CORRECTION_NOT_ESTABLISHED",
            "F2.5 caracteriza el método congelado; no diseña una regla nueva.",
            "La corrección es una ruta futura separada.",
            "No se puede diseñar una regla tras ver F2.5 y presentar F2.5 como su validación.",
        ),
    ]

    # ------------------------------------------------------------------
    # Limitations register
    # ------------------------------------------------------------------

    limitations = [
        {
            "limitation_id": "L001",
            "category": "COHORT_SCOPE",
            "description": "Cohorte de 10 eventos y 5 parejas.",
            "source_artifact": "fase2_tarea05_observational_robustness_audit.json",
            "effect_on_claims": "Limita generalización y precisión de cualquier afirmación observacional.",
            "mitigation_already_applied": "Claims restringidos a la cohorte congelada.",
            "remaining_requirement": "Validación externa o held-out para generalización.",
        },
        {
            "limitation_id": "L002",
            "category": "DEPENDENCE_STRUCTURE",
            "description": "Ventanas, perfiles y seeds son medidas repetidas dentro de eventos.",
            "source_artifact": "fase2_tarea05_observational_robustness_audit.json",
            "effect_on_claims": "Impide tratar 780 variantes como observaciones independientes.",
            "mitigation_already_applied": "Resúmenes por evento y contrastes emparejados.",
            "remaining_requirement": "Diseños inferenciales jerárquicos solo en una fase futura prerregistrada.",
        },
        {
            "limitation_id": "L003",
            "category": "GROUND_TRUTH",
            "description": "Ausencia de ground truth observacional y físico independiente.",
            "source_artifact": "fase2_tarea05_observational_robustness_audit.json",
            "effect_on_claims": "Bloquea sensibilidad, especificidad, FPR y verdad física.",
            "mitigation_already_applied": "Roles descritos como construcción de cohorte.",
            "remaining_requirement": "Benchmark independiente con etiquetas justificadas o ground truth sintético para una corrección.",
        },
        {
            "limitation_id": "L004",
            "category": "INPUT_ADMISSIBILITY",
            "description": "266 variantes primarias fueron inadmisibles.",
            "source_artifact": "fase2_tarea05_observational_robustness_audit.json",
            "effect_on_claims": "Reduce denominadores elegibles y condiciona comparabilidad.",
            "mitigation_already_applied": "Inadmisibilidad separada de no selección.",
            "remaining_requirement": "Mantener denominadores y razones explícitas en el manuscrito.",
        },
        {
            "limitation_id": "L005",
            "category": "PROCESSING_SCOPE",
            "description": "Perfiles limitados a los seis contrastes prerregistrados.",
            "source_artifact": "fase2_tarea01_processing_profiles.csv",
            "effect_on_claims": "No cubre todas las políticas de preprocesamiento plausibles.",
            "mitigation_already_applied": "No se añadieron perfiles post hoc.",
            "remaining_requirement": "Prerregistrar cualquier perfil adicional en una fase futura.",
        },
        {
            "limitation_id": "L006",
            "category": "BASELINE_FIELDS",
            "description": "F2.1 no congeló BIC individuales M0, M1 y M2 del baseline.",
            "source_artifact": "fase2_tarea05_observational_robustness_audit.json",
            "effect_on_claims": "Impide una comparación independiente congelada de cada BIC baseline.",
            "mitigation_already_applied": "Se verificaron clasificación, deltas, centro M1 y etiqueta.",
            "remaining_requirement": "Congelar BIC individuales antes de una futura replicación.",
        },
        {
            "limitation_id": "L007",
            "category": "TEMPORAL_CONTRACT",
            "description": "El control externo mediana/rfftfreq no coincide con AFINO 0.5 media/fftfreq positivo.",
            "source_artifact": "fase2_tarea03_observational_runner_validation_audit.json dentro del paquete F2.3",
            "effect_on_claims": "Obliga a separar el control prerregistrado de la convención implementada.",
            "mitigation_already_applied": "Validación temporal dual y limitación documentada.",
            "remaining_requirement": "Describir con precisión la convención AFINO 0.5 en métodos.",
        },
        {
            "limitation_id": "L008",
            "category": "CONVERGENCE",
            "description": "convergence_status permanece NOT_AUDITABLE.",
            "source_artifact": "fase2_tarea04_full_execution_audit.json",
            "effect_on_claims": "Bloquea afirmar convergencia demostrada.",
            "mitigation_already_applied": "Estado conservado en todas las filas.",
            "remaining_requirement": "Instrumentación de convergencia explícita en una futura versión.",
        },
        {
            "limitation_id": "L009",
            "category": "NUMERICAL_DIAGNOSTICS",
            "description": "Warnings y bounds frecuentes en M2.",
            "source_artifact": "fase2_tarea04_full_execution_audit.json",
            "effect_on_claims": "Exige cautela al interpretar BIC y parámetros M2.",
            "mitigation_already_applied": "Resumen por modelo, perfil, rol y ventana.",
            "remaining_requirement": "Investigar causalidad solo en un estudio separado y prerregistrado.",
        },
        {
            "limitation_id": "L010",
            "category": "NUMERICAL_DIAGNOSTICS",
            "description": "Bounds frecuentes en M1.",
            "source_artifact": "fase2_tarea04_full_execution_audit.json",
            "effect_on_claims": "Puede limitar interpretación de parámetros y centros formales.",
            "mitigation_already_applied": "Bounds registrados sin exclusión post hoc.",
            "remaining_requirement": "Evaluar parametrización o bounds en una ruta de corrección independiente.",
        },
        {
            "limitation_id": "L011",
            "category": "OPTIMIZER_MULTIPLICITY",
            "description": "Multiplicidad de payloads de parámetros entre seeds.",
            "source_artifact": "fase2_tarea05_observational_robustness_report.md",
            "effect_on_claims": "Bloquea unicidad del óptimo numérico.",
            "mitigation_already_applied": "Separación entre estabilidad de decisión y multiplicidad numérica.",
            "remaining_requirement": "Control de multiplicidad y criterios de convergencia en Fase 3 si se propone corrección.",
        },
        {
            "limitation_id": "L012",
            "category": "PERIOD_CONDITIONING",
            "description": "El periodo se evaluó solo cuando baseline y variante permanecieron seleccionados.",
            "source_artifact": "fase2_tarea05_observational_robustness_audit.json",
            "effect_on_claims": "La robustez del periodo está condicionada a supervivencia de clasificación.",
            "mitigation_already_applied": "Centros no seleccionados separados.",
            "remaining_requirement": "Mantener esta condición en abstract, resultados y discusión.",
        },
        {
            "limitation_id": "L013",
            "category": "DISCOVERY_SCOPE",
            "description": "Candidate discovery permaneció bloqueado.",
            "source_artifact": "fase1_tarea14_phase1_decision.json",
            "effect_on_claims": "No hay evidencia de rendimiento en descubrimiento.",
            "mitigation_already_applied": "Cohorte cerrada y sin eventos nuevos.",
            "remaining_requirement": "Nuevo prerregistro antes de cualquier búsqueda de candidatos.",
        },
        {
            "limitation_id": "L014",
            "category": "IMPLEMENTATION_SCOPE",
            "description": "Una única versión y commit de AFINO.",
            "source_artifact": "fase2_tarea04_full_execution_audit.json",
            "effect_on_claims": "Resultados no generalizables automáticamente a otras versiones.",
            "mitigation_already_applied": "Commit y paquete congelados.",
            "remaining_requirement": "Replicación cruzada si una futura versión modifica el método.",
        },
        {
            "limitation_id": "L015",
            "category": "PIPELINE_REPRODUCTION",
            "description": "Adaptador TESS privado y pipeline completo de autores no reconstruidos.",
            "source_artifact": "fase1_tarea14_phase1_synthesis_report.md",
            "effect_on_claims": "La reproducción es efectiva, no documentalmente completa.",
            "mitigation_already_applied": "Lenguaje de baseline efectivo y alcance limitado.",
            "remaining_requirement": "Información adicional de autores o documentación pública equivalente.",
        },
        {
            "limitation_id": "L016",
            "category": "SYNTHETIC_TO_OBSERVATIONAL",
            "description": "Los resultados sintéticos no son métricas de rendimiento observacional.",
            "source_artifact": "fase1_tarea14_phase1_evidence_ledger.csv",
            "effect_on_claims": "Bloquea trasladar synthetic false selection o detectabilidad a FPR o sensibilidad TESS.",
            "mitigation_already_applied": "Planos de evidencia separados.",
            "remaining_requirement": "Held-out con ground truth apropiado para claims de rendimiento.",
        },
        {
            "limitation_id": "L017",
            "category": "CORRECTION_VALIDATION",
            "description": "No existe regla correctiva prerregistrada ni benchmark held-out.",
            "source_artifact": "fase2_tarea05_observational_robustness_audit.json",
            "effect_on_claims": "Bloquea afirmar una corrección validada.",
            "mitigation_already_applied": "Corrección separada de manuscrito de robustez.",
            "remaining_requirement": "Ruta B completa de Fase 3.",
        },
        {
            "limitation_id": "L018",
            "category": "DATA_REUSE",
            "description": "Los diez eventos F2 no pueden servir simultáneamente para diseñar y validar una regla nueva.",
            "source_artifact": "Decisión documental F2.6 basada en F2.5 y principios de separación confirmación–exploración.",
            "effect_on_claims": "Evita validación post hoc circular.",
            "mitigation_already_applied": "F2.5 reservado como evidencia descriptiva del baseline congelado.",
            "remaining_requirement": "Datos held-out independientes para la corrección.",
        },
    ]

    # ------------------------------------------------------------------
    # Manuscript claim matrix
    # ------------------------------------------------------------------

    manuscript_claims = [
        {
            "claim_id": "M001",
            "claim_text": "El baseline publicado fue reproducido.",
            "status": "SUPPORTED_WITH_EXPLICIT_LIMITATION",
            "evidence_basis": "E002; E008; E009",
            "required_qualification": "Usar 'baseline observacional efectivo congelado' y limitarlo a cinco detecciones y cinco controles.",
            "allowed_manuscript_wording": "El baseline observacional congelado reprodujo las diez clasificaciones de la cohorte examinada.",
            "prohibited_manuscript_wording": "Se reprodujo íntegramente el pipeline privado de los autores.",
            "phase3_dependency": "",
        },
        {
            "claim_id": "M002",
            "claim_text": "AFINO selecciona de forma robusta las cinco detecciones bajo todas las variantes.",
            "status": "NOT_SUPPORTED",
            "evidence_basis": "E014",
            "required_qualification": "Reconocer las 136 pérdidas de selección y que no todas las variantes fueron admisibles.",
            "allowed_manuscript_wording": "Las clasificaciones publicadas reproducidas mostraron dependencia de ventana y procesamiento.",
            "prohibited_manuscript_wording": "Las cinco detecciones fueron robustas a todas las variantes.",
            "phase3_dependency": "",
        },
        {
            "claim_id": "M003",
            "claim_text": "Las clasificaciones publicadas son sensibles a ventana y procesamiento.",
            "status": "SUPPORTED_WITH_EXPLICIT_LIMITATION",
            "evidence_basis": "E014; E016; E017",
            "required_qualification": "Hablar de la cohorte congelada y de transiciones internas, no de falsos negativos.",
            "allowed_manuscript_wording": "Parte de las clasificaciones publicadas reproducidas cambió bajo perturbaciones prerregistradas.",
            "prohibited_manuscript_wording": "Las pérdidas demuestran que las detecciones publicadas son falsas.",
            "phase3_dependency": "",
        },
        {
            "claim_id": "M004",
            "claim_text": "Los controles emparejados elegibles permanecieron no seleccionados.",
            "status": "SUPPORTED_WITH_EXPLICIT_LIMITATION",
            "evidence_basis": "E014; E029",
            "required_qualification": "Restringirlo al diseño congelado y no llamarlos verdaderos negativos.",
            "allowed_manuscript_wording": "No se observaron ganancias respecto a W00/P00 en los controles elegibles de esta cohorte.",
            "prohibited_manuscript_wording": "Los controles prueban ausencia física de QPP.",
            "phase3_dependency": "",
        },
        {
            "claim_id": "M005",
            "claim_text": "La clasificación fue estable frente a seed externa en W00.",
            "status": "SUPPORTED_NOW",
            "evidence_basis": "E018",
            "required_qualification": "Restringir a 46 variantes W00 elegibles y seeds 0–9.",
            "allowed_manuscript_wording": "Las 46 variantes W00 elegibles mantuvieron su clasificación entre diez seeds externas.",
            "prohibited_manuscript_wording": "El optimizador siempre es estable.",
            "phase3_dependency": "",
        },
        {
            "claim_id": "M006",
            "claim_text": "El óptimo numérico fue único.",
            "status": "PROHIBITED",
            "evidence_basis": "E019; E027",
            "required_qualification": "La evidencia separa clasificación estable y multiplicidad numérica.",
            "allowed_manuscript_wording": "stable classification ≠ unique numerical optimum.",
            "prohibited_manuscript_wording": "La estabilidad entre seeds demuestra un óptimo único.",
            "phase3_dependency": "Requeriría diagnóstico de convergencia y multiplicidad independiente.",
        },
        {
            "claim_id": "M007",
            "claim_text": "El periodo fue estable cuando baseline y variante permanecieron seleccionados.",
            "status": "SUPPORTED_WITH_EXPLICIT_LIMITATION",
            "evidence_basis": "E024; E025",
            "required_qualification": "Indicar que solo se evaluaron 140 filas condicionadas a selección retenida.",
            "allowed_manuscript_wording": "Entre decisiones seleccionadas comparables, el cambio absoluto mediano fue 0,244031 s.",
            "prohibited_manuscript_wording": "El periodo fue robusto en todas las variantes.",
            "phase3_dependency": "",
        },
        {
            "claim_id": "M008",
            "claim_text": "AFINO ha sido validado observacionalmente.",
            "status": "PROHIBITED",
            "evidence_basis": "E028; E029; E030; E032",
            "required_qualification": "La Fase 2 solo caracteriza robustez interna.",
            "allowed_manuscript_wording": "Se caracterizó la robustez de una implementación congelada en una cohorte limitada.",
            "prohibited_manuscript_wording": "AFINO está validado observacionalmente.",
            "phase3_dependency": "Requeriría validación independiente con población y ground truth adecuados.",
        },
        {
            "claim_id": "M009",
            "claim_text": "Se estimó sensibilidad o especificidad.",
            "status": "PROHIBITED",
            "evidence_basis": "E030",
            "required_qualification": "No existe ground truth observacional independiente.",
            "allowed_manuscript_wording": "No se estimaron sensibilidad ni especificidad.",
            "prohibited_manuscript_wording": "La cohorte permite calcular sensibilidad o especificidad.",
            "phase3_dependency": "Held-out con etiquetas válidas.",
        },
        {
            "claim_id": "M010",
            "claim_text": "Se estableció una tasa observacional de falsos positivos.",
            "status": "PROHIBITED",
            "evidence_basis": "E020; E030",
            "required_qualification": "0/480 es synthetic false selection bajo un generador concreto.",
            "allowed_manuscript_wording": "El nulo sintético produjo 0/480 selecciones; no es FPR observacional.",
            "prohibited_manuscript_wording": "La tasa observacional de falsos positivos es cero.",
            "phase3_dependency": "Ground truth observacional independiente.",
        },
        {
            "claim_id": "M011",
            "claim_text": "Se estableció verdad física de QPP.",
            "status": "PROHIBITED",
            "evidence_basis": "E029",
            "required_qualification": "Rol observacional ≠ ground truth físico.",
            "allowed_manuscript_wording": "Se reprodujeron etiquetas publicadas sin establecer verdad física.",
            "prohibited_manuscript_wording": "Las detecciones contienen QPP físicamente demostradas.",
            "phase3_dependency": "Evidencia física independiente.",
        },
        {
            "claim_id": "M012",
            "claim_text": "Se desarrolló una corrección validada del procedimiento de selección.",
            "status": "REQUIRES_PHASE3",
            "evidence_basis": "E034",
            "required_qualification": "F2.5 no diseñó una regla nueva.",
            "allowed_manuscript_wording": "Los resultados motivan una futura ruta de corrección prerregistrada.",
            "prohibited_manuscript_wording": "La Fase 2 corrigió y validó AFINO.",
            "phase3_dependency": "Ruta B completa con regla previa y held-out independiente.",
        },
        {
            "claim_id": "M013",
            "claim_text": "Un manuscrito metodológico de robustez es defendible.",
            "status": "SUPPORTED_NOW",
            "evidence_basis": "E001–E034",
            "required_qualification": "Separar reproducción, sintético, robustez, diagnósticos y límites.",
            "allowed_manuscript_wording": "La evidencia sustenta un manuscrito de reproducción y robustez con limitaciones explícitas.",
            "prohibited_manuscript_wording": "El manuscrito demuestra corrección general del método.",
            "phase3_dependency": "",
        },
        {
            "claim_id": "M014",
            "claim_text": "Una variante inadmisible equivale a una no selección.",
            "status": "PROHIBITED",
            "evidence_basis": "E006; E007",
            "required_qualification": "inadmissibility ≠ non-selection.",
            "allowed_manuscript_wording": "Las variantes inadmisibles se conservaron fuera del denominador elegible.",
            "prohibited_manuscript_wording": "Las 266 inadmisibles fueron no detecciones.",
            "phase3_dependency": "",
        },
        {
            "claim_id": "M015",
            "claim_text": "SELECTION_GAINED=0 implica que no existieron transiciones locales 0→1.",
            "status": "PROHIBITED",
            "evidence_basis": "E015; E016; E017",
            "required_qualification": "Las referencias global y locales son distintas.",
            "allowed_manuscript_wording": "No hubo ganancias contra W00/P00, aunque sí transiciones 0→1 en contrastes locales.",
            "prohibited_manuscript_wording": "Los contrastes locales contradicen el resultado baseline.",
            "phase3_dependency": "",
        },
        {
            "claim_id": "M016",
            "claim_text": "El contrato temporal mediana/rfftfreq coincidió con AFINO 0.5.",
            "status": "NOT_SUPPORTED",
            "evidence_basis": "E011",
            "required_qualification": "Separar el control prerregistrado de la convención observada.",
            "allowed_manuscript_wording": "AFINO 0.5 fue coherente con media/fftfreq positivo; el control externo no coincidió.",
            "prohibited_manuscript_wording": "El control mediana/rfftfreq fue confirmado.",
            "phase3_dependency": "",
        },
        {
            "claim_id": "M017",
            "claim_text": "Warnings y bounds causaron los cambios de clasificación.",
            "status": "PROHIBITED",
            "evidence_basis": "E026; E027",
            "required_qualification": "Son diagnósticos, no mecanismos causales establecidos.",
            "allowed_manuscript_wording": "Warnings y bounds fueron frecuentes y acompañan la interpretación.",
            "prohibited_manuscript_wording": "Los warnings o bounds explican las pérdidas.",
            "phase3_dependency": "Estudio causal separado y prerregistrado.",
        },
    ]

    # ------------------------------------------------------------------
    # Phase 3 entry requirements
    # ------------------------------------------------------------------

    phase3_requirements = [
        {
            "requirement_id": "A001",
            "route_id": "ROUTE_A",
            "route_name": "MANUSCRITO_DE_ROBUSTEZ",
            "requirement_text": "Arquitectura final de claims basada en la matriz F2.6.",
            "rationale": "Evita mezclar robustez interna con validación o corrección.",
            "status_at_phase2_close": "READY_TO_START",
            "blocking_for_route": "true",
            "prohibited_shortcut": "Redactar primero y ajustar el alcance después.",
        },
        {
            "requirement_id": "A002",
            "route_id": "ROUTE_A",
            "route_name": "MANUSCRITO_DE_ROBUSTEZ",
            "requirement_text": "Selección final de tablas y figuras con denominadores y estados de inadmisibilidad visibles.",
            "rationale": "El manuscrito debe distinguir inadmisibilidad, no selección y pérdida.",
            "status_at_phase2_close": "PENDING_EDITORIAL_SELECTION",
            "blocking_for_route": "true",
            "prohibited_shortcut": "Usar solo figuras favorables o ocultar variantes inadmisibles.",
        },
        {
            "requirement_id": "A003",
            "route_id": "ROUTE_A",
            "route_name": "MANUSCRITO_DE_ROBUSTEZ",
            "requirement_text": "Métodos reproducibles desde F1.14 y F2.1–F2.5.",
            "rationale": "La trazabilidad por hashes es una fortaleza central.",
            "status_at_phase2_close": "SOURCE_MATERIAL_AVAILABLE",
            "blocking_for_route": "true",
            "prohibited_shortcut": "Omitir la convención temporal real de AFINO 0.5.",
        },
        {
            "requirement_id": "A004",
            "route_id": "ROUTE_A",
            "route_name": "MANUSCRITO_DE_ROBUSTEZ",
            "requirement_text": "Discusión explícita de las 18 limitaciones registradas.",
            "rationale": "El alcance defendible depende de mantenerlas visibles.",
            "status_at_phase2_close": "REGISTER_AVAILABLE",
            "blocking_for_route": "true",
            "prohibited_shortcut": "Reducir las limitaciones a una nota genérica.",
        },
        {
            "requirement_id": "A005",
            "route_id": "ROUTE_A",
            "route_name": "MANUSCRITO_DE_ROBUSTEZ",
            "requirement_text": "Disponibilidad de código y datos derivados autorizados.",
            "rationale": "Permite reproducir tablas sin redistribuir material no autorizado.",
            "status_at_phase2_close": "PACKAGE_PREPARATION_REQUIRED",
            "blocking_for_route": "true",
            "prohibited_shortcut": "Publicar rutas locales, credenciales o FITS sin revisar licencias.",
        },
        {
            "requirement_id": "A006",
            "route_id": "ROUTE_A",
            "route_name": "MANUSCRITO_DE_ROBUSTEZ",
            "requirement_text": "Redacción del manuscrito con separación entre evidencia observacional, sintética y numérica.",
            "rationale": "Cada plano responde una pregunta distinta.",
            "status_at_phase2_close": "NOT_STARTED",
            "blocking_for_route": "true",
            "prohibited_shortcut": "Usar el nulo sintético como FPR observacional.",
        },
        {
            "requirement_id": "A007",
            "route_id": "ROUTE_A",
            "route_name": "MANUSCRITO_DE_ROBUSTEZ",
            "requirement_text": "Revisión final de wording prohibido antes de someter.",
            "rationale": "Evita afirmar validación, ground truth o corrección.",
            "status_at_phase2_close": "MATRIX_AVAILABLE",
            "blocking_for_route": "true",
            "prohibited_shortcut": "Convertir conclusiones limitadas en claims generales.",
        },
        {
            "requirement_id": "B001",
            "route_id": "ROUTE_B",
            "route_name": "DESARROLLO_DE_CORRECCION",
            "requirement_text": "Definir la regla nueva antes de acceder a los datos de validación.",
            "rationale": "Previene ajuste post hoc.",
            "status_at_phase2_close": "NOT_DEFINED",
            "blocking_for_route": "true",
            "prohibited_shortcut": "Diseñar la regla sobre F2.5 y declarar F2.5 como validación.",
        },
        {
            "requirement_id": "B002",
            "route_id": "ROUTE_B",
            "route_name": "DESARROLLO_DE_CORRECCION",
            "requirement_text": "Benchmark held-out independiente.",
            "rationale": "La corrección necesita evaluación fuera de los datos que la motivaron.",
            "status_at_phase2_close": "NOT_AVAILABLE",
            "blocking_for_route": "true",
            "prohibited_shortcut": "Reutilizar los diez eventos F2 como entrenamiento y validación simultáneos.",
        },
        {
            "requirement_id": "B003",
            "route_id": "ROUTE_B",
            "route_name": "DESARROLLO_DE_CORRECCION",
            "requirement_text": "Ground truth sintético explícito para clasificación y periodo.",
            "rationale": "Permite conocer presencia, ausencia y periodo por construcción.",
            "status_at_phase2_close": "NEW_DESIGN_REQUIRED",
            "blocking_for_route": "true",
            "prohibited_shortcut": "Usar roles observacionales como verdad física.",
        },
        {
            "requirement_id": "B004",
            "route_id": "ROUTE_B",
            "route_name": "DESARROLLO_DE_CORRECCION",
            "requirement_text": "Criterios de éxito prerregistrados.",
            "rationale": "Define de antemano qué constituye mejora y qué trade-offs son aceptables.",
            "status_at_phase2_close": "NOT_DEFINED",
            "blocking_for_route": "true",
            "prohibited_shortcut": "Elegir métricas después de observar held-out.",
        },
        {
            "requirement_id": "B005",
            "route_id": "ROUTE_B",
            "route_name": "DESARROLLO_DE_CORRECCION",
            "requirement_text": "Comparación con el baseline congelado sin modificar sus resultados.",
            "rationale": "Mantiene una referencia histórica auditada.",
            "status_at_phase2_close": "BASELINE_AVAILABLE",
            "blocking_for_route": "true",
            "prohibited_shortcut": "Retocar el baseline para favorecer la regla nueva.",
        },
        {
            "requirement_id": "B006",
            "route_id": "ROUTE_B",
            "route_name": "DESARROLLO_DE_CORRECCION",
            "requirement_text": "Control de complejidad, multiplicidad y convergencia.",
            "rationale": "La estabilidad de clasificación no demostró unicidad numérica.",
            "status_at_phase2_close": "NOT_IMPLEMENTED",
            "blocking_for_route": "true",
            "prohibited_shortcut": "Ignorar seeds, warnings, bounds o múltiples soluciones.",
        },
        {
            "requirement_id": "B007",
            "route_id": "ROUTE_B",
            "route_name": "DESARROLLO_DE_CORRECCION",
            "requirement_text": "Análisis de clasificación y periodo como outcomes separados.",
            "rationale": "El periodo solo es interpretable cuando la selección sobrevive.",
            "status_at_phase2_close": "PRINCIPLE_ESTABLISHED",
            "blocking_for_route": "true",
            "prohibited_shortcut": "Usar centros M1 no seleccionados como periodos recuperados.",
        },
        {
            "requirement_id": "B008",
            "route_id": "ROUTE_B",
            "route_name": "DESARROLLO_DE_CORRECCION",
            "requirement_text": "Prohibición explícita de usar F2.5 como validación post hoc.",
            "rationale": "F2.5 ya fue observado y solo puede motivar hipótesis.",
            "status_at_phase2_close": "MANDATORY",
            "blocking_for_route": "true",
            "prohibited_shortcut": "Presentar mejora sobre F2.5 como evidencia confirmatoria.",
        },
        {
            "requirement_id": "B009",
            "route_id": "ROUTE_B",
            "route_name": "DESARROLLO_DE_CORRECCION",
            "requirement_text": "Separación formal entre conjunto de desarrollo y conjunto de validación.",
            "rationale": "Evita circularidad y optimismo de selección.",
            "status_at_phase2_close": "NOT_AVAILABLE",
            "blocking_for_route": "true",
            "prohibited_shortcut": "Particionar post hoc los diez eventos tras diseñar la regla.",
        },
    ]

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------

    decision = {
        "phase2_status": PHASE2_DECISION,
        "robustness_manuscript_viable": True,
        "correction_claim_established": False,
        "held_out_validation_required_for_correction": True,
        "candidate_discovery_allowed": False,
        "observational_ground_truth_established": False,
        "afino_validated": False,
        "sensitivity_estimated": False,
        "specificity_estimated": False,
        "recommended_next_route": (
            "ROUTE_A_ROBUSTNESS_MANUSCRIPT_NOW; "
            "ROUTE_B_ONLY_AS_SEPARATE_PREREGISTERED_HELD_OUT_PROGRAM"
        ),
        "decision_basis": [
            "F1.14 separó reproducción observacional, ground truth sintético, diagnósticos numéricos e interpretación física no establecida.",
            "F2.1 congeló cohorte, ventanas, perfiles, outcomes y denominadores antes de materializar variantes.",
            "F2.2 conservó 780 variantes, incluidas 266 inadmisibles, y congeló 928 decisiones ejecutables.",
            "F2.3 validó el runner con una limitación temporal explícita y sin tuning.",
            "F2.4 completó 2.784 llamadas y 928 decisiones válidas con integridad estructural.",
            "F2.5 mostró pérdidas de selección bajo perturbaciones, estabilidad frente a seed en W00 y multiplicidad numérica.",
            "F2.5 no estableció ground truth, sensibilidad, especificidad, FPR ni verdad física.",
            "No existe una regla correctiva definida antes de datos held-out.",
            "Los diez eventos F2 no pueden usarse para desarrollar y validar simultáneamente una corrección.",
        ],
        "immediate_manuscript_scope": [
            "reproducción del baseline observacional efectivo",
            "resultados sintéticos relevantes de Fase 1",
            "admisibilidad de inputs observacionales",
            "dependencia de clasificación respecto a ventana y procesamiento",
            "estabilidad de clasificación frente a seed externa",
            "periodo condicionado a selección retenida",
            "warnings, bounds y convergencia no auditable",
            "limitaciones de interpretación y ausencia de ground truth",
        ],
        "prohibited_phase2_conclusions": [
            "AFINO está validado observacionalmente.",
            "Se estimaron sensibilidad o especificidad.",
            "Se estableció una tasa observacional de falsos positivos.",
            "Se estableció verdad física de QPP.",
            "Se validó una corrección del procedimiento.",
            "Los controles son verdaderos negativos.",
            "La estabilidad entre seeds demuestra un óptimo único.",
        ],
    }

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    report = f"""# Fase 2 — Tarea 2.6

## Síntesis de Fase 2 y decisión de ruta del manuscrito

**Decisión:** `{PHASE2_DECISION}`

## 1. Pregunta metodológica

La pregunta que puede responder la Fase 2 no es si AFINO es correcto en
general ni si las señales etiquetadas contienen QPP físicamente demostradas.
La pregunta defendible es más delimitada: una vez congelado un baseline
observacional efectivo que reproduce diez clasificaciones conocidas, ¿cómo
cambian esas clasificaciones cuando se perturban de manera prerregistrada la
ventana temporal y el procesamiento, y qué estabilidad numérica conserva la
implementación AFINO 0.5? Esta formulación mantiene separados cuatro planos:
reproducción de una clasificación publicada, comportamiento bajo ground truth
sintético, robustez interna de una cohorte observacional y diagnósticos
numéricos. La síntesis documental no añade umbrales, eventos ni estadísticas
científicas nuevas.

## 2. Evidencia reproducida

F1.14 autorizó pasar a robustez observacional con limitaciones y mantuvo
bloqueado el descubrimiento. El baseline efectivo había reproducido cinco
detecciones publicadas y conservado como no seleccionados cinco controles
emparejados. F2.1 congeló diez eventos, cinco parejas, trece ventanas, seis
perfiles y denominadores separados para análisis primario y estabilidad.
F2.2 materializó 780 variantes y congeló el plan exacto antes de AFINO. F2.3
validó el runner checkpointed: 84 resultados canary, reanudación 31+53+0,
idempotencia y seis replays exactos. F2.4 ejecutó las 2.784 llamadas previstas
y exportó 928 decisiones válidas sin trabajos pendientes. Por último, F2.5
representó las 780 variantes primarias, conservó las 46 variantes W00 con diez
seeds y cerró con `FROZEN_COHORT_ROBUSTNESS_CHARACTERIZED_WITH_LIMITATIONS`.

La reproducción tiene un alcance concreto. Demuestra que el protocolo público
congelado recupera las clasificaciones de estas diez observaciones y permite
evaluar su estabilidad interna. No demuestra que se haya reconstruido el
adaptador TESS privado ni el pipeline documental completo de los autores.

## 3. Resultados sintéticos relevantes de Fase 1

Los benchmarks sintéticos aportan contexto, pero no métricas observacionales.
En el nulo estacionario principal hubo `synthetic false selection 0/480`.
Entre 99 condiciones positivas, 21 tuvieron alguna selección y 78 ninguna,
con una dependencia fuerte de longitud, periodo, ruido y amplitud. En las
2.040 decisiones de ventanas cortas N=15 o N=30 fallaron simultáneamente las
comparaciones frente a M0 y M2, y M0 fue el ganador BIC. El benchmark anidado
mostró cruces ascendentes y descendentes: ampliar la porción temporal no
produjo una mejora monotónica. Además, la clasificación fue estable frente a
seed en los subconjuntos sintéticos, mientras M2 presentó múltiples soluciones
en gran parte de las condiciones.

Estos resultados justificaron estudiar ventana y optimizador en observaciones
reales. No autorizan llamar sensibilidad al porcentaje de condiciones
positivas seleccionadas ni FPR observacional al resultado del nulo. Tampoco
demuestran un efecto causal puro del número de bins, porque las extensiones
anidadas modifican simultáneamente cola, normalización, ventana de Hann y FFT.

## 4. Admisibilidad observacional

F2.2 y F2.5 coinciden en que 514 de las 780 variantes fueron elegibles y 266
inadmisibles: 142 por `IRREGULAR_SAMPLING`, 98 por `TOO_FEW_CADENCES` y 26 por
`PEAK_REMOVED_BY_QUALITY`. Esta separación es sustantiva, no meramente
administrativa. `inadmissibility ≠ non-selection`: una variante que no cumple
el contrato de entrada no proporciona una decisión negativa de AFINO y no
debe entrar en el denominador de selección entre elegibles.

La admisibilidad también limita comparaciones. Una celda con menos variantes
elegibles no puede compararse utilizando `selected/planned` como si las
inadmisibles fueran ceros. El manuscrito debe mostrar siempre variantes
previstas, elegibles e inadmisibles y conservar sus razones. Esta decisión
evita una apariencia artificial de estabilidad o de pérdida creada por
recodificación.

## 5. Robustez de clasificación

Entre las 780 variantes hubo 140 `SELECTED`, 374 `NOT_SELECTED` y 266
`INPUT_INADMISSIBLE`. Respecto al baseline global W00/P00 de cada evento,
F2.5 registró 140 selecciones retenidas, 136 pérdidas, 238 no selecciones
retenidas y cero ganancias. La lectura defendible es que las clasificaciones
publicadas reproducidas son sensibles a cambios de ventana y procesamiento,
mientras los controles emparejados elegibles permanecieron no seleccionados
en este diseño. Las pérdidas no son falsos negativos y los controles no son
verdaderos negativos, porque `observational role ≠ physical ground truth`.

El valor `SELECTION_GAINED = 0` respecto a W00/P00 no contradice las cuatro
transiciones temporales 0→1 ni la transición de procesamiento 0→1. Las
referencias son diferentes. La comparación global enfrenta cada variante con
W00/P00. El contraste de ventanas enfrenta una ventana con W00 del mismo
perfil. El contraste de procesamiento enfrenta el perfil derecho con el
perfil izquierdo en el mismo evento y ventana. Una variante puede pasar de
0 a 1 respecto a una referencia local que ya difiere del baseline global sin
crear una ganancia respecto a W00/P00.

## 6. Seed, warnings y bounds

Las 46 variantes W00 elegibles mantuvieron su clasificación entre seeds 0–9:
15 fueron seleccionadas 10/10 veces y 31 no seleccionadas 0/10. No hubo
discordancia de decisión. Sin embargo, cada variante mostró múltiples
payloads de parámetros en los tres modelos. La formulación que debe
mantenerse es `stable classification ≠ unique numerical optimum`. La
estabilidad binaria no prueba que el optimizador alcance un único punto ni
que las soluciones tengan una interpretación física distinta.

Los diagnósticos operativos tampoco son accesorios. M1 alcanzó bounds en
632 de 928 llamadas. M2 produjo warnings en 555 llamadas, 4.690 warnings
totales y bounds en 827 llamadas. `convergence_status` permaneció
`NOT_AUDITABLE` en las 2.784 llamadas. Estos hechos deben figurar en métodos,
resultados o limitaciones, pero no permiten atribuir causalidad entre un
warning, un bound y un cambio de clasificación.

## 7. Periodo

La tabla de robustez del periodo contiene 140 filas en las que el baseline y
la variante permanecieron seleccionados y ambos periodos estaban disponibles.
Dentro de esa población condicionada, el cambio absoluto mediano fue
0,244031 s y el máximo 2,714694 s. Esta evidencia permite describir
estabilidad del periodo cuando la selección sobrevive, no robustez global del
periodo. `period robustness is conditional on retained selection`.

Los 374 centros formales M1 de decisiones no seleccionadas se conservaron como
`formal_m1_center_not_selected`. Son outputs auditables del modelo, pero no
periodos recuperados. No compensan las 136 pérdidas de clasificación ni las
266 variantes inadmisibles y deben permanecer fuera de las figuras y
resúmenes de periodo recuperado.

## 8. Limitaciones

La cohorte contiene solo diez eventos y cinco parejas. Ventanas, perfiles y
seeds son medidas repetidas dentro de eventos. No existe ground truth
observacional o físico independiente, y los perfiles se limitan a los
prerregistrados. F2.1 no congeló BIC individuales del baseline. El control
temporal externo mediana/rfftfreq no coincidió con la convención efectiva
media/fftfreq positivo de AFINO 0.5. La convergencia no es auditable; M1 y M2
presentan bounds frecuentes; M2 acumula warnings; y la multiplicidad de
parámetros impide afirmar unicidad numérica.

La evidencia corresponde a una única versión y commit de AFINO. El
descubrimiento de candidatos permaneció bloqueado. El adaptador TESS privado
y la política completa de los autores siguen sin reconstruirse. Finalmente,
los diez eventos F2 ya han sido observados: pueden motivar una corrección,
pero no funcionar simultáneamente como datos de desarrollo y validación.

## 9. Claims defendibles

Son defendibles: reproducción del baseline observacional efectivo en las diez
observaciones; dependencia de las clasificaciones publicadas respecto a
ventana y procesamiento; permanencia no seleccionada de los controles
elegibles dentro del diseño; estabilidad de clasificación frente a seed en
W00; estabilidad condicionada del periodo; y presencia de limitaciones
numéricas documentadas. También es defendible integrar los resultados
sintéticos de Fase 1 como caracterización del dominio probado, siempre
separados del rendimiento observacional.

No son defendibles: validación observacional de AFINO, sensibilidad,
especificidad, FPR observacional, ground truth físico, unicidad del óptimo o
causalidad de warnings y bounds. Tampoco es defendible afirmar que las cinco
detecciones fueron seleccionadas bajo todas las variantes. El manuscrito debe
formular las pérdidas como transiciones internas y las inadmisibles como
inputs sin decisión.

## 10. Decisión: manuscrito de robustez o corrección futura

La ruta inmediata recomendada es la Ruta A: un manuscrito metodológico de
reproducción y robustez con arquitectura de claims, métodos reproducibles,
tablas con denominadores, discusión extensa de limitaciones y código y datos
derivados auditables. La base documental y científica necesaria ya existe.

La Ruta B, una corrección del procedimiento, permanece abierta pero no
establecida. Exige definir una regla antes de ver los datos de validación,
prerregistrar criterios de éxito, construir ground truth sintético apropiado,
comparar con el baseline congelado, controlar complejidad y multiplicidad y
separar clasificación de periodo. Sobre todo, requiere un benchmark held-out
independiente. Está prohibido ajustar una regla sobre F2.5 y presentar los
mismos diez eventos como validación confirmatoria. La Fase 2 queda cerrada:
el artículo de robustez es viable con limitaciones; la afirmación de
corrección requiere Fase 3.

`{PHASE2_DECISION}`
"""

    report_word_count = len(
        re.findall(
            r"\b[\wÁÉÍÓÚÜÑáéíóúüñ]+\b",
            report,
        )
    )
    if not 1200 <= report_word_count <= 1700:
        raise RuntimeError(
            f"Report word count {report_word_count} outside 1200–1700."
        )

    # ------------------------------------------------------------------
    # Documentary audit
    # ------------------------------------------------------------------

    claim_fields = [
        "claim_id",
        "evidence_plane",
        "claim_text",
        "source_phase",
        "source_artifact",
        "source_locator",
        "source_sha256",
        "evidence_class",
        "scope",
        "allowed_interpretation",
        "prohibited_interpretation",
    ]
    limitation_fields = [
        "limitation_id",
        "category",
        "description",
        "source_artifact",
        "effect_on_claims",
        "mitigation_already_applied",
        "remaining_requirement",
    ]
    manuscript_fields = [
        "claim_id",
        "claim_text",
        "status",
        "evidence_basis",
        "required_qualification",
        "allowed_manuscript_wording",
        "prohibited_manuscript_wording",
        "phase3_dependency",
    ]
    phase3_fields = [
        "requirement_id",
        "route_id",
        "route_name",
        "requirement_text",
        "rationale",
        "status_at_phase2_close",
        "blocking_for_route",
        "prohibited_shortcut",
    ]

    claims_without_source = sum(
        not row["source_artifact"].strip()
        or not row["source_sha256"].strip()
        or not row["source_locator"].strip()
        for row in claims
    )
    claims_without_scope = sum(
        not row["scope"].strip() for row in claims
    )
    claims_without_prohibited = sum(
        not row["prohibited_interpretation"].strip()
        for row in claims
    )
    represented_planes = sorted({
        row["evidence_plane"] for row in claims
    })
    if set(represented_planes) != MANDATORY_EVIDENCE_PLANES:
        raise RuntimeError(
            f"Evidence planes mismatch: {represented_planes}"
        )
    if (
        claims_without_source
        or claims_without_scope
        or claims_without_prohibited
    ):
        raise RuntimeError("Incomplete evidence-ledger claims.")
    if any(
        row["status"] not in CLAIM_STATUSES
        for row in manuscript_claims
    ):
        raise RuntimeError("Invalid manuscript claim status.")

    audit = {
        "date_utc": utc_now(),
        "phase2_status": PHASE2_DECISION,
        "source_packages_verified": source_packages_verified,
        "direct_sources_verified": direct_hashes,
        "normative_states_verified": {
            phase: observed
            for phase, (observed, _) in expected_states.items()
        },
        "claims_total": len(claims),
        "claims_without_source": claims_without_source,
        "claims_without_scope": claims_without_scope,
        "claims_without_prohibited_interpretation":
            claims_without_prohibited,
        "evidence_planes_represented": represented_planes,
        "limitations_registered": len(limitations),
        "manuscript_claims_assessed": len(manuscript_claims),
        "phase3_requirements": len(phase3_requirements),
        "phase3_requirements_by_route": {
            "ROUTE_A": sum(
                row["route_id"] == "ROUTE_A"
                for row in phase3_requirements
            ),
            "ROUTE_B": sum(
                row["route_id"] == "ROUTE_B"
                for row in phase3_requirements
            ),
        },
        "incidents": [
            {
                "incident_id": "F2.3-TEMPORAL-CONTRACT-001",
                "category": "DOCUMENTED_VALIDATION_LIMITATION",
                "description": "El control mediana/rfftfreq no coincidió con la convención AFINO 0.5 media/fftfreq positivo.",
                "effect_on_synthesis": "Se conserva como limitación y no invalida las clasificaciones ejecutadas.",
                "resolved_for_phase2": True,
            },
            {
                "incident_id": "F2.5-BASELINE-BIC-FIELDS-001",
                "category": "FROZEN_FIELD_ABSENCE",
                "description": "F2.1 no contiene BIC individuales M0/M1/M2 del baseline.",
                "effect_on_synthesis": "El manuscrito no puede afirmar una comparación independiente congelada de esos tres valores.",
                "resolved_for_phase2": True,
            },
        ],
        "report_word_count": report_word_count,
        "decision_consistency": {
            "robustness_manuscript_viable": True,
            "correction_claim_established": False,
            "correction_requires_phase3": True,
            "held_out_required": True,
            "f2_5_may_be_used_as_posthoc_validation": False,
        },
        "confirmations": {
            "afino_executed": False,
            "fits_opened": False,
            "variants_regenerated": False,
            "new_statistics_computed": False,
            "new_threshold_added": False,
            "candidate_discovery_authorized": False,
            "observational_ground_truth_established": False,
            "sensitivity_estimated": False,
            "specificity_estimated": False,
            "physical_qpp_truth_inferred": False,
            "correction_claim_established": False,
            "events_removed": False,
            "inadmissible_variants_removed": False,
        },
    }

    # ------------------------------------------------------------------
    # Stage, validate, publish
    # ------------------------------------------------------------------

    staging = Path(tempfile.mkdtemp(
        prefix=".fase2_tarea06_staging_",
        dir=output_dir,
    ))
    try:
        write_csv(
            staging / OUTPUT_NAMES[0],
            claim_fields,
            claims,
        )
        write_csv(
            staging / OUTPUT_NAMES[1],
            limitation_fields,
            limitations,
        )
        write_csv(
            staging / OUTPUT_NAMES[2],
            manuscript_fields,
            manuscript_claims,
        )
        write_csv(
            staging / OUTPUT_NAMES[3],
            phase3_fields,
            phase3_requirements,
        )
        (staging / OUTPUT_NAMES[4]).write_text(
            json.dumps(
                decision,
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        (staging / OUTPUT_NAMES[5]).write_text(
            json.dumps(
                audit,
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        (staging / OUTPUT_NAMES[6]).write_text(
            report,
            encoding="utf-8",
        )

        expected_rows = {
            OUTPUT_NAMES[0]: len(claims),
            OUTPUT_NAMES[1]: len(limitations),
            OUTPUT_NAMES[2]: len(manuscript_claims),
            OUTPUT_NAMES[3]: len(phase3_requirements),
        }
        for filename, expected in expected_rows.items():
            observed = len(read_csv(staging / filename))
            if observed != expected:
                raise RuntimeError(
                    f"{filename}: {observed} != {expected}"
                )

        final_decision = json.loads(
            (staging / OUTPUT_NAMES[4]).read_text(
                encoding="utf-8"
            )
        )
        final_audit = json.loads(
            (staging / OUTPUT_NAMES[5]).read_text(
                encoding="utf-8"
            )
        )
        if final_decision["phase2_status"] != PHASE2_DECISION:
            raise RuntimeError("Decision status changed.")
        if final_audit["phase2_status"] != PHASE2_DECISION:
            raise RuntimeError("Audit status changed.")
        if any(final_audit["confirmations"].values()):
            raise RuntimeError("A required confirmation is not false.")

        for name in OUTPUT_NAMES:
            os.replace(staging / name, output_dir / name)
        staging.rmdir()

        final_hashes = {
            name: sha256(output_dir / name)
            for name in OUTPUT_NAMES
        }
        print("F2.6 PHASE 2 SYNTHESIS COMPLETE")
        print(f"phase2_status: {PHASE2_DECISION}")
        print(f"claims_total: {len(claims)}")
        print(f"limitations_registered: {len(limitations)}")
        print(
            f"manuscript_claims_assessed: "
            f"{len(manuscript_claims)}"
        )
        print(
            f"phase3_requirements: "
            f"{len(phase3_requirements)}"
        )
        print(f"report_word_count: {report_word_count}")
        print("afino_executed: false")
        print("fits_opened: false")
        print("new_statistics_computed: false")
        for name in OUTPUT_NAMES:
            print(f"{name}: {final_hashes[name]}")
    except Exception:
        print(
            f"F2.6 SYNTHESIS STOPPED; preserve staging: {staging}",
            file=sys.stderr,
        )
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    build_outputs(args.input_dir.resolve(), args.output_dir.resolve())
    return 0


if __name__ == "__main__":
    import sys
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"PHASE2_SYNTHESIS_BLOCKED: {exc}",
            file=sys.stderr,
        )
        raise
