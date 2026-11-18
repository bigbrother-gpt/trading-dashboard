# HERMES v1.1 beta — Open-source pilot

**Global Financial Intelligence System** · *Beyond the headlines. Ahead of the markets.*

## Status: v1.0 engineering milestone, NOT production-ready

This is a **working static frontend and a tested, metadata-only ingestion pipeline**, not an autonomous, verified global financial intelligence service. The approved v0.2 editorial frontend, map, logo, favicon and accessible pins are preserved. No paid dependencies or API keys are used. No external feed has been verified live during this build; rights, reliability and real-world accuracy are untested.

### What runs

- `index.html`, `map.svg`, `hermes-symbol.svg`, `live-data.js`: static site, no framework or build system.
- `engine/collect.py`: bounded RSS/Atom retrieval (up to 2 MB per feed, timeouts, 4 workers, 30-day publication-date filter).
- `engine/relevance.py`: multilingual keyword-based triage, 8 topic families, watchlist instrument candidates.
- `engine/cross_reference.py`: conservative lexical clustering; preserves references, does not assume source independence.
- `engine/fact_review.py`: **structured observations only**, advisory saturation after 3 redundant observations and externally verified independence.
- `engine/scoring.py`: transparent weighted formula 50% economic/financial, 30% escalation, 20% strategic. **Never auto-assigns scores from headlines.**
- `engine/publish.py`: validates feed snapshot, rejects stale/failed runs, keeps 30-day records, emits up to 180 **unverified** headlines to `data/events.json` (max 650 KB).
- `live-data.js`: loads the published JSON if present and recent; renders feed titles safely as text, with source links and explicit uncertainty. Without a valid snapshot, displays **fictional demo events** with an unmissable warning.
- `.github/workflows/discovery.yml`: **manual** public-repository diagnostic workflow. Uploads a static preview as an artifact; it **does not deploy** or schedule collection.

### Running locally for development (not required for users)

```bash
python3 -m unittest discover -s tests -v
python3 engine/collect.py
python3 engine/relevance.py
python3 engine/cross_reference.py
python3 engine/fact_review.py
python3 engine/publish.py
python3 -m http.server 8000
```

Open `http://localhost:8000`. Collection requires network access to the provisional feeds; the test suite runs offline. To deploy the static output, host `index.html`, `map.svg`, `hermes-symbol.svg`, `live-data.js` and `data/events.json` together. The `data/events.json` file is ignored by Git by default to avoid accumulating snapshots in repository history; a future deployment workflow should publish a **fresh artifact**, not commit snapshots.

### Explicit limitations

1. **Not yet AI:** no LLM, semantic embeddings, automatic article-body extraction, factual verification or multilingual deep understanding. A zero-cost AI inference service cannot be guaranteed under GitHub Actions CPU/time constraints; benchmark and licensing review required.
2. **Not yet independent corroboration:** multiple URLs/domains can repeat one wire story. `fact_review.py` only processes manually structured claims; it cannot autonomously validate independence.
3. **No geocoding:** real headlines do not get fabricated map coordinates. In live-snapshot mode, the map has no pins until verified geolocation is implemented. Demo mode has clearly fictional pins.
4. **No reliable severity:** score requires externally established evidence; no automatic Critical/Emerging labels are assigned to real headlines.
5. **No market quotes:** Markets shows dashes rather than invented numbers. Broadcasts are links to external official pages, not embedded streams.
6. **Feeds unverified:** the 14-source catalog is provisional. Endpoints, usage rights, availability and licensing must be checked before enabling automatic public redistribution.
7. **Not deployed:** no GitHub repository or Pages site created. No always-on service or guaranteed refresh interval.
8. **Zero cost conditional:** only standard free GitHub features are proposed, subject to provider limits/terms. No guaranteed future unlimited free hosting, bandwidth, compute or data licensing.
9. **30-day retention applies to published records** with parseable dates; undated items can be displayed as undated and should be further reviewed. Build artifacts are retained 1 day. Repository history should not include data snapshots.
10. **Potential source/impact mappings are hypotheses**, not verified market effects, forecasts or financial advice.

