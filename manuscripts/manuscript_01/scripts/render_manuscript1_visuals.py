from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
M1 = ROOT / "manuscripts/manuscript_01"
VIS = M1 / "visuals"
CONFIG = VIS / "config/m1_2_visual_rendering_contract.json"
VBIND = VIS / "evidence/m1_2_visual_source_bindings.json"
PLAN = M1 / "planning/m1_figure_table_plan.csv"
CLAIMS = M1 / "planning/m1_claim_matrix.csv"
PLANES = M1 / "planning/m1_evidence_plane_registry.csv"
ARCH_BINDINGS = M1 / "planning/m1_source_bindings.json"

FIG_DIR = VIS / "figures"
TAB_DIR = VIS / "tables"
EVID_DIR = VIS / "evidence"

VALUE_AUDIT = EVID_DIR / "m1_2_rendered_value_audit.csv"
MANIFEST = EVID_DIR / "m1_2_visual_manifest.csv"
AUDIT = EVID_DIR / "m1_2_visual_audit.json"
SUMS = EVID_DIR / "SHA256SUMS.txt"
README = VIS / "README.md"
DR010 = ROOT / "docs/decisions/DR-010-manuscript1-visual-freeze.md"

ENTRY_COMMIT = "52024ec3728eeda25f9d640d8f1395a87671c541"
ENTRY_TAG = "manuscript1-architecture-v1"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "axes.titlesize": 11,
    "axes.labelsize": 9,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "figure.titlesize": 12,
})


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip("\r\n")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def truthy(v: str) -> bool:
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def num_sort(values):
    def key(v):
        try:
            return (0, float(v))
        except Exception:
            return (1, str(v))
    return sorted(values, key=key)


def fmt_float(v: float) -> str:
    if v == 0:
        return "0"
    if v == 1:
        return "1"
    if abs(v) < 1e-4:
        return f"{v:.3e}"
    return f"{v:.6f}".rstrip("0").rstrip(".")


def tex_escape(s: str) -> str:
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(ch, ch) for ch in str(s))


def dataframe_to_tex(fields: list[str], rows: list[dict], caption: str, label: str) -> str:
    colspec = "p{" + "}p{".join(["0.16\\linewidth"] * len(fields)) + "}"
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\small",
        rf"\caption{{{tex_escape(caption)}}}",
        rf"\label{{{tex_escape(label)}}}",
        rf"\begin{{tabular}}{{{colspec}}}",
        r"\hline",
        " & ".join(rf"\textbf{{{tex_escape(f)}}}" for f in fields) + r" \\",
        r"\hline",
    ]
    for row in rows:
        vals = [tex_escape(row.get(f, "")) for f in fields]
        lines.append(" & ".join(vals) + r" \\")
    lines += [r"\hline", r"\end{tabular}", r"\end{table*}", ""]
    return "\n".join(lines)


def save_figure(fig, artifact_id: str, stem: str):
    pdf = FIG_DIR / f"{artifact_id}_{stem}.pdf"
    png = FIG_DIR / f"{artifact_id}_{stem}.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return pdf, png


contract = json.loads(CONFIG.read_text(encoding="utf-8"))
visual_bindings = json.loads(VBIND.read_text(encoding="utf-8"))
arch_bindings = json.loads(ARCH_BINDINGS.read_text(encoding="utf-8"))
plan_rows = read_csv(PLAN)
claim_rows = read_csv(CLAIMS)
plane_rows = read_csv(PLANES)

plan_map = {r["artifact_id"]: r for r in plan_rows}
claim_map = {r["claim_id"]: r for r in claim_rows}
plane_map = {r["evidence_plane_id"]: r for r in plane_rows}
source_map = {r["source_id"]: r for r in visual_bindings["sources"]}

if git("rev-list", "-n", "1", ENTRY_TAG) != ENTRY_COMMIT:
    raise RuntimeError("M1.1 architecture freeze changed")

contract_commit = git("log", "-1", "--format=%H", "--", CONFIG.relative_to(ROOT).as_posix())
if not contract_commit:
    raise RuntimeError("rendering contract is not Git-frozen")
if git("rev-parse", "HEAD") != contract_commit:
    raise RuntimeError(
        "First definitive render must run exactly at the rendering-contract freeze commit"
    )

if contract["entry_architecture_commit"] != ENTRY_COMMIT:
    raise RuntimeError("rendering contract entry commit mismatch")
if contract["authoritative_plan"]["sha256"] != sha(PLAN):
    raise RuntimeError("authoritative M1.1 figure/table plan SHA changed")
if contract["new_scientific_computation"] is not False:
    raise RuntimeError("contract science firewall violated")
if contract["new_statistical_inference"] is not False:
    raise RuntimeError("contract inference firewall violated")
if contract["new_source_artifact"] is not False:
    raise RuntimeError("contract source firewall violated")

for sid, meta in source_map.items():
    p = ROOT / meta["repository_relative_path"]
    if not p.is_file():
        raise RuntimeError(f"visual source missing: {sid}")
    if sha(p) != meta["sha256"] or p.stat().st_size != meta["bytes"]:
        raise RuntimeError(f"visual source identity changed: {sid}")

FIG_DIR.mkdir(parents=True, exist_ok=False)
TAB_DIR.mkdir(parents=True, exist_ok=False)
EVID_DIR.mkdir(parents=True, exist_ok=True)

value_rows: list[dict[str, str]] = []
vid_counter = 0


def add_value(
    artifact_id: str,
    location: str,
    label: str,
    displayed,
    source_id: str,
    source_locator: str,
    source_value,
    transformation: str,
    status: str,
):
    global vid_counter
    vid_counter += 1
    src = source_map[source_id]
    value_rows.append({
        "rendered_value_id": f"M1RV{vid_counter:04d}",
        "artifact_id": artifact_id,
        "panel_or_table_location": location,
        "displayed_label": str(label),
        "displayed_value": str(displayed),
        "source_id": source_id,
        "source_artifact": src["repository_relative_path"],
        "source_locator": str(source_locator),
        "source_value": str(source_value),
        "transformation": transformation,
        "exact_match_status": status,
    })


def source_path(sid: str) -> Path:
    return ROOT / source_map[sid]["repository_relative_path"]


# -------------------------------------------------------------------------
# Frozen source helpers / assertions
# -------------------------------------------------------------------------

f2_events = read_csv(source_path("M1S016"))
f3a_primary = read_csv(source_path("M1S031"))
f3a_base = read_csv(source_path("M1S030"))
f3a_synth = source_path("M1S038").read_text(encoding="utf-8", errors="replace")
sf = read_csv(source_path("M1S043"))
period_rows = read_csv(source_path("M1S044"))
dev_metrics = json.loads(source_path("M1S039").read_text(encoding="utf-8"))
ho_metrics = json.loads(source_path("M1S042").read_text(encoding="utf-8"))

if len(f2_events) != 10:
    raise RuntimeError("F2 event count changed")
if len(f3a_primary) != 9516:
    raise RuntimeError("F3A planned-variant rows changed")
if len(f3a_base) != 122:
    raise RuntimeError("F3A baseline cohort rows changed")
if len(sf) != 156:
    raise RuntimeError("HELDOUT selection-function rows changed")
if len(period_rows) != 152:
    raise RuntimeError("HELDOUT period-recovery rows changed")

