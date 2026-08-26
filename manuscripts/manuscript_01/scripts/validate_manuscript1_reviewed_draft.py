#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re
import zlib

ROOT = Path(__file__).resolve().parents[3]
REV = ROOT / "manuscripts/manuscript_01/revision"
EV = REV / "evidence"
DRAFT = ROOT / "manuscripts/manuscript_01/draft"
PLANNING = ROOT / "manuscripts/manuscript_01/planning"

PLANNING_HASHES = {'manuscripts/manuscript_01/planning/SHA256SUMS.txt': 'a098c6cb130f21ecff88a7aeff5292267d1b1560f64aeb067639205af5161206',
 'manuscripts/manuscript_01/planning/m1_architecture_audit.json': '540d8f332129db6ebec7ee3d455954aad2005aa767eff8490f309110ca5302b0',
 'manuscripts/manuscript_01/planning/m1_bibliographic_positioning_matrix.csv': 'ce8dad4a60a05850e336871be8a148bfbf3bbce7b0e4bacebdb1034b0e1410c8',
 'manuscripts/manuscript_01/planning/m1_claim_matrix.csv': '8b01572171feef251357925d3553ec7843789407a343b895aedc52ea6ed8a9b4',
 'manuscripts/manuscript_01/planning/m1_evidence_plane_registry.csv': '9157754193b06cebb65442847be2c7ddbc57e8aef68564682da54f5c034d0a0a',
 'manuscripts/manuscript_01/planning/m1_figure_table_plan.csv': 'aad8812717b79c0e15e767e835e1157f2dbc66f502dba81b9bb4d8be391bd35a',
 'manuscripts/manuscript_01/planning/m1_limitations_matrix.csv': '1e284906a55c63728df81e733684556874a0daeca862c862f9801516bca895d5',
 'manuscripts/manuscript_01/planning/m1_scope_contract.md': 'fbe444aca8de6bd3dd2d6ea04bf0aab35cc4979bf05194a26c20b8b8d56f6972',
 'manuscripts/manuscript_01/planning/m1_section_map.csv': 'cd69a164c3e237ce71977b0b7166f6b2754b4dbb283130d7e09aca4703511e32',
 'manuscripts/manuscript_01/planning/m1_source_bindings.json': '3516ede53b0b77e33ba5099468a1b70f59d7606a564cb1a2bc90f86172292409'}
