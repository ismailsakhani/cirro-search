from typing import Any

from elasticsearch import Elasticsearch
from elasticsearch import NotFoundError as ESNotFoundError
from elasticsearch.helpers import bulk

from app.domain.models.entity_type import EntityType
from app.infrastructure.config import Settings, get_settings
from app.providers.elasticsearch.client import create_elasticsearch_client, ensure_index
from app.providers.elasticsearch.queries import build_autocomplete_query, build_search_query
from app.providers.exceptions import IndexingError, ProviderUnavailableError
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


class ElasticsearchProvider:
    """SearchProvider implementation backed by Elasticsearch."""

    def __init__(
        self,
        client: Elasticsearch | None = None,
        settings: Settings | None = None,
        *,
        auto_create_index: bool = True,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client or create_elasticsearch_client(self._settings)
        self._index = self._settings.elasticsearch_index

        if auto_create_index:
            ensure_index(self._client, self._index)

    @property
    def name(self) -> str:
        return "elasticsearch"

    @property
    def index_name(self) -> str:
        return self._index

    def search(self, request: ProviderSearchRequest) -> ProviderSearchResponse:
        body = build_search_query(
            query=request.query,
            entity_type=request.entity_type,
            expanded_terms=request.expanded_terms,
            limit=request.limit,
        )
        return self._execute(body)

    def autocomplete(
        self, request: ProviderAutocompleteRequest
    ) -> ProviderSearchResponse:
        body = build_autocomplete_query(
            query=request.query,
            entity_type=request.entity_type,
            expanded_terms=request.expanded_terms,
            limit=request.limit,
        )
        return self._execute(body)

    def index_document(self, document: SearchDocument) -> None:
        try:
            self._client.index(
                index=self._index,
                id=document.id,
                document=self._serialize_document(document),
            )
        except Exception as exc:
            raise IndexingError(f"Failed to index document '{document.id}': {exc}") from exc

    def delete_document(self, document_id: str) -> None:
        try:
            self._client.delete(index=self._index, id=document_id)
        except ESNotFoundError:
            return
        except Exception as exc:
            raise IndexingError(f"Failed to delete document '{document_id}': {exc}") from exc

    def bulk_index(self, documents: list[SearchDocument]) -> BulkIndexResult:
        if not documents:
            return BulkIndexResult(indexed=0, failed=0)

        actions = [
            {
                "_op_type": "index",
                "_index": self._index,
                "_id": document.id,
                "_source": self._serialize_document(document),
            }
            for document in documents
        ]

        try:
            indexed, errors = bulk(
                self._client,
                actions,
                raise_on_error=False,
                raise_on_exception=False,
                refresh=True,
            )
        except Exception as exc:
            raise IndexingError(f"Bulk indexing failed: {exc}") from exc

        error_messages = [
            f"{error.get('index', {}).get('_id')}: {error.get('index', {}).get('error')}"
            for error in errors
        ]
        return BulkIndexResult(
            indexed=indexed,
            failed=len(errors),
            errors=error_messages,
        )

    def get_health(self) -> ProviderHealth:
        try:
            health = self._client.cluster.health(index=self._index)
            status = health.get("status", "red")
            if status == "red":
                return ProviderHealth(
                    status=ProviderHealthStatus.UNAVAILABLE,
                    provider=self.name,
                    message=f"Cluster status is {status}",
                    details={"cluster_status": status},
                )
            if status == "yellow":
                return ProviderHealth(
                    status=ProviderHealthStatus.DEGRADED,
                    provider=self.name,
                    message=f"Cluster status is {status}",
                    details={"cluster_status": status},
                )
            return ProviderHealth(
                status=ProviderHealthStatus.HEALTHY,
                provider=self.name,
                details={"cluster_status": status, "index": self._index},
            )
        except Exception as exc:
            return ProviderHealth(
                status=ProviderHealthStatus.UNAVAILABLE,
                provider=self.name,
                message=str(exc),
            )

    def _execute(self, body: dict[str, Any]) -> ProviderSearchResponse:
        try:
            response = self._client.search(
                index=self._index,
                query=body["query"],
                size=body["size"],
            )
        except Exception as exc:
            raise ProviderUnavailableError(f"Elasticsearch search failed: {exc}") from exc

        hits = [
            ProviderHit(
                document=self._deserialize_document(hit["_source"]),
                score=float(hit.get("_score") or 0.0),
                matched_fields=self._extract_matched_fields(hit),
            )
            for hit in response["hits"]["hits"]
        ]

        return ProviderSearchResponse(
            hits=hits,
            took_ms=int(response.get("took", 0)),
            provider=self.name,
        )

    @staticmethod
    def _serialize_document(document: SearchDocument) -> dict[str, Any]:
        payload = document.model_dump()
        payload["type"] = document.type.value
        return payload

    @staticmethod
    def _deserialize_document(source: dict[str, Any]) -> SearchDocument:
        data = dict(source)
        data["type"] = EntityType(data["type"])
        return SearchDocument.model_validate(data)

    @staticmethod
    def _extract_matched_fields(hit: dict[str, Any]) -> list[str]:
        highlight = hit.get("highlight")
        if isinstance(highlight, dict):
            return list(highlight.keys())
        return []
