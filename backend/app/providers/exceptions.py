class SearchProviderError(Exception):
    """Base error for search provider operations."""


class ProviderUnavailableError(SearchProviderError):
    """Raised when the underlying search engine is unreachable or unhealthy."""


class IndexingError(SearchProviderError):
    """Raised when document indexing fails."""
