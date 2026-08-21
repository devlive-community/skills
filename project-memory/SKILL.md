---
name: project-memory
description: Persist user habits, preferences, project conventions, and every completed feature in the current project's .claude/ directory so Claude Code remembers them across sessions. Use whenever the user says "记住", "记一下", "记到记忆里", "永久记忆", "别忘了", "下次也这样", "这是我的习惯/规范", or asks to remember something, and after completing or modifying a feature, making a technical decision, or discovering a project convention. Store each feature in a separate file and review existing project memory before starting new work.
---

# Project Memory

Persist information worth retaining in the current project's `.claude/` directory so Claude Code automatically remembers it the next time the project is opened.

## Why `.claude/`

Claude Code automatically loads `./CLAUDE.md` or `./.claude/CLAUDE.md` from the project root. These files can use `@relative-path` syntax to import other files inline. Relative paths are resolved from the directory containing `CLAUDE.md`, with up to five levels of nesting.

Memory takes effect automatically in the next session only when it is stored in this `CLAUDE.md`-imported structure. An arbitrary file elsewhere will not be loaded. Machine-local auto memory under `~/.claude/projects/...` does not travel with the repository, cannot be committed, and is not visible to the team, so it does not satisfy the requirement for permanent project memory. This skill always writes to the project's `.claude/` directory.

## Directory Structure

Maintain this structure under the project root, creating it when necessary:

```text
project/.claude/
├── CLAUDE.md                 # Memory entry point; imports always-loaded memory
└── memory/
    ├── preferences.md        # User habits and preferences
    ├── conventions.md        # Project conventions
    ├── decisions.md          # Important technical decisions and rationale; optional
    └── features/
        ├── INDEX.md          # Lightweight, always-loaded feature index
        ├── <feature-name>.md # One file per feature
        └── ...
```

Import `preferences.md`, `conventions.md`, and `features/INDEX.md` so they are always loaded. Do not import individual feature files. Read them only when relevant, using the index, so accumulated feature details do not consume the entire context window.

## First-Time Initialization

1. Identify the project root: usually the level containing `.git`, `package.json`, `Cargo.toml`, or `src/`.
2. If `.claude/CLAUDE.md` does not exist, create it from the template below. If it exists, do not overwrite it; append only missing import lines.
3. Create `.claude/memory/`, `preferences.md`, `conventions.md`, and `features/INDEX.md` using the templates below. Empty placeholders are acceptable initially.
4. Run `date +%F` and use its output for timestamps. Never invent a date.

Use this `.claude/CLAUDE.md` entry-point template:

```markdown
# Project Memory Entry Point

> This file is maintained by project-memory and loaded automatically by Claude Code.
> Do not remove the import lines below. Append imports here for any new always-loaded memory.

## Always-Loaded Memory
- User habits and preferences: @memory/preferences.md
- Project conventions: @memory/conventions.md
- Feature memory index: @memory/features/INDEX.md

Detailed feature memory is stored in `memory/features/<feature-name>.md`. Read it when needed using the index above.
```

`@` imports are not resolved inside code blocks or inline code. Import lines in the actual entry-point file must be ordinary Markdown text without backticks.

## Route Each Memory Item

Store information in the most appropriate file rather than putting everything in one place:

- **User habit or personal preference** → `memory/preferences.md`
  Examples: prefers Simplified Chinese replies, English commit messages without AI attribution, end-to-end delegation with fewer questions, DeepSeek for code generation, or concise communication.
- **Project-wide convention or team rule** → `memory/conventions.md`
  Examples: Conventional Commits, directory structure, naming rules, technology choices, lint or CI requirements, and prohibited patterns.
- **Feature implementation memory** → `memory/features/<feature-name>.md`
  Examples: user authentication, token usage statistics, diet recommendations, or a multi-cloud storage adapter. Keep one feature per file.
- **Important technical decision and rationale** → `memory/decisions.md`
  Use this only for major cross-feature trade-offs. Otherwise, record the rationale in the relevant feature file.

When uncertain, route personal information to `preferences.md`, repository-specific working rules to `conventions.md`, and implementation details to a feature file.

## Record a Feature

After completing or significantly modifying a feature:

1. Choose a kebab-case filename such as `user-authentication.md`, `token-usage-stats.md`, or `diet-recommendation.md`. Keep one feature per file.
2. Write or update `memory/features/<feature-name>.md` using the feature template.
3. Add or update its row in `memory/features/INDEX.md` so a later session can locate it quickly.
4. If the feature file already exists, update it in place: merge the current implementation, remove obsolete details, and refresh the date.

Feature file template:

```markdown
# Feature: <display name> (<feature-slug>)

## Overview
In one or two sentences, explain what the feature does and which problem it solves.

## Key Implementation
- Technology / dependencies:
- Core files and locations:
- Data flow / architecture:

## Conventions and Caveats
- Special conventions:
- Known pitfalls / edge cases:

## Related Decisions
- Rationale and trade-offs:

_Last updated: <YYYY-MM-DD>_
```

`features/INDEX.md` template:

```markdown
# Feature Memory Index

> Add or update one row whenever a feature is completed or modified. See the linked file for details.

| Feature | File | Summary | Updated |
|---------|------|---------|---------|
| User authentication | user-authentication.md | JWT with refresh tokens | 2026-07-31 |
```

## Writing Rules

- **Read before writing.** Inspect the target file first, then update or merge instead of blindly appending. Avoid duplicates and contradictions. Do not repeat an existing preference unless it has changed.
- **Explicit memory requests are mandatory.** When the user says "记住", "记一下", "记到记忆里", "永久记忆", "别忘了", or otherwise explicitly asks to remember something, write it immediately to the appropriate file and confirm the write. Do not merely promise in chat.
- **Keep memory concise and actionable.** Record conventions, preferences, pitfalls, and rationale that will be useful next time. Do not copy large directory trees or dependency lists that are already obvious from the code.
- **Use real timestamps.** Run `date +%F`; do not invent dates.
- **Keep the entry point valid.** When adding a new category of always-loaded memory, add its import to `.claude/CLAUDE.md`. Do not import individual feature files; list them in `features/INDEX.md`.
- **Assume memory is committable.** Project memory is meant to travel with the repository and be shared with the team. If the user says an item is private and must not be committed, store it under `.claude/memory/`, add that specific file to the project's `.gitignore`, and tell the user.

## Recall Before Starting Work

Before beginning a new task, use existing memory:

- Always-loaded memory in `preferences.md`, `conventions.md`, and `features/INDEX.md` should already be available. Align the work with it.
- If the task involves an indexed feature, locate and read its `features/<feature-name>.md` file before changing the implementation.
- If memory conflicts with the current code, confirm the discrepancy with the user before updating the memory to match.

## Examples

**User:** "以后提交信息一律用英文，作者 qianmoQ，不要带 AI 署名，记住。"

**Action:** Update the commit conventions section in `memory/conventions.md` with English-only commits, author `qianmoQ`, and no AI attribution. Run `date +%F` for the update date, then confirm the write.

**User:** "刚做完的这个 Token 用量统计功能记一下。"

**Action:** Create `memory/features/token-usage-stats.md` from the feature template and add a row to `features/INDEX.md`, then confirm the files written.

**User:** "我喜欢你直接给结果，别问一堆问题。"

**Action:** Record the preference for direct delivery and fewer follow-up questions in `memory/preferences.md`, including the current date.
