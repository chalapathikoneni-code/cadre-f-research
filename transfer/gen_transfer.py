"""Frozen source-file transfer generator (originated in the JWB Pod D experiment).
Items derive from SOURCES, not per-pair minting. Two tiers per source.
Cluster of a pair = reliability group of its primary source."""
import sys, random
from pathlib import Path
ROOT = Path(__file__).resolve().parent
# Caller inserts artifact/code into the import path.
import wcaea_fixed as W

REGIMES = {
    'R1_sparse':   dict(nsrc=40, obl=(1, 3), tier=3.0, bands=(0.05, 0.40), ngroups=5, hub=0.0, spread2=False),
    'R2_complement': dict(nsrc=10, obl=(2, 4), tier=3.0, bands=(0.05, 0.40), ngroups=4, hub=0.0, spread2=True),
    'R3_hetero':   dict(nsrc=25, obl=(1, 5), tier=8.0, bands=(0.02, 0.60), ngroups=6, hub=0.0, spread2=False),
    'R4_hub':      dict(nsrc=12, obl=(1, 4), tier=4.0, bands=(0.05, 0.45), ngroups=4, hub=0.50, spread2=False),
}

def gen(seed, regime, nq=25):
    cfg = REGIMES[regime]
    rng = random.Random(seed)
    queries = [f'q{j}' for j in range(nq)]
    obl = {q: [f'o{t}' for t in range(rng.randint(*cfg['obl']))] for q in queries}
    pairs = [(q, o) for q in queries for o in obl[q]]
    sources = [f'S{t}' for t in range(cfg['nsrc'])]
    groups = [f'G{t}' for t in range(cfg['ngroups'])]
    src_group = {s: rng.choice(groups) for s in sources}
    lo, hi = cfg['bands']
    cpf = {g: rng.uniform(lo, hi) for g in groups}
    # primary source per pair (R2: round-robin across >=2 sources per query)
    primary = {}
    if cfg['spread2']:
        for q in queries:
            shuf = sources[:]; rng.shuffle(shuf)
            for k, o in enumerate(obl[q]):
                primary[(q, o)] = shuf[k % max(2, len(shuf) // 2)]
    elif cfg['hub'] > 0:
        hub_src = sources[:max(1, cfg['nsrc'] // 6)]
        for pr in pairs:
            primary[pr] = rng.choice(hub_src) if rng.random() < cfg['hub'] else rng.choice(sources)
    else:
        for pr in pairs: primary[pr] = rng.choice(sources)
    pc = {pr: src_group[primary[pr]] for pr in pairs}
    own = {}
    for pr in pairs: own.setdefault(primary[pr], []).append(pr)
    items = {}
    for s, sprs in own.items():
        by_q = {}
        for pr in sprs: by_q.setdefault(pr[0], []).append(pr)
        full_cost = 0.0
        for q, qprs in by_q.items():
            qprs = sorted(qprs)
            half = qprs[:max(1, (len(qprs) + 1) // 2)] if len(qprs) > 1 else qprs
            c = round(rng.uniform(1.0, 2.0) + 0.5 * len(half), 2)
            items[f'{s}~{q}'] = {'cost': c, 'resolves': set(half)}
            full_cost += c
        items[f'{s}~FULL'] = {'cost': round(full_cost * cfg['tier'] / max(1, len(by_q)), 2),
                              'resolves': set(sprs)}
    covered = set()
    for it in items.values(): covered |= it['resolves']
    for j, pr in enumerate(p for p in pairs if p not in covered):
        items[f'repair{j}'] = {'cost': 3.0, 'resolves': {pr}}
    inst = W.Instance(queries, obl, items, pc, cpf, name=f'podD_{regime}_{seed}')
    B = float(round(0.40 * sum(it['cost'] for it in items.values())))
    return inst, B