M12_HASHES = {'docs/decisions/DR-010-manuscript1-visual-freeze.md': '27763fde0fbf9116f1a3a2e49b3442c865b1e2555ca104a22c4f5327e693ae72',
 'manuscripts/manuscript_01/scripts/render_manuscript1_visuals.py': 'cd527d9112dc89c200553c7d7ae590086c2c79ac8ecfcdf64f6f96291af32c39',
 'manuscripts/manuscript_01/scripts/validate_manuscript1_visuals.py': 'f51888d00d10363dab91f8ce62bf3a4466a837ed74430e6d37430524231a373d',
 'manuscripts/manuscript_01/tests/test_manuscript1_visual_package.py': 'e43d7baaa268753088da8cf9e6e2f1d987c47d7f7c8ce76d92e16f84f0981eaa',
 'manuscripts/manuscript_01/visuals/README.md': 'cffb65beab3ddeb897a8af98948e94cb97749fc0b5bb257d009bc4d05b3bac24',
 'manuscripts/manuscript_01/visuals/config/m1_2_visual_rendering_contract.json': 'ac3009c3e5a906df794c9737751c52ae0f9df21943d74a4cf1419989ddc6373d',
 'manuscripts/manuscript_01/visuals/evidence/SHA256SUMS.txt': '97a0cea3c27270a915c3c83362ffc2d7d4d1a0c00a94abcc90e0d434917d8164',
 'manuscripts/manuscript_01/visuals/evidence/m1_2_rendered_value_audit.csv': '63fcba7cdb30405349333806840caf981a85027f5b66b32dbb3ae5d5e2f3543e',
 'manuscripts/manuscript_01/visuals/evidence/m1_2_visual_audit.json': '0d17b125648eef681c8c2ce6bc0f914cb0e299b559e3c2247cbd58cc8e7c8fb6',
 'manuscripts/manuscript_01/visuals/evidence/m1_2_visual_manifest.csv': '65d26812f676d152f67c678ed3ae4d8860020ab4c0ed794340ce910026079718',
 'manuscripts/manuscript_01/visuals/evidence/m1_2_visual_source_bindings.json': 'aa0d5b81702a9ffc554474fb4d2ef19d1162ac7780df313186da1712d19663d5',
 'manuscripts/manuscript_01/visuals/figures/M1F01_evidence_architecture.pdf': '97c02646329face145d88f7178778d33abd70338a6319ffc53847ef632806351',
 'manuscripts/manuscript_01/visuals/figures/M1F01_evidence_architecture.png': '5b85981343f255c7f902855acc1dc5943b068bf9447003c509a362dbf18d25b1',
 'manuscripts/manuscript_01/visuals/figures/M1F02_f2_f3a_robustness_progression.pdf': '5ba9e701166f8ee798f3a57e16c789552d6729560d814d2707ce015db1fb48b7',
 'manuscripts/manuscript_01/visuals/figures/M1F02_f2_f3a_robustness_progression.png': '296a6b0f594389c4e254e461910a133369f8b62f96dac5878557ee4bc97b631c',
 'manuscripts/manuscript_01/visuals/figures/M1F03_f3a_catalogue_robustness.pdf': 'f26316dd58d6e652ba0ff8f46457962d9b198b7d869c271134deb3f27bc0a394',
 'manuscripts/manuscript_01/visuals/figures/M1F03_f3a_catalogue_robustness.png': '1f98581cc8660747f016f441e95b2857ff58d05a65f3c5d840913ff38e4ba098',
 'manuscripts/manuscript_01/visuals/figures/M1F04_f3b_heldout_selection_function.pdf': 'aba98bcd823c06b873181a69cdb56e0d97fad54f2c56511e35d6cb717e037d7e',
 'manuscripts/manuscript_01/visuals/figures/M1F04_f3b_heldout_selection_function.png': '74fd86903ae3fc71ae43e3b2c621744269b5f8ee738bdf83c13f3118f6f4642e',
 'manuscripts/manuscript_01/visuals/figures/M1F05_f3b_period_recovery.pdf': '96c105a1dcff766390d0faa0eaba70f9d4707bb4e5278fca72e86b219995c185',
 'manuscripts/manuscript_01/visuals/figures/M1F05_f3b_period_recovery.png': '17cb98e656c03d1d1fcdc059c503234192342792bd601ad3479d1dff1395b508',
 'manuscripts/manuscript_01/visuals/tables/M1T01_evidence_planes.csv': 'bb2263fc95a5a2c3e70f555471e9fe359b4ba814741a28910ce5aff3de82618c',
 'manuscripts/manuscript_01/visuals/tables/M1T01_evidence_planes.tex': '28f9809c08cabb4d1ef084dce635aa7753d7896ba02e12a8d0389d4964420de6',
 'manuscripts/manuscript_01/visuals/tables/M1T02_f3a_robustness_counts.csv': '4424822e696a6112e78f68b52018ef89cb5cfcdaf40131606bffa7b29b79665b',
 'manuscripts/manuscript_01/visuals/tables/M1T02_f3a_robustness_counts.tex': 'f22bdd6287151eab469112cfb89e2afa3b043bbd5bd2472cfc4b7fe516c90150',
 'manuscripts/manuscript_01/visuals/tables/M1T03_synthetic_performance.csv': '2f929b33c79dfef009320b4c1e67be499f3ad0a85981a0e96b604509cf619045',
 'manuscripts/manuscript_01/visuals/tables/M1T03_synthetic_performance.tex': '83266bed70ae6aa60419144d01401d0418e18bde814343ff86376226366f0111',
 'manuscripts/manuscript_01/visuals/tables/M1T04_claim_boundaries.csv': '7b22ee46585ea6b0b3176e0d0723fdf32c979c9cbeb2f2dc9b11cc4c95158225',
 'manuscripts/manuscript_01/visuals/tables/M1T04_claim_boundaries.tex': '68b35fb7652933c38aeb73f505a12faeda91d448c9917b54a850931666116df8'}
M13_HASHES = {'docs/decisions/DR-011-manuscript1-first-complete-draft.md': 'f1695781ef5b4e761a2bfd91e87ecd3c3dcf14ce9b203c11d3f9e4115082cc6e',
 'manuscripts/manuscript_01/draft/README.md': 'f90f8b73ee1a378fb1d10ef9f4042eb8de4ba6b6c9279336109684288533d644',
 'manuscripts/manuscript_01/draft/evidence/SHA256SUMS.txt': '797b286f65ecdaecba4f03365c11466cf236cf93233f33d640e90c1c985ed810',
 'manuscripts/manuscript_01/draft/evidence/m1_3_citation_audit.csv': 'b186f6189b7a2af046969983e42f1860a584e4ac265ee34bdabaa11137c07075',
 'manuscripts/manuscript_01/draft/evidence/m1_3_claim_usage.csv': 'fea995690d2641b4b6dfc7b72a5064513ba98df59f6b44c49b9f8e6963c35202',
 'manuscripts/manuscript_01/draft/evidence/m1_3_draft_audit.json': 'e9bb64b7aa766747a9bfb39dbfae989be9147ad38849bbad5642b633796a0b0a',
 'manuscripts/manuscript_01/draft/evidence/m1_3_figure_table_usage.csv': 'e212771bd9f495973bfc2f60bad42da18bb143354a113951765be5eebf9c0c58',
 'manuscripts/manuscript_01/draft/evidence/m1_3_numeric_traceability.csv': 'd8f60cc3b8b978a9ed8c32d5aac11baf04fb30b555054faba9961fc06e903e1b',
 'manuscripts/manuscript_01/draft/evidence/m1_3_section_word_counts.csv': '917aab76b4c10838a09465debb7e10ef26d630fdf081b9d66ed20557fd22e54f',
 'manuscripts/manuscript_01/draft/evidence/m1_3_source_bindings.json': 'a9a6201ac15eeb28c572a2e514d430aa9ab14df12d4168398e7bb2d32d32b6e1',
 'manuscripts/manuscript_01/draft/manuscript_v1.pdf': '71fa1f614e7623e54481fbb59e059e39734201701320a0220333a0062dd00127',
 'manuscripts/manuscript_01/draft/manuscript_v1.tex': 'bf99e137972aeea9dec8739609a5937a6f1439182042ba1565fd80f3b19f2977',
 'manuscripts/manuscript_01/draft/notes/m1_3_author_queries.md': '3609bcb544f9822a7e16283a8e86c4a8a0d3d97c5715dbff5d6b64c879f1543a',
 'manuscripts/manuscript_01/draft/references.bib': 'aee3e5c9145828ea122e65b026e1a900d87371c25daaa15d046f255d985bbd7e',
 'manuscripts/manuscript_01/scripts/validate_manuscript1_first_draft.py': 'd999d7bb17f76df6a68dad9824f2af5fc724a4c5b87861cd4e024e56ee594046',
 'manuscripts/manuscript_01/tests/test_manuscript1_first_draft.py': '574450185a4b81de008cabccff1e3fc993a76fbe4065d2913e356a1f3ebfba6c'}
