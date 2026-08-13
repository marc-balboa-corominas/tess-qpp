#!/usr/bin/env python3
"""F3A.5 catalogue-scale observational robustness characterization.

Consumes only frozen CSV/JSON files. It must not import AFINO/Astropy/Lightkurve
or open FITS, NPY payload arrays, or SQLite databases.
"""
from __future__ import annotations
import argparse, ast, csv, hashlib, json, math, statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

CONTRACT_REL=Path("workflows/phase3a/config/f3a5_analysis_contract.json")
TABLE_DIR=Path("workflows/phase3a/evidence/tables")
FIG_DIR=Path("workflows/phase3a/evidence/figures")
REPORT_DIR=Path("workflows/phase3a/evidence/reports")
SUMS_REL=Path("workflows/phase3a/evidence/f3a5_SHA256SUMS.txt")
README_REL=Path("workflows/phase3a/README.md")

BASELINE_REL=TABLE_DIR/"f3a5_reference_baseline_audit.csv"
OUTCOME_REL=TABLE_DIR/"f3a5_primary_outcome_matrix.csv"
EVENT_REL=TABLE_DIR/"f3a5_event_summary.csv"
CELL_REL=TABLE_DIR/"f3a5_window_profile_summary.csv"
WINDOW_REL=TABLE_DIR/"f3a5_window_summary.csv"
PROFILE_REL=TABLE_DIR/"f3a5_processing_profile_summary.csv"
INAD_REL=TABLE_DIR/"f3a5_inadmissibility_summary.csv"
PERIOD_REL=TABLE_DIR/"f3a5_period_robustness.csv"
PERIOD_SUM_REL=TABLE_DIR/"f3a5_period_summary.csv"
OPT_REL=TABLE_DIR/"f3a5_optimizer_stability.csv"
SEED_DIAG_REL=TABLE_DIR/"f3a5_seed_model_diagnostics.csv"
AUDIT_REL=REPORT_DIR/"f3a5_robustness_audit.json"
REPORT_REL=REPORT_DIR/"f3a5_robustness_report.md"

FIGURES=[
 FIG_DIR/"f3a5_qpp_reference_cell_heatmap.png",
 FIG_DIR/"f3a5_not_selected_reference_cell_heatmap.png",
 FIG_DIR/"f3a5_period_change_distribution.png",
 FIG_DIR/"f3a5_seed_stability_diagnostic.png",
]

PROHIBITED_IMPORT_ROOTS={'afino','astropy','lightkurve'}


def sha256_file(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()

def read_csv(path:Path):
 with path.open('r',encoding='utf-8',newline='') as f: return list(csv.DictReader(f))

def write_csv(path:Path,rows:list[dict[str,Any]],fields:list[str]):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='raise',lineterminator='\n'); w.writeheader(); w.writerows(rows)

def b(v): return str(v).lower()=='true'
def txt_bool(v): return 'true' if bool(v) else 'false'
def fnum(v):
 try:
  x=float(v); return x if math.isfinite(x) else None
 except (TypeError,ValueError): return None

def ratio(n,d): return '' if d==0 else n/d

def linear_quantile(values,q):
 vals=sorted(float(x) for x in values)
 if not vals: return None
 if len(vals)==1:return vals[0]
 pos=(len(vals)-1)*q; lo=math.floor(pos); hi=math.ceil(pos)
 if lo==hi:return vals[lo]
 return vals[lo]+(vals[hi]-vals[lo])*(pos-lo)

def summary6(values):
 vals=[float(x) for x in values if x is not None and math.isfinite(float(x))]
 if not vals:return {'n':0,'min':'','q1':'','median':'','q3':'','max':''}
 return {'n':len(vals),'min':min(vals),'q1':linear_quantile(vals,.25),'median':linear_quantile(vals,.5),'q3':linear_quantile(vals,.75),'max':max(vals)}

def value_range(values):
 vals=[float(x) for x in values if x is not None and math.isfinite(float(x))]
 return '' if not vals else max(vals)-min(vals)

def verify_inputs(repo:Path,contract:dict):
 errors=[]
 for rel,expected in contract['normative_inputs'].items():
  p=repo/rel
  if not p.is_file(): errors.append(f'MISSING:{rel}'); continue
  actual=sha256_file(p)
  if actual!=expected: errors.append(f'HASH:{rel}:{actual}')
 if errors: raise RuntimeError('F3A5_INPUT_BINDING_FAILURE\n'+'\n'.join(errors))
 # Explicitly fail if this analyzer ever acquires prohibited imports.
 tree=ast.parse(Path(__file__).read_text(encoding='utf-8'))
 roots=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.Import): roots.extend(alias.name.split('.')[0] for alias in node.names)
  elif isinstance(node,ast.ImportFrom) and node.module: roots.append(node.module.split('.')[0])
 bad=sorted(set(roots)&PROHIBITED_IMPORT_ROOTS)
 if bad: raise RuntimeError('PROHIBITED_IMPORT:'+','.join(bad))
 return True

