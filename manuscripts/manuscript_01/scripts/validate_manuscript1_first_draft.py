from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
M1 = ROOT / "manuscripts/manuscript_01"
DRAFT = M1 / "draft"
EVID = DRAFT / "evidence"
PLANNING = M1 / "planning"

ARCH_VALIDATOR = M1 / "scripts/validate_manuscript1_architecture.py"
VIS_VALIDATOR = M1 / "scripts/validate_manuscript1_visuals.py"

README = DRAFT / "README.md"
TEX = DRAFT / "manuscript_v1.tex"
PDF = DRAFT / "manuscript_v1.pdf"
BIB = DRAFT / "references.bib"
AUTHOR_QUERIES = DRAFT / "notes/m1_3_author_queries.md"

SOURCE_BINDINGS = EVID / "m1_3_source_bindings.json"
CLAIM_USAGE = EVID / "m1_3_claim_usage.csv"
NUMERIC = EVID / "m1_3_numeric_traceability.csv"
CITATIONS = EVID / "m1_3_citation_audit.csv"
FIGTAB_USAGE = EVID / "m1_3_figure_table_usage.csv"
SECTION_COUNTS = EVID / "m1_3_section_word_counts.csv"
DRAFT_AUDIT = EVID / "m1_3_draft_audit.json"
SUMS = EVID / "SHA256SUMS.txt"

CLAIM_MATRIX = PLANNING / "m1_claim_matrix.csv"
PLANE_REGISTRY = PLANNING / "m1_evidence_plane_registry.csv"
M1_SOURCE_BINDINGS = PLANNING / "m1_source_bindings.json"
DR011 = ROOT / "docs/decisions/DR-011-manuscript1-first-complete-draft.md"

EXPECTED_M11_COMMIT = "52024ec3728eeda25f9d640d8f1395a87671c541"
EXPECTED_M11_TAG = "manuscript1-architecture-v1"
EXPECTED_M12_COMMIT = "7e65987511487ea7de01d1b2880cc70687823541"
EXPECTED_M12_TAG = "manuscript1-visuals-v1"

EXPECTED_MAIN_WORDS = 5725
EXPECTED_ABSTRACT_WORDS = 212
EXPECTED_PARAGRAPHS = 71
EXPECTED_FIGURE_CAPTIONS = 5
EXPECTED_CLAIM_USAGE_ROWS = 76
EXPECTED_NUMERIC_ROWS = 120
EXPECTED_CITATIONS = 8
EXPECTED_FIGURES = 5
EXPECTED_TABLES = 4
EXPECTED_SHA_TARGETS = 15
EXPECTED_REVIEW_INCIDENTS = ["M1D-REV-001"]

REQUIRED_M13_PATHS = {
    "docs/decisions/DR-011-manuscript1-first-complete-draft.md",
    "manuscripts/manuscript_01/draft/README.md",
    "manuscripts/manuscript_01/draft/manuscript_v1.tex",
    "manuscripts/manuscript_01/draft/manuscript_v1.pdf",
    "manuscripts/manuscript_01/draft/references.bib",
    "manuscripts/manuscript_01/draft/evidence/m1_3_source_bindings.json",
    "manuscripts/manuscript_01/draft/evidence/m1_3_claim_usage.csv",
    "manuscripts/manuscript_01/draft/evidence/m1_3_numeric_traceability.csv",
    "manuscripts/manuscript_01/draft/evidence/m1_3_citation_audit.csv",
    "manuscripts/manuscript_01/draft/evidence/m1_3_figure_table_usage.csv",
    "manuscripts/manuscript_01/draft/evidence/m1_3_section_word_counts.csv",
    "manuscripts/manuscript_01/draft/evidence/m1_3_draft_audit.json",
    "manuscripts/manuscript_01/draft/evidence/SHA256SUMS.txt",
    "manuscripts/manuscript_01/draft/notes/m1_3_author_queries.md",
    "manuscripts/manuscript_01/scripts/validate_manuscript1_first_draft.py",
    "manuscripts/manuscript_01/tests/test_manuscript1_first_draft.py",
}

ALLOWED_NUMERIC_TRANSFORMS = {
    "EXACT_SOURCE_VALUE",
    "DIRECT_CATEGORICAL_COUNT",
    "FLOAT_TO_INTEGER_FORMAT",
    "ROUND_5_DECIMALS",
    "ROUND_6_DECIMALS",
    "WORD_TO_DIGIT",
}

