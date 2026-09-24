# Commit Message Examples

## Good

Single-line feature:

```text
feat(dock-engine): add multi-row layout calculation
```

Feature with a body that explains the change:

```text
feat(plugin/json-formatter): add streaming parse for files over 50 MB

Loading the whole file into a String froze the UI on large inputs.
Parse with serde_json::StreamDeserializer and report progress every 1 MB
through the task log channel.

Closes #88
```

Bug fix whose body explains the cause:

```text
fix(dock-engine): prevent icon flicker when external display connects

The overlay window was recreated on every screen-parameter notification,
which caused a brief flash. It now diffs existing windows against the new
screen list and only rebuilds the ones that changed.

Fixes #47
```

Refactor, tests, and documentation as separate commits:

```text
refactor(settings): extract persistence into SettingsStore
test(settings): cover migration from v1 schema
docs: document settings storage location in README
```

i18n, build, CI, and release commits:

```text
i18n(ja): add Japanese translations for settings and errors
build: upgrade tauri to 2.3.0
ci: cache cargo registry in release workflow
chore(release): prepare 1.4.0
chore(release): start 1.5.0 development
```

Breaking change:

```text
feat(api)!: rename listItems to queryItems

BREAKING CHANGE: callers must switch to queryItems; listItems is removed.
```

Revert:

```text
revert: feat(search): add fuzzy matching for command palette

This reverts commit abc1234. Fuzzy ranking stalled large projects by 300 ms.
```

Cross-cutting change with no scope:

```text
style: apply rustfmt 2024 edition formatting
```

## Bad → Fixed

| Bad | Problem | Fixed |
|-----|---------|-------|
| `feat: 实现多行 Dock 布局` | Chinese text | `feat(dock): add multi-row layout` |
| `feat(dock): added multi-row layout` | Past tense | `feat(dock): add multi-row layout` |
| `feat(dock): adds multi-row layout` | Third person | `feat(dock): add multi-row layout` |
| `Feat(Dock): Add layout.` | Uppercase and trailing period | `feat(dock): add layout` |
| `fix: fix bug` | Vague | `fix(search): return empty list instead of null on no match` |
| `update code` / `wip` | No type and no meaning | Describe the actual change |
| `feat: add i18n and workspace manager and fix dock bug` | Several concerns | Split into three commits |
| `feat: add layout in /Users/john/Desktop/app` | Absolute personal path | `feat(dock): add layout engine` |
| Trailer `Co-Authored-By: Claude <noreply@anthropic.com>` | AI attribution | Remove the trailer |
| `feat(dock): add multi-row layout with configurable column count and automatic wrapping` | Header is over 72 characters | Shorten the header and move the details into the body |
