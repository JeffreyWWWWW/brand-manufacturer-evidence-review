import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.validate_evidence_review import (
    ValidationIssue,
    assert_valid_payload,
    compute_content_hash,
    validate_payload,
)
from tests.helpers import SKILL_ROOT, cloned_fixture


def test_valid_draft_has_no_issues():
    assert validate_payload(cloned_fixture("minimal-valid-review.json")) == []


def test_validation_issue_is_orderable_value_object():
    assert ValidationIssue("/a", "CODE", "message") < ValidationIssue("/b", "CODE", "message")


def test_assert_valid_payload_accepts_valid_draft():
    assert assert_valid_payload(cloned_fixture("minimal-valid-review.json")) is None


def test_content_hash_is_sha256_prefixed():
    assert compute_content_hash(cloned_fixture("minimal-valid-review.json")).startswith("sha256:")


def codes(payload, **kwargs):
    return {issue.code for issue in validate_payload(payload, **kwargs)}


def test_shared_entity_fixture_has_no_issues():
    assert validate_payload(cloned_fixture("shared-entity-review.json")) == []


@pytest.mark.parametrize(
    ("collection_path", "id_key", "code"),
    (
        (("输入材料",), "来源编号", "DUPLICATE_SOURCE_ID"),
        (("调查范围", "目标品牌"), "品牌ID", "DUPLICATE_BRAND_ID"),
        (("调查范围", "代表性商品"), "商品ID", "DUPLICATE_PRODUCT_ID"),
        (("品牌复核结果", 0, "主要来源"), "证据编号", "DUPLICATE_EVIDENCE_ID"),
        (("主体索引",), "主体ID", "DUPLICATE_ENTITY_ID"),
        (("主体关系",), "关系ID", "DUPLICATE_RELATIONSHIP_ID"),
    ),
)
def test_rejects_duplicate_ids_within_each_namespace(collection_path, id_key, code):
    payload = cloned_fixture("minimal-valid-review.json")
    collection = payload
    for key in collection_path:
        collection = collection[key]
    collection.append(dict(collection[0]))
    assert code in codes(payload)


def test_ids_in_different_namespaces_do_not_conflict():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["输入材料"][0]["来源编号"] = "SRC-001"
    assert validate_payload(payload) == []


def test_rejects_missing_and_duplicate_brand_reviews():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["品牌复核结果"] = []
    assert "BRAND_REVIEW_COVERAGE" in codes(payload)

    payload = cloned_fixture("minimal-valid-review.json")
    payload["品牌复核结果"].append(dict(payload["品牌复核结果"][0]))
    assert "BRAND_REVIEW_COVERAGE" in codes(payload)


def test_rejects_brand_review_outside_investigation_scope():
    payload = cloned_fixture("minimal-valid-review.json")
    extra = dict(payload["品牌复核结果"][0])
    extra["品牌"] = {"原始名称": "范围外品牌", "规范名称": "范围外品牌"}
    extra["主体关系"] = {
        "商标权利人": [],
        "品牌运营主体": [],
        "母公司": [],
        "收购与历史关系": [],
    }
    extra["制造关系"] = {
        "品牌层面主要制造商": [],
        "具体SKU制造商": [],
        "制造模式": "未知",
        "SKU适用限制": [],
    }
    extra["主要来源"] = []
    payload["品牌复核结果"].append(extra)
    assert "OUT_OF_SCOPE_BRAND_REVIEW" in codes(payload)


def test_rejects_empty_query_path():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["品牌复核结果"][0]["实际查询路径"] = []
    assert "EMPTY_QUERY_PATH" in codes(payload)


def test_rejects_dangling_and_wrong_type_relationship_endpoints():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["主体关系"][0]["终点ID"] = "ENT-999"
    assert "DANGLING_RELATIONSHIP_ENDPOINT" in codes(payload)

    payload = cloned_fixture("minimal-valid-review.json")
    payload["主体关系"][0]["终点类型"] = "品牌"
    assert "RELATIONSHIP_ENDPOINT_TYPE_MISMATCH" in codes(payload)


def test_rejects_missing_or_input_source_evidence_references():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["主体关系"][0]["证据引用"] = ["EVD-999"]
    assert "MISSING_EVIDENCE_REFERENCE" in codes(payload)

    payload = cloned_fixture("minimal-valid-review.json")
    payload["主体关系"][0]["证据引用"] = ["SRC-001"]
    assert "SOURCE_USED_AS_EVIDENCE" in codes(payload)


