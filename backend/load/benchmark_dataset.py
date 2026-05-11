"""Local API benchmark for larger SigmaLite datasets.

This is intentionally lightweight and deterministic. It uses FastAPI's
TestClient against an isolated SQLite database so it can run without staging
credentials. Staging/production load should still use Locust.
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
from typing import Callable


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


def run_benchmark(rows: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="sigmalite-benchmark-") as tmp:
        workdir = Path(tmp)
        _configure_env(workdir)

        from fastapi.testclient import TestClient

        from app.core.database import Base, engine
        from app.main import app

        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        client = TestClient(app)

        username = f"bench_{rows}"
        password = "benchpass123"
        register = client.post(
            "/api/auth/register",
            json={
                "email": f"{username}@example.com",
                "username": username,
                "password": password,
            },
        )
        register.raise_for_status()
        login = client.post("/api/auth/login", data={"username": username, "password": password})
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        timings: dict[str, float] = {}

        name, elapsed, upload = _timed(
            "upload_ingest_seconds",
            lambda: client.post(
                "/api/datasets",
                headers=headers,
                data={"name": f"{rows} row benchmark"},
                files={"file": ("benchmark.csv", _csv_bytes(rows), "text/csv")},
            ),
        )
        upload.raise_for_status()
        timings[name] = elapsed
        dataset_id = upload.json()["id"]

        sheet = client.post(
            "/api/sheets",
            headers=headers,
            json={"name": "benchmark sheet", "dataset_id": dataset_id},
        )
        sheet.raise_for_status()
        sheet_id = sheet.json()["id"]

        operations = {
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
            "export_csv_seconds": lambda: client.post(
                f"/api/sheets/{sheet_id}/export",
                headers=headers,
                json={"format": "csv", "filters": [], "logic": "and"},
            ),
        }
        for name, operation in operations.items():
            op_name, elapsed, response = _timed(name, operation)
            response.raise_for_status()
            timings[op_name] = elapsed

        return {
            "rows": rows,
            "timings": timings,
            "public_beta_targets": evaluate_public_beta_targets(timings),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=50_000)
    parser.add_argument(
        "--assert-targets",
        action="store_true",
        help="Exit nonzero if public-beta query/filter/aggregate targets are missed.",
    )
    args = parser.parse_args()
    result = run_benchmark(args.rows)
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
