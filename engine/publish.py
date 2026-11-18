"""Publish a bounded, explicitly UNVERIFIED metadata-only snapshot for static hosting.

No speculative impact, location, factual corroboration or AI-generated assertions.
"""
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from relevance import ROOT, WATCHLIST
from evidence import extract, provenance
from geography import locate
from intelligence import audit

MAX_ITEMS = 180
MAX_BYTES = 650_000
TTL_DAYS = 30


def utc(value):
    if not isinstance(value, str): return None
    try:
        result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return result.astimezone(dt.timezone.utc) if result.tzinfo else None
    except ValueError: return None


def safe_link(value):
    if not isinstance(value, str) or len(value)>2000: return None
    p = urlsplit(value)
    return value if p.scheme in ('http','https') and p.hostname else None


def build(discovery, relevance, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    if utc(discovery.get('generated_at')) is None or utc(relevance.get('generated_at')) is None:
        raise ValueError('Missing or invalid generation timestamp')
    # Reject stale source snapshots: a failed collection must not masquerade as current news.
    if abs((now-utc(discovery['generated_at'])).total_seconds())>3600:
        raise ValueError('Discovery snapshot is stale')
    if abs((now-utc(relevance['generated_at'])).total_seconds())>3600:
        raise ValueError('Relevance snapshot is stale')
    registry = {s['id']:s for s in json.loads((ROOT/'engine/sources.json').read_text())}
    statuses = discovery.get('sources', [])
    if not any(s.get('status')=='ok' for s in statuses):
        raise ValueError('No successful feed: publication blocked')
    items=[]
    for candidate in relevance.get('candidates', []):
        title = candidate.get('title','')
        if not isinstance(title,str) or not title.strip(): continue
        refs=[]
        for ref in candidate.get('references',[]):
            link=safe_link(ref.get('url'))
            if link and ref.get('source') in registry:
                refs.append({'url':link,'source':registry[ref['source']]['name'][:100]})
        if not refs: continue
        published=utc(next((r.get('published') for r in candidate['references'] if utc(r.get('published'))),None))
        if published and not now-dt.timedelta(days=TTL_DAYS)<=published<=now+dt.timedelta(hours=1): continue
        # Missing dates are retained as undated, never falsely marked as current.
        assets=[x for x in candidate.get('potential_instruments',[]) if x in WATCHLIST]
        topics=[s.get('topic') for s in candidate.get('signals',[]) if isinstance(s.get('topic'),str)]
        items.append({'id':str(candidate.get('id',''))[:64], 'title':re.sub(r'\s+',' ',title).strip()[:300],
            'published':published.isoformat() if published else None,
            'triage':candidate.get('triage') if candidate.get('triage') in ('candidate','review_unmatched') else 'review_unmatched',
            'topics':topics[:8], 'potential_instruments':assets,
            'references':refs[:12], 'verification':'unverified', 'importance':None,
            'country':(locate(title) or {}).get('country'), 'coordinates':(locate(title) or {}).get('coordinates'),
            'geo_precision':(locate(title) or {}).get('precision'), 'geo_verified':False,
            'claims':extract(candidate), 'provenance':provenance(candidate), 'source_audit':audit(candidate), 'facts':[], 'impact':None})
    items.sort(key=lambda r:(r['published'] is not None,r['published'] or ''),reverse=True)
    output={'schema_version':1,'generated_at':now.isoformat(), 'mode':'UNVERIFIED FEED HEADLINES; headline claims and tentative country mentions; no corroboration or market impact',
            'source_health':{'ok':sum(s.get('status')=='ok' for s in statuses),'total':len(statuses)},
            'items':items[:MAX_ITEMS]}
    # Keep only bounded output, even with unexpectedly large titles / URLs.
    while len(json.dumps(output,ensure_ascii=False).encode())>MAX_BYTES and output['items']:
        output['items'].pop()
    return output


def main():
    d=json.loads((ROOT/'data/discovery.json').read_text())
    r=json.loads((ROOT/'data/relevance.json').read_text())
    output=build(d,r)
    target=ROOT/'data/events.json';target.parent.mkdir(exist_ok=True)
    temp=target.with_suffix('.tmp')
    temp.write_text(json.dumps(output,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    temp.replace(target)
    print(f"Published {len(output['items'])} UNVERIFIED headlines, {output['source_health']['ok']} healthy feeds")

if __name__=='__main__': main()
