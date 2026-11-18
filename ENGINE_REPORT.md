# HERMES v1.4 — Economic Intelligence Engine: validation report

## Delivered and tested

- Strict, deterministic analysis of attributed macroeconomic releases (`engine/economic_engine.py`), 11 indicator types, USD/EUR/GBP/JPY, values/previous/revisions, forecast provenance and timestamp checks, absolute and relative surprise, source URLs, UTC timestamps and DST-aware London/New York context.
- Conditional theoretical directional mappings for watchlist assets (`XAUUSD`, `GBPUSD`, `EURUSD`, `EURGBP`, `USDJPY`, `NAS100`, `BTCUSD`). **Heuristics only**, not predictions. For gold, stocks and BTC, rate sensitivity can reverse; directions are deliberately marked low confidence.
- Optional comparison with **supplied, attributed** observed prices (`engine/market_interpretation.py`). Divergence is not evidence of manipulation. No price movements are fabricated.
- Compact, provenance-bearing AI input format; existing optional `engine/ai.py` classifier remains disabled and unbenchmarked. No model was downloaded, run or verified in this build.
- 61/61 unit tests pass offline. No actual feeds, forecasts, market quotes or live model were tested.

## Hard limitations (not production-ready)

1. **No automatic official statistical-release parsing.** `data/economic_releases.json` must be supplied with real, validated records. The example file is explicitly fictional and must not be copied to the live input.
2. Official URL allowlisting establishes a plausible host, **not** that the record's numbers came from that page. No document retrieval, cryptographic authentication or primary-source value comparison is performed.
3. Forecast consensus must be supplied from a separate permitted source with pre-release timestamp. No free consensus provider has been validated.
4. No running, tested local language model; `ai_inputs` is a structured input for a future model, not model-generated interpretation.
5. Theory mappings are simplified and cannot reliably predict short-term price action. Surprise magnitude is not standardized by historical dispersion; different indicators are not directly comparable.
6. No real observed market data are ingested by this module. No causal attribution or manipulation detection.
7. No UI change to the approved interface. `data/economic_intelligence.json` is generated only if the input file exists and is **not yet rendered** on the site.
8. Official domain registry is a technical allowlist, not a license or endpoint audit. GDELT remains out of scope.

## How to run

`python3 -m unittest discover -s tests -v`

`python3 engine/economic_engine.py` — does nothing if `data/economic_releases.json` is absent. To test synthetic data, copy `data/economic_releases.example.json` to `data/economic_releases.json` **only in an offline test environment**, run the command, and delete both generated files before publishing. Do not present synthetic figures as real.

## Next validation gates

1. Real institutional feed/API connectors with parsing and source-linked evidence spans, revision handling and strict freshness.
2. Legal, pre-release consensus source and clear vintage handling.
3. Open-weights language model CPU benchmark with constrained evidence-grounded output and automatic abstention, not hallucinated facts.
4. Real-price comparisons with instrument definitions, aligned timestamps and redistribution permissions.
5. End-to-end real-data browser/publication tests, then release.

## Incremental update — grounded economic briefs

- Added `engine/grounded_brief.py`, a fail-closed, deterministic interpretation layer. It renders attributed actual/forecast/surprise values and conditional theoretical directions without inventing market reactions.
- The economic engine now includes a `briefs` array in its generated JSON output. If forecast is unavailable, it explicitly withholds surprise and directional inference.
- Added three tests for forecast abstention, forecast-backed interpretation, and invalid verification status. **64/64 offline tests pass**.
- This is **not** a validated autonomous AI model or a live official-data connector. Real-source parsing, consensus licensing, and CPU model benchmarking remain outstanding.
