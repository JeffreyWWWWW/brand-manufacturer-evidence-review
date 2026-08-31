import sys
import json
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "plugins" / "brand-manufacturer-evidence-review" / "skills" / "brand-manufacturer-evidence-review"
sys.path.insert(0, str(SKILL_ROOT))
STYLE_PATH = ROOT / "plugins" / "brand-manufacturer-evidence-review" / "skills" / "brand-manufacturer-evidence-review" / "assets" / "report-style" / "business-report-style.json"
MANIFEST_PATH = ROOT / "plugins" / "brand-manufacturer-evidence-review" / ".codex-plugin" / "plugin.json"

from scripts.render_evidence_review_report import _load_tokens, add_report_note


def test_report_note_contains_skill_and_schema_versions():
    document = Document()
    tokens = _load_tokens(STYLE_PATH)
    skill_version = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["version"]
    payload = {"Skill版本": skill_version, "规范版本": "2026-08-01", "用户确认": {}}

    add_report_note(document, payload, tokens)

    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert f"Skill版本：{skill_version}" in text
    assert "规范版本：2026-08-01" in text