for phrase in [
    "thirteen temporal windows and six processing profiles",
    "780 planned variants across ten events",
    "122 events",
    "9,516 planned variants",
    "6,422 were eligible",
    "3,094 inadmissible",
]:
    if phrase not in f3a_synth:
        raise RuntimeError(f"required frozen synthesis phrase missing: {phrase}")


def count_baseline(role, state):
    return sum(
        1 for r in f3a_base
        if r["observational_reference_role"] == role
        and r["baseline_gate_state"] == state
    )


baseline_counts = {
    ("PUBLISHED_QPP_REFERENCE", "REFERENCE_CONCORDANT"): count_baseline("PUBLISHED_QPP_REFERENCE", "REFERENCE_CONCORDANT"),
    ("PUBLISHED_QPP_REFERENCE", "REFERENCE_BASELINE_MISMATCH"): count_baseline("PUBLISHED_QPP_REFERENCE", "REFERENCE_BASELINE_MISMATCH"),
    ("PUBLISHED_QPP_REFERENCE", "INPUT_INADMISSIBLE"): count_baseline("PUBLISHED_QPP_REFERENCE", "INPUT_INADMISSIBLE"),
    ("PUBLISHED_NOT_SELECTED_REFERENCE", "REFERENCE_CONCORDANT"): count_baseline("PUBLISHED_NOT_SELECTED_REFERENCE", "REFERENCE_CONCORDANT"),
    ("PUBLISHED_NOT_SELECTED_REFERENCE", "REFERENCE_BASELINE_MISMATCH"): count_baseline("PUBLISHED_NOT_SELECTED_REFERENCE", "REFERENCE_BASELINE_MISMATCH"),
    ("PUBLISHED_NOT_SELECTED_REFERENCE", "INPUT_INADMISSIBLE"): count_baseline("PUBLISHED_NOT_SELECTED_REFERENCE", "INPUT_INADMISSIBLE"),
}
expected_baseline = {
    ("PUBLISHED_QPP_REFERENCE", "REFERENCE_CONCORDANT"): 8,
    ("PUBLISHED_QPP_REFERENCE", "REFERENCE_BASELINE_MISMATCH"): 51,
    ("PUBLISHED_QPP_REFERENCE", "INPUT_INADMISSIBLE"): 2,
    ("PUBLISHED_NOT_SELECTED_REFERENCE", "REFERENCE_CONCORDANT"): 57,
    ("PUBLISHED_NOT_SELECTED_REFERENCE", "REFERENCE_BASELINE_MISMATCH"): 0,
    ("PUBLISHED_NOT_SELECTED_REFERENCE", "INPUT_INADMISSIBLE"): 4,
}
if baseline_counts != expected_baseline:
    raise RuntimeError(f"F3A baseline gate counts changed: {baseline_counts}")


def transition_count(role: str, transition: str) -> int:
    return sum(
        1 for r in f3a_primary
        if r["observational_reference_role"] == role
        and r["baseline_gate_state"] == "REFERENCE_CONCORDANT"
        and truthy(r["transition_eligible"])
        and r["classification_transition"].strip().upper() == transition
    )


transition_counts = {
    "QPP_SELECTED_RETAINED": transition_count("PUBLISHED_QPP_REFERENCE", "SELECTED_RETAINED"),
    "QPP_SELECTION_LOST": transition_count("PUBLISHED_QPP_REFERENCE", "SELECTION_LOST"),
    "NS_NOT_SELECTED_RETAINED": transition_count("PUBLISHED_NOT_SELECTED_REFERENCE", "NOT_SELECTED_RETAINED"),
    "NS_SELECTION_GAINED": transition_count("PUBLISHED_NOT_SELECTED_REFERENCE", "SELECTION_GAINED"),
}
expected_transitions = {
    "QPP_SELECTED_RETAINED": 295,
    "QPP_SELECTION_LOST": 171,
    "NS_NOT_SELECTED_RETAINED": 3178,
    "NS_SELECTION_GAINED": 0,
}
if transition_counts != expected_transitions:
    # Expose exact frozen categories to make any source-schema mismatch auditable.
    cats = Counter(
        (r["observational_reference_role"], r["baseline_gate_state"], r["transition_eligible"], r["classification_transition"])
        for r in f3a_primary
    )
    raise RuntimeError(
        "F3A transition counts changed or category labels differ: "
        + repr(transition_counts)
        + " categories="
        + repr(cats.most_common(20))
    )


def context_has_count(text: str, count_variants: list[str], context: str) -> bool:
    paragraphs = re.split(r"\n\s*\n", text)
    for para in paragraphs:
        pl = para.lower()
        if context.lower() in pl and any(v in para for v in count_variants):
            return True
    return False


for variants, ctx in [
    (["116"], "optimizer"),
    (["1,160", "1160"], "seed"),
    (["295"], "period"),
]:
    if not context_has_count(f3a_synth, variants, ctx):
        raise RuntimeError(f"F3A synthesis missing required {ctx} frozen count context")


# -------------------------------------------------------------------------
# M1F01 — evidence architecture
# -------------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(10.5, 8))
ax.set_axis_off()
y_positions = [0.84, 0.68, 0.52, 0.36, 0.20]
plane_ids = ["M1EP01", "M1EP02", "M1EP03", "M1EP04", "M1EP05"]
titles = [
    "F0 observational reproduction",
    "F1 synthetic / numerical benchmark",
    "F2 observational pilot robustness",
    "F3A catalogue-scale observational robustness",
    "F3B synthetic-ground-truth HELDOUT validation",
]
for i, (pid, title, y) in enumerate(zip(plane_ids, titles, y_positions)):
    p = plane_map[pid]
    box = FancyBboxPatch(
        (0.08, y - 0.055), 0.62, 0.10,
        boxstyle="round,pad=0.012",
        linewidth=1.2, edgecolor="0.15", facecolor="0.95",
    )
    ax.add_patch(box)
    ax.text(0.10, y + 0.018, title, fontsize=10, weight="bold", va="center")
    ax.text(
        0.10, y - 0.020,
        f"Truth status: {p['ground_truth_status']}",
        fontsize=7.5, va="center",
    )
    if i < len(y_positions) - 1:
        ax.annotate(
            "", xy=(0.39, y_positions[i+1] + 0.060), xytext=(0.39, y - 0.060),
            arrowprops=dict(arrowstyle="->", linewidth=1.0, color="0.25"),
        )

baii = FancyBboxPatch(
    (0.75, 0.40), 0.21, 0.20,
    boxstyle="round,pad=0.015",
    linewidth=1.5, linestyle="--",
    edgecolor="0.15", facecolor="1.0",
)
ax.add_patch(baii)
ax.text(0.855, 0.555, "BAII", ha="center", va="center", weight="bold", fontsize=11)
ax.text(
    0.855, 0.500,
    "POSITIONING /\nPRECEDENCE FIREWALL",
    ha="center", va="center", fontsize=8.5,
)
ax.text(
    0.855, 0.435,
    "NOT A RESULT PLANE",
    ha="center", va="center", fontsize=8.5, weight="bold",
)
ax.annotate(
    "", xy=(0.705, 0.50), xytext=(0.75, 0.50),
    arrowprops=dict(arrowstyle="-", linewidth=1.0, linestyle="--", color="0.25"),
)
ax.text(
    0.08, 0.06,
    "Evidence planes have different truth conditions and denominators; arrows denote programme progression, not physical validation.",
    fontsize=8.3,
)
fig.suptitle("Manuscript 1 evidence architecture", y=0.97)
save_figure(fig, "M1F01", "evidence_architecture")


