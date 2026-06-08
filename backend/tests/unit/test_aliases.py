from app.domain.classifier.query_classifier import QueryClassifier
from app.domain.aliases.resolver import AliasResolver
from app.domain.models.entity_type import EntityType


def test_resolve_newrk() -> None:
    resolver = AliasResolver()
    classification = QueryClassifier().classify("newrk")

    result = resolver.resolve("newrk", classification)

    assert result.matched is True
    assert result.entity_id == "airport:EWR"
    assert result.entity_type == EntityType.AIRPORT


def test_resolve_ewr_c101() -> None:
    resolver = AliasResolver()
    classification = QueryClassifier().classify("ewr c101")

    result = resolver.resolve("ewr c101", classification)

    assert result.matched is True
    assert result.entity_id == "gate:EWR:C101"
    assert result.entity_type == EntityType.GATE
