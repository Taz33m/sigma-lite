from app.core.rate_limit import check_query_rate_limit
from app.main import app


def _dataset_route_dependencies(path, method):
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return [dependency.call for dependency in route.dependant.dependencies]
    raise AssertionError(f"Route {method} {path} not found")


def test_upload_csv_dataset(client, auth_headers, sample_csv_bytes):
    response = client.post(
        "/api/datasets",
        headers=auth_headers,
        data={"name": "people"},
        files={"file": ("people.csv", sample_csv_bytes, "text/csv")},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "people"
    assert data["row_count"] == 3
    assert data["column_count"] == 3
    assert data["file_name"] == "people.csv"


def test_upload_rate_limit_is_per_authenticated_user(
    client, auth_headers, second_user_headers
):
    for index in range(10):
        response = client.post(
            "/api/datasets",
            headers=auth_headers,
            data={"name": f"people {index}"},
            files={"file": ("people.csv", b"name,age\nAlice,30\n", "text/csv")},
        )
        assert response.status_code == 201, response.text

    blocked = client.post(
        "/api/datasets",
        headers=auth_headers,
        data={"name": "blocked"},
        files={"file": ("people.csv", b"name,age\nAlice,30\n", "text/csv")},
    )
    assert blocked.status_code == 429

    collaborator_allowed = client.post(
        "/api/datasets",
        headers=second_user_headers,
        data={"name": "other user"},
        files={"file": ("people.csv", b"name,age\nBob,25\n", "text/csv")},
    )
    assert collaborator_allowed.status_code == 201, collaborator_allowed.text


def test_upload_rejects_non_csv(client, auth_headers):
    response = client.post(
        "/api/datasets",
        headers=auth_headers,
        data={"name": "bad"},
        files={"file": ("data.txt", b"not a csv", "text/plain")},
    )
    assert response.status_code == 400


def test_upload_rejects_empty_csv(client, auth_headers):
    response = client.post(
        "/api/datasets",
        headers=auth_headers,
        data={"name": "empty"},
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert response.status_code == 400
    assert "Invalid CSV file" in response.json()["detail"]


def test_upload_sanitizes_display_filename(client, auth_headers, sample_csv_bytes):
    response = client.post(
        "/api/datasets",
        headers=auth_headers,
        data={"name": "safe name"},
        files={"file": ("../people.csv", sample_csv_bytes, "text/csv")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["file_name"] == "people.csv"


def test_upload_same_filename_keeps_independent_files(client, auth_headers):
    first = client.post(
        "/api/datasets",
        headers=auth_headers,
        data={"name": "first"},
        files={"file": ("people.csv", b"name,age\nAlice,30\n", "text/csv")},
    )
    second = client.post(
        "/api/datasets",
        headers=auth_headers,
        data={"name": "second"},
        files={"file": ("people.csv", b"name,age\nBob,25\n", "text/csv")},
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    first_id = first.json()["id"]
    second_id = second.json()["id"]
    assert first.json()["file_name"] == "people.csv"
    assert second.json()["file_name"] == "people.csv"

    delete = client.delete(f"/api/datasets/{first_id}", headers=auth_headers)
    assert delete.status_code == 204

    remaining = client.get(
        f"/api/datasets/{second_id}/data",
        headers=auth_headers,
    )
    assert remaining.status_code == 200
    assert remaining.json()["data"][0]["name"] == "Bob"


def test_upload_requires_auth(client, sample_csv_bytes):
    response = client.post(
        "/api/datasets",
        data={"name": "x"},
        files={"file": ("x.csv", sample_csv_bytes, "text/csv")},
    )
    assert response.status_code == 401


def test_list_datasets(client, auth_headers, uploaded_dataset):
    response = client.get("/api/datasets", headers=auth_headers)
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["id"] == uploaded_dataset["id"]


def test_get_dataset(client, auth_headers, uploaded_dataset):
    response = client.get(
        f"/api/datasets/{uploaded_dataset['id']}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["id"] == uploaded_dataset["id"]


def test_get_dataset_data_paginated(client, auth_headers, uploaded_dataset):
    response = client.get(
        f"/api/datasets/{uploaded_dataset['id']}/data?page=1&page_size=2",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total_rows"] == 3
    assert len(body["data"]) == 2
    assert body["data"][0]["__source_index"] == 0
    assert body["data"][0]["__cell_versions"]["name"] == 1


def test_query_dataset_sorts_server_side(client, auth_headers, uploaded_dataset):
    response = client.post(
        f"/api/datasets/{uploaded_dataset['id']}/query",
        headers=auth_headers,
        json={
            "filters": [],
            "logic": "and",
            "sort": {"column": "name", "direction": "desc"},
            "page": 1,
            "page_size": 3,
        },
    )
    assert response.status_code == 200, response.text
    assert [row["name"] for row in response.json()["data"]] == ["Carol", "Bob", "Alice"]


def test_get_dataset_data_rejects_invalid_pagination(
    client, auth_headers, uploaded_dataset
):
    response = client.get(
        f"/api/datasets/{uploaded_dataset['id']}/data?page=1&page_size=0",
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_dataset_isolation_between_users(
    client, auth_headers, uploaded_dataset, second_user_headers
):
    response = client.get(
        f"/api/datasets/{uploaded_dataset['id']}", headers=second_user_headers
    )
    assert response.status_code == 404


def test_filter_dataset(client, auth_headers, uploaded_dataset):
    response = client.post(
        f"/api/datasets/{uploaded_dataset['id']}/filter",
        headers=auth_headers,
        json={
            "filters": [{"column": "city", "operator": "eq", "value": "NYC"}],
            "logic": "and",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 1
    assert body["data"][0]["name"] == "Alice"
    assert body["data"][0]["__source_index"] == 0


def test_filter_dataset_coerces_numeric_comparison_value(
    client, auth_headers, uploaded_dataset
):
    response = client.post(
        f"/api/datasets/{uploaded_dataset['id']}/filter",
        headers=auth_headers,
        json={
            "filters": [{"column": "age", "operator": "gt", "value": "25"}],
            "logic": "and",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 2
    assert [row["name"] for row in body["data"]] == ["Alice", "Carol"]


def test_filter_dataset_coerces_numeric_equality_value(
    client, auth_headers, uploaded_dataset
):
    response = client.post(
        f"/api/datasets/{uploaded_dataset['id']}/filter",
        headers=auth_headers,
        json={
            "filters": [{"column": "age", "operator": "eq", "value": "25"}],
            "logic": "and",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 1
    assert body["data"][0]["name"] == "Bob"


def test_filter_dataset_coerces_numeric_not_equal_value(
    client, auth_headers, uploaded_dataset
):
    response = client.post(
        f"/api/datasets/{uploaded_dataset['id']}/filter",
        headers=auth_headers,
        json={
            "filters": [{"column": "age", "operator": "ne", "value": "25"}],
            "logic": "and",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 2
    assert [row["name"] for row in body["data"]] == ["Alice", "Carol"]


def test_filter_dataset_rejects_invalid_numeric_comparison_value(
    client, auth_headers, uploaded_dataset
):
    response = client.post(
        f"/api/datasets/{uploaded_dataset['id']}/filter",
        headers=auth_headers,
        json={
            "filters": [{"column": "age", "operator": "gt", "value": "old"}],
            "logic": "and",
        },
    )
    assert response.status_code == 400
    assert "must be numeric" in response.json()["detail"]


def test_update_dataset_cell_persists_value(client, auth_headers, uploaded_dataset):
    response = client.patch(
        f"/api/datasets/{uploaded_dataset['id']}/cell",
        headers=auth_headers,
        json={"row_index": 1, "column": "city", "value": "Seattle"},
    )
    assert response.status_code == 200
    assert response.json()["value"] == "Seattle"

    data = client.get(
        f"/api/datasets/{uploaded_dataset['id']}/data?page=1&page_size=3",
        headers=auth_headers,
    ).json()
    assert data["data"][1]["city"] == "Seattle"
    audit = client.get(
        f"/api/audit?entity_type=dataset&entity_id={uploaded_dataset['id']}",
        headers=auth_headers,
    )
    assert audit.status_code == 200, audit.text
    assert any(
        event["action"] == "cell.updated"
        and event["metadata"]["column"] == "city"
        and event["metadata"]["version"] == response.json()["version"]
        for event in audit.json()
    )


def test_update_dataset_cell_evaluates_basic_formula(
    client, auth_headers, uploaded_dataset
):
    response = client.patch(
        f"/api/datasets/{uploaded_dataset['id']}/cell",
        headers=auth_headers,
        json={"row_index": 0, "column": "city", "value": "=SUM(age)"},
    )
    assert response.status_code == 200
    assert response.json()["value"] == 95

    data = client.get(
        f"/api/datasets/{uploaded_dataset['id']}/data?page=1&page_size=1",
        headers=auth_headers,
    ).json()
    assert data["data"][0]["city"] == 95


def test_update_dataset_cell_evaluates_a1_range_formula(
    client, auth_headers, uploaded_dataset
):
    response = client.patch(
        f"/api/datasets/{uploaded_dataset['id']}/cell",
        headers=auth_headers,
        json={"row_index": 0, "column": "city", "value": "=SUM(B1:B2)"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["value"] == 55


def test_update_dataset_cell_evaluates_whole_column_formula(
    client, auth_headers, uploaded_dataset
):
    response = client.patch(
        f"/api/datasets/{uploaded_dataset['id']}/cell",
        headers=auth_headers,
        json={"row_index": 0, "column": "city", "value": "=COUNT(B:B)"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["value"] == 3


def test_update_dataset_cell_rejects_invalid_formula(
    client, auth_headers, uploaded_dataset
):
    response = client.patch(
        f"/api/datasets/{uploaded_dataset['id']}/cell",
        headers=auth_headers,
        json={"row_index": 0, "column": "age", "value": "=SUM(Z1:Z2)"},
    )
    assert response.status_code == 400
    assert "Column" in response.json()["detail"]


def test_update_dataset_cell_rejects_unknown_column(
    client, auth_headers, uploaded_dataset
):
    response = client.patch(
        f"/api/datasets/{uploaded_dataset['id']}/cell",
        headers=auth_headers,
        json={"row_index": 0, "column": "missing", "value": "x"},
    )
    assert response.status_code == 400


def test_filter_dataset_rejects_unknown_column(client, auth_headers, uploaded_dataset):
    response = client.post(
        f"/api/datasets/{uploaded_dataset['id']}/filter",
        headers=auth_headers,
        json={
            "filters": [{"column": "missing", "operator": "eq", "value": "NYC"}],
            "logic": "and",
        },
    )
    assert response.status_code == 400
    assert "Column 'missing' not found" in response.json()["detail"]


def test_filter_dataset_rejects_invalid_operator(client, auth_headers, uploaded_dataset):
    response = client.post(
        f"/api/datasets/{uploaded_dataset['id']}/filter",
        headers=auth_headers,
        json={
            "filters": [{"column": "city", "operator": "matches", "value": "NYC"}],
            "logic": "and",
        },
    )
    assert response.status_code == 422


def test_aggregate_dataset(client, auth_headers, uploaded_dataset):
    response = client.post(
        f"/api/datasets/{uploaded_dataset['id']}/aggregate",
        headers=auth_headers,
        json={"column": "age", "operation": "sum"},
    )
    assert response.status_code == 200
    assert response.json()["result"] == 95


def test_legacy_dataset_read_routes_use_query_rate_limit():
    assert check_query_rate_limit in _dataset_route_dependencies(
        "/api/datasets/{dataset_id}/data", "GET"
    )
    assert check_query_rate_limit in _dataset_route_dependencies(
        "/api/datasets/{dataset_id}/filter", "POST"
    )
    assert check_query_rate_limit in _dataset_route_dependencies(
        "/api/datasets/{dataset_id}/aggregate", "POST"
    )


def test_update_dataset(client, auth_headers, uploaded_dataset):
    response = client.put(
        f"/api/datasets/{uploaded_dataset['id']}",
        headers=auth_headers,
        json={"name": "renamed"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "renamed"
    audit = client.get(
        f"/api/audit?entity_type=dataset&entity_id={uploaded_dataset['id']}",
        headers=auth_headers,
    )
    assert audit.status_code == 200, audit.text
    assert any(
        event["action"] == "dataset.updated"
        and event["metadata"]["fields"] == ["name"]
        for event in audit.json()
    )


def test_delete_dataset(client, auth_headers, uploaded_dataset):
    response = client.delete(
        f"/api/datasets/{uploaded_dataset['id']}", headers=auth_headers
    )
    assert response.status_code == 204
    follow = client.get(
        f"/api/datasets/{uploaded_dataset['id']}", headers=auth_headers
    )
    assert follow.status_code == 404
    audit = client.get(
        f"/api/audit?entity_type=dataset&entity_id={uploaded_dataset['id']}",
        headers=auth_headers,
    )
    assert audit.status_code == 200, audit.text
    assert any(
        event["action"] == "dataset.deleted"
        and event["metadata"]["name"] == uploaded_dataset["name"]
        for event in audit.json()
    )
