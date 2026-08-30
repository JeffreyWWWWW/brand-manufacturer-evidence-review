"""Deterministic quality summary derived from an evidence review payload."""

from __future__ import annotations

from urllib.parse import urlparse
from typing import Any, Mapping


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mappings(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _host(url: Any) -> str:
    if not isinstance(url, str):
        return ""
    return urlparse(url).netloc.lower().removeprefix("www.").split(":")[0]


def build_quality_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    scope = _mapping(payload.get("调查范围"))
    products = _mappings(scope.get("代表性商品"))
    product_by_id = {item.get("商品ID"): item for item in products}
    reviews = _mappings(payload.get("品牌复核结果"))
    brands = _mappings(scope.get("目标品牌"))
    brand_summary: list[dict[str, Any]] = []
    total_conflicts = 0
    total_followups = 0
    for brand in brands:
        key = (brand.get("原始名称"), brand.get("规范名称"))
        review = next((item for item in reviews if (_mapping(item.get("品牌")).get("原始名称"), _mapping(item.get("品牌")).get("规范名称")) == key), {})
        sources = _mappings(review.get("主要来源"))
        hosts = {_host(item.get("URL")) for item in sources if _host(item.get("URL"))}
        subject_relations = _mapping(review.get("主体关系"))
        covered_roles = [role for role in ("商标权利人", "品牌运营主体", "母公司", "收购与历史关系") if _mappings(subject_relations.get(role))]
        manufacturing = _mapping(review.get("制造关系"))
        covered_roles.extend(role for role in ("品牌层面主要制造商", "具体SKU制造商") if _mappings(manufacturing.get(role)))
        sku_summary = []
        for product in products:
            checklist = _mapping(product.get("SKU证据核验"))
            sku_summary.append({"商品ID": product.get("商品ID"), "证据完整度": checklist.get("证据完整度")})
        conflict_count = sum(1 for text in _strings(review.get("关键说明")) if "冲突" in text)
        followup_count = sum(1 for text in [str(_mapping(review.get("结论评价")).get("人工复核建议", "")), *(_strings(review.get("关键说明")))] if "冲突" not in text and any(token in text for token in ("补充", "补证", "待核实", "待确认", "未取得")))
        followup_count += sum(1 for claim in _mappings(payload.get("主张证据矩阵")) if claim.get("结论状态") in {"候选", "证据不足", "存在冲突"} and claim.get("下一步补证"))
        total_conflicts += conflict_count
        total_followups += followup_count
        brand_summary.append({"品牌ID": brand.get("品牌ID"), "主要来源数": len(sources), "独立来源域名数": len(hosts), "关键角色覆盖": covered_roles, "SKU证据完整度": sku_summary, "冲突数": conflict_count, "待补证数": followup_count})
    return {"品牌": brand_summary, "总体": {"品牌数量": len(brands), "冲突数": total_conflicts, "待补证数": total_followups}}
