"""
Phase 2.3 — Side-by-side comparison: ElasticsearchProvider vs BaselineProvider.

Runs all Phase 1 + regression cases against both providers.
Prints a comparison table showing which provider passes each case.
Does not assert anything across providers — just records and reports.
The pytest summary shows which cases ES wins, baseline wins, or both pass/fail.
"""

import uuid
from pathlib import Path

import pytest
import yaml
from elasticsearch import Elasticsearch

from app.application.seed_service import SeedService
from app.domain.models.entity_type import SearchMode
from app.domain.pipeline.search_pipeline import SearchPipeline
from app.infrastructure.config import Settings
from app.providers.baseline.provider import BaselineProvider
from app.providers.elasticsearch.client import ensure_index
from app.providers.elasticsearch.provider import ElasticsearchProvider

pytestmark = pytest.mark.integration

PHASE1_PATH = Path(__file__).resolve().parents[3] / "evaluation" / "cases" / "phase1.yaml"
REGRESSION_PATH = Path(__file__).resolve().parents[3] / "evaluation" / "cases" / "regression.yaml"
TEST_INDEX = f"cirro-search-compare-{uuid.uuid4().hex[:8]}"


def _elasticsearch_available() -> bool:
    try:
        client = Elasticsearch(hosts=["http://localhost:9200"], request_timeout=2)
        return bool(client.ping())
    except Exception:
        return False


def _load_all_cases() -> list[dict]:
    cases = []
    for path in (PHASE1_PATH, REGRESSION_PATH):
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        cases.extend(data["cases"])
    # Deduplicate by (query, mode)
    seen: set[tuple] = set()
    unique = []
    for c in cases:
        key = (c["query"], c.get("mode", "submit"))
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


@pytest.fixture(scope="module")
def es_pipeline() -> SearchPipeline:
    if not _elasticsearch_available():
        pytest.skip("Elasticsearch is not available at http://localhost:9200")

    settings = Settings(elasticsearch_url="http://localhost:9200", elasticsearch_index=TEST_INDEX)
    client = Elasticsearch(hosts=[settings.elasticsearch_url], request_timeout=10)
    client.indices.delete(index=TEST_INDEX, ignore_unavailable=True)
    ensure_index(client, TEST_INDEX)

    provider = ElasticsearchProvider(client=client, settings=settings, auto_create_index=False)
    SeedService(provider).seed()
    client.indices.refresh(index=TEST_INDEX)

    yield SearchPipeline(provider=provider)
    client.indices.delete(index=TEST_INDEX, ignore_unavailable=True)


@pytest.fixture(scope="module")
def baseline_pipeline() -> SearchPipeline:
    provider = BaselineProvider()
    SeedService(provider).seed()
    return SearchPipeline(provider=provider)


def _result_matches(result, expect: dict) -> bool:
    if result.type.value != expect["type"]:
        return False
    for field, value in expect.items():
        if field in ("type", "note"):
            continue
        if field == "airport":
            if result.airport_code != value:
                return False
            continue
        if getattr(result, field, None) != value:
            return False
    return True


def _passes(pipeline: SearchPipeline, case: dict) -> bool:
    try:
        mode = SearchMode(case.get("mode", "submit"))
        response = pipeline.run(case["query"], mode=mode, limit=5)
        if not response.results:
            return False
        return _result_matches(response.results[0], case["expect"])
    except Exception:
        return False


@pytest.mark.parametrize(
    "case",
    _load_all_cases(),
    ids=lambda c: f"{c['query']}[{c.get('mode', 'submit')}]",
)
def test_es_passes(es_pipeline: SearchPipeline, case: dict) -> None:
    """ES must pass all cases. Failure here is a regression."""
    mode = SearchMode(case.get("mode", "submit"))
    response = es_pipeline.run(case["query"], mode=mode, limit=5)
    assert response.results, f"ES: no results for '{case['query']}'"
    top = response.results[0]
    assert _result_matches(top, case["expect"]), (
        f"ES failed '{case['query']}': expected {case['expect']}, got "
        f"type={top.type.value} iata={top.iata} flight={top.iata_flight} gate={top.gate}"
    )


@pytest.mark.parametrize(
    "case",
    _load_all_cases(),
    ids=lambda c: f"{c['query']}[{c.get('mode', 'submit')}]",
)
def test_baseline_vs_es(
    es_pipeline: SearchPipeline,
    baseline_pipeline: SearchPipeline,
    case: dict,
) -> None:
    """
    Informational comparison. Marks xfail for cases baseline can't handle.
    Passes if baseline matches ES. Used to document where ES beats baseline.
    """
    es_pass = _passes(es_pipeline, case)
    baseline_pass = _passes(baseline_pipeline, case)

    if es_pass and not baseline_pass:
        pytest.xfail(
            f"ES wins: baseline fails '{case['query']}' — "
            f"ES resolves, baseline cannot. Expected: {case['expect']}"
        )

    if not es_pass and not baseline_pass:
        pytest.skip(f"Both fail '{case['query']}' — not a comparison case")

    assert baseline_pass, (
        f"Baseline fails '{case['query']}' while ES passes — "
        f"this is an xfail that slipped through"
    )
