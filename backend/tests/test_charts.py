import pytest


@pytest.fixture
def chart_payload(created_sheet):
    return {
        "name": "ages",
        "chart_type": "bar",
        "sheet_id": created_sheet["id"],
        "config": {"x": "name", "y": "age"},
    }


def test_create_chart(client, auth_headers, chart_payload):
    response = client.post("/api/charts", headers=auth_headers, json=chart_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "ages"
    assert data["chart_type"] == "bar"
    assert data["config"] == {"x": "name", "y": "age"}


def test_create_chart_invalid_type(client, auth_headers, chart_payload):
    chart_payload["chart_type"] = "donut"
    response = client.post("/api/charts", headers=auth_headers, json=chart_payload)
    assert response.status_code == 400


def test_create_chart_unknown_sheet(client, auth_headers):
    response = client.post(
        "/api/charts",
        headers=auth_headers,
        json={
            "name": "ghost",
            "chart_type": "line",
            "sheet_id": 99999,
            "config": {},
        },
    )
    assert response.status_code == 404


def test_list_and_filter_charts(client, auth_headers, chart_payload, created_sheet):
    chart = client.post(
        "/api/charts", headers=auth_headers, json=chart_payload
    ).json()

    all_charts = client.get("/api/charts", headers=auth_headers).json()
    assert len(all_charts) == 1
    assert all_charts[0]["id"] == chart["id"]

    by_sheet = client.get(
        f"/api/charts?sheet_id={created_sheet['id']}", headers=auth_headers
    ).json()
    assert len(by_sheet) == 1


def test_update_chart(client, auth_headers, chart_payload):
    chart = client.post(
        "/api/charts", headers=auth_headers, json=chart_payload
    ).json()
    response = client.put(
        f"/api/charts/{chart['id']}",
        headers=auth_headers,
        json={"chart_type": "line"},
    )
    assert response.status_code == 200
    assert response.json()["chart_type"] == "line"


def test_update_chart_invalid_type(client, auth_headers, chart_payload):
    chart = client.post(
        "/api/charts", headers=auth_headers, json=chart_payload
    ).json()
    response = client.put(
        f"/api/charts/{chart['id']}",
        headers=auth_headers,
        json={"chart_type": "spiral"},
    )
    assert response.status_code == 400


def test_delete_chart(client, auth_headers, chart_payload):
    chart = client.post(
        "/api/charts", headers=auth_headers, json=chart_payload
    ).json()
    response = client.delete(
        f"/api/charts/{chart['id']}", headers=auth_headers
    )
    assert response.status_code == 204
    follow = client.get(f"/api/charts/{chart['id']}", headers=auth_headers)
    assert follow.status_code == 404


def test_chart_isolation_between_users(
    client, auth_headers, second_user_headers, chart_payload
):
    chart = client.post(
        "/api/charts", headers=auth_headers, json=chart_payload
    ).json()
    response = client.get(
        f"/api/charts/{chart['id']}", headers=second_user_headers
    )
    assert response.status_code == 404
