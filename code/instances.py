"""Instance families for W-CAEA experiments. F1-F3 are constructed stress
cases; F4 is random scaling; F5 is EPA/EDGAR-shaped (see the F5_* builders
below for their parameters)."""
import os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcaea_fixed import Instance

def F1_claim3(num_obligations=8, mB=3, pfail=0.05):
    """Surrogate completion-blindness (lit-A §5 Claim 3, generalised).
    Query A: K obligations, K cheap items. Queries B_j: 1 obligation, one
    expensive item each (cost K-1). Budget K-1: surrogate-greedy starves B."""
    queries = ['A'] + [f'B{query_idx}' for query_idx in range(mB)]
    obl = {'A': [f'a{obl_idx}' for obl_idx in range(num_obligations)]}
    items, pc, cpf = {}, {}, {}
    for obl_idx in range(num_obligations):
        items[f'eA{obl_idx}'] = {'cost': 1, 'resolves': {('A', f'a{obl_idx}')}}
        pc[('A', f'a{obl_idx}')] = f'gA{obl_idx}'; cpf[f'gA{obl_idx}'] = pfail
    for query_idx in range(mB):
        obl[f'B{query_idx}'] = ['b']
        items[f'eB{query_idx}'] = {'cost': num_obligations - 1, 'resolves': {(f'B{query_idx}', 'b')}}
        pc[(f'B{query_idx}', 'b')] = f'gB{query_idx}'; cpf[f'gB{query_idx}'] = pfail
    return Instance(queries, obl, items, pc, cpf, name='F1_claim3')

def F2_completion_trap(ncheap=6, pfail=0.1):
    """Near-completion trap for true myopic greedy. X has three obligations.
    The cheap item (cost 1) resolves two of them (surrogate ratio 2, strictly
    maximal, so the declared surrogate tie-break picks it first under any
    cost-respecting plateau rule); the expensive item (cost 100) resolves the
    last. pfail = 0 on gx0 and on all Y clusters, so "gain 0 until partner
    bought" holds for the corrected gain function: after eX0, eX1 is the only
    positive-gain item (gain 1, ratio 1/100 > 0) and true myopic greedy must
    buy it, spending budget 101 for 1 decided query, while the optimum decides
    all ncheap Y queries for 2*ncheap."""
    queries = ['X'] + [f'Y{query_idx}' for query_idx in range(ncheap)]
    obl = {'X': ['x0', 'x1', 'x2']}
    items = {'eX0': {'cost': 1, 'resolves': {('X', 'x0'), ('X', 'x1')}},
             'eX1': {'cost': 100, 'resolves': {('X', 'x2')}}}
    pc = {('X', 'x0'): 'gx0', ('X', 'x1'): 'gx0', ('X', 'x2'): 'gx1'}
    cpf = {'gx0': 0.0, 'gx1': pfail}
    for query_idx in range(ncheap):
        obl[f'Y{query_idx}'] = ['y0', 'y1']
        items[f'eY{query_idx}a'] = {'cost': 1, 'resolves': {(f'Y{query_idx}', 'y0')}}
        items[f'eY{query_idx}b'] = {'cost': 1, 'resolves': {(f'Y{query_idx}', 'y1')}}
        pc[(f'Y{query_idx}', 'y0')] = f'gy{query_idx}a'; pc[(f'Y{query_idx}', 'y1')] = f'gy{query_idx}b'
        cpf[f'gy{query_idx}a'] = 0.0; cpf[f'gy{query_idx}b'] = 0.0
    return Instance(queries, obl, items, pc, cpf, name='F2_trap')

def F3_copy_trap(nq=4, pfail=0.2):
    """Dependence/copy trap (lit-B). Each query needs o_val (settled by its
    own copy check, cost 1) and o_origin (settled only by the shared origin
    verification, cost 6; copies cannot settle an origin obligation).
    Coverage planning wastes budget on copies; at B=7 only completion-aware
    targeting decides any query."""
    queries = [f'q{query_idx}' for query_idx in range(nq)]
    obl, items, pc, cpf = {}, {}, {}, {}
    for query_idx in range(nq):
        obl[f'q{query_idx}'] = ['o_val', 'o_origin']
        items[f'copy{query_idx}'] = {'cost': 1, 'resolves': {(f'q{query_idx}', 'o_val')}}
        pc[(f'q{query_idx}', 'o_val')] = f'gc{query_idx}'; cpf[f'gc{query_idx}'] = pfail
        pc[(f'q{query_idx}', 'o_origin')] = 'g_origin'
    cpf['g_origin'] = pfail
    items['origin'] = {'cost': 6, 'resolves': {(f'q{query_idx}', 'o_origin') for query_idx in range(nq)}}
    return Instance(queries, obl, items, pc, cpf, name='F3_copytrap')

