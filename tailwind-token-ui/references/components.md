# Component library standard

## Directory

```
src/ui/   (packages/ui/src/ in a monorepo; extension per framework: .vue for Vue, .tsx for React)
├── index.ts            # single export entry
├── Button  IconButton  Input  Textarea  NumberInput
├── Select  Combobox  Checkbox  Switch  RadioGroup  SegmentedControl  Slider
├── Modal  ConfirmDialog  Drawer  Popover  DropdownMenu  Tooltip  Toast
├── Tabs  Card  Badge  Kbd  Divider  Empty  Spinner  Skeleton  ScrollArea  Progress
├── FileDrop  ColorPicker  CodeBlock  CopyButton  LogViewer (virtualized log, colored by level)
└── hooks/ or composables/   # useFloating, useClickOutside, useFocusTrap, useId, useTheme
```

## Priorities

- **P0 (required in the first week):** Button, IconButton, Input, Textarea, Select, Checkbox, Switch, Tooltip, Modal, Toast, Tabs, Card, ScrollArea
- **P1:** Combobox, NumberInput, RadioGroup, SegmentedControl, DropdownMenu, Popover, Badge, Kbd, Empty, Spinner, CopyButton, CodeBlock
- **P2:** Slider, ColorPicker, DatePicker, FileDrop, Drawer, Skeleton

## Shared API conventions

- `size`: `'sm' | 'md' | 'lg'`, default `md`; heights map to `h-control-sm/md/lg`.
- `variant` (Button etc.): `'primary' | 'secondary' | 'ghost' | 'danger' | 'outline'`.
- Form components: Vue uses `v-model`; React uses a controlled `value` + `onValueChange(value)` and also supports an uncontrolled `defaultValue`; all support `disabled`, `readonly`, `invalid` and `placeholder`.
- Selection components take `options: { label: string; value: T; disabled?: boolean; icon?: Component }[]`.
- Forward `class` and undeclared attrs to the root element; merge class names with `cn()` (clsx + tailwind-merge).
- Write variant/size styles as object maps (or `cva`), not long ternaries in templates.
- Use a single icon library (Vue: `lucide-vue-next`, React: `lucide-react`); components never hard-code SVG colors and use `currentColor`.

## Floating components

- Always position with `@floating-ui/vue` (or `@floating-ui/react`): `flip`, `shift`, `offset(4)`, and `size` so dropdowns are at least as wide as their trigger.
- Floating layers are teleported to `body`; z-index uses the `z-dropdown/z-modal/z-toast/z-tooltip` tokens.
- Close on outside click and `Esc`; an open Modal traps focus and locks scrolling, and returns focus to the trigger when closed.

## Accessibility and keyboard

| Component | Requirements |
|------|------|
| Select/Combobox | `role="combobox"` + `listbox/option`, `aria-expanded`, `aria-activedescendant`; ↑↓ to move, Enter to select, Esc to close, type-ahead by first letter; Combobox filters as you type |
| Checkbox/Switch | internal `sr-only` native input, or `role="checkbox|switch"` + `aria-checked`; Space toggles |
| Tabs | `role="tablist/tab/tabpanel"`; ←→ to switch |
| Modal | `role="dialog"`, `aria-modal`, `aria-labelledby` |
| Tooltip | shown after a 400 ms hover/focus delay; `aria-describedby` |

Every interactive element must have a `focus-visible:ring-2 ring-ring` focus style; the disabled state is `opacity-50 pointer-events-none`.

## Vue template: Button.vue

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { cn } from './utils'
import Spinner from './Spinner.vue'

const props = withDefaults(defineProps<{
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  disabled?: boolean
  block?: boolean
}>(), { variant: 'secondary', size: 'md' })

const variants = {
  primary: 'bg-primary text-fg-on-primary hover:bg-primary-hover',
  secondary: 'bg-surface-2 text-fg border border-border hover:bg-hover',
  outline: 'bg-transparent text-fg border border-border-strong hover:bg-hover',
  ghost: 'bg-transparent text-fg-muted hover:bg-hover hover:text-fg',
  danger: 'bg-danger text-fg-on-primary hover:opacity-90',
}
const sizes = {
  sm: 'h-control-sm px-2.5 text-xs gap-1',
  md: 'h-control-md px-3 text-sm gap-1.5',
  lg: 'h-control-lg px-4 text-sm gap-2',
}
const classes = computed(() => cn(
  'inline-flex items-center justify-center rounded-control font-medium select-none',
  'transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
  'disabled:opacity-50 disabled:pointer-events-none',
  variants[props.variant], sizes[props.size], props.block && 'w-full',
))
</script>

<template>
  <button type="button" :class="classes" :disabled="disabled || loading">
    <Spinner v-if="loading" class="size-3.5" />
    <slot />
  </button>
