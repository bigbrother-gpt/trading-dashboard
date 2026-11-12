
#!/usr/bin/env python3
"""
Daily Trading Dashboard
Free sources: Yahoo Finance + unofficial FF-format calendar.

Generates:
    archive/trading_dashboard.html
    data/latest.json
    data/prices.json

Daily change is calculated using the latest two available
Yahoo Finance daily bars, not saved dashboard snapshots.
"""

import html
import json
import logging
import math

from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests
import yfinance as yf


# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

LISBON = ZoneInfo("Europe/Lisbon")

NOW = datetime.now(timezone.utc)
LOCAL = NOW.astimezone(LISBON)
DAY = LOCAL.date().isoformat()

CALENDAR_URLS = [
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_nextweek.json",
]

BASE_INSTRUMENTS = [
    ("NASDAQ 100 (NDX)", "^NDX"),
    ("EUR/USD", "EURUSD=X"),
    ("GBP/USD", "GBPUSD=X"),
    ("EUR/GBP", "EURGBP=X"),
    ("BTC/USD", "BTC-USD"),
    ("Gold futures (XAU proxy)", "GC=F"),
]

JPY_CANDIDATES = [
    ("USD/JPY", "JPY=X"),
    ("EUR/JPY", "EURJPY=X"),
    ("GBP/JPY", "GBPJPY=X"),
]

CURRENCIES = {"USD", "EUR", "GBP", "JPY"}

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def safe(value):
    return html.escape(str(value), quote=True)


def clean(value, limit=180):
    if value is None:
        return ""
    return str(value).strip()[:limit]


def format_price(item):
    price = item.get("price")

    if price is None:
        return "Unavailable"

    if price < 100:
        return f"{price:,.5f}"

    return f"{price:,.2f}"


def price_decimals(price):
    if price is None:
        return 2

    return 5 if price < 100 else 2


# ------------------------------------------------------------
# YAHOO FINANCE DATA
# ------------------------------------------------------------

def get_quote(name, ticker):
    """
    Retrieve the latest available daily bar and calculate
    the change versus the previous available daily bar.

    A daily bar may still be forming.
    """

    result = {
        "name": name,
        "ticker": ticker,
        "price": None,
        "previous_close": None,
        "change": None,
        "change_pct": None,
        "asof": None,
        "previous_asof": None,
        "source": (
            "https://finance.yahoo.com/quote/"
            + quote(ticker, safe="")
        ),
        "note": "Latest daily bar; not a live quote",
    }

    try:
        history = yf.Ticker(ticker).history(
            period="10d",
            interval="1d",
            auto_adjust=False,
        )

        if history.empty or "Close" not in history:
            raise ValueError("No daily price returned")

        valid = history.dropna(subset=["Close"])

        if valid.empty:
            raise ValueError("No valid daily price")

        current = float(valid.iloc[-1]["Close"])

        if not math.isfinite(current) or current <= 0:
            raise ValueError("Invalid current price")

        result["price"] = current

        current_time = valid.index[-1].to_pydatetime()

        if current_time.tzinfo is None:
            raise ValueError("Daily bar timestamp has no timezone")

        result["asof"] = current_time.astimezone(
            LISBON
        ).strftime("%Y-%m-%d %H:%M %Z")

        if len(valid) >= 2:
            previous = float(valid.iloc[-2]["Close"])

            if math.isfinite(previous) and previous > 0:
                difference = current - previous
                percentage = difference / previous * 100

                result["previous_close"] = previous
                result["change"] = difference
                result["change_pct"] = percentage

                previous_time = valid.index[-2].to_pydatetime()

                if previous_time.tzinfo is not None:
                    result["previous_asof"] = (
                        previous_time.astimezone(LISBON)
                        .strftime("%Y-%m-%d %H:%M %Z")
                    )

        if ticker == "GC=F":
            result["note"] = (
                "COMEX gold futures proxy; not spot XAU/USD"
            )

        elif ticker == "BTC-USD":
            result["note"] = (
                "Bitcoin trades 24/7; latest daily bar "
                "may be incomplete"
            )

        elif ticker == "^NDX":
            result["note"] = (
                "NASDAQ 100 index; US cash-market sessions"
            )

        else:
            result["note"] = (
                "Forex daily bar; may be incomplete"
            )

        logging.info(
            "%s: %s | change=%s | change_pct=%s",
            ticker,
            current,
            result["change"],
            result["change_pct"],
        )

    except Exception as exc:
        logging.warning(
            "Quote unavailable for %s: %s",
            ticker,
            exc,
        )

    return result


