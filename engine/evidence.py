"""Conservative evidence-linked title claims; no claims of verified article-body facts."""
import re, hashlib
from urllib.parse import urlsplit

ACTION_WORDS=('announces','announced','reports','reported','suspends','suspended','cuts','cut','raises','raised','closes','closed','halts','halted','approves','approved','warns','warned','increases','increased','decreases','decreased','anuncia','anunciou','suspende','suspendeu','aprova','aprovou','fecha','fechou')
WIRE_NAMES=('reuters','associated press','ap news','afp','agence france-presse','bloomberg')
def extract(candidate):
    title=str(candidate.get('title','')).strip()
    refs=candidate.get('references',[])
    if not title or not refs: return []
    if '?' in title or re.search(r'\b(?:may|might|could|possibly|rumou?rs?|allegedly|supostamente|alegadamente|poder[aá]|talvez)\b',title,re.I):return []
    # Headline evidence is an assertion by a publisher, not an independently confirmed fact.
    normalized=' '.join(re.findall(r'\w+',title.casefold()))
    if not any(re.search(r'(?<!\w)'+re.escape(word)+r'(?!\w)',normalized) for word in ACTION_WORDS): return []
    evidence=[]
    for ref in refs[:8]:
        url=ref.get('url','')
        if urlsplit(url).scheme not in ('http','https'): continue
        evidence.append({'source':ref.get('source',''), 'url':url})
    if not evidence: return []
    return [{'id':hashlib.sha256(normalized.encode()).hexdigest()[:16], 'text':title[:300], 'kind':'publisher_headline_claim', 'verification':'unverified', 'evidence':evidence}]

def provenance(candidate):
    refs=candidate.get('references',[])
    domains={urlsplit(r.get('url','')).hostname for r in refs if r.get('url')}
    # Distinct domains are NOT evidence of independent original reporting.
    return {'distinct_domains':len(domains-{None}), 'independent_confirmations':None, 'origin_verified':False}
