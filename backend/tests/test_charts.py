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


def test_shared_editor_can_create_chart_and_owner_can_audit(
    client, auth_headers, second_user_headers, created_sheet
):
    share = client.post(
        f"/api/sheets/{created_sheet['id']}/shares",
        headers=auth_headers,
        json={"username_or_email": "otheruser", "role": "editor"},
    )
    assert share.status_code == 201, share.text
    collaborator = client.get("/api/auth/me", headers=second_user_headers).json()

    created = client.post(
        "/api/charts",
        headers={
            **second_user_headers,
            "x-request-id": "chart-create-request",
            "cf-connecting-ip": "203.0.113.30",
        },
        json={
            "name": "shared ages",
            "chart_type": "bar",
            "sheet_id": created_sheet["id"],
            "config": {"x_axis": "name", "y_axis": "age"},
        },
    )
    assert created.status_code == 201, created.text
    chart = created.json()

    listed_by_owner = client.get(
        f"/api/charts?sheet_id={created_sheet['id']}",
        headers=auth_headers,
    )
    assert listed_by_owner.status_code == 200, listed_by_owner.text
    assert any(item["id"] == chart["id"] for item in listed_by_owner.json())

    all_for_collaborator = client.get("/api/charts", headers=second_user_headers)
    assert all_for_collaborator.status_code == 200, all_for_collaborator.text
    assert any(item["id"] == chart["id"] for item in all_for_collaborator.json())

    audit = client.get(
        f"/api/audit?actor_id={collaborator['id']}&entity_type=chart",
        headers=auth_headers,
    )
    assert audit.status_code == 200, audit.text
    assert any(
        event["action"] == "chart.created"
        and event["entity_id"] == chart["id"]
        and event["metadata"]["sheet_id"] == created_sheet["id"]
        and event["request_id"] == "chart-create-request"
        and event["ip_address"] is None
        for event in audit.json()
    )


def test_shared_viewer_can_read_but_not_write_charts(
    client, auth_headers, second_user_headers, chart_payload, created_sheet
):
    chart = client.post("/api/charts", headers=auth_headers, json=chart_payload).json()
    share = client.post(
        f"/api/sheets/{created_sheet['id']}/shares",
        headers=auth_headers,
        json={"username_or_email": "otheruser", "role": "viewer"},
    )
    assert share.status_code == 201, share.text

    read = client.get(f"/api/charts/{chart['id']}", headers=second_user_headers)
    assert read.status_code == 200, read.text

    create = client.post(
        "/api/charts",
        headers=second_user_headers,
        json={
            "name": "denied",
            "chart_type": "bar",
            "sheet_id": created_sheet["id"],
            "config": {},
        },
    )
    assert create.status_code == 403

    update = client.put(
        f"/api/charts/{chart['id']}",
        headers=second_user_headers,
        json={"name": "denied"},
    )
    assert update.status_code == 403

    delete = client.delete(f"/api/charts/{chart['id']}", headers=second_user_headers)
    assert delete.status_code == 403
