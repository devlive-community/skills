# Known pitfalls and fixes

## Window, layout and styling
- **Window never appears:** it was shown from the frontend. Show it from Rust `on_page_load(Finished)`.
- **Drawer/modal jitter, scrollbar flashes:** caused by toggling body overflow. Keep `html/body/#root` overflow hidden, and give overlays `overflow: hidden` inline and drawers `[scrollbar-gutter:stable]`.
- **Custom scrollbars ignored in Chromium:** setting standard `scrollbar-width`/`scrollbar-color` disables `::-webkit-scrollbar`. Use only the WebKit pseudo-elements.
- **Tailwind classes from the ui/SDK/plugins missing:** add `@source` for each workspace package in the app's CSS.
- **`@theme inline` self-reference loops:** name raw variables with a prefix (`--<app>-bg`) and map `--color-bg: var(--<app>-bg)`.
- **macOS traffic lights reappear:** re-hide them on resize, focus and theme change.

## Rust / crates
- **`serde_json` `arbitrary_precision`:** numbers serialize as a private map through other serde formats (YAML/TOML). Convert `Value` manually for those.
- **Unicode boundaries:** CodeMirror uses UTF-16 offsets. Convert Rust byte offsets before sending marks; cut previews on char boundaries.
- **reqwest blocking + rustls:** you must install a crypto provider once (`rustls::crypto::ring::default_provider().install_default()`). Enabling reqwest's default `rustls` pulls in aws-lc; reuse `ring` like the updater does.
- **reqwest blocking `timeout`** applies per wait/read, so it works as a stall timeout. `timeout(None)` risks hanging forever.
- **System proxy intercepts localhost:** some machines route `127.0.0.1` through the proxy (→ 502). Call `.no_proxy()` for loopback hosts, and offer a "use system proxy" switch.
- **TUN / fake-ip proxies** answer every DNS query with `198.18.0.0/15`. Flag those answers, and never assert concrete IPs in network tests.
- **hickory-resolver 0.26:** `Record` has public fields (`name`, `ttl`, `data`); build custom servers with `Resolver::builder_with_config(ResolverConfig::from_name_servers(..), TokioRuntimeProvider::new())`.
- **sysinfo:** CPU usage and network rates need two samples, so keep a long-lived sampler in the plugin. macOS reports the same APFS container at several mount points (dedupe) and placeholder MACs (`00:…`, `02:00:00:00:00:00`).
- **Version lookups:** check `Cargo.lock` first and reuse an existing major version of a crate (num-bigint, rand, image) instead of adding a duplicate.
- **rand 0.10:** `rand::rng()`, `RngExt::random_range`, `seq::SliceRandom`.
- **jiff:** `DateTime` also parses plain dates. Try the date path first when there is no `T`.
- **jsonwebtoken 11:** `default-features = false` + `rust_crypto`, `use_pem`.
- **Blocking a Tokio-based crate inside `plugin_call`:** create a `new_current_thread().enable_all()` runtime per call and `block_on`.
- **Clippy `-D warnings` regulars:** `is_multiple_of`, `sort_by_key` with `Reverse`, `std::slice::from_ref(&x)` instead of `&[x.clone()]`, `div_ceil`.

## Frontend
- **React hooks lint:** don't call a state-setting function synchronously inside an effect. Fetch in the effect and set state in the promise callback, keyed on a version counter; derive state during render instead of syncing it.
- **i18n lint:** arrows, `×` and `/` between JSX expressions are literal text; wrap them in a template literal.
- **lucide v1** removed brand icons.
- **Stable callbacks:** `usePlugin().call` and `errorMessage` are memoized, so they are safe in effect deps (polling with `setInterval`).
- **Large strings in CodeMirror** with `lineWrapping` freeze the UI. See "Large results" in tasks-and-resources.md.

## Process
- **A check failed but the commit still ran:** pipes and heredocs broke the chain. Use `set -o pipefail` and keep `&&`.
- **A build tool picked up the wrong workspace** (shared `CARGO_TARGET_DIR` baked in another checkout's path). Give scratch builds their own target dir.
- **New plugin not visible in dev:** restart Vite (the `import.meta.glob` result is fixed at startup) and run `pnpm install`.
- **Browser preview harness** (scratchpad only, never committed): Vite with a `mockIPC` script, an HTTP bridge that links the real plugin crates, and a Playwright script for screenshots with steps `click= text= css= type= key= js= wait=`. Enable `shouldMockEvents` to simulate Tauri events. Screenshot light/dark × each language and inspect them before committing UI.
