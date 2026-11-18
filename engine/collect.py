"""Bounded RSS/Atom discovery. No article text, AI or publication of claims."""
import concurrent.futures as cf
import datetime as dt
import email.utils
import hashlib
import json
import re
import unicodedata
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIMIT=2_000_000

def text(node,*names):
    for child in node:
        if child.tag.split('}')[-1] in names and child.text:
            return child.text.strip()
    return ''

def normalize(s):
    return ' '.join(re.findall(r'\w+',unicodedata.normalize('NFKC',s).casefold()))

def date(s):
    try:
        d=dt.datetime.fromisoformat(s.replace('Z','+00:00'))
    except ValueError:
        try: d=email.utils.parsedate_to_datetime(s)
        except (ValueError,TypeError): return None
    if d.tzinfo is None: return None
    return d.astimezone(dt.timezone.utc)

def parse(raw,source,now):
    root=ET.fromstring(raw); rows=[]
    for node in root.iter():
        if node.tag.split('}')[-1] not in ('item','entry'): continue
        title=text(node,'title')[:400]; link=text(node,'link')
        if not link:
            link=next((c.get('href','') for c in node if c.tag.split('}')[-1]=='link' and c.get('rel','alternate')=='alternate'),'')
        if urllib.parse.urlsplit(link).scheme not in ('https','http') or not title: continue
        published=date(text(node,'pubDate','published','updated','date'))
        if published and not now-dt.timedelta(days=30)<=published<=now+dt.timedelta(hours=1): continue
        rows.append(dict(id=hashlib.sha256(normalize(title).encode()).hexdigest()[:24],title=title,url=link,source=source['id'],published=published.isoformat() if published else None,seen=now.isoformat()))
    return rows

def fetch(source,now):
    try:
        req=urllib.request.Request(source['url'],headers={'User-Agent':'HERMES-open-source-research/0.3'})
        with urllib.request.urlopen(req,timeout=12) as r: raw=r.read(LIMIT+1)
        if len(raw)>LIMIT: raise ValueError('feed exceeds size limit')
        rows=parse(raw,source,now); return rows,dict(id=source['id'],status='ok',items=len(rows))
    except Exception as e: return [],dict(id=source['id'],status='error',message=str(e)[:200])

def merge(rows):
    groups={}
    for row in rows:
        g=groups.setdefault(row['id'],dict(id=row['id'],title=row['title'],references=[]))
        if not any(r['url']==row['url'] for r in g['references']): g['references'].append({k:row[k] for k in ('url','source','published','seen')})
    return list(groups.values())

def main():
    now=dt.datetime.now(dt.timezone.utc); sources=json.loads((ROOT/'engine/sources.json').read_text()); rows=[]; health=[]
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        for result,status in pool.map(lambda s:fetch(s,now),sources): rows.extend(result); health.append(status)
    output=dict(generated_at=now.isoformat(),mode='unverified discovery; exact-title grouping only',sources=health,candidates=merge(rows))
    path=ROOT/'data/discovery.json'; path.parent.mkdir(exist_ok=True); tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps(output,ensure_ascii=False,indent=2)); tmp.replace(path)
    print(f'{len(rows)} items; {len(output["candidates"])} title groups; {sum(s["status"]=="ok" for s in health)}/{len(sources)} feeds successful')
    if not any(s['status']=='ok' for s in health): raise SystemExit(1)
if __name__=='__main__': main()
