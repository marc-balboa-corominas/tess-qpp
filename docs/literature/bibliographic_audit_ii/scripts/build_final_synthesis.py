from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

EXPECTED_INPUT_HASHES = {
    "docs/literature/bibliographic_audit_ii/screening/screening_manifest.json": "b8d53cc6f51cfbf33ba3fd5d32a5651c0db772842d9fdab678d70f0f15ef7dba",
    "docs/literature/bibliographic_audit_ii/extraction/extraction_manifest.json": "4de9ffac6ccd78e15690ab674c15af91529788fc7b05f63966f6fb79880b1581",
    "docs/literature/bibliographic_audit_ii/extraction/f3_overlap_reference.json": "1b6be4a17d23457d3164b23c4b16557467e84ae44bbb35df57064b7c9566639e",
}

HISTORICAL_HASH_CONTRACT = {'docs/literature/bibliographic_audit_ii/AUDIT_MATRIX.csv': 'ef1723c53d09f6fe95aa2f1f127d329b1a29ea389a9e75e4c77ec735ec4e10c5',
 'docs/literature/bibliographic_audit_ii/SEED_SOURCES.csv': '05690c0f57a684c77b681510e4b18dcde163848a6eabcad3a735b9a3bccd8838',
 'docs/literature/bibliographic_audit_ii/amendments/BAII_DESIGN_V1_1_0.md': 'ec076cc629ebc46c35253a1a0670023523700a0dc3c6b7f68baeb06f876ef514',
 'docs/literature/bibliographic_audit_ii/audit_preregistration.json': '64f182980f8494b2242a7743151441718ca8a50d177ceb6442b8e5540742ae84',
 'docs/literature/bibliographic_audit_ii/extraction/README.md': 'd518759133282379cfd0fad7d707874aeab8c30098071106754c0af57167713e',
 'docs/literature/bibliographic_audit_ii/extraction/SHA256SUMS.txt': '818c6e042fbacc1c8a64307d7ff190f4533fa3df34fdc2276cdd3c2ee9ee5c44',
 'docs/literature/bibliographic_audit_ii/extraction/SHA256SUMS_REFERENCE_FREEZE.txt': '5e938dd96b63a92607094cf9fa00b64113cf322db2f0ccad7be7f923f9e6632b',
 'docs/literature/bibliographic_audit_ii/extraction/extraction_evidence_log.csv': '2c90080fb8779fc38de4c7fdd8c8126de00f97e48f4655d6988e089fd7fbb55c',
 'docs/literature/bibliographic_audit_ii/extraction/extraction_manifest.json': '4de9ffac6ccd78e15690ab674c15af91529788fc7b05f63966f6fb79880b1581',
 'docs/literature/bibliographic_audit_ii/extraction/extraction_report.md': 'c8e0feb5c3ab2bb875f74aa23062e9b50b16b36bf2e75fcd03dcca3c2fe94b59',
 'docs/literature/bibliographic_audit_ii/extraction/f3_overlap_reference.json': '1b6be4a17d23457d3164b23c4b16557467e84ae44bbb35df57064b7c9566639e',
 'docs/literature/bibliographic_audit_ii/extraction/included_work_extraction.csv': 'a5c8b5ba13da94e01fdc18ed95bea2abf036e481c695415ae276e89eb4fa047c',
 'docs/literature/bibliographic_audit_ii/extraction/overlap_assessment.csv': '6585149e956f22060186a67750ccfa8402ee558a00b10c3341c3979480fbb768',
 'docs/literature/bibliographic_audit_ii/extraction/overlap_dimension_evidence.csv': '114ac1d5e330ad0beacd002ae913d3ad11a132ecf0b2142b6f14b3d48a315552',
 'docs/literature/bibliographic_audit_ii/extraction/source_access_log.csv': 'c3f67df0dbb2a2dd3c03f1de6ecac5873c3927f7c9d39a408a66c594d4107035',
 'docs/literature/bibliographic_audit_ii/protocol.md': '75b7d372c778364882047d859ad90598c8fd553cbb1e70ddfae39c3d35e21927',
 'docs/literature/bibliographic_audit_ii/retrieval/README.md': 'fe16746c3513066a3992cd51d2e9c241853c6005b5d766ca4ff5249be2c31d54',
 'docs/literature/bibliographic_audit_ii/retrieval/SHA256SUMS.txt': '4c54368647ef93b3b7b5694eb49651320665d048b3d43f7f354c490229ff0ef3',
 'docs/literature/bibliographic_audit_ii/retrieval/raw_hit_ledger.csv': '716c57663e90f4a7cc3f7d762620cbebe51a11d411ea10a97d9646a640b45dbd',
 'docs/literature/bibliographic_audit_ii/retrieval/retrieval_manifest.json': '819de2c50a2b8921e9e69c16e40e896ae387d39e73fefca084500ef25435c97e',
 'docs/literature/bibliographic_audit_ii/retrieval/search_execution_log.csv': '8778bc78a4bebde2751560807d6b990ebf971ff6acd3af76e32d6eb9453a4370',
 'docs/literature/bibliographic_audit_ii/screening/README.md': '194e9ff3c31b112ee194e027ff201bbebe70f7407c708d768938fc4335709048',
 'docs/literature/bibliographic_audit_ii/screening/SHA256SUMS.txt': '9fd5698e17b947953b60cdb96d46af3130086e8e79599b7f1057d629f73a464d',
 'docs/literature/bibliographic_audit_ii/screening/auto_work_candidates.csv': 'ffbb71847522361076c82dc24e16da94292f9016f20d47af249f0ee860e5f7c0',
 'docs/literature/bibliographic_audit_ii/screening/manual_adjudications.csv': '98ea1f5dd7f8815dd3599bf2b8db6661e731bc373971e0cf6555bc7f2d29a03b',
 'docs/literature/bibliographic_audit_ii/screening/raw_hit_to_work_map.csv': '2d9ac5f37507cbd3b9e79481fa74edf582fc5f44bcf942e7d890586dcceca55e',
 'docs/literature/bibliographic_audit_ii/screening/screened_works.csv': '143aa10bb942780e250f6b5cb9489acfa8bbc2a05b633624a4856d4d245533e2',
 'docs/literature/bibliographic_audit_ii/screening/screening_decision_log.csv': 'b80b2a01e488b4ebe7f4c833a58f192de5d55e216bdeb66b9e2ed896d2bc16cb',
 'docs/literature/bibliographic_audit_ii/screening/screening_manifest.json': 'b8d53cc6f51cfbf33ba3fd5d32a5651c0db772842d9fdab678d70f0f15ef7dba',
 'docs/literature/bibliographic_audit_ii/screening/screening_report.md': 'f63e3b1160bcf5f8d1da3fe03b33bbbf6f12ad0081e52ebbbb7d2eacfeca7bb9',
 'docs/literature/bibliographic_audit_ii/screening/verification_lookup_log.csv': '63fc3317c2cd0a962e145c6034c08b7e1871b0e69e9fe0a91534993961b6f850',
 'docs/literature/bibliographic_audit_ii/screening/version_registry.csv': '33d2ef5e00bd3d343a01184b08b93aa8128ed739bb98ce86472dac93c12c6cdc',
 'docs/literature/bibliographic_audit_ii/screening/work_registry.csv': 'eacaa8ad6f0ba78a91adf9bf8327d1727c6e045a0f7771ba32837c0eaf089661',
 'docs/literature/bibliographic_audit_ii/screening_schema.csv': '0c9031aae2d9f5c674c5e4c3e0f4201af81cc0fabdc3e325fb863cebe8f69d0f',
 'docs/literature/bibliographic_audit_ii/scripts/build_extraction_scaffold.py': '2214860582b7a717955cbf887cb1ba77a825a968b0fcb893ccfd240f6483f92f',
 'docs/literature/bibliographic_audit_ii/scripts/build_work_resolution.py': 'e14670757b94de8732a8b6648b9f1a7c412e1b116e1ba792e2142b919736d0b4',
 'docs/literature/bibliographic_audit_ii/scripts/retrieve_raw_corpus.py': '7f5535cd7edbb57082158c6e80eac86b9f73ce16b2163989d4f67e6ddebf204a',
 'docs/literature/bibliographic_audit_ii/scripts/validate_extraction.py': 'f7d90def3e74950fba3d1fbe10bb7d8bb8d37988437142295478fb321c1de7ff',
 'docs/literature/bibliographic_audit_ii/scripts/validate_screening.py': '5913768f99ace63161d954b7830874455c5fd81df1e04978863706eee5a7b0e2',
 'docs/literature/bibliographic_audit_ii/search_plan.yaml': 'a76420e4603baeda95d70c8d3308bc614458d09d9769979d327ef79bf9a52f28'}