SOURCE_HASHES = {'docs/literature/bibliographic_audit_ii/closure/final_evidence_ledger.csv': '09f7d73f97773672b90552cfe7fc73d8bd0fa4e67a8a0460bb3c6dbd4f63ab0a',
 'docs/literature/bibliographic_audit_ii/closure/final_gate_decision.json': '3bd6872cdf558889769d245ba86d7cd924bd333db1fe117a9a591e9755ba8c1c',
 'docs/literature/bibliographic_audit_ii/closure/final_synthesis_report.md': '84b795fda2711c45aa18364775545ce5c7ad4ada1c80cd4863078345ede0d2d5',
 'docs/literature/bibliographic_audit_ii/closure/precedence_positioning_matrix.csv': '0b14fe7002b1b11e77b56203b9d85336b5b21ac2683bd0e1a1c64799b8d035e1',
 'foundation/f0-f2/phase0/fase0_tarea15_evidence_matrix.csv': '42136fc3ef268c65c72d15910e6f248ed513940f268c4bcf5e69b455a143b270',
 'foundation/f0-f2/phase0/fase0_tarea15_phase0_synthesis.md': 'cdebb7584ff1d1dbaadfa9f1c0dd55883aa7d1573627a7303bc17c3671613b0e',
 'foundation/f0-f2/phase0/fase0_tarea15_reproduced_baseline.json': '4c0bf97f875b9beb2bd2d619b26fa77b083fb946a05d3ee48c32896046690dc7',
 'foundation/f0-f2/phase1/fase1_tarea06_condition_summary.csv': '25c60ca7cfdbb46bb9a389fa16ce8f2be98e734e689186815c6a97cdc042d1eb',
 'foundation/f0-f2/phase1/fase1_tarea06_core_benchmark_analysis.md': 'c9d31f3b248ae6298eb40d50b27f58adc545226c2c616996584a7cd0749a570c',
 'foundation/f0-f2/phase1/fase1_tarea06_model_diagnostics.csv': 'cb5ec327e240e7bf0ebfd33ea8d2e1a262f45996ca7611de55a8dd678814eccf',
 'foundation/f0-f2/phase1/fase1_tarea06_optimizer_stability_summary.csv': 'c08bd09988b5ae220bc0f83213b4af4c648923c0883995ad084a65ed455b13e2',
 'foundation/f0-f2/phase1/fase1_tarea13_condition_summary.csv': '1358d319313e2adb98e6e2d64f770eb00eb190169a77a6d3b05901a1cb1aa427',
 'foundation/f0-f2/phase1/fase1_tarea13_model_diagnostics_by_n.csv': 'd8a4193c644d820a2546cd828e9ef141aa674bd89401d5a1cf1afe98743f0a54',
 'foundation/f0-f2/phase1/fase1_tarea13_nested_analysis_audit.json': '7994cd4475c02f2f2675a3275dc1b7d6b90f0bfc9a9532555ea0541e8012ef35',
 'foundation/f0-f2/phase1/fase1_tarea13_nested_analysis_report.md': '532711677fdc92ad317110000f27c49bc72c1a809892bca6a93c6a32d871b728',
 'foundation/f0-f2/phase1/fase1_tarea13_optimizer_stability_summary.csv': '0250bf0deb69f02e8a716b9c8e77c43dc962ad6b28147c1831fc28570793bbc9',
 'foundation/f0-f2/phase1/fase1_tarea14_phase1_decision.json': '356504bce1df734bfd5cf01cf1e84211fc5a458f6bf81ddb5458ef0a9166ef1a',
 'foundation/f0-f2/phase1/fase1_tarea14_phase1_evidence_ledger.csv': 'ab471a68016c19abb6672be7ab29f1f890d9b9c67dfdf750edfb224afbae975a',
 'foundation/f0-f2/phase1/fase1_tarea14_phase1_synthesis_report.md': '5d748476630023ec6b0f4a11c0851711f34b5b5c7a20a2e30fce1b1138a6c466',
 'foundation/f0-f2/phase2/fase2_tarea05_event_summary.csv': 'e43d6656f82b97b57b6dc7df5ed1b2060304a7202bcf214e1c6087327edf52d7',
 'foundation/f0-f2/phase2/fase2_tarea05_observational_robustness_audit.json': 'be80d4bcb56199624787bc49ad15a59648cc541d44907c975229967ef74ca3d1',
 'foundation/f0-f2/phase2/fase2_tarea05_observational_robustness_report.md': '0b9b2451be1fbe46418ad810591d6c54c8ddf6a2cb93e2b67dfd65196dc530aa',
 'foundation/f0-f2/phase2/fase2_tarea05_optimizer_stability_summary.csv': '47710386c2735cdcde10230735b249db87896f58a33b6af5180ea8e85594a7ea',
 'foundation/f0-f2/phase2/fase2_tarea05_period_robustness.csv': '4f411991b4cecff126700d143bb38fc7ef0dd4ad7e631c66fa5d5a255e0df53d',
 'foundation/f0-f2/phase2/fase2_tarea06_manuscript_claim_matrix.csv': '070c7cb4eb85345c6222ecc476d527007abdfff940d80b2fd3a1b009286e57b0',
 'foundation/f0-f2/phase2/fase2_tarea06_phase2_decision.json': '6ac1962077833b08d979b715a52a75a99b1d3a169430ca7abc46d17926eb3ab2',
 'foundation/f0-f2/phase2/fase2_tarea06_phase2_evidence_ledger.csv': 'eb6eb383839d5360ad9b843d61b682a808f49c6f5932bea1c30d0c47a4aaa225',
 'foundation/f0-f2/phase2/fase2_tarea06_phase2_limitations_register.csv': '5379501c84162ff18b4c1dfc7d576e9051a214c885a2ab0ce10faf684d67c07a',
 'foundation/f0-f2/phase2/fase2_tarea06_phase2_synthesis_report.md': 'b2c693c40fd8d29227e4d03837e1901e488624b1dc60d87ca8b5b5461a93303e',
 'workflows/phase3a/closure/f3a6_claim_matrix.csv': '46bbafc78230b77d7e0cca0cc7a87d18588da4eb7247e6a23e420524dd1aa8b4',
 'workflows/phase3a/closure/f3a6_limitations_register.csv': '7a9dd6eede0038c320d719bb78d9c3a2a5d63a25740847d0e222078a34e6d2e0',
 'workflows/phase3a/closure/f3a6_phase3a_decision.json': '7826665097e7fdaf366d24eb914abb3a357b9a5ad60bcdeee887a286db919214',
 'workflows/phase3a/closure/f3a6_phase3a_synthesis_report.md': 'c6398e78364047a8e0dac3cfffb7b1661f23f8bbef8fa2f64d1d151234ad5432',
 'workflows/phase3a/evidence/reports/f3a5_robustness_audit.json': 'fd5be4f38e656ed9bcac7c1974e15a40baac2666404880d792e1b89120b847f2',
 'workflows/phase3a/evidence/tables/f3a5_optimizer_stability.csv': '2f1286e6697b87a7de6ec63c4237f40a4943e3dcb6ad256be1e06cd1a3ee3767',
 'workflows/phase3a/evidence/tables/f3a5_period_robustness.csv': 'b231bab71060bbc4b444a62beafaeb29798e766ba4a09baca14f5a42712dd5f3',
 'workflows/phase3a/evidence/tables/f3a5_primary_outcome_matrix.csv': '950547b4c97b871d8a6015ffaef6a8931252b4fd34d75b3ad00a7c69d85e0526',
 'workflows/phase3a/evidence/tables/f3a5_reference_baseline_audit.csv': '86958544bd2f8246c79a7b0a75abd1aaf55d6ca2b044c65fa5c34725c2eed2bc',
 'workflows/phase3b/closure/f3b8_claim_matrix.csv': 'f913ad8588e14a1ec7b161956e91494e82c71aac936b9a73655c3a46b7b5581a',
 'workflows/phase3b/closure/f3b8_limitations_register.csv': 'ba745119a38b9711a556454b4fcf5c22c3830ac130beb4a1fc0429efedc54851',
 'workflows/phase3b/closure/f3b8_manuscript1_handoff.csv': 'aaa8dc0e5d3a22811f345b0a456b7e71458058d075529e5a09d4e4e657f2e891',
 'workflows/phase3b/closure/f3b8_phase3b_decision.json': 'fe00632755722d37fcb6c6d5f90d1e6b65f7e6552bb6a023da419e387027111a',
 'workflows/phase3b/development/analysis/f3b4_baseline_metrics.json': '718f1a03af218da8a3bc52cdea9f8007f7b3dffc3477038a5577eef0f162250c',
 'workflows/phase3b/development/analysis/f3b4_candidate_rule_gate.json': 'f47b2b03aff0d60d8dbce040d7298d1904295552f610cdf92bba6a48f6eddbf9',
 'workflows/phase3b/development/analysis/f3b4_final_rule_freeze.json': 'e2faffdbb15d6e0fec52ff166e81a2ed58f5665d7d3f9dc43cb8b78f5c0a198c',
 'workflows/phase3b/heldout/evaluation/evidence/reports/f3b7_heldout_baseline_metrics.json': '2d69eb0bea19edea244721065b34e995b26b9b9665174b0f63d8e14de8516730',
 'workflows/phase3b/heldout/evaluation/evidence/tables/f3b7_heldout_period_recovery.csv': 'a7f1ab028d80e8a4c64b16e1f791f7c565b7021dcda5de50ec6bf9524bbe493c',
 'workflows/phase3b/heldout/evaluation/evidence/tables/f3b7_heldout_selection_function.csv': 'fe8654481c83f23c9ebc276a84455d0c2f6de55d9e76011d1199cafa43a30509'}
