"""HERMES economic event impact vs market reaction, using explicit evidence.

No live market prices, forecasts, or economic event timestamps are inferred.
Input: JSON event with event_id, country, indicator, release_timestamp (ISO 8601
with timezone), actual, forecast, unit, expectations mapping, and prices mapping.
Prices: per instrument {before: number, after: number, before_timestamp: ISO,
after_timestamp: ISO}. Expectations: per instrument "up", "down", or "neutral".
"""
import argparse
import json
import math
from datetime import datetime
from pathlib import Path

DIRECTIONS = {"up", "down", "neutral"}
def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Timestamps must be ISO 8601 strings with timezone")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("Timestamp must have timezone")
    return dt

def finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Expected a finite numeric value")
    return float(value)

def analyze(event, threshold_pct=0.05):
    threshold_pct = finite_number(threshold_pct)
    if threshold_pct < 0:
        raise ValueError("threshold_pct must be nonnegative")
    for field in ("event_id", "country", "indicator"):
        if not isinstance(event.get(field), str) or not event[field].strip():
            raise ValueError(f"Missing {field}")
    release = timestamp(event["release_timestamp"])
    actual = finite_number(event["actual"])
    forecast = finite_number(event["forecast"])
    if not isinstance(event.get("unit"), str) or not event["unit"]:
        raise ValueError("Explicit unit required")
    expectations = event.get("expectations", {})
    prices = event.get("prices", {})
    if not isinstance(expectations, dict) or not isinstance(prices, dict):
        raise ValueError("expectations and prices must be objects")
    results = {}
    for instrument, expectation in expectations.items():
        if expectation not in DIRECTIONS:
            raise ValueError(f"Invalid expectation for {instrument}")
        price = prices.get(instrument)
        if price is None:
            results[instrument] = {"expected_direction": expectation, "status": "missing_market_prices",
                                   "observed_direction": None, "return_pct": None}
            continue
        before = finite_number(price["before"])
        after = finite_number(price["after"])
        if before <= 0 or after <= 0:
            raise ValueError("Prices must be positive")
        before_time = timestamp(price["before_timestamp"])
        after_time = timestamp(price["after_timestamp"])
        if not (before_time <= release <= after_time) or before_time == after_time:
            raise ValueError("Price window must bracket release and have positive duration")
        change = (after / before - 1) * 100
        observed = "neutral" if abs(change) <= threshold_pct else ("up" if change > 0 else "down")
        status = "aligned" if observed == expectation else "divergent"
        results[instrument] = {"expected_direction": expectation, "observed_direction": observed,
                               "return_pct": round(change, 6), "status": status}
    return {
        "event_id": event["event_id"], "country": event["country"], "indicator": event["indicator"],
        "release_timestamp": event["release_timestamp"], "actual": actual, "forecast": forecast,
        "unit": event["unit"], "surprise": round(actual - forecast, 10),
        "surprise_unit": event["unit"], "threshold_pct": threshold_pct,
        "instruments": results,
        "caveat": "Expected directions are supplied hypotheses, not independently validated predictions. "
                  "Divergence is descriptive, not evidence of causality."
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--threshold-pct", type=float, default=0.05)
    args = parser.parse_args()
    event = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = analyze(event, args.threshold_pct)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Analyzed {len(result['instruments'])} instruments; saved {out}")

if __name__ == "__main__":
    main()
