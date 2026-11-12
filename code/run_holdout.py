"""Precommitted paired-world holdout for CADRE alternatives.

Writes every case immediately; no filter on results. Run with
PYTHONHASHSEED=0 for exact reproducibility of incidental ordering.
"""
import csv,math,os,random,sys,time,statistics
from pathlib import Path
base_dir=Path(__file__).resolve().parent
sys.path.insert(0,str(base_dir))
import wcaea_fixed as wf
sys.modules['wcaea']=wf
import instances,paotr,cadre_opt,cadre_feasible as cf
cadre_opt.wcaea=wf;cadre_opt.exp_true_gain=wf.exp_true_gain;cadre_opt.decided=wf.decided

POLICIES={'myopic':wf.pol_myopic,'cadre-audited':cadre_opt.pol_completion_opt,
          'cadre-cover':cf.pol_cadre_cover,'sssc':wf.pol_sssc,
          'paotr-adapted':paotr.pol_paotr}


def run(inst,pol,budget,world):
    state={};spent=0.0;rng=random.Random(77);steps=0
    while spent<budget and wf.n_decided(inst,state)<len(inst.queries):
        steps+=1
        if steps>10000: raise RuntimeError('nonterminating policy')
        item=pol(inst,state,spent,budget,rng)
        if item is None:break
        assert item in inst.items and wf.item_useful(inst,state,item),item
        assert inst.items[item]['cost']<=budget-spent+1e-10
        spent+=inst.items[item]['cost']
        state=wf.apply_item(inst,state,item,world)
    assert spent<=budget+1e-10
    return wf.n_decided(inst,state),spent

def world_for(inst,seed,trial):
    return wf.draw_world(inst,random.Random(992000+seed*31+trial*7919))

results_path=Path(os.environ.get('CADRE_RESULTS_PATH', str(base_dir/'holdout_results.csv')))
if not results_path.exists():
 with results_path.open('w',newline='') as fh:
    writer=csv.writer(fh);writer.writerow(['phase','regime','seed','nqueries','nitems','budget','budget_frac','share','maxobl','trial','policy','decided','spent','ms_policy_run'])

def case(phase,regime,inst,budget,seed,share,maxobl,bfrac,trials,policy_names):
    worlds=[world_for(inst,seed,trial_idx) for trial_idx in range(trials)]
    results={}
    for name in policy_names:
        if name not in POLICIES: raise ValueError(name)
        pol=POLICIES[name];vals=[];cost=[];times=[]
        for world_idx,world in enumerate(worlds):
            start=time.perf_counter();decided_count,spent=run(inst,pol,budget,world);elapsed=1000*(time.perf_counter()-start)
            vals.append(decided_count);cost.append(spent);times.append(elapsed)
            with results_path.open('a',newline='') as fh:
                csv.writer(fh).writerow([phase,regime,seed,len(inst.queries),len(inst.items),budget,bfrac,share,maxobl,world_idx,name,decided_count,spent,round(elapsed,5)])
        results[name]=(statistics.mean(vals),statistics.mean(times))
    print(f'{phase} {regime} seed={seed} n={len(inst.queries)} B={budget} trials={trials} '+
          ' '.join(f'{pname}:{stats[0]:.2f}/{stats[1]:.0f}ms' for pname,stats in results.items()),flush=True)

phase=sys.argv[1] if len(sys.argv)>1 else 'primary'
if phase=='primary':
    for n_queries in (25,50):
        for seed in range(4000,4012):
            inst=instances.F4_random(nq=n_queries,share=.3,maxobl=3,seed=seed)
            budget=float(round(.4*sum(meta['cost'] for meta in inst.items.values())))
            case('primary','default',inst,budget,seed,.3,3,.4,40,['myopic','cadre-audited','cadre-cover'])
elif phase=='sensitivity':
    for share,maxobl in [(0.05,3),(.8,3),(.3,6),(.8,6)]:
        for seed in range(4100,4104):
            inst=instances.F4_random(nq=50,share=share,maxobl=maxobl,seed=seed)
            total=sum(meta['cost'] for meta in inst.items.values())
            for ffrac in (.25,.60):
                budget=float(round(ffrac*total))
                case('sensitivity',f'share{share}_obl{maxobl}',inst,budget,seed,share,maxobl,ffrac,25,['myopic','cadre-audited','cadre-cover'])
elif phase=='scaling':
    for n_queries,seeds,trials in [(100,[4200,4201,4202],10),(200,[4300,4301],3),(500,[4400],1)]:
        for seed in seeds:
            inst=instances.F4_random(nq=n_queries,share=.3,maxobl=3,seed=seed)
            budget=float(round(.4*sum(meta['cost'] for meta in inst.items.values())))
            case('scaling','default',inst,budget,seed,.3,3,.4,trials,['myopic','cadre-audited','cadre-cover'])
else:raise ValueError(phase)
print('DONE',phase,flush=True)
