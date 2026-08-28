# Brand Manufacturer Evidence Review Plugin Packaging

## Goal

Package the existing `brand-manufacturer-evidence-review` skill as a standard,
skills-only Codex plugin that other users can install from this public GitHub
repository and refresh when the repository publishes an update.

## Repository Layout

The repository becomes a single-plugin marketplace:

```text
.agents/plugins/marketplace.json
plugins/brand-manufacturer-evidence-review/
  .codex-plugin/plugin.json
  skills/brand-manufacturer-evidence-review/
    SKILL.md
    agents/openai.yaml
    assets/report-style/business-report-style.json
    references/evidence-review.schema.json
    references/review-rules.md
    scripts/__init__.py
    scripts/render_evidence_review_report.py
    scripts/validate_evidence_review.py
README.md
requirements-dev.txt
tests/
```

The current root-level skill files move under the plugin's `skills/` directory.
This makes relative links in `SKILL.md` continue to work while removing the old
root-skill installation shape. Repository-level tests remain outside the plugin
archive and resolve the new skill root through a shared test constant.

## Plugin And Marketplace Metadata

`.codex-plugin/plugin.json` provides a stable plugin identifier, a strict SemVer
version, repository and author information, and user-facing interface metadata.
It declares `./skills/` as the bundled skill directory. The initial packaged
version is `1.0.0` because the repository already has a public release.

`.agents/plugins/marketplace.json` exposes the plugin as an available
Productivity entry. Its local source path is `./plugins/brand-manufacturer-evidence-review`,
following the Codex repository-marketplace convention.

## Distribution And Updates

Users add the GitHub repository as a marketplace pinned to `main`, install the
plugin from that marketplace, and start a new Codex task so bundled skills are
discovered. The README documents both the Plugins Directory flow and exact CLI
commands.

The maintainer updates files in this repository and increments the manifest
version using SemVer. Users refresh the Git-backed marketplace and reinstall or
upgrade the plugin as supported by their Codex surface, then start a new task.
No generated release archive or duplicated copy of the skill is maintained.

## Validation And Tests

Tests first assert the intended marketplace, manifest, and relocated skill
contract, then the implementation moves the files and updates test paths.
Validation includes:

- the existing Python behavior and end-to-end report tests;
- JSON parsing and semantic checks for both marketplace and plugin manifests;
- verification that every declared plugin path exists inside the package;
- the built-in plugin validator;
- the skill validator against the relocated skill directory;
- a clean-worktree check after commits.

`requirements-dev.txt` records the packages needed to run the repository test
suite so validation is reproducible on a fresh checkout.

## Branch And Merge

Implementation occurs on `codex/package-as-plugin` in an isolated worktree based
on commit `058df16`. This preserves the user's unrelated staged deletions in the
original checkout. After verification, the feature branch is merged into `main`
with a non-interactive Git merge; no push is performed unless separately
requested.
