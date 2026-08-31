import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "plugins" / "brand-manufacturer-evidence-review" / "skills" / "brand-manufacturer-evidence-review" / "references" / "evidence-review.schema.json"


def test_schema_requires_skill_version_field():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert "Skill版本" in schema["required"]
    assert schema["properties"]["Skill版本"] == {"$ref": "#/$defs/freeText"}


def test_schema_rejects_payload_without_skill_version():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors({}))
    assert any("Skill版本" in error.message for error in errors)