def test_rejects_scope_level_missing_or_input_source_evidence_references():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["调查范围"]["目标品牌"][0]["证据引用"] = ["SRC-001"]
    payload["调查范围"]["代表性商品"][0]["证据引用"] = ["EVD-999"]
    assert {"SOURCE_USED_AS_EVIDENCE", "MISSING_EVIDENCE_REFERENCE"} <= codes(payload)


def test_requires_evidence_to_belong_to_corresponding_brand_review():
    payload = cloned_fixture("shared-entity-review.json")
    payload["主体关系"][0]["证据引用"] = ["EVD-002"]
    assert "CROSS_BRAND_EVIDENCE_REFERENCE" in codes(payload)


def test_rejects_entity_brand_and_role_view_mismatches():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["主体索引"][0]["关联品牌"] = []
    assert "ENTITY_BRAND_VIEW_MISMATCH" in codes(payload)

    payload = cloned_fixture("minimal-valid-review.json")
    payload["主体索引"][0]["主体角色"] = ["品牌运营主体"]
    assert "ENTITY_ROLE_VIEW_MISMATCH" in codes(payload)

    payload = cloned_fixture("minimal-valid-review.json")
    payload["主体关系"][0]["关系类型"] = "品牌运营主体"
    assert "NESTED_RELATIONSHIP_VIEW_MISMATCH" in codes(payload)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    (
        ("当前状态", "历史", "ENTITY_CURRENT_STATUS_MISMATCH"),
        ("结论状态", "存在冲突", "ENTITY_CONCLUSION_STATUS_MISMATCH"),
        ("可靠性等级", "低", "ENTITY_RELIABILITY_MISMATCH"),
        ("证据引用", [], "ENTITY_EVIDENCE_COVERAGE_MISMATCH"),
    ),
)
def test_rejects_entity_summary_that_conflicts_with_relationships(field, value, code):
    payload = cloned_fixture("minimal-valid-review.json")
    payload["主体索引"][0][field] = value
    assert code in codes(payload)


def test_entity_summary_uses_most_conservative_relationship_values():
    payload = cloned_fixture("minimal-valid-review.json")
    add_brand_evidence(payload)
    link, relation = add_subject_fact(payload, "收购与历史关系", "历史权利人")
    link.update({"结论状态": "候选", "可靠性等级": "低", "证据引用": ["EVD-002"]})
    relation.update({
        "时间状态": "历史",
        "结论状态": "候选",
        "可靠性等级": "低",
        "证据引用": ["EVD-002"],
    })
    entity = payload["主体索引"][0]
    entity.update({
        "当前状态": "当前",
        "结论状态": "候选",
        "可靠性等级": "低",
        "证据引用": ["EVD-001", "EVD-002"],
    })
    assert validate_payload(payload) == []


def test_rejects_overall_classification_brand_outside_scope():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["总体复核分级"][0]["品牌"] = ["BRD-999"]
    assert "DANGLING_OVERALL_CLASSIFICATION_BRAND" in codes(payload)


def add_brand_evidence(payload):
    evidence = dict(payload["品牌复核结果"][0]["主要来源"][0])
    evidence["证据编号"] = "EVD-002"
    payload["品牌复核结果"][0]["主要来源"].append(evidence)


def add_subject_fact(payload, field, role):
    relation = dict(payload["主体关系"][0])
    relation.update({"关系ID": "REL-002", "关系类型": role})
    payload["主体关系"].append(relation)
    payload["主体索引"][0]["主体角色"].append(role)
    link = dict(payload["品牌复核结果"][0]["主体关系"]["商标权利人"][0])
    payload["品牌复核结果"][0]["主体关系"][field].append(link)
    return link, relation


def add_manufacturing_fact(payload, field, role, level, products):
    relation = dict(payload["主体关系"][0])
    relation.update({
        "关系ID": "REL-002",
        "关系类型": role,
        "适用层级": level,
        "适用商品ID": list(products),
    })
    payload["主体关系"].append(relation)
    payload["主体索引"][0]["主体角色"].append(role)
    link = {
        "主体ID": "ENT-001",
        "结论状态": "已确认",
        "可靠性等级": "中",
        "证据引用": ["EVD-001"],
        "适用限制": ["品牌级证据。"],
    }
    if level == "SKU级":
        link["适用商品ID"] = list(products)
    payload["品牌复核结果"][0]["制造关系"][field] = [link]
    return link, relation


