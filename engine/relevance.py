"""Transparent multilingual triage, not factual verification or market prediction."""
import json, re, unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
WATCHLIST=('XAUUSD','GBPUSD','EURUSD','EURGBP','USDJPY','NAS100','BTCUSD')
RULES={
 'monetary_policy': (['interest rates','rate cut','rate hike','central bank','monetary policy','taxas de juro','política monetária','taux directeur','politique monétaire','zinsentscheidung','leitzins','金融政策','政策金利'], WATCHLIST),
 'energy_supply': (['oil supply','oil production','gas pipeline','oil embargo','refinery shutdown','produção de petróleo','oleoduto','production de pétrole','gazoduc','ölproduktion'], ('XAUUSD','EURUSD','GBPUSD','USDJPY','NAS100')),
 'trade_logistics': (['port closure','port strike','shipping disruption','shipping suspended','trade tariffs','export ban','fecho do porto','greve portuária','droits de douane','grève portuaire','hafensperrung'], ('EURUSD','GBPUSD','USDJPY','NAS100','XAUUSD')),
 'macro_data': (['inflation','consumer prices','unemployment','gross domestic product','payrolls','inflação','desemprego','chômage','arbeitslosigkeit','inflationsrate'], WATCHLIST),
 'systemic_risk': (['bank failure','bank run','sovereign default','capital controls','bank collapse','falência bancária','défaut souverain','bankenkrise'], WATCHLIST),
 'technology_supply': (['chip shortage','semiconductor exports','chip export','semiconductor factory','escassez de semicondutores','semi-conducteurs','halbleiterexport'], ('NAS100','USDJPY','BTCUSD')),
 'digital_assets': (['bitcoin','crypto exchange','stablecoin','cryptocurrency','bitcoin etf','criptomoeda','cryptomonnaie','kryptowährung'], ('BTCUSD','NAS100')),
 'geopolitical_risk': (['military escalation','missile attack','air strikes','ceasefire','sanctions','ataque de mísseis','cessar-fogo','frappe aérienne','cessez-le-feu','waffenstillstand'], ('XAUUSD','USDJPY','EURUSD','GBPUSD','NAS100','BTCUSD')),
}
def norm(s):
    return ' '.join(re.findall(r'\w+', ''.join(c for c in unicodedata.normalize('NFKD',s.casefold()) if not unicodedata.combining(c))))
def matches(s,term):
    t=norm(term)
    if any('\u3040'<=c<='\u9fff' for c in t): return t in s
    return f' {t} ' in f' {s} '
def classify(candidate):
    s=norm(candidate['title']); signals=[]; instruments=set()
    for topic,(terms,assets) in RULES.items():
        hits=[t for t in terms if matches(s,t)]
        if hits: signals.append(dict(topic=topic,matched=hits)); instruments.update(assets)
    direct=[a for a in WATCHLIST if matches(s,a)]
    instruments.update(direct)
    return dict(candidate,triage='candidate' if signals or direct else 'review_unmatched',signals=signals,direct_mentions=direct,potential_instruments=[a for a in WATCHLIST if a in instruments],verification='unverified',importance=None,confidence=None,urgency=None)
def process(payload):
    rows=[classify(c) for c in payload['candidates']]
    return dict(generated_at=payload['generated_at'],mode='rule-based headline triage; no confirmed facts or impact',counts={k:sum(r['triage']==k for r in rows) for k in ('candidate','review_unmatched')},candidates=rows)
def main():
    source=ROOT/'data/discovery.json'; target=ROOT/'data/relevance.json'
    output=process(json.loads(source.read_text())); tmp=target.with_suffix('.tmp'); tmp.write_text(json.dumps(output,ensure_ascii=False,indent=2)); tmp.replace(target); print(output['counts'])
if __name__=='__main__': main()
