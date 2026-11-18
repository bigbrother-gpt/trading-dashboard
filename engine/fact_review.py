"""Evidence-level review of explicitly supplied claims; no automated truth verification.

Claims are supplied as structured observations with source URLs and provenance IDs.
The engine never infers factual claims from headlines or equates different domains
with independent confirmations. A stop suggestion is advisory and conditional.
"""
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]

def normalize_claim(claim):
    return (str(claim.get('subject','')).strip().casefold(),
            str(claim.get('predicate','')).strip().casefold(),
            str(claim.get('value','')).strip().casefold(),
            str(claim.get('unit','')).strip().casefold())

def review(observations, required_independent=2, redundant_limit=3):
    """Review one event's chronologically ordered source observations.

    Each observation: url, origin_id (known upstream origin, else null),
    claims [{subject,predicate,value,unit}]. A unique origin_id is *not*
    proof of independence: caller must explicitly mark independently_verified.
    """
    facts = {}; by_slot = {}; novelty = []; contradictions = []
    redundant_streak = 0
    verified_origins = set()
    for observation in observations:
        url = observation.get('url','')
        origin = observation.get('origin_id')
        new_count = 0
        for claim in observation.get('claims',[]):
            key = normalize_claim(claim)
            if not key[0] or not key[1] or not key[2]:
                continue
            slot = (key[0],key[1],key[3])
            if slot in by_slot and key not in by_slot[slot]:
                contradictions.append({'source':url,'subject':key[0], 'predicate':key[1],
                                       'different_values':sorted({x[2] for x in by_slot[slot]} | {key[2]})})
            by_slot.setdefault(slot,set()).add(key)
            if key not in facts:
                facts[key] = {'claim':dict(zip(('subject','predicate','value','unit'),key)), 'sources':[]}
                new_count += 1
            if url and url not in facts[key]['sources']:
                facts[key]['sources'].append(url)
        if observation.get('independently_verified') is True and origin:
            verified_origins.add(str(origin))
        redundant_streak = 0 if new_count else redundant_streak + 1
        novelty.append({'source':url,'new_claims':new_count,'redundant_streak':redundant_streak})
    # Independence must be externally established, not guessed from domains.
    enough = len(verified_origins) >= required_independent
    no_conflict = not contradictions
    saturated = redundant_streak >= redundant_limit
    return {'observed_claims':list(facts.values()),'novelty_by_source':novelty,
            'contradictions':contradictions,'verified_independent_origins':len(verified_origins),
            'saturation_observed':saturated,
            'stop_recommended':bool(saturated and enough and no_conflict),
            'status':'advisory_only',
            'warning':'Claims are observations, not verified facts. Independence flags require external evidence. No source retrieval is performed.'}

def main():
    path=ROOT/'data'/'fact_observations.json'
    if not path.exists():
        print('No structured observations supplied; no factual verification or saturation assessment performed.')
        return
    payload=json.loads(path.read_text(encoding='utf-8'))
    output={'events':{key:review(items) for key,items in payload.get('events',{}).items()},
            'mode':'structured evidence review; no automatic fact verification'}
    target=ROOT/'data'/'fact_review.json'
    target.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Reviewed {len(output["events"])} event(s); advisory only')

if __name__=='__main__':
    main()
