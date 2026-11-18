"""Safe, evidence-limited interpretation; not a causal inference or trading signal."""
from decimal import Decimal
from economic_engine import InvalidRelease, number

def compare(result, market_observations=None):
    observations=market_observations or {}
    assessments={}
    for asset,theory in result.get('theoretical_movements',{}).items():
        obs=observations.get(asset)
        if obs is None:
            assessments[asset]={'theoretical':theory['direction'],'observed':'unavailable','comparison':'not_testable'}
            continue
        if not isinstance(obs,dict) or not obs.get('source_url') or not obs.get('window'):
            raise InvalidRelease('Observed market move requires source and observation window')
        start=number(obs.get('start'));end=number(obs.get('end'))
        if start<=0 or end<=0:raise InvalidRelease('Market prices must be positive')
        direction='up' if end>start else 'down' if end<start else 'neutral'
        predicted=theory['direction']
        assessments[asset]={'theoretical':predicted,'observed':direction,
            'comparison':'aligned' if predicted==direction else 'divergent' if predicted!='neutral' else 'not_testable',
            'change':str(end-start),'change_percent':str((end-start)/start*Decimal('100')),
            'window':obs['window'],'source_url':obs['source_url'],
            'interpretation':'Divergence does not establish manipulation or any particular cause.'}
    return assessments

def brief(result):
    if result['surprise'] is None:
        return f"{result['indicator']} ({result['currency']}): actual {result['actual']} {result['unit']}; no attributed pre-release consensus. No surprise or theoretical directional movement inferred."
    d=result['surprise_direction']
    return (f"{result['indicator']} ({result['currency']}, {result['period']}): actual {result['actual']} "
            f"vs forecast {result['forecast']} {result['unit']} ({d} by {result['surprise']}). "
            "Asset directions are conditional macro heuristics, not forecasts or observed reactions.")
