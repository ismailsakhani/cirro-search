import uuid
from pathlib import Path

import pytest
import yaml
from elasticsearch import Elasticsearch

from app.application.seed_service import SeedService
from app.domain.models.entity_type import SearchMode
from app.domain.pipeline.search_pipeline import SearchPipeline
from app.infrastructure.config import Settings
from app.providers.elasticsearch.client import ensure_index
from app.providers.elasticsearch.provider import ElasticsearchProvider

pytestmark = pytest.mark.integration

CASES_PATH = Path(__file__).resolve().parents[3] / "evaluation" / "cases" / "phase1.yaml"
TEST_INDEX = f"cirro-search-eval-{uuid.uuid4().hex[:8]}"


def _elasticsearch_available() -> bool:
    try:
        client = Elasticsearch(hosts=["http://localhost:9200"], request_timeout=2)
        return bool(client.ping())
    except Exception:
        return False


def _load_cases() -> list[dict]:
    with CASES_PATH.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data["cases"]


@pytest.fixture(scope="module")
def pipeline() -> SearchPipeline:
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


def _result_matches(result, expect: dict) -> bool:
    if result.type.value != expect["type"]:
        return False

    for field, value in expect.items():
        if field == "type":
            continue
        if field == "airport":
            if result.airport_code != value:
                return False
            continue
        if getattr(result, field, None) != value:
            return False
    return True


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["query"])
def test_phase1_case(pipeline: SearchPipeline, case: dict) -> None:
    mode = SearchMode(case.get("mode", "submit"))
    response = pipeline.run(case["query"], mode=mode, limit=5)

    assert response.results, f"No results for query '{case['query']}'"

    top = response.results[0]
    assert _result_matches(top, case["expect"]), (
        f"Query '{case['query']}' expected {case['expect']} but got "
        f"{{'type': '{top.type.value}', 'iata': '{top.iata}', "
        f"'iata_flight': '{top.iata_flight}', 'gate': '{top.gate}', "
        f"'airport_code': '{top.airport_code}'}}"
    )