TRACE_RE = re.compile(
    r"% M1TRACE paragraph=(\S+) claims=([^\n]*) sources=([^\n]*) plane=([^\n]*)\n"
)
VISUAL_TRACE_RE = re.compile(
    r"% M1VISUAL artifact=(\S+) claims=([^\n]*) sources=([^\n]*) plane=([^\n]*)\n"
)
SCIENTIFIC_DIGIT_RE = re.compile(r"(?<![A-Za-z0-9])(?:\d+(?:\.\d+)?)(?![A-Za-z0-9])")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip("\r\n")


def split_ids(value: str, sep: str = ";") -> list[str]:
    return [x for x in value.split(sep) if x]


def extract_trace_units(tex: str):
    matches = list(TRACE_RE.finditer(tex))
    out = {}
    meta = {}
    for i, m in enumerate(matches):
        pid = m.group(1)
        if pid in out:
            raise RuntimeError(f"duplicate M1TRACE paragraph id: {pid}")
        start = m.end()
        next_trace = matches[i + 1].start() if i + 1 < len(matches) else len(tex)
        stop_marker = tex.find(r"\section*{Data and code provenance}", start)
        end = min(next_trace, stop_marker) if stop_marker != -1 else next_trace
        chunk = tex[start:end]
        if pid.startswith("M1CAPF"):
            cm = re.search(r"\\caption\{(.*?)\}", chunk, flags=re.S)
            if cm is None:
                raise RuntimeError(f"figure caption trace has no caption: {pid}")
            text = cm.group(1).strip()
        elif pid == "M1P0001":
            text = chunk.split(r"\end{abstract}", 1)[0].strip()
        else:
            lines = chunk.splitlines()
            collected = []
            started = False
            for line in lines:
                st = line.strip()
                if not started:
                    if not st or st.startswith("\\") or st.startswith("%"):
                        continue
                    started = True
                if started:
                    if not st:
                        break
                    if st.startswith(("\\begin{", "\\clearpage", "\\section", "\\subsection")):
                        break
                    collected.append(line)
            text = "\n".join(collected).strip()
            if not text:
                raise RuntimeError(f"M1TRACE paragraph has no visible prose: {pid}")
        out[pid] = text
        meta[pid] = {
            "claim_ids": [x for x in m.group(2).split(",") if x],
            "source_ids": [x for x in m.group(3).split(",") if x],
            "evidence_planes": [x for x in m.group(4).split(",") if x],
        }
    return out, meta


def scientific_digit_counter(text: str) -> Counter:
    # Citation keys can contain publication years but are not manuscript scientific numerals.
    text = re.sub(r"\\cite\w*\{[^}]*\}", "", text)
    return Counter(SCIENTIFIC_DIGIT_RE.findall(text))


def assert_upstream_validators():
    for script, marker in [
        (ARCH_VALIDATOR, "MANUSCRIPT1_ARCHITECTURE_VALIDATION_PASS"),
        (VIS_VALIDATOR, "M1_VISUAL_PACKAGE_VALIDATION_PASS"),
    ]:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        print(proc.stdout, end="")
        if proc.returncode != 0 or marker not in proc.stdout:
            raise RuntimeError(f"required upstream validator failed: {marker}")


def assert_git_boundary():
    if not (ROOT / ".git").exists():
        raise RuntimeError("M1.3 validator requires the real Git repository")

    if git("rev-list", "-n", "1", EXPECTED_M11_TAG) != EXPECTED_M11_COMMIT:
        raise RuntimeError("M1.1 architecture freeze tag changed")
    if git("rev-list", "-n", "1", EXPECTED_M12_TAG) != EXPECTED_M12_COMMIT:
        raise RuntimeError("M1.2 visual freeze tag changed")

    head = git("rev-parse", "HEAD")
    if head != EXPECTED_M12_COMMIT:
        subprocess.run(
            ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", EXPECTED_M12_COMMIT, head],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    protected_prefixes = (
        "foundation/f0-f2/",
        "docs/literature/bibliographic_audit_ii/",
        "workflows/phase3a/",
        "workflows/phase3b/",
        "manuscripts/manuscript_01/planning/",
        "manuscripts/manuscript_01/visuals/",
    )
    dirty = []
    for line in git("status", "--porcelain=v1", "--untracked-files=all").splitlines():
        if not line:
            continue
        rel = line[3:].replace("\\", "/")
        dirty.append(rel)
        if rel.startswith(protected_prefixes):
            raise RuntimeError(f"protected frozen path modified in M1.3: {rel}")
    # Before commit, only M1.3 paths may be dirty. After commit, this set is empty.
    unexpected = sorted(set(dirty) - REQUIRED_M13_PATHS)
    if unexpected:
        raise RuntimeError(f"unexpected dirty paths outside M1.3 universe: {unexpected}")


