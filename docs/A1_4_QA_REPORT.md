# A1.4 Mobile UX QA Report

Status: PASS WITH WARNINGS / merge approved

## Scope reviewed

- iPhone/small touch presentation of the A1.3 Planning Canvas.
- No analytical/model changes.
- Existing A1.1 real-data accessibility result remains the only interactive stress-test input.

## Automated QA

Pull request CI run 32560675955:

- Python unit/model checks: PASS
- A0 foundation checks: PASS
- Public data contract: PASS
- Source probe for selected real inputs: PASS
- A1.1 real-data accessibility rebuild: PASS
- A1.1 result contract: PASS
- A1.3/A1.4 generated static site build: PASS
- Generated-site smoke test: PASS
- Artifact upload: PASS

The generated artifact contains `index.html`, `styles.css`, `mobile.css`, `app.js`, and the verified derived data outputs.

## Mobile contract review

PASS:

- dedicated mobile stylesheet loads after desktop stylesheet;
- `viewport-fit=cover` is present;
- mobile/touch query forces a one-column Planning Canvas;
- order is Builder -> Map -> Impact -> Analytics;
- future/uncomputed road and rail/ferry sections are hidden on mobile;
- Baseline / Scenario A / Recovery remain available in a horizontally scrollable scenario ribbon;
- primary builder actions are at least 48 px high;
- map block is given a phone-appropriate viewport height;
- Leaflet zoom controls and impact tabs are enlarged;
- KPI text and ranking controls are enlarged;
- analytics cards stack vertically;
- horizontal page shrink is explicitly prevented.

## Truthfulness review

PASS. Mobile simplification does not imply additional analytical capability. Road closure, capacity reduction, rail/ferry, Synthetic OD, Traffic Assignment, freight, relief and multi-recovery ranking remain uncomputed.

## Warnings

1. Device/browser rendering should still be visually verified on the deployed iPhone Safari page because GitHub CI currently validates the responsive contract statically rather than using a full browser screenshot regression suite.
2. Hiding future sections on mobile is intentional progressive disclosure; desktop continues to show them as disabled roadmap items.
3. External Leaflet/OSM availability remains a runtime dependency of map rendering, unchanged from A1.3.

## Decision

A1.4 is safe to merge. After Pages deployment, verify on the same iPhone used for the A1.3 screenshot. If any residual zoomed-desktop rendering remains, capture the deployed screenshot and treat it as an A1.4.1 CSS regression rather than changing the analytical model.
