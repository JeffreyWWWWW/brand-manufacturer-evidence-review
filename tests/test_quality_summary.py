import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "plugins" / "brand-manufacturer-evidence-review" / "skills" / "brand-manufacturer-evidence-review"
sys.path.insert(0, str(SKILL_ROOT))

from scripts.quality_summary import build_quality_summary
from scripts.validate_evidence_review import validate_payload


def test_quality_summary_reports_sources_roles_sku_gaps_and_followups():
    payload = {
        "调查范围": {
            "目标品牌": [{"品牌ID": "BRD-001", "原始名称": "Demo", "规范名称": "Demo"}],
            "代表性商品": [
                {"商品ID": "PRD-001", "SKU证据核验": {"证据完整度": "1/7"}},
            ],
        },
        "品牌复核结果": [
            {
                "品牌": {"原始名称": "Demo", "规范名称": "Demo"},
                "主要来源": [
                    {"证据编号": "EVD-001", "URL": "https://brand.example/about"},
                    {"证据编号": "EVD-002", "URL": "https://registry.example/record"},
                ],
                "主体关系": {"商标权利人": [{"结论状态": "已确认"}], "品牌运营主体": []},
                "制造关系": {"品牌层面主要制造商": [], "具体SKU制造商": []},
                "结论评价": {"人工复核建议": "补充包装标签"},
                "关键说明": ["存在冲突：名称待核实"],
            }
        ],
        "主张证据矩阵": [{"结论状态": "候选", "下一步补证": "补充登记记录"}],
    }

    summary = build_quality_summary(payload)

    assert summary["品牌"][0] == {
        "品牌ID": "BRD-001",
        "主要来源数": 2,
        "独立来源域名数": 2,
        "关键角色覆盖": ["商标权利人"],
        "SKU证据完整度": [{"商品ID": "PRD-001", "证据完整度": "1/7"}],
        "冲突数": 1,
        "待补证数": 2,
    }
    assert summary["总体"] == {"品牌数量": 1, "冲突数": 1, "待补证数": 2}


def test_validator_rejects_stale_quality_summary():
    payload = {
        "调查范围": {"目标品牌": [], "代表性商品": []},
        "品牌复核结果": [],
        "主张证据矩阵": [],
        "质量摘要": {"品牌": [], "总体": {"品牌数量": 99, "冲突数": 0, "待补证数": 0}},
    }

    issues = validate_payload(payload)

    assert any(issue.code == "QUALITY_SUMMARY_MISMATCH" for issue in issues)
