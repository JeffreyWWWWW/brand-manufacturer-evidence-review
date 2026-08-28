import json
from pathlib import Path

import jsonschema
import pytest

from tests.helpers import cloned_fixture, load_fixture

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "references" / "evidence-review.schema.json"

TOP_LEVEL_REQUIRED = (
    "规范版本", "报告信息", "输入材料", "调查范围", "证据链方法", "品牌复核结果",
    "主体索引", "主体关系", "总体复核分级", "数据库访问记录", "使用限制与建议", "用户确认",
)

OBJECT_REQUIRED_FIELDS = {
    "reportInfo": ("报告标题", "调查日期", "生成时间", "底稿编号"),
    "inputSource": ("来源编号", "来源类型", "文件名或URL", "客户提供", "内容摘要"),
    "product": ("商品ID", "平台", "原始URL", "平台标识符", "型号", "SKU", "证据引用"),
    "brand": ("品牌ID", "原始名称", "规范名称", "证据引用"),
    "investigationScope": ("产品原始名称", "产品规范名称", "产品描述", "代表性商品", "目标品牌"),
    "evidenceStep": ("步骤编号", "名称", "执行方法", "证据优先级"),
    "entityLink": ("主体ID", "结论状态", "可靠性等级", "证据引用", "适用限制"),
    "skuEntityLink": ("主体ID", "适用商品ID", "结论状态", "可靠性等级", "证据引用", "适用限制"),
    "evidence": ("证据编号", "来源名称", "URL", "来源类别", "访问日期", "支持结论", "证据等级"),
    "brandDisplay": ("原始名称", "规范名称"),
    "brandSubjectRelationships": ("商标权利人", "品牌运营主体", "母公司", "收购与历史关系"),
    "manufacturingRelationships": ("品牌层面主要制造商", "具体SKU制造商", "制造模式", "SKU适用限制"),
    "conclusionEvaluation": ("可靠性等级", "可靠性依据", "人工复核建议"),
    "brandReview": ("品牌", "实际查询路径", "查询结果摘要", "主体关系", "制造关系", "结论评价", "关键说明", "主要来源"),
    "entity": ("主体ID", "规范名称", "名称变体", "主体类型", "司法辖区", "注册标识", "官方网站", "关联品牌", "主体角色", "当前状态", "结论状态", "可靠性等级", "证据引用", "适用限制"),
    "relationship": ("关系ID", "起点类型", "起点ID", "关系类型", "终点类型", "终点ID", "时间状态", "适用层级", "适用商品ID", "结论状态", "可靠性等级", "证据引用", "适用限制"),
    "overallClass": ("复核等级", "品牌", "适用结论"),
    "databaseAccess": ("数据库", "官方入口", "访问时间", "访问结果", "使用建议"),
    "confirmation": ("是否确认", "确认时间", "用户确认原文", "内容摘要哈希"),
}

ID_CASES = (
    (("输入材料", 0, "来源编号"), "SRC-001"),
    (("调查范围", "目标品牌", 0, "品牌ID"), "BRD-001"),
    (("调查范围", "代表性商品", 0, "商品ID"), "PRD-001"),
    (("品牌复核结果", 0, "主要来源", 0, "证据编号"), "EVD-001"),
    (("主体索引", 0, "主体ID"), "ENT-001"),
    (("主体关系", 0, "关系ID"), "REL-001"),
)

