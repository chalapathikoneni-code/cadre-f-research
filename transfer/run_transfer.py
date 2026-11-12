"""Reproduce the four source-file workload regimes.

The policies are unchanged. Paired latent worlds are shared across them.
"""
import sys, random, time, csv, statistics, argparse
from pathlib import Path
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'code'))
sys.path.insert(0,str(root/'transfer'))
import wcaea_fixed as W
sys.modules['wcaea']=W
import cadre_opt, cadre_feasible as CF
cadre_opt.wcaea=W
cadre_opt.exp_true_gain=W.exp_true_gain
cadre_opt.decided=W.decided
CF.cadre_opt=cadre_opt
from gen_transfer import gen
POLICIES=[('cadreF',CF.pol_cadre_cover),('myopic',W.pol_myopic),('cadre',cadre_opt.pol_completion_opt),('coverage',W.pol_coverage)]
REGIMES=['R1_sparse','R2_complement','R3_hetero','R4_hub']

def run(inst,policy,B,world):
    state={};spent=0.0;rng=random.Random(0);guard=0
    t0=time.perf_counter()
    while spent < B and W.n_decided(inst,state)<len(inst.queries) and guard<10000:
        guard+=1
        e=policy(inst,state,spent,B,rng)
        if e is None:break
        assert e in inst.items and W.item_useful(inst,state,e)
        assert inst.items[e]['cost']<=B-spent+1e-9
        spent+=inst.items[e]['cost']
        state=W.apply_item(inst,state,e,world)
    return W.n_decided(inst,state),spent,(time.perf_counter()-t0)*1000

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--instances',type=int,default=20)
    parser.add_argument('--worlds',type=int,default=10)
    parser.add_argument('--output',type=Path,default=Path('transfer/TRANSFER_RERUN.csv'))
    args=parser.parse_args()
    n_inst=2 if args.smoke else args.instances
    n_worlds=2 if args.smoke else args.worlds
    rows=[]
    for ri,regime in enumerate(REGIMES):
        for ii in range(n_inst):
            seed=3100001+10000*ri+ii
            inst,B=gen(seed,regime)
            wrng=random.Random(seed+555000)
            worlds=[W.draw_world(inst,wrng) for _ in range(n_worlds)]
            for pn,pol in POLICIES:
                ds=[];ss=[];ts=[]
                for w in worlds:
                    d,s,ms=run(inst,pol,B,w);ds.append(d);ss.append(s);ts.append(ms)
                rows.append(dict(regime=regime,instance=ii,seed=seed,policy=pn,
                    decided_mean=round(statistics.mean(ds),4),decided_sd=round(statistics.pstdev(ds),3),
                    spent_mean=round(statistics.mean(ss),2),budget=B,
                    budget_util=round(statistics.mean(ss)/B,3),ms_mean=round(statistics.mean(ts),2)))
        print(regime,'done',flush=True)
    out=(root/args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    with open(out,'w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0].keys()));writer.writeheader();writer.writerows(rows)
    if not args.smoke and n_worlds==10:
        oracle={(r['regime'],int(r['instance']),r['policy']):r for r in csv.DictReader(open(root/'transfer/TRANSFER_FROZEN_HOLDOUT.csv'))}
        missing=[]
        for r in rows:
            key=(r['regime'],r['instance'],r['policy'])
            orig=oracle[key]
            if abs(r['decided_mean']-float(orig['decided_mean']))>1e-9 or abs(r['spent_mean']-float(orig['spent_mean']))>1e-9:
                missing.append((key,r['decided_mean'],orig['decided_mean'],r['spent_mean'],orig['spent_mean']))
        print('frozen decisions/spend mismatches',len(missing))
        if missing:
            print('examples',missing[:8]);sys.exit(2)
    print('output',out,'rows',len(rows))
if __name__=='__main__':main()
