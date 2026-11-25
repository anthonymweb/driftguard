---
name: Clarity SecOps
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#434655'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#006e2d'
  on-secondary: '#ffffff'
  secondary-container: '#7cf994'
  on-secondary-container: '#007230'
  tertiary: '#ac0031'
  on-tertiary: '#ffffff'
  tertiary-container: '#d71142'
  on-tertiary-container: '#ffecec'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#7ffc97'
  secondary-fixed-dim: '#62df7d'
  on-secondary-fixed: '#002109'
  on-secondary-fixed-variant: '#005320'
  tertiary-fixed: '#ffdada'
  tertiary-fixed-dim: '#ffb3b6'
  on-tertiary-fixed: '#40000c'
  on-tertiary-fixed-variant: '#920028'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  display:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.025em
  display-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  code-snippet:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-sm: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

This design system establishes an approachable, high-precision security intelligence environment. It directly rejects the trope of dark-terminal, hacker-centric cybersecurity interfaces filled with dense green terminal walls and intimidating ASCII noise. Instead, it draws direct inspiration from modern product benchmarks like Linear and Stripe—pairing engineering rigor with consumer-grade software elegance.

### Emotional Response & Personality
- **Clarity & Composure:** Security incidents provoke anxiety; the UI acts as a stabilizing agent. High legibility, crisp structural hierarchy, and generous negative space instill calm competence.
- **Engineered Precision:** Micro-interactions, tight border rhythms, and clear operational data evoke surgical accuracy without unnecessary visual theatrics.
- **Progressive Disclosure:** Deep forensic metadata remains readily accessible on demand, but top-level screens prioritize triage speed, human-readable summaries, and clear remediation workflows.

### Design Movement
**Modern Refined Functionalism.** The aesthetic relies on luminous off-white backdrops, elevated white surface containers, razor-thin neutral outlines, and targeted micro-accents. Color is deployed strictly as information—guiding triage attention rather than decorating the canvas.

## Colors

The palette is engineered for cognitive speed, utilizing standard security triage semantics re-tuned for balanced contrast on crisp light surfaces.

### Semantic Spectrum & Usage
- **Primary Canvas & Surfaces:** Pure `#FFFFFF` card containers floating over a subtle tinted ground (`#F8FAFC`).
- **Primary Actions & Fresh Signals (`#2563EB`):** Royal blue used for primary CTA buttons, active selection states, workflow triggers, and newly discovered vulnerabilities.
- **Resolved / Hardened (`#16A34A`):** Emerald green indicates verified remediations, clean audit checks, and secured endpoints.
- **Regressions / Severe Threats (`#E11D48`):** Deep rose red communicates critical CVEs, policy regressions, and immediate blockers.
- **Warnings / Drift (`#D97706`):** Balanced amber signals non-blocking warnings, pending reviews, and configuration anomalies.
- **Typography & Structural Slates:**
  - Lead Titles & Data: `#0F172A` (Slate 900)
  - Secondary Context & Metadata: `#64748B` (Slate 500)
  - Subtle Dividing Lines & Outlines: `#E2E8F0` (Slate 200)
  - Muted Interactive Surfaces: `#F1F5F9` (Slate 100)

Never mix alert hues for non-semantic reasons. Status badges should use light tinted background fills with solid high-contrast foreground glyphs and text to preserve balance.

## Typography

The type system balances executive summary presentation with data-dense forensic workflows.

- **Plus Jakarta Sans** provides structural geometry with rounded terminal touches in headings, conveying approachability and modern enterprise polish.
- **Inter** handles all operational reads, data grids, status descriptions, and interactive labels due to its tall x-height and neutral rendering at sub-14px sizes.
- **JetBrains Mono** is reserved strictly for immutable identifiers, commit SHAs, CVE designations, and code snippets. It must never be used for primary UI navigation or labels.

### Scaling & Legibility Rules
- For dense tabular scanning, use `body-sm` (13px) with a tabular figures (`tnum`) OpenType feature enabled.
- Avoid all-caps text unless used in micro-status tags (`label-sm`), which must always carry positive tracking (`+0.04em`).

## Layout & Spacing

The layout philosophy uses a flexible, content-adaptive fluid grid structured around 8px baseline rhythm units.

### Canvas Organization
- **Desktop (1280px+):** Fixed collateral navigation sidebar (240px–260px) paired with an expansive 12-column responsive layout for finding lists, telemetry widgets, and deep-dive inspection panes. Canvas padding sets at `margin` (32px), with `gutter` (24px) between analytical cards.
- **Tablet (768px – 1279px):** Collapsible icon rail (64px) with an 8-column layout. Gutters compress to 16px to maximize data visualization area.
- **Mobile (<768px):** Single-column stacked triage flow. Card margins compress to `margin-mobile` (16px). Complex multi-attribute tables automatically re-render into sequential card modules with collapsible disclosure toggles.

