"""
Baseline provider: in-memory fuzzy search reproducing Cirrostrats fuzz_find behavior.

Cirrostrats uses a suggestions cache (in-memory list) with substring + fuzzy matching.
This provider mimics that: load all documents into memory, score via substring overlap
and edit distance. No indexing infrastructure needed.

Used for side-by-side comparison against ElasticsearchProvider in Phase 2.
"""

from difflib import SequenceMatcher

from app.providers.exceptions import IndexingError
from app.providers.models import (
    BulkIndexResult,
    ProviderAutocompleteRequest,
    ProviderHealth,
    ProviderHealthStatus,
    ProviderHit,
    ProviderSearchRequest,
    ProviderSearchResponse,
    SearchDocument,
)


def _fuzzy_score(query: str, text: str) -> float:
    """Return a 0–1 similarity score between query and text."""
    q = query.lower().strip()
    t = text.lower()

    # Exact substring → highest score
    if q in t:
        return 1.0 + (len(q) / max(len(t), 1))

    # Prefix match → high score
    if t.startswith(q):
        return 0.9 + (len(q) / max(len(t), 1))

    # SequenceMatcher ratio (Cirrostrats uses thefuzz/rapidfuzz under the hood)
    return SequenceMatcher(None, q, t).ratio()


class BaselineProvider:
    """
    In-memory fuzzy search provider mirroring Cirrostrats suggestions cache behavior.

    Scores each document against all searchable fields and returns top-N by score.
    Threshold: 0.4 (matches Cirrostrats' effective cutoff in fuzz_find).
    """

    FUZZY_THRESHOLD = 0.4
    NAME = "baseline"

    def __init__(self) -> None:
        self._documents: dict[str, SearchDocument] = {}

    @property
    def name(self) -> str:
        return self.NAME

    def search(self, request: ProviderSearchRequest) -> ProviderSearchResponse:
        terms = [request.query, *request.expanded_terms]
        return self._run(terms, request.entity_type, request.limit)

    def autocomplete(self, request: ProviderAutocompleteRequest) -> ProviderSearchResponse:
        terms = [request.query, *request.expanded_terms]
        return self._run(terms, request.entity_type, request.limit, prefix_bias=True)

    def index_document(self, document: SearchDocument) -> None:
        self._documents[document.id] = document

    def delete_document(self, document_id: str) -> None:
        self._documents.pop(document_id, None)

    def bulk_index(self, documents: list[SearchDocument]) -> BulkIndexResult:
        for doc in documents:
            self._documents[doc.id] = doc
        return BulkIndexResult(indexed=len(documents), failed=0)

    def get_health(self) -> ProviderHealth:
        return ProviderHealth(
            status=ProviderHealthStatus.HEALTHY,
            provider=self.NAME,
            details={"document_count": len(self._documents)},
        )

    def _run(
        self,
        terms: list[str],
        entity_type,
        limit: int,
        *,
        prefix_bias: bool = False,
    ) -> ProviderSearchResponse:
        scored: list[tuple[float, SearchDocument]] = []

        for doc in self._documents.values():
            if entity_type and doc.type != entity_type:
                continue

            best = self._best_score(terms, doc, prefix_bias=prefix_bias)
            if best >= self.FUZZY_THRESHOLD:
                scored.append((best, doc))

        scored.sort(key=lambda x: x[0], reverse=True)

        hits = [
            ProviderHit(document=doc, score=score, matched_fields=["baseline_fuzzy"])
            for score, doc in scored[:limit]
        ]

        return ProviderSearchResponse(hits=hits, took_ms=0, provider=self.NAME)

    def _best_score(
        self, terms: list[str], doc: SearchDocument, *, prefix_bias: bool
    ) -> float:
        fields = self._doc_fields(doc)
        best = 0.0

        for term in terms:
            for field_value in fields:
                if not field_value:
                    continue
                s = _fuzzy_score(term, field_value)
                if prefix_bias and field_value.lower().startswith(term.lower()):
                    s = max(s, 0.95)
                best = max(best, s)

        return best

    @staticmethod
    def _doc_fields(doc: SearchDocument) -> list[str | None]:
        return [
            doc.iata,
            doc.icao,
            doc.iata_flight,
            doc.icao_flight,
            doc.gate,
            doc.airport_code,
            doc.flight_number,
            doc.name,
            doc.display,
            doc.searchable_text,
            *doc.aliases,
        ]
