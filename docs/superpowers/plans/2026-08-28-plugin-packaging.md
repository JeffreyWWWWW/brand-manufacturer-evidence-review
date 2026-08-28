# Plugin Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing root-level skill into an installable, GitHub-backed Codex plugin marketplace without changing its evidence-review behavior.

**Architecture:** Keep one canonical copy of the skill under `plugins/brand-manufacturer-evidence-review/skills/brand-manufacturer-evidence-review/`. A repository marketplace points to the plugin, while repository-level tests add the relocated skill root to Python's import path and exercise the same scripts and resources.

**Tech Stack:** JSON manifests, Markdown skill instructions, Python 3.11, pytest, jsonschema, python-docx

**Spec:** `docs/superpowers/specs/2026-08-28-plugin-packaging-design.md`

## Global Constraints

- Plugin and skill identifiers remain `brand-manufacturer-evidence-review`.
- The initial plugin version is strict SemVer `1.0.0`.
- The marketplace source path is `./plugins/brand-manufacturer-evidence-review`.
- Existing evidence-review behavior and relative skill resource paths remain unchanged.
- No generated release archive or duplicated skill copy is added.
- No push is performed.

---

### Task 1: Define The Plugin Packaging Contract

**Files:**
- Create: `tests/test_plugin_packaging.py`
- Create: `.agents/plugins/marketplace.json`
- Create: `plugins/brand-manufacturer-evidence-review/.codex-plugin/plugin.json`

**Interfaces:**
- Consumes: repository root and standard Codex marketplace layout
- Produces: valid JSON manifests whose plugin name, local source, skill path, and declared assets resolve consistently

- [ ] **Step 1: Write the failing packaging test**

Create tests that load both JSON files, require matching plugin identifiers,
assert version `1.0.0`, assert source path `./plugins/brand-manufacturer-evidence-review`,
and resolve the declared `skills` path and all interface asset paths inside the plugin.

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_plugin_packaging.py -q`

Expected: failure because `.agents/plugins/marketplace.json` does not exist.

- [ ] **Step 3: Add minimal valid manifests**

Create a one-entry marketplace and a skills-only plugin manifest with real
repository metadata and user-facing interface fields. Do not declare MCP,
apps, hooks, screenshots, or license files that do not exist.

- [ ] **Step 4: Run the packaging test**

Run: `python -m pytest tests/test_plugin_packaging.py -q`

Expected: plugin-path assertions still fail because the skill has not moved.

### Task 2: Relocate The Skill Without Behavioral Changes

**Files:**
- Move: `SKILL.md`, `agents/`, `assets/`, `references/`, `scripts/`
- Create: `tests/conftest.py`
- Modify: `tests/test_skill_contract.py`
- Modify: `tests/test_schema.py`
- Modify: `tests/test_render_evidence_review_report.py`
- Modify: `tests/test_validate_evidence_review.py`

**Interfaces:**
- Consumes: `PLUGIN_ROOT` and `SKILL_ROOT` path constants in `tests/conftest.py`
- Produces: importable `scripts` package and executable script paths at the relocated skill root

- [ ] **Step 1: Move the skill tree mechanically**

Move all runtime files to
`plugins/brand-manufacturer-evidence-review/skills/brand-manufacturer-evidence-review/`
without changing their contents.

- [ ] **Step 2: Point tests at the relocated root**

In `tests/conftest.py`, insert the absolute skill root at the start of
`sys.path`. Replace repository-root resource and CLI paths in affected tests
with the same plugin skill root.

- [ ] **Step 3: Run packaging and contract tests**

Run: `python -m pytest tests/test_plugin_packaging.py tests/test_skill_contract.py tests/test_public_repository.py -q`

Expected: all selected tests pass.

### Task 3: Document Installation And Make Verification Reproducible

**Files:**
- Create: `README.md`
- Create: `requirements-dev.txt`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: GitHub repository `JeffreyWWWWW/brand-manufacturer-evidence-review` and marketplace name from the manifest
- Produces: exact install, refresh, local validation, and maintainer release instructions

- [ ] **Step 1: Add user and maintainer instructions**

Document `codex plugin marketplace add JeffreyWWWWW/brand-manufacturer-evidence-review --ref main`,
plugin installation through `/plugins`, `codex plugin marketplace upgrade`,
new-task discovery, and SemVer release updates.

- [ ] **Step 2: Declare test dependencies**

Add `pytest`, `jsonschema`, and `python-docx` to `requirements-dev.txt` and
ignore only generated caches and outputs, not repository tests.

- [ ] **Step 3: Run complete validation**

Run the full pytest suite with the declared dependencies, then run
`validate_plugin.py` against the plugin root and `quick_validate.py` against
the nested skill root.

Expected: all commands exit zero.

- [ ] **Step 4: Review and commit**

Inspect `git diff --check`, the complete branch diff from `058df16`, and Git
status. Commit the implementation only after fresh verification succeeds.
