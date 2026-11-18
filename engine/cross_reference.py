"""Conservative, auditable headline clustering and cross-reference diagnostics.

This stage does NOT verify facts or assert publisher independence. It never fetches
additional articles. Saturation is advisory until a verified event/fact extractor exists.
"""
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from relevance import norm, ROOT

STOP = {'the','a','an','of','in','on','at','to','for','and','or','with','from','after','as','by','is','are','de','da','do','das','dos','em','no','na','um','uma','et','le','la','les','des','du','der','die','das','und'}

def tokens(title):
    return {x for x in re.findall(r'\w+', norm(title)) if len(x)>2 and x not in STOP}

def similarity(a,b):
    x,y=tokens(a),tokens(b)
    return len(x&y)/len(x|y) if x and y else 0.0

def host(url):
    return (urlsplit(url).hostname or '').lower().removeprefix('www.')

def date_key(item):
    value=next((r.get('published') for r in item.get('references',[]) if r.get('published')),None)
    try: return dt.datetime.fromisoformat(value.replace('Z','+00:00')).date() if value else None
    except (ValueError,AttributeError): return None

def compatible(a,b):
    # Require same nonempty triage topics and strong lexical agreement.
    ta={s['topic'] for s in a.get('signals',[])}
    tb={s['topic'] for s in b.get('signals',[])}
    if not (ta & tb): return False
    da,db=date_key(a),date_key(b)
    if da and db and abs((da-db).days)>2: return False
    return similarity(a['title'],b['title']) >= .82

def build(payload):
    items=sorted(payload['candidates'],key=lambda r:(r.get('title',''),r.get('id','')))
    groups=[]
    for item in items:
        match=next((g for g in groups if compatible(item,g['members'][0])),None)
        if match is None:
            match={'members':[]};groups.append(match)
        match['members'].append(item)
    events=[]
    for g in groups:
        members=g['members']; refs=[]; seen=set()
        for item in members:
            for ref in item.get('references',[]):
                key=ref.get('url')
                if key and key not in seen:
                    seen.add(key); refs.append(ref)
        refs.sort(key=lambda r:(r.get('published') or '',r.get('source') or '',r.get('url') or ''))
        domains=sorted({host(r.get('url','')) for r in refs if host(r.get('url',''))})
        titles=sorted({m['title'] for m in members})
        # No claim that distinct domains are independent: syndicated articles are common.
        # Without article bodies, novelty cannot be inferred from title differences.
        stable_id=hashlib.sha256('|'.join(sorted(m['id'] for m in members)).encode()).hexdigest()[:20]
        events.append({'id':stable_id,'representative_title':titles[0],
            'candidate_ids':[m['id'] for m in members], 'headline_variants':titles,
            'references':refs,'source_domains':domains,'domain_count':len(domains),
            'independent_confirmations':None,'verified_facts':[],
            'novel_facts':None,'saturation':'not_assessable_from_headlines',
            'stop_recommended':False,'reactivation':'recheck_on_new_input',
            'verification':'unverified','notes':'Domain diversity is not independent corroboration; headline similarity is not factual agreement.'})
    return {'generated_at':payload.get('generated_at'),
            'mode':'conservative headline clusters; no factual cross-reference or saturation decisions',
            'event_count':len(events),'events':events}

def main():
    source=ROOT/'data/relevance.json';target=ROOT/'data/cross_reference.json'
    result=build(json.loads(source.read_text()))
    tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2));tmp.replace(target)
    print(f'{result["event_count"]} provisional clusters; no automatic saturation decisions')
if __name__=='__main__': main()