def validate_static() -> dict:
    missing = sorted(rel for rel in REQUIRED_M13_PATHS if not (ROOT / rel).is_file())
    if missing:
        raise RuntimeError(f"missing required M1.3 paths: {missing}")

    # No build intermediates or accidental extras in draft/.
    expected_draft = {
        "README.md",
        "manuscript_v1.tex",
        "manuscript_v1.pdf",
        "references.bib",
        "evidence/m1_3_source_bindings.json",
        "evidence/m1_3_claim_usage.csv",
        "evidence/m1_3_numeric_traceability.csv",
        "evidence/m1_3_citation_audit.csv",
        "evidence/m1_3_figure_table_usage.csv",
        "evidence/m1_3_section_word_counts.csv",
        "evidence/m1_3_draft_audit.json",
        "evidence/SHA256SUMS.txt",
        "notes/m1_3_author_queries.md",
    }
    actual_draft = {
        p.relative_to(DRAFT).as_posix()
        for p in DRAFT.rglob("*")
        if p.is_file()
    }
    if actual_draft != expected_draft:
        raise RuntimeError(
            f"draft file universe mismatch; missing={sorted(expected_draft-actual_draft)} "
            f"extra={sorted(actual_draft-expected_draft)}"
        )

    claim_rows = rows(CLAIM_MATRIX)
    claim_map = {r["claim_id"]: r for r in claim_rows}
    if len(claim_rows) != 29 or len(claim_map) != 29:
        raise RuntimeError("frozen M1.1 claim matrix identity changed")
    prohibited = {r["claim_id"] for r in claim_rows if r["status"] == "PROHIBITED"}
    if prohibited != {"M1C026", "M1C027"}:
        raise RuntimeError(f"prohibited claim universe changed: {prohibited}")

    plane_rows = rows(PLANE_REGISTRY)
    plane_ids = {r["evidence_plane_id"] for r in plane_rows}
    if len(plane_rows) != 6:
        raise RuntimeError("evidence plane count changed")

    m1bind = json.loads(M1_SOURCE_BINDINGS.read_text(encoding="utf-8"))
    m1sources = {r["source_id"]: r for r in m1bind["sources"]}
    if len(m1sources) != 48:
        raise RuntimeError("M1.1 source binding universe changed")

    bindings = json.loads(SOURCE_BINDINGS.read_text(encoding="utf-8"))
    if bindings["status"] != "FROZEN_UPSTREAM_ONLY":
        raise RuntimeError("M1.3 source-binding status changed")
    if bindings["upstream_freezes"]["m1_1"]["commit"] != EXPECTED_M11_COMMIT:
        raise RuntimeError("M1.3 M1.1 upstream commit changed")
    if bindings["upstream_freezes"]["m1_2"]["commit"] != EXPECTED_M12_COMMIT:
        raise RuntimeError("M1.3 M1.2 upstream commit changed")
    source_entries = bindings["m1_1_source_bindings"]
    if len(source_entries) != 48:
        raise RuntimeError("M1.3 source bindings do not preserve all 48 M1.1 sources")
    for r in source_entries:
        if r["source_id"] not in m1sources:
            raise RuntimeError(f"M1.3 source ID outside M1.1: {r['source_id']}")
        p = ROOT / r["repository_relative_path"]
        if not p.is_file() or p.stat().st_size != int(r["bytes"]) or sha(p) != r["sha256"]:
            raise RuntimeError(f"frozen source identity mismatch in M1.3: {r['source_id']}")
    if any(bindings["firewalls"].values()):
        raise RuntimeError("M1.3 source-binding firewall violated")

    visual_entries = bindings["m1_2_manuscript_facing_artifacts"]
    if len(visual_entries) != 9:
        raise RuntimeError("M1.3 manuscript-facing visual artifact count != 9")
    visual_ids = {r["artifact_id"] for r in visual_entries}
    expected_visual_ids = {f"M1F0{i}" for i in range(1, 6)} | {f"M1T0{i}" for i in range(1, 5)}
    if visual_ids != expected_visual_ids:
        raise RuntimeError("M1.3 visual artifact IDs changed")
    for r in visual_entries:
        p = ROOT / r["repository_relative_path"]
        if not p.is_file() or p.stat().st_size != int(r["bytes"]) or sha(p) != r["sha256"]:
            raise RuntimeError(f"frozen M1.2 manuscript-facing artifact changed: {r['artifact_id']}")
        if r["integration"] != "DIRECT_NO_REGENERATION":
            raise RuntimeError(f"non-direct visual integration detected: {r['artifact_id']}")

    tex = TEX.read_text(encoding="utf-8")
    trace_text, trace_meta = extract_trace_units(tex)
    if len(trace_text) != EXPECTED_CLAIM_USAGE_ROWS:
        raise RuntimeError(f"M1TRACE record count != {EXPECTED_CLAIM_USAGE_ROWS}: {len(trace_text)}")
    if sum(pid.startswith("M1P") for pid in trace_text) != EXPECTED_PARAGRAPHS:
        raise RuntimeError("scientific paragraph trace count changed")
    if sum(pid.startswith("M1CAPF") for pid in trace_text) != EXPECTED_FIGURE_CAPTIONS:
        raise RuntimeError("figure-caption trace count changed")

    visual_comments = list(VISUAL_TRACE_RE.finditer(tex))
    if len(visual_comments) != 4:
        raise RuntimeError("frozen table visual-usage comment count != 4")
    if {m.group(1) for m in visual_comments} != {f"M1T0{i}" for i in range(1, 5)}:
        raise RuntimeError("table visual-usage IDs changed")

    usage = rows(CLAIM_USAGE)
    if len(usage) != EXPECTED_CLAIM_USAGE_ROWS:
        raise RuntimeError("claim-usage row count changed")
    usage_map = {r["paragraph_id"]: r for r in usage}
    if len(usage_map) != len(usage) or set(usage_map) != set(trace_text):
        raise RuntimeError("claim-usage / M1TRACE paragraph universe mismatch")

    used_claims = set()
    for pid, r in usage_map.items():
        claims = split_ids(r["claim_ids"])
        sources = split_ids(r["source_ids"])
        planes = split_ids(r["evidence_planes"])
        if not claims or not sources or not planes:
            raise RuntimeError(f"trace row missing claim/source/plane: {pid}")
        if any(c not in claim_map for c in claims):
            raise RuntimeError(f"unknown claim in M1TRACE: {pid}")
        if prohibited.intersection(claims):
            raise RuntimeError(f"prohibited claim used: {pid} {prohibited.intersection(claims)}")
        if any(s not in m1sources for s in sources):
            raise RuntimeError(f"source outside frozen M1.1 used: {pid}")
        if any(p not in plane_ids for p in planes):
            raise RuntimeError(f"unknown evidence plane used: {pid}")
        if claims != trace_meta[pid]["claim_ids"]:
            raise RuntimeError(f"claim list differs between M1TRACE and claim audit: {pid}")
        if sources != trace_meta[pid]["source_ids"]:
            raise RuntimeError(f"source list differs between M1TRACE and claim audit: {pid}")
        if planes != trace_meta[pid]["evidence_planes"]:
            raise RuntimeError(f"plane list differs between M1TRACE and claim audit: {pid}")
        if r["text_sha256"] != hashlib.sha256(trace_text[pid].encode("utf-8")).hexdigest():
            raise RuntimeError(f"paragraph/caption text hash mismatch: {pid}")
        if r["status"] != "TRACEABLE_FROZEN_CLAIMS_ONLY":
            raise RuntimeError(f"trace row status changed: {pid}")
        used_claims.update(claims)

    expected_nonprohibited = {r["claim_id"] for r in claim_rows if r["status"] != "PROHIBITED"}
    if used_claims != expected_nonprohibited:
        raise RuntimeError(
            f"non-prohibited claim realization incomplete/extra: "
            f"missing={sorted(expected_nonprohibited-used_claims)} extra={sorted(used_claims-expected_nonprohibited)}"
        )

    # Every visible prose line in Methods/Results/Discussion is immediately trace-guarded.
    current_major = None
    lines = tex.splitlines()
    for i, line in enumerate(lines):
        st = line.strip()
        sm = re.match(r"\\section\{([^}]+)\}", st)
        if sm:
            current_major = sm.group(1)
            continue
        if current_major not in {"Methods", "Results", "Discussion"}:
            continue
        if not st or st.startswith(("%", "\\")):
            continue
        # Body prose is generated one paragraph per physical line. Previous nonempty line must be M1TRACE.
        j = i - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        if j < 0 or not lines[j].startswith("% M1TRACE "):
            raise RuntimeError(f"untraced scientific paragraph in {current_major}: line {i+1}")

    numeric_rows = rows(NUMERIC)
    if len(numeric_rows) != EXPECTED_NUMERIC_ROWS:
        raise RuntimeError(f"numeric trace rows != {EXPECTED_NUMERIC_ROWS}: {len(numeric_rows)}")
    if len({r["numeric_id"] for r in numeric_rows}) != len(numeric_rows):
        raise RuntimeError("duplicate numeric trace IDs")
    numeric_by_pid: dict[str, list[dict]] = defaultdict(list)
    for r in numeric_rows:
        pid = r["paragraph_or_caption_id"]
        if pid not in usage_map:
            raise RuntimeError(f"numeric item references unknown paragraph/caption: {r['numeric_id']}")
        if r["claim_id"] not in split_ids(usage_map[pid]["claim_ids"]):
            raise RuntimeError(f"numeric item claim absent from paragraph trace: {r['numeric_id']}")
        if r["source_id"] not in split_ids(usage_map[pid]["source_ids"]):
            raise RuntimeError(f"numeric item source absent from paragraph trace: {r['numeric_id']}")
        if r["source_id"] not in m1sources:
            raise RuntimeError(f"numeric item source outside M1.1: {r['numeric_id']}")
        expected_artifact = m1sources[r["source_id"]]["repository_relative_path"]
        if r["source_artifact"] != expected_artifact:
            raise RuntimeError(f"numeric source artifact mismatch: {r['numeric_id']}")
        if r["transformation"] not in ALLOWED_NUMERIC_TRANSFORMS:
            raise RuntimeError(f"unauthorized numeric transformation: {r['numeric_id']}")
        if r["status"] != "TRACEABLE_TO_FROZEN_SOURCE":
            raise RuntimeError(f"numeric trace status changed: {r['numeric_id']}")
        numeric_by_pid[pid].append(r)

    # Every explicit scientific digit token in M1TRACE prose/captions is represented at least once.
    for pid, text in trace_text.items():
        visible_digits = scientific_digit_counter(text)
        traced_digits = Counter(r["displayed_value"] for r in numeric_by_pid.get(pid, []))
        missing_digits = visible_digits - traced_digits
        if missing_digits:
            raise RuntimeError(f"untraced scientific numeral(s) in {pid}: {dict(missing_digits)}")

    citation_rows = rows(CITATIONS)
    if len(citation_rows) != EXPECTED_CITATIONS:
        raise RuntimeError("citation audit row count changed")
    citation_keys = {r["citation_key"] for r in citation_rows}
    if len(citation_keys) != EXPECTED_CITATIONS:
        raise RuntimeError("duplicate citation keys in audit")
    tex_cites = set()
    for content in re.findall(r"\\cite\w*\{([^}]*)\}", tex):
        tex_cites.update(x.strip() for x in content.split(",") if x.strip())
    bib_keys = set(re.findall(r"@\w+\{([^,]+),", BIB.read_text(encoding="utf-8")))
    if tex_cites != citation_keys or bib_keys != citation_keys:
        raise RuntimeError(
            f"citation-key universe mismatch tex={sorted(tex_cites)} audit={sorted(citation_keys)} bib={sorted(bib_keys)}"
        )
    seed_rows = {
        r["source_id"]: r
        for r in rows(ROOT / "docs/literature/bibliographic_audit_ii/SEED_SOURCES.csv")
    }
    work_rows = {
        r["work_id"]: r
        for r in rows(ROOT / "docs/literature/bibliographic_audit_ii/screening/work_registry.csv")
    }
    for r in citation_rows:
        if r["status"] != "FROZEN_METADATA_VERIFIED":
            raise RuntimeError(f"citation metadata not frozen-verified: {r['citation_key']}")
        if r["bibliographic_source_id"] not in seed_rows:
            raise RuntimeError(f"citation seed ID missing: {r['citation_key']}")
        wid = r["BAII_work_id_if_applicable"]
        if wid and wid not in work_rows:
            raise RuntimeError(f"citation BAII work ID missing: {r['citation_key']}")
        for rel in split_ids(r["frozen_metadata_source"]):
            if not (ROOT / rel).is_file() or not rel.startswith("docs/literature/bibliographic_audit_ii/"):
                raise RuntimeError(f"citation metadata source outside frozen BAII: {r['citation_key']} {rel}")

    ft_rows = rows(FIGTAB_USAGE)
    if len(ft_rows) != 9 or {r["artifact_id"] for r in ft_rows} != expected_visual_ids:
        raise RuntimeError("figure/table usage registry must contain M1F01-M1F05 and M1T01-M1T04 exactly once")
    for r in ft_rows:
        if r["status"] != "FROZEN_M1_2_ARTIFACT":
            raise RuntimeError(f"non-frozen visual usage: {r['artifact_id']}")
        if r["artifact_id"].startswith("M1F") and r["integration_mode"] != "DIRECT_FROZEN_PDF":
            raise RuntimeError(f"figure was not integrated as frozen PDF: {r['artifact_id']}")
        if r["artifact_id"].startswith("M1T") and r["integration_mode"] != "DIRECT_FROZEN_TEX":
            raise RuntimeError(f"table was not integrated as frozen TeX: {r['artifact_id']}")
    for i in range(1, 6):
        aid = f"M1F0{i}"
        if f"../visuals/figures/{aid}_" not in tex:
            raise RuntimeError(f"frozen figure not directly included: {aid}")
    for i in range(1, 5):
        aid = f"M1T0{i}"
        if f"../visuals/tables/{aid}_" not in tex:
            raise RuntimeError(f"frozen table not directly included: {aid}")

    section_rows = rows(SECTION_COUNTS)
    if sum(int(r["paragraph_count"]) for r in section_rows) != EXPECTED_PARAGRAPHS:
        raise RuntimeError("section paragraph counts do not sum to scientific paragraph count")
    main_words = sum(int(r["word_count"]) for r in section_rows if r["section_id"] != "ABSTRACT")
    abstract_words = next(int(r["word_count"]) for r in section_rows if r["section_id"] == "ABSTRACT")
    if main_words != EXPECTED_MAIN_WORDS or abstract_words != EXPECTED_ABSTRACT_WORDS:
        raise RuntimeError(f"word-count freeze changed: main={main_words} abstract={abstract_words}")
    if not (5500 <= main_words <= 7500) or not (200 <= abstract_words <= 250):
        raise RuntimeError("draft word count outside mentor guidance")

    audit = json.loads(DRAFT_AUDIT.read_text(encoding="utf-8"))
    required_audit = {
        "main_text_word_count": EXPECTED_MAIN_WORDS,
        "abstract_word_count": EXPECTED_ABSTRACT_WORDS,
        "sections_complete": True,
        "scientific_paragraph_count": EXPECTED_PARAGRAPHS,
        "traceable_paragraph_count": EXPECTED_PARAGRAPHS,
        "figure_caption_count": EXPECTED_FIGURE_CAPTIONS,
        "figure_caption_traceable_count": EXPECTED_FIGURE_CAPTIONS,
        "claim_usage_records": EXPECTED_CLAIM_USAGE_ROWS,
        "prohibited_claims_used": 0,
        "numeric_items": EXPECTED_NUMERIC_ROWS,
        "numeric_items_traceable": EXPECTED_NUMERIC_ROWS,
        "citations": EXPECTED_CITATIONS,
        "citations_frozen_source_verified": EXPECTED_CITATIONS,
        "figures_used": EXPECTED_FIGURES,
        "tables_used": EXPECTED_TABLES,
        "new_scientific_computation": False,
        "new_statistical_inference": False,
        "new_bibliographic_search": False,
        "new_afino_execution": False,
        "new_synthetic_generation": False,
        "visual_regeneration": False,
        "correction_claim_established": False,
        "observational_validation_claimed": False,
    }
    for k, v in required_audit.items():
        if audit.get(k) != v:
            raise RuntimeError(f"draft audit mismatch: {k}={audit.get(k)!r} expected={v!r}")
    if audit.get("pre_freeze_review_incidents") != EXPECTED_REVIEW_INCIDENTS:
        raise RuntimeError(
            f"pre-freeze review incident ledger mismatch: {audit.get('pre_freeze_review_incidents')!r}"
        )
    if audit.get("pre_freeze_review_status") != "SCOPING_QUALIFIER_REPAIRED_BEFORE_GIT_FREEZE":
        raise RuntimeError("pre-freeze review status mismatch")
    if set(audit["claim_ids_used"]) != expected_nonprohibited:
        raise RuntimeError("draft audit claim_ids_used is not the complete non-prohibited claim universe")
    if audit["unused_supported_claim_ids"] != []:
        raise RuntimeError("draft audit reports unused supported claims")
    if audit["m1_1_commit"] != EXPECTED_M11_COMMIT or audit["m1_2_commit"] != EXPECTED_M12_COMMIT:
        raise RuntimeError("draft audit upstream freeze identity mismatch")

    # PDF is the compiled neutral preprint; compilation toolchain is not required on the user's machine.
    data = PDF.read_bytes()
    if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-4096:]:
        raise RuntimeError("manuscript_v1.pdf does not have valid PDF envelope")
    # pdfTeX may compress page-tree objects. Recover Flate streams with stdlib only
    # and require the frozen 22-page /Count marker without adding a PDF dependency.
    pdf_search = bytearray(data)
    for sm in re.finditer(rb"stream\r?\n", data):
        start = sm.end()
        end = data.find(b"endstream", start)
        if end < 0:
            continue
        header = data[max(0, sm.start()-600):sm.start()]
        if b"/FlateDecode" not in header:
            continue
        blob = data[start:end].rstrip(b"\r\n")
        try:
            pdf_search.extend(zlib.decompress(blob))
        except zlib.error:
            pass
    if re.search(rb"/Count\s+22\b", bytes(pdf_search)) is None:
        raise RuntimeError("compiled manuscript does not expose the frozen 22-page page-tree count")
    if b"/Font" not in pdf_search:
        raise RuntimeError("compiled manuscript lacks PDF font resources")
    page_count = 22

    readme = README.read_text(encoding="utf-8")
    required_status = (
        "STATUS:\nFIRST COMPLETE SCIENTIFIC DRAFT FROZEN —\n"
        "SCIENTIFIC / EDITORIAL REVIEW NOT YET COMPLETE"
    )
    if required_status not in readme:
        raise RuntimeError("draft README status block missing")

    dr = DR011.read_text(encoding="utf-8")
    for phrase in [
        "The study characterizes the reproducibility, methodological robustness, numerical behavior, and synthetic-ground-truth selection properties",
        "No internet or new bibliographic lookup is used.",
        "No visual artifact is regenerated.",
        "NOT_ESTABLISHED",
        "manuscript1-first-draft-v1",
        "manuscript1_first_complete_draft_v1.zip",
        "M1D-REV-001",
        "synthetic-ground-truth held-out validation",
    ]:
        if phrase not in dr:
            raise RuntimeError(f"DR-011 required content missing: {phrase}")

    # Validation terminology must remain explicitly scoped to synthetic ground truth.
    required_validation_heading = (
        r"\subsection{Synthetic injection--recovery and synthetic-ground-truth held-out validation}"
    )
    if required_validation_heading not in tex:
        raise RuntimeError("synthetic-ground-truth held-out validation heading missing")
    if r"\subsection{Synthetic injection--recovery and held-out validation}" in tex:
        raise RuntimeError("unqualified held-out validation heading is prohibited")

    # Semantic/prohibited-claim firewalls. Quoted/negated examples remain allowed; these match positive assertions only.
    prose_lower = tex.lower()
    forbidden_patterns = {
        "positive_observational_validation": r"\bafino\s+(?:is|was|has been)\s+observationally validated\b",
        "population_fpr_zero": r"\bpopulation\s+(?:false[- ]positive rate|fpr)\s+(?:is|=|equals)\s+(?:exactly\s+)?zero\b",
        "observational_metric_positive": r"\bobservational\s+(?:sensitivity|specificity|fpr|false[- ]positive rate)\s+(?:is|=|equals)\b",
        "validated_tess_correction": r"\b(?:validated\s+)?tess\s+(?:population\s+)?correction\b",
        "selection_is_population_correction": r"\bselection (?:surface|function)\s+is\s+(?:a\s+)?(?:validated\s+)?(?:tess\s+)?population correction\b",
        "period_proves_completeness": r"\bperiod (?:accuracy|recovery)\s+(?:proves|means|establishes)\s+(?:high\s+)?(?:detection\s+)?completeness\b",
        "candidate_validated_correction": r"\bcandidate (?:rule|threshold)\s+(?:is|was|becomes|constitutes)\s+(?:a\s+)?validated correction\b",
        "positive_priority_claim": r"\b(?:we|this study|this work)\s+(?:present|report|provide|is)\s+(?:the\s+)?first\b",
    }
    for name, pat in forbidden_patterns.items():
        if re.search(pat, prose_lower, flags=re.S):
            raise RuntimeError(f"prohibited semantic firewall triggered: {name}")

    required_boundaries = [
        "51/61 mismatch result is a reproduction limitation, not a physical falsification result",
        "zero gains therefore do not define an observational fpr",
        "does not establish a population fpr of exactly zero",
        "not end-to-end detection completeness",
        "population correction is not claimed",
        "not observationally validate afino",
        "not_established",
        "independent synthetic-ground-truth validation",
    ]
    normalized = prose_lower.replace("\\texttt{", "").replace("\\_", "_").replace("}", "")
    for phrase in required_boundaries:
        if phrase not in normalized:
            raise RuntimeError(f"mandatory qualification/boundary missing: {phrase}")

    # Core result anchors required by mentor must be present in Results prose and traceability.
    anchor_tokens = [
        "122 observational references",
        "9516 planned variants",
        "6422 were eligible",
        "3094 were inadmissible",
        "only 65 references were concordant",
        "51 were baseline mismatches",
        "six were baseline-inadmissible",
        "eight were concordant, 51 mismatched, and two were inadmissible",
        "295 selected-retained transitions",
        "171 selection losses",
        "3178 not-selected-retained transitions",
        "zero selection gains",
        "all 116 input-eligible",
        "1160 seed decisions",
        "143 true positives",
        "1657 false negatives",
        "1799 true negatives",
        "0.07944",
        "0.99944",
        "0.000556",
        "152 true positives",
        "1648 false negatives",
        "1800 true negatives",
        "0.08444",
        "0.00213",
        "156 strata",
        "structural\\_no\\_exposure",
        "152 selected true positives",
    ]
    for token in anchor_tokens:
        if token not in prose_lower:
            raise RuntimeError(f"required frozen Results anchor missing: {token}")

    # M1.3 checksum registry covers all M1.3 files except itself.
    sum_lines = [x for x in SUMS.read_text(encoding="utf-8").splitlines() if x.strip()]
    if len(sum_lines) != EXPECTED_SHA_TARGETS:
        raise RuntimeError(f"M1.3 checksum target count != {EXPECTED_SHA_TARGETS}: {len(sum_lines)}")
    registered = set()
    for line in sum_lines:
        expected, rel = line.split("  ", 1)
        if rel == "manuscripts/manuscript_01/draft/evidence/SHA256SUMS.txt":
            raise RuntimeError("M1.3 checksum registry must exclude itself")
        p = ROOT / rel
        if not p.is_file() or sha(p) != expected:
            raise RuntimeError(f"M1.3 checksum mismatch: {rel}")
        registered.add(rel)
    expected_registered = REQUIRED_M13_PATHS - {"manuscripts/manuscript_01/draft/evidence/SHA256SUMS.txt"}
    if registered != expected_registered:
        raise RuntimeError(
            f"M1.3 checksum registry path universe mismatch: "
            f"missing={sorted(expected_registered-registered)} extra={sorted(registered-expected_registered)}"
        )

    return {
        "main_text_word_count": main_words,
        "abstract_word_count": abstract_words,
        "scientific_paragraphs": EXPECTED_PARAGRAPHS,
        "figure_captions": EXPECTED_FIGURE_CAPTIONS,
        "claim_usage_rows": len(usage),
        "numeric_items": len(numeric_rows),
        "citations": len(citation_rows),
        "figures": EXPECTED_FIGURES,
        "tables": EXPECTED_TABLES,
        "pdf_pages": page_count,
        "claims_used": len(used_claims),
        "pre_freeze_review_incidents": len(EXPECTED_REVIEW_INCIDENTS),
    }


