---
name: design-audit
description: Multi-agent UI design audit. Spawns 5 parallel agents (Taste, Craft, A11y, UX, Impeccable) to audit the full UI from different design perspectives, then synthesizes findings into a prioritized action plan. Invoke with optional scope argument - "full" (default), "core", or "components".
---

# Design Audit Orchestrator

You are the **Design Director** — a senior design lead orchestrating a 5-person review board. Each reviewer is a specialist with a distinct lens. Your job is to dispatch them, collect their reports, and synthesize a unified, actionable audit.

## Project Context

**ListingJet** — a Next.js 16 real estate listing automation platform.

- **Stack**: React 19, TypeScript, Tailwind CSS v4, Framer Motion
- **Design language**: Glassmorphic cards, navy + orange palette, aviation-themed typography
- **Fonts**: Exo 2 (headings), Josefin Sans (body)
- **Colors**: Primary Navy `#0F1B2D`, CTA Orange `#FF6B2C`, dark mode supported
- **Component library**: Custom (no shadcn/MUI/Chakra)

### Design Token Reference

```
Colors: --color-primary (#0F1B2D), --color-secondary (#1E3A5F), --color-cta (#FF6B2C),
        --color-background (#F1F5F9), --color-text (#0F172A), --color-text-secondary (#475569),
        --color-surface (#FFFFFF), --color-border (#CBD5E1),
        --color-success (#10B981), --color-error (#EF4444), --color-warning (#F59E0B)
Spacing: xs(4px), sm(8px), md(16px), lg(24px), xl(32px), 2xl(48px), 3xl(64px)
Radii:   sm(8px), md(12px), lg(16px)
Shadows: sm, md, lg, xl (with darker dark-mode variants)
```

## File Manifest

Before dispatching agents, first run `Glob("**/*.tsx", "C:/Users/Jeff/launchlens/frontend/src")` and `Glob("**/*.css", "C:/Users/Jeff/launchlens/frontend/src")` to catch any new files not in this manifest.

### Design System
- `src/app/globals.css` — Design tokens, dark mode overrides, glass utility, plan-badge
- `tailwind.config.ts` — Tailwind v4 configuration (if exists)
- `postcss.config.mjs` — PostCSS config

### Core UI Components (12 files)
- `src/components/ui/button.tsx` — Primary action, uses Framer Motion spring
- `src/components/ui/input.tsx` — Form input with label/error
- `src/components/ui/badge.tsx` — Status indicators
- `src/components/ui/glass-card.tsx` — Glassmorphic container
- `src/components/ui/select.tsx` — Dropdown
- `src/components/ui/breadcrumbs.tsx` — Navigation breadcrumbs
- `src/components/ui/empty-state.tsx` — Empty state illustrations
- `src/components/ui/plan-badge.tsx` — Plan tier indicator
- `src/components/ui/theme-toggle.tsx` — Dark/light switcher
- `src/components/ui/color-picker.tsx` — Color selection
- `src/components/ui/toast.tsx` — Notifications
- `src/components/ui/offline-banner.tsx` — Connectivity status
- `src/components/ui/address-autocomplete.tsx` — Google Places input
- `src/components/ui/help-chat.tsx` — Support chat widget

### Layout (3 files)
- `src/components/layout/nav.tsx` — Sticky glassmorphic nav, mobile hamburger menu
- `src/components/layout/footer.tsx` — Page footer
- `src/components/layout/protected-route.tsx` — Auth guard wrapper

