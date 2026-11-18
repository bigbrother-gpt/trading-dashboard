"""ECB official DAILY reference rates; no real-time quotes, no implied trading prices.
Only currencies quoted against EUR. Derived crosses are mathematical reference ratios.
No prices are invented for gold, Nasdaq-100 or bitcoin.
"""
import csv
import datetime as dt
import io
import json
import math
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
URL="https://data-api.ecb.europa.eu/service/data/EXR/D.USD+GBP+JPY.EUR.SP00.A?format=csvdata&lastNObservations=45"
WINDOWS={'1D':1,'5D':5,'1M':30}

def parse_csv(raw):
    rows={}
    for row in csv.DictReader(io.StringIO(raw)):
        c=row.get('CURRENCY'); d=row.get('TIME_PERIOD'); val=row.get('OBS_VALUE')
        if c not in ('USD','GBP','JPY') or not d or not val:continue
        try:
            date=dt.date.fromisoformat(d); rate=float(val)
        except (ValueError,TypeError):continue
        if not math.isfinite(rate) or rate<=0:continue
        rows.setdefault(date,{})[c]=rate
    return rows

def crosses(rates):
    if not all(x in rates for x in ('USD','GBP','JPY')):return {}
    u,g,j=(rates[x] for x in ('USD','GBP','JPY'))
    return {'EURUSD':u,'EURGBP':g,'GBPUSD':u/g,'USDJPY':j/u}

def snapshot(rows,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    # Do not label stale data as current. ECB publishes reference observations on business days.
    valid=sorted(d for d in rows if d<=now.date() and (now.date()-d).days<=7 and len(crosses(rows[d]))==4)
    if not valid:return {'generated_at':now.isoformat(),'quotes':[],'status':'no_recent_complete_ecb_observations'}
    latest=valid[-1]; quotes=[]; history=sorted(d for d in rows if d<=latest and len(crosses(rows[d]))==4)
    for symbol,value in crosses(rows[latest]).items():
        changes={}
        for window,days in WINDOWS.items():
            # 1D / 5D: preceding ECB observation counts; 1M: nearest observation <= 30 calendar days prior.
            if window=='1M':
                previous=next((d for d in reversed(history) if d<=latest-dt.timedelta(days=30)),None)
            else:
                index=len(history)-1-days
                previous=history[index] if index>=0 else None
            if previous:
                base=crosses(rows[previous])[symbol]
                changes[window]={'points':round(value-base,8),'percent':round((value/base-1)*100,5),'baseline':previous.isoformat()}
        quotes.append({'symbol':symbol,'last':round(value,8),'asof':latest.isoformat(),
            'provider':'European Central Bank (ECB)','kind':'daily_reference_derived' if symbol in ('GBPUSD','USDJPY') else 'daily_reference',
            'rights':'attribution_required_review','changes':changes,'note':'ECB reference rate, not executable or real-time market price'})
    return {'generated_at':now.isoformat(),'status':'reference_rates_only','quotes':quotes,'unavailable':['XAUUSD','NAS100','BTCUSD'],
            'method':'ECB euro reference rates; GBPUSD=EURUSD/EURGBP; USDJPY=EURJPY/EURUSD; 1D and 5D are ECB observations, 1M is calendar-based'}

def main():
    req=urllib.request.Request(URL,headers={'User-Agent':'HERMES-open-source/1.3','Accept':'text/csv'})
    try:
        with urllib.request.urlopen(req,timeout=15) as response:
            raw=response.read(1_000_001)
        if len(raw)>1_000_000:raise ValueError('ECB response too large')
        payload=snapshot(parse_csv(raw.decode('utf-8-sig')))
    except Exception as exc:
        payload={'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'quotes':[], 'status':'unavailable','error':type(exc).__name__}
    target=ROOT/'data/markets.json';target.parent.mkdir(exist_ok=True)
    tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2));tmp.replace(target)
    print('ECB daily reference:',payload['status'],len(payload['quotes']))
if __name__=='__main__':main()
