"""Supplementary, explicitly exploratory F5 EPA-shaped probability sweep.
Not measured EPA records; all pfail values are scenario parameters.
"""
import csv,math,random,statistics,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import wcaea_fixed as wf
sys.modules['wcaea']=wf
import instances,cadre_opt,cadre_feasible as cf,paotr
cadre_opt.wcaea=wf;cadre_opt.exp_true_gain=wf.exp_true_gain;cadre_opt.decided=wf.decided
pols={'myopic':wf.pol_myopic,'cadre-audited':cadre_opt.pol_completion_opt,'cadre-feasible':cf.pol_cadre_cover,'paotr-adapted':paotr.pol_paotr}

def run(inst,pol,world,budget):
    st={};spent=0.0;rng=random.Random(31)
    while spent<budget and wf.n_decided(inst,st)<len(inst.queries):
        item=pol(inst,st,spent,budget,rng)
        if item is None:break
        assert wf.item_useful(inst,st,item) and inst.items[item]['cost']+spent<=budget
        spent+=inst.items[item]['cost'];st=wf.apply_item(inst,st,item,world)
    return wf.n_decided(inst,st),spent

out=[]
def batch(tag,inst,budget,trials,pol_names):
    worlds=[wf.draw_world(inst,random.Random(191311 + trial_idx*7373)) for trial_idx in range(trials)]
    vals={};times={}
    for pname in pol_names:
        pol=pols[pname];ds=[];ss=[];tc=time.perf_counter()
        for world in worlds:
            decided_count,spent=run(inst,pol,world,budget);ds.append(decided_count);ss.append(spent)
        elapsed=1000*(time.perf_counter()-tc)/trials
        mean_decided=statistics.mean(ds)
        se=statistics.stdev(ds)/math.sqrt(trials)
        vals[pname]=mean_decided;times[pname]=elapsed
        out.append([tag,trials,budget,pname,mean_decided,se,statistics.mean(ss),elapsed])
    print(tag,' '.join(f'{name}:{val:.3f}' for name,val in vals.items()),'ms',times,flush=True)

batch('F5_nominal',instances.F5_epa(),30.0,300,list(pols))
for pi in (.1,.3,.5):
  for pw in (.05,.15,.3):
    inst=instances.F5_epa()
    for cluster in inst.cluster_pfail:
        if cluster.startswith('gi_'):inst.cluster_pfail[cluster]=pi
        if cluster.startswith('gw_'):inst.cluster_pfail[cluster]=pw
    batch(f'F5_sweep_i{pi}_w{pw}',inst,30.0,60,['myopic','cadre-audited','cadre-feasible'])
with open(str(Path(__file__).resolve().parent/'EPA_SENSITIVITY.csv'),'w',newline='') as csv_file:
    writer=csv.writer(csv_file);writer.writerow(['scenario','trials','budget','policy','mean_decided','se','mean_spent','ms_per_run']);writer.writerows(out)
print('DONE EPA')