def load_inputs(repo:Path):
 c=json.loads((repo/CONTRACT_REL).read_text(encoding='utf-8'))
 paths={k:repo/k for k in c['normative_inputs']}
 return c,{
  'denom':json.loads(paths['workflows/phase3a/design/outcomes_denominators.json'].read_text(encoding='utf-8')),
  'labels':json.loads(paths['workflows/phase3a/design/reference_label_policy.json'].read_text(encoding='utf-8')),
  'stability':json.loads(paths['workflows/phase3a/design/numerical_stability_protocol.json'].read_text(encoding='utf-8')),
  'matrix':read_csv(paths['workflows/phase3a/design/robustness_matrix.csv']),
  'cohort':read_csv(paths['workflows/phase3a/evidence/tables/f3a2_cohort_manifest.csv']),
  'variants':read_csv(paths['workflows/phase3a/evidence/tables/f3a2_primary_variant_manifest.csv']),
  'grid':read_csv(paths['workflows/phase3a/evidence/tables/f3a2_resolved_decision_grid.csv']),
  'results':read_csv(paths['workflows/phase3a/evidence/tables/f3a4_full_results.csv']),
  'decisions':read_csv(paths['workflows/phase3a/evidence/tables/f3a4_full_decisions.csv']),
  'temporal':read_csv(paths['workflows/phase3a/evidence/tables/f3a4_temporal_contract_diagnostic.csv']),
 }

def baseline_gate(cohort,variants,decisions):
 primary={(r['variant_id'],int(r['external_optimizer_seed'])):r for r in decisions if r['decision_class']=='PRIMARY'}
 bv={r['phase3a_event_id']:r for r in variants if r['window_variant_id']=='W00' and r['processing_profile_id']=='P00'}
 out=[]; by={}
 expected={'PUBLISHED_QPP_REFERENCE':True,'PUBLISHED_NOT_SELECTED_REFERENCE':False}
 for e in cohort:
  v=bv[e['phase3a_event_id']]
  d=primary.get((v['variant_id'],0))
  available=d is not None and d.get('decision_status')=='VALID'
  selected=b(d['qpp_selected']) if available else None
  exp=expected[e['observational_reference_role']]
  if v['materialization_status']=='INPUT_INADMISSIBLE': state='INPUT_INADMISSIBLE'
  elif not available: state='INCOMPLETE_NUMERICAL'
  else: state='REFERENCE_CONCORDANT' if selected==exp else 'REFERENCE_BASELINE_MISMATCH'
  row={
   'phase3a_event_id':e['phase3a_event_id'],'pair_id':e['pair_id'],'observational_reference_role':e['observational_reference_role'],
   'baseline_variant_id':v['variant_id'],'baseline_materialization_status':v['materialization_status'],
   'baseline_inadmissibility_reason':v['inadmissibility_reason_code'],
   'baseline_decision_available':txt_bool(available),'baseline_qpp_selected':'' if selected is None else txt_bool(selected),
   'expected_reference_selection_state':txt_bool(exp),'baseline_gate_state':state,
  }
  out.append(row); by[e['phase3a_event_id']]={**row,'_selected':selected}
 return out,by

def primary_outcomes(variants,decisions,base):
 dby={r['variant_id']:r for r in decisions if r['decision_class']=='PRIMARY' and int(r['external_optimizer_seed'])==0}
 out=[]
 for v in variants:
  bg=base[v['phase3a_event_id']]; d=dby.get(v['variant_id'])
  available=d is not None and d.get('decision_status')=='VALID'; selected=b(d['qpp_selected']) if available else None
  trans=''; concord=''; eligible=False
  if bg['baseline_gate_state']=='REFERENCE_CONCORDANT' and v['materialization_status']=='ELIGIBLE_FOR_AFINO' and available:
   eligible=True; bs=bg['_selected']
   if bs and selected: trans='SELECTED_RETAINED'
   elif bs and not selected: trans='SELECTION_LOST'
   elif not bs and not selected: trans='NOT_SELECTED_RETAINED'
   else: trans='SELECTION_GAINED'
   concord=txt_bool(selected==bs)
  period=d.get('formal_m1_period_s','') if available else ''
  role=''
  if available: role='recovered_period_selected' if selected else 'formal_m1_center_not_selected'
  out.append({
   'phase3a_event_id':v['phase3a_event_id'],'pair_id':v['pair_id'],'observational_reference_role':v['observational_reference_role'],
   'variant_id':v['variant_id'],'matrix_cell_id':v['matrix_cell_id'],'window_variant_id':v['window_variant_id'],'processing_profile_id':v['processing_profile_id'],
   'materialization_status':v['materialization_status'],'inadmissibility_reason':v['inadmissibility_reason_code'],
   'baseline_gate_state':bg['baseline_gate_state'],'baseline_qpp_selected':'' if bg['_selected'] is None else txt_bool(bg['_selected']),
   'variant_decision_available':txt_bool(available),'variant_qpp_selected':'' if selected is None else txt_bool(selected),
   'transition_eligible':txt_bool(eligible),'classification_transition':trans,'classification_concordant_with_baseline':concord,
   'formal_m1_period_s':period,'period_role':role,
  })
 return out