@pytest.mark.parametrize(
    ("field", "role"),
    (
        ("商标权利人", "商标权利人"),
        ("品牌运营主体", "品牌运营主体"),
        ("母公司", "母公司"),
        ("收购与历史关系", "历史权利人"),
    ),
)
def test_each_nested_subject_section_must_exactly_match_a_normalized_relationship(field, role):
    payload = cloned_fixture("minimal-valid-review.json")
    link, _ = add_subject_fact(payload, field, role)
    link["结论状态"] = "候选"
    assert {"NESTED_RELATIONSHIP_VIEW_MISMATCH", "NORMALIZED_RELATIONSHIP_VIEW_MISMATCH"} <= codes(payload)


@pytest.mark.parametrize(
    "field",
    ("结论状态", "可靠性等级", "适用限制", "证据引用"),
)
def test_subject_links_compare_all_semantic_fields_exactly(field):
    payload = cloned_fixture("minimal-valid-review.json")
    add_brand_evidence(payload)
    link = payload["品牌复核结果"][0]["主体关系"]["商标权利人"][0]
    link[field] = {
        "结论状态": "候选",
        "可靠性等级": "低",
        "适用限制": ["不同限制。"],
        "证据引用": ["EVD-002"],
    }[field]
    assert {"NESTED_RELATIONSHIP_VIEW_MISMATCH", "NORMALIZED_RELATIONSHIP_VIEW_MISMATCH"} <= codes(payload)


def test_normalized_only_subject_relationship_is_rejected_without_entity_role_side_effect():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["主体关系"][0]["关系类型"] = "品牌运营主体"
    payload["品牌复核结果"][0]["主体关系"]["商标权利人"] = []
    payload["主体索引"][0]["主体角色"] = ["品牌运营主体"]
    assert "NORMALIZED_RELATIONSHIP_VIEW_MISMATCH" in codes(payload)


def test_reverse_brand_entity_relationship_direction_matches_nested_fact():
    payload = cloned_fixture("minimal-valid-review.json")
    relation = payload["主体关系"][0]
    relation["起点类型"], relation["终点类型"] = relation["终点类型"], relation["起点类型"]
    relation["起点ID"], relation["终点ID"] = relation["终点ID"], relation["起点ID"]
    assert validate_payload(payload) == []


@pytest.mark.parametrize(
    ("field", "role", "level", "products"),
    (
        ("品牌层面主要制造商", "品牌层面制造商", "品牌级", []),
        ("具体SKU制造商", "具体SKU制造商", "SKU级", ["PRD-001"]),
    ),
)
def test_each_nested_manufacturing_section_must_exactly_match_a_normalized_relationship(
    field, role, level, products
):
    payload = cloned_fixture("minimal-valid-review.json")
    link, _ = add_manufacturing_fact(payload, field, role, level, products)
    link["可靠性等级"] = "低"
    assert {"NESTED_RELATIONSHIP_VIEW_MISMATCH", "NORMALIZED_RELATIONSHIP_VIEW_MISMATCH"} <= codes(payload)


def test_nested_only_brand_manufacturer_is_rejected_as_relationship_view_mismatch():
    payload = cloned_fixture("minimal-valid-review.json")
    link, _ = add_manufacturing_fact(payload, "品牌层面主要制造商", "品牌层面制造商", "品牌级", [])
    payload["主体关系"].pop()
    link["适用限制"] = ["品牌级证据。"]
    assert "NESTED_RELATIONSHIP_VIEW_MISMATCH" in codes(payload)


def test_normalized_only_sku_manufacturer_is_rejected_as_relationship_view_mismatch():
    payload = cloned_fixture("minimal-valid-review.json")
    add_manufacturing_fact(payload, "具体SKU制造商", "具体SKU制造商", "SKU级", ["PRD-001"])
    payload["品牌复核结果"][0]["制造关系"]["具体SKU制造商"] = []
    assert "NORMALIZED_RELATIONSHIP_VIEW_MISMATCH" in codes(payload)


