"""Frozen matched-world component-variant study for CADRE-F; no policy edits.
Run from any cwd. Follows published gen2's three families, 12 instances x
10 identical latent worlds per policy. No selection/tuning on results.
"""
from __future__ import annotations
import csv, os, sys, random, time, json, math, hashlib, statistics
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT
os.chdir(SRC)
OUT=ROOT/'ablation'
sys.path.insert(0,str(SRC/'code'))
sys.path.insert(0,str(SRC/'freeze'))
import wcaea_fixed as W
sys.modules['wcaea']=W
import cadre_opt, cadre_feasible as cf
cadre_opt.wcaea=W; cadre_opt.exp_true_gain=W.exp_true_gain; cadre_opt.decided=W.decided
cf.cadre_opt=cadre_opt
from gen2_independent import gen2
POLS={'CADRE-F':cf.pol_cadre_cover,'Expected-plan ranking':cf.pol_cadre_expected,'Plan-following':cf.pol_cadre_plan,'CPC ranking':cf.pol_cadre_guard,'CPC':cadre_opt.pol_completion_opt,'Myopic':W.pol_myopic}
BASE=700001
FAMILIES=['sparse','dense','hetero']
N_INST=12
N_WORLDS=10
CONFIG=dict(generator='gen2_independent.py',seeds='700001 + 1000*family_index + instance_index',family=FAMILIES,instances_per_family=N_INST,paired_worlds_per_instance=N_WORLDS,world_seed='base_seed + 555000',budget='generator 0.40 * total evidence costs',policy_set=list(POLS),selection='none; policies imported unchanged; report all results',stats='paired t interval on per-instance mean over paired worlds; df=11; exploratory unadjusted')
(OUT/'ablation_config_frozen.json').write_text(json.dumps(CONFIG,indent=2,sort_keys=True)+'\n')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
hashes={str(p.relative_to(ROOT)):sha(p) for p in [OUT/'ablation_config_frozen.json',SRC/'code'/'cadre_feasible.py',SRC/'code'/'wcaea_fixed.py',SRC/'code'/'cadre_opt.py',SRC/'freeze'/'gen2_independent.py']}
(OUT/'ablation_code_hashes_before_runs.json').write_text(json.dumps(hashes,sort_keys=True,indent=2)+'\n')
print('FROZEN',sha(OUT/'ablation_config_frozen.json'),flush=True)

def run(inst,policy,budget,world):
    state={};spent=0.0;rng=random.Random(0);steps=0
    t0=time.perf_counter()
    while spent+1e-9<budget and W.n_decided(inst,state)<len(inst.queries):
        steps+=1
        if steps>10000:raise RuntimeError('loop')
        item=policy(inst,state,spent,budget,rng)
        if item is None:break
        assert item in inst.items and W.item_useful(inst,state,item),(inst.name,item)
        assert inst.items[item]['cost']<=budget-spent+1e-8,(inst.name,item,spent,budget)
        spent+=inst.items[item]['cost']
        state=W.apply_item(inst,state,item,world)
    assert spent<=budget+1e-8
    return W.n_decided(inst,state),spent,(time.perf_counter()-t0)*1000

raw=[]
for fi,family in enumerate(FAMILIES):
 for ii in range(N_INST):
    seed=BASE+1000*fi+ii
    inst,B=gen2(seed,family)
    worldrng=random.Random(seed+555000)
    worlds=[W.draw_world(inst,worldrng) for _ in range(N_WORLDS)]
    for name,pol in POLS.items():
      for wi,w in enumerate(worlds):
        d,s,ms=run(inst,pol,B,w)
        raw.append(dict(family=family,instance=ii,seed=seed,world=wi,policy=name,queries=len(inst.queries),items=len(inst.items),budget=B,decided=d,spent=round(s,6),run_ms=round(ms,6)))
    print(f'{family} instance {ii+1}/{N_INST}: complete',flush=True)
rawfile=OUT/'CADRE_F_ABLATION_RAW.csv'
with rawfile.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(raw[0]));w.writeheader();w.writerows(raw)

# Per-instance means are independent units; worlds are repeated measures.
from scipy.stats import t as StudentT
summ=[]
for family in FAMILIES:
 subset=[r for r in raw if r['family']==family]
 per={}
 for name in POLS:
  q=[];rt=[];bu=[]
  for ii in range(N_INST):
   records=[r for r in subset if r['policy']==name and r['instance']==ii]
   assert len(records)==N_WORLDS
   q.append(statistics.mean(r['decided'] for r in records))
   rt.append(statistics.mean(r['run_ms'] for r in records))
   bu.append(statistics.mean(r['spent']/r['budget'] for r in records))
  per[name]=(q,rt,bu)
 for name in POLS:
  diffs=[a-b for a,b in zip(per[name][0],per['CADRE-F'][0])]
  m=statistics.mean(diffs);s=statistics.stdev(diffs)
  h=StudentT.ppf(.975,N_INST-1)*s/math.sqrt(N_INST)
  p=StudentT.sf(abs(m)/(s/math.sqrt(N_INST)),N_INST-1)*2 if s>1e-12 else (1. if abs(m)<1e-10 else 0.)
  summ.append(dict(family=family,policy=name,mean_decided=round(statistics.mean(per[name][0]),5),diff_vs_CADRE_F=round(m,5),diff95_low=round(m-h,5),diff95_high=round(m+h,5),p_unadjusted=round(p,6),positive_instances_vs_F=sum(d>1e-9 for d in diffs),negative_instances_vs_F=sum(d< -1e-9 for d in diffs),mean_run_ms=round(statistics.mean(per[name][1]),4),budget_util=round(statistics.mean(per[name][2]),4)))
sumfile=OUT/'CADRE_F_ABLATION_SUMMARY.csv'
with sumfile.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(summ[0]));w.writeheader();w.writerows(summ)
assert len(raw)==len(FAMILIES)*N_INST*N_WORLDS*len(POLS)
for p,original_sha in hashes.items():
 assert sha(ROOT/p)==original_sha,('source changed',p)
print('HASHES_UNCHANGED',flush=True)
for x in summ:
 print(f"{x['family']:<6} {x['policy']:<22} mean {x['mean_decided']:<7.3f} minus F {x['diff_vs_CADRE_F']:+.3f} CI [{x['diff95_low']:+.3f},{x['diff95_high']:+.3f}]",flush=True)
print('DONE',len(raw),'rows',flush=True)