CRITICAL_ROWS = [{'work_id': 'BAIIW0001',
  'preferred_version_id': 'BAIIV0002',
  'title': 'Stationary quasi-periodic pulsations in 20-second cadence TESS flares',
  'baii4_f3a_overlap': 'DIRECT',
  'baii4_f3a_impact': 'F3A_REDRAFT_REQUIRED',
  'gate_review_status': 'CONFIRMED_FOR_GATE_REVIEW',
  'evidence_sufficient_for_gate': 'YES',
  'access_limitation_present': 'NO',
  'central_overlap_dimension': 'F3A_CATALOG_SCALE',
  'secondary_overlap_dimensions': 'F3A_QPP_CLASSIFICATION_REFERENCE',
  'what_the_work_actually_establishes': 'Uses 20-second TESS data from Sectors 27–80 at catalogue scale, reporting '
                                        '3,878 flares on 1,285 flaring stars and 61 QPPs across 57 stars. QPPs are '
                                        'selected with AFINO Fourier model comparison after automated flare detection.',
  'what_it_does_not_establish': 'Does not establish the complete prospective F3A robustness design: the abstract-level '
                                'evidence does not resolve the planned window/processing/quality/gap perturbation '
                                'matrix, and it does not provide injection–recovery, known physical truth or an '
                                'independent held-out validation benchmark.',
  'implication_for_f3a': 'The future F3A design must explicitly reconsider its central catalogue-scale contribution '
                         'and framing before freeze.',
  'implication_type': 'CENTRAL_CONTRIBUTION_RECONSIDERATION',
  'evidence_ids': 'BAII4E0001;BAII4E0002;BAII4E0003;BAII4E0004',
  'source_limitations': 'The abstract frames the physical QPP mechanism as debated; detailed selection-function '
                        'performance is not reported.',
  'baii4_assessment_status': 'BAII4_ASSESSMENT_CONFIRMED',
  'review_notes': 'BAII.4 assessment confirmed from the frozen extraction/evidence layer.'},
 {'work_id': 'BAIIW0002',
  'preferred_version_id': 'BAIIV0004',
  'title': 'Detailed cool star flare morphology with CHEOPS and TESS***',
  'baii4_f3a_overlap': 'PARTIAL',
  'baii4_f3a_impact': 'F3A_DESIGN_ADJUSTMENT_POSSIBLE',
  'gate_review_status': 'CONFIRMED_FOR_GATE_REVIEW',
  'evidence_sufficient_for_gate': 'YES',
  'access_limitation_present': 'NO',
  'central_overlap_dimension': 'F3A_COHORT_UNIVERSE',
  'secondary_overlap_dimensions': 'NONE',
  'what_the_work_actually_establishes': 'Reports High-cadence CHEOPS and TESS sample of late-K and M stars; scale: 130 '
                                        'stars and NOT_REPORTED flares; primary method: Dedicated flare-morphology '
                                        'analysis. BAII.4 assessed PARTIAL F3A overlap, principally on '
                                        'F3A_COHORT_UNIVERSE.',
  'what_it_does_not_establish': 'Does not reproduce the complete prospective F3A programme. In particular, it does not '
                                "by itself fix the project's prospectively defined cohort, independent QPP "
                                'reference-label contract, and the full window/processing/quality/numerical robustness '
                                'matrix.',
  'implication_for_f3a': 'This concrete literature feature must be considered when the relevant F3A design choice is '
                         "prospectively frozen; it does not mandate adoption of the paper's method.",
  'implication_type': 'COHORT_UNIVERSE_CONSIDERATION',
  'evidence_ids': 'BAII4E0005;BAII4E0006;BAII4E0007;BAII4E0008',
  'source_limitations': 'QPP confirmation is described as tentative; the abstract does not provide the detailed QPP '
                        'decision rule.',
  'baii4_assessment_status': 'BAII4_ASSESSMENT_CONFIRMED',
  'review_notes': 'BAII.4 assessment confirmed from the frozen extraction/evidence layer.'},
 {'work_id': 'BAIIW0003',
  'preferred_version_id': 'BAIIV0006',
  'title': 'Properties of Flare Quasiperiodic Pulsations Based on a New TESS Flare Catalog',
  'baii4_f3a_overlap': 'DIRECT',
  'baii4_f3a_impact': 'F3A_REDRAFT_REQUIRED',
  'gate_review_status': 'CONFIRMED_FOR_GATE_REVIEW',
  'evidence_sufficient_for_gate': 'YES',
  'access_limitation_present': 'YES',
  'central_overlap_dimension': 'F3A_CATALOG_SCALE',
  'secondary_overlap_dimensions': 'F3A_QPP_CLASSIFICATION_REFERENCE',
  'what_the_work_actually_establishes': 'Reports a very large TESS 2-minute flare catalogue (208,280 flares from about '
                                        '29,280 flaring stars) and applies a previously published fully convolutional '
                                        'neural-network QPP classifier, selecting 10,465 M-star flares with QPP '
                                        'features.',
  'what_it_does_not_establish': 'The allowed-source recheck does not resolve the full classifier training/validation '
                                'protocol, robustness to window/processing choices, or a selection-function/held-out '
                                'architecture. Those details therefore remain NOT_REPORTED and are not inferred.',
  'implication_for_f3a': 'The future F3A design must explicitly reconsider its central catalogue-scale contribution '
                         'and framing before freeze.',
  'implication_type': 'CENTRAL_CONTRIBUTION_RECONSIDERATION',
  'evidence_ids': 'BAII4E0009;BAII4E0010;BAII4E0011;BAII4E0012',
  'source_limitations': 'BAII.4 source-access limitation remains present. The accessible provider-level evidence does '
                        'not resolve the complete classifier-training/validation protocol.',
  'baii4_assessment_status': 'BAII4_ASSESSMENT_CONFIRMED',
  'review_notes': 'BAII.4 assessment confirmed from the frozen extraction/evidence layer. BAII.5 performed the '
                  'required final allowed-source check; the refereed record and high-level '
                  'catalogue/QPP-classification facts remain supported, but the unresolved method-validation detail '
                  'was not filled by inference.'},
 {'work_id': 'BAIIW0004',
  'preferred_version_id': 'BAIIV0008',
  'title': 'A recurrent 70─100 min quasi-periodic pulsation in the intermediate-aged mid-M dwarf GJ 3512',
  'baii4_f3a_overlap': 'PARTIAL',
  'baii4_f3a_impact': 'F3A_DESIGN_ADJUSTMENT_POSSIBLE',
  'gate_review_status': 'CONFIRMED_FOR_GATE_REVIEW',
  'evidence_sufficient_for_gate': 'YES',
  'access_limitation_present': 'NO',
  'central_overlap_dimension': 'F3A_QPP_CLASSIFICATION_REFERENCE',
  'secondary_overlap_dimensions': 'F3A_WINDOW_ROBUSTNESS',
  'what_the_work_actually_establishes': 'Reports Single-star multi-sector TESS time series (GJ 3512); scale: 1 star '
                                        'and ~1 flare/day; ~5 flares in Sector 60 flares; primary method: Morlet '
                                        'continuous wavelet transform. BAII.4 assessed PARTIAL F3A overlap, '
                                        'principally on F3A_QPP_CLASSIFICATION_REFERENCE.',
  'what_it_does_not_establish': 'Does not reproduce the complete prospective F3A programme. In particular, it does not '
                                "by itself fix the project's prospectively defined cohort, independent QPP "
                                'reference-label contract, and the full window/processing/quality/numerical robustness '
                                'matrix.',
  'implication_for_f3a': 'This concrete literature feature must be considered when the relevant F3A design choice is '
                         "prospectively frozen; it does not mandate adoption of the paper's method.",
  'implication_type': 'QPP_METHOD_AND_WINDOW_COMPARATOR',
  'evidence_ids': 'BAII4E0013;BAII4E0014;BAII4E0015;BAII4E0016',
  'source_limitations': 'Sector 60 detection is marginal and lower activity may reduce detectability; a physical '
                        'coronal interpretation remains to be confirmed.',
  'baii4_assessment_status': 'BAII4_ASSESSMENT_CONFIRMED',
  'review_notes': 'BAII.4 assessment confirmed from the frozen extraction/evidence layer.'},
 {'work_id': 'BAIIW0023',
  'preferred_version_id': 'BAIIV0036',
  'title': 'Scalable, Advanced Machine Learning Based Approaches for Stellar Flare Identification: Application to TESS '
           'Short-cadence Data and Analysis of a New Flare Catalog',
  'baii4_f3a_overlap': 'PARTIAL',
  'baii4_f3a_impact': 'F3A_DESIGN_ADJUSTMENT_POSSIBLE',
  'gate_review_status': 'CONFIRMED_FOR_GATE_REVIEW',
  'evidence_sufficient_for_gate': 'YES',
  'access_limitation_present': 'NO',
  'central_overlap_dimension': 'F3A_COHORT_UNIVERSE',
  'secondary_overlap_dimensions': 'NONE',
  'what_the_work_actually_establishes': 'Reports TESS 2-min all-sky machine-learning flare catalogue, Sectors 1–72; '
                                        'scale: 1.3 million light curves; ~18,000 flare stars and ~250,000 flares; '
                                        'primary method: DNN / Random Forest / XGBoost flare identification. BAII.4 '
                                        'assessed PARTIAL F3A overlap, principally on F3A_COHORT_UNIVERSE.',
  'what_it_does_not_establish': 'Does not reproduce the complete prospective F3A programme. In particular, it does not '
                                "by itself fix the project's prospectively defined cohort, independent QPP "
                                'reference-label contract, and the full window/processing/quality/numerical robustness '
                                'matrix.',
  'implication_for_f3a': 'This concrete literature feature must be considered when the relevant F3A design choice is '
                         "prospectively frozen; it does not mandate adoption of the paper's method.",
  'implication_type': 'CATALOG_SOURCE_AND_EVENT_SELECTION',
  'evidence_ids': 'BAII4E0025;BAII4E0026;BAII4E0027;BAII4E0028',
  'source_limitations': 'The abstract explicitly notes low-amplitude incompleteness affecting flare-frequency '
                        'uncertainties.',
  'baii4_assessment_status': 'BAII4_ASSESSMENT_CONFIRMED',
  'review_notes': 'BAII.4 assessment confirmed from the frozen extraction/evidence layer.'},
 {'work_id': 'BAIIW0024',
  'preferred_version_id': 'BAIIV0038',
  'title': 'Detecting Stellar Flares in Photometric Data Using Hidden Markov Models',
  'baii4_f3a_overlap': 'PARTIAL',
  'baii4_f3a_impact': 'F3A_DESIGN_ADJUSTMENT_POSSIBLE',
  'gate_review_status': 'CONFIRMED_FOR_GATE_REVIEW',
  'evidence_sufficient_for_gate': 'YES',
  'access_limitation_present': 'NO',
  'central_overlap_dimension': 'F3A_PROCESSING_ROBUSTNESS',
  'secondary_overlap_dimensions': 'NONE',
  'what_the_work_actually_establishes': 'Reports Method-development study with simulation/injection-recovery and one '
                                        'TESS example; scale: 1 TESS example star plus synthetic experiments and '
                                        'NOT_REPORTED flares; primary method: Three-state hidden Markov model with '
                                        'celerite baseline. BAII.4 assessed PARTIAL F3A overlap, principally on '
                                        'F3A_PROCESSING_ROBUSTNESS.',
  'what_it_does_not_establish': 'Does not reproduce the complete prospective F3A programme. In particular, it does not '
                                "by itself fix the project's prospectively defined cohort, independent QPP "
                                'reference-label contract, and the full window/processing/quality/numerical robustness '
                                'matrix.',
  'implication_for_f3a': 'This concrete literature feature must be considered when the relevant F3A design choice is '
                         "prospectively frozen; it does not mandate adoption of the paper's method.",
  'implication_type': 'PROCESSING_ROBUSTNESS_AND_VALIDATION',
  'evidence_ids': 'BAII4E0029;BAII4E0030;BAII4E0031;BAII4E0032',
  'source_limitations': 'Independent held-out validation and a formal development/held-out split are not reported in '
                        'the abstract.',
  'baii4_assessment_status': 'BAII4_ASSESSMENT_CONFIRMED',
  'review_notes': 'BAII.4 assessment confirmed from the frozen extraction/evidence layer.'},
 {'work_id': 'BAIIW0037',
  'preferred_version_id': 'BAIIV0060',
  'title': 'Detecting stellar flares in the presence of a deterministic trend and stochastic volatility',
  'baii4_f3a_overlap': 'PARTIAL',
  'baii4_f3a_impact': 'F3A_DESIGN_ADJUSTMENT_POSSIBLE',
  'gate_review_status': 'CONFIRMED_FOR_GATE_REVIEW',
  'evidence_sufficient_for_gate': 'YES',
  'access_limitation_present': 'NO',
  'central_overlap_dimension': 'F3A_PROCESSING_ROBUSTNESS',
  'secondary_overlap_dimensions': 'NONE',
  'what_the_work_actually_establishes': 'Reports Method study demonstrated on three TESS stars; scale: 3 exemplar '
                                        'stars and up to 145, 460 and 403 detections depending target/threshold '
                                        'flares; primary method: Time-varying harmonic trend + ARMA/GARCH flare '
                                        'detection. BAII.4 assessed PARTIAL F3A overlap, principally on '
                                        'F3A_PROCESSING_ROBUSTNESS.',
  'what_it_does_not_establish': 'Does not reproduce the complete prospective F3A programme. In particular, it does not '
                                "by itself fix the project's prospectively defined cohort, independent QPP "
                                'reference-label contract, and the full window/processing/quality/numerical robustness '
                                'matrix.',
  'implication_for_f3a': 'This concrete literature feature must be considered when the relevant F3A design choice is '
                         "prospectively frozen; it does not mandate adoption of the paper's method.",
  'implication_type': 'PROCESSING_ROBUSTNESS_COMPARATOR',
  'evidence_ids': 'BAII4E0057;BAII4E0058;BAII4E0059;BAII4E0060',
  'source_limitations': 'Detection counts depend on chosen thresholds; broader validation is not reported in the '
                        'abstract.',
  'baii4_assessment_status': 'BAII4_ASSESSMENT_CONFIRMED',
  'review_notes': 'BAII.4 assessment confirmed from the frozen extraction/evidence layer.'},
 {'work_id': 'BAIIW0071',
  'preferred_version_id': 'BAIIV0113',
  'title': 'Searching for Stellar Activity Cycles using Flares II: The TESS CVZ',
  'baii4_f3a_overlap': 'PARTIAL',
  'baii4_f3a_impact': 'F3A_DESIGN_ADJUSTMENT_POSSIBLE',
  'gate_review_status': 'CONFIRMED_FOR_GATE_REVIEW',
  'evidence_sufficient_for_gate': 'YES',
  'access_limitation_present': 'NO',
  'central_overlap_dimension': 'F3A_COHORT_UNIVERSE',
  'secondary_overlap_dimensions': 'NONE',
  'what_the_work_actually_establishes': 'Reports TESS Continuous Viewing Zone long-baseline short-cadence survey; '
                                        'scale: >14,000 stars and NOT_REPORTED flares; primary method: Long-term '
                                        'flare-rate monitoring with per-star injection–recovery. BAII.4 assessed '
                                        'PARTIAL F3A overlap, principally on F3A_COHORT_UNIVERSE.',
  'what_it_does_not_establish': 'Does not reproduce the complete prospective F3A programme. In particular, it does not '
                                "by itself fix the project's prospectively defined cohort, independent QPP "
                                'reference-label contract, and the full window/processing/quality/numerical robustness '
                                'matrix.',
  'implication_for_f3a': 'This concrete literature feature must be considered when the relevant F3A design choice is '
                         "prospectively frozen; it does not mandate adoption of the paper's method.",
  'implication_type': 'COHORT_AND_SELECTION_FUNCTION_CONTEXT',
  'evidence_ids': 'BAII4E0093;BAII4E0094;BAII4E0095;BAII4E0096',
  'source_limitations': 'The abstract does not describe a development/held-out split; long-term candidates require '
                        'interpretation against sampling/systematics.',
  'baii4_assessment_status': 'BAII4_ASSESSMENT_CONFIRMED',
  'review_notes': 'BAII.4 assessment confirmed from the frozen extraction/evidence layer.'},
 {'work_id': 'BAIIW0098',
  'preferred_version_id': 'BAIIV0156',
  'title': 'Detecting Quasiperiodic Pulsations in Solar and Stellar Flares with a Neural Network',
  'baii4_f3a_overlap': 'PARTIAL',
  'baii4_f3a_impact': 'F3A_DESIGN_ADJUSTMENT_POSSIBLE',
  'gate_review_status': 'CONFIRMED_FOR_GATE_REVIEW',
  'evidence_sufficient_for_gate': 'YES',
  'access_limitation_present': 'NO',
  'central_overlap_dimension': 'F3A_QPP_CLASSIFICATION_REFERENCE',
  'secondary_overlap_dimensions': 'NONE',
  'what_the_work_actually_establishes': 'Reports Synthetic QPP/non-QPP training set + Kepler flare '
                                        'validation/application; scale: 90,000 synthetic flare light curves; '
                                        '2274-event Kepler catalogue application and 2274 real catalogue events in '
                                        'large application flares; primary method: Fully convolutional neural network '
                                        '(FCN) QPP classifier. BAII.4 assessed PARTIAL F3A overlap, principally on '
                                        'F3A_QPP_CLASSIFICATION_REFERENCE.',
  'what_it_does_not_establish': 'Does not reproduce the complete prospective F3A programme. In particular, it does not '
                                "by itself fix the project's prospectively defined cohort, independent QPP "
                                'reference-label contract, and the full window/processing/quality/numerical robustness '
                                'matrix.',
  'implication_for_f3a': 'This concrete literature feature must be considered when the relevant F3A design choice is '
                         "prospectively frozen; it does not mandate adoption of the paper's method.",
  'implication_type': 'QPP_REFERENCE_CLASSIFIER_AND_VALIDATION',
  'evidence_ids': 'BAII4E0097;BAII4E0098;BAII4E0099;BAII4E0100',
  'source_limitations': 'The learned signal family is specifically exponentially decaying harmonic QPP; transfer to '
                        'other QPP morphologies or TESS is not established by the abstract.',
  'baii4_assessment_status': 'BAII4_ASSESSMENT_CONFIRMED',
  'review_notes': 'BAII.4 assessment confirmed from the frozen extraction/evidence layer.'},
 {'work_id': 'BAIIW0145',
  'preferred_version_id': 'BAIIV0222',
  'title': 'Stellar flare morphology with TESS across the main sequence',
  'baii4_f3a_overlap': 'PARTIAL',
  'baii4_f3a_impact': 'F3A_DESIGN_ADJUSTMENT_POSSIBLE',
  'gate_review_status': 'CONFIRMED_FOR_GATE_REVIEW',
  'evidence_sufficient_for_gate': 'YES',
  'access_limitation_present': 'NO',
  'central_overlap_dimension': 'F3A_COHORT_UNIVERSE',
  'secondary_overlap_dimensions': 'F3A_EVENT_SELECTION',
  'what_the_work_actually_establishes': 'Reports Main-sequence TESS flare catalogue across Sectors 1–69; scale: '
                                        '~14,000 flare stars and ~120,000 flares; primary method: flatwrm2 LSTM flare '
                                        'detection. BAII.4 assessed PARTIAL F3A overlap, principally on '
                                        'F3A_COHORT_UNIVERSE.',
  'what_it_does_not_establish': 'Does not reproduce the complete prospective F3A programme. In particular, it does not '
                                "by itself fix the project's prospectively defined cohort, independent QPP "
                                'reference-label contract, and the full window/processing/quality/numerical robustness '
                                'matrix.',
  'implication_for_f3a': 'This concrete literature feature must be considered when the relevant F3A design choice is '
                         "prospectively frozen; it does not mandate adoption of the paper's method.",
  'implication_type': 'CATALOG_SOURCE_AND_EVENT_SELECTION',
  'evidence_ids': 'BAII4E0113;BAII4E0114;BAII4E0115;BAII4E0116',
  'source_limitations': 'Strict filtering/manual vetting reduces completeness, which is directly relevant to catalogue '
                        'selection effects.',
  'baii4_assessment_status': 'BAII4_ASSESSMENT_CONFIRMED',
  'review_notes': 'BAII.4 assessment confirmed from the frozen extraction/evidence layer.'},
 {'work_id': 'BAIIW0149',
  'preferred_version_id': 'BAIIV0230',
  'title': 'Planet-induced Stellar Flare Candidates from the TESS Mission',
  'baii4_f3a_overlap': 'PARTIAL',
  'baii4_f3a_impact': 'F3A_DESIGN_ADJUSTMENT_POSSIBLE',
  'gate_review_status': 'CONFIRMED_FOR_GATE_REVIEW',
  'evidence_sufficient_for_gate': 'YES',
  'access_limitation_present': 'NO',
  'central_overlap_dimension': 'F3A_COHORT_UNIVERSE',
  'secondary_overlap_dimensions': 'F3A_EVENT_SELECTION',
  'what_the_work_actually_establishes': 'Reports TESS exoplanet-host flare survey with simulated injection tests; '
                                        'scale: NOT_REPORTED and NOT_REPORTED flares; primary method: ardor multitier '
                                        'flare-detection pipeline. BAII.4 assessed PARTIAL F3A overlap, principally on '
                                        'F3A_COHORT_UNIVERSE.',
  'what_it_does_not_establish': 'Does not reproduce the complete prospective F3A programme. In particular, it does not '
                                "by itself fix the project's prospectively defined cohort, independent QPP "
                                'reference-label contract, and the full window/processing/quality/numerical robustness '
                                'matrix.',
  'implication_for_f3a': 'This concrete literature feature must be considered when the relevant F3A design choice is '
                         "prospectively frozen; it does not mandate adoption of the paper's method.",
  'implication_type': 'EVENT_SELECTION_AND_SELECTION_FUNCTION',
  'evidence_ids': 'BAII4E0121;BAII4E0122;BAII4E0123;BAII4E0124',
  'source_limitations': 'No independent confirmatory held-out split matching the BAII F3B contract is reported; some '
                        'tier validation uses visually vetted real flares.',
  'baii4_assessment_status': 'BAII4_ASSESSMENT_CONFIRMED',
  'review_notes': 'BAII.4 assessment confirmed from the frozen extraction/evidence layer.'},
 {'work_id': 'BAIIW0150',
  'preferred_version_id': 'BAIIV0232',
  'title': 'Extending TESS flare frequency distributions with CHEOPS: Power-law versus lognormal',
  'baii4_f3a_overlap': 'PARTIAL',
  'baii4_f3a_impact': 'F3A_DESIGN_ADJUSTMENT_POSSIBLE',
  'gate_review_status': 'CONFIRMED_FOR_GATE_REVIEW',
  'evidence_sufficient_for_gate': 'YES',
  'access_limitation_present': 'NO',
  'central_overlap_dimension': 'F3A_COHORT_UNIVERSE',
  'secondary_overlap_dimensions': 'NONE',
  'what_the_work_actually_establishes': 'Reports Combined TESS+CHEOPS M-dwarf sample; scale: 110 M dwarfs and 5620 '
                                        'flares; primary method: Combined-mission flare detection and FFD modeling. '
                                        'BAII.4 assessed PARTIAL F3A overlap, principally on F3A_COHORT_UNIVERSE.',
  'what_it_does_not_establish': 'Does not reproduce the complete prospective F3A programme. In particular, it does not '
                                "by itself fix the project's prospectively defined cohort, independent QPP "
                                'reference-label contract, and the full window/processing/quality/numerical robustness '
                                'matrix.',
  'implication_for_f3a': 'This concrete literature feature must be considered when the relevant F3A design choice is '
                         "prospectively frozen; it does not mandate adoption of the paper's method.",
  'implication_type': 'COHORT_AND_COMPLETENESS_CONTEXT',
  'evidence_ids': 'BAII4E0125;BAII4E0126;BAII4E0127;BAII4E0128',
  'source_limitations': 'The high-energy drop remains unexplained and may be intrinsic or observational; injection '
                        'details are not resolved by the abstract.',
  'baii4_assessment_status': 'BAII4_ASSESSMENT_CONFIRMED',
  'review_notes': 'BAII.4 assessment confirmed from the frozen extraction/evidence layer.'},
 {'work_id': 'BAIIW0156',
  'preferred_version_id': 'BAIIV0242',
  'title': 'FLARENET: A Convolutional Neural Network for Stellar Flare Detection with TESS',
  'baii4_f3a_overlap': 'PARTIAL',
  'baii4_f3a_impact': 'F3A_DESIGN_ADJUSTMENT_POSSIBLE',
  'gate_review_status': 'CONFIRMED_FOR_GATE_REVIEW',
  'evidence_sufficient_for_gate': 'YES',
  'access_limitation_present': 'NO',
  'central_overlap_dimension': 'F3A_QPP_CLASSIFICATION_REFERENCE',
  'secondary_overlap_dimensions': 'F3A_QUALITY_AND_GAPS',
  'what_the_work_actually_establishes': 'Reports TESS 20-s flare classifier trained on quiescent light curves + '
                                        'synthetic flares; scale: ~1000 quiescent 20-s light curves for training '
                                        'backgrounds and 100 synthetic flares injected per training light curve '
                                        'flares; primary method: flarenet 1D convolutional neural network. BAII.4 '
                                        'assessed PARTIAL F3A overlap, principally on '
                                        'F3A_QPP_CLASSIFICATION_REFERENCE.',
  'what_it_does_not_establish': 'Does not reproduce the complete prospective F3A programme. In particular, it does not '
                                "by itself fix the project's prospectively defined cohort, independent QPP "
                                'reference-label contract, and the full window/processing/quality/numerical robustness '
                                'matrix.',
  'implication_for_f3a': 'This concrete literature feature must be considered when the relevant F3A design choice is '
                         "prospectively frozen; it does not mandate adoption of the paper's method.",
  'implication_type': 'QUALITY_GAPS_AND_VALIDATION',
  'evidence_ids': 'BAII4E0133;BAII4E0134;BAII4E0135;BAII4E0136',
  'source_limitations': 'Injection evaluation draws from the same flare-parameter distribution/background family used '
                        'for training; an independent project-style held-out benchmark is not stated.',
  'baii4_assessment_status': 'BAII4_ASSESSMENT_CONFIRMED',
  'review_notes': 'BAII.4 assessment confirmed from the frozen extraction/evidence layer.'},
 {'work_id': 'BAIIW0168',
  'preferred_version_id': 'BAIIV0257',
  'title': 'Scalable Bayesian Additive Models for Stellar Flare Detection via Amortized Gaussian Process Inference and '
           'Hidden Markov Models',
  'baii4_f3a_overlap': 'PARTIAL',
  'baii4_f3a_impact': 'F3A_DESIGN_ADJUSTMENT_POSSIBLE',
  'gate_review_status': 'CONFIRMED_FOR_GATE_REVIEW',
  'evidence_sufficient_for_gate': 'YES',
  'access_limitation_present': 'NO',
  'central_overlap_dimension': 'F3A_PROCESSING_ROBUSTNESS',
  'secondary_overlap_dimensions': 'NONE',
  'what_the_work_actually_establishes': 'Reports Method study with extensive simulation and empirical stellar time '
                                        'series; scale: NOT_REPORTED and NOT_REPORTED flares; primary method: VAE '
                                        'surrogate + Celerite + HMM additive Bayesian flare model. BAII.4 assessed '
                                        'PARTIAL F3A overlap, principally on F3A_PROCESSING_ROBUSTNESS.',
  'what_it_does_not_establish': 'Does not reproduce the complete prospective F3A programme. In particular, it does not '
                                "by itself fix the project's prospectively defined cohort, independent QPP "
                                'reference-label contract, and the full window/processing/quality/numerical robustness '
                                'matrix.',
  'implication_for_f3a': 'This concrete literature feature must be considered when the relevant F3A design choice is '
                         "prospectively frozen; it does not mandate adoption of the paper's method.",
  'implication_type': 'PROCESSING_ROBUSTNESS_COMPARATOR',
  'evidence_ids': 'BAII4E0141;BAII4E0142;BAII4E0143;BAII4E0144',
  'source_limitations': 'The abstract does not describe a flare injection–recovery selection function or independent '
                        'held-out benchmark.',
  'baii4_assessment_status': 'BAII4_ASSESSMENT_CONFIRMED',
  'review_notes': 'BAII.4 assessment confirmed from the frozen extraction/evidence layer.'},
 {'work_id': 'BAIIW0190',
  'preferred_version_id': 'BAIIV0283',
  'title': 'AFINO: Automated Flare Inference of Oscillations',
  'baii4_f3a_overlap': 'PARTIAL',
  'baii4_f3a_impact': 'F3A_DESIGN_ADJUSTMENT_POSSIBLE',
  'gate_review_status': 'CONFIRMED_FOR_GATE_REVIEW',
  'evidence_sufficient_for_gate': 'YES',
  'access_limitation_present': 'NO',
  'central_overlap_dimension': 'F3A_NUMERICAL_STABILITY',
  'secondary_overlap_dimensions': 'NONE',
  'what_the_work_actually_establishes': 'Reports Software/method record; scale: NOT_APPLICABLE and NOT_APPLICABLE '
                                        'flares; primary method: AFINO Fourier-based model comparison. BAII.4 assessed '
                                        'PARTIAL F3A overlap, principally on F3A_NUMERICAL_STABILITY.',
  'what_it_does_not_establish': 'Does not reproduce the complete prospective F3A programme. In particular, it does not '
                                "by itself fix the project's prospectively defined cohort, independent QPP "
                                'reference-label contract, and the full window/processing/quality/numerical robustness '
                                'matrix.',
  'implication_for_f3a': 'This concrete literature feature must be considered when the relevant F3A design choice is '
                         "prospectively frozen; it does not mandate adoption of the paper's method.",
  'implication_type': 'NUMERICAL_STABILITY_DOCUMENTATION',
  'evidence_ids': 'BAII4E0157;BAII4E0158;BAII4E0159;BAII4E0160',
  'source_limitations': 'ASCL is a software record; scientific performance/selection-function validation must be '
                        'sourced from studies using the code.',
  'baii4_assessment_status': 'BAII4_ASSESSMENT_CONFIRMED',
  'review_notes': 'BAII.4 assessment confirmed from the frozen extraction/evidence layer.'}]
