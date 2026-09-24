# Token system

## Naming layers

| Layer | Purpose | Example |
|------|------|------|
| Primitive value | Only appears inside tokens.css | `oklch(0.62 0.19 255)` |
| Semantic token (CSS variable with a project prefix) | Expresses purpose; one value set each for light and dark | `--tf-bg`, `--tf-surface`, `--tf-fg-muted`, `--tf-primary` |
| Tailwind utility class | Mapped through `@theme inline` | `bg-surface`, `text-fg-muted`, `bg-primary` |

Business code only touches the third layer.

## Semantic token list

- **Backgrounds:** `bg` (app background), `surface` (cards/panels), `surface-2` (nested areas/sidebar), `elevated` (popovers/menus), `overlay` (backdrop)
- **Foregrounds:** `fg` (body text), `fg-muted` (secondary), `fg-subtle` (placeholder/disabled), `fg-on-primary` (text on the primary color)
- **Borders:** `border` (default), `border-strong` (hover/emphasized separators), `ring` (focus ring)
- **Interaction:** `hover` (generic hover background), `active` (pressed/selected background)
- **Brand and status:** `primary` / `primary-hover` / `primary-soft` (tinted background); likewise `success`, `warning`, `danger` and `info`, each with `-soft` and `-fg`
- **Radii:** `radius-control` (buttons/inputs), `radius-card`, `radius-popover`
- **Shadows:** `shadow-card`, `shadow-popover`, `shadow-modal`
- **Sizes:** `h-control-sm/md/lg` (control heights 28/32/36px)
- **Fonts:** `font-sans`, `font-mono`; font sizes use the default Tailwind scale
- **Motion:** `duration-fast` (120ms), `duration-normal` (200ms), `ease-standard`
- **Layers:** `z-dropdown`, `z-modal`, `z-toast`, `z-tooltip`

## tokens.css template (Tailwind v4)

