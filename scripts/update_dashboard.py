#!/usr/bin/env python3
"""Free daily static market snapshot. No fabricated quotes or event values."""
import html
import json
import logging
import math
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
LISBON = ZoneInfo('Europe/Lisbon')
NOW = datetime.now(timezone.utc)
LOCAL = NOW.astimezone(LISBON)
DAY = LOCAL.date().isoformat()
CALENDAR_URL = 'https://nfs.faireconomy.media/ff_calendar_thisweek.json'
BASE = [('NASDAQ 100 (NDX)', '^NDX'), ('EUR/USD', 'EURUSD=X'),
        ('GBP/USD', 'GBPUSD=X'), ('EUR/GBP', 'EURGBP=X'),
        ('BTC/USD', 'BTC-USD'), ('Gold futures (XAU proxy)', 'GC=F')]
JPY = [('USD/JPY', 'JPY=X'), ('EUR/JPY', 'EURJPY=X'), ('GBP/JPY', 'GBPJPY=X')]
CURRENCIES = {'USD', 'EUR', 'GBP', 'JPY'}
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')


def safe(v):
    return html.escape(str(v), quote=True)


def clean(v, maxlen=160):
    return str(v).strip()[:maxlen] if v is not None else ''


def get_quote(name, ticker):
    result = {'name': name, 'ticker': ticker, 'price': None, 'asof': None,
              'source': 'https://finance.yahoo.com/quote/' + quote(ticker, safe=''),
              'note': 'Daily bar; not a live quote'}
    try:
        history = yf.Ticker(ticker).history(period='10d', interval='1d', auto_adjust=False)
        if history.empty or 'Close' not in history:
            raise ValueError('No daily price returned')
        valid = history.dropna(subset=['Close'])
        if valid.empty:
            raise ValueError('No valid close')
        row = valid.iloc[-1]
        price = float(row['Close'])
        if not math.isfinite(price) or price <= 0:
            raise ValueError('Invalid price')
        bar_time = valid.index[-1].to_pydatetime()
        if bar_time.tzinfo is None:
            raise ValueError('Quote bar has no timezone')
        result['price'] = price
        result['asof'] = bar_time.astimezone(LISBON).strftime('%Y-%m-%d %H:%M %Z')
        if ticker == 'GC=F':
            result['note'] = 'COMEX gold futures proxy; NOT spot XAU/USD'
        elif ticker == 'BTC-USD':
            result['note'] = 'Daily bar; Bitcoin trades 24/7'
        elif ticker == '^NDX':
            result['note'] = 'Index daily bar; US cash market has fixed hours'
    except Exception as exc:
        logging.warning('Quote failed for %s: %s', ticker, exc)
    return result


def calendar_events():
    """Read an unofficial FF-format mirror; its impact fields are NOT FF-verified."""
    note = 'Unofficial public Forex Factory-format calendar mirror; ratings not independently verified with Forex Factory.'
    try:
        response = requests.get(CALENDAR_URL, timeout=20, headers={'User-Agent': 'Mozilla/5.0 (compatible; StaticMarketBrief/1.0)'})
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise ValueError('Unexpected calendar format')
        out = []
        end = NOW + timedelta(hours=72)
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                raw = item.get('date')
                if not raw:
                    continue
                dt = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
                if dt.tzinfo is None or not NOW <= dt.astimezone(timezone.utc) <= end:
                    continue
                curr = clean(item.get('country', ''), 8).upper()
                if curr not in CURRENCIES:
                    continue
                impact_raw = clean(item.get('impact', ''), 25)
                impact = impact_raw.title() if impact_raw.lower() in ('high', 'medium', 'low') else 'Unspecified'
                title = clean(item.get('title') or 'Untitled event', 180)
                local = dt.astimezone(LISBON)
                watches = []
                if curr == 'USD': watches = ['NDX', 'EURUSD', 'GBPUSD', 'BTCUSD', 'XAUUSD', 'USDJPY']
                if curr == 'EUR': watches = ['EURUSD', 'EURGBP', 'EURJPY']
                if curr == 'GBP': watches = ['GBPUSD', 'EURGBP', 'GBPJPY']
                if curr == 'JPY': watches = ['USDJPY', 'EURJPY', 'GBPJPY']
                out.append({'iso': local.isoformat(), 'date': local.strftime('%Y-%m-%d'),
                            'time': local.strftime('%H:%M'), 'currency': curr, 'title': title,
                            'impact': impact, 'forecast': clean(item.get('forecast') or '—', 60),
                            'previous': clean(item.get('previous') or '—', 60),
                            'actual': clean(item.get('actual') or '—', 60), 'watches': watches})
            except (ValueError, TypeError, OverflowError):
                continue
        out.sort(key=lambda e: e['iso'])
        return out, note
    except Exception as exc:
        logging.warning('Calendar fetch failed: %s', exc)
        return [], 'Calendar unavailable at generation time; no events asserted.'


