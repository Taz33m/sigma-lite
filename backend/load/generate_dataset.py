"""Generate deterministic CSVs for SigmaLite load tests."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def write_dataset(rows: int, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    departments = ["Engineering", "Sales", "Marketing", "Finance", "Support"]
    cities = ["New York", "San Francisco", "Chicago", "Boston", "Austin"]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["employee_id", "name", "department", "city", "age", "salary", "score"])
        for index in range(rows):
            writer.writerow(
                [
                    index + 1,
                    f"person-{index}",
                    departments[index % len(departments)],
                    cities[index % len(cities)],
                    22 + (index % 43),
                    55000 + (index % 90000),
                    round((index % 1000) / 10, 1),
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, required=True, choices=[10_000, 50_000, 100_000, 250_000])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_dataset(args.rows, args.output)
    print(f"Wrote {args.rows} rows to {args.output}")


if __name__ == "__main__":
    main()