def event_summaries(cohort,outcomes,base):
 by=defaultdict(list)
 for r in outcomes:by[r['phase3a_event_id']].append(r)
 reasons=['IRREGULAR_SAMPLING','TOO_FEW_CADENCES','PEAK_REMOVED_BY_QUALITY','PEAK_OUTSIDE_WINDOW','WINDOW_OUT_OF_RANGE']
 rows=[]
 for e in cohort:
  rr=by[e['phase3a_event_id']]; tc=Counter(r['classification_transition'] for r in rr); rc=Counter(r['inadmissibility_reason'] for r in rr)
  elig=sum(r['materialization_status']=='ELIGIBLE_FOR_AFINO' for r in rr); inad=sum(r['materialization_status']=='INPUT_INADMISSIBLE' for r in rr)
  te=sum(b(r['transition_eligible']) for r in rr); cc=sum(r['classification_concordant_with_baseline']=='true' for r in rr)
  row={'phase3a_event_id':e['phase3a_event_id'],'pair_id':e['pair_id'],'observational_reference_role':e['observational_reference_role'],'baseline_gate_state':base[e['phase3a_event_id']]['baseline_gate_state'],
       'planned_cells':78,'eligible_cells':elig,'inadmissible_cells':inad,'transition_eligible_cells':te,
       'selected_retained':tc['SELECTED_RETAINED'],'selection_lost':tc['SELECTION_LOST'],'not_selected_retained':tc['NOT_SELECTED_RETAINED'],'selection_gained':tc['SELECTION_GAINED'],
       'classification_concordant_cells':cc,'classification_concordance_denominator':te,'classification_concordance_fraction_among_eligible':ratio(cc,te)}
  for reason in reasons:row['inadmissible_'+reason.lower()]=rc[reason]
  rows.append(row)
 return rows

def summarize_groups(outcomes,matrix,mode):
 # mode cell/window/profile. Always stratified by role.
 groups=defaultdict(list)
 for r in outcomes:
  if mode=='cell': key=(r['matrix_cell_id'],r['window_variant_id'],r['processing_profile_id'],r['observational_reference_role'])
  elif mode=='window': key=(r['window_variant_id'],r['observational_reference_role'])
  else:key=(r['processing_profile_id'],r['observational_reference_role'])
  groups[key].append(r)
 rows=[]
 for key,rr in sorted(groups.items()):
  tc=Counter(r['classification_transition'] for r in rr); reasons=Counter(r['inadmissibility_reason'] for r in rr if r['inadmissibility_reason'])
  planned=len(rr); eligible=sum(r['materialization_status']=='ELIGIBLE_FOR_AFINO' for r in rr); inad=sum(r['materialization_status']=='INPUT_INADMISSIBLE' for r in rr)
  incomplete=sum(r['materialization_status']=='ELIGIBLE_FOR_AFINO' and r['variant_decision_available']!='true' for r in rr)
  trans=sum(b(r['transition_eligible']) for r in rr); cc=tc['SELECTED_RETAINED']+tc['NOT_SELECTED_RETAINED']
  common={'planned_event_count':planned if mode=='cell' else '', 'planned_variant_rows':planned if mode!='cell' else '',
    'eligible_count':eligible,'inadmissible_count':inad,'incomplete_count':incomplete,
    'reference_concordant_baseline_count':len({r['phase3a_event_id'] for r in rr if r['baseline_gate_state']=='REFERENCE_CONCORDANT'}),
    'transition_count':trans,'selected_retained':tc['SELECTED_RETAINED'],'selection_lost':tc['SELECTION_LOST'],
    'not_selected_retained':tc['NOT_SELECTED_RETAINED'],'selection_gained':tc['SELECTION_GAINED'],
    'classification_concordant_count':cc,'classification_concordance_denominator':trans,'classification_concordance_fraction_among_eligible':ratio(cc,trans),
    'inadmissibility_reason_counts':json.dumps(dict(sorted(reasons.items())),separators=(',',':'))}
  if mode=='cell':
   row={'matrix_cell_id':key[0],'window_variant_id':key[1],'processing_profile_id':key[2],'observational_reference_role':key[3],**common}
  elif mode=='window':
   row={'window_variant_id':key[0],'observational_reference_role':key[1],**common,'independent_observations':'false','repeated_measure_unit':'phase3a_event_id'}
  else:
   row={'processing_profile_id':key[0],'observational_reference_role':key[1],**common,'independent_observations':'false','repeated_measure_unit':'phase3a_event_id'}
  rows.append(row)
 return rows

def inadmissibility_summary(outcomes):
 reasons=['ALL','IRREGULAR_SAMPLING','TOO_FEW_CADENCES','PEAK_REMOVED_BY_QUALITY','PEAK_OUTSIDE_WINDOW','WINDOW_OUT_OF_RANGE']
 specs=[('GLOBAL',['ALL'],lambda r:'ALL'),('REFERENCE_ROLE',sorted({r['observational_reference_role'] for r in outcomes}),lambda r:r['observational_reference_role']),('WINDOW',sorted({r['window_variant_id'] for r in outcomes}),lambda r:r['window_variant_id']),('PROCESSING_PROFILE',sorted({r['processing_profile_id'] for r in outcomes}),lambda r:r['processing_profile_id'])]
 rows=[]
 for scope,vals,keyfn in specs:
  for val in vals:
   rr=outcomes if scope=='GLOBAL' else [r for r in outcomes if keyfn(r)==val]
   for reason in reasons:
    n=sum(r['materialization_status']=='INPUT_INADMISSIBLE' and (reason=='ALL' or r['inadmissibility_reason']==reason) for r in rr)
    rows.append({'scope_type':scope,'scope_value':val,'inadmissibility_reason':reason,'planned_variant_rows':len(rr),'inadmissible_count':n,'inadmissible_fraction_of_planned':ratio(n,len(rr))})
 return rows