PRECEDENCE_ROWS = [{'positioning_claim_id': 'P001',
  'candidate_claim': 'Catalogue-scale TESS QPP studies already exist.',
  'audit_assessment': 'SUPPORTED_AS_BOUNDED_STATEMENT',
  'supporting_work_ids': 'BAIIW0001;BAIIW0003',
  'supporting_evidence_ids': 'BAII4E0001;BAII4E0002;BAII4E0003;BAII4E0004;BAII4E0009;BAII4E0010;BAII4E0011;BAII4E0012',
  'safe_wording': 'Within the included BAII corpus, catalogue-scale TESS QPP analyses are represented by at least '
                  'BAIIW0001 and BAIIW0003.',
  'unsafe_wording': 'No catalogue-scale TESS QPP study existed before this project.',
  'manuscript_relevance': 'HIGH',
  'f3a_design_relevance': 'CENTRAL',
  'notes': 'This is a bounded corpus statement, not an exhaustive priority claim.'},
 {'positioning_claim_id': 'P002',
  'candidate_claim': 'TESS QPP catalog/classification work predates F3A.',
  'audit_assessment': 'SUPPORTED_AS_BOUNDED_STATEMENT',
  'supporting_work_ids': 'BAIIW0001;BAIIW0003',
  'supporting_evidence_ids': 'BAII4E0001;BAII4E0002;BAII4E0003;BAII4E0004;BAII4E0009;BAII4E0010;BAII4E0011;BAII4E0012',
  'safe_wording': 'The included literature contains TESS QPP catalogue and classification work published before the '
                  'prospective F3A freeze.',
  'unsafe_wording': 'F3A is the first TESS QPP catalogue/classification study.',
  'manuscript_relevance': 'HIGH',
  'f3a_design_relevance': 'CENTRAL',
  'notes': 'Supported by included works only.'},
 {'positioning_claim_id': 'P003',
  'candidate_claim': 'AFINO has already been applied at catalogue scale to TESS QPP analysis.',
  'audit_assessment': 'SUPPORTED_AS_BOUNDED_STATEMENT',
  'supporting_work_ids': 'BAIIW0001',
  'supporting_evidence_ids': 'BAII4E0001;BAII4E0002;BAII4E0003;BAII4E0004',
  'safe_wording': 'BAIIW0001 applies AFINO to a catalogue-scale sample of 20-second TESS flares.',
  'unsafe_wording': 'This project introduces the first catalogue-scale AFINO analysis of TESS QPPs.',
  'manuscript_relevance': 'HIGH',
  'f3a_design_relevance': 'CENTRAL',
  'notes': 'The exact future F3A robustness contribution must be distinguished from catalogue-scale AFINO use itself.'},
 {'positioning_claim_id': 'P004',
  'candidate_claim': 'Machine-learning QPP classification has been applied to TESS catalogue data.',
  'audit_assessment': 'SUPPORTED_AS_BOUNDED_STATEMENT',
  'supporting_work_ids': 'BAIIW0003',
  'supporting_evidence_ids': 'BAII4E0009;BAII4E0010;BAII4E0011;BAII4E0012',
  'safe_wording': 'BAIIW0003 reports applying a previously published fully convolutional QPP classifier to a large '
                  'TESS flare catalogue.',
  'unsafe_wording': 'Machine-learning QPP classification has not previously been used on TESS catalogue data.',
  'manuscript_relevance': 'HIGH',
  'f3a_design_relevance': 'CENTRAL',
  'notes': 'Detailed classifier validation remains access-limited in BAII; only the supported high-level claim is '
           'used.'},
 {'positioning_claim_id': 'P005',
  'candidate_claim': 'Injection–recovery/selection-function approaches already exist in adjacent flare/QPP '
                     'methodology.',
  'audit_assessment': 'SUPPORTED_AS_BOUNDED_STATEMENT',
  'supporting_work_ids': 'BAIIW0024;BAIIW0071;BAIIW0098;BAIIW0147;BAIIW0149;BAIIW0150;BAIIW0154;BAIIW0156;BAIIW0168',
  'supporting_evidence_ids': 'BAII4E0029;BAII4E0030;BAII4E0031;BAII4E0032;BAII4E0093;BAII4E0094;BAII4E0095;BAII4E0096;BAII4E0097;BAII4E0098;BAII4E0099;BAII4E0100;BAII4E0117;BAII4E0118;BAII4E0119;BAII4E0120;BAII4E0121;BAII4E0122;BAII4E0123;BAII4E0124;BAII4E0125;BAII4E0126;BAII4E0127;BAII4E0128;BAII4E0129;BAII4E0130;BAII4E0131;BAII4E0132;BAII4E0133;BAII4E0134;BAII4E0135;BAII4E0136;BAII4E0141;BAII4E0142;BAII4E0143;BAII4E0144',
  'safe_wording': 'The included BAII literature contains multiple injection–recovery, known-ground-truth and '
                  'selection-function analogues relevant to future F3B design.',
  'unsafe_wording': 'F3B would introduce injection–recovery or selection-function validation to flare/QPP methodology '
                    'for the first time.',
  'manuscript_relevance': 'MEDIUM',
  'f3a_design_relevance': 'INDIRECT',
  'notes': 'These works are heterogeneous and do not all study QPPs or TESS.'},
 {'positioning_claim_id': 'P006',
  'candidate_claim': 'The audit found no included study with the complete prospective F3B development/held-out '
                     'architecture.',
  'audit_assessment': 'SUPPORTED_AS_BOUNDED_STATEMENT',
  'supporting_work_ids': 'BAIIW0024;BAIIW0071;BAIIW0098;BAIIW0147;BAIIW0149;BAIIW0150;BAIIW0154;BAIIW0156;BAIIW0168',
  'supporting_evidence_ids': 'BAII4E0029;BAII4E0030;BAII4E0031;BAII4E0032;BAII4E0093;BAII4E0094;BAII4E0095;BAII4E0096;BAII4E0097;BAII4E0098;BAII4E0099;BAII4E0100;BAII4E0117;BAII4E0118;BAII4E0119;BAII4E0120;BAII4E0121;BAII4E0122;BAII4E0123;BAII4E0124;BAII4E0125;BAII4E0126;BAII4E0127;BAII4E0128;BAII4E0129;BAII4E0130;BAII4E0131;BAII4E0132;BAII4E0133;BAII4E0134;BAII4E0135;BAII4E0136;BAII4E0141;BAII4E0142;BAII4E0143;BAII4E0144',
  'safe_wording': 'No included BAII.4 work was assessed as matching the full project-specific combination of '
                  'prospective development/validation separation and an independent held-out benchmark.',
  'unsafe_wording': 'No previous study has ever used development/held-out validation for QPP detection.',
  'manuscript_relevance': 'MEDIUM',
  'f3a_design_relevance': 'NONE',
  'notes': 'Absence is restricted to the 40 included works and the project-specific architecture.'},
 {'positioning_claim_id': 'P007',
  'candidate_claim': 'F3A would be the first catalogue-scale TESS QPP study.',
  'audit_assessment': 'CONTRADICTED_BY_INCLUDED_LITERATURE',
  'supporting_work_ids': 'BAIIW0001;BAIIW0003',
  'supporting_evidence_ids': 'BAII4E0001;BAII4E0002;BAII4E0003;BAII4E0004;BAII4E0009;BAII4E0010;BAII4E0011;BAII4E0012',
  'safe_wording': 'Do not claim first catalogue-scale TESS QPP study; instead state the narrower robustness question '
                  'actually addressed by the redesigned F3A.',
  'unsafe_wording': 'F3A is the first catalogue-scale TESS QPP study.',
  'manuscript_relevance': 'HIGH',
  'f3a_design_relevance': 'CENTRAL',
  'notes': 'Directly contradicted by included literature.'},
 {'positioning_claim_id': 'P008',
  'candidate_claim': 'F3B would be the first QPP injection–recovery study.',
  'audit_assessment': 'CONTRADICTED_BY_INCLUDED_LITERATURE',
  'supporting_work_ids': 'BAIIW0098',
  'supporting_evidence_ids': 'BAII4E0097;BAII4E0098;BAII4E0099;BAII4E0100',
  'safe_wording': 'Describe the project-specific validation architecture without claiming first QPP '
                  'injection–recovery.',
  'unsafe_wording': 'F3B is the first QPP injection–recovery study.',
  'manuscript_relevance': 'HIGH',
  'f3a_design_relevance': 'NONE',
  'notes': 'BAIIW0098 uses synthetic known-truth QPP/non-QPP data and explicit validation; priority language is not '
           'authorized.'},
 {'positioning_claim_id': 'P009',
  'candidate_claim': 'No previous work studies robustness to methodological choices.',
  'audit_assessment': 'CONTRADICTED_BY_INCLUDED_LITERATURE',
  'supporting_work_ids': 'BAIIW0004;BAIIW0024;BAIIW0037;BAIIW0145;BAIIW0156;BAIIW0168',
  'supporting_evidence_ids': 'BAII4E0013;BAII4E0014;BAII4E0015;BAII4E0016;BAII4E0029;BAII4E0030;BAII4E0031;BAII4E0032;BAII4E0057;BAII4E0058;BAII4E0059;BAII4E0060;BAII4E0113;BAII4E0114;BAII4E0115;BAII4E0116;BAII4E0133;BAII4E0134;BAII4E0135;BAII4E0136;BAII4E0141;BAII4E0142;BAII4E0143;BAII4E0144',
  'safe_wording': 'The literature contains multiple method-, processing-, window-, quality- and gap-related robustness '
                  'considerations; F3A must state its specific robustness scope.',
  'unsafe_wording': 'No prior work examined methodological robustness.',
  'manuscript_relevance': 'HIGH',
  'f3a_design_relevance': 'HIGH',
  'notes': 'The included works do not necessarily implement the same robustness grid as the project.'},
 {'positioning_claim_id': 'P010',
  'candidate_claim': 'This project is the first to study TESS QPP selection effects.',
  'audit_assessment': 'PROHIBITED_PRIORITY_CLAIM',
  'supporting_work_ids': 'BAIIW0001;BAIIW0003;BAIIW0098',
  'supporting_evidence_ids': 'BAII4E0001;BAII4E0002;BAII4E0003;BAII4E0004;BAII4E0009;BAII4E0010;BAII4E0011;BAII4E0012;BAII4E0097;BAII4E0098;BAII4E0099;BAII4E0100',
  'safe_wording': 'BAII does not establish a global priority claim about TESS QPP selection effects; any manuscript '
                  'statement must be scoped to the project-specific design and audited corpus.',
  'unsafe_wording': 'This is the first study of TESS QPP selection effects.',
  'manuscript_relevance': 'HIGH',
  'f3a_design_relevance': 'HIGH',
  'notes': 'The audit cannot convert non-retrieval of an exact precedent into absence from the literature.'}]
COMPARATOR_ROWS = [{'work_id': 'BAIIW0004',
  'method_name_or_family': 'Morlet continuous wavelet transform',
  'target_problem': 'QPP classification/detection',
  'relevant_to_f3a': 'YES',
  'relevant_to_f3b': 'NO',
  'implementation_available': 'NOT_REPORTED',
  'procedure_sufficiently_defined': 'YES',
  'comparison_value': 'Direct QPP-detection comparator with explicit wavelet and window choices; useful to distinguish '
                      'Fourier-model-comparison robustness from time-frequency detection.',
  'comparison_cost_or_risk': 'Requires a distinct time-frequency implementation and fair threshold/significance '
                             'harmonization.',
  'consideration_priority': 'MUST_ADDRESS_BEFORE_F3A_FREEZE',
  'evidence_ids': 'BAII4E0013;BAII4E0014;BAII4E0015;BAII4E0016',
  'adoption_decision': 'NOT_DECIDED_IN_BAII',
  'notes': 'Consideration priority does not imply implementation or adoption.'},
 {'work_id': 'BAIIW0023',
  'method_name_or_family': 'DNN / Random Forest / XGBoost flare identification',
  'target_problem': 'stellar flare detection / upstream event construction',
  'relevant_to_f3a': 'YES',
  'relevant_to_f3b': 'NO',
  'implementation_available': 'NOT_REPORTED',
  'procedure_sufficiently_defined': 'YES',
  'comparison_value': 'Large-scale TESS flare-identification alternatives can affect the upstream event universe '
                      'entering any QPP analysis.',
  'comparison_cost_or_risk': 'Large ML pipelines may be costly to reproduce and may not be necessary if F3A freezes an '
                             'external catalogue rather than rebuilding flare detection.',
  'consideration_priority': 'MUST_ADDRESS_BEFORE_F3A_FREEZE',
  'evidence_ids': 'BAII4E0025;BAII4E0026;BAII4E0027;BAII4E0028',
  'adoption_decision': 'NOT_DECIDED_IN_BAII',
  'notes': 'Consideration priority does not imply implementation or adoption.'},
 {'work_id': 'BAIIW0024',
  'method_name_or_family': 'Three-state hidden Markov model with celerite baseline',
  'target_problem': 'stellar flare detection / upstream event construction',
  'relevant_to_f3a': 'YES',
  'relevant_to_f3b': 'YES',
  'implementation_available': 'NOT_REPORTED',
  'procedure_sufficiently_defined': 'YES',
  'comparison_value': 'Provides a probabilistic flare-detection baseline plus injection–recovery/known-truth '
                      'evaluation relevant to both processing and validation design.',
  'comparison_cost_or_risk': 'Model complexity and tuning may exceed what is needed for F3A; validation transfer to '
                             'QPP selection is not automatic.',
  'consideration_priority': 'MUST_ADDRESS_BEFORE_F3B_FREEZE',
  'evidence_ids': 'BAII4E0029;BAII4E0030;BAII4E0031;BAII4E0032',
  'adoption_decision': 'NOT_DECIDED_IN_BAII',
  'notes': 'Consideration priority does not imply implementation or adoption.'},
 {'work_id': 'BAIIW0037',
  'method_name_or_family': 'Time-varying harmonic trend + ARMA/GARCH flare detection',
  'target_problem': 'stellar flare detection / upstream event construction',
  'relevant_to_f3a': 'YES',
  'relevant_to_f3b': 'NO',
  'implementation_available': 'NOT_REPORTED',
  'procedure_sufficiently_defined': 'YES',
  'comparison_value': 'Explicit trend and stochastic-volatility treatment is a concrete processing comparator for '
                      'flare-event construction.',
  'comparison_cost_or_risk': 'Different statistical assumptions and implementation complexity may make only a limited '
                             'comparator practical.',
  'consideration_priority': 'MUST_ADDRESS_BEFORE_F3A_FREEZE',
  'evidence_ids': 'BAII4E0057;BAII4E0058;BAII4E0059;BAII4E0060',
  'adoption_decision': 'NOT_DECIDED_IN_BAII',
  'notes': 'Consideration priority does not imply implementation or adoption.'},
 {'work_id': 'BAIIW0098',
  'method_name_or_family': 'Fully convolutional neural network (FCN) QPP classifier',
  'target_problem': 'stellar flare detection / upstream event construction',
  'relevant_to_f3a': 'YES',
  'relevant_to_f3b': 'YES',
  'implementation_available': 'NOT_REPORTED',
  'procedure_sufficiently_defined': 'YES',
  'comparison_value': 'Direct QPP classifier with synthetic known truth; central comparator for reference-label '
                      'strategy and later F3B validation.',
  'comparison_cost_or_risk': 'Signal-family mismatch and classifier retraining/transfer to TESS must be handled '
                             'explicitly.',
  'consideration_priority': 'MUST_ADDRESS_BEFORE_F3A_FREEZE',
  'evidence_ids': 'BAII4E0097;BAII4E0098;BAII4E0099;BAII4E0100',
  'adoption_decision': 'NOT_DECIDED_IN_BAII',
  'notes': 'Consideration priority does not imply implementation or adoption.'},
 {'work_id': 'BAIIW0145',
  'method_name_or_family': 'flatwrm2 LSTM flare detection',
  'target_problem': 'stellar flare detection / upstream event construction',
  'relevant_to_f3a': 'YES',
  'relevant_to_f3b': 'NO',
  'implementation_available': 'NOT_REPORTED',
  'procedure_sufficiently_defined': 'YES',
  'comparison_value': 'Large TESS LSTM flare catalogue provides an alternative upstream catalogue/event-selection '
                      'pipeline.',
  'comparison_cost_or_risk': 'Reproducing catalogue construction may be unnecessary if used only for positioning or '
                             'sensitivity checks.',
  'consideration_priority': 'MUST_ADDRESS_BEFORE_F3A_FREEZE',
  'evidence_ids': 'BAII4E0113;BAII4E0114;BAII4E0115;BAII4E0116',
  'adoption_decision': 'NOT_DECIDED_IN_BAII',
  'notes': 'Consideration priority does not imply implementation or adoption.'},
 {'work_id': 'BAIIW0147',
  'method_name_or_family': 'Wavelet-based denoising + flare detection',
  'target_problem': 'QPP classification/detection',
  'relevant_to_f3a': 'NO',
  'relevant_to_f3b': 'YES',
  'implementation_available': 'NOT_REPORTED',
  'procedure_sufficiently_defined': 'YES',
  'comparison_value': 'Wavelet denoising plus injection–recovery gives a concrete low-energy '
                      'detection/selection-function analogue for F3B.',
  'comparison_cost_or_risk': 'CHEOPS/low-energy context does not transfer directly to TESS QPP selection.',
  'consideration_priority': 'MUST_ADDRESS_BEFORE_F3B_FREEZE',
  'evidence_ids': 'BAII4E0117;BAII4E0118;BAII4E0119;BAII4E0120',
  'adoption_decision': 'NOT_DECIDED_IN_BAII',
  'notes': 'Consideration priority does not imply implementation or adoption.'},
 {'work_id': 'BAIIW0149',
  'method_name_or_family': 'ardor multitier flare-detection pipeline',
  'target_problem': 'stellar flare detection / upstream event construction',
  'relevant_to_f3a': 'YES',
  'relevant_to_f3b': 'YES',
  'implementation_available': 'NOT_REPORTED',
  'procedure_sufficiently_defined': 'YES',
  'comparison_value': 'Multitier TESS flare pipeline with injection tests informs event selection and '
                      'completeness/false-selection handling.',
  'comparison_cost_or_risk': 'Planet-host target selection differs from the prospective F3A universe; only '
                             'pipeline/validation features are transferable.',
  'consideration_priority': 'MUST_ADDRESS_BEFORE_F3A_FREEZE',
  'evidence_ids': 'BAII4E0121;BAII4E0122;BAII4E0123;BAII4E0124',
  'adoption_decision': 'NOT_DECIDED_IN_BAII',
  'notes': 'Consideration priority does not imply implementation or adoption.'},
 {'work_id': 'BAIIW0154',
  'method_name_or_family': 'Logistic regression + FRED template flare detection',
  'target_problem': 'stellar flare detection / upstream event construction',
  'relevant_to_f3a': 'NO',
  'relevant_to_f3b': 'YES',
  'implementation_available': 'NOT_REPORTED',
  'procedure_sufficiently_defined': 'YES',
  'comparison_value': 'Template/logistic detection with injection–recovery is a useful methodological validation '
                      'analogue outside TESS.',
  'comparison_cost_or_risk': 'Ground-based cadence/noise differs from TESS; comparator value is methodological rather '
                             'than observationally direct.',
  'consideration_priority': 'MUST_ADDRESS_BEFORE_F3B_FREEZE',
  'evidence_ids': 'BAII4E0129;BAII4E0130;BAII4E0131;BAII4E0132',
  'adoption_decision': 'NOT_DECIDED_IN_BAII',
  'notes': 'Consideration priority does not imply implementation or adoption.'},
 {'work_id': 'BAIIW0156',
  'method_name_or_family': 'flarenet 1D convolutional neural network',
  'target_problem': 'stellar flare detection / upstream event construction',
  'relevant_to_f3a': 'YES',
  'relevant_to_f3b': 'YES',
  'implementation_available': 'NOT_REPORTED',
  'procedure_sufficiently_defined': 'YES',
  'comparison_value': 'TESS 20-s CNN flare detector with synthetic injections, quality/gap handling and threshold '
                      'dependence informs both upstream selection and F3B.',
  'comparison_cost_or_risk': 'Primarily flare, not QPP, detection; incorporation could conflate upstream event '
                             'selection with QPP classification.',
  'consideration_priority': 'MUST_ADDRESS_BEFORE_F3B_FREEZE',
  'evidence_ids': 'BAII4E0133;BAII4E0134;BAII4E0135;BAII4E0136',
  'adoption_decision': 'NOT_DECIDED_IN_BAII',
  'notes': 'Consideration priority does not imply implementation or adoption.'},
 {'work_id': 'BAIIW0168',
  'method_name_or_family': 'VAE surrogate + Celerite + HMM additive Bayesian flare model',
  'target_problem': 'stellar flare detection / upstream event construction',
  'relevant_to_f3a': 'YES',
  'relevant_to_f3b': 'YES',
  'implementation_available': 'NOT_REPORTED',
  'procedure_sufficiently_defined': 'YES',
  'comparison_value': 'Bayesian additive GP/HMM model offers a principled processing comparator and simulation '
                      'framework.',
  'comparison_cost_or_risk': 'Computational and modeling complexity may be disproportionate unless used as a focused '
                             'processing comparator.',
  'consideration_priority': 'MUST_ADDRESS_BEFORE_F3A_FREEZE',
  'evidence_ids': 'BAII4E0141;BAII4E0142;BAII4E0143;BAII4E0144',
  'adoption_decision': 'NOT_DECIDED_IN_BAII',
  'notes': 'Consideration priority does not imply implementation or adoption.'}]
