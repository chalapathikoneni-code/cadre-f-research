"""Independent structural checks, exhaustive outcome tests, and oracle."""
import itertools,random,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import wcaea_fixed as wf
import cadre_feasible as cf

demo=wf.Instance(['q1','q2'],{'q1':['a'],'q2':['b']},
              {'cheap':{'cost':1,'resolves':{('q1','a')}},'costly':{'cost':10,'resolves':{('q2','b')}}},
              {('q1','a'):'g',('q2','b'):'g'},{'g':.2})
assert wf._cost_to_decide(demo,{},'q2')==1
assert cf.feasible_bound(demo,{},'q2')==10
assert cf.expected_plan_bound(demo,{},'q2')==10
print('WITNESS PASS: proxy=1, actual feasible cost=10, budget=5')

# independent (non-reusing exact_budgeted) cost-to-decide oracle for one query
from functools import lru_cache
def oracle_expected_min_cost(inst,query):
    items=list(inst.items)
    @lru_cache(None)
    def value_of(state_fs):
        state=dict(state_fs)
        if wf.decided(inst,state,query):return 0.0
        ans=math.inf
        known={inst.pair_cluster[pair]:outcome for pair,outcome in state.items()}
        for item in items:
            pairs=[pair for pair in inst.items[item]['resolves'] if pair not in state]
            if not pairs:continue
            clusters=sorted({inst.pair_cluster[pair] for pair in pairs if inst.pair_cluster[pair] not in known})
            exp=0.0
            for bits in itertools.product((0,1),repeat=len(clusters)):
                prob=1.0;theta=dict(known)
                for cluster,is_fail in zip(clusters,bits):
                    pfail=inst.cluster_pfail[cluster];prob*=pfail if is_fail else (1-pfail);theta[cluster]='fail' if is_fail else 'pass'
                if prob==0:continue
                next_state=dict(state)
                for pair in pairs:next_state[pair]=theta[inst.pair_cluster[pair]]
                sub_value=value_of(frozenset(next_state.items()))
                exp+=prob*sub_value
            ans=min(ans,inst.items[item]['cost']+exp)
        return ans
    return value_of(frozenset())

def small_instance(seed):
    rng=random.Random(seed)
    qn=rng.randint(1,3)
    queries=['q'+str(idx) for idx in range(qn)]
    obligations={query:['o'+str(idx) for idx in range(rng.randint(1,2))] for query in queries}
    pairs=[(query,oblig) for query in queries for oblig in obligations[query]]
    gn=rng.randint(1,3);clusters=['g'+str(idx) for idx in range(gn)]
    pc={pair:rng.choice(clusters) for pair in pairs}
    cpf={cluster:rng.choice([0.,.1,.2,.4,.8,1.]) for cluster in clusters}
    items={f'e{idx}':{'cost':rng.randint(1,7), 'resolves':{pair}} for idx,pair in enumerate(pairs)}
    for idx in range(rng.randint(0,2)):
        subset_size=rng.randint(1,len(pairs))
        items[f's{idx}']={'cost':rng.randint(1,5),'resolves':set(rng.sample(pairs,subset_size))}
    return wf.Instance(queries,obligations,items,pc,cpf)

count=0;maxgap=0
for seed in range(150):
    inst=small_instance(seed)
    for query in inst.queries:
        ub=cf.feasible_bound(inst,{},query)
        eub=cf.expected_plan_bound(inst,{},query)
        opt=oracle_expected_min_cost(inst,query)
        assert math.isfinite(opt) and opt <= eub + 1e-8 <= ub+1e-8,(seed,query,opt,eub,ub)
        plan,cost=cf.completion_plan(inst,{},query)
        assert abs(cost-ub)<1e-8
        seen=set()
        for item in plan: seen.update(inst.items[item]['resolves'])
        assert all((query,oblig) in seen for oblig in inst.obligations[query]),(seed,query,plan)
        maxgap=max(maxgap,eub-opt)
        count+=1
print(f'PASS: {count} oracle comparisons, 0 failures; max expected proxy-vs-optimal gap {maxgap:.4f}')
print('PASS: explicit feasible cover upper-bounds optimal expected and worst-case completion costs on all tested instances.')
