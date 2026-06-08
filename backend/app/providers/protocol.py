from typing import Protocol, runtime_checkable

from app.providers.models import (
    BulkIndexResult,
    ProviderAutocompleteRequest,
    ProviderHealth,
    ProviderSearchRequest,
    ProviderSearchResponse,
    SearchDocument,
)


@runtime_checkable
class SearchProvider(Protocol):
    """
    Abstraction over search engine backends.

    Domain and pipeline code depend on this interface — not on Elasticsearch
    or any other concrete implementation.
    """

    @property
    def name(self) -> str:
        """Short identifier for this provider (e.g. 'elasticsearch', 'baseline')."""
        ...

    def search(self, request: ProviderSearchRequest) -> ProviderSearchResponse:
        """Execute a full search for submit mode."""
        ...

    def autocomplete(
        self, request: ProviderAutocompleteRequest
    ) -> ProviderSearchResponse:
        """Execute a prefix-oriented search for autocomplete mode."""
        ...

    def index_document(self, document: SearchDocument) -> None:
        """Index a single document."""
        ...

    def delete_document(self, document_id: str) -> None:
        """Remove a document by id."""
        ...

    def bulk_index(self, documents: list[SearchDocument]) -> BulkIndexResult:
        """Index multiple documents in one operation."""
        ...

    def get_health(self) -> ProviderHealth:
        """Report whether the underlying search engine is reachable and usable."""
        ...
