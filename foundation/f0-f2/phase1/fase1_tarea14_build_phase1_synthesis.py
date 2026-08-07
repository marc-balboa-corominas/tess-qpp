from __future__ import annotations

from pathlib import Path
from typing import Any
import csv
import hashlib
import json
import re
import zipfile


ROOT = Path(__file__).resolve().parent

OUTPUT_NAMES = [
    "fase1_tarea14_phase1_evidence_ledger.csv",
    "fase1_tarea14_phase2_entry_requirements.csv",
    "fase1_tarea14_phase1_decision.json",
    "fase1_tarea14_phase1_synthesis_audit.json",
    "fase1_tarea14_phase1_synthesis_report.md",
]

DIRECT_SOURCE_HASHES = {
    "fase0_tarea15_reproduced_baseline.json":
        "4c0bf97f875b9beb2bd2d619b26fa77b083fb946a05d3ee48c32896046690dc7",
    "fase1_tarea01_core_benchmark_preregistration.json":
        "dd80346172290e014d73f78240b3e31f135bcc7e4f075963e7e20d8456de3401",
    "fase1_tarea06_analysis_audit.json":
        "207b1b058a8faf6d145bb31d698a9994c90fa2550e0ea7d204c330f7a875a04a",
    "fase1_tarea06_condition_summary.csv":
        "25c60ca7cfdbb46bb9a389fa16ce8f2be98e734e689186815c6a97cdc042d1eb",
    "fase1_tarea06_core_benchmark_analysis.md":
        "c9d31f3b248ae6298eb40d50b27f58adc545226c2c616996584a7cd0749a570c",
    "fase1_tarea07_short_window_diagnostic_audit.json":
        "c565716438d3990119aea48ed85ac8018fa4772d0cb1c952f33e02971ab0c2da",
    "fase1_tarea07_short_window_amplitude_contrasts.csv":
        "d92ecbf529949a22b2d8314af491b401d920b52d10a3a0db89fa5cb10bc432fc",
    "fase1_tarea07_short_window_diagnostic.md":
        "ea7489ead5d1f57f8effb6e52a8311eeafbac41d9b41af62981f4603d34d5dc0",
    "fase1_tarea08_nested_window_preregistration.json":
        "d80890319b4646f8df994ba7c1dd9da3dc1f141834dbf289d1b17c484fa67487",
    "fase1_tarea13_nested_analysis_audit.json":
        "7994cd4475c02f2f2675a3275dc1b7d6b90f0bfc9a9532555ea0541e8012ef35",
    "fase1_tarea13_nested_analysis_report.md":
        "532711677fdc92ad317110000f27c49bc72c1a809892bca6a93c6a32d871b728",
    "fase1_tarea13_optimizer_stability_summary.csv":
        "0250bf0deb69f02e8a716b9c8e77c43dc962ad6b28147c1831fc28570793bbc9",
    "fase1_tarea13_model_diagnostics_by_n.csv":
        "d8a4193c644d820a2546cd828e9ef141aa674bd89401d5a1cf1afe98743f0a54",
}

PACKAGE_SOURCES = {
    "F1.6": {
        "package": "fase1_tarea06_entregables_mentor.zip",
        "artifacts": [
            "fase1_tarea06_analysis_audit.json",
            "fase1_tarea06_condition_summary.csv",
            "fase1_tarea06_core_benchmark_analysis.md",
        ],
    },
    "F1.7": {
        "package": "fase1_tarea07_entregables_mentor.zip",
        "artifacts": [
            "fase1_tarea07_short_window_diagnostic_audit.json",
            "fase1_tarea07_short_window_amplitude_contrasts.csv",
            "fase1_tarea07_short_window_diagnostic.md",
        ],
    },
    "F1.8": {
        "package": "fase1_tarea08_entregables_mentor.zip",
        "artifacts": [
            "fase1_tarea08_nested_window_preregistration.json",
        ],
    },
    "F1.13": {
        "package": "fase1_tarea13_entregables_mentor.zip",
        "artifacts": [
            "fase1_tarea13_nested_analysis_audit.json",
            "fase1_tarea13_nested_analysis_report.md",
            "fase1_tarea13_optimizer_stability_summary.csv",
            "fase1_tarea13_model_diagnostics_by_n.csv",
        ],
    },
}