# ------------------------------------------------------------
# ECONOMIC CALENDAR
# ------------------------------------------------------------

def calendar_events():
    """
    Retrieve upcoming events from an unofficial
    Forex Factory-format public calendar mirror.

    Impact labels are mirror-reported and unverified.
    """

    events = []
    seen = set()
    successful_feeds = 0

    end = NOW + timedelta(hours=72)

    for url in CALENDAR_URLS:
        try:
            response = requests.get(
                url,
                timeout=20,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(compatible; TradingDashboard/1.0)"
                    )
                },
            )

            response.raise_for_status()
            payload = response.json()

            if not isinstance(payload, list):
                raise ValueError(
                    "Unexpected calendar response format"
                )

            successful_feeds += 1

            for item in payload:
                if not isinstance(item, dict):
                    continue

                try:
                    raw_date = item.get("date")

                    if not raw_date:
                        continue

                    dt = datetime.fromisoformat(
                        str(raw_date).replace(
                            "Z",
                            "+00:00",
                        )
                    )

                    if dt.tzinfo is None:
                        continue

                    utc_dt = dt.astimezone(timezone.utc)

                    if not NOW <= utc_dt <= end:
                        continue

                    currency = clean(
                        item.get("country"),
                        8,
                    ).upper()

                    if currency not in CURRENCIES:
                        continue

                    title = clean(
                        item.get("title") or "Untitled event"
                    )

                    unique_key = (
                        utc_dt.isoformat(),
                        currency,
                        title,
                    )

                    if unique_key in seen:
                        continue

                    seen.add(unique_key)

                    impact_raw = clean(
                        item.get("impact"),
                        30,
                    ).lower()

                    if impact_raw in (
                        "high",
                        "medium",
                        "low",
                    ):
                        impact = impact_raw.title()
                    else:
                        impact = "Unspecified"

                    local_dt = dt.astimezone(LISBON)

                    watches = {
                        "USD": [
                            "NASDAQ 100",
                            "EUR/USD",
                            "GBP/USD",
                            "BTC/USD",
                            "Gold",
                            "USD/JPY",
                        ],
                        "EUR": [
                            "EUR/USD",
                            "EUR/GBP",
                            "EUR/JPY",
                        ],
                        "GBP": [
                            "GBP/USD",
                            "EUR/GBP",
                            "GBP/JPY",
                        ],
                        "JPY": [
                            "USD/JPY",
                            "EUR/JPY",
                            "GBP/JPY",
                        ],
                    }[currency]

                    events.append({
                        "iso": local_dt.isoformat(),
                        "date": local_dt.strftime(
                            "%Y-%m-%d"
                        ),
                        "time": local_dt.strftime(
                            "%H:%M"
                        ),
                        "currency": currency,
                        "title": title,
                        "impact": impact,
                        "forecast": clean(
                            item.get("forecast") or "—",
                            60,
                        ),
                        "previous": clean(
                            item.get("previous") or "—",
                            60,
                        ),
                        "actual": clean(
                            item.get("actual") or "—",
                            60,
                        ),
                        "watches": watches,
                    })

                except (
                    ValueError,
                    TypeError,
                    OverflowError,
                    AttributeError,
                ):
                    continue

        except Exception as exc:
            logging.warning(
                "Calendar feed unavailable (%s): %s",
                url,
                exc,
            )

    events.sort(
        key=lambda event: event["iso"]
    )

    if successful_feeds:
        note = (
            "Unofficial public Forex Factory-format "
            "calendar mirror. Event impact ratings are "
            "not independently verified."
        )
    else:
        note = (
            "Calendar feeds unavailable during generation. "
            "No event data asserted."
        )

    logging.info(
        "Calendar: %d events from %d feeds",
        len(events),
        successful_feeds,
    )

    return events, note


# ------------------------------------------------------------
# AUTOMATIC JPY PAIR SELECTION
# ------------------------------------------------------------