def select_jpy(events):
    # Simple deterministic event relevance score, not a market prediction.
    weights = {'High': 3, 'Medium': 2, 'Low': 1, 'Unspecified': 0}
    scores = {name: 0 for name, _ in JPY}
    for e in events:
        for name in scores:
            base = name.split('/')[0]
            if e['currency'] in (base, 'JPY'):
                scores[name] += weights.get(e['impact'], 0)
    chosen = max(JPY, key=lambda p: (scores[p[0]], -JPY.index(p)))
    rationale = ('Selected using upcoming 72-hour calendar impact scores for each pair’s currencies; '
                 'ties default to USD/JPY. This is not a volatility forecast.')
    return chosen, rationale


def format_price(q):
    if q['price'] is None:
        return 'Unavailable'
    return f"{q['price']:,.5f}" if q['price'] < 100 else f"{q['price']:,.2f}"


def make_html(quotes, events, note, jpy_reason):
    cards = []
    for q in quotes:
        cards.append(f'''<article class="tile"><div class="sub">{safe(q['name'])}</div>
          <div class="price">{safe(format_price(q))}</div><div class="muted">{safe(q['note'])}</div>
          <div class="muted">Bar timestamp (Lisbon): {safe(q['asof'] or 'unavailable')}</div>
          <a href="{safe(q['source'])}" target="_blank" rel="noopener noreferrer">Source ↗</a></article>''')
    rows = []
    for e in events:
        affected = ', '.join(e['watches'])
        rows.append(f'''<tr data-currency="{safe(e['currency'])}" data-impact="{safe(e['impact'])}" data-search="{safe((e['title']+' '+affected).lower())}" data-date="{safe(e['date'])}" data-iso="{safe(e['iso'])}">
          <td>{safe(e['date'])} {safe(e['time'])}</td><td>{safe(e['currency'])}</td>
          <td><details><summary>{safe(e['title'])}</summary><small>Watch: {safe(affected)}. Conditional reaction depends on the actual-versus-forecast surprise, liquidity and broader market context.</small></details></td>
          <td><span class="impact {safe(e['impact'].lower())}">{safe(e['impact'])}*</span></td>
          <td>{safe(e['forecast'])}</td><td>{safe(e['previous'])}</td><td>{safe(e['actual'])}</td><td>{safe(affected)}</td></tr>''')
    priority = sorted(events, key=lambda e: ({'High': 3, 'Medium': 2, 'Low': 1}.get(e['impact'], 0), e['iso']), reverse=True)[:4]
    priorities = ''.join(f'<li><b>{safe(e["impact"])}*</b> · {safe(e["date"])} {safe(e["time"])} Lisbon · {safe(e["currency"])} — {safe(e["title"])}</li>' for e in priority) or '<li>No verified upcoming events available from the feed.</li>'
    table = ''.join(rows) or '<tr><td colspan="8">No events available from the feed for the next 72 hours. This does not mean no events are scheduled.</td></tr>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trading Intelligence · {safe(DAY)}</title><style>
