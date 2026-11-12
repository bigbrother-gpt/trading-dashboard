
#!/usr/bin/env python3
"""Free daily static market snapshot. No fabricated quotes or event values."""
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

ROOT = Path(__file__).resolve().parents[1]
LISBON = ZoneInfo("Europe/Lisbon")
NOW = datetime.now(timezone.utc)
LOCAL = NOW.astimezone(LISBON)
DAY = LOCAL.date().isoformat()

CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

BASE = [
    ("NASDAQ 100 (NDX)", "^NDX"),
    ("EUR/USD", "EURUSD=X"),
    ("GBP/USD", "GBPUSD=X"),
    ("EUR/GBP", "EURGBP=X"),
    ("BTC/USD", "BTC-USD"),
    ("Gold futures (XAU proxy)", "GC=F"),
]

JPY = [
    ("USD/JPY", "JPY=X"),
    ("EUR/JPY", "EURJPY=X"),
    ("GBP/JPY", "GBPJPY=X"),
]

CURRENCIES = {"USD", "EUR", "GBP", "JPY"}

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def safe(value):
    return html.escape(str(value), quote=True)


def clean(value, maxlen=160):
    return str(value).strip()[:maxlen] if value is not None else ""


def get_quote(name, ticker):
    result = {
        "name": name,
        "ticker": ticker,
        "price": None,
        "asof": None,
        "source": "https://finance.yahoo.com/quote/" + quote(ticker, safe=""),
        "note": "Daily bar; not a live quote",
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
            raise ValueError("No valid close")

        price = float(valid.iloc[-1]["Close"])
        if not math.isfinite(price) or price <= 0:
            raise ValueError("Invalid price")

        bar_time = valid.index[-1].to_pydatetime()
        if bar_time.tzinfo is None:
            raise ValueError("Quote bar has no timezone")

        result["price"] = price
        result["asof"] = bar_time.astimezone(LISBON).strftime(
            "%Y-%m-%d %H:%M %Z"
        )

        if ticker == "GC=F":
            result["note"] = "COMEX gold futures proxy; NOT spot XAU/USD"
        elif ticker == "BTC-USD":
            result["note"] = "Daily bar; Bitcoin trades 24/7"
        elif ticker == "^NDX":
            result["note"] = "Index daily bar; US cash market has fixed hours"

    except Exception as exc:
        logging.warning("Quote failed for %s: %s", ticker, exc)

    return result


def calendar_events():
    """Read an unofficial FF-format calendar mirror."""
    note = (
        "Unofficial public Forex Factory-format calendar mirror; "
        "ratings not independently verified with Forex Factory."
    )

    try:
        response = requests.get(
            CALENDAR_URL,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; StaticMarketBrief/1.0)"
            },
        )
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            raise ValueError("Unexpected calendar format")

        events = []
        end = NOW + timedelta(hours=72)

        for item in data:
            if not isinstance(item, dict):
                continue

            try:
                raw = item.get("date")
                if not raw:
                    continue

                dt = datetime.fromisoformat(
                    str(raw).replace("Z", "+00:00")
                )

                if dt.tzinfo is None:
                    continue

                utc_dt = dt.astimezone(timezone.utc)
                if not NOW <= utc_dt <= end:
                    continue

                currency = clean(item.get("country", ""), 8).upper()
                if currency not in CURRENCIES:
                    continue

                impact_raw = clean(item.get("impact", ""), 25)
                if impact_raw.lower() in ("high", "medium", "low"):
                    impact = impact_raw.title()
                else:
                    impact = "Unspecified"

                local = dt.astimezone(LISBON)

                watches = {
                    "USD": [
                        "NDX", "EURUSD", "GBPUSD",
                        "BTCUSD", "XAUUSD", "USDJPY",
                    ],
                    "EUR": ["EURUSD", "EURGBP", "EURJPY"],
                    "GBP": ["GBPUSD", "EURGBP", "GBPJPY"],
                    "JPY": ["USDJPY", "EURJPY", "GBPJPY"],
                }[currency]

                events.append({
                    "iso": local.isoformat(),
                    "date": local.strftime("%Y-%m-%d"),
                    "time": local.strftime("%H:%M"),
                    "currency": currency,
                    "title": clean(
                        item.get("title") or "Untitled event", 180
                    ),
                    "impact": impact,
                    "forecast": clean(
                        item.get("forecast") or "—", 60
                    ),
                    "previous": clean(
                        item.get("previous") or "—", 60
                    ),
                    "actual": clean(
                        item.get("actual") or "—", 60
                    ),
                    "watches": watches,
                })

            except (ValueError, TypeError, OverflowError):
                continue

        events.sort(key=lambda event: event["iso"])
        return events, note

    except Exception as exc:
        logging.warning("Calendar fetch failed: %s", exc)
        return [], (
            "Calendar unavailable at generation time; "
            "no events asserted."
        )


