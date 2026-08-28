import json
from copy import deepcopy
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def cloned_fixture(name: str) -> dict[str, object]:
    return deepcopy(load_fixture(name))
