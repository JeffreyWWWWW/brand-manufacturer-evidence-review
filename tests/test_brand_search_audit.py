import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "plugins" / "brand-manufacturer-evidence-review" / "skills" / "brand-manufacturer-evidence-review"
sys.path.insert(0, str(SKILL_ROOT))

from scripts.validate_evidence_review import validate_payload


def _payload(query_paths, search_refs, records):
    return {
        "调查范围": {
            "目标品牌": [
                {"品牌ID": "BRD-001", "原始名称": "Demo", "规范名称": "Demo"}
            ],
            "代表性商品": [],
        },
        "网络检索记录": records,
        "品牌复核结果": [
            {
                "品牌": {"原始名称": "Demo", "规范名称": "Demo"},
                "实际查询路径": query_paths,
                "检索记录引用": search_refs,
                "主要来源": [],
            }
        ],
        "主张证据矩阵": [],
        "主体索引": [],
        "主体关系": [],
        "总体复核分级": [],
        "质量摘要": {"品牌": [], "总体": {}},
    }


def _record(identifier, engine):
    return {
        "检索编号": identifier,
        "检索词": "Demo official",
        "入口URL": "https://example.com/about",
        "访问时间": "2026-08-31T10:00:00+08:00",
        "访问结果": "取得候选并核验原始页面",
        "提取摘要": "Demo",
        "失败原因": "",
        "来源引擎": engine,
    }


def _codes(payload):
    return {issue.code for issue in validate_payload(payload)}


def test_rejects_tavily_query_path_without_brand_search_reference():
    payload = _payload(
        ["Tavily候选发现后回到原始页面核验"],
        [],
        [_record("WEB-001", "Tavily候选/原始页面核验")],
    )

    assert "TAVILY_QUERY_PATH_WITHOUT_REFERENCE" in _codes(payload)


def test_rejects_dangling_brand_search_reference():
    payload = _payload(
        ["品牌官网"],
        ["WEB-999"],
        [_record("WEB-001", "Browser")],
    )

    assert "MISSING_WEB_SEARCH_REFERENCE" in _codes(payload)


def test_rejects_tavily_query_path_when_referenced_search_is_not_tavily():
    payload = _payload(
        ["Tavily候选发现后回到原始页面核验"],
        ["WEB-001"],
        [_record("WEB-001", "Browser")],
    )

    assert "TAVILY_QUERY_PATH_WITHOUT_REFERENCE" in _codes(payload)


def test_accepts_tavily_query_path_with_referenced_tavily_search():
    payload = _payload(
        ["Tavily候选发现后回到原始页面核验"],
        ["WEB-001"],
        [_record("WEB-001", "Tavily候选/原始页面核验")],
    )

    assert "TAVILY_QUERY_PATH_WITHOUT_REFERENCE" not in _codes(payload)
    assert "MISSING_WEB_SEARCH_REFERENCE" not in _codes(payload)


def test_accepts_empty_search_references_when_query_path_does_not_claim_tavily():
    payload = _payload(
        ["底稿未保留品牌级WEB检索记录"],
        [],
        [_record("WEB-001", "Browser")],
    )

    assert "TAVILY_QUERY_PATH_WITHOUT_REFERENCE" not in _codes(payload)
    assert not any(
        issue.code == "SCHEMA_ERROR" and "检索记录引用" in issue.path
        for issue in validate_payload(payload)
    )