F3B_ROWS = [{'consideration_id': 'F3BC001',
  'source_work_ids': 'BAIIW0024',
  'relevant_f3b_dimension': 'F3B_INJECTION_RECOVERY',
  'literature_approach': 'Injection–recovery=YES; completeness=YES; false-selection=YES.',
  'potential_project_relevance': 'This provides a concrete literature analogue that should constrain the prospective '
                                 'F3B choice without being copied automatically.',
  'must_consider_before_f3b_freeze': 'YES',
  'evidence_ids': 'BAII4E0030;BAII4E0031;BAII4E0032',
  'current_project_requirement': 'Phase 3B is reserved for realistic injection-recovery and independent held-out '
                                 'validation.',
  'remaining_design_question': 'Specify how the future F3B implementation will use or distinguish this literature '
                               'approach while preserving explicit known truth, prospective success criteria, and '
                               'independent validation.',
  'status': 'OPEN_FOR_F3B_DESIGN'},
 {'consideration_id': 'F3BC002',
  'source_work_ids': 'BAIIW0071',
  'relevant_f3b_dimension': 'F3B_SELECTION_FUNCTION',
  'literature_approach': 'Selection function=YES; completeness=YES; false-selection=NOT_REPORTED.',
  'potential_project_relevance': 'This provides a concrete literature analogue that should constrain the prospective '
                                 'F3B choice without being copied automatically.',
  'must_consider_before_f3b_freeze': 'YES',
  'evidence_ids': 'BAII4E0094;BAII4E0095;BAII4E0096',
  'current_project_requirement': 'Any correction/performance program requires explicit known truth and prospectively '
                                 'defined success criteria; selection/recovery performance belongs to Phase 3B rather '
                                 'than observational F3A.',
  'remaining_design_question': 'Specify how the future F3B implementation will use or distinguish this literature '
                               'approach while preserving explicit known truth, prospective success criteria, and '
                               'independent validation.',
  'status': 'OPEN_FOR_F3B_DESIGN'},
 {'consideration_id': 'F3BC003',
  'source_work_ids': 'BAIIW0098',
  'relevant_f3b_dimension': 'F3B_SYNTHETIC_GROUND_TRUTH',
  'literature_approach': 'Synthetic data=YES; ground truth known=YES; signal family=Exponentially decaying harmonic '
                         'QPP versus no-QPP synthetic flare families..',
  'potential_project_relevance': 'This provides a concrete literature analogue that should constrain the prospective '
                                 'F3B choice without being copied automatically.',
  'must_consider_before_f3b_freeze': 'YES',
  'evidence_ids': 'BAII4E0098;BAII4E0099;BAII4E0100',
  'current_project_requirement': 'Explicit synthetic ground truth is required for classification and period; '
                                 'observational roles must not be treated as physical truth.',
  'remaining_design_question': 'Specify how the future F3B implementation will use or distinguish this literature '
                               'approach while preserving explicit known truth, prospective success criteria, and '
                               'independent validation.',
  'status': 'OPEN_FOR_F3B_DESIGN'},
 {'consideration_id': 'F3BC004',
  'source_work_ids': 'BAIIW0147',
  'relevant_f3b_dimension': 'F3B_SELECTION_FUNCTION',
  'literature_approach': 'Selection function=YES; completeness=YES; false-selection=NOT_REPORTED.',
  'potential_project_relevance': 'This provides a concrete literature analogue that should constrain the prospective '
                                 'F3B choice without being copied automatically.',
  'must_consider_before_f3b_freeze': 'YES',
  'evidence_ids': 'BAII4E0118;BAII4E0119;BAII4E0120',
  'current_project_requirement': 'Any correction/performance program requires explicit known truth and prospectively '
                                 'defined success criteria; selection/recovery performance belongs to Phase 3B rather '
                                 'than observational F3A.',
  'remaining_design_question': 'Specify how the future F3B implementation will use or distinguish this literature '
                               'approach while preserving explicit known truth, prospective success criteria, and '
                               'independent validation.',
  'status': 'OPEN_FOR_F3B_DESIGN'},
 {'consideration_id': 'F3BC005',
  'source_work_ids': 'BAIIW0149',
  'relevant_f3b_dimension': 'F3B_INJECTION_RECOVERY',
  'literature_approach': 'Injection–recovery=YES; completeness=YES; false-selection=YES.',
  'potential_project_relevance': 'This provides a concrete literature analogue that should constrain the prospective '
                                 'F3B choice without being copied automatically.',
  'must_consider_before_f3b_freeze': 'YES',
  'evidence_ids': 'BAII4E0122;BAII4E0123;BAII4E0124',
  'current_project_requirement': 'Phase 3B is reserved for realistic injection-recovery and independent held-out '
                                 'validation.',
  'remaining_design_question': 'Specify how the future F3B implementation will use or distinguish this literature '
                               'approach while preserving explicit known truth, prospective success criteria, and '
                               'independent validation.',
  'status': 'OPEN_FOR_F3B_DESIGN'},
 {'consideration_id': 'F3BC006',
  'source_work_ids': 'BAIIW0150',
  'relevant_f3b_dimension': 'F3B_SELECTION_FUNCTION',
  'literature_approach': 'Selection function=YES; completeness=YES; false-selection=NOT_REPORTED.',
  'potential_project_relevance': 'This provides a concrete literature analogue that should constrain the prospective '
                                 'F3B choice without being copied automatically.',
  'must_consider_before_f3b_freeze': 'YES',
  'evidence_ids': 'BAII4E0126;BAII4E0127;BAII4E0128',
  'current_project_requirement': 'Any correction/performance program requires explicit known truth and prospectively '
                                 'defined success criteria; selection/recovery performance belongs to Phase 3B rather '
                                 'than observational F3A.',
  'remaining_design_question': 'Specify how the future F3B implementation will use or distinguish this literature '
                               'approach while preserving explicit known truth, prospective success criteria, and '
                               'independent validation.',
  'status': 'OPEN_FOR_F3B_DESIGN'},
 {'consideration_id': 'F3BC007',
  'source_work_ids': 'BAIIW0154',
  'relevant_f3b_dimension': 'F3B_INJECTION_RECOVERY',
  'literature_approach': 'Injection–recovery=YES; completeness=YES; false-selection=NOT_REPORTED.',
  'potential_project_relevance': 'This provides a concrete literature analogue that should constrain the prospective '
                                 'F3B choice without being copied automatically.',
  'must_consider_before_f3b_freeze': 'YES',
  'evidence_ids': 'BAII4E0130;BAII4E0131;BAII4E0132',
  'current_project_requirement': 'Phase 3B is reserved for realistic injection-recovery and independent held-out '
                                 'validation.',
  'remaining_design_question': 'Specify how the future F3B implementation will use or distinguish this literature '
                               'approach while preserving explicit known truth, prospective success criteria, and '
                               'independent validation.',
  'status': 'OPEN_FOR_F3B_DESIGN'},
 {'consideration_id': 'F3BC008',
  'source_work_ids': 'BAIIW0156',
  'relevant_f3b_dimension': 'F3B_SYNTHETIC_GROUND_TRUTH',
  'literature_approach': 'Synthetic data=YES; ground truth known=YES; signal family=Synthetic Llamaradas Estelares '
                         'flare profiles injected into real quiescent TESS backgrounds..',
  'potential_project_relevance': 'This provides a concrete literature analogue that should constrain the prospective '
                                 'F3B choice without being copied automatically.',
  'must_consider_before_f3b_freeze': 'YES',
  'evidence_ids': 'BAII4E0134;BAII4E0135;BAII4E0136',
  'current_project_requirement': 'Explicit synthetic ground truth is required for classification and period; '
                                 'observational roles must not be treated as physical truth.',
  'remaining_design_question': 'Specify how the future F3B implementation will use or distinguish this literature '
                               'approach while preserving explicit known truth, prospective success criteria, and '
                               'independent validation.',
  'status': 'OPEN_FOR_F3B_DESIGN'},
 {'consideration_id': 'F3BC009',
  'source_work_ids': 'BAIIW0168',
  'relevant_f3b_dimension': 'F3B_SYNTHETIC_GROUND_TRUTH',
  'literature_approach': 'Synthetic data=YES; ground truth known=YES; signal family=Simulated GP/background structure '
                         'used to test surrogate fidelity..',
  'potential_project_relevance': 'This provides a concrete literature analogue that should constrain the prospective '
                                 'F3B choice without being copied automatically.',
  'must_consider_before_f3b_freeze': 'YES',
  'evidence_ids': 'BAII4E0142;BAII4E0143;BAII4E0144',
  'current_project_requirement': 'Explicit synthetic ground truth is required for classification and period; '
                                 'observational roles must not be treated as physical truth.',
  'remaining_design_question': 'Specify how the future F3B implementation will use or distinguish this literature '
                               'approach while preserving explicit known truth, prospective success criteria, and '
                               'independent validation.',
  'status': 'OPEN_FOR_F3B_DESIGN'}]
SUPPLEMENTAL_ROWS = [{'supplemental_id': 'SUP001',
  'title': 'Stellar flare study of nearby young moving group members with TESS Data',
  'identifier': 'arXiv:2602.20402',
  'discovery_route': 'BAII.4 source verification / citation chasing',
  'discovery_work_id': 'BAIIW0182',
  'systematic_corpus_member': 'false',
  'systematic_denominator_effect': 'NONE',
  'contextual_relevance': 'TESS stellar-flare catalogue/detection context in 417 nearby-young-moving-group members; '
                          'the abstract reports 6,288 flares from 27,416 candidates and cadence-dependent recovery, '
                          'but no QPP analysis.',
  'f3a_relevance': 'CONTEXT_ONLY: upstream TESS flare selection/cadence context; not a direct QPP/F3A gate trigger.',
  'f3b_relevance': 'CONTEXT_ONLY: detection/recovery language may inform general flare-selection context, but the '
                   'abstract does not establish the project-specific F3B architecture.',
  'source_checked': 'arXiv:2602.20402 abstract (submitted 2026-02-23); related journal DOI 10.3847/1538-4357/ae44f2 '
                    'listed by arXiv.',
  'assessment': 'RECENT_NON_SYSTEMATIC_CONTEXT_ONLY',
  'allowed_use': 'Contextual citation or later design discussion with explicit supplemental status.',
  'prohibited_use': 'Do not add to 190 systematic work_ids, 40 included works, or use as a retroactive gate '
                    'denominator.'}]
