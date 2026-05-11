import json

import httpx
import pytest

from load.staging_smoke import SmokeError, run_staging_smoke


def _json_response(status_code, payload):
    return httpx.Response(status_code, json=payload)


def test_staging_smoke_runs_key_flow_with_mock_transport():
    requests = []

    def handler(request):
        requests.append(request)
        assert str(request.url).startswith("https://api.example.test/")

        if request.method == "GET" and request.url.path == "/health/ready":
            return _json_response(200, {"status": "ready"})
        if request.method == "POST" and request.url.path == "/api/auth/register":
            return _json_response(201, {"id": 10, "username": "created"})
        if request.method == "POST" and request.url.path == "/api/auth/login":
            return _json_response(
                200,
                {
                    "access_token": "token-123",
                    "refresh_token": "refresh-123",
                    "token_type": "bearer",
                },
            )

        assert request.headers["authorization"] == "Bearer token-123"

        if request.method == "POST" and request.url.path == "/api/datasets":
            assert "multipart/form-data" in request.headers["content-type"]
            return _json_response(201, {"id": 20, "row_count": 3, "column_count": 3})
        if request.method == "POST" and request.url.path == "/api/sheets":
            return _json_response(201, {"id": 30, "dataset_id": 20})
        if request.method == "POST" and request.url.path == "/api/datasets/20/query":
            return _json_response(
                200,
                {
                    "data": [
                        {
                            "name": "Alice",
                            "age": "30",
                            "city": "NYC",
                            "__source_index": 0,
                            "__cell_versions": {"city": 1},
                        }
                    ],
                    "total_rows": 1,
                },
            )
        if request.method == "PATCH" and request.url.path == "/api/sheets/30/cell":
            payload = json.loads(request.read())
            assert payload == {
                "row_index": 0,
                "column": "city",
                "value": "Boston",
                "expected_version": 1,
            }
            return _json_response(
                200,
                {"row_index": 0, "column": "city", "value": "Boston", "version": 2},
            )
        if request.method == "POST" and request.url.path == "/api/sheets/30/comments":
            return _json_response(201, {"id": 40, "text": "Smoke check comment"})
        if request.method == "POST" and request.url.path == "/api/charts":
            return _json_response(201, {"id": 50, "name": "Smoke ages"})
        if request.method == "POST" and request.url.path == "/api/sheets/30/export":
            return httpx.Response(200, content=b"name,age,city\nAlice,30,Boston\n")

        return httpx.Response(404, json={"detail": request.url.path})

    client = httpx.Client(
        base_url="https://api.example.test",
        transport=httpx.MockTransport(handler),
    )

    summary = run_staging_smoke("https://api.example.test/", client=client)

    assert summary["ok"] is True
    assert summary["api_url"] == "https://api.example.test"
    assert summary["dataset_id"] == 20
    assert summary["sheet_id"] == 30
    assert summary["comment_id"] == 40
    assert summary["chart_id"] == 50
    assert summary["patched_cell_version"] == 2
    assert summary["csv_export_bytes"] == len(b"name,age,city\nAlice,30,Boston\n")
    assert summary["checks"] == [
        "health_ready",
        "register",
        "login",
        "upload_csv",
        "create_sheet",
        "query_dataset",
        "patch_cell",
        "create_comment",
        "create_chart",
        "export_csv",
    ]
    assert [request.url.path for request in requests] == [
        "/health/ready",
        "/api/auth/register",
        "/api/auth/login",
        "/api/datasets",
        "/api/sheets",
        "/api/datasets/20/query",
        "/api/sheets/30/cell",
        "/api/sheets/30/comments",
        "/api/charts",
        "/api/sheets/30/export",
    ]

    client.close()


def test_staging_smoke_fails_clearly_on_bad_status():
    def handler(request):
        return httpx.Response(503, json={"detail": "database unavailable"})

    client = httpx.Client(
        base_url="https://api.example.test",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(SmokeError, match="health ready failed"):
        run_staging_smoke("https://api.example.test", client=client)

    client.close()