REFEREE_EXPECTED = {'M14R01': {'claims': ['M1C006', 'M1C007'], 'limitations': ['M1L008']},
 'M14R02': {'claims': ['M1C005', 'M1C008', 'M1C010'], 'limitations': ['M1L008', 'M1L009']},
 'M14R03': {'claims': ['M1C015', 'M1C016'], 'limitations': ['M1L013']},
 'M14R04': {'claims': ['M1C013', 'M1C014'], 'limitations': ['M1L012']},
 'M14R05': {'claims': ['M1C002', 'M1C012', 'M1C020', 'M1C025'], 'limitations': ['M1L003', 'M1L014']},
 'M14R06': {'claims': ['M1C019', 'M1C020', 'M1C023'], 'limitations': ['M1L014']},
 'M14R07': {'claims': ['M1C021', 'M1C022', 'M1C014'], 'limitations': ['M1L015', 'M1L012']},
 'M14R08': {'claims': ['M1C003', 'M1C011'], 'limitations': ['M1L004', 'M1L010']},
 'M14R09': {'claims': ['M1C017', 'M1C018'], 'limitations': ['M1L016']},
 'M14R10': {'claims': ['M1C012', 'M1C017', 'M1C018'], 'limitations': ['M1L016', 'M1L017']},
 'M14R11': {'claims': ['M1C028'], 'limitations': ['M1L018']},
 'M14R12': {'claims': ['M1C028'], 'limitations': ['M1L007', 'M1L018']}}

