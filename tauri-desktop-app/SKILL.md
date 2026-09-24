---
name: tauri-desktop-app
description: Standard for building cross-platform desktop apps with Tauri 2 + Rust + React (the Forge family such as ToolForge, and any new desktop project). Use this skill whenever creating or changing a Tauri/Rust desktop app - scaffolding a workspace, adding a feature, tool or plugin, wiring i18n, persistence, long-running tasks, downloads/resources, window chrome, quit confirmation, about page, auto-update, CI or release scripts. Core rules - all data processing in Rust; everything is a plugin; SQLite is the only local storage; every UI string is translated (Rust returns error codes only); work over ~300 ms runs as a cancellable task with live logs; Rust tests live in separate *_test.rs files; semantic Tailwind tokens and custom components only; one feature per commit. Triggers include "tauri", "desktop app", "桌面应用", "桌面端", "plugin", "插件", "i18n", "国际化", "auto update", "在线更新", "release", "发布", "Forge".
---

# Tauri Desktop App Standard

A production-proven way to build fast, secure, lightweight desktop apps with **Tauri 2 + Rust + React 19**.
The reference implementation is **ToolForge** (`/Users/shicheng/Code/toolforge`); when in doubt, read how it does it.

## Non-negotiable rules

| # | Rule | Enforced by |
|---|------|-------------|
| 1 | **All data processing happens in Rust.** Parsing, formatting, encoding, hashing, crypto, regex, diff, conversion, image, file and network I/O. The frontend only collects input and renders results. | ESLint `no-restricted-imports/globals/syntax` + convention scanner |
| 2 | **Everything is a plugin**, built-ins included. The host hard-codes no feature: it discovers plugins from a registry and loads their UI, icon and locales by convention. | Code review; host code must not import a plugin by name |
| 3 | **SQLite is the only local storage** (rusqlite in the app data dir). No `localStorage` / `sessionStorage` / `IndexedDB` / cookies. | ESLint + scanner |
| 4 | **Every user-visible string is translated** (react-i18next). Rust never returns human text, only `{ code, params }` for errors and log lines. | `i18next/no-literal-string` (JSX text) |
| 5 | **Anything that can take > ~300 ms runs as a task**: its own thread, streamed logs, progress, stages, cancellable, persisted history. | Design review |
| 6 | **Large results stay in Rust.** Return a bounded preview + stats; copy/save full data via an id-based plugin call. Never push MBs through IPC or render them at once. | Design review |
| 7 | **Rust tests are in separate `xxx_test.rs` files**, never inline `mod tests {}`. | Scanner rule `rust-inline-tests` |
| 8 | **UI uses semantic Tailwind tokens and in-house components only**, with no raw palette, hex, `dark:` or native `<select>`/checkbox/dialog. Follow the global **tailwind-token-ui** skill. | Scanner rules `raw-palette`, `dark-variant`, `native-controls` |
| 9 | **Plugin / app ids use reverse-DNS** `org.devlive.<app>.<plugin>` (app identifier `org.devlive.<app>`). Never `com.<app>`. | Review |
| 10 | **One feature = one commit** (Conventional Commits, English, no AI attribution). Run the full check before every commit. | **git-commit-convention** skill, `cargo xtask check` |
| 11 | **README.md is English; README.zh-CN.md mirrors it**, both linked at the top and kept in sync. No "project structure" dump in the README. | Review |
| 12 | Secrets (updater private key, tokens) never enter the repo; tests generate keys at runtime. | Review |

If a rule seems to block a legitimate need, ask the user before bending it. For real exceptions a line may carry the scanner's allow marker (`// <prefix>-allow: <reason>`, e.g. `tf-allow` in ToolForge) so it is skipped (e.g. a hex color that is *input data*, not styling).

## Tech stack (default choices)

- **Shell:** Tauri 2, Rust edition 2024, Cargo workspace + pnpm workspace.
- **Frontend:** React 19, TypeScript, Vite, Tailwind v4 (`@theme inline` tokens), zustand, @floating-ui/react, cva + tailwind-merge, lucide-react, CodeMirror (`@uiw/react-codemirror`), @tanstack/react-virtual, react-i18next.
- **Rust:** serde / serde_json (`preserve_order`), rusqlite (`bundled`), reqwest **blocking** + rustls with the `ring` provider (shared with the updater), tauri-plugin-updater / dialog / clipboard-manager / opener.
- Not Vue. No frontend data-processing libraries (lodash, dayjs, js-yaml, crypto-js, uuid, papaparse, …).

## Workflow for any change

1. **Recall context.** Read the project's `.claude/CLAUDE.md` memory (see the **project-memory** skill) and the relevant reference file below.
2. **Design in Rust first.** Define the plugin function(s) or command, the args/result structs (`#[serde(rename_all = "camelCase")]`), and the error codes. Decide call vs task and whether results can be large.
3. **Implement Rust + tests** (`*_test.rs`, real data, edge cases, error codes). Pin third-party behaviour with tests (official vectors, round trips).
4. **Implement the UI** with the plugin SDK (`usePlugin`, `useDebouncedCall`, `useTask`, `host`), tokens and components only, and all strings in locales for **every** supported language.
5. **Verify visually** in a browser preview (mock IPC + an HTTP bridge to the real Rust plugins, screenshot light/dark and zh/en). Fix what you see; check real data, not only happy paths.
6. **Run `cargo xtask check`** (rules → rustfmt → clippy `-D warnings` → tests → typecheck → eslint → build). All green.
7. **Commit one feature** via the git-commit-convention skill. Update both READMEs in a separate `docs:` commit when the tool list changes. Update project memory.
8. **Never push or release** unless the user asks; the user runs releases.

## Reference files

Read the one that matches the task (they contain the concrete code shapes):

| File | When |
|------|------|
| `references/architecture.md` | New project scaffold, workspace layout, crates, errors, SQLite store, commands, state |
| `references/plugins.md` | Adding a plugin/tool: manifest, `ToolPlugin`, UI SDK, registration, checklist |
| `references/i18n.md` | Locales, namespaces, error/log codes, plurals, lint rules |
| `references/tasks-and-resources.md` | Long-running work, live logs, cancellation, large results, downloadable models/resources |
| `references/window-and-shell.md` | Window chrome, first-frame theme, quit confirmation, custom menu and About page, updater UI |
| `references/ci-release.md` | `cargo xtask`, convention scanner, ESLint, GitHub Actions, release script, updater signing |
| `references/pitfalls.md` | Known traps and their fixes; skim before debugging anything odd |

## Definition of done (every feature)

- [ ] Data processing is in Rust; the UI only renders.
- [ ] Errors are `code + params`; every code is translated in every locale.
- [ ] Slow paths are tasks with logs/progress/cancel; large outputs are previews with save/copy by id.
- [ ] No browser storage; persistence goes through SQLite commands.
- [ ] Tokens + in-house components only; light and dark both look right.
- [ ] Rust tests in `*_test.rs`, covering happy path, edge cases and error codes.
- [ ] `cargo xtask check` passes; previewed in both languages.
- [ ] One commit for the feature (+ `docs:` commit for READMEs if needed); memory updated.