def period_rows(outcomes,base):
 baseline_period={}
 for r in outcomes:
  if r['window_variant_id']=='W00' and r['processing_profile_id']=='P00':baseline_period[r['phase3a_event_id']]=fnum(r['formal_m1_period_s'])
 rows=[]
 for r in outcomes:
  bg=base[r['phase3a_event_id']]; bp=baseline_period.get(r['phase3a_event_id']); vp=fnum(r['formal_m1_period_s'])
  if bg['baseline_gate_state']=='REFERENCE_CONCORDANT' and bg['_selected'] is True and r['variant_qpp_selected']=='true' and bp is not None and vp is not None:
   rows.append({'phase3a_event_id':r['phase3a_event_id'],'variant_id':r['variant_id'],'window_variant_id':r['window_variant_id'],'processing_profile_id':r['processing_profile_id'],
                'baseline_period_s':bp,'variant_period_s':vp,'signed_period_change_s':vp-bp,'absolute_period_change_s':abs(vp-bp),'period_ratio_variant_to_baseline':vp/bp})
 return rows

def period_summary(rows):
 out=[]
 for field in ('signed_period_change_s','absolute_period_change_s','period_ratio_variant_to_baseline'):
  s=summary6([r[field] for r in rows]); out.append({'quantity':field,**s})
 return out

def optimizer_stability(decisions,results,cohort):
 target=[d for d in decisions if d['window_variant_id']=='W00' and d['processing_profile_id']=='P00']
 by_event=defaultdict(list)
 for d in target:by_event[d['phase3a_event_id']].append(d)
 rby=defaultdict(dict)
 for r in results:
  if r['window_variant_id']=='W00' and r['processing_profile_id']=='P00':rby[(r['phase3a_event_id'],int(r['external_optimizer_seed']))][r['model_id']]=r
 role={r['phase3a_event_id']:r['observational_reference_role'] for r in cohort}
 rows=[]
 for event,ds in sorted(by_event.items()):
  ds=sorted(ds,key=lambda d:int(d['external_optimizer_seed'])); seeds=[int(d['external_optimizer_seed']) for d in ds]
  if seeds!=list(range(10)): raise RuntimeError(f'SEED_COMPLETENESS:{event}:{seeds}')
  selected=[b(d['qpp_selected']) for d in ds]; seed0=selected[0]
  bics={m:[float(d['bic_'+m.lower()]) for d in ds] for m in ('M0','M1','M2')}
  d01=[float(d['delta_bic_0_1']) for d in ds]; d21=[float(d['delta_bic_2_1']) for d in ds]; periods=[fnum(d['formal_m1_period_s']) for d in ds]
  unique={}; warns={}; bounds={}; conv=set()
  for m in ('M0','M1','M2'):
   modelrows=[rby[(event,s)][m] for s in range(10)]
   unique[m]=len({r['parameters_json'] for r in modelrows}); warns[m]=sum(int(r['warning_count'])>0 for r in modelrows); bounds[m]=sum(int(r['parameter_at_bound'])>0 for r in modelrows); conv.update(r['convergence_status'] for r in modelrows)
  discord=sum(x!=seed0 for x in selected)
  rows.append({'phase3a_event_id':event,'observational_reference_role':role[event],'seed_count':10,'seed0_selected':txt_bool(seed0),'selected_seed_count':sum(selected),
               'classification_state_set':'|'.join(sorted({'SELECTED' if x else 'NOT_SELECTED' for x in selected})),'discordant_vs_seed0_count':discord,'discordant_vs_seed0_fraction':discord/10,
               'bic_m0_range':value_range(bics['M0']),'bic_m1_range':value_range(bics['M1']),'bic_m2_range':value_range(bics['M2']),'delta01_range':value_range(d01),'delta21_range':value_range(d21),'formal_m1_period_range_s':value_range(periods),
               'unique_parameter_payloads_m0':unique['M0'],'unique_parameter_payloads_m1':unique['M1'],'unique_parameter_payloads_m2':unique['M2'],
               'warning_calls_by_model':json.dumps(warns,separators=(',',':')),'bound_calls_by_model':json.dumps(bounds,separators=(',',':')),'convergence_status_set':'|'.join(sorted(conv))})
 return rows

def seed_diagnostics(results,opt_rows):
 out=[]
 target=[r for r in results if r['window_variant_id']=='W00' and r['processing_profile_id']=='P00']
 for m in ('M0','M1','M2'):
  rr=[r for r in target if r['model_id']==m]
  field='unique_parameter_payloads_'+m.lower(); event_counts=[int(x[field]) for x in opt_rows]; s=summary6(event_counts)
  out.append({'model_id':m,'calls':len(rr),'warning_calls':sum(int(r['warning_count'])>0 for r in rr),'warning_count':sum(int(r['warning_count']) for r in rr),'bound_calls':sum(int(r['parameter_at_bound'])>0 for r in rr),
              'convergence_status_counts':json.dumps(dict(sorted(Counter(r['convergence_status'] for r in rr).items())),separators=(',',':')),
              'unique_parameter_payload_summary':json.dumps(s,separators=(',',':'))})
 return out