EVIDENCE_CLASSES = [
    "OBSERVATIONAL_REPRODUCTION",
    "SYNTHETIC_GROUND_TRUTH",
    "NUMERICAL_DIAGNOSTIC",
    "METHOD_CONSTRAINT",
    "PHYSICAL_INTERPRETATION_NOT_ESTABLISHED",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


for name in OUTPUT_NAMES:
    if (ROOT / name).exists():
        raise FileExistsError(
            f"Refusing to overwrite existing artifact: {name}"
        )

source_hashes_before: dict[str, str] = {}
for filename, expected in DIRECT_SOURCE_HASHES.items():
    path = ROOT / filename
    if not path.is_file():
        raise FileNotFoundError(path)
    observed = sha256(path)
    if observed != expected:
        raise RuntimeError(
            f"Source hash mismatch for {filename}: "
            f"{observed} != {expected}"
        )
    source_hashes_before[filename] = observed

package_verification: list[dict[str, Any]] = []
for source_task, specification in PACKAGE_SOURCES.items():
    package_path = ROOT / specification["package"]
    if not package_path.is_file():
        raise FileNotFoundError(package_path)
    with zipfile.ZipFile(package_path, "r") as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise RuntimeError(
                f"Corrupt package member {bad_member} in "
                f"{package_path.name}"
            )
        manifest = json.loads(
            archive.read("PACKAGE_MANIFEST.json")
        )
    entries = {
        item["filename"]: item["sha256"]
        for item in manifest["files"]
    }
    verified_artifacts = []
    for artifact in specification["artifacts"]:
        if artifact not in entries:
            raise RuntimeError(
                f"{artifact} absent from {package_path.name} manifest."
            )
        if entries[artifact] != DIRECT_SOURCE_HASHES[artifact]:
            raise RuntimeError(
                f"Package manifest mismatch for {artifact}."
            )
        if sha256(ROOT / artifact) != entries[artifact]:
            raise RuntimeError(
                f"Direct artifact differs from package manifest: {artifact}"
            )
        verified_artifacts.append({
            "artifact": artifact,
            "sha256": entries[artifact],
            "verified": True,
        })
    package_verification.append({
        "source_task": source_task,
        "package": package_path.name,
        "package_sha256": sha256(package_path),
        "package_status": manifest.get("status", ""),
        "review_status": manifest.get("review_status", ""),
        "artifacts": verified_artifacts,
    })

baseline = json.loads(
    (ROOT / "fase0_tarea15_reproduced_baseline.json").read_text(
        encoding="utf-8"
    )
)
f1_prereg = json.loads(
    (
        ROOT / "fase1_tarea01_core_benchmark_preregistration.json"
    ).read_text(encoding="utf-8")
)
f16_audit = json.loads(
    (ROOT / "fase1_tarea06_analysis_audit.json").read_text(
        encoding="utf-8"
    )
)
f17_audit = json.loads(
    (
        ROOT / "fase1_tarea07_short_window_diagnostic_audit.json"
    ).read_text(encoding="utf-8")
)
f18_prereg = json.loads(
    (
        ROOT / "fase1_tarea08_nested_window_preregistration.json"
    ).read_text(encoding="utf-8")
)
f113_audit = json.loads(
    (ROOT / "fase1_tarea13_nested_analysis_audit.json").read_text(
        encoding="utf-8"
    )
)

# Cross-task chain verification for the two sources that predate mentor ZIPs.
if f1_prereg["baseline_reference"]["sha256"] != (
    DIRECT_SOURCE_HASHES["fase0_tarea15_reproduced_baseline.json"]
):
    raise RuntimeError("F1.1 does not reference the frozen F0.15 hash.")
if f1_prereg["baseline_reference"]["verification_status"] != "VERIFIED":
    raise RuntimeError("F1.1 baseline reference was not verified.")
if f16_audit["input_hashes_pre"][
    "fase1_tarea01_core_benchmark_preregistration.json"
] != DIRECT_SOURCE_HASHES[
    "fase1_tarea01_core_benchmark_preregistration.json"
]:
    raise RuntimeError("F1.6 does not preserve the frozen F1.1 hash.")
if f16_audit["input_hashes_post"] != f16_audit["input_hashes_pre"]:
    raise RuntimeError("F1.6 inputs changed during its analysis.")

if baseline["status"] != "EMPIRICALLY_REPRODUCED_BASELINE":
    raise RuntimeError("Unexpected F0.15 baseline status.")
if f1_prereg["preregistration_status"] != (
    "FROZEN_BEFORE_SYNTHETIC_GENERATION"
):
    raise RuntimeError("Unexpected F1.1 preregistration status.")
if f16_audit["execution_status"] != "CORE_BENCHMARK_ANALYSIS_COMPLETE":
    raise RuntimeError("Unexpected F1.6 status.")
if f17_audit["execution_status"] != (
    "SHORT_WINDOW_FAILURE_DIAGNOSTIC_COMPLETE"
):
    raise RuntimeError("Unexpected F1.7 status.")
if f18_prereg["preregistration_status"] != (
    "FROZEN_BEFORE_SERIES_GENERATION"
):
    raise RuntimeError("Unexpected F1.8 status.")
if f113_audit["analysis_conclusion"] != (
    "NESTED_SUPPORT_HYPOTHESIS_MIXED"
):
    raise RuntimeError("Unexpected F1.13 conclusion.")

H = DIRECT_SOURCE_HASHES
ledger_rows = [
    {
        "claim_id": "C001",
        "domain": "observational_baseline",
        "claim_text":
            "Cinco detecciones QPP publicadas fueron reproducidas con el "
            "baseline observacional congelado.",
        "evidence_class": "OBSERVATIONAL_REPRODUCTION",
        "source_task": "F0.15",
        "source_artifact": "fase0_tarea15_reproduced_baseline.json",
        "source_sha256":
            H["fase0_tarea15_reproduced_baseline.json"],
        "source_location":
            "validated_events.published_qpp_reproduced",
        "population": "detecciones publicadas examinadas",
        "numerator": 5,
        "denominator": 5,
        "estimate": "5 reproducciones estables",
        "uncertainty_or_dispersion":
            "10/10 seeds por detección en la cohorte congelada",
        "scope":
            "Solo las cinco detecciones TESS examinadas con el baseline "
            "efectivo; no las 61 detecciones del catálogo.",
        "supported_interpretation":
            "El protocolo congelado reproduce la decisión publicada en "
            "estas cinco observaciones.",
        "prohibited_interpretation":
            "AFINO está validado para la población TESS o se reprodujo el "
            "pipeline completo de los autores.",
        "status": "SUPPORTED",
    },
    {
        "claim_id": "C002",
        "domain": "observational_baseline",
        "claim_text":
            "Los cinco eventos observacionales emparejados no seleccionados "
            "se conservaron como no seleccionados.",
        "evidence_class": "OBSERVATIONAL_REPRODUCTION",
        "source_task": "F0.15",
        "source_artifact": "fase0_tarea15_reproduced_baseline.json",
        "source_sha256":
            H["fase0_tarea15_reproduced_baseline.json"],
        "source_location":
            "validated_events.matched_not_selected_retained",
        "population": "controles observacionales emparejados",
        "numerator": 5,
        "denominator": 5,
        "estimate": "5 controles retenidos",
        "uncertainty_or_dispersion": "0/10 seeds seleccionadas por control",
        "scope":
            "Cinco eventos emparejados pertenecientes a cinco TIC; no una "
            "muestra poblacional de no detecciones.",
        "supported_interpretation":
            "El baseline preserva la clasificación del catálogo en estos "
            "controles emparejados.",
        "prohibited_interpretation":
            "Especificidad observacional o tasa observacional de falsos "
            "positivos.",
        "status": "SUPPORTED",
    },
    {
        "claim_id": "C003",
        "domain": "physical_truth",
        "claim_text":
            "La reproducción observacional no establece ground truth físico "
            "independiente para QPP.",
        "evidence_class": "PHYSICAL_INTERPRETATION_NOT_ESTABLISHED",
        "source_task": "F0.15",
        "source_artifact": "fase0_tarea15_reproduced_baseline.json",
        "source_sha256":
            H["fase0_tarea15_reproduced_baseline.json"],
        "source_location":
            "numerical_risks.NO_OBSERVATIONAL_GROUND_TRUTH",
        "population": "diez observaciones congeladas",
        "numerator": "",
        "denominator": "",
        "estimate": "no establecido",
        "uncertainty_or_dispersion": "UNRESOLVED",
        "scope":
            "Las etiquetas son resultados del catálogo, no verificación "
            "física independiente.",
        "supported_interpretation":
            "Se reproduce una clasificación publicada.",
        "prohibited_interpretation":
            "Las cinco detecciones contienen QPP físicas demostradas y los "
            "controles no las contienen.",
        "status": "NOT_ESTABLISHED",
    },
    {
        "claim_id": "C004",
        "domain": "observational_scope",
        "claim_text":
            "El baseline observacional es una reproducción efectiva, no una "
            "reconstrucción documental completa ni una estimación de "
            "rendimiento poblacional.",
        "evidence_class": "METHOD_CONSTRAINT",
        "source_task": "F0.15",
        "source_artifact": "fase0_tarea15_reproduced_baseline.json",
        "source_sha256":
            H["fase0_tarea15_reproduced_baseline.json"],
        "source_location": "scope_statement",
        "population": "protocolo observacional congelado",
        "numerator": "",
        "denominator": "",
        "estimate": "alcance limitado",
        "uncertainty_or_dispersion":
            "paper_reproduction_status=UNRESOLVED",
        "scope":
            "Baseline identificado empíricamente para diez observaciones.",
        "supported_interpretation":
            "Existe un protocolo reproducible apto para pruebas de robustez "
            "sobre la misma cohorte.",
        "prohibited_interpretation":
            "Equivalencia documental con la capa TESS privada.",
        "status": "SUPPORTED_WITH_LIMITATION",
    },
    {
        "claim_id": "C005",
        "domain": "synthetic_core_null",
        "claim_text":
            "El benchmark sintético principal produjo 0/480 selecciones "
            "bajo su nulo construido.",
        "evidence_class": "SYNTHETIC_GROUND_TRUTH",
        "source_task": "F1.6",
        "source_artifact": "fase1_tarea06_analysis_audit.json",
        "source_sha256": H["fase1_tarea06_analysis_audit.json"],
        "source_location":
            "descriptive_results.null_selected/null_planned",
        "population": "realizaciones nulas sintéticas primarias",
        "numerator": 0,
        "denominator": 480,
        "estimate": "synthetic false selection 0/480",
        "uncertainty_or_dispersion":
            "Cada condición nula: 0/40; Wilson descriptivo superior 8,8 %",
        "scope":
            "Generador estacionario congelado, ruido rojo, cadencia 20 s y "
            "protocolo AFINO prerregistrado.",
        "supported_interpretation":
            "No hubo synthetic false selection en este nulo y diseño.",
        "prohibited_interpretation":
            "Tasa observacional de falsos positivos igual a cero.",
        "status": "SUPPORTED",
    },
    {
        "claim_id": "C006",
        "domain": "synthetic_core_positive",
        "claim_text":
            "La detección positiva sintética estuvo fuertemente "
            "estratificada por N, periodo, ruido y amplitud.",
        "evidence_class": "SYNTHETIC_GROUND_TRUTH",
        "source_task": "F1.6",
        "source_artifact": "fase1_tarea06_condition_summary.csv",
        "source_sha256": H["fase1_tarea06_condition_summary.csv"],
        "source_location":
            "99 filas ground_truth=STATIONARY_QPP_PRESENT",
        "population": "99 condiciones positivas sintéticas",
        "numerator": 21,
        "denominator": 99,
        "estimate":
            "21 condiciones con alguna selección; 78 con 0/40; rango "
            "0–100 %",
        "uncertainty_or_dispersion":
            "Mediana por condición 0 %; estratificación completa",
        "scope":
            "QPP estacionaria modulada por la envolvente y grid F1.1.",
        "supported_interpretation":
            "La detectabilidad depende de la condición sintética.",
        "prohibited_interpretation":
            "Sensibilidad global de AFINO o extrapolación a curvas reales.",
        "status": "SUPPORTED",
    },
    {
        "claim_id": "C007",
        "domain": "synthetic_short_windows",
        "claim_text":
            "N=15 y N=30 tuvieron 0/40 selecciones en todas sus condiciones "
            "positivas del benchmark principal.",
        "evidence_class": "SYNTHETIC_GROUND_TRUTH",
        "source_task": "F1.6",
        "source_artifact": "fase1_tarea06_condition_summary.csv",
        "source_sha256": H["fase1_tarea06_condition_summary.csv"],
        "source_location":
            "filas positivas con n_samples en {15,30}; n_selected=0",
        "population": "condiciones positivas N=15 y N=30",
        "numerator": 0,
        "denominator": "40 por condición",
        "estimate": "0/40 en cada condición",
        "uncertainty_or_dispersion":
            "Sin categoría global de éxito prerregistrada",
        "scope":
            "Ventanas de 280 y 580 s en el generador principal.",
        "supported_interpretation":
            "El protocolo no seleccionó M1 en las condiciones cortas "
            "probadas.",
        "prohibited_interpretation":
            "AFINO nunca puede detectar QPP en observaciones cortas.",
        "status": "SUPPORTED",
    },
    {
        "claim_id": "C008",
        "domain": "synthetic_core_amplitude",
        "claim_text":
            "Aumentar la amplitud fue no decreciente en los 33 estratos "
            "completos del benchmark principal.",
        "evidence_class": "SYNTHETIC_GROUND_TRUTH",
        "source_task": "F1.6",
        "source_artifact": "fase1_tarea06_core_benchmark_analysis.md",
        "source_sha256":
            H["fase1_tarea06_core_benchmark_analysis.md"],
        "source_location": "§3, párrafo de contrastes de amplitud",
        "population": "33 estratos completos (N, P, alpha)",
        "numerator": 33,
        "denominator": 33,
        "estimate":
            "28 contrastes positivos, 71 cero y 0 negativos",
        "uncertainty_or_dispersion":
            "Solo 4/33 estratos aumentaron estrictamente en ambos pasos",
        "scope": "Amplitudes q=0,01, 0,02 y 0,04 emparejadas.",
        "supported_interpretation":
            "Mayor q no redujo la selección dentro de los pares sintéticos.",
        "prohibited_interpretation":
            "Relación causal general o monotonicidad en datos reales.",
        "status": "SUPPORTED",
    },
    {
        "claim_id": "C009",
        "domain": "numerical_stability_core",
        "claim_text":
            "La decisión fue estable frente a la seed externa en F1.6, "
            "pero M2 mostró múltiples soluciones en 97/111 condiciones.",
        "evidence_class": "NUMERICAL_DIAGNOSTIC",
        "source_task": "F1.6",
        "source_artifact": "fase1_tarea06_analysis_audit.json",
        "source_sha256": H["fase1_tarea06_analysis_audit.json"],
        "source_location":
            "descriptive_results.optimizer_conditions_with_decision_change "
            "y m2_multiple_solution_conditions",
        "population": "111 condiciones, seeds externas 0–9",
        "numerator": 97,
        "denominator": 111,
        "estimate":
            "0 condiciones con cambio de decisión; 97 con rango M2>0,001",
        "uncertainty_or_dispersion":
            "Máximo rango M2 documentado: 4,542837",
        "scope": "Estabilidad de clasificación y dispersión de BIC.",
        "supported_interpretation":
            "La clasificación puede ser estable entre seeds.",
        "prohibited_interpretation":
            "La solución numérica u óptimo de M2 es único.",
        "status": "SUPPORTED_WITH_LIMITATION",
    },
    {
        "claim_id": "C010",
        "domain": "numerical_diagnostics_core",
        "claim_text":
            "Bounds y warnings fueron frecuentes en el benchmark principal, "
            "especialmente en M1 y M2.",
        "evidence_class": "NUMERICAL_DIAGNOSTIC",
        "source_task": "F1.6",
        "source_artifact": "fase1_tarea06_core_benchmark_analysis.md",
        "source_sha256":
            H["fase1_tarea06_core_benchmark_analysis.md"],
        "source_location": "§6 Bounds, warnings y fallos numéricos",
        "population": "4.440 llamadas primarias por modelo",
        "numerator": "",
        "denominator": 4440,
        "estimate":
            "bounds M0=471, M1=3135, M2=1747; warnings M2=2106 "
            "llamadas",
        "uncertainty_or_dispersion":
            "M1 bounds 10,6/70,6/39,3 % por modelo; warnings M2 47,4 %",
        "scope": "Diagnóstico numérico del benchmark sintético.",
        "supported_interpretation":
            "Deben acompañar la lectura de BIC y periodos.",
        "prohibited_interpretation":
            "Son causas demostradas de una selección o invalidan "
            "automáticamente una llamada OK.",
        "status": "SUPPORTED_WITH_LIMITATION",
    },
    {
        "claim_id": "C011",
        "domain": "short_window_failure",
        "claim_text":
            "En F1.7 ambas comparaciones fallaron en las 2.040 series "
            "cortas y M0 fue siempre la limitante inmediata.",
        "evidence_class": "SYNTHETIC_GROUND_TRUTH",
        "source_task": "F1.7",
        "source_artifact":
            "fase1_tarea07_short_window_diagnostic_audit.json",
        "source_sha256":
            H["fase1_tarea07_short_window_diagnostic_audit.json"],
        "source_location":
            "descriptive_results.threshold_failure_class_counts, "
            "bic_winner_counts y all_joint_margins_limited_by_m0",
        "population": "2.040 decisiones primarias N∈{15,30}",
        "numerator": 2040,
        "denominator": 2040,
        "estimate":
            "BOTH_COMPARISONS_FAILED y BIC winner M0 en 2.040/2.040",
        "uncertainty_or_dispersion":
            "Δ01 mediano -5,478 (N15) y -7,454 (N30)",
        "scope": "Ventanas cortas del benchmark principal.",
        "supported_interpretation":
            "La comparación M1 frente a M0 fue el cuello de botella "
            "inmediato.",
        "prohibited_interpretation":
            "M0 es causalmente responsable o el resultado prueba una "
            "limitación universal.",
        "status": "SUPPORTED",
    },
    {
        "claim_id": "C012",
        "domain": "short_window_amplitude",
        "claim_text":
            "Aumentar amplitud desplazó favorablemente los márgenes en F1.7 "
            "sin producir cruces de umbral.",
        "evidence_class": "SYNTHETIC_GROUND_TRUTH",
        "source_task": "F1.7",
        "source_artifact":
            "fase1_tarea07_short_window_amplitude_contrasts.csv",
        "source_sha256":
            H["fase1_tarea07_short_window_amplitude_contrasts.csv"],
        "source_location":
            "45 filas; median_change_joint_margin>0 y todos los campos "
            "threshold_crossing_count=0",
        "population": "45 contrastes emparejados de amplitud",
        "numerator": 45,
        "denominator": 45,
        "estimate":
            "45/45 cambio favorable en Δ01 y joint margin; 40/45 en Δ21",
        "uncertainty_or_dispersion":
            "0 cruces y 0 cambios de ganador BIC",
        "scope": "N=15 y N=30, amplitudes emparejadas.",
        "supported_interpretation":
            "La amplitud mueve la evidencia en dirección favorable.",
        "prohibited_interpretation":
            "Existe una categoría posterior de casi detección.",
        "status": "SUPPORTED",
    },
    {
        "claim_id": "C013",
        "domain": "short_window_length",
        "claim_text":
            "N=30 no se aproximó uniformemente más a los umbrales que N=15.",
        "evidence_class": "METHOD_CONSTRAINT",
        "source_task": "F1.7",
        "source_artifact":
            "fase1_tarea07_short_window_diagnostic_audit.json",
        "source_sha256":
            H["fase1_tarea07_short_window_diagnostic_audit.json"],
        "source_location":
            "descriptive_results.common_strata_n15_closer/"
            "common_strata_n30_closer",
        "population": "18 estratos comunes N15–N30",
        "numerator": 17,
        "denominator": 18,
        "estimate":
            "N15 menos negativo en 17 estratos; N30 en 1",
        "uncertainty_or_dispersion": "Comparación descriptiva emparejada",
        "scope": "Periodos comunes de las ventanas cortas.",
        "supported_interpretation":
            "Más duración no garantizó mayor proximidad al umbral.",
        "prohibited_interpretation":
            "Extender ventanas empeora causalmente la detección.",
        "status": "SUPPORTED_WITH_LIMITATION",
    },
    {
        "claim_id": "C014",
        "domain": "nested_design_scope",
        "claim_text":
            "F1.8 prerregistró el efecto total de extender prefijos, no un "
            "efecto causal puro del número de bins.",
        "evidence_class": "METHOD_CONSTRAINT",
        "source_task": "F1.8",
        "source_artifact":
            "fase1_tarea08_nested_window_preregistration.json",
        "source_sha256":
            H["fase1_tarea08_nested_window_preregistration.json"],
        "source_location":
            "interpretation_limits y paired_trajectory_analysis",
        "population": "360 trayectorias anidadas prerregistradas",
        "numerator": "",
        "denominator": "",
        "estimate": "restricción causal prerregistrada",
        "uncertainty_or_dispersion":
            "Cambian prefijo, ruido, normalización, Hann y grid FFT",
        "scope": "Benchmark anidado padre–prefijos.",
        "supported_interpretation":
            "Se evalúa el efecto total de observar una ventana más extensa.",
        "prohibited_interpretation":
            "Los cambios son causados exclusivamente por el número de bins.",
        "status": "SUPPORTED",
    },
    {
        "claim_id": "C015",
        "domain": "nested_null",
        "claim_text":
            "El benchmark anidado produjo dos synthetic false selections "
            "entre 720 decisiones nulas primarias.",
        "evidence_class": "SYNTHETIC_GROUND_TRUTH",
        "source_task": "F1.13",
        "source_artifact": "fase1_tarea13_nested_analysis_audit.json",
        "source_sha256":
            H["fase1_tarea13_nested_analysis_audit.json"],
        "source_location":
            "selection_by_n.null_synthetic_false_selection",
        "population": "720 decisiones nulas anidadas",
        "numerator": 2,
        "denominator": 720,
        "estimate": "synthetic false selection 2/720",
        "uncertainty_or_dispersion":
            "Una en N=60 y una en N=120; 2/120 trayectorias alguna vez",
        "scope": "Nulo sintético del benchmark anidado.",
        "supported_interpretation":
            "Hubo dos selecciones bajo el nulo construido.",
        "prohibited_interpretation":
            "Tasa observacional de falsos positivos.",
        "status": "SUPPORTED",
    },
    {
        "claim_id": "C016",
        "domain": "nested_positive",
        "claim_text":
            "Solo cuatro de 1.440 decisiones positivas anidadas fueron "
            "seleccionadas.",
        "evidence_class": "SYNTHETIC_GROUND_TRUTH",
        "source_task": "F1.13",
        "source_artifact": "fase1_tarea13_nested_analysis_audit.json",
        "source_sha256":
            H["fase1_tarea13_nested_analysis_audit.json"],
        "source_location":
            "selection_by_n.positive y "
            "period_recovery.selected_execution_count",
        "population": "1.440 decisiones positivas anidadas",
        "numerator": 4,
        "denominator": 1440,
        "estimate": "4 selecciones",
        "uncertainty_or_dispersion":
            "2 en N=60, 2 en N=120; 0 en las demás longitudes",
        "scope": "P=50/80 s, q=0,04 y alpha 0/1/2.",
        "supported_interpretation":
            "La selección fue muy escasa en este diseño anidado.",
        "prohibited_interpretation":
            "Sensibilidad observacional o incapacidad general de AFINO.",
        "status": "SUPPORTED",
    },
    {
        "claim_id": "C017",
        "domain": "nested_support_contrast",
        "claim_text":
            "C_support fue negativo en 959/1.200 transiciones positivas.",
        "evidence_class": "SYNTHETIC_GROUND_TRUTH",
        "source_task": "F1.13",
        "source_artifact": "fase1_tarea13_nested_analysis_audit.json",
        "source_sha256":
            H["fase1_tarea13_nested_analysis_audit.json"],
        "source_location":
            "support_hypothesis_contrast.overall",
        "population": "1.200 transiciones positivas anidadas",
        "numerator": 959,
        "denominator": 1200,
        "estimate":
            "mediana -0,744515; 241 positivas, 0 cero, 959 negativas",
        "uncertainty_or_dispersion":
            "Q1=-1,162037; Q3=-0,167933",
        "scope": "Contraste prerregistrado ΔΔ01−ΔΔ21.",
        "supported_interpretation":
            "En la mayoría de transiciones mejoró más el margen frente a M2.",
        "prohibited_interpretation":
            "Efecto causal puro de bins o umbral global de éxito posterior.",
        "status": "SUPPORTED",
    },
    {
        "claim_id": "C018",
        "domain": "nested_threshold_crossings",
        "claim_text":
            "Hubo cuatro cruces conjuntos ascendentes y dos descendentes en "
            "las transiciones positivas.",
        "evidence_class": "SYNTHETIC_GROUND_TRUTH",
        "source_task": "F1.13",
        "source_artifact": "fase1_tarea13_nested_analysis_audit.json",
        "source_sha256":
            H["fase1_tarea13_nested_analysis_audit.json"],
        "source_location": "crossings.positive",
        "population": "1.200 transiciones positivas",
        "numerator": "4 ascendentes; 2 descendentes",
        "denominator": 1200,
        "estimate": "False→True=4; True→False=2",
        "uncertainty_or_dispersion":
            "M0 arriba/abajo=6/3; M2 arriba/abajo=15/9",
        "scope": "Cambios adyacentes de prefijo.",
        "supported_interpretation":
            "La extensión puede crear y revertir selecciones en este diseño.",
        "prohibited_interpretation":
            "Selección monotónica o robusta por el mero aumento de N.",
        "status": "SUPPORTED",
    },
    {
        "claim_id": "C019",
        "domain": "nested_trajectory_monotonicity",
        "claim_text":
            "La selección anidada no fue monotónica.",
        "evidence_class": "SYNTHETIC_GROUND_TRUTH",
        "source_task": "F1.13",
        "source_artifact": "fase1_tarea13_nested_analysis_audit.json",
        "source_sha256":
            H["fase1_tarea13_nested_analysis_audit.json"],
        "source_location": "trajectory_sequences.positive",
        "population": "240 trayectorias positivas",
        "numerator": 4,
        "denominator": 240,
        "estimate":
            "236 secuencias 000000, 2 secuencias 000100 y 2 secuencias "
            "000001",
        "uncertainty_or_dispersion":
            "Las dos selecciones N60 revirtieron en N90",
        "scope": "Seis prefijos por trayectoria.",
        "supported_interpretation":
            "Existen reversiones y selecciones tardías aisladas.",
        "prohibited_interpretation":
            "Una selección temprana permanecerá activa al extender la curva.",
        "status": "SUPPORTED",
    },
    {
        "claim_id": "C020",
        "domain": "period_recovery",
        "claim_text":
            "La recuperación de periodo condicionada a selección es "
            "demasiado escasa para establecer una tendencia.",
        "evidence_class": "METHOD_CONSTRAINT",
        "source_task": "F1.13",
        "source_artifact": "fase1_tarea13_nested_analysis_report.md",
        "source_sha256":
            H["fase1_tarea13_nested_analysis_report.md"],
        "source_location": "§ Periodo formal y selección",
        "population": "cuatro decisiones positivas seleccionadas",
        "numerator": 4,
        "denominator": 1440,
        "estimate": "una observación por cada estrato seleccionado",
        "uncertainty_or_dispersion":
            "Errores firmados: +17,251; -12,154; +11,108; -18,625 s",
        "scope": "Periodo condicionado a la doble selección BIC.",
        "supported_interpretation":
            "Debe separarse clasificación de caracterización del periodo.",
        "prohibited_interpretation":
            "La extensión mejora o empeora robustamente el periodo "
            "recuperado.",
        "status": "LIMITATION_ESTABLISHED",
    },
    {
        "claim_id": "C021",
        "domain": "nested_optimizer_stability",
        "claim_text":
            "No hubo discordancia de decisión en F1.13, pero las 540 "
            "decisiones del subconjunto de estabilidad fueron no selecciones.",
        "evidence_class": "NUMERICAL_DIAGNOSTIC",
        "source_task": "F1.13",
        "source_artifact":
            "fase1_tarea13_optimizer_stability_summary.csv",
        "source_sha256":
            H["fase1_tarea13_optimizer_stability_summary.csv"],
        "source_location":
            "54 filas; decision_sequence=0000000000",
        "population": "54 condiciones × 10 seeds externas",
        "numerator": 0,
        "denominator": 54,
        "estimate":
            "0 condiciones discordantes; selected_seed_count=0 en 54/54",
        "uncertainty_or_dispersion":
            "El subconjunto no contiene decisiones positivas",
        "scope": "data_seed=0 por condición.",
        "supported_interpretation":
            "La no selección fue estable frente a la seed en este "
            "subconjunto.",
        "prohibited_interpretation":
            "La estabilidad fue probada para decisiones positivas anidadas.",
        "status": "SUPPORTED_WITH_LIMITATION",
    },
    {
        "claim_id": "C022",
        "domain": "nested_m2_multiplicity",
        "claim_text":
            "M2 presentó múltiples soluciones según el criterio congelado "
            "en 38/54 condiciones de F1.13.",
        "evidence_class": "NUMERICAL_DIAGNOSTIC",
        "source_task": "F1.13",
        "source_artifact": "fase1_tarea13_nested_analysis_audit.json",
        "source_sha256":
            H["fase1_tarea13_nested_analysis_audit.json"],
        "source_location":
            "optimizer_stability.m2_multiple_solution_flag_count",
        "population": "54 condiciones de estabilidad",
        "numerator": 38,
        "denominator": 54,
        "estimate": "bic_range_m2>0,001 en 38 condiciones",
        "uncertainty_or_dispersion":
            "Decisión estable en las 54 condiciones",
        "scope": "Criterio operativo de multiplicidad por BIC.",
        "supported_interpretation":
            "stable classification ≠ unique numerical optimum",
        "prohibited_interpretation":
            "M2 tiene una solución numérica o física única.",
        "status": "SUPPORTED_WITH_LIMITATION",
    },
    {
        "claim_id": "C023",
        "domain": "numerical_causality",
        "claim_text":
            "Warnings y bounds son diagnósticos y no causas demostradas de "
            "los cambios de selección.",
        "evidence_class": "NUMERICAL_DIAGNOSTIC",
        "source_task": "F1.13",
        "source_artifact":
            "fase1_tarea13_model_diagnostics_by_n.csv",
        "source_sha256":
            H["fase1_tarea13_model_diagnostics_by_n.csv"],
        "source_location":
            "18 filas por n_samples y model_id",
        "population": "6.480 llamadas primarias del benchmark anidado",
        "numerator": "",
        "denominator": 6480,
        "estimate":
            "M2 warning rate 12,8 % en N15 y 93,1 % en N120; bounds "
            "frecuentes",
        "uncertainty_or_dispersion": "Estratificado por N y modelo",
        "scope": "Control numérico descriptivo.",
        "supported_interpretation":
            "Deben reportarse en la fase observacional.",
        "prohibited_interpretation":
            "Explican causalmente una selección o no selección.",
        "status": "SUPPORTED_WITH_LIMITATION",
    },
    {
        "claim_id": "C024",
        "domain": "synthetic_to_observational_scope",
        "claim_text":
            "Los resultados sintéticos no estiman rendimiento observacional.",
        "evidence_class": "PHYSICAL_INTERPRETATION_NOT_ESTABLISHED",
        "source_task": "F1.1/F1.6",
        "source_artifact":
            "fase1_tarea01_core_benchmark_preregistration.json",
        "source_sha256":
            H["fase1_tarea01_core_benchmark_preregistration.json"],
        "source_location": "ground_truth.interpretation_limit",
        "population": "benchmarks sintéticos F1.1–F1.13",
        "numerator": "",
        "denominator": "",
        "estimate": "no estimado",
        "uncertainty_or_dispersion":
            "Ground truth conocido solo por construcción",
        "scope": "Simulaciones estacionarias congeladas.",
        "supported_interpretation":
            "Permiten evaluar comportamiento bajo condiciones conocidas.",
        "prohibited_interpretation":
            "Sensibilidad, especificidad o falsos positivos observacionales.",
        "status": "NOT_ESTABLISHED",
    },
    {
        "claim_id": "C025",
        "domain": "unmodeled_observational_complexity",
        "claim_text":
            "No se han estudiado todavía damping adicional, gaps, muestreo "
            "irregular ni alternativas observacionales de detrending.",
        "evidence_class": "METHOD_CONSTRAINT",
        "source_task": "F1.1",
        "source_artifact":
            "fase1_tarea01_core_benchmark_preregistration.json",
        "source_sha256":
            H["fase1_tarea01_core_benchmark_preregistration.json"],
        "source_location": "module_exclusions",
        "population": "dominio no cubierto por Fase 1",
        "numerator": "",
        "denominator": "",
        "estimate": "no estudiado",
        "uncertainty_or_dispersion":
            "Exclusiones explícitas antes de generar resultados",
        "scope": "Robustez observacional futura.",
        "supported_interpretation":
            "Estas dimensiones requieren controles prerregistrados.",
        "prohibited_interpretation":
            "Los resultados actuales son robustos a estas perturbaciones.",
        "status": "OPEN",
    },
    {
        "claim_id": "C026",
        "domain": "nested_causal_scope",
        "claim_text":
            "No se ha demostrado un efecto causal puro del número de bins.",
        "evidence_class": "PHYSICAL_INTERPRETATION_NOT_ESTABLISHED",
        "source_task": "F1.8/F1.13",
        "source_artifact": "fase1_tarea13_nested_analysis_report.md",
        "source_sha256":
            H["fase1_tarea13_nested_analysis_report.md"],
        "source_location": "§ Interpretación",
        "population": "1.800 transiciones anidadas",
        "numerator": "",
        "denominator": "",
        "estimate": "causalidad no establecida",
        "uncertainty_or_dispersion":
            "Cambian cola, ruido del prefijo, normalización, Hann y FFT",
        "scope": "Efecto total de extender la observación.",
        "supported_interpretation":
            "Se describen cambios asociados a la extensión del prefijo.",
        "prohibited_interpretation":
            "Los bins adicionales causaron los cambios de BIC o selección.",
        "status": "NOT_ESTABLISHED",
    },
]

ledger_fields = [
    "claim_id",
    "domain",
    "claim_text",
    "evidence_class",
    "source_task",
    "source_artifact",
    "source_sha256",
    "source_location",
    "population",
    "numerator",
    "denominator",
    "estimate",
    "uncertainty_or_dispersion",
    "scope",
    "supported_interpretation",
    "prohibited_interpretation",
    "status",
]
write_csv(
    ROOT / "fase1_tarea14_phase1_evidence_ledger.csv",
    ledger_rows,
    ledger_fields,
)

requirements_rows = [
    {
        "requirement_id": "R001",
        "phase1_finding":
            "Una sola cadencia cambió la clasificación de calibración y "
            "F1.13 mostró reversiones al extender prefijos.",
        "risk_for_observational_analysis":
            "Dependencia de límites temporales y de la ventana exacta.",
        "required_phase2_control":
            "Perturbación de límites temporales alrededor de cada evento "
            "con reglas simétricas y congeladas.",
        "must_be_preregistered": True,
        "blocking_for_candidate_discovery": True,
        "rationale":
            "La robustez debe medirse en las observaciones conocidas antes "
            "de usar el método para descubrir eventos.",
    },
    {
        "requirement_id": "R002",
        "phase1_finding":
            "PDCSAP reprodujo más positivos que SAP en la validación "
            "observacional de Fase 0.",
        "risk_for_observational_analysis":
            "La clasificación puede depender del producto fotométrico.",
        "required_phase2_control":
            "Comparación PDCSAP frente a SAP manteniendo iguales ventana, "
            "QUALITY, semillas y protocolo.",
        "must_be_preregistered": True,
        "blocking_for_candidate_discovery": True,
        "rationale":
            "El flujo primario no puede elegirse después de observar la "
            "clasificación.",
    },
    {
        "requirement_id": "R003",
        "phase1_finding":
            "La política QUALITY puede eliminar el pico y crear muestreo "
            "irregular.",
        "risk_for_observational_analysis":
            "Cambios de decisión inducidos por filtrado y pérdida de "
            "cadencias.",
        "required_phase2_control":
            "Tratamiento explícito de QUALITY, incluyendo finite_all y una "
            "política q0 predefinida con registro de cadencias eliminadas.",
        "must_be_preregistered": True,
        "blocking_for_candidate_discovery": True,
        "rationale":
            "Evita seleccionar retrospectivamente la política que conserva "
            "la detección.",
    },
    {
        "requirement_id": "R004",
        "phase1_finding":
            "F1.1 excluyó gaps y muestreo irregular; las variantes q0 reales "
            "sí pueden contenerlos.",
        "risk_for_observational_analysis":
            "FFT y likelihood pueden recibir tiempos no uniformes sin que el "
            "protocolo actual modele esa irregularidad.",
        "required_phase2_control":
            "Auditoría de gaps, regularidad temporal y criterio de "
            "admisibilidad o representación alternativa.",
        "must_be_preregistered": True,
        "blocking_for_candidate_discovery": True,
        "rationale":
            "La entrada observacional debe cumplir un contrato temporal "
            "explícito.",
    },
    {
        "requirement_id": "R005",
        "phase1_finding":
            "La Fase 1 no estudió alternativas de detrending ni de "
            "representación espectral.",
        "risk_for_observational_analysis":
            "La selección puede depender del preprocesamiento y de la "
            "competencia entre modelos de fondo.",
        "required_phase2_control":
            "Comparar el baseline sin detrending externo con alternativas "
            "observacionales definidas antes de ver resultados.",
        "must_be_preregistered": True,
        "blocking_for_candidate_discovery": True,
        "rationale":
            "Las alternativas deben ser pruebas de robustez, no ajustes para "
            "obtener selección.",
    },
    {
        "requirement_id": "R006",
        "phase1_finding":
            "Las decisiones fueron estables en los subconjuntos probados, "
            "pero M2 mostró soluciones múltiples.",
        "risk_for_observational_analysis":
            "Una seed única puede ocultar dispersión numérica y soluciones "
            "competidoras.",
        "required_phase2_control":
            "Seed externa del optimizador congelada y conjunto de seeds de "
            "estabilidad separado del análisis primario.",
        "must_be_preregistered": True,
        "blocking_for_candidate_discovery": True,
        "rationale":
            "stable classification ≠ unique numerical optimum",
    },
    {
        "requirement_id": "R007",
        "phase1_finding":
            "Warnings y bounds fueron frecuentes y variaron por modelo y N.",
        "risk_for_observational_analysis":
            "Resultados formalmente OK pueden estar cerca de límites o "
            "mostrar inestabilidad numérica.",
        "required_phase2_control":
            "Registrar warnings y bounds por modelo, seed y variante sin "
            "usarlos como exclusión retrospectiva.",
        "must_be_preregistered": True,
        "blocking_for_candidate_discovery": True,
        "rationale":
            "Los diagnósticos deben acompañar la clasificación sin "
            "convertirse en reglas post hoc.",
    },
    {
        "requirement_id": "R008",
        "phase1_finding":
            "La recuperación condicionada a selección y el centro formal de "
            "M1 tienen poblaciones y precisión distintas.",
        "risk_for_observational_analysis":
            "Confundir clasificación estable con periodo físicamente robusto.",
        "required_phase2_control":
            "Separar robustez de clasificación, estabilidad de BIC y "
            "robustez del periodo recuperado.",
        "must_be_preregistered": True,
        "blocking_for_candidate_discovery": True,
        "rationale":
            "La presencia de una selección no garantiza caracterización "
            "estable del periodo.",
    },
    {
        "requirement_id": "R009",
        "phase1_finding":
            "La evidencia observacional procede de cinco detecciones y cinco "
            "controles ya congelados.",
        "risk_for_observational_analysis":
            "Sesgo de selección y expansión retrospectiva de la cohorte.",
        "required_phase2_control":
            "Limitar la fase siguiente a las diez observaciones congeladas y "
            "mantener bloqueada la búsqueda de candidatos.",
        "must_be_preregistered": True,
        "blocking_for_candidate_discovery": True,
        "rationale":
            "Primero debe evaluarse robustez sobre selecciones conocidas.",
    },
    {
        "requirement_id": "R010",
        "phase1_finding":
            "No existe ground truth físico observacional ni rendimiento "
            "poblacional estimado.",
        "risk_for_observational_analysis":
            "Reetiquetar concordancia con el catálogo como verdad física, "
            "sensibilidad o especificidad.",
        "required_phase2_control":
            "Definir outcomes como conservación o cambio de la clasificación "
            "publicada bajo perturbaciones, no como verdad física.",
        "must_be_preregistered": True,
        "blocking_for_candidate_discovery": True,
        "rationale":
            "La fase de robustez estudia estabilidad de resultados conocidos, "
            "no validez física ni rendimiento de descubrimiento.",
    },
]

requirements_fields = [
    "requirement_id",
    "phase1_finding",
    "risk_for_observational_analysis",
    "required_phase2_control",
    "must_be_preregistered",
    "blocking_for_candidate_discovery",
    "rationale",
]
write_csv(
    ROOT / "fase1_tarea14_phase2_entry_requirements.csv",
    requirements_rows,
    requirements_fields,
)

decision = {
    "decision":
        "PHASE1_COMPLETE_PROCEED_TO_OBSERVATIONAL_ROBUSTNESS_WITH_LIMITATIONS",
    "decision_basis": [
        "El baseline observacional reproduce cinco detecciones publicadas y "
        "conserva cinco controles emparejados.",
        "La Fase 1 identificó límites sintéticos y numéricos concretos que "
        "pueden convertirse en controles observacionales prerregistrados.",
        "No existe una inconsistencia documental que obligue a repetir el "
        "benchmark sintético antes de estudiar las diez observaciones "
        "congeladas.",
        "La autorización se limita a robustez de clasificaciones conocidas y "
        "no implica validación, rendimiento poblacional ni verdad física.",
    ],
    "supporting_claim_ids": [
        "C001", "C002", "C004", "C005", "C006", "C011",
        "C012", "C018",
    ],
    "limiting_claim_ids": [
        "C003", "C009", "C010", "C013", "C015", "C016",
        "C017", "C019", "C020", "C021", "C022", "C023",
        "C024", "C025", "C026",
    ],
    "unresolved_questions": [
        "Robustez de cada una de las diez observaciones a perturbaciones de "
        "límites temporales.",
        "Dependencia observacional PDCSAP frente a SAP.",
        "Dependencia de la política QUALITY y de gaps o muestreo irregular.",
        "Dependencia de detrending o representación espectral alternativa.",
        "Estabilidad conjunta de clasificación, BIC y periodo entre seeds.",
        "Unicidad numérica de M2.",
        "Ground truth físico independiente para QPP.",
        "Sensibilidad, especificidad y tasas observacionales poblacionales.",
        "Adaptador TESS privado y política global exacta de los autores.",
    ],
    "permitted_next_phase":
        "Análisis prerregistrado de robustez de las cinco detecciones y cinco "
        "controles observacionales ya congelados, aplicando controles "
        "simétricos y sin ampliar la cohorte.",
    "prohibited_claims": [
        "AFINO está validado.",
        "Las detecciones reproducidas constituyen ground truth físico.",
        "Los controles demuestran ausencia física de QPP.",
        "Las tasas sintéticas son sensibilidad, especificidad o falsos "
        "positivos observacionales.",
        "El número de bins causó por sí solo los cambios observados.",
        "La estabilidad de clasificación demuestra un óptimo numérico único.",
        "La fase siguiente autoriza búsqueda de nuevos candidatos.",
    ],
    "candidate_discovery_allowed": False,
    "new_thresholds_added": False,
    "afino_executed": False,
}

(ROOT / "fase1_tarea14_phase1_decision.json").write_text(
    json.dumps(decision, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

report = """# Fase 1 — Tarea 1.14

## Síntesis, cierre de Fase 1 y puerta de entrada a robustez observacional

**Decisión:** `PHASE1_COMPLETE_PROCEED_TO_OBSERVATIONAL_ROBUSTNESS_WITH_LIMITATIONS`

La Fase 1 se cierra con una separación explícita entre cuatro planos de
evidencia: reproducción observacional, ground truth sintético, diagnóstico
numérico e interpretación física no establecida. Esta separación es esencial
porque los resultados responden preguntas diferentes. La reproducción muestra
que un protocolo público congelado puede recuperar determinadas
clasificaciones publicadas. Los benchmarks sintéticos muestran cómo se
comporta ese protocolo cuando la presencia o ausencia de una componente
periódica es conocida por construcción. Los warnings, bounds y variaciones
entre seeds informan sobre estabilidad numérica. Ninguno de estos planos
demuestra por sí solo la existencia física de QPP en una observación real.

## Evidencia observacional reproducida

El baseline `afino_public_tess_reproduction_v1` reprodujo cinco detecciones QPP
publicadas y conservó como no seleccionados cinco eventos emparejados. En los
positivos, la doble regla BIC permaneció activa en las diez seeds externas; en
los controles, permaneció inactiva. El valor de esta evidencia es operativo:
existe un procedimiento identificable, congelado por hashes y reproducible
sobre diez observaciones conocidas. Esto basta para formular pruebas de
robustez sobre la misma cohorte.

El alcance sigue siendo limitado. No se reprodujeron las 61 detecciones del
catálogo ni los 3.817 eventos no seleccionados, y el adaptador TESS privado de
los autores continúa sin estar disponible. La política global de QUALITY, el
uso global de PDCSAP, la configuración privada completa del optimizador y la
convergencia formal tampoco están resueltos. La concordancia con el catálogo
no equivale a reconstrucción documental completa ni permite calcular
sensibilidad o especificidad.

Tampoco existe ground truth físico observacional. Las cinco detecciones son
eventos etiquetados por el catálogo y los cinco controles son eventos que ese
catálogo no seleccionó. La afirmación autorizada es que el baseline reproduce
esas clasificaciones. Continúa prohibido afirmar que los positivos contienen
QPP físicamente demostradas o que los controles prueban su ausencia.

## Ground truth sintético y dominio de funcionamiento

F1.1 congeló un generador con nulos y QPP estacionarias conocidas por
construcción. En el benchmark principal, M1 no fue seleccionado en ninguna de
las 480 realizaciones nulas. Este resultado se denomina `synthetic false
selection 0/480`; no es una tasa observacional de falsos positivos.

Las condiciones positivas mostraron una estratificación fuerte. De 99
condiciones, 78 quedaron en 0/40 y 21 tuvieron alguna selección. Todas las
condiciones positivas con N=15 y N=30 quedaron en 0/40. La selección se
concentró en ventanas más largas, amplitudes mayores y periodos más cortos.
Dentro de los estratos emparejados, aumentar amplitud nunca redujo la tasa,
pero el resultado no define una sensibilidad global: depende del generador,
del grid y del protocolo concretos.

F1.7 descompuso específicamente las ventanas cortas. En las 2.040 decisiones
con N=15 o N=30 fallaron simultáneamente las comparaciones frente a M0 y M2.
M0 fue el ganador BIC y la limitante del margen conjunto en todos los casos.
Aumentar la amplitud desplazó favorablemente Δ01 y el margen conjunto en los
45 contrastes, pero no produjo ningún cruce de umbral ni cambio de ganador.
Además, N=30 no quedó uniformemente más cerca del umbral que N=15: N=15 tuvo
un margen menos negativo en 17 de los 18 estratos comunes. Por tanto, la
dificultad de las ventanas cortas no se resume en “faltan bins”; el balance de
likelihood y penalización frente a M0 permaneció desfavorable.

## Aporte y límites del benchmark anidado

F1.8 prerregistró extensiones padre–prefijo para estudiar el efecto total de
observar una porción temporal mayor. El benchmark no aisló causalmente el
número de bins: al extender el prefijo también cambian la cola observada, los
momentos del ruido, la normalización interna, la ventana de Hann y la
cuadrícula FFT.

F1.13 encontró dos synthetic false selections entre 720 decisiones nulas y
solo cuatro selecciones entre 1.440 decisiones positivas. El contraste
prerregistrado `C_support=ΔΔ01−ΔΔ21` fue negativo en 959 de 1.200
transiciones. En la mayoría de extensiones, la evidencia relativa frente a M2
aumentó más que la evidencia frente a M0; por ello, la parte principal de la
hipótesis de soporte temporal no quedó apoyada de forma dominante.

Sí aparecieron cruces conjuntos: cuatro ascendentes y dos descendentes. La
selección no fue monotónica. Dos trayectorias positivas se seleccionaron en
N=60 y revirtieron en N=90; otras dos aparecieron únicamente en N=120. Esto
aporta evidencia de sensibilidad a la ventana y justifica estudiar
perturbaciones temporales en las observaciones reales. No demuestra que
extender una observación mejore de forma general la clasificación.

La recuperación de periodo condicionada a selección quedó limitada a cuatro
casos, una observación por estrato seleccionado. Esa población es demasiado
pequeña para establecer una tendencia. El centro formal de M1 en ejecuciones
no seleccionadas debe permanecer separado del concepto de periodo recuperado.

## Estabilidad y no unicidad numérica

La clasificación no cambió entre seeds en las 111 condiciones del benchmark
principal ni en las 54 condiciones de estabilidad anidadas. Sin embargo, esta
estabilidad tiene límites. En F1.13, las 540 decisiones del subconjunto de
estabilidad fueron no selecciones; por tanto, no se probó estabilidad de
selecciones positivas anidadas. M2 superó el criterio de múltiples soluciones
en 97/111 condiciones del benchmark principal y en 38/54 condiciones
anidadas. Debe conservarse la formulación: `stable classification ≠ unique
numerical optimum`.

Los bounds de M1 y M2 y los warnings de M2 fueron frecuentes y variaron con la
longitud de la serie. Son diagnósticos que deben registrarse, no explicaciones
causales ni criterios post hoc para aceptar o descartar resultados.

## Puerta de entrada a la siguiente fase

Existe base suficiente para pasar a una fase de robustez observacional porque
hay diez observaciones ya congeladas, un baseline reproducible y riesgos
concretos identificados antes de ampliar la cohorte. No se requiere otro
benchmark sintético para decidir si esas diez clasificaciones sobreviven a
perturbaciones razonables. La decisión no valida AFINO y no autoriza
descubrimiento.

La siguiente fase deberá prerregistrar, como mínimo: perturbaciones de límites
temporales; PDCSAP frente a SAP; política QUALITY; gaps y muestreo irregular;
alternativas de detrending o representación espectral; seeds externas;
warnings y bounds por modelo; y separación entre robustez de clasificación y
periodo recuperado. Las variantes deberán aplicarse simétricamente a las cinco
detecciones y los cinco controles. Los outcomes serán conservación, pérdida o
cambio de la clasificación publicada bajo perturbaciones, no verdad física.

La búsqueda de nuevos candidatos permanece bloqueada. También continúan
prohibidas las afirmaciones de sensibilidad, especificidad, tasa observacional
de falsos positivos, ground truth físico y efecto causal puro del número de
bins. Una fase posterior podrá abordar descubrimiento únicamente tras un nuevo
prerregistro que defina población, selección, variantes, multiplicidad,
criterios de exclusión y separación entre confirmación y exploración.

## Conclusión

La Fase 1 ha cumplido su función: caracterizó el comportamiento del baseline
bajo ground truth sintético, identificó fallos de ventanas cortas, mostró
sensibilidad no monotónica a extensiones temporales y documentó límites
numéricos. La evidencia es suficiente para estudiar robustez de las diez
observaciones conocidas, pero insuficiente para presentar AFINO como validado
o para iniciar búsqueda de candidatos.

`PHASE1_COMPLETE_PROCEED_TO_OBSERVATIONAL_ROBUSTNESS_WITH_LIMITATIONS`
"""

report_word_count = len(
    re.findall(r"\b[\wÁÉÍÓÚÜÑáéíóúüñ]+\b", report)
)
if not (900 <= report_word_count <= 1300):
    raise RuntimeError(
        f"Report word count outside 900–1300: {report_word_count}"
    )

(ROOT / "fase1_tarea14_phase1_synthesis_report.md").write_text(
    report,
    encoding="utf-8",
)

source_hashes_after = {
    filename: sha256(ROOT / filename)
    for filename in DIRECT_SOURCE_HASHES
}
if source_hashes_after != source_hashes_before:
    raise RuntimeError("A normative source changed during F1.14.")

evidence_classes_present = sorted({
    row["evidence_class"] for row in ledger_rows
})
if evidence_classes_present != sorted(EVIDENCE_CLASSES):
    raise RuntimeError("Not all five evidence classes are represented.")

missing_source = [
    row["claim_id"] for row in ledger_rows
    if not row["source_artifact"] or not row["source_sha256"]
]
missing_scope = [
    row["claim_id"] for row in ledger_rows
    if not row["scope"]
]
missing_prohibited = [
    row["claim_id"] for row in ledger_rows
    if not row["prohibited_interpretation"]
]

audit = {
    "synthesis_status": "PHASE1_SYNTHESIS_COMPLETE",
    "source_hashes_verified": {
        "direct_artifacts_before": source_hashes_before,
        "direct_artifacts_after": source_hashes_after,
        "package_manifests": package_verification,
        "cross_task_chain": [
            {
                "source": "F0.15",
                "verification":
                    "Direct required hash plus F1.1 "
                    "baseline_reference.sha256",
                "verified": True,
            },
            {
                "source": "F1.1",
                "verification":
                    "Direct required hash plus F1.6 "
                    "input_hashes_pre/post",
                "verified": True,
            },
        ],
    },
    "ledger_row_count": len(ledger_rows),
    "evidence_classes_present": evidence_classes_present,
    "claims_with_missing_source": missing_source,
    "claims_with_missing_scope": missing_scope,
    "claims_with_prohibited_interpretation": missing_prohibited,
    "phase2_requirement_row_count": len(requirements_rows),
    "phase_decision": decision["decision"],
    "report_word_count": report_word_count,
    "incidents": [],
    "traceability_notes": [
        "F0.15 y F1.1 no disponían de un ZIP mentor independiente en el "
        "workspace. Sus hashes se verificaron directamente y mediante la "
        "cadena normativa F0.15→F1.1→F1.6.",
        "No se detectaron discrepancias entre audit JSON, CSV científicos, "
        "informes o manifiestos de paquete para las afirmaciones empleadas.",
    ],
    "confirmations": {
        "afino_executed": False,
        "new_curves_generated": False,
        "new_benchmark_statistics_computed": False,
        "observational_ground_truth_claimed": False,
        "synthetic_rates_relabelled_as_observational": False,
        "afino_validated_claimed": False,
        "new_selection_threshold_added": False,
        "candidate_discovery_authorized": False,
        "physical_qpp_truth_inferred": False,
    },
}

(ROOT / "fase1_tarea14_phase1_synthesis_audit.json").write_text(
    json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

# Final structural checks.
if not (15 <= len(ledger_rows) <= 30):
    raise RuntimeError("Evidence ledger row count outside 15–30.")
if not (8 <= len(requirements_rows) <= 15):
    raise RuntimeError("Entry requirement row count outside 8–15.")
if missing_source or missing_scope or missing_prohibited:
    raise RuntimeError("Evidence ledger contains incomplete traceability.")
if decision["candidate_discovery_allowed"]:
    raise RuntimeError("Candidate discovery must remain blocked.")
if decision["new_thresholds_added"]:
    raise RuntimeError("A new threshold was added.")
if decision["afino_executed"]:
    raise RuntimeError("AFINO execution incorrectly recorded.")

print("F1.14 phase synthesis complete")
print(f"decision: {decision['decision']}")
print(f"ledger_rows: {len(ledger_rows)}")
print(f"requirements_rows: {len(requirements_rows)}")
print(f"report_word_count: {report_word_count}")
print("source_hashes_verified: true")
print("candidate_discovery_allowed: false")
for name in OUTPUT_NAMES:
    print(f"{name}: {sha256(ROOT / name)}")