F3A_REQUIREMENT_ROWS = [{'requirement_id': 'F3AR001',
  'requirement_category': 'COHORT_UNIVERSE',
  'source_work_ids': 'BAIIW0001;BAIIW0003;BAIIW0023;BAIIW0145',
  'source_evidence_ids': 'BAII4E0001;BAII4E0002;BAII4E0003;BAII4E0004;BAII4E0009;BAII4E0010;BAII4E0011;BAII4E0012;BAII4E0025;BAII4E0026;BAII4E0027;BAII4E0028;BAII4E0113;BAII4E0114;BAII4E0115;BAII4E0116',
  'issue': 'Catalogue-scale TESS flare/QPP populations already exist at multiple cadences and scales.',
  'why_it_matters': 'F3A cannot define its contribution merely as scaling QPP analysis to a larger TESS catalogue; the '
                    'cohort universe must be chosen for a distinct robustness question.',
  'current_f3a_reference': 'Prospectively defined catalogue-scale observational cohort; source catalogue(s), '
                           'eligibility criteria, cohort construction, inclusion/exclusion, duplicates/repeated '
                           'observations and observational roles/strata must be frozen before execution.',
  'required_design_question': 'Which source catalogue(s), cadence regime, sectors, target classes and observational '
                              'strata define the prospective F3A cohort, and why is that cohort appropriate for the '
                              'robustness question rather than a duplicate catalogue exercise?',
  'must_resolve_before_f3a_freeze': 'YES',
  'resolution_status': 'OPEN_FOR_F3A_DESIGN',
  'allowed_resolution_types': 'PROSPECTIVE_COHORT_DEFINITION;BOUNDED_SCOPE_JUSTIFICATION;EXTERNAL_CATALOG_SELECTION',
  'prohibited_shortcut': 'Do not justify the cohort by claiming catalogue-scale TESS QPP work does not already exist.'},
 {'requirement_id': 'F3AR002',
  'requirement_category': 'CATALOG_SOURCE',
  'source_work_ids': 'BAIIW0001;BAIIW0003;BAIIW0023;BAIIW0145',
  'source_evidence_ids': 'BAII4E0001;BAII4E0002;BAII4E0003;BAII4E0004;BAII4E0009;BAII4E0010;BAII4E0011;BAII4E0012;BAII4E0025;BAII4E0026;BAII4E0027;BAII4E0028;BAII4E0113;BAII4E0114;BAII4E0115;BAII4E0116',
  'issue': 'Different published TESS catalogue-construction pipelines produce materially different flare universes.',
  'why_it_matters': 'Upstream catalogue construction can change the events available for QPP classification and '
                    'therefore the apparent robustness sample.',
  'current_f3a_reference': 'Catalogue-scale observational robustness extending the frozen ten-event F2 pilot to a '
                           'substantially broader prospectively defined observational cohort.',
  'required_design_question': 'Will F3A freeze an existing catalogue, construct a new flare universe, or compare '
                              'catalogue sources; and what provenance contract prevents upstream selection from being '
                              'conflated with QPP robustness?',
  'must_resolve_before_f3a_freeze': 'YES',
  'resolution_status': 'OPEN_FOR_F3A_DESIGN',
  'allowed_resolution_types': 'FREEZE_EXISTING_CATALOG;PROSPECTIVE_RECONSTRUCTION;PREDECLARED_MULTI_CATALOG_SENSITIVITY',
  'prohibited_shortcut': 'Do not select a catalogue after seeing F3A outcomes.'},
 {'requirement_id': 'F3AR003',
  'requirement_category': 'EVENT_SELECTION',
  'source_work_ids': 'BAIIW0023;BAIIW0145;BAIIW0149',
  'source_evidence_ids': 'BAII4E0025;BAII4E0026;BAII4E0027;BAII4E0028;BAII4E0113;BAII4E0114;BAII4E0115;BAII4E0116;BAII4E0121;BAII4E0122;BAII4E0123;BAII4E0124',
  'issue': 'Automated flare-detection and vetting pipelines encode target/event-selection choices before QPP analysis.',
  'why_it_matters': 'F3A event eligibility and duplicate/repeated-observation handling must be independent of the '
                    'eventual robustness result.',
  'current_f3a_reference': 'Event eligibility, cohort construction, inclusion/exclusion, duplicate handling and '
                           'provenance/selection of QPP-labelled or comparison events must be defined prospectively; '
                           'candidate discovery is not authorized.',
  'required_design_question': 'What exact eligibility, duplicate handling, repeated-sector treatment and flare-event '
                              'provenance rules are frozen before execution?',
  'must_resolve_before_f3a_freeze': 'YES',
  'resolution_status': 'OPEN_FOR_F3A_DESIGN',
  'allowed_resolution_types': 'PREDECLARED_ELIGIBILITY;PREDECLARED_DUPLICATE_POLICY;PREDECLARED_OBSERVATION_ROLE',
  'prohibited_shortcut': 'Do not use F3A output to discover or promote candidate events into the cohort.'},
 {'requirement_id': 'F3AR004',
  'requirement_category': 'QPP_REFERENCE_LABELS',
  'source_work_ids': 'BAIIW0001;BAIIW0003;BAIIW0098',
  'source_evidence_ids': 'BAII4E0001;BAII4E0002;BAII4E0003;BAII4E0004;BAII4E0009;BAII4E0010;BAII4E0011;BAII4E0012;BAII4E0097;BAII4E0098;BAII4E0099;BAII4E0100',
  'issue': 'Included literature uses both AFINO and neural-network QPP classifications, while observational labels are '
           'not physical truth.',
  'why_it_matters': 'F3A needs an independent reference-label/provenance contract and must distinguish robustness of a '
                    'classifier from validation against known truth.',
  'current_f3a_reference': 'QPP-labelled/comparison-event provenance and selection rules must be independent of the '
                           'F3A output; F3A cannot establish physical truth, sensitivity/specificity, observational '
                           'false-positive rate or true-negative status.',
  'required_design_question': 'Which QPP-labelled and comparison events are admissible as observational references, '
                              'how are conflicting labels handled, and which classifier(s) are baseline versus '
                              'comparator?',
  'must_resolve_before_f3a_freeze': 'YES',
  'resolution_status': 'OPEN_FOR_F3A_DESIGN',
  'allowed_resolution_types': 'INDEPENDENT_REFERENCE_LABELS;PREDECLARED_BASELINE_CLASSIFIER;PREDECLARED_COMPARATOR_SET',
  'prohibited_shortcut': 'Do not treat observational non-selection as a true negative or catalogue labels as physical '
                         'ground truth.'},
 {'requirement_id': 'F3AR005',
  'requirement_category': 'WINDOW_ROBUSTNESS',
  'source_work_ids': 'BAIIW0004',
  'source_evidence_ids': 'BAII4E0013;BAII4E0014;BAII4E0015;BAII4E0016',
  'issue': 'QPP conclusions can depend on explicit window/detrending choices, and wavelet analysis provides a concrete '
           'alternative window-sensitive procedure.',
  'why_it_matters': 'Temporal-window dependence is already a recognized methodological dimension and cannot be left '
                    'implicit.',
  'current_f3a_reference': 'Temporal-window dependence is a primary observational-robustness dimension; future F3A '
                           'must freeze temporal-window perturbations rather than silently inherit the F2 grid.',
  'required_design_question': 'Which temporal-window perturbations are scientifically meaningful, how are they '
                              'generated, and what summary defines classification robustness across them?',
  'must_resolve_before_f3a_freeze': 'YES',
  'resolution_status': 'OPEN_FOR_F3A_DESIGN',
  'allowed_resolution_types': 'PREDECLARED_WINDOW_GRID;PHYSICALLY_MOTIVATED_WINDOW_SET',
  'prohibited_shortcut': 'Do not inherit the F2 window grid silently or tune windows after seeing catalogue results.'},
 {'requirement_id': 'F3AR006',
  'requirement_category': 'PROCESSING_ROBUSTNESS',
  'source_work_ids': 'BAIIW0024;BAIIW0037;BAIIW0168',
  'source_evidence_ids': 'BAII4E0029;BAII4E0030;BAII4E0031;BAII4E0032;BAII4E0057;BAII4E0058;BAII4E0059;BAII4E0060;BAII4E0141;BAII4E0142;BAII4E0143;BAII4E0144',
  'issue': 'Alternative baseline, detrending and stochastic-process models can change flare/event representations.',
  'why_it_matters': 'F3A explicitly targets dependence on processing choices; literature provides concrete '
                    'alternatives that must at least be considered.',
  'current_f3a_reference': 'Dependence on processing choices is a primary observational-robustness dimension; '
                           'processing profiles must be explicitly frozen prospectively.',
  'required_design_question': 'Which processing profiles are part of the frozen robustness matrix, which are out of '
                              'scope, and what scientific rationale governs that boundary?',
  'must_resolve_before_f3a_freeze': 'YES',
  'resolution_status': 'OPEN_FOR_F3A_DESIGN',
  'allowed_resolution_types': 'PREDECLARED_PROCESSING_PROFILES;JUSTIFIED_EXCLUSION_OF_COMPARATORS',
  'prohibited_shortcut': 'Do not add or remove processing profiles after observing which ones preserve QPP '
                         'selections.'},
 {'requirement_id': 'F3AR007',
  'requirement_category': 'QUALITY_GAPS',
  'source_work_ids': 'BAIIW0156;BAIIW0145',
  'source_evidence_ids': 'BAII4E0133;BAII4E0134;BAII4E0135;BAII4E0136;BAII4E0113;BAII4E0114;BAII4E0115;BAII4E0116',
  'issue': 'Quality filtering, gap filling and input admissibility can be explicit parts of automated flare pipelines.',
  'why_it_matters': 'F3A must keep inadmissible/failed inputs separate from non-selection and prospectively define '
                    'missingness handling.',
  'current_f3a_reference': 'Admissibility and failed/missing execution handling must remain explicit; input '
                           'inadmissibility is not non-selection. The future design must freeze an admissibility '
                           'contract and missingness/failed-execution handling.',
  'required_design_question': 'What TESS quality flags, gap thresholds/filling policies and failed-execution states '
                              'are admissible, and how are they represented in denominators?',
  'must_resolve_before_f3a_freeze': 'YES',
  'resolution_status': 'OPEN_FOR_F3A_DESIGN',
  'allowed_resolution_types': 'ADMISSIBILITY_CONTRACT;PREDECLARED_GAP_POLICY;EXPLICIT_FAILED_EXECUTION_STATE',
  'prohibited_shortcut': 'Do not recode inadmissible or failed executions as QPP negatives.'},
 {'requirement_id': 'F3AR008',
  'requirement_category': 'NUMERICAL_STABILITY',
  'source_work_ids': 'BAIIW0190;BAIIW0001',
  'source_evidence_ids': 'BAII4E0157;BAII4E0158;BAII4E0159;BAII4E0160;BAII4E0001;BAII4E0002;BAII4E0003;BAII4E0004',
  'issue': 'AFINO is an automated model-comparison implementation, but the software record does not establish '
           'optimizer uniqueness or seed stability.',
  'why_it_matters': 'The project already separates classification robustness from numerical optimization behavior; the '
                    'catalogue-scale design must retain that separation.',
  'current_f3a_reference': 'Classification robustness and optimizer behaviour are separate evidence planes. '
                           'Optimizer-seed policy and numerical diagnostics must be frozen; warnings, bounds, '
                           'convergence limitations and numerical multiplicity remain reportable. Stable '
                           'classification does not demonstrate a unique numerical optimum.',
  'required_design_question': 'What optimizer-seed policy, warnings/bounds/convergence diagnostics and numerical '
                              'multiplicity summaries will be frozen for F3A?',
  'must_resolve_before_f3a_freeze': 'YES',
  'resolution_status': 'OPEN_FOR_F3A_DESIGN',
  'allowed_resolution_types': 'PREDECLARED_SEED_POLICY;NUMERICAL_DIAGNOSTIC_CONTRACT',
  'prohibited_shortcut': 'Do not interpret stable classification alone as proof of a unique numerical optimum.'},
 {'requirement_id': 'F3AR009',
  'requirement_category': 'COMPARATOR_STRATEGY',
  'source_work_ids': 'BAIIW0004;BAIIW0023;BAIIW0024;BAIIW0037;BAIIW0098;BAIIW0145;BAIIW0147;BAIIW0149;BAIIW0154;BAIIW0156;BAIIW0168',
  'source_evidence_ids': 'BAII4E0013;BAII4E0014;BAII4E0015;BAII4E0016;BAII4E0025;BAII4E0026;BAII4E0027;BAII4E0028;BAII4E0029;BAII4E0030;BAII4E0031;BAII4E0032;BAII4E0057;BAII4E0058;BAII4E0059;BAII4E0060;BAII4E0097;BAII4E0098;BAII4E0099;BAII4E0100;BAII4E0113;BAII4E0114;BAII4E0115;BAII4E0116;BAII4E0117;BAII4E0118;BAII4E0119;BAII4E0120;BAII4E0121;BAII4E0122;BAII4E0123;BAII4E0124;BAII4E0129;BAII4E0130;BAII4E0131;BAII4E0132;BAII4E0133;BAII4E0134;BAII4E0135;BAII4E0136;BAII4E0141;BAII4E0142;BAII4E0143;BAII4E0144',
  'issue': 'BAII.4 identified 11 sufficiently defined methodological comparator candidates.',
  'why_it_matters': 'F3A must decide prospectively which comparators are necessary to support the robustness claim and '
                    'which are positioning-only or reserved for F3B.',
  'current_f3a_reference': 'The F3 comparison reference does not freeze a final comparator set.',
  'required_design_question': 'Which of the 11 candidates must be implemented, benchmarked, cited only, or explicitly '
                              'deferred to F3B, and what decision rule justifies each choice?',
  'must_resolve_before_f3a_freeze': 'YES',
  'resolution_status': 'OPEN_FOR_F3A_DESIGN',
  'allowed_resolution_types': 'IMPLEMENT_COMPARATOR;POSITIONING_ONLY;DEFER_TO_F3B;JUSTIFIED_EXCLUSION',
  'prohibited_shortcut': 'Do not equate BAII consideration priority with automatic adoption.'},
 {'requirement_id': 'F3AR010',
  'requirement_category': 'POSITIONING',
  'source_work_ids': 'BAIIW0001;BAIIW0003',
  'source_evidence_ids': 'BAII4E0001;BAII4E0002;BAII4E0003;BAII4E0004;BAII4E0009;BAII4E0010;BAII4E0011;BAII4E0012',
  'issue': 'Catalogue-scale TESS QPP analysis and TESS catalogue QPP classification already appear in the included '
           'literature.',
  'why_it_matters': 'The future contribution must be framed around the project-specific robustness design rather than '
                    'catalogue scale or TESS/QPP usage alone.',
  'current_f3a_reference': 'BAII.4 prospective F3A role and overlap assessment.',
  'required_design_question': 'What exact bounded contribution can F3A claim after distinguishing it from existing '
                              'catalogue-scale TESS QPP and machine-learning classification work?',
  'must_resolve_before_f3a_freeze': 'YES',
  'resolution_status': 'POSITIONING_ONLY',
  'allowed_resolution_types': 'BOUNDED_CONTRIBUTION_STATEMENT;PRECEDENCE_SAFE_WORDING',
  'prohibited_shortcut': 'Do not use first-study, no-previous-work or scooped language.'}]
LIMITATION_ROWS = [{'limitation_id': 'LIM001',
  'category': 'SEARCH_WINDOW',
  'description': 'The systematic recent-literature search was bounded to 2024-01-01 through the 2026-08-07 search '
                 'freeze.',
  'effect_on_gate': 'The gate is evidence-based for the frozen window but cannot represent literature outside it '
                    'exhaustively.',
  'mitigation': 'Use bounded wording and preserve the frozen search date.',
  'remaining_risk': 'Relevant earlier or post-freeze work may exist outside the systematic retrieval.',
  'manuscript_implication': 'Do not generalize corpus non-retrieval to universal absence.'},
 {'limitation_id': 'LIM002',
  'category': 'PROVIDERS',
  'description': 'Systematic retrieval used two principal providers, SciX/ADS and arXiv.',
  'effect_on_gate': 'Coverage is strong for astrophysics but not logically exhaustive of all indexing systems.',
  'mitigation': 'Preserve provider provenance and use only bounded corpus claims.',
  'remaining_risk': 'Relevant records absent from both providers may not have entered the corpus.',
  'manuscript_implication': 'Avoid exhaustive priority claims.'},
 {'limitation_id': 'LIM003',
  'category': 'FROZEN_QUERIES',
  'description': 'The corpus depends on the preregistered query families and the v1.1.0 technical SciX '
                 'date-serialization amendment.',
  'effect_on_gate': 'The gate inherits the sensitivity and blind spots of those frozen queries.',
  'mitigation': 'Do not retrospectively broaden terms; document missed candidates separately.',
  'remaining_risk': 'Relevant terminology outside the frozen queries may have been missed.',
  'manuscript_implication': 'Describe the audit as systematic under the frozen protocol, not exhaustive of all '
                            'possible phrasing.'},
 {'limitation_id': 'LIM004',
  'category': 'BACKGROUND_ONLY',
  'description': 'Thirty-three BACKGROUND_ONLY works were outside the 40-work primary structured-extraction '
                 'denominator.',
  'effect_on_gate': 'They provide context but were not subjected to the same full BAII.4 extraction matrix.',
  'mitigation': 'Do not mix them into the primary 40-work denominator; cite as context only when needed.',
  'remaining_risk': 'A contextual methodological nuance may not be represented in primary extraction fields.',
  'manuscript_implication': 'Keep denominators explicit.'},
 {'limitation_id': 'LIM005',
  'category': 'SOURCE_ACCESS',
  'description': 'Five BAII.4 works retain documented access limitations.',
  'effect_on_gate': 'Unresolved details cannot be used as affirmative evidence; BAIIW0003 is therefore interpreted '
                    'only at the supported catalogue/classifier level.',
  'mitigation': 'Use NOT_REPORTED and rely on independently sufficient gate evidence such as BAIIW0001.',
  'remaining_risk': 'Full-text details could refine, but not currently reverse, some bounded assessments.',
  'manuscript_implication': 'Flag access-limited claims and avoid over-specific descriptions.'},
 {'limitation_id': 'LIM006',
  'category': 'FULL_TEXT_COVERAGE',
  'description': 'Only three works were extracted primarily from full text.',
  'effect_on_gate': 'Methodological detail is uneven across the corpus.',
  'mitigation': 'Restrict strong design claims to evidence explicitly available at the extracted source level.',
  'remaining_risk': 'Some implementation details may remain unresolved.',
  'manuscript_implication': 'Do not imply uniform full-text review of all 40 works.'},
 {'limitation_id': 'LIM007',
  'category': 'ABSTRACT_COVERAGE',
  'description': 'Thirty-five works were extracted primarily from abstracts.',
  'effect_on_gate': 'Abstracts support high-level scope/method conclusions but may not resolve all validation or '
                    'numerical details.',
  'mitigation': 'Encode unresolved fields as NOT_REPORTED and separate high-level overlap from detailed implementation '
                'claims.',
  'remaining_risk': 'Fine-grained comparator feasibility may require later full-text review during design.',
  'manuscript_implication': 'Use cautious method-detail wording.'},
 {'limitation_id': 'LIM008',
  'category': 'SUPPLEMENTAL_CITATION',
  'description': 'One recent citation candidate, arXiv:2602.20402, was discovered outside the frozen systematic route.',
  'effect_on_gate': 'It may inform context but cannot alter the 190/40 denominators or become a retrospective '
                    'systematic hit.',
  'mitigation': 'Record it in supplemental_context_registry.csv with denominator effect NONE.',
  'remaining_risk': 'Other citation-chased papers may exist but were not converted into systematic evidence.',
  'manuscript_implication': 'Clearly separate systematic and supplemental citations.'},
 {'limitation_id': 'LIM009',
  'category': 'ABSENCE_INFERENCE',
  'description': 'Failure to retrieve an exact precedent cannot be converted into proof that no such literature '
                 'exists.',
  'effect_on_gate': 'Negative priority claims are not authorized.',
  'mitigation': 'Phrase negatives as “No included work in Bibliographic Audit II was found to...” when justified.',
  'remaining_risk': 'Unretrieved literature can invalidate universal absence claims.',
  'manuscript_implication': 'Avoid “first”, “no previous study” and equivalent priority language unless independently '
                            'established later.'},
 {'limitation_id': 'LIM010',
  'category': 'F3_REFERENCE',
  'description': 'Prospective impact was assessed against the pre-extraction F3 comparison micro-freeze, not a final '
                 'F3A design.',
  'effect_on_gate': 'BAII.5 determines what must be reconsidered before design freeze; it does not adjudicate a final '
                    'protocol.',
  'mitigation': 'Express outputs as open F3A design requirements.',
  'remaining_risk': 'The eventual redesigned F3A may resolve some concerns without implementing every literature '
                    'method.',
  'manuscript_implication': 'Do not present BAII.5 requirements as already adopted methods.'},
 {'limitation_id': 'LIM011',
  'category': 'NOVELTY',
  'description': 'Bibliographic Audit II did not conduct a formal global novelty assessment.',
  'effect_on_gate': 'The gate can constrain positioning and design but cannot authorize priority claims.',
  'mitigation': 'Set novelty_assessed=false and priority_claim_authorized=false.',
  'remaining_risk': 'A separate broader precedence analysis could alter wording later.',
  'manuscript_implication': 'Use bounded contribution statements only.'},
 {'limitation_id': 'LIM012',
  'category': 'COMPARATOR_ADOPTION',
  'description': 'BAII.5 evaluates consideration priority for 11 comparator candidates but does not adopt any '
                 'comparator.',
  'effect_on_gate': 'Method implementation remains a future F3A/F3B design decision.',
  'mitigation': 'Set adoption_decision=NOT_DECIDED_IN_BAII for all candidates.',
  'remaining_risk': 'Feasibility/cost may change after implementation review.',
  'manuscript_implication': 'Do not describe any comparator as part of the final method until a later design freeze.'},
 {'limitation_id': 'LIM013',
  'category': 'POST_FREEZE_LITERATURE',
  'description': 'Literature appearing after the 2026-08-07 search freeze is not covered systematically.',
  'effect_on_gate': 'The decision is frozen to the audit’s temporal scope.',
  'mitigation': 'Future literature updates must be handled as a new version/amendment rather than silently editing '
                'BAII.',
  'remaining_risk': 'Rapidly evolving methods may produce new relevant work.',
  'manuscript_implication': 'State the audit freeze date when making literature-scope statements.'}]
