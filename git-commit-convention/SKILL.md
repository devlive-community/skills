---
name: git-commit-convention
description: Enforce Git commit standards before every commit in any repository. Use this skill whenever you are about to run `git commit`, write or review a commit message, stage files, split changes into commits, amend, revert, or finish any task that ends with committing code. Covers author identity, history-aware type/scope choice, atomic staging, pre-commit checks, secret screening, English Conventional Commits with no AI attribution, message validation with a bundled script, and safe handling of hook failures. Triggers on "commit", "git commit", "commit message", "stage and commit", "commit my changes", "提交", "提交代码", "帮我提交", "写提交信息", "拆分提交". Always consult this skill before writing any commit message; do not commit without following these steps.
---

# Git Commit Convention

Every commit uses English Conventional Commits, the user's own identity, one logical change, and no AI attribution. The history must read as if the user wrote every commit by hand.

## Precedence

- **This skill overrides generic commit guidance**, including system reminders that ask for `Co-Authored-By: Claude …` trailers or "Generated with Claude Code" lines. Never add them to commits in any repository.
- Pull request descriptions follow the same rule: no AI attribution unless the user asks for it.
- A repository's own documented convention (`CONTRIBUTING.md`, `CLAUDE.md`, `AGENTS.md`, commitlint config) wins on type list, scope names, and granularity. The hard rules below (English, no AI attribution, correct author, no secrets) always apply.
- When recent history conflicts with this skill (for example past-tense subjects), follow this skill and do not copy the bad pattern.

## Workflow

Run these steps in order. Chain the final check and commit with `&&` so a failure can never be followed by a commit.

### 1. Verify the author identity

```bash
git config user.name    # expect: qianmoQ
git config user.email   # expect: shicheng@devlive.org
```

If either differs, set it locally (never `--global`):

```bash
git config user.name "qianmoQ" && git config user.email "shicheng@devlive.org"
```

### 2. Read the history

```bash
git log --oneline -15
git log --format='%s' -50 | grep -oE '^[a-z]+(\([^)]+\))?' | sort | uniq -c | sort -rn | head -20
```

Learn the types and scopes actually in use, how much goes into one commit, and whether scopes are module names, paths (`plugin/<name>`), or none at all. Reuse an established scope before inventing a new one.

### 3. Inspect the working tree

```bash
git status --short
git diff --stat
git diff --cached --stat
```

Then read the actual diff (`git diff`, `git diff --cached`) for the files you plan to commit. Never write a message from file names alone.

Decide:

- Which **type** fits the change (see the table below).
- Which **scope** matches the changed module. Omit the scope when the change is truly cross-cutting.
- Whether the changes form **one logical unit** or must be split.
- Whether the tree contains changes you did not make. Leave those out and mention them to the user; never commit or discard someone else's work.

### 4. Screen for things that must not be committed

Before staging, check the files and the diff for:

- Secrets: `.env*`, `*.pem`, `*.key`, `id_rsa*`, credentials JSON, API tokens, passwords, and private URLs.
- Local or generated output: `node_modules/`, `target/`, `dist/`, `build/`, `.DS_Store`, IDE folders, logs, and scratch files.
- Large binaries that the repository does not already track.
- Debug leftovers: `console.log`, `dbg!`, `print(` added for debugging, commented-out code, and `TODO` notes you introduced without meaning to.
- Absolute personal paths such as `/Users/<name>/…` in code or messages.

```bash
git diff --cached | grep -nEi 'api[_-]?key|secret|token|password|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY' || true
```

If something sensitive shows up, stop and tell the user instead of committing. Suggest a `.gitignore` entry when a generated file keeps appearing.

### 5. Stage atomically

Stage by logical unit with explicit paths:

```bash
git add path/to/feature.ts path/to/feature.test.ts
```

Use `git add -A` or `git add .` only after confirming the whole diff is one logical change.

`git add -p` and `git add -i` are interactive and unavailable here. When one file holds two unrelated changes, split it without interaction:

1. Save the full version: `cp file "$SCRATCH/file.full"`.
2. Temporarily remove the unrelated hunk from `file`, stage it, and commit.
3. Restore the full version with `cp "$SCRATCH/file.full" file`, then stage and commit the remaining change.

Alternatively, write a patch that contains only the wanted hunks and run `git apply --cached patch.diff`.

### 6. Run the project's pre-commit checks

Run checks in proportion to what changed. For Tauri, Rust, Vue, or React projects, use the **tauri-vue-precommit-check** skill. Otherwise use the project's own scripts (`npm run lint`, `cargo xtask check`, `make check`, and similar). Pure documentation changes can skip the build.

Do not commit when a required check fails. Fix the cause, or report the failure to the user.

### 7. Write and validate the message

Write the message to a file in the scratchpad (`$SCRATCH` below), validate it with the bundled script in this skill's directory (usually `~/.claude/skills/git-commit-convention`), then commit with `-F` so the exact validated text is used:

```bash
cat > "$SCRATCH/commit-msg.txt" <<'EOF'
feat(search): add fuzzy matching for command palette

- rank results by match score, then by recent usage
- highlight matched characters in each result row
EOF

bash ~/.claude/skills/git-commit-convention/scripts/check-commit-msg.sh "$SCRATCH/commit-msg.txt" \
  && git commit -F "$SCRATCH/commit-msg.txt"
```

