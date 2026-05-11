from app.models.user import User


def _upload_dataset_for(client, headers, name):
    response = client.post(
        "/api/datasets",
        headers=headers,
        data={"name": name, "description": "audit scope fixture"},
        files={
            "file": (
                "audit.csv",
                b"name,age,city\nAlice,30,NYC\nBob,25,LA\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_sheet(client, auth_headers, uploaded_dataset):
    response = client.post(
        "/api/sheets",
        headers={**auth_headers, "x-request-id": "sheet-create-request"},
        json={
            "name": "my sheet",
            "description": "first sheet",
            "dataset_id": uploaded_dataset["id"],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "my sheet"
    assert data["dataset_id"] == uploaded_dataset["id"]
    assert data["access_role"] == "owner"
    audit = client.get(
        f"/api/audit?entity_type=sheet&entity_id={data['id']}",
        headers=auth_headers,
    )
    assert audit.status_code == 200, audit.text
    assert any(
        event["action"] == "sheet.created"
        and event["metadata"]["dataset_id"] == uploaded_dataset["id"]
        and event["request_id"] == "sheet-create-request"
        for event in audit.json()
    )


def test_create_sheet_unknown_dataset(client, auth_headers):
    response = client.post(
        "/api/sheets",
        headers=auth_headers,
        json={"name": "ghost", "dataset_id": 99999},
    )
    assert response.status_code == 404


def test_create_sheet_other_users_dataset(
    client, second_user_headers, uploaded_dataset
):
    response = client.post(
        "/api/sheets",
        headers=second_user_headers,
        json={"name": "spy", "dataset_id": uploaded_dataset["id"]},
    )
    assert response.status_code == 404


def test_list_and_filter_sheets(
    client, auth_headers, uploaded_dataset, created_sheet
):
    all_sheets = client.get("/api/sheets", headers=auth_headers).json()
    assert len(all_sheets) == 1

    filtered = client.get(
        f"/api/sheets?dataset_id={uploaded_dataset['id']}", headers=auth_headers
    ).json()
    assert len(filtered) == 1
    assert filtered[0]["id"] == created_sheet["id"]


def test_get_sheet(client, auth_headers, created_sheet):
    response = client.get(
        f"/api/sheets/{created_sheet['id']}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["id"] == created_sheet["id"]


def test_sheet_scoped_data_query_and_aggregate_for_shared_viewer(
    client, auth_headers, second_user_headers, created_sheet
):
    share = client.post(
        f"/api/sheets/{created_sheet['id']}/shares",
        headers=auth_headers,
        json={"username_or_email": "otheruser", "role": "viewer"},
    )
    assert share.status_code == 201, share.text

    data = client.get(
        f"/api/sheets/{created_sheet['id']}/data?page=1&page_size=2",
        headers=second_user_headers,
    )
    assert data.status_code == 200, data.text
    assert data.json()["total_rows"] == 3
    assert data.json()["data"][0]["__cell_versions"]["name"] == 1

    query = client.post(
        f"/api/sheets/{created_sheet['id']}/query",
        headers=second_user_headers,
        json={
            "filters": [{"column": "age", "operator": "gte", "value": 30}],
            "logic": "and",
            "sort": {"column": "name", "direction": "desc"},
            "page": 1,
            "page_size": 5,
        },
    )
    assert query.status_code == 200, query.text
    assert [row["name"] for row in query.json()["data"]] == ["Carol", "Alice"]

    aggregate = client.post(
        f"/api/sheets/{created_sheet['id']}/aggregate",
        headers=second_user_headers,
        json={
            "column": "age",
            "operation": "sum",
            "filters": [{"column": "age", "operator": "gte", "value": 30}],
            "logic": "and",
        },
    )
    assert aggregate.status_code == 200, aggregate.text
    assert aggregate.json()["result"] == 70

    metadata = client.get(
        f"/api/datasets/{created_sheet['dataset_id']}",
        headers=second_user_headers,
    )
    assert metadata.status_code == 200, metadata.text
    assert metadata.json()["schema"]["column_count"] == 3


def test_shared_viewer_cannot_bypass_sheet_boundary_with_dataset_endpoint(
    client, auth_headers, second_user_headers, created_sheet
):
    share = client.post(
        f"/api/sheets/{created_sheet['id']}/shares",
        headers=auth_headers,
        json={"username_or_email": "otheruser", "role": "viewer"},
    )
    assert share.status_code == 201, share.text

    direct = client.post(
        f"/api/datasets/{created_sheet['dataset_id']}/query",
        headers=second_user_headers,
        json={"filters": [], "logic": "and", "page": 1, "page_size": 5},
    )
    assert direct.status_code == 404


def test_create_and_list_sheet_comments(client, auth_headers, created_sheet):
    response = client.post(
        f"/api/sheets/{created_sheet['id']}/comments",
        headers={
            **auth_headers,
            "x-request-id": "comment-create-request",
            "cf-connecting-ip": "203.0.113.20",
        },
        json={"text": "Check this cell", "row_index": 1, "column": "age"},
    )
    assert response.status_code == 201, response.text
    comment = response.json()
    assert comment["text"] == "Check this cell"
    assert comment["row_index"] == 1
    assert comment["column"] == "age"
    assert comment["username"] == "fixtureuser"

    listed = client.get(
        f"/api/sheets/{created_sheet['id']}/comments",
        headers=auth_headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == comment["id"]

    audit = client.get(
        f"/api/audit?entity_type=comment&entity_id={comment['id']}",
        headers=auth_headers,
    )
    assert audit.status_code == 200, audit.text
    assert any(
        event["action"] == "comment.created"
        and event["metadata"]["sheet_id"] == created_sheet["id"]
        and event["request_id"] == "comment-create-request"
        and event["ip_address"] is None
        for event in audit.json()
    )


def test_create_comment_broadcasts_committed_comment(
    client, auth_headers, created_sheet, monkeypatch
):
    broadcasts = []

    async def fake_broadcast(sheet_id, message, exclude=None):
        broadcasts.append((sheet_id, message, exclude))

    monkeypatch.setattr(
        "app.api.routes.sheets.websocket_manager.broadcast_to_sheet",
        fake_broadcast,
    )

    response = client.post(
        f"/api/sheets/{created_sheet['id']}/comments",
        headers=auth_headers,
        json={"text": "Check this cell", "row_index": 1, "column": "age"},
    )
    assert response.status_code == 201, response.text
    assert len(broadcasts) == 1
    sheet_id, message, exclude = broadcasts[0]
    assert sheet_id == created_sheet["id"]
    assert exclude is None
    assert message["type"] == "comment"
    assert message["id"] == response.json()["id"]
    assert message["text"] == "Check this cell"
    assert message["row_index"] == 1
    assert message["column"] == "age"


def test_sheet_cell_update_detects_conflict_and_force_overwrites(
    client, auth_headers, created_sheet
):
    data = client.get(
        f"/api/datasets/{created_sheet['dataset_id']}/data?page=1&page_size=3",
        headers=auth_headers,
    ).json()
    version = data["data"][1]["__cell_versions"]["city"]

    first = client.patch(
        f"/api/sheets/{created_sheet['id']}/cell",
        headers=auth_headers,
        json={
            "row_index": 1,
            "column": "city",
            "value": "Seattle",
            "expected_version": version,
        },
    )
    assert first.status_code == 200, first.text
    assert first.json()["version"] == version + 1

    stale = client.patch(
        f"/api/sheets/{created_sheet['id']}/cell",
        headers=auth_headers,
        json={
            "row_index": 1,
            "column": "city",
            "value": "Austin",
            "expected_version": version,
        },
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["current_value"] == "Seattle"

    forced = client.patch(
        f"/api/sheets/{created_sheet['id']}/cell",
        headers=auth_headers,
        json={
            "row_index": 1,
            "column": "city",
            "value": "Austin",
            "expected_version": first.json()["version"],
            "force": True,
        },
    )
    assert forced.status_code == 200, forced.text
    assert forced.json()["value"] == "Austin"


def test_formula_preview_supports_arithmetic_and_round(
    client, auth_headers, created_sheet
):
    response = client.post(
        f"/api/sheets/{created_sheet['id']}/formula-preview",
        headers=auth_headers,
        json={"row_index": 0, "column": "city", "value": "=ROUND(SUM(B:B)/COUNT(B:B), 1)"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["valid"] is True
    assert response.json()["value"] == 31.7


def test_formula_preview_rejects_direct_self_reference(
    client, auth_headers, created_sheet
):
    response = client.post(
        f"/api/sheets/{created_sheet['id']}/formula-preview",
        headers=auth_headers,
        json={"row_index": 0, "column": "name", "value": "=A1"},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert "own cell" in response.json()["error"]


def test_formula_preview_rejects_self_reference_inside_ranges(
    client, auth_headers, created_sheet
):
    response = client.post(
        f"/api/sheets/{created_sheet['id']}/formula-preview",
        headers=auth_headers,
        json={"row_index": 0, "column": "age", "value": "=SUM(B:B)"},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert "own cell" in response.json()["error"]


def test_persisted_formula_rejects_circular_references(
    client, auth_headers, created_sheet
):
    first = client.patch(
        f"/api/sheets/{created_sheet['id']}/cell",
        headers=auth_headers,
        json={"row_index": 0, "column": "city", "value": "=B2", "expected_version": 1},
    )
    assert first.status_code == 200, first.text

    circular = client.patch(
        f"/api/sheets/{created_sheet['id']}/cell",
        headers=auth_headers,
        json={"row_index": 1, "column": "age", "value": "=C1", "expected_version": 1},
    )
    assert circular.status_code == 400
    assert "circular" in circular.json()["detail"]


def test_sheet_exports_full_dataset_formats(client, auth_headers, created_sheet):
    for fmt, signature in [
        ("csv", b"name,age,city"),
        ("xlsx", b"PK"),
        ("pdf", b"%PDF"),
    ]:
        response = client.post(
            f"/api/sheets/{created_sheet['id']}/export",
            headers=auth_headers,
            json={"format": fmt, "filters": [], "logic": "and"},
        )
        assert response.status_code == 200, response.text
        assert response.content.startswith(signature)


def test_pdf_export_includes_report_context(client, auth_headers, created_sheet):
    comment = client.post(
        f"/api/sheets/{created_sheet['id']}/comments",
        headers=auth_headers,
        json={"text": "Review age outlier", "row_index": 2, "column": "age"},
    )
    assert comment.status_code == 201, comment.text
    chart = client.post(
        "/api/charts",
        headers=auth_headers,
        json={
            "name": "ages",
            "chart_type": "bar",
            "sheet_id": created_sheet["id"],
            "config": {"x_axis": "name", "y_axis": "age"},
        },
    )
    assert chart.status_code == 201, chart.text

    response = client.post(
        f"/api/sheets/{created_sheet['id']}/export",
        headers=auth_headers,
        json={
            "format": "pdf",
            "filters": [{"column": "age", "operator": "gte", "value": 30}],
            "logic": "and",
            "include_comments": True,
            "include_charts": True,
        },
    )
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")
    assert b"Schema:" in response.content
    assert b"Filters:" in response.content
    assert b"Review age outlier" in response.content
    assert b"ages" in response.content


def test_export_rate_limit_blocks_and_audits_request(
    client, auth_headers, created_sheet
):
    for _ in range(10):
        response = client.post(
            f"/api/sheets/{created_sheet['id']}/export",
            headers=auth_headers,
            json={"format": "csv", "filters": [], "logic": "and"},
        )
        assert response.status_code == 200, response.text

    blocked = client.post(
        f"/api/sheets/{created_sheet['id']}/export",
        headers=auth_headers,
        json={"format": "csv", "filters": [], "logic": "and"},
    )
    assert blocked.status_code == 429

    audit = client.get("/api/audit?entity_type=request", headers=auth_headers)
    assert audit.status_code == 200, audit.text
    assert any(
        event["action"] == "rate_limit.blocked"
        and event["metadata"]["scope"] == "export"
        and event["metadata"]["path"] == f"/api/sheets/{created_sheet['id']}/export"
        and event["metadata"]["limit"] == 10
        for event in audit.json()
    )


def test_export_rate_limit_is_per_authenticated_user(
    client, auth_headers, second_user_headers, created_sheet
):
    share = client.post(
        f"/api/sheets/{created_sheet['id']}/shares",
        headers=auth_headers,
        json={"username_or_email": "otheruser", "role": "viewer"},
    )
    assert share.status_code == 201, share.text

    for _ in range(10):
        response = client.post(
            f"/api/sheets/{created_sheet['id']}/export",
            headers=auth_headers,
            json={"format": "csv", "filters": [], "logic": "and"},
        )
        assert response.status_code == 200, response.text

    owner_blocked = client.post(
        f"/api/sheets/{created_sheet['id']}/export",
        headers=auth_headers,
        json={"format": "csv", "filters": [], "logic": "and"},
    )
    assert owner_blocked.status_code == 429

    collaborator_allowed = client.post(
        f"/api/sheets/{created_sheet['id']}/export",
        headers=second_user_headers,
        json={"format": "csv", "filters": [], "logic": "and"},
    )
    assert collaborator_allowed.status_code == 200, collaborator_allowed.text


def test_sheet_sharing_roles_gate_write_access(
    client, auth_headers, second_user_headers, created_sheet
):
    viewer = client.post(
        f"/api/sheets/{created_sheet['id']}/shares",
        headers=auth_headers,
        json={"username_or_email": "otheruser", "role": "viewer"},
    )
    assert viewer.status_code == 201, viewer.text
    assert viewer.json()["role"] == "viewer"

    shared_sheet = client.get(
        f"/api/sheets/{created_sheet['id']}",
        headers=second_user_headers,
    )
    assert shared_sheet.status_code == 200
    assert shared_sheet.json()["access_role"] == "viewer"

    share_list = client.get(
        f"/api/sheets/{created_sheet['id']}/shares",
        headers=second_user_headers,
    )
    assert share_list.status_code == 403

    denied = client.patch(
        f"/api/sheets/{created_sheet['id']}/cell",
        headers=second_user_headers,
        json={"row_index": 0, "column": "city", "value": "Boston", "expected_version": 1},
    )
    assert denied.status_code == 403

    editor = client.post(
        f"/api/sheets/{created_sheet['id']}/shares",
        headers=auth_headers,
        json={"username_or_email": "otheruser", "role": "editor"},
    )
    assert editor.status_code == 201
    assert editor.json()["role"] == "editor"

    allowed = client.patch(
        f"/api/sheets/{created_sheet['id']}/cell",
        headers=second_user_headers,
        json={"row_index": 0, "column": "city", "value": "Boston", "expected_version": 1},
    )
    assert allowed.status_code == 200, allowed.text


def test_deleted_share_revokes_rest_export_and_websocket_ticket_access(
    client, auth_headers, second_user_headers, created_sheet
):
    share = client.post(
        f"/api/sheets/{created_sheet['id']}/shares",
        headers=auth_headers,
        json={"username_or_email": "otheruser", "role": "viewer"},
    )
    assert share.status_code == 201, share.text

    assert client.get(
        f"/api/sheets/{created_sheet['id']}",
        headers=second_user_headers,
    ).status_code == 200

    delete = client.delete(
        f"/api/sheets/{created_sheet['id']}/shares/{share.json()['id']}",
        headers=auth_headers,
    )
    assert delete.status_code == 204, delete.text

    assert client.get(
        f"/api/sheets/{created_sheet['id']}",
        headers=second_user_headers,
    ).status_code == 404
    assert client.post(
        f"/api/sheets/{created_sheet['id']}/query",
        headers=second_user_headers,
        json={"filters": [], "logic": "and", "page": 1, "page_size": 5},
    ).status_code == 404
    assert client.post(
        f"/api/sheets/{created_sheet['id']}/export",
        headers=second_user_headers,
        json={"format": "csv", "filters": [], "logic": "and"},
    ).status_code == 404
    assert client.post(
        f"/api/sheets/{created_sheet['id']}/ws-ticket",
        headers=second_user_headers,
    ).status_code == 404


def test_share_audit_events_include_request_metadata(
    client, auth_headers, second_user_headers, created_sheet
):
    share = client.post(
        f"/api/sheets/{created_sheet['id']}/shares",
        headers={
            **auth_headers,
            "x-request-id": "share-upsert-request",
            "cf-connecting-ip": "203.0.113.10",
        },
        json={"username_or_email": "otheruser", "role": "viewer"},
    )
    assert share.status_code == 201, share.text

    delete = client.delete(
        f"/api/sheets/{created_sheet['id']}/shares/{share.json()['id']}",
        headers={
            **auth_headers,
            "x-request-id": "share-delete-request",
            "cf-connecting-ip": "203.0.113.11",
        },
    )
    assert delete.status_code == 204, delete.text

    audit = client.get(
        f"/api/audit?entity_type=sheet&entity_id={created_sheet['id']}",
        headers=auth_headers,
    )
    assert audit.status_code == 200, audit.text
    by_action = {event["action"]: event for event in audit.json()}
    assert by_action["share.upserted"]["request_id"] == "share-upsert-request"
    assert by_action["share.upserted"]["ip_address"] is None
    assert by_action["share.deleted"]["request_id"] == "share-delete-request"
    assert by_action["share.deleted"]["ip_address"] is None


def test_sheet_owner_can_filter_collaborator_audit_events(
    client, auth_headers, second_user_headers, created_sheet
):
    share = client.post(
        f"/api/sheets/{created_sheet['id']}/shares",
        headers=auth_headers,
        json={"username_or_email": "otheruser", "role": "editor"},
    )
    assert share.status_code == 201, share.text

    collaborator = client.get("/api/auth/me", headers=second_user_headers).json()
    update = client.patch(
        f"/api/sheets/{created_sheet['id']}/cell",
        headers=second_user_headers,
        json={"row_index": 0, "column": "city", "value": "Boston", "expected_version": 1},
    )
    assert update.status_code == 200, update.text

    owner_view = client.get(
        (
            f"/api/audit?entity_type=sheet&entity_id={created_sheet['id']}"
            f"&actor_id={collaborator['id']}"
        ),
        headers=auth_headers,
    )
    assert owner_view.status_code == 200, owner_view.text
    assert any(
        event["action"] == "cell.updated"
        and event["actor_id"] == collaborator["id"]
        and event["metadata"]["column"] == "city"
        for event in owner_view.json()
    )

    collaborator_view = client.get(
        f"/api/audit?entity_type=sheet&entity_id={created_sheet['id']}",
        headers=second_user_headers,
    )
    assert collaborator_view.status_code == 200, collaborator_view.text
    assert all(event["actor_id"] == collaborator["id"] for event in collaborator_view.json())


def test_sheet_cell_update_broadcasts_committed_update(
    client, auth_headers, created_sheet, monkeypatch
):
    broadcasts = []

    async def fake_broadcast(sheet_id, message, exclude=None):
        broadcasts.append((sheet_id, message, exclude))

    monkeypatch.setattr(
        "app.api.routes.sheets.websocket_manager.broadcast_to_sheet",
        fake_broadcast,
    )

    response = client.patch(
        f"/api/sheets/{created_sheet['id']}/cell",
        headers=auth_headers,
        json={"row_index": 0, "column": "city", "value": "Boston", "expected_version": 1},
    )
    assert response.status_code == 200, response.text
    assert len(broadcasts) == 1
    sheet_id, message, exclude = broadcasts[0]
    assert sheet_id == created_sheet["id"]
    assert exclude is None
    assert message["type"] == "cell_update"
    assert message["row_index"] == 0
    assert message["column"] == "city"
    assert message["value"] == "Boston"
    assert message["version"] == response.json()["version"]


def test_audit_endpoint_returns_current_users_events(client, auth_headers, created_sheet):
    client.post(
        f"/api/sheets/{created_sheet['id']}/export",
        headers=auth_headers,
        json={"format": "csv", "filters": [], "logic": "and"},
    )
    response = client.get("/api/audit", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert any(event["action"] == "sheet.exported" for event in response.json())


def test_superuser_can_filter_audit_events_by_actor(
    client, auth_headers, second_user_headers, db_session
):
    admin = client.get("/api/auth/me", headers=auth_headers).json()
    admin_record = db_session.query(User).filter(User.id == admin["id"]).one()
    admin_record.is_superuser = True
    db_session.commit()

    collaborator = client.get("/api/auth/me", headers=second_user_headers).json()
    dataset = _upload_dataset_for(client, second_user_headers, "collaborator data")

    response = client.get(
        f"/api/audit?actor_id={collaborator['id']}&entity_type=dataset",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    events = response.json()
    assert events
    assert all(event["actor_id"] == collaborator["id"] for event in events)
    assert any(
        event["action"] == "dataset.uploaded"
        and event["entity_id"] == dataset["id"]
        for event in events
    )


def test_regular_user_actor_filter_does_not_leak_unrelated_audit_events(
    client, auth_headers, second_user_headers
):
    collaborator = client.get("/api/auth/me", headers=second_user_headers).json()
    _upload_dataset_for(client, second_user_headers, "private collaborator data")

    response = client.get(
        f"/api/audit?actor_id={collaborator['id']}&entity_type=dataset",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json() == []


def test_comment_isolation_between_users(
    client, auth_headers, second_user_headers, created_sheet
):
    create = client.post(
        f"/api/sheets/{created_sheet['id']}/comments",
        headers=auth_headers,
        json={"text": "private"},
    )
    assert create.status_code == 201

    response = client.get(
        f"/api/sheets/{created_sheet['id']}/comments",
        headers=second_user_headers,
    )
    assert response.status_code == 404


def test_create_comment_rejects_blank_text(client, auth_headers, created_sheet):
    response = client.post(
        f"/api/sheets/{created_sheet['id']}/comments",
        headers=auth_headers,
        json={"text": ""},
    )
    assert response.status_code == 422


def test_create_comment_rejects_unknown_column(client, auth_headers, created_sheet):
    response = client.post(
        f"/api/sheets/{created_sheet['id']}/comments",
        headers=auth_headers,
        json={"text": "bad anchor", "row_index": 1, "column": "missing"},
    )
    assert response.status_code == 400
    assert "Column 'missing' not found" in response.json()["detail"]


def test_create_comment_rejects_row_outside_dataset(client, auth_headers, created_sheet):
    response = client.post(
        f"/api/sheets/{created_sheet['id']}/comments",
        headers=auth_headers,
        json={"text": "bad row", "row_index": 99, "column": "age"},
    )
    assert response.status_code == 400
    assert "outside the dataset" in response.json()["detail"]


def test_update_sheet(client, auth_headers, created_sheet):
    response = client.put(
        f"/api/sheets/{created_sheet['id']}",
        headers=auth_headers,
        json={"name": "renamed", "config": {"sortBy": "age"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "renamed"
    assert body["config"] == {"sortBy": "age"}
    audit = client.get(
        f"/api/audit?entity_type=sheet&entity_id={created_sheet['id']}",
        headers=auth_headers,
    )
    assert audit.status_code == 200, audit.text
    assert any(
        event["action"] == "sheet.updated"
        and event["metadata"]["fields"] == ["config", "name"]
        for event in audit.json()
    )


def test_delete_sheet(client, auth_headers, created_sheet):
    response = client.delete(
        f"/api/sheets/{created_sheet['id']}", headers=auth_headers
    )
    assert response.status_code == 204
    follow = client.get(
        f"/api/sheets/{created_sheet['id']}", headers=auth_headers
    )
    assert follow.status_code == 404
    audit = client.get(
        f"/api/audit?entity_type=sheet&entity_id={created_sheet['id']}",
        headers=auth_headers,
    )
    assert audit.status_code == 200, audit.text
    assert any(
        event["action"] == "sheet.deleted"
        and event["metadata"]["name"] == created_sheet["name"]
        for event in audit.json()
    )


def test_sheet_isolation_between_users(
    client, second_user_headers, created_sheet
):
    response = client.get(
        f"/api/sheets/{created_sheet['id']}", headers=second_user_headers
    )
    assert response.status_code == 404