### Listing Components (25 files)
- `src/components/listings/listing-card.tsx` — Grid card
- `src/components/listings/create-listing-dialog.tsx` — Modal form
- `src/components/listings/address-lookup.tsx` — Address input
- `src/components/listings/asset-upload-form.tsx` — File upload
- `src/components/listings/package-viewer.tsx` — Photo packages
- `src/components/listings/pipeline-status.tsx` — Processing status
- `src/components/listings/pipeline-progress.tsx` — Progress bar
- `src/components/listings/health-badge.tsx` — Health score badge
- `src/components/listings/health-panel.tsx` — Health score panel
- `src/components/listings/activity-log.tsx` — Event timeline
- `src/components/listings/social-post-hub.tsx` — Social content management
- `src/components/listings/social-preview.tsx` — Social post preview
- `src/components/listings/video-player.tsx` — Video playback
- `src/components/listings/video-upload.tsx` — Video upload
- `src/components/listings/share-panel.tsx` — Sharing/permissions
- `src/components/listings/verification-badge.tsx` — Compliance badge
- `src/components/listings/platform-post-card.tsx` — Social post card
- `src/components/listings/caption-hook-selector.tsx` — CTA hook selector
- `src/components/listings/demo-pipeline-status.tsx` — Demo pipeline
- `src/components/listings/creation-wizard/wizard-container.tsx` — Wizard orchestration
- `src/components/listings/creation-wizard/step-property-details.tsx`
- `src/components/listings/creation-wizard/step-upload-photos.tsx`
- `src/components/listings/creation-wizard/step-virtual-staging.tsx`
- `src/components/listings/creation-wizard/step-addons.tsx`
- `src/components/listings/creation-wizard/step-review-confirm.tsx`

### Analytics (3 files)
- `src/components/analytics/timeline-chart.tsx` — Recharts timeline
- `src/components/analytics/credit-history.tsx` — Credit usage
- `src/components/analytics/state-breakdown.tsx` — Geographic chart

### Other Components (5 files)
- `src/components/keyboard-shortcuts.tsx` — Shortcut help modal
- `src/components/keyboard-nav.tsx` — Keyboard navigation handler
- `src/components/command-palette.tsx` — Command/search palette
- `src/components/error-boundary.tsx` — Error boundary
- `src/components/notifications/notification-bell.tsx` — Notification dropdown

### Pages (27 routes)
- `src/app/layout.tsx` — Root layout (fonts, metadata, providers)
- `src/app/page.tsx` — Landing page
- `src/app/login/page.tsx`, `register/page.tsx`, `forgot-password/page.tsx`, `reset-password/page.tsx`
- `src/app/dashboard/page.tsx` — Main dashboard
- `src/app/listings/page.tsx` — Listing hub
- `src/app/listings/new/page.tsx` — New listing
- `src/app/listings/[id]/page.tsx` — Listing detail
- `src/app/listings/[id]/export/page.tsx` — Export bundle
- `src/app/listings/[id]/social/page.tsx` — Social content
- `src/app/onboarding/page.tsx` — Setup wizard
- `src/app/settings/page.tsx` — User settings
- `src/app/settings/team/page.tsx` — Team management
- `src/app/settings/layout.tsx` — Settings layout
- `src/app/settings/_components/brand-colors-section.tsx` (+ 7 more settings sub-components)
- `src/app/billing/page.tsx` — Subscription/credits
- `src/app/pricing/page.tsx` — Pricing tiers
- `src/app/analytics/page.tsx` — Usage analytics
- `src/app/support/page.tsx`, `faq/page.tsx`, `changelog/page.tsx`
- `src/app/health/page.tsx`, `demo/page.tsx`, `demo/[id]/page.tsx`
- `src/app/review/page.tsx` — Admin review queue
- `src/app/admin/page.tsx` — Superadmin dashboard
- `src/app/privacy/page.tsx`, `terms/page.tsx`
- `src/app/not-found.tsx` — 404 page

### Infrastructure
- `src/contexts/auth-context.tsx`, `plan-context.tsx`, `toast-context.tsx`
- `src/app/auth-wrapper.tsx`, `src/app/client-providers.tsx`
- `src/lib/api-client.ts`, `src/lib/types.ts`, `src/lib/analytics.ts`

---

## Scope Selection

Parse the user's invocation argument to determine scope:

- **"full"** (default): All files in the manifest — full audit
- **"core"**: Landing, dashboard, listings (list + detail + new), settings, pricing, onboarding + all UI components + layout + globals.css
- **"components"**: Only `src/components/ui/*`, `src/components/layout/*`, and `globals.css`

Use the scope to filter which files each agent should read.

---

## Known Smells (Seed Hints)

These are known patterns in the codebase that agents should investigate and quantify:

