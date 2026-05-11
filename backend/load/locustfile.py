"""Locust scenario for SigmaLite public-beta load checks."""
from __future__ import annotations

import io
import random
import time

from locust import HttpUser, between, task


def sample_csv(rows: int = 1000) -> bytes:
    lines = ["name,age,city,department,salary"]
    cities = ["NYC", "LA", "SF", "Austin"]
    departments = ["Engineering", "Sales", "Marketing"]
    for index in range(rows):
        lines.append(
            f"person-{index},{20 + index % 45},{cities[index % len(cities)]},"
            f"{departments[index % len(departments)]},{60000 + index % 50000}"
        )
    return "\n".join(lines).encode("utf-8")


class SigmaLiteUser(HttpUser):
    wait_time = between(1, 4)

    def on_start(self) -> None:
        suffix = f"{int(time.time() * 1000)}-{random.randint(1000, 9999)}"
        username = f"load_{suffix}"
        password = "loadpass123"
        self.client.post(
            "/api/auth/register",
            json={
                "email": f"{username}@example.com",
                "username": username,
                "password": password,
            },
        )
        login = self.client.post(
            "/api/auth/login",
            data={"username": username, "password": password},
        )
        token = login.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {token}"}

        upload = self.client.post(
            "/api/datasets",
            headers=self.headers,
            data={"name": f"load dataset {suffix}"},
            files={"file": ("load.csv", io.BytesIO(sample_csv()), "text/csv")},
        )
        self.dataset_id = upload.json()["id"]
        sheet = self.client.post(
            "/api/sheets",
            headers=self.headers,
            json={"name": "load sheet", "dataset_id": self.dataset_id},
        )
        self.sheet_id = sheet.json()["id"]

    @task(8)
    def query_page(self) -> None:
        self.client.post(
            f"/api/sheets/{self.sheet_id}/query",
            headers=self.headers,
            json={"filters": [], "logic": "and", "page": 1, "page_size": 100},
            name="/api/sheets/:id/query page",
        )

    @task(4)
    def filter_and_sort(self) -> None:
        self.client.post(
            f"/api/sheets/{self.sheet_id}/query",
            headers=self.headers,
            json={
                "filters": [{"column": "city", "operator": "eq", "value": "NYC"}],
                "logic": "and",
                "sort": {"column": "salary", "direction": "desc"},
                "page": 1,
                "page_size": 100,
            },
            name="/api/sheets/:id/query filter-sort",
        )

    @task(2)
    def aggregate(self) -> None:
        self.client.post(
            f"/api/sheets/{self.sheet_id}/aggregate",
            headers=self.headers,
            json={"column": "salary", "operation": "avg", "group_by": ["department"]},
            name="/api/sheets/:id/aggregate",
        )

    @task(1)
    def edit_comment_export(self) -> None:
        data = self.client.post(
            f"/api/sheets/{self.sheet_id}/query",
            headers=self.headers,
            json={"filters": [], "logic": "and", "page": 1, "page_size": 1},
            name="/api/sheets/:id/query edit-primer",
        ).json()
        version = data["data"][0]["__cell_versions"]["city"]
        self.client.patch(
            f"/api/sheets/{self.sheet_id}/cell",
            headers=self.headers,
            json={
                "row_index": 0,
                "column": "city",
                "value": "Boston",
                "expected_version": version,
            },
            name="/api/sheets/:id/cell",
        )
        self.client.post(
            f"/api/sheets/{self.sheet_id}/comments",
            headers=self.headers,
            json={"text": "Load test note", "row_index": 0, "column": "city"},
            name="/api/sheets/:id/comments",
        )
        self.client.post(
            f"/api/sheets/{self.sheet_id}/export",
            headers=self.headers,
            json={"format": "csv", "filters": [], "logic": "and"},
            name="/api/sheets/:id/export",
        )
