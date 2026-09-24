---
name: project-memory
description: Persist user habits, preferences, project conventions, technical decisions, and every completed feature in the current project's .claude/ directory so Claude Code remembers them across sessions and the team can see them in git. Use whenever the user says "记住", "记一下", "记到记忆里", "永久记忆", "别忘了", "下次也这样", "以后都这样", "这是我的习惯/规范", "remember this", or asks to remember or forget something; after completing, changing, or removing a feature; after making a technical decision or discovering a project convention; and before starting new work, to recall existing memory. Store each feature in a separate file, keep always-loaded memory small, and never store memory only in machine-local auto memory.
---

# Project Memory

Persist information worth keeping in the current project's `.claude/` directory, so Claude Code loads it automatically the next time the project is opened and the team can see it in git.

## Why `.claude/`

Claude Code automatically loads `./CLAUDE.md` and `./.claude/CLAUDE.md` from the project root. These files can pull in other files with `@relative/path` imports. Paths resolve relative to the importing file, and imports can nest up to five levels deep.

Memory only loads in the next session when it is reachable through that import chain. A file anywhere else is ignored. Machine-local auto memory under `~/.claude/projects/...` does not travel with the repository and cannot be committed or shared, so it does **not** satisfy a "permanent project memory" request. This skill always writes to the project's `.claude/`. Do not duplicate the same items into auto memory, because two sources drift apart.

## Directory Structure

```text
project/.claude/
├── CLAUDE.md                 # Entry point: imports always-loaded memory
└── memory/
    ├── preferences.md        # User habits and preferences (always loaded)
    ├── conventions.md        # Project conventions (always loaded)
    ├── decisions.md          # Major cross-feature decisions (optional; read on demand)
    └── features/
        ├── INDEX.md          # One row per feature (always loaded)
        └── <feature-slug>.md # One file per feature (read on demand)
```

Only `preferences.md`, `conventions.md`, and `features/INDEX.md` are imported. Feature files and `decisions.md` are read when a task touches them, so accumulated detail never floods the context window.

## Setup and Health Check

The bundled script lives in this skill's directory (usually `~/.claude/skills/project-memory`):

```bash
bash ~/.claude/skills/project-memory/scripts/memory.sh init    # create missing files; never overwrites
bash ~/.claude/skills/project-memory/scripts/memory.sh check   # imports, index sync, git-ignore, size, secrets
```

The project root defaults to the git top level. Pass a path as the second argument for a nested package that the user wants to keep separate memory for.

`init` creates the entry point, templated `preferences.md` and `conventions.md`, and an empty `features/INDEX.md`. If `.claude/CLAUDE.md` already exists, it only appends missing import lines. An existing root `CLAUDE.md` is left untouched, since both files load.

Run `check` after writing memory. It reports:

- missing or backtick-wrapped imports (`@` imports are **not** resolved inside inline code or code blocks);
- feature files without an index row, and index rows without a file;
- always-loaded memory over about 400 lines;
- text that looks like a secret;
- memory files that `.gitignore` excludes.

**If memory is git-ignored** (many projects ignore all of `.claude/`), memory silently stops being shared. Tell the user, and propose narrowing the rule instead of deleting it:

```gitignore
.claude/*
!.claude/CLAUDE.md
!.claude/memory/
```

Keep `.claude/settings.local.json` ignored.

## Route Each Memory Item

| What | Where | Examples |
|------|-------|----------|
| How the user likes to work | `memory/preferences.md` | Reply in Simplified Chinese; deliver end to end with few questions; concise answers; preferred model or tool |
| Rules for this repository | `memory/conventions.md` | Commit format and author, directory layout, naming, tech choices, lint/CI gates, prohibited patterns |
| How a feature is built | `memory/features/<slug>.md` | Authentication, token usage stats, multi-cloud storage adapter |
| Major cross-feature trade-off | `memory/decisions.md` | Picking SQLite over JSON files for all storage; dropping Windows 7 support |

Tie-breakers:

- If a rule is about **the code or repository** (anyone contributing must follow it), it goes in `conventions.md`, even when the user states it as a personal habit. Commit rules are conventions.
- If it is about **how Claude should interact with the user**, it goes in `preferences.md`.
- If it only matters for one feature, put it in that feature's file, including the rationale, instead of `decisions.md`.
- If the user says the rule applies to **all projects**, record it here and also mention once that `~/.claude/CLAUDE.md` is the place for truly global instructions. Do not edit that file without being asked.

## What Not to Record

- Secrets, tokens, passwords, private URLs, or customer data. Memory is committed and shared.
- Anything the code, `git log`, or README already states plainly: dependency lists, directory trees, change history.
- Temporary task state ("currently fixing X", "next step: Y"). Use a todo list or the conversation instead.
- Guesses. Record what was decided or verified, not what you assume.
- Relative dates. Convert "next Friday" to an absolute date.

