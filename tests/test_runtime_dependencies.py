import subprocess
import sys

from tests.helpers import SKILL_ROOT


CHECKER_PATH = SKILL_ROOT / "scripts" / "check_runtime_dependencies.py"
REQUIREMENTS_PATH = SKILL_ROOT / "requirements-runtime.txt"


def test_runtime_dependency_contract_is_bundled_with_the_skill():
    assert REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines() == [
        "jsonschema>=4.26,<5",
        "python-docx>=1.2,<2",
    ]
    assert CHECKER_PATH.is_file()


def test_runtime_dependency_checker_reports_a_machine_actionable_result():
    result = subprocess.run(
        [sys.executable, str(CHECKER_PATH)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "RUNTIME_DEPENDENCIES_OK"


def test_runtime_dependency_checker_prints_install_command_when_packages_are_missing():
    result = subprocess.run(
        [sys.executable, "-S", str(CHECKER_PATH)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "RUNTIME_DEPENDENCIES_MISSING: python-docx, jsonschema" in result.stdout
    assert "python -m pip install -r" in result.stdout
    assert str(REQUIREMENTS_PATH) in result.stdout