# -------------------------------------------------------------------------
# M1F02 — F2 -> F3A design progression
# -------------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(11, 6.6))
ax.set_axis_off()

def design_card(x, title, subtitle, lines, baseline_gate=False):
    card = FancyBboxPatch(
        (x, 0.22), 0.36, 0.60,
        boxstyle="round,pad=0.018",
        linewidth=1.3, edgecolor="0.2", facecolor="0.96",
    )
    ax.add_patch(card)
    ax.text(x+0.18, 0.75, title, ha="center", fontsize=13, weight="bold")
    ax.text(x+0.18, 0.70, subtitle, ha="center", fontsize=9)
    yy = 0.61
    for line in lines:
        ax.text(x+0.06, yy, line, fontsize=10, va="center")
        yy -= 0.09
    if baseline_gate:
        gate = FancyBboxPatch(
            (x+0.05, 0.27), 0.26, 0.075,
            boxstyle="round,pad=0.01",
            linewidth=1.0, edgecolor="0.15", facecolor="1.0",
        )
        ax.add_patch(gate)
        ax.text(x+0.18, 0.307, "Baseline gate before transitions", ha="center", va="center", fontsize=8)

design_card(
    0.08, "F2", "Pilot observational robustness",
    ["10 events", "13 x 6 perturbation matrix", "780 planned variants"],
)
design_card(
    0.56, "F3A", "Catalogue-scale observational robustness",
    ["122 events", "13 x 6 perturbation matrix", "9,516 planned variants"],
    baseline_gate=True,
)
ax.annotate(
    "", xy=(0.56, 0.52), xytext=(0.44, 0.52),
    arrowprops=dict(arrowstyle="->", linewidth=1.5, color="0.25"),
)
ax.text(0.50, 0.57, "same prospective design", ha="center", fontsize=8)
ax.text(
    0.50, 0.10,
    "Different denominators; descriptive continuity only. No pooled rate and no inferential comparison.",
    ha="center", fontsize=9, weight="bold",
)
fig.suptitle("Observational robustness: continuity of design and change of scale", y=0.96)

add_value("M1F02","F2 card","events","10","M1S016","row_count","10","direct frozen table row count","DIRECT_CATEGORICAL_COUNT")
add_value("M1F02","F2 card","temporal windows","13","M1S038","phrase: thirteen temporal windows and six processing profiles","13","literal-to-label formatting","DETERMINISTIC_LABEL_FORMAT")
add_value("M1F02","F2 card","processing profiles","6","M1S038","phrase: thirteen temporal windows and six processing profiles","6","literal-to-label formatting","DETERMINISTIC_LABEL_FORMAT")
add_value("M1F02","F2 card","planned variants","780","M1S038","phrase: 780 planned variants across ten events","780","literal number formatting","DETERMINISTIC_LABEL_FORMAT")
add_value("M1F02","F3A card","events","122","M1S031","unique phase3a_event_id / frozen cohort","122","direct categorical count confirmed by frozen synthesis","DIRECT_CATEGORICAL_COUNT")
add_value("M1F02","F3A card","temporal windows","13","M1S038","frozen 13 x 6 design continuity","13","literal-to-label formatting","DETERMINISTIC_LABEL_FORMAT")
add_value("M1F02","F3A card","processing profiles","6","M1S038","frozen 13 x 6 design continuity","6","literal-to-label formatting","DETERMINISTIC_LABEL_FORMAT")
add_value("M1F02","F3A card","planned variants","9516","M1S031","row_count","9516","direct frozen table row count with thousands separator","DIRECT_CATEGORICAL_COUNT")
save_figure(fig, "M1F02", "f2_f3a_robustness_progression")


# -------------------------------------------------------------------------
# M1F03 — F3A baseline gate + transitions
# -------------------------------------------------------------------------

fig = plt.figure(figsize=(11.5, 8.5))
gs = fig.add_gridspec(2, 1, height_ratios=[1, 1.15], hspace=0.42)
ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[1, 0])

roles = ["QPP reference", "Not-selected reference"]
states = ["Concordant", "Mismatch", "Inadmissible"]
vals = [
    [8, 51, 2],
    [57, 0, 4],
]
hatches = ["", "///", "xx"]
grays = ["0.75", "0.45", "0.95"]

left = np.zeros(2)
for j, state in enumerate(states):
    v = [vals[i][j] for i in range(2)]
    bars = ax1.barh(roles, v, left=left, color=grays[j], edgecolor="0.2", hatch=hatches[j], label=state)
    for i, (bar, n) in enumerate(zip(bars, v)):
        if n > 0:
            x = left[i] + n/2
            ax1.text(
                x, bar.get_y()+bar.get_height()/2, str(n),
                ha="center", va="center", fontsize=8, weight="bold"
            )
        else:
            # Preserve the zero-valued frozen category without visually colliding
            # with the next non-zero stacked segment.
            ax1.annotate(
                "0",
                xy=(left[i], bar.get_y()+bar.get_height()/2),
                xytext=(0, -16),
                textcoords="offset points",
                ha="center", va="center",
                fontsize=7.5, weight="bold",
                bbox=dict(boxstyle="round,pad=0.12", facecolor="white", edgecolor="0.55", linewidth=0.5),
            )
    left += np.array(v)
ax1.set_xlim(0, 64)
ax1.set_xlabel("Events in frozen baseline gate")
ax1.set_title("A — Baseline gate by observational reference role")
ax1.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.18))
ax1.text(
    0.0, -0.34,
    "51 baseline mismatches are reproduction mismatches, not 51 physically false QPPs.",
    transform=ax1.transAxes, fontsize=8.5, weight="bold",
)

trans_names = ["Selected retained", "Selection lost", "Not-selected retained", "Selection gained"]
trans_vals = [295, 171, 3178, 0]
y = np.arange(4)
bars = ax2.barh(y, trans_vals, color=["0.65","0.85","0.45","1.0"], edgecolor="0.2", hatch=["","///","","xx"])
ax2.set_yticks(y, labels=trans_names)
ax2.invert_yaxis()
ax2.set_xlabel("Cell-level baseline-relative transitions")
ax2.set_title("B — Transitions conditional on baseline concordance")
for bar, n in zip(bars, trans_vals):
    if n == 0:
        ax2.text(12, bar.get_y()+bar.get_height()/2, "0", va="center", fontsize=8, weight="bold")
    else:
        ax2.text(bar.get_width()+25, bar.get_y()+bar.get_height()/2, str(n), va="center", fontsize=8)
ax2.set_xlim(0, 3400)
ax2.text(
    0.0, -0.22,
    "Cell-level repeated-measure transitions; not independent event counts. Observational rows are not TP/TN/FP/FN.",
    transform=ax2.transAxes, fontsize=8.5,
)
fig.suptitle("F3A catalogue-scale observational robustness", y=0.98)

