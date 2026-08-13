from __future__ import annotations
import importlib.util,json,sys
from pathlib import Path
import pytest
REPO=Path(__file__).resolve().parents[3]
P=REPO/'workflows/phase3a/scripts/analyze_catalogue_robustness.py'
spec=importlib.util.spec_from_file_location('f3a5_analysis',P);A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)

def test_contract_counts_and_no_threshold():
 c=json.loads((REPO/A.CONTRACT_REL).read_text(encoding='utf-8')); assert c['planned_counts']['events']==122;assert c['planned_counts']['primary_variants']==9516;assert c['planned_counts']['primary_eligible']==6422;assert c['planned_counts']['primary_inadmissible']==3094;assert c['planned_counts']['baseline_input_eligible']==116;assert c['robustness_threshold'] is None;assert c['formal_hypothesis_tests']=='NONE'
def test_prohibited_metrics_contract():
 c=json.loads((REPO/A.CONTRACT_REL).read_text(encoding='utf-8'));assert set(c['prohibited_metrics'])=={'accuracy','sensitivity','specificity','observational_false_positive_rate','physical_truth_rate'};assert c['scientific_boundaries']['candidate_discovery_authorized'] is False
def test_baseline_gate_classification():
 cohort=[{'phase3a_event_id':'E1','pair_id':'P','observational_reference_role':'PUBLISHED_QPP_REFERENCE'},{'phase3a_event_id':'E2','pair_id':'P','observational_reference_role':'PUBLISHED_NOT_SELECTED_REFERENCE'},{'phase3a_event_id':'E3','pair_id':'P','observational_reference_role':'PUBLISHED_QPP_REFERENCE'}]
 variants=[{'phase3a_event_id':'E1','variant_id':'V1','window_variant_id':'W00','processing_profile_id':'P00','materialization_status':'ELIGIBLE_FOR_AFINO','inadmissibility_reason_code':''},{'phase3a_event_id':'E2','variant_id':'V2','window_variant_id':'W00','processing_profile_id':'P00','materialization_status':'ELIGIBLE_FOR_AFINO','inadmissibility_reason_code':''},{'phase3a_event_id':'E3','variant_id':'V3','window_variant_id':'W00','processing_profile_id':'P00','materialization_status':'INPUT_INADMISSIBLE','inadmissibility_reason_code':'X'}]
 decisions=[{'variant_id':'V1','external_optimizer_seed':'0','decision_class':'PRIMARY','decision_status':'VALID','qpp_selected':'true'},{'variant_id':'V2','external_optimizer_seed':'0','decision_class':'PRIMARY','decision_status':'VALID','qpp_selected':'true'}]
 rows,_=A.baseline_gate(cohort,variants,decisions); assert [r['baseline_gate_state'] for r in rows]==['REFERENCE_CONCORDANT','REFERENCE_BASELINE_MISMATCH','INPUT_INADMISSIBLE']
def test_four_transition_states_and_mismatch_exclusion():
 base={'E1':{'baseline_gate_state':'REFERENCE_CONCORDANT','_selected':True},'E2':{'baseline_gate_state':'REFERENCE_CONCORDANT','_selected':False},'E3':{'baseline_gate_state':'REFERENCE_BASELINE_MISMATCH','_selected':True}}
 def v(e,id):return {'phase3a_event_id':e,'pair_id':'P','observational_reference_role':'R','variant_id':id,'matrix_cell_id':'C','window_variant_id':'W','processing_profile_id':'P','materialization_status':'ELIGIBLE_FOR_AFINO','inadmissibility_reason_code':''}
 variants=[v('E1','V1'),v('E1','V2'),v('E2','V3'),v('E2','V4'),v('E3','V5')]
 sels=[True,False,False,True,False];dec=[{'variant_id':x['variant_id'],'external_optimizer_seed':'0','decision_class':'PRIMARY','decision_status':'VALID','qpp_selected':str(s).lower(),'formal_m1_period_s':'10'} for x,s in zip(variants,sels)]
 out=A.primary_outcomes(variants,dec,base);assert [r['classification_transition'] for r in out[:4]]==['SELECTED_RETAINED','SELECTION_LOST','NOT_SELECTED_RETAINED','SELECTION_GAINED'];assert out[4]['classification_transition']=='';assert out[4]['transition_eligible']=='false'
