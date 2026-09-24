# Architecture

## Workspace layout

```
<app>/
├── Cargo.toml                 # [workspace] members: apps/desktop/src-tauri, crates/*, plugins/*/backend
├── .cargo/config.toml         # [alias] xtask = "run --quiet --package xtask --"
├── package.json               # scripts: dev, build, typecheck, lint, check, release
├── pnpm-workspace.yaml        # apps/*, packages/*, plugins/*/ui
├── eslint.config.js
├── tsconfig.base.json
├── apps/desktop/
│   ├── src/                   # React shell: layout, stores, views, locales, plugin loading
│   └── src-tauri/             # Tauri entry: window, commands, tasks, updater, lifecycle, menu
├── crates/
│   ├── <app>-plugin-api/      # host ↔ plugin contract (Manifest, ToolPlugin, TaskContext, PluginError)
│   ├── <app>-core/            # AppError, SQLite Store, PluginRegistry, TaskManager, Resources, markdown…
│   └── xtask/                 # check / bump / notes / version + convention scanner
├── packages/
│   ├── ui/                    # @<app>/ui: tokens.css + component library (tailwind-token-ui)
│   └── plugin-ui-sdk/         # @<app>/plugin-ui-sdk: usePlugin, useTask, useDebouncedCall, host, …
├── plugins/<name>/            # manifest.json, icon.svg, locales/, backend/ (Rust), ui/ (React)
├── scripts/release.sh
└── .github/workflows/         # ci.yml, pr.yml, release.yml, dependabot.yml
```

Workspace `Cargo.toml`:
- `[workspace.package]` holds the version (kept in sync with `apps/desktop/package.json` by `cargo xtask bump`).
- `[workspace.dependencies]` lists shared crates and every plugin crate (`tfp-<name> = { path = "plugins/<name>/backend" }`).
- `[profile.release]`: `codegen-units = 1`, `lto = true`, `opt-level = "s"`, `panic = "abort"`, `strip = true`.
- Hot crates (ML inference, image codecs) get `[profile.dev.package.X] opt-level = 3` **and** `[profile.release.package.X] opt-level = 3`. Size-optimizing them makes inference noticeably slower, and debug builds make them unusably slow.

`tauri.conf.json`:
- `"version": "../package.json"` so there is a single version source.
- `"windows": []`: the window is created in Rust (see window-and-shell.md).
- Strict CSP. Only `ipc:`/`http://ipc.localhost` connect sources and `asset: data: blob:` images.
- `bundle.createUpdaterArtifacts: true` and `plugins.updater.pubkey/endpoints` (see ci-release.md).

## Errors: code + params, never text

```rust
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PluginError {
    pub code: String,                                   // "json.syntax", "fs.not_found", "http.timeout"
    #[serde(default, skip_serializing_if = "Map::is_empty")]
    pub params: Map<String, Value>,                     // { "line": 3, "column": 7 }
}
impl PluginError {
    pub fn new(code: impl Into<String>) -> Self { … }
    pub fn with(mut self, key: &str, value: impl Into<Value>) -> Self { … }
}
```

- `AppError` (host) has the same shape with `impl From<PluginError> for AppError`, and `AppResult<T> = Result<T, AppError>`.
- Codes are namespaced: `<plugin-prefix>.<reason>` for plugins, `app.*`, `fs.*`, `store.*`, `task.*`, `resource.*` for the host.
- Put the raw technical message in `params.detail`, and show it under the translated message when useful.
- The frontend translates via `errors.<code>` in the plugin namespace, falling back to `common` (see i18n.md).

## SQLite store (only persistence)

- The `<app>-core::Store` wraps a `Mutex<rusqlite::Connection>` at `<app_data_dir>/<app>.db` with numbered migrations.
- Tables: `kv` (prefs JSON etc.), `favorites`, `recent`, `tasks` (task history).
- Commands: `prefs_get/prefs_set`, `favorites_list/favorite_toggle`, `recent_list/recent_touch`.
- The frontend prefs store debounces writes (300 ms). Flush immediately for prefs that Rust reads on its own, e.g. `confirmQuit`.
- Rust can read prefs directly (theme for first-frame, locale for the menu, confirmQuit for quitting).

## App state and commands

```rust
pub struct AppState {
    pub store: Arc<Store>,
    pub plugins: Arc<PluginRegistry>,
    pub tasks: TaskManager,            // .with_resources(resources.clone())
    pub resources: Arc<Resources>,
}
```

- `setup()`: open the store, read prefs, create `TaskManager` (marks interrupted tasks, prunes old ones), create the main window, and `app.manage(AppState { … })`.
- Extra managed state: `PendingUpdate`, `ActiveDownloads`, `QuitGuard`.
- `.build(ctx)?.run(|app, event| …)` instead of `.run(ctx)` so `RunEvent::ExitRequested` can be intercepted.

Typical command set:
- `app_info` (version, os, arch, tauriVersion, webviewVersion, dataDir), `app_log` (forward frontend errors), `app_open_url` (http/https only), `app_reveal_path`.
- `plugin_list`, `plugin_call` (runs in `spawn_blocking`), `fs_read_text` (size-limited), `fs_write_text`.
- `task_start/task_cancel/task_list/task_logs`.
- `resource_list/resource_download/resource_delete`.
- `update_check/update_install/app_restart`.
- `app_close_ack/app_quit/app_menu_locale`.

Capabilities are minimal: only the window, dialog, clipboard permissions actually used. Anything else is done through Rust commands so it can be validated there.

## Frontend shell

- Stores (zustand): `app` (plugins, favorites, recent, route, dialogs), `prefs` (SQLite-backed), `update`, `tasks` (task center; subscribes to a global `task://event`).
- Routing is a small `route` union in the app store (`home | tool | favorites | recent | history | settings | about`), not a router library.
- Plugins are discovered with `import.meta.glob` over `plugins/*/manifest.json`, `ui/src/index.tsx` (lazy), `icon.svg?raw` and `locales/*.json`. The authoritative list comes from Rust `plugin_list`. **Restart Vite after adding a plugin directory**, because the glob result is fixed at startup.
- `styles.css` must `@source` the ui package, the SDK and `plugins/` or Tailwind will not generate their classes.
- Disable the WebView context menu; forward `error`/`unhandledrejection` to `app_log`.