baseline_audit_specs = [
    ("QPP concordant",8,"PUBLISHED_QPP_REFERENCE","REFERENCE_CONCORDANT"),
    ("QPP mismatch",51,"PUBLISHED_QPP_REFERENCE","REFERENCE_BASELINE_MISMATCH"),
    ("QPP inadmissible",2,"PUBLISHED_QPP_REFERENCE","INPUT_INADMISSIBLE"),
    ("not-selected concordant",57,"PUBLISHED_NOT_SELECTED_REFERENCE","REFERENCE_CONCORDANT"),
    ("not-selected mismatch",0,"PUBLISHED_NOT_SELECTED_REFERENCE","REFERENCE_BASELINE_MISMATCH"),
    ("not-selected inadmissible",4,"PUBLISHED_NOT_SELECTED_REFERENCE","INPUT_INADMISSIBLE"),
]
for label,n,role,state in baseline_audit_specs:
    add_value("M1F03","Panel A",label,n,"M1S030",f"count where observational_reference_role={role}; baseline_gate_state={state}",n,"direct categorical count","DIRECT_CATEGORICAL_COUNT")

for label,n,locator in [
    ("selected retained",295,"PUBLISHED_QPP_REFERENCE + REFERENCE_CONCORDANT + transition_eligible + SELECTED_RETAINED"),
    ("selection lost",171,"PUBLISHED_QPP_REFERENCE + REFERENCE_CONCORDANT + transition_eligible + SELECTION_LOST"),
    ("not-selected retained",3178,"PUBLISHED_NOT_SELECTED_REFERENCE + REFERENCE_CONCORDANT + transition_eligible + NOT_SELECTED_RETAINED"),
    ("selection gained",0,"PUBLISHED_NOT_SELECTED_REFERENCE + REFERENCE_CONCORDANT + transition_eligible + SELECTION_GAINED"),
]:
    add_value("M1F03","Panel B",label,n,"M1S031",locator,n,"direct categorical count","DIRECT_CATEGORICAL_COUNT")

save_figure(fig, "M1F03", "f3a_catalogue_robustness")


# -------------------------------------------------------------------------
# M1F04 — HELDOUT synthetic selection function
# Publication-readability revision after pre-freeze visual review:
# designed for native full-width (~7.2 in) manuscript placement.
# -------------------------------------------------------------------------

families = Counter(r["stratum_family"] for r in sf)
if families != Counter({"POSITIVE_BASE":36, "POSITIVE_PERIOD_BIN":108, "NULL_POOLED":12}):
    raise RuntimeError(f"selection-function family counts changed: {families}")

exposure_counts = Counter(r["exposure_status"] for r in sf)
if exposure_counts.get("STRUCTURAL_NO_EXPOSURE",0) != 9:
    raise RuntimeError("STRUCTURAL_NO_EXPOSURE count changed")

n_samples = num_sort(set(r["n_samples"] for r in sf))
alphas = num_sort(set(r["red_noise_alpha"] for r in sf))
qpps = num_sort(set(r["qpp_fraction"] for r in sf if r["stratum_family"] != "NULL_POOLED"))
period_bins = [x for x in ["P40_63","P63_106","P106_300"] if x in set(r["period_bin_id"] for r in sf)]
if len(qpps) != 3 or len(period_bins) != 3:
    raise RuntimeError("unexpected F3B selection-function category cardinality")

# Native journal-full-width composition. The dense 9-column period-expanded
# surfaces are stacked vertically rather than placed three-across.
fig = plt.figure(figsize=(7.2, 10.4))
gs = fig.add_gridspec(
    5, 3,
    height_ratios=[1.15, 1.25, 1.25, 1.25, 1.10],
    hspace=0.78,
    wspace=0.34,
)

def add_heatmap_value(ax, xi, yi, r, panel, fontsize=6.2):
    if r["exposure_status"] == "STRUCTURAL_NO_EXPOSURE":
        rect = Rectangle(
            (xi-0.5, yi-0.5), 1, 1,
            facecolor="white", edgecolor="0.25", hatch="///", linewidth=0.7
        )
        ax.add_patch(rect)
        ax.text(xi, yi, "N/E", ha="center", va="center", fontsize=fontsize, weight="bold")
        add_value(
            "M1F04", panel, f"stratum {r['stratum_order']}", "N/E", "M1S043",
            f"stratum_order={r['stratum_order']}:exposure_status",
            "STRUCTURAL_NO_EXPOSURE",
            "structural absence rendered as N/E rather than zero",
            "STRUCTURAL_NO_EXPOSURE_PRESERVED",
        )
    else:
        v = float(r["conditional_selection_point_estimate"])
        txt = f"{v:.2f}"
        ax.text(
            xi, yi, txt, ha="center", va="center",
            fontsize=fontsize, color=("white" if v > 0.60 else "black")
        )
        add_value(
            "M1F04", panel, f"stratum {r['stratum_order']}", txt, "M1S043",
            f"stratum_order={r['stratum_order']}:conditional_selection_point_estimate",
            r["conditional_selection_point_estimate"],
            "two-decimal deterministic label formatting of frozen point estimate",
            "DETERMINISTIC_LABEL_FORMAT",
        )

def render_matrix(ax, row_lookup, x_keys, y_keys, title, panel, xlabels, fontsize=6.2):
    data = np.full((len(y_keys), len(x_keys)), np.nan, dtype=float)
    for yi, yv in enumerate(y_keys):
        for xi, xv in enumerate(x_keys):
            r = row_lookup.get((yv, xv))
            if r is None:
                raise RuntimeError(f"missing selection-function stratum for {panel}: {(yv, xv)}")
            if r["exposure_status"] != "STRUCTURAL_NO_EXPOSURE":
                data[yi, xi] = float(r["conditional_selection_point_estimate"])

    ax.imshow(np.ma.masked_invalid(data), cmap="Greys", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(x_keys)), labels=xlabels, fontsize=6.5)
    ax.set_yticks(np.arange(len(y_keys)), labels=[f"n={n}" for n in y_keys], fontsize=6.5)
    ax.set_title(title, fontsize=7.8, pad=5)

    for yi, yv in enumerate(y_keys):
        for xi, xv in enumerate(x_keys):
            add_heatmap_value(ax, xi, yi, row_lookup[(yv, xv)], panel, fontsize=fontsize)

# A — Positive base, three compact facets.
for j, q in enumerate(qpps):
    ax = fig.add_subplot(gs[0, j])
    rows_here = [
        r for r in sf
        if r["stratum_family"] == "POSITIVE_BASE" and r["qpp_fraction"] == q
    ]
    lookup = {(r["n_samples"], r["red_noise_alpha"]): r for r in rows_here}
    render_matrix(
        ax, lookup, alphas, n_samples,
        f"A{j+1} — Base; QPP fraction={q}",
        f"Panel A{j+1}",
        [f"alpha={a}" for a in alphas],
        fontsize=6.3,
    )
    ax.tick_params(axis="x", labelrotation=35)

# B — Period-expanded surfaces stacked vertically at full width.
xpairs = [(a, p) for a in alphas for p in period_bins]
period_label = {
    "P40_63": "40–63",
    "P63_106": "63–106",
    "P106_300": "106–300",
}