FINAL_EVIDENCE_ROWS = [{'claim_id': 'CLM001',
  'claim_type': 'SYSTEMATIC_CORPUS_FACT',
  'claim_text': 'Bibliographic Audit II resolves the frozen systematic corpus to 190 unique works, of which 40 were '
                'included for structured extraction.',
  'source_work_ids': '',
  'source_evidence_ids': '',
  'source_baii_artifacts': 'screening/screening_manifest.json;extraction/extraction_manifest.json',
  'scope': 'BAII frozen corpus',
  'allowed_interpretation': 'The audit denominator is 190 works with 40 primary extracted works.',
  'prohibited_interpretation': 'The 190 works are all QPP literature or all relevant literature globally.',
  'relevance_to_f3a': 'HIGH',
  'relevance_to_f3b': 'HIGH',
  'relevance_to_manuscript1': 'HIGH',
  'confidence_basis': 'Frozen manifests and validated denominators.'},
 {'claim_id': 'CLM002',
  'claim_type': 'OBSERVATIONAL_OVERLAP',
  'claim_text': 'Two included works have DIRECT F3A overlap under the frozen BAII.4 rubric: BAIIW0001 and BAIIW0003.',
  'source_work_ids': 'BAIIW0001;BAIIW0003',
  'source_evidence_ids': 'BAII4E0001;BAII4E0002;BAII4E0003;BAII4E0004;BAII4E0009;BAII4E0010;BAII4E0011;BAII4E0012',
  'source_baii_artifacts': 'extraction/overlap_assessment.csv;extraction/overlap_dimension_evidence.csv',
  'scope': 'F3A comparison micro-freeze',
  'allowed_interpretation': 'Both works materially overlap catalogue-scale TESS QPP/classification dimensions relevant '
                            'to the prospective F3A contribution.',
  'prohibited_interpretation': 'Either work invalidates F3A or proves the future F3A cannot be novel.',
  'relevance_to_f3a': 'CENTRAL',
  'relevance_to_f3b': 'LOW',
  'relevance_to_manuscript1': 'HIGH',
  'confidence_basis': 'Direct dimensional evidence and critical BAII.5 review.'},
 {'claim_id': 'CLM003',
  'claim_type': 'METHOD_OVERLAP',
  'claim_text': 'BAIIW0001 applies AFINO Fourier model comparison to a catalogue-scale sample of 20-second TESS flares '
                'and reports 61 QPPs across 57 stars.',
  'source_work_ids': 'BAIIW0001',
  'source_evidence_ids': 'BAII4E0001;BAII4E0002;BAII4E0003;BAII4E0004',
  'source_baii_artifacts': 'extraction/included_work_extraction.csv;extraction/extraction_evidence_log.csv',
  'scope': 'BAIIW0001 supported source level',
  'allowed_interpretation': 'Catalogue-scale AFINO/TESS QPP use predates the prospective F3A freeze.',
  'prohibited_interpretation': 'BAIIW0001 implements the complete planned F3A robustness design.',
  'relevance_to_f3a': 'CENTRAL',
  'relevance_to_f3b': 'LOW',
  'relevance_to_manuscript1': 'HIGH',
  'confidence_basis': 'Frozen BAII.4 evidence plus allowed-source arXiv verification.'},
 {'claim_id': 'CLM004',
  'claim_type': 'METHOD_OVERLAP',
  'claim_text': 'BAIIW0003 applies a previously published fully convolutional QPP classifier to a very large TESS '
                'flare catalogue and reports 10,465 M-star flares with QPP features.',
  'source_work_ids': 'BAIIW0003',
  'source_evidence_ids': 'BAII4E0009;BAII4E0010;BAII4E0011;BAII4E0012',
  'source_baii_artifacts': 'extraction/included_work_extraction.csv;extraction/extraction_evidence_log.csv;closure/critical_overlap_review.csv',
  'scope': 'High-level catalogue/classifier facts only',
  'allowed_interpretation': 'Machine-learning QPP classification on large TESS catalogue data predates F3A.',
  'prohibited_interpretation': 'The audit resolves the complete classifier training, validation or selection-function '
                               'architecture.',
  'relevance_to_f3a': 'CENTRAL',
  'relevance_to_f3b': 'MEDIUM',
  'relevance_to_manuscript1': 'HIGH',
  'confidence_basis': 'Frozen provider-level evidence; access limitation retained after BAII.5 recheck.'},
 {'claim_id': 'CLM005',
  'claim_type': 'DESIGN_CONSIDERATION',
  'claim_text': 'Thirteen additional included works carry F3A_DESIGN_ADJUSTMENT_POSSIBLE and identify concrete cohort, '
                'method, processing, quality/gap or numerical considerations.',
  'source_work_ids': 'BAIIW0002;BAIIW0004;BAIIW0023;BAIIW0024;BAIIW0037;BAIIW0071;BAIIW0098;BAIIW0145;BAIIW0149;BAIIW0150;BAIIW0156;BAIIW0168;BAIIW0190',
  'source_evidence_ids': 'BAII4E0005;BAII4E0006;BAII4E0007;BAII4E0008;BAII4E0013;BAII4E0014;BAII4E0015;BAII4E0016;BAII4E0025;BAII4E0026;BAII4E0027;BAII4E0028;BAII4E0029;BAII4E0030;BAII4E0031;BAII4E0032;BAII4E0057;BAII4E0058;BAII4E0059;BAII4E0060;BAII4E0093;BAII4E0094;BAII4E0095;BAII4E0096;BAII4E0097;BAII4E0098;BAII4E0099;BAII4E0100;BAII4E0113;BAII4E0114;BAII4E0115;BAII4E0116;BAII4E0121;BAII4E0122;BAII4E0123;BAII4E0124;BAII4E0125;BAII4E0126;BAII4E0127;BAII4E0128;BAII4E0133;BAII4E0134;BAII4E0135;BAII4E0136;BAII4E0141;BAII4E0142;BAII4E0143;BAII4E0144;BAII4E0157;BAII4E0158;BAII4E0159;BAII4E0160',
  'source_baii_artifacts': 'extraction/overlap_assessment.csv;closure/critical_overlap_review.csv',
  'scope': 'Prospective F3A design consideration',
  'allowed_interpretation': 'These considerations must be addressed or explicitly deferred before F3A freeze.',
  'prohibited_interpretation': 'Every literature method must be implemented in F3A.',
  'relevance_to_f3a': 'HIGH',
  'relevance_to_f3b': 'MEDIUM',
  'relevance_to_manuscript1': 'MEDIUM',
  'confidence_basis': '15/15 critical-impact works reviewed.'},
 {'claim_id': 'CLM006',
  'claim_type': 'DESIGN_CONSIDERATION',
  'claim_text': 'Eleven BAII.4 comparator candidates are sufficiently defined to merit explicit consideration, but no '
                'adoption decision is made in BAII.5.',
  'source_work_ids': 'BAIIW0004;BAIIW0023;BAIIW0024;BAIIW0037;BAIIW0098;BAIIW0145;BAIIW0147;BAIIW0149;BAIIW0154;BAIIW0156;BAIIW0168',
  'source_evidence_ids': 'BAII4E0013;BAII4E0014;BAII4E0015;BAII4E0016;BAII4E0025;BAII4E0026;BAII4E0027;BAII4E0028;BAII4E0029;BAII4E0030;BAII4E0031;BAII4E0032;BAII4E0057;BAII4E0058;BAII4E0059;BAII4E0060;BAII4E0097;BAII4E0098;BAII4E0099;BAII4E0100;BAII4E0113;BAII4E0114;BAII4E0115;BAII4E0116;BAII4E0117;BAII4E0118;BAII4E0119;BAII4E0120;BAII4E0121;BAII4E0122;BAII4E0123;BAII4E0124;BAII4E0129;BAII4E0130;BAII4E0131;BAII4E0132;BAII4E0133;BAII4E0134;BAII4E0135;BAII4E0136;BAII4E0141;BAII4E0142;BAII4E0143;BAII4E0144',
  'source_baii_artifacts': 'extraction/overlap_assessment.csv;closure/comparator_consideration_matrix.csv',
  'scope': 'Comparator consideration',
  'allowed_interpretation': 'Future F3A/F3B design must record how each high-priority comparator is handled.',
  'prohibited_interpretation': 'All 11 comparators are adopted or required to be implemented.',
  'relevance_to_f3a': 'HIGH',
  'relevance_to_f3b': 'HIGH',
  'relevance_to_manuscript1': 'MEDIUM',
  'confidence_basis': '11/11 comparator candidates represented.'},
 {'claim_id': 'CLM007',
  'claim_type': 'VALIDATION_OVERLAP',
  'claim_text': 'Nine included works provide F3B-relevant injection–recovery, synthetic-ground-truth or '
                'selection-function analogues.',
  'source_work_ids': 'BAIIW0024;BAIIW0071;BAIIW0098;BAIIW0147;BAIIW0149;BAIIW0150;BAIIW0154;BAIIW0156;BAIIW0168',
  'source_evidence_ids': 'BAII4E0029;BAII4E0030;BAII4E0031;BAII4E0032;BAII4E0093;BAII4E0094;BAII4E0095;BAII4E0096;BAII4E0097;BAII4E0098;BAII4E0099;BAII4E0100;BAII4E0117;BAII4E0118;BAII4E0119;BAII4E0120;BAII4E0121;BAII4E0122;BAII4E0123;BAII4E0124;BAII4E0125;BAII4E0126;BAII4E0127;BAII4E0128;BAII4E0129;BAII4E0130;BAII4E0131;BAII4E0132;BAII4E0133;BAII4E0134;BAII4E0135;BAII4E0136;BAII4E0141;BAII4E0142;BAII4E0143;BAII4E0144',
  'source_baii_artifacts': 'extraction/overlap_dimension_evidence.csv;closure/f3b_design_considerations.csv',
  'scope': 'Prospective F3B validation design',
  'allowed_interpretation': 'F3B should be designed with explicit awareness of these validation approaches.',
  'prohibited_interpretation': 'These works implement the exact project-specific F3B architecture or must be copied.',
  'relevance_to_f3a': 'LOW',
  'relevance_to_f3b': 'HIGH',
  'relevance_to_manuscript1': 'MEDIUM',
  'confidence_basis': '9/9 F3B-impact works represented.'},
 {'claim_id': 'CLM008',
  'claim_type': 'VALIDATION_OVERLAP',
  'claim_text': 'No included BAII.4 work was assessed as matching the complete project-specific combination of '
                'prospective development/validation separation and independent held-out validation.',
  'source_work_ids': 'BAIIW0024;BAIIW0071;BAIIW0098;BAIIW0147;BAIIW0149;BAIIW0150;BAIIW0154;BAIIW0156;BAIIW0168',
  'source_evidence_ids': 'BAII4E0029;BAII4E0030;BAII4E0031;BAII4E0032;BAII4E0093;BAII4E0094;BAII4E0095;BAII4E0096;BAII4E0097;BAII4E0098;BAII4E0099;BAII4E0100;BAII4E0117;BAII4E0118;BAII4E0119;BAII4E0120;BAII4E0121;BAII4E0122;BAII4E0123;BAII4E0124;BAII4E0125;BAII4E0126;BAII4E0127;BAII4E0128;BAII4E0129;BAII4E0130;BAII4E0131;BAII4E0132;BAII4E0133;BAII4E0134;BAII4E0135;BAII4E0136;BAII4E0141;BAII4E0142;BAII4E0143;BAII4E0144',
  'source_baii_artifacts': 'extraction/included_work_extraction.csv;extraction/overlap_dimension_evidence.csv',
  'scope': 'Only the 40 included BAII.4 works and the frozen F3B reference',
  'allowed_interpretation': 'The complete project-specific architecture was not found among included works.',
  'prohibited_interpretation': 'No previous study anywhere has used development/held-out validation for QPP or flare '
                               'detection.',
  'relevance_to_f3a': 'NONE',
  'relevance_to_f3b': 'HIGH',
  'relevance_to_manuscript1': 'MEDIUM',
  'confidence_basis': 'Bounded negative statement from the structured 40-work corpus.'},
 {'claim_id': 'CLM009',
  'claim_type': 'POSITIONING_CONSTRAINT',
  'claim_text': 'F3A must not be positioned as the first catalogue-scale TESS QPP study.',
  'source_work_ids': 'BAIIW0001;BAIIW0003',
  'source_evidence_ids': 'BAII4E0001;BAII4E0002;BAII4E0003;BAII4E0004;BAII4E0009;BAII4E0010;BAII4E0011;BAII4E0012',
  'source_baii_artifacts': 'closure/precedence_positioning_matrix.csv',
  'scope': 'Manuscript/F3A positioning',
  'allowed_interpretation': 'The contribution must be narrowed to the project-specific robustness design and bounded '
                            'cohort/method choices.',
  'prohibited_interpretation': 'First catalogue-scale TESS QPP study.',
  'relevance_to_f3a': 'CENTRAL',
  'relevance_to_f3b': 'NONE',
  'relevance_to_manuscript1': 'HIGH',
  'confidence_basis': 'Direct contradiction by included literature.'},
 {'claim_id': 'CLM010',
  'claim_type': 'POSITIONING_CONSTRAINT',
  'claim_text': 'Global priority claims such as “first TESS QPP selection-effects study” are not authorized by BAII.',
  'source_work_ids': 'BAIIW0001;BAIIW0003;BAIIW0098',
  'source_evidence_ids': 'BAII4E0001;BAII4E0002;BAII4E0003;BAII4E0004;BAII4E0009;BAII4E0010;BAII4E0011;BAII4E0012;BAII4E0097;BAII4E0098;BAII4E0099;BAII4E0100',
  'source_baii_artifacts': 'closure/precedence_positioning_matrix.csv;closure/limitations_register.csv',
  'scope': 'Priority wording',
  'allowed_interpretation': 'Use bounded corpus and design-specific statements.',
  'prohibited_interpretation': 'Convert absence of an exact retrieved precedent into a global literature absence.',
  'relevance_to_f3a': 'HIGH',
  'relevance_to_f3b': 'HIGH',
  'relevance_to_manuscript1': 'HIGH',
  'confidence_basis': 'Protocol limitation and included overlapping literature.'},
 {'claim_id': 'CLM011',
  'claim_type': 'LIMITATION',
  'claim_text': 'Five included works retain source-access limitations; only three works were extracted primarily from '
                'full text and 35 primarily from abstracts.',
  'source_work_ids': 'BAIIW0003;BAIIW0029;BAIIW0043;BAIIW0182;BAIIW0188',
  'source_evidence_ids': '',
  'source_baii_artifacts': 'extraction/extraction_manifest.json;extraction/source_access_log.csv',
  'scope': 'Evidence-depth limitation',
  'allowed_interpretation': 'Gate claims must remain at the evidence level actually supported.',
  'prohibited_interpretation': 'All 40 works received equivalent full-text methodological review.',
  'relevance_to_f3a': 'HIGH',
  'relevance_to_f3b': 'HIGH',
  'relevance_to_manuscript1': 'HIGH',
  'confidence_basis': 'Frozen source-access and extraction manifest counts.'},
 {'claim_id': 'CLM012',
  'claim_type': 'LIMITATION',
  'claim_text': 'The citation candidate arXiv:2602.20402 is supplemental context only and has no effect on the '
                'systematic 190/40 denominators.',
  'source_work_ids': 'BAIIW0182',
  'source_evidence_ids': '',
  'source_baii_artifacts': 'extraction/extraction_manifest.json;closure/supplemental_context_registry.csv',
  'scope': 'Non-systematic citation chasing',
  'allowed_interpretation': 'The paper may inform later context or design discussion.',
  'prohibited_interpretation': 'Treat the paper as a retroactive BAII systematic hit or included work.',
  'relevance_to_f3a': 'LOW',
  'relevance_to_f3b': 'LOW',
  'relevance_to_manuscript1': 'LOW',
  'confidence_basis': 'BAII.4 deferred-citation record and BAII.5 arXiv verification.'},
 {'claim_id': 'CLM013',
  'claim_type': 'DESIGN_CONSIDERATION',
  'claim_text': 'The gate hierarchy is triggered because at least one confirmed DIRECT F3A overlap with '
                'F3A_REDRAFT_REQUIRED has sufficient evidence and affects the central catalogue-scale '
                'contribution/framing.',
  'source_work_ids': 'BAIIW0001;BAIIW0003',
  'source_evidence_ids': 'BAII4E0001;BAII4E0002;BAII4E0003;BAII4E0004;BAII4E0009;BAII4E0010;BAII4E0011;BAII4E0012',
  'source_baii_artifacts': 'closure/critical_overlap_review.csv;closure/final_gate_decision.json',
  'scope': 'Frozen BAII.5 gate rule',
  'allowed_interpretation': 'F3A design must be reconsidered prospectively before it is scientifically frozen.',
  'prohibited_interpretation': 'F3A is cancelled, invalidated, or necessarily non-novel.',
  'relevance_to_f3a': 'CENTRAL',
  'relevance_to_f3b': 'NONE',
  'relevance_to_manuscript1': 'HIGH',
  'confidence_basis': 'Hierarchy A satisfied; BAIIW0001 independently supplies sufficient direct evidence even if '
                      'BAIIW0003 remains access-limited.'},
 {'claim_id': 'CLM014',
  'claim_type': 'SYSTEMATIC_CORPUS_FACT',
  'claim_text': 'BAII.5 does not modify F0–F2, BAII.1–BAII.4, F3A or F3B, and no new systematic search is executed.',
  'source_work_ids': '',
  'source_evidence_ids': '',
  'source_baii_artifacts': 'closure/final_synthesis_audit.json',
  'scope': 'Governance',
  'allowed_interpretation': 'BAII.5 is a documentary synthesis and pre-design gate.',
  'prohibited_interpretation': 'The gate itself constitutes the redesigned F3A protocol.',
  'relevance_to_f3a': 'HIGH',
  'relevance_to_f3b': 'HIGH',
  'relevance_to_manuscript1': 'MEDIUM',
  'confidence_basis': 'Hash-based historical freeze validation and closure audit.'}]
FINAL_GATE = {'audit_id': 'tess_qpp_bibliographic_audit_ii_v1',
 'audit_version': '1.1.0',
 'baii_status': 'BIBLIOGRAPHIC_AUDIT_II_COMPLETE',
 'f3a_gate_decision': 'F3A_DESIGN_RECONSIDERATION_REQUIRED',
 'decision_rule_applied': 'Hierarchy A: at least one BAII.4 F3A_REDRAFT_REQUIRED work remains DIRECT F3A overlap after '
                          'BAII.5 critical review, has evidence sufficient for gate use, and materially overlaps the '
                          'central catalogue-scale contribution/framing.',
 'gate_trigger_work_ids': ['BAIIW0001', 'BAIIW0003'],
 'gate_trigger_evidence_ids': ['BAII4E0001',
                               'BAII4E0002',
                               'BAII4E0003',
                               'BAII4E0004',
                               'BAII4E0009',
                               'BAII4E0010',
                               'BAII4E0011',
                               'BAII4E0012'],
 'f3a_design_reconsideration_required': True,
 'f3a_design_adjustment_required': True,
 'positioning_update_required': True,
 'f3b_design_considerations_present': True,
 'comparator_consideration_required': True,
 'systematic_work_count': 190,
 'included_work_count': 40,
 'direct_f3a_overlap_count': 2,
 'direct_f3b_overlap_count': 7,
 'f3a_redraft_required_count': 2,
 'f3a_adjustment_possible_count': 13,
 'f3b_adjustment_possible_count': 9,
 'access_limitations_material_to_gate': False,
 'novelty_assessed': False,
 'priority_claim_authorized': False,
 'f3a_modified': False,
 'f3b_modified': False,
 'recommended_next_task': 'F3A.1 — prospective reconsideration and freeze of the F3A scientific design from the BAII.5 '
                          'gate before any catalogue-scale execution.',
 'decision_basis': ['BAIIW0001 independently establishes direct catalogue-scale TESS QPP/AFINO overlap with sufficient '
                    'gate evidence.',
                    'BAIIW0003 independently establishes direct large-catalogue TESS QPP-classification overlap at the '
                    'supported provider/abstract level; unresolved full-method detail remains NOT_REPORTED.',
                    'Thirteen additional works identify concrete cohort, event-selection, processing, quality/gap, '
                    'numerical or comparator considerations.',
                    'The decision does not cancel F3A and does not assert novelty or lack of novelty; it requires '
                    'prospective redesign/reframing before freeze.'],
 'freeze_bindings': {'design_tag': 'bibliographic-audit-ii-design-v2',
                     'design_commit': 'a53ea8c5935e686df1fe8680b9c36bdf5111d05e',
                     'corpus_tag': 'bibliographic-audit-ii-corpus-v1',
                     'corpus_commit': 'ed62e78bf5280b557e0565ebcf21d8441948946b',
                     'screening_tag': 'bibliographic-audit-ii-screening-v1',
                     'screening_commit': 'c5cd41bcc04bc0bafa4fc457d42e39cdee06a8d1',
                     'f3_comparison_microfreeze_commit': '9ae33ce9458ceb826e1efbea31a4f96843334f5d',
                     'extraction_tag': 'bibliographic-audit-ii-extraction-v1',
                     'extraction_commit': '0b8da64a546e4871faec59fe9dfd5a2d8c93db6b'},
 'input_hashes': {'screening_manifest.json': 'b8d53cc6f51cfbf33ba3fd5d32a5651c0db772842d9fdab678d70f0f15ef7dba',
                  'extraction_manifest.json': '4de9ffac6ccd78e15690ab674c15af91529788fc7b05f63966f6fb79880b1581',
                  'f3_overlap_reference.json': '1b6be4a17d23457d3164b23c4b16557467e84ae44bbb35df57064b7c9566639e'}}