def select_jpy(events):
    weights = {
        "High": 3,
        "Medium": 2,
        "Low": 1,
        "Unspecified": 0,
    }

    scores = {name: 0 for name, _ in JPY}

    for event in events:
        for name in scores:
            base = name.split("/")[0]
            if event["currency"] in (base, "JPY"):
                scores[name] += weights.get(event["impact"], 0)

    selected = max(
        JPY,
        key=lambda pair: (
            scores[pair[0]],
            -JPY.index(pair),
        ),
    )

    reason = (
        "Selected using upcoming 72-hour calendar impact scores "
        "for each pair's currencies; ties default to USD/JPY. "
        "This is not a volatility forecast."
    )

    return selected, reason


def format_price(item):
    price = item["price"]

    if price is None:
        return "Unavailable"

    if price < 100:
        return f"{price:,.5f}"

    return f"{price:,.2f}"


def make_html(quotes, events, note, jpy_reason, previous=None):
    previous = previous or {}
    cards = []

    for item in quotes:
        old = previous.get(item["ticker"])

        change_html = (
            '<div class="muted">'
            'Change since previous daily snapshot: N/A '
            '(no comparable previous price)'
            '</div>'
        )

        if (
            item["price"] is not None
            and isinstance(old, (int, float))
            and math.isfinite(old)
            and old > 0
        ):
            percentage = (item["price"] / old - 1) * 100
            difference = item["price"] - old

            if percentage > 0:
                tone = "up"
            elif percentage < 0:
                tone = "down"
            else:
                tone = "flat"

            change_html = (
                f'<div class="change {tone}">'
                f'{percentage:+.2f}% '
                f'<small>({difference:+,.5f} '
                f'since previous daily snapshot)</small>'
                f'</div>'
            )

        cards.append(
            f"""
            <article class="tile">
                <div class="sub">{safe(item["name"])}</div>
                <div class="price">{safe(format_price(item))}</div>
                {change_html}
                <div class="muted">{safe(item["note"])}</div>
                <div class="muted">
                    Bar timestamp (Lisbon):
                    {safe(item["asof"] or "unavailable")}
                </div>
                <a href="{safe(item["source"])}"
                   target="_blank"
                   rel="noopener noreferrer">
                    Yahoo Finance source
                </a>
            </article>
            """
        )

    rows = []

    for event in events:
        affected = ", ".join(event["watches"])

        rows.append(
            f"""
            <tr
                data-currency="{safe(event["currency"])}"
                data-impact="{safe(event["impact"])}"
                data-search="{safe((event["title"] + " " + affected).lower())}"
                data-date="{safe(event["date"])}"
            >
                <td>{safe(event["date"])} {safe(event["time"])}</td>
                <td>{safe(event["currency"])}</td>
                <td>
                    <details>
                        <summary>{safe(event["title"])}</summary>
                        <small>
                            Watch: {safe(affected)}.
                            Conditional reaction depends on the
                            actual-versus-forecast surprise,
                            liquidity and broader market context.
                        </small>
                    </details>
                </td>
                <td>
                    <span class="impact {safe(event["impact"].lower())}">
                        {safe(event["impact"])}*
                    </span>
                </td>
                <td>{safe(event["forecast"])}</td>
                <td>{safe(event["previous"])}</td>
                <td>{safe(event["actual"])}</td>
                <td>{safe(affected)}</td>
            </tr>
            """
        )

    priority = sorted(
        events,
        key=lambda event: (
            {"High": 3, "Medium": 2, "Low": 1}.get(
                event["impact"], 0
            ),
            event["iso"],
        ),
        reverse=True,
    )[:4]

    priorities = "".join(
        f'<li><b>{safe(event["impact"])}*</b> · '
        f'{safe(event["date"])} {safe(event["time"])} Lisbon · '
        f'{safe(event["currency"])} — '
        f'{safe(event["title"])}</li>'
        for event in priority
    )

    if not priorities:
        priorities = (
            "<li>No upcoming events available from the feed.</li>"
        )

    table = "".join(rows)

    if not table:
        table = (
            '<tr><td colspan="8">'
            "No events available from the feed for the next 72 hours. "
            "This does not mean no events are scheduled."
            "</td></tr>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trading Intelligence · {safe(DAY)}</title>

<style>
:root {{
    color-scheme: dark;
    font-family: system-ui, Arial, sans-serif;
    background: #080e1a;
    color: #e7effb;
}}

* {{ box-sizing: border-box; }}

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

p, li {{ line-height: 1.5; }}

.muted, .sub, small {{
    color: #a7b7cc;
    font-size: 12px;
}}

.lead {{ color: #b7c9e1; }}

.grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(195px, 1fr));
    gap: 12px;
}}

