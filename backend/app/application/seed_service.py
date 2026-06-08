from pathlib import Path

from app.infrastructure.seed.loader import default_seed_dir, load_seed_documents
from app.providers.models import BulkIndexResult
from app.providers.protocol import SearchProvider


class SeedService:
    """Load seed data into the search provider."""

    def __init__(self, provider: SearchProvider, seed_dir: Path | None = None) -> None:
        self._provider = provider
        self._seed_dir = seed_dir or default_seed_dir()

    def seed(self, *, recreate: bool = False) -> BulkIndexResult:
        documents = load_seed_documents(self._seed_dir)

        if recreate:
            for document in documents:
                self._provider.delete_document(document.id)

        return self._provider.bulk_index(documents)

    @property
    def document_count(self) -> int:
        return len(load_seed_documents(self._seed_dir))
