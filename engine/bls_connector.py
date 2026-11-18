
"""HERMES official BLS observations connector."""

import argparse
import json
import urllib.request
from pathlib import Path

API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

SERIES = {
    "CUUR0000SA0": "US CPI-U index (not seasonally adjusted)",
    "LNS14000000": "US unemployment rate (seasonally adjusted)",
}


def fetch_observations():
    request_data = {
        "seriesid": list(SERIES),
    }

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(request_data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)

    if result.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(
            f"BLS API failed: {result.get('message')}"
        )

    observations = []

    for series in result.get("Results", {}).get("series", []):
        series_id = series.get("seriesID")

        if series_id not in SERIES:
            continue

        for item in series.get("data", []):
            period = item.get("period", "")

            if not (
                period.startswith("M")
                and len(period) == 3
                and period[1:].isdigit()
                and 1 <= int(period[1:]) <= 12
            ):
                continue

            observations.append({
                "series_id": series_id,
                "indicator": SERIES[series_id],
                "year": item["year"],
                "period": period,
                "actual": item["value"],
                "forecast": None,
                "release_timestamp": None,
                "verification": "api_observation_not_release_verified",
                "source": API_URL,
            })

    if not observations:
        raise RuntimeError("No valid BLS observations returned")

    return {
        "source": "US Bureau of Labor Statistics",
        "data_kind": "observations_not_release_events",
        "observations": observations,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="data/bls_observations.json",
    )
    args = parser.parse_args()

    result = fetch_observations()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"Saved {len(result['observations'])} "
        f"official BLS observations to {output}"
    )


if __name__ == "__main__":
    main()
