"""Optional zero-API-key CPU model adapter. Disabled by default.

No autonomous factual verification. Explicitly fail closed on model errors.
Requires separately installed transformers + torch and an audited, locally available model.
"""
import os

def availability():
    model=os.getenv('HERMES_LOCAL_MODEL','').strip()
    if not model:return {'enabled':False,'reason':'No model configured; conservative evidence extraction used'}
    try:
        from transformers import pipeline
        classifier=pipeline('zero-shot-classification',model=model,device=-1,local_files_only=True)
        return {'enabled':True,'classifier':classifier,'model':model}
    except Exception as exc:
        return {'enabled':False,'reason':type(exc).__name__+': model unavailable'}

def advisory_topics(headlines, engine):
    if not engine.get('enabled'):return []
    labels=['monetary policy','energy supply','trade and logistics','macroeconomics','banking risk','technology','digital assets','geopolitics']
    try:
        return [engine['classifier'](h,candidate_labels=labels,multi_label=True) for h in headlines[:20]]
    except Exception:
        return []