### Next validation gates before production

- Confirm each feed's live availability and content redistribution rights; remove unsupported sources.
- Benchmark on real feeds, multilingual false negatives, duplication and origin lineage.
- Implement evidence-linked fact extraction, contradictions, event identity, verified country coordinates and uncertainty labels.
- Benchmark open-weights AI on actual free CPU quotas; if infeasible, keep rule-based pipeline rather than add costs.
- Validate a free source for delayed market data and permitted embeds.
- Implement safe artifact-only Pages deployment and scheduled collection only after rights and quota review.
- Accessibility, responsive browser, security, reliability and public beta tests.

### Design and product requirements

- No rounded cards, gradients, glows, shadows, sidebars or generic CSS templates.
- Editorial numbered sections: Map → Live → News → Markets; prominent country boundaries, transparent caduceus logo and favicon.
- Severity symbol as well as color for accessibility: ! Critical, ▲ Emerging, ◆ Early Signal, i Informational.
- Approved watchlist: XAUUSD, GBPUSD, EURUSD, EURGBP, USDJPY, NAS100, BTCUSD.
- Proposed weighted scoring 0.50F + 0.30E + 0.20S; provisional thresholds 85/60/30.
- News history: 30 days. No hosted video. Creator and users pay 0 €; no required personal server.

Code license: MIT (project code). Source articles and third-party content retain their own rights. Natural Earth geographic data is public domain.


## v1.1 additions

See `RELEASE_REPORT.md`. `pages.yml` is manual and must only be enabled after feed rights review. Markets remain blank unless a properly licensed `data/markets.json` is supplied. Optional `engine/ai.py` is NOT enabled or tested by default.


## v1.2 — segurança e validação

Ver `RELEASE_REPORT.md`. A interface limpa os dados de demonstração se não existir um snapshot recente. O workflow suporta agendamento de 6 em 6 horas, mas **só o executa se** a variável do repositório `HERMES_ENABLE_SCHEDULE` estiver definida como `true`. Não ativar antes de verificar fontes e direitos. O GDELT permanece fora do projeto nesta fase.

Testar: `python3 -m unittest discover -s tests -v`. Executar localmente com `python3 -m http.server 8000` (sem dados ao vivo até executar o pipeline).


## v1.3 — ECB e Intelligence Engine

- Fonte primária oficial ECB já incluída em `engine/sources.json` (`https://www.ecb.europa.eu/rss/press.html`).
- `engine/market_ecb.py`: recolhe **taxas de referência diárias** EURUSD, EURGBP e pares matematicamente derivados GBPUSD e USDJPY. Não são cotações negociáveis nem em tempo real. 1D e 5D referem-se a observações anteriores do BCE; 1M a aproximadamente 30 dias de calendário, quando existir histórico suficiente.
- XAUUSD, NAS100 e BTCUSD permanecem indisponíveis até encontrar fonte autorizada. Não usar Yahoo Finance, Forex Factory ou Bloomberg por scraping sem validar licença.
- Os direitos de reutilização e atribuição dos dados ECB exigem revisão antes da publicação pública; o código não afirma autorização.
- O motor de afirmações rejeita títulos interrogativos ou expressamente especulativos. Isto não é verificação factual por IA.
- GitHub: ativar Pages/Actions; executar workflow manualmente primeiro. O agendamento exige variável `HERMES_ENABLE_SCHEDULE=true`.
- O GDELT continua fora do projeto por decisão de prioridades.


## v1.4 economic intelligence

See [ENGINE_REPORT.md](ENGINE_REPORT.md). Deterministic macro surprise and conditional theoretical direction module, with provenance requirements and 61 offline tests. **This is not an autonomous AI and is not production-ready.** No live economic release connector or licensed forecast provider is implemented.