def F4_random(nq=25, maxobl=3, share=0.3, pfail=0.2, seed=11, costmax=5):
    rng = random.Random(seed)
    queries = [f'q{query_idx}' for query_idx in range(nq)]
    obl, pc, cpf = {}, {}, {}
    ncl = max(2, int(nq * 0.6))
    clusters = [f'g{cluster_idx}' for cluster_idx in range(ncl)]
    for cluster in clusters: cpf[cluster] = rng.uniform(0.05, 0.4)
    for query in queries:
        n_obl = rng.randint(1, maxobl)
        obl[query] = [f'o{obl_idx}' for obl_idx in range(n_obl)]
        for oblig in obl[query]:
            pc[(query, oblig)] = rng.choice(clusters)
    items = {}
    pairs = [(query, oblig) for query in queries for oblig in obl[query]]
    for pair_idx, pair in enumerate(pairs):
        resolves_set = {pair}
        for other_pair in rng.sample(pairs, k=min(len(pairs), rng.randint(0, 3))):
            if rng.random() < share: resolves_set.add(other_pair)
        items[f'e{pair_idx}'] = {'cost': rng.randint(1, costmax), 'resolves': resolves_set}
    return Instance(queries, obl, items, pc, cpf, name=f'F4_n{nq}_s{seed}')

def F5_epa(nmon=6, ndays=5, seed=3):
    """EPA-shaped: queries = monitor-day questions; obligations from the EPA
    case families {unit, window, identity, completeness}. Items: hourly file
    check per monitor (window+completeness, shared across that monitor's
    days), daily file check per monitor-day (unit), site metadata lookup per
    site (identity, shared). pfail set from observed trap frequencies:
    identity 0.3 (conservative, most monitor-days miskeyed before the fix),
    window 0.15, unit 0.05, completeness 0.1."""
    rng = random.Random(seed)
    queries, obl, items, pc, cpf = [], {}, {}, {}, {}
    for mon_idx in range(nmon):
        items[f'hourly_m{mon_idx}'] = {'cost': 3, 'resolves': set()}
        items[f'meta_m{mon_idx}'] = {'cost': 2, 'resolves': set()}
        for day_idx in range(ndays):
            query = f'm{mon_idx}_d{day_idx}'; queries.append(query)
            obl[query] = ['unit', 'window', 'identity', 'completeness']
            items[f'daily_{query}'] = {'cost': 1, 'resolves': {(query, 'unit')}}
            items[f'hourly_m{mon_idx}']['resolves'] |= {(query, 'window'), (query, 'completeness')}
            items[f'meta_m{mon_idx}']['resolves'] |= {(query, 'identity')}
            pc[(query, 'unit')] = f'gu_{query}'; cpf[f'gu_{query}'] = 0.05
            pc[(query, 'window')] = f'gw_{query}'; cpf[f'gw_{query}'] = 0.15
            pc[(query, 'identity')] = f'gi_m{mon_idx}'; cpf[f'gi_m{mon_idx}'] = 0.3
            pc[(query, 'completeness')] = f'gc_{query}'; cpf[f'gc_{query}'] = 0.1
    return Instance(queries, obl, items, pc, cpf, name='F5_epa')

def F5_edgar():
    """EDGAR-shaped from results/edgar_cases.csv: one query per case;
    obligations per family; items shared per filer (frame lookup) and per
    concept-family check. pfail per family = fraction of cases whose silver
    outcome required abstention-resolving semantics, proxied by the naive
    baseline error rate per family in the case file."""
    import csv as _csv
    fam_err, fam_n, fam_obl = {}, {}, {}
    OBL = {'a_period_calendar': ['period_type', 'frame'], 'b_instant_duration': ['measure_kind', 'period_type'],
           'c_annual_quarterly': ['period_type', 'duration'], 'd_unit_conflict': ['unit', 'scale'],
           'e_amended_duplicates': ['amendment', 'period_type'], 'f_aggregate_quarters': ['aggregation', 'period_type']}
    with open('results/edgar_cases.csv') as csv_file:
        for row in _csv.DictReader(csv_file):
            fam = row['family']; fam_n[fam] = fam_n.get(fam, 0) + 1
            if row['baseline_verdict'] != 'correct': fam_err[fam] = fam_err.get(fam, 0) + 1
    queries, obl, items, pc, cpf = [], {}, {}, {}, {}
    idx = {}
    with open('results/edgar_cases.csv') as csv_file:
        for row in _csv.DictReader(csv_file):
            query = row['case_id']; fam = row['family']; queries.append(query)
            obl[query] = OBL[fam]
            fail_rate = fam_err.get(fam, 0) / fam_n[fam]
            for oblig in OBL[fam]:
                pc[(query, oblig)] = f'g_{fam}_{oblig}'; cpf[f'g_{fam}_{oblig}'] = round(fail_rate, 3)
            key = f"check_{fam}"
            items.setdefault(key, {'cost': 2, 'resolves': set()})
            for oblig in OBL[fam]: items[key]['resolves'].add((query, oblig))
            fkey = f"frame_{row['cik']}"
            items.setdefault(fkey, {'cost': 3, 'resolves': set()})
            items[fkey]['resolves'].add((query, OBL[fam][0]))
    return Instance(queries, obl, items, pc, cpf, name='F5_edgar')
