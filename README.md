# Brand Manufacturer Evidence Review

用于复核产品品牌与商标权利人、品牌运营主体、母公司及制造商之间的证据关系。该插件区分品牌层面与具体 SKU 的制造证据，并在用户确认后生成可追溯的 JSON 底稿和 DOCX 报告。

## 安装

需要支持插件的 Codex CLI 或 ChatGPT 桌面端 Codex。

```powershell
codex plugin marketplace add JeffreyWWWWW/brand-manufacturer-evidence-review --ref main
codex plugin add brand-manufacturer-evidence-review@brand-manufacturer-evidence-review
```

也可以先添加 marketplace，然后在 Codex 中输入 `/plugins`，选择 `Brand Manufacturer Evidence Review` 并安装。安装完成后新建一个任务，使 Codex 加载插件中的 skill。

首次执行时，skill 会运行 `scripts/check_runtime_dependencies.py`。如果本地 Python 缺少 `jsonschema` 或 `python-docx`，该检查会输出基于插件内 `requirements-runtime.txt` 的精确安装命令。

可选配置 Tavily 作为检索增强器：设置环境变量 `TAVILY_API_KEY` 后，skill 可运行 `scripts/tavily_search.py` 发现第二来源、历史页面和产品文件；未设置时不影响正常调查。Tavily 摘要只能作为候选线索，最终证据仍需回到原始网页、官方登记或可定位的 PDF。PowerShell 示例：

```powershell
$env:TAVILY_API_KEY = "tvly-..."
python plugins\brand-manufacturer-evidence-review\skills\brand-manufacturer-evidence-review\scripts\tavily_search.py "CURT manufacturer"
```

适配器使用 `advanced` 搜索并默认返回 20 条候选结果；可通过 `--max-results` 下调数量。Agent 会优先核验官方域名、监管数据库、PDF 和独立来源域名，并过滤重复或低价值候选。适配器使用标准库调用 Tavily REST API，不新增运行时依赖；网络超时、HTTP 错误或未配置密钥时会返回可记录的状态，不会阻断没有 Tavily 的正常调查。

最终 JSON 还会包含自动计算的 `质量摘要`，汇总每个品牌的来源覆盖、独立域名数、SKU 证据完整度、冲突和待补证数量；验证器会拒绝与事实不一致的手工摘要。

## 使用

skill 支持显式和自动触发。需要确定使用它时，在新任务中写出
`$brand-manufacturer-evidence-review`；自动触发则由 Codex 根据请求语义和 skill
描述判断，不是固定关键词匹配。

以下请求通常会自动触发：

- “帮我查这个品牌背后是谁，商标属于哪家公司，实际由谁运营和生产？”
- “核验这批商品的品牌方、母公司和代工厂，区分品牌级信息与具体 SKU 证据。”
- “包装标签写了 Manufactured by XXX，这能否证明它是该 SKU 的制造商？”
- “复核品牌、商标权利人、运营主体、OEM/ODM 之间的证据链，并生成 JSON 和 DOCX 报告。”

以下请求不应仅因出现“品牌”“商标”“制造商”等词而触发：

- 只做商标注册或近似商标检索；
- 只做专利检索、FTO 或侵权风险分析；
- 只调查法人代表、创始人、高管或技术负责人；
- 只收集供应商、工厂或经销商名单，不判断其与目标品牌的法律或制造证据关系。

“帮我查这个品牌”或“找一下制造商”缺少调查目标，可能需要补充说明。最好明确要求核验品牌与法律主体、制造主体之间的关系及证据层级。

完整示例：

> 请复核这些产品品牌对应的商标权利人、运营主体、母公司和制造商，区分品牌级与具体 SKU 证据。

插件会先在对话中展示证据摘要。只有在用户明确确认后，才会写入最终 JSON 并由该 JSON 生成 DOCX。

每个新任务的首次响应会在调查报告前显示当前插件 skill 版本（`Skill 版本：<version>`）。版本读取自 `.codex-plugin/plugin.json`；最终 JSON 顶层的 `Skill版本` 和 DOCX“报告说明”会保存同一值。JSON 中的 `规范版本` 是数据规范版本，含义不同，继续单独保留。

正式文件名由调查范围和调查日期确定：单品牌使用规范品牌名，多品牌使用 `N品牌`，固定格式为 `<范围>_品牌权属与制造商证据复核报告_<YYYYMMDD>.docx`，底稿使用对应的“证据底稿”中缀。生成器会拒绝不符合该格式或 JSON/DOCX 范围、日期不一致的输出路径。

## 获取更新

```powershell
codex plugin marketplace upgrade brand-manufacturer-evidence-review
codex plugin add brand-manufacturer-evidence-review@brand-manufacturer-evidence-review
```

升级并重新安装后新建一个任务，以加载新版本。

## 开发与发布

插件清单位于 `plugins/brand-manufacturer-evidence-review/.codex-plugin/plugin.json`。更新 skill 时，同步按 SemVer 修改其 `version`，在开发分支运行测试和插件校验，再将更改合并至 `main`。公开 `main` 分支不包含仓库测试目录。

```powershell
$env:PYTHONUTF8 = "1"
python "$env:CODEX_HOME\skills\.system\plugin-creator\scripts\validate_plugin.py" plugins\brand-manufacturer-evidence-review
python "$env:CODEX_HOME\skills\.system\skill-creator\scripts\quick_validate.py" plugins\brand-manufacturer-evidence-review\skills\brand-manufacturer-evidence-review
```

macOS 或 Linux：

```bash
PYTHONUTF8=1 python "$CODEX_HOME/skills/.system/plugin-creator/scripts/validate_plugin.py" plugins/brand-manufacturer-evidence-review
PYTHONUTF8=1 python "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" plugins/brand-manufacturer-evidence-review/skills/brand-manufacturer-evidence-review
```

Marketplace 入口位于 `.agents/plugins/marketplace.json`，因此该 GitHub 仓库本身就是可被 Codex 添加和升级的插件来源。
