---
name: tailwind-token-ui
description: General standard for a "design-token theme + in-house component library" built on Tailwind CSS v4. Use this skill in any project (Tauri / Vue / React / plain frontend, especially Forge desktop apps such as ToolForge and CodeForge) whenever you set up or change Tailwind styles, themes, dark mode or UI components, create components such as Button/Input/Select/Checkbox/Switch/Modal/Tooltip/Tabs, or see native <select>/<input type="checkbox|radio|range|date|color|file">/<dialog>/title tooltips in a page. Core rules - colors, radii, shadows and spacing always go through semantic tokens (bg-surface, text-fg-muted, border-border…); business code must never hard-code values such as bg-gray-100, text-blue-600 or #hex; native browser controls are forbidden and must be replaced by the project's own components. Triggers include "tailwind", "theme", "token", "dark mode", "component library", "UI components", "styles", "theming", "主题", "暗色模式", "组件库", "UI 组件", "样式", "换肤".
---

# Tailwind Token Theme + In-House Component Library

## Two iron rules

1. **Semantic tokens only, never the raw palette.** Business code and components may only use semantic classes such as `bg-surface`, `text-fg-muted`, `border-border`, `bg-primary`, `rounded-control` and `shadow-popover`. Forbidden: `bg-gray-100`, `text-blue-600`, `bg-[#1e293b]`, inline `style="color:#..."`, `dark:bg-gray-800`.
   *Why:* switching themes (light/dark/brand color) only changes token values and components stay untouched. Once raw palette classes creep in, dark mode needs patches everywhere (CodeForge today is the counter-example).
2. **No native interactive controls; always use dedicated components.** The elements in the left column must never appear directly in pages; use the project components on the right:

| Forbidden | Replacement component |
|-----------|-----------------------|
| `<select>` / `<datalist>` | `Select`, `Combobox` (searchable) |
| `<input type="checkbox">` | `Checkbox`, `Switch` |
| `<input type="radio">` | `RadioGroup` / `SegmentedControl` |
| `<input type="range">` | `Slider` |
| `<input type="number">` | `NumberInput` (with stepper buttons) |
| `<input type="date/time">` | `DatePicker` / `TimePicker` |
| `<input type="color">` | `ColorPicker` |
| `<input type="file">` | `FileDrop` (use the dialog plugin under Tauri) |
| `<dialog>`, `alert/confirm/prompt` | `Modal` / `ConfirmDialog` / `Toast` |
| `title="..."` tooltips | `Tooltip` |
| Native scrollbar styling | Global tokenized scrollbar or `ScrollArea` |
| Bare `<button>` / `<input>` / `<textarea>` | `Button` / `Input` / `Textarea` |

Components may use native elements **internally** as an accessibility foundation (e.g. Checkbox wraps an `sr-only` input, Input renders an `<input>`), but only the wrapped component is exposed.

## Workflow

1. **Inspect the project:** Tailwind version (`tailwindcss` in `package.json`; v4 uses `@import "tailwindcss"`), framework (Vue/React), and whether a `src/ui` / `src/components/ui` directory and a token file already exist. If they do, follow and complete them; **do not start a parallel system**.
2. **Token layer:** if missing, create `src/styles/tokens.css` (CSS variables + `@theme inline` mapping) and `src/styles/index.css` following `references/tokens.md`.
3. **Component layer:** implement components under `src/ui/` following the list and API conventions in `references/components.md`, with consistent `variant` / `size` / `disabled` / `v-model` conventions.
4. **Business layer:** pages only compose `src/ui` components and use semantic token classes for layout.
5. **Self-check:** run the violation scan below; it must print nothing before you deliver.

## Violation scan (run before delivering)

```bash
# 1) Native controls (excluding the internals of src/ui components)
grep -rnE '<select|<datalist|type="(checkbox|radio|range|number|date|time|color|file)"|<dialog|window\.(alert|confirm|prompt)|\btitle="' src --include=*.vue --include=*.tsx --include=*.jsx | grep -v '/ui/'
# 2) Raw palette / hard-coded colors
grep -rnE '\b(bg|text|border|ring|fill|stroke|from|to|via|outline|divide|shadow)-(slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|black|white)(-[0-9]{2,3})?\b|#[0-9a-fA-F]{3,8}\b|\[(#|rgb|hsl|oklch)' src --include=*.vue --include=*.tsx --include=*.jsx --include=*.ts
# 3) dark: variants (tokens already handle dark mode; business code must not use them)
grep -rn 'dark:' src --include=*.vue --include=*.tsx --include=*.jsx | grep -v 'styles/'
```

Fix every hit: replace colors with semantic tokens, replace native controls with components, and add missing tokens/components to the token or component layer first. When an exception is genuinely needed (third-party editor themes, chart palettes), define the colors centrally as tokens (e.g. `--chart-1..8`) instead of scattering them through business code.

## Dark mode and theme switching

- Use the `class` strategy: `<html class="dark">` or `data-theme="dark"`. The CSS `@custom-variant dark (&:where(.dark, .dark *));` is for the token layer only.
- Theme storage: Tauri projects persist it in the app store/config; the default follows the system (listen to `matchMedia('(prefers-color-scheme: dark)')`).
- Brand colors / multiple themes: add a `[data-theme="xxx"]` block that overrides only a few variables such as `--primary*`.
- Avoid a flash on the first frame: inline a script in `index.html` `<head>` that reads the setting and sets the class immediately.

## Reference files

- `references/tokens.md`: token naming system, full `tokens.css` template (light/dark), Tailwind v4 `@theme` mapping, v3 fallback.
- `references/components.md`: component list (by priority), shared API conventions, Vue 3 and React templates (Button / Select), accessibility and keyboard requirements.

## Visual quality (modern and polished by default)

Unless the project has its own design spec, apply these defaults (benchmarks: Raycast / Linear / Vercel):

- **Hierarchy comes from whitespace and font weight, not lines and color blocks:** body `text-sm text-fg`, secondary information `text-fg-muted`; drop dividers wherever possible; cards use `bg-surface` + a 1px `border-border` + `shadow-card`.
- **4/8pt grid:** spacing only uses the 1/1.5/2/3/4/6/8 steps; control heights always use `h-control-*`.
- **One accent color:** `primary` is only for primary actions, selected states and focus rings; everything else stays in neutral grays.
- **Three radius levels:** control (buttons/inputs) < popover (floating layers) < card; when nesting, inner radius = outer radius − padding.
- **Restrained motion:** 120–200 ms, `ease-out`; only transition opacity / transform / colors; respect `prefers-reduced-motion`.
- **Complete states:** every component designs all seven states (hover, active, focus-visible, disabled, loading, empty, error), with none missing.
- **Empty and loading states:** an empty list or area shows an icon + explanation + primary action; loading longer than 300 ms uses a Skeleton, not just a spinner.
- **Desktop apps:** use a custom title bar; give the sidebar a translucent material where supported (macOS vibrancy / Windows Mica) and fall back to `bg-surface-2` otherwise; disable text selection and image dragging in body content, but keep input and result areas selectable.
- Before delivering, screenshot both the light and dark themes and check contrast (body text ≥ 4.5:1).
