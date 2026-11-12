"""Shared experiment harness. Loads the policy implementations and the
instance generators. All runners assert the hard budget and that every
acquired item is useful."""
import sys, os, time, random, math, statistics
CODE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CODE)
import wcaea_fixed as wcaea
sys.modules['wcaea'] = wcaea
W = wcaea  # short alias imported by the EPA, tiered and n200 runners
import cadre_feasible as CF
import cadre_opt as CO
CO.wcaea = wcaea; CO.exp_true_gain = wcaea.exp_true_gain; CO.decided = wcaea.decided
CF.cadre_opt = CO
import instances as A_inst

def run_policy(inst, pol, budget, world, rngseed=0):
    state, spent, guard = {}, 0.0, 0
    rng = random.Random(rngseed); start_time = time.perf_counter()
    while spent < budget and wcaea.n_decided(inst, state) < len(inst.queries) and guard < 100000:
        guard += 1
        item = pol(inst, state, spent, budget, rng)
        if item is None: break
        assert item in inst.items and wcaea.item_useful(inst, state, item), 'useless/unknown item'
        assert inst.items[item]['cost'] <= budget - spent + 1e-9, 'BUDGET VIOLATION'
        spent += inst.items[item]['cost']; state = wcaea.apply_item(inst, state, item, world)
    assert spent <= budget + 1e-9
    return wcaea.n_decided(inst, state), spent, time.perf_counter() - start_time

def expected_value(inst, pol, budget, nworlds=400, wseed=777):
    """Monte-Carlo expected decided (for stochastic instances) with SE."""
    wrng = random.Random(wseed)
    vals = []
    for _ in range(nworlds):
        world = wcaea.draw_world(inst, wrng)
        decided_count, spent, _ = run_policy(inst, pol, budget, world)
        vals.append(decided_count)
    mean_decided = statistics.mean(vals)
    se = statistics.stdev(vals) / math.sqrt(len(vals)) if len(vals) > 1 else 0.0
    return mean_decided, se

TCRIT = {11: 2.201, 19: 2.093, 29: 2.045}
def paired_ci(diffs):
    count = len(diffs); mean_diff = statistics.mean(diffs)
    sd = statistics.stdev(diffs) if count > 1 else 0.0
    crit = TCRIT.get(count - 1, 2.0)
    half = crit * sd / math.sqrt(count) if count > 1 else 0.0
    return mean_diff, (mean_diff - half, mean_diff + half)
