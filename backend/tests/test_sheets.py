def test_create_sheet(client, auth_headers, uploaded_dataset):
    response = client.post(
        "/api/sheets",
        headers=auth_headers,
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


def test_create_and_list_sheet_comments(client, auth_headers, created_sheet):
    response = client.post(
        f"/api/sheets/{created_sheet['id']}/comments",
        headers=auth_headers,
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


def test_delete_sheet(client, auth_headers, created_sheet):
    response = client.delete(
        f"/api/sheets/{created_sheet['id']}", headers=auth_headers
    )
    assert response.status_code == 204
    follow = client.get(
        f"/api/sheets/{created_sheet['id']}", headers=auth_headers
    )
    assert follow.status_code == 404


def test_sheet_isolation_between_users(
    client, second_user_headers, created_sheet
):
    response = client.get(
        f"/api/sheets/{created_sheet['id']}", headers=second_user_headers
    )
    assert response.status_code == 404
