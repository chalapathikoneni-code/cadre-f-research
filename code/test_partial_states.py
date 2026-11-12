import math,random,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import wcaea_fixed as wf, cadre_feasible as cf
from test_feasible import small_instance
from test_feasible import oracle_expected_min_cost as empty_oracle
# same method as independent oracle, allowing a reached state
from functools import lru_cache
from itertools import product

def optimal_from(inst,query,initial):
    items=list(inst.items)
    @lru_cache(None)
    def value_of(state_fs):
        state=dict(state_fs)
        if wf.decided(inst,state,query):return 0.0
        best=math.inf
        known={inst.pair_cluster[pair]:outcome for pair,outcome in state.items()}
        for item in items:
            pairs=[pair for pair in inst.items[item]['resolves'] if pair not in state]
            if not pairs:continue
            clusters=sorted({inst.pair_cluster[pair] for pair in pairs if inst.pair_cluster[pair] not in known})
            ev=0.0
            for bits in product((0,1),repeat=len(clusters)):
                prob=1.0;outcomes=dict(known)
                for cluster,is_fail in zip(clusters,bits):
                    pfail=inst.cluster_pfail[cluster];prob*=pfail if is_fail else (1-pfail);outcomes[cluster]='fail' if is_fail else 'pass'
                if prob==0:continue
                next_state=dict(state)
                for pair in pairs:next_state[pair]=outcomes[inst.pair_cluster[pair]]
                ev+=prob*value_of(frozenset(next_state.items()))
            best=min(best,inst.items[item]['cost']+ev)
        return best
    return value_of(frozenset(initial.items()))

count=0
for seed in range(100,250):
    inst=small_instance(seed)
    rng=random.Random(seed)
    world=wf.draw_world(inst,rng)
    st={}
    for item in rng.sample(list(inst.items),rng.randint(0,min(2,len(inst.items)))):
        st=wf.apply_item(inst,st,item,world)
    for query in inst.queries:
        if wf.decided(inst,st,query):continue
        cover=cf.feasible_bound(inst,st,query)
        exp=cf.expected_plan_bound(inst,st,query)
        opt=optimal_from(inst,query,st)
        assert opt-1e-9 <= exp <= cover+1e-9,(seed,query,opt,exp,cover,st)
        plan,cost=cf.completion_plan(inst,st,query)
        assert sum(inst.items[item]['cost'] for item in plan)==cost
        for bits in product(('pass','fail'),repeat=len(inst.clusters())):
            cluster_map=dict(zip(inst.clusters(),bits))
            if any(cluster_map[inst.pair_cluster[pair]]!=outcome for pair,outcome in st.items()):continue
            world={pair:cluster_map[inst.pair_cluster[pair]] for pair in inst.pairs()}
            sim_state=dict(st)
            for item in plan:
                if wf.decided(inst,sim_state,query):break
                sim_state=wf.apply_item(inst,sim_state,item,world)
            assert wf.decided(inst,sim_state,query), (seed,query,st,plan)
        count+=1
print(f'PASS: {count} reached partial query-states, every bound valid against exact oracle and every feasible plan decides the query in all compatible worlds')
