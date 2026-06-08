from app.domain.models.entity_type import EntityType
from app.providers.elasticsearch.queries import build_autocomplete_query, build_search_query


def test_build_search_query_includes_entity_filter() -> None:
    query = build_search_query(
        query="newrk",
        entity_type=EntityType.AIRPORT,
        expanded_terms=["newark"],
        limit=5,
    )

    bool_query = query["query"]["function_score"]["query"]["bool"]
    assert query["size"] == 5
    assert bool_query["filter"] == [{"term": {"type": "airport"}}]
    assert len(bool_query["should"]) > 0


def test_build_search_query_deduplicates_terms() -> None:
    query_deduped = build_search_query(
        query="ua4433",
        entity_type=None,
        expanded_terms=["ua4433", "UAL4433"],
        limit=10,
    )
    query_no_dup = build_search_query(
        query="ua4433",
        entity_type=None,
        expanded_terms=["UAL4433"],
        limit=10,
    )

    deduped_should = query_deduped["query"]["function_score"]["query"]["bool"]["should"]
    no_dup_should = query_no_dup["query"]["function_score"]["query"]["bool"]["should"]
    assert len(deduped_should) == len(no_dup_should)


def test_build_autocomplete_query_uses_prefix_clauses() -> None:
    query = build_autocomplete_query(
        query="ewr",
        entity_type=EntityType.GATE,
        expanded_terms=[],
        limit=5,
    )

    should = query["query"]["bool"]["should"]
    clause_types = {next(iter(clause.keys())) for clause in should}
    assert "prefix" in clause_types
    assert "match" in clause_types
    assert query["query"]["bool"]["filter"] == [{"term": {"type": "gate"}}]