@pytest.mark.parametrize("field", ("适用商品ID", "证据引用"))
def test_sku_manufacturing_links_compare_product_and_evidence_sets_exactly(field):
    payload = cloned_fixture("minimal-valid-review.json")
    add_brand_evidence(payload)
    payload["调查范围"]["代表性商品"].append({
        **payload["调查范围"]["代表性商品"][0],
        "商品ID": "PRD-002",
    })
    link, _ = add_manufacturing_fact(
        payload, "具体SKU制造商", "具体SKU制造商", "SKU级", ["PRD-001"]
    )
    link[field] = ["PRD-002"] if field == "适用商品ID" else ["EVD-002"]
    assert {"NESTED_RELATIONSHIP_VIEW_MISMATCH", "NORMALIZED_RELATIONSHIP_VIEW_MISMATCH"} <= codes(payload)


@pytest.mark.parametrize("limitation", (
    "结论限于伪造且不一致的范围。",
    "结论基于伪造且不一致的范围。",
    "关系仅覆盖伪造且不一致的范围。",
    "历史关系。",
))
def test_limitations_compare_full_text_without_prefix_filtering(limitation):
    payload = cloned_fixture("minimal-valid-review.json")
    payload["品牌复核结果"][0]["主体关系"]["商标权利人"][0]["适用限制"] = [limitation]
    assert {"NESTED_RELATIONSHIP_VIEW_MISMATCH", "NORMALIZED_RELATIONSHIP_VIEW_MISMATCH"} <= codes(payload)


def test_limitations_evidence_and_products_preserve_duplicate_counts():
    payload = cloned_fixture("minimal-valid-review.json")
    link = payload["品牌复核结果"][0]["主体关系"]["商标权利人"][0]
    link["适用限制"].append(link["适用限制"][0])
    link["证据引用"].append("EVD-001")
    assert {"NESTED_RELATIONSHIP_VIEW_MISMATCH", "NORMALIZED_RELATIONSHIP_VIEW_MISMATCH"} <= codes(payload)

    payload = cloned_fixture("minimal-valid-review.json")
    link, relation = add_manufacturing_fact(
        payload, "具体SKU制造商", "具体SKU制造商", "SKU级", ["PRD-001"]
    )
    link["适用限制"] = relation["适用限制"]
    link["适用商品ID"].append("PRD-001")
    assert {"NESTED_RELATIONSHIP_VIEW_MISMATCH", "NORMALIZED_RELATIONSHIP_VIEW_MISMATCH"} <= codes(payload)


def add_product_entity_sku_relation(payload, direction="product-to-entity"):
    link = {
        "主体ID": "ENT-001",
        "适用商品ID": ["PRD-001"],
        "结论状态": "已确认",
        "可靠性等级": "中",
        "证据引用": ["EVD-001"],
        "适用限制": ["仅适用 PRD-001。"],
    }
    payload["品牌复核结果"][0]["制造关系"]["具体SKU制造商"] = [link]
    payload["主体索引"][0]["主体角色"].append("具体SKU制造商")
    relation = {
        **payload["主体关系"][0],
        "关系ID": "REL-002",
        "关系类型": "具体SKU制造商",
        "适用层级": "SKU级",
        "适用商品ID": ["PRD-001"],
        "结论状态": link["结论状态"],
        "可靠性等级": link["可靠性等级"],
        "证据引用": link["证据引用"],
        "适用限制": link["适用限制"],
    }
    if direction == "product-to-entity":
        relation.update({"起点类型": "商品", "起点ID": "PRD-001", "终点类型": "主体", "终点ID": "ENT-001"})
    else:
        relation.update({"起点类型": "主体", "起点ID": "ENT-001", "终点类型": "商品", "终点ID": "PRD-001"})
    payload["主体关系"].append(relation)
    return link, relation


@pytest.mark.parametrize("direction", ("product-to-entity", "entity-to-product"))
def test_product_entity_sku_relationship_binds_to_exactly_one_nested_brand_fact(direction):
    payload = cloned_fixture("minimal-valid-review.json")
    add_product_entity_sku_relation(payload, direction)
    assert validate_payload(payload) == []


def test_product_entity_sku_relationship_without_nested_brand_fact_is_rejected():
    payload = cloned_fixture("minimal-valid-review.json")
    add_product_entity_sku_relation(payload)
    payload["品牌复核结果"][0]["制造关系"]["具体SKU制造商"] = []
    assert "NORMALIZED_RELATIONSHIP_VIEW_MISMATCH" in codes(payload)


