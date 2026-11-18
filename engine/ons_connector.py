"""Standalone UK ONS CPI annual-rate observation connector; no release-event claims."""
import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7g7/mm23/data"
SERIES = "D7G7"

def parse(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("months"), list):
        raise ValueError("ONS response missing months array")
    observations = []
    for item in payload["months"]:
        if not isinstance(item, dict):
            continue
        date, value = item.get("date"), item.get("value")
        if not isinstance(date, str) or not isinstance(value, (str, int, float)):
            continue
        if not value or str(value).strip() in ("", "..", "-"):
            continue
        try:
            numeric = float(value)
        except (ValueError, TypeError):
            continue
        observations.append({
            "series_id": SERIES,
            "indicator": "UK CPI 12-month inflation rate (all items)",
            "country": "GB",
            "currency": "GBP",
            "period": date,
            "actual": numeric,
            "unit": "percent",
            "forecast": None,
            "release_timestamp": None,
            "verification": "api_observation_not_release_verified",
            "source": URL
        })
    if not observations:
        raise ValueError("No usable monthly CPI observations in ONS response")
    return {"source": URL, "data_kind": "observations_not_release_events",
            "observations": observations}

def fetch():
    req = Request(URL, headers={"User-Agent": "HERMES-economic-research/1.0",
                                "Accept": "application/json"})
    with urlopen(req, timeout=25) as response:
        return json.load(response)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/ons_uk_cpi_observations.json")
    args = parser.parse_args()
    result = parse(fetch())
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(result['observations'])} UK CPI observations to {target}")

if __name__ == "__main__":
    main()
