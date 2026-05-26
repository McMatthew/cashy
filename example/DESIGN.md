---
name: Pro-Efficiency POS
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#bbcabf'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#86948a'
  outline-variant: '#3c4a42'
  surface-tint: '#4edea3'
  primary: '#4edea3'
  on-primary: '#003824'
  primary-container: '#10b981'
  on-primary-container: '#00422b'
  inverse-primary: '#006c49'
  secondary: '#ffb95f'
  on-secondary: '#472a00'
  secondary-container: '#ee9800'
  on-secondary-container: '#5b3800'
  tertiary: '#b9c7e0'
  on-tertiary: '#233144'
  tertiary-container: '#95a4bb'
  on-tertiary-container: '#2c3a4e'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#6ffbbe'
  primary-fixed-dim: '#4edea3'
  on-primary-fixed: '#002113'
  on-primary-fixed-variant: '#005236'
  secondary-fixed: '#ffddb8'
  secondary-fixed-dim: '#ffb95f'
  on-secondary-fixed: '#2a1700'
  on-secondary-fixed-variant: '#653e00'
  tertiary-fixed: '#d5e3fd'
  tertiary-fixed-dim: '#b9c7e0'
  on-tertiary-fixed: '#0d1c2f'
  on-tertiary-fixed-variant: '#3a485c'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
typography:
  display-price:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 26px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-bold:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  touch-target-min: 48px
  gutter: 1rem
  margin-edge: 1.5rem
  stack-sm: 0.5rem
  stack-md: 1rem
  stack-lg: 2rem
---

## Brand & Style
The design system is engineered for high-velocity retail and hospitality environments. The brand personality is authoritative, reliable, and invisible—prioritizing task completion over visual flair. It employs a **Corporate / Modern** style with a "rugged" functionalist edge, ensuring that the interface remains legible under harsh overhead lighting and during rapid multi-touch interactions. The aesthetic avoids unnecessary ornamentation, focusing on "hit-ready" zones and clear visual hierarchies that reduce cognitive load for operators during peak hours.

## Colors
The palette utilizes a "Low-Strain Dark Mode" to prevent eye fatigue during long shifts. 
- **Primary (Emerald Green):** Reserved exclusively for positive progression and primary transaction actions like "Checkout" or "Add Item."
- **Secondary (Warning Amber):** Used for alerts, stock warnings, and destructive actions that require a second thought.
- **Surface Tones (Slate & Charcoal):** The interface uses `#0F172A` (Deep Slate) for the base background and `#1E293B` or `#334155` for cards and interactive containers to create a clear structural hierarchy.
- **Text:** High-contrast off-white (`#F8FAFC`) for primary information and muted grey-blue (`#94A3B8`) for secondary metadata.

## Typography
This design system utilizes **Inter** for its neutral, systematic qualities and exceptional legibility at small sizes. 
- **Pricing:** Uses the `display-price` token with a bold weight and tight letter spacing to ensure the total amount is the most prominent element on the screen.
- **Product Names:** Set in `headline-md` or `body-lg` with semi-bold weights to distinguish them from quantities and descriptions.
- **Data Density:** Label styles use uppercase tracking for secondary data (SKUs, tax categories) to differentiate "fixed" data from "variable" user input.

## Layout & Spacing
The layout follows a **Fluid Grid** model optimized for landscape tablets and industrial touchscreens.
- **Touch-First:** A minimum touch target of 48px is strictly enforced for all interactive elements.
- **The "Three-Pane" Logic:** On desktop/tablet, the layout is split into a 25% Sidebar (Categories), 50% Center (Product Grid), and 25% Right (Current Order/Cart).
- **Mobile Reflow:** On handheld devices, the Cart becomes a persistent bottom drawer, and the Categories become a horizontal scrolling tab bar.
- **Rhythm:** An 8px linear scale (0.5rem) governs all padding and margins to maintain a tight, professional density.

## Elevation & Depth
Depth is conveyed through **Tonal Layering** supplemented by subtle, functional shadows. 
- **Level 0 (Base):** The darkest slate (`#0F172A`), representing the app "floor."
- **Level 1 (Cards/Buttons):** Elevated using a slightly lighter slate (`#1E293B`) with a 1px border (`#334155`) to define edges.
- **Level 2 (Active/Modals):** Uses a subtle ambient shadow (0px 4px 12px rgba(0,0,0,0.4)) to lift focused elements above the grid. 
The system avoids heavy blurs or decorative gradients, keeping the focus on the physical boundary of the touchable area.

## Shapes
A consistent **8px (0.5rem)** corner radius is applied across all primary components, including product tiles, buttons, and input fields. This "Medium Rounded" approach balances a modern friendly feel with the structural rigidity required for a professional tool. Smaller utility components (chips, quantity steppers) may use a 4px radius to maintain visual proportion.

## Components
- **Action Buttons:** Primary buttons (Add to Order) use a solid Emerald Green background with dark slate text. Secondary buttons use an outlined style. All buttons have a defined "Pressed" state that shifts the background color 10% darker for tactile feedback.
- **Product Tiles:** Large, hit-friendly cards containing the product name (top-left) and price (bottom-right). Tiles for out-of-stock items are desaturated to 40% opacity.
- **The Cart List:** High-density rows with a minimum height of 64px. Each row includes a "Swipe to Remove" gesture or a clear "X" icon for quick editing.
- **Input Fields:** Stepped quantity selectors use large "+" and "-" icons rather than standard text input to facilitate rapid adjustments without a keyboard.
- **Status Badges:** Small, high-contrast pills used for "Dining In," "Takeaway," or "Paid" status, using the semantic color palette.
- **Numpad:** A custom, oversized numeric grid for manual price entry or PIN codes, featuring high-contrast borders and large typography.