import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = ROOT / ".agents" / "plugins" / "marketplace.json"
EXPECTED_NAME = "brand-manufacturer-evidence-review"


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_marketplace_resolves_installable_plugin_and_skill():
    marketplace = load_json(MARKETPLACE_PATH)
    entries = [entry for entry in marketplace["plugins"] if entry["name"] == EXPECTED_NAME]

    assert len(entries) == 1
    entry = entries[0]
    assert entry["source"] == {
        "source": "local",
        "path": "./plugins/brand-manufacturer-evidence-review",
    }
    assert entry["policy"] == {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }
    assert entry["category"] == "Productivity"

    plugin_root = (ROOT / entry["source"]["path"]).resolve()
    manifest = load_json(plugin_root / ".codex-plugin" / "plugin.json")
    assert manifest["name"] == EXPECTED_NAME
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
    assert manifest["version"] == "1.0.0"

    skills_root = (plugin_root / manifest["skills"]).resolve()
    skill_root = skills_root / EXPECTED_NAME
    assert skill_root.is_dir()
    skill_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    assert f"name: {EXPECTED_NAME}" in skill_text.split("---", 2)[1]


def test_manifest_declares_only_existing_local_paths():
    marketplace = load_json(MARKETPLACE_PATH)
    plugin_root = (ROOT / marketplace["plugins"][0]["source"]["path"]).resolve()
    manifest = load_json(plugin_root / ".codex-plugin" / "plugin.json")

    for field in ("skills",):
        assert (plugin_root / manifest[field]).resolve().exists()
    for field in ("composerIcon", "logo", "logoDark"):
        if field in manifest.get("interface", {}):
            assert (plugin_root / manifest["interface"][field]).resolve().is_file()
    for screenshot in manifest.get("interface", {}).get("screenshots", []):
        assert (plugin_root / screenshot).resolve().is_file()
