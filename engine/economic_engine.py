"""HERMES economic intelligence: deterministic, auditable release analysis.

No fabricated forecasts, observed market moves, AI claims or live data. Stdlib only.
Inputs are explicitly attributed release records; sources must be independently validated.
"""
import datetime as dt
import json
import math
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
OFFICIAL={
 'ecb.europa.eu':'ECB','sdw-wsrest.ecb.europa.eu':'ECB',
 'federalreserve.gov':'Federal Reserve','bls.gov':'BLS',
 'bea.gov':'BEA','census.gov':'US Census', 'eurostat.ec.europa.eu':'Eurostat',
 'ec.europa.eu':'European Commission', 'bankofengland.co.uk':'Bank of England',
 'ons.gov.uk':'ONS','boj.or.jp':'Bank of Japan',
 'stat.go.jp':'Statistics Bureau Japan','eia.gov':'EIA',
}
# Sign: impact of HIGHER-than-expected release on the base currency under
# simple ceteris-paribus monetary-policy / growth interpretation. Not predictions.
INDICATORS={
 'cpi':('inflation',1),'core_cpi':('inflation',1),'ppi':('inflation',1),
 'pce':('inflation',1),'core_pce':('inflation',1),
 'policy_rate':('policy',1),'nonfarm_payrolls':('labour',1),
 'unemployment_rate':('labour',-1),'gdp_growth':('growth',1),
 'retail_sales':('growth',1),'industrial_production':('growth',1),
}
# USD bullish: USD quoted first -> up; USD quoted second -> down.
# XAUUSD, NAS100, BTCUSD are only tentative policy-sensitive heuristics.
PAIRS={'USD':{'EURUSD':-1,'GBPUSD':-1,'USDJPY':1,'XAUUSD':-1,'NAS100':-1,'BTCUSD':-1},
       'EUR':{'EURUSD':1,'EURGBP':1},
       'GBP':{'GBPUSD':1,'EURGBP':-1},
       'JPY':{'USDJPY':-1}}

class InvalidRelease(ValueError): pass

def number(v):
    if isinstance(v,bool) or v is None: raise InvalidRelease('Numeric field missing')
    try: d=Decimal(str(v))
    except (InvalidOperation,ValueError): raise InvalidRelease('Invalid number')
    if not d.is_finite(): raise InvalidRelease('Nonfinite number')
    return d

def timestamp(v):
    try: d=dt.datetime.fromisoformat(str(v).replace('Z','+00:00'))
    except ValueError: raise InvalidRelease('Invalid timestamp')
    if d.tzinfo is None: raise InvalidRelease('Timezone required')
    return d.astimezone(dt.timezone.utc)

def official(url):
    try: p=urlsplit(url)
    except ValueError: return None
    if p.scheme!='https' or p.username or p.password or p.port not in (None,443):return None
    host=(p.hostname or '').lower()
    # Exact host / validated subdomain only, not substring matches.
    for domain,org in OFFICIAL.items():
        if host==domain or host.endswith('.'+domain):return org
    return None

def source(url):
    try:p=urlsplit(url)
    except ValueError:return False
    return p.scheme=='https' and bool(p.hostname) and not (p.username or p.password)

def sessions(moment):
    result={}
    for name,zone,start,end in [('London','Europe/London',8,16),('New York','America/New_York',8,17)]:
        local=moment.astimezone(ZoneInfo(zone))
        result[name]={'local_time':local.isoformat(),'active':local.weekday()<5 and start<=local.hour<end}
    return result

def fmt(d):return format(d.normalize(),'f') if d else '0'

