from app.domain.airline_mapping.codes import (
    AIRLINE_NAMES,
    IATA_AIRLINE_CODES,
    IATA_TO_ICAO,
    ICAO_AIRLINE_CODES,
    ICAO_TO_IATA,
)
from app.domain.classifier.patterns import (
    DIGITS_PATTERN,
    GATE_PATTERN,
    IATA_AIRPORT_PATTERN,
    ICAO_AIRPORT_PATTERN,
)
from app.domain.models.query import ClassificationResult, FlightIdentifier, QueryType


class QueryClassifier:
    """Classify aviation search queries using ordered pattern rules."""

    def classify(self, query: str) -> ClassificationResult:
        normalized = self._normalize(query)
        if not normalized:
            return ClassificationResult(
                query_type=QueryType.UNKNOWN,
                normalized_query=normalized,
                confidence=0.0,
                matched_pattern="empty",
            )

        upper = normalized.upper()
        compact = upper.replace(" ", "")

        icao_airport = self._match_icao_airport(compact)
        if icao_airport:
            return icao_airport

        flight = self._match_flight(compact)
        if flight:
            return flight

        digits = self._match_digits(compact)
        if digits:
            return digits

        iata_airport = self._match_iata_airport(compact)
        if iata_airport:
            return iata_airport

        gate = self._match_gate(compact)
        if gate:
            return gate

        airline_name_flight = self._match_airline_name_flight(normalized)
        if airline_name_flight:
            return airline_name_flight

        if self._looks_ambiguous(normalized):
            return ClassificationResult(
                query_type=QueryType.AMBIGUOUS,
                normalized_query=normalized,
                matched_pattern="text",
            )

        return ClassificationResult(
            query_type=QueryType.UNKNOWN,
            normalized_query=normalized,
            confidence=0.0,
            matched_pattern="none",
        )

    @staticmethod
    def _normalize(query: str) -> str:
        return " ".join(query.strip().split())

    def _match_icao_airport(self, compact: str) -> ClassificationResult | None:
        if ICAO_AIRPORT_PATTERN.match(compact):
            return ClassificationResult(
                query_type=QueryType.AIRPORT_ICAO,
                normalized_query=compact,
                airport_code=compact,
                matched_pattern="icao_airport",
            )
        return None

    def _match_flight(self, compact: str) -> ClassificationResult | None:
        for code in ICAO_AIRLINE_CODES:
            if compact.startswith(code) and compact[len(code) :].isdigit():
                flight_number = compact[len(code) :]
                return ClassificationResult(
                    query_type=QueryType.FLIGHT,
                    normalized_query=compact,
                    flight=FlightIdentifier(
                        code_type="ICAO",
                        icao_airline_code=code,
                        iata_airline_code=ICAO_TO_IATA.get(code),
                        flight_number=flight_number,
                    ),
                    matched_pattern="icao_flight",
                )

        for code in IATA_AIRLINE_CODES:
            if compact.startswith(code) and compact[len(code) :].isdigit():
                # Alphanumeric IATA codes (e.g. "B6", "G4", "C1") whose remainder
                # produces a gate-like string (single letter + ≤3 digits) are
                # ambiguous. Prefer gate classification for short queries like "B17".
                if (
                    code[-1].isdigit()
                    and compact[0].isalpha()
                    and compact[1:].isdigit()
                    and len(compact) <= 4
                ):
                    continue
                flight_number = compact[len(code) :]
                return ClassificationResult(
                    query_type=QueryType.FLIGHT,
                    normalized_query=compact,
                    flight=FlightIdentifier(
                        code_type="IATA",
                        iata_airline_code=code,
                        icao_airline_code=IATA_TO_ICAO.get(code),
                        flight_number=flight_number,
                    ),
                    matched_pattern="iata_flight",
                )
        return None

    def _match_digits(self, compact: str) -> ClassificationResult | None:
        if DIGITS_PATTERN.match(compact):
            return ClassificationResult(
                query_type=QueryType.DIGITS,
                normalized_query=compact,
                digits=compact,
                matched_pattern="digits",
            )
        return None

    def _match_iata_airport(self, compact: str) -> ClassificationResult | None:
        if IATA_AIRPORT_PATTERN.match(compact) and compact not in IATA_AIRLINE_CODES:
            return ClassificationResult(
                query_type=QueryType.AIRPORT_IATA,
                normalized_query=compact,
                airport_code=compact,
                matched_pattern="iata_airport",
            )
        return None

    def _match_gate(self, compact: str) -> ClassificationResult | None:
        if GATE_PATTERN.match(compact):
            return ClassificationResult(
                query_type=QueryType.GATE,
                normalized_query=compact,
                gate=compact,
                matched_pattern="gate",
            )
        return None

    def _match_airline_name_flight(self, normalized: str) -> ClassificationResult | None:
        lower = normalized.lower()
        for name, iata in AIRLINE_NAMES.items():
            prefix = f"{name} "
            if lower.startswith(prefix):
                remainder = lower[len(prefix) :].strip()
                if remainder.isdigit():
                    return ClassificationResult(
                        query_type=QueryType.FLIGHT,
                        normalized_query=normalized,
                        flight=FlightIdentifier(
                            code_type="IATA",
                            iata_airline_code=iata,
                            icao_airline_code=IATA_TO_ICAO.get(iata),
                            flight_number=remainder,
                        ),
                        matched_pattern="airline_name_flight",
                    )
        return None

    @staticmethod
    def _looks_ambiguous(normalized: str) -> bool:
        if " " in normalized:
            return True
        alpha = normalized.replace(" ", "")
        return alpha.isalpha() and len(alpha) >= 3