.tile, .panel {{
    border: 1px solid #293a53;
    background: #101b2d;
    border-radius: 12px;
    padding: 15px;
}}

.price {{
    font-size: 25px;
    font-weight: 750;
    margin: 10px 0;
}}

a {{ color: #89b9ff; }}

.controls {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 12px 0;
}}

select, input, button {{
    background: #172840;
    border: 1px solid #405675;
    border-radius: 8px;
    padding: 10px;
    color: white;
    min-width: 130px;
}}

button {{ cursor: pointer; }}

.tablewrap {{ overflow-x: auto; }}

table {{
    width: 100%;
    border-collapse: collapse;
    min-width: 930px;
    font-size: 13px;
}}

th, td {{
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

tr:hover {{ background: #14233a; }}

.impact {{ font-weight: 700; }}
.high {{ color: #ff818a; }}
.medium {{ color: #ffd18a; }}
.low {{ color: #8bdeb2; }}

summary {{ cursor: pointer; }}

.foot {{
    margin-top: 24px;
    font-size: 12px;
    color: #b4c1d1;
}}

.change {{
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 8px;
}}

.up {{ color: #8bdeb2; }}
.down {{ color: #ff818a; }}
.flat {{ color: #a7b7cc; }}

.stamp {{
    display: inline-block;
    background: #1c304a;
    border-radius: 12px;
    padding: 12px;
    margin: 10px 0;
}}

@media (max-width: 600px) {{
    body {{ padding: 12px; }}
    .controls > * {{ flex: 1 1 40%; }}
}}
</style>
</head>

<body>
<h1>◈ Daily Trading Intelligence</h1>

<p class="lead">
    Fixed reference snapshot · {safe(DAY)} · Lisbon time · No live charts
</p>

<div class="stamp">
    ⏰ <strong>Daily price updates:</strong>
    Prices are fetched automatically once daily around
    <strong>00:00 (midnight), Lisbon time</strong>.
    GitHub scheduling may be delayed.
    <br>
    Last generated: {safe(LOCAL.strftime("%Y-%m-%d %H:%M %Z"))}.
    <br>
    Latest available daily bars, not live quotes.
</div>

<section class="panel">
    <h2>Top catalysts · next 72 hours</h2>
    <ul>{priorities}</ul>
    <p class="muted">
        * Impact categories supplied by an unofficial
        Forex Factory-format mirror, not directly verified
        with Forex Factory.
    </p>
</section>

<h2>Reference prices</h2>

<p class="muted">
    Percentage changes compare successive saved daily snapshots,
    not necessarily exact midnight-to-midnight market prices.
    An unavailable previous price shows N/A.
</p>

<div class="grid">
    {"".join(cards)}
</div>

<section class="panel" style="margin-top:18px">
    <b>JPY pair selection</b>
    <p>{safe(jpy_reason)}</p>

    <b>Conditional scenarios</b>

    <p>
        <strong>Bullish:</strong>
        A supportive macro surprise plus confirmation in price
        action may favor upside.
    </p>

    <p>
        <strong>Bearish:</strong>
        An adverse surprise plus confirmed downside momentum
        may favor declines.
    </p>

    <p class="muted">
        Neither scenario is a prediction or trade signal.
        Confirm prices with your broker before trading.
    </p>
</section>

<h2>Economic calendar · next 72 hours</h2>

<p class="muted">
    {safe(note)}
    All event times are Europe/Lisbon.
    Actual, forecast and previous figures are shown
    only when provided.
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

    <input id="date" type="date" aria-label="Filter by date">

    <input
        id="search"
        placeholder="Filter instrument / event"
        aria-label="Filter instrument or event"
    >

    <button id="reset">Reset</button>
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
        {table}
    </tbody>
</table>
</div>

<p class="foot">
    Sources:
    <a href="{safe(CALENDAR_URL)}">
        Unofficial public Forex Factory-format calendar mirror
    </a>;
    linked Yahoo Finance instrument pages.
    NDX is an index, not NQ futures.
    GC=F is gold futures, not spot XAUUSD.
    Calendar data may be incomplete or unavailable.
    This static snapshot does not fetch prices on page refresh.
</p>

<script>
const ids = ["currency", "impact", "date", "search"];

const fields = Object.fromEntries(
    ids.map(id => [id, document.getElementById(id)])
);

function filterEvents() {{
    for (const row of document.querySelectorAll("#rows tr")) {{
        if (!row.dataset.currency) continue;

        const visible =
            (!fields.currency.value ||
                row.dataset.currency === fields.currency.value) &&
            (!fields.impact.value ||
                row.dataset.impact === fields.impact.value) &&
            (!fields.date.value ||
                row.dataset.date === fields.date.value) &&
            (!fields.search.value ||
                row.dataset.search.includes(
                    fields.search.value.toLowerCase()
                ));

        row.hidden = !visible;
    }}
}}

ids.forEach(id => {{
    fields[id].addEventListener("input", filterEvents);
}});

document.getElementById("reset").onclick = () => {{
    ids.forEach(id => fields[id].value = "");
    filterEvents();
}};

let ascending = true;

document.querySelectorAll("th[data-sort]").forEach(th => {{
    th.addEventListener("click", () => {{
        const index = Number(th.dataset.sort);
        const body = document.getElementById("rows");
        const rows = [...body.querySelectorAll("tr")];

        rows.sort((a, b) => {{
            const x = a.cells[index]?.innerText || "";
            const y = b.cells[index]?.innerText || "";

            return ascending
                ? x.localeCompare(y, undefined, {{numeric: true}})
                : y.localeCompare(x, undefined, {{numeric: true}});
        }});

        rows.forEach(row => body.appendChild(row));
        ascending = !ascending;
    }});
}});
</script>
</body>
</html>"""


def main():
    events, calendar_note = calendar_events()
    selected, reason = select_jpy(events)

    quotes = [
        get_quote(*instrument)
        for instrument in BASE + [selected]
    ]

    available = sum(
        item["price"] is not None for item in quotes
    )

    if available == 0:
        raise RuntimeError(
            "All quote sources failed; refusing to publish "
            "a misleading snapshot"
        )

    output = ROOT / "archive" / "trading_dashboard.html"
    manifest_path = ROOT / "data" / "latest.json"
    prices_path = ROOT / "data" / "prices.json"

    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    previous = {}

    if prices_path.exists():
        try:
            saved = json.loads(
                prices_path.read_text(encoding="utf-8")
            )

            if (
                saved.get("date") != DAY
                and isinstance(saved.get("prices"), dict)
            ):
                previous = saved["prices"]

            elif (
                saved.get("date") == DAY
                and isinstance(saved.get("previous_prices"), dict)
            ):
                previous = saved["previous_prices"]

        except (ValueError, OSError, AttributeError) as exc:
            logging.warning(
                "Previous snapshot unreadable: %s", exc
            )

    page = make_html(
        quotes,
        events,
        calendar_note,
        reason,
        previous,
    )

    if "<!doctype html>" not in page.lower() or len(page) < 3000:
        raise RuntimeError(
            "Generated HTML failed basic validation"
        )

    output.write_text(page, encoding="utf-8")

    manifest = {
        "date": DAY,
        "file": "archive/trading_dashboard.html",
        "published_at": NOW.isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z"),
    }

    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    prices_path.write_text(
        json.dumps({
            "date": DAY,
            "prices": {
                item["ticker"]: item["price"]
                for item in quotes
                if item["price"] is not None
            },
            "previous_prices": previous,
        }, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"Generated {output.relative_to(ROOT)}; "
        f"{available}/7 quotes; "
        f"{len(events)} events"
    )

    print(f"Updated manifest: {manifest}")


if __name__ == "__main__":
    main()
