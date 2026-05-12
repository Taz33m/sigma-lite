"""SigmaLite benchmark for larger datasets.

By default this runs FastAPI's TestClient against an isolated SQLite database
so it can run without external services. Pass ``--api-url`` to benchmark a
running API backed by Postgres/Redis or a staging/self-hosted deployment.
Staging concurrency checks should still use Locust.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _configure_env(workdir: Path) -> None:
    os.environ["DATABASE_URL"] = f"sqlite:///{workdir / 'benchmark.db'}"
    os.environ["SECRET_KEY"] = "benchmark-secret-key-not-for-production"
    os.environ["ENVIRONMENT"] = "test"
    os.environ["UPLOAD_DIR"] = str(workdir / "uploads")
    os.environ["RATE_LIMIT_BACKEND"] = "memory"


def _csv_bytes(rows: int) -> bytes:
    departments = ["Engineering", "Sales", "Marketing", "Finance", "Support"]
    cities = ["New York", "San Francisco", "Chicago", "Boston", "Austin"]
    output = io.StringIO()
    output.write("employee_id,name,department,city,age,salary,score\n")
    for index in range(rows):
        output.write(
            f"{index + 1},person-{index},{departments[index % len(departments)]},"
            f"{cities[index % len(cities)]},{22 + (index % 43)},"
            f"{55000 + (index % 90000)},{round((index % 1000) / 10, 1)}\n"
        )
    return output.getvalue().encode("utf-8")


def _timed(name: str, fn: Callable[[], object]) -> tuple[str, float, object]:
    started = time.perf_counter()
    result = fn()
    return name, time.perf_counter() - started, result


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * percentile))))
    return ordered[index]


def _expect_success(response: httpx.Response, step: str) -> httpx.Response:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        excerpt = response.text.strip()[:500] or "<empty response>"
        raise RuntimeError(
            f"{step} failed with HTTP {response.status_code}: {excerpt}"
        ) from exc
    return response


def _register_and_login(client: httpx.Client, rows: int) -> dict[str, str]:
    suffix = uuid4().hex[:10]
    username = f"bench_{rows}_{suffix}"
    password = f"BenchPass-{uuid4().hex[:12]}"
    _expect_success(
        client.post(
            "/api/auth/register",
            json={
                "email": f"{username}@example.com",
                "username": username,
                "password": password,
            },
        ),
        "register benchmark user",
    )
    login = _expect_success(
        client.post("/api/auth/login", data={"username": username, "password": password}),
        "login benchmark user",
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_benchmark_sheet(
    client: httpx.Client,
    *,
    headers: dict[str, str],
    rows: int,
) -> tuple[int, int, dict[str, float]]:
    timings: dict[str, float] = {}
    name, elapsed, upload = _timed(
        "upload_ingest_seconds",
        lambda: client.post(
            "/api/datasets",
            headers=headers,
            data={"name": f"{rows} row benchmark {uuid4().hex[:8]}"},
            files={"file": ("benchmark.csv", _csv_bytes(rows), "text/csv")},
        ),
    )
    _expect_success(upload, "upload benchmark dataset")
    timings[name] = elapsed
    dataset_id = upload.json()["id"]

    sheet = _expect_success(
        client.post(
            "/api/sheets",
            headers=headers,
            json={"name": "benchmark sheet", "dataset_id": dataset_id},
        ),
        "create benchmark sheet",
    )
    return dataset_id, sheet.json()["id"], timings


def _measure_operations(
    client: httpx.Client,
    *,
    headers: dict[str, str],
    sheet_id: int,
    repetitions: int,
    include_export: bool,
) -> tuple[dict[str, float], dict[str, list[float]]]:
    samples: dict[str, list[float]] = {
        "page_query_seconds": [],
        "filter_sort_seconds": [],
        "aggregate_seconds": [],
    }
    operations: dict[str, Callable[[], httpx.Response]] = {
        "page_query_seconds": lambda: client.post(
            f"/api/sheets/{sheet_id}/query",
            headers=headers,
            json={"filters": [], "logic": "and", "page": 25, "page_size": 100},
        ),
        "filter_sort_seconds": lambda: client.post(
            f"/api/sheets/{sheet_id}/query",
            headers=headers,
            json={
                "filters": [{"column": "department", "operator": "eq", "value": "Engineering"}],
                "logic": "and",
                "sort": {"column": "salary", "direction": "desc"},
                "page": 1,
                "page_size": 100,
            },
        ),
        "aggregate_seconds": lambda: client.post(
            f"/api/sheets/{sheet_id}/aggregate",
            headers=headers,
            json={"column": "salary", "operation": "avg", "group_by": ["department"]},
        ),
    }
    if include_export:
        samples["export_csv_seconds"] = []
        operations["export_csv_seconds"] = lambda: client.post(
            f"/api/sheets/{sheet_id}/export",
            headers=headers,
            json={"format": "csv", "filters": [], "logic": "and"},
        )

    for _ in range(repetitions):
        for operation_name, operation in operations.items():
            _, elapsed, response = _timed(operation_name, operation)
            _expect_success(response, operation_name)
            samples[operation_name].append(elapsed)

    timings = {
        operation_name: value
        for operation_name, values in samples.items()
        if (value := _percentile(values, 0.95)) is not None
    }
    return timings, samples


PUBLIC_BETA_TARGETS = {
    "page_query_seconds": 0.5,
    "filter_sort_seconds": 1.5,
    "aggregate_seconds": 2.0,
}


def evaluate_public_beta_targets(timings: dict[str, float]) -> list[dict[str, object]]:
    """Return public-beta target checks for measured operations."""
    checks = []
    for operation, target_seconds in PUBLIC_BETA_TARGETS.items():
        actual_seconds = timings.get(operation)
        checks.append(
            {
                "operation": operation,
                "target_seconds": target_seconds,
                "actual_seconds": actual_seconds,
                "ok": actual_seconds is not None and actual_seconds <= target_seconds,
            }
        )
    return checks


def run_benchmark(
    rows: int,
    *,
    repetitions: int = 1,
    include_export: bool = True,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="sigmalite-benchmark-") as tmp:
        workdir = Path(tmp)
        _configure_env(workdir)

        from fastapi.testclient import TestClient

        from app.core.database import Base, engine
        from app.main import app

        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        client = TestClient(app)

        headers = _register_and_login(client, rows)
        _, sheet_id, timings = _create_benchmark_sheet(client, headers=headers, rows=rows)
        operation_timings, samples = _measure_operations(
            client,
            headers=headers,
            sheet_id=sheet_id,
            repetitions=repetitions,
            include_export=include_export,
        )
        timings.update(operation_timings)

        return {
            "rows": rows,
            "mode": "sqlite-testclient",
            "repetitions": repetitions,
            "timings": timings,
            "samples": samples,
            "public_beta_targets": evaluate_public_beta_targets(timings),
        }


def run_api_benchmark(
    api_url: str,
    *,
    rows: int,
    repetitions: int,
    timeout: float,
    include_export: bool,
) -> dict[str, Any]:
    base_url = api_url.rstrip("/")
    with httpx.Client(base_url=base_url, timeout=timeout) as client:
        _expect_success(client.get("/health/ready"), "health ready")
        headers = _register_and_login(client, rows)
        dataset_id, sheet_id, timings = _create_benchmark_sheet(
            client,
            headers=headers,
            rows=rows,
        )
        operation_timings, samples = _measure_operations(
            client,
            headers=headers,
            sheet_id=sheet_id,
            repetitions=repetitions,
            include_export=include_export,
        )
        timings.update(operation_timings)
        return {
            "rows": rows,
            "mode": "api",
            "api_url": base_url,
            "dataset_id": dataset_id,
            "sheet_id": sheet_id,
            "repetitions": repetitions,
            "timings": timings,
            "samples": samples,
            "public_beta_targets": evaluate_public_beta_targets(timings),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=50_000)
    parser.add_argument(
        "--api-url",
        help="Benchmark a running API instead of the isolated SQLite TestClient.",
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Skip CSV export timing. Useful for large API runs focused on query targets.",
    )
    parser.add_argument(
        "--assert-targets",
        action="store_true",
        help="Exit nonzero if public-beta query/filter/aggregate targets are missed.",
    )
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("--repetitions must be at least 1")
    if args.api_url:
        result = run_api_benchmark(
            args.api_url,
            rows=args.rows,
            repetitions=args.repetitions,
            timeout=args.timeout,
            include_export=not args.skip_export,
        )
    else:
        result = run_benchmark(
            args.rows,
            repetitions=args.repetitions,
            include_export=not args.skip_export,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.assert_targets:
        failures = [
            check
            for check in result["public_beta_targets"]
            if not check["ok"]
        ]
        if failures:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