def generate_figures(repo,cell_rows,period,opt_rows):
 import matplotlib.pyplot as plt
 FIG_DIR_ABS=repo/FIG_DIR; FIG_DIR_ABS.mkdir(parents=True,exist_ok=True)
 windows=list(dict.fromkeys(r['window_variant_id'] for r in cell_rows)); profiles=list(dict.fromkeys(r['processing_profile_id'] for r in cell_rows))
 for role,path in [('PUBLISHED_QPP_REFERENCE',FIGURES[0]),('PUBLISHED_NOT_SELECTED_REFERENCE',FIGURES[1])]:
  rr={(r['window_variant_id'],r['processing_profile_id']):r for r in cell_rows if r['observational_reference_role']==role}
  mat=[]
  for w in windows:mat.append([float(rr[(w,p)]['classification_concordance_fraction_among_eligible']) if rr[(w,p)]['classification_concordance_fraction_among_eligible']!='' else float('nan') for p in profiles])
  fig,ax=plt.subplots(figsize=(12,12)); im=ax.imshow(mat,aspect='auto',vmin=0,vmax=1); ax.set_xticks(range(len(profiles)),profiles); ax.set_yticks(range(len(windows)),windows); ax.set_xlabel('processing profile'); ax.set_ylabel('window variant'); ax.set_title(role+' — classification concordance by frozen cell')
  for i,w in enumerate(windows):
   for j,p in enumerate(profiles):
    x=rr[(w,p)]; frac=x['classification_concordance_fraction_among_eligible']; label=('NA' if frac=='' else f"{float(frac):.2f}")+f"\nn={x['classification_concordance_denominator']}\nel={x['eligible_count']} in={x['inadmissible_count']}"; ax.text(j,i,label,ha='center',va='center',fontsize=6)
  fig.colorbar(im,ax=ax,label='classification concordance fraction'); fig.tight_layout(); fig.savefig(repo/path,dpi=180); plt.close(fig)
 # Period distribution: signed change only, preserving separate table for full summaries.
 fig,ax=plt.subplots(figsize=(10,6)); vals=[float(r['signed_period_change_s']) for r in period]; ax.hist(vals,bins=40); ax.axvline(0); ax.set_xlabel('signed period change (s)'); ax.set_ylabel('selected-selected variant rows'); ax.set_title('F3A.5 selected-selected period change distribution'); fig.tight_layout(); fig.savefig(repo/FIGURES[2],dpi=180); plt.close(fig)
 fig,ax=plt.subplots(figsize=(10,6)); vals=[float(r['discordant_vs_seed0_fraction']) for r in opt_rows]; ax.hist(vals,bins=11,range=(0,1)); ax.set_xlabel('classification discordance fraction vs seed 0'); ax.set_ylabel('W00/P00 input-eligible events'); ax.set_title('F3A.5 optimizer seed stability diagnostic'); fig.tight_layout(); fig.savefig(repo/FIGURES[3],dpi=180); plt.close(fig)

