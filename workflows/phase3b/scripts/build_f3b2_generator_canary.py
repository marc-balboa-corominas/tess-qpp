#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, math, py_compile, subprocess, tempfile
from pathlib import Path
import numpy as np

EXPECTED_HEAD='467abe9d5fc8379e342f7c98d735aae12ad56ea1'
F3B1_COMMIT='b8680934644be1bfec196e2009311b3060968f0a'
F3B1_TAG='phase3b-design-v1'
BOUND_PYTHON_MAJOR_MINOR=(3,13)
BOUND_NUMPY_VERSION='2.3.5'
BOUND_BYTEORDER='little'
ABS_TOL=5e-12
EXPECTED={
 'workflows/phase3b/development/config/f3b2_generator_implementation_binding.json':'b6519f84c0e6aa6b0c86cbd7a66dd79c1de1758e313d96ea4d750ebb212d9946',
 'workflows/phase3b/scripts/f3b_synthetic_generator.py':'d538d53c7845916e29c4dd351b85ae91076d5a342acb5619898788ef5d825d11',
 'workflows/phase3b/tests/test_f3b2_generator_and_materialization.py':'0f9c71fa0b16a604c4dcaa125606006d998ff53964c525c3d4b342c06fe6600c',
 'workflows/phase3b/design/f3b1_split_registry.csv':'2316e09ba061910d360ba0d11aa4a766a3b657f56182bb6ba1c455d2b8120c93',
 'workflows/phase3b/design/f3b1_numerical_stability_protocol.json':'cee38e35aa2c6fcab0f6d3022744f9c10cbd27532657303b72c8fcd1a83a8a16',
 'foundation/f0-f2/phase1/fase1_tarea02_synthetic_generator.py':'743005e580f20be331408d9165522932a289d256cef0efbe4c4f24fcb38c54bd',
 'foundation/f0-f2/phase1/fase1_tarea02_generator_validation_audit.json':'3e4d588110dbe535038dc0e85ec08a60e47de946d438c05b121b379ee0c02f11',
 'foundation/f0-f2/phase1/fase1_tarea01_core_benchmark_preregistration.json':'dd80346172290e014d73f78240b3e31f135bcc7e4f075963e7e20d8456de3401',
}
REPO_SCRIPT=Path('workflows/phase3b/scripts/build_f3b2_generator_canary.py')
MANIFEST=Path('workflows/phase3b/development/evidence/tables/f3b2_generator_canary_manifest.csv')
AUDIT=Path('workflows/phase3b/development/evidence/reports/f3b2_generator_validation_audit.json')
GEN=Path('workflows/phase3b/scripts/f3b_synthetic_generator.py')
SPLIT=Path('workflows/phase3b/design/f3b1_split_registry.csv')
NUM=Path('workflows/phase3b/design/f3b1_numerical_stability_protocol.json')
F1GEN=Path('foundation/f0-f2/phase1/fase1_tarea02_synthetic_generator.py')
F1AUD=Path('foundation/f0-f2/phase1/fase1_tarea02_generator_validation_audit.json')
F1PRE=Path('foundation/f0-f2/phase1/fase1_tarea01_core_benchmark_preregistration.json')
F1_CASES=[(15,0.0,0),(15,2.0,39),(30,1.0,17),(60,0.0,39),(120,2.0,0)]

