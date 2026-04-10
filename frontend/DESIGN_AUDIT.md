# ListingJet Design Audit

**Date**: 2026-04-09
**Scope**: Full
**Perspectives**: Taste, Craft, A11y, UX, Impeccable

## Executive Summary

- **Critical**: 22 unique issues requiring immediate attention
- **Warning**: 38 unique issues to address in the next sprint
- **Suggestion**: 27 opportunities for refinement

The design token system is well-structured but poorly adopted. Auth/marketing pages were built before the token system existed and never migrated — they account for 70%+ of hardcoded hex violations. The `help-chat.tsx` component was dropped in from a generic template and uses an entirely foreign color palette (gray/blue). Accessibility has significant gaps: no skip link, no focus traps in any modal/dialog, no `prefers-reduced-motion` support anywhere, and form errors are invisible to screen readers. Motion design is inconsistent with 3+ different spring configurations and many components lacking entrance/exit animations.

---

## Critical Issues

| # | Perspective(s) | File | Issue | Fix |
|---|---------------|------|-------|-----|
| 1 | A11y | `layout.tsx:60` | No skip-to-content link (WCAG 2.4.1 Level A failure) — keyboard users must tab through entire nav on every page | Add `<a href="#main-content" class="sr-only focus:not-sr-only ...">Skip to main content</a>` as first child of `<body>`, add `id="main-content"` to content wrapper |
| 2 | Craft, A11y | `globals.css` + all components | Zero `prefers-reduced-motion` support anywhere in codebase — all animations play for users who have OS-level reduced motion enabled | Add `@media (prefers-reduced-motion: reduce)` global override in globals.css; add `useReducedMotion()` guards in GlassCard tilt, badge pulse, pipeline spin |
| 3 | Taste, Craft, A11y, Impeccable | `help-chat.tsx` (entire file) | Component uses gray/blue palette (`bg-gray-100`, `bg-blue-600`, `text-gray-900`, `focus:ring-blue-500`), no tokens, no dialog role, no focus trap, no enter/exit animation — a rogue design island on every authenticated page (4 agents flagged) | Full rewrite: map to token colors, add `role="dialog" aria-modal="true"`, focus trap, AnimatePresence enter/exit |
| 4 | A11y | `command-palette.tsx:131-202` | Modal has no `role="dialog"`, no `aria-modal`, no focus trap — focus escapes into obscured page | Add dialog semantics and focus trapping |
| 5 | A11y | `create-listing-dialog.tsx:121-358` | Same modal accessibility failures as #4 — no dialog role, no focus trap | Add `role="dialog" aria-modal="true" aria-labelledby`, focus trap, return focus on close |
| 6 | A11y | `keyboard-shortcuts.tsx:39-76` | Same modal failures — no dialog role, no aria-label, no focus trap | Add dialog semantics and focus trapping |
| 7 | A11y | `share-panel.tsx:110-283` | Slide-in overlay has no dialog role, no focus trap, close button lacks aria-label | Add `role="dialog" aria-modal="true"`, focus trap, `aria-label="Close share panel"` |
| 8 | Taste, Impeccable | `glass-card.tsx:51` | Uses hardcoded `bg-white/70` and `dark:bg-[rgba(30,41,59,0.7)]` instead of the `.glass` utility already defined in globals.css (wrong dark color value too) | Replace with `className="glass"` utility or `bg-[var(--color-surface)]/70` |
| 9 | Taste, Impeccable | `listings/page.tsx:102`, `listings/[id]/page.tsx:137`, `onboarding/page.tsx:231` + 40 more | CTA buttons use hardcoded `bg-[#F97316]` / `hover:bg-[#ea580c]` instead of `<Button variant="primary">` — creates two competing CTA color systems | Replace all with `<Button variant="primary">` or `bg-[var(--color-cta)]` |
| 10 | Taste, Impeccable | `login/page.tsx`, `register/page.tsx`, `onboarding/page.tsx` | Auth pages hard-code `bg-[#0B1120]` (not `--color-primary` #0F1B2D) and `bg-[#F5F7FA]` (not `--color-background` #F1F5F9) — wrong hex values | Replace with `bg-[var(--color-primary)]` and `bg-[var(--color-background)]` |
| 11 | Taste, Impeccable | `health-panel.tsx:29-78` | Uses `bg-white`, `text-slate-700`, `text-slate-900`, `bg-slate-100` — no tokens. Unreadable in dark mode without `!important` patch | Replace with `bg-[var(--color-card)]`, `text-[var(--color-text)]`, `text-[var(--color-text-secondary)]` |
| 12 | Taste | `pipeline-status.tsx:76-78` | Uses `bg-blue-500` / `text-blue-600` for active stage — blue is not in the design palette | Replace with `bg-[var(--color-cta)]` / `text-[var(--color-cta)]` |
| 13 | Taste | `activity-log.tsx:129` | Avatar fallback is `var(--color-primary, #F97316)` — the fallback is CTA orange, not primary navy | Change fallback to `#0F1B2D` or remove it |
| 14 | UX | `nav.tsx:15` | No active link styling — every nav link looks identical, users cannot tell where they are | Use `usePathname()` and apply distinct style (e.g., `font-semibold border-b-2 border-[var(--color-cta)]`) when path matches |
| 15 | UX | `listings/[id]/page.tsx:74` | Page title is always "Listing Detail | ListingJet" regardless of property — 10 tabs are indistinguishable | Update to `${listing.address.street} | ListingJet` on load |
| 16 | UX | `settings/team/page.tsx:519` | Invite form asks for new member's password — entering someone else's credentials is a trust-breaking anti-pattern | Replace with email-link invite flow; replace `window.confirm` with branded modal |
| 17 | A11y | `login/page.tsx`, `register/page.tsx`, `forgot-password/page.tsx`, `reset-password/page.tsx` | Form error messages are plain `<p>` with no `role="alert"` — invisible to screen readers | Add `role="alert"` to all error paragraphs |
| 18 | A11y | `address-autocomplete.tsx:49-86` | No combobox ARIA pattern — no `role="combobox"`, no `aria-expanded`, no `role="listbox"`, no keyboard arrow navigation | Implement full ARIA combobox pattern with arrow key support |
| 19 | Craft | `pipeline-progress.tsx:79` | Spinner uses `animate-spin` on Unicode `⟳` character — unreliable cross-browser, no reduced-motion guard | Replace with SVG spinner, add reduced-motion guard |
| 20 | Craft | `empty-state.tsx` | Zero animation on a component that signals "nothing here yet" — appears as a hard cut | Add `motion.div` entrance with `opacity: 0→1, y: 10→0` |
| 21 | Craft | `listings/[id]/page.tsx:136-141` | Full-page loading is a raw spinner with no skeleton — entire page snaps in on resolve | Replace with skeleton matching page layout (breadcrumb, header, pipeline dots, two-column grid) |
| 22 | Impeccable | `billing/page.tsx:26-32` | `TX_TYPE_STYLES` hard-codes `bg-green-50 text-green-700`, `bg-blue-50`, `bg-red-50` — bypasses success/error/warning tokens | Map to `bg-[var(--color-success)]/10 text-[var(--color-success)]` etc. |

## Warnings

| # | Perspective(s) | File | Issue | Fix |
|---|---------------|------|-------|-----|
| 1 | Impeccable | 28 files | `style={{ fontFamily: "var(--font-heading)" }}` on `<h1>`–`<h6>` elements — redundant, globals.css already applies heading font to all headings | Remove all 28 instances |
| 2 | Taste | `listings/[id]/page.tsx:225+` | 7 content panels use `bg-white rounded-2xl border border-slate-100` instead of `<GlassCard>` — two card styles on same page | Standardize to `<GlassCard tilt={false}>` or `bg-[var(--color-card)]` |
| 3 | Craft | `button.tsx` vs `glass-card.tsx` vs `notification-bell.tsx` | 3 different spring configs: `400/17`, `300/20`, `400/30` — inconsistent perceived weight | Standardize to two spring tokens: MICRO (400/17) and SURFACE (350/25) |
| 4 | Craft | `dashboard/page.tsx:208-241` | Stagger delays expressed two ways: `0.1 + 0.08*i` vs `0.08*i` — functionally identical but confusing | Standardize to variants pattern with `delay: i * 0.08` |
| 5 | Taste | `billing/page.tsx:386`, `pricing/page.tsx:248-249,375` | Gradients and backgrounds use `#0B1120` / `#1a2744` (wrong primary values) | Replace with `var(--color-primary)` / `var(--color-secondary)` |
| 6 | Taste | `register/page.tsx:99` | Left panel gradient uses 3 hardcoded hex values not matching any token | Replace with `from-[var(--color-primary)] via-[var(--color-secondary)] to-[var(--color-primary)]` |
| 7 | Impeccable | `color-picker.tsx:22,32` | Uses `border-white/20 bg-white/60` — bypasses input tokens, renders ghost-white in dark mode | Use `border-[var(--color-input-border)] bg-[var(--color-input-bg)]` |
| 8 | Taste | `listings/page.tsx:186-202` | Permission badge uses `bg-blue-50 text-blue-600` — blue not in design system | Replace with `bg-[var(--color-primary)]/10 text-[var(--color-primary)]` |
| 9 | Craft | `wizard-container.tsx:156-162` | Backward navigation still slides left-to-right — spatially inverted | Track direction in state, use `direction * 30` for initial/exit x values |
| 10 | Craft | `toast.tsx:61-63` | Exit animates `y: -10` (up) but entry is from `y: 20` (up) — exit direction inverted | Change exit to `y: 20` (down) to match entry, add spring transition |
| 11 | Craft | `theme-toggle.tsx:40-54` | Sun/moon icon swap has no animation — instant DOM swap on highest-visibility toggle | Add `AnimatePresence mode="wait"` with rotation micro-animation |
| 12 | Craft | `listing-card.tsx:114-139` | Delete confirm UI swap causes instant layout shift — buttons replace icon with no transition | Wrap in `AnimatePresence mode="wait"` with scale/opacity |
| 13 | Craft | `social-post-hub.tsx:126-130` | Loading state is raw spinner, no skeleton for 3-column card layout | Replace with 3-column skeleton matching PlatformPostCard structure |
| 14 | A11y | `notification-bell.tsx:56-68` | Bell button doesn't communicate unread count to screen readers | Make `aria-label` dynamic: `Notifications, ${unreadCount} unread` |
| 15 | A11y | `notification-bell.tsx:91-97` | "Mark all read" has `focus:outline-none` with no replacement focus indicator | Replace with `focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]` |
| 16 | A11y | `listings/page.tsx:114-135` | Tab toggle has no `role="tablist"` / `role="tab"` / `aria-selected` semantics | Add proper ARIA tab pattern |
| 17 | A11y | `pipeline-status.tsx:88-93` | Stage dots convey state entirely through color/scale — no text alternative for screen readers | Add visually-hidden labels to each dot |
| 18 | A11y | `offline-banner.tsx:25-34` | Dynamic banner has no `role="alert"` — screen readers won't announce connectivity change | Add `role="alert"` to motion.div |
| 19 | A11y | `listing-card.tsx:33-38` | `role="button"` div contains nested real `<button>` elements — violates ARIA authoring practices | Convert outer to `<article>`, make card navigation a proper `<a>` or scoped `<button>` |
| 20 | A11y | `share-panel.tsx:250-257` | Permission-change `<select>` has no label or aria-label | Add `aria-label` with grantee name |
| 21 | A11y | `wizard-container.tsx:124-151` | Step indicator nav has no `aria-current="step"` on active step | Add `aria-current="step"` and `aria-label` to nav |
| 22 | UX | `nav.tsx` | 8+ flat top-level links with no hierarchy | Group into primary/utility sections, collapse Help/Support/Changelog into dropdown |
| 23 | UX | `onboarding/page.tsx` | Registration redirects to `/dashboard` not `/onboarding` — guided first-run never triggers | Push to `/onboarding` after register |
| 24 | UX | `analytics/page.tsx` | No empty state for accounts with zero data — new users see empty charts | Detect zero-activity and render `<EmptyState>` with CTA |
| 25 | UX | `listings/[id]/export/page.tsx` | CMA/microsite failures silently swallowed via `.catch(() => {})` | Track per-resource error state, show inline retry |
| 26 | UX | `support/page.tsx:74-78` | Ticket fetch failure silently caught — empty list with no explanation | Set error state, render retry button |
| 27 | UX | `wizard-container.tsx` | Virtual Staging step is optional upsell but offers no skip affordance | Add "Skip this step" link |
| 28 | UX | `settings/layout.tsx` | Settings and Team are separate routes with no in-page sidebar linking them | Add persistent settings sidebar with active-link styling |
| 29 | UX | `listings/page.tsx` | Error state tracked but no error UI rendered when fetch fails — blank page | Render full-page error state with retry |
| 30 | Impeccable | `social-post-hub.tsx:138,149` + `platform-post-card.tsx:109` | Card container uses custom dark rgba instead of `--color-card` | Unify to `bg-[var(--color-card)]` |
| 31 | Impeccable | `input.tsx:27` + 3 more files | Error state uses raw `border-red-400`/`text-red-500` instead of `--color-error` | Replace with `border-[var(--color-error)]` / `text-[var(--color-error)]` |
| 32 | Impeccable | `listings/page.tsx:115-131` | Tab toggle uses raw `bg-white text-slate-900` bypassing tokens | Use `bg-[var(--color-card)] text-[var(--color-text)]` |
| 33 | Impeccable | `keyboard-shortcuts.tsx:42-43` | Modal uses `bg-white border-slate-200` with no dark classes — relies on !important patch | Use `bg-[var(--color-card)] border-[var(--color-card-border)]` |
| 34 | Impeccable | `login/page.tsx`, `register/page.tsx` | Auth pages build raw `<input>` elements instead of using `<Input>` component | Replace with `<Input>` component |
| 35 | Impeccable | `globals.css:110-126` | 22 `!important` overrides contain 6 undocumented hex aliases (#162032, #1E2D42, etc.) | Define named tokens for these values |
| 36 | Impeccable | `logos-section.tsx:98,107,204` | Hardcodes `#FF6B2C` (light CTA) — shows wrong orange in dark mode | Replace with `var(--color-cta)` |
| 37 | Impeccable | `hud-preview.tsx:243` | Save button uses `bg-[#FF6B2C]` instead of `<Button variant="primary">` | Replace with Button component |
| 38 | Impeccable | `plan-badge.tsx:51-52` | Upgrade badge uses raw `bg-amber-100 text-amber-700` | Map to `bg-[var(--color-warning)]/15 text-[var(--color-warning)]` |

## Suggestions

### Visual Design
- Badge component (`badge.tsx`) uses hardcoded Tailwind palette for all states — low contrast in dark mode. Add dark variants or convert to CSS custom properties.
- Landing page stat numbers use `text-slate-900` — replace with `text-[var(--color-text)]`.
- Offline banner uses `bg-yellow-500` — replace with `bg-[var(--color-warning)]`.
- Pipeline progress uses Unicode characters instead of consistent SVG icons.
- Analytics time range toggle uses `bg-white/10` — nearly invisible on light backgrounds.
- Skeleton loading states use `bg-white/50` — should use `bg-[var(--color-surface)]`.

### Motion & Interaction
- Badge pulse should use `ease: "easeInOut"` and `repeatType: "mirror"` for smoother breathing.
- Landing page stagger: cap delay at `Math.min(i * 0.07, 0.3)` for fast scrollers (9 cards = 0.8s delay on last).
- Activity log entries should stagger-animate to reinforce timeline metaphor.
- Offline banner should use spring transition for consistency.
- Virtual staging photo selection toggle needs AnimatePresence on checkmark overlay.
- Caption hook selector needs cross-fade on text swap between tabs.
- Addon card checkmarks need AnimatePresence for satisfying credit-action confirmation.
- Onboarding progress bar should delay initial animation by 0.4s to let page settle.
- Standardize stagger deltas: pipeline-progress (0.03) and social-preview (0.05) → unify at 0.04.

### Accessibility
- Button should use `focus-visible:ring-2` instead of `focus:ring-2` to suppress ring on mouse click.
- Color picker has redundant `aria-label` when `<label>` already provides accessible name.
- Video player chapter buttons should use `sr-only` span instead of unreliable `title` attribute.
- Breadcrumbs should mark current page with `aria-current="page"`.
- Listing card placeholder SVG should have `aria-hidden="true"`.
- Plan badge font-size 10px is below informal browser minimum — raise to 12px (0.75rem).
- External links in Terms/Privacy checkbox should warn "(opens in new tab)" for screen readers.

### User Experience
- Dashboard empty state CTA should be above stat cards, not below fold.
- Listing card inline delete confirm should be replaced with named modal.
- `/pricing` should redirect authenticated users to `/billing` to avoid duplication.
- `/review` should gate at route level by role, not rely on API 403s.
- Forgot-password success should show inline confirmation on same page.
- Social post success should trigger toast ("Copied" / "Scheduled").

### Consistency
- Spacing tokens (`--space-xs` through `--space-3xl`) are defined but never referenced — all components use Tailwind values directly. Either remove tokens or create Tailwind plugin.
- CTA token has two values: `#FF6B2C` (light) and `#F97316` (dark) — some files hardcode one, some the other. Product decision needed: should CTA shift in dark mode?
- Error boundary uses raw `bg-red-100 text-red-500` instead of `--color-error` token.
- No `suppressHydrationWarning` issues found (positive).

## Page Scorecard

| Page | Taste | Craft | A11y | UX | Impeccable |
|------|-------|-------|------|----|------------|
| Landing (`page.tsx`) | warn | pass | warn | pass | warn |
| Login | fail | pass | fail | pass | fail |
| Register | fail | pass | fail | warn | fail |
| Dashboard | warn | warn | warn | warn | warn |
| Listings Hub | fail | warn | fail | fail | fail |
| Listing Detail | fail | fail | warn | fail | fail |
| New Listing | warn | warn | fail | pass | warn |
| Settings | warn | pass | warn | fail | warn |
| Team Settings | pass | pass | warn | fail | pass |
| Billing | fail | pass | pass | pass | fail |
| Pricing | fail | pass | pass | warn | fail |
| Onboarding | fail | warn | warn | fail | fail |
| Analytics | warn | pass | pass | fail | warn |
| Support | pass | pass | pass | fail | pass |
| Admin/Review | pass | pass | pass | warn | pass |

**Legend**: pass = no issues, warn = warnings only, fail = has critical issues

## Token Violation Census (Impeccable)

| Category | Count | Worst Offenders |
|----------|-------|----------------|
| Hardcoded hex colors | 217 across 40+ files | listing detail, login, register, onboarding, billing, pricing |
| Inline `fontFamily` overrides | 28 instances | dashboard, listings, billing, login, register, onboarding |
| `bg-white` without dark pair | ~35 instances | health-panel, listing detail, keyboard-shortcuts, auth pages |
| Raw `text-slate-*` / `border-slate-*` | ~90+ instances | health-panel, activity-log, footer, platform-post-card |
| Raw `bg-gray-*` / `text-gray-*` | ~20 instances | help-chat (entire component) |
| Semantic color bypassing tokens | 83 instances | billing (TX_TYPE_STYLES), health-panel, error-boundary |
| `!important` overrides | 22 | globals.css lines 106-126 |

## Spring Config Catalog (Craft)

| Component | Stiffness | Damping | Context |
|-----------|-----------|---------|---------|
| button.tsx | 400 | 17 | hover/tap scale |
| glass-card.tsx | 300 | 20 | tilt rotateX/Y |
| notification-bell.tsx | 400 | 30 | dropdown open/close |
| plan-badge.tsx | default | default | hover/tap (no config) |
| video-player.tsx | default | default | chapter buttons (no config) |
| All other components | — | — | No spring, duration-based or CSS transitions |

**Recommendation**: Standardize to two spring tokens:
- `SPRING_MICRO = { stiffness: 400, damping: 17 }` — buttons, badges, chips
- `SPRING_SURFACE = { stiffness: 350, damping: 25 }` — panels, dropdowns, modals

## Root Causes

1. **Auth/marketing pages built before token system** — never migrated, account for 70%+ of hardcoded hex violations
2. **`#F97316` used as inline stand-in** for `Button variant="primary"` — fix is to use the component
3. **help-chat.tsx dropped from a template** — generic gray/blue chat UI never adapted to ListingJet design system
4. **22 `!important` overrides are symptoms** — they exist because components use raw Tailwind instead of tokens. Fixing token violations will allow most to be removed
5. **No accessibility review was ever performed** — every modal/dialog lacks ARIA semantics and focus trapping

---

<details><summary>Taste Report (8 critical, 17 warnings, 9 suggestions)</summary>

### Critical
- C001: glass-card.tsx hardcoded bg-white/70 instead of .glass utility
- C002: help-chat.tsx entire foreign gray/blue palette
- C003: listings/page.tsx raw button with bg-[#F97316] instead of Button component
- C004: Multiple pages use bg-[#F5F7FA] instead of --color-background
- C005: listings/[id]/page.tsx uses bg-[#0B1120] (wrong primary hex)
- C006: health-panel.tsx all slate classes, no tokens
- C007: pipeline-status.tsx uses blue (not in palette) for active stage
- C008: activity-log.tsx avatar fallback is CTA orange instead of primary navy

### Warnings
W001-W017: Hardcoded hex values across listings/[id], billing, pricing, register, dashboard, listing-card, social-post-hub, color-picker, package-viewer. See full Taste report.

### Suggestions
S001-S009: Badge dark mode, landing page stats, offline banner yellow, pipeline Unicode chars, grid layout edge case, analytics toggle, wizard input, skeleton colors, tab toggle.

</details>

<details><summary>Craft Report (6 critical, 14 warnings, 9 suggestions)</summary>

### Critical
- C001: help-chat.tsx panel has zero enter/exit animation
- C002: command-palette.tsx and keyboard-shortcuts.tsx modals mount/unmount with no animation
- C003: pipeline-progress.tsx Unicode spinner unreliable
- C004: empty-state.tsx has zero animation
- C005: No prefers-reduced-motion support anywhere in codebase
- C006: listing detail loading state is raw spinner, no skeleton

### Warnings
W001-W014: Inconsistent spring configs, stagger delay inconsistency, toast exit direction inverted, theme toggle no animation, listing card delete layout shift, social-post-hub loading, demo-pipeline ring styling, tab content no transition, approval banner aggressive scale, health panel bar no entrance, pipeline stage no completion celebration.

### Suggestions
S001-S009: Badge pulse easing, landing stagger cap, activity log stagger, offline banner spring, virtual staging selection, caption cross-fade, addon checkmarks, onboarding progress delay, stagger delta standardization.

</details>

<details><summary>A11y Report (9 critical, 18 warnings, 7 suggestions)</summary>

### Critical
- C001: No skip-to-content link (WCAG 2.4.1)
- C002: command-palette.tsx no dialog role, no focus trap
- C003: create-listing-dialog.tsx no dialog role, no focus trap
- C004: share-panel.tsx no dialog role, no focus trap
- C005: keyboard-shortcuts.tsx no dialog role, no focus trap
- C006: Auth page form errors not announced to screen readers
- C007: address-autocomplete.tsx no combobox ARIA pattern
- C008: video-upload.tsx unlinked label
- C009: share-panel.tsx unlinked labels

### Warnings
W001-W018: Notification bell unread count, focus:outline-none without replacement, address autocomplete label linkage, wizard step indicator no aria-current, listing card nested interactive elements, non-functional button, help-chat title-only accessible names, help-chat no dialog/focus trap, tab toggle no ARIA tabs, pipeline dots color-only, badge motion-only indicator, login pulse dot, share panel unlabeled selects, revoke button title-only, brand kit banner no role, offline banner no role, dashboard pipeline color-only bars, wizard validation error no role.

### Suggestions
S001-S007: Button focus-visible, color picker redundant aria-label, video player sr-only spans, breadcrumbs aria-current, listing card aria-hidden SVG, plan-badge minimum font size, external link warnings.

</details>

<details><summary>UX Report (4 critical, 9 warnings, 6 suggestions)</summary>

### Critical
- C001: No active nav link styling — users can't tell where they are
- C002: Listing detail page title always "Listing Detail" regardless of property
- C003: Team invite asks for new member's password — trust-breaking anti-pattern
- C004: Error boundary fallback may strand users with no recovery action

### Warnings
W001-W009: Nav link overload (8+ flat links), onboarding never triggered for new users, analytics no empty state, export failures silently swallowed, support fetch failure silent, wizard virtual staging no skip, settings no sidebar navigation, 404 page may be dead end, listings fetch error shows blank page.

### Suggestions
S001-S006: Dashboard empty state above fold, listing card delete modal, pricing/billing dedup, review page role gate, forgot-password inline confirm, social post toast feedback.

</details>

<details><summary>Impeccable Report (8 critical, 14 warnings, 6 suggestions)</summary>

### Critical
- C001: help-chat.tsx entire gray/blue palette (no tokens)
- C002: Auth/onboarding pages hardcode wrong hex values for primary/background
- C003: 40+ instances of bg-[#F97316] instead of Button component or var(--color-cta)
- C004: health-panel.tsx all slate classes, no tokens
- C005: billing TX_TYPE_STYLES bypass success/error/warning tokens
- C006: glass-card.tsx ignores .glass utility and --color-card token
- C007: logos-section.tsx hardcodes #FF6B2C (wrong in dark mode)
- C008: hud-preview.tsx save button hardcodes #FF6B2C instead of Button component

### Warnings
W001-W014: 28 redundant fontFamily overrides, plan-badge raw amber, landing page raw slate/white, social-post-hub custom dark rgba, input error raw red, tab toggle raw classes, keyboard-shortcuts raw bg-white, activity-log fontFamily, hud-preview labels fontFamily, color-picker bypasses input tokens, ad-hoc card styles in listing detail, globals.css undocumented hex aliases, help-chat focus ring blue, auth pages raw inputs instead of Input component.

### Suggestions
S001-S006: Unused spacing tokens, empty-state text-slate, CTA dark mode decision needed, error-boundary raw red, pipeline-status needs --color-info token, no suppressHydrationWarning issues (positive).

</details>
