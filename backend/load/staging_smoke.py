"""Deployed API smoke test for SigmaLite public-beta verification."""
from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any
from uuid import uuid4

import httpx


SAMPLE_CSV = b"name,age,city\nAlice,30,NYC\nBob,25,LA\nCarol,40,SF\n"


class SmokeError(RuntimeError):
    """Raised when a deployed smoke check fails."""


def _response_excerpt(response: httpx.Response) -> str:
    text = response.text.strip()
    return text[:500] if text else "<empty response>"


def _expect(response: httpx.Response, expected_status: int, step: str) -> httpx.Response:
    if response.status_code != expected_status:
        raise SmokeError(
            f"{step} failed: expected HTTP {expected_status}, got "
            f"{response.status_code}: {_response_excerpt(response)}"
        )
    return response


def _json(response: httpx.Response, step: str) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError as exc:
        raise SmokeError(f"{step} failed: response was not JSON") from exc
    if not isinstance(body, dict):
        raise SmokeError(f"{step} failed: expected a JSON object")
    return body


def _unique_user() -> dict[str, str]:
    suffix = f"{int(time.time())}-{uuid4().hex[:8]}"
    username = f"smoke_{suffix}"
    return {
        "email": f"{username}@example.com",
        "username": username,
        "password": f"SmokePass-{uuid4().hex[:12]}",
    }


def run_staging_smoke(
    api_url: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Run a compact end-to-end smoke flow against a deployed API."""
    base_url = api_url.rstrip("/")
    close_client = client is None
    if client is None:
        client = httpx.Client(base_url=base_url, timeout=timeout)

    checks: list[str] = []
    user = _unique_user()
    headers: dict[str, str] = {}

    try:
        ready = _expect(client.get("/health/ready"), 200, "health ready")
        _json(ready, "health ready")
        checks.append("health_ready")

        register = _expect(
            client.post(
                "/api/auth/register",
                json={
                    "email": user["email"],
                    "username": user["username"],
                    "password": user["password"],
                    "full_name": "SigmaLite Smoke",
                },
            ),
            201,
            "register unique user",
        )
        registered_user = _json(register, "register unique user")
        checks.append("register")

        login = _expect(
            client.post(
                "/api/auth/login",
                data={"username": user["username"], "password": user["password"]},
            ),
            200,
            "login",
        )
        token = _json(login, "login").get("access_token")
        if not token:
            raise SmokeError("login failed: response did not include access_token")
        headers = {"Authorization": f"Bearer {token}"}
        checks.append("login")

        upload = _expect(
            client.post(
                "/api/datasets",
                headers=headers,
                data={"name": f"Smoke dataset {user['username']}", "description": "staging smoke"},
                files={"file": ("smoke.csv", SAMPLE_CSV, "text/csv")},
            ),
            201,
            "upload csv dataset",
        )
        dataset = _json(upload, "upload csv dataset")
        dataset_id = dataset.get("id")
        if dataset_id is None:
            raise SmokeError("upload csv dataset failed: response did not include id")
        checks.append("upload_csv")

        sheet_response = _expect(
            client.post(
                "/api/sheets",
                headers=headers,
                json={
                    "name": f"Smoke sheet {user['username']}",
                    "description": "staging smoke",
                    "dataset_id": dataset_id,
                },
            ),
            201,
            "create sheet",
        )
        sheet = _json(sheet_response, "create sheet")
        sheet_id = sheet.get("id")
        if sheet_id is None:
            raise SmokeError("create sheet failed: response did not include id")
        checks.append("create_sheet")

        query_response = _expect(
            client.post(
                f"/api/datasets/{dataset_id}/query",
                headers=headers,
                json={
                    "filters": [{"column": "age", "operator": "gte", "value": 25}],
                    "logic": "and",
                    "sort": {"column": "name", "direction": "asc"},
                    "page": 1,
                    "page_size": 3,
                },
            ),
            200,
            "query dataset",
        )
        query = _json(query_response, "query dataset")
        rows = query.get("data")
        if not isinstance(rows, list) or not rows:
            raise SmokeError("query dataset failed: no rows returned")
        checks.append("query_dataset")

        first_row = rows[0]
        versions = first_row.get("__cell_versions", {}) if isinstance(first_row, dict) else {}
        expected_version = versions.get("city")
        if expected_version is None:
            raise SmokeError("query dataset failed: row did not include city cell version")

        cell_response = _expect(
            client.patch(
                f"/api/sheets/{sheet_id}/cell",
                headers=headers,
                json={
                    "row_index": first_row.get("__source_index", 0),
                    "column": "city",
                    "value": "Boston",
                    "expected_version": expected_version,
                },
            ),
            200,
            "patch sheet cell",
        )
        cell = _json(cell_response, "patch sheet cell")
        checks.append("patch_cell")

        comment_response = _expect(
            client.post(
                f"/api/sheets/{sheet_id}/comments",
                headers=headers,
                json={"text": "Smoke check comment", "row_index": 0, "column": "city"},
            ),
            201,
            "create comment",
        )
        comment = _json(comment_response, "create comment")
        checks.append("create_comment")

        chart_response = _expect(
            client.post(
                "/api/charts",
                headers=headers,
                json={
                    "name": "Smoke ages",
                    "chart_type": "bar",
                    "sheet_id": sheet_id,
                    "config": {"x_axis": "name", "y_axis": "age"},
                },
            ),
            201,
            "create chart",
        )
        chart = _json(chart_response, "create chart")
        checks.append("create_chart")

        export_response = _expect(
            client.post(
                f"/api/sheets/{sheet_id}/export",
                headers=headers,
                json={"format": "csv", "filters": [], "logic": "and"},
            ),
            200,
            "export csv",
        )
        if not export_response.content.startswith(b"name,age,city"):
            raise SmokeError("export csv failed: CSV did not start with expected header")
        checks.append("export_csv")

        return {
            "ok": True,
            "api_url": base_url,
            "checks": checks,
            "user": {"id": registered_user.get("id"), "username": user["username"]},
            "dataset_id": dataset_id,
            "sheet_id": sheet_id,
            "comment_id": comment.get("id"),
            "chart_id": chart.get("id"),
            "patched_cell_version": cell.get("version"),
            "rows_queried": len(rows),
            "csv_export_bytes": len(export_response.content),
        }
    finally:
        if close_client:
            client.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a compact deployed SigmaLite API smoke test."
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("SIGMALITE_API_URL"),
        help="Deployed API base URL. Defaults to SIGMALITE_API_URL.",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    if not args.api_url:
        parser.error("--api-url is required when SIGMALITE_API_URL is not set")

    try:
        summary = run_staging_smoke(args.api_url, timeout=args.timeout)
    except (SmokeError, httpx.HTTPError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 1

    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
