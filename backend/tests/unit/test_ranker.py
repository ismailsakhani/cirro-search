from app.domain.classifier.query_classifier import QueryClassifier
from app.domain.models.entity_type import EntityType
from app.domain.ranking.basic_ranker import BasicRanker
from app.providers.models import ProviderHit, SearchDocument


def test_ranker_prefers_ua4433_for_digits() -> None:
    ranker = BasicRanker()
    classification = QueryClassifier().classify("4433")

    hits = [
        ProviderHit(
            document=SearchDocument(
                id="flight:AA4433",
                type=EntityType.FLIGHT,
                display="AA4433",
                searchable_text="aa4433 4433",
                iata_flight="AA4433",
                flight_number="4433",
                metadata={"popularity": 10},
            ),
            score=1.0,
        ),
        ProviderHit(
            document=SearchDocument(
                id="flight:UA4433",
                type=EntityType.FLIGHT,
                display="UA4433",
                searchable_text="ua4433 4433",
                iata_flight="UA4433",
                flight_number="4433",
                metadata={"popularity": 100},
            ),
            score=1.0,
        ),
    ]

    ranked = ranker.rank(hits, classification, "4433")

    assert ranked[0].iata_flight == "UA4433"
