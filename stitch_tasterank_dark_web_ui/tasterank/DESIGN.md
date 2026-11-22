---
name: TasteRank
colors:
  surface: '#111318'
  surface-dim: '#111318'
  surface-bright: '#37393f'
  surface-container-lowest: '#0c0e13'
  surface-container-low: '#1a1b21'
  surface-container: '#1e1f25'
  surface-container-high: '#282a2f'
  surface-container-highest: '#33353a'
  on-surface: '#e2e2e9'
  on-surface-variant: '#e4bdba'
  inverse-surface: '#e2e2e9'
  inverse-on-surface: '#2e3036'
  outline: '#ab8886'
  outline-variant: '#5b403e'
  surface-tint: '#ffb3ae'
  primary: '#ffb3ae'
  on-primary: '#68000b'
  primary-container: '#ff5351'
  on-primary-container: '#5c0008'
  inverse-primary: '#bb1522'
  secondary: '#ffb3b1'
  on-secondary: '#611118'
  secondary-container: '#822a2e'
  on-secondary-container: '#ff9e9d'
  tertiary: '#bfc6da'
  on-tertiary: '#293140'
  tertiary-container: '#8991a3'
  on-tertiary-container: '#222a39'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdad7'
  primary-fixed-dim: '#ffb3ae'
  on-primary-fixed: '#410004'
  on-primary-fixed-variant: '#930014'
  secondary-fixed: '#ffdad8'
  secondary-fixed-dim: '#ffb3b1'
  on-secondary-fixed: '#410007'
  on-secondary-fixed-variant: '#7f282c'
  tertiary-fixed: '#dbe2f6'
  tertiary-fixed-dim: '#bfc6da'
  on-tertiary-fixed: '#141c2a'
  on-tertiary-fixed-variant: '#3f4757'
  background: '#111318'
  on-background: '#e2e2e9'
  surface-variant: '#33353a'
typography:
  display:
    fontFamily: Newsreader
    fontSize: 48px
    fontWeight: '600'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-mobile:
    fontFamily: Newsreader
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 44px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Newsreader
    fontSize: 32px
    fontWeight: '500'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Newsreader
    fontSize: 26px
    fontWeight: '500'
    lineHeight: 34px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Newsreader
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 32px
  headline-sm:
    fontFamily: Newsreader
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  section-eyebrow:
    fontFamily: Outfit
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.14em
  body-lg:
    fontFamily: Outfit
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Outfit
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Outfit
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  label-lg:
    fontFamily: Outfit
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Outfit
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Outfit
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.04em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.25rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-tablet: 2rem
  margin-desktop: 3rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system delivers an intimate, atmospheric nocturnal dining experience tailored for discerning food lovers and urban epicures seeking hyper-personalized restaurant discovery. The design aesthetic sits at the intersection of **Dark Food-Tech Precision** and **Editorial Culinary Warmth**, channeling the sensory allure of late-night dining rooms, candlelight on slate tabletops, and Michelin-guide sophistication.

The visual style blends dark minimalism with glassmorphic depth: ultra-deep charcoal grounds, translucent floating surfaces, and targeted crimson-to-coral gradients that direct user attention without sliding into neon or cyberpunk excess. It evokes anticipation, curation, and culinary passion while maintaining absolute functional clarity for search, filtering, and rapid visual scanning of dishes and venues.

## Colors

The palette revolves around deep twilight values punctuated by vivid, culinary-grade reds.

### Palette Architecture
- **Base Canvas (`#0B0D12` to `#10141C`)**: The grounding black-charcoal canvas absorbs distractions and simulates the intimacy of a dimly lit restaurant interior.
- **Primary Red (`#FF4B4B`) & Secondary Coral (`#FF8A8A`)**: Used as a linear gradient (`linear-gradient(135deg, #FF4B4B 0%, #FF8A8A 100%)`) for key actions, primary CTA pills, rank badges, verified tastemaker seals, and focus rings.
- **Tertiary Slate (`#2A3241`)**: Anchors secondary interactive states, category segment tabs, and structural separators.
- **Translucent Layering**: Card bodies use `rgba(255, 255, 255, 0.04)` with subtle hairline borders in `rgba(255, 255, 255, 0.08)`.
- **Text Tiers**:
  - Primary text: `#F2F4F8` for uncompromised readability over dark fields.
  - Secondary text: `#A8B0C0` for metadata, reviewer remarks, and attributes.
  - Muted/Disabled text: `#7C869A` for secondary labels, hints, and timestamp data.
- **Radial Lighting**: Ambient stage lighting utilizes localized, oversized radial blurs of `#FF4B4B` locked to an 18% maximum opacity, contrasted against faint `#182232` slate glows to prevent flat blackouts. No purple, magenta, or neon cyan casts are permitted.

## Typography

Typography establishes an intentional contrast between culinary tradition and algorithmic velocity:
- **Headline Font (Newsreader)**: Delivers an editorial, Michelin-guide character for dining establishment titles, curator quotes, hero statements, and dish nomenclature. Its soft organic serifs ground the dark mode with warmth.
- **Body & Label Font (Outfit)**: A crisp, contemporary geometric sans designed for legibility at density. It manages UI mechanics, ingredient specifications, distance metrics, match percentages, and interactive inputs.
- **Section Eyebrows**: Set in `section-eyebrow` using micro-tracked uppercase letters (`letterSpacing: 0.14em`) to establish crisp section delineations without relying on heavy horizontal rules.

