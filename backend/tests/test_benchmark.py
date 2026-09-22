"""The load tool must protect databases and retain inconvenient measurements."""

from collections import Counter
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.engine import URL, make_url

from app.cli import benchmark

RUNTIME = make_url("postgresql+asyncpg://tracker:example@127.0.0.1:5433/tracker")
OWNER = RUNTIME.set(username="tracker_owner")


@pytest.mark.parametrize(
    "name",
    [
        "tracker",
        "tracker_test",
        "postgres",
        "tracker_benchmark_",
        "tracker_benchmark_" + "a" * 41,
        "tracker_benchmark_x;DROP DATABASE tracker",
        "tracker_benchmark_../tracker",
    ],
)
def test_only_explicit_benchmark_database_names_are_accepted(name: str) -> None:
    with pytest.raises(benchmark.BenchmarkError):
        benchmark.validate_target(name, RUNTIME, OWNER)
    benchmark.validate_target("tracker_benchmark_safe_20260911", RUNTIME, OWNER)


@pytest.mark.parametrize(
    ("runtime", "owner"),
    [
        (RUNTIME.set(host="database.example.com"), OWNER),
        (RUNTIME, OWNER.set(host="database.example.com")),
        (RUNTIME, OWNER.set(port=5434)),
        (RUNTIME.set(drivername="sqlite"), OWNER),
        (RUNTIME.set(username='tracker";DROP'), OWNER),
        (RUNTIME, make_url("postgresql+asyncpg://127.0.0.1:5433/tracker")),
    ],
)
def test_remote_mismatched_or_unquotable_targets_are_rejected(runtime: URL, owner: URL) -> None:
    with pytest.raises(benchmark.BenchmarkError):
        benchmark.validate_target("tracker_benchmark_safe", runtime, owner)


async def test_existing_database_is_never_reused_or_deleted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = AsyncMock()
    connection.fetchval.return_value = 1
    connect = AsyncMock(return_value=connection)
    monkeypatch.setattr(benchmark.asyncpg, "connect", connect)

    with pytest.raises(benchmark.BenchmarkError, match="already exists"):
        await benchmark.create_database("tracker_benchmark_existing", OWNER, "test-password")

    connection.execute.assert_not_awaited()
    connection.close.assert_awaited_once()


def test_summary_includes_http_errors_and_timeouts_in_percentiles() -> None:
    observations = [
        benchmark.Observation(0, 0, "GET /example", 200, 10, 0, None),
        benchmark.Observation(1, 1, "GET /example", 503, 1500, 200, "HTTP_503"),
        benchmark.Observation(2, 2, "GET /example", None, 10000, 3000, "ReadTimeout"),
    ]
    result = benchmark.summarize(observations)
    assert result["requests"] == 3
    assert result["errors"] == 2
    assert result["p50_ms"] == 1500
    assert result["p95_ms"] == result["max_ms"] == 10000
    assert result["scheduled_response_p95_ms"] == 13000
    assert result["error_rate_percent"] == 66.667
    assert result["http_statuses"] == {"200": 1, "503": 1, "None": 1}


async def test_one_hundred_requests_use_the_exact_mix_without_hidden_reads() -> None:
    calls: Counter[str] = Counter()

    def response(request: benchmark.httpx.Request) -> benchmark.httpx.Response:
        path = request.url.path
        if path.endswith("/analytics"):
            key = "analytics"
        elif path.endswith("/login"):
            key = "login"
        elif path.endswith("/me"):
            key = "me"
        elif request.method == "PATCH":
            key = "patch"
        elif path.endswith("/tasks"):
            key = "filters"
            assert len(request.url.params) == 6
        elif "/boards/" in path:
            key = "board"
        else:
            key = "task"
        calls[key] += 1
        return benchmark.httpx.Response(200, json={"data": {"version": 2}, "csrf_token": "csrf"})

    client = benchmark.Client(0, "http://127.0.0.1:8010", "benchmark-password")
    await client.client.aclose()
    client.client = benchmark.httpx.AsyncClient(
        base_url="http://127.0.0.1:8010", transport=benchmark.httpx.MockTransport(response)
    )
    try:
        results = [
            await client.request(index, benchmark.time.perf_counter()) for index in range(100)
        ]
    finally:
        await client.client.aclose()

    assert all(item.error is None for item in results)
    assert calls == Counter(board=30, task=30, filters=20, patch=10, analytics=5, me=2, login=3)
    assert sum(calls.values()) == 100


async def test_pacing_uses_original_schedule_even_after_a_slow_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [0.0]
    starts: list[tuple[int, float]] = []

    async def fake_sleep(seconds: float) -> None:
        now[0] += seconds

    class SlowClient:
        number = 0

        async def request(self, sequence: int, scheduled: float) -> benchmark.Observation:
            starts.append((sequence, scheduled))
            now[0] += 1.5  # Slower than this client's one-second cadence.
            return benchmark.Observation(sequence, 0, "slow", 200, 1500, 0, None)

    monkeypatch.setattr(benchmark.time, "perf_counter", lambda: now[0])
    monkeypatch.setattr(benchmark.asyncio, "sleep", fake_sleep)
    result, duration = await benchmark.phase([SlowClient()], 3)  # type: ignore[list-item]
    assert starts == [(0, 0.0), (10, 1.0), (20, 2.0)]
    assert len(result) == 3
    assert duration == 4.5


def test_fast_http_cannot_pass_when_the_scheduled_load_was_not_met() -> None:
    result = {
        "overall": {
            "requests": 3000,
            "errors": 0,
            "p95_ms": 10,
            "schedule_delay_p95_ms": 2500,
            "schedule_delay_max_ms": 5000,
        },
        "warmup": {"errors": 0},
        "by_route": {"GET /example": {"p95_ms": 10}},
        "actual_measurement_seconds": 305,
        "source_sha256_before": "same",
        "source_sha256_after": "same",
    }
    verdict = benchmark.acceptance(result)
    assert verdict["overall_p95_within_1s"] is True
    assert verdict["load_profile_met"] is False
    assert all(verdict.values()) is False