def run(repo,*args,check=True):
    cp=subprocess.run(['git','-C',str(repo),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if check and cp.returncode: raise RuntimeError('git '+' '.join(args)+' failed: '+cp.stderr.decode(errors='replace').strip())
    return cp

def gt(repo,*args): return run(repo,*args).stdout.decode('utf-8',errors='replace').strip()
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()
def shab(b): return hashlib.sha256(b).hexdigest()
def load(path,name):
    s=importlib.util.spec_from_file_location(name,path)
    if s is None or s.loader is None: raise RuntimeError(f'Cannot import {path}')
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def rows(path):
    with path.open('r',encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def close(a,b,msg):
    a=np.asarray(a); b=np.asarray(b)
    if a.shape!=b.shape or not np.allclose(a,b,rtol=0,atol=ABS_TOL):
        d=float(np.max(np.abs(a-b))) if a.shape==b.shape else float('inf')
        raise RuntimeError(f'{msg}: max_abs_delta={d}')
def alpha_code(spec,a):
    m=spec['generator']['noise']['alpha_code']
    for k in [str(float(a)),format(float(a),'.1f'),str(a)]:
        if k in m: return int(m[k])
    raise RuntimeError('Missing alpha code')

def f1_check(repo,f3b):
    f1=load(repo/F1GEN,'f1_ref'); spec=json.loads((repo/F1PRE).read_text(encoding='utf-8'))
    aud=json.loads((repo/F1AUD).read_text(encoding='utf-8'))
    frozen={(int(c['n_samples']),float(c['red_noise_alpha']),int(c['data_seed'])) for c in aud['independent_reference']['cases']}
    if not set(F1_CASES).issubset(frozen): raise RuntimeError('Frozen F1 cases missing')
    detail=[]
    for n,a,s in F1_CASES:
        r=f1.generate_paired_block(n,a,s,spec)
        c=f3b.f1_compatible_block(n,a,s,master_seed=int(spec['rng_and_pairing']['master_seed']),alpha_code=alpha_code(spec,a))
        close(c['time_s'],r['time_s'],'F1 time'); close(c['flare_envelope'],r['flare_envelope'],'F1 flare'); close(c['noise'],r['noise'],'F1 noise')
        if not math.isclose(float(c['phase_rad']),float(r['phase_rad']),rel_tol=0,abs_tol=ABS_TOL): raise RuntimeError('F1 phase mismatch')
        cn=f3b.materialize_null_latent(c); rn=f1.materialize_null(r,spec); close(cn,rn,'F1 null')
        cp,cc=f3b.f1_compatible_positive(c,50.0,0.02); rp=f1.materialize_positive(r,50.0,0.02,spec)
        close(cp,rp,'F1 positive'); close(cp-cn,cc,'F1 component')
        detail.append({'n_samples':n,'red_noise_alpha':a,'data_seed':s,'status':'PASS'})
    return {'status':'F3B2_F1_GENERATOR_CONTINUITY_PASS','abs_tol':ABS_TOL,'rel_tol':0.0,'reference_cases':detail}

def validate_block(b,r):
    n=int(b['n_samples']); t=np.arange(n,dtype=np.float64)*20.0
    if not np.array_equal(b['time_s'],t): raise RuntimeError('time grid mismatch')
    dur=float(b['duration_s']); peak=int(round(0.20*(n-1)))
    if int(b['peak_index'])!=peak: raise RuntimeError('peak mismatch')
    tp=t[peak]; exp=np.where(t<=tp,0.5*np.exp((t-tp)/(0.04*dur)),0.5*np.exp(-(t-tp)/(0.30*dur)))
    close(b['flare_envelope'],exp,'flare envelope')
    noise=np.asarray(b['noise'],dtype=np.float64)
    if not np.all(np.isfinite(noise)): raise RuntimeError('nonfinite noise')
    mean=float(np.mean(noise)); std=float(np.std(noise,ddof=1))
    if abs(mean)>ABS_TOL or abs(std-0.005)>ABS_TOL: raise RuntimeError(f'noise normalization mean={mean} std={std}')
    if int(b.get('redraw_count',-1))!=0: raise RuntimeError('redraw detected')
    if not np.array_equal(b['noise'],r['noise']) or float(b['phase_rad'])!=float(r['phase_rad']): raise RuntimeError('background/phase reconstruction mismatch')
    if not 0.0<=float(b['phase_rad'])<2*np.pi: raise RuntimeError('phase range')
    return mean,std

def period(bg,dur,f3b):
    a=f3b.draw_true_period(bg,dur); b=f3b.draw_true_period(bg,dur)
    if float(a['true_period_s'])!=float(b['true_period_s']) or int(a['period_entropy'])!=int(b['period_entropy']): raise RuntimeError('period reconstruction mismatch')
    if not 40.0<=float(a['true_period_s'])<=300.0 or float(a['cycles_in_window'])<3.0: raise RuntimeError('period support/cycles')
    return a

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default='.'); args=ap.parse_args(); repo=Path(args.repo_root).resolve()
    if gt(repo,'rev-parse','HEAD')!=EXPECTED_HEAD: raise RuntimeError('Canary must run from committed pre-draw binding')
    if gt(repo,'rev-parse',F3B1_TAG+'^{}')!=F3B1_COMMIT: raise RuntimeError('F3B.1 tag mismatch')
    import sys
    if sys.version_info[:2]!=BOUND_PYTHON_MAJOR_MINOR: raise RuntimeError(f'Python binding mismatch: {sys.version_info[:2]} != {BOUND_PYTHON_MAJOR_MINOR}')
    if np.__version__!=BOUND_NUMPY_VERSION: raise RuntimeError(f'NumPy binding mismatch: {np.__version__} != {BOUND_NUMPY_VERSION}')
    if sys.byteorder!=BOUND_BYTEORDER: raise RuntimeError(f'Byteorder binding mismatch: {sys.byteorder} != {BOUND_BYTEORDER}')
    if gt(repo,'status','--short'): raise RuntimeError('Working tree must be clean before first F3B canary draw')
    for rel,h in EXPECTED.items():
        p=repo/rel
        if not p.is_file() or sha(p)!=h: raise RuntimeError('Frozen input SHA mismatch: '+rel)
    if (repo/'data/interim/phase3b/f3b2_development').exists(): raise RuntimeError('Full DEVELOPMENT materialization already exists')
    if (repo/'data/interim/phase3b/heldout').exists(): raise RuntimeError('HELDOUT materialization directory exists')
    guard=repo/'workflows/phase3b/heldout/README.md'; tg=run(repo,'show',F3B1_TAG+':workflows/phase3b/heldout/README.md').stdout
    if guard.read_bytes()!=tg: raise RuntimeError('HELDOUT guard changed')
    rp=repo/REPO_SCRIPT
    if rp.exists() or (repo/MANIFEST).exists() or (repo/AUDIT).exists(): raise RuntimeError('Canary artifact already exists; refusing overwrite')
    rp.parent.mkdir(parents=True,exist_ok=True); rp.write_bytes(Path(__file__).read_bytes()); py_compile.compile(str(rp),cfile=str(Path(tempfile.gettempdir())/'f3b2_canary.pyc'),doraise=True)
    f3b=load(repo/GEN,'f3b_canary'); continuity=f1_check(repo,f3b)
    sr=rows(repo/SPLIT); dev=[r for r in sr if r['split']=='DEVELOPMENT']; held=[r for r in sr if r['split']=='HELDOUT']
    if (len(dev),len(held))!=(4320,4320): raise RuntimeError('split row count')
    db={r['background_realization_id'] for r in dev}; hb={r['background_realization_id'] for r in held}
    if len(db)!=1800 or len(hb)!=1800 or db&hb: raise RuntimeError('background split failure')
    bybg={}
    for r in dev: bybg.setdefault(r['background_realization_id'],[]).append(r)
    num=json.loads((repo/NUM).read_text(encoding='utf-8')); sel=num['selected_backgrounds']; prim=[x['background_realization_id'] for x in sel]
    if len(prim)!=36 or len(set(prim))!=36 or any(x not in db for x in prim): raise RuntimeError('primary canary background selection')
    cc={}
    for r in dev:
        if r['gap_quality_regime']!='CONTIGUOUS_ALL_GOOD': cc.setdefault(int(r['n_samples']),{}).setdefault(r['background_realization_id'],r)
    ch=[]
    for n in [15,30,60,120]:
        c=list(cc.get(n,{}).values())
        if not c: raise RuntimeError(f'no challenge candidate n={n}')
        ch.append(min(c,key=lambda r:r['challenge_rank_sha256'])['background_realization_id'])
    calls=[]; pcalls=[]; blocks={}; periods={}; manifest=[]
    def block(bg,row,reconstruct=False):
        if bg not in db or bg in hb: raise RuntimeError('non-DEVELOPMENT RNG call')
        if reconstruct:
            calls.append(bg); return f3b.generate_background_realization(bg,int(row['n_samples']),float(row['red_noise_alpha']))
        if bg not in blocks:
            calls.append(bg); blocks[bg]=f3b.generate_background_realization(bg,int(row['n_samples']),float(row['red_noise_alpha']))
        return blocks[bg]
    def per(bg,b):
        if bg not in periods:
            pcalls.append(bg); periods[bg]=period(bg,float(b['duration_s']),f3b)
        return periods[bg]
    def add(kind,basis,row,b,latent,ret,mean,std,p=None,comp=None):
        manifest.append({
         'canary_class':kind,'selection_basis':basis,'simulation_unit_id':row['simulation_unit_id'],'background_realization_id':row['background_realization_id'],'split':row['split'],'truth_state':row['truth_state'],'gap_quality_regime':row['gap_quality_regime'],'n_samples':int(row['n_samples']),'duration_s':float(row['duration_s']),'red_noise_alpha':float(row['red_noise_alpha']),'qpp_fraction':float(row['positive_pair_qpp_fraction']) if p is not None else '','true_period_s':float(p['true_period_s']) if p is not None else '','cycles_in_window':float(p['cycles_in_window']) if p is not None else '','qpp_phase_rad':float(b['phase_rad']),'peak_index':int(b['peak_index']),'redraw_count':int(b['redraw_count']),'noise_mean':mean,'noise_std_ddof1':std,'time_sha256':f3b.canonical_float64_sha256(b['time_s']),'flare_envelope_sha256':f3b.canonical_float64_sha256(b['flare_envelope']),'background_noise_sha256':f3b.canonical_float64_sha256(b['noise']),'latent_flux_sha256':f3b.canonical_float64_sha256(latent),'qpp_component_sha256':f3b.canonical_float64_sha256(comp) if comp is not None else '','retain_mask_sha256':f3b.canonical_bool_sha256(ret['retain_mask']),'retained_time_sha256':f3b.canonical_float64_sha256(ret['retained_time_s']),'retained_flux_sha256':f3b.canonical_float64_sha256(ret['retained_flux']),'retained_native_index_sha256':f3b.canonical_int64_sha256(ret['retained_native_index']),'logical_payload_sha256':f3b.logical_payload_sha256(row['simulation_unit_id'],ret['retained_time_s'],ret['retained_flux'],ret['retained_native_index']),'validation_status':'PASS'})
    for item in sel:
        bg=item['background_realization_id']; rr=[r for r in bybg[bg] if r['gap_quality_regime']=='CONTIGUOUS_ALL_GOOD']
        if len(rr)!=2 or {r['truth_state'] for r in rr}!={'SYNTHETIC_QPP_PRESENT','SYNTHETIC_QPP_ABSENT'}: raise RuntimeError('primary pair')
        b=block(bg,rr[0]); mean,std=validate_block(b,block(bg,rr[0],True)); nr=next(r for r in rr if r['truth_state']=='SYNTHETIC_QPP_ABSENT'); pr=next(r for r in rr if r['truth_state']=='SYNTHETIC_QPP_PRESENT')
        nl=f3b.materialize_null_latent(b); p=per(bg,b); pl,comp=f3b.materialize_positive_latent(b,float(p['true_period_s']),float(pr['positive_pair_qpp_fraction'])); close(pl-nl,comp,'positive-null component')
        add('PRIMARY','f3b1_numerical_stability_protocol.selected_backgrounds',nr,b,nl,f3b.apply_retain_mask(b,nl,'CONTIGUOUS_ALL_GOOD'),mean,std)
        add('PRIMARY','f3b1_numerical_stability_protocol.selected_backgrounds',pr,b,pl,f3b.apply_retain_mask(b,pl,'CONTIGUOUS_ALL_GOOD'),mean,std,p,comp)
    for bg in ch:
        rr=[r for r in bybg[bg] if r['gap_quality_regime']!='CONTIGUOUS_ALL_GOOD']
        if len(rr)!=4: raise RuntimeError('challenge row count')
        b=block(bg,rr[0]); mean,std=validate_block(b,block(bg,rr[0],True)); nl=f3b.materialize_null_latent(b); pr=next(r for r in rr if r['truth_state']=='SYNTHETIC_QPP_PRESENT'); p=per(bg,b); pl,comp=f3b.materialize_positive_latent(b,float(p['true_period_s']),float(pr['positive_pair_qpp_fraction'])); close(pl-nl,comp,'challenge positive-null component')
        for r in sorted(rr,key=lambda x:(x['gap_quality_regime'],x['truth_state'])):
            pos=r['truth_state']=='SYNTHETIC_QPP_PRESENT'; latent=pl if pos else nl; before=f3b.canonical_float64_sha256(latent); ret=f3b.apply_retain_mask(b,latent,r['gap_quality_regime']); after=f3b.canonical_float64_sha256(latent)
            if before!=after: raise RuntimeError('challenge mutated latent flux')
            false=np.flatnonzero(~ret['retain_mask']); expected=int(b['peak_index'])+1 if r['gap_quality_regime']=='ONE_INTERNAL_NONPEAK_SAMPLE_MASKED' else int(b['peak_index'])
            if len(false)!=1 or int(false[0])!=expected: raise RuntimeError('challenge mask index')
            add('CHALLENGE','minimum challenge_rank_sha256 per n_samples',r,b,latent,ret,mean,std,p if pos else None,comp if pos else None)
    if len(manifest)!=88 or sum(r['canary_class']=='PRIMARY' for r in manifest)!=72 or sum(r['canary_class']=='CHALLENGE' for r in manifest)!=16 or len({r['simulation_unit_id'] for r in manifest})!=88: raise RuntimeError('canary counts/duplicates')
    if any(x in hb for x in calls) or any(x in hb for x in pcalls): raise RuntimeError('HELDOUT stochastic call detected')
    fields=list(manifest[0].keys()); sio=io.StringIO(newline=''); w=csv.DictWriter(sio,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(manifest); mb=sio.getvalue().encode('utf-8'); mp=repo/MANIFEST; mp.parent.mkdir(parents=True,exist_ok=True); mp.write_bytes(mb)
    audit={'schema_version':1,'phase':'F3B.2','artifact_role':'GENERATOR_CANARY_VALIDATION_AUDIT','status':'F3B2_GENERATOR_CANARY_PASS','f3b1_design_tag':F3B1_TAG,'f3b1_design_commit':F3B1_COMMIT,'f3b2_implementation_binding_commit':EXPECTED_HEAD,'execution_environment':{'python_version':sys.version.split()[0],'python_major_minor':list(sys.version_info[:2]),'numpy_version':np.__version__,'byteorder':sys.byteorder},'generator_sha256':EXPECTED['workflows/phase3b/scripts/f3b_synthetic_generator.py'],'f1_generator_continuity_status':continuity['status'],'f1_generator_continuity':continuity,'canary':{'primary_backgrounds':36,'primary_series':72,'challenge_backgrounds':4,'challenge_series':16,'total_series':88,'primary_selection':'exact 36 F3B.1 numerical-stability backgrounds','challenge_selection':'one DEVELOPMENT challenge background per n_samples using minimum challenge_rank_sha256'},'validations':{'time_grid_exact':True,'flare_peak_and_two_branch_envelope':True,'red_noise_finite':True,'red_noise_mean_abs_tol_5e_12':True,'red_noise_sample_std_0_005_abs_tol_5e_12':True,'redraw_count_zero':True,'null_positive_shared_background_exact':True,'positive_minus_null_equals_qpp_component_abs_tol_5e_12':True,'period_support_40_300_s':True,'minimum_cycles_ge_3':True,'period_reconstruction_exact':True,'phase_range_0_2pi':True,'phase_reconstruction_exact':True,'challenge_only_changes_retained_input':True,'latent_flux_invariant_under_challenge_mask':True},'heldout_nonmaterialization':{'heldout_registry_rows':4320,'heldout_background_rng_initializations':0,'heldout_period_draws':0,'heldout_phase_draws':0,'heldout_noise_draws':0,'heldout_flux_arrays':0,'heldout_payloads':0,'heldout_generated':False,'heldout_accessed':False},'execution_state':{'f3b_canary_stochastic_draws_executed':True,'full_development_materialized':False,'afino_executed':False,'candidate_rule_fitted':False,'candidate_thresholds_generated':False,'scientific_metrics_computed':False},'manifest':{'path':MANIFEST.as_posix(),'sha256':shab(mb),'rows':88},'limitations':['Canary validates implementation mechanics, not empirical realism.','No sensitivity, specificity, FPR, balanced accuracy, selection-function estimate, candidate threshold or AFINO outcome is computed.']}
    apath=repo/AUDIT; apath.parent.mkdir(parents=True,exist_ok=True); apath.write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    for scope in ['foundation/f0-f2','docs/literature/bibliographic_audit_ii','workflows/phase3a']:
        if gt(repo,'diff','--name-only',F3B1_COMMIT,'--',scope): raise RuntimeError('protected scope changed: '+scope)
    if guard.read_bytes()!=tg: raise RuntimeError('HELDOUT guard changed during canary')
    changed={line[3:].strip().replace('\\','/') for line in run(repo,'status','--short','--untracked-files=all').stdout.decode('utf-8',errors='replace').splitlines() if line.strip()}
    exp={REPO_SCRIPT.as_posix(),MANIFEST.as_posix(),AUDIT.as_posix()}
    if changed!=exp: raise RuntimeError('unexpected working-tree changes: '+repr(sorted(changed)))
    print('F3B2_GENERATOR_CANARY_PASS')
    print('python_version =',sys.version.split()[0])
    print('numpy_version =',np.__version__)
    print('byteorder =',sys.byteorder)
    print('environment_binding = PASS')
    print('f1_generator_continuity_status = F3B2_F1_GENERATOR_CONTINUITY_PASS')
    print('canary_builder_sha256 =',sha(rp)); print('canary_manifest_sha256 =',sha(mp)); print('generator_validation_audit_sha256 =',sha(apath))
    print('primary_backgrounds = 36'); print('primary_series = 72'); print('challenge_backgrounds = 4'); print('challenge_series = 16'); print('total_canary_series = 88')
    print('time_grid_exact = true'); print('flare_validation = PASS'); print('red_noise_validation = PASS'); print('redraw_count = 0'); print('background_reconstruction = EXACT'); print('period_reconstruction = EXACT'); print('phase_reconstruction = EXACT'); print('period_support = 40..300 s'); print('minimum_cycles = >=3'); print('challenge_latent_flux_invariant = true')
    print('heldout_registry_rows = 4320'); print('heldout_background_rng_initializations = 0'); print('heldout_period_draws = 0'); print('heldout_noise_draws = 0'); print('heldout_flux_arrays = 0'); print('heldout_generated = false'); print('heldout_accessed = false'); print('afino_executed = false'); print('full_development_materialized = false'); print('scientific_metrics_computed = false'); print('repo_changes = 3 files only'); print('NEXT = review canary evidence; do not materialize full DEVELOPMENT yet')

if __name__=='__main__': main()
