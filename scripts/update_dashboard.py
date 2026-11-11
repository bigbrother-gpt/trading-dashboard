            raise ValueError('No quote returned')
        row = history.dropna(subset=['Close']).iloc[-1]
        ts = history.dropna(subset=['Close']).index[-1]
        return {'name': name, 'ticker': ticker, 'price': float(row['Close']),
                'asof': str(ts), 'source': f'https://finance.yahoo.com/quote/{ticker.replace("=", "%3D")}'}
    except Exception as exc:
        logging.warning('Quote unavailable for %s: %s', ticker, exc)
        return {'name': name, 'ticker': ticker, 'price': None, 'asof': None,
                'source': f'https://finance.yahoo.com/quote/{ticker.replace("=", "%3D")}'}


def calendar_events():
    """Unofficial public Forex Factory mirror; not guaranteed, and no FF impact inferred."""
    try:
        response = requests.get(CALENDAR_URL, timeout=18,
                                headers={'User-Agent': 'TradingDashboard/1.0 (public research)'})
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError('Unexpected calendar format')
        events = []
        for item in payload:
            try:
                raw = item.get('date')
                if not raw:
                    continue
                dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    continue  # Never guess an event's timezone.
                local = dt.astimezone(LISBON)
                if local.date() != LOCAL.date():
                    continue
                events.append({
                    'time': local.strftime('%H:%M'),
                    'currency': str(item.get('country', '—'))[:12],
                    'title': str(item.get('title', 'Untitled event'))[:180],
                    'impact': str(item.get('impact', 'Unspecified'))[:30],
                    'forecast': str(item.get('forecast') or '—')[:60],
                    'previous': str(item.get('previous') or '—')[:60],
                })
            except (ValueError, TypeError, AttributeError):
                continue
        return sorted(events, key=lambda e: e['time']), 'Unofficial public calendar mirror (not verified directly against Forex Factory)'
    except Exception as exc:
        logging.warning('Calendar unavailable: %s', exc)
        return [], 'Calendar unavailable; no event data asserted'


def esc(value):
    return html.escape(str(value), quote=True)


def make_html(quotes, events, calendar_note):
    quote_cards = []
    for q in quotes:
        val = 'Unavailable' if q['price'] is None else f"{q['price']:,.5f}" if q['price'] < 100 else f"{q['price']:,.2f}"
        timestamp = q['asof'] or 'No timestamp available'
        quote_cards.append(f'''<article class="tile" data-search="{esc(q['name'])}">
          <h2>{esc(q['name'])}</h2><div class="price">{esc(val)}</div>
          <small>Last available daily close: {esc(timestamp)}</small>
          <p><a href="{esc(q['source'])}" target="_blank" rel="noopener">Yahoo Finance source ↗</a></p></article>''')
    event_rows = ''.join(f'''<tr><td>{esc(e['time'])}</td><td>{esc(e['currency'])}</td>
        <td>{esc(e['title'])}</td><td>{esc(e['impact'])}</td><td>{esc(e['forecast'])}</td>
        <td>{esc(e['previous'])}</td></tr>''' for e in events)
    if not event_rows:
        event_rows = '<tr><td colspan="6">No events available from the free feed for this Lisbon date. This does not mean no events are scheduled.</td></tr>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Trading Intelligence — {DAY}</title>
<style>
:root{{color-scheme:dark;font-family:Inter,system-ui,Arial,sans-serif;background:#080f1e;color:#e9f0fc}}
*{{box-sizing:border-box}}body{{margin:0;padding:26px;max-width:1320px;margin:auto}}
h1{{font-size:clamp(24px,3vw,36px);margin:0 0 8px}}h2{{font-size:16px;margin:0 0 14px}}
p,small{{color:#aebdd2;line-height:1.5}}a{{color:#7cc8ff}}
.lead{{margin-bottom:24px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}}
.tile,.panel{{background:#121e33;border:1px solid #2b3d58;border-radius:14px;padding:18px}}
.price{{font-size:29px;font-weight:750;letter-spacing:-.5px;margin-bottom:12px}}
.panel{{margin-top:22px;overflow:auto}}table{{width:100%;border-collapse:collapse;min-width:690px;text-align:left}}
th,td{{padding:11px;border-bottom:1px solid #2b3d58;font-size:13px;vertical-align:top}}th{{color:#8fb1d3}}
.note{{background:#19283b;border-left:3px solid #6fa8dc;padding:12px;border-radius:6px}}
input{{background:#15243a;color:white;border:1px solid #42536b;border-radius:8px;padding:11px;width:100%;max-width:350px;margin:10px 0 18px}}
</style></head><body>
<h1>Trading Intelligence</h1><p class="lead">Daily fixed-reference snapshot · {esc(DAY)} · Generated {esc(LOCAL.strftime('%Y-%m-%d %H:%M %Z'))} (Europe/Lisbon)</p>
<p class="note"><strong>Data integrity:</strong> Prices below are last available daily closes, not live quotes or midnight execution prices. Gold is a futures proxy (GC=F), not spot XAU/USD. Market data may be delayed, stale, or unavailable. No automated trading signals are implied.</p>
<input id="filter" placeholder="Filter instruments…" aria-label="Filter instruments">
<section class="grid" id="quotes">{''.join(quote_cards)}</section>
<section class="panel"><h2>Today's economic calendar · Lisbon time</h2>
<p>{esc(calendar_note)}. Impact labels, when available, are feed-provided and unverified; not independently assessed. Forecasts and previous values may be missing.</p>
<table><thead><tr><th>Time</th><th>Currency</th><th>Event</th><th>Feed impact</th><th>Forecast</th><th>Previous</th></tr></thead><tbody>{event_rows}</tbody></table>
<p><a href="https://www.forexfactory.com/calendar" target="_blank" rel="noopener">Check the official Forex Factory calendar ↗</a></p></section>
<section class="panel"><h2>Scenario framework (not a forecast)</h2>
<p><strong>Bullish condition:</strong> Look for confirmed upward price structure and supportive economic surprises after the event release.</p>
<p><strong>Bearish condition:</strong> Look for confirmed downward price structure and adverse economic surprises after the event release.</p>
<p><strong>Risk:</strong> At midnight Lisbon, several markets are closed or illiquid. Recheck current quotes, spreads, economic-release times, and your risk limits before any trade.</p></section>
<script>document.getElementById('filter').addEventListener('input',e=>{{const s=e.target.value.toLowerCase();document.querySelectorAll('#quotes .tile').forEach(x=>x.hidden=!x.dataset.search.toLowerCase().includes(s));}});</script>
</body></html>'''


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    quotes = [get_quote(*pair) for pair in INSTRUMENTS]
    # Select one JPY pair deterministically by Lisbon calendar date; never claim market-based selection.
    chosen = JPY_CANDIDATES[LOCAL.date().toordinal() % len(JPY_CANDIDATES)]
    quotes.append(get_quote(*chosen))
    events, calendar_note = calendar_events()
    if not any(q['price'] is not None for q in quotes):
        raise RuntimeError('No price data retrieved: refusing to publish an empty snapshot')
    filename = f'trading_dashboard_{DAY}.html'
    archive = ROOT / 'archive'
    data = ROOT / 'data'
    archive.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    (archive / filename).write_text(make_html(quotes, events, calendar_note), encoding='utf-8')
    manifest = {'date': DAY, 'file': f'archive/{filename}', 'published_at': NOW.isoformat()}
    (data / 'latest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Generated {filename}: {sum(q["price"] is not None for q in quotes)} quotes, {len(events)} events')


if __name__ == '__main__':
    main()
