from __future__ import annotations

import argparse
import copy
import hashlib
import json
from urllib.parse import urlparse
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

try:
    from scripts.quality_summary import build_quality_summary
except ModuleNotFoundError:  # direct CLI execution from the scripts directory
    from quality_summary import build_quality_summary


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA_PATH = ROOT / "references" / "evidence-review.schema.json"


@dataclass(frozen=True, order=True)
class ValidationIssue:
    path: str
    code: str
    message: str


def compute_content_hash(payload: Mapping[str, Any]) -> str:
    content = copy.deepcopy(dict(payload))
    content.pop("用户确认", None)
    canonical = json.dumps(
        content, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mappings(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _ordered_strings(value: Any) -> tuple[str, ...]:
    return tuple(sorted(_strings(value)))


def _path(*parts: str | int) -> str:
    result = "$"
    for part in parts:
        result += f"[{part}]" if isinstance(part, int) else f".{part}"
    return result


def _issue(issues: list[ValidationIssue], path: str, code: str, message: str) -> None:
    issues.append(ValidationIssue(path, code, message))


def _independent_source_hosts(
    evidence_ids: Iterable[str], evidence_by_id: Mapping[str, Mapping[str, Any]]
) -> set[str]:
    hosts: set[str] = set()
    for evidence_id in evidence_ids:
        url = evidence_by_id.get(evidence_id, {}).get("URL")
        if not isinstance(url, str):
            continue
        host = urlparse(url).netloc.lower().split("@")[-1].split(":")[0]
        if host:
            hosts.add(host.removeprefix("www."))
    return hosts


def _schema_issues(payload: Mapping[str, Any], schema_path: Path) -> list[ValidationIssue]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    issues = []
    for error in validator.iter_errors(payload):
        path = _path(*error.absolute_path)
        issues.append(ValidationIssue(path, "SCHEMA_ERROR", error.message))
    return issues


def _declared_ids(
    payload: Mapping[str, Any],
    issues: list[ValidationIssue],
) -> dict[str, set[str]]:
    scope = _mapping(payload.get("调查范围"))
    collections: tuple[tuple[str, list[Mapping[str, Any]], str, str, tuple[str | int, ...]], ...] = (
        ("SRC", _mappings(payload.get("输入材料")), "来源编号", "DUPLICATE_SOURCE_ID", ("输入材料",)),
        ("BRD", _mappings(scope.get("目标品牌")), "品牌ID", "DUPLICATE_BRAND_ID", ("调查范围", "目标品牌")),
        ("PRD", _mappings(scope.get("代表性商品")), "商品ID", "DUPLICATE_PRODUCT_ID", ("调查范围", "代表性商品")),
        ("ENT", _mappings(payload.get("主体索引")), "主体ID", "DUPLICATE_ENTITY_ID", ("主体索引",)),
        ("REL", _mappings(payload.get("主体关系")), "关系ID", "DUPLICATE_RELATIONSHIP_ID", ("主体关系",)),
    )
    evidence: list[tuple[Mapping[str, Any], tuple[str | int, ...]]] = []
    for review_index, review in enumerate(_mappings(payload.get("品牌复核结果"))):
        for evidence_index, item in enumerate(_mappings(review.get("主要来源"))):
            evidence.append((item, ("品牌复核结果", review_index, "主要来源", evidence_index)))

    found: dict[str, set[str]] = {prefix: set() for prefix, *_ in collections}
    found["EVD"] = set()
    for prefix, collection, key, duplicate_code, base_path in collections:
        for index, item in enumerate(collection):
            identifier = item.get(key)
            if not isinstance(identifier, str):
                continue
            if identifier in found[prefix]:
                _issue(issues, _path(*base_path, index, key), duplicate_code, f"{identifier} is declared more than once")
            found[prefix].add(identifier)
    for item, item_path in evidence:
        identifier = item.get("证据编号")
        if not isinstance(identifier, str):
            continue
        if identifier in found["EVD"]:
            _issue(issues, _path(*item_path, "证据编号"), "DUPLICATE_EVIDENCE_ID", f"{identifier} is declared more than once")
        found["EVD"].add(identifier)
    return found


def _check_evidence_refs(
    references: Iterable[str],
    evidence_ids: set[str],
    issues: list[ValidationIssue],
    path: str,
    allowed_ids: set[str] | None = None,
    require_evidence: bool = True,
) -> None:
    values = list(references)
    if not values and require_evidence:
        _issue(issues, path, "MISSING_EVIDENCE_REFERENCE", "external conclusion requires at least one EVD evidence reference")
    for reference in values:
        if reference.startswith("SRC-"):
            _issue(issues, path, "SOURCE_USED_AS_EVIDENCE", f"{reference} is an input source, not external evidence")
        elif reference not in evidence_ids:
            _issue(issues, path, "MISSING_EVIDENCE_REFERENCE", f"{reference} does not identify a declared EVD record")
        elif allowed_ids is not None and reference not in allowed_ids:
            _issue(issues, path, "CROSS_BRAND_EVIDENCE_REFERENCE", f"{reference} is not a primary source for this brand")


def _brand_review_ids(
    payload: Mapping[str, Any], ids: dict[str, set[str]], issues: list[ValidationIssue]
) -> tuple[dict[int, str], dict[str, int], dict[int, set[str]]]:
    scope = _mapping(payload.get("调查范围"))
    brands = _mappings(scope.get("目标品牌"))
    target_by_name: dict[tuple[str, str], str] = {}
    for brand_index, item in enumerate(brands):
        name = item.get("原始名称")
        normalized = item.get("规范名称")
        identifier = item.get("品牌ID")
        if all(isinstance(value, str) for value in (name, normalized, identifier)):
            target_by_name[(name, normalized)] = identifier
        _check_evidence_refs(
            _strings(item.get("证据引用")),
            ids["EVD"],
            issues,
            _path("调查范围", "目标品牌", brand_index, "证据引用"),
            require_evidence=False,
        )
    for product_index, item in enumerate(_mappings(scope.get("代表性商品"))):
        _check_evidence_refs(
            _strings(item.get("证据引用")),
            ids["EVD"],
            issues,
            _path("调查范围", "代表性商品", product_index, "证据引用"),
            require_evidence=False,
        )

    review_brand: dict[int, str] = {}
    review_count: dict[str, int] = {}
    review_evidence: dict[int, set[str]] = {}
    for index, review in enumerate(_mappings(payload.get("品牌复核结果"))):
        display = _mapping(review.get("品牌"))
        brand_id = target_by_name.get((display.get("原始名称"), display.get("规范名称")))
        if brand_id is not None:
            review_brand[index] = brand_id
            review_count[brand_id] = review_count.get(brand_id, 0) + 1
        else:
            _issue(
                issues,
                _path("品牌复核结果", index, "品牌"),
                "OUT_OF_SCOPE_BRAND_REVIEW",
                "brand review does not match a target brand in the investigation scope",
            )
        paths = _strings(review.get("实际查询路径"))
        if not paths:
            _issue(issues, _path("品牌复核结果", index, "实际查询路径"), "EMPTY_QUERY_PATH", "brand review requires at least one actual query path")
        review_evidence[index] = {
            item["证据编号"]
            for item in _mappings(review.get("主要来源"))
            if isinstance(item.get("证据编号"), str)
        }
    for brand in brands:
        identifier = brand.get("品牌ID")
        if isinstance(identifier, str) and review_count.get(identifier, 0) != 1:
            _issue(issues, _path("品牌复核结果"), "BRAND_REVIEW_COVERAGE", f"{identifier} must have exactly one brand review")
    return review_brand, review_count, review_evidence


def _endpoint_exists(endpoint_type: Any, endpoint_id: Any, ids: dict[str, set[str]]) -> bool:
    prefixes = {"品牌": "BRD", "主体": "ENT", "商品": "PRD"}
    prefix = prefixes.get(endpoint_type)
    return isinstance(endpoint_id, str) and prefix is not None and endpoint_id in ids[prefix]


def _check_relationships(
    payload: Mapping[str, Any],
    ids: dict[str, set[str]],
    brand_evidence: Mapping[str, set[str]],
    issues: list[ValidationIssue],
) -> dict[str, set[str]]:
    entity_brands: dict[str, set[str]] = {identifier: set() for identifier in ids["ENT"]}
    expected_prefix = {"品牌": "BRD-", "主体": "ENT-", "商品": "PRD-"}
    time_states: dict[tuple[Any, ...], set[Any]] = {}
    for index, relation in enumerate(_mappings(payload.get("主体关系"))):
        relation_path = _path("主体关系", index)
        for side in ("起点", "终点"):
            endpoint_type = relation.get(f"{side}类型")
            endpoint_id = relation.get(f"{side}ID")
            if isinstance(endpoint_id, str) and endpoint_type in expected_prefix and not endpoint_id.startswith(expected_prefix[endpoint_type]):
                _issue(issues, relation_path, "RELATIONSHIP_ENDPOINT_TYPE_MISMATCH", f"{side}ID {endpoint_id} does not match {endpoint_type} endpoint type")
            if not _endpoint_exists(endpoint_type, endpoint_id, ids):
                _issue(issues, relation_path, "DANGLING_RELATIONSHIP_ENDPOINT", f"{side} endpoint does not identify a declared record")
        start_type, start_id = relation.get("起点类型"), relation.get("起点ID")
        end_type, end_id = relation.get("终点类型"), relation.get("终点ID")
        if start_type == "品牌" and end_type == "主体" and isinstance(start_id, str) and isinstance(end_id, str):
            entity_brands.setdefault(end_id, set()).add(start_id)
        if end_type == "品牌" and start_type == "主体" and isinstance(start_id, str) and isinstance(end_id, str):
            entity_brands.setdefault(start_id, set()).add(end_id)
        relation_brand = start_id if start_type == "品牌" else end_id if end_type == "品牌" else None
        _check_evidence_refs(
            _strings(relation.get("证据引用")),
            ids["EVD"],
            issues,
            relation_path,
            brand_evidence.get(relation_brand) if isinstance(relation_brand, str) else None,
        )
        if {start_type, end_type} == {"商品", "主体"} and (
            relation.get("关系类型") != "具体SKU制造商"
            or relation.get("适用层级") != "SKU级"
        ):
            _issue(
                issues,
                relation_path,
                "PRODUCT_ENTITY_RELATIONSHIP_NOT_SKU_MANUFACTURER",
                "product/entity relationships must be SKU-level specific SKU manufacturer relationships",
            )
        is_sku = relation.get("适用层级") == "SKU级" or relation.get("关系类型") == "具体SKU制造商"
        if is_sku:
            products = _strings(relation.get("适用商品ID"))
            if not products or any(product not in ids["PRD"] for product in products):
                _issue(issues, relation_path, "SKU_RELATIONSHIP_WITHOUT_PRODUCT", "SKU relationship requires at least one declared PRD product")
            endpoint_products = {
                endpoint_id
                for endpoint_type, endpoint_id in ((start_type, start_id), (end_type, end_id))
                if endpoint_type == "商品" and isinstance(endpoint_id, str)
            }
            if endpoint_products and not endpoint_products.issubset(products):
                _issue(issues, relation_path, "SKU_RELATIONSHIP_WITHOUT_PRODUCT", "SKU relationship product endpoints must be included in applicable products")
        signature = (
            relation.get("起点类型"), relation.get("起点ID"), relation.get("关系类型"),
            relation.get("终点类型"), relation.get("终点ID"), relation.get("适用层级"),
            tuple(sorted(_strings(relation.get("适用商品ID")))),
        )
        time_states.setdefault(signature, set()).add(relation.get("时间状态"))
    for signature, states in time_states.items():
        if len(states) > 1:
            _issue(issues, _path("主体关系"), "RELATIONSHIP_TIME_STATUS_CONFLICT", "one normalized relationship cannot combine current, historic, or uncertain time states")
    return entity_brands


def _check_review_views(
    payload: Mapping[str, Any],
    ids: dict[str, set[str]],
    review_brands: dict[int, str],
    review_evidence: dict[int, set[str]],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    issues: list[ValidationIssue],
) -> list[tuple[str, str, str]]:
    role_sections = {
        "商标权利人": ("商标权利人", {"商标权利人"}, "品牌级"),
        "品牌运营主体": ("品牌运营主体", {"品牌运营主体"}, "品牌级"),
        "母公司": ("母公司", {"母公司"}, "品牌级"),
        "收购与历史关系": ("收购与历史关系", {"历史权利人", "控制主体", "收购方"}, "品牌级"),
        "品牌层面主要制造商": ("品牌层面主要制造商", {"品牌层面制造商"}, "品牌级"),
        "具体SKU制造商": ("具体SKU制造商", {"具体SKU制造商"}, "SKU级"),
    }
    relation_section = {
        role: section
        for section, (_, roles, _) in role_sections.items()
        for role in roles
    }
    nested_facts: dict[tuple[Any, ...], list[str]] = defaultdict(list)
    normalized_facts: dict[tuple[Any, ...], list[str]] = defaultdict(list)
    nested_sku_candidates: dict[tuple[Any, ...], list[tuple[str, str]]] = defaultdict(list)
    product_bindings: list[tuple[str, str, str]] = []

    def fact_signature(
        brand_id: Any,
        entity_id: Any,
        section: str,
        link: Mapping[str, Any],
        level: Any,
        products: Iterable[str],
    ) -> tuple[Any, ...]:
        return (
            brand_id,
            entity_id,
            section,
            link.get("结论状态"),
            link.get("可靠性等级"),
            _ordered_strings(link.get("证据引用")),
            _ordered_strings(link.get("适用限制")),
            level,
            tuple(sorted(products)),
        )

    def sku_candidate_signature(
        entity_id: Any, link: Mapping[str, Any], products: Iterable[str]
    ) -> tuple[Any, ...]:
        return (
            entity_id,
            link.get("结论状态"),
            link.get("可靠性等级"),
            _ordered_strings(link.get("证据引用")),
            _ordered_strings(link.get("适用限制")),
            "SKU级",
            tuple(sorted(products)),
        )

    for review_index, review in enumerate(_mappings(payload.get("品牌复核结果"))):
        brand_id = review_brands.get(review_index)
        allowed_evidence = review_evidence.get(review_index, set())
        subject_relations = _mapping(review.get("主体关系"))
        for field in ("商标权利人", "品牌运营主体", "母公司", "收购与历史关系"):
            section, _, level = role_sections[field]
            for link_index, link in enumerate(_mappings(subject_relations.get(field))):
                link_path = _path("品牌复核结果", review_index, "主体关系", field, link_index)
                entity_id = link.get("主体ID")
                if entity_id not in ids["ENT"]:
                    _issue(issues, link_path, "DANGLING_NESTED_ENTITY", "nested entity reference does not identify a declared entity")
                _check_evidence_refs(_strings(link.get("证据引用")), ids["EVD"], issues, link_path, allowed_evidence)
                if link.get("结论状态") == "已确认" or link.get("可靠性等级") == "高":
                    hosts = _independent_source_hosts(_strings(link.get("证据引用")), evidence_by_id)
                    if len(hosts) < 2:
                        _issue(issues, link_path, "KEY_RELATION_NEEDS_INDEPENDENT_SOURCES", "key relationship marked confirmed/high requires at least two independent source domains")
                if brand_id is not None:
                    nested_facts[fact_signature(brand_id, entity_id, section, link, level, ())].append(link_path)

        manufacturing = _mapping(review.get("制造关系"))
        brand_manufacturers = _mappings(manufacturing.get("品牌层面主要制造商"))
        if brand_manufacturers and not _strings(manufacturing.get("SKU适用限制")):
            _issue(issues, _path("品牌复核结果", review_index, "制造关系", "SKU适用限制"), "BRAND_MANUFACTURER_WITHOUT_SKU_LIMITATION", "brand-level manufacturing requires a SKU applicability limitation")
        for field in ("品牌层面主要制造商", "具体SKU制造商"):
            section, _, level = role_sections[field]
            for link_index, link in enumerate(_mappings(manufacturing.get(field))):
                link_path = _path("品牌复核结果", review_index, "制造关系", field, link_index)
                if link.get("主体ID") not in ids["ENT"]:
                    _issue(issues, link_path, "DANGLING_NESTED_ENTITY", "nested entity reference does not identify a declared entity")
                _check_evidence_refs(_strings(link.get("证据引用")), ids["EVD"], issues, link_path, allowed_evidence)
                if field == "品牌层面主要制造商" and (link.get("结论状态") == "已确认" or link.get("可靠性等级") == "高"):
                    hosts = _independent_source_hosts(_strings(link.get("证据引用")), evidence_by_id)
                    if len(hosts) < 2:
                        _issue(issues, link_path, "KEY_RELATION_NEEDS_INDEPENDENT_SOURCES", "key relationship marked confirmed/high requires at least two independent source domains")
                if field == "具体SKU制造商":
                    products = _strings(link.get("适用商品ID"))
                    if not products or any(product not in ids["PRD"] for product in products):
                        _issue(issues, link_path, "SKU_MANUFACTURER_WITHOUT_PRODUCT", "SKU manufacturer requires at least one declared PRD product")
                    completeness = []
                    for product_id in products:
                        product = next((item for item in _mappings(_mapping(payload.get("调查范围")).get("代表性商品")) if item.get("商品ID") == product_id), {})
                        raw = str(_mapping(product.get("SKU证据核验")).get("证据完整度", "0/7"))
                        try:
                            completeness.append(int(raw.split("/", 1)[0]))
                        except (ValueError, IndexError):
                            completeness.append(0)
                    if completeness and min(completeness) < 2 and (link.get("结论状态") == "已确认" or link.get("可靠性等级") == "高"):
                        _issue(issues, link_path, "SKU_MANUFACTURER_EVIDENCE_TOO_WEAK", "specific SKU manufacturer marked confirmed/high while product evidence completeness is below 2/7")
                else:
                    products = []
                if brand_id is not None:
                    nested_facts[fact_signature(brand_id, link.get("主体ID"), section, link, level, products)].append(link_path)
                    if field == "具体SKU制造商":
                        nested_sku_candidates[sku_candidate_signature(link.get("主体ID"), link, products)].append((brand_id, link_path))

    for relation_index, relation in enumerate(_mappings(payload.get("主体关系"))):
        section = relation_section.get(relation.get("关系类型"))
        start_type, start_id = relation.get("起点类型"), relation.get("起点ID")
        end_type, end_id = relation.get("终点类型"), relation.get("终点ID")
        if section is None:
            continue
        if start_type == "品牌" and end_type == "主体":
            brand_id, entity_id = start_id, end_id
        elif start_type == "主体" and end_type == "品牌":
            brand_id, entity_id = end_id, start_id
        else:
            if (
                relation.get("关系类型") != "具体SKU制造商"
                or relation.get("适用层级") != "SKU级"
            ):
                continue
            if start_type == "商品" and end_type == "主体":
                product_id, entity_id = start_id, end_id
            elif start_type == "主体" and end_type == "商品":
                entity_id, product_id = start_id, end_id
            else:
                continue
            products = _strings(relation.get("适用商品ID"))
            relation_path = _path("主体关系", relation_index)
            if product_id not in products:
                _issue(issues, relation_path, "NORMALIZED_RELATIONSHIP_VIEW_MISMATCH", "SKU relationship endpoint product is absent from applicable products")
                continue
            candidates = nested_sku_candidates[sku_candidate_signature(entity_id, relation, products)]
            brands = {brand_id for brand_id, _ in candidates}
            if len(brands) == 0:
                _issue(issues, relation_path, "NORMALIZED_RELATIONSHIP_VIEW_MISMATCH", "product relationship has no identical nested SKU manufacturer fact")
                continue
            if len(brands) > 1:
                _issue(issues, relation_path, "AMBIGUOUS_PRODUCT_RELATIONSHIP_BRAND", "product relationship matches nested SKU manufacturer facts for multiple brands")
                continue
            brand_id = next(iter(brands))
            if isinstance(entity_id, str):
                product_bindings.append((brand_id, entity_id, "具体SKU制造商"))
        normalized_facts[
            fact_signature(
                brand_id,
                entity_id,
                section,
                relation,
                relation.get("适用层级"),
                _strings(relation.get("适用商品ID")),
            )
        ].append(_path("主体关系", relation_index))

    for signature in sorted(set(nested_facts) | set(normalized_facts), key=repr):
        nested_paths = nested_facts[signature]
        normalized_paths = normalized_facts[signature]
        for path in nested_paths[len(normalized_paths):]:
            _issue(issues, path, "NESTED_RELATIONSHIP_VIEW_MISMATCH", "nested brand fact has no identical normalized relationship")
        for path in normalized_paths[len(nested_paths):]:
            _issue(issues, path, "NORMALIZED_RELATIONSHIP_VIEW_MISMATCH", "normalized relationship has no identical nested brand fact")
    return product_bindings


def _check_entity_view(
    payload: Mapping[str, Any],
    entity_brands: dict[str, set[str]],
    product_bindings: list[tuple[str, str, str]],
    issues: list[ValidationIssue],
) -> None:
    relationships = _mappings(payload.get("主体关系"))
    bound_roles = {(brand_id, entity_id, role) for brand_id, entity_id, role in product_bindings}
    current_rank = {"历史": 0, "当前": 1, "不确定": 2}
    conclusion_rank = {"已确认": 0, "候选": 1, "证据不足": 2, "存在冲突": 3}
    reliability_rank = {"高": 0, "中": 1, "低": 2}
    for brand_id, entity_id, _ in product_bindings:
        entity_brands.setdefault(entity_id, set()).add(brand_id)
    for index, entity in enumerate(_mappings(payload.get("主体索引"))):
        entity_id = entity.get("主体ID")
        if not isinstance(entity_id, str):
            continue
        path = _path("主体索引", index)
        if set(_strings(entity.get("关联品牌"))) != entity_brands.get(entity_id, set()):
            _issue(issues, path, "ENTITY_BRAND_VIEW_MISMATCH", "entity associated brands do not match the normalized relationship view")
        actual_roles = set()
        for relation in relationships:
            start_type, start_id = relation.get("起点类型"), relation.get("起点ID")
            end_type, end_id = relation.get("终点类型"), relation.get("终点ID")
            role = relation.get("关系类型")
            if not isinstance(role, str):
                continue
            if start_type == "品牌" and end_type == "主体" and end_id == entity_id:
                actual_roles.add(role)
            elif start_type == "主体" and end_type == "品牌" and start_id == entity_id:
                actual_roles.add(role)
            elif any(bound_entity == entity_id and bound_role == role for _, bound_entity, bound_role in bound_roles):
                actual_roles.add(role)
        if set(_strings(entity.get("主体角色"))) != actual_roles:
            _issue(issues, path, "ENTITY_ROLE_VIEW_MISMATCH", "entity roles do not match the normalized relationship view")
        entity_relationships = [
            relation
            for relation in relationships
            if (
                relation.get("起点类型") == "主体"
                and relation.get("起点ID") == entity_id
            )
            or (
                relation.get("终点类型") == "主体"
                and relation.get("终点ID") == entity_id
            )
        ]
        if entity_relationships:
            expected_current = max(
                (relation.get("时间状态") for relation in entity_relationships),
                key=lambda value: current_rank.get(value, -1),
            )
            expected_conclusion = max(
                (relation.get("结论状态") for relation in entity_relationships),
                key=lambda value: conclusion_rank.get(value, -1),
            )
            expected_reliability = max(
                (relation.get("可靠性等级") for relation in entity_relationships),
                key=lambda value: reliability_rank.get(value, -1),
            )
            if entity.get("当前状态") != expected_current:
                _issue(issues, path, "ENTITY_CURRENT_STATUS_MISMATCH", "entity current status must conservatively summarize its relationships")
            if entity.get("结论状态") != expected_conclusion:
                _issue(issues, path, "ENTITY_CONCLUSION_STATUS_MISMATCH", "entity conclusion status must conservatively summarize its relationships")
            if entity.get("可靠性等级") != expected_reliability:
                _issue(issues, path, "ENTITY_RELIABILITY_MISMATCH", "entity reliability must conservatively summarize its relationships")
            relationship_evidence = {
                reference
                for relation in entity_relationships
                for reference in _strings(relation.get("证据引用"))
            }
            if not relationship_evidence.issubset(set(_strings(entity.get("证据引用")))):
                _issue(issues, path, "ENTITY_EVIDENCE_COVERAGE_MISMATCH", "entity evidence must cover all evidence used by its relationships")
        _check_evidence_refs(_strings(entity.get("证据引用")), set().union(*[
            {item.get("证据编号")} for review in _mappings(payload.get("品牌复核结果")) for item in _mappings(review.get("主要来源")) if isinstance(item.get("证据编号"), str)
        ]), issues, path)


def _check_overall_classification(
    payload: Mapping[str, Any], ids: dict[str, set[str]], issues: list[ValidationIssue]
) -> None:
    for index, item in enumerate(_mappings(payload.get("总体复核分级"))):
        for brand_id in _strings(item.get("品牌")):
            if brand_id not in ids["BRD"]:
                _issue(
                    issues,
                    _path("总体复核分级", index, "品牌"),
                    "DANGLING_OVERALL_CLASSIFICATION_BRAND",
                    f"{brand_id} does not identify a target brand",
                )


def _check_confirmation(payload: Mapping[str, Any], issues: list[ValidationIssue], require_confirmed: bool) -> None:
    confirmation = _mapping(payload.get("用户确认"))
    confirmed = confirmation.get("是否确认")
    fields = ("确认时间", "用户确认原文", "内容摘要哈希")
    values = [confirmation.get(field) for field in fields]
    path = _path("用户确认")
    if confirmed is False:
        if any(value is not None for value in values):
            _issue(issues, path, "UNCONFIRMED_FIELDS_NOT_NULL", "unconfirmed payload must keep confirmation fields null")
        if require_confirmed:
            _issue(issues, path, "NOT_CONFIRMED", "report requires explicit confirmation")
    elif confirmed is True:
        if any(not isinstance(value, str) or not value.strip() for value in values):
            _issue(issues, path, "CONFIRMED_FIELDS_MISSING", "confirmed payload requires non-empty confirmation fields")
        elif confirmation.get("内容摘要哈希") != compute_content_hash(payload):
            _issue(issues, path, "CONFIRMATION_HASH_MISMATCH", "confirmation hash does not match report facts")
    elif require_confirmed:
        _issue(issues, path, "NOT_CONFIRMED", "report requires explicit confirmation")


def _check_research_gate(payload: Mapping[str, Any], issues: list[ValidationIssue]) -> None:
    records = _mappings(payload.get("网络检索记录"))
    text = " ".join(str(item.get("入口URL", "")) + " " + str(item.get("访问结果", "")) for item in records).lower()
    official = any(any(token in text for token in ("uspto", "wipo", "cipo", "euipo", "nhtsa", "监管", "官方登记")) for _ in [0])
    brand_official = any(any(token in text for token in ("about", "terms", "warranty", "product", "manufacturer")) for _ in [0])
    if len(records) < 2 or not official or not brand_official:
        _issue(issues, "网络检索记录", "RESEARCH_GATE_NOT_MET", "requires recorded official registry/regulatory and brand/product official searches")


def _check_sku_completeness(payload: Mapping[str, Any], issues: list[ValidationIssue]) -> None:
    keys = ("包装标签", "产品铭牌", "型号或UPC", "说明书Manufacturer", "说明书Importer", "平台销售字段", "合规或监管文件")
    for index, product in enumerate(_mappings(_mapping(payload.get("调查范围")).get("代表性商品"))):
        checklist = _mapping(product.get("SKU证据核验"))
        count = sum(1 for key in keys if _mapping(checklist.get(key)).get("状态") == "已取得")
        expected = f"{count}/7"
        if checklist.get("证据完整度") != expected:
            _issue(issues, _path("调查范围", "代表性商品", index, "SKU证据核验", "证据完整度"), "SKU_COMPLETENESS_MISMATCH", f"expected {expected}, got {checklist.get('证据完整度')}")


def _check_quality_summary(payload: Mapping[str, Any], issues: list[ValidationIssue]) -> None:
    expected = build_quality_summary(payload)
    actual = payload.get("质量摘要")
    if actual != expected:
        _issue(issues, _path("质量摘要"), "QUALITY_SUMMARY_MISMATCH", "quality summary must match deterministic facts derived from the payload")


def validate_payload(
    payload: Mapping[str, Any], schema_path: Path | None = None, require_confirmed: bool = False
) -> list[ValidationIssue]:
    if not isinstance(payload, Mapping):
        return [ValidationIssue("$", "SCHEMA_ERROR", "payload must be an object")]
    issues = _schema_issues(payload, schema_path or DEFAULT_SCHEMA_PATH)
    ids = _declared_ids(payload, issues)
    evidence_by_id = {
        str(item.get("证据编号")): item
        for review in _mappings(payload.get("品牌复核结果"))
        for item in _mappings(review.get("主要来源"))
        if isinstance(item.get("证据编号"), str)
    }
    review_brands, _, review_evidence = _brand_review_ids(payload, ids, issues)
    brand_evidence = {
        brand_id: review_evidence[review_index]
        for review_index, brand_id in review_brands.items()
    }
    entity_brands = _check_relationships(payload, ids, brand_evidence, issues)
    product_bindings = _check_review_views(payload, ids, review_brands, review_evidence, evidence_by_id, issues)
    _check_entity_view(payload, entity_brands, product_bindings, issues)
    _check_overall_classification(payload, ids, issues)
    _check_research_gate(payload, issues)
    _check_sku_completeness(payload, issues)
    _check_quality_summary(payload, issues)
    _check_confirmation(payload, issues, require_confirmed)
    return sorted(set(issues))


def assert_valid_payload(
    payload: Mapping[str, Any], schema_path: Path | None = None, require_confirmed: bool = False
) -> None:
    issues = validate_payload(payload, schema_path=schema_path, require_confirmed=require_confirmed)
    if issues:
        lines = [f"{issue.code} {issue.path} {issue.message}" for issue in issues]
        raise ValueError("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an evidence review JSON payload.")
    parser.add_argument("json_path", type=Path)
    parser.add_argument("--schema-path", type=Path)
    parser.add_argument("--require-confirmed", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"JSON_READ_ERROR {args.json_path} {error}")
        return 1
    issues = validate_payload(payload, args.schema_path, args.require_confirmed)
    if issues:
        for issue in issues:
            print(f"{issue.code} {issue.path} {issue.message}")
        return 1
    print(f"VALID: {args.json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
