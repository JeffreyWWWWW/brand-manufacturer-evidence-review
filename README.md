# Brand Manufacturer Evidence Review

一个用于 Codex 的品牌与制造商证据复核插件。它调查产品品牌背后的法律主体和制造关系，区分品牌层面的公开事实与具体 SKU 的制造证据，并在用户确认后生成可追溯、可校验的 JSON 底稿和 DOCX 报告。

当前插件版本：`1.1.3`

## 核心能力

- 识别并复核商标权利人、品牌运营主体、母公司或控制主体；
- 调查制造商、生产商及 OEM/ODM 关系；
- 核验包装标签、铭牌、说明书、商品页和监管文件中的制造主体；
- 区分品牌级制造信息与具体 SKU 制造证据，避免过度推断；
- 保留来源、原文摘录、页面定位、证据等级、结论状态和适用限制；
- 显式披露证据不足、待核实事项和来源冲突；
- 自动计算来源覆盖、SKU 证据完整度、冲突数和待补证数等质量指标；
- 由同一份已确认 JSON 生成结果导向的 DOCX 报告。

## 证据原则

插件不会把商业品牌名直接等同于法律主体，也不会仅凭搜索摘要、模型记忆或用户截图确认关键关系。

- 调查至少核验一个官方登记或监管来源，以及一个品牌或产品官方来源；
- 关键关系原则上需要两个独立来源域名交叉验证，单一来源不能评为高可靠性；
- 搜索摘要、Marketplace、Amazon、经销商页面及 Tavily 结果仅作为候选线索；
- 具体 SKU 的制造结论必须有包装、型号、UPC、说明书或监管文件等产品级证据支撑；
- 无法确认的结论标记为“证据不足/待核实”，可靠来源相互矛盾时保留冲突；
- 只有用户明确确认调查内容后，插件才生成最终文件。

## 适用范围

适合以下任务：

- 调查“品牌背后是谁”；
- 核验品牌方、商标权利人、运营主体和母公司之间的关系；
- 查明产品由谁制造，或复核 OEM/ODM、代工厂关系；
- 判断包装上的 `Manufactured by`、`Distributed by` 或 `Imported by` 能证明什么；
- 对一批商品开展品牌权属与制造商证据复核；
- 生成可供后续审计或结构化处理的 JSON 底稿与 DOCX 报告。

以下任务不属于本插件的主要范围：

- 纯商标注册或近似商标检索；
- 专利检索、FTO 或侵权风险分析；
- 只调查法定代表人、创始人、高管或技术负责人；
- 只收集供应商、工厂或经销商名单，不判断其与目标品牌的证据关系。

## 安装

需要支持插件的 Codex CLI 或 Codex 桌面端。

```powershell
codex plugin marketplace add JeffreyWWWWW/brand-manufacturer-evidence-review --ref main
codex plugin add brand-manufacturer-evidence-review@brand-manufacturer-evidence-review
```

也可以先添加 marketplace，然后在 Codex 中输入 `/plugins`，选择 `Brand Manufacturer Evidence Review` 并安装。安装完成后，请新建任务以加载插件中的 skill。

首次运行时，插件会检查 Python 运行依赖。如果缺少 `jsonschema` 或 `python-docx`，检查脚本会根据插件内的 `requirements-runtime.txt` 给出安装命令。

## 快速开始

### 1. 发起调查

在新任务中显式调用 skill：

```text
$brand-manufacturer-evidence-review

请复核这些产品品牌对应的商标权利人、运营主体、母公司和制造商，区分品牌级与具体 SKU 证据。
```

也可以直接描述调查需求，由 Codex 根据请求语义自动判断是否调用。为了减少补充确认，建议同时提供：

- 目标品牌和产品名称；
- 商品链接、型号、UPC 或 SKU；
- 包装、铭牌、说明书或标签图片；
- 需要核验的国家、地区或时间范围；
- 已知公司名称及需要重点确认的关系。

### 2. 审阅调查报告

插件首先在对话中返回完整的中文调查报告，包括主体关系、制造关系、证据等级、结论、限制和补证建议。每个新任务的首次报告前会显示从插件清单读取的 `Skill 版本`。

