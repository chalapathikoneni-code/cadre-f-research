import csv,statistics,collections,math,sys
from pathlib import Path
results_path=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/cadre_holdout_results.csv')
rows=list(csv.DictReader(results_path.open()))
by=collections.defaultdict(list)
for row in rows:
    key=(row['phase'],row['regime'],int(row['nqueries']),int(row['seed']),float(row['budget_frac']),row['policy'])
    by[key].append(row)
def mean_se(vals):
    count=len(vals);mu=statistics.mean(vals)
    se=statistics.stdev(vals)/math.sqrt(count) if count>1 else float('nan')
    return mu,se

def aggregate(phase,regime,n_queries,bfrac):
    seeds=sorted({key[3] for key in by if key[0]==phase and key[1]==regime and key[2]==n_queries and key[4]==bfrac})
    good=[]
    for seed in seeds:
        vals={pol:by.get((phase,regime,n_queries,seed,bfrac,pol),[]) for pol in ['myopic','cadre-audited','cadre-cover']}
        if not all(vals.values()):continue
        if len(set(len(recs) for recs in vals.values()))>1:continue
        good.append((seed,{pol_name:statistics.mean(int(rec['decided']) for rec in recs) for pol_name,recs in vals.items()},
                     {pol_name:statistics.mean(float(rec['ms_policy_run']) for rec in recs) for pol_name,recs in vals.items()}))
    if not good:return None
    means={pol_name:statistics.mean(row[1][pol_name] for row in good) for pol_name in ['myopic','cadre-audited','cadre-cover']}
    diffs={pol_name:[row[1]['cadre-cover']-row[1][pol_name] for row in good] for pol_name in ['myopic','cadre-audited']}
    ds={pol_name:mean_se(vals) for pol_name,vals in diffs.items()}
    ts={pol_name:statistics.mean(row[2][pol_name] for row in good) for pol_name in ['myopic','cadre-audited','cadre-cover']}
    wins={pol_name:sum(diff>1e-8 for diff in diffs[pol_name]) for pol_name in diffs}
    losses={pol_name:sum(diff<-1e-8 for diff in diffs[pol_name]) for pol_name in diffs}
    return good,means,ds,ts,wins,losses

print('PRIMARY')
for n_queries in (25,50):
    agg=aggregate('primary','default',n_queries,.4)
    if not agg:continue
    good,means,ds,ts,wins,losses=agg
    print(f'n={n_queries}; independent seeds={len(good)}; means={means}; cover-original diff={ds["cadre-audited"]}; cover-myopic diff={ds["myopic"]}; wins={wins}; losses={losses}; ms={ts}')

print('SENSITIVITY')
for reg in ['share0.05_obl3','share0.8_obl3','share0.3_obl6','share0.8_obl6']:
  for frac in (.25,.60):
    agg=aggregate('sensitivity',reg,50,frac)
    if agg:
      good,means,ds,times,wins,losses=agg
      print(reg,'f',frac,'seeds',len(good),'means',means,'cover-minus-audited',ds['cadre-audited'],'cover-minus-myopic',ds['myopic'],'wins/losses',wins,losses,'ms',times)
print('SCALING')
for n_queries in (100,200,500):
 agg=aggregate('scaling','default',n_queries,.4)
 if agg:
  good,means,ds,times,wins,losses=agg
  print(n_queries,'seeds',len(good),'means',means,'cover-minus-audited',ds['cadre-audited'],'cover-minus-myopic',ds['myopic'],'wins/losses',wins,losses,'ms',times)
