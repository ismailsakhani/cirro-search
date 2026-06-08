"""
Phase 3 search analytics store (in-memory).

Tracks query frequency and mode distribution. Data feeds into PopularityFirstRanker
experiments and informs Phase 4 popularity ranking decisions.

No persistence — resets on restart. Upgrade to SQLite in Phase 5 if needed.
"""

from __future__ import annotations

import threading
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class QueryRecord:
    query: str
    mode: str
    count: int = 0
    result_count: int = 0


class AnalyticsStore:
    """Thread-safe in-memory query analytics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._query_counts: Counter[str] = Counter()
        self._mode_counts: Counter[str] = Counter()
        self._zero_result_queries: Counter[str] = Counter()

    def record(self, query: str, mode: str, *, result_count: int) -> None:
        key = query.strip().lower()
        with self._lock:
            self._query_counts[key] += 1
            self._mode_counts[mode] += 1
            if result_count == 0:
                self._zero_result_queries[key] += 1

    def top_queries(self, n: int = 20) -> list[tuple[str, int]]:
        with self._lock:
            return self._query_counts.most_common(n)

    def top_zero_result_queries(self, n: int = 20) -> list[tuple[str, int]]:
        with self._lock:
            return self._zero_result_queries.most_common(n)

    def mode_distribution(self) -> dict[str, int]:
        with self._lock:
            return dict(self._mode_counts)

    def query_count(self, query: str) -> int:
        with self._lock:
            return self._query_counts[query.strip().lower()]

    def total_searches(self) -> int:
        with self._lock:
            return sum(self._query_counts.values())

    def stats(self) -> dict:
        with self._lock:
            return {
                "total_searches": sum(self._query_counts.values()),
                "unique_queries": len(self._query_counts),
                "zero_result_queries": len(self._zero_result_queries),
                "mode_distribution": dict(self._mode_counts),
                "top_10": self._query_counts.most_common(10),
            }


# Module-level singleton — imported by FastAPI dependency
_store = AnalyticsStore()


def get_analytics_store() -> AnalyticsStore:
    return _store
