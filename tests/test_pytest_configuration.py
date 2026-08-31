from configparser import ConfigParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pytest_only_collects_the_maintained_test_suite():
    config = ConfigParser()
    config.read(ROOT / "pytest.ini", encoding="utf-8")

    assert config["pytest"]["testpaths"].split() == ["tests"]