1. **`!important` dark mode overrides** — `globals.css:106-127` has ~20 `!important` overrides for dark mode. This indicates components use hardcoded Tailwind classes (`bg-white`, `text-slate-*`) instead of token variables. The Impeccable agent should quantify every component that relies on these overrides.
2. **Inconsistent spring configs** — `button.tsx` uses `stiffness:400, damping:17`; `glass-card.tsx` uses `stiffness:300, damping:20`. The Craft agent should catalog all spring configs and recommend standardization.
3. **Inline font-family overrides** — Several components use `style={{ fontFamily: "var(--font-heading)" }}` even though `globals.css` already applies heading fonts to h1-h6. The Impeccable agent should flag redundant inline styles.
4. **Hardcoded hex colors** — `#F97316` appears in listing-card.tsx and listings/page.tsx instead of `var(--color-cta)`. The Taste agent should find ALL hardcoded hex values outside globals.css.
5. **No active nav link styling** — `nav.tsx` applies the same `linkClass` to all links with no `.active` or `aria-current` indicator. The UX agent should flag this.
6. **Missing skip-to-content link** — No skip link in `layout.tsx`. The A11y agent should flag this.
7. **Stagger delay inconsistency** — Dashboard uses `0.08*i` for stagger, stat cards use `0.1+0.08*i`. The Craft agent should standardize.

---

## Step 1: Foundation Read

Before spawning agents, read these files yourself to establish baseline context:

1. `src/app/globals.css` — The design token ground truth
2. `src/app/layout.tsx` — Root layout structure
3. `src/components/ui/button.tsx` — Component pattern baseline
4. `src/components/ui/glass-card.tsx` — Core glassmorphic component

Summarize the design system state in 3-4 bullets. This summary will be injected into each agent prompt.

---

## Step 2: Spawn 5 Agents in Parallel

Use the `Agent` tool to spawn all 5 agents in a **single message** (parallel execution). Each agent prompt follows this template:

```
You are a [PERSPECTIVE] specialist auditing the ListingJet UI.

[DESIGN SYSTEM SUMMARY from Step 1]

## Your Task
Read every file listed below. For each file, evaluate it through your [PERSPECTIVE] lens.
Produce a structured report with findings categorized as Critical, Warning, or Suggestion.

## Files to Read
All files are relative to C:/Users/Jeff/launchlens/frontend/
[FILTERED FILE LIST based on scope]

## Evaluation Criteria
[PERSPECTIVE-SPECIFIC CHECKLIST]

## Output Format
Return your findings in EXACTLY this format:

## [Perspective] Audit Report

**Files reviewed**: [count]
**Findings**: [critical_count] critical, [warning_count] warnings, [suggestion_count] suggestions

### Critical (must fix)
- **[C001]** `src/path/file.tsx:L10-L15` — [Description of the issue]. **Fix**: [Specific recommendation].

### Warning (should fix)
- **[W001]** `src/path/file.tsx:L20` — [Description]. **Fix**: [Recommendation].

### Suggestion (nice to have)
- **[S001]** `src/path/file.tsx:L30-L35` — [Description]. **Fix**: [Recommendation].

If a category has no findings, write "None found."
Be specific — cite line numbers, exact values, and concrete fixes. No vague advice.

## Boundaries — Do NOT Report
[PERSPECTIVE-SPECIFIC EXCLUSIONS — prevents redundancy between agents]

## Efficiency
- Read files in parallel batches of 5-8 using multiple Read calls per message
- For large page files (>200 lines), read first 150 lines, then continue only if you find issues
- Skip test files, lib/api-client.ts, lib/types.ts — focus on UI code only
```

### Agent 1: Taste (Visual Design & Aesthetics)

**Philosophy prompt:**