## Record a Feature

After completing, significantly changing, or removing a feature:

1. Choose a stable kebab-case slug that matches how the codebase names the feature (`user-authentication`, `token-usage-stats`). If a file already exists for this feature, reuse it rather than creating a near-duplicate.
2. Write or update `memory/features/<slug>.md` from the template below. When updating, merge in the current state, delete obsolete details, and refresh the date. Do not append a changelog.
3. Add or update the feature's row in `features/INDEX.md`, keeping its summary to one line.
4. **Renamed feature:** rename the file and update the index row. **Removed feature:** delete the file and the row. Keep any lesson that still applies by moving it to `conventions.md` or `decisions.md`.
5. Run `memory.sh check`.

Feature file template:

```markdown
# Feature: <Display Name> (<feature-slug>)

## Overview
One or two sentences: what it does and which problem it solves.

## Key Implementation
- Entry points / core files: `path/to/file.ts` (`FunctionName`)
- Data flow / architecture:
- Storage / external APIs:

## Conventions and Caveats
- Rules specific to this feature:
- Known pitfalls and edge cases:

## Related Decisions
- Why it is built this way and what was rejected:

_Last updated: <YYYY-MM-DD>_
```

Refer to code by file path and symbol name, not line numbers, which go stale quickly.

`features/INDEX.md` row format:

```markdown
| Feature | File | Summary | Updated |
|---------|------|---------|---------|
| User authentication | user-authentication.md | JWT access + refresh tokens, stored in keychain | 2026-07-31 |
```

## Record a Decision

Append to `memory/decisions.md`, newest first:

```markdown
## <YYYY-MM-DD> — <Decision title>
- **Context:** what forced the choice
- **Decision:** what was chosen
- **Alternatives rejected:** and why
- **Consequences:** what this commits the project to
```

When a decision is reversed, mark the old entry `Superseded by <date>` instead of deleting it.

## Writing Rules

- **Explicit requests are mandatory and immediate.** When the user says "记住", "记一下", "别忘了", or otherwise asks to remember something, write it to the right file in the same turn and confirm the exact file and wording. Do not just promise to remember.
- **Read before writing.** Read the target file first. Update or merge instead of blindly appending. Remove duplicates and contradictions. When a preference changes, replace the old line instead of keeping both.
- **Forget on request.** When the user says "忘掉", "不用记了", or "forget X", delete the item and confirm.
- **Keep it short and actionable.** Write one bullet per rule and phrase it as an instruction ("Use pnpm, never npm"). Keep always-loaded files well under 400 lines combined and move detail into feature files.
- **Use real dates.** Run `date +%F`; never invent a date.
- **Keep the entry point valid.** Add an import line when you introduce a new always-loaded file. Never import individual feature files.
- **Private items:** if the user says an item must not be committed, put it in `.claude/memory/private.md`, import it from the entry point, add that exact path to `.gitignore`, and tell the user.

## Committing Memory

Memory files are ordinary project files. Commit them only when the user asked for commits or the active workflow includes them, and always through the **git-commit-convention** skill.

- Follow the repository's established pattern. Without one, keep memory out of the feature commit and commit it separately, for example `docs(memory): record token usage stats feature`.
- A memory-only change for an explicit "记住" request does not need a commit unless the user asks for one. Mention that the change is uncommitted.

## Recall Before Starting Work

- The always-loaded files should already be in context. Follow them, because they carry the same weight as the project's own instructions.
- If the task touches an indexed feature, read its feature file before changing code. Read `decisions.md` before reversing an architectural choice.
- If memory conflicts with the current code, trust the code for facts. Confirm with the user before changing a rule, then update the memory so the conflict does not recur.
- To confirm what is loaded, the user can run `/memory` in Claude Code.

## Examples

**User:** "以后提交信息一律用英文，作者 qianmoQ，不要带 AI 署名，记住。"
**Action:** These are repository rules, so update the "Git and Commits" section of `memory/conventions.md`: English-only Conventional Commits, author `qianmoQ <shicheng@devlive.org>`, no AI attribution trailers. Refresh the date and confirm the file and lines written.

**User:** "我喜欢你直接给结果，别问一堆问题。"
**Action:** This is how the user wants Claude to interact, so add "Deliver end to end; ask only when a decision is genuinely the user's" under Workflow in `memory/preferences.md`, then confirm.

**User:** "刚做完的这个 Token 用量统计功能记一下。"
**Action:** Read the implementation, create `memory/features/token-usage-stats.md` from the template, add its row to `features/INDEX.md`, run `memory.sh check`, and report the files written.

**User:** "旧的导出功能删掉了，记忆也清一下。"
**Action:** Delete `memory/features/legacy-export.md` and its index row. Move any still-relevant pitfall to `conventions.md`, then run `memory.sh check`.
