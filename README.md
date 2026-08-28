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

## 使用

在新任务中提供产品、品牌和商品链接或原始调查材料，例如：

> 请复核这些产品品牌对应的商标权利人、运营主体、母公司和制造商，区分品牌级与具体 SKU 证据。

插件会先在对话中展示证据摘要。只有在用户明确确认后，才会写入最终 JSON 并由该 JSON 生成 DOCX。

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
