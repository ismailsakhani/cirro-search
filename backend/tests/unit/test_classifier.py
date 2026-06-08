import pytest

from app.domain.classifier.query_classifier import QueryClassifier
from app.domain.models.query import QueryType

pytestmark = pytest.mark.parametrize(
    "query,expected_type,extra",
    [
        ("KEWR", QueryType.AIRPORT_ICAO, {"airport_code": "KEWR"}),
        ("EWR", QueryType.AIRPORT_IATA, {"airport_code": "EWR"}),
        ("UA4433", QueryType.FLIGHT, {"flight_number": "4433"}),
        ("UAL4433", QueryType.FLIGHT, {"flight_number": "4433"}),
        ("4433", QueryType.DIGITS, {"digits": "4433"}),
        ("C101", QueryType.GATE, {"gate": "C101"}),
        ("Newark", QueryType.AMBIGUOUS, {}),
        ("newark airport", QueryType.AMBIGUOUS, {}),
        ("united 4433", QueryType.FLIGHT, {"flight_number": "4433"}),
        ("", QueryType.UNKNOWN, {}),
    ],
)
def test_classifier(query: str, expected_type: QueryType, extra: dict) -> None:
    classifier = QueryClassifier()
    result = classifier.classify(query)

    assert result.query_type == expected_type

    if "airport_code" in extra:
        assert result.airport_code == extra["airport_code"]
    if "flight_number" in extra:
        assert result.flight is not None
        assert result.flight.flight_number == extra["flight_number"]
    if "digits" in extra:
        assert result.digits == extra["digits"]
    if "gate" in extra:
        assert result.gate == extra["gate"]
