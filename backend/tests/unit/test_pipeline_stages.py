from app.domain.classifier.query_classifier import QueryClassifier
from app.domain.pipeline.stages import build_expansions


def test_build_expansions_for_ua4433() -> None:
    classification = QueryClassifier().classify("UA4433")
    expansions = build_expansions(classification)

    assert "UA4433" in expansions
    assert "GJS4433" in expansions