```css
/* src/styles/tokens.css */
@custom-variant dark (&:where(.dark, .dark *));

/*
 * Raw variables all carry a project prefix (--tf- in this example) and are mapped to
 * Tailwind namespaces in @theme. Never write a same-name mapping such as
 * `--radius-control: var(--radius-control)`: @theme variables are also emitted on :root,
 * so the same name becomes a self-reference and stops working.
 */
:root {
  color-scheme: light;
  --tf-bg: #f7f9f8;
  --tf-surface: #ffffff;
  --tf-surface-2: #f5f8f6;
  --tf-elevated: #ffffff;
  --tf-overlay: rgb(15 23 20 / 0.42);

  --tf-fg: #17201b;
  --tf-fg-muted: #5a665f;
  --tf-fg-subtle: #97a19b;
  --tf-fg-on-primary: #ffffff;

  --tf-border: #e4eae6;
  --tf-border-strong: #d2dad5;
  --tf-ring: rgb(28 154 79 / 0.4);
  --tf-hover: #edf3ef;
  --tf-active: #e2ebe5;

  --tf-primary: #1c9a4f;
  --tf-primary-hover: #168243;
  --tf-primary-soft: #e2f4e8;

  --tf-success: #16a34a;  --tf-success-soft: #dcfce7;
  --tf-warning: #d97706;  --tf-warning-soft: #fef3c7;
  --tf-danger: #dc2626;   --tf-danger-soft: #fee2e2;
  --tf-info: #2563eb;     --tf-info-soft: #dbeafe;

  --tf-radius-control: 7px;
  --tf-radius-popover: 10px;
  --tf-radius-card: 12px;

  --tf-shadow-card: 0 1px 2px rgb(16 24 20 / 0.04);
  --tf-shadow-popover: 0 10px 28px rgb(16 24 20 / 0.12), 0 0 0 1px var(--tf-border);
  --tf-shadow-modal: 0 24px 64px rgb(16 24 20 / 0.22), 0 0 0 1px var(--tf-border);
}

.dark {
  color-scheme: dark;
  --tf-bg: #0f1311;
  --tf-surface: #161b18;
  --tf-surface-2: #1b211d;
  --tf-elevated: #1e2521;
  --tf-overlay: rgb(0 0 0 / 0.6);
  --tf-fg: #e6ece8;
  --tf-fg-muted: #a2ada6;
  --tf-fg-subtle: #6c7870;
  --tf-fg-on-primary: #04120a;
  --tf-border: #262e29;
  --tf-border-strong: #35403a;
  --tf-ring: rgb(52 196 109 / 0.45);
  --tf-hover: #212923;
  --tf-active: #29332c;
  --tf-primary: #34c46d;
  --tf-primary-hover: #4cd181;
  --tf-primary-soft: #16301f;
  --tf-success-soft: #16301f;
  --tf-warning-soft: #332611;
  --tf-danger-soft: #3a1717;
  --tf-info-soft: #172640;
  --tf-shadow-popover: 0 10px 28px rgb(0 0 0 / 0.5), 0 0 0 1px var(--tf-border);
}

@theme inline {
  --color-bg: var(--tf-bg);
  --color-surface: var(--tf-surface);
  --color-surface-2: var(--tf-surface-2);
  --color-elevated: var(--tf-elevated);
  --color-overlay: var(--tf-overlay);
  --color-fg: var(--tf-fg);
  --color-fg-muted: var(--tf-fg-muted);
  --color-fg-subtle: var(--tf-fg-subtle);
  --color-fg-on-primary: var(--tf-fg-on-primary);
  --color-border: var(--tf-border);
  --color-border-strong: var(--tf-border-strong);
  --color-ring: var(--tf-ring);
  --color-hover: var(--tf-hover);
  --color-active: var(--tf-active);
  --color-primary: var(--tf-primary);
  --color-primary-hover: var(--tf-primary-hover);
  --color-primary-soft: var(--tf-primary-soft);
  --color-success: var(--tf-success);  --color-success-soft: var(--tf-success-soft);
  --color-warning: var(--tf-warning);  --color-warning-soft: var(--tf-warning-soft);
  --color-danger: var(--tf-danger);    --color-danger-soft: var(--tf-danger-soft);
  --color-info: var(--tf-info);        --color-info-soft: var(--tf-info-soft);

  --radius-control: var(--tf-radius-control);
  --radius-popover: var(--tf-radius-popover);
  --radius-card: var(--tf-radius-card);

  --shadow-card: var(--tf-shadow-card);
  --shadow-popover: var(--tf-shadow-popover);
  --shadow-modal: var(--tf-shadow-modal);

  --spacing-control-sm: 1.75rem;
  --spacing-control-md: 2rem;
  --spacing-control-lg: 2.25rem;

  --animate-fade-in: tf-fade-in 150ms ease-out;
  --animate-pop-in: tf-pop-in 160ms cubic-bezier(0.16, 1, 0.3, 1);
  @keyframes tf-fade-in { from { opacity: 0; } }
  @keyframes tf-pop-in { from { opacity: 0; transform: scale(0.97) translateY(-4px); } }
}

/* z-index layers: Tailwind v4 has no z-index theme namespace, so define them with @utility */
@utility z-dropdown { z-index: 40; }
@utility z-modal { z-index: 50; }
@utility z-toast { z-index: 60; }
@utility z-tooltip { z-index: 70; }
```

> `@theme inline` makes utilities reference `var(--tf-xxx)` directly, so toggling `.dark` needs no CSS regeneration. `--spacing-control-md` generates classes such as `h-control-md` and `size-control-md`.
> Do not rely on plugins such as `tailwindcss-animate` for animations (`animate-in`/`fade-in` do not exist by default in v4); define your own with `--animate-*` + `@keyframes`.
> Styles that a single color token cannot express, such as gradients, are defined one by one as named `@utility` classes (e.g. `tile-violet`); `--value()` in `@utility name-*` cannot build variable names.
> In a monorepo where the component library or plugins live in separate packages, the entry CSS must add them explicitly with `@source "../../packages/ui/src";`.

## index.css entry

```css
/* src/styles/index.css */
@import "tailwindcss";
@import "./tokens.css";

@layer base {
  html, body, #app { height: 100%; }
  body { @apply bg-bg text-fg font-sans antialiased; }
  ::selection { background: var(--tf-primary-soft); }
  * { scrollbar-width: thin; scrollbar-color: var(--tf-border-strong) transparent; }
  :focus-visible { outline: 2px solid var(--tf-ring); outline-offset: 1px; }
}
```

## Tailwind v3 fallback

v3 projects use `darkMode: 'class'` in `tailwind.config.js` and map tokens in `theme.extend.colors`,
e.g. `surface: 'var(--surface)'`. When opacity modifiers are needed, store the variable as an `R G B` triple and write `'rgb(var(--surface) / <alpha-value>)'`. Upgrade to v4 whenever possible.

## Rules for adding tokens

- First check whether an existing token can express it; only add one if not, and **always provide both the light and the dark value**.
- Names describe purpose, not color (`--tag-json` ✅, `--light-orange` ❌).
- Domain-specific palettes (charts, syntax highlighting, tag categories) use numbered groups: `--chart-1..8`.
