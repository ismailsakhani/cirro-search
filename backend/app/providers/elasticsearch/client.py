from elasticsearch import Elasticsearch

from app.infrastructure.config import Settings, get_settings
from app.providers.elasticsearch.index_config import INDEX_MAPPINGS, INDEX_SETTINGS


def create_elasticsearch_client(settings: Settings | None = None) -> Elasticsearch:
    """Create an Elasticsearch client from application settings."""
    config = settings or get_settings()
    return Elasticsearch(
        hosts=[config.elasticsearch_url],
        request_timeout=config.elasticsearch_request_timeout,
    )


def ensure_index(client: Elasticsearch, index_name: str) -> None:
    """Create the search index if it does not already exist."""
    if client.indices.exists(index=index_name):
        return

    client.indices.create(
        index=index_name,
        settings=INDEX_SETTINGS,
        mappings=INDEX_MAPPINGS,
    )
