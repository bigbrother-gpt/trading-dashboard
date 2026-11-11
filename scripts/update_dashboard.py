#!/usr/bin/env python3
"""Generate a sourced, fixed-price daily snapshot; no AI or paid services."""
import html
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
LISBON = ZoneInfo('Europe/Lisbon')
NOW = datetime.now(timezone.utc)
LOCAL = NOW.astimezone(LISBON)
DAY = LOCAL.date().isoformat()

# Yahoo symbols are indicative only; Yahoo availability and FX quotes can vary.
INSTRUMENTS = [
    ('NASDAQ 100', '^NDX'), ('EUR/USD', 'EURUSD=X'), ('GBP/USD', 'GBPUSD=X'),
    ('EUR/GBP', 'EURGBP=X'), ('BTC/USD', 'BTC-USD'), ('Gold (USD/oz)', 'GC=F'),
]
JPY_CANDIDATES = [('USD/JPY', 'JPY=X'), ('EUR/JPY', 'EURJPY=X'), ('GBP/JPY', 'GBPJPY=X')]
CALENDAR_URL = 'https://nfs.faireconomy.media/ff_calendar_thisweek.json'


def get_quote(name, ticker):
    try:
        history = yf.Ticker(ticker).history(period='5d', interval='1d', auto_adjust=False)
        if history.empty or 'Close' not in history:
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
