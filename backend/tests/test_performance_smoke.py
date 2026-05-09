def test_10k_row_product_smoke(client, auth_headers):
    rows = ["name,age,city"]
    for index in range(10_000):
        city = "NYC" if index % 2 == 0 else "LA"
        rows.append(f"person-{index},{index % 100},{city}")

    upload = client.post(
        "/api/datasets",
        headers=auth_headers,
        data={"name": "10k smoke"},
        files={"file": ("large.csv", "\n".join(rows).encode(), "text/csv")},
    )
    assert upload.status_code == 201, upload.text
    dataset = upload.json()
    assert dataset["row_count"] == 10_000

    page = client.get(
        f"/api/datasets/{dataset['id']}/data?page=2&page_size=100",
        headers=auth_headers,
    )
    assert page.status_code == 200
    assert len(page.json()["data"]) == 100

    filtered = client.post(
        f"/api/datasets/{dataset['id']}/filter",
        headers=auth_headers,
        json={
            "filters": [{"column": "city", "operator": "eq", "value": "NYC"}],
            "logic": "and",
            "page": 1,
            "page_size": 100,
        },
    )
    assert filtered.status_code == 200
    assert filtered.json()["total_rows"] == 5_000

    aggregate = client.post(
        f"/api/datasets/{dataset['id']}/aggregate",
        headers=auth_headers,
        json={"column": "age", "operation": "count"},
    )
    assert aggregate.status_code == 200
    assert aggregate.json()["result"] == 10_000

    sheet = client.post(
        "/api/sheets",
        headers=auth_headers,
        json={"name": "10k sheet", "dataset_id": dataset["id"]},
    )
    assert sheet.status_code == 201

    chart = client.post(
        "/api/charts",
        headers=auth_headers,
        json={
            "name": "10k chart",
            "chart_type": "bar",
            "sheet_id": sheet.json()["id"],
            "config": {"x_axis": "city", "y_axis": "age"},
        },
    )
    assert chart.status_code == 201
