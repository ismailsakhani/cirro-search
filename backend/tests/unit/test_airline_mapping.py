from app.domain.airline_mapping.codeshare import expand_flight_identifiers


def test_expand_ua4433() -> None:
    terms = expand_flight_identifiers("UA", "UAL", "4433")

    assert "UA4433" in terms
    assert "UAL4433" in terms
    assert "GJS4433" in terms
    assert "UCA4433" in terms


def test_expand_digits_only_context() -> None:
    terms = expand_flight_identifiers(None, None, "4433")

    assert terms == []