FREE_TEXT_PATHS = (
    (("规范版本",), "规范版本"),
    (("报告信息", "报告标题"), "报告标题"), (("报告信息", "底稿编号"), "底稿编号"),
    (("输入材料", 0, "来源类型"), "来源类型"), (("输入材料", 0, "文件名或URL"), "文件名或URL"),
    (("输入材料", 0, "内容摘要"), "内容摘要"),
    (("调查范围", "产品原始名称"), "产品原始名称"), (("调查范围", "产品规范名称"), "产品规范名称"),
    (("调查范围", "产品描述"), "产品描述"), (("调查范围", "代表性商品", 0, "平台"), "平台"),
    (("调查范围", "代表性商品", 0, "平台标识符"), "平台标识符"), (("调查范围", "代表性商品", 0, "型号"), "型号"),
    (("调查范围", "代表性商品", 0, "SKU"), "SKU"), (("调查范围", "目标品牌", 0, "原始名称"), "原始名称"),
    (("调查范围", "目标品牌", 0, "规范名称"), "规范名称"), (("证据链方法", 0, "步骤编号"), "步骤编号"),
    (("证据链方法", 0, "名称"), "名称"), (("证据链方法", 0, "执行方法"), "执行方法"),
    (("品牌复核结果", 0, "品牌", "原始名称"), "品牌原始名称"), (("品牌复核结果", 0, "品牌", "规范名称"), "品牌规范名称"),
    (("品牌复核结果", 0, "实际查询路径", 0), "查询路径"), (("品牌复核结果", 0, "查询结果摘要"), "查询结果摘要"),
    (("品牌复核结果", 0, "主体关系", "商标权利人", 0, "适用限制", 0), "主体限制"),
    (("品牌复核结果", 0, "制造关系", "SKU适用限制", 0), "SKU限制"),
    (("品牌复核结果", 0, "结论评价", "可靠性依据"), "可靠性依据"), (("品牌复核结果", 0, "结论评价", "人工复核建议"), "复核建议"),
    (("品牌复核结果", 0, "关键说明", 0), "关键说明"), (("品牌复核结果", 0, "主要来源", 0, "来源名称"), "来源名称"),
    (("品牌复核结果", 0, "主要来源", 0, "来源类别"), "来源类别"), (("品牌复核结果", 0, "主要来源", 0, "支持结论", 0), "支持结论"),
    (("主体索引", 0, "规范名称"), "主体规范名称"), (("主体索引", 0, "名称变体", 0), "名称变体"),
    (("主体索引", 0, "司法辖区"), "司法辖区"),
    (("主体索引", 0, "适用限制", 0), "主体适用限制"), (("主体关系", 0, "适用限制", 0), "关系适用限制"),
    (("总体复核分级", 0, "适用结论"), "适用结论"), (("数据库访问记录", 0, "数据库"), "数据库"),
    (("数据库访问记录", 0, "访问结果"), "访问结果"), (("数据库访问记录", 0, "使用建议"), "使用建议"),
    (("使用限制与建议", 0), "使用限制"), (("用户确认", "用户确认原文"), "确认原文"),
)


def load_schema() -> dict[str, object]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def errors_for(payload: dict[str, object]) -> list[jsonschema.ValidationError]:
    validator = jsonschema.Draft202012Validator(
        load_schema(), format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )
    return list(validator.iter_errors(payload))


def errors_without_format_checker(payload: dict[str, object]) -> list[jsonschema.ValidationError]:
    return list(jsonschema.Draft202012Validator(load_schema()).iter_errors(payload))


def set_path(payload: dict[str, object], path: tuple[object, ...], value: object) -> None:
    current: object = payload
    for part in path[:-1]:
        current = current[part]  # type: ignore[index]
    current[path[-1]] = value  # type: ignore[index]


def test_schema_is_valid_draft_2020_12():
    jsonschema.Draft202012Validator.check_schema(load_schema())


def test_minimal_and_shared_entity_fixtures_match_schema():
    assert errors_for(load_fixture("minimal-valid-review.json")) == []
    assert errors_for(load_fixture("shared-entity-review.json")) == []


@pytest.mark.parametrize(
    "path",
    (
        ("调查范围", "目标品牌"),
        ("品牌复核结果",),
        ("品牌复核结果", 0, "主要来源", 0, "支持结论"),
    ),
)
def test_schema_rejects_empty_required_business_collections(path):
    payload = cloned_fixture("minimal-valid-review.json")
    set_path(payload, path, [])
    assert any(error.validator == "minItems" for error in errors_for(payload))


def test_schema_declares_explicit_top_level_required_fields():
    schema = load_schema()
    assert tuple(schema["required"]) == TOP_LEVEL_REQUIRED
    payload = cloned_fixture("minimal-valid-review.json")
    for field in TOP_LEVEL_REQUIRED:
        incomplete = payload.copy()
        incomplete.pop(field)
        assert any(error.validator == "required" for error in errors_for(incomplete))


