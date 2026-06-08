"""
Phase 4 exit gate: assert latency targets are met against live API.
Runs a smaller set of rounds so CI completes quickly.
"""

import pytest
from tests.benchmarks.bench_latency import run_benchmark


TARGETS = {
    "autocomplete": {"p50": 50, "p95": 150},
    "submit": {"p50": 100, "p95": 300},
}


def _api_available() -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:8001/health", timeout=2):
            return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def benchmark_results():
    if not _api_available():
        pytest.skip("cirro-search API not available at http://localhost:8001")
    auto, submit = run_benchmark("http://localhost:8001", runs=10)
    return auto, submit


def test_autocomplete_p50(benchmark_results):
    auto, _ = benchmark_results
    r = auto.report()
    assert r["p50_ms"] <= TARGETS["autocomplete"]["p50"], (
        f"Autocomplete p50 {r['p50_ms']}ms exceeds target {TARGETS['autocomplete']['p50']}ms"
    )


def test_autocomplete_p95(benchmark_results):
    auto, _ = benchmark_results
    r = auto.report()
    assert r["p95_ms"] <= TARGETS["autocomplete"]["p95"], (
        f"Autocomplete p95 {r['p95_ms']}ms exceeds target {TARGETS['autocomplete']['p95']}ms"
    )


def test_submit_p50(benchmark_results):
    _, submit = benchmark_results
    r = submit.report()
    assert r["p50_ms"] <= TARGETS["submit"]["p50"], (
        f"Submit p50 {r['p50_ms']}ms exceeds target {TARGETS['submit']['p50']}ms"
    )


def test_submit_p95(benchmark_results):
    _, submit = benchmark_results
    r = submit.report()
    assert r["p95_ms"] <= TARGETS["submit"]["p95"], (
        f"Submit p95 {r['p95_ms']}ms exceeds target {TARGETS['submit']['p95']}ms"
    )