</template>
```

## Vue template: Select.vue (skeleton)

```vue
<script setup lang="ts" generic="T extends string | number">
import { ref, computed } from 'vue'
import { useFloating, offset, flip, shift, size as fSize, autoUpdate } from '@floating-ui/vue'
import { onClickOutside } from '@vueuse/core'
import { ChevronDown, Check } from 'lucide-vue-next'

const model = defineModel<T | null>()
const props = withDefaults(defineProps<{
  options: { label: string; value: T; disabled?: boolean }[]
  placeholder?: string; size?: 'sm' | 'md' | 'lg'; disabled?: boolean
}>(), { placeholder: 'Select…', size: 'md' })

const open = ref(false)
const activeIndex = ref(-1)
const trigger = ref<HTMLElement>(); const panel = ref<HTMLElement>()
const { floatingStyles } = useFloating(trigger, panel, {
  placement: 'bottom-start', whileElementsMounted: autoUpdate,
  middleware: [offset(4), flip(), shift({ padding: 8 }),
    fSize({ apply: ({ rects, elements }) => { elements.floating.style.minWidth = `${rects.reference.width}px` } })],
})
const selected = computed(() => props.options.find(o => o.value === model.value))
onClickOutside(panel, () => (open.value = false), { ignore: [trigger] })

function choose(i: number) { const o = props.options[i]; if (!o || o.disabled) return; model.value = o.value; open.value = false; trigger.value?.focus() }
function onKey(e: KeyboardEvent) {
  if (!open.value && ['Enter', ' ', 'ArrowDown'].includes(e.key)) { open.value = true; activeIndex.value = Math.max(0, props.options.findIndex(o => o.value === model.value)); e.preventDefault(); return }
  if (!open.value) return
  if (e.key === 'ArrowDown') activeIndex.value = Math.min(props.options.length - 1, activeIndex.value + 1)
  else if (e.key === 'ArrowUp') activeIndex.value = Math.max(0, activeIndex.value - 1)
  else if (e.key === 'Enter') choose(activeIndex.value)
  else if (e.key === 'Escape') open.value = false
  else return
  e.preventDefault()
}
</script>

<template>
  <button ref="trigger" type="button" role="combobox" :aria-expanded="open" :disabled="disabled"
    class="inline-flex h-control-md w-full items-center justify-between gap-2 rounded-control border border-border bg-surface px-3 text-sm text-fg hover:border-border-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
    @click="open = !open" @keydown="onKey">
    <span :class="selected ? 'text-fg' : 'text-fg-subtle'" class="truncate">{{ selected?.label ?? placeholder }}</span>
    <ChevronDown class="size-4 text-fg-muted transition-transform" :class="open && 'rotate-180'" />
  </button>
  <Teleport to="body">
    <ul v-if="open" ref="panel" role="listbox" :style="floatingStyles"
      class="z-dropdown max-h-64 overflow-auto rounded-popover bg-elevated p-1 shadow-popover">
      <li v-for="(o, i) in options" :key="String(o.value)" role="option" :aria-selected="o.value === model"
        class="flex cursor-pointer items-center justify-between gap-2 rounded-[calc(var(--radius-popover)-2px)] px-2 py-1.5 text-sm text-fg"
        :class="[i === activeIndex && 'bg-hover', o.disabled && 'opacity-50 pointer-events-none']"
        @mouseenter="activeIndex = i" @click="choose(i)">
        <span class="truncate">{{ o.label }}</span>
        <Check v-if="o.value === model" class="size-4 text-primary" />
      </li>
    </ul>
  </Teleport>
</template>
```

Implement the `size` prop the same way as the `sizes` map in Button; this skeleton is fixed at md for brevity.

## React template: Button.tsx

```tsx
import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from './utils'
import { Spinner } from './Spinner'

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-control font-medium select-none transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:pointer-events-none',
  {
    variants: {
      variant: {
        primary: 'bg-primary text-fg-on-primary hover:bg-primary-hover',
        secondary: 'bg-surface-2 text-fg border border-border hover:bg-hover',
        outline: 'bg-transparent text-fg border border-border-strong hover:bg-hover',
        ghost: 'bg-transparent text-fg-muted hover:bg-hover hover:text-fg',
        danger: 'bg-danger text-fg-on-primary hover:opacity-90',
      },
      size: {
        sm: 'h-control-sm px-2.5 text-xs gap-1',
        md: 'h-control-md px-3 text-sm gap-1.5',
        lg: 'h-control-lg px-4 text-sm gap-2',
      },
      block: { true: 'w-full' },
    },
    defaultVariants: { variant: 'secondary', size: 'md' },
  },
)

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  loading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, block, loading, disabled, children, ...props }, ref) => (
    <button ref={ref} type="button" className={cn(buttonVariants({ variant, size, block }), className)}
      disabled={disabled || loading} {...props}>
      {loading && <Spinner className="size-3.5" />}
      {children}
    </button>
  ),
)
Button.displayName = 'Button'
```

## React template: Select.tsx (skeleton)

```tsx
import { useState, useRef } from 'react'
import { useFloating, useClick, useDismiss, useRole, useListNavigation, useInteractions,
  offset, flip, shift, size as fSize, autoUpdate, FloatingPortal, FloatingFocusManager } from '@floating-ui/react'
