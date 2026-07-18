---
kind: frontend_style
name: Tailwind + Radix UI Design System with CSS Variables Theming
category: frontend_style
scope:
    - '**'
source_files:
    - frontend/tailwind.config.ts
    - frontend/src/styles/globals.css
    - frontend/src/context/ThemeContext.tsx
    - frontend/src/lib/utils.ts
    - frontend/src/components/ui/button.tsx
    - frontend/src/components/ui/card.tsx
---

The frontend uses a modern, token-driven styling stack centered on Tailwind CSS v3 combined with Radix UI primitives and a custom component library. Visual consistency is achieved through CSS custom properties (HSL tokens) that power both light and dark themes, while class composition utilities keep component styles composable and conflict-free.

**Styling framework & toolchain**
- Tailwind CSS v3 with `tailwind.config.ts` extending the default theme with design tokens (colors, border radius, box shadows, keyframes/animations).
- PostCSS + Autoprefixer for vendor prefixing.
- Vite as the build/dev server; TypeScript throughout.
- `class-variance-authority` (CVA) for variant-based component styling (`variant`, `size` props), paired with `clsx` + `tailwind-merge` via a shared `cn()` helper in `src/lib/utils.ts` to safely merge Tailwind classes.

**Design tokens & theming**
- All colors are defined as HSL CSS variables under `:root` and `.dark` in `src/styles/globals.css` (e.g. `--primary`, `--destructive`, `--card`, `--ring`).
- `tailwind.config.ts` maps these variables into semantic color aliases (`border`, `input`, `ring`, `background`, `foreground`, `primary`, `secondary`, `muted`, `accent`, `destructive`, `card`) so components reference tokens rather than raw values.
- A React `ThemeProvider` in `src/context/ThemeContext.tsx` manages three modes — `light | dark | system` — persisted in `localStorage` under the key `cloudbridge.theme`. It toggles the `light`/`dark` class on `<html>` and listens to `prefers-color-scheme` changes when mode is `system`.
- The `ThemeToggle` component exposes the toggle API to users.

**Component library architecture**
- Base UI primitives live in `src/components/ui/` (button, card, dialog, dropdown-menu, input, label, select, tabs, toast, tooltip, badge, avatar, skeleton, switch, separator, accordion). Each is a thin wrapper around a Radix primitive or a styled HTML element, using CVA variants where appropriate and always passing className through `cn(...)`.
- Domain-specific wrappers live in `src/components/migrations/` (MigrationForm, ConfirmDeleteDialog, StatusBadge) and layout pieces in `src/components/layout/` (AppShell, Sidebar, TopNavbar).
- Icons come from `lucide-react`; charts from `recharts`.

**Animation & motion conventions**
- Custom keyframes (`slide-in-left`, `fade-in`, `scale-in`, `accordion-down/up`) and named animations are declared in `tailwind.config.ts` and used via Tailwind's `animate-*` utilities.
- `framer-motion` is available for more complex transitions but the base layer prefers CSS keyframes for simplicity.

**Responsive strategy**
- Fully responsive via Tailwind's mobile-first breakpoint utilities; no separate media-query files. Global scrollbar styling and selection colors are applied at the base layer in `globals.css`.

**Rules developers should follow**
1. **Use semantic tokens, not raw colors.** Reference `bg-primary`, `text-muted-foreground`, etc. — never hardcode hex/hsl values in components.
2. **Compose with `cn()` from `@/lib/utils`.** Always pass user-supplied className through `cn(baseClasses, props.className)` so overrides work.
3. **Prefer CVA for multi-variant components.** Define `variant` and `size` variants via `cva()` and expose them as typed props (see `Button`).
4. **Wrap Radix primitives, don't use them raw.** Build small, themed wrappers in `components/ui/` that apply consistent spacing, typography, and ring/focus styles.
5. **Keep theme logic out of components.** Use `useTheme()` from `@/context/ThemeContext` only when you need to react to theme changes; otherwise rely on CSS variables.
6. **Animations belong in Tailwind config.** Add new keyframes/animations in `tailwind.config.ts` under `theme.extend.keyframes` / `animation` rather than inline `@keyframes`.
7. **Dark-mode support is opt-in per page.** Pages must be wrapped by `ThemeProvider` (already done at app root) and use the `.dark` selector for any non-token overrides.