EXPECTED_V2_TEX_SHA = "68178633764c3fc51a62434f520ed7c11f40d03a882bc6330c7546b5267baddd"
EXPECTED_V2_PDF_SHA = "3e9325f4777f243676de45a4e42809479ec95f3342b2c0cd437ddc239702ea5d"
EXPECTED_REF_BIB_SHA = "aee3e5c9145828ea122e65b026e1a900d87371c25daaa15d046f255d985bbd7e"

PROHIBITED_CLAIMS = {"M1C026","M1C027"}
EXPECTED_ALLOWED_CLAIMS = {
    "M1C001","M1C002","M1C003","M1C004","M1C005","M1C006","M1C007","M1C008","M1C009",
    "M1C010","M1C011","M1C012","M1C013","M1C014","M1C015","M1C016","M1C017","M1C018",
    "M1C019","M1C020","M1C021","M1C022","M1C023","M1C024","M1C025","M1C028","M1C029"
}

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def rows(path: Path):
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def require(cond: bool, msg: str):
    if not cond:
        raise RuntimeError(msg)

def verify_hash_registry(registry: dict[str,str], label: str):
    for rel, expected in registry.items():
        p=ROOT/rel
        require(p.is_file(), f"{label} file missing: {rel}")
        require(sha(p)==expected, f"{label} file changed: {rel}")

# 1. Frozen upstream planes and source-bound evidence remain exact.
verify_hash_registry(PLANNING_HASHES, "M1.1 architecture")
verify_hash_registry(M12_HASHES, "M1.2 visual freeze")
verify_hash_registry(M13_HASHES, "M1.3 first-draft freeze")
verify_hash_registry(SOURCE_HASHES, "M1.1 authoritative source binding")
require(len(PLANNING_HASHES)==10, "M1.1 planning hash count changed")
require(len(M12_HASHES)==29, "M1.2 frozen-file hash count changed")
require(len(M13_HASHES)==16, "M1.3 frozen-file hash count changed")
require(len(SOURCE_HASHES)==48, "M1.1 source-binding hash count changed")

# 2. Final M1.4 package files and checksum registry.
required = [
    "manuscripts/manuscript_01/revision/README.md",
    "manuscripts/manuscript_01/revision/manuscript_v2.tex",
    "manuscripts/manuscript_01/revision/manuscript_v2.pdf",
    "manuscripts/manuscript_01/revision/references_v2.bib",
    "manuscripts/manuscript_01/revision/evidence/m1_4_review_contract.json",
    "manuscripts/manuscript_01/revision/evidence/m1_4_issue_register.csv",
    "manuscripts/manuscript_01/revision/evidence/m1_4_claim_language_audit.csv",
    "manuscripts/manuscript_01/revision/evidence/m1_4_numeric_traceability.csv",
    "manuscripts/manuscript_01/revision/evidence/m1_4_citation_audit.csv",
    "manuscripts/manuscript_01/revision/evidence/m1_4_visual_layout_audit.csv",
    "manuscripts/manuscript_01/revision/evidence/m1_4_revision_log.csv",
    "manuscripts/manuscript_01/revision/evidence/m1_4_pre_edit_audit.json",
    "manuscripts/manuscript_01/revision/evidence/m1_4_referee_audit.md",
    "manuscripts/manuscript_01/revision/evidence/m1_4_revision_audit.json",
    "manuscripts/manuscript_01/revision/evidence/SHA256SUMS.txt",
    "manuscripts/manuscript_01/revision/notes/m1_4_remaining_author_queries.md",
    "manuscripts/manuscript_01/scripts/validate_manuscript1_reviewed_draft.py",
    "manuscripts/manuscript_01/tests/test_manuscript1_reviewed_draft.py",
    "docs/decisions/DR-012-manuscript1-scientific-editorial-review.md",
]
for rel in required:
    require((ROOT/rel).is_file(), f"M1.4 required file missing: {rel}")