def select_jpy(events):
    """
    Choose one JPY pair using upcoming economic
    calendar impact scores.

    This is not a price or volatility prediction.
    """

    weights = {
        "High": 3,
        "Medium": 2,
        "Low": 1,
        "Unspecified": 0,
    }

    scores = {
        name: 0
        for name, _ in JPY_CANDIDATES
    }

    for event in events:
        currency = event["currency"]
        weight = weights.get(
            event["impact"],
            0,
        )

        for name in scores:
            base_currency = name.split("/")[0]

            if currency in (
                base_currency,
                "JPY",
            ):
                scores[name] += weight

    selected = max(
        JPY_CANDIDATES,
        key=lambda pair: (
            scores[pair[0]],
            -JPY_CANDIDATES.index(pair),
        ),
    )

    reason = (
        f"Selected {selected[0]} using upcoming "
        "72-hour economic-calendar impact scores. "
        "Ties favor USD/JPY. This is a monitoring "
        "priority, not a volatility forecast."
    )

    return selected, reason


# ------------------------------------------------------------
# PRICE CARD HTML
# ------------------------------------------------------------

def make_price_card(item):
    price = item.get("price")
    change = item.get("change")
    percentage = item.get("change_pct")

    if (
        change is not None
        and percentage is not None
        and price is not None
    ):
        if change > 0:
            tone = "up"
            arrow = "▲"

        elif change < 0:
            tone = "down"
            arrow = "▼"

        else:
            tone = "flat"
            arrow = "●"

        decimals = price_decimals(price)

        change_html = f"""
        <div class="ticker-change {tone}">
            <span class="ticker-arrow">{arrow}</span>
            <span>{change:+,.{decimals}f}</span>
            <span>({percentage:+.2f}%)</span>
        </div>
        """

    else:
        change_html = """
        <div class="ticker-change flat">
            Daily change: N/A
        </div>
        """

    previous_label = (
        item.get("previous_asof")
        or "unavailable"
    )

    return f"""
    <article class="tile">

        <div class="sub">
            {safe(item["name"])}
        </div>

        <div class="ticker-price">
            {safe(format_price(item))}
        </div>

        {change_html}

        <div class="muted">
            Change versus previous available daily bar
        </div>

        <div class="muted">
            {safe(item["note"])}
        </div>

        <div class="muted">
            Latest bar (Lisbon):
            {safe(item["asof"] or "unavailable")}
        </div>

        <div class="muted">
            Previous bar (Lisbon):
            {safe(previous_label)}
        </div>

        <a
            href="{safe(item["source"])}"
            target="_blank"
            rel="noopener noreferrer"
        >
            Yahoo Finance source
        </a>

    </article>
    """


# ------------------------------------------------------------
# CALENDAR TABLE HTML
# ------------------------------------------------------------

def make_event_row(event):
    affected = ", ".join(
        event["watches"]
    )

    search_text = (
        event["title"] + " " + affected
    ).lower()

    return f"""
    <tr
        data-currency="{safe(event["currency"])}"
        data-impact="{safe(event["impact"])}"
        data-date="{safe(event["date"])}"
        data-search="{safe(search_text)}"
    >
        <td>
            {safe(event["date"])}
            {safe(event["time"])}
        </td>

        <td>
            {safe(event["currency"])}
        </td>

        <td>
            <details>
                <summary>
                    {safe(event["title"])}
                </summary>

                <small>
                    Instruments to monitor:
                    {safe(affected)}.
                    Market reaction depends on the
                    actual-versus-forecast surprise
                    and wider market conditions.
                </small>
            </details>
        </td>

        <td>
            <span class="impact {safe(event["impact"].lower())}">
                {safe(event["impact"])}*
            </span>
        </td>

        <td>
            {safe(event["forecast"])}
        </td>

        <td>
            {safe(event["previous"])}
        </td>

        <td>
            {safe(event["actual"])}
        </td>

        <td>
            {safe(affected)}
        </td>
    </tr>
    """


# ------------------------------------------------------------
# GENERATE DASHBOARD HTML
# ------------------------------------------------------------

