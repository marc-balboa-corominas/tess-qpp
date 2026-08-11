#!/usr/bin/env python3
"""
F3A.2 — bind and download the exact TESS SPOC 20-second light-curve products
for the already frozen Phase 3A cohort.

Scientific boundary:
- reads the frozen cohort and frozen TESS binding policy;
- queries MAST metadata deterministically;
- downloads only the selected official 20-s SPOC LC products;
- hashes each physical FITS before opening its scientific arrays;
- audits FITS identity, required columns, time metadata, and source-marker mapping;
- DOES NOT construct F3A robustness variants;
- DOES NOT import or execute AFINO;
- DOES NOT compute QPP classifications.

The script is checkpointed and safe to rerun.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import time
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    import numpy as np
    from astropy.io import fits
    from astroquery.mast import Observations
except Exception as exc:
    raise SystemExit(
        "Missing dependency. Install with:\n"
        "  python -m pip install --upgrade astroquery astropy numpy\n"
        f"Original import error: {exc}"
    )

F3A1_FROZEN_HASHES = {
    "workflows/phase3a/design/cohort_contract.yaml":
        "613267b13bdcfbcb89859ee9f2ed7f072d161b43c295574b718a0d3061d48c86",
    "workflows/phase3a/design/reference_label_policy.json":
        "e139db5e335eb6ae059a25166e08918c9fa5f7ae2d9a7f6d406ef5c52e2412f0",
    "workflows/phase3a/design/robustness_matrix.csv":
        "2412c686b91a287361865347f8159fb48fabae809eee783222dbbc190f0d3590",
    "workflows/phase3a/design/outcomes_denominators.json":
        "59b5513c763e6fba0859ddd139ca9c746374b75c0682dfa8e6c474ed47d3234c",
    "workflows/phase3a/design/numerical_stability_protocol.json":
        "c7869210a9d7d75532d285349a39f62be108e72acb53dd4143e2e4891b66686a",
    "workflows/phase3a/design/preregistration.json":
        "b37741f058b6cc133014b52bef6621ee34ddfc9cc671d80113c2ec7b76094ba5",
}

COHORT_REL = Path("workflows/phase3a/evidence/tables/f3a2_cohort_manifest.csv")
POLICY_REL = Path("workflows/phase3a/config/f3a2_tess_product_binding_policy.json")
PRODUCT_MANIFEST_REL = Path("workflows/phase3a/evidence/tables/f3a2_tess_product_manifest.csv")
TIME_AUDIT_REL = Path("workflows/phase3a/evidence/tables/f3a2_time_mapping_audit.csv")
CHECKPOINT_REL = Path("local_archive/phase3a/f3a2_tess_binding/checkpoint.json")
CANDIDATES_REL = Path("local_archive/phase3a/f3a2_tess_binding/mast_product_candidates.jsonl")
DEFAULT_RAW_REL = Path("data/raw/phase3a/tess")


PRODUCT_FIELDS = [
    "phase3a_event_id",
    "tic_id",
    "sector",
    "product_status",
    "product_identifier",
    "product_uri_or_archive_key",
    "physical_filename",
    "physical_sha256",
    "size_bytes",
    "fits_checksum_status",
    "fits_datasum_status",
    "time_column_present",
    "sap_flux_present",
    "pdcsap_flux_present",
    "quality_present",
    "n_rows",
    "median_cadence_s",
    "source_start_index",
    "source_peak_index",
    "source_end_index",
    "start_mapping_residual_s",
    "peak_mapping_residual_s",
    "end_mapping_residual_s",
    "time_mapping_status",
    "candidate_product_count",
    "candidate_datauris_json",
    "selected_prvversion",
    "mast_obsid",
    "timesys",
    "bjdrefi",
    "bjdreff",
    "timeunit",
    "header_ticid",
    "header_sector",
]

TIME_FIELDS = [
    "phase3a_event_id",
    "tic_id",
    "sector",
    "source_time_system",
    "source_time_unit",
    "source_start_time",
    "source_peak_time",
    "source_end_time",
    "native_timesys",
    "native_bjdref",
    "native_timeunit",
    "source_start_index",
    "source_peak_index",
    "source_end_index",
    "start_mapping_residual_s",
    "peak_mapping_residual_s",
    "end_mapping_residual_s",
    "start_le_peak_le_end",
    "w00_includes_peak",
    "mapping_reproducible",
    "time_mapping_status",
    "mapping_notes",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})
    tmp.replace(path)


def verify_frozen_inputs(repo: Path) -> None:
    for rel, expected in F3A1_FROZEN_HASHES.items():
        p = repo / rel
        if not p.is_file():
            raise RuntimeError(f"Missing frozen F3A.1 input: {rel}")
        actual = sha256_file(p)
        if actual != expected:
            raise RuntimeError(
                f"Frozen F3A.1 hash mismatch: {rel}\n"
                f"expected={expected}\nactual={actual}"
            )


def jsonable(v: Any) -> Any:
    if v is None:
        return None
    try:
        if hasattr(v, "mask") and bool(v.mask):
            return None
    except Exception:
        pass
    try:
        if isinstance(v, np.generic):
            return v.item()
    except Exception:
        pass
    return str(v) if not isinstance(v, (str, int, float, bool)) else v


def version_key(value: Any) -> tuple[int, ...]:
    if value is None:
        return tuple()
    nums = re.findall(r"\d+", str(value))
    return tuple(int(x) for x in nums)


def candidate_sort_key(row: dict[str, Any]) -> tuple:
    # Highest processing/calibration version first; then lexicographically smallest URI.
    v = version_key(row.get("prvversion"))
    padded = v + (0,) * (8 - len(v))
    return tuple(-x for x in padded[:8]) + (str(row.get("dataURI", "")),)


def exact_fast_lc_filename(filename: str, tic: int, sector: int) -> bool:
    low = filename.lower()
    tic16 = f"{tic:016d}"
    return (
        f"-s{sector:04d}-" in low
        and f"-{tic16}-" in low
        and low.endswith("_fast-lc.fits")
    )


def table_rows_to_dicts(table) -> list[dict[str, Any]]:
    rows = []
    for r in table:
        d = {}
        for name in table.colnames:
            try:
                d[name] = jsonable(r[name])
            except Exception:
                d[name] = None
        rows.append(d)
    return rows


def query_matching_products(tic: int, sector: int) -> tuple[list[dict[str, Any]], str]:
    """
    Query exact SPOC 20-second TESS time-series observations. Several target_name
    spellings are tried only as metadata-query fallbacks; product acceptance is
    ultimately based on exact TIC+sector filename identity.
    """
    target_forms = [
        str(tic),
        f"{tic:016d}",
        f"TIC {tic}",
        f"*{tic}*",
    ]
    errors = []

    for target_name in target_forms:
        try:
            obs = Observations.query_criteria(
                obs_collection="TESS",
                provenance_name="SPOC",
                sequence_number=int(sector),
                target_name=target_name,
                dataproduct_type="timeseries",
                t_exptime=[19.0, 21.0],
                dataRights="PUBLIC",
            )
        except Exception as exc:
            errors.append(f"{target_name!r}: {type(exc).__name__}: {exc}")
            continue

        if len(obs) == 0:
            continue

        try:
            products = Observations.get_product_list(obs)
        except Exception as exc:
            errors.append(f"{target_name!r} products: {type(exc).__name__}: {exc}")
            continue

        matches = []
        for d in table_rows_to_dicts(products):
            fn = str(d.get("productFilename") or "")
            if exact_fast_lc_filename(fn, tic, sector):
                matches.append(d)

        if matches:
            # De-duplicate by dataURI.
            by_uri = {}
            for d in matches:
                uri = str(d.get("dataURI") or "")
                if uri:
                    by_uri[uri] = d
            return sorted(by_uri.values(), key=candidate_sort_key), target_name

    return [], " | ".join(errors[-4:])


def checksum_status(hdul, kind: str) -> str:
    results = []
    for hdu in hdul:
        try:
            value = hdu.verify_checksum() if kind == "checksum" else hdu.verify_datasum()
        except Exception:
            results.append("ERROR")
            continue
        # astropy convention: 1 valid, 0 invalid, 2 keyword absent.
        if value == 1:
            results.append("VALID")
        elif value == 0:
            results.append("INVALID")
        elif value == 2:
            results.append("NOT_PRESENT")
        else:
            results.append(str(value))
    if "INVALID" in results or "ERROR" in results:
        return "FAIL:" + "|".join(results)
    if all(x == "VALID" for x in results):
        return "PASS"
    return "PARTIAL:" + "|".join(results)


def nearest_native_index(time_values: np.ndarray, marker: float) -> tuple[int, float]:
    finite_idx = np.flatnonzero(np.isfinite(time_values))
    if len(finite_idx) == 0:
        raise ValueError("TIME contains no finite cadences")
    vals = time_values[finite_idx]
    dist = np.abs(vals - marker)
    min_dist = np.nanmin(dist)
    # Exact tie -> lowest original row index.
    tie = finite_idx[np.isclose(dist, min_dist, rtol=0.0, atol=1e-15)]
    idx = int(np.min(tie))
    residual_s = float((time_values[idx] - marker) * 86400.0)
    return idx, residual_s


def inspect_fits(path: Path, expected_tic: int, expected_sector: int) -> dict[str, Any]:
    # Physical bytes have already been hashed before this function is called.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with fits.open(path, memmap=True, checksum=False) as hdul:
            primary = hdul[0].header
            if len(hdul) < 2 or getattr(hdul[1], "data", None) is None:
                raise RuntimeError(f"No LIGHTCURVE binary table in {path.name}")
            ext = hdul[1]
            header = ext.header
            data = ext.data
            names = set(data.names or [])

            required = {
                "TIME": "TIME" in names,
                "SAP_FLUX": "SAP_FLUX" in names,
                "PDCSAP_FLUX": "PDCSAP_FLUX" in names,
                "QUALITY": "QUALITY" in names,
            }

            time_values = np.asarray(data["TIME"], dtype=np.float64) if required["TIME"] else np.array([])
            finite_t = time_values[np.isfinite(time_values)]
            median_cadence_s = ""
            if len(finite_t) >= 2:
                median_cadence_s = float(np.nanmedian(np.diff(finite_t)) * 86400.0)

            timesys = str(primary.get("TIMESYS", header.get("TIMESYS", ""))).strip()
            bjdrefi = primary.get("BJDREFI", header.get("BJDREFI", ""))
            bjdreff = primary.get("BJDREFF", header.get("BJDREFF", ""))
            timeunit = str(primary.get("TIMEUNIT", header.get("TIMEUNIT", ""))).strip()
            ticid = primary.get("TICID", header.get("TICID", ""))
            sector = primary.get("SECTOR", header.get("SECTOR", ""))

            # Re-open without changing bytes to evaluate FITS checksum keywords.
            cs = checksum_status(hdul, "checksum")
            ds = checksum_status(hdul, "datasum")

            return {
                "required": required,
                "time_values": time_values,
                "n_rows": len(data),
                "median_cadence_s": median_cadence_s,
                "timesys": timesys,
                "bjdrefi": bjdrefi,
                "bjdreff": bjdreff,
                "timeunit": timeunit,
                "header_ticid": ticid,
                "header_sector": sector,
                "fits_checksum_status": cs,
                "fits_datasum_status": ds,
            }


def time_metadata_compatible(info: dict[str, Any]) -> tuple[bool, str]:
    try:
        bjdref = float(info["bjdrefi"]) + float(info["bjdreff"])
    except Exception:
        return False, "BJDREF_UNREADABLE"
    if str(info["timesys"]).upper() != "TDB":
        return False, f"TIMESYS={info['timesys']}"
    if not math.isclose(bjdref, 2457000.0, rel_tol=0.0, abs_tol=1e-9):
        return False, f"BJDREF={bjdref}"
    if str(info["timeunit"]).lower() not in {"d", "day", "days"}:
        return False, f"TIMEUNIT={info['timeunit']}"
    return True, "TBJD_NUMERIC_COMPATIBLE_WITH_TESS_BTJD"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--download-dir", default=str(DEFAULT_RAW_REL))
    ap.add_argument("--sleep-s", type=float, default=0.15)
    ap.add_argument("--query-only", action="store_true",
                    help="Resolve MAST candidates but do not download/open FITS.")
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()
    raw_dir = Path(args.download_dir)
    if not raw_dir.is_absolute():
        raw_dir = repo / raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)

    verify_frozen_inputs(repo)

    cohort_path = repo / COHORT_REL
    policy_path = repo / POLICY_REL
    if not cohort_path.is_file() or not policy_path.is_file():
        raise RuntimeError("Missing frozen F3A.2 cohort or TESS policy.")

    cohort = load_csv(cohort_path)
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    if policy.get("status") != "FROZEN_BEFORE_FITS_ACCESS":
        raise RuntimeError("Unexpected TESS binding policy status.")

    if len(cohort) != 122:
        raise RuntimeError(f"Expected frozen cohort of 122 rows, got {len(cohort)}")

    pair_to_events: dict[tuple[int, int], list[dict[str, str]]] = defaultdict(list)
    for r in cohort:
        pair_to_events[(int(r["tic_id"]), int(r["sector"]))].append(r)

    if len(pair_to_events) != 87:
        raise RuntimeError(f"Expected 87 unique TIC-sector pairs, got {len(pair_to_events)}")

    checkpoint_path = repo / CHECKPOINT_REL
    candidate_log = repo / CANDIDATES_REL
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    checkpoint: dict[str, Any] = {}
    if checkpoint_path.is_file():
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))

    product_rows = []
    time_rows = []
    pair_summary = {}

    for order, ((tic, sector), events) in enumerate(sorted(pair_to_events.items()), start=1):
        pair_key = f"{tic}:S{sector}"
        print(f"[{order:02d}/{len(pair_to_events)}] TIC {tic} sector {sector}", flush=True)

        matches, query_basis = query_matching_products(tic, sector)

        log_record = {
            "tic_id": tic,
            "sector": sector,
            "queried_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "query_basis": query_basis,
            "candidate_count": len(matches),
            "candidates": matches,
        }
        with candidate_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(log_record, ensure_ascii=False) + "\n")

        if not matches:
            pair_summary[pair_key] = {"status": "MISSING_PRODUCT", "candidate_count": 0}
            for ev in events:
                product_rows.append({
                    "phase3a_event_id": ev["phase3a_event_id"],
                    "tic_id": tic, "sector": sector,
                    "product_status": "MISSING_PRODUCT",
                    "candidate_product_count": 0,
                    "candidate_datauris_json": "[]",
                    "time_mapping_status": "MISSING_PRODUCT",
                })
                time_rows.append({
                    "phase3a_event_id": ev["phase3a_event_id"],
                    "tic_id": tic, "sector": sector,
                    "source_time_system": "TBJD",
                    "source_time_unit": "d",
                    "source_start_time": ev["source_start_time"],
                    "source_peak_time": ev["source_peak_time"],
                    "source_end_time": ev["source_end_time"],
                    "mapping_reproducible": "false",
                    "time_mapping_status": "MISSING_PRODUCT",
                    "mapping_notes": "No exact SPOC 20-second fast LC found by frozen metadata rules.",
                })
            continue

        selected = matches[0]
        fn = str(selected["productFilename"])
        uri = str(selected["dataURI"])
        cand_uris = [str(x.get("dataURI") or "") for x in matches]

        if args.query_only:
            pair_summary[pair_key] = {
                "status": "CANDIDATE_BOUND_QUERY_ONLY",
                "candidate_count": len(matches),
                "selected_dataURI": uri,
                "selected_filename": fn,
            }
            continue

        local_path = raw_dir / fn
        if local_path.is_file() and checkpoint.get(pair_key, {}).get("physical_sha256"):
            existing_sha = sha256_file(local_path)
            if existing_sha != checkpoint[pair_key]["physical_sha256"]:
                raise RuntimeError(
                    f"Existing FITS hash changed for {pair_key}: {local_path}"
                )
            print("  existing exact FITS reused", flush=True)
        else:
            status, msg, url = Observations.download_file(
                uri, local_path=str(local_path), cache=True, verbose=True
            )
            if status not in {"COMPLETE", "SKIPPED"} or not local_path.is_file():
                raise RuntimeError(
                    f"MAST download failed for {pair_key}: status={status} msg={msg}"
                )

        # Mandatory physical hash before opening scientific arrays.
        physical_sha = sha256_file(local_path)
        physical_size = local_path.stat().st_size

        checkpoint[pair_key] = {
            "dataURI": uri,
            "filename": fn,
            "physical_sha256": physical_sha,
            "size_bytes": physical_size,
        }
        checkpoint_path.write_text(
            json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8"
        )

        info = inspect_fits(local_path, tic, sector)
        compatible, compatibility_note = time_metadata_compatible(info)

        header_tic_ok = str(info["header_ticid"]).strip().lstrip("0") == str(tic)
        try:
            header_sector_ok = int(info["header_sector"]) == int(sector)
        except Exception:
            header_sector_ok = False

        if not header_tic_ok or not header_sector_ok:
            raise RuntimeError(
                f"FITS identity mismatch for {pair_key}: "
                f"TICID={info['header_ticid']} SECTOR={info['header_sector']}"
            )

        required_ok = all(info["required"].values())
        if not required_ok:
            raise RuntimeError(
                f"Required LC columns missing for {pair_key}: {info['required']}"
            )

        for ev in events:
            base_product = {
                "phase3a_event_id": ev["phase3a_event_id"],
                "tic_id": tic,
                "sector": sector,
                "product_status": "BOUND_DOWNLOADED",
                "product_identifier": fn,
                "product_uri_or_archive_key": uri,
                "physical_filename": fn,
                "physical_sha256": physical_sha,
                "size_bytes": physical_size,
                "fits_checksum_status": info["fits_checksum_status"],
                "fits_datasum_status": info["fits_datasum_status"],
                "time_column_present": str(info["required"]["TIME"]).lower(),
                "sap_flux_present": str(info["required"]["SAP_FLUX"]).lower(),
                "pdcsap_flux_present": str(info["required"]["PDCSAP_FLUX"]).lower(),
                "quality_present": str(info["required"]["QUALITY"]).lower(),
                "n_rows": info["n_rows"],
                "median_cadence_s": info["median_cadence_s"],
                "candidate_product_count": len(matches),
                "candidate_datauris_json": json.dumps(cand_uris),
                "selected_prvversion": selected.get("prvversion") or "",
                "mast_obsid": selected.get("obsID") or selected.get("obsid") or "",
                "timesys": info["timesys"],
                "bjdrefi": info["bjdrefi"],
                "bjdreff": info["bjdreff"],
                "timeunit": info["timeunit"],
                "header_ticid": info["header_ticid"],
                "header_sector": info["header_sector"],
            }

            source_start = float(ev["source_start_time"])
            source_peak = float(ev["source_peak_time"])
            source_end = float(ev["source_end_time"])

            if not compatible:
                mapping_status = "SOURCE_TIME_MAPPING_UNRESOLVED"
                p_row = dict(base_product)
                p_row["time_mapping_status"] = mapping_status
                product_rows.append(p_row)
                time_rows.append({
                    "phase3a_event_id": ev["phase3a_event_id"],
                    "tic_id": tic,
                    "sector": sector,
                    "source_time_system": "TBJD",
                    "source_time_unit": "d",
                    "source_start_time": source_start,
                    "source_peak_time": source_peak,
                    "source_end_time": source_end,
                    "native_timesys": info["timesys"],
                    "native_bjdref": f"{float(info['bjdrefi']) + float(info['bjdreff']):.12f}"
                        if info["bjdrefi"] != "" and info["bjdreff"] != "" else "",
                    "native_timeunit": info["timeunit"],
                    "mapping_reproducible": "false",
                    "time_mapping_status": mapping_status,
                    "mapping_notes": compatibility_note,
                })
                continue

            t = info["time_values"]
            start_idx, start_res = nearest_native_index(t, source_start)
            peak_idx, peak_res = nearest_native_index(t, source_peak)
            end_idx, end_res = nearest_native_index(t, source_end)

            ordered = start_idx <= peak_idx <= end_idx
            mapping_status = "TIME_MAPPING_VALID" if ordered else "WINDOW_OUT_OF_RANGE"

            p_row = dict(base_product)
            p_row.update({
                "source_start_index": start_idx,
                "source_peak_index": peak_idx,
                "source_end_index": end_idx,
                "start_mapping_residual_s": f"{start_res:.9f}",
                "peak_mapping_residual_s": f"{peak_res:.9f}",
                "end_mapping_residual_s": f"{end_res:.9f}",
                "time_mapping_status": mapping_status,
            })
            product_rows.append(p_row)

            time_rows.append({
                "phase3a_event_id": ev["phase3a_event_id"],
                "tic_id": tic,
                "sector": sector,
                "source_time_system": "TBJD",
                "source_time_unit": "d",
                "source_start_time": source_start,
                "source_peak_time": source_peak,
                "source_end_time": source_end,
                "native_timesys": info["timesys"],
                "native_bjdref": f"{float(info['bjdrefi']) + float(info['bjdreff']):.12f}",
                "native_timeunit": info["timeunit"],
                "source_start_index": start_idx,
                "source_peak_index": peak_idx,
                "source_end_index": end_idx,
                "start_mapping_residual_s": f"{start_res:.9f}",
                "peak_mapping_residual_s": f"{peak_res:.9f}",
                "end_mapping_residual_s": f"{end_res:.9f}",
                "start_le_peak_le_end": str(ordered).lower(),
                "w00_includes_peak": str(ordered).lower(),
                "mapping_reproducible": "true",
                "time_mapping_status": mapping_status,
                "mapping_notes": compatibility_note,
            })

        pair_summary[pair_key] = {
            "status": "BOUND_DOWNLOADED",
            "candidate_count": len(matches),
            "selected_dataURI": uri,
            "selected_filename": fn,
            "physical_sha256": physical_sha,
            "size_bytes": physical_size,
        }

        time.sleep(max(args.sleep_s, 0.0))

    if args.query_only:
        print("PHASE3A_TESS_PRODUCT_DISCOVERY_COMPLETE_QUERY_ONLY")
        print(f"frozen_cohort_events={len(cohort)}")
        print(f"unique_tic_sector_pairs={len(pair_to_events)}")
        print(f"pairs_with_candidate={sum(v['status']=='CANDIDATE_BOUND_QUERY_ONLY' for v in pair_summary.values())}")
        print(f"pairs_missing_product={sum(v['status']=='MISSING_PRODUCT' for v in pair_summary.values())}")
        print("fits_opened=false")
        print("afino_executed=false")
        return 0

    product_rows.sort(key=lambda r: r["phase3a_event_id"])
    time_rows.sort(key=lambda r: r["phase3a_event_id"])
    write_csv(repo / PRODUCT_MANIFEST_REL, product_rows, PRODUCT_FIELDS)
    write_csv(repo / TIME_AUDIT_REL, time_rows, TIME_FIELDS)

    unique_fits = {
        r["physical_sha256"]
        for r in product_rows
        if r.get("physical_sha256")
    }
    missing = sum(r["product_status"] == "MISSING_PRODUCT" for r in product_rows)
    valid = sum(r["time_mapping_status"] == "TIME_MAPPING_VALID" for r in product_rows)
    unresolved = sum(
        r["time_mapping_status"] == "SOURCE_TIME_MAPPING_UNRESOLVED"
        for r in product_rows
    )
    out_of_range = sum(r["time_mapping_status"] == "WINDOW_OUT_OF_RANGE" for r in product_rows)

    if len(product_rows) != 122 or len(time_rows) != 122:
        raise RuntimeError("Event-product/time-audit relationship count must remain 122.")

    print("PHASE3A_TESS_PRODUCT_BINDING_STAGE_COMPLETE")
    print(f"frozen_cohort_events={len(cohort)}")
    print(f"unique_tic_sector_pairs={len(pair_to_events)}")
    print(f"event_product_relationships={len(product_rows)}")
    print(f"unique_physical_fits={len(unique_fits)}")
    print(f"missing_product_event_relationships={missing}")
    print(f"time_mapping_valid={valid}")
    print(f"time_mapping_unresolved={unresolved}")
    print(f"time_mapping_out_of_range={out_of_range}")
    print("physical_sha256_before_fits_open=true")
    print("afino_imported=false")
    print("afino_executed=false")
    print("scientific_results_computed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