sum_lines=[x for x in (EV/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines() if x.strip()]
require(len(sum_lines)==18, f"M1.4 checksum target count != 18: {len(sum_lines)}")
sum_targets=set()
for line in sum_lines:
    expected, rel=line.split("  ",1)
    require(rel!="manuscripts/manuscript_01/revision/evidence/SHA256SUMS.txt","checksum registry includes itself")
    p=ROOT/rel
    require(p.is_file(), f"M1.4 checksum target missing: {rel}")
    require(sha(p)==expected, f"M1.4 checksum mismatch: {rel}")
    sum_targets.add(rel)
require(sum_targets==set(required)-{"manuscripts/manuscript_01/revision/evidence/SHA256SUMS.txt"}, "M1.4 checksum target universe mismatch")

# 3. Contract / audit status and firewalls.
contract=json.loads((EV/"m1_4_review_contract.json").read_text(encoding="utf-8"))
audit=json.loads((EV/"m1_4_revision_audit.json").read_text(encoding="utf-8"))
require(contract["status"]=="SCIENTIFIC_EDITORIAL_REVIEW_COMPLETE_VALIDATION_READY","final review contract status mismatch")
require(contract["gates"]=={
    "gate1_issue_register":"COMPLETE_PRE_EDIT_AND_RESOLVED_IN_V2",
    "gate2_semantic_language_audit":"COMPLETE_V2_ZERO_REVISE",
    "gate3_scientific_editing":"COMPLETE",
    "gate4_visual_readability":"COMPLETE_TABLE1_TABLE4_PASS",
    "gate5_referee_attack_test":"COMPLETE_12_OF_12_PASS",
}, "gate completion map mismatch")
require(contract["referee_attack_test"]["attack_count"]==12 and contract["referee_attack_test"]["pass_count"]==12,"referee contract count mismatch")
require(contract["referee_attack_test"]["new_defense_claims"]==0,"new referee defense claim introduced")
require(contract["target_journal_formatting_started"] is False,"target-journal formatting started inside M1.4")
for k,v in contract["firewalls"].items():
    require(v is False, f"contract firewall violated: {k}")

require(audit["status"]=="GATE1_TO_GATE5_COMPLETE_FINAL_VALIDATION_READY","final revision audit status mismatch")
require(audit["gate5_referee_attack_test_complete"] is True,"Gate 5 not complete")
require(audit["referee_attack_questions"]==12 and audit["referee_attack_pass"]==12 and audit["referee_attack_fail"]==0,"Gate 5 audit counts mismatch")
require(audit["new_referee_defense_claims"]==0,"new referee defense claim recorded")
require(audit["target_journal_formatting_started"] is False,"target-journal formatting boundary violated")
require(audit["required_final_validator_result"]=="MANUSCRIPT1_SCIENTIFIC_EDITORIAL_REVIEW_PASS","required validator marker mismatch")

for k in [
    "new_scientific_computation","new_statistical_inference","new_bibliographic_search",
    "new_afino_execution","new_synthetic_generation","new_confidence_intervals",
    "new_scientific_figures_tables","new_threshold_search","visual_regeneration",
]:
    require(audit[k] is False, f"revision firewall violated: {k}")
require(audit["m1_1_to_m1_3_mutation"] is False,"M1.1-M1.3 mutation reported")

# 4. Gate 1 issue resolution, Gate 2 semantic-language zero-REVISE.
issues=rows(EV/"m1_4_issue_register.csv")
require(len(issues)==10,"issue register count != 10")
require(all(r["status"].startswith("RESOLVED_") for r in issues),"unresolved M1.4 issue remains")
require(all(r["scientific_effect"]=="NONE" for r in issues),"issue register scientific effect is not NONE")

lang=rows(EV/"m1_4_claim_language_audit.csv")
require(len(lang)==155,"semantic language row count != 155")
require(all(r["status"]=="PASS" for r in lang),"semantic audit contains non-PASS row")
require(all(r["scope_explicit"]=="true" and r["qualification_present"]=="true" for r in lang if r["term"]=="VALIDATION"),"generic/unqualified validation language remains")
require(audit["generic_validation_language_unqualified"]==0,"generic validation count nonzero")
require(audit["observational_synthetic_conflation"]==0,"observational/synthetic conflation nonzero")
require(audit["denominator_conflation"]==0,"denominator conflation nonzero")

# 5. V2 trace metadata must be identical to frozen V1.
v1=(DRAFT/"manuscript_v1.tex").read_text(encoding="utf-8")
v2=(REV/"manuscript_v2.tex").read_text(encoding="utf-8")
trace_re=re.compile(r"% M1TRACE paragraph=(\S+) claims=([^\n]*) sources=([^\n]*) plane=([^\n]*)\n")
def trace_meta(tex):
    out={}
    for m in trace_re.finditer(tex):
        out[m.group(1)]=(m.group(2),m.group(3),m.group(4))
    return out
t1=trace_meta(v1); t2=trace_meta(v2)
require(t1==t2,"M1TRACE claim/source/evidence-plane mappings changed in v2")
require(len(t2)==76,"M1TRACE record count != 76")
require(sum(k.startswith("M1P") for k in t2)==71,"scientific paragraph trace count != 71")
require(sum(k.startswith("M1CAPF") for k in t2)==5,"figure-caption trace count != 5")

used_claims=set()
used_sources=set()
for claims_s,sources_s,planes_s in t2.values():
    used_claims.update(x for x in claims_s.split(",") if x)
    used_sources.update(x for x in sources_s.split(",") if x)
require(used_claims==EXPECTED_ALLOWED_CLAIMS,"v2 non-prohibited claim coverage changed")
require(not (used_claims & PROHIBITED_CLAIMS),"prohibited claim ID appears in v2 trace")
require(audit["claim_ids_used_count"]==27,"revision audit claim count != 27")
require(audit["new_claim_ids"]==[] and audit["new_source_ids"]==[],"new claim/source IDs recorded")

# 6. Numeric traceability: exact frozen mapping retained and each mapping remains status-PASS.
nums=rows(EV/"m1_4_numeric_traceability.csv")
frozen_nums=rows(DRAFT/"evidence/m1_3_numeric_traceability.csv")
require(len(nums)==120 and len(frozen_nums)==120,"numeric traceability row count != 120")
core=["numeric_id","paragraph_or_caption_id","displayed_value","scientific_meaning","claim_id","source_id","source_artifact","source_locator","frozen_source_value","transformation","status"]
for a,b in zip(nums,frozen_nums):
    require(all(a[k]==b[k] for k in core),f"numeric mapping changed: {a['numeric_id']}")
    require(a["revision_version"]=="M1.4_V2" and a["revision_status"]=="UNCHANGED_NUMERAL_MAPPING_REVERIFIED",f"numeric v2 audit status invalid: {a['numeric_id']}")
require(audit["numeric_items"]==120 and audit["numeric_items_traceable"]==120,"numeric traceability summary mismatch")

# 7. Citations remain exactly frozen-corpus citations.
cites=rows(EV/"m1_4_citation_audit.csv")
require(len(cites)==8,"citation audit count != 8")
require(all(r["new_bibliographic_search"]=="false" for r in cites),"citation audit reports new bibliography search")
tex_cites=set()
for content in re.findall(r"\\cite\w*\{([^}]*)\}",v2):
    tex_cites.update(x.strip() for x in content.split(",") if x.strip())
bib_keys=set(re.findall(r"@\w+\{([^,]+),",(REV/"references_v2.bib").read_text(encoding="utf-8")))
audit_keys={r["citation_key"] for r in cites}
require(tex_cites==bib_keys==audit_keys and len(tex_cites)==8,"v2 citation key universe mismatch")
require(audit["citations"]==8 and audit["citations_from_frozen_corpus"]==8,"citation summary mismatch")

# 8. Frozen visuals unchanged and revised layout all PASS.
visual=rows(EV/"m1_4_visual_layout_audit.csv")
require(len(visual)==9,"visual layout audit count != 9")
for r in visual:
    p=ROOT/r["frozen_repository_relative_path"]
    require(p.is_file() and sha(p)==r["frozen_sha256"],f"frozen visual changed: {r['artifact_id']}")
    require(r["revised_status"]=="PASS",f"visual readability not PASS: {r['artifact_id']}")
    require(r["scientific_content_changed"]=="false",f"scientific visual content changed: {r['artifact_id']}")
status={r["artifact_id"]:r["revised_status"] for r in visual}
require(status["M1T01"]=="PASS","Table 1 readability not PASS")
require(status["M1T04"]=="PASS","Table 4 readability not PASS")
require(audit["table1_readability"]=="PASS" and audit["table4_readability"]=="PASS","table readability summary mismatch")
require(audit["pdf_render_inspection"]=="PASS","PDF render inspection not PASS")

# 9. Revision log contains only bounded edits with zero scientific effect.
log=rows(EV/"m1_4_revision_log.csv")
require(len(log)==10,"revision log count != 10")
require(all(r["scientific_effect"]=="NONE" and r["new_claim_ids"]=="NONE" and r["new_source_ids"]=="NONE" and r["new_scientific_numerals"]=="NONE" for r in log),"revision log contains scientific/new-ID effect")

# 10. Gate 5 referee attack test: all mandatory questions and mappings.
ref_text=(EV/"m1_4_referee_audit.md").read_text(encoding="utf-8")
attack_ids=re.findall(r"^## (M14R\d{2}) — ",ref_text,flags=re.M)
require(attack_ids==[f"M14R{i:02d}" for i in range(1,13)],"referee attack ID universe/order mismatch")
require(ref_text.count("**Verdict:** `PASS_BOUNDED_BY_FROZEN_CLAIMS`")==12,"referee PASS verdict count != 12")

claim_rows={r["claim_id"]:r for r in rows(PLANNING/"m1_claim_matrix.csv")}
lim_rows={r["limitation_id"]:r for r in rows(PLANNING/"m1_limitations_matrix.csv")}
for aid, expected in REFEREE_EXPECTED.items():
    sec=re.search(rf"^## {aid} — .*?(?=^## M14R|^## Gate 5 conclusion)",ref_text,flags=re.M|re.S)
    require(sec is not None,f"referee section missing: {aid}")
    s=sec.group(0)
    for cid in expected["claims"]:
        require(cid in s,f"referee {aid} missing claim {cid}")
        require(cid in claim_rows and claim_rows[cid]["status"]!="PROHIBITED",f"referee {aid} maps prohibited/unknown claim {cid}")
    for lid in expected["limitations"]:
        require(lid in s,f"referee {aid} missing limitation {lid}")
        require(lid in lim_rows,f"referee {aid} maps unknown limitation {lid}")
require(audit["referee_attack_questions"]==12 and audit["referee_attack_pass"]==12,"referee summary mismatch")

# 11. Known high-risk wording corrections remain in V2.
required_phrases=[
    "no new classifier rule was promoted to synthetic-ground-truth held-out evaluation",
    "known-truth evaluation analogues",
    "catalogue-scale dependence of reference classifications on methodological perturbations",
    "correction \\texttt{NOT\\_ESTABLISHED}",
]
for phrase in required_phrases:
    require(phrase in v2,f"required bounded v2 wording missing: {phrase}")
for forbidden in [
    "no new classifier rule was validated",
    "known-truth validation analogues",
    "catalogue-scale methodological sensitivity",
    "Scaling therefore did not remove sensitivity to analysis choices.",
]:
    require(forbidden not in v2,f"known over-broad v1 wording remains: {forbidden}")

# 12. PDF and exact v2 identities.
require(sha(REV/"manuscript_v2.tex")==EXPECTED_V2_TEX_SHA,"manuscript_v2.tex identity mismatch")
require(sha(REV/"manuscript_v2.pdf")==EXPECTED_V2_PDF_SHA,"manuscript_v2.pdf identity mismatch")
require(sha(REV/"references_v2.bib")==EXPECTED_REF_BIB_SHA,"references_v2.bib identity mismatch")
data=(REV/"manuscript_v2.pdf").read_bytes()
require(data.startswith(b"%PDF-") and b"%%EOF" in data[-4096:],"manuscript_v2.pdf envelope invalid")
search=bytearray(data)
for sm in re.finditer(rb"stream\r?\n",data):
    start=sm.end(); end=data.find(b"endstream",start)
    if end<0: continue
    header=data[max(0,sm.start()-600):sm.start()]
    if b"/FlateDecode" not in header: continue
    blob=data[start:end].rstrip(b"\r\n")
    try: search.extend(zlib.decompress(blob))
    except zlib.error: pass
require(re.search(rb"/Count\s+22\b",bytes(search)) is not None,"manuscript_v2.pdf page count != 22")

# 13. Required final status / decision record.
readme=(REV/"README.md").read_text(encoding="utf-8")
required_status="STATUS:\nSCIENTIFIC / EDITORIAL REVIEW COMPLETE —\nREVISED SCIENTIFIC DRAFT FROZEN\nTARGET-JOURNAL FORMATTING NOT STARTED"
require(required_status in readme,"final README status block missing")
dr=(ROOT/"docs/decisions/DR-012-manuscript1-scientific-editorial-review.md").read_text(encoding="utf-8")
require("12/12 mandatory referee attacks" in dr,"DR-012 missing Gate 5 outcome")
require("Target-journal formatting" in dr,"DR-012 missing post-M1.4 boundary")

print("MANUSCRIPT1_SCIENTIFIC_EDITORIAL_REVIEW_PASS")
print("m1_1_architecture_unchanged = true")
print("m1_1_source_bindings = 48/48")
print("m1_2_visuals_unchanged = true")
print("m1_3_first_draft_unchanged = true")
print("issues_resolved = 10/10")
print("semantic_language_rows = 155")
print("generic_validation_unqualified = 0")
print("observational_synthetic_conflation = 0")
print("denominator_conflation = 0")
print("scientific_paragraphs_traceable = 71/71")
print("figure_captions_traceable = 5/5")
print("claim_ids_used = 27")
print("prohibited_claims = 0")
print("new_claim_ids = 0")
print("new_source_ids = 0")
print("numeric_items_traceable = 120/120")
print("citations_frozen_corpus = 8/8")
print("figures = 5/5")
print("tables = 4/4")
print("table1_readability = PASS")
print("table4_readability = PASS")
print("pdf_render_inspection = PASS")
print("pdf_pages = 22")
print("referee_attacks = 12/12 PASS")
print("new_scientific_computation = false")
print("new_statistical_inference = false")
print("new_bibliography_search = false")
print("new_afino_execution = false")
print("new_synthetic_generation = false")
print("target_journal_formatting_started = false")
