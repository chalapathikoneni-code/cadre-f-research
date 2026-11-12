"""Build the EPA AirData replay tables (see PROTOCOL.md).

Inputs (raw/): daily_88101_2024.csv, daily_88101_2025.csv, aqs_monitors.csv
Outputs (tables/):
  monitor_days_2025.csv  mon,site,date,month,rec_bytes,reg,method,complete,event
  file_bytes_2025.csv    site,month,bytes
  reg_bytes.csv          site,bytes
  pfail_monitor.csv      mon,reg,method,complete      (smoothed 2024 estimates)
  pfail_site_event.csv   site,event                    (smoothed 2024 estimates)
  global_rates.csv       obligation,rate_2024,rate_2025
Usage: python prep_epa.py RAW_DIR OUT_DIR [PARAM]   (PARAM: AQS parameter code, default 88101)
"""
import csv
import os
import sys
from collections import defaultdict

RAW, OUT = sys.argv[1], sys.argv[2]
PARAM = sys.argv[3] if len(sys.argv) > 3 else '88101'
os.makedirs(OUT, exist_ok=True)
SMOOTH = 10.0
OBL = ('reg', 'method', 'complete', 'event')


def lines_with_bytes(path):
    """Yield (row_dict, nbytes) for each data line, nbytes = UTF-8 length incl. newline."""
    with open(path, 'rb') as fh:
        header = next(csv.reader([fh.readline().decode('utf-8')]))
        for raw in fh:
            row = next(csv.reader([raw.decode('utf-8')]))
            yield dict(zip(header, row)), len(raw)


# ---- registry: 88101 monitors and per-site registry bytes (all parameters)
reg = {}
reg_bytes = defaultdict(int)
for r, nb in lines_with_bytes(os.path.join(RAW, 'aqs_monitors.csv')):
    site = f"{r['State Code']}-{r['County Code']}-{r['Site Number']}"
    reg_bytes[site] += nb
    if r['Parameter Code'] == PARAM:
        reg[f"{site}-{r['POC']}"] = (r['First Year of Data'], r['Last Sample Date'], r['Last Method Code'])


def monitor_days(path):
    """Aggregate daily rows to monitor-days with the four real outcomes."""
    md = {}
    for r, nb in lines_with_bytes(path):
        site = f"{r['State Code']}-{r['County Code']}-{r['Site Num']}"
        mon = f"{site}-{r['POC']}"
        key = (mon, r['Date Local'])
        try:
            obs = float(r['Observation Percent'])
        except ValueError:
            obs = 0.0
        x = md.get(key)
        if x is None:
            x = md[key] = dict(mon=mon, site=site, date=r['Date Local'], bytes=0,
                               best_obs=-1.0, method=None, event_fail=False)
        x['bytes'] += nb
        if obs > x['best_obs']:
            x['best_obs'], x['method'] = obs, r['Method Code']
        if r['Event Type'] != 'None':
            x['event_fail'] = True
    for x in md.values():
        info = reg.get(x['mon'])
        if info is None:
            x['reg'] = x['method_ok'] = False
        else:
            first, last, lmeth = info
            yr = int(x['date'][:4])
            x['reg'] = (not first or int(first) <= yr) and (not last or x['date'] <= last)
            x['method_ok'] = (x['method'] == lmeth)
        x['complete'] = x['best_obs'] >= 75.0
    return md


def outcomes(x):
    """1 = fail, 0 = pass, per obligation."""
    return dict(reg=int(not x['reg']), method=int(not x['method_ok']),
                complete=int(not x['complete']), event=int(x['event_fail']))


md24 = monitor_days(os.path.join(RAW, f'daily_{PARAM}_2024.csv'))
md25 = monitor_days(os.path.join(RAW, f'daily_{PARAM}_2025.csv'))

# ---- 2024 estimates
cnt_mon = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # mon -> obl -> [k, n]
site_day_event = defaultdict(bool)
glob = {o: [0, 0] for o in OBL}
for x in md24.values():
    o = outcomes(x)
    for ob in ('reg', 'method', 'complete'):
        cnt_mon[x['mon']][ob][0] += o[ob]
        cnt_mon[x['mon']][ob][1] += 1
        glob[ob][0] += o[ob]
        glob[ob][1] += 1
    site_day_event[(x['site'], x['date'])] |= bool(o['event'])
cnt_site = defaultdict(lambda: [0, 0])
for (site, _), f in site_day_event.items():
    cnt_site[site][0] += int(f)
    cnt_site[site][1] += 1
    glob['event'][0] += int(f)
    glob['event'][1] += 1
g24 = {o: glob[o][0] / glob[o][1] for o in OBL}


def smooth(k, n, g):
    return (k + SMOOTH * g) / (n + SMOOTH)


with open(os.path.join(OUT, 'pfail_monitor.csv'), 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['mon', 'reg', 'method', 'complete'])
    for mon, c in cnt_mon.items():
        w.writerow([mon] + [round(smooth(c[o][0], c[o][1], g24[o]), 6) for o in ('reg', 'method', 'complete')])
with open(os.path.join(OUT, 'pfail_site_event.csv'), 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['site', 'event'])
    for site, (k, n) in cnt_site.items():
        w.writerow([site, round(smooth(k, n, g24['event']), 6)])

# ---- 2025 tables
g25 = {o: [0, 0] for o in OBL}
file_bytes = defaultdict(int)
with open(os.path.join(OUT, 'monitor_days_2025.csv'), 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['mon', 'site', 'date', 'month', 'rec_bytes'] + list(OBL))
    for x in md25.values():
        o = outcomes(x)
        for ob in OBL:
            g25[ob][0] += o[ob]
            g25[ob][1] += 1
        file_bytes[(x['site'], x['date'][:7])] += x['bytes']
        w.writerow([x['mon'], x['site'], x['date'], x['date'][:7], x['bytes']] + [o[ob] for ob in OBL])
with open(os.path.join(OUT, 'file_bytes_2025.csv'), 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['site', 'month', 'bytes'])
    for (s, m), b in file_bytes.items():
        w.writerow([s, m, b])
with open(os.path.join(OUT, 'reg_bytes.csv'), 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['site', 'bytes'])
    for s, b in reg_bytes.items():
        w.writerow([s, b])
with open(os.path.join(OUT, 'global_rates.csv'), 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['obligation', 'rate_2024', 'rate_2025'])
    for o in OBL:
        w.writerow([o, round(g24[o], 5), round(g25[o][0] / g25[o][1], 5)])
print('monitor-days 2024', len(md24), '2025', len(md25))
print(open(os.path.join(OUT, 'global_rates.csv')).read())
