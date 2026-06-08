from fastapi import APIRouter, Depends

from app.api.dependencies import get_search_pipeline
from app.api.schemas import HealthResponseSchema
from app.domain.pipeline.search_pipeline import SearchPipeline
from app.infrastructure.config import get_settings
from app.providers.models import ProviderHealthStatus

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponseSchema)
def health(
    pipeline: SearchPipeline = Depends(get_search_pipeline),
) -> HealthResponseSchema:
    settings = get_settings()
    provider_health = pipeline.health()

    return HealthResponseSchema(
        status="ok" if provider_health.status != ProviderHealthStatus.UNAVAILABLE else "degraded",
        provider=provider_health.provider,
        provider_status=provider_health.status.value,
        index=settings.elasticsearch_index,
    )