:root{{color-scheme:dark;font-family:system-ui,Arial,sans-serif;background:#080e1a;color:#e7effb}}*{{box-sizing:border-box}}body{{margin:0;padding:20px;max-width:1550px;margin-inline:auto}}h1{{font-size:clamp(22px,3vw,32px);margin:0}}h2{{font-size:18px;margin-top:28px}}p,li{{line-height:1.5}}.muted,.sub,small{{color:#a7b7cc;font-size:12px}}.lead{{color:#b7c9e1}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(195px,1fr));gap:12px}}.tile,.panel{{border:1px solid #293a53;background:#101b2d;border-radius:12px;padding:15px}}.price{{font-size:25px;font-weight:750;margin:10px 0}}a{{color:#89b9ff}}.controls{{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0}}select,input{{background:#172840;border:1px solid #405675;border-radius:8px;padding:10px;color:white;min-width:130px}}.tablewrap{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;min-width:930px;font-size:13px}}th,td{{padding:10px;border-bottom:1px solid #283750;text-align:left;vertical-align:top}}th{{cursor:pointer;color:#c5dcff;white-space:nowrap}}tr:hover{{background:#14233a}}.impact{{font-weight:700}}.high{{color:#ff818a}}.medium{{color:#ffd18a}}.low{{color:#8bdeb2}}summary{{cursor:pointer}}.foot{{margin-top:24px;font-size:12px;color:#b4c1d1}}.stamp{{display:inline-block;background:#1c304a;border-radius:20px;padding:6px 10px;margin:10px 0}}@media(max-width:600px){{body{{padding:12px}}.controls>*{{flex:1 1 40%}}}}
</style></head><body>
<h1>◈ Daily Trading Intelligence</h1><p class="lead">Fixed reference snapshot · {safe(DAY)} · Lisbon time · No live charts</p>
<div class="stamp">Generated {safe(LOCAL.strftime('%Y-%m-%d %H:%M %Z'))} · Prices are last available DAILY bars, not live quotes</div>
<section class="panel"><h2>Top catalysts · next 72 hours</h2><ul>{priorities}</ul><p class="muted">* Impact categories supplied by an unofficial FF-format mirror, not directly verified with Forex Factory.</p></section>
<h2>Reference prices</h2><div class="grid">{''.join(cards)}</div>
<section class="panel" style="margin-top:18px"><b>JPY pair selection</b><p>{safe(jpy_reason)}</p>
<b>Conditional scenarios</b><p><strong>Bullish:</strong> a supportive macro surprise plus confirmation in price action may favor upside. <strong>Bearish:</strong> an adverse surprise plus confirmed downside momentum may favor declines. Neither scenario is a prediction or trade signal.</p>
<p class="muted">Risk: macro surprises, spreads, weekend gaps, futures-versus-spot differences, and stale free data. Confirm prices with your broker before trading.</p></section>
<h2>Economic calendar · next 72 hours</h2><p class="muted">{safe(note)} All event times are Europe/Lisbon. Actual/forecast/previous are shown only when provided.</p>
<div class="controls"><select id="currency"><option value="">All currencies</option><option>USD</option><option>EUR</option><option>GBP</option><option>JPY</option></select>
<select id="impact"><option value="">All impacts</option><option>High</option><option>Medium</option><option>Low</option><option>Unspecified</option></select>
<input id="date" type="date" aria-label="Filter by date"><input id="search" placeholder="Filter instrument / event" aria-label="Filter instrument or event"><button id="reset">Reset</button></div>
<div class="tablewrap"><table><thead><tr><th data-sort="0">Lisbon date/time ↕</th><th data-sort="1">Currency ↕</th><th data-sort="2">Event ↕</th><th data-sort="3">Impact ↕</th><th data-sort="4">Forecast ↕</th><th data-sort="5">Previous ↕</th><th data-sort="6">Actual ↕</th><th data-sort="7">Watched instruments ↕</th></tr></thead><tbody id="rows">{table}</tbody></table></div>
<p class="foot">Sources: <a href="{safe(CALENDAR_URL)}">unofficial public FF-format calendar mirror</a>; linked Yahoo Finance instrument pages. Source timestamps and data availability vary. NDX is an index, not NQ futures; GC=F is gold futures, not spot XAUUSD. Calendar data may be incomplete or blocked. This static snapshot does not auto-refresh.</p>
<script>
const ids=['currency','impact','date','search'];const fields=Object.fromEntries(ids.map(x=>[x,document.getElementById(x)]));
function filter(){{for(const r of document.querySelectorAll('#rows tr')){{if(!r.dataset.currency)continue;const ok=(!fields.currency.value||r.dataset.currency===fields.currency.value)&&(!fields.impact.value||r.dataset.impact===fields.impact.value)&&(!fields.date.value||r.dataset.date===fields.date.value)&&(!fields.search.value||r.dataset.search.includes(fields.search.value.toLowerCase()));r.hidden=!ok;}}}}
ids.forEach(x=>fields[x].addEventListener('input',filter));document.getElementById('reset').onclick=()=>{{ids.forEach(x=>fields[x].value='');filter();}};
let asc=true;document.querySelectorAll('th[data-sort]').forEach(th=>th.addEventListener('click',()=>{{const i=Number(th.dataset.sort),body=document.getElementById('rows');const rows=[...body.querySelectorAll('tr')];rows.sort((a,b)=>{{const x=a.cells[i]?.innerText||'',y=b.cells[i]?.innerText||'';return asc?x.localeCompare(y,undefined,{{numeric:true}}):y.localeCompare(x,undefined,{{numeric:true}});}});rows.forEach(r=>body.appendChild(r));asc=!asc;}}));
</script></body></html>'''


def main():
    events, calendar_note = calendar_events()
    selected, reason = select_jpy(events)
    quotes = [get_quote(*x) for x in BASE + [selected]]
    available = sum(q['price'] is not None for q in quotes)
    if available == 0:
        raise RuntimeError('All quote sources failed; refusing to publish a misleading snapshot')
    output = ROOT / 'archive' / 'trading_dashboard.html'
    manifest_path = ROOT / 'data' / 'latest.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    page = make_html(quotes, events, calendar_note, reason)
    if '<!doctype html>' not in page.lower() or len(page) < 3000:
        raise RuntimeError('Generated HTML failed basic validation')
    output.write_text(page, encoding='utf-8')
    manifest = {'date': DAY, 'file': 'archive/trading_dashboard.html',
                'published_at': NOW.isoformat(timespec='seconds').replace('+00:00', 'Z')}
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Generated {output.relative_to(ROOT)} ({len(page)} chars); {available}/7 quotes; {len(events)} events')
    print(f'Updated manifest: {manifest}')


if __name__ == '__main__':
    main()
