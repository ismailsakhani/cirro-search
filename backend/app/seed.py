"""CLI entry point: python -m app.seed"""

from app.application.seed_service import SeedService
from app.infrastructure.config import get_settings
from app.providers.elasticsearch.provider import ElasticsearchProvider


def main() -> None:
    settings = get_settings()
    provider = ElasticsearchProvider(settings=settings)
    service = SeedService(provider)
    result = service.seed(recreate=False)

    print(f"Seeded {result.indexed} documents into {settings.elasticsearch_index}")
    if result.failed:
        print(f"Failed: {result.failed}")
        for error in result.errors:
            print(f"  - {error}")


if __name__ == "__main__":
    main()
