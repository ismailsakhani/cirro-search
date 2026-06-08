from app.domain.models.entity_type import EntityType


def _collect_query_terms(query: str, expanded_terms: list[str]) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()

    for term in [query, *expanded_terms]:
        normalized = term.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        terms.append(normalized)

    return terms


def _entity_type_filter(entity_type: EntityType | None) -> list[dict]:
    if entity_type is None:
        return []
    return [{"term": {"type": entity_type.value}}]


def build_search_query(
    query: str,
    entity_type: EntityType | None,
    expanded_terms: list[str],
    limit: int,
) -> dict:
    """Build an Elasticsearch query for submit/search mode."""
    terms = _collect_query_terms(query, expanded_terms)
    should_clauses: list[dict] = []

    for term in terms:
        # Keyword fields are case-sensitive — add exact term queries with normalized case
        # so "cdg" matches stored "CDG" and "ua500" matches stored "UA500"
        upper = term.upper()
        for field in ("iata", "icao", "iata_flight", "icao_flight", "gate", "airport_code"):
            should_clauses.append({"term": {field: {"value": upper, "boost": 20}}})
        # flight_number stores bare digits ("4433") — exact match with high boost
        # so digit-only queries surface the right flights before fuzzy distractors
        should_clauses.append({"term": {"flight_number": {"value": term, "boost": 40}}})
        should_clauses.append(
            {
                "multi_match": {
                    "query": term,
                    "fields": [
                        "iata^8",
                        "icao^8",
                        "iata_flight^8",
                        "icao_flight^8",
                        "flight_number^6",
                        "gate^8",
                        "airport_code^6",
                        "searchable_text^4",
                        "aliases^3",
                        "name^3",
                        "display^2",
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            }
        )

    bool_query = {
        "filter": _entity_type_filter(entity_type),
        "should": should_clauses,
        "minimum_should_match": 1,
    }

    return {
        "size": limit,
        "query": {
            "function_score": {
                "query": {"bool": bool_query},
                "functions": [
                    {
                        "field_value_factor": {
                            "field": "metadata.popularity",
                            "factor": 1.0,
                            "modifier": "none",
                            "missing": 0,
                        }
                    }
                ],
                "boost_mode": "sum",
                "score_mode": "sum",
            }
        },
    }


def build_autocomplete_query(
    query: str,
    entity_type: EntityType | None,
    expanded_terms: list[str],
    limit: int,
) -> dict:
    """Build an Elasticsearch query optimized for autocomplete."""
    terms = _collect_query_terms(query, expanded_terms)
    should_clauses: list[dict] = []

    for term in terms:
        normalized = term.lower()
        should_clauses.extend(
            [
                {"prefix": {"iata": {"value": normalized, "boost": 8}}},
                {"prefix": {"icao": {"value": normalized, "boost": 8}}},
                {"prefix": {"iata_flight": {"value": normalized.upper(), "boost": 8}}},
                {"prefix": {"icao_flight": {"value": normalized.upper(), "boost": 8}}},
                {"prefix": {"gate": {"value": normalized.upper(), "boost": 8}}},
                {"prefix": {"airport_code": {"value": normalized.upper(), "boost": 6}}},
                {
                    "match": {
                        "searchable_text.edge": {
                            "query": term,
                            "boost": 4,
                        }
                    }
                },
                {
                    "multi_match": {
                        "query": term,
                        "fields": ["searchable_text^3", "aliases^2", "name^2", "display"],
                        "type": "best_fields",
                        "fuzziness": "AUTO",
                    }
                },
            ]
        )

    return {
        "size": limit,
        "query": {
            "bool": {
                "filter": _entity_type_filter(entity_type),
                "should": should_clauses,
                "minimum_should_match": 1,
            }
        },
    }