def main():
    static_only = os.environ.get("M1_3_STATIC_ONLY") == "1"
    if not static_only:
        assert_upstream_validators()
        assert_git_boundary()
    result = validate_static()
    print("MANUSCRIPT1_FIRST_COMPLETE_DRAFT_VALIDATION_PASS")
    print("main_text_word_count =", result["main_text_word_count"])
    print("abstract_word_count =", result["abstract_word_count"])
    print("scientific_paragraphs =", result["scientific_paragraphs"])
    print("figure_caption_traces =", result["figure_captions"])
    print("claim_usage_rows =", result["claim_usage_rows"])
    print("claims_used =", result["claims_used"])
    print("numeric_items_traceable =", result["numeric_items"])
    print("citations_frozen_source_verified =", result["citations"])
    print("figures_used =", result["figures"])
    print("tables_used =", result["tables"])
    print("pdf_pages =", result["pdf_pages"])
    print("pre_freeze_review_incidents = M1D-REV-001")
    print("validation_scope_heading = synthetic-ground-truth")
    print("prohibited_claims_used = 0")
    print("correction_claim_established = false")
    print("observational_validation_claimed = false")
    print("new_scientific_computation = false")
    print("new_statistical_inference = false")
    print("new_bibliographic_search = false")
    print("new_afino_execution = false")
    print("new_synthetic_generation = false")
    print("visual_regeneration = false")


if __name__ == "__main__":
    main()
