import re
import importlib
import json
from pathlib import Path

from tests.helpers import SKILL_ROOT


ROOT = SKILL_ROOT
SKILL_PATH = ROOT / "SKILL.md"
AGENT_CONFIG_PATH = ROOT / "agents" / "openai.yaml"
RULES_PATH = ROOT / "references" / "review-rules.md"
SCHEMA_PATH = ROOT / "references" / "evidence-review.schema.json"
SCRIPT_PATHS = (
    ROOT / "scripts" / "validate_evidence_review.py",
    ROOT / "scripts" / "render_evidence_review_report.py",
)


def read_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---", 2)
    fields = {}
    for line in frontmatter.strip().splitlines():
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields, body.strip()


def read_yaml_mapping(path: Path) -> dict[str, object]:
    root: dict[str, object] = {}
    current: dict[str, str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if line.startswith("  "):
            assert current is not None
            key, value = line.strip().split(":", 1)
            current[key] = value.strip().strip('"')
            continue
        key, value = line.split(":", 1)
        if value.strip():
            root[key] = value.strip().strip('"')
            current = None
        else:
            current = {}
            root[key] = current
    return root


def markdown_section(text: str, heading: str) -> str:
    marker = f"## {heading}\n"
    start = text.index(marker) + len(marker)
    end = text.find("\n## ", start)
    return text[start:] if end == -1 else text[start:end]


def test_skill_entrypoint_declares_name_and_required_resources():
    frontmatter, body = read_frontmatter(SKILL_PATH)

    assert frontmatter["name"] == "brand-manufacturer-evidence-review"
    assert "references/review-rules.md" in body
    assert "references/evidence-review.schema.json" in body
    assert "scripts/validate_evidence_review.py" in body
    assert "scripts/render_evidence_review_report.py" in body


def test_task_resources_parse_and_scripts_import():
    for path in (RULES_PATH, SCHEMA_PATH, *SCRIPT_PATHS):
        assert path.is_file()
    assert json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))["$schema"]
    assert importlib.import_module("scripts.validate_evidence_review")
    assert importlib.import_module("scripts.render_evidence_review_report")


def test_skill_explains_why_commercial_names_require_legal_entity_evidence():
    _, body = read_frontmatter(SKILL_PATH)
    business_context = body.split("读取原始客户材料", 1)[0]

    for concept in (
        "电商页面",
        "商业品牌",
        "法律主体",
        "企业、商标、专利",
        "准确法律名称",
        "司法辖区",
        "角色",
        "当前/历史状态",
        "证据",
        "适用限制",
    ):
        assert concept in business_context


def test_skill_omits_process_disclaimers_from_user_facing_copy():
    frontmatter, body = read_frontmatter(SKILL_PATH)
    user_facing_copy = f'{frontmatter["description"]}\n{body}'

    assert "本 Skill 不" not in user_facing_copy


def test_agent_config_keeps_automatic_discovery_enabled():
    config = read_yaml_mapping(AGENT_CONFIG_PATH)

    assert config["interface"]["display_name"] == "品牌与制造商证据复核"
    assert config.get("policy", {}).get("allow_implicit_invocation") != "false"


def test_rules_keep_indirect_sources_from_proving_manufacturing_or_ownership():
    rules = markdown_section(RULES_PATH.read_text(encoding="utf-8"), "证据评估")

    assert all(source in rules for source in ("Amazon", "经销商", "搜索摘要"))
    assert "不能单独证明" in rules
    assert "商标权利人或制造商" in rules


def test_rules_keep_sku_manufacturer_empty_without_direct_product_evidence():
    rules = markdown_section(RULES_PATH.read_text(encoding="utf-8"), "主体与关系")

    assert "SKU" in rules
    assert "标签、包装、说明书、型号、SKU 或同等产品资料" in rules
    assert "制造商保持为空" in rules
    assert "适用限制" in rules


def test_rules_require_docx_to_be_derived_from_validated_json_for_reuse():
    rules = markdown_section(RULES_PATH.read_text(encoding="utf-8"), "交付与复用")

    assert "最终 JSON 通过校验后" in rules
    assert "DOCX 只能从该 JSON 生成" in rules
    assert "后续消费者必须读取已确认 JSON" in rules
    assert "而不是解析 DOCX" in rules


def test_runtime_contract_uses_neutral_names():
    contract_paths = (SKILL_PATH, AGENT_CONFIG_PATH, RULES_PATH, SCHEMA_PATH, *SCRIPT_PATHS)
    contract_text = "\n".join(path.read_text(encoding="utf-8") for path in contract_paths)
    forbidden_patterns = {
        "stage": r"\bstage(?:\b|_)",
        "intake": r"\bintake\b",
        "ready_for": r"\bready_for(?:\b|_)",
    }

    for name, pattern in forbidden_patterns.items():
        assert not re.search(pattern, contract_text, flags=re.IGNORECASE), name


def test_skill_requires_explicit_confirmation_before_final_outputs():
    _, body = read_frontmatter(SKILL_PATH)

    assert "沉默不构成确认" in body
    assert "brand-manufacturer-evidence-review.json" in body
    assert "brand-manufacturer-evidence-review.docx" in body