def test_unbound_product_entity_relationship_does_not_populate_entity_view():
    payload = cloned_fixture("minimal-valid-review.json")
    entity = {
        **payload["主体索引"][0],
        "主体ID": "ENT-002",
        "关联品牌": [],
        "主体角色": ["具体SKU制造商"],
    }
    payload["主体索引"].append(entity)
    _, relation = add_product_entity_sku_relation(payload)
    relation["终点ID"] = "ENT-002"
    payload["品牌复核结果"][0]["制造关系"]["具体SKU制造商"] = []
    assert {"NORMALIZED_RELATIONSHIP_VIEW_MISMATCH", "ENTITY_ROLE_VIEW_MISMATCH"} <= codes(payload)
    assert "ENTITY_BRAND_VIEW_MISMATCH" not in codes(payload)


def test_product_entity_sku_relationship_with_multiple_matching_brand_facts_is_ambiguous():
    payload = cloned_fixture("shared-entity-review.json")
    link, relation = add_product_entity_sku_relation(payload)
    payload["品牌复核结果"][1]["制造关系"]["具体SKU制造商"] = [{
        **link,
        "证据引用": ["EVD-001"],
    }]
    payload["品牌复核结果"][1]["主要来源"][0]["证据编号"] = "EVD-001"
    relation["证据引用"] = ["EVD-001"]
    assert "AMBIGUOUS_PRODUCT_RELATIONSHIP_BRAND" in codes(payload)


def test_product_endpoint_sku_relation_must_include_endpoint_product_in_scope():
    payload = cloned_fixture("minimal-valid-review.json")
    _, relation = add_product_entity_sku_relation(payload)
    product = dict(payload["调查范围"]["代表性商品"][0])
    product["商品ID"] = "PRD-002"
    payload["调查范围"]["代表性商品"].append(product)
    relation["适用商品ID"] = ["PRD-002"]
    assert "SKU_RELATIONSHIP_WITHOUT_PRODUCT" in codes(payload)


def test_product_entity_relationship_requires_sku_manufacturer_at_sku_level():
    payload = cloned_fixture("minimal-valid-review.json")
    relation = {
        **payload["主体关系"][0],
        "关系ID": "REL-002",
        "起点类型": "商品",
        "起点ID": "PRD-001",
        "关系类型": "品牌层面制造商",
        "终点类型": "主体",
        "终点ID": "ENT-001",
        "适用层级": "品牌级",
        "适用商品ID": [],
    }
    payload["主体关系"].append(relation)
    assert "PRODUCT_ENTITY_RELATIONSHIP_NOT_SKU_MANUFACTURER" in codes(payload)


def test_rejects_nested_entity_missing_from_index():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["品牌复核结果"][0]["主体关系"]["商标权利人"][0]["主体ID"] = "ENT-999"
    assert "DANGLING_NESTED_ENTITY" in codes(payload)


def test_sku_relationships_and_manufacturers_require_existing_products():
    payload = cloned_fixture("minimal-valid-review.json")
    relation = dict(payload["主体关系"][0])
    relation.update({
        "关系ID": "REL-002",
        "关系类型": "具体SKU制造商",
        "适用层级": "SKU级",
        "适用商品ID": [],
    })
    payload["主体关系"].append(relation)
    assert "SKU_RELATIONSHIP_WITHOUT_PRODUCT" in codes(payload)

    payload = cloned_fixture("minimal-valid-review.json")
    manufacturer = {
        "主体ID": "ENT-001",
        "适用商品ID": ["PRD-999"],
        "结论状态": "已确认",
        "可靠性等级": "中",
        "证据引用": ["EVD-001"],
        "适用限制": ["仅适用包装标签。"],
    }
    payload["品牌复核结果"][0]["制造关系"]["具体SKU制造商"] = [manufacturer]
    assert "SKU_MANUFACTURER_WITHOUT_PRODUCT" in codes(payload)


def test_brand_level_manufacturers_require_sku_limitation():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["品牌复核结果"][0]["制造关系"]["品牌层面主要制造商"] = [{
        "主体ID": "ENT-001",
        "结论状态": "已确认",
        "可靠性等级": "中",
        "证据引用": ["EVD-001"],
        "适用限制": ["品牌级证据。"],
    }]
    payload["品牌复核结果"][0]["制造关系"]["SKU适用限制"] = []
    assert "BRAND_MANUFACTURER_WITHOUT_SKU_LIMITATION" in codes(payload)