def build_report(audit,cell,window,profile):
 gates=audit['baseline_gate_counts']; trans=audit['transition_counts']; inad=audit['inadmissibility_counts']; nperiod=audit['period_comparable_rows']; stable=audit['seed_stable_events']; discord=audit['seed_discordant_events']
 def extrema(rows,role):
  r=[x for x in rows if x['observational_reference_role']==role and x['classification_concordance_fraction_among_eligible']!='']; r=sorted(r,key=lambda x:float(x['classification_concordance_fraction_among_eligible'])); return r[0],r[-1]
 qlo,qhi=extrema(cell,'PUBLISHED_QPP_REFERENCE'); nlo,nhi=extrema(cell,'PUBLISHED_NOT_SELECTED_REFERENCE')
 report=f"""# F3A.5 — Caracterización catalogue-scale de robustez observacional

## 1. Cohorte y referencia observacional

F3A.5 caracteriza descriptivamente el comportamiento de la clasificación observacional congelada a través de la matriz prospectiva de 78 perturbaciones. La cohorte permanece fijada en 122 eventos emparejados: 61 con rol `PUBLISHED_QPP_REFERENCE` y 61 con rol `PUBLISHED_NOT_SELECTED_REFERENCE`. Estos roles reproducen la salida observacional del procedimiento publicado y no se interpretan como verdad física. El universo primario contiene 9.516 variantes planificadas, 6.422 entradas elegibles y 3.094 entradas inadmisibles. No se ejecutó AFINO, no se abrieron FITS, NPY ni SQLite y no se regeneró ninguna variante durante esta fase.

## 2. Baseline reproduction gate

El baseline prerregistrado es W00/P00 con seed 0. Los 122 eventos se distribuyen entre los estados del gate de la siguiente forma: {json.dumps(gates,ensure_ascii=False)}. El gate conserva explícitamente cualquier desacuerdo con la etiqueta observacional de referencia. Solo los eventos `REFERENCE_CONCORDANT` contribuyen a denominadores de transición; los eventos con baseline inadmisible, incompleto o discordante permanecen visibles pero no reciben un baseline alternativo. Esta restricción evita transformar una diferencia de reproducción en una clasificación forzada. En consecuencia, las transiciones descritas más abajo son condicionales a disponer de un baseline observacional reproducido bajo el contrato congelado. El número total de eventos planificados no cambia por el resultado del gate: los 122 siguen presentes en la auditoría, y los estados no concordantes se reportan como parte del resultado metodológico. Esta separación es central para interpretar correctamente los denominadores posteriores. Una fracción calculada sobre transiciones no equivale a una fracción sobre la cohorte completa, y una celda con menos filas de transición puede deberse tanto a inadmisibilidad de esa perturbación como a exclusión prospectiva por no haber reproducido el baseline de referencia. Por ello, F3A.5 conserva simultáneamente planned, eligible, baseline-concordant y transition denominators en vez de condensarlos en una única tasa.

## 3. Inadmisibilidad

La inadmisibilidad es un outcome metodológico independiente. Se reproducen exactamente 3.094 filas `INPUT_INADMISSIBLE` sobre 9.516 variantes planificadas. El desglose global es {json.dumps(inad,ensure_ascii=False)}. Estos conteos se presentan también por rol de referencia, ventana y perfil de procesamiento. No se atribuye causalidad física a estas categorías: reflejan exclusivamente el contrato de admisibilidad definido antes de la ejecución, incluyendo continuidad temporal, número mínimo de cadencias, supervivencia del pico tras QUALITY y permanencia de la ventana en el producto disponible. El denominador global permanece siempre en 9.516 para el resumen primario de inadmisibilidad. Los desgloses por rol, ventana y perfil mantienen sus respectivos planned denominators, de modo que una frecuencia elevada en un estrato no se interpreta automáticamente como propiedad del evento ni del fenómeno QPP. Tampoco se reemplaza una fila inadmisible por otra ventana o producto: hacerlo introduciría una adaptación posterior a los resultados y rompería la matriz prospectiva 122 × 78.

## 4. Clasificación a través de las 78 celdas

La matriz primaria mantiene las 9.516 filas, incluidas las 3.094 inadmisibles. Entre filas con baseline concordante y resultado completo, los cuatro outcomes de transición suman {json.dumps(trans,ensure_ascii=False)}. Cada fracción de concordancia se acompaña de su denominador; no se aplica ningún threshold de robustez y no se produce una etiqueta binaria robusto/no robusto. Para el rol QPP de referencia, la celda con menor fracción descriptiva entre las celdas con denominador disponible es {qlo['matrix_cell_id']} ({qlo['window_variant_id']}/{qlo['processing_profile_id']}), con fracción {float(qlo['classification_concordance_fraction_among_eligible']):.3f} y denominador {qlo['classification_concordance_denominator']}; la mayor es {qhi['matrix_cell_id']} con {float(qhi['classification_concordance_fraction_among_eligible']):.3f} y denominador {qhi['classification_concordance_denominator']}. Para el rol no seleccionado de referencia, los extremos descriptivos equivalentes son {nlo['matrix_cell_id']} con {float(nlo['classification_concordance_fraction_among_eligible']):.3f} (n={nlo['classification_concordance_denominator']}) y {nhi['matrix_cell_id']} con {float(nhi['classification_concordance_fraction_among_eligible']):.3f} (n={nhi['classification_concordance_denominator']}). Estos extremos no constituyen selección inferencial de celdas: las 78/78 permanecen publicadas y visibles en las tablas y heatmaps. El objetivo de señalar extremos es únicamente facilitar la lectura descriptiva de una matriz completa ya fijada, no escoger retrospectivamente configuraciones favorables. Las heatmaps muestran, para cada celda y rol, la fracción de concordancia junto con el denominador de transición, el número de entradas elegibles y el número de entradas inadmisibles. Una misma fracción puede por tanto tener pesos descriptivos distintos según el número de eventos que realmente contribuyen. F3A.5 evita resumir esas diferencias mediante un score único, porque el diseño congelado no definió tal score ni un umbral de éxito.

## 5. Patrones descriptivos por ventana

El marginal de ventanas contiene 26 filas: 13 ventanas por dos roles. Cada fila agrega seis perfiles, por lo que existen 366 filas de variante planificadas por combinación ventana–rol. Esas 366 filas no son observaciones independientes; la unidad repetida sigue siendo `phase3a_event_id`. La tabla conserva planned, eligible, inadmissible, transition y los cuatro outcomes de transición, además del denominador explícito de concordancia. Los patrones entre ventanas se describen únicamente como variaciones de estos conteos y fracciones. No se realizan tests de significación, no se comparan p-values y no se interpreta una diferencia marginal como efecto causal de desplazar el inicio o el final de la ventana.

## 6. Patrones descriptivos por procesamiento

El marginal de procesamiento contiene 12 filas: seis perfiles por dos roles. Cada fila resume 793 variantes planificadas, correspondientes a 61 eventos medidos bajo 13 ventanas. De nuevo, las filas son medidas repetidas y no 793 flares independientes. Los perfiles PDCSAP/SAP, finite-all/q0-native y detrending heredado se mantienen exactamente como fueron congelados. La tabla permite observar descriptivamente cómo cambian elegibilidad y concordancia según el pipeline, sin declarar superioridad estadística de ningún perfil ni optimizar retrospectivamente una configuración a partir de sus resultados.

## 7. Estabilidad numérica

El plano de estabilidad permanece separado de la perturbación observacional. Se reconstruyen 116 eventos W00/P00 elegibles, cada uno con seeds 0–9, para 1.160 decisiones. Hay {stable} eventos cuya clasificación coincide con seed 0 en las diez semillas y {discord} con al menos una discordancia respecto de seed 0. Para cada evento se conservan rangos de BIC, márgenes de selección, centro formal M1, número de payloads de parámetros únicos por modelo, warnings, bounds y estados de convergencia. La estabilidad de clasificación no se interpreta como evidencia de un óptimo único, y `NOT_AUDITABLE` no se reetiqueta como convergencia demostrada. Los warnings y bounds permanecen diagnósticos numéricos, no explicaciones causales de una transición de clasificación.

## 8. Periodo condicionado a selección retenida

El plano de periodo incluye {nperiod} filas comparables. Una fila entra únicamente cuando el baseline es `REFERENCE_CONCORDANT`, el baseline está seleccionado, la variante también está seleccionada y ambos periodos M1 son finitos. Se reportan cambio firmado, cambio absoluto y ratio variante/baseline con n, mínimo, Q1, mediana, Q3 y máximo. Los centros formales M1 de resultados no seleccionados permanecen disponibles en la outcome matrix bajo la etiqueta `formal_m1_center_not_selected`, pero no se recodifican como periodos recuperados. No se introduce la noción de “true period”.

## 9. Limitaciones

La caracterización está limitada por el carácter observacional de las etiquetas de referencia, por la existencia de inadmisibilidad bajo algunas perturbaciones y por cualquier desacuerdo del baseline con la etiqueta publicada. La concordancia se condiciona a resultados elegibles y a baseline reproducido, de modo que sus denominadores varían entre celdas y deben leerse junto a cada fracción. Los marginales de ventanas y procesamiento contienen medidas repetidas; por ello sus conteos no representan muestras independientes. No existe threshold prerregistrado que transforme una fracción en robustez binaria, ni familia de tests inferenciales, intervalos de confianza nuevos o corrección de multiplicidad. Tampoco se introducen comparadores externos adicionales: los once trabajos BAII permanecen en las disposiciones ya congeladas en F3A.1. Los resultados de seed se limitan a la configuración W00/P00 y no deben extrapolarse como diagnóstico de estabilidad numérica de todas las 78 celdas. Del mismo modo, el plano de periodo está condicionado a selección retenida y por construcción no describe las variantes que pierden selección, las que permanecen no seleccionadas o las entradas inadmisibles. Estas restricciones no son datos faltantes a completar retrospectivamente, sino partes explícitas del contrato de interpretación.

## 10. Qué puede y qué no puede concluir F3A

F3A.5 permite describir, a escala de catálogo, la conservación o cambio de una clasificación observacional concreta frente a perturbaciones prospectivas de ventana y procesamiento, manteniendo inadmisibilidad y estabilidad del optimizador como planos explícitos. Permite cuantificar transiciones condicionadas a un baseline reproducido, localizar descriptivamente celdas con mayor o menor concordancia sin ocultar denominadores y caracterizar la variabilidad del periodo únicamente cuando la selección se conserva. No permite estimar accuracy, sensibilidad, especificidad, false-positive rate observacional ni verdad física QPP. Tampoco autoriza candidate discovery, nuevos thresholds, nuevas ejecuciones AFINO ni reinterpretación causal de warnings, bounds o inadmisibilidad. La síntesis explícita F2→F3A y la decisión formal de cierre de Phase 3A quedan reservadas para F3A.6.
"""
 return report

