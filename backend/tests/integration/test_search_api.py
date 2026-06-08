import uuid

import pytest
from elasticsearch import Elasticsearch
from fastapi.testclient import TestClient

from app.application.seed_service import SeedService
from app.infrastructure.config import Settings
from app.main import app
from app.providers.elasticsearch.client import ensure_index
from app.providers.elasticsearch.provider import ElasticsearchProvider

pytestmark = pytest.mark.integration

TEST_INDEX = f"cirro-search-api-{uuid.uuid4().hex[:8]}"


def _elasticsearch_available() -> bool:
    try:
        client = Elasticsearch(hosts=["http://localhost:9200"], request_timeout=2)
        return bool(client.ping())
    except Exception:
        return False


@pytest.fixture(scope="module")
def client() -> TestClient:
    if not _elasticsearch_available():
        pytest.skip("Elasticsearch is not available at http://localhost:9200")

    settings = Settings(elasticsearch_url="http://localhost:9200", elasticsearch_index=TEST_INDEX)
    es_client = Elasticsearch(hosts=[settings.elasticsearch_url], request_timeout=10)
    es_client.indices.delete(index=TEST_INDEX, ignore_unavailable=True)
    ensure_index(es_client, TEST_INDEX)

    provider = ElasticsearchProvider(client=es_client, settings=settings, auto_create_index=False)
    SeedService(provider).seed()
    es_client.indices.refresh(index=TEST_INDEX)

    from app.api.dependencies import get_search_pipeline
    from app.domain.pipeline.search_pipeline import SearchPipeline

    pipeline = SearchPipeline(provider=provider)
    app.dependency_overrides[get_search_pipeline] = lambda: pipeline

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    es_client.indices.delete(index=TEST_INDEX, ignore_unavailable=True)


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "degraded"}


def test_search_newrk(client: TestClient) -> None:
    response = client.get("/api/v1/search", params={"q": "newrk"})
    assert response.status_code == 200
    data = response.json()
    assert data["results"]
    assert data["results"][0]["iata"] == "EWR"