def test_relationship_time_statuses_are_preserved_as_distinct_records():
    payload = cloned_fixture("minimal-valid-review.json")
    historic = dict(payload["主体关系"][0])
    historic.update({"关系ID": "REL-002", "关系类型": "历史权利人", "时间状态": "历史"})
    payload["主体关系"].append(historic)
    payload["主体索引"][0]["主体角色"].append("历史权利人")
    historic_link = {
        "主体ID": "ENT-001",
        "结论状态": "已确认",
        "可靠性等级": "中",
        "证据引用": ["EVD-001"],
        "适用限制": ["历史关系。"],
    }
    payload["品牌复核结果"][0]["主体关系"]["收购与历史关系"].append(historic_link)
    historic["适用限制"] = list(historic_link["适用限制"])
    assert validate_payload(payload) == []


def test_rejects_conflicting_time_states_for_the_same_normalized_relationship():
    payload = cloned_fixture("minimal-valid-review.json")
    conflicting = dict(payload["主体关系"][0])
    conflicting.update({"关系ID": "REL-002", "时间状态": "历史"})
    payload["主体关系"].append(conflicting)
    assert "RELATIONSHIP_TIME_STATUS_CONFLICT" in codes(payload)


def test_confirmation_fields_are_consistent_and_require_matching_hash():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["用户确认"]["确认时间"] = "2026-08-27T10:00:00+08:00"
    assert "UNCONFIRMED_FIELDS_NOT_NULL" in codes(payload)

    payload = cloned_fixture("minimal-valid-review.json")
    payload["用户确认"] = {
        "是否确认": True,
        "确认时间": "2026-08-27T10:00:00+08:00",
        "用户确认原文": "确认",
        "内容摘要哈希": "sha256:wrong",
    }
    assert "CONFIRMATION_HASH_MISMATCH" in codes(payload)
    payload["用户确认"]["内容摘要哈希"] = compute_content_hash(payload)
    assert validate_payload(payload) == []


def test_hash_ignores_confirmation_key_order_and_changes_with_facts():
    payload = cloned_fixture("minimal-valid-review.json")
    original_hash = compute_content_hash(payload)
    payload["用户确认"]["用户确认原文"] = "different confirmation text"
    assert compute_content_hash(payload) == original_hash
    payload["报告信息"]["报告标题"] = "changed fact"
    assert compute_content_hash(payload) != original_hash


def test_require_confirmed_and_assertion_message_are_readable():
    payload = cloned_fixture("minimal-valid-review.json")
    assert "NOT_CONFIRMED" in codes(payload, require_confirmed=True)
    with pytest.raises(ValueError, match=r"NOT_CONFIRMED .* report requires explicit confirmation"):
        assert_valid_payload(payload, require_confirmed=True)


def test_schema_error_does_not_prevent_safe_business_checks():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["主体关系"] = "not a list"
    issues = validate_payload(payload)
    assert any(issue.code == "SCHEMA_ERROR" for issue in issues)
    assert issues == sorted(issues)


def test_cli_has_expected_exit_codes():
    root = SKILL_ROOT
    valid_path = root / ".task3-cli-valid.json"
    command = [sys.executable, "scripts/validate_evidence_review.py", str(valid_path)]
    invalid_path = root / ".task3-cli-invalid.json"
    invalid_payload = cloned_fixture("minimal-valid-review.json")
    invalid_payload["用户确认"]["确认时间"] = "2026-08-27T10:00:00+08:00"
    try:
        valid_path.write_text(
            json.dumps(cloned_fixture("minimal-valid-review.json"), ensure_ascii=False),
            encoding="utf-8",
        )
        valid = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        assert valid.returncode == 0
        assert valid.stdout.strip() == f"VALID: {valid_path}"
        invalid_path.write_text(json.dumps(invalid_payload, ensure_ascii=False), encoding="utf-8")
        invalid = subprocess.run(
            [*command[:2], str(invalid_path)], cwd=root, capture_output=True, text=True, check=False
        )
        assert invalid.returncode == 1
        assert "UNCONFIRMED_FIELDS_NOT_NULL" in invalid.stdout
    finally:
        valid_path.unlink(missing_ok=True)
        invalid_path.unlink(missing_ok=True)
