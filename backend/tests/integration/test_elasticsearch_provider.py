import uuid

import pytest
from elasticsearch import Elasticsearch

from app.domain.models.entity_type import EntityType
from app.infrastructure.config import Settings
from app.providers.elasticsearch.client import ensure_index
from app.providers.elasticsearch.provider import ElasticsearchProvider
from app.providers.models import ProviderAutocompleteRequest, ProviderSearchRequest, SearchDocument
from app.providers.protocol import SearchProvider

pytestmark = pytest.mark.integration

TEST_INDEX = f"cirro-search-test-{uuid.uuid4().hex[:8]}"


def _elasticsearch_available() -> bool:
    try:
        client = Elasticsearch(hosts=["http://localhost:9200"], request_timeout=2)
        return bool(client.ping())
    except Exception:
        return False


@pytest.fixture(scope="module")
def provider() -> ElasticsearchProvider:
    if not _elasticsearch_available():
        pytest.skip("Elasticsearch is not available at http://localhost:9200")

    settings = Settings(elasticsearch_url="http://localhost:9200", elasticsearch_index=TEST_INDEX)
    client = Elasticsearch(hosts=[settings.elasticsearch_url], request_timeout=5)
    ensure_index(client, TEST_INDEX)

    es_provider = ElasticsearchProvider(
        client=client,
        settings=settings,
        auto_create_index=False,
    )
    es_provider.bulk_index(
        [
            SearchDocument(
                id="airport:EWR",
                type=EntityType.AIRPORT,
                display="EWR - Newark Liberty International Airport",
                searchable_text="ewr kewr newark newrk newark airport",
                iata="EWR",
                icao="KEWR",
                name="Newark Liberty International Airport",
                aliases=["newark", "newrk", "newark airport"],
            ),
            SearchDocument(
                id="airport:LAS",
                type=EntityType.AIRPORT,
                display="LAS - Harry Reid International Airport",
                searchable_text="las klas harry reid vegas vegas airport",
                iata="LAS",
                icao="KLAS",
                name="Harry Reid International Airport",
                aliases=["vegas", "vegas airport", "harry reid"],
            ),
            SearchDocument(
                id="flight:UA4433",
                type=EntityType.FLIGHT,
                display="GJS4433 (UA4433) - UA",
                searchable_text="ua4433 ual4433 gjs4433 united 4433 4433",
                iata_flight="UA4433",
                icao_flight="GJS4433",
                flight_number="4433",
                airline="UA",
                aliases=["united 4433"],
            ),
            SearchDocument(
                id="gate:EWR:C101",
                type=EntityType.GATE,
                display="EWR - C101 Departures",
                searchable_text="c101 ewr c101 ewr-c101 gate c101 departures",
                airport_code="EWR",
                gate="C101",
                aliases=["ewr c101"],
            ),
        ]
    )
    client.indices.refresh(index=TEST_INDEX)
    yield es_provider
    client.indices.delete(index=TEST_INDEX, ignore_unavailable=True)


def test_elasticsearch_provider_satisfies_protocol(provider: ElasticsearchProvider) -> None:
    assert isinstance(provider, SearchProvider)


def test_search_newrk_returns_ewr(provider: ElasticsearchProvider) -> None:
    response = provider.search(
        ProviderSearchRequest(query="newrk", entity_type=EntityType.AIRPORT, limit=3)
    )

    assert response.provider == "elasticsearch"
    assert response.hits
    assert response.hits[0].document.iata == "EWR"


def test_search_vegas_airport_returns_las(provider: ElasticsearchProvider) -> None:
    response = provider.search(
        ProviderSearchRequest(query="vegas airport", entity_type=EntityType.AIRPORT, limit=3)
    )

    assert response.hits
    assert response.hits[0].document.iata == "LAS"


def test_search_4433_returns_ua4433(provider: ElasticsearchProvider) -> None:
    response = provider.search(
        ProviderSearchRequest(query="4433", entity_type=EntityType.FLIGHT, limit=3)
    )

    assert response.hits
    assert response.hits[0].document.iata_flight == "UA4433"


def test_autocomplete_ewr_c101_returns_gate(provider: ElasticsearchProvider) -> None:
    response = provider.autocomplete(
        ProviderAutocompleteRequest(query="ewr c101", entity_type=EntityType.GATE, limit=3)
    )

    assert response.hits
    assert response.hits[0].document.gate == "C101"


def test_get_health(provider: ElasticsearchProvider) -> None:
    health = provider.get_health()

    assert health.provider == "elasticsearch"
    assert health.status.value in {"healthy", "degraded"}


def test_delete_document(provider: ElasticsearchProvider) -> None:
    document = SearchDocument(
        id="airport:JFK",
        type=EntityType.AIRPORT,
        display="JFK - John F Kennedy International Airport",
        searchable_text="jfk kjfk kennedy",
        iata="JFK",
    )

    provider.index_document(document)
    provider._client.indices.refresh(index=provider.index_name)
    assert provider.search(ProviderSearchRequest(query="jfk")).hits

    provider.delete_document("airport:JFK")
    provider._client.indices.refresh(index=provider.index_name)
    assert not provider.search(ProviderSearchRequest(query="jfk")).hits
