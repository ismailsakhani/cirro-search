"""
In-memory SearchProvider for tests and pipeline development.

Not a production backend — validates the abstraction contract only.
"""

from app.domain.models.entity_type import EntityType
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


class FakeSearchProvider:
    """Minimal in-memory implementation of SearchProvider."""

    def __init__(self, name: str = "fake") -> None:
        self._name = name
        self._documents: dict[str, SearchDocument] = {}

    @property
    def name(self) -> str:
        return self._name

    def search(self, request: ProviderSearchRequest) -> ProviderSearchResponse:
        return self._match(
            query=request.query,
            entity_type=request.entity_type,
            expanded_terms=request.expanded_terms,
            limit=request.limit,
        )

    def autocomplete(
        self, request: ProviderAutocompleteRequest
    ) -> ProviderSearchResponse:
        return self._match(
            query=request.query,
            entity_type=request.entity_type,
            expanded_terms=request.expanded_terms,
            limit=request.limit,
        )

    def index_document(self, document: SearchDocument) -> None:
        self._documents[document.id] = document

    def delete_document(self, document_id: str) -> None:
        self._documents.pop(document_id, None)

    def bulk_index(self, documents: list[SearchDocument]) -> BulkIndexResult:
        for document in documents:
            self._documents[document.id] = document
        return BulkIndexResult(indexed=len(documents), failed=0)

    def get_health(self) -> ProviderHealth:
        return ProviderHealth(
            status=ProviderHealthStatus.HEALTHY,
            provider=self._name,
        )

    def _match(
        self,
        query: str,
        entity_type: EntityType | None,
        expanded_terms: list[str],
        limit: int,
    ) -> ProviderSearchResponse:
        terms = [query.lower(), *[t.lower() for t in expanded_terms]]
        hits: list[ProviderHit] = []

        for document in self._documents.values():
            if entity_type is not None and document.type != entity_type:
                continue

            haystack = document.searchable_text.lower()
            if not any(term in haystack for term in terms if term):
                continue

            hits.append(
                ProviderHit(
                    document=document,
                    score=1.0,
                    matched_fields=["searchable_text"],
                )
            )

        hits.sort(key=lambda hit: hit.score, reverse=True)
        return ProviderSearchResponse(
            hits=hits[:limit],
            took_ms=0,
            provider=self._name,
        )
