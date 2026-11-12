"""Alternative policies for W-CAEA-Budget.

CADRE-COVER: use a certified feasible full-cover cost in place of the
cluster-footprint cost-to-decide proxy, in both ranking and gates.
CADRE-EXPECT: rank by the expected cost of an explicit early-stop completion
plan, but certify budget eligibility with the full-cover cost.
CADRE-GUARD: keep the proxy for ranking candidates, and replace only the two
affordability decisions with certified full-cover costs.

These are new policies and do not carry over the earlier CADRE results.
"""
from __future__ import annotations
import itertools, math, random, sys
import wcaea_fixed as wf
sys.modules.setdefault("wcaea", wf)
import cadre_opt
cadre_opt.wcaea = wf
cadre_opt.exp_true_gain = wf.exp_true_gain
cadre_opt.decided = wf.decided

# Cache holds actual Instance objects, avoiding id() reuse collisions.
_INST_CACHE: dict[int, tuple[object, dict]] = {}

def _context(inst):
    key=id(inst)
    hit=_INST_CACHE.get(key)
    if hit and hit[0] is inst: return hit[1]
    by_query={}
    for query in inst.queries:
        oblig_names=tuple(inst.obligations[query]); oblig_bit={oblig: 1<<bit_index for bit_index,oblig in enumerate(oblig_names)}
        item_masks={item:sum(oblig_bit[oblig] for (owner,oblig) in meta['resolves'] if owner==query)
                    for item,meta in inst.items.items()}
        item_masks={item:mask_val for item,mask_val in item_masks.items() if mask_val}
        by_query[query]=(oblig_names,item_masks,{})
    _INST_CACHE[key]=(inst,by_query)
    return by_query

def completion_plan(inst,state,query):
    """A concrete feasible nonadaptive item cover of every unresolved (q,o).

    For k<=10 unresolved pairs this uses an exact min-cost set-cover DP,
    otherwise weighted greedy. It returns a witness plan, not a bound guessed
    from source-cluster similarity. The sum of costs is an achievable
    worst-case decision cost if every item is bought and the query stays
    undecided. It is not the adaptive optimum.
    """
    if wf.decided(inst,state,query): return (),0.0
    oblig_names,item_masks,cache=_context(inst)[query]
    target=sum(1<<bit_index for bit_index,oblig in enumerate(oblig_names) if (query,oblig) not in state)
    if not target: return (),0.0
    if target in cache: return cache[target]
    choices=[(item,mask&target,float(inst.items[item]['cost'])) for item,mask in item_masks.items() if mask&target]
    cover=0
    for _,mask,_ in choices: cover |= mask
    if target & ~cover: return (),math.inf
    if target.bit_count() <= 10:
        memo={0:(0.0,())}
        def min_cover(mask):
            if mask in memo: return memo[mask]
            best=(math.inf,())
            for item,item_mask,cost in choices:
                rest_mask=mask & ~item_mask
                if rest_mask==mask:continue
                tail_cost,tail=min_cover(rest_mask)
                total_cost=cost+tail_cost
                if total_cost < best[0]-1e-12:
                    best=(total_cost,(item,)+tail)
            memo[mask]=best
            return best
        cost,plan=min_cover(target)
    else:
        uncovered=target;plan=[];cost=0.0
        while uncovered:
            viable=[(int((item_mask&uncovered).bit_count())/item_cost, -item_cost, item,item_mask,item_cost) for item,item_mask,item_cost in choices if item_mask&uncovered]
            if not viable: return (),math.inf
            ratio,neg,item,item_mask,item_cost=max(viable)
            plan.append(item);cost+=item_cost;uncovered &= ~item_mask
        plan=tuple(plan)
    cache[target]=(tuple(plan),float(cost))
    return cache[target]

def feasible_bound(inst,state,query):
    return completion_plan(inst,state,query)[1]

def expected_plan_bound(inst,state,query):
    """Expected acquisition cost of a feasible fixed plan with early stop.

    This upper-bounds the optimal expected cost, but it does not certify that
    the remaining hard budget suffices in every realization. Only the
    full-cover cost from completion_plan can do that.
    """
    plan,worst=completion_plan(inst,state,query)
    if not math.isfinite(worst): return math.inf
    if not plan: return 0.0
    known={inst.pair_cluster[pair]:outcome for pair,outcome in state.items()}
    seen={inst.pair_cluster[pair] for pair in state if pair[0]==query}
    survival=1.0; exp_cost=0.0
    for item in plan:
        exp_cost += survival*inst.items[item]['cost']
        # The item resolves its explicit obligations for this query. A
        # cluster shared with other queries is not, on its own, evidence for
        # this query's pair.
        query_clusters={inst.pair_cluster[pair] for pair in inst.items[item]['resolves']
              if pair[0]==query and pair not in state} - seen
        for cluster in query_clusters:
            survival *= (1-inst.cluster_pfail[cluster]) if cluster not in known else (1.0 if known[cluster]=='pass' else 0.0)
        seen |= query_clusters
    return exp_cost

