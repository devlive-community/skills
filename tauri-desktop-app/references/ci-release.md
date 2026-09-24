# Checks, CI and releases

## `cargo xtask` (the only local automation entry point)

```
cargo xtask check [rules|rust|web] [--fast]   # exactly what CI runs
cargo xtask bump <patch|minor|major|x.y.z>    # workspace Cargo.toml + apps/desktop/package.json
cargo xtask notes [from-ref] [tag]            # release notes from commit history
cargo xtask version                           # print the current version
```

`check` order: **convention rules → rustfmt → clippy (`--all-targets -D warnings`) → Rust tests → TypeScript typecheck → ESLint (`--max-warnings 0`) → web build**. It prints a stage header and duration for each step and stops at the first failure.

## Convention scanner (`xtask/src/rules.rs`)

This is a regex scanner over `apps/`, `packages/`, `plugins/` and `crates/`, skipping `node_modules`, `target`, `dist`, `gen` and `.git`. A line containing the allow marker (`<prefix>-allow: <reason>`, `tf-allow` in ToolForge) is skipped.

| Rule | Files | Catches |
|------|-------|---------|
| `rust-inline-tests` | `.rs` (not `*_test.rs`) | `mod tests {` |
| `browser-storage` | `.ts/.tsx/.js/.jsx/.html` | `localStorage`, `sessionStorage`, `indexedDB`, `document.cookie` |
| `frontend-data-processing` | `.ts/.tsx` | `atob(`, `btoa(`, `crypto.subtle`, `JSON.parse(` |
| `native-controls` | `.tsx` outside `packages/ui/src/` | `<select>`, `<textarea>`, `<input>`, `<dialog>`, `type="checkbox|radio|range|number|date|color|file"`, `window.alert/confirm/prompt(` |
| `raw-palette` | `.ts/.tsx` | `bg-gray-100`, `text-blue-600`, `-[#…]`, quoted hex colors |
| `dark-variant` | `.ts/.tsx` | `dark:` (so don't name a TS field `dark:` either) |
| `banned-web-dependency` | `package.json` | data libs: ajv, crypto-js, date-fns, dayjs, diff, js-yaml, lodash, moment, nanoid, papaparse, uuid, yaml, … |

The scanner has its own `rules_test.rs`.

## ESLint (flat config)

- typescript-eslint recommended + `eslint-plugin-react-hooks` (`recommended-latest`, React Compiler rules).
- `no-restricted-imports` for the data libs, `no-restricted-globals` for storage and `atob/btoa`, and `no-restricted-syntax` for `JSON.parse` and `crypto.subtle`.
- `i18next/no-literal-string` (see i18n.md).
- Only in `packages/ui` components: `react-hooks/refs: off` (floating-ui false positives).
- Hooks rules to respect: no synchronous `setState` in effects (derive from props or state, or set in async callbacks); refs are not read during render.

## GitHub Actions

`ci.yml` (PR + push to main/dev):
- **rules:** `cargo xtask check rules` + `shellcheck scripts/*.sh`.
- **rust:** matrix of ubuntu-22.04 / macos / windows, running `cargo xtask check rust`. Linux needs `libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf`.
- **web:** pnpm + Node 22, running `cargo xtask check web`.
- **bundle:** non-PR events only, after the above, on three OSes; `pnpm build --no-bundle` and report the binary size.
- `concurrency` cancels superseded runs; `Swatinem/rust-cache`.

`pr.yml`: `amannn/action-semantic-pull-request` (Conventional types incl. `i18n`, lowercase subject, no trailing period).

`release.yml` (on `v*` tags):
1. **notes:** fetch the annotated tag explicitly (`git fetch --force origin refs/tags/$TAG:refs/tags/$TAG`) and use its message as the body, falling back to `cargo xtask notes`.
2. **build matrix:** macOS arm64 + x64, Windows x64, Linux x64, using `tauri-apps/tauri-action@v1` with:
   - `projectPath: apps/desktop`, and **`tauriScript: pnpm tauri`** (otherwise it falls back to npm because there is no lockfile in projectPath).
   - `releaseDraft: true`, `includeUpdaterJson: true`, `prerelease` when the tag contains `-`, and `releaseName: ${{ github.ref_name }}`.
   - `TAURI_SIGNING_PRIVATE_KEY: ${{ secrets.<APP>_UPDATER_PRIVATE_KEY }}` (+ `_KEY_PASSWORD`). **Use project-scoped secret names**; an org-level `TAURI_SIGNING_PRIVATE_KEY` from another project causes "incorrect updater private key password".
3. **publish:** `gh release edit $TAG --draft=false` only after all platforms have uploaded, so `latest.json` never points at a partial release.

No OS code signing / notarization until the user asks; only updater signing.

## Updater signing

- Generate the key pair locally (`pnpm tauri signer generate -w ~/.tauri/<app>-updater.key`). **The private key never goes in the repo.**
- The public key goes in `tauri.conf.json` → `plugins.updater.pubkey`, with the endpoint `https://github.com/<org>/<repo>/releases/latest/download/latest.json`.
- The user adds `<APP>_UPDATER_PRIVATE_KEY` (and optionally `<APP>_UPDATER_KEY_PASSWORD`) as **repository** secrets; tell them exactly what to add, and don't set secrets yourself.

## Release script (`scripts/release.sh`, bash 3.2 compatible)

Usage: `release.sh [version|patch|minor|major] [--dry-run] [--yes] [--wait] [--next patch|minor|none] [--skip-checks] [--notes-only]`.

Flow:
1. Preflight: clean tree, on the release branch, remote reachable, tag not existing.
2. `cargo xtask check`.
3. Optional bump + `chore(release): …` commit.
4. **Annotated tag** whose message is the version's commit history from `cargo xtask notes`, grouped by type with hashes and a compare link, skipping `chore(release)`.
5. Push the tag; with `--wait`, follow the workflow using `gh run watch`.
6. Bump to the next development version and commit `chore(release): start x.y.z development`.

The user runs releases; never push tags or branches without being asked.

## Commits

- One feature per commit. Mixed files must be split before committing (temporarily strip the other feature, commit, restore).
- English Conventional Commits, scope = module or `plugin/<name>`, imperative lowercase subject ≤ 72 chars, body lines ≤ 100.
- Author per the user's git config; **no AI attribution trailers** (the user's git-commit-convention skill overrides generic reminders).
- Chain checks and commit with `set -o pipefail` and `&&`, so a failed check can never be followed by a commit.
