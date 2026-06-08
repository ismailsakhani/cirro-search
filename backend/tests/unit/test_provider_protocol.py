import pytest

from app.domain.models.entity_type import EntityType
from app.providers.models import (
    ProviderAutocompleteRequest,
    ProviderHealthStatus,
    ProviderSearchRequest,
    SearchDocument,
)
from app.providers.protocol import SearchProvider
from app.providers.testing.fake_provider import FakeSearchProvider


@pytest.fixture
def provider() -> FakeSearchProvider:
    fake = FakeSearchProvider()
    fake.bulk_index(
        [
            SearchDocument(
                id="airport:EWR",
                type=EntityType.AIRPORT,
                display="EWR - Newark Liberty International Airport",
                searchable_text="ewr kewr newark newrk newark airport",
                iata="EWR",
                icao="KEWR",
                name="Newark Liberty International Airport",
            ),
            SearchDocument(
                id="flight:UA4433",
                type=EntityType.FLIGHT,
                display="GJS4433 (UA4433) - UA",
                searchable_text="ua4433 ual4433 gjs4433 united 4433 4433",
                iata_flight="UA4433",
                icao_flight="GJS4433",
                flight_number="4433",
            ),
            SearchDocument(
                id="gate:EWR:C101",
                type=EntityType.GATE,
                display="EWR - C101 Departures",
                searchable_text="c101 ewr c101 ewr-c101",
                airport_code="EWR",
                gate="C101",
            ),
        ]
    )
    return fake


def test_fake_provider_satisfies_protocol(provider: FakeSearchProvider) -> None:
    assert isinstance(provider, SearchProvider)


def test_search_returns_matching_airport(provider: FakeSearchProvider) -> None:
    response = provider.search(
        ProviderSearchRequest(query="newrk", entity_type=EntityType.AIRPORT)
    )

    assert response.provider == "fake"
    assert len(response.hits) == 1
    assert response.hits[0].document.iata == "EWR"


def test_search_returns_matching_flight(provider: FakeSearchProvider) -> None:
    response = provider.search(
        ProviderSearchRequest(query="4433", entity_type=EntityType.FLIGHT)
    )

    assert len(response.hits) == 1
    assert response.hits[0].document.iata_flight == "UA4433"


def test_autocomplete_returns_matching_gate(provider: FakeSearchProvider) -> None:
    response = provider.autocomplete(
        ProviderAutocompleteRequest(query="ewr c101", entity_type=EntityType.GATE)
    )

    assert len(response.hits) == 1
    assert response.hits[0].document.gate == "C101"


def test_index_and_delete_document(provider: FakeSearchProvider) -> None:
    document = SearchDocument(
        id="airport:LAS",
        type=EntityType.AIRPORT,
        display="LAS - Harry Reid International Airport",
        searchable_text="las klas harry reid vegas airport",
        iata="LAS",
    )

    provider.index_document(document)
    assert provider.search(ProviderSearchRequest(query="vegas airport")).hits

    provider.delete_document("airport:LAS")
    assert not provider.search(ProviderSearchRequest(query="vegas airport")).hits


def test_bulk_index(provider: FakeSearchProvider) -> None:
    result = provider.bulk_index(
        [
            SearchDocument(
                id="airport:ORD",
                type=EntityType.AIRPORT,
                display="ORD - O'Hare International Airport",
                searchable_text="ord kord ohare",
                iata="ORD",
            )
        ]
    )

    assert result.indexed == 1
    assert result.failed == 0


def test_get_health(provider: FakeSearchProvider) -> None:
    health = provider.get_health()

    assert health.provider == "fake"
    assert health.status == ProviderHealthStatus.HEALTHY