def analyse(record):
    if not isinstance(record,dict):raise InvalidRelease('Release must be object')
    indicator=record.get('indicator')
    if indicator not in INDICATORS:raise InvalidRelease('Unsupported indicator')
    currency=record.get('currency')
    if currency not in PAIRS:raise InvalidRelease('Unsupported currency')
    primary=record.get('official_url','')
    org=official(primary)
    if not org:raise InvalidRelease('Official source not in allowlist')
    released=timestamp(record.get('released_at'))
    period=str(record.get('period','')).strip()
    if not period or len(period)>80:raise InvalidRelease('Period required')
    unit=record.get('unit')
    if unit not in ('percent','percentage_points','index','thousands','persons','basis_points','currency','count'):
        raise InvalidRelease('Unit not supported')
    actual=number(record.get('actual'))
    previous=number(record['previous']) if record.get('previous') is not None else None
    forecast=None; forecast_source=None; surprise=None
    if record.get('forecast') is not None:
        forecast_source=record.get('forecast_source_url')
        if not isinstance(forecast_source,str) or not source(forecast_source):
            raise InvalidRelease('Forecast requires an attributed HTTPS source')
        asof=timestamp(record.get('forecast_asof'))
        if asof>=released:raise InvalidRelease('Forecast must predate release')
        forecast=number(record['forecast'])
        surprise=actual-forecast
    elif record.get('forecast_source_url') or record.get('forecast_asof'):
        raise InvalidRelease('Forecast provenance without forecast')
    if record.get('previous_revised') is not None and previous is None:
        raise InvalidRelease('Revised previous requires original previous')
    revised=number(record['previous_revised']) if record.get('previous_revised') is not None else None
    # Do not compare incomparable periods: caller must explicitly label indicator units.
    impact_sign=INDICATORS[indicator][1]
    theoretical={}
    if surprise is not None:
        for asset,base in PAIRS[currency].items():
            direction=impact_sign*base*(1 if surprise>0 else -1 if surprise<0 else 0)
            theoretical[asset]={'direction':'up' if direction>0 else 'down' if direction<0 else 'neutral',
                'basis':'conditional_macro_heuristic', 'observed_move':None,
                'confidence':'low', 'warning':'Not a prediction; no price movement measured. Other forces may dominate.'}
    # Percent difference can be misleading when forecast is zero or negative.
    relative=fmt((surprise/abs(forecast))*100) if surprise is not None and forecast!=0 else None
    return {'id':str(record.get('id',''))[:100], 'indicator':indicator,'currency':currency,
      'period':period,'unit':unit,'released_at':released.isoformat(),
      'official':{'institution':org,'url':primary,'status':'source_attributed_not_live_verified'},
      'actual':fmt(actual),'previous':fmt(previous) if previous is not None else None,
      'previous_revised':fmt(revised) if revised is not None else None,
      'forecast':fmt(forecast) if forecast is not None else None,
      'forecast_source_url':forecast_source,
      'surprise':fmt(surprise) if surprise is not None else None,
      'surprise_relative_percent':relative,
      'surprise_direction':('above' if surprise>0 else 'below' if surprise<0 else 'in_line') if surprise is not None else 'unavailable',
      'sessions':sessions(released),'theoretical_movements':theoretical,
      'observed_market_reaction':'not_measured',
      'verification':'official_url_attributed_values_not_independently_retrieved',
      'caveat':'Official releases establish reported values, not causal market outcomes. Forecasts require separate provenance.'}

def compact(result):
    keys=('indicator','currency','period','unit','released_at','actual','forecast','previous','previous_revised','surprise','surprise_direction')
    return {k:result[k] for k in keys} | {'source':result['official']['url'],'theory':{k:v['direction'] for k,v in result['theoretical_movements'].items()}}

def build(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('releases'),list):
        raise InvalidRelease('Expected releases array')
    out=[]; errors=[]
    for i,r in enumerate(payload['releases'][:500]):
        try:out.append(analyse(r))
        except (InvalidRelease,TypeError,OverflowError) as exc:errors.append({'index':i,'reason':str(exc)[:160]})
    try:
        from .grounded_brief import build_briefs
    except ImportError:
        from grounded_brief import build_briefs
    return {'briefs':build_briefs({'releases':out}), 'schema_version':1,'mode':'deterministic_official_release_intelligence',
            'releases':out,'rejected':errors,'ai_inputs':[compact(x) for x in out],
            'ai_status':'no_model_inference_performed'}

def main():
    path=ROOT/'data'/'economic_releases.json'
    if not path.exists():
        print('No verified release input. Engine operational, no economic data fabricated.')
        return
    output=build(json.loads(path.read_text(encoding='utf-8')))
    dest=ROOT/'data'/'economic_intelligence.json'
    dest.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Economic engine: {len(output['releases'])} releases, {len(output['rejected'])} rejected")

if __name__=='__main__':main()
