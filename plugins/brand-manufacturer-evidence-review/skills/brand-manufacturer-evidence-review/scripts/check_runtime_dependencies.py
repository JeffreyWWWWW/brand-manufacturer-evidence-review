from __future__ import annotations

import importlib.util
from pathlib import Path


REQUIRED_MODULES = {
    "docx": "python-docx",
    "jsonschema": "jsonschema",
}
REQUIREMENTS_PATH = Path(__file__).resolve().parents[1] / "requirements-runtime.txt"


def missing_packages() -> list[str]:
    return [
        package
        for module, package in REQUIRED_MODULES.items()
        if importlib.util.find_spec(module) is None
    ]


def main() -> int:
    missing = missing_packages()
    if missing:
        print(f"RUNTIME_DEPENDENCIES_MISSING: {', '.join(missing)}")
        print(f'INSTALL: python -m pip install -r "{REQUIREMENTS_PATH}"')
        return 1
    print("RUNTIME_DEPENDENCIES_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