import { ChevronDown, Check } from 'lucide-react'
import { cn } from './utils'

export interface Option<T> { label: string; value: T; disabled?: boolean }

export function Select<T extends string | number>({ value, onValueChange, options, placeholder, disabled, className }: {
  value: T | null; onValueChange: (v: T) => void; options: Option<T>[]
  placeholder?: string; disabled?: boolean; className?: string
}) {
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState<number | null>(null)
  const listRef = useRef<(HTMLElement | null)[]>([])
  const selectedIndex = options.findIndex(o => o.value === value)

  const { refs, floatingStyles, context } = useFloating({
    open, onOpenChange: setOpen, placement: 'bottom-start', whileElementsMounted: autoUpdate,
    middleware: [offset(4), flip(), shift({ padding: 8 }),
      fSize({ apply: ({ rects, elements }) => { elements.floating.style.minWidth = `${rects.reference.width}px` } })],
  })
  const { getReferenceProps, getFloatingProps, getItemProps } = useInteractions([
    useClick(context), useDismiss(context), useRole(context, { role: 'listbox' }),
    useListNavigation(context, { listRef, activeIndex, selectedIndex, onNavigate: setActiveIndex, loop: true }),
  ])
  const choose = (i: number) => { const o = options[i]; if (!o || o.disabled) return; onValueChange(o.value); setOpen(false) }
  const selected = options[selectedIndex]

  return (
    <>
      <button ref={refs.setReference} type="button" disabled={disabled} {...getReferenceProps()}
        className={cn('inline-flex h-control-md w-full items-center justify-between gap-2 rounded-control border border-border bg-surface px-3 text-sm hover:border-border-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50', className)}>
        <span className={cn('truncate', selected ? 'text-fg' : 'text-fg-subtle')}>{selected?.label ?? placeholder}</span>
        <ChevronDown className={cn('size-4 text-fg-muted transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <FloatingPortal>
          <FloatingFocusManager context={context} modal={false}>
            <div ref={refs.setFloating} style={floatingStyles} {...getFloatingProps()}
              className="z-dropdown max-h-64 overflow-auto rounded-popover bg-elevated p-1 shadow-popover outline-none">
              {options.map((o, i) => (
                <div key={String(o.value)} ref={el => { listRef.current[i] = el }} role="option"
                  aria-selected={i === selectedIndex} tabIndex={i === activeIndex ? 0 : -1}
                  className={cn('flex cursor-pointer items-center justify-between gap-2 rounded-[calc(var(--radius-popover)-2px)] px-2 py-1.5 text-sm text-fg outline-none',
                    i === activeIndex && 'bg-hover', o.disabled && 'opacity-50 pointer-events-none')}
                  {...getItemProps({ onClick: () => choose(i), onKeyDown: e => { if (e.key === 'Enter') choose(i) } })}>
                  <span className="truncate">{o.label}</span>
                  {i === selectedIndex && <Check className="size-4 text-primary" />}
                </div>
              ))}
            </div>
          </FloatingFocusManager>
        </FloatingPortal>
      )}
    </>
  )
}
```

## utils.ts

```ts
import { clsx, type ClassValue } from 'clsx'
import { extendTailwindMerge } from 'tailwind-merge'
// Teach tailwind-merge the custom token classes so they are not wrongly merged or dropped
// tailwind-merge v3: extend the theme scales, not classGroups
const twMerge = extendTailwindMerge({
  extend: {
    theme: {
      color: ['bg', 'surface', 'surface-2', 'elevated', 'fg', 'fg-muted', 'fg-subtle', 'fg-on-primary',
        'border', 'border-strong', 'ring', 'hover', 'active', 'primary', 'primary-hover', 'primary-soft',
        'success', 'success-soft', 'warning', 'warning-soft', 'danger', 'danger-soft', 'info', 'info-soft'],
      radius: ['control', 'popover', 'card'],
      shadow: ['card', 'popover', 'modal'],
      spacing: ['control-sm', 'control-md', 'control-lg'],
    },
  },
})
export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs))
```

## Component preview page

In development, provide a `/__ui` route (or Histoire/Storybook) that shows every component in every variant × size × state, with a light/dark toggle, as the manual visual regression check.