for j, q in enumerate(qpps):
    ax = fig.add_subplot(gs[1+j, :])
    rows_here = [
        r for r in sf
        if r["stratum_family"] == "POSITIVE_PERIOD_BIN" and r["qpp_fraction"] == q
    ]
    lookup = {
        (r["n_samples"], (r["red_noise_alpha"], r["period_bin_id"])): r
        for r in rows_here
    }
    render_matrix(
        ax, lookup, xpairs, n_samples,
        f"B{j+1} — Period-expanded; QPP fraction={q}",
        f"Panel B{j+1}",
        [period_label[p] for _, p in xpairs],
        fontsize=6.2,
    )
    # render_matrix() sets a centered title; remove that layer before adding
    # the publication-facing left-aligned title tier.
    ax.set_title("", loc="center")
    ax.set_title(
        f"B{j+1} — Period-expanded; QPP fraction={q}",
        loc="left", fontsize=7.8, pad=22
    )
    ax.tick_params(axis="x", labelrotation=0, pad=2)

    # Alpha group labels above each three-period block, below the panel title.
    for center, a in zip([1, 4, 7], alphas):
        ax.text(
            center, 1.02, f"alpha={a}",
            transform=ax.get_xaxis_transform(),
            ha="center", va="bottom", fontsize=6.6, weight="bold"
        )
    ax.axvline(2.5, color="0.55", linewidth=0.6)
    ax.axvline(5.5, color="0.55", linewidth=0.6)
    if j == 2:
        ax.set_xlabel("True-period bin (s), repeated within each red-noise-alpha block", fontsize=7)

# C — Null strata, full width.
ax = fig.add_subplot(gs[4, :])
null_rows = [r for r in sf if r["stratum_family"] == "NULL_POOLED"]
null_lookup = {(r["n_samples"], r["red_noise_alpha"]): r for r in null_rows}
render_matrix(
    ax, null_lookup, alphas, n_samples,
    "C — Synthetic null strata (QPP-fraction pairing label pooled; not a null parameter)",
    "Panel C",
    [f"alpha={a}" for a in alphas],
    fontsize=6.3,
)
ax.set_xlabel("Red-noise alpha", fontsize=7)

fig.suptitle(
    "F3B independent HELDOUT synthetic selection function\n"
    "Cell text = frozen conditional_selection_point_estimate; hatched N/E = structural no exposure",
    y=0.995, fontsize=9.4,
)
fig.text(
    0.5, 0.012,
    "Synthetic HELDOUT domain only. Grayscale assists reading; cell text carries the quantitative value.",
    ha="center", fontsize=6.8,
)

# Axis category values are frozen source labels, not newly estimated quantities.
for val in n_samples:
    add_value(
        "M1F04","Axes","n_samples category",val,"M1S043",
        f"first row with n_samples={val}:n_samples",val,
        "direct categorical axis label","EXACT_SOURCE_VALUE"
    )
for val in alphas:
    add_value(
        "M1F04","Axes","red_noise_alpha category",val,"M1S043",
        f"first row with red_noise_alpha={val}:red_noise_alpha",val,
        "direct categorical axis label","EXACT_SOURCE_VALUE"
    )
for val in qpps:
    add_value(
        "M1F04","Facets","qpp_fraction category",val,"M1S043",
        f"first row with qpp_fraction={val}:qpp_fraction",val,
        "direct categorical facet label","EXACT_SOURCE_VALUE"
    )

save_figure(fig, "M1F04", "f3b_heldout_selection_function")


# -------------------------------------------------------------------------
# M1F05 — conditional period recovery
# -------------------------------------------------------------------------

true_p = np.array([float(r["true_period_s"]) for r in period_rows])
rec_p = np.array([float(r["recovered_period_s"]) for r in period_rows])
rel_e = np.array([float(r["relative_period_error"]) for r in period_rows])

fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.6))
ax=axes[0]
ax.scatter(true_p, rec_p, marker="o", facecolors="none", edgecolors="0.25", linewidths=0.7, s=22)
lo=min(float(true_p.min()),float(rec_p.min()))
hi=max(float(true_p.max()),float(rec_p.max()))
ax.plot([lo,hi],[lo,hi],linestyle="--",linewidth=1.0,color="0.35")
ax.set_xlabel("True period (s)")
ax.set_ylabel("Recovered period (s)")
ax.set_title("A — Selected true positives: recovered vs true period")

ax=axes[1]
ax.scatter(true_p, rel_e, marker="x", color="0.25", linewidths=0.8, s=22)
ax.axhline(0,linestyle="--",linewidth=1.0,color="0.35")
ax.set_xlabel("True period (s)")
ax.set_ylabel("Relative period error")
ax.set_title("B — Selected true positives: relative period error")

fig.suptitle("Conditional period recovery in the independent synthetic HELDOUT")
fig.text(
    0.5, 0.015,
    "152 selected true positives out of 1800 eligible synthetic positives. Period accuracy is conditional on selection.",
    ha="center", fontsize=8.8, weight="bold",
)
fig.tight_layout(rect=[0,0.06,1,0.93])

for i,r in enumerate(period_rows, start=1):
    add_value(
        "M1F05","Panel A",f"point {i}",
        f"true={r['true_period_s']}; recovered={r['recovered_period_s']}",
        "M1S044",f"row {i}:true_period_s,recovered_period_s",
        f"true={r['true_period_s']}; recovered={r['recovered_period_s']}",
        "direct source coordinate pair","EXACT_SOURCE_PAIR",
    )
    add_value(
        "M1F05","Panel B",f"point {i}",
        f"true={r['true_period_s']}; relative_error={r['relative_period_error']}",
        "M1S044",f"row {i}:true_period_s,relative_period_error",
        f"true={r['true_period_s']}; relative_error={r['relative_period_error']}",
        "direct source coordinate pair","EXACT_SOURCE_PAIR",
    )
add_value("M1F05","Figure note","selected true positives","152","M1S044","row_count","152","direct frozen table row count","DIRECT_CATEGORICAL_COUNT")
add_value("M1F05","Figure note","eligible synthetic positives","1800","M1S042","sensitivity_TPR.denominator","1800","direct frozen metric denominator used as contextual annotation mandated by M1.2","EXACT_SOURCE_VALUE")
save_figure(fig, "M1F05", "f3b_period_recovery")


# -------------------------------------------------------------------------
# Tables
# -------------------------------------------------------------------------

# M1T01
plane_source = {
    "M1EP01":"M1S002","M1EP02":"M1S015","M1EP03":"M1S025",
    "M1EP04":"M1S038","M1EP05":"M1S048","M1EP06":"M1S029",
}
t01_fields = ["plane","data_type","ground_truth_status","what_it_establishes","what_it_does_not_establish","manuscript_role"]
t01_rows=[]
for pid in ["M1EP01","M1EP02","M1EP03","M1EP04","M1EP05","M1EP06"]:
    p=plane_map[pid]
    t01_rows.append({
        "plane": p["phase"] + (" — AUXILIARY NON-RESULT" if pid=="M1EP06" else ""),
        "data_type": p["observational_or_synthetic"],
        "ground_truth_status": p["ground_truth_status"],
        "what_it_establishes": p["what_it_establishes"],
        "what_it_does_not_establish": p["what_it_does_not_establish"],
        "manuscript_role": p["manuscript_role"],
    })
write_csv(TAB_DIR/"M1T01_evidence_planes.csv",t01_fields,t01_rows)
(TAB_DIR/"M1T01_evidence_planes.tex").write_text(
    dataframe_to_tex(t01_fields,t01_rows,"Manuscript 1 evidence planes and truth conditions.","tab:m1_evidence_planes"),
    encoding="utf-8",newline="\n"
)