def make_html(quotes, events, calendar_note, jpy_reason):
    quote_cards = "".join(
        make_price_card(item)
        for item in quotes
    )

    event_rows = "".join(
        make_event_row(event)
        for event in events
    )

    if not event_rows:
        event_rows = """
        <tr>
            <td colspan="8">
                No calendar events available for the
                next 72 hours. This does not mean
                no events are scheduled.
            </td>
        </tr>
        """

    priority_events = sorted(
        events,
        key=lambda event: (
            -{
                "High": 3,
                "Medium": 2,
                "Low": 1,
            }.get(event["impact"], 0),
            event["iso"],
        ),
    )[:5]

    priorities = "".join(
        f"""
        <li>
            <b>{safe(event["impact"])}*</b>
            · {safe(event["date"])}
            {safe(event["time"])} Lisbon
            · {safe(event["currency"])}
            — {safe(event["title"])}
        </li>
        """
        for event in priority_events
    )

    if not priorities:
        priorities = (
            "<li>No upcoming events available "
            "from the calendar feed.</li>"
        )

    generated_at = LOCAL.strftime(
        "%Y-%m-%d %H:%M %Z"
    )

    return f"""<!doctype html>
<html lang="en">

<head>
<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<title>
Daily Trading Intelligence · {safe(DAY)}
</title>

<style>

:root {{
    color-scheme: dark;
    font-family: system-ui, Arial, sans-serif;
    background: #080e1a;
    color: #e7effb;
}}

* {{
    box-sizing: border-box;
}}

body {{
    max-width: 1550px;
    margin: 0 auto;
    padding: 20px;
}}

h1 {{
    font-size: clamp(22px, 3vw, 32px);
    margin: 0;
}}

h2 {{
    font-size: 18px;
    margin-top: 28px;
}}

p, li {{
    line-height: 1.5;
}}

.muted,
.sub,
small {{
    color: #a7b7cc;
    font-size: 12px;
}}

.sub {{
    color: #9dcdf5;
    font-size: 14px;
    font-weight: 600;
}}

.lead {{
    color: #b7c9e1;
}}

.grid {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(210px, 1fr));
    gap: 12px;
}}

.tile,
.panel {{
    border: 1px solid #293a53;
    background: #101b2d;
    border-radius: 12px;
    padding: 15px;
}}

.tile {{
    min-height: 225px;
}}

.ticker-price {{
    font-size: 28px;
    font-weight: 750;
    color: #ffffff;
    margin: 12px 0 4px;
    font-variant-numeric: tabular-nums;
}}

.ticker-change {{
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    font-size: 15px;
    font-weight: 750;
    margin: 4px 0 12px;
    font-variant-numeric: tabular-nums;
}}

.ticker-arrow {{
    font-size: 13px;
}}

.ticker-change.up {{
    color: #20c997;
}}

.ticker-change.down {{
    color: #ff4d5e;
}}

.ticker-change.flat {{
    color: #a7b7cc;
}}

.tile .muted {{
    margin: 6px 0;
}}

a {{
    color: #89b9ff;
}}

.controls {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 12px 0;
}}

select,
input,
button {{
    background: #172840;
    border: 1px solid #405675;
    border-radius: 8px;
    padding: 10px;
    color: white;
    min-width: 130px;
}}

button {{
    cursor: pointer;
}}

.tablewrap {{
    overflow-x: auto;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    min-width: 930px;
    font-size: 13px;
}}

th,
td {{
    padding: 10px;
    border-bottom: 1px solid #283750;
    text-align: left;
    vertical-align: top;
}}

th {{
    cursor: pointer;
    color: #c5dcff;
    white-space: nowrap;
}}

tr:hover {{
    background: #14233a;
}}

tr[hidden] {{
    display: none;
}}

.impact {{
    font-weight: 700;
}}

.high {{
    color: #ff818a;
}}

.medium {{
    color: #ffd18a;
}}

.low {{
    color: #8bdeb2;
}}

summary {{
    cursor: pointer;
}}

.foot {{
    margin-top: 24px;
    font-size: 12px;
    color: #b4c1d1;
}}

.stamp {{
    display: inline-block;
    background: #1c304a;
    border: 1px solid #304a6c;
    border-radius: 12px;
    padding: 14px;
    margin: 10px 0 20px;
    line-height: 1.6;
}}

@media (max-width: 600px) {{

    body {{
        padding: 12px;
    }}

    .controls > * {{
        flex: 1 1 40%;
    }}

    .ticker-price {{
        font-size: 26px;
    }}
}}

</style>
</head>

<body>

<h1>◈ Daily Trading Intelligence</h1>

<p class="lead">
    Fixed reference snapshot
    · {safe(DAY)}
    · Lisbon time
    · No live charts
</p>

<div class="stamp">

    ⏰ <strong>Daily price updates</strong>

    <p>
        Prices are fetched automatically once daily
        around <strong>00:00 (midnight),
        Lisbon time</strong>.
        GitHub scheduling may be delayed.
    </p>

    <div>
        Last generated:
        <strong>{safe(generated_at)}</strong>
    </div>

    <div>
        Latest available daily reference prices,
        not live quotes.
    </div>

</div>

<section class="panel">

    <h2>Top catalysts · next 72 hours</h2>

    <ul>
        {priorities}
    </ul>

    <p class="muted">
        * Impact ratings are provided by an unofficial
        Forex Factory-format calendar mirror.
        They have not been independently verified.
    </p>

</section>

<h2>Reference prices</h2>

<p class="muted">
    Each card shows the latest available daily bar,
    the absolute price movement and the percentage
    change versus the previous available daily bar.
    These are not necessarily exact midnight-to-midnight
    changes or confirmed completed-session closes.
</p>

<div class="grid">
    {quote_cards}
</div>

<section
    class="panel"
    style="margin-top:18px"
>

    <h2>JPY pair selection</h2>

    <p>
        {safe(jpy_reason)}
    </p>

    <h2>Conditional market scenarios</h2>

    <p>
        <strong>Bullish scenario:</strong>
        Supportive economic surprises combined
        with confirmed upside price action
        may favor higher prices.
    </p>

    <p>
        <strong>Bearish scenario:</strong>
        Adverse economic surprises combined
        with confirmed downside price action
        may favor lower prices.
    </p>

    <p class="muted">
        These are generic conditional scenarios,
        not predictions, recommendations or
        trading signals.
    </p>

</section>

<h2>Economic calendar · next 72 hours</h2>

<p class="muted">
    {safe(calendar_note)}
    All event times use Europe/Lisbon.
    Forecast, previous and actual values appear
    only when available from the feed.
</p>

<div class="controls">

    <select id="currency">
        <option value="">All currencies</option>
        <option>USD</option>
        <option>EUR</option>
        <option>GBP</option>
        <option>JPY</option>
    </select>

    <select id="impact">
        <option value="">All impacts</option>
        <option>High</option>
        <option>Medium</option>
        <option>Low</option>
        <option>Unspecified</option>
    </select>

    <input
        id="date"
        type="date"
        aria-label="Filter by date"
    >

    <input
        id="search"
        placeholder="Filter instrument / event"
        aria-label="Filter instrument or event"
    >

    <button id="reset">
        Reset
    </button>

</div>

<div class="tablewrap">

<table>

<thead>
<tr>
    <th data-sort="0">Lisbon date/time ↕</th>
    <th data-sort="1">Currency ↕</th>
    <th data-sort="2">Event ↕</th>
    <th data-sort="3">Impact ↕</th>
    <th data-sort="4">Forecast ↕</th>
    <th data-sort="5">Previous ↕</th>
    <th data-sort="6">Actual ↕</th>
    <th data-sort="7">Watched instruments ↕</th>
</tr>
</thead>

<tbody id="rows">
    {event_rows}
</tbody>

</table>

</div>

<p class="foot">

    Sources:
    <a href="{safe(CALENDAR_URLS[0])}"
       target="_blank"
       rel="noopener noreferrer">
       Unofficial public Forex Factory-format calendar feed
    </a>
    and the linked Yahoo Finance instrument pages.

    NASDAQ 100 is an index, not NQ futures.

    Gold GC=F is a futures proxy,
    not spot XAU/USD.

    Calendar data may be incomplete.

    Refreshing this website does not fetch
    new market prices.

</p>

<script>

const ids = [
    "currency",
    "impact",
    "date",
    "search"
];

const fields = Object.fromEntries(
    ids.map(id => [
        id,
        document.getElementById(id)
    ])
);

function filterEvents() {{

    for (
        const row of
        document.querySelectorAll("#rows tr")
    ) {{

        if (!row.dataset.currency) {{
            continue;
        }}

        const visible =
            (
                !fields.currency.value ||
                row.dataset.currency ===
                fields.currency.value
            ) &&
            (
                !fields.impact.value ||
                row.dataset.impact ===
                fields.impact.value
            ) &&
            (
                !fields.date.value ||
                row.dataset.date ===
                fields.date.value
            ) &&
            (
                !fields.search.value ||
                row.dataset.search.includes(
                    fields.search.value.toLowerCase()
                )
            );

        row.hidden = !visible;
    }}
}}

ids.forEach(id => {{
    fields[id].addEventListener(
        "input",
        filterEvents
    );
}});

document.getElementById("reset").onclick = () => {{

    ids.forEach(id => {{
        fields[id].value = "";
    }});

    filterEvents();
}};

let ascending = true;

document.querySelectorAll(
    "th[data-sort]"
).forEach(th => {{

    th.addEventListener("click", () => {{

        const index = Number(
            th.dataset.sort
        );

        const body = document.getElementById(
            "rows"
        );

        const rows = [
            ...body.querySelectorAll("tr")
        ];

        rows.sort((a, b) => {{

            const x =
                a.cells[index]?.innerText || "";

            const y =
                b.cells[index]?.innerText || "";

            return ascending
                ? x.localeCompare(
                    y,
                    undefined,
                    {{numeric: true}}
                )
                : y.localeCompare(
                    x,
                    undefined,
                    {{numeric: true}}
                );
        }});

        rows.forEach(row => {{
            body.appendChild(row);
        }});

        ascending = !ascending;
    }});
}});

</script>

</body>
</html>
"""


