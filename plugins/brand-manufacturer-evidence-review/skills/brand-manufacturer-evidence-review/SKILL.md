---
name: brand-manufacturer-evidence-review
description: 复核产品品牌与商标权利人、品牌运营主体、母公司及制造商之间的证据关系，并输出规范化 JSON 底稿和 DOCX 报告。适用于需要识别品牌背后法律主体或区分品牌级与具体 SKU 制造证据的任务。
---

# 品牌与制造商证据复核

电商页面以商业品牌和商品名组织，企业、商标、专利等调查对象则按法律主体组织；商业名称不能替代法律主体。为使结论可复核和复用，需要保存准确法律名称、司法辖区、角色、当前/历史状态、证据及适用限制。

读取原始客户材料，登记 `SRC-xxx` 来源，提取产品、商品和目标品牌；按照 [证据复核规则](references/review-rules.md) 调查并构建符合 [JSON Schema](references/evidence-review.schema.json) 的草稿。

在对话中展示品牌、主体角色、制造范围、可靠性、证据和限制的完整摘要。用户修正后重新校验；只有用户明确确认时才写入最终 JSON。沉默不构成确认。

运行 `scripts/check_runtime_dependencies.py` 检查运行依赖。如果缺失依赖，先按其输出的命令从 `requirements-runtime.txt` 安装；然后使用 `scripts/validate_evidence_review.py` 校验最终 JSON。校验通过且用户确认一致后，使用 `scripts/render_evidence_review_report.py` 仅从该 JSON 生成 DOCX，并逐页渲染检查。

最终交付：

- `outputs/brand-manufacturer-evidence-review.json`
- `outputs/brand-manufacturer-evidence-review.docx`
