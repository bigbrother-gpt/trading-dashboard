"""Safe, deterministic brief generation from validated economic engine output.

This is NOT a language model. It never supplies missing market prices or forecasts.
"""

LABELS={'cpi':'CPI','core_cpi':'Core CPI','ppi':'PPI','pce':'PCE','core_pce':'Core PCE','policy_rate':'Policy rate','nonfarm_payrolls':'Nonfarm payrolls','unemployment_rate':'Unemployment rate','gdp_growth':'GDP growth','retail_sales':'Retail sales','industrial_production':'Industrial production'}

def brief(release):
    if release.get('verification') != 'official_url_attributed_values_not_independently_retrieved':
        raise ValueError('Unexpected verification state')
    indicator=release['indicator']
    if indicator not in LABELS: raise ValueError('Unsupported indicator')
    actual=release['actual']; unit=release['unit']; forecast=release.get('forecast')
    result={'headline':f"{release['currency']} {LABELS[indicator]}: {actual} ({unit})",
      'source_url':release['official']['url'], 'released_at':release['released_at'],
      'verification':'Attributed input; source values not independently retrieved',
      'market_reaction':'Not measured; no claim about actual price movement',
      'theoretical_movements':release.get('theoretical_movements',{}),
      'method':'deterministic_template_not_ai_inference'}
    if forecast is None:
        result['interpretation']='Forecast unavailable. Economic surprise and directional inference withheld.'
    else:
        direction=release['surprise_direction']
        result['interpretation']=(f"Actual {actual} versus pre-release forecast {forecast}; "
          f"surprise {release['surprise']} ({unit}), {direction} expectations. "
          'Theoretical asset directions are conditional heuristics, not predictions.')
    return result

def build_briefs(engine_output):
    return [brief(item) for item in engine_output['releases']]