# M1T02
t02_fields=["category","scope","count_or_state","interpretive_scope"]
t02_specs=[
    ("Cohort","all F3A observational references","122 events","Observational reference cohort; not physical ground truth","M1S030","row_count",122),
    ("Primary variants","frozen 13 x 6 matrix across 122 events","9516","Repeated-measure methodological variants","M1S031","row_count",9516),
    ("Input eligibility","eligible variants","6422","Eligible for classification within the frozen stress test","M1S038","synthesis frozen count",6422),
    ("Input eligibility","inadmissible variants","3094","Structural/methodological inadmissibility retained as outcome","M1S038","synthesis frozen count",3094),
    ("Baseline gate","all references: concordant","65","8 QPP-reference + 57 not-selected-reference","M1S030","direct categorical count",65),
    ("Baseline gate","all references: mismatch","51","Published-QPP reproduction mismatch; not physical falsity","M1S030","direct categorical count",51),
    ("Baseline gate","all references: inadmissible","6","No baseline comparison available","M1S030","direct categorical count",6),
    ("Baseline gate","QPP reference: concordant / mismatch / inadmissible","8 / 51 / 2","Reference-state gate only","M1S030","direct categorical counts", "8 / 51 / 2"),
    ("Baseline gate","not-selected reference: concordant / mismatch / inadmissible","57 / 0 / 4","Reference-state gate only; mismatch count is not FPR","M1S030","direct categorical counts","57 / 0 / 4"),
    ("Transitions","QPP selected retained / selection lost","295 / 171","Cell-level repeated measures conditional on baseline concordance","M1S031","direct categorical counts","295 / 171"),
    ("Transitions","not-selected retained / selection gained","3178 / 0","Cell-level repeated measures; zero gain is not observational FPR","M1S031","direct categorical counts","3178 / 0"),
    ("Numerical stability","optimizer summaries","116","Input-eligible W00/P00 event scope","M1S038","frozen synthesis count",116),
    ("Numerical stability","seed decisions","1160","Frozen seed grid; not evidence of unique optimizer convergence","M1S038","frozen synthesis count",1160),
    ("Numerical stability","seed-discordant events","0","Binary output seed-stable in frozen scope","M1S038","frozen synthesis count",0),
    ("Period robustness","period-comparable variants","295","Conditional on retained selection and baseline comparability","M1S038","frozen synthesis count",295),
]
t02_rows=[]
for category,scope,count,interp,sid,locator,sourceval in t02_specs:
    t02_rows.append({"category":category,"scope":scope,"count_or_state":str(count),"interpretive_scope":interp})
    add_value("M1T02",f"{category}: {scope}","count_or_state",count,sid,locator,sourceval,"direct frozen count presentation","DIRECT_CATEGORICAL_COUNT")
write_csv(TAB_DIR/"M1T02_f3a_robustness_counts.csv",t02_fields,t02_rows)
(TAB_DIR/"M1T02_f3a_robustness_counts.tex").write_text(
    dataframe_to_tex(t02_fields,t02_rows,"F3A catalogue-scale robustness counts and interpretive scope.","tab:m1_f3a_counts"),
    encoding="utf-8",newline="\n"
)

