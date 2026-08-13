#!/usr/bin/env python3
"""Independent F3A.5 CSV/JSON-only structural and scientific-contract validator."""
from __future__ import annotations
import argparse,csv,hashlib,json,math
from collections import Counter,defaultdict
from pathlib import Path

CONTRACT=Path('workflows/phase3a/config/f3a5_analysis_contract.json')
T=Path('workflows/phase3a/evidence/tables')
F=Path('workflows/phase3a/evidence/figures')
R=Path('workflows/phase3a/evidence/reports')
S=Path('workflows/phase3a/evidence/f3a5_SHA256SUMS.txt')
README=Path('workflows/phase3a/README.md')
TRANSITIONS=('SELECTED_RETAINED','SELECTION_LOST','NOT_SELECTED_RETAINED','SELECTION_GAINED')
BASE_STATES=('REFERENCE_CONCORDANT','REFERENCE_BASELINE_MISMATCH','INPUT_INADMISSIBLE','INCOMPLETE_NUMERICAL')
INAD_REASONS=('IRREGULAR_SAMPLING','TOO_FEW_CADENCES','PEAK_REMOVED_BY_QUALITY','PEAK_OUTSIDE_WINDOW','WINDOW_OUT_OF_RANGE')
FIGURES=(
 'f3a5_qpp_reference_cell_heatmap.png','f3a5_not_selected_reference_cell_heatmap.png',
 'f3a5_period_change_distribution.png','f3a5_seed_stability_diagnostic.png')
