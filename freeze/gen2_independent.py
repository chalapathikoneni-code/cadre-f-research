"""Source-catalog workload generator.

Generates skewed dependence clusters, item-first source coverage, correlated
item cost, and coverage repairs. Three synthetic regimes: sparse, dense,
heterogeneous. These specifications determine reproducible instance seeds.
"""
import random, math, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
import wcaea_fixed as W
Instance = W.Instance

FAMILIES = {
    'sparse': dict(nq=25, obl=(2, 5), nclusters=40, zipf=1.0, span=(1, 1),
                   pcover=0.50, items_per_pair=1.2, cost_base=(1, 3), per_pair=0.5,
                   pfail=('uniform', 0.05, 0.40), budget_frac=0.40),
    'dense': dict(nq=25, obl=(1, 4), nclusters=8, zipf=0.7, span=(2, 3),
                  pcover=0.35, items_per_pair=0.5, cost_base=(2, 6), per_pair=0.8,
                  pfail=('uniform', 0.05, 0.40), budget_frac=0.40),
    'hetero': dict(nq=25, obl=(1, 6), nclusters=15, zipf=1.6, span=(1, 2),
                   pcover=0.40, items_per_pair=0.8, cost_base=(1, 4), per_pair=1.2,
                   pfail=('bimodal', 0.02, 0.50), budget_frac=0.40),
}

def gen2(seed, family):
    cfg = FAMILIES[family]
    rng = random.Random(seed)
    nq = cfg['nq']
    queries = [f'q{j}' for j in range(nq)]
    obl = {q: [f'o{t}' for t in range(rng.randint(*cfg['obl']))] for q in queries}
    pairs = [(q, o) for q in queries for o in obl[q]]
    clusters = [f'g{t}' for t in range(cfg['nclusters'])]
    weights = [1.0 / (t + 1) ** cfg['zipf'] for t in range(cfg['nclusters'])]
    pc = {pr: rng.choices(clusters, weights=weights)[0] for pr in pairs}
    mode, lo, hi = cfg['pfail']
    if mode == 'uniform':
        cpf = {g: rng.uniform(lo, hi) for g in clusters}
    else:
        cpf = {g: (lo if rng.random() < 0.5 else hi) * rng.uniform(0.8, 1.2) for g in clusters}
    by_cluster = {}
    for pr in pairs: by_cluster.setdefault(pc[pr], []).append(pr)
    items = {}
    m = max(4, int(cfg['items_per_pair'] * len(pairs)))
    for i in range(m):
        span = rng.randint(*cfg['span'])
        home = rng.sample(clusters, min(span, len(clusters)))
        res = set()
        for g in home:
            for pr in by_cluster.get(g, []):
                if rng.random() < cfg['pcover']: res.add(pr)
        if not res: continue
        cost = rng.uniform(*cfg['cost_base']) + cfg['per_pair'] * len(res) + rng.uniform(0, 2)
        items[f's{i}'] = {'cost': round(max(1.0, cost), 2), 'resolves': res}
    covered = set()
    for it in items.values(): covered |= it['resolves']
    for j, pr in enumerate(p for p in pairs if p not in covered):
        items[f'r{j}'] = {'cost': float(rng.randint(2, 6)), 'resolves': {pr}}
    tot = sum(it['cost'] for it in items.values())
    return Instance(queries, obl, items, pc, cpf, name=f'gen2_{family}_{seed}'), float(round(cfg['budget_frac'] * tot))