## Layout & Spacing

The layout is built around a responsive fluid grid optimized for high-density culinary imagery and ranked lists.

### Layout System
- **Grid Structure**:
  - Mobile (< 768px): 4-column layout, `margin: 1rem`, `gutter: 1.25rem`.
  - Tablet (768px – 1024px): 8-column layout, `margin-tablet: 2rem`, `gutter: 1.25rem`.
  - Desktop (> 1024px): 12-column layout capped at `1320px` max-width container, `margin-desktop: 3rem`, `gutter-desktop: 1.5rem`.
- **Rhythm**: Element spacing relies strictly on a 4px/8px incremental base. Internal component padding favors vertical compactness paired with generous edge margins, maintaining an airy, premium restaurant bill-of-fare structure.

## Elevation & Depth

Visual hierarchy does not rely on harsh dropshadows or bright borders, but on subtle tonal surfaces and light filtration:

1. **Base Floor (L0)**: Canvas background `#0B0D12` to `#10141C`.
2. **Standard Elevated Cards (L1)**: `background: rgba(255, 255, 255, 0.04)`, `backdrop-filter: blur(16px)`, surrounded by a hairline stroke `border: 1px solid rgba(255, 255, 255, 0.08)`. Deep shadow: `box-shadow: 0 12px 32px -4px rgba(0, 0, 0, 0.5)`.
3. **Hovered & Interactive Surfaces (L2)**: `background: rgba(255, 255, 255, 0.07)`, stroke shifts to `rgba(255, 255, 255, 0.14)`. Shadow expands to `0 16px 40px -4px rgba(0, 0, 0, 0.7)`.
4. **Modal Panels & Drawers (L3)**: Floating sheets use `background: #141822`, overlaying a backdrop blur `blur(20px)` at `rgba(11, 13, 18, 0.8)`.
5. **Warm Focal Bloom**: Key recommendation cards receive an ambient, diffuse drop-glow behind the element using `box-shadow: 0 0 48px -12px rgba(255, 75, 75, 0.18)`.

## Shapes

The design system employs a refined curvature scale anchored at **Level 2 (Rounded)**:
- Standard cards, interactive inputs, and modal sheets utilize `rounded-lg` (16px / `1rem`).
- Small interaction targets (badges, icon buttons, filter chips) default to standard rounding (8px / `0.5rem`).
- Primary call-to-actions, rank badges, and pill chips use fully continuous organic pill forms (`rounded-full` / 9999px) to contrast against rectangular glass photography viewports.

## Components

### Buttons
- **Primary CTA**: Wrapped in full pill shapes (`rounded-full`), filled with `linear-gradient(135deg, #FF4B4B 0%, #FF8A8A 100%)`. Text in `#FFFFFF` with semi-bold weight. Focused states exhibit a `2px` ring in `rgba(255, 75, 75, 0.6)` with `2px` offset.
- **Secondary / Ghost Action**: `background: rgba(255, 255, 255, 0.05)`, border `1px solid rgba(255, 255, 255, 0.12)`, text `#F2F4F8`. Hover lifts background to `rgba(255, 255, 255, 0.09)`.

### Chips & Filter Tags
- Compact height (32px), `rounded-full` radius, `background: rgba(255, 255, 255, 0.04)`, `border: 1px solid rgba(255, 255, 255, 0.08)`, text `#A8B0C0`.
- **Selected State**: Tinted with `rgba(255, 75, 75, 0.15)`, text transitions to `#FF8A8A`, border sharpens to `rgba(255, 75, 75, 0.4)`.

### Restaurant & Dish Cards
- Form factor built with `rounded-lg` (16px). Image wrappers use dark gradient overlays (`linear-gradient(180deg, transparent 40%, rgba(11, 13, 18, 0.9) 100%)`) to ensure typography stays legible over food photography.
- Incorporates ambient 1px hairline top-border to mimic glass catching overhead bistro light.

### AI TasteRank Badges
- Floating rank badges (e.g., "#1 Match · 98%") feature the signature red gradient fill with white bold typography, accompanied by a subtle pulse or glow of `rgba(255, 75, 75, 0.25)`.

### Form & Search Inputs
- `border-radius: 12px` to `16px`. `background: rgba(255, 255, 255, 0.03)`, `border: 1px solid rgba(255, 255, 255, 0.08)`, text `#F2F4F8`, placeholder `#7C869A`.
- Active focus state transitions border to `#FF4B4B` accompanied by an outer halo blur of `0 0 0 3px rgba(255, 75, 75, 0.15)`.

### Selection Controls (Checkboxes & Radios)
- Custom square (`6px` radius) or circle controls. Inactive: `border: 1.5px solid #7C869A`, `background: transparent`.
- Active: `background: #FF4B4B`, border disappears, interior check/dot rendered in crisp `#FFFFFF`.