FINAL_AUDIT = {'task': 'BAII.5',
 'status': 'BAII5_FINAL_SYNTHESIS_AUDIT_COMPLETE',
 'raw_systematic_works': 190,
 'primary_extracted_works': 40,
 'critical_f3a_works_reviewed': 15,
 'redraft_required_reviewed': 2,
 'comparators_assessed': 11,
 'f3b_impact_works_represented': 9,
 'gate_decision_count': 1,
 'baii1_files_modified': 0,
 'baii2_files_modified': 0,
 'baii3_files_modified': 0,
 'baii4_files_modified': 0,
 'f0_f2_modified': 0,
 'f3a_modified': 0,
 'f3b_modified': 0,
 'evidence_references_missing': 0,
 'unknown_work_ids': 0,
 'unknown_evidence_ids': 0,
 'unsupported_gate_requirements': 0,
 'priority_claims_asserted': 0,
 'new_systematic_search_executed': False,
 'systematic_denominator_modified': False,
 'screening_modified': False,
 'work_ids_modified': False,
 'scientific_results_computed': False,
 'candidate_discovery_authorized': False,
 'novelty_assessed': False,
 'f3a_design_frozen': False,
 'f3b_design_frozen': False,
 'gate_decision': 'F3A_DESIGN_RECONSIDERATION_REQUIRED',
 'gate_trigger_work_ids': ['BAIIW0001', 'BAIIW0003'],
 'supplemental_context_rows': 1,
 'limitations_rows': 13,
 'final_evidence_claims': 14,
 'f3a_gate_requirements': 10,
 'historical_hash_contract': {'docs/literature/bibliographic_audit_ii/AUDIT_MATRIX.csv': 'ef1723c53d09f6fe95aa2f1f127d329b1a29ea389a9e75e4c77ec735ec4e10c5',
                              'docs/literature/bibliographic_audit_ii/SEED_SOURCES.csv': '05690c0f57a684c77b681510e4b18dcde163848a6eabcad3a735b9a3bccd8838',
                              'docs/literature/bibliographic_audit_ii/amendments/BAII_DESIGN_V1_1_0.md': 'ec076cc629ebc46c35253a1a0670023523700a0dc3c6b7f68baeb06f876ef514',
                              'docs/literature/bibliographic_audit_ii/audit_preregistration.json': '64f182980f8494b2242a7743151441718ca8a50d177ceb6442b8e5540742ae84',
                              'docs/literature/bibliographic_audit_ii/extraction/README.md': 'd518759133282379cfd0fad7d707874aeab8c30098071106754c0af57167713e',
                              'docs/literature/bibliographic_audit_ii/extraction/SHA256SUMS.txt': '818c6e042fbacc1c8a64307d7ff190f4533fa3df34fdc2276cdd3c2ee9ee5c44',
                              'docs/literature/bibliographic_audit_ii/extraction/SHA256SUMS_REFERENCE_FREEZE.txt': '5e938dd96b63a92607094cf9fa00b64113cf322db2f0ccad7be7f923f9e6632b',
                              'docs/literature/bibliographic_audit_ii/extraction/extraction_evidence_log.csv': '2c90080fb8779fc38de4c7fdd8c8126de00f97e48f4655d6988e089fd7fbb55c',
                              'docs/literature/bibliographic_audit_ii/extraction/extraction_manifest.json': '4de9ffac6ccd78e15690ab674c15af91529788fc7b05f63966f6fb79880b1581',
                              'docs/literature/bibliographic_audit_ii/extraction/extraction_report.md': 'c8e0feb5c3ab2bb875f74aa23062e9b50b16b36bf2e75fcd03dcca3c2fe94b59',
                              'docs/literature/bibliographic_audit_ii/extraction/f3_overlap_reference.json': '1b6be4a17d23457d3164b23c4b16557467e84ae44bbb35df57064b7c9566639e',
                              'docs/literature/bibliographic_audit_ii/extraction/included_work_extraction.csv': 'a5c8b5ba13da94e01fdc18ed95bea2abf036e481c695415ae276e89eb4fa047c',
                              'docs/literature/bibliographic_audit_ii/extraction/overlap_assessment.csv': '6585149e956f22060186a67750ccfa8402ee558a00b10c3341c3979480fbb768',
                              'docs/literature/bibliographic_audit_ii/extraction/overlap_dimension_evidence.csv': '114ac1d5e330ad0beacd002ae913d3ad11a132ecf0b2142b6f14b3d48a315552',
                              'docs/literature/bibliographic_audit_ii/extraction/source_access_log.csv': 'c3f67df0dbb2a2dd3c03f1de6ecac5873c3927f7c9d39a408a66c594d4107035',
                              'docs/literature/bibliographic_audit_ii/protocol.md': '75b7d372c778364882047d859ad90598c8fd553cbb1e70ddfae39c3d35e21927',
                              'docs/literature/bibliographic_audit_ii/retrieval/README.md': 'fe16746c3513066a3992cd51d2e9c241853c6005b5d766ca4ff5249be2c31d54',
                              'docs/literature/bibliographic_audit_ii/retrieval/SHA256SUMS.txt': '4c54368647ef93b3b7b5694eb49651320665d048b3d43f7f354c490229ff0ef3',
                              'docs/literature/bibliographic_audit_ii/retrieval/raw_hit_ledger.csv': '716c57663e90f4a7cc3f7d762620cbebe51a11d411ea10a97d9646a640b45dbd',
                              'docs/literature/bibliographic_audit_ii/retrieval/retrieval_manifest.json': '819de2c50a2b8921e9e69c16e40e896ae387d39e73fefca084500ef25435c97e',
                              'docs/literature/bibliographic_audit_ii/retrieval/search_execution_log.csv': '8778bc78a4bebde2751560807d6b990ebf971ff6acd3af76e32d6eb9453a4370',
                              'docs/literature/bibliographic_audit_ii/screening/README.md': '194e9ff3c31b112ee194e027ff201bbebe70f7407c708d768938fc4335709048',
                              'docs/literature/bibliographic_audit_ii/screening/SHA256SUMS.txt': '9fd5698e17b947953b60cdb96d46af3130086e8e79599b7f1057d629f73a464d',
                              'docs/literature/bibliographic_audit_ii/screening/auto_work_candidates.csv': 'ffbb71847522361076c82dc24e16da94292f9016f20d47af249f0ee860e5f7c0',
                              'docs/literature/bibliographic_audit_ii/screening/manual_adjudications.csv': '98ea1f5dd7f8815dd3599bf2b8db6661e731bc373971e0cf6555bc7f2d29a03b',
                              'docs/literature/bibliographic_audit_ii/screening/raw_hit_to_work_map.csv': '2d9ac5f37507cbd3b9e79481fa74edf582fc5f44bcf942e7d890586dcceca55e',
                              'docs/literature/bibliographic_audit_ii/screening/screened_works.csv': '143aa10bb942780e250f6b5cb9489acfa8bbc2a05b633624a4856d4d245533e2',
                              'docs/literature/bibliographic_audit_ii/screening/screening_decision_log.csv': 'b80b2a01e488b4ebe7f4c833a58f192de5d55e216bdeb66b9e2ed896d2bc16cb',
                              'docs/literature/bibliographic_audit_ii/screening/screening_manifest.json': 'b8d53cc6f51cfbf33ba3fd5d32a5651c0db772842d9fdab678d70f0f15ef7dba',
                              'docs/literature/bibliographic_audit_ii/screening/screening_report.md': 'f63e3b1160bcf5f8d1da3fe03b33bbbf6f12ad0081e52ebbbb7d2eacfeca7bb9',
                              'docs/literature/bibliographic_audit_ii/screening/verification_lookup_log.csv': '63fc3317c2cd0a962e145c6034c08b7e1871b0e69e9fe0a91534993961b6f850',
                              'docs/literature/bibliographic_audit_ii/screening/version_registry.csv': '33d2ef5e00bd3d343a01184b08b93aa8128ed739bb98ce86472dac93c12c6cdc',
                              'docs/literature/bibliographic_audit_ii/screening/work_registry.csv': 'eacaa8ad6f0ba78a91adf9bf8327d1727c6e045a0f7771ba32837c0eaf089661',
                              'docs/literature/bibliographic_audit_ii/screening_schema.csv': '0c9031aae2d9f5c674c5e4c3e0f4201af81cc0fabdc3e325fb863cebe8f69d0f',
                              'docs/literature/bibliographic_audit_ii/scripts/build_extraction_scaffold.py': '2214860582b7a717955cbf887cb1ba77a825a968b0fcb893ccfd240f6483f92f',
                              'docs/literature/bibliographic_audit_ii/scripts/build_work_resolution.py': 'e14670757b94de8732a8b6648b9f1a7c412e1b116e1ba792e2142b919736d0b4',
                              'docs/literature/bibliographic_audit_ii/scripts/retrieve_raw_corpus.py': '7f5535cd7edbb57082158c6e80eac86b9f73ce16b2163989d4f67e6ddebf204a',
                              'docs/literature/bibliographic_audit_ii/scripts/validate_extraction.py': 'f7d90def3e74950fba3d1fbe10bb7d8bb8d37988437142295478fb321c1de7ff',
                              'docs/literature/bibliographic_audit_ii/scripts/validate_screening.py': '5913768f99ace63161d954b7830874455c5fd81df1e04978863706eee5a7b0e2',
                              'docs/literature/bibliographic_audit_ii/search_plan.yaml': 'a76420e4603baeda95d70c8d3308bc614458d09d9769979d327ef79bf9a52f28'},
 'notes': ['Top-level BAII README and top-level checksum manifest are intentionally advanced by BAII.5; historical '
           'retrieval/screening/extraction READMEs and checksum manifests remain unchanged.',
           'BAIIW0003 retains its BAII.4 access limitation after the required allowed-source recheck; no unsupported '
           'method-validation details were inferred.',
           'The deferred arXiv:2602.20402 record remains supplemental and has no systematic denominator effect.'],
 'validation_target_status': 'BAII5_FINAL_SYNTHESIS_VALIDATION_PASS',
 'builder_rebuild_status': 'BAII5_FINAL_SYNTHESIS_REBUILD_EXACT'}

TOP_README = '# Bibliographic Audit II\n\n**STATUS:** `BIBLIOGRAPHIC AUDIT II CLOSED — F3A GATE DECISION FROZEN`\n\nBibliographic Audit II is the literature gate between the frozen F0–F2 foundation and the future freeze of F3A. BAII.1 v1.0.0 froze the prospective search and screening design. BAII.1 v1.1.0 is a narrow technical amendment created after incomplete BAII.2 retrieval attempts exposed a SciX parser incompatibility in the exact `date` timestamp syntax. The scientific query semantics and screening design remain unchanged.\n\n## Sequence\n\n```text\nBAII.1 protocol freeze\n        ↓\nBAII.2 systematic search + raw corpus freeze\n        ↓\nBAII.3 deduplication + screening\n        ↓\nBAII.4 structured extraction + overlap analysis\n        ↓\nBAII.5 synthesis + F3A gate decision\n```\n\n## BAII.1 / amendment boundaries\n\n- Complete 12/12 BAII.2 raw corpus frozen: **yes**\n- Incomplete technical retrieval attempts preserved: **2**\n- Successful provider executions before v1.1.0: **12 arXiv executions across two attempts**\n- Failed provider executions before v1.1.0: **12 SciX executions across two attempts**\n- BAII.2 normative executions: **12/12 successful**\n- BAII.2 raw hit rows: **322** (**249 SciX + 73 arXiv**)\n- BAII.2 deterministic rebuild: **`RAW_LEDGER_REBUILD_EXACT`**\n- BAII.3 raw hits mapped: **322/322**\n- BAII.3 unique intellectual works: **190**\n- BAII.3 bibliographic versions: **283**\n- BAII.3 preferred versions: **190**\n- BAII.3 screening outcomes: **40 include / 33 background / 117 exclude / 0 unresolved**\n- BAII.3 automatic candidate rebuild: **`AUTO_WORK_CANDIDATE_REBUILD_EXACT`**\n- Scientific works screened under BAII.3: **190**\n- Deduplication / `work_id` assignment: **complete and frozen for BAII.3**\n- F0–F2 modified: **no**\n- F3A or F3B modified: **no**\n- Candidate discovery authorized: **no**\n- Scientific results computed: **no**\n- BAII.4 prospective design-impact assessment: **complete and frozen**\n- BAII.5 final F3A gate decision: **`F3A_DESIGN_RECONSIDERATION_REQUIRED`**\n- Formal novelty assessment performed: **no**\n- Priority claim authorized: **no**\n\nThe directory already contained `AUDIT_MATRIX.csv` and `SEED_SOURCES.csv` before BAII.1. They remain unchanged. `SEED_SOURCES.csv` is pre-existing seed/context material, not a systematically retrieved or screened BAII corpus. `AUDIT_MATRIX.csv` is a legacy empty template and is not the normative BAII.1 screening schema; future BAII screening uses `screening_schema.csv`.\n\nThe previously tracked `PROTOCOL.md` established the literature gate. BAII.1 normalized it to lowercase `protocol.md`; Git history preserves the earlier version. The immutable v1.0.0 design remains tagged `bibliographic-audit-ii-design-v1`. Amendment v1.1.0 documents the two incomplete BAII.2 attempts and changes only SciX parser serialization of the already frozen exact `date` range.\n\n## Design-freeze files\n\nAt the immutable `bibliographic-audit-ii-design-v2` tag, the v1.1.0 design freeze comprises:\n\n- `README.md`\n- `protocol.md`\n- `search_plan.yaml`\n- `screening_schema.csv`\n- `audit_preregistration.json`\n- `amendments/BAII_DESIGN_V1_1_0.md`\n- `SHA256SUMS.txt`\n\n`screening_schema.csv` is unchanged from v1.0.0. At the design tag, `SHA256SUMS.txt` hashes the six content files above and never hashes itself. After BAII.2 the working-branch `README.md` advances status, so the working-branch checksum manifest updates only that README checksum; the original design-v2 checksum manifest remains immutable in Git history.\n\nThe v1.0.0 tag must not be moved or replaced. Version 1.1.0 is frozen by annotated tag `bibliographic-audit-ii-design-v2` at commit `a53ea8c5935e686df1fe8680b9c36bdf5111d05e`. If another material error is discovered, retrieval stops, the incident is documented, the protocol version is incremented again, and a new immutable design tag is created.\n\n\n## BAII.2 raw-corpus freeze\n\nThe normative BAII.2 retrieval completed all 12 frozen query × provider executions successfully.\nThe frozen ledger contains 322 raw hits. BAII.3 maps every hit exactly once into 190 unique `work_id` entities while preserving all raw-hit provenance.\n\nThe raw archive is `bibliographic_audit_ii_raw_corpus_v1.zip` with SHA-256\n`9dd526ecf58b6fed8af4d2902989dc6b8d4255126fd82aed02ce59d07537f993`.\n\n## BAII.3 work-resolution and screening freeze\n\nBAII.3 resolves the 322 raw hits into **190 unique intellectual works** and **283 bibliographic versions**, with exactly one preferred version per work. The automatic resolution layer produced 201 exact bibliographic components; 11 explicit same-work adjudications reduced this to 190 works, while 11 explicit distinct-work adjudications prevented false fuzzy merges. No relationship remains unresolved.\n\nFinal screening at work level yields **40 `INCLUDE_FOR_BAII4`**, **33 `BACKGROUND_ONLY`**, **117 `EXCLUDE`**, and **0 access-limited unresolved decisions**. `SEED_SOURCES.csv` remains outside the systematic denominator; four seeds (S005–S008) also occur independently in the systematic corpus.\n\nBAII.3 did not assign `relevance_labels`, F3A/F3B design impact, Manuscript 1 positioning impact, or novelty. BAII.4 subsequently extracted the 40 included works and froze descriptive overlap plus prospective impact annotations against the pre-frozen F3 comparison reference. Novelty remains unassessed and the final F3A gate remains reserved for BAII.5.\n\n\n## BAII.4 structured extraction and overlap freeze\n\nBefore systematic extraction, the documentary F3 comparison target was frozen in\n`extraction/f3_overlap_reference.json` (SHA-256\n`1b6be4a17d23457d3164b23c4b16557467e84ae44bbb35df57064b7c9566639e`) and committed at\n`9ae33ce9458ceb826e1efbea31a4f96843334f5d`.\n\nBAII.4 extracted **40/40** included works, retaining **160 extraction-evidence rows**, **40\nwork-level overlap assessments**, **62 dimensional overlap-evidence rows**, and **40 source-access\nrecords**. No work is blocked. Five work records retain explicitly documented source-access\nlimitations and unresolved detail is encoded as `NOT_REPORTED`.\n\nDescriptive overlap is **2 DIRECT / 36 PARTIAL / 2 CONTEXT_ONLY** for F3A and **7 DIRECT / 2\nPARTIAL / 31 CONTEXT_ONLY** for F3B. The impact rubric records **2 `F3A_REDRAFT_REQUIRED`**, **13\n`F3A_DESIGN_ADJUSTMENT_POSSIBLE`**, **9 `F3B_DESIGN_ADJUSTMENT_POSSIBLE`**, and **23\n`POSITIONING_ONLY`** assignments. These are prospective literature-gate annotations, not actual\nchanges to F3A/F3B and not novelty or precedence claims.\n\nBAII.5 has now completed the final synthesis and frozen the pre-F3A gate decision. No BAII.3 screening field or BAII.4 extraction/overlap field was retrospectively modified.\n\n## BAII.5 final synthesis and gate freeze\n\nBAII.5 reviewed all **15** works carrying prospective F3A impact, including the two\n`F3A_REDRAFT_REQUIRED` / `DIRECT` overlap works, assessed all **11** comparator candidates, and\nrepresented all **9** F3B-impact works. The systematic denominator remains **190 works / 40 primary\nextracted works**.\n\nThe frozen hierarchical gate resolves to:\n\n`F3A_DESIGN_RECONSIDERATION_REQUIRED`\n\nBAIIW0001 independently satisfies the highest gate branch through direct catalogue-scale TESS QPP\noverlap with sufficient evidence. BAIIW0003 independently reinforces the catalogue/classification\noverlap but retains its documented source-access limitation; unresolved implementation details\nremain `NOT_REPORTED`.\n\nThe gate does not cancel F3A and is not a novelty verdict. It means that the next task must\nprospectively reformulate and freeze F3A while addressing the open BAII.5 requirements before any\ncatalogue-scale execution.\n\nF0–F2 remain frozen. F3A and F3B remain scientifically unfrozen.\n\nNext task: **F3A.1 — prospective reconsideration and freeze of the F3A scientific design from the\nBAII.5 gate.**\n'
CLOSURE_README = '# Bibliographic Audit II — BAII.5 closure\n\n**STATUS:** `BIBLIOGRAPHIC AUDIT II CLOSED — F3A GATE DECISION FROZEN`\n\nBAII.5 performs final documentary synthesis over the frozen BAII.1–BAII.4 lineage. It does not\nmodify F0–F2, F3A or F3B and does not execute new scientific analysis.\n\nFinal gate:\n\n`F3A_DESIGN_RECONSIDERATION_REQUIRED`\n\nThis decision follows the frozen hierarchical gate rule. The confirmed DIRECT F3A overlaps\nBAIIW0001 and BAIIW0003 remain `F3A_REDRAFT_REQUIRED` after critical review, with sufficient\nevidence for the bounded gate conclusion. BAIIW0001 independently satisfies the gate trigger.\n\nThe gate requires prospective reconsideration before the scientific F3A design is frozen. It does\nnot cancel F3A, does not assert that F3A lacks novelty, and does not authorize any priority claim.\n\nThe systematic denominator remains 190 works, with 40 primary extracted works. The supplemental\ncitation candidate remains outside both denominators.\n\nNext task:\n\n`F3A.1 — prospective reconsideration and freeze of the F3A scientific design from the BAII.5 gate`\n'
FINAL_REPORT = '# Bibliographic Audit II — BAII.5 Final Synthesis Report\n\n## 1. Objective and scope\n\nBAII.5 closes Bibliographic Audit II as a documentary gate between the frozen F0–F2 foundation and the future scientific freeze of Phase 3A. It does not redesign F3A, modify F3B, execute new scientific analyses, reopen screening, or perform a new systematic literature search. Its purpose is narrower: synthesize the frozen BAII.1–BAII.4 evidence into one traceable decision about what must happen before F3A can be scientifically frozen.\n\nThe final gate is therefore a governance and design-readiness decision. It uses the four preregistered gate states only, applies the frozen hierarchical rule, and preserves the distinction between bibliographic overlap, prospective design impact, and claims of novelty or priority. No global novelty assessment is made.\n\n## 2. Corpus and screening\n\nThe systematic BAII corpus remains unchanged at 190 unique intellectual works derived from the frozen 322 raw hits. BAII.3 included 40 works for primary structured extraction, retained 33 as background-only context, excluded 117, and left no unresolved screening decisions. BAII.4 subsequently extracted exactly those 40 included works, producing 160 evidence rows, 40 work-level overlap assessments, 62 dimensional overlap assessments, and 40 source-access records.\n\nBAII.5 does not alter any of those denominators. The deferred citation candidate discovered in BAII.4 is treated separately as supplemental context and never becomes a retrospective systematic hit. Likewise, no background-only work is promoted into the primary 40-work extraction set.\n\n## 3. Panorama of the 40 included works\n\nThe 40 works cover several distinct literature roles: catalogue-scale TESS flare and QPP studies, QPP-detection/classification methods, general flare-detection pipelines, robustness or processing studies, and injection–recovery/known-truth validation approaches. BAII.4 identified 26 catalogue-relevant works, 17 detection-method-relevant works, 10 robustness-relevant works, seven direct F3B-overlap works, and eight selection-function-relevant works.\n\nEvidence depth is heterogeneous. Five works retain documented access limitations. Only three were extracted primarily from full text, while 35 were extracted primarily from abstracts and two from table/provider-metadata sources. BAII.5 therefore keeps detailed implementation claims conservative and does not replace NOT_REPORTED fields with inference.\n\n## 4. Direct overlap with F3A\n\nTwo works remain DIRECT F3A overlaps after critical review: BAIIW0001, *Stationary quasi-periodic pulsations in 20-second cadence TESS flares*, and BAIIW0003, *Properties of Flare Quasiperiodic Pulsations Based on a New TESS Flare Catalog*. Both retain the BAII.4 category F3A_REDRAFT_REQUIRED.\n\nBAIIW0001 is sufficient on its own to trigger the highest gate branch. It uses 20-second TESS data from Sectors 27–80, reports 3,878 flares across 1,285 flaring stars, identifies 61 QPPs across 57 stars, and applies AFINO Fourier model comparison after automated flare detection. This directly overlaps both the catalogue-scale and QPP-classification reference dimensions of the prospective F3A comparison target.\n\nThe overlap does not mean that BAIIW0001 implements the complete planned F3A programme. The frozen evidence does not establish the full prospective window, processing, quality/gap and numerical-stability robustness architecture, nor does it provide known physical truth or the project-specific independent held-out validation reserved for F3B. The implication is therefore redesign/reframing, not cancellation.\n\n## 5. The two catalogue-scale TESS QPP works\n\nBAIIW0003 provides a second, independent reason that F3A cannot be framed simply as catalogue-scale TESS QPP work. It reports a large TESS 2-minute flare catalogue with 208,280 flare events from about 29,280 flaring stars and applies a previously published fully convolutional QPP classifier, selecting 10,465 M-star flares with QPP features.\n\nBAII.5 performed the required final allowed-source recheck. The high-level catalogue and QPP-classification facts remain supported, but the complete classifier training, validation, robustness and selection-function details were not resolved through the allowed-source path. The BAII.4 access limitation is therefore retained. This limitation does not justify weakening the direct catalogue/classification overlap, but it prevents BAII.5 from making stronger claims about the classifier’s complete validation architecture.\n\nTogether, BAIIW0001 and BAIIW0003 establish that catalogue scale, TESS use and QPP classification cannot themselves define the distinctive F3A contribution.\n\n## 6. F3A design considerations\n\nBeyond the two redraft-required cases, 13 works retain F3A_DESIGN_ADJUSTMENT_POSSIBLE. Their implications cluster into concrete design questions rather than automatic method changes.\n\nFirst, the cohort universe and catalogue source must be frozen prospectively. Large TESS flare catalogues generated by different automated pipelines already exist, and upstream event construction can affect the population presented to QPP analysis. Second, QPP reference labels require explicit provenance: AFINO-based observational selection, neural-network classification and comparison-event roles must not be confused with physical truth.\n\nThird, F3A must preserve its intended robustness focus. The literature supplies concrete alternatives involving wavelet/window choices, stochastic or Gaussian-process baselines, detrending, quality/gap handling and automated flare pipelines. These do not mandate a maximal comparison grid, but the future F3A design must state which dimensions are included, which comparators are deferred, and why. Finally, AFINO numerical behaviour remains a separate evidence plane from classification robustness; optimizer-seed and convergence diagnostics must remain prospectively specified.\n\nThese issues are recorded as open F3A gate requirements. BAII.5 does not mark any of them ADOPTED, REJECTED or IMPLEMENTED.\n\n## 7. Literature relevant to F3B\n\nNine included works carry F3B_DESIGN_ADJUSTMENT_POSSIBLE. They include injection–recovery studies, synthetic known-truth experiments, completeness/selection-function characterization and QPP or flare classifiers tested on controlled data. These works establish that injection–recovery and selection-function ideas are not new in the adjacent flare/QPP methodological space.\n\nAt the same time, BAII did not identify an included work assessed as matching the complete project-specific F3B architecture: explicit prospective development/validation separation combined with an independent held-out benchmark under the frozen F3B reference. This is a bounded statement about the 40 included works, not a global priority claim. F3B remains scientifically unfrozen, and its signal families, noise/background model, success criteria and held-out protocol remain future design decisions.\n\n## 8. Comparators\n\nBAII.4 identified 11 sufficiently defined comparator candidates. BAII.5 represents all 11 and assigns consideration priority without adopting any of them. Directly relevant examples include Morlet wavelet QPP analysis, the fully convolutional QPP classifier, multiple TESS flare-detection pipelines, hidden-Markov/Celerite approaches, ARMA/GARCH processing, wavelet denoising, FLARENET and Bayesian additive GP/HMM models.\n\nThe comparator matrix distinguishes methods that must be addressed before the F3A freeze from those primarily relevant to F3B. “Must address” means that the later design must explicitly implement, reject with rationale, defer, or treat the method as positioning-only. It does not mean that every comparator must be run.\n\n## 9. Positioning and claims to avoid\n\nThe audit supports several bounded positioning statements. Catalogue-scale TESS QPP studies are present in the included literature. AFINO has already been applied at catalogue scale to TESS QPP analysis. Machine-learning QPP classification has been applied to a large TESS flare catalogue. Injection–recovery and selection-function approaches are represented in adjacent flare/QPP methodology.\n\nConsequently, F3A must not be described as the first catalogue-scale TESS QPP study. F3B must not be described as the first QPP injection–recovery study. Claims that no previous work examined methodological robustness are contradicted by included literature. The audit also does not authorize a global claim that the project is the first to study TESS QPP selection effects. Non-retrieval of an exact precedent is not proof of absence from the literature.\n\n## 10. Bibliographic limitations\n\nThe gate inherits the frozen 2024–2026 search window, the two principal providers, the preregistered query families, uneven source-access depth, the exclusion of 33 background-only works from primary extraction, and the distinction between systematic and citation-chased context. Literature after the 2026-08-07 search freeze is not systematically covered.\n\nThe deferred candidate arXiv:2602.20402 concerns TESS flare detection in nearby young moving-group members. Its abstract provides relevant upstream flare/cadence context but does not establish a direct QPP overlap. It remains outside the systematic denominator.\n\n## 11. Formal gate decision\n\nThe frozen hierarchical rule selects **F3A_DESIGN_RECONSIDERATION_REQUIRED**. Hierarchy A is satisfied because at least one case—and in practice two cases—remains F3A_REDRAFT_REQUIRED plus DIRECT F3A overlap with evidence sufficient for gate use and material relevance to the central catalogue-scale contribution or experimental framing.\n\nBAIIW0001 independently satisfies the trigger, so the access limitation on BAIIW0003 is not outcome-determinative. The decision means that freezing the pre-BAII conception of F3A without explicit reconsideration would be methodologically inappropriate. It does not mean F3A is cancelled, invalid, or demonstrated to be non-novel.\n\n## 12. Exact implication for the next task\n\nBibliographic Audit II is complete. F0–F2 remain frozen. BAII.1–BAII.4 remain frozen. F3A and F3B remain scientifically unfrozen.\n\nThe next task is **F3A.1 — prospective reconsideration and freeze of the F3A scientific design from the BAII.5 gate**. F3A.1 must resolve the open cohort, catalogue, event-selection, QPP-reference, robustness, numerical and comparator questions before any catalogue-scale execution. Only after that prospective design is explicitly frozen should scientific execution begin.\n'
DR003 = '# DR-003 — Bibliographic Audit II F3A gate\n\n## Status\n\n**Accepted — gate frozen**\n\n## Date\n\n2026-08-11\n\n## Decision\n\nThe Bibliographic Audit II pre-F3A gate is:\n\n`F3A_DESIGN_RECONSIDERATION_REQUIRED`\n\n## Context\n\nBAII.1 froze the literature-search/screening design, BAII.2 froze the raw systematic corpus,\nBAII.3 froze work resolution and screening, and BAII.4 froze structured extraction plus descriptive\noverlap against the pre-extraction F3 comparison reference.\n\nBAII.4 identified two `DIRECT` F3A overlaps with `F3A_REDRAFT_REQUIRED`:\nBAIIW0001 and BAIIW0003, plus thirteen additional `F3A_DESIGN_ADJUSTMENT_POSSIBLE` works.\n\n## Evidence\n\nBAIIW0001 reports catalogue-scale 20-second TESS flare/QPP analysis using AFINO and is independently\nsufficient to satisfy the highest preregistered gate branch. BAIIW0003 reports a much larger TESS\nflare catalogue with fully convolutional QPP classification and independently confirms that\ncatalogue scale/TESS/QPP classification cannot define the F3A contribution by themselves.\n\nBAIIW0003 retains a documented source-access limitation. BAII.5 therefore uses only the high-level\ncatalogue/classification facts already supported by the frozen evidence and does not infer missing\nvalidation details.\n\nThe 15 F3A-impact works, 11 comparator candidates and 9 F3B-impact works are represented in the\nBAII.5 closure artifacts.\n\n## Consequences\n\nThe existing pre-BAII conception of F3A must not be scientifically frozen without prospective\nreconsideration of cohort universe, catalogue source, event selection, QPP reference labels,\nrobustness dimensions, numerical diagnostics, comparator strategy and positioning.\n\nThis does **not** mean that F3A is cancelled, invalidated, or shown to be non-novel.\n\n## What changes now\n\nThe program advances to a new design task:\n\n`F3A.1 — prospective reconsideration and freeze of the F3A scientific design from the BAII.5 gate`\n\nThat task must resolve the open gate requirements before catalogue-scale execution.\n\n## What does not change\n\n- F0–F2 remain frozen.\n- BAII.1–BAII.4 remain frozen.\n- The BAII systematic denominator remains 190 works / 40 primary extracted works.\n- F3A is still not scientifically frozen.\n- F3B is still not scientifically frozen.\n- No comparator has been adopted by BAII.\n- No novelty or priority claim is authorized.\n\n## Next gate\n\nF3A.1 must produce a prospectively frozen F3A scientific design that explicitly addresses the\nBAII.5 gate requirements. Scientific execution may begin only after that design freeze.\n'

CSV_SPECS = {
    "critical_overlap_review.csv": (CRITICAL_ROWS, ['work_id',
 'preferred_version_id',
 'title',
 'baii4_f3a_overlap',
 'baii4_f3a_impact',
 'gate_review_status',
 'evidence_sufficient_for_gate',
 'access_limitation_present',
 'central_overlap_dimension',
 'secondary_overlap_dimensions',
 'what_the_work_actually_establishes',
 'what_it_does_not_establish',
 'implication_for_f3a',
 'implication_type',
 'evidence_ids',
 'source_limitations',
 'baii4_assessment_status',
 'review_notes']),
    "precedence_positioning_matrix.csv": (PRECEDENCE_ROWS, ['positioning_claim_id',
 'candidate_claim',
 'audit_assessment',
 'supporting_work_ids',
 'supporting_evidence_ids',
 'safe_wording',
 'unsafe_wording',
 'manuscript_relevance',
 'f3a_design_relevance',
 'notes']),
    "comparator_consideration_matrix.csv": (COMPARATOR_ROWS, ['work_id',
 'method_name_or_family',
 'target_problem',
 'relevant_to_f3a',
 'relevant_to_f3b',
 'implementation_available',
 'procedure_sufficiently_defined',
 'comparison_value',
 'comparison_cost_or_risk',
 'consideration_priority',
 'evidence_ids',
 'adoption_decision',
 'notes']),
    "f3b_design_considerations.csv": (F3B_ROWS, ['consideration_id',
 'source_work_ids',
 'relevant_f3b_dimension',
 'literature_approach',
 'potential_project_relevance',
 'must_consider_before_f3b_freeze',
 'evidence_ids',
 'current_project_requirement',
 'remaining_design_question',
 'status']),
    "supplemental_context_registry.csv": (SUPPLEMENTAL_ROWS, ['supplemental_id',
 'title',
 'identifier',
 'discovery_route',
 'discovery_work_id',
 'systematic_corpus_member',
 'systematic_denominator_effect',
 'contextual_relevance',
 'f3a_relevance',
 'f3b_relevance',
 'source_checked',
 'assessment',
 'allowed_use',
 'prohibited_use']),
    "f3a_gate_requirements.csv": (F3A_REQUIREMENT_ROWS, ['requirement_id',
 'requirement_category',
 'source_work_ids',
 'source_evidence_ids',
 'issue',
 'why_it_matters',
 'current_f3a_reference',
 'required_design_question',
 'must_resolve_before_f3a_freeze',
 'resolution_status',
 'allowed_resolution_types',
 'prohibited_shortcut']),
    "limitations_register.csv": (LIMITATION_ROWS, ['limitation_id', 'category', 'description', 'effect_on_gate', 'mitigation', 'remaining_risk', 'manuscript_implication']),
    "final_evidence_ledger.csv": (FINAL_EVIDENCE_ROWS, ['claim_id',
 'claim_type',
 'claim_text',
 'source_work_ids',
 'source_evidence_ids',
 'source_baii_artifacts',
 'scope',
 'allowed_interpretation',
 'prohibited_interpretation',
 'relevance_to_f3a',
 'relevance_to_f3b',
 'relevance_to_manuscript1',
 'confidence_basis']),
}

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})

def assert_frozen_inputs(repo: Path) -> None:
    for rel, expected in EXPECTED_INPUT_HASHES.items():
        path = repo / rel
        observed = sha256_file(path)
        if observed != expected:
            raise RuntimeError(f"Frozen BAII input changed: {rel}: {observed} != {expected}")
    for rel, expected in HISTORICAL_HASH_CONTRACT.items():
        path = repo / rel
        observed = sha256_file(path)
        if observed != expected:
            raise RuntimeError(f"Historical BAII artifact changed: {rel}: {observed} != {expected}")

def update_top_checksum(baii: Path) -> None:
    checksum = baii / "SHA256SUMS.txt"
    lines = checksum.read_text(encoding="ascii").splitlines()
    out = []
    readme_hash = sha256_file(baii / "README.md")
    for line in lines:
        if line.endswith("  README.md"):
            out.append(f"{readme_hash}  README.md")
        else:
            out.append(line)
    checksum.write_text("\n".join(out) + "\n", encoding="ascii")

def write_closure_checksums(closure: Path) -> None:
    target = closure / "SHA256SUMS.txt"
    files = sorted(p for p in closure.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt")
    target.write_text(
        "\n".join(f"{sha256_file(p)}  {p.name}" for p in files) + "\n",
        encoding="ascii",
    )

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    baii = repo / "docs/literature/bibliographic_audit_ii"
    closure = baii / "closure"
    decisions = repo / "docs/decisions"
    closure.mkdir(parents=True, exist_ok=True)
    decisions.mkdir(parents=True, exist_ok=True)

    assert_frozen_inputs(repo)

    for name, (rows, fields) in CSV_SPECS.items():
        write_csv(closure / name, rows, fields)

    (closure / "final_gate_decision.json").write_text(
        json.dumps(FINAL_GATE, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (closure / "final_synthesis_audit.json").write_text(
        json.dumps(FINAL_AUDIT, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (closure / "README.md").write_text(CLOSURE_README, encoding="utf-8")
    (closure / "final_synthesis_report.md").write_text(FINAL_REPORT, encoding="utf-8")
    (decisions / "DR-003-bibliographic-audit-ii-f3a-gate.md").write_text(DR003, encoding="utf-8")
    (baii / "README.md").write_text(TOP_README, encoding="utf-8")

    write_closure_checksums(closure)
    update_top_checksum(baii)

    print("BAII5_FINAL_SYNTHESIS_BUILD_COMPLETE")
    print(f"critical_f3a_reviews={len(CRITICAL_ROWS)}")
    print(f"comparators={len(COMPARATOR_ROWS)}")
    print(f"f3b_considerations={len(F3B_ROWS)}")
    print(f"gate={FINAL_GATE['f3a_gate_decision']}")

if __name__ == "__main__":
    main()