def _expected_metric_reduction(inst,state,query,item,base,metric):
    """Enumerate fresh outcomes once, conditional on already observed clusters."""
    if not math.isfinite(base): return 0.0
    known={inst.pair_cluster[pair]:outcome for pair,outcome in state.items()}
    new_pairs=[pair for pair in inst.items[item]['resolves'] if pair not in state]
    unknown=sorted({inst.pair_cluster[pair] for pair in new_pairs if inst.pair_cluster[pair] not in known})
    result=0.0
    for bits in itertools.product((0,1), repeat=len(unknown)):
        prob=1.0;theta=dict(known)
        for cluster,is_fail in zip(unknown,bits):
            pfail=inst.cluster_pfail[cluster]
            prob *= pfail if is_fail else (1-pfail)
            theta[cluster]='fail' if is_fail else 'pass'
        if prob==0: continue
        state_copy=dict(state)
        for pair in new_pairs: state_copy[pair]=theta[inst.pair_cluster[pair]]
        next_val=metric(inst,state_copy,query)
        if math.isfinite(next_val):
            result+=prob*(base-next_val)
    return result

def _policy(inst,state,spent,budget,rng,mode):
    cand=wf._remaining(inst,state,spent,budget)
    if not cand: return None
    rem=budget-spent
    undecided=[query for query in inst.queries if not wf.decided(inst,state,query)]
    # Independently certified hard-budget feasibility: entire q-pair cover.
    worst={query:feasible_bound(inst,state,query) for query in undecided}
    finite=sorted(cost_value for cost_value in worst.values() if math.isfinite(cost_value))
    n_aff=sum(cost_value<=rem for cost_value in finite)
    if n_aff>=2: fair=finite[0]+finite[1]
    elif finite: fair=finite[0]
    else: fair=rem
    best=None;best_score=0.0
    for item in cand:
        cost=inst.items[item]['cost']
        if cost>fair: continue
        gain=wf.exp_true_gain(inst,state,item)
        if gain/cost>best_score+1e-12:best,best_score=item,gain/cost
    if best is not None:return best
    eligible=[query for query in undecided if worst[query]<=rem]
    if not eligible:
        # Keep the chance to gain from early refutation even when no all-pass
        # completion fits the budget. Fall back to myopic here.
        return wf.pol_myopic(inst,state,spent,budget,rng)
    metric=expected_plan_bound if mode=='expected' else (cadre_opt.ctd_fast if mode=='guard' else feasible_bound)
    ctds={query:metric(inst,state,query) for query in eligible}
    qstar=min(eligible,key=lambda query:(ctds[query],worst[query]))
    base=ctds[qstar]
    best=None;best_score=-math.inf
    for item in cand:
        red=_expected_metric_reduction(inst,state,qstar,item,base,metric)
        score=red/inst.items[item]['cost']
        if score > best_score+1e-12:best,best_score=item,score
    return best

def pol_cadre_cover(inst,state,spent,budget,rng):
    return _policy(inst,state,spent,budget,rng,'cover')

def pol_cadre_expected(inst,state,spent,budget,rng):
    return _policy(inst,state,spent,budget,rng,'expected')

def pol_cadre_guard(inst,state,spent,budget,rng):
    return _policy(inst,state,spent,budget,rng,'guard')

def pol_cadre_plan(inst,state,spent,budget,rng):
    """A simpler completion-plan policy.

    Uses the same actual-pair cover certificate for affordability and fair
    shares. On a plateau it targets the smallest expected-cost feasible
    explicit plan, then buys one of that plan's items. It will not spend on
    unrelated cheap copies just because they share a source cluster.
    """
    cand=wf._remaining(inst,state,spent,budget)
    if not cand:return None
    rem=budget-spent
    undecided=[query for query in inst.queries if not wf.decided(inst,state,query)]
    worst={query:feasible_bound(inst,state,query) for query in undecided}
    finite=sorted(cost_value for cost_value in worst.values() if math.isfinite(cost_value))
    n_aff=sum(cost_value<=rem for cost_value in finite)
    fair=(finite[0]+finite[1] if n_aff>=2 else finite[0] if finite else rem)
    best=None;best_score=0.0
    for item in cand:
        cost=inst.items[item]['cost']
        if cost>fair:continue
        gain=wf.exp_true_gain(inst,state,item)
        if gain/cost>best_score+1e-12:best,best_score=item,gain/cost
    if best is not None:return best
    eligible=[query for query in undecided if worst[query]<=rem]
    if not eligible:return wf.pol_myopic(inst,state,spent,budget,rng)
    qstar=min(eligible,key=lambda query:(expected_plan_bound(inst,state,query),worst[query]))
    plan,_=completion_plan(inst,state,qstar)
    available=[item for item in plan if item in cand]
    if not available:return wf.pol_myopic(inst,state,spent,budget,rng)
    known={inst.pair_cluster[pair]:outcome for pair,outcome in state.items()}
    def refute_per_cost(item):
        clusters={inst.pair_cluster[pair] for pair in inst.items[item]['resolves'] if pair[0]==qstar and pair not in state}
        survive=1.0
        for cluster in clusters:
            survive *= (1.0 if known.get(cluster)=='pass' else 0.0 if known.get(cluster)=='fail' else 1.0-inst.cluster_pfail[cluster])
        return (1-survive)/inst.items[item]['cost']
    return max(available,key=lambda item:(refute_per_cost(item),-inst.items[item]['cost']))
