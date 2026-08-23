# AGENTS.md

## Repository-level development rules

Before proposing or implementing a new feature, read:

- `docs/COMPETITION_JUDGING_STRATEGY.md`
- `ROADMAP.md`
- `docs/SPECIFICATION.md`

## Competition development rules

1. Do not change the core theme without explicit review.
2. Do not optimize technical sophistication for its own sake.
3. The main remaining competition gaps are:
   - real-world problem anchoring,
   - robustness / uncertainty,
   - recovery / intervention comparison,
   - representative findings,
   - competition-mode UX.
4. Complete the Ozu evidence chain before broad Ehime-wide expansion unless the roadmap explicitly changes this priority.
5. CI, provenance and Golden regression are release-quality requirements, not the product's main competition story.
6. Do not hide uncertainty or convert unobserved/modelled values into apparent facts.
7. Before adding scope, state which P0 / P1 / P2 competition blocker the work resolves.
8. Preserve A / B / C / D provenance and the distinction between observed evidence, processed official data, modelled results and scenario assumptions.
9. Do not treat 65+ / 75+ / 85+ as equivalent to all vulnerable populations.
10. Do not update Golden values merely to make a refactor or new feature pass.

## Current competition-first sequence

Use `ROADMAP.md` as the formal stage authority. The current intended flow is:

Criticality → Robustness / Uncertainty → Real-world Evidence Anchor → Recovery / Intervention → Competition Mode → Generalization / Release.

If a proposed task does not improve a documented competition blocker, existing analytical truthfulness, or release quality, lower its priority until after Competition Release.
