# Skill 版本显示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让每次新任务和最终 JSON/DOCX 报告都能追溯实际执行的插件 skill 版本。

**Architecture:** 以 `.codex-plugin/plugin.json` 的 `version` 为唯一权威版本源。skill 文档规定首次响应展示版本；JSON Schema 要求顶层 `Skill版本`；DOCX 渲染器从 JSON 读取该字段并在“报告说明”展示，避免渲染器维护第二份版本号。

**Tech Stack:** Markdown skill 文档、JSON Schema、Python `jsonschema`、Python `python-docx`、现有验证与渲染脚本。

## Global Constraints

- 版本唯一来源为 `.codex-plugin/plugin.json` 的 `version`，本次更新值为 `1.0.4`。
- `Skill版本` 表示执行 skill 版本；`规范版本` 表示 JSON 数据规范版本，二者均保留。
- 缺少 `Skill版本` 的 JSON 必须被 Schema 拒绝，不生成正式 DOCX。
- DOCX 页脚继续只显示页码，版本仅在“报告说明”出现。
- 不改变用户确认流程和确定性输出文件名规则。

### Task 1: Extend JSON version contract

**Files:**
- Modify: `plugins/brand-manufacturer-evidence-review/skills/brand-manufacturer-evidence-review/references/evidence-review.schema.json`
- Test: `qa_vevor/test_schema_contract.py` (or nearest existing schema test file)

**Interfaces:**
- Produces a top-level required JSON string field named `Skill版本`.

- [ ] **Step 1: Write the failing test**

Add tests that load the schema and assert a valid payload with `Skill版本: "1.0.3"` passes while removing `Skill版本` produces a validation error mentioning the required property.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -q qa_vevor/test_schema_contract.py`

Expected: the missing-field test fails because the schema does not yet require `Skill版本`.

- [ ] **Step 3: Write minimal schema change**

Add `Skill版本` to the root `required` list and map it to the existing non-empty `freeText` definition in `properties`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -q qa_vevor/test_schema_contract.py`

Expected: all schema contract tests pass.

- [ ] **Step 5: Commit**

```powershell
git add plugins/brand-manufacturer-evidence-review/skills/brand-manufacturer-evidence-review/references/evidence-review.schema.json qa_vevor/test_schema_contract.py
git commit -m "feat: require skill version in evidence payloads"
```

### Task 2: Render version metadata in DOCX

**Files:**
- Modify: `plugins/brand-manufacturer-evidence-review/skills/brand-manufacturer-evidence-review/scripts/render_evidence_review_report.py`
- Test: `qa_vevor/test_report_rendering.py` (or nearest existing renderer test file)

**Interfaces:**
- `add_report_note(document, payload, tokens)` reads `payload["Skill版本"]` and `payload["规范版本"]` and emits both labels.

- [ ] **Step 1: Write the failing test**

Add a renderer test that builds the existing minimal confirmed payload with `Skill版本: "1.0.3"`, renders a DOCX, extracts paragraph text, and asserts both `Skill版本：1.0.3` and the existing `规范版本` label are present.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -q qa_vevor/test_report_rendering.py`

Expected: failure because the renderer currently omits `Skill版本` and `规范版本` from “报告说明”.

- [ ] **Step 3: Write minimal renderer change**

In `add_report_note`, add `_add_label_value` calls for `Skill版本` and `规范版本` before confirmation metadata. Do not alter footer configuration.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -q qa_vevor/test_report_rendering.py`

Expected: renderer tests pass and the generated DOCX remains readable.

- [ ] **Step 5: Commit**

```powershell
git add plugins/brand-manufacturer-evidence-review/skills/brand-manufacturer-evidence-review/scripts/render_evidence_review_report.py qa_vevor/test_report_rendering.py
git commit -m "feat: include skill version in report notes"
```

### Task 3: Document runtime display and validate the package

**Files:**
- Modify: `plugins/brand-manufacturer-evidence-review/skills/brand-manufacturer-evidence-review/SKILL.md`
- Modify: `plugins/brand-manufacturer-evidence-review/skills/brand-manufacturer-evidence-review/agents/openai.yaml`
- Modify: `README.md`

**Interfaces:**
- Skill instructions require the first response of each new task to show `Skill 版本：<manifest version>` before the report.
- Agent prompt and README explain the distinction between `Skill版本` and `规范版本`.

- [ ] **Step 1: Update the skill contract**

Add an explicit “版本标识” section near the response/report requirements. State that the version is read from `.codex-plugin/plugin.json`, shown once in the first response, copied to JSON `Skill版本`, and rendered in DOCX “报告说明”.

- [ ] **Step 2: Update the default prompt and README**

Mention the first-response version line and the two distinct report fields without hard-coding a second version source.

- [ ] **Step 3: Run package validation**

Run:

```powershell
$env:PYTHONUTF8 = "1"
python "$env:CODEX_HOME\skills\.system\plugin-creator\scripts\validate_plugin.py" plugins\brand-manufacturer-evidence-review
python "$env:CODEX_HOME\skills\.system\skill-creator\scripts\quick_validate.py" plugins\brand-manufacturer-evidence-review\skills\brand-manufacturer-evidence-review
pytest -q qa_vevor
```

Expected: plugin validation, skill validation, and all QA tests pass.

- [ ] **Step 4: Commit**

```powershell
git add plugins/brand-manufacturer-evidence-review/skills/brand-manufacturer-evidence-review/SKILL.md plugins/brand-manufacturer-evidence-review/skills/brand-manufacturer-evidence-review/agents/openai.yaml README.md
git commit -m "docs: document skill version visibility"
```
