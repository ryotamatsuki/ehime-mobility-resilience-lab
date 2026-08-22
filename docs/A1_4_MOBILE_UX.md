# A1.4 Mobile UX Optimization

Status: implementation candidate

## Purpose

A1.3 introduced the desktop-oriented three-pane Planning Canvas. On an iPhone screenshot, the browser rendered the full desktop canvas at a reduced scale, making labels and controls too small for practical use. A1.4 changes presentation only; the verified A1.1 accessibility model and A1.3 scenario logic are unchanged.

## Mobile decision flow

On small/touch devices the visual order is fixed to:

1. Scenario selection
2. Verified transit disruption builder
3. Map
4. Impact summary / detail / provenance
5. Before/After, distribution and recovery analysis

The mobile view deliberately hides future/uncomputed road and rail/ferry builder sections. This is presentation-only: those functions remain visible on desktop as disabled future capabilities.

## Implemented contracts

- `viewport-fit=cover` and safe-area padding.
- Dedicated `web/mobile.css` loaded after the desktop stylesheet.
- Breakpoint fallback uses both viewport/device width and coarse-pointer detection so iPhone Safari cannot fall back to the shrunken desktop canvas when width reporting is unusual.
- Scenario ribbon becomes horizontal, touch-scrollable and shows only Baseline / Scenario A / Recovery.
- Main Planning Canvas becomes one column.
- Builder controls use >=48 px primary actions and larger checkbox/tap targets.
- Future/uncomputed builder sections are hidden on mobile.
- Map receives its own 52-58vh block and larger Leaflet zoom controls.
- Impact tabs become sticky below the scenario ribbon.
- KPI text, ranking controls and selected-mesh content are enlarged.
- Before/After mini maps, distribution and recovery cards stack vertically.
- Footer remains horizontally scrollable rather than forcing page-wide shrink.

## Truthfulness

A1.4 does not add new analytical capability. Road closures, capacity reduction, railway/ferry disruption, Synthetic OD, Traffic Assignment, freight and relief remain uncomputed. The only interactive disruption remains the verified Gururin Ozu clockwise-route outage.

## Acceptance criteria

- Desktop three-pane layout remains defined in `styles.css`.
- Mobile stylesheet is loaded after desktop stylesheet.
- Mobile breakpoint forces `.planning-canvas` to `flex-direction: column`.
- Order is builder -> map -> impact -> analytics.
- Mobile future sections are hidden.
- Primary/secondary action touch target height is at least 48 px.
- Generated `_site` includes `mobile.css`.
- Existing A1.1 real-data rebuild and A1.3 generated-site contract continue to pass.
