"""Export a Cloudflare API Shield-friendly OpenAPI 3.0 schema.

FastAPI currently emits OpenAPI 3.1 for this app. Cloudflare API Shield schema
validation expects OpenAPI 3.0, so this script performs a conservative
down-conversion for the schema shapes SigmaLite emits.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///./openapi_export.db")
os.environ.setdefault("SECRET_KEY", "openapi-export-secret-not-for-production")
os.environ.setdefault("ENVIRONMENT", "test")

from app.main import app  # noqa: E402


def _convert_nullable_anyof(value: dict[str, Any]) -> dict[str, Any]:
    any_of = value.get("anyOf")
    if not isinstance(any_of, list) or len(any_of) != 2:
        return value

    non_null = [item for item in any_of if item != {"type": "null"}]
    if len(non_null) != 1:
        return value

    converted = dict(non_null[0])
    converted["nullable"] = True
    for key, item in value.items():
        if key != "anyOf":
            converted.setdefault(key, item)
    return converted


def downconvert_schema(value: Any) -> Any:
    """Recursively down-convert common OpenAPI 3.1 JSON Schema constructs."""
    if isinstance(value, list):
        return [downconvert_schema(item) for item in value]

    if not isinstance(value, dict):
        return value

    value = _convert_nullable_anyof(value)
    converted = {
        key: downconvert_schema(item)
        for key, item in value.items()
        if key not in {"$schema", "unevaluatedProperties"}
    }

    const = converted.pop("const", None)
    if const is not None and "enum" not in converted:
        converted["enum"] = [const]

    exclusive_minimum = converted.get("exclusiveMinimum")
    if isinstance(exclusive_minimum, (int, float)):
        converted["minimum"] = exclusive_minimum
        converted["exclusiveMinimum"] = True

    exclusive_maximum = converted.get("exclusiveMaximum")
    if isinstance(exclusive_maximum, (int, float)):
        converted["maximum"] = exclusive_maximum
        converted["exclusiveMaximum"] = True

    return converted


def openapi_30() -> dict[str, Any]:
    schema = downconvert_schema(app.openapi())
    schema["openapi"] = "3.0.3"
    return schema


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    rendered = json.dumps(openapi_30(), indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote OpenAPI 3.0 schema to {args.output}")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