def test_schema_declares_required_fields_for_every_planned_object():
    schema = load_schema()
    assert set(OBJECT_REQUIRED_FIELDS) == {
        name for name, definition in schema["$defs"].items() if definition.get("type") == "object"
    }
    for name, expected_fields in OBJECT_REQUIRED_FIELDS.items():
        assert tuple(schema["$defs"][name]["required"]) == expected_fields


def test_schema_closes_every_object():
    schema = load_schema()
    object_schemas = []

    def collect_objects(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                object_schemas.append(node)
            for value in node.values():
                collect_objects(value)
        elif isinstance(node, list):
            for value in node:
                collect_objects(value)

    collect_objects(schema)
    assert object_schemas
    assert all(node.get("additionalProperties") is False for node in object_schemas)


def test_schema_rejects_unknown_fields_at_multiple_object_levels():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["未声明字段"] = "不应接受"
    payload["报告信息"]["额外字段"] = "不应接受"
    payload["品牌复核结果"][0]["结论评价"]["额外字段"] = "不应接受"
    assert sum(error.validator == "additionalProperties" for error in errors_for(payload)) == 3


def test_schema_rejects_invalid_entity_identifier():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["主体索引"][0]["主体ID"] = "COMPANY-1"
    assert any("ENT-" in error.message for error in errors_for(payload))


@pytest.mark.parametrize("path, valid_id", ID_CASES)
@pytest.mark.parametrize("suffix", ("\n", " "))
def test_schema_rejects_each_id_with_trailing_characters(path, valid_id, suffix):
    payload = cloned_fixture("minimal-valid-review.json")
    set_path(payload, path, valid_id + suffix)
    assert errors_for(payload)


@pytest.mark.parametrize("path, label", FREE_TEXT_PATHS)
@pytest.mark.parametrize("placeholder", ("   ", " / ", "\tN/a\n"))
def test_schema_rejects_free_text_whitespace_and_exact_placeholders(path, label, placeholder):
    payload = cloned_fixture("minimal-valid-review.json")
    set_path(payload, path, placeholder)
    assert errors_for(payload), label


def test_schema_allows_slash_and_na_inside_normal_text():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["报告信息"]["报告标题"] = "证据/N/A复核报告"
    payload["品牌复核结果"][0]["查询结果摘要"] = "路径 / N/A 均属于正常说明内容。"
    assert errors_for(payload) == []


@pytest.mark.parametrize("path", (("报告信息", "生成时间"), ("数据库访问记录", 0, "访问时间"), ("用户确认", "确认时间")))
def test_schema_rejects_out_of_range_numeric_timezone(path):
    payload = cloned_fixture("minimal-valid-review.json")
    set_path(payload, path, "2026-08-27T09:30:00+99:99")
    assert errors_for(payload)


@pytest.mark.parametrize("offset", ("Z", "+00:00", "-05:30", "+23:59"))
def test_schema_accepts_rfc3339_numeric_and_z_offsets(offset):
    for path in (("报告信息", "生成时间"), ("数据库访问记录", 0, "访问时间"), ("用户确认", "确认时间")):
        payload = cloned_fixture("minimal-valid-review.json")
        set_path(payload, path, "2026-08-27T09:30:00" + offset)
        assert errors_for(payload) == []


INVALID_RFC3339_DATE_TIMES = (
    "2026-02-30T09:30:00+08:00",
    "2026-08-27T25:30:00+08:00",
    "2026-08-27T09:60:00+08:00",
    "2026-08-27T09:30:60+08:00",
    "2026-08-27 09:30:00+08:00",
)


@pytest.mark.parametrize(
    "path",
    (("报告信息", "生成时间"), ("数据库访问记录", 0, "访问时间"), ("用户确认", "确认时间")),
)
@pytest.mark.parametrize("date_time", INVALID_RFC3339_DATE_TIMES)
def test_schema_rejects_invalid_rfc3339_date_time_without_format_checker(path, date_time):
    payload = cloned_fixture("minimal-valid-review.json")
    set_path(payload, path, date_time)
    assert errors_without_format_checker(payload)


@pytest.mark.parametrize(
    "date_time",
    ("2026-08-27t09:30:00z", "2026-08-27T09:30:00.123456+08:00"),
)
def test_schema_accepts_rfc3339_case_variants_without_format_checker(date_time):
    payload = cloned_fixture("minimal-valid-review.json")
    payload["报告信息"]["生成时间"] = date_time
    assert errors_without_format_checker(payload) == []


def test_schema_accepts_rfc3339_leap_second_only_at_month_end_without_format_checker():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["报告信息"]["生成时间"] = "2016-12-31T23:59:60Z"
    assert errors_without_format_checker(payload) == []


@pytest.mark.parametrize(
    "date_time",
    ("2026-04-31T09:30:00+08:00", "2026-02-29T09:30:00+08:00"),
)
def test_schema_rejects_invalid_month_days_without_format_checker(date_time):
    payload = cloned_fixture("minimal-valid-review.json")
    payload["报告信息"]["生成时间"] = date_time
    assert errors_without_format_checker(payload)


@pytest.mark.parametrize(
    "date_time",
    ("2024-02-29T09:30:00+08:00", "2000-02-29T09:30:00+08:00"),
)
def test_schema_accepts_leap_year_february_days_without_format_checker(date_time):
    payload = cloned_fixture("minimal-valid-review.json")
    payload["报告信息"]["生成时间"] = date_time
    assert errors_without_format_checker(payload) == []


@pytest.mark.parametrize("endpoint_type, endpoint_id", (("品牌", "ENT-001"), ("主体", "BRD-001"), ("商品", "BRD-001")))
def test_schema_rejects_mismatched_relationship_start_endpoint(endpoint_type, endpoint_id):
    payload = cloned_fixture("minimal-valid-review.json")
    payload["主体关系"][0]["起点类型"] = endpoint_type
    payload["主体关系"][0]["起点ID"] = endpoint_id
    assert errors_for(payload)


@pytest.mark.parametrize("endpoint_type, endpoint_id", (("品牌", "ENT-001"), ("主体", "BRD-001"), ("商品", "BRD-001")))
def test_schema_rejects_mismatched_relationship_end_endpoint(endpoint_type, endpoint_id):
    payload = cloned_fixture("minimal-valid-review.json")
    payload["主体关系"][0]["终点类型"] = endpoint_type
    payload["主体关系"][0]["终点ID"] = endpoint_id
    assert errors_for(payload)


@pytest.mark.parametrize("uri", ("/", "relative/path", "not a uri"))
def test_schema_rejects_invalid_uri_values(uri):
    payload = cloned_fixture("minimal-valid-review.json")
    payload["主体索引"][0]["官方网站"] = [uri]
    assert errors_for(payload)


def test_schema_accepts_nullable_uri_fields():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["主体索引"][0]["官方网站"] = [None]
    payload["调查范围"]["代表性商品"][0]["原始URL"] = None
    assert errors_for(payload) == []


def test_shared_entity_fixture_reuses_one_entity_across_two_brands_and_relationships():
    minimal = load_fixture("minimal-valid-review.json")
    shared = load_fixture("shared-entity-review.json")
    assert len(shared["主体索引"]) == 1
    assert shared["主体索引"][0]["主体ID"] == "ENT-001"
    assert shared["主体索引"][0]["关联品牌"] == ["BRD-001", "BRD-002"]
    assert [brand["品牌ID"] for brand in shared["调查范围"]["目标品牌"]] == ["BRD-001", "BRD-002"]
    assert [review["品牌"]["规范名称"] for review in shared["品牌复核结果"]] == [brand["规范名称"] for brand in shared["调查范围"]["目标品牌"]]
    assert minimal["品牌复核结果"][0] == shared["品牌复核结果"][0]
    assert [(relation["关系ID"], relation["起点ID"], relation["终点ID"]) for relation in shared["主体关系"]] == [
        ("REL-001", "BRD-001", "ENT-001"), ("REL-002", "BRD-002", "ENT-001")
    ]


def test_schema_rejects_unknown_manufacturing_mode():
    payload = cloned_fixture("minimal-valid-review.json")
    payload["品牌复核结果"][0]["制造关系"]["制造模式"] = "经销"
    assert errors_for(payload)