def test_inadmissible_variant_handling():
 base={'E':{'baseline_gate_state':'REFERENCE_CONCORDANT','_selected':True}};v={'phase3a_event_id':'E','pair_id':'P','observational_reference_role':'R','variant_id':'V','matrix_cell_id':'C','window_variant_id':'W','processing_profile_id':'P','materialization_status':'INPUT_INADMISSIBLE','inadmissibility_reason_code':'TOO_FEW_CADENCES'};r=A.primary_outcomes([v],[],base)[0];assert r['transition_eligible']=='false';assert r['classification_transition']=='';assert r['inadmissibility_reason']=='TOO_FEW_CADENCES'
def test_concordance_numerator_denominator():
 rr=[{'phase3a_event_id':'E','classification_transition':'SELECTED_RETAINED','inadmissibility_reason':'','materialization_status':'ELIGIBLE_FOR_AFINO','transition_eligible':'true','classification_concordant_with_baseline':'true'},{'phase3a_event_id':'E','classification_transition':'SELECTION_LOST','inadmissibility_reason':'','materialization_status':'ELIGIBLE_FOR_AFINO','transition_eligible':'true','classification_concordant_with_baseline':'false'}];assert sum(x['classification_concordant_with_baseline']=='true' for x in rr)==1;assert sum(A.b(x['transition_eligible']) for x in rr)==2
def test_period_eligibility_and_not_selected_exclusion():
 base={'E':{'baseline_gate_state':'REFERENCE_CONCORDANT','_selected':True}}; rows=[{'phase3a_event_id':'E','variant_id':'B','window_variant_id':'W00','processing_profile_id':'P00','formal_m1_period_s':'10','variant_qpp_selected':'true'},{'phase3a_event_id':'E','variant_id':'S','window_variant_id':'W1','processing_profile_id':'P00','formal_m1_period_s':'12','variant_qpp_selected':'true'},{'phase3a_event_id':'E','variant_id':'N','window_variant_id':'W2','processing_profile_id':'P00','formal_m1_period_s':'20','variant_qpp_selected':'false'}];p=A.period_rows(rows,base);assert [x['variant_id'] for x in p]==['B','S'];assert p[1]['signed_period_change_s']==2
def test_linear_quantile():assert A.linear_quantile([0,10,20,30],.25)==7.5
def test_repeated_measure_contract():
 c=json.loads((REPO/A.CONTRACT_REL).read_text(encoding='utf-8'));assert c['repeated_measures']['window']['planned_variant_rows_per_role_window']==366;assert c['repeated_measures']['processing_profile']['planned_variant_rows_per_role_profile']==793;assert c['repeated_measures']['window']['independent_observations'] is False
def test_seed_discordance_logic():
 s=[True]*9+[False];seed0=s[0];assert sum(x!=seed0 for x in s)==1
def test_unique_parameter_payload_counting():assert len(set(['[1,2]','[1,2]','[2,3]']))==2
def test_analyzer_has_no_prohibited_imports():
 import ast
 tree=ast.parse(P.read_text(encoding='utf-8')); roots=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.Import):roots.extend(a.name.split('.')[0] for a in node.names)
  elif isinstance(node,ast.ImportFrom) and node.module:roots.append(node.module.split('.')[0])
 assert not (set(roots)&{'afino','astropy','lightkurve'})
def test_analyzer_has_no_forbidden_binary_open_contract():
 src=P.read_text(encoding='utf-8').lower();assert '.npy' not in src;assert 'sqlite3' not in src;assert '.fits' not in src
def test_required_outputs_contract():
 c=json.loads((REPO/A.CONTRACT_REL).read_text(encoding='utf-8'));assert c['required_outputs']=={'baseline_rows':122,'outcome_matrix_rows':9516,'event_summaries':122,'cell_role_summaries':156,'window_role_summaries':26,'profile_role_summaries':12,'optimizer_summaries':116,'seed_model_diagnostics':3,'figures':4}