# ------------------------------------------------------------
# SAVE OUTPUTS
# ------------------------------------------------------------

def main():
    logging.info(
        "Starting dashboard generation for %s",
        DAY,
    )

    events, calendar_note = calendar_events()

    selected_jpy, jpy_reason = select_jpy(
        events
    )

    instruments = (
        BASE_INSTRUMENTS
        + [selected_jpy]
    )

    quotes = [
        get_quote(name, ticker)
        for name, ticker in instruments
    ]

    available_count = sum(
        item["price"] is not None
        for item in quotes
    )

    if available_count == 0:
        raise RuntimeError(
            "All Yahoo Finance quotes failed. "
            "Refusing to publish an empty snapshot."
        )

    dashboard_path = (
        ROOT
        / "archive"
        / "trading_dashboard.html"
    )

    manifest_path = (
        ROOT
        / "data"
        / "latest.json"
    )

    prices_path = (
        ROOT
        / "data"
        / "prices.json"
    )

    dashboard_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    page = make_html(
        quotes,
        events,
        calendar_note,
        jpy_reason,
    )

    if (
        "<!doctype html>" not in page.lower()
        or len(page) < 3000
    ):
        raise RuntimeError(
            "Generated HTML failed validation."
        )

    dashboard_path.write_text(
        page,
        encoding="utf-8",
    )

    manifest = {
        "date": DAY,
        "file": "archive/trading_dashboard.html",
        "published_at": NOW.isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z"),
    }

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    prices_data = {
        "date": DAY,
        "generated_at": manifest["published_at"],
        "prices": {
            item["ticker"]: item["price"]
            for item in quotes
            if item["price"] is not None
        },
        "daily_changes": {
            item["ticker"]: {
                "absolute": item["change"],
                "percent": item["change_pct"],
                "previous_close": item["previous_close"],
            }
            for item in quotes
        },
    }

    prices_path.write_text(
        json.dumps(
            prices_data,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    logging.info(
        "Dashboard generated: %s",
        dashboard_path,
    )

    logging.info(
        "Quotes available: %s/%s",
        available_count,
        len(quotes),
    )

    logging.info(
        "Calendar events: %s",
        len(events),
    )

    logging.info(
        "Selected JPY pair: %s",
        selected_jpy[0],
    )

    logging.info(
        "Manifest updated: %s",
        manifest,
    )


if __name__ == "__main__":
    main()