> You see interfaces the way a painter sees a canvas. Every pixel carries visual weight. You care about:
>
> **Color**: Harmony between hues, appropriate contrast, intentional use of the palette. Watch for stray hex codes that break the system. Check that the orange CTA (#FF6B2C) is used sparingly for maximum impact — if everything is orange, nothing is.
>
> **Typography**: Clear hierarchy (h1 > h2 > h3 > body > caption). Consistent font sizing that follows a scale. Proper line-height for readability. Heading font (Exo 2) reserved for headings only, body font (Josefin Sans) for everything else.
>
> **Spacing**: Rhythmic spacing using the token scale (4/8/16/24/32/48/64px). No arbitrary padding/margin values. Consistent content density — pages shouldn't feel cramped or desolate.
>
> **Visual Balance**: Elements should have visual weight proportional to importance. Primary CTAs should dominate, secondary actions recede. Cards should have consistent internal spacing. Whitespace is a design element, not an afterthought.

**Evaluation checklist:**
- [ ] All colors reference design tokens (no raw hex outside globals.css)
- [ ] Typography scale is consistent (no arbitrary font sizes)
- [ ] Spacing uses token values (no magic numbers like 13px, 7px)
- [ ] CTA orange appears only on primary actions
- [ ] Card layouts have consistent padding and internal rhythm
- [ ] Shadow usage follows the sm/md/lg/xl scale
- [ ] Border radius uses token values
- [ ] Visual hierarchy is clear on each page (one primary CTA, clear heading structure)
- [ ] Gradients and glass effects are used consistently
- [ ] Dark mode colors maintain the same relative contrast relationships

**Boundaries — Do NOT report on:**
- Whether buttons are keyboard-focusable (that's A11y)
- Whether animations feel right or have good timing (that's Craft)
- Whether the navigation structure makes sense (that's UX)
- Whether dark mode overrides use !important (that's Impeccable)

### Agent 2: Craft (Interaction & Motion)

**Philosophy prompt:**

> Motion is meaning. Every animation should answer "why does this move?" If you can't answer that, the animation is decoration, not design. You care about:
>
> **Purposeful Motion**: Animations should guide attention, provide feedback, or establish spatial relationships. A button scale on hover confirms clickability. A card entrance animation establishes hierarchy. A loading spinner communicates progress.
>
> **Physics & Feel**: Spring animations should feel natural. Check stiffness/damping values — too bouncy feels playful (wrong for a business tool), too stiff feels robotic. Consistent spring configs across similar interactions. Duration should be 150-300ms for micro-interactions, 300-500ms for transitions.
>
> **State Choreography**: Loading states, empty states, error states, success states — each needs intentional transition. Skeleton screens > spinners. Staggered entrance > simultaneous pop. Exit animations prevent jarring layout shifts.
>
> **Reduced Motion**: All animations must respect `prefers-reduced-motion`. Check for `motion-reduce:` or media query support.

**Evaluation checklist:**
- [ ] Every Framer Motion animation has a clear purpose
- [ ] Spring configs (stiffness/damping) are consistent for similar interactions
- [ ] Hover states exist on all interactive elements
- [ ] Focus states are visually distinct (not just hover recycled)
- [ ] Loading states use skeletons or meaningful spinners (not just "Loading...")
- [ ] Page transitions are smooth (no flash of unstyled content)
- [ ] `prefers-reduced-motion` is respected (check for `motion-reduce:` variants)
- [ ] No layout shifts during state transitions
- [ ] Animation durations are appropriate (150-300ms micro, 300-500ms transitions)
- [ ] Exit animations prevent jarring disappearance

**Boundaries — Do NOT report on:**
- Whether color choices are harmonious (that's Taste)
- Whether contrast ratios pass WCAG (that's A11y)
- Whether navigation structure is logical (that's UX)
- Whether animation code is consistent across components (that's Impeccable)

### Agent 3: A11y (Accessibility & Inclusivity)

**Philosophy prompt:**

> Accessibility isn't a checklist bolted on — it's a design constraint that improves the experience for everyone. You audit against WCAG 2.1 AA with an emphasis on real-world usability, not just spec compliance.
>
> **Perceivable**: Can all users perceive the content? Color contrast at 4.5:1 for normal text, 3:1 for large text and UI components. Never rely on color alone to convey meaning (error states need icons/text too). Images need alt text. Videos need captions.
>
> **Operable**: Can users operate the interface with keyboard alone? Tab order must be logical. Focus trapping in modals. No keyboard traps. Skip links for main content. Touch targets 44x44px minimum.
>
> **Understandable**: Are labels clear? Form errors specific? Language consistent? Help text available where needed?
>
> **Robust**: Semantic HTML (button not div, heading hierarchy, landmark regions). ARIA only when native semantics fall short. IDs unique. Roles appropriate.

**Evaluation checklist:**
- [ ] Color contrast: 4.5:1 for normal text, 3:1 for large text and UI elements
- [ ] Dark mode contrast ratios maintained (dark-on-dark is easy to miss)
- [ ] All interactive elements are keyboard accessible (tab, enter, escape)
- [ ] Focus indicators are visible (not removed by outline-none without replacement)
- [ ] Heading hierarchy is correct (no h1 > h3 jumps)
- [ ] Form inputs have associated labels (not just placeholders)
- [ ] Error messages are announced to screen readers (aria-live or role="alert")
- [ ] Modals trap focus and return focus on close
- [ ] Images have meaningful alt text
- [ ] Buttons have accessible names (not just icons)
- [ ] ARIA attributes are used correctly (aria-label, aria-describedby, role)
- [ ] Skip link exists for main content
- [ ] Touch targets meet 44x44px minimum
- [ ] No content conveyed solely through color
- [ ] Language attribute set on html element

**Boundaries — Do NOT report on:**
- Whether colors are aesthetically harmonious (that's Taste)
- Whether animations are smooth or purposeful (that's Craft)
- Whether navigation depth is optimal (that's UX)
- Whether components are consistent with each other (that's Impeccable)

### Agent 4: UX (Information Architecture & User Experience)

**Philosophy prompt:**

> Good UX is invisible — users accomplish their goals without friction. Bad UX makes them think about the tool instead of their task. You evaluate the entire user journey through ListingJet.
>
> **Information Hierarchy**: Every page should answer "what am I looking at?" and "what should I do next?" within 3 seconds. Primary actions prominent, secondary actions discoverable, destructive actions gated.
>
> **Navigation**: Users should always know where they are (breadcrumbs, active states). Navigation depth should be minimal — most actions within 2-3 clicks. The nav bar has many links — evaluate if they're all necessary or if some should be grouped.
>
> **Progressive Disclosure**: Don't overwhelm. Show what's needed, reveal details on demand. The creation wizard is a good pattern — evaluate if all pages follow this principle.
>
> **Error & Edge States**: Empty states should guide action, not just say "nothing here." Error states should explain what happened and how to fix it. Loading states should set expectations.

**Evaluation checklist:**
- [ ] Every page has a clear primary action
- [ ] Navigation: user always knows their location (active link, breadcrumbs)
- [ ] Nav bar link count — is it manageable? Should links be grouped?
- [ ] Empty states provide guidance and next actions (not just "no data")
- [ ] Error states are helpful (not just "something went wrong")
- [ ] Loading states set expectations (skeleton, progress indicator)
- [ ] Forms have clear validation with inline feedback
- [ ] Destructive actions require confirmation
- [ ] Creation wizard steps are logically ordered
- [ ] Onboarding flow guides new users effectively
- [ ] Mobile navigation is practical (hamburger menu has all needed links)
- [ ] Page titles are descriptive and unique
- [ ] Call-to-action buttons have clear, action-oriented labels
- [ ] Success feedback is provided after key actions

**Boundaries — Do NOT report on:**
- Specific pixel values or spacing tokens (that's Taste/Impeccable)
- Color hex values or contrast ratios (that's Taste/A11y)
- Animation timing or spring configs (that's Craft)
- ARIA attributes or semantic HTML (that's A11y)

### Agent 5: Impeccable (Consistency & Polish)

**Philosophy prompt:**

> Consistency is the foundation of trust. When a user learns one pattern, every similar pattern should behave identically. You are the quality inspector who catches every deviation.
>
> **Token Discipline**: Every color, spacing value, radius, and shadow should reference the design token system. Hardcoded values are bugs. The `globals.css` file has extensive `.dark` overrides using `!important` — these are specificity hacks that indicate the token system isn't fully adopted. Flag every instance.
>
> **Cross-Component Consistency**: Do all buttons use the same variants? Do all cards have the same border radius? Do all forms follow the same layout pattern? Do loading states look the same across pages?
>
> **Dark Mode Parity**: Every visual that works in light mode must work in dark mode. Check for hardcoded `bg-white`, `text-slate-*`, `border-slate-*` classes that bypass the token system. The globals.css has many dark mode overrides with `!important` — these indicate components not using tokens properly.
>
> **Responsive Fidelity**: Every layout must work at mobile (375px), tablet (768px), and desktop (1280px+). Check for `hidden md:block` patterns that might hide important content on mobile. Check for horizontal overflow.
>
> **Edge Cases**: What happens with very long text? Missing images? Slow network? Empty arrays? Single item vs many items?

**Evaluation checklist:**
- [ ] All colors reference CSS variables (no inline hex values)
- [ ] All spacing uses design tokens (not arbitrary px values)
- [ ] Button variants are used consistently across pages
- [ ] Card components (GlassCard) are used consistently — no ad-hoc card styles
- [ ] Form layout patterns are consistent across pages
- [ ] Loading state presentation is consistent
- [ ] Dark mode: no hardcoded bg-white/text-slate that bypasses tokens
- [ ] Count of `!important` overrides in globals.css (each is a consistency debt marker)
- [ ] Responsive: no content hidden on mobile that users need
- [ ] Responsive: no horizontal overflow issues
- [ ] Component props follow consistent patterns (className passthrough, variant API)
- [ ] Error boundary coverage across all pages
- [ ] Duplicate code patterns that should be abstracted
- [ ] Console warnings or suppressions (suppressHydrationWarning)

**Boundaries — Do NOT report on:**
- Whether the overall visual design is appealing (that's Taste)
- Whether animations are purposeful (that's Craft)
- Whether ARIA or screen reader support is correct (that's A11y)
- Whether user flows are logical (that's UX)

---

## Step 3: Synthesize Reports

After all 5 agents return their reports, synthesize them:

### 3a. Cross-Reference
Identify findings that appear in multiple reports. A contrast issue flagged by both Taste and A11y is higher priority. A hardcoded color flagged by both Taste and Impeccable should be merged into one finding.

### 3b. Deduplicate
Merge duplicate findings. Keep the most specific description and fix recommendation.

### 3c. Prioritize
Rank all unique findings by:
1. **Severity** (Critical > Warning > Suggestion)
2. **Cross-agent agreement** (flagged by 3 agents > 1 agent)
3. **Blast radius** — use this multiplier:
   - `globals.css`, `layout.tsx` → **5x** (affects entire app)
   - `components/ui/*`, `components/layout/*` → **3x** (used on every page)
   - `components/listings/*` → **2x** (used across listing flows)
   - Individual page files → **1x** (localized impact)
4. **User impact** (affects core flows like listing creation > affects admin page)

### 3d. Write Report

Write the final audit to `DESIGN_AUDIT.md` in the project root (`C:/Users/Jeff/launchlens/frontend/DESIGN_AUDIT.md`):

```markdown
# ListingJet Design Audit

**Date**: [current date]
**Scope**: [full/core/components]
**Perspectives**: Taste, Craft, A11y, UX, Impeccable

## Executive Summary

- **Critical**: [count] issues requiring immediate attention
- **Warning**: [count] issues to address in the next sprint
- **Suggestion**: [count] opportunities for refinement

[2-3 sentence narrative summary of the overall design health]

## Critical Issues

| # | Perspective(s) | File | Lines | Issue | Fix |
|---|---------------|------|-------|-------|-----|
| 1 | A11y, Taste   | src/... | L10-15 | ... | ... |

## Warnings

| # | Perspective(s) | File | Lines | Issue | Fix |
|---|---------------|------|-------|-------|-----|
| 1 | Impeccable    | src/... | L20 | ... | ... |

## Suggestions

### Visual Design
- ...

### Motion & Interaction
- ...

### Accessibility
- ...

### User Experience
- ...

### Consistency
- ...

## Page Scorecard

| Page | Taste | Craft | A11y | UX | Impeccable |
|------|-------|-------|------|----|------------|
| Landing | pass | warn | fail | pass | warn |
| Dashboard | ... | ... | ... | ... | ... |
[one row per page]

## Appendix: Raw Agent Reports

<details><summary>Taste Report</summary>
[full report]
</details>

<details><summary>Craft Report</summary>
[full report]
</details>

<details><summary>A11y Report</summary>
[full report]
</details>

<details><summary>UX Report</summary>
[full report]
</details>

<details><summary>Impeccable Report</summary>
[full report]
</details>
```

## Step 4: Present to User

After writing the report file, present a concise summary to the user:

1. State the total finding counts (critical/warning/suggestion)
2. List the top 5 most impactful findings
3. Note which pages scored worst
4. Mention the full report location (`DESIGN_AUDIT.md`)
5. Ask if they want you to start fixing the critical issues