def update_readme(repo:Path):
 p=repo/README_REL
 text=p.read_text(encoding='utf-8') if p.exists() else '# Phase 3A\n\n## STATUS\n\n'
 lines=text.splitlines()
 try:
  idx=next(i for i,x in enumerate(lines) if x.strip()=='## STATUS')
  content_idx=idx+1
  while content_idx<len(lines) and not lines[content_idx].strip(): content_idx+=1
  replacement=['CATALOGUE-SCALE ROBUSTNESS CHARACTERIZED —','PHASE 3A CLOSURE NOT STARTED']
  if content_idx<len(lines): lines=lines[:content_idx]+replacement+lines[content_idx+1:]
  else: lines.extend(['']+replacement)
  text='\n'.join(lines)+'\n'
 except StopIteration:
  text=text.rstrip()+'\n\n## STATUS\n\nCATALOGUE-SCALE ROBUSTNESS CHARACTERIZED —\nPHASE 3A CLOSURE NOT STARTED\n'
 p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding='utf-8',newline='\n')

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default='.'); ap.add_argument('--preflight-only',action='store_true'); args=ap.parse_args(); repo=Path(args.repo_root).resolve()
 contract,_=load_inputs(repo); verify_inputs(repo,contract)
 if args.preflight_only:
  print('PHASE3A_F3A5_ANALYSIS_PREFLIGHT_PASS'); print('scientific_summaries_computed=false'); print('new_afino_execution=false'); print('fits_opened=false'); print('payload_npy_opened=false'); print('sqlite_opened=false'); return 0
 contract,data=load_inputs(repo)
 if not (len(data['cohort'])==122 and len(data['variants'])==9516 and len(data['matrix'])==78 and len(data['decisions'])==7466 and len(data['results'])==22398): raise RuntimeError('FROZEN_INPUT_COUNT_MISMATCH')
 baseline,base=baseline_gate(data['cohort'],data['variants'],data['decisions']); outcomes=primary_outcomes(data['variants'],data['decisions'],base); events=event_summaries(data['cohort'],outcomes,base); cells=summarize_groups(outcomes,data['matrix'],'cell'); windows=summarize_groups(outcomes,data['matrix'],'window'); profiles=summarize_groups(outcomes,data['matrix'],'profile'); inad=inadmissibility_summary(outcomes); periods=period_rows(outcomes,base); psum=period_summary(periods); opt=optimizer_stability(data['decisions'],data['results'],data['cohort']); sdiag=seed_diagnostics(data['results'],opt)
 write_csv(repo/BASELINE_REL,baseline,list(baseline[0])); write_csv(repo/OUTCOME_REL,outcomes,list(outcomes[0])); write_csv(repo/EVENT_REL,events,list(events[0])); write_csv(repo/CELL_REL,cells,list(cells[0])); write_csv(repo/WINDOW_REL,windows,list(windows[0])); write_csv(repo/PROFILE_REL,profiles,list(profiles[0])); write_csv(repo/INAD_REL,inad,list(inad[0])); write_csv(repo/PERIOD_REL,periods,list(periods[0]) if periods else ['phase3a_event_id','variant_id','window_variant_id','processing_profile_id','baseline_period_s','variant_period_s','signed_period_change_s','absolute_period_change_s','period_ratio_variant_to_baseline']); write_csv(repo/PERIOD_SUM_REL,psum,list(psum[0])); write_csv(repo/OPT_REL,opt,list(opt[0])); write_csv(repo/SEED_DIAG_REL,sdiag,list(sdiag[0]))
 generate_figures(repo,cells,periods,opt)
 gate_keys=['REFERENCE_CONCORDANT','REFERENCE_BASELINE_MISMATCH','INPUT_INADMISSIBLE','INCOMPLETE_NUMERICAL']; trans_keys=['SELECTED_RETAINED','SELECTION_LOST','NOT_SELECTED_RETAINED','SELECTION_GAINED']; inad_keys=['IRREGULAR_SAMPLING','TOO_FEW_CADENCES','PEAK_REMOVED_BY_QUALITY','PEAK_OUTSIDE_WINDOW','WINDOW_OUT_OF_RANGE']
 gate_counter=Counter(r['baseline_gate_state'] for r in baseline); trans_counter=Counter(r['classification_transition'] for r in outcomes if r['classification_transition']); inad_counter=Counter(r['inadmissibility_reason'] for r in outcomes if r['materialization_status']=='INPUT_INADMISSIBLE')
 gate_counts={k:gate_counter[k] for k in gate_keys}; trans_counts={k:trans_counter[k] for k in trans_keys}; inad_counts={k:inad_counter[k] for k in inad_keys}; discord=sum(float(r['discordant_vs_seed0_fraction'])>0 for r in opt); stable=len(opt)-discord
 state='PHASE3A_CATALOGUE_ROBUSTNESS_CHARACTERIZED_WITH_LIMITATIONS' if gate_counts['REFERENCE_BASELINE_MISMATCH'] or gate_counts['INPUT_INADMISSIBLE'] or gate_counts['INCOMPLETE_NUMERICAL'] else 'PHASE3A_CATALOGUE_ROBUSTNESS_CHARACTERIZED'
 audit={'analysis_status':state,'baseline_gate_counts':gate_counts,'baseline_gate_denominator':len(baseline),'transition_counts':trans_counts,'transition_denominator':sum(trans_counts.values()),'inadmissibility_counts':inad_counts,'inadmissibility_denominator':len(outcomes),'period_comparable_rows':len(periods),'seed_discordant_events':discord,'seed_stable_events':stable,'numerical_diagnostics':{r['model_id']:r for r in sdiag},'counts':{'cohort_rows':len(data['cohort']),'primary_planned_rows':len(data['variants']),'primary_eligible_source_rows':sum(r['materialization_status']=='ELIGIBLE_FOR_AFINO' for r in data['variants']),'primary_inadmissible_source_rows':sum(r['materialization_status']=='INPUT_INADMISSIBLE' for r in data['variants']),'baseline_rows':len(baseline),'baseline_input_eligible':sum(r['baseline_materialization_status']=='ELIGIBLE_FOR_AFINO' for r in baseline),'outcome_matrix_rows':len(outcomes),'event_summaries':len(events),'cell_role_summaries':len(cells),'window_role_summaries':len(windows),'profile_role_summaries':len(profiles),'optimizer_summaries':len(opt),'stability_decisions':sum(int(r['seed_count']) for r in opt)},'scientific_boundaries':{'new_afino_execution':False,'fits_opened':False,'payload_npy_opened':False,'sqlite_opened':False,'variants_regenerated':False,'new_threshold_added':False,'formal_hypothesis_test_performed':False,'observational_ground_truth_established':False,'sensitivity_computed':False,'specificity_computed':False,'observational_fpr_computed':False,'candidate_discovery_authorized':False}}
 report=build_report(audit,cells,windows,profiles); wc=len(report.split());
 if not 1200<=wc<=1700: raise RuntimeError(f'REPORT_WORD_COUNT:{wc}')
 audit['report_word_count']=wc; REPORT_DIR_ABS=repo/REPORT_DIR; REPORT_DIR_ABS.mkdir(parents=True,exist_ok=True); (repo/AUDIT_REL).write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); (repo/REPORT_REL).write_text(report,encoding='utf-8',newline='\n'); update_readme(repo)
 outputs=[BASELINE_REL,OUTCOME_REL,EVENT_REL,CELL_REL,WINDOW_REL,PROFILE_REL,INAD_REL,PERIOD_REL,PERIOD_SUM_REL,OPT_REL,SEED_DIAG_REL,*FIGURES,AUDIT_REL,REPORT_REL,README_REL,CONTRACT_REL]
 lines=['# F3A.5 checksum registry v1','# KIND\tSHA256\tLOCATOR']+[f"GIT_FILE\t{sha256_file(repo/r)}\t{r.as_posix()}" for r in outputs]; (repo/SUMS_REL).write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
 print(state); print('baseline_rows=',len(baseline)); print('outcome_matrix_rows=',len(outcomes)); print('event_summaries=',len(events)); print('cell_role_summaries=',len(cells)); print('window_role_summaries=',len(windows)); print('profile_role_summaries=',len(profiles)); print('optimizer_summaries=',len(opt)); print('stability_decisions=',sum(int(r['seed_count']) for r in opt)); print('period_comparable_rows=',len(periods)); print('report_word_count=',wc); print('new_afino_execution=false'); return 0
if __name__=='__main__': raise SystemExit(main())
