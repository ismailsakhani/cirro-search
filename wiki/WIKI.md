# cirro-search — Technical Wiki

> Full technical documentation for engineers. Generated from a complete source audit on 2026-06-08.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [How to Run Locally](#3-how-to-run-locally)
4. [Directory Structure](#4-directory-structure)
5. [Backend — Complete File Reference](#5-backend--complete-file-reference)
6. [Backend — Search Pipeline (end-to-end trace)](#6-backend--search-pipeline-end-to-end-trace)
7. [Backend — API Endpoint Reference](#7-backend--api-endpoint-reference)
8. [Backend — Data Models](#8-backend--data-models)
9. [Backend — Elasticsearch Index](#9-backend--elasticsearch-index)
10. [Backend — Tests](#10-backend--tests)
11. [Frontend — Complete File Reference](#11-frontend--complete-file-reference)
12. [Frontend — State Flow](#12-frontend--state-flow)
13. [Frontend — Request Lifecycle](#13-frontend--request-lifecycle)
14. [Frontend — Local Storage](#14-frontend--local-storage)
15. [Data — Seed Files](#15-data--seed-files)
16. [Scripts](#16-scripts)
17. [Evaluation + Experiments](#17-evaluation--experiments)

---

## 1. Project Overview

cirro-search is a full-stack aviation search laboratory built to research and validate search engine approaches for the Cirrostrats iOS app. It indexes airports, flights, and gates into Elasticsearch and exposes a REST API consumed by a React playground UI. The system allows side-by-side comparison of search providers (Elasticsearch vs in-memory baseline), experimentation with ES query parameters and ranking strategies, and regression testing against known Cirrostrats search bugs.

**Problem it solves:** Cirrostrats' in-memory fuzzy search (fuzz_find) fails on exact 3-letter code disambiguation, codeshare expansion, and natural language alias queries. cirro-search proves that Elasticsearch with a domain ranking pipeline solves all known failure cases at production-grade latency.

### Technology Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Search engine | Elasticsearch | 8.15.3 | Document storage + full-text/prefix search |
| API framework | FastAPI | ≥0.111 | REST API, dependency injection |
| Data validation | Pydantic | ≥2.7 | Request/response schemas, domain models |
| Settings | pydantic-settings | ≥2.3 | Env var config with `.env` support |
| ASGI server | Uvicorn | ≥0.30 | HTTP server for FastAPI |
| Eval parsing | PyYAML | ≥6.0 | Load evaluation case YAML files |
| ES client | elasticsearch-py | ≥8.15,<9 | Python ES client |
| Frontend framework | React | 18.3.1 | Component UI |
| Language | TypeScript | 5.5.3 | Type-safe frontend |
| Build tool | Vite | 5.3.4 | Dev server + bundler |
| Routing | react-router-dom | 7.17.0 | SPA routing |
| Container | Docker + Compose | — | Run ES + Kibana locally |
| Python | CPython | ≥3.11 | Backend runtime |
| Node | Node.js | ≥18 | Frontend build runtime |

---

## 2. System Architecture

### Request Flow

```
Browser (localhost:3000)
        │
        │  HTTP GET /api/v1/search?q=...
        │  HTTP GET /api/v1/suggestions?q=...
        │  HTTP POST /api/v1/feedback/select
        │
        ▼
Vite Dev Server (:3000)
  proxy /api  → http://127.0.0.1:8000
  proxy /health → http://127.0.0.1:8000
        │
        ▼
FastAPI + Uvicorn (:8000)
  app/main.py
  └── CORSMiddleware (allow_origins=["*"])
  └── routers: health, search, feedback
        │
        │  search pipeline (classify → expand → alias → es)
        ▼
Elasticsearch (:9200)
  index: cirro-search-v1
  1 shard, 0 replicas
  ~85,545 airports + flights + gates
        │
        ▼  (Kibana :5601 — dev only, not used by app)
```

### Docker Container Diagram

```
docker-compose.yml
├── elasticsearch
│     image: elasticsearch:8.15.3
│     container: cirro-search-elasticsearch
│     port: 9200:9200
│     volume: cirro-search-es-data
│     env: single-node, security disabled, 512m heap
│     healthcheck: wait for yellow cluster status
│
└── kibana
      image: kibana:8.15.3
      container: cirro-search-kibana
      port: 5601:5601
      depends_on: elasticsearch (healthy)
```

### Vite Proxy

Vite's `server.proxy` in `vite.config.ts` rewrites requests from the browser. Any request starting with `/api` or `/health` is forwarded to `http://127.0.0.1:8000`. This lets the React frontend call `/api/v1/search` without CORS issues — both the frontend and the proxied backend appear to the browser as the same origin (localhost:3000). In production, a real reverse proxy (nginx, etc.) would replace Vite's proxy.

---

## 3. How to Run Locally

### Prerequisites

- Python 3.11+
- Node 18+
- Docker Desktop (or Docker Engine + Compose plugin)

### Step-by-step

```bash
# 1. Start Elasticsearch (and Kibana) via Docker
cd /path/to/cirro-search
docker compose -f docker/docker-compose.yml up -d

# Wait for ES to be healthy (~30–60s)
docker compose -f docker/docker-compose.yml ps

# 2. Create Python virtual environment
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install Python dependencies
pip install -e ".[dev]"

# 4. Seed data into Elasticsearch
python -m app.seed

# 5. Start backend
uvicorn app.main:app --reload --port 8000

# 6. In a new terminal — install frontend dependencies
cd ../frontend
npm install

# 7. Start frontend dev server
npm run dev
# → http://localhost:3000
```

### Environment Variables

All vars read from `.env` in the `backend/` directory or from the shell environment.

| Variable | Default | What it controls |
|---|---|---|
| `ELASTICSEARCH_URL` | `http://localhost:9200` | ES host — change for remote/Docker networking |
| `ELASTICSEARCH_INDEX` | `cirro-search-v1` | Index name used for all operations |
| `ELASTICSEARCH_REQUEST_TIMEOUT` | `10` | Per-request ES timeout in seconds |

---

## 4. Directory Structure

```
cirro-search/
├── backend/                         # Python FastAPI backend
│   ├── app/
│   │   ├── __init__.py              # Empty package marker
│   │   ├── main.py                  # FastAPI app factory, CORS, router registration
│   │   ├── seed.py                  # CLI entry point: python -m app.seed
│   │   ├── api/
│   │   │   ├── dependencies.py      # lru_cache DI factories (pipeline, feedback service)
│   │   │   ├── schemas.py           # Pydantic API request/response models
│   │   │   └── routes/
│   │   │       ├── __init__.py      # Empty
│   │   │       ├── search.py        # /api/v1/search, /suggestions, /analytics/stats, /trending
│   │   │       ├── health.py        # GET /health
│   │   │       └── feedback.py      # POST /api/v1/feedback/select
│   │   ├── application/
│   │   │   ├── search_service.py    # Use case: delegates suggest/search to pipeline
│   │   │   ├── seed_service.py      # Use case: loads seed docs, bulk-indexes via provider
│   │   │   ├── selection_feedback_service.py  # Painless script: atomic popularity increment
│   │   │   └── experiment_service.py          # Phase 3: isolated ES indices per experiment variant
│   │   ├── domain/
│   │   │   ├── pipeline/
│   │   │   │   ├── search_pipeline.py  # Orchestrates all stages + fallback logic
│   │   │   │   └── stages.py           # Pure functions: normalize, expansions, entity type, terms
│   │   │   ├── ranking/
│   │   │   │   └── basic_ranker.py     # Domain scoring: +1000/+200/+100/+75/+50/+25/popularity
│   │   │   ├── classifier/
│   │   │   │   ├── query_classifier.py # Ordered pattern classification of query strings
│   │   │   │   └── patterns.py         # Pre-compiled regex patterns
│   │   │   ├── aliases/
│   │   │   │   └── resolver.py         # Loads aliases.json, resolves natural language terms
│   │   │   ├── airline_mapping/
│   │   │   │   ├── codes.py            # IATA↔ICAO tables, AIRLINE_NAMES, IATA_TO_AIRLINE_NAME
│   │   │   │   └── codeshare.py        # CODESHARE_EXPANSION, expand_flight_identifiers()
│   │   │   └── models/
│   │   │       ├── __init__.py         # Empty
│   │   │       ├── entity_type.py      # EntityType, SearchMode enums
│   │   │       ├── query.py            # QueryType, FlightIdentifier, ClassificationResult, AliasResolution
│   │   │       ├── result.py           # SearchResult, RankedResult, PipelineDebug, PipelineResponse
│   │   │       ├── airport.py          # Airport domain entity
│   │   │       ├── flight.py           # Flight domain entity
│   │   │       └── gate.py             # Gate domain entity
│   │   ├── providers/
│   │   │   ├── __init__.py             # Empty
│   │   │   ├── protocol.py             # SearchProvider Protocol (runtime_checkable)
│   │   │   ├── models.py               # SearchDocument, ProviderHit, ProviderSearchResponse, etc.
│   │   │   ├── exceptions.py           # SearchProviderError, ProviderUnavailableError, IndexingError
│   │   │   ├── elasticsearch/
│   │   │   │   ├── __init__.py         # Empty
│   │   │   │   ├── client.py           # create_elasticsearch_client(), ensure_index()
│   │   │   │   ├── index_config.py     # INDEX_SETTINGS, INDEX_MAPPINGS
│   │   │   │   ├── queries.py          # build_search_query(), build_autocomplete_query()
│   │   │   │   └── provider.py         # ElasticsearchProvider: search, autocomplete, bulk_index, health
│   │   │   ├── baseline/
│   │   │   │   ├── __init__.py         # Empty
│   │   │   │   └── provider.py         # BaselineProvider: in-memory fuzzy (SequenceMatcher)
│   │   │   └── testing/
│   │   │       ├── __init__.py         # Empty
│   │   │       └── fake_provider.py    # FakeSearchProvider: in-memory substring match for unit tests
│   │   └── infrastructure/
│   │       ├── config.py               # Settings (pydantic-settings), get_settings() with lru_cache
│   │       ├── analytics_store.py      # Thread-safe in-memory counters, get_analytics_store() singleton
│   │       └── seed/
│   │           └── loader.py           # airport_to_document(), flight_to_document(), gate_to_document()
│   ├── tests/
│   │   ├── unit/                        # No ES required
│   │   │   ├── test_classifier.py
│   │   │   ├── test_ranker.py
│   │   │   ├── test_aliases.py
│   │   │   ├── test_airline_mapping.py
│   │   │   ├── test_elasticsearch_queries.py
│   │   │   ├── test_pipeline_stages.py
│   │   │   └── test_provider_protocol.py
│   │   ├── integration/                 # Requires ES at localhost:9200
│   │   │   ├── test_elasticsearch_provider.py
│   │   │   └── test_search_api.py
│   │   ├── evaluation/                  # Requires ES; marked pytest.mark.integration
│   │   │   ├── test_phase1_cases.py
│   │   │   ├── test_regression_cases.py
│   │   │   ├── test_provider_comparison.py
│   │   │   └── experiments/
│   │   │       └── test_experiments.py
│   │   └── benchmarks/
│   │       ├── bench_latency.py
│   │       ├── compare_providers.py
│   │       └── test_latency_targets.py
│   └── pyproject.toml                   # Build config, deps, pytest config, ruff config
│
├── frontend/                            # TypeScript + React + Vite
│   ├── index.html                       # HTML shell; defines pulse @keyframe for skeleton cards
│   ├── package.json                     # npm scripts: dev, build, preview
│   ├── vite.config.ts                   # Vite config: port 3000, proxy /api + /health → :8000
│   ├── tsconfig.json                    # TypeScript config
│   └── src/
│       ├── main.tsx                     # Entry: StrictMode + BrowserRouter + createRoot
│       ├── App.tsx                      # Routes: / → Playground, /result → ResultDetail
│       ├── theme.ts                     # Design tokens: colors, font, radius
│       ├── types/
│       │   └── search.ts                # SearchResult, DebugInfo, SearchResponse, SuggestionResponse
│       ├── pages/
│       │   ├── Playground.tsx           # Main search page: input + result panel + trending fetch
│       │   └── ResultDetail.tsx         # Detail page: EXPLANATION_LABEL + QUERY_TYPE_LABEL maps
│       ├── components/
│       │   ├── SearchInput.tsx          # Input + Search button; cycling placeholder every 3s
│       │   ├── ResultPanel.tsx          # Results list, discovery panel, debug panel, skeleton cards
│       │   ├── AirportCard.tsx          # Airport result card; countryFlag() Unicode emoji
│       │   ├── FlightCard.tsx           # Flight result card; airline_name resolution
│       │   ├── GateCard.tsx             # Gate result card
│       │   ├── SuggestionList.tsx       # ORPHANED — dropdown list; not rendered in any page
│       │   └── EmptyStateDropdown.tsx   # ORPHANED — separate dropdown; superseded by ResultPanel discovery panel
│       ├── hooks/
│       │   ├── useSearch.ts             # Core search state: debounce, suggestion waterfall, submit
│       │   ├── useRecentSearches.ts     # localStorage recent searches (MAX_RECENTS=10)
│       │   └── useCyclingPlaceholder.ts # Cycles through placeholder strings on interval
│       ├── api/
│       │   ├── searchClient.ts          # fetch wrappers: search(), suggestions()
│       │   └── feedbackClient.ts        # recordSelection() — fire-and-forget POST
│       └── utils/
│           └── highlight.tsx            # highlightMatch(): indexOf-based query highlighting
│
├── data/
│   └── seed/
│       ├── airports.json                # ~85,545 airports (global, from OurAirports CSV)
│       ├── flights.json                 # Synthetic flights (~35 airlines × 59 numbers)
│       ├── gates.json                   # Generated gates from airports.json by popularity tier
│       └── aliases.json                 # Natural language → entity_id alias table
│
├── docker/
│   └── docker-compose.yml               # ES 8.15.3 + Kibana 8.15.3
│
├── elasticsearch/
│   ├── settings/
│   │   └── index-settings.json          # Minimal settings: 1 shard, 0 replicas
│   └── scripts/
│       ├── create-index.sh              # Shell: curl create index with settings
│       ├── delete-index.sh              # Shell: curl delete index
│       └── health-check.sh             # Shell: curl cluster health
│
├── evaluation/
│   └── cases/
│       ├── phase1.yaml                  # 9 original evaluation cases (aliases, codeshare, etc.)
│       └── regression.yaml             # 78 regression cases (airport/flight/gate coverage)
│
├── experiments/
│   └── configs/
│       ├── exp-001-fuzzy-tolerance.yaml # Compare AUTO vs fixed-1 vs fixed-2 fuzziness
│       ├── exp-002-field-weights.yaml   # Compare default vs high-code vs balanced field boosts
│       └── exp-003-ranking-strategy.yaml # Compare domain vs es-score vs popularity-first ranking
│
├── scripts/
│   ├── convert_airports.py             # OurAirports CSV → airports.json
│   ├── generate_flights.py             # airlines.dat → flights.json + codes.py
│   └── generate_gates.py               # airports.json → gates.json (tier-based terminal config)
│
└── CREATE_WIKI.md                       # Instructions for generating this wiki
```

---

## 5. Backend — Complete File Reference

### `backend/app/main.py`

**Purpose:** FastAPI application factory. Creates the `app` instance, adds CORS middleware, and includes all three routers.

**Key exports:**
```python
app: FastAPI  # the ASGI application
```

**Configuration:**
- `CORSMiddleware`: `allow_origins=["*"]`, `allow_methods=["GET", "POST"]`, `allow_headers=["*"]`
- Routers: `health.router`, `search.router`, `feedback.router`

**Notes:** CORS is fully open. Acceptable for a development lab; tighten for any production deployment.

---

### `backend/app/seed.py`

**Purpose:** CLI entry point for seeding data. Run as `python -m app.seed`.

**Key function:**
```python
def main() -> None
```

Instantiates `ElasticsearchProvider` and `SeedService`, calls `service.seed(recreate=False)`, prints indexed count and any errors. `recreate=False` means documents are upserted (existing docs with same id are overwritten) but the index is not dropped first.

---

### `backend/app/api/dependencies.py`

**Purpose:** FastAPI dependency factories with `@lru_cache` for singleton semantics.

**Functions:**
```python
@lru_cache
def get_search_pipeline() -> SearchPipeline
    # Creates Settings → ElasticsearchProvider → SearchPipeline

@lru_cache
def get_selection_feedback_service() -> SelectionFeedbackService
    # Creates Settings → ES client → SelectionFeedbackService
```

**Notes:** `@lru_cache` on module-level functions means each factory returns the same instance for the process lifetime. Thread-safe because FastAPI's startup is single-threaded.

---

### `backend/app/api/schemas.py`

**Purpose:** Pydantic models for API request/response serialization. Mirror domain models but are the API contract, not domain logic.

**Models:**

```python
class SearchResultSchema(BaseModel):
    id: str
    type: str
    display: str
    score: float
    iata: str | None = None
    icao: str | None = None
    name: str | None = None
    city: str | None = None
    country: str | None = None
    airline: str | None = None
    airline_name: str | None = None
    iata_flight: str | None = None
    icao_flight: str | None = None
    flight_number: str | None = None
    airport_code: str | None = None
    gate: str | None = None
    matched_fields: list[str] = []
    explanation: list[str] = []
    metadata: dict[str, Any] = {}

class PipelineDebugSchema(BaseModel):
    classification: dict[str, Any]
    expansions: list[str] = []
    alias_resolution: dict[str, Any] | None = None
    provider: str
    provider_took_ms: int = 0
    pipeline_took_ms: int = 0
    fallback_used: bool = False

class SearchResponseSchema(BaseModel):
    query: str
    mode: str
    results: list[SearchResultSchema]
    debug: PipelineDebugSchema

class HealthResponseSchema(BaseModel):
    status: str
    provider: str
    provider_status: str
    index: str | None = None
```

---

### `backend/app/api/routes/search.py`

**Purpose:** All search-related HTTP endpoints. Prefix: `/api/v1`.

**Endpoints:**

```python
GET /api/v1/suggestions?q=<str>&limit=<int>  # → SearchResponseSchema
GET /api/v1/search?q=<str>&limit=<int>        # → SearchResponseSchema
GET /api/v1/analytics/stats                   # → dict
GET /api/v1/trending?limit=<int>              # → {"queries": [{"query": str, "count": int}]}
```

**Internal helper:**
```python
def _to_schema(response: PipelineResponse) -> SearchResponseSchema
    # model_validate each result, pass debug fields through
```

Both `suggestions` and `search` call `analytics.record(q, mode, result_count=...)` as a side effect after the search completes.

---

### `backend/app/api/routes/health.py`

**Purpose:** Health probe endpoint.

```python
GET /health  # → HealthResponseSchema
```

Returns `status="ok"` if provider health is HEALTHY or DEGRADED; `status="degraded"` only if UNAVAILABLE. Also returns the provider name, raw provider status, and index name.

---

### `backend/app/api/routes/feedback.py`

**Purpose:** Record user selection events.

```python
class SelectionEvent(BaseModel):
    result_id: str

POST /api/v1/feedback/select  # body: SelectionEvent → 204 No Content
```

Delegates to `SelectionFeedbackService.record_selection(event.result_id)`.

---

### `backend/app/application/search_service.py`

**Purpose:** Thin application-layer wrapper around `SearchPipeline`. Translates `suggest`/`search` use cases to pipeline `run()` calls with the appropriate `SearchMode`.

```python
class SearchService:
    def suggest(self, query: str, *, limit: int = 10) -> PipelineResponse
        # mode = SearchMode.AUTOCOMPLETE
    def search(self, query: str, *, limit: int = 10) -> PipelineResponse
        # mode = SearchMode.SUBMIT
```

---

### `backend/app/application/seed_service.py`

**Purpose:** Loads seed documents from disk and indexes them via the provider.

```python
class SeedService:
    def seed(self, *, recreate: bool = False) -> BulkIndexResult
        # If recreate=True: deletes each doc before re-indexing
        # Calls load_seed_documents() then provider.bulk_index()

    @property
    def document_count(self) -> int
        # Returns count of documents in seed dir
```

Default seed directory: resolved from `Path(__file__).parents[4] / "data" / "seed"`.

---

### `backend/app/application/selection_feedback_service.py`

**Purpose:** Atomically increment `metadata.popularity` in Elasticsearch when a result is selected by the user.

```python
class SelectionFeedbackService:
    def record_selection(self, result_id: str) -> None
```

Uses an ES Painless script (inline, `lang: painless`) for an atomic read-modify-write. The script handles three cases: `metadata` is null, `popularity` key is missing, or `popularity` exists. **Silently swallows all exceptions** — selection tracking must never break search.

---

### `backend/app/application/experiment_service.py`

**Purpose:** Phase 3 A/B testing infrastructure. Creates isolated ES indices per experiment variant, seeds data, runs evaluation cases, and produces a structured comparison report.

**Key data classes:**
```python
@dataclass class CaseResult:   # query, mode, expected, passed, top_result, rank_of_expected
@dataclass class VariantReport: # variant_name, pass_count, total_count, case_results; .pass_rate property
@dataclass class ExperimentReport: # experiment_id, name, axis, variants; .winner(), .summary_lines()
```

**Internal variant providers:**
- `_VariantElasticsearchProvider`: subclass of `ElasticsearchProvider` with overridable `query_kwargs` (fuzziness, field boosts)
- `_EsScoreRanker`: subclass of `BasicRanker` that skips all domain boosts — returns ES hits in raw ES score order
- `_PopularityFirstRanker`: subclass of `BasicRanker` that scores as `popularity * 10 + es_score`

Index naming: `exp-{exp_id}-{variant_name}-{run_id}` where `run_id` is a short UUID hex.

---

### `backend/app/domain/pipeline/search_pipeline.py`

**Purpose:** Orchestrates all pipeline stages. The central class that connects classifier, alias resolver, provider, and ranker.

```python
class SearchPipeline:
    def __init__(
        self,
        provider: SearchProvider,
        classifier: QueryClassifier | None = None,    # default: QueryClassifier()
        alias_resolver: AliasResolver | None = None,  # default: AliasResolver()
        ranker: BasicRanker | None = None,            # default: BasicRanker()
    )

    def health(self) -> ProviderHealth

    def run(
        self,
        query: str,
        mode: SearchMode = SearchMode.SUBMIT,
        *,
        limit: int = 10,
    ) -> PipelineResponse
```

**Fallback logic:** After the primary search, if `provider_response.hits` is empty AND `mode == SUBMIT`, a second search is issued with `entity_type=None` (no type filter). If the fallback finds hits, `fallback_used=True` is set in the debug output.

**`_search_provider()` internal method:** Dispatches to `provider.autocomplete()` for `AUTOCOMPLETE` mode, `provider.search()` for `SUBMIT` mode.

---

### `backend/app/domain/pipeline/stages.py`

**Purpose:** Pure stateless functions for each pipeline stage. No side effects, fully testable without mocks.

```python
def normalize_query(query: str) -> str
    # strip + collapse whitespace: " ua 44 " → "ua 44"

def build_expansions(classification: ClassificationResult) -> list[str]
    # If FLIGHT: calls expand_flight_identifiers(iata, icao, flight_number)
    # If DIGITS: appends digits
    # If AIRPORT_CODE: appends airport_code
    # If GATE: appends gate
    # Deduplicates by lowercase key

def resolve_entity_type(
    classification: ClassificationResult,
    alias: AliasResolution,
) -> EntityType | None
    # alias.entity_type takes priority over classification.entity_type

def collect_search_terms(
    query: str,
    expansions: list[str],
    alias: AliasResolution,
) -> list[str]
    # [query, *expansions, *alias.expanded_terms], deduplicated by lowercase key
```

---

### `backend/app/domain/ranking/basic_ranker.py`

**Purpose:** Domain re-ranking layer applied on top of raw ES hits. Adds deterministic signal boosts to the raw ES BM25 score.

```python
class BasicRanker:
    def rank(
        self,
        hits: list[ProviderHit],
        classification: ClassificationResult,
        query: str,
        *,
        preferred_entity_id: str | None = None,
    ) -> list[RankedResult]

    def _score_hit(...) -> tuple[float, list[str]]

    def to_search_results(self, ranked: list[RankedResult]) -> list[SearchResult]
```

**Score signals applied in `_score_hit()`:**

| Signal | Condition | Boost | Explanation label |
|---|---|---|---|
| Base ES score | always | `hit.score` (raw BM25) | `es_score` |
| Alias entity match | `doc.id == preferred_entity_id` | +1000 | `alias_entity_match` |
| Type alignment | `doc.type == classification.entity_type` | +50 | `type_alignment` |
| Exact IATA | `doc.iata.lower() == query_compact` | +200 | `exact_iata` |
| Exact ICAO | `doc.icao.lower() == query_compact` | +200 | `exact_icao` |
| Exact IATA flight | `doc.iata_flight.lower() == query_compact` | +200 | `exact_iata_flight` |
| Exact ICAO flight | `doc.icao_flight.lower() == query_compact` | +200 | `exact_icao_flight` |
| Exact gate | `doc.gate.lower() == query_compact` | +200 | `exact_gate` |
| Exact flight number | `doc.flight_number == query_compact` | +100 | `exact_flight_number` |
| Digits match | `classification.query_type == DIGITS and doc.flight_number == classification.digits` | +75 | `digits_match` |
| Searchable text match | `query_lower in doc.searchable_text.lower()` | +25 | `searchable_text_match` |
| Popularity | `doc.metadata.get("popularity", 0) * 0.1` | variable | `popularity` |

`query_compact = query.strip().lower().replace(" ", "")` — space-collapsed form for code matching.

Hits are sorted descending by final score. `to_search_results()` strips the `rank` field from `RankedResult` before returning `SearchResult` objects.

---

### `backend/app/domain/classifier/query_classifier.py`

**Purpose:** Classify raw query strings into typed `ClassificationResult` objects using ordered pattern matching.

```python
class QueryClassifier:
    def classify(self, query: str) -> ClassificationResult
```

**Classification order (first match wins):**

1. **ICAO_AIRPORT** — `ICAO_AIRPORT_PATTERN`: `^[KC][A-Z]{3}$` — 4-letter codes starting with K or C (North America)
2. **FLIGHT (ICAO codes)** — iterate `ICAO_AIRLINE_CODES` (sorted longest-first); if `compact.startswith(code)` and remainder is all digits → `QueryType.FLIGHT`
3. **FLIGHT (IATA codes)** — iterate `IATA_AIRLINE_CODES` (sorted longest-first); same logic, but skip alphanumeric-code short queries like `B17` (ambiguous with gates)
4. **DIGITS** — `^\d+$` — bare numbers, e.g. `4433`
5. **IATA_AIRPORT** — `^[A-Z]{3}$` AND compact not in `IATA_AIRLINE_CODES`
6. **GATE** — `^[A-Z]\d{1,4}$` — letter + 1–4 digits
7. **AIRLINE_NAME_FLIGHT** — scan `AIRLINE_NAMES` dict; if `lower.startswith(name + " ")` and remainder is digits → `QueryType.FLIGHT`
8. **AMBIGUOUS** — contains a space OR is ≥3 alphabetic chars (text search)
9. **UNKNOWN** — fallthrough

**Why IATA codes come after FLIGHT:** ensures `UA44` is classified as FLIGHT before `UAL` is tested as IATA airport. Codes sorted longest-first for greedy matching.

**Gate/flight ambiguity guard (line 106–112):** If an IATA airline code ends in a digit (e.g. `B6`), and the full query looks like `B6{digits}` with total length ≤4, skip the FLIGHT match and fall through to GATE. This prevents `B17` being classified as a JetBlue flight.

---

### `backend/app/domain/classifier/patterns.py`

**Purpose:** Pre-compiled regex constants used by `QueryClassifier`.

```python
ICAO_AIRPORT_PATTERN = re.compile(r"^[KC][A-Z]{3}$")   # KJFK, KEWR, CYYZ, CYOW
IATA_AIRPORT_PATTERN = re.compile(r"^[A-Z]{3}$")        # CDG, LHR, EWR
DIGITS_PATTERN       = re.compile(r"^\d+$")              # 4433, 44
GATE_PATTERN         = re.compile(r"^[A-Z]\d{1,4}$")    # C101, B7, A1
FLIGHT_NUMBER_PATTERN = re.compile(r"^(\d+)$")           # same as DIGITS (unused in classifier directly)
TAIL_NUMBER_PATTERN   = re.compile(r"^N[0-9A-Z]{1,5}$") # N12345 (reserved for future use)
```

---

### `backend/app/domain/aliases/resolver.py`

**Purpose:** Map natural language queries and compound queries to specific entity IDs.

```python
class AliasResolver:
    def __init__(
        self,
        aliases: list[dict] | None = None,   # pass directly for tests
        seed_path: Path | None = None,        # default: data/seed/aliases.json
    )

    def resolve(
        self, query: str, classification: ClassificationResult
    ) -> AliasResolution
```

**Lookup:** `self._by_term` is a `dict[str, dict]` keyed by lowercase term. On `resolve()`, the query is lowercased and looked up. If found, returns `AliasResolution(matched=True, entity_id=..., entity_type=..., expanded_terms=[...])`.

**`_terms_for_entry()` expansion:** When an alias is matched, generates additional search terms based on entity_id prefix:
- `airport:CDG` → adds `["CDG", "cdg"]`
- `flight:UA4433` → adds `["UA4433", "4433"]`
- `gate:EWR:C101` → adds `["C101", "EWR", "ewr c101"]`

If query is `AMBIGUOUS` with no alias match, returns `AliasResolution(matched=False, expanded_terms=[query])`.

---

### `backend/app/domain/airline_mapping/codes.py`

**Purpose:** Auto-generated IATA ↔ ICAO airline code tables. Source: `scripts/generate_flights.py`.

**Exports:**
- `IATA_TO_ICAO: dict[str, str]` — ~700+ IATA codes → ICAO codes (e.g. `"UA" → "UAL"`)
- `ICAO_TO_IATA: dict[str, str]` — reverse mapping (derived from IATA_TO_ICAO)
- `ICAO_AIRLINE_CODES: tuple[str, ...]` — all ICAO codes, sorted longest-first for greedy prefix matching
- `IATA_AIRLINE_CODES: tuple[str, ...]` — all IATA codes, sorted longest-first
- `AIRLINE_NAMES: dict[str, str]` — 37 common airline name strings → IATA (e.g. `"united" → "UA"`, `"british airways" → "BA"`)
- `IATA_TO_AIRLINE_NAME: dict[str, str]` — 37 IATA codes → display names (e.g. `"UA" → "United Airlines"`)

---

### `backend/app/domain/airline_mapping/codeshare.py`

**Purpose:** Codeshare expansion — maps IATA marketing carrier to operating ICAO carriers. Used to find flights that appear under a different airline code in the index.

```python
CODESHARE_EXPANSION: dict[str, list[str]] = {
    "UA": ["UAL", "GJS", "UCA", "SKW", "RPA", "OO"],   # United: GoJet, Air Wisconsin, SkyWest, Republic, PSA
    "AA": ["AAL", "SKW", "OO", "EV", "MQ", "OH"],       # American: SkyWest, Mesa, ExpressJet, Envoy, PSA
    "DL": ["DAL", "SKW", "OO", "EV", "ASQ"],            # Delta: SkyWest, Mesa, ExpressJet, ASA
    "AS": ["ASA", "SKW", "OO", "QX"],                   # Alaska: SkyWest, Horizon
    "WN": ["SWA"],
    "B6": ["JBU"],
    "F9": ["FFT"],
    "NK": ["NKS"],
    "G4": ["AAY"],
    "BA": ["BAW", "SHT"],
    "LH": ["DLH", "CLH", "EWG"],
    "AF": ["AFR", "HOP"],
    "KL": ["KLM"],
    "EK": ["UAE"],
    "QR": ["QTR"],
}

def expand_flight_identifiers(
    iata_airline: str | None,
    icao_airline: str | None,
    flight_number: str,
) -> list[str]
    # Returns: [UAL4433, GJS4433, UCA4433, SKW4433, RPA4433, OO4433, UA4433]
    # for input (iata="UA", icao="UAL", number="4433")
```

Algorithm: starts with `icao_airline`, appends all codeshare partners from `CODESHARE_EXPANSION[iata]`, appends `IATA_TO_ICAO[iata]` (the canonical ICAO), then appends the IATA form itself. Deduplicates with a seen set.

---

### `backend/app/domain/models/entity_type.py`

```python
class EntityType(StrEnum):
    AIRPORT = "airport"
    FLIGHT  = "flight"
    GATE    = "gate"

class SearchMode(StrEnum):
    AUTOCOMPLETE = "autocomplete"
    SUBMIT       = "submit"
```

---

### `backend/app/domain/models/query.py`

```python
class QueryType(StrEnum):
    AIRPORT_ICAO = "airport_icao"
    AIRPORT_IATA = "airport_iata"
    FLIGHT       = "flight"
    DIGITS       = "digits"
    GATE         = "gate"
    AMBIGUOUS    = "ambiguous"
    UNKNOWN      = "unknown"

class FlightIdentifier(BaseModel):
    code_type: str             # "IATA" or "ICAO"
    iata_airline_code: str | None = None
    icao_airline_code: str | None = None
    flight_number: str

class ClassificationResult(BaseModel):
    query_type: QueryType
    normalized_query: str
    confidence: float = 1.0
    matched_pattern: str | None = None
    flight: FlightIdentifier | None = None
    airport_code: str | None = None
    gate: str | None = None
    digits: str | None = None

    @property
    def entity_type(self) -> EntityType | None:
        # AIRPORT_ICAO/AIRPORT_IATA → AIRPORT
        # FLIGHT/DIGITS             → FLIGHT
        # GATE                      → GATE
        # AMBIGUOUS/UNKNOWN         → None

class SearchQuery(BaseModel):
    raw: str
    normalized: str
    mode: SearchMode = SearchMode.SUBMIT

class AliasResolution(BaseModel):
    matched: bool = False
    entity_id: str | None = None
    entity_type: EntityType | None = None
    expanded_terms: list[str] = []
```

---

### `backend/app/domain/models/result.py`

```python
class SearchResult(BaseModel):
    id: str
    type: EntityType
    display: str
    score: float
    iata: str | None = None
    icao: str | None = None
    name: str | None = None
    city: str | None = None
    country: str | None = None
    airline: str | None = None
    airline_name: str | None = None
    iata_flight: str | None = None
    icao_flight: str | None = None
    flight_number: str | None = None
    airport_code: str | None = None
    gate: str | None = None
    matched_fields: list[str] = []
    explanation: list[str] = []
    metadata: dict[str, Any] = {}

class RankedResult(SearchResult):
    rank: int    # 1-based position

class PipelineDebug(BaseModel):
    classification: dict[str, Any]
    expansions: list[str] = []
    alias_resolution: dict[str, Any] | None = None
    provider: str
    provider_took_ms: int = 0
    pipeline_took_ms: int = 0
    fallback_used: bool = False

class PipelineResponse(BaseModel):
    query: str
    mode: str
    results: list[SearchResult]
    debug: PipelineDebug
```

---

### `backend/app/domain/models/airport.py`, `flight.py`, `gate.py`

Domain entity models (not used in the main pipeline — the pipeline works with `SearchDocument`). Available for future domain logic.

```python
class Airport(BaseModel):
    id: str; iata: str | None; icao: str | None; name: str; city: str | None; country: str | None
    aliases: list[str] = []

class Flight(BaseModel):
    id: str; airline: str; iata_flight: str | None; icao_flight: str | None
    flight_number: str; aliases: list[str] = []

class Gate(BaseModel):
    id: str; airport_code: str; gate: str; aliases: list[str] = []
```

---

### `backend/app/providers/protocol.py`

**Purpose:** The `SearchProvider` Protocol. All pipeline and domain code depends on this interface only — never on `ElasticsearchProvider` directly.

```python
@runtime_checkable
class SearchProvider(Protocol):
    @property
    def name(self) -> str: ...

    def search(self, request: ProviderSearchRequest) -> ProviderSearchResponse: ...
    def autocomplete(self, request: ProviderAutocompleteRequest) -> ProviderSearchResponse: ...
    def index_document(self, document: SearchDocument) -> None: ...
    def delete_document(self, document_id: str) -> None: ...
    def bulk_index(self, documents: list[SearchDocument]) -> BulkIndexResult: ...
    def get_health(self) -> ProviderHealth: ...
```

`runtime_checkable` means `isinstance(obj, SearchProvider)` works at runtime without inheritance. Used in `test_provider_protocol.py`.

---

### `backend/app/providers/models.py`

```python
class SearchDocument(BaseModel):
    id: str; type: EntityType; display: str; searchable_text: str
    iata/icao/name/city/country/airline/airline_name/iata_flight/icao_flight/
    flight_number/airport_code/gate: str | None = None
    aliases: list[str] = []; metadata: dict[str, Any] = {}

class ProviderSearchRequest(BaseModel):
    query: str; mode: SearchMode = SUBMIT
    entity_type: EntityType | None = None
    expanded_terms: list[str] = []
    limit: int = 10  (ge=1, le=100)

class ProviderAutocompleteRequest(BaseModel):
    query: str; entity_type: EntityType | None = None
    expanded_terms: list[str] = []
    limit: int = 10  (ge=1, le=50)

class ProviderHit(BaseModel):
    document: SearchDocument; score: float; matched_fields: list[str] = []

class ProviderSearchResponse(BaseModel):
    hits: list[ProviderHit] = []; took_ms: int = 0; provider: str

class BulkIndexResult(BaseModel):
    indexed: int = 0; failed: int = 0; errors: list[str] = []

class ProviderHealthStatus(StrEnum):
    HEALTHY = "healthy"; DEGRADED = "degraded"; UNAVAILABLE = "unavailable"

class ProviderHealth(BaseModel):
    status: ProviderHealthStatus; provider: str
    message: str | None = None; details: dict[str, Any] = {}
```

---

### `backend/app/providers/exceptions.py`

```python
class SearchProviderError(Exception)          # base
class ProviderUnavailableError(SearchProviderError)  # ES unreachable/unhealthy
class IndexingError(SearchProviderError)       # indexing operation failed
```

---

### `backend/app/providers/elasticsearch/client.py`

```python
def create_elasticsearch_client(settings: Settings | None = None) -> Elasticsearch
    # host: settings.elasticsearch_url
    # timeout: settings.elasticsearch_request_timeout

def ensure_index(client: Elasticsearch, index_name: str) -> None
    # idempotent: skips if index exists
    # creates with INDEX_SETTINGS + INDEX_MAPPINGS from index_config.py
```

---

### `backend/app/providers/elasticsearch/index_config.py`

**Purpose:** ES index settings and mappings. Defines custom analyzers and per-field types.

**Settings:**
```python
INDEX_SETTINGS = {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {
        "tokenizer": {
            "edge_ngram_tokenizer": {
                "type": "edge_ngram",
                "min_gram": 2, "max_gram": 20,
                "token_chars": ["letter", "digit"],
            }
        },
        "analyzer": {
            "search_text_analyzer":      # standard tokenizer + lowercase + asciifolding
            "search_text_edge_analyzer": # edge_ngram_tokenizer + lowercase + asciifolding
        }
    }
}
```

**Mappings — field types:**

| Field | Type | Analyzer / Notes |
|---|---|---|
| `id` | keyword | exact match only |
| `type` | keyword | exact match only |
| `display` | text + keyword sub-field | `search_text_analyzer`; `.keyword` for sorting |
| `searchable_text` | text + `edge` sub-field | main: `search_text_analyzer`; `.edge`: `search_text_edge_analyzer` (index), `search_text_analyzer` (search) |
| `iata` | keyword | case-sensitive exact match |
| `icao` | keyword | case-sensitive exact match |
| `name` | text | `search_text_analyzer` |
| `city` | text | `search_text_analyzer` |
| `country` | keyword | |
| `airline` | keyword | |
| `iata_flight` | keyword | |
| `icao_flight` | keyword | |
| `flight_number` | keyword | bare digits only |
| `airport_code` | keyword | |
| `gate` | keyword | |
| `aliases` | text | `search_text_analyzer` |
| `metadata` | object | `enabled: true` — supports sub-field queries like `metadata.popularity` |

**Note:** `airline_name` is NOT in the index mappings — it is stored in the `SearchDocument` model and serialized into ES as a dynamic field. It will be indexed with default ES dynamic mapping (text with keyword sub-field).

---

### `backend/app/providers/elasticsearch/queries.py`

**Purpose:** Build ES query DSL dicts for both search and autocomplete modes.

#### `build_search_query()` (submit mode)

For each search term, emits:
1. **Term queries** on `iata`, `icao`, `iata_flight`, `icao_flight`, `gate`, `airport_code` with the uppercased term and `boost: 20`. This handles case mismatch — stored values are uppercase, user input may be lowercase.
2. **Term query** on `flight_number` with `boost: 40` — flight_number stores bare digits so this avoids fuzzy collisions on short digit queries.
3. **Multi-match** across all fields with `fuzziness: "AUTO"` and field boosts (`iata^8`, `icao^8`, `iata_flight^8`, `icao_flight^8`, `flight_number^6`, `gate^8`, `airport_code^6`, `searchable_text^4`, `aliases^3`, `name^3`, `display^2`).

Wrapped in `function_score` with `field_value_factor` on `metadata.popularity` (factor=1.0, modifier=none, missing=0) and `boost_mode: "sum"` — popularity is added to BM25 score, not multiplied.

Filter: `{"term": {"type": entity_type.value}}` if entity_type is not None.

#### `build_autocomplete_query()` (autocomplete mode)

For each search term, emits:
1. **Prefix queries** on `iata`, `icao`, `airport_code` (lowercase, boost 6–8)
2. **Prefix queries** on `iata_flight`, `icao_flight`, `gate` (uppercase, boost 8)
3. **Match** on `searchable_text.edge` (the edge-ngram sub-field, boost 4) — enables partial prefix matches on names
4. **Multi-match** on `searchable_text^3`, `aliases^2`, `name^2`, `display` with `fuzziness: "AUTO"`

No `function_score` wrapper — autocomplete does not apply popularity scoring. No `minimum_should_match` — any single clause match is sufficient.

#### Difference between the two queries

| Aspect | `build_search_query` | `build_autocomplete_query` |
|---|---|---|
| Exact code matching | Term queries + `boost:20` (uppercase) | Prefix queries |
| Popularity | `function_score` wrapping | Not applied |
| Fuzzy matching | `fuzziness: AUTO` in multi_match | `fuzziness: AUTO` in multi_match |
| Edge-ngram | Not used | `searchable_text.edge` match |
| Use case | Final submit search | Dropdown suggestions as user types |

---

### `backend/app/providers/elasticsearch/provider.py`

**Purpose:** `ElasticsearchProvider` — concrete implementation of `SearchProvider` backed by Elasticsearch.

```python
class ElasticsearchProvider:
    def __init__(
        self,
        client: Elasticsearch | None = None,
        settings: Settings | None = None,
        *,
        auto_create_index: bool = True,   # calls ensure_index on init
    )
```

**Key methods:**
- `search()` → calls `build_search_query()`, delegates to `_execute()`
- `autocomplete()` → calls `build_autocomplete_query()`, delegates to `_execute()`
- `index_document()` → `client.index()`, raises `IndexingError` on failure
- `delete_document()` → `client.delete()`, silently ignores `ESNotFoundError`
- `bulk_index()` → `elasticsearch.helpers.bulk()` with `raise_on_error=False, refresh=True`
- `get_health()` → `client.cluster.health(index=...)`: green → HEALTHY, yellow → DEGRADED, red/exception → UNAVAILABLE

**`_execute()` internal method:** Calls `client.search(index=..., query=body["query"], size=body["size"])`. Deserializes each hit: `_source` → `SearchDocument` (with `EntityType` cast), score from `_score`, matched_fields from `highlight` keys (if highlight is present).

**`_serialize_document()`:** `model_dump()` + convert `type` enum to `.value` string.

**`_deserialize_document()`:** `dict(source)` + convert `type` string back to `EntityType` enum.

**Note on feedback:** The `SelectionFeedbackService` uses a Painless script to atomically increment `metadata.popularity` in ES. This increment persists in the index and will influence future `function_score` queries immediately (thanks to `refresh=True` in `bulk_index`).

---

### `backend/app/providers/baseline/provider.py`

**Purpose:** In-memory fuzzy search provider mimicking Cirrostrats' `fuzz_find` behavior. Used for side-by-side comparison against ES in Phase 2 benchmarks. Not used in production search routes.

```python
class BaselineProvider:
    FUZZY_THRESHOLD = 0.4   # matches Cirrostrats effective cutoff
    NAME = "baseline"
```

**Scoring (`_fuzzy_score()`):**
1. Exact substring → `1.0 + len(q) / len(t)` (highest)
2. Prefix match → `0.9 + len(q) / len(t)` (high)
3. `SequenceMatcher(None, q, t).ratio()` (Cirrostrats uses thefuzz/rapidfuzz)

Fields scored: `iata`, `icao`, `iata_flight`, `icao_flight`, `gate`, `airport_code`, `flight_number`, `name`, `display`, `searchable_text`, `*aliases`.

**`prefix_bias`:** In autocomplete mode, if any field starts with the query, `score = max(score, 0.95)`.

---

### `backend/app/providers/testing/fake_provider.py`

**Purpose:** Minimal in-memory `SearchProvider` for unit tests. Validates the Protocol abstraction without needing ES or the fuzzy scoring logic.

Stores documents in `self._documents: dict[str, SearchDocument]`. Matches by `any(term in doc.searchable_text.lower() for term in terms)`. All hits get `score=1.0`.

---

### `backend/app/infrastructure/config.py`

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    elasticsearch_url: str = "http://localhost:9200"     # alias: ELASTICSEARCH_URL
    elasticsearch_index: str = "cirro-search-v1"         # alias: ELASTICSEARCH_INDEX
    elasticsearch_request_timeout: int = 10               # alias: ELASTICSEARCH_REQUEST_TIMEOUT

@lru_cache
def get_settings() -> Settings
```

`lru_cache` means `get_settings()` returns the same `Settings` instance for the process lifetime. Changing env vars after startup has no effect. In tests that need custom settings, pass `Settings(...)` directly to `ElasticsearchProvider`.

---

### `backend/app/infrastructure/analytics_store.py`

**Purpose:** Thread-safe in-memory query analytics. Records query frequency, mode distribution, and zero-result queries.

```python
class AnalyticsStore:
    def record(self, query: str, mode: str, *, result_count: int) -> None
    def top_queries(self, n: int = 20) -> list[tuple[str, int]]
    def top_zero_result_queries(self, n: int = 20) -> list[tuple[str, int]]
    def mode_distribution(self) -> dict[str, int]
    def query_count(self, query: str) -> int
    def total_searches(self) -> int
    def stats(self) -> dict   # all of the above combined

_store = AnalyticsStore()     # module-level singleton

def get_analytics_store() -> AnalyticsStore   # FastAPI dependency
```

**Thread safety:** All methods acquire `self._lock` (a `threading.Lock`) before accessing counters. `Counter` is not thread-safe on its own.

**Unbounded counter caveat:** `_query_counts` grows without bound — every unique query string adds an entry that is never evicted. In a long-running deployment with diverse query traffic this will grow indefinitely. The docstring notes "Upgrade to SQLite in Phase 5 if needed."

**Data loss on restart:** All counters are in-memory. Trending resets on every server restart.

---

### `backend/app/infrastructure/seed/loader.py`

**Purpose:** Convert raw seed JSON records to `SearchDocument` objects for indexing.

```python
def default_seed_dir() -> Path
    # → repo_root / data / seed

def load_seed_documents(seed_dir: Path | None = None) -> list[SearchDocument]
    # Loads airports.json + flights.json + gates.json → list of SearchDocument

def airport_to_document(record: dict) -> SearchDocument
def flight_to_document(record: dict) -> SearchDocument
def gate_to_document(record: dict) -> SearchDocument
```

**`airport_to_document()`:**
- `id = record["id"]` (e.g. `"airport:CDG"`)
- `display = f"{iata} - {name}"` if iata else name
- `searchable_text` = deduplicated tokens from: iata, icao, name, city, aliases
- `metadata = {"popularity": record.get("popularity", 0)}`

**`flight_to_document()`:**
- `airline_name` = `IATA_TO_AIRLINE_NAME.get(airline.upper())` — resolves from codes.py table
- `display = f"{icao_flight} ({iata_flight}) - {airline}"` if iata_flight else icao_flight
- `searchable_text` = tokens from: iata_flight, icao_flight, flight_number, airline, aliases

**`gate_to_document()`:**
- `id = record["id"]` (e.g. `"gate:EWR:C101"`)
- `display = f"{airport_code} - {gate} Departures"`
- `name = record.get("airport_name")`
- `city = record.get("airport_city")`
- `searchable_text` = tokens from: airport_code, gate, display, aliases

---

## 6. Backend — Search Pipeline (end-to-end trace)

**Query:** `ua44` — HTTP submit search.

### Step 1: HTTP request arrives

```
GET /api/v1/search?q=ua44
```

FastAPI routes to `search()` in `api/routes/search.py`. FastAPI resolves dependencies: `get_search_pipeline()` (creates/returns cached `SearchPipeline`) and `get_analytics_store()` (returns module singleton).

### Step 2: `SearchService.search()` called

```python
# routes/search.py
response = service.search("ua44", limit=10)
# delegates to:
self._pipeline.run("ua44", mode=SearchMode.SUBMIT, limit=10)
```

### Step 3: `SearchPipeline.run()` — timer started

```python
started = time.perf_counter()
normalized = normalize_query("ua44")
# → "ua44"  (strip + collapse whitespace — no change here)
```

### Step 4: `QueryClassifier.classify("ua44")`

1. `upper = "UA44"`, `compact = "UA44"`
2. `_match_icao_airport("UA44")` → `ICAO_AIRPORT_PATTERN` `^[KC][A-Z]{3}$` → no match
3. `_match_flight("UA44")` → iterates ICAO codes first (UAL, GJS, etc.) → none start "UA44" (UAL ≠ UA prefix). Iterates IATA codes: `"UA"` → `"UA44".startswith("UA")` = True, `"44".isdigit()` = True → match.
   - `code_type = "IATA"`, `iata_airline_code = "UA"`, `icao_airline_code = IATA_TO_ICAO["UA"] = "UAL"`, `flight_number = "44"`
4. Returns `ClassificationResult(query_type=FLIGHT, matched_pattern="iata_flight", flight=FlightIdentifier(...))`

### Step 5: `build_expansions(classification)`

`classification.flight` is set:
```python
expand_flight_identifiers("UA", "UAL", "44")
→ ["UAL44", "GJS44", "UCA44", "SKW44", "RPA44", "OO44", "UA44"]
```

Returns `["UAL44", "GJS44", "UCA44", "SKW44", "RPA44", "OO44", "UA44"]`.

### Step 6: `AliasResolver.resolve("ua44", classification)`

Lookup: `"ua44"` in `self._by_term`. Not present in aliases.json.
Classification query_type is `FLIGHT`, not `AMBIGUOUS`, so returns:
```python
AliasResolution(matched=False)
```
`expanded_terms = []`, `entity_id = None`.

### Step 7: `resolve_entity_type(classification, alias)`

`alias.entity_type` is None (no alias match).
Falls back to `classification.entity_type`:
```python
QueryType.FLIGHT → EntityType.FLIGHT
```
Returns `EntityType.FLIGHT`.

### Step 8: `collect_search_terms("ua44", expansions, alias)`

```python
terms = ["ua44", "UAL44", "GJS44", "UCA44", "SKW44", "RPA44", "OO44", "UA44"]
# deduplicated by lowercase — no duplicates here
```

### Step 9: `ElasticsearchProvider.search()` called

`_search_provider()` dispatches to `provider.search()` (SUBMIT mode).
`build_search_query(query="ua44", entity_type=FLIGHT, expanded_terms=[...], limit=10)`:
- Filter: `{"term": {"type": "flight"}}`
- For each of the 8 terms: term queries on code fields (boosted 20), term query on flight_number (boost 40), multi_match with fuzziness AUTO
- Wrapped in function_score with popularity factor

ES executes the query, returns hits for UA44, UAL44, etc.

### Step 10: Fallback check

`provider_response.hits` is not empty → fallback skipped. `fallback_used = False`.

### Step 11: `BasicRanker.rank(hits, classification, "ua44")`

For each hit, `_score_hit()` runs:
- Base: raw ES BM25 score (e.g. `15.3`)
- `preferred_entity_id = None` → no alias boost
- `expected_type = EntityType.FLIGHT` → for flight hit: `score += 50` → `65.3`; `explanation = ["es_score", "type_alignment"]`
- For the UA44 hit: `doc.iata_flight.lower() = "ua44" == "ua44"` → `score += 200` → `265.3`; `explanation` appends `"exact_iata_flight"`
- `"ua44" in doc.searchable_text.lower()` → True → `score += 25` → `290.3`; appends `"searchable_text_match"`
- `doc.metadata.get("popularity", 0) = 50` → `score += 5.0` → `295.3`; appends `"popularity"`
- Final explanation: `["es_score", "type_alignment", "exact_iata_flight", "searchable_text_match", "popularity"]`

Hits sorted descending. UA44 surfaces at rank 1.

### Step 12: `BasicRanker.to_search_results(ranked)`

Strips `rank` field, returns `list[SearchResult]`.

### Step 13: `PipelineResponse` assembled

```python
PipelineResponse(
    query="ua44", mode="submit", results=[SearchResult(id="flight:UA44", ...)],
    debug=PipelineDebug(
        classification={"query_type": "flight", "normalized_query": "ua44", ...},
        expansions=["ua44", "UAL44", ...],
        alias_resolution=None,
        provider="elasticsearch",
        provider_took_ms=8,
        pipeline_took_ms=12,
        fallback_used=False,
    )
)
```

### Step 14: `_to_schema()` — serialization

`SearchResponseSchema` built from `PipelineResponse`. Each `SearchResult` → `SearchResultSchema` via `model_validate(r.model_dump())`.

### Step 15: HTTP response returned

JSON body: `SearchResponseSchema` with all fields. Status 200.

### Step 16: Analytics recorded (side effect)

```python
analytics.record("ua44", "submit", result_count=1)
# increments _query_counts["ua44"], _mode_counts["submit"]
```

---

## 7. Backend — API Endpoint Reference

| Method | Path | Auth | Query Params | Request Body | Response | Description |
|---|---|---|---|---|---|---|
| GET | `/health` | None | — | — | `HealthResponseSchema` | Provider health check; status="ok" or "degraded" |
| GET | `/api/v1/search` | None | `q` (str, required), `limit` (int, 1–100, default 10) | — | `SearchResponseSchema` | Full submit search; runs complete pipeline |
| GET | `/api/v1/suggestions` | None | `q` (str, required), `limit` (int, 1–50, default 10) | — | `SearchResponseSchema` | Autocomplete suggestions; uses prefix/edge-ngram queries |
| GET | `/api/v1/analytics/stats` | None | — | — | `dict` | Total searches, unique queries, zero-result queries, mode distribution, top 10 |
| GET | `/api/v1/trending` | None | `limit` (int, 1–50, default 10) | — | `{"queries": [{query, count}]}` | Top N queries by search count since last restart |
| POST | `/api/v1/feedback/select` | None | — | `{"result_id": str}` | 204 No Content | Record user selection; atomically increments `metadata.popularity` in ES |

---

## 8. Backend — Data Models

### Domain Models

| Model | File | Key fields |
|---|---|---|
| `EntityType` | models/entity_type.py | AIRPORT / FLIGHT / GATE |
| `SearchMode` | models/entity_type.py | AUTOCOMPLETE / SUBMIT |
| `QueryType` | models/query.py | AIRPORT_ICAO / AIRPORT_IATA / FLIGHT / DIGITS / GATE / AMBIGUOUS / UNKNOWN |
| `FlightIdentifier` | models/query.py | code_type, iata_airline_code, icao_airline_code, flight_number |
| `ClassificationResult` | models/query.py | query_type, normalized_query, confidence, matched_pattern, flight, airport_code, gate, digits |
| `AliasResolution` | models/query.py | matched, entity_id, entity_type, expanded_terms |
| `SearchResult` | models/result.py | id, type, display, score, iata, icao, airline, airline_name, explanation, matched_fields, metadata |
| `RankedResult` | models/result.py | SearchResult + rank (int) |
| `PipelineDebug` | models/result.py | classification, expansions, alias_resolution, provider, provider_took_ms, pipeline_took_ms, fallback_used |
| `PipelineResponse` | models/result.py | query, mode, results, debug |
| `Airport` | models/airport.py | id, iata, icao, name, city, country, aliases |
| `Flight` | models/flight.py | id, airline, iata_flight, icao_flight, flight_number, aliases |
| `Gate` | models/gate.py | id, airport_code, gate, aliases |

### Provider Models

| Model | Key fields |
|---|---|
| `SearchDocument` | id, type, display, searchable_text, iata, icao, name, city, country, airline, airline_name, iata_flight, icao_flight, flight_number, airport_code, gate, aliases, metadata |
| `ProviderSearchRequest` | query, mode, entity_type, expanded_terms, limit |
| `ProviderAutocompleteRequest` | query, entity_type, expanded_terms, limit |
| `ProviderHit` | document, score, matched_fields |
| `ProviderSearchResponse` | hits, took_ms, provider |
| `BulkIndexResult` | indexed, failed, errors |
| `ProviderHealth` | status (ProviderHealthStatus), provider, message, details |

### API Schemas

| Schema | Mirrors |
|---|---|
| `SearchResultSchema` | `SearchResult` — identical fields |
| `PipelineDebugSchema` | `PipelineDebug` — identical fields |
| `SearchResponseSchema` | `PipelineResponse` |
| `HealthResponseSchema` | status, provider, provider_status, index |

---

## 9. Backend — Elasticsearch Index

### Index Name

Default: `cirro-search-v1` (configurable via `ELASTICSEARCH_INDEX` env var).

### Mappings

| Field | ES Type | Analyzer | Sub-fields | Purpose |
|---|---|---|---|---|
| `id` | keyword | — | — | Unique doc ID; also `_id` |
| `type` | keyword | — | — | "airport" / "flight" / "gate" |
| `display` | text | search_text_analyzer | `.keyword` | Human-readable label |
| `searchable_text` | text | search_text_analyzer | `.edge` (edge_ngram, indexed w/ search_text_edge_analyzer) | Combined name/code/city blob; edge sub-field for autocomplete |
| `iata` | keyword | — | — | 3-letter airport code |
| `icao` | keyword | — | — | 4-letter airport code |
| `name` | text | search_text_analyzer | — | Full airport/airline name |
| `city` | text | search_text_analyzer | — | City name |
| `country` | keyword | — | — | ISO 2-letter country code |
| `airline` | keyword | — | — | 2-letter IATA airline code |
| `iata_flight` | keyword | — | — | e.g. "UA44" |
| `icao_flight` | keyword | — | — | e.g. "UAL44" |
| `flight_number` | keyword | — | — | Bare digits only: "44" |
| `airport_code` | keyword | — | — | For gates: the airport IATA |
| `gate` | keyword | — | — | e.g. "C101" |
| `aliases` | text | search_text_analyzer | — | Known alternative names |
| `metadata` | object | — | enabled: true | popularity counter etc. |

### Settings

```json
{
  "number_of_shards": 1,
  "number_of_replicas": 0,
  "analysis": {
    "tokenizer": {
      "edge_ngram_tokenizer": { "type": "edge_ngram", "min_gram": 2, "max_gram": 20, "token_chars": ["letter", "digit"] }
    },
    "analyzer": {
      "search_text_analyzer":      { "type": "custom", "tokenizer": "standard", "filter": ["lowercase", "asciifolding"] },
      "search_text_edge_analyzer": { "type": "custom", "tokenizer": "edge_ngram_tokenizer", "filter": ["lowercase", "asciifolding"] }
    }
  }
}
```

### Serialized Airport Document Example

```json
{
  "_id": "airport:CDG",
  "_source": {
    "id": "airport:CDG",
    "type": "airport",
    "display": "CDG - Charles de Gaulle Airport",
    "searchable_text": "cdg lfpg charles de gaulle airport paris",
    "iata": "CDG",
    "icao": "LFPG",
    "name": "Charles de Gaulle Airport",
    "city": "Paris",
    "country": "FR",
    "airline": null,
    "airline_name": null,
    "iata_flight": null,
    "icao_flight": null,
    "flight_number": null,
    "airport_code": null,
    "gate": null,
    "aliases": ["cdg", "lfpg", "paris", "charles de gaulle airport", "roissy", "cdg airport"],
    "metadata": { "popularity": 90 }
  }
}
```

---

## 10. Backend — Tests

### Unit Tests (`backend/tests/unit/`)

No ES required. Use `FakeSearchProvider` or direct instantiation.

| File | What it tests | Run command |
|---|---|---|
| `test_classifier.py` | 10 parametrized cases: KEWR→ICAO, EWR→IATA, UA4433→FLIGHT, UAL4433→FLIGHT, 4433→DIGITS, C101→GATE, Newark→AMBIGUOUS, "newark airport"→AMBIGUOUS, "united 4433"→FLIGHT, ""→UNKNOWN | `pytest tests/unit/test_classifier.py` |
| `test_ranker.py` | Score signal application; exact code boosts; alias entity match | `pytest tests/unit/test_ranker.py` |
| `test_aliases.py` | AliasResolver loading, term expansion per entity_id prefix | `pytest tests/unit/test_aliases.py` |
| `test_airline_mapping.py` | IATA↔ICAO round-trip; expand_flight_identifiers codeshare output | `pytest tests/unit/test_airline_mapping.py` |
| `test_elasticsearch_queries.py` | build_search_query and build_autocomplete_query output shape; entity_type filter inclusion | `pytest tests/unit/test_elasticsearch_queries.py` |
| `test_pipeline_stages.py` | normalize_query, build_expansions, resolve_entity_type, collect_search_terms | `pytest tests/unit/test_pipeline_stages.py` |
| `test_provider_protocol.py` | isinstance check on FakeSearchProvider; Protocol contract compliance | `pytest tests/unit/test_provider_protocol.py` |

Run all unit tests:
```bash
cd backend && pytest tests/unit/
```

### Integration Tests (`backend/tests/integration/`)

Require ES at `http://localhost:9200`. Use `pytest.mark.integration`.

| File | What it tests | Requires ES |
|---|---|---|
| `test_elasticsearch_provider.py` | index_document, delete_document, bulk_index, search, autocomplete, get_health | Yes |
| `test_search_api.py` | Full HTTP API via FastAPI TestClient (httpx); search + suggestions + health endpoints | Yes |

Run:
```bash
pytest tests/integration/ -m integration
```

### Evaluation Tests (`backend/tests/evaluation/`)

Require ES. Each test creates a temporary isolated index (UUID suffix), seeds all data, runs cases, then tears down. All marked `pytest.mark.integration`.

| File | Cases | What it verifies |
|---|---|---|
| `test_phase1_cases.py` | 9 cases from `evaluation/cases/phase1.yaml` | Original Phase 1 requirements (aliases, codeshare, etc.) |
| `test_regression_cases.py` | 78 cases from `evaluation/cases/regression.yaml` | All known Cirrostrats bugs + extended coverage |
| `test_provider_comparison.py` | All cases from both suites | ES vs Baseline side-by-side pass rates |
| `test_experiments.py` | exp-001, exp-002, exp-003 | All 3 experiment variants run; winner reported |

Current pass rate: **87/87** across both suites (as of Phase 4 benchmarks).

### Benchmark Tests (`backend/tests/benchmarks/`)

| File | What it measures |
|---|---|
| `bench_latency.py` | P50/P95/P99 latency for search and suggestions against real ES |
| `compare_providers.py` | Head-to-head latency: ES vs Baseline provider |
| `test_latency_targets.py` | Asserts latency targets (e.g. p95 < 50ms for suggestions) |

---

## 11. Frontend — Complete File Reference

### `frontend/index.html`

HTML shell. Defines `box-sizing: border-box` global reset, dark background (`#0a0a14`), and critically: the `@keyframes pulse` animation used by skeleton loading cards in `ResultPanel.tsx`:

```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
```

This keyframe is defined in the HTML `<style>` block rather than in component CSS because `ResultPanel` references it by name in an inline style object (`animation: 'pulse 1.4s ease-in-out infinite'`).

---

### `frontend/src/main.tsx`

Entry point. Mounts the React app.

```tsx
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
)
```

`StrictMode` causes effects to run twice in development — this can cause double trending fetches in Playground. Expected behavior.

---

### `frontend/src/App.tsx`

Route definitions.

```tsx
<Routes>
  <Route path="/"       element={<Playground />} />
  <Route path="/result" element={<ResultDetail />} />
</Routes>
```

`/result` receives state via `navigate('/result', { state: { result, debug, query } })` from `ResultPanel`. If navigated to directly without state, `ResultDetail` shows a "No result selected" fallback.

---

### `frontend/src/theme.ts`

Design token system. All components import from here — no hardcoded color strings in components.

```typescript
export const colors = {
  bg: '#0a0a14',           // page background
  surface: '#0f0f1a',      // card background
  surfaceAlt: '#141420',   // alternate surface (section headers)
  panel: '#1a1a2e',        // panel background, border
  panelHover: '#1e1e3a',   // hover state
  panelActive: '#252545',  // active state
  border: '#1e1e3a',       // standard border
  borderSubtle: '#333',    // subtle border
  borderMuted: '#2a2a3a',  // muted border
  borderDim: '#2a2a2a',    // dim border
  text: '#e0e0e0',         // primary text
  textMuted: '#888',       // secondary text
  textDim: '#555',         // tertiary text
  textFaint: '#444',       // faintest text
  accent: '#7eb8f7',       // blue accent (codes, links)
  accentHover: '#3d7de8',  // accent on hover
  accentActive: '#4f8ef7', // accent active
  accentDisabled: '#3a6bbf', // disabled button
  matchedField: '#3a5a3a', // matched field tag text
  matchedFieldBg: '#0d1a0d',
  matchedFieldBorder: '#1a2e1a',
  score: '#3a3a5a',        // score display
  error: '#f77',
  errorBg: '#1a0808',
  errorBorder: '#a33',
  fallbackGreen: '#5a3',   // fallback triggered indicator
  fallbackGreenBg: '#1a3a1a',
}

export const font = { mono: 'monospace' }

export const radius = { sm: 4, md: 6, lg: 8 }  // border-radius values in px
```

---

### `frontend/src/types/search.ts`

TypeScript interfaces mirroring backend Pydantic schemas.

```typescript
interface SearchResult {
  id: string; display: string; type: 'airport' | 'flight' | 'gate' | string; score: number
  iata: string | null; icao: string | null; name: string | null; city: string | null
  country: string | null; airline: string | null; airline_name: string | null
  iata_flight: string | null; icao_flight: string | null; flight_number: string | null
  airport_code: string | null; gate: string | null
  matched_fields: string[]; explanation: string[]; metadata: Record<string, unknown>
}

interface DebugInfo {
  classification: { query_type: string; normalized_query: string; matched_pattern: string; entity_type: string | null }
  expansions: string[]
  alias_resolution?: { matched: boolean; entity_id: string | null; entity_type: string | null } | null
  provider: string; provider_took_ms: number; pipeline_took_ms: number; fallback_used: boolean
}

interface SearchResponse { query: string; mode: string; results: SearchResult[]; debug: DebugInfo }

type SuggestionResponse = SearchResponse   // same shape, different semantic intent
```

---

### `frontend/src/pages/Playground.tsx`

Main search page. Composes `useSearch`, `useRecentSearches`, and a `trending` local state.

**State managed:**
```typescript
// from useSearch:
query, submitResult, suggestionResult, loading, error, setQuery, submit

// from useRecentSearches:
recents, saveRecent, removeRecent

// local:
trending: TrendingQuery[]  // fetched once on mount from /api/v1/trending?limit=6
```

**Trending fetch:** `useEffect` with empty deps — fires on mount. Calls `fetch('/api/v1/trending?limit=6')`. Silently ignores errors. Re-runs on StrictMode double-invoke in dev.

**`activeResult`:** `submitResult ?? suggestionResult` — shows suggestion cards while typing, switches to submit results on Enter.

**Renders:** `<SearchInput>` + `<ResultPanel>` inside a centered flex column with padding and max-width of 900px.

---

### `frontend/src/pages/ResultDetail.tsx`

Detail page for a clicked result. Receives state from `navigate('/result', { state })`.

**Location state shape:**
```typescript
interface LocationState {
  result: SearchResult
  debug: SearchResponse['debug']
  query: string
}
```

**`QUERY_TYPE_LABEL` map:** Maps each `query_type` string to `{ short: string; plain: string }` with human-readable explanations for both engineers and non-technical users. Keys: `AIRPORT_IATA`, `AIRPORT_ICAO`, `FLIGHT`, `GATE`, `DIGITS`, `AMBIGUOUS`, `UNKNOWN`.

**`EXPLANATION_LABEL` map:** Maps each ranker explanation code to `{ label: string; tech: string; plain: string }`. Keys: `es_score`, `exact_iata`, `exact_icao`, `exact_iata_flight`, `exact_icao_flight`, `exact_gate`, `exact_flight_number`, `type_alignment`, `alias_entity_match`, `digits_match`, `searchable_text_match`, `popularity`.

**Sections rendered:**
1. **"What you searched"** — query type, normalized query, entity_type filter, alias resolution, expansions, fallback
2. **"Why [result.display] ranked here"** — relevance score, all explanation codes
3. **"Where in the document the match was found"** — matched_fields (if any)
4. **"Performance"** — pipeline_took_ms, provider_took_ms, and derived pipeline overhead

---

### `frontend/src/components/SearchInput.tsx`

```typescript
interface Props {
  value: string
  loading: boolean
  onChange: (v: string) => void
  onSubmit: (v: string) => void
}
```

**Cycling placeholder:** Uses `useCyclingPlaceholder(PLACEHOLDERS, 3000)` — cycles through 4 placeholder strings every 3 seconds.

**Button states:**
- Normal: `colors.accentActive` background, "Search" label
- Hover: `colors.accentHover` background
- Loading: `colors.accentDisabled` background, "…" label, `disabled` attr, `cursor: not-allowed`

**Keyboard:** Enter → `onSubmit(value)`, Escape → `onChange('')`.

---

### `frontend/src/components/ResultPanel.tsx`

The most complex component. Handles 4 states:

1. **Loading (no prior result):** 3 `<SkeletonCard>` components with pulse animation
2. **Error:** red error banner with error text
3. **No result (discovery panel):** shows recents (up to 5) → trending (up to 6) → featured chips (if both empty). `FEATURED = ['heathrow', 'ua44', 'cdg', 'ewr c101', 'dubai', 'hong kong', '4433', 'kewr']`
4. **Results:** stats row (count, ms, ES ms, fallback badge, show/hide debug) → result cards → optional `<DebugPanel>`

**`ResultCard`:** Dispatches to `AirportCard`, `FlightCard`, or `GateCard` based on `result.type`. On click: `recordSelection(r.id)` (fire-and-forget), `saveRecent(r, query)`, `navigate('/result', {state})`.

**`SkeletonCard`:** Two skeleton blocks (icon + lines) with `pulse` animation. Animation defined in `index.html`.

**`DebugPanel`:** Three sections:
1. "What you typed" — raw query, understood as (QUERY_TYPE_LABEL), searched only, alias, expansions, fallback
2. "Speed" — total time, ES time, pipeline overhead
3. "Why [top result] ranked #1" — score, all explanation codes via EXPLANATION_LABEL

`TYPE_ICON`: `{ airport: '✈', flight: '→', gate: '▣' }`

---

### `frontend/src/components/AirportCard.tsx`

```typescript
interface Props { result: SearchResult; query?: string; onClick?: () => void }
```

**`countryFlag(iso: string | null): string`:** Converts ISO 2-letter country code to Unicode flag emoji using Regional Indicator Symbol Letters (code point offset `0x1F1E6 - 65`). Returns `'✈'` if iso is null or not 2 chars.

**Renders:** flag emoji | IATA code (highlighted) + ICAO sub-label | airport name (highlighted) + city/country + matched_fields tags.

**Highlight:** `highlightMatch(text, query)` applied to code and name.

---

### `frontend/src/components/FlightCard.tsx`

```typescript
interface Props { result: SearchResult; query?: string; onClick?: () => void }
```

**Airline name resolution:**
```typescript
const airlineName =
  result.airline_name ??
  (result.display.includes(' - ')
    ? result.display.split(' - ').slice(1).join(' - ')
    : result.airline ?? '')
```
Prefers `airline_name` field (populated from `IATA_TO_AIRLINE_NAME` in loader), falls back to parsing display string.

**Renders:** ✈ icon | IATA flight code (highlighted) + ICAO sub-label | airline name (highlighted) + "Flight {number}" + matched_fields tags.

---

### `frontend/src/components/GateCard.tsx`

```typescript
interface Props { result: SearchResult; query?: string; onClick?: () => void }
```

**Renders:** ▣ icon | gate label (highlighted) | `{airport_code} — {name}` + city + matched_fields tags.

---

### `frontend/src/components/SuggestionList.tsx`

**Status: ORPHANED** — not imported or rendered anywhere in the current codebase. Originally designed as a floating dropdown positioned absolutely below `SearchInput`. Superseded by the inline results in `ResultPanel` (which shows suggestion cards in the main panel rather than a floating dropdown).

Props: `{ results: SearchResult[]; onSelect: (display: string) => void }`. Shows up to 6 results.

---

### `frontend/src/components/EmptyStateDropdown.tsx`

**Status: ORPHANED** — not imported or rendered anywhere. Originally a standalone component for showing recents + trending as an absolute-positioned dropdown. Its functionality was integrated into `ResultPanel`'s discovery panel (the `!result` branch). This component has its own `useEffect` that fetches `/api/v1/trending` independently.

---

### `frontend/src/hooks/useSearch.ts`

Core search state manager. Returns: `{ query, submitResult, suggestionResult, loading, error, setQuery, submit, selectSuggestion }`.

**Full state shape:**
```typescript
interface SearchState {
  query: string
  submitResult: SearchResponse | null
  suggestionResult: SuggestionResponse | null
  loading: boolean
  error: string | null
}
```

**`setQuery(q)`:** Updates query state, clears error. Cancels pending debounce. If `q.trim()` is empty, clears `suggestionResult` immediately. Otherwise sets 200ms debounce timer to call `suggestions(q)` → sets `suggestionResult`.

**`submit(q)`:** Cancels pending debounce. Normalizes: `q.trim().toLowerCase().replace(/\s+/g, '')`.

**Waterfall logic (submit):**
1. Check `suggestionResultRef.current` for exact match: `r.iata?.toLowerCase() === normalizedQ` OR `r.icao?.toLowerCase() === normalizedQ` OR `r.iata_flight?.toLowerCase().replace(/\s+/g, '') === normalizedQ` OR `r.gate?.toLowerCase() === normalizedQ`.
2. If hit found → set `submitResult` from cached suggestion, clear `suggestionResult`, return (no API call).
3. If no hit → call `search(q)` → set `submitResult`, clear `suggestionResult`.

**`suggestionResultRef` stale closure fix:** `submit` has `[]` deps (stable reference). Without the ref, it would capture the initial `null` value of `suggestionResult` forever. A `useEffect` syncs the ref on every `suggestionResult` change, giving `submit` access to current suggestions without being in its dep array.

**`selectSuggestion(q)`:** Bypasses debounce and suggestion cache — directly calls `search(q)`. Used when a suggestion card is explicitly clicked (as opposed to pressing Enter on the typed query).

---

### `frontend/src/hooks/useRecentSearches.ts`

```typescript
interface RecentSearch {
  id: string; display: string; type: 'airport' | 'flight' | 'gate' | string
  iata: string | null; icao: string | null; iata_flight: string | null; gate: string | null
  query: string; savedAt: number
}

const MAX_RECENTS = 10
const STORAGE_KEY = 'cirro_recent_searches'
```

**Functions:**
- `saveRecent(result, query)`: deduplicates by `result.id` (removes existing entry with same id), prepends new entry, slices to `MAX_RECENTS`. Writes to localStorage.
- `removeRecent(id)`: filters by id, writes to localStorage.
- `clearAll()`: removes localStorage key, resets state.

**Error handling:** Every localStorage read/write is wrapped in try/catch. Failures degrade silently — private browsing, storage full, or JSON corruption all handled gracefully.

---

### `frontend/src/hooks/useCyclingPlaceholder.ts`

```typescript
function useCyclingPlaceholder(options: string[], intervalMs: number): string
```

Cycles `index` state through `[0, options.length)` at `intervalMs` interval using `setInterval`. If `options.length <= 1`, skips the effect (no cycling needed). Cleans up interval on unmount.

---

### `frontend/src/api/searchClient.ts`

```typescript
const BASE = '/api/v1'

export async function search(q: string): Promise<SearchResponse>
// GET /api/v1/search?q=<encoded>; throws Error with status code on non-ok response

export async function suggestions(q: string): Promise<SuggestionResponse>
// GET /api/v1/suggestions?q=<encoded>; throws Error on non-ok response
```

Both use `encodeURIComponent(q)`. No retry logic, no timeout — relies on browser fetch defaults.

---

### `frontend/src/api/feedbackClient.ts`

```typescript
export function recordSelection(resultId: string): void
```

**Fire-and-forget pattern:** `fetch(...)` call is not awaited. The returned Promise is not stored. `.catch(() => {})` swallows all errors. This function must never block navigation or show an error to the user.

---

### `frontend/src/utils/highlight.tsx`

```typescript
export function highlightMatch(text: string, query: string | undefined): React.ReactNode
```

**Algorithm:** Finds first occurrence of `query.trim().toLowerCase()` in `text.toLowerCase()` using `indexOf`. Splits `text` into three slices: before, match, after. Wraps match in `<mark>` with `background: transparent`, `color: colors.accent`, `fontWeight: 700`.

**Why indexOf, not regex:** User input can contain regex special characters (`(`, `[`, `.`, `*`, etc.) that would cause `new RegExp(query)` to throw. `indexOf` is safe for arbitrary input and avoids the need for escaping.

---

## 12. Frontend — State Flow

```
useSearch (hook)
  ├── query ──────────────────────► SearchInput.value
  ├── loading ────────────────────► SearchInput.loading
  ├── setQuery ───────────────────► SearchInput.onChange
  ├── submit ─────────────────────► SearchInput.onSubmit
  │
  ├── submitResult \
  │                 ┤ activeResult = submitResult ?? suggestionResult
  ├── suggestionResult /           ► ResultPanel.result
  ├── loading ────────────────────► ResultPanel.loading
  └── error ──────────────────────► ResultPanel.error

useRecentSearches (hook)
  ├── recents ────────────────────► ResultPanel.recents
  ├── saveRecent ─────────────────► ResultPanel.saveRecent
  └── removeRecent ───────────────► ResultPanel.onRemoveRecent

Playground (local state)
  └── trending ───────────────────► ResultPanel.trending

ResultPanel
  └── on card click:
        recordSelection(r.id)      ← feedbackClient (fire-and-forget)
        saveRecent(r, query)       ← writes to localStorage
        navigate('/result', {      ← react-router
          state: { result, debug, query }
        })

ResultDetail
  └── location.state = { result, debug, query }
      renders full detail + EXPLANATION_LABEL + QUERY_TYPE_LABEL maps
```

---

## 13. Frontend — Request Lifecycle

### Scenario A — User types "ew" (suggestion flow)

1. `onChange` fires → `setQuery("ew")` called
2. Previous debounce timer cancelled. New 200ms timer set.
3. 200ms elapses (no further keystrokes)
4. `suggestions("ew")` called → `GET /api/v1/suggestions?q=ew`
5. Backend runs pipeline in AUTOCOMPLETE mode: prefix queries on code fields + edge-ngram on `searchable_text.edge`
6. Response arrives → `suggestionResult` set
7. `activeResult = submitResult ?? suggestionResult` — since `submitResult` is null, `suggestionResult` is shown
8. ResultPanel renders suggestion cards (AirportCard/FlightCard/GateCard for each result)

### Scenario B — User presses Enter with "ewr" in input (submit waterfall)

1. `onKeyDown Enter` → `submit("ewr")` called
2. Pending debounce timer cancelled (if any)
3. `normalizedQ = "ewr"` (lowercase, space-stripped)
4. Check `suggestionResultRef.current` — if suggestions exist from previous "ew"/"ewr" typing:
   - Scan results: `r.iata?.toLowerCase() === "ewr"` → if Newark Liberty found in suggestions → hit!
   - Set `submitResult = { ...currentSuggestions, results: [hit], mode: 'submit' }`, clear `suggestionResult`, **return** (no HTTP call)
5. If no exact match in suggestions → `loading = true`, `GET /api/v1/search?q=ewr` fires
6. Backend: classifier → AIRPORT_IATA, entity_type = AIRPORT, search only airports, rank, return
7. Response → `submitResult` set, `suggestionResult` cleared, `loading = false`
8. ResultPanel shows submit results

---

## 14. Frontend — Local Storage

| Key | Value type | Max items | Dedup strategy |
|---|---|---|---|
| `cirro_recent_searches` | `RecentSearch[]` (JSON array) | 10 (`MAX_RECENTS`) | By `result.id` — duplicate id is removed before prepending |

**`RecentSearch` shape stored:**
```typescript
{
  id: string           // e.g. "airport:EWR"
  display: string      // e.g. "EWR - Newark Liberty International Airport"
  type: string         // "airport" | "flight" | "gate"
  iata: string | null
  icao: string | null
  iata_flight: string | null
  gate: string | null
  query: string        // the search query that produced this result
  savedAt: number      // Date.now() timestamp
}
```

**Error handling:** `readFromStorage()` and `writeToStorage()` both wrap localStorage calls in try/catch. `readFromStorage()` returns `[]` on any error. `writeToStorage()` silently ignores errors (storage full, private mode).

---

## 15. Data — Seed Files

### `data/seed/airports.json`

| Property | Value |
|---|---|
| Record count | ~85,545 (global — from OurAirports CSV) |
| Types included | large_airport, medium_airport, small_airport |
| Generated by | `scripts/convert_airports.py` |

**Full record schema:**
```json
{
  "id": "airport:CDG",
  "iata": "CDG",
  "icao": "LFPG",
  "name": "Charles de Gaulle Airport",
  "city": "Paris",
  "country": "FR",
  "aliases": ["cdg", "lfpg", "paris", "charles de gaulle airport", "roissy", ...],
  "popularity": 90
}
```

**Loader function:** `airport_to_document(record)` → `SearchDocument` with `type=AIRPORT`.

---

### `data/seed/flights.json`

| Property | Value |
|---|---|
| Record count | ~35 airlines × 59 flight numbers = ~2,065 records |
| Data type | Synthetic (not real-time) |
| Generated by | `scripts/generate_flights.py` |

**Full record schema:**
```json
{
  "id": "flight:UA44",
  "airline": "UA",
  "iata_flight": "UA44",
  "icao_flight": "UAL44",
  "flight_number": "44",
  "aliases": ["ua44", "ual44"],
  "popularity": 100
}
```

**Loader function:** `flight_to_document(record)` → `SearchDocument` with `type=FLIGHT`, `airline_name` resolved via `IATA_TO_AIRLINE_NAME`.

---

### `data/seed/gates.json`

| Property | Value |
|---|---|
| Record count | Depends on airports with popularity ≥50; large airports get 4 terminals × (30 + 21 extra in C) |
| Generated by | `scripts/generate_gates.py` |

**Full record schema:**
```json
{
  "id": "gate:EWR:C101",
  "airport_code": "EWR",
  "gate": "C101",
  "airport_name": "Newark Liberty International Airport",
  "airport_city": "Newark",
  "aliases": ["ewr c101", "ewr-c101", "c101 ewr"],
  "popularity": 90
}
```

**Loader function:** `gate_to_document(record)` → `SearchDocument` with `type=GATE`.

---

### `data/seed/aliases.json`

| Property | Value |
|---|---|
| Record count | ~50+ alias entries |
| Format | Array of `{term, entity_id, entity_type}` objects |
| Loaded by | `AliasResolver.__init__()` |

**Sample records:**
```json
[
  { "term": "newrk",        "entity_id": "airport:EWR", "entity_type": "airport" },
  { "term": "newark",       "entity_id": "airport:EWR", "entity_type": "airport" },
  { "term": "ewr c101",     "entity_id": "gate:EWR:C101", "entity_type": "gate" },
  { "term": "united 4433",  "entity_id": "flight:UA4433", "entity_type": "flight" },
  { "term": "heathrow",     "entity_id": "airport:LHR", "entity_type": "airport" }
]
```

`entity_id` format: `airport:{IATA}`, `flight:{IATA_FLIGHT}`, `gate:{AIRPORT_CODE}:{GATE}`.

---

## 16. Scripts

### `scripts/convert_airports.py`

**Purpose:** Converts OurAirports `airports.csv` to `data/seed/airports.json`.

**Usage:**
```bash
python scripts/convert_airports.py [input_csv] [output_json]
# Defaults: ~/Downloads/airports(1).csv → data/seed/airports.json
```

**Input:** OurAirports CSV with fields: `iata_code`, `icao_code`, `name`, `municipality`, `iso_country`, `type`, `keywords`.

**Filter:** `type` must be in `{"large_airport", "medium_airport", "small_airport"}` — excludes heliports, seaplane bases, balloonports, closed airports.

**Popularity assignment:** `BASE_POPULARITY = {large_airport: 90, medium_airport: 60, small_airport: 30}`.

**Alias building:** Includes iata_code, icao_code, municipality, name, all keywords (comma-split), and `{municipality} airport`. All lowercased and deduplicated.

**Output format:** Same schema as shown in section 15.

---

### `scripts/generate_flights.py`

**Purpose:** Generates synthetic `data/seed/flights.json` and regenerates `backend/app/domain/airline_mapping/codes.py` from OpenFlights `airlines.dat`.

**Usage:**
```bash
python scripts/generate_flights.py [airlines_dat] [output_flights_json] [output_codes_py]
# Defaults: ~/Downloads/airlines.dat → data/seed/flights.json + backend/app/.../codes.py
```

**Flight numbers generated:** `1–50` (range) + `[100, 200, 300, 400, 500, 1000, 1500, 2000, 4433]` (key stress-test anchors) = 59 unique numbers per airline.

**Popularity:** Major carriers (UA, AA, DL, BA, LH, etc. — ~63 airlines) get `popularity=100`; others get `popularity=50`.

**`codes.py` regeneration:** Writes `IATA_TO_ICAO`, `ICAO_TO_IATA`, `IATA_AIRLINE_CODES`, `ICAO_AIRLINE_CODES`, `AIRLINE_NAMES`, and `IATA_TO_AIRLINE_NAME` from fresh airline data. This script is the source of truth for the codes tables.

---

### `scripts/generate_gates.py`

**Purpose:** Generates `data/seed/gates.json` from `data/seed/airports.json`. Only generates gates for airports with `popularity >= 50`.

**Usage:**
```bash
python scripts/generate_gates.py [airports_json] [output_gates_json]
# Defaults: data/seed/airports.json → data/seed/gates.json
```

**Terminal configuration by popularity tier:**

| Min popularity | Terminals | Gates per terminal |
|---|---|---|
| 90 (large) | A, B, C, D | A/B/D: 1–30; C: 1–30 + 100–120 (covers C101 demo case) |
| 70 (medium) | A, B | 1–15 |
| 50 (small) | A | 1–8 |

**Alias building:** For gate `C101` at airport `EWR`: generates `["ewr c101", "ewr-c101", "c101 ewr"]`.

---

## 17. Evaluation + Experiments

### Evaluation Cases

**`evaluation/cases/phase1.yaml`** — 9 cases covering the original Phase 1 requirements:
- Natural language alias: `newrk` → airport EWR, `newark airport` → EWR, `vegas airport` → LAS, `harry reid` → LAS
- Flight codeshare: `ua4433` → flight UA4433
- Digit-only flight: `4433` → flight_number 4433
- Airline name + number: `united 4433` → UA4433
- Gate by code: `c101` → gate C101
- Compound gate: `ewr c101` → gate C101 at EWR

**`evaluation/cases/regression.yaml`** — 78 cases covering:
- Extended airport queries: `ewr`, `kewr`, `newark`, `las`, `perry`, `CYOW`, `denver`, `boston logan`, `chicago ohare`, CDG, LHR, JFK, DEN, SFO, LAX, etc.
- Known Cirrostrats bugs: `las` prefix miss, `CYOW` code display bug, `perry` alias resolution bug
- City name searches: `denver`, `dubai`, `hong kong`, etc.
- Flight queries: `ba117`, `dl1`, `ua500`, `ual500`, `G74433` (codeshare), etc.
- Gate queries: various `{airport} {gate}` compound forms
- Autocomplete mode cases: partial queries in suggest mode

**How to run:**
```bash
cd backend
# Requires ES running and seeded
pytest tests/evaluation/ -m integration -v
```

Each evaluation test creates an isolated temporary index (`cirro-search-regression-{uuid}`), seeds all data, runs cases, then tears down the index after the module scope.

**Current pass rate:** 87/87 across both suites (Phase 4, measured with full global airport dataset).

### Experiments

Three Phase 3 experiments, each run by `ExperimentService`:

| Experiment | Config | Axis | Variants | Hypothesis |
|---|---|---|---|---|
| exp-001 | `exp-001-fuzzy-tolerance.yaml` | ES `fuzziness` param | auto, fixed-1, fixed-2 | AUTO performs best; fixed-2 risks EWR ↔ ERW collisions |
| exp-002 | `exp-002-field-weights.yaml` | Field boost multipliers | default (^8), high-code (^12), balanced (^6/^5) | High code boost improves 3-letter disambiguation |
| exp-003 | `exp-003-ranking-strategy.yaml` | Post-retrieval ranker | domain (BasicRanker), es-score (raw), popularity-first | Domain ranker essential for digits/codeshare disambiguation |

**How to run:**
```bash
cd backend
pytest tests/evaluation/experiments/test_experiments.py -m integration -v
```

Each variant gets its own isolated ES index. Results are compared and a winner is declared per experiment. Indices are cleaned up after (unless `keep=True` is passed to `ExperimentService.run()`).

**All three experiments confirmed ES + domain pipeline as the winning configuration in Phase 3.**
