from load.export_openapi_30 import downconvert_schema, openapi_30


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_openapi_export_downconverts_to_3_0():
    schema = openapi_30()

    assert schema["openapi"] == "3.0.3"
    for item in _walk(schema):
        assert "$schema" not in item
        assert "unevaluatedProperties" not in item
        any_of = item.get("anyOf")
        if isinstance(any_of, list):
            assert {"type": "null"} not in any_of


def test_openapi_downconverter_handles_common_3_1_keywords():
    converted = downconvert_schema(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "properties": {
                "status": {"const": "ok"},
                "score": {"anyOf": [{"type": "number"}, {"type": "null"}]},
                "limit": {"exclusiveMinimum": 0, "exclusiveMaximum": 10},
            },
            "unevaluatedProperties": False,
        }
    )

    assert "$schema" not in converted
    assert "unevaluatedProperties" not in converted
    assert converted["properties"]["status"] == {"enum": ["ok"]}
    assert converted["properties"]["score"]["type"] == "number"
    assert converted["properties"]["score"]["nullable"] is True
    assert converted["properties"]["limit"]["minimum"] == 0
    assert converted["properties"]["limit"]["exclusiveMinimum"] is True
    assert converted["properties"]["limit"]["maximum"] == 10
    assert converted["properties"]["limit"]["exclusiveMaximum"] is True
