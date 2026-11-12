"""Check the published results against packaged CSVs. Python 3.10+ standard library."""
from pathlib import Path
from collections import defaultdict
import csv, math, statistics
ROOT=Path(__file__).resolve().parent

def load(name):
    with (ROOT/name).open(newline='') as f:return list(csv.DictReader(f))
def close(actual,expected,tol=.005,label=''):
    assert abs(actual-expected) <= tol,(label,actual,expected,tol)
def paired_interval(values,df):
    n=len(values);assert n==df+1
    m=statistics.mean(values)
    tc={11:2.200985160082949,19:2.093024054408263}.get(df)
    assert tc is not None
    h=tc*statistics.stdev(values)/math.sqrt(n)
    return m,m-h,m+h

# 12 F4 instance seeds per size, 40 paired worlds/seed x 3 policies.
rows=[r for r in load('data/HOLDOUT_FINAL.csv') if r['phase']=='primary']
assert len(rows)==2880
for size,means,diff_myo,diff_cpc in [
 (25,{'myopic':20.448,'cadre-audited':19.927,'cadre-cover':20.654},(.206,.074,.339),(.727,.424,1.030)),
 (50,{'myopic':41.677,'cadre-audited':39.606,'cadre-cover':41.996},(.319,.100,.537),(2.390,1.677,3.102))]:
 sub=[r for r in rows if int(r['nqueries'])==size]
 assert len(sub)==1440
 for p,v in means.items():
  xs=[float(r['decided']) for r in sub if r['policy']==p]
  assert len(xs)==480
  close(statistics.mean(xs),v,label=f'primary {size} {p}')
 seed_groups=defaultdict(dict)
 for r in sub:seed_groups[(r['seed'],r['trial'])][r['policy']]=float(r['decided'])
 for base,expected in [('myopic',diff_myo),('cadre-audited',diff_cpc)]:
  by_seed=defaultdict(list)
  for (seed,trial),v in seed_groups.items():
   assert len(v)==3
   by_seed[seed].append(v['cadre-cover']-v[base])
  assert len(by_seed)==12 and all(len(x)==40 for x in by_seed.values())
  m,lo,hi=paired_interval([statistics.mean(x) for x in by_seed.values()],11)
  for actual,want in zip((m,lo,hi),expected):close(actual,want,label=f'primary {size} - {base}')
 print('PRIMARY',size,'PASS')

# 13 F4 configuration-level comparisons including dense six-obligation workloads.
conf=load('data/F4_CONFIGURATION_SUMMARY.csv');assert len(conf)==13
assert sum(float(r['CI_F_Myopic'].split(',')[0].strip('['))>0 for r in conf)==9
assert sum(float(r['CI_F_CPC'].split(',')[0].strip('['))>0 for r in conf)==12
dense=next(r for r in conf if r['configuration']=='X_dense')
for field,expected in [('CADRE_F_mean',23.295),('Myopic_mean',21.430),('delta_F_Myopic',1.865)]:close(float(dense[field]),expected,label=field)
print('CONFIGURATIONS 13 PASS')

# Source-first source catalog: count independent instances, compare source CSVs.
source=load('freeze/INDEPENDENT_RESULTS_RAW.csv')
summary=load('freeze/INDEPENDENT_ANALYSIS.csv')
for fam,reference in [('sparse',(21.092,20.592,19.825)),('dense',(23.517,23.517,22.533)),('hetero',(22.658,22.633,21.108))]:
 sub=[r for r in source if r['family']==fam]
 for pol,expect in zip(('cadreF','myopic','cadre'),reference):
  vals=[float(r['decided_mean']) for r in sub if r['policy']==pol]
  assert len(vals)==12
  close(statistics.mean(vals),expect,0.01,f'{fam} {pol}')
 assert len([r for r in summary if r['family']==fam])==2
print('SOURCE CATALOG PASS')

# Ablations: numerical results and equivalent variants across all three families.
ablation=load('ablation/CADRE_F_ABLATION_SUMMARY.csv')
for fam in ['sparse','dense','hetero']:
 d={r['policy']:float(r['mean_decided']) for r in ablation if r['family']==fam}
 assert len(d)==6
 assert d['CADRE-F']==d['Expected-plan ranking']==d['Plan-following']
close(next(float(r['mean_decided']) for r in ablation if r['family']=='sparse' and r['policy']=='CPC ranking'),20.63333)
print('ABLATION PASS')

# Exact worlds for F1-F3. The new Table V includes CADRE-F and OPT.
exact=load('data/exact_policy_results.csv')
ref={
 'F1_p01':{'surrogate':.06793465,'myopic':1.0,'paotr-adapted':1.0,'cadre-audited':1.0,'cadre-feasible':1.0},
 'F2':{'surrogate':6.0,'myopic':1.0,'paotr-adapted':6.0,'cadre-audited':6.0,'cadre-feasible':6.0},
 'F3':{'surrogate':.8,'myopic':1.6,'paotr-adapted':.8,'cadre-audited':1.6,'cadre-feasible':1.6}}
for family,expected in ref.items():
 d={r['policy']:float(r['exact_expected_decided']) for r in exact if r['family']==family}
 for pol,v in expected.items():close(d[pol],v,label=f'{family} {pol}')
print('EXACT CONSTRUCTED CASES PASS')

# One F5 protocol for the paper (300 matched worlds, SE from CSV).
f5=[r for r in load('data/EPA_SENSITIVITY.csv') if r['scenario']=='F5_nominal']
assert len(f5)==4 and all(int(r['trials'])==300 for r in f5)
for r in f5:
 close(float(r['mean_decided']), {'myopic':21.216667,'cadre-audited':21.313333,'cadre-feasible':21.313333,'paotr-adapted':21.533333}[r['policy']],label='F5 '+r['policy'])
print('F5 PASS')

# Source-file transfer, paired instance-level t-intervals.
transfer=load('transfer/TRANSFER_FROZEN_HOLDOUT.csv')
assert len(transfer)==320
for reg,reference in [('R1_sparse',(24.97,25.,-.03)),('R2_complement',(22.19,23.975,-1.785)),('R3_hetero',(24.985,24.965,.020)),('R4_hub',(23.825,24.83,-1.005))]:
 sub=[r for r in transfer if r['regime']==reg]
 by=defaultdict(dict)
 for r in sub:by[int(r['instance'])][r['policy']]=float(r['decided_mean'])
 assert len(by)==20 and all(len(v)==4 for v in by.values())
 f=statistics.mean(v['cadreF'] for v in by.values());myo=statistics.mean(v['myopic'] for v in by.values())
 diff=paired_interval([v['cadreF']-v['myopic'] for v in by.values()],19)
 for got,want in zip((f,myo,diff[0]),reference):close(got,want,label=reg)
 print('TRANSFER',reg,'PASS',tuple(round(x,3) for x in diff))
print('ALL REPORTED DATA CHECKS PASS')
