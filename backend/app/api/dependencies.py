from functools import lru_cache

from app.application.selection_feedback_service import SelectionFeedbackService
from app.domain.pipeline.search_pipeline import SearchPipeline
from app.infrastructure.config import get_settings
from app.providers.elasticsearch.client import create_elasticsearch_client
from app.providers.elasticsearch.provider import ElasticsearchProvider


@lru_cache
def get_search_pipeline() -> SearchPipeline:
    settings = get_settings()
    provider = ElasticsearchProvider(settings=settings)
    return SearchPipeline(provider=provider)


@lru_cache
def get_selection_feedback_service() -> SelectionFeedbackService:
    settings = get_settings()
    client = create_elasticsearch_client(settings)
    return SelectionFeedbackService(client, settings.elasticsearch_index)