TABLES=(
 'f3a5_reference_baseline_audit.csv','f3a5_primary_outcome_matrix.csv','f3a5_event_summary.csv',
 'f3a5_window_profile_summary.csv','f3a5_window_summary.csv','f3a5_processing_profile_summary.csv',
 'f3a5_inadmissibility_summary.csv','f3a5_period_robustness.csv','f3a5_period_summary.csv',
 'f3a5_optimizer_stability.csv','f3a5_seed_model_diagnostics.csv')

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()
def rows(p):
 with p.open('r',encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def b(x):return str(x).lower()=='true'
def finite(x):
 try:return math.isfinite(float(x))
 except (ValueError,TypeError):return False

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',default='.');args=ap.parse_args();repo=Path(args.repo_root).resolve()
 c=json.loads((repo/CONTRACT).read_text(encoding='utf-8'))
 for rel,expected in c['normative_inputs'].items():
  p=repo/rel
  if not p.is_file() or sha(p)!=expected:raise RuntimeError('FROZEN_INPUT_HASH_MISMATCH:'+rel)

 cohort=rows(repo/'workflows/phase3a/evidence/tables/f3a2_cohort_manifest.csv')
 variants=rows(repo/'workflows/phase3a/evidence/tables/f3a2_primary_variant_manifest.csv')
 grid=rows(repo/'workflows/phase3a/evidence/tables/f3a2_resolved_decision_grid.csv')
 matrix=rows(repo/'workflows/phase3a/design/robustness_matrix.csv')
 dec=rows(repo/'workflows/phase3a/evidence/tables/f3a4_full_decisions.csv')
 results=rows(repo/'workflows/phase3a/evidence/tables/f3a4_full_results.csv')
 baseline=rows(repo/T/'f3a5_reference_baseline_audit.csv');out=rows(repo/T/'f3a5_primary_outcome_matrix.csv');events=rows(repo/T/'f3a5_event_summary.csv')
 cells=rows(repo/T/'f3a5_window_profile_summary.csv');wins=rows(repo/T/'f3a5_window_summary.csv');profs=rows(repo/T/'f3a5_processing_profile_summary.csv')
 inad=rows(repo/T/'f3a5_inadmissibility_summary.csv');period=rows(repo/T/'f3a5_period_robustness.csv');psum=rows(repo/T/'f3a5_period_summary.csv')
 opt=rows(repo/T/'f3a5_optimizer_stability.csv');seeddiag=rows(repo/T/'f3a5_seed_model_diagnostics.csv')
 audit=json.loads((repo/R/'f3a5_robustness_audit.json').read_text(encoding='utf-8'))
 report=(repo/R/'f3a5_robustness_report.md').read_text(encoding='utf-8')
 readme=(repo/README).read_text(encoding='utf-8')

 cohort_ids={r['phase3a_event_id'] for r in cohort}; variant_ids={r['variant_id'] for r in variants}
 roles={r['observational_reference_role'] for r in cohort}; windows={r['window_variant_id'] for r in matrix}; profiles={r['processing_profile_id'] for r in matrix}
 matrix_cells={(r['matrix_cell_id'],r['window_variant_id'],r['processing_profile_id']) for r in matrix}
 baseline_by_event={r['phase3a_event_id']:r for r in baseline}; outcome_by_variant={r['variant_id']:r for r in out}; variant_by_id={r['variant_id']:r for r in variants}
 primary={(r['variant_id'],int(r['external_optimizer_seed'])):r for r in dec if r['decision_class']=='PRIMARY'}
 baseline_variant={r['phase3a_event_id']:r for r in variants if r['window_variant_id']=='W00' and r['processing_profile_id']=='P00'}
 role_expected={'PUBLISHED_QPP_REFERENCE':True,'PUBLISHED_NOT_SELECTED_REFERENCE':False}

 checks={
  'cohort_rows':len(cohort)==122 and len(cohort_ids)==122,
  'cohort_roles':roles==set(role_expected) and Counter(r['observational_reference_role'] for r in cohort)=={'PUBLISHED_QPP_REFERENCE':61,'PUBLISHED_NOT_SELECTED_REFERENCE':61},
  'primary_planned_rows':len(variants)==9516 and len(variant_ids)==9516,
  'primary_eligible':sum(r['materialization_status']=='ELIGIBLE_FOR_AFINO' for r in variants)==6422,
  'primary_inadmissible':sum(r['materialization_status']=='INPUT_INADMISSIBLE' for r in variants)==3094,
  'matrix_rows':len(matrix)==78 and len(matrix_cells)==78 and len(windows)==13 and len(profiles)==6,
  'baseline_rows':len(baseline)==122 and set(baseline_by_event)==cohort_ids,
  'baseline_input_eligible':sum(r['baseline_materialization_status']=='ELIGIBLE_FOR_AFINO' for r in baseline)==116,
  'outcome_rows':len(out)==9516 and set(outcome_by_variant)==variant_ids,
  'event_rows':len(events)==122 and {r['phase3a_event_id'] for r in events}==cohort_ids,
  'cell_rows':len(cells)==156,
  'window_rows':len(wins)==26,
  'profile_rows':len(profs)==12,
  'optimizer_rows':len(opt)==116,
  'seeddiag_rows':len(seeddiag)==3 and {r['model_id'] for r in seeddiag}=={'M0','M1','M2'},
  'period_summary_rows':len(psum)==3 and {r['quantity'] for r in psum}=={'signed_period_change_s','absolute_period_change_s','period_ratio_variant_to_baseline'},
 }

 # Recompute baseline gate exactly from frozen role, baseline materialization and primary seed0 decision.
 baseline_ok=True
 for e in cohort:
  eid=e['phase3a_event_id']; v=baseline_variant[eid]; d=primary.get((v['variant_id'],0)); available=d is not None and d['decision_status']=='VALID'; selected=b(d['qpp_selected']) if available else None
  if v['materialization_status']=='INPUT_INADMISSIBLE':state='INPUT_INADMISSIBLE'
  elif not available:state='INCOMPLETE_NUMERICAL'
  else:state='REFERENCE_CONCORDANT' if selected==role_expected[e['observational_reference_role']] else 'REFERENCE_BASELINE_MISMATCH'
  br=baseline_by_event[eid]
  baseline_ok &= br['baseline_variant_id']==v['variant_id'] and br['baseline_materialization_status']==v['materialization_status'] and br['baseline_gate_state']==state
  baseline_ok &= br['expected_reference_selection_state']==('true' if role_expected[e['observational_reference_role']] else 'false')
  baseline_ok &= b(br['baseline_decision_available'])==available and (br['baseline_qpp_selected']=='' if selected is None else b(br['baseline_qpp_selected'])==selected)
 checks['baseline_gate_recalculation']=baseline_ok and set(r['baseline_gate_state'] for r in baseline)<=set(BASE_STATES)

 # Exact primary variant mapping and transition reconstruction.
 outcome_ok=True; expected_transition_ids=[]
 for v in variants:
  r=outcome_by_variant[v['variant_id']]; bg=baseline_by_event[v['phase3a_event_id']]; d=primary.get((v['variant_id'],0)); available=d is not None and d['decision_status']=='VALID'; selected=b(d['qpp_selected']) if available else None
  outcome_ok &= all(r[k]==v[k] for k in ('phase3a_event_id','pair_id','observational_reference_role','variant_id','matrix_cell_id','window_variant_id','processing_profile_id','materialization_status'))
  outcome_ok &= b(r['variant_decision_available'])==available
  if v['materialization_status']=='ELIGIBLE_FOR_AFINO': outcome_ok &= available
  else: outcome_ok &= not available and not b(r['transition_eligible'])
  trans=''; concord=''; eligible=False
  if bg['baseline_gate_state']=='REFERENCE_CONCORDANT' and v['materialization_status']=='ELIGIBLE_FOR_AFINO' and available:
   eligible=True; bs=b(bg['baseline_qpp_selected'])
   trans='SELECTED_RETAINED' if bs and selected else 'SELECTION_LOST' if bs else 'NOT_SELECTED_RETAINED' if not selected else 'SELECTION_GAINED'
   concord='true' if selected==bs else 'false'; expected_transition_ids.append(v['variant_id'])
  outcome_ok &= b(r['transition_eligible'])==eligible and r['classification_transition']==trans and r['classification_concordant_with_baseline']==concord
 checks['primary_mapping_and_transitions']=outcome_ok
 checks['transition_states']=all(r['classification_transition'] in ('',*TRANSITIONS) for r in out)
 checks['transition_baseline']=all((not b(r['transition_eligible'])) or r['baseline_gate_state']=='REFERENCE_CONCORDANT' for r in out)

 # Event summaries: complete and denominators explicit/reconstructable.
 event_ok=True
 by_event=defaultdict(list)
 for r in out:by_event[r['phase3a_event_id']].append(r)
 for e in events:
  rr=by_event[e['phase3a_event_id']]; te=sum(b(x['transition_eligible']) for x in rr); cc=sum(x['classification_concordant_with_baseline']=='true' for x in rr)
  event_ok &= int(e['planned_cells'])==78 and int(e['eligible_cells'])+int(e['inadmissible_cells'])==78 and int(e['transition_eligible_cells'])==te and int(e['classification_concordant_cells'])==cc and int(e['classification_concordance_denominator'])==te
  if te: event_ok &= math.isclose(float(e['classification_concordance_fraction_among_eligible']),cc/te,rel_tol=0,abs_tol=1e-15)
  else: event_ok &= e['classification_concordance_fraction_among_eligible']==''
 checks['event_summary_reconstruction']=event_ok

 # Cell/window/profile exact structural coverage and repeated-measure denominators.
 expected_cell={(cid,w,p,role) for cid,w,p in matrix_cells for role in roles}
 actual_cell={(r['matrix_cell_id'],r['window_variant_id'],r['processing_profile_id'],r['observational_reference_role']) for r in cells}
 checks['all_78_cells_both_roles']=actual_cell==expected_cell and all(int(r['planned_event_count'])==61 for r in cells)
 checks['cell_planned_total']=sum(int(r['planned_event_count']) for r in cells)==9516
 checks['cell_eligible_total']=sum(int(r['eligible_count']) for r in cells)==6422
 checks['cell_inadmissible_total']=sum(int(r['inadmissible_count']) for r in cells)==3094
 checks['window_complete']= {(r['window_variant_id'],r['observational_reference_role']) for r in wins}=={(w,role) for w in windows for role in roles} and all(int(r['planned_variant_rows'])==366 and r['independent_observations']=='false' and r['repeated_measure_unit']=='phase3a_event_id' for r in wins)
 checks['profile_complete']={(r['processing_profile_id'],r['observational_reference_role']) for r in profs}=={(p,role) for p in profiles for role in roles} and all(int(r['planned_variant_rows'])==793 and r['independent_observations']=='false' and r['repeated_measure_unit']=='phase3a_event_id' for r in profs)

 # Rebuild every inadmissibility summary row from the 9516-row outcome matrix.
 def expected_inad(scope,val,reason):
  rr=out if scope=='GLOBAL' else [r for r in out if (r['observational_reference_role'] if scope=='REFERENCE_ROLE' else r['window_variant_id'] if scope=='WINDOW' else r['processing_profile_id'])==val]
  n=sum(r['materialization_status']=='INPUT_INADMISSIBLE' and (reason=='ALL' or r['inadmissibility_reason']==reason) for r in rr)
  return len(rr),n
 inad_ok=True
 for r in inad:
  planned,n=expected_inad(r['scope_type'],r['scope_value'],r['inadmissibility_reason']); inad_ok &= int(r['planned_variant_rows'])==planned and int(r['inadmissible_count'])==n
 global_rows={(r['inadmissibility_reason']):r for r in inad if r['scope_type']=='GLOBAL' and r['scope_value']=='ALL'}
 expected_global={'ALL':3094,'IRREGULAR_SAMPLING':1824,'TOO_FEW_CADENCES':844,'PEAK_REMOVED_BY_QUALITY':282,'PEAK_OUTSIDE_WINDOW':138,'WINDOW_OUT_OF_RANGE':6}
 inad_ok &= set(global_rows)==set(expected_global) and all(int(global_rows[k]['inadmissible_count'])==v and int(global_rows[k]['planned_variant_rows'])==9516 for k,v in expected_global.items())
 checks['inadmissibility_reconstruction']=inad_ok

 # Period table must be complete, not merely valid: exact selected-selected finite set.
 baseline_period={r['phase3a_event_id']:r['formal_m1_period_s'] for r in out if r['window_variant_id']=='W00' and r['processing_profile_id']=='P00'}
 expected_period=set()
 for r in out:
  bg=baseline_by_event[r['phase3a_event_id']]; bp=baseline_period.get(r['phase3a_event_id'])
  if bg['baseline_gate_state']=='REFERENCE_CONCORDANT' and b(bg['baseline_qpp_selected']) and b(r['variant_qpp_selected']) and finite(bp) and finite(r['formal_m1_period_s']): expected_period.add(r['variant_id'])
 actual_period={r['variant_id'] for r in period}
 period_ok=actual_period==expected_period and len(actual_period)==len(period)
 for r in period:
  o=outcome_by_variant[r['variant_id']]; bg=baseline_by_event[r['phase3a_event_id']]; period_ok &= bg['baseline_gate_state']=='REFERENCE_CONCORDANT' and b(bg['baseline_qpp_selected']) and b(o['variant_qpp_selected']) and finite(r['baseline_period_s']) and finite(r['variant_period_s'])
 checks['period_selected_selected_complete']=period_ok

 # Stability grid and diagnostic reconstruction from frozen decisions/results.
 stab=[d for d in dec if d['window_variant_id']=='W00' and d['processing_profile_id']=='P00']; sg=defaultdict(set)
 for d in stab:sg[d['phase3a_event_id']].add(int(d['external_optimizer_seed']))
 baseline_eligible_events={e for e,v in baseline_variant.items() if v['materialization_status']=='ELIGIBLE_FOR_AFINO'}
 checks['stability_grid']=set(sg)==baseline_eligible_events and len(sg)==116 and all(s==set(range(10)) for s in sg.values())
 checks['optimizer_event_set']={r['phase3a_event_id'] for r in opt}==baseline_eligible_events and all(int(r['seed_count'])==10 for r in opt)
 target_results=[r for r in results if r['window_variant_id']=='W00' and r['processing_profile_id']=='P00']
 diag_ok=True
 diag_by={r['model_id']:r for r in seeddiag}
 for m in ('M0','M1','M2'):
  rr=[r for r in target_results if r['model_id']==m]; d=diag_by[m]
  diag_ok &= len(rr)==1160 and int(d['calls'])==1160 and int(d['warning_calls'])==sum(int(x['warning_count'])>0 for x in rr) and int(d['warning_count'])==sum(int(x['warning_count']) for x in rr) and int(d['bound_calls'])==sum(int(x['parameter_at_bound'])>0 for x in rr)
  diag_ok &= json.loads(d['convergence_status_counts'])==dict(sorted(Counter(x['convergence_status'] for x in rr).items()))
 checks['seed_model_diagnostics_reconstructed']=diag_ok

 # Audit must explicitly preserve zero-valued categories and denominators.
 actual_gate=Counter(r['baseline_gate_state'] for r in baseline); actual_trans=Counter(r['classification_transition'] for r in out if r['classification_transition']); actual_inad=Counter(r['inadmissibility_reason'] for r in out if r['materialization_status']=='INPUT_INADMISSIBLE')
 checks['audit_baseline_counts']=audit['baseline_gate_counts']=={k:actual_gate[k] for k in BASE_STATES} and audit['baseline_gate_denominator']==122
 checks['audit_all_four_transitions']=audit['transition_counts']=={k:actual_trans[k] for k in TRANSITIONS} and audit['transition_denominator']==sum(actual_trans.values())
 checks['audit_inadmissibility']=audit['inadmissibility_counts']=={k:actual_inad[k] for k in INAD_REASONS} and audit['inadmissibility_denominator']==9516
 checks['audit_period_seed_counts']=audit['period_comparable_rows']==len(period) and audit['seed_stable_events']+audit['seed_discordant_events']==116

 prohibited=set(c['prohibited_metrics']);headers=set()
 for p in [baseline,out,events,cells,wins,profs,inad,period,psum,opt,seeddiag]:
  if p:headers.update(p[0])
 checks['prohibited_metric_columns_absent']=not(headers&prohibited)
 boundaries=audit['scientific_boundaries']; expected_false=['new_afino_execution','fits_opened','payload_npy_opened','sqlite_opened','variants_regenerated','new_threshold_added','formal_hypothesis_test_performed','observational_ground_truth_established','sensitivity_computed','specificity_computed','observational_fpr_computed','candidate_discovery_authorized']
 checks['boundary_flags']=all(boundaries.get(k) is False for k in expected_false)
 checks['analysis_state']=audit['analysis_status'] in ('PHASE3A_CATALOGUE_ROBUSTNESS_CHARACTERIZED','PHASE3A_CATALOGUE_ROBUSTNESS_CHARACTERIZED_WITH_LIMITATIONS')
 checks['report_word_count']=1200<=len(report.split())<=1700 and audit['report_word_count']==len(report.split())
 checks['readme_status']='CATALOGUE-SCALE ROBUSTNESS CHARACTERIZED —\nPHASE 3A CLOSURE NOT STARTED' in readme
 checks['figures']=all((repo/F/n).is_file() and (repo/F/n).stat().st_size>0 for n in FIGURES)

 # Checksum registry must contain exactly every generated/frozen artifact specified by analyzer, except itself.
 expected_locs={
  *(str((T/n).as_posix()) for n in TABLES),*(str((F/n).as_posix()) for n in FIGURES),
  str((R/'f3a5_robustness_audit.json').as_posix()),str((R/'f3a5_robustness_report.md').as_posix()),
  str(README.as_posix()),str(CONTRACT.as_posix())}
 entries=[x.split('\t',2) for x in (repo/S).read_text(encoding='utf-8').splitlines() if x and not x.startswith('#')]
 locs={loc for kind,digest,loc in entries}
 checks['checksum_registry_exact_members']=locs==expected_locs and len(entries)==len(expected_locs)
 checks['checksum_registry_hashes']=all((repo/loc).is_file() and sha(repo/loc)==digest for kind,digest,loc in entries)

 failed=[k for k,v in checks.items() if not v]
 if failed:
  print('PHASE3A_CATALOGUE_ROBUSTNESS_ANALYSIS_BLOCKED');print('failed=',','.join(failed));return 2
 print('PHASE3A_CATALOGUE_ROBUSTNESS_VALIDATION_PASS')
 for k in sorted(checks):print(k,'= PASS')
 print('baseline_gate_counts =',json.dumps(audit['baseline_gate_counts'],sort_keys=True))
 print('transition_counts =',json.dumps(audit['transition_counts'],sort_keys=True))
 print('inadmissibility_counts =',json.dumps(audit['inadmissibility_counts'],sort_keys=True))
 print('period_comparable_rows =',len(period));print('seed_stable_events =',audit['seed_stable_events']);print('seed_discordant_events =',audit['seed_discordant_events'])
 print('new_afino_execution = false');print('fits_opened = false');print('variants_regenerated = false');print('observational_ground_truth_established = false');print('sensitivity_computed = false');print('specificity_computed = false');print('observational_fpr_computed = false');print('candidate_discovery_authorized = false');return 0
if __name__=='__main__':raise SystemExit(main())
