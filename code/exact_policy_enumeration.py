"""Exact expected decided-count for fixed policies on tractable F1-F3 cases.

No Monte Carlo; enumerate all non-deterministic cluster assignments, with
independent Bernoulli probabilities and a fixed policy action function.
"""
import csv,math,random,sys,itertools
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import wcaea_fixed as wf
sys.modules['wcaea']=wf
import instances,cadre_opt,cadre_feasible as cf,paotr
cadre_opt.wcaea=wf;cadre_opt.exp_true_gain=wf.exp_true_gain;cadre_opt.decided=wf.decided
pols={'myopic':wf.pol_myopic, 'surrogate':wf.pol_sssc,
      'paotr-adapted':paotr.pol_paotr,
      'cadre-audited':cadre_opt.pol_completion_opt,
      'cadre-feasible':cf.pol_cadre_cover}

def eval_exact(inst,budget,policy):
    clusters=list(inst.cluster_pfail)
    stochastic=[cluster for cluster in clusters if 0<inst.cluster_pfail[cluster]<1]
    det={cluster:('pass' if inst.cluster_pfail[cluster]==0 else 'fail') for cluster in clusters if cluster not in stochastic}
    val=spent=0.0
    for combo in itertools.product((0,1),repeat=len(stochastic)):
        theta=dict(det);prob=1.0
        for cluster,fail in zip(stochastic,combo):
            pfail=inst.cluster_pfail[cluster]
            prob *= pfail if fail else 1-pfail
            theta[cluster]='fail' if fail else 'pass'
        if prob==0:continue
        world={pair:theta[inst.pair_cluster[pair]] for pair in inst.pairs()}
        state={};used=0.0;rng=random.Random(9)
        while used<budget and wf.n_decided(inst,state)<len(inst.queries):
            item=policy(inst,state,used,budget,rng)
            if item is None:break
            assert wf.item_useful(inst,state,item)
            assert used+inst.items[item]['cost']<=budget
            used+=inst.items[item]['cost'];state=wf.apply_item(inst,state,item,world)
        val+=prob*wf.n_decided(inst,state)
        spent+=prob*used
    return val,spent,len(stochastic)

cases=[('F1_p01',instances.F1_claim3(pfail=.01),7),
       ('F2',instances.F2_completion_trap(),101),
       ('F3',instances.F3_copy_trap(),7)]
out=[]
for tag,inst,budget in cases:
    for policy_name,pol in pols.items():
        mu,spent,ncl=eval_exact(inst,budget,pol)
        out.append([tag,budget,policy_name,round(mu,10),round(spent,10),ncl])
        print(tag,policy_name,'exact utility',f'{mu:.8f}','mean spent',f'{spent:.6f}','random clusters',ncl,flush=True)
with open(str(Path(__file__).resolve().parent/'exact_policy_results.csv'),'w',newline='') as csv_file:
    writer=csv.writer(csv_file);writer.writerow(['family','budget','policy','exact_expected_decided','exact_expected_spent','random_clusters']);writer.writerows(out)
