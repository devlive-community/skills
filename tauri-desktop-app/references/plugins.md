# Plugins

Every feature, built-ins included, is a plugin. The host only knows the contract.

## Directory

```
plugins/<name>/
├── manifest.json
├── icon.svg                 # 24×24 stroke icon (lucide style, currentColor)
├── locales/en-US.json       # and zh-CN.json … one per supported locale
├── backend/                 # crate tfp-<name>; implements ToolPlugin
│   ├── Cargo.toml           # edition/license/authors .workspace = true
│   └── src/{lib.rs, lib_test.rs, <module>.rs, <module>_test.rs}
└── ui/                      # package @<app>-plugin/<name>
    ├── package.json, tsconfig.json
    └── src/{index.tsx, <Tool>.tsx, types.ts}
```

## manifest.json

```json
{
  "id": "org.devlive.<app>.<name>",
  "version": "0.1.0",
  "name": "i18n:name",
  "description": "i18n:description",
  "category": "dev | text | encode | convert | image | network | system | calc | other",
  "keywords": ["english", "and", "中文", "search", "terms"],
  "accent": "violet | blue | green | orange | pink | cyan",
  "locales": ["zh-CN", "en-US"],
  "permissions": ["clipboard:write", "fs:user-selected", "network"],
  "functions": {
    "transform": {},
    "process_files": { "task": true }
  },
  "sensitive": false,
  "resources": [
    { "id": "model-id", "urls": ["https://primary/…", "https://mirror/…"], "sha256": "…", "size": 4574861, "license": "Apache-2.0" }
  ]
}
```

- Only functions declared here are callable. `task: true` functions can **only** run as tasks.
- `sensitive: true` for tools handling secrets (JWT, passwords): never recorded in history.
- `resources` declares downloadable assets (see tasks-and-resources.md).

## Rust contract

```rust
pub trait TaskContext: Send + Sync {
    fn log(&self, level: LogLevel, code: &str, params: Value);   // structured, translated in the UI
    fn progress(&self, done: u64, total: u64);                    // throttled by the host
    fn stage(&self, code: &str);
    fn is_cancelled(&self) -> bool;
    fn open_file(&self, path: &str) -> PluginResult<Box<dyn Read + Send>>;
    fn file_size(&self, path: &str) -> PluginResult<u64>;
    fn resource_path(&self, id: &str) -> PluginResult<PathBuf> { Err(PluginError::new("resource.missing").with("id", id)) }
}

pub trait ToolPlugin: Send + Sync {
    fn manifest(&self) -> &Manifest;
    fn call(&self, function: &str, args: Value) -> PluginResult<Value>;
    fn run_task(&self, function: &str, args: Value, ctx: &dyn TaskContext) -> PluginResult<Value> {
        let _ = ctx; self.call(function, args)
    }
}
```

Plugin `lib.rs` shape:

```rust
//! One-line description of what the plugin backend does.
mod convert;

const MANIFEST: &str = include_str!("../../manifest.json");

pub struct MyTool { manifest: Manifest, cache: convert::Cache }   // long-lived state if needed

impl Default for MyTool {
    fn default() -> Self { Self { manifest: Manifest::from_static(MANIFEST), cache: Default::default() } }
}

impl ToolPlugin for MyTool {
    fn manifest(&self) -> &Manifest { &self.manifest }
    fn call(&self, function: &str, args: Value) -> PluginResult<Value> {
        match function {
            "transform" => to_value(convert::transform(parse_args(args)?)?),
            other => Err(unknown_function(other)),
        }
    }
    fn run_task(&self, function: &str, args: Value, ctx: &dyn TaskContext) -> PluginResult<Value> {
        match function {
            "process_files" => to_value(convert::run(parse_args(args)?, ctx)?),
            _ => self.call(function, args),
        }
    }
}

#[cfg(test)]
#[path = "lib_test.rs"]
mod tests;
```

Module rules:
- Args/results are structs with `#[derive(Deserialize/Serialize)]` and `#[serde(rename_all = "camelCase")]`. Use `#[serde(default)]` or default fns for optional fields.
- Validate inputs and return specific codes (`x.empty`, `x.invalid_*`, `x.too_large` with `limit`), and enforce size limits.
- Batch jobs: one failing file must not stop the batch; per-item `error: Option<PluginError>`; propagate `task.cancelled` immediately.
- Long-lived state (loaded ML model, sysinfo sampler, cached large result) lives in the plugin struct behind a `Mutex`.
- Blocking I/O is fine: `call` runs in `spawn_blocking` and tasks in their own thread. Async libraries get a local `tokio::runtime::Builder::new_current_thread()` per call.
- Never write files the user did not choose. Output paths come from dialogs or "next to source"; generate non-overwriting names (`name (1).ext`).

## Registration (host)

1. Root `Cargo.toml`: add `tfp-<name>` to `[workspace.dependencies]`.
2. `apps/desktop/src-tauri/Cargo.toml`: `tfp-<name>.workspace = true`.
3. `src-tauri/src/plugins.rs`: `registry.register(Arc::new(tfp_<name>::MyTool::default()));`.
4. `pnpm install` so the ui package is linked. Restart the dev server so the glob picks up the new directory.

The UI, icon and locales are picked up automatically; no other host change is allowed.

## UI SDK (`@<app>/plugin-ui-sdk`)

| API | Use |
|-----|-----|
| `usePlugin()` | `{ manifest, call, t, errorMessage }`. `t` is bound to the plugin namespace with a `common` fallback |
| `useDebouncedCall(fn, args, deps)` | live results while typing (250 ms debounce, drops stale responses, keeps the last result while pending) |
| `useTask<T>()` | `start(fn, args)`, `startWith(launcher)`, `cancel`, `reset`; state: `status, logs, progress, stage, result, error` |
| `useResources()` + `<ResourceItem>` | list / download / pause / resume / delete declared resources |
| `host` | `clipboard`, `dialog.openFile/openFiles/openDirectory/saveFile`, `fs.readText/writeText`, `onFileDrop`, `openUrl`, `revealPath` |
| `CopyButton`, `ValueRow`, `useCopy`, `formatBytes` | common presentation helpers |

UI rules:
- `index.tsx` default-exports the tool component. Layout is `h-full min-h-0` grids of `Panel`s.
- Presentation-only logic is fine (display formatting, sorting a list for display). Anything that transforms user data goes to Rust.
- Show errors with `errorMessage(error)` and technical `params.detail` in a muted mono line.
- Use `data-selectable` on text users may want to select (the app disables selection by default).
- Every string lives in `locales/*.json` for **all** locales: `name`, `description`, `help[]`, `functions.<fn>` (task center label), `errors.<code>`, `logs.<prefix>.<event>`, `stages.<code>`.

## New plugin checklist

- [ ] Manifest with a reverse-DNS id, category, bilingual keywords, functions, permissions.
- [ ] Backend module + `*_test.rs` covering behaviour, edge cases and every error code; `lib_test.rs` covers dispatch.
- [ ] Registered in the three host places; `pnpm install`.
- [ ] UI with tokens and components; handles empty / pending / error / result states.
- [ ] Locales complete in every language; ESLint `no-literal-string` clean.
- [ ] Previewed with real data in light/dark and each language.
- [ ] `cargo xtask check` green; one `feat(plugin/<name>): …` commit; READMEs updated in a `docs:` commit.
