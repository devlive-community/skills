# Tasks, large results and downloadable resources

## Task system

Use a task for file processing, batches, downloads, inference, network calls with progress, and anything that could exceed ~300 ms.

Host (`<app>-core::TaskManager`):
- `start(plugin_id, function, sink, job)` inserts a `tasks` row, spawns a thread, catches panics (`task.panicked`), and records status (`succeeded | failed | cancelled | interrupted`), elapsed time and error code.
- `TaskRunner` implements `TaskContext`:
  - **Logs** are batched (flush every 50 ms or 200 lines) and also written as JSONL to `<data>/logs/tasks/<id>.jsonl`.
  - **Progress** is throttled (~100 ms, always emitting the final value).
  - **Cancellation** is an `AtomicBool` read through `is_cancelled()`.
  - **Resources** come from `resource_path()` via an optional `Arc<Resources>`.
- Events (`TaskEvent`): `started | logs | progress | stage | finished { status, result, error, elapsedMs }`.
  - They are streamed to the caller through a `tauri::ipc::Channel<TaskEvent>`.
  - Everything except logs is also broadcast as `task://event` for the global task center.
- On startup, tasks left `running` are marked `interrupted`, and history is pruned (e.g. keep 200).

Plugin side:

```rust
pub fn run(args: Args, ctx: &dyn TaskContext) -> PluginResult<Report> {
    ctx.stage("x.scan");
    for (i, path) in args.paths.iter().enumerate() {
        if ctx.is_cancelled() { return Err(cancelled()); }
        ctx.log(LogLevel::Info, "x.file_start", json!({ "file": name, "index": i + 1, "count": n }));
        match process(path, ctx) {
            Ok(done) => { /* push result, log x.file_done */ }
            Err(e) if e.code == "task.cancelled" => return Err(e),
            Err(e) => { ctx.log(LogLevel::Warn, "x.file_failed", json!({ "file": name, "code": e.code })); /* push error item */ }
        }
        ctx.progress(i as u64 + 1, n as u64);
    }
    Ok(report)
}
```

UI:

```tsx
const task = useTask<Report>()
task.start('process_files', { paths })        // also: task.cancel(), task.reset()
// task.status, task.progress, task.stage, task.logs (LogViewer), task.result, task.error
```

Show a progress bar and a Cancel button while running, and a `LogViewer` panel with live logs. The task center lists history, logs and a function label (`functions.<fn>` in the plugin namespace, or `common:taskFunctions.<fn>` for host tasks).

## Large results (keep them in Rust)

Symptoms of getting this wrong: the UI freezes, IPC stalls, and the task history bloats. Examples are a 20 MB file as Base64 in a CodeMirror editor, or a 30 MB HTTP body.

Pattern:
1. Store the full result in the plugin (`Mutex<Option<(id, Vec<u8> | String)>>`, keeping only the latest).
2. Return `{ id, preview (≤ 64 KB–1 MB, cut on a char boundary), truncated, size/chars, …stats }`.
3. Add functions `file_output { id }` (full text for copy) and `save_output { id, path }` (Rust writes the file). Stale ids return `x.result_expired`.
4. The UI shows the preview, a "showing first N of M" notice, and Copy/Save buttons that call those functions.
5. Binary data is never converted to Base64 for display. Thumbnails are small PNG data URIs generated in Rust.

## Downloadable resources (models, runtimes)

Declared in the plugin manifest `resources[]` (`id`, `urls[]` tried in order, `sha256`, `size`, `license`).

Host (`<app>-core::Resources`, stored at `<data>/resources/<plugin-id>/`):
- `<id>` is the file, `<id>.json` the install record, `<id>.part` the partial download.
- Resource ids are path-safe (`[a-z0-9._-]`, no leading dot); plugin ids are rejected if they contain separators.
- Download:
  - Resume `.part` with `Range: bytes=N-` after re-hashing the existing bytes. If the server ignores Range (returns 200), restart from zero.
  - Stream in 256 KB chunks, updating SHA-256 and reporting progress; honour cancellation, keeping `.part` so it can resume later.
  - Verify size and hash, delete the part on mismatch, then rename and write the record.
  - Mirror fallback: log `resource.source_failed`, then try the next URL.
- HTTP: `reqwest::blocking` with the rustls `ring` provider installed once (`Once` + `install_default`), `connect_timeout`, and `timeout(30 s)`. The blocking timeout applies **per wait/read**, so it acts as a stall timeout, not a whole-download limit.
- Commands:
  - `resource_list(pluginId)` returns status (installed, partial bytes, size, license).
  - `resource_download(pluginId, resourceId, onEvent)` runs as a host task named `download_resource`. An `ActiveDownloads` set with a `Drop` guard prevents concurrent duplicates.
  - `resource_delete` is refused while a download is running.

Plugin:

```rust
let model = ctx.resource_path("u2netp")?;   // Err(resource.missing) until downloaded
```

UI: `const resources = useResources()` and `<ResourceItem resources={resources} id="u2netp" selected onSelect />`. It shows the name/description from `resources.<id>.*`, size, license, progress, and pause/resume/delete. Disable the action that needs a model until it is installed, and say why.

Tests: run a local `TcpListener` HTTP server in the test that supports Range, 404, ignored Range and truncated bodies. Cover checksum mismatch, cancel then resume, mirror fallback and unsafe ids.

## On-device ML (example: background removal)

- Use `tract-onnx` (pure Rust, no native runtime to ship per platform). Load once and cache the `Arc<TypedRunnableModel>` per model.
- Match each model's preprocessing exactly. ImageNet mean/std vs `mean 0.5, std 1.0` produces garbage masks if mixed up; verify against a real image before wiring the UI.
- Keep original resolution: resize the mask back with bilinear filtering, apply EXIF orientation, and composite in Rust.
- Keep real-model tests `#[ignore]` with the model path from an env var, so CI does not download models.
- Optimize tract/image crates at `opt-level = 3` in dev and release profiles.
