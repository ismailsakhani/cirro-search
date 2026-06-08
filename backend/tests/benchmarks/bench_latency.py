"""
Phase 4 latency benchmark.

Measures p50/p95/p99 and mean latency for autocomplete and submit modes
against a live cirro-search API (default: http://localhost:8001).

Usage:
    python -m tests.benchmarks.bench_latency
    python -m tests.benchmarks.bench_latency --url http://localhost:8001 --runs 200

Exit criteria (from PLAN.md):
    Autocomplete p50 < 50ms,  p95 < 150ms
    Submit       p50 < 100ms, p95 < 300ms
"""

from __future__ import annotations

import argparse
import statistics
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field


QUERIES_AUTOCOMPLETE = [
    "new",
    "newar",
    "ua4",
    "ua44",
    "ua443",
    "las",
    "las v",
    "c10",
    "ewr",
    "den",
    "bos",
    "atl",
    "dal",
    "ua",
]

QUERIES_SUBMIT = [
    "newrk",
    "newark airport",
    "vegas airport",
    "harry reid",
    "ua4433",
    "4433",
    "united 4433",
    "c101",
    "ewr c101",
    "ewr",
    "kewr",
    "newark",
    "las",
    "perry",
    "CYOW",
    "denver",
    "boston logan",
    "atlanta",
    "ua500",
    "b17",
]


@dataclass
class BenchResult:
    mode: str
    query: str
    latency_ms: float
    status: int
    result_count: int = 0


@dataclass
class BenchSummary:
    mode: str
    samples: list[float] = field(default_factory=list)

    def add(self, ms: float) -> None:
        self.samples.append(ms)

    def p(self, pct: float) -> float:
        if not self.samples:
            return 0.0
        sorted_s = sorted(self.samples)
        idx = min(int(len(sorted_s) * pct / 100), len(sorted_s) - 1)
        return sorted_s[idx]

    def mean(self) -> float:
        return statistics.mean(self.samples) if self.samples else 0.0

    def report(self) -> dict:
        return {
            "mode": self.mode,
            "n": len(self.samples),
            "mean_ms": round(self.mean(), 1),
            "p50_ms": round(self.p(50), 1),
            "p95_ms": round(self.p(95), 1),
            "p99_ms": round(self.p(99), 1),
            "min_ms": round(min(self.samples), 1) if self.samples else 0,
            "max_ms": round(max(self.samples), 1) if self.samples else 0,
        }


def _fetch(url: str, timeout: float = 5.0) -> tuple[int, float, int]:
    """Return (status_code, latency_ms, result_count)."""
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            import json
            body = json.loads(resp.read())
            elapsed = (time.perf_counter() - start) * 1000
            count = len(body.get("results", []))
            return resp.status, elapsed, count
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        return 0, elapsed, 0


def run_benchmark(base_url: str, runs: int = 100) -> tuple[BenchSummary, BenchSummary]:
    auto_summary = BenchSummary(mode="autocomplete")
    submit_summary = BenchSummary(mode="submit")

    # Warm up — discard first 5 requests
    for q in QUERIES_SUBMIT[:5]:
        _fetch(f"{base_url}/api/v1/search?q={urllib.parse.quote(q)}")

    for _ in range(runs):
        for q in QUERIES_AUTOCOMPLETE:
            url = f"{base_url}/api/v1/suggestions?q={urllib.parse.quote(q)}"
            _, ms, _ = _fetch(url)
            auto_summary.add(ms)

        for q in QUERIES_SUBMIT:
            url = f"{base_url}/api/v1/search?q={urllib.parse.quote(q)}"
            _, ms, _ = _fetch(url)
            submit_summary.add(ms)

    return auto_summary, submit_summary


def print_report(auto: BenchSummary, submit: BenchSummary) -> None:
    thresholds = {
        "autocomplete": {"p50": 50, "p95": 150},
        "submit": {"p50": 100, "p95": 300},
    }

    print("\n" + "=" * 55)
    print("cirro-search  —  Latency Benchmark  (Phase 4)")
    print("=" * 55)

    for summary in (auto, submit):
        r = summary.report()
        t = thresholds[summary.mode]
        p50_ok = "✓" if r["p50_ms"] <= t["p50"] else "✗"
        p95_ok = "✓" if r["p95_ms"] <= t["p95"] else "✗"

        print(f"\nMode: {r['mode'].upper()}  (n={r['n']})")
        print(f"  mean   {r['mean_ms']:>8.1f} ms")
        print(f"  p50    {r['p50_ms']:>8.1f} ms   {p50_ok}  target < {t['p50']}ms")
        print(f"  p95    {r['p95_ms']:>8.1f} ms   {p95_ok}  target < {t['p95']}ms")
        print(f"  p99    {r['p99_ms']:>8.1f} ms")
        print(f"  min    {r['min_ms']:>8.1f} ms")
        print(f"  max    {r['max_ms']:>8.1f} ms")

    print("\n" + "=" * 55)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8001")
    parser.add_argument("--runs", type=int, default=50)
    args = parser.parse_args()

    print(f"Benchmarking {args.url}  ({args.runs} rounds × {len(QUERIES_SUBMIT)} submit + {len(QUERIES_AUTOCOMPLETE)} autocomplete queries)...")
    auto, submit = run_benchmark(args.url, runs=args.runs)
    print_report(auto, submit)
    print(f"\nRaw data:")
    print(f"  autocomplete: {auto.report()}")
    print(f"  submit:       {submit.report()}")
