"""Transparent, offline intelligence review; metadata never becomes verified fact.

Explicit observation timestamps avoid mislabelling successive updates as conflicts.
No LLM output is treated as verification and no domain count proves independence.
"""
import datetime as dt
import re
from urllib.parse import urlsplit
from collections import defaultdict

WIRE = ('reuters','associated press','ap news','afp','agence france-presse','bloomberg')

def origin_hint(title):
    t=str(title).casefold()
    matches=[w for w in WIRE if re.search(r'(?<!\w)'+re.escape(w)+r'(?!\w)',t)]
    return matches[0] if matches else None

def audit(candidate):
    refs=candidate.get('references',[])
    urls=set(); hosts=set(); bad=0
    for ref in refs:
        url=ref.get('url','') if isinstance(ref,dict) else ''
        try: p=urlsplit(url)
        except (ValueError,TypeError): bad+=1;continue
        if p.scheme not in ('https','http') or not p.hostname:bad+=1;continue
        urls.add(url);hosts.add(p.hostname.casefold().removeprefix('www.'))
    return {'valid_urls':len(urls),'publisher_hosts':len(hosts),
            'shared_wire_origin_hint':origin_hint(candidate.get('title','')),
            'independent_reporting_confirmed':False,
            'verification':'unverified', 'rejected_links':bad}

def temporal_review(observations):
    """Claims with the same subject/predicate/unit are compared only for same as-of instant.
    Without an as-of timestamp, differences are marked ambiguous, not contradictions.
    """
    slots=defaultdict(list); conflicts=[]; evolutions=[]; ambiguous=[]
    for o in observations:
        for c in o.get('claims',[]):
            if not isinstance(c,dict):continue
            subject=str(c.get('subject','')).strip().casefold()
            predicate=str(c.get('predicate','')).strip().casefold()
            value=str(c.get('value','')).strip().casefold()
            unit=str(c.get('unit','')).strip().casefold()
            asof=c.get('asof')
            if not subject or not predicate or not value:continue
            if asof:
                try:
                    parsed=dt.datetime.fromisoformat(str(asof).replace('Z','+00:00'))
                    asof=parsed.astimezone(dt.timezone.utc).isoformat() if parsed.tzinfo else None
                except ValueError:asof=None
            slot=(subject,predicate,unit)
            for old in slots[slot]:
                if old['value']==value:continue
                record={'subject':subject,'predicate':predicate,'values':[old['value'],value], 'sources':[old['url'],o.get('url','')]}
                if old['asof'] and asof:
                    if old['asof']==asof:conflicts.append(record)
                    else:evolutions.append(record)
                else:ambiguous.append(record)
            slots[slot].append({'value':value,'asof':asof,'url':o.get('url','')})
    return {'same_time_conflicts':conflicts,'time_evolution':evolutions,
            'time_ambiguous_differences':ambiguous,'verified_facts':0,
            'warning':'Unverified source observations; time evolution is not proof of truth.'}
