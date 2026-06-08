from app.domain.models.entity_type import EntityType
from app.domain.models.query import ClassificationResult, QueryType
from app.domain.models.result import RankedResult, SearchResult
from app.providers.models import ProviderHit


class BasicRanker:
    """Phase 1 ranker: exact match boost + type alignment + popularity."""

    def rank(
        self,
        hits: list[ProviderHit],
        classification: ClassificationResult,
        query: str,
        *,
        preferred_entity_id: str | None = None,
    ) -> list[RankedResult]:
        query_lower = query.strip().lower()
        query_compact = query_lower.replace(" ", "")

        scored: list[tuple[float, list[str], ProviderHit]] = []
        for hit in hits:
            score, explanation = self._score_hit(
                hit,
                classification,
                query_lower,
                query_compact,
                preferred_entity_id=preferred_entity_id,
            )
            scored.append((score, explanation, hit))

        scored.sort(key=lambda item: item[0], reverse=True)

        results: list[RankedResult] = []
        for index, (score, explanation, hit) in enumerate(scored, start=1):
            doc = hit.document
            results.append(
                RankedResult(
                    **doc.model_dump(exclude={"searchable_text", "aliases"}),
                    score=score,
                    rank=index,
                    matched_fields=hit.matched_fields,
                    explanation=explanation,
                )
            )
        return results

    def _score_hit(
        self,
        hit: ProviderHit,
        classification: ClassificationResult,
        query_lower: str,
        query_compact: str,
        *,
        preferred_entity_id: str | None,
    ) -> tuple[float, list[str]]:
        doc = hit.document
        score = hit.score
        explanation: list[str] = ["es_score"]

        if preferred_entity_id and doc.id == preferred_entity_id:
            score += 1000
            explanation.append("alias_entity_match")

        expected_type = classification.entity_type
        if expected_type and doc.type == expected_type:
            score += 50
            explanation.append("type_alignment")

        if doc.iata and doc.iata.lower() == query_compact:
            score += 200
            explanation.append("exact_iata")
        if doc.icao and doc.icao.lower() == query_compact:
            score += 200
            explanation.append("exact_icao")
        if doc.iata_flight and doc.iata_flight.lower() == query_compact:
            score += 200
            explanation.append("exact_iata_flight")
        if doc.icao_flight and doc.icao_flight.lower() == query_compact:
            score += 200
            explanation.append("exact_icao_flight")
        if doc.gate and doc.gate.lower() == query_compact:
            score += 200
            explanation.append("exact_gate")
        if doc.flight_number and doc.flight_number == query_compact:
            score += 100
            explanation.append("exact_flight_number")

        if classification.query_type == QueryType.DIGITS and doc.flight_number == classification.digits:
            score += 75
            explanation.append("digits_match")

        if query_lower in doc.searchable_text.lower():
            score += 25
            explanation.append("searchable_text_match")

        popularity = doc.metadata.get("popularity", 0)
        if popularity:
            score += float(popularity) * 0.1
            explanation.append("popularity")

        return score, explanation

    def to_search_results(self, ranked: list[RankedResult]) -> list[SearchResult]:
        return [
            SearchResult.model_validate(item.model_dump(exclude={"rank"}))
            for item in ranked
        ]