### Whitespace Principles
- Give complex diagnostic data room to breathe. High risk does not warrant claustrophobic spacing.
- Inner card padding must stay uniform: use `space-lg` (24px) for analytical dashboards and `space-md` (16px) for itemized finding lists.

## Elevation & Depth

Visual separation relies on clean surface contrast and low-contrast outlines rather than heavy drop shadows.

### The Layering Stack
1. **Application Ground (`#F8FAFC`):** The canvas background setting off elevated surfaces.
2. **Elevated Containers (`#FFFFFF`):** High-priority workspace cards, issue lists, and telemetry modules. Every container carries a crisp 1px stroke using `#E2E8F0` to clearly define spatial boundaries.
3. **Elevated Interactive Overlays:** Dropdowns, popovers, and slide-over audit panels sit at higher z-index layers. These surfaces use pure white backgrounds, subtle border definition (`#E2E8F0`), and an ultra-diffused, ambient shadow:
   `0 10px 25px -5px rgba(15, 23, 42, 0.04), 0 8px 10px -6px rgba(15, 23, 42, 0.02)`.

No dramatic colored drop shadows or heavy skeuomorphic bevels are permitted. Depth is clean, architectural, and razor-sharp.

## Shapes

The design system maintains a balanced geometry—modern and approachable without becoming excessively bubbly.

- Standard buttons, text inputs, segmented controls, and badges use **8px border radii** (`roundedness: 2`).
- Structural containment elements such as cards, diagnostic charts, and modal panels use **16px border radii** (`rounded-lg`).
- Status indicators, presence dots, and user avatars remain fully circular (`9999px`).
- Sharp 0px corners are reserved exclusively for code preview blocks embedded inside container cards.

## Components

### Buttons & Interactive Triggers
- **Primary:** Solid `#2563EB` fill, white `#FFFFFF` text, subtle inner top-edge highlight. Hover state shifts to `#1D4ED8`. Active state shifts to `#1E40AF`.
- **Secondary:** Surface `#FFFFFF` with `#E2E8F0` border and `#0F172A` text. Hover brings a subtle background tint of `#F8FAFC` and border `#CBD5E1`.
- **Destructive / High-Severity Action:** Solid `#E11D48` or secondary with `#E11D48` text and soft rose hover tint (`#FFE4E6`).
- **Ghost:** No background fill, `#64748B` text, hovering yields `#F1F5F9`.

### Chips & Semantic Status Badges
Status indicators must always prioritize readability over heavy saturation:
- **New / Active:** Background `#EFF6FF`, Border `#BFDBFE`, Text `#1D4ED8`.
- **Resolved / Hardened:** Background `#F0FDF4`, Border `#BBF7D0`, Text `#15803D`.
- **Regression / Critical:** Background `#FFF1F2`, Border `#FECDD3`, Text `#BE123C`.
- **Warning / Review Needed:** Background `#FFFBEB`, Border `#FDE68A`, Text `#B45309`.
- **Neutral / Informational:** Background `#F8FAFC`, Border `#E2E8F0`, Text `#475569`.
Each status chip pairs an inline 6px dot or semantic icon next to `label-sm` text.

### Finding & Issue Lists
- Items sit inside contiguous card lists separated by 1px borders (`#F1F5F9`).
- Left-aligned indicator flags reveal severity level instantly.
- Highlighting rows on hover triggers an effortless transition to `#F8FAFC` with a rightward action shortcut icon becoming visible.

### Input Fields & Search Controls
- Surface: `#FFFFFF` enclosed in a 1px `#E2E8F0` border.
- Text: `#0F172A` with `#94A3B8` placeholder.
- Focus: Transition to `#2563EB` border with a 3px soft blue ring (`rgba(37, 99, 235, 0.12)`). No default browser focus outlines.
- Global Search / Command Bar: Features an integrated keyboard shortcut chip (`⌘K`) in `label-sm` monospaced font.

### Cards & Analytical Panels
- White background (`#FFFFFF`), 1px structural outline (`#E2E8F0`), and 16px corner radius.
- Header bars separate cleanly with an optional subtle lower divider stroke, cleanly housing action filters and contextual timestamps.

### Progressive Disclosure Slide-overs (Drawers)
- Slide-over inspection sheet anchored to the right edge (560px desktop width) for analyzing raw trace logs, reproduction steps, and CVE dossiers without losing context in the primary list.