import json
from copy import deepcopy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "brand-manufacturer-evidence-review"
SKILL_ROOT = PLUGIN_ROOT / "skills" / "brand-manufacturer-evidence-review"
FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def cloned_fixture(name: str) -> dict[str, object]:
    return deepcopy(load_fixture(name))
