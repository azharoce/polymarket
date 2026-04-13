# Design System Strategy: The High-Fidelity Analyst

## 1. Overview & Creative North Star
**Creative North Star: "The Kinetic Ledger"**
Traditional financial dashboards often feel like static spreadsheets. To elevate this platform, we move toward "The Kinetic Ledger"—a design philosophy that treats data as a living, breathing entity. Instead of a rigid grid of boxes, we use **intentional asymmetry** and **tonal depth** to guide the eye. By breaking the "template" look with oversized display type for key metrics and overlapping surface layers, we create an editorial experience that feels like a premium Bloomberg terminal reimagined for the decentralized era. This system prioritizes information density without sacrificing the "breathing room" required for high-stakes decision-making.

---

## 2. Colors: Tonal Architecture
We utilize a sophisticated palette of deep navy and electric violets. The goal is to move away from flat UI by using "visual soul" found in gradients and glassmorphism.

*   **Core Tones:**
    *   **Background (`#0b1326`):** The foundation. Never pure black; a deep, ink-like navy that provides better contrast for neon accents.
    *   **Primary (`#adc6ff`) & Secondary (`#d0bcff`):** These are our "Action" and "Insight" colors. Use them sparingly to highlight interactive paths.
    *   **Tertiary (`#4edea3`):** Reserved exclusively for "Success" and positive PnL.
    *   **Error (`#ffb4ab`):** Reserved for "Danger," liquidations, or negative PnL.

*   **The "No-Line" Rule:** 
    **Prohibit 1px solid borders for sectioning.** Boundaries must be defined solely through background color shifts. A `surface-container-high` card should sit on a `surface` background without a stroke.
*   **Surface Hierarchy & Nesting:** 
    Use the tier system to create depth. For example, a trading module should use `surface-container-lowest` for the main area, with the order-entry form nested inside using `surface-container-highest` to "lift" it toward the user.
*   **The "Glass & Gradient" Rule:** 
    For floating modals or dropdowns, use `surface-container-highest` with a 60% opacity and a `20px` backdrop-blur. Apply a subtle linear gradient from `primary` to `primary_container` (at 15% opacity) as a top-down overlay to give components a "frosted glass" premium finish.

---

## 3. Typography: Editorial Authority
We use a high-contrast pairing: **Space Grotesk** for data/headlines and **Inter** for utility/reading.

*   **Display & Headline (Space Grotesk):** This is our "Analytical" font. Its technical, slightly geometric curves suggest precision. Use `display-lg` for total portfolio value and `headline-sm` for market titles.
*   **Body & Label (Inter):** This is our "Utility" font. Optimized for readability at small scales.
*   **Numerical Data:** All PnL and price data must use `inter` with `font-variant-numeric: tabular-nums` to ensure columns of numbers align perfectly for easy scanning.
*   **Hierarchy Tip:** Use `label-sm` in `on-surface-variant` for "Secondary Data" (like 24h volume) to keep the UI from feeling cluttered despite the high density.

---

## 4. Elevation & Depth: Tonal Layering
We do not use shadows to indicate "material." We use light.

*   **The Layering Principle:** Depth is achieved by stacking. 
    *   `surface` (Base) → `surface-container-low` (Section) → `surface-container-high` (Interactive Card).
*   **Ambient Shadows:** If a "floating" element (like a context menu) is required, use an extra-diffused shadow: `box-shadow: 0 24px 48px -12px rgba(0, 0, 0, 0.5)`. The shadow color should be a darker version of the surface, never neutral grey.
*   **The "Ghost Border" Fallback:** If a separation is visually required for accessibility, use the `outline_variant` at **15% opacity**. This creates a "suggestion" of a border rather than a hard structural line.
*   **Glassmorphism:** Use `surface-tint` at 5% opacity on top of containers to simulate light hitting the top of a glass pane.

---

## 5. Components: Precision Primitives

*   **Action Buttons:**
    *   **Primary:** Linear gradient (`primary` to `primary_container`). `0.25rem` (sm) roundedness. No border.
    *   **Secondary:** `surface-container-highest` background with `on-surface` text.
*   **The "Value Chip":** 
    For PnL indicators. Use `tertiary_container` for positive and `error_container` for negative. Use `label-md` for the text. No borders; use a soft `0.25rem` corner.
*   **Financial Inputs:**
    Input fields should use `surface-container-lowest` with a "Ghost Border" that illuminates to `primary` only when focused. Helper text should always use `label-sm`.
*   **Cards & Lists (The Forbid Rule):** 
    **Never use horizontal dividers.** To separate list items (like open bets), use a `4px` vertical gap and alternate the background slightly using `surface-container-low` and `surface-container-lowest`. This "Zebra-Striping" must be so subtle it is felt, not seen.
*   **Trading Charts:** 
    The chart area should be the only place where `surface-bright` is used for grid lines (at 5% opacity) to ensure the candlestick data remains the focal point.

---

## 6. Do’s and Don’ts

### Do:
*   **Do** use `spaceGrotesk` for all "Money" values to give them a distinct, premium character.
*   **Do** rely on `surface-container` shifts for hierarchy. If a screen feels flat, lighten the inner containers; don't add borders.
*   **Do** use `tertiary` (green) and `error` (red) only for data. Never use these colors for UI decorations or buttons.

### Don’t:
*   **Don’t** use 100% white (`#FFFFFF`) for text. Use `on-surface` (`#dae2fd`) to reduce eye strain during long trading sessions.
*   **Don’t** use the `full` roundedness scale for anything other than status indicators (pills). Financial dashboards require the "stability" of the `0.25rem` (sm) and `0.375rem` (md) radius.
*   **Don’t** use standard "Drop Shadows." If an element isn't lifting via color, it shouldn't be lifting at all.