此时仍不会生成最终文件。请检查事实、法律主体、证据和表述；如需修改，直接指出具体问题。

### 3. 确认并生成文件

确认报告内容后回复：

```text
确认生成文件
```

插件随后校验结构化数据、质量摘要和输出文件名，并由最终 JSON 生成 DOCX。正式交付物为：

```text
outputs/<项目或品牌范围>_品牌权属与制造商证据底稿_<YYYYMMDD>.json
outputs/<项目或品牌范围>_品牌权属与制造商证据复核报告_<YYYYMMDD>.docx
```

JSON 是可追溯的事实底稿和后续处理的权威数据源；DOCX 是便于阅读和交付的结果报告。两者使用相同的调查范围、日期和事实基础。

## 可选：Tavily 检索增强

设置环境变量 `TAVILY_API_KEY` 后，插件可使用 Tavily 发现第二来源、历史页面、产品 PDF、收购公告和制造商线索。未配置 Tavily 不影响正常调查。

PowerShell 示例：

```powershell
$env:TAVILY_API_KEY = "tvly-..."
python plugins\brand-manufacturer-evidence-review\skills\brand-manufacturer-evidence-review\scripts\tavily_search.py "CURT manufacturer"
```

适配器默认使用 `advanced` 搜索并返回最多 20 条候选结果，可通过 `--max-results` 下调数量。它使用 Python 标准库调用 Tavily REST API，不需要安装 Tavily SDK。

Tavily 返回的摘要和链接只用于发现线索。形成正式证据前，仍需回到原始网页、官方登记或可定位的 PDF 核验；Tavily 错误或未配置密钥不会阻断其他官方来源的调查流程。

## 获取更新

```powershell
codex plugin marketplace upgrade brand-manufacturer-evidence-review
codex plugin add brand-manufacturer-evidence-review@brand-manufacturer-evidence-review
```

升级并重新安装后，请新建任务以加载新版本。

## 项目结构

```text
.
├── .agents/plugins/marketplace.json
├── plugins/brand-manufacturer-evidence-review/
│   ├── .codex-plugin/plugin.json
│   └── skills/brand-manufacturer-evidence-review/
│       ├── SKILL.md
│       ├── agents/openai.yaml
│       ├── assets/report-style/
│       ├── references/
│       ├── scripts/
│       └── requirements-runtime.txt
├── tests/
├── pytest.ini
└── README.md
```

- `.codex-plugin/plugin.json`：插件清单、版本和界面元数据；
- `SKILL.md`：调查工作流、证据门槛和交付规则；
- `references/`：JSON Schema 与证据复核规则；
- `scripts/`：依赖检查、检索适配、质量摘要、校验和 DOCX 渲染工具；
- `assets/report-style/`：报告样式配置；
- `tests/`：插件行为与数据约束测试。

## 开发与验证

更新插件时，应按 SemVer 同步修改 `plugins/brand-manufacturer-evidence-review/.codex-plugin/plugin.json` 中的 `version`，并确保 README、skill 行为、JSON Schema 和测试保持一致。

运行测试：

```powershell
$env:PYTHONUTF8 = "1"
python -m pytest
```

验证插件和 skill：

```powershell
$env:PYTHONUTF8 = "1"
python "$env:CODEX_HOME\skills\.system\plugin-creator\scripts\validate_plugin.py" plugins\brand-manufacturer-evidence-review
python "$env:CODEX_HOME\skills\.system\skill-creator\scripts\quick_validate.py" plugins\brand-manufacturer-evidence-review\skills\brand-manufacturer-evidence-review
```

macOS 或 Linux：

```bash
PYTHONUTF8=1 python -m pytest
PYTHONUTF8=1 python "$CODEX_HOME/skills/.system/plugin-creator/scripts/validate_plugin.py" plugins/brand-manufacturer-evidence-review
PYTHONUTF8=1 python "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" plugins/brand-manufacturer-evidence-review/skills/brand-manufacturer-evidence-review
```

Marketplace 入口位于 `.agents/plugins/marketplace.json`，因此本 GitHub 仓库本身可作为 Codex 插件的安装与更新来源。