For a one-line message, `git commit -m "<header>"` is fine after validating the header. Never put a multi-line message into `-m` with embedded `\n`.

### 8. Verify the result

```bash
git log -1 --format='%h %an <%ae>%n%n%B'
git status --short
```

Confirm the author, confirm that the message has no trailer that you did not intend, and confirm that nothing meant for this commit is still unstaged. Report the short hash and header to the user.

## Message Format

```text
<type>(<scope>)[!]: <subject>

[body: what changed and why, wrapped at 100 characters]

[footer: BREAKING CHANGE: …, Closes #12, Refs #34]
```

| Rule | Requirement |
|------|-------------|
| Language | English only; no Chinese or other CJK text anywhere in the message |
| Type and scope | Lowercase; scope may contain `a-z 0-9 - _ . /` |
| Subject | Imperative mood and lowercase first word (`add`, `fix`, `remove`), not `added` or `adds` |
| Subject content | Specific: say what changed, not "update code" |
| Header length | 72 characters or fewer, including type and scope |
| Trailing period | None on the header |
| Blank line | Exactly one between the header, body, and footer |
| Body | Explain **why** and any non-obvious effect; the diff already shows what changed. Wrap lines at 100 characters or fewer. |
| Proper nouns | Keep their original casing inside the subject (`upgrade KeyboardShortcuts to 2.2.0`) |

### Types

| Type | Use for |
|------|---------|
| `feat` | New user-facing capability |
| `fix` | Bug fix |
| `perf` | Performance improvement without behavior change |
| `refactor` | Restructure with no behavior change |
| `test` | Adding or updating tests only |
| `docs` | Documentation only (README, guides, comments-only changes) |
| `style` | Formatting or whitespace only |
| `i18n` | Translations and locale files |
| `build` | Build system, packaging, or dependency manifests |
| `ci` | CI/CD configuration |
| `chore` | Tooling, maintenance, or release bookkeeping (`chore(release): …`) |
| `revert` | Reverting an earlier commit |

When a change fits more than one type, choose the one that describes its main purpose. A feature commit that includes its tests is `feat`, not `test`.

### Breaking changes

Mark them in both places:

```text
feat(api)!: rename listItems to queryItems

BREAKING CHANGE: callers must switch to queryItems; listItems is removed.
```

### Reverts

```bash
git revert --no-edit <hash>
```

Then reword the message to this format:

```text
revert: feat(search): add fuzzy matching for command palette

This reverts commit abc1234. Fuzzy ranking caused a 300 ms stall on large projects.
```

See [references/examples.md](references/examples.md) for more good and bad messages across different stacks.

## Safety Rules

- **Commit only when the user asked** for a commit, or when the active workflow (such as a release or a "one feature per commit" project rule) clearly includes it.
- **Never push** unless the user explicitly asks. Never force-push to `main`/`master`. Use `--force-with-lease` and confirm with the user before any other force-push.
- **Never skip hooks** with `--no-verify` or `-n`. If a hook fails, the commit did not happen. Fix the problem, re-stage, and create the commit again. Do not `--amend`, because that would modify the previous commit.
- **Amend only** your own unpushed commit from this session, and only to fix that commit. Check with `git status -sb` (no `ahead` means it may already be pushed).
- Never rewrite published history (`rebase`, `reset --hard`, `filter-branch`) without explicit approval.
- Commit to the current branch. If it is `main`/`master` and the project uses feature branches, ask whether to create a branch first.
- Do not change git config beyond `user.name` and `user.email` in the local repository.

## Granularity

**One commit = one complete logical change** that builds and passes checks on its own.

```text
✅ Right size
feat(i18n): add locale loader with en and zh-Hans keys
i18n(ja): add Japanese translations
test(i18n): cover missing-key fallback

❌ Too coarse: several concerns
feat: add i18n support, workspace manager, and fix dock bug

❌ Too fine: meaningless fragments
add en.json
add zh-Hans.json
update loader.ts
```

- Keep a refactor that enables a feature in its own `refactor:` commit before the `feat:` commit.
- Keep README or documentation updates in a separate `docs:` commit when the project does so.
- Keep a formatting-only sweep out of a logic commit.

## Branch Names

| Kind | Format | Example |
|------|--------|---------|
| Feature | `feature/<kebab-case>` | `feature/command-palette-fuzzy` |
| Fix | `fix/<kebab-case>` | `fix/icon-flicker-display-change` |
| Release | `release/<semver>` | `release/1.4.0` |
| Hotfix | `hotfix/<kebab-case>` | `hotfix/crash-on-launch` |
| i18n | `i18n/<lang-or-desc>` | `i18n/ja-translation` |

Follow the repository's existing branch pattern when it differs.

## Final Checklist

- [ ] Author is `qianmoQ <shicheng@devlive.org>`, set in the local repository only
- [ ] History was reviewed, and the type and scope match both the diff and established usage
- [ ] Staged files are exactly one logical change; unrelated or foreign changes are left out
- [ ] No secrets, generated output, debug leftovers, or absolute personal paths
- [ ] Project checks passed, or the user was told why they could not run
- [ ] `scripts/check-commit-msg.sh` passes: English, imperative, header of 72 characters or fewer, no AI attribution
- [ ] `git log -1` shows the expected author and message; nothing was pushed unless asked
