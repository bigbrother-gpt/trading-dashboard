"""Deterministic score ONLY for independently supplied, explicitly evidenced metrics."""
from decimal import Decimal, InvalidOperation

def score(impact, escalation, strategic):
    values=[]
    for value in (impact, escalation, strategic):
        if isinstance(value,bool) or value is None: raise ValueError('Missing metric')
        try: v=Decimal(str(value))
        except InvalidOperation as e: raise ValueError('Invalid metric') from e
        if not v.is_finite() or not 0<=v<=100: raise ValueError('Metric outside 0..100')
        values.append(v)
    n=values[0]*Decimal('0.50')+values[1]*Decimal('0.30')+values[2]*Decimal('0.20')
    level='Critical' if n>=85 else 'Emerging' if n>=60 else 'Early Signal' if n>=30 else 'Informational'
    return {'score':float(n),'classification':level,'provisional_thresholds':True}
