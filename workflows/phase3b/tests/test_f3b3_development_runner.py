from __future__ import annotations

import ast
import csv
import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
RUNNER_PATH = ROOT / "workflows/phase3b/scripts/run_f3b_development_checkpointed.py"
TABLE = ROOT / "workflows/phase3b/development/evidence/tables"
CONFIG = ROOT / "workflows/phase3b/development/config"

def _load_runner():
    spec = importlib.util.spec_from_file_location("f3b3_runner", RUNNER_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def test_blinded_plan_truth_columns_absent():
    rows = _csv(TABLE / "f3b3_blinded_execution_plan.csv")
    assert len(rows) == 12744
    forbidden = {"truth_state", "true_period_s", "qpp_fraction", "ground_truth_label"}
    assert forbidden.isdisjoint(rows[0].keys())

def test_blinded_plan_one_to_one_mapping():
    src = _csv(TABLE / "f3b2_development_exact_afino_plan.csv")
    blind = _csv(TABLE / "f3b3_blinded_execution_plan.csv")
    assert len(src) == len(blind) == 12744
    fields = list(blind[0].keys())
    assert [{k:r[k] for k in fields} for r in src] == blind

def test_canary_counts_and_seed_balance():
    decisions = _csv(TABLE / "f3b3_canary_decision_manifest.csv")
    jobs = _csv(TABLE / "f3b3_canary_job_manifest.csv")
    assert len(decisions) == 216
    assert len(jobs) == 648
    seeds = [int(x["external_optimizer_seed"]) for x in decisions]
    assert seeds.count(0) == seeds.count(1) == seeds.count(9) == 72
    assert sum(x["decision_class"] == "BASELINE" for x in decisions) == 72
    assert sum(x["decision_class"] == "NUMERICAL_STABILITY_EXTRA" for x in decisions) == 144

def test_canary_jobs_are_exact_subset():
    blind = {r["job_id"]: r for r in _csv(TABLE / "f3b3_blinded_execution_plan.csv")}
    jobs = _csv(TABLE / "f3b3_canary_job_manifest.csv")
    assert len({r["job_id"] for r in jobs}) == 648
    for row in jobs:
        src = blind[row["job_id"]]
        assert {k:row[k] for k in src.keys()} == src

def test_payload_hash_rejection():
    r = _load_runner()
    rows = _csv(TABLE / "f3b3_blinded_execution_plan.csv")
    payloads = r.load_payload_dataset(ROOT)
    job = r.validate_job(rows[0])
    bad = dict(job)
    bad["payload_logical_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="Payload logical SHA mismatch"):
        r.extract_payload(bad, payloads)

def test_unknown_job_rejection(tmp_path):
    r = _load_runner()
    rows = _csv(TABLE / "f3b3_canary_job_manifest.csv")
    fields = list(rows[0].keys())
    rows[0] = dict(rows[0])
    rows[0]["job_id"] = "UNKNOWN"
    p = tmp_path / "canary.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(rows)
    # unknown path is also prohibited, giving a hard rejection before inference
    with pytest.raises(RuntimeError):
        r.load_plan(ROOT, p)

@pytest.mark.parametrize("field,bad_value", [("external_optimizer_seed", "999"), ("model_id", "M9")])
def test_seed_model_mismatch_rejection(monkeypatch, field, bad_value):
    r = _load_runner()
    original_read_csv = r.read_csv
    canonical = (ROOT / "workflows/phase3b/development/evidence/tables/f3b3_canary_job_manifest.csv").resolve()
    bad_rows = [dict(x) for x in original_read_csv(canonical)]
    bad_rows[0][field] = bad_value
    def fake_read_csv(path):
        return bad_rows if Path(path).resolve() == canonical else original_read_csv(path)
    monkeypatch.setattr(r, "read_csv", fake_read_csv)
    with pytest.raises(RuntimeError, match="differs from blinded source plan"):
        r.load_plan(ROOT, canonical)

def _jobs(n=9):
    r = _load_runner()
    return [r.validate_job(x) for x in _csv(TABLE / "f3b3_canary_job_manifest.csv")[:n]]

def test_partial_decision_resume_and_completed_skip(tmp_path):
    r = _load_runner()
    cp = tmp_path / "cp.sqlite"
    jobs = _jobs(9)
    env={"test":True}
    s1=r.run_jobs(checkpoint=cp,jobs=jobs,payloads=None,max_new_jobs=4,resume=False,
                  manifest_sha="m",plan_kind="canary",runner_sha="r",environment=env,
                  executor=lambda j,p:r._fake_result_for_test(j))
    assert s1 == {"existing_before":0,"new_jobs":4,"total_after":4,"pending_after":5}
    s2=r.run_jobs(checkpoint=cp,jobs=jobs,payloads=None,max_new_jobs=5,resume=True,
                  manifest_sha="m",plan_kind="canary",runner_sha="r",environment=env,
                  executor=lambda j,p:r._fake_result_for_test(j))
    assert s2 == {"existing_before":4,"new_jobs":5,"total_after":9,"pending_after":0}
    s3=r.run_jobs(checkpoint=cp,jobs=jobs,payloads=None,max_new_jobs=9,resume=True,
                  manifest_sha="m",plan_kind="canary",runner_sha="r",environment=env,
                  executor=lambda j,p:r._fake_result_for_test(j))
    assert s3["new_jobs"] == 0 and s3["total_after"] == 9

def test_duplicate_checkpoint_prevention(tmp_path):
    r = _load_runner()
    cp = tmp_path / "cp.sqlite"
    jobs=_jobs(1); env={"test":True}
    r.run_jobs(checkpoint=cp,jobs=jobs,payloads=None,max_new_jobs=1,resume=False,
               manifest_sha="m",plan_kind="canary",runner_sha="r",environment=env,
               executor=lambda j,p:r._fake_result_for_test(j))
    with pytest.raises(RuntimeError, match="Checkpoint exists"):
        r.run_jobs(checkpoint=cp,jobs=jobs,payloads=None,max_new_jobs=0,resume=False,
                   manifest_sha="m",plan_kind="canary",runner_sha="r",environment=env,
                   executor=lambda j,p:r._fake_result_for_test(j))

def test_selection_rule_exactness():
    r=_load_runner()
    assert r.selection_rule(21,0,21) is True
    assert r.selection_rule(10,0,21) is False
    assert r.selection_rule(21,0,10) is False
    assert r.selection_rule(10.0000000001,0,10.0000000001) is True

def test_decision_assembly_requires_three_models():
    r=_load_runner()
    jobs=_jobs(3)
    results=[r._fake_result_for_test(j) for j in jobs]
    out=r.assemble_complete_decisions(results)
    assert len(out)==1
    assert out[0]["decision_status"]=="VALID"
    assert r.assemble_complete_decisions(results[:2]) == []

def test_full_plan_authorization_guard():
    r=_load_runner()
    with pytest.raises(RuntimeError, match="EXPLICIT_AUTHORIZATION"):
        r.load_plan(ROOT, TABLE / "f3b3_blinded_execution_plan.csv")

def test_heldout_plan_rejection(tmp_path):
    r=_load_runner()
    p=tmp_path/"heldout_plan.csv"; p.write_text("x\n",encoding="utf-8")
    with pytest.raises(RuntimeError, match="HELDOUT"):
        r.load_plan(ROOT, p)

def test_environment_binding_is_f3a_stack():
    binding=json.loads((CONFIG/"f3b3_afino_execution_environment_binding.json").read_text(encoding="utf-8"))
    env=binding["execution_environment"]
    assert env["python_version"]=="3.13.13"
    assert env["numpy_version"]=="2.5.1"
    assert env["scipy_version"]=="1.18.0"
    assert env["afino_package_version"]=="0.5"
    assert env["afino_commit"]=="6aceac9518fc8056052807e666da9d0c8bebb010"
    assert env["byteorder"]=="little"

def test_completed_full_checkpoint_idempotence_semantics(tmp_path):
    r=_load_runner()
    cp=tmp_path/"cp.sqlite"; jobs=_jobs(6); env={"test":True}
    r.run_jobs(checkpoint=cp,jobs=jobs,payloads=None,max_new_jobs=6,resume=False,
               manifest_sha="m",plan_kind="canary",runner_sha="r",environment=env,
               executor=lambda j,p:r._fake_result_for_test(j))
    s=r.run_jobs(checkpoint=cp,jobs=jobs,payloads=None,max_new_jobs=999,resume=True,
                 manifest_sha="m",plan_kind="canary",runner_sha="r",environment=env,
                 executor=lambda j,p:r._fake_result_for_test(j))
    assert s["new_jobs"]==0 and s["pending_after"]==0

def test_runner_source_boundary_excludes_generator_truth_and_heldout_io():
    source = RUNNER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert all("f3b_synthetic_generator" not in name for name in imported)
    assert all("truth" not in name.lower() for name in imported)
    assert "truth_ledger" not in source

def _valid_full_authorization(path: Path):
    payload = {
        "frozen_jobs": 12744, "frozen_decisions": 4248, "baseline_decisions": 3600,
        "stability_extra_decisions": 648, "validated_canary_jobs": 648,
        "remaining_new_jobs": 12096, "canary_reuse": True, "canary_rerun": False,
        "development_only": True, "heldout_authorized": False,
        "scientific_metrics_authorized": False, "candidate_rule_fitting_authorized": False,
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

def test_canary_to_full_bootstrap_preserves_result_core(tmp_path):
    r = _load_runner()
    canary_rows = _csv(TABLE / "f3b3_canary_job_manifest.csv")
    blind_rows = _csv(TABLE / "f3b3_blinded_execution_plan.csv")
    blind_fields = list(blind_rows[0].keys())
    canary_jobs = [r.validate_job({k: row[k] for k in blind_fields}) for row in canary_rows]
    full_jobs = [r.validate_job(row) for row in blind_rows]
    canary_cp = tmp_path / "canary.sqlite"
    env = {"test": True}
    runner_sha = "runner-test-sha"
    r.run_jobs(
        checkpoint=canary_cp, jobs=canary_jobs, payloads=None, max_new_jobs=648, resume=False,
        manifest_sha=r.EXPECTED_CANARY_JOB_SHA256, plan_kind="canary",
        runner_sha=runner_sha, environment=env, executor=lambda j,p:r._fake_result_for_test(j),
    )
    auth = tmp_path / "authorization.json"
    _valid_full_authorization(auth)
    full_cp = tmp_path / "full.sqlite"
    out = r.bootstrap_canary_results(
        source_checkpoint=canary_cp, destination_checkpoint=full_cp,
        canary_jobs=canary_jobs, full_jobs=full_jobs,
        full_manifest_sha=r.EXPECTED_BLINDED_PLAN_SHA256,
        runner_sha=runner_sha, environment=env, authorization_path=auth,
    )
    assert out == {"imported_rows":648, "result_core_mismatches":0, "payload_mismatches":0, "remaining_new_jobs":12096}
    src = {x["job_id"]:x for x in r.fetch_results(canary_cp)}
    dst = {x["job_id"]:x for x in r.fetch_results(full_cp)}
    assert set(src) == set(dst)
    assert all(src[k]["result_core_sha256"] == dst[k]["result_core_sha256"] for k in src)

def test_resume_rejects_checkpoint_identity_drift(tmp_path):
    r = _load_runner()
    jobs = _jobs(3)
    cp = tmp_path / "cp.sqlite"
    env = {"test": True}
    r.run_jobs(
        checkpoint=cp, jobs=jobs, payloads=None, max_new_jobs=3, resume=False,
        manifest_sha="m", plan_kind="canary", runner_sha="r", environment=env,
        executor=lambda j,p:r._fake_result_for_test(j),
    )
    con = r.connect_checkpoint(cp)
    try:
        con.execute("UPDATE results SET payload_logical_sha256=? WHERE job_id=?", ("0"*64, jobs[0]["job_id"]))
        con.commit()
    finally:
        con.close()
    with pytest.raises(RuntimeError, match="scientific identity mismatch"):
        r.run_jobs(
            checkpoint=cp, jobs=jobs, payloads=None, max_new_jobs=0, resume=True,
            manifest_sha="m", plan_kind="canary", runner_sha="r", environment=env,
            executor=lambda j,p:r._fake_result_for_test(j),
        )
