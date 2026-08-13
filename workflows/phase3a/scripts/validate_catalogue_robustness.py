#!/usr/bin/env python3
"""Independent F3A.5 CSV/JSON-only structural validator."""
from __future__ import annotations
import argparse,csv,hashlib,json,math
from collections import Counter,defaultdict
from pathlib import Path

CONTRACT=Path('workflows/phase3a/config/f3a5_analysis_contract.json'); T=Path('workflows/phase3a/evidence/tables'); R=Path('workflows/phase3a/evidence/reports'); S=Path('workflows/phase3a/evidence/f3a5_SHA256SUMS.txt')

def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()
def rows(p):
 with p.open('r',encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def b(x):return str(x).lower()=='true'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',default='.');args=ap.parse_args();repo=Path(args.repo_root).resolve();c=json.loads((repo/CONTRACT).read_text(encoding='utf-8'))
 for rel,expected in c['normative_inputs'].items():
  if sha(repo/rel)!=expected:raise RuntimeError('FROZEN_INPUT_HASH_MISMATCH:'+rel)
 cohort=rows(repo/'workflows/phase3a/evidence/tables/f3a2_cohort_manifest.csv');variants=rows(repo/'workflows/phase3a/evidence/tables/f3a2_primary_variant_manifest.csv');grid=rows(repo/'workflows/phase3a/evidence/tables/f3a2_resolved_decision_grid.csv');dec=rows(repo/'workflows/phase3a/evidence/tables/f3a4_full_decisions.csv')
 baseline=rows(repo/T/'f3a5_reference_baseline_audit.csv');out=rows(repo/T/'f3a5_primary_outcome_matrix.csv');events=rows(repo/T/'f3a5_event_summary.csv');cells=rows(repo/T/'f3a5_window_profile_summary.csv');wins=rows(repo/T/'f3a5_window_summary.csv');profs=rows(repo/T/'f3a5_processing_profile_summary.csv');inad=rows(repo/T/'f3a5_inadmissibility_summary.csv');period=rows(repo/T/'f3a5_period_robustness.csv');psum=rows(repo/T/'f3a5_period_summary.csv');opt=rows(repo/T/'f3a5_optimizer_stability.csv');seeddiag=rows(repo/T/'f3a5_seed_model_diagnostics.csv');audit=json.loads((repo/R/'f3a5_robustness_audit.json').read_text(encoding='utf-8'))
 checks={
 'cohort_rows':len(cohort)==122,'primary_planned_rows':len(variants)==9516,'primary_eligible':sum(r['materialization_status']=='ELIGIBLE_FOR_AFINO' for r in variants)==6422,'primary_inadmissible':sum(r['materialization_status']=='INPUT_INADMISSIBLE' for r in variants)==3094,
 'baseline_rows':len(baseline)==122,'baseline_input_eligible':sum(r['baseline_materialization_status']=='ELIGIBLE_FOR_AFINO' for r in baseline)==116,'outcome_rows':len(out)==9516,'event_rows':len(events)==122,'cell_rows':len(cells)==156,'window_rows':len(wins)==26,'profile_rows':len(profs)==12,'optimizer_rows':len(opt)==116,'seeddiag_rows':len(seeddiag)==3,
 'cell_planned_total':sum(int(r['planned_event_count']) for r in cells)==9516,'cell_eligible_total':sum(int(r['eligible_count']) for r in cells)==6422,'cell_inadmissible_total':sum(int(r['inadmissible_count']) for r in cells)==3094,
 'all_cells_both_roles':len({(r['matrix_cell_id'],r['observational_reference_role']) for r in cells})==156,
 'window_planned':all(int(r['planned_variant_rows'])==366 and r['independent_observations']=='false' and r['repeated_measure_unit']=='phase3a_event_id' for r in wins),
 'profile_planned':all(int(r['planned_variant_rows'])==793 and r['independent_observations']=='false' and r['repeated_measure_unit']=='phase3a_event_id' for r in profs),
 'seed_complete':all(int(r['seed_count'])==10 for r in opt) and sum(int(r['seed_count']) for r in opt)==1160,
 'transition_baseline':all((not b(r['transition_eligible'])) or r['baseline_gate_state']=='REFERENCE_CONCORDANT' for r in out),
 'transition_states':all(r['classification_transition'] in ('','SELECTED_RETAINED','SELECTION_LOST','NOT_SELECTED_RETAINED','SELECTION_GAINED') for r in out),
 'period_selected_selected':all(next(x for x in baseline if x['phase3a_event_id']==r['phase3a_event_id'])['baseline_gate_state']=='REFERENCE_CONCORDANT' and next(x for x in out if x['variant_id']==r['variant_id'])['variant_qpp_selected']=='true' for r in period),
 'unique_variants':len({r['variant_id'] for r in out})==9516,'unique_events':len({r['phase3a_event_id'] for r in events})==122,
 }
 # Eligible variants exactly one seed0 primary decision; inadmissible no primary decision.
 primary=[d for d in dec if d['decision_class']=='PRIMARY' and int(d['external_optimizer_seed'])==0]; pvars=Counter(d['variant_id'] for d in primary); checks['eligible_decision_mapping']=all((pvars[v['variant_id']]==1 if v['materialization_status']=='ELIGIBLE_FOR_AFINO' else pvars[v['variant_id']]==0) for v in variants)
 # 116 x 10 stability decisions in W00/P00 across primary+stability.
 stab=[d for d in dec if d['window_variant_id']=='W00' and d['processing_profile_id']=='P00']; g=defaultdict(set)
 for d in stab:g[d['phase3a_event_id']].add(int(d['external_optimizer_seed']))
 checks['stability_grid']=len(g)==116 and all(s==set(range(10)) for s in g.values())
 # Prohibited metrics absent from output headers.
 prohibited=set(c['prohibited_metrics']); headers=set()
 for p in [baseline,out,events,cells,wins,profs,inad,period,psum,opt,seeddiag]:
  if p:headers.update(p[0])
 checks['prohibited_metric_columns_absent']=not (headers & prohibited)
 boundaries=audit['scientific_boundaries']; expected_false=['new_afino_execution','fits_opened','payload_npy_opened','sqlite_opened','variants_regenerated','new_threshold_added','formal_hypothesis_test_performed','observational_ground_truth_established','sensitivity_computed','specificity_computed','observational_fpr_computed','candidate_discovery_authorized'];checks['boundary_flags']=all(boundaries[k] is False for k in expected_false)
 # checksum registry must cover itself-excluded generated artifacts and all hashes match.
 entries=[x.split('\t',2) for x in (repo/S).read_text(encoding='utf-8').splitlines() if x and not x.startswith('#')];checks['checksum_registry']=all((repo/loc).is_file() and sha(repo/loc)==digest for kind,digest,loc in entries)
 failed=[k for k,v in checks.items() if not v]
 if failed: print('PHASE3A_CATALOGUE_ROBUSTNESS_ANALYSIS_BLOCKED'); print('failed=',','.join(failed)); return 2
 print('PHASE3A_CATALOGUE_ROBUSTNESS_VALIDATION_PASS')
 for k in ('cohort_rows','primary_planned_rows','primary_eligible','primary_inadmissible','baseline_rows','baseline_input_eligible','outcome_rows','event_rows','cell_rows','window_rows','profile_rows','optimizer_rows','seed_complete','stability_grid','transition_baseline','period_selected_selected','boundary_flags','checksum_registry'):print(k,'= PASS')
 print('new_afino_execution = false');print('fits_opened = false');print('variants_regenerated = false');print('observational_ground_truth_established = false');print('sensitivity_computed = false');print('specificity_computed = false');print('observational_fpr_computed = false');print('candidate_discovery_authorized = false');return 0
if __name__=='__main__':raise SystemExit(main())
