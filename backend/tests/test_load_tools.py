import csv

from load.benchmark_dataset import evaluate_public_beta_targets
from load.generate_dataset import write_dataset


def test_generate_dataset_writes_deterministic_rows(tmp_path):
    output = tmp_path / "sample.csv"

    write_dataset(3, output)

    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows == [
        ["employee_id", "name", "department", "city", "age", "salary", "score"],
        ["1", "person-0", "Engineering", "New York", "22", "55000", "0.0"],
        ["2", "person-1", "Sales", "San Francisco", "23", "55001", "0.1"],
        ["3", "person-2", "Marketing", "Chicago", "24", "55002", "0.2"],
    ]


def test_public_beta_target_evaluation_flags_misses():
    checks = evaluate_public_beta_targets(
        {
            "page_query_seconds": 0.25,
            "filter_sort_seconds": 2.5,
            "aggregate_seconds": 1.0,
        }
    )

    by_operation = {check["operation"]: check for check in checks}
    assert by_operation["page_query_seconds"]["ok"] is True
    assert by_operation["filter_sort_seconds"]["ok"] is False
    assert by_operation["filter_sort_seconds"]["target_seconds"] == 1.5
    assert by_operation["aggregate_seconds"]["ok"] is True