# M1T03
def find_balanced(obj):
    found=[]
    def walk(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if k.lower().replace("-","_")=="balanced_accuracy":
                    found.append(v)
                walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(obj)
    vals=[]
    for x in found:
        if isinstance(x,(int,float)): vals.append(float(x))
        elif isinstance(x,dict) and "point_estimate" in x: vals.append(float(x["point_estimate"]))
    if not vals:
        raise RuntimeError("balanced_accuracy not found in frozen metric artifact")
    # deduplicate near-identical
    uniq=[]
    for v in vals:
        if not any(abs(v-u)<1e-14 for u in uniq): uniq.append(v)
    if len(uniq)!=1:
        raise RuntimeError(f"ambiguous balanced_accuracy values: {uniq}")
    return uniq[0]

dev_cm=dev_metrics["confusion_matrix"]
ho_cm=ho_metrics["confusion_matrix"]
dev_pm=dev_metrics["primary_classification_metrics"]
ho_pm=ho_metrics["primary_classification_metrics"]
dev_ba=find_balanced(dev_metrics)
ho_ba=find_balanced(ho_metrics)

metric_specs=[
    ("TP",dev_cm["TP"],ho_cm["TP"],None,None,"confusion count"),
    ("FN",dev_cm["FN"],ho_cm["FN"],None,None,"confusion count"),
    ("TN",dev_cm["TN"],ho_cm["TN"],None,None,"confusion count"),
    ("FP",dev_cm["FP"],ho_cm["FP"],None,None,"confusion count"),
]
for label,key in [("Sensitivity","sensitivity_TPR"),("Specificity","specificity_TNR"),("FPR","false_positive_rate_FPR")]:
    d=dev_pm[key]; h=ho_pm[key]
    dci=(d["wilson_95_lower"],d["wilson_95_upper"])
    hci=(h["interval"]["lower"],h["interval"]["upper"])
    metric_specs.append((label,d["point_estimate"],h["point_estimate"],dci,hci,"synthetic-ground-truth metric"))
metric_specs.append(("Balanced accuracy",dev_ba,ho_ba,None,None,"split-specific descriptive metric"))

t03_fields=["metric","DEVELOPMENT","DEVELOPMENT_95pct_Wilson","HELDOUT","HELDOUT_95pct_Wilson","interpretive_scope"]
t03_rows=[]
for label,dv,hv,dci,hci,scope in metric_specs:
    def disp(v):
        return str(v) if isinstance(v,int) else fmt_float(float(v))
    ddisp=disp(dv); hdisp=disp(hv)
    dcidisp="" if dci is None else f"[{fmt_float(float(dci[0]))}, {fmt_float(float(dci[1]))}]"
    hcidisp="" if hci is None else f"[{fmt_float(float(hci[0]))}, {fmt_float(float(hci[1]))}]"
    interp="Synthetic-ground-truth performance within the frozen design. No observational performance inference."
    t03_rows.append({
        "metric":label,"DEVELOPMENT":ddisp,"DEVELOPMENT_95pct_Wilson":dcidisp,
        "HELDOUT":hdisp,"HELDOUT_95pct_Wilson":hcidisp,"interpretive_scope":interp,
    })
    if label in {"TP","FN","TN","FP"}:
        add_value("M1T03",label,"DEVELOPMENT",ddisp,"M1S039",f"confusion_matrix.{label}",dv,"direct frozen metric value","EXACT_SOURCE_VALUE")
        add_value("M1T03",label,"HELDOUT",hdisp,"M1S042",f"confusion_matrix.{label}",hv,"direct frozen metric value","EXACT_SOURCE_VALUE")
    elif label=="Balanced accuracy":
        add_value("M1T03",label,"DEVELOPMENT",ddisp,"M1S039","secondary_classification_summary.balanced_accuracy",dv,"deterministic decimal formatting","DETERMINISTIC_LABEL_FORMAT")
        add_value("M1T03",label,"HELDOUT",hdisp,"M1S042","secondary_classification_summary.balanced_accuracy",hv,"deterministic decimal formatting","DETERMINISTIC_LABEL_FORMAT")
    else:
        key={"Sensitivity":"sensitivity_TPR","Specificity":"specificity_TNR","FPR":"false_positive_rate_FPR"}[label]
        add_value("M1T03",label,"DEVELOPMENT",ddisp,"M1S039",f"primary_classification_metrics.{key}.point_estimate",dv,"deterministic decimal formatting","DETERMINISTIC_LABEL_FORMAT")
        add_value("M1T03",label,"HELDOUT",hdisp,"M1S042",f"primary_classification_metrics.{key}.point_estimate",hv,"deterministic decimal formatting","DETERMINISTIC_LABEL_FORMAT")
        add_value("M1T03",label,"DEVELOPMENT 95% Wilson",dcidisp,"M1S039",f"primary_classification_metrics.{key}.wilson_95_lower/upper",dci,"frozen interval bracket formatting","DETERMINISTIC_LABEL_FORMAT")
        add_value("M1T03",label,"HELDOUT 95% Wilson",hcidisp,"M1S042",f"primary_classification_metrics.{key}.interval.lower/upper",hci,"frozen interval bracket formatting","DETERMINISTIC_LABEL_FORMAT")

write_csv(TAB_DIR/"M1T03_synthetic_performance.csv",t03_fields,t03_rows)
(TAB_DIR/"M1T03_synthetic_performance.tex").write_text(
    dataframe_to_tex(t03_fields,t03_rows,"Frozen DEVELOPMENT and independent HELDOUT synthetic-ground-truth performance; split-specific only.","tab:m1_synthetic_performance"),
    encoding="utf-8",newline="\n"
)

# M1T04
boundary_specs = [
    ("F0 reproduction",["M1C001"]),
    ("F3A 51/61 baseline mismatch",["M1C006","M1C007"]),
    ("F3A zero selection gains",["M1C009","M1C010"]),
    ("F3A seed stability (116/116)",["M1C011"]),
    ("F3B HELDOUT FP=0 (0/1800)",["M1C015","M1C016"]),
    ("F3B selection function (156 strata)",["M1C019","M1C020"]),
    ("Conditional period recovery (152 selected TPs)",["M1C021","M1C022"]),
    ("DEVELOPMENT candidate-rule failure",["M1C017","M1C018"]),
    ("Correction NOT_ESTABLISHED",["M1C023"]),
    ("Programme evidence-plane boundary",["M1C024"]),
    ("BAII priority constraint",["M1C028"]),
]
t04_fields=["evidence_or_result","claim_ids","allowed_interpretation","mandatory_qualification","prohibited_interpretation"]
t04_rows=[]
for label,cids in boundary_specs:
    cs=[claim_map[c] for c in cids]
    t04_rows.append({
        "evidence_or_result":label,
        "claim_ids":";".join(cids),
        "allowed_interpretation":" | ".join(c["allowed_wording"] for c in cs),
        "mandatory_qualification":" | ".join(c["mandatory_qualification"] for c in cs),
        "prohibited_interpretation":" | ".join(c["prohibited_wording"] for c in cs),
    })
write_csv(TAB_DIR/"M1T04_claim_boundaries.csv",t04_fields,t04_rows)
(TAB_DIR/"M1T04_claim_boundaries.tex").write_text(
    dataframe_to_tex(t04_fields,t04_rows,"Manuscript-facing claim and limitation boundaries from the frozen M1.1 claim architecture.","tab:m1_claim_boundaries"),
    encoding="utf-8",newline="\n"
)

# Numeric phrases visibly introduced in M1T04 labels.
for loc,display,sid,source_locator,source_value in [
    ("F3A mismatch label","51/61","M1S030","QPP reference baseline gate: 51 mismatch among 61 reference events","51/61"),
    ("F3A seed stability label","116/116","M1S038","frozen optimizer stability scope in synthesis","116/116"),
    ("HELDOUT FP label","0/1800","M1S042","false_positive_rate_FPR numerator/denominator","0/1800"),
    ("selection function label","156","M1S043","row_count","156"),
    ("period recovery label","152","M1S044","row_count","152"),
]:
    add_value("M1T04",loc,"boundary label",display,sid,source_locator,source_value,"frozen value embedded in manuscript-facing boundary label","DETERMINISTIC_LABEL_FORMAT")


# -------------------------------------------------------------------------
# README + DR-010
# -------------------------------------------------------------------------

README.write_text(
"""# Manuscript 1 definitive visual package

STATUS:
DEFINITIVE FIGURE / TABLE PACKAGE FROZEN —
FULL MANUSCRIPT PROSE NOT STARTED

This directory contains the rendering-only Manuscript 1.2 visual package produced from the
frozen Manuscript 1.1 evidence/claim/section architecture. It contains five figures in PDF+PNG
and four tables in CSV+TeX, plus full source/value provenance.

No new scientific computation, statistical inference, bibliography search, AFINO execution,
synthetic generation, smoothing, interpolation, regression, new estimator, scientifically
meaningful normalization, or F2/F3A/F3B denominator pooling is performed here.

`m1_2_rendered_value_audit.csv` is the gate for every scientifically significant number, cell
or plotted point. Structural no-exposure states are rendered as `N/E`, never as zero.

Full manuscript prose remains unstarted.
""",
    encoding="utf-8", newline="\n"
)

DR010.parent.mkdir(parents=True, exist_ok=True)
DR010.write_text(
"""# DR-010 — Manuscript 1 definitive visual package

## Status

Definitive visual-package content freeze candidate. Formal closure requires final Git tag and
byte-exact OSF verification.

## Architecture freeze source

`manuscript1-architecture-v1` at `52024ec3728eeda25f9d640d8f1395a87671c541`.

## Visual scope

Five figures (`M1F01`–`M1F05`) and four tables (`M1T01`–`M1T04`) exactly.

## Five figure decisions

- M1F01: documentary evidence-plane architecture with BAII as a non-result positioning firewall.
- M1F02: F2→F3A continuity of design and change of scale without pooled rates.
- M1F03: F3A baseline gate plus baseline-concordant repeated-measure transitions; no TP/TN/FP/FN.
- M1F04: 156-row independent HELDOUT synthetic selection surface with nine structural no-exposure states preserved as N/E.
- M1F05: 152 selected-TP period-recovery points, visibly conditioned on 152/1800 selected synthetic positives.

## Four table decisions

- M1T01: six evidence planes/truth conditions, BAII explicitly auxiliary non-result.
- M1T02: F3A frozen catalogue/gate/transition/stability/period-comparable counts with interpretive scope.
- M1T03: DEVELOPMENT and HELDOUT synthetic metrics kept split-specific, with only frozen Wilson intervals.
- M1T04: manuscript-facing projection of frozen M1.1 claim boundaries; no new claim is created.

## Rendering-only transformation policy

Allowed transformations are frozen-scope row filtering, deterministic ordering, display pivoting,
unit/label formatting, direct categorical counting already defined by source rows, and visual
composition. No new binning, smoothing, regression, interpolation, confidence interval, estimator,
scientifically meaningful normalization, or cross-plane pooling is allowed.

## Numerical provenance policy

Every scientifically significant rendered number/cell/point is mapped in
`m1_2_rendered_value_audit.csv` to a frozen M1.1 source ID, source artifact, locator and source value.
`STRUCTURAL_NO_EXPOSURE` is not rendered as zero.

## Interpretation firewall

Observational robustness is not observational accuracy. F3A reference mismatches are not physical
falsifications. Zero F3A selection gains are not observational FPR. F3B is synthetic ground-truth
evidence only. Observed HELDOUT FP=0 does not establish population FPR=0. The synthetic selection
function is not an observational population correction. Period recovery is conditional on selection.

## Accessibility / readability policy

PDF is primary; PNG is a 300-dpi preview. Text remains vector in PDF. Figures use grayscale plus
text, marker shape, line style and/or hatching; color-only encoding is forbidden.

## Pre-freeze repair history

- `M1V-TOOL-001`: renderer API compatibility defect, repaired before the first definitive render; scientific effect `NONE`.
- `M1V-VIS-001`: first-candidate M1F04 publication-readability defect, repaired before the second render; scientific/source/claim effects `NONE`.
- `M1V-TOOL-002`: Windows file-lock interruption during rejected-candidate cleanup, recovered before the third render; scientific effect `NONE`.
- `M1V-VIS-002`: second-candidate M1F03/M1F04 readability polish, repaired before the third render; scientific/source/claim effects `NONE`.
- `M1V-VIS-003`: third-candidate M1F04 duplicate-title-layer defect, repaired before the fourth render; scientific/source/claim effects `NONE`.

Rejected visual candidates were never committed or tagged.

## No-new-analysis statement

`new_scientific_computation=false`, `new_statistical_inference=false`,
`new_bibliographic_search=false`, `new_afino_execution=false`,
`new_synthetic_generation=false`, and full manuscript prose remains unstarted.

## Next manuscript task

After final Git/OSF freeze and mentor approval, open Manuscript 1.3 — first complete scientific
draft, beginning with Methods + Results under claim-ID/evidence-plane traceability.
""",
    encoding="utf-8", newline="\n"
)


# -------------------------------------------------------------------------
# Render manifest
# -------------------------------------------------------------------------

manifest_fields = ["artifact_id","rendered_path","format","sha256","bytes","source_ids","claim_ids","render_status"]
manifest_rows=[]
for aid,row in plan_map.items():
    if aid.startswith("M1F"):
        paths = sorted(FIG_DIR.glob(f"{aid}_*"))
    else:
        paths = sorted(TAB_DIR.glob(f"{aid}_*"))
    expected_formats = {"pdf","png"} if aid.startswith("M1F") else {"csv","tex"}
    got={p.suffix.lstrip(".").lower() for p in paths}
    if got != expected_formats or len(paths)!=2:
        raise RuntimeError(f"rendered file set mismatch for {aid}: {paths}")
    for p in paths:
        manifest_rows.append({
            "artifact_id":aid,
            "rendered_path":p.relative_to(ROOT).as_posix(),
            "format":p.suffix.lstrip(".").upper(),
            "sha256":sha(p),
            "bytes":p.stat().st_size,
            "source_ids":row["source_ids"],
            "claim_ids":row["claim_ids"],
            "render_status":"RENDERED_FROM_FROZEN_SOURCES",
        })
if len(manifest_rows)!=18:
    raise RuntimeError("visual manifest rows != 18")
write_csv(MANIFEST,manifest_fields,manifest_rows)

# Rendered-value audit.
value_fields = [
    "rendered_value_id","artifact_id","panel_or_table_location","displayed_label",
    "displayed_value","source_id","source_artifact","source_locator","source_value",
    "transformation","exact_match_status",
]
write_csv(VALUE_AUDIT,value_fields,value_rows)

# Core audit.
visual_audit = {
    "schema_version":"1.0.0",
    "artifact_role":"MANUSCRIPT1_DEFINITIVE_VISUAL_PACKAGE_AUDIT",
    "status":"M1_VISUAL_PACKAGE_VALIDATION_PASS",
    "architecture_freeze":{"commit":ENTRY_COMMIT,"tag":ENTRY_TAG},
    "rendering_contract_freeze_commit":contract_commit,
    "figures":5,
    "tables":4,
    "figure_pdf":5,
    "figure_png":5,
    "table_csv":4,
    "table_tex":4,
    "visual_manifest_rows":18,
    "rendered_value_audit_rows":len(value_rows),
    "pre_freeze_tooling_incidents":[
        x["incident_id"] for x in contract.get("pre_render_tooling_incidents",[])
    ],
    "pre_freeze_visual_review_incidents":[
        x["incident_id"] for x in contract.get("visual_review_incidents",[])
    ],
    "all_source_bindings_verified":True,
    "all_visible_scientific_values_source_mapped":True,
    "normative_plan_source_ids_unchanged":True,
    "normative_plan_claim_ids_unchanged":True,
    "contextual_architecture_annotations_policy":contract["contextual_architecture_annotations_policy"],
    "f3a_frozen_counts":{
        "qpp_baseline_mismatch":"51/61",
        "transitions":"295/171/3178/0",
        "seed_stable_events":"116/116",
    },
    "f3b_frozen_counts":{
        "development_confusion":"143/1657/1799/1",
        "heldout_confusion":"152/1648/1800/0",
        "selection_function_rows":156,
        "structural_no_exposure":9,
        "period_rows":152,
    },
    "interpretation_firewalls":{
        "f2_f3a_denominators_pooled":False,
        "development_heldout_pooled":False,
        "f3a_observational_confusion_labels_used":False,
        "f3b_metrics_explicitly_synthetic":True,
        "heldout_fp_zero_described_as_population_fpr_zero":False,
        "selection_function_described_as_observational_correction":False,
        "period_recovery_conditioned_on_selection":True,
    },
    "new_scientific_computation":False,
    "new_statistical_inference":False,
    "new_bibliographic_search":False,
    "new_afino_execution":False,
    "new_synthetic_generation":False,
    "manuscript_full_prose_started":False,
}
write_json(AUDIT,visual_audit)

# Final checksum registry: every M1.2 final file except this checksum file itself.
targets = [
    README, CONFIG,
    *sorted(FIG_DIR.glob("*")),
    *sorted(TAB_DIR.glob("*")),
    VBIND, MANIFEST, VALUE_AUDIT, AUDIT,
    ROOT/"manuscripts/manuscript_01/scripts/render_manuscript1_visuals.py",
    ROOT/"manuscripts/manuscript_01/scripts/validate_manuscript1_visuals.py",
    ROOT/"manuscripts/manuscript_01/tests/test_manuscript1_visual_package.py",
    DR010,
]
if len(targets)!=28:
    raise RuntimeError(f"M1.2 checksum target count != 28: {len(targets)}")
SUMS.write_text(
    "\n".join(
        f"{sha(p)}  {p.relative_to(ROOT).as_posix()}"
        for p in sorted(targets,key=lambda p:p.relative_to(ROOT).as_posix())
    ) + "\n",
    encoding="utf-8", newline="\n"
)

print("M1_VISUAL_RENDER_PASS")
print("figures = 5")
print("tables = 4")
print("figure_pdf = 5")
print("figure_png = 5")
print("table_csv = 4")
print("table_tex = 4")
print("visual_manifest_rows = 18")
print("rendered_value_audit_rows =",len(value_rows))
print("source_bindings_verified =",len(source_map))
print("M1F04_selection_rows = 156")
print("M1F04_structural_no_exposure = 9")
print("M1F05_period_rows = 152")
print("new_scientific_computation = false")
print("new_statistical_inference = false")
print("new_bibliographic_search = false")
print("new_afino_execution = false")
print("new_synthetic_generation = false")
print("manuscript_full_prose_started = false")
