# Window, shell and app lifecycle

## Main window (created in Rust)

- Build it with `WebviewWindowBuilder` in `setup()` (the config has `"windows": []`):
  - `.visible(false)`, and show it in `on_page_load` when `PageLoadEvent::Finished` arrives. Never rely on the frontend to call `show()`; if JS fails, the window would never appear.
  - `.background_color(...)` matching the theme's `--bg` token to avoid a white flash.
  - `.initialization_script(...)` injecting `window.__<APP>_BOOT__ = { prefs, os }` from SQLite, and toggling the `dark` class before any script runs (first-frame theme).
  - `.min_inner_size(...)`, `.center()`.
- Chrome:
  - **macOS** keeps the native window (rounded corners, shadow, resizing) with `TitleBarStyle::Overlay` + `hidden_title(true)`. The traffic lights are hidden through `objc2-app-kit` (`standardWindowButton(...).setHidden(true)`), and hidden again on `Resized`, `Focused` and `ThemeChanged` because the system restores them.
  - **Windows/Linux** use `.decorations(false)`.
  - All platforms use in-app `WindowControls` (minimize, maximize/restore, close); the title bar is a drag region (`data-tauri-drag-region`).
- The frontend disables the context menu; `html, body, #root { overflow: hidden }` and content areas scroll inside.
- Overlays and drawers must not toggle body overflow (it causes scrollbar jitter). Use `style={{ overflow: 'hidden' }}` on the overlay and `[scrollbar-gutter:stable]` in drawers.

## Quit confirmation (never quit silently)

Closing the window (custom ✕, ⌘W), ⌘Q and the menu's Quit all ask first.

Rust (`lifecycle.rs`):
- `QuitGuard { confirmed: AtomicBool, requested: AtomicU64, acked: AtomicU64 }` is managed state.
- `request_quit(app) -> bool`:
  - Returns true right away if already confirmed or if prefs `confirmQuit == false`, which Rust reads from SQLite.
  - Otherwise: show and focus the window, emit `app://close-requested` with a sequence number, and spawn a thread. If the frontend has not called `app_close_ack(seq)` within ~1.5 s, set `confirmed` and `app.exit(0)`, so a broken page can never trap the user.
  - Returns false.
- Window `on_window_event`: on `CloseRequested { api }` where `!request_quit`, call `api.prevent_close()`.
- `run(|app, event|)`: on `RunEvent::ExitRequested { code: None, api }` where `!request_quit`, call `api.prevent_exit()`. `app.exit(n)` carries `Some(code)` and passes through.
- `app_quit` sets confirmed and exits; `app_restart` (after an update) also sets confirmed first.

UI: on `app://close-requested`, acknowledge first, then open a `QuitDialog` with Quit (danger) / Cancel / Minimize, a warning when tasks are running, and "Don't ask again". Settings has a matching switch, flushed to SQLite immediately.

## Custom macOS menu and in-app About page

Never show the native About panel. Build the menu in Rust (macOS only), rebuilt when the language changes:
- **App menu:** a custom `About <App>` item and `Settings…` (⌘,), both of which emit `app://navigate` with `about`/`settings`; then Services, Hide, Hide Others, Show All, and the predefined Quit (which goes through the quit confirmation).
- **Edit menu:** undo, redo, cut, copy, paste, select all. It is required, or ⌘C/⌘V stop working in inputs.
- **Window menu:** minimize, zoom, full screen, close window.
- Labels come from a small `Labels` table per locale, and `app_menu_locale(locale)` rebuilds the menu.

About page (`view: 'about'`), reachable from the sidebar footer, Settings and the menu:
- Logo, name, version, tool count, tagline, update button, source link.
- System info: version, platform, Tauri + WebView versions, data folder with a reveal button, and "Copy system info" for bug reports.
- Links (source, release notes, report issue, license) and credits with licenses.
- External links always go through `app_open_url` (http/https only) → opener plugin; never navigate the WebView away.
- lucide v1 has no brand icons (no `Github`); use generic ones such as `FolderGit2`.

## Auto update (UI part)

- `update_check` returns `{ version, currentVersion, date, notes }`, where `notes` is markdown **parsed in Rust** into blocks. pulldown-cmark → `heading/paragraph/list/quote/code/rule` with spans `{ text, strong, em, strike, code, href }`. Raw HTML is dropped, only http(s) links are kept, and bare URLs are autolinked. A `Markdown` component renders the blocks with tokens.
- `update_install` streams progress through a Channel; `app_restart` relaunches.
- Silent check a few seconds after startup when `autoUpdate` is on; users can skip a version.
- The version badge in the title bar shows the real version (never a "beta" placeholder).
