from elasticsearch import Elasticsearch


class SelectionFeedbackService:
    """Atomically increments metadata.popularity in ES when a result is selected."""

    def __init__(self, client: Elasticsearch, index: str) -> None:
        self._client = client
        self._index = index

    def record_selection(self, result_id: str) -> None:
        """
        Uses a Painless script for an atomic increment — no read-modify-write race.
        Silently swallows all errors: selection tracking must never break search.
        """
        try:
            self._client.update(
                index=self._index,
                id=result_id,
                script={
                    "lang": "painless",
                    "source": (
                        "if (ctx._source.metadata == null) {"
                        "  ctx._source.metadata = ['popularity': 1];"
                        "} else if (!ctx._source.metadata.containsKey('popularity')) {"
                        "  ctx._source.metadata.popularity = 1;"
                        "} else {"
                        "  ctx._source.metadata.popularity += 1;"
                        "}"
                    ),
                },
            )
        except Exception:
            pass
