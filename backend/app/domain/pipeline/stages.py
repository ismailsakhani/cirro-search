from app.domain.airline_mapping.codeshare import expand_flight_identifiers
from app.domain.aliases.resolver import AliasResolver
from app.domain.classifier.query_classifier import QueryClassifier
from app.domain.models.entity_type import EntityType, SearchMode
from app.domain.models.query import AliasResolution, ClassificationResult, QueryType
from app.domain.models.result import PipelineDebug, PipelineResponse, SearchResult
from app.domain.ranking.basic_ranker import BasicRanker
from app.providers.models import ProviderAutocompleteRequest, ProviderSearchRequest
from app.providers.protocol import SearchProvider


def normalize_query(query: str) -> str:
    return " ".join(query.strip().split())


def build_expansions(classification: ClassificationResult) -> list[str]:
    expansions: list[str] = []

    if classification.flight:
        flight = classification.flight
        expansions.extend(
            expand_flight_identifiers(
                flight.iata_airline_code,
                flight.icao_airline_code,
                flight.flight_number,
            )
        )

    if classification.digits:
        expansions.append(classification.digits)

    if classification.airport_code:
        expansions.append(classification.airport_code)

    if classification.gate:
        expansions.append(classification.gate)

    seen: set[str] = set()
    unique: list[str] = []
    for term in expansions:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            unique.append(term)
    return unique


def resolve_entity_type(
    classification: ClassificationResult,
    alias: AliasResolution,
) -> EntityType | None:
    if alias.entity_type:
        return alias.entity_type
    return classification.entity_type


def collect_search_terms(
    query: str,
    expansions: list[str],
    alias: AliasResolution,
) -> list[str]:
    terms = [query, *expansions, *alias.expanded_terms]
    seen: set[str] = set()
    unique: list[str] = []
    for term in terms:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            unique.append(term)
    return unique
