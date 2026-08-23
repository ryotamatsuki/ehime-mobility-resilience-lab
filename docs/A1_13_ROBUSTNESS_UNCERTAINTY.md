# A1.13 — Robustness / Uncertainty

## 1. Purpose

A1.13 tests whether the conclusions produced by A1.11 Time-dependent Criticality and A1.12 Vulnerable Population / Equity depend on one narrow set of modelling assumptions.

This stage is not a new risk score and does not estimate failure probability. It is a deterministic sensitivity analysis over pre-registered model assumptions.

## 2. Protected predecessor contract

A1.12 remains the protected baseline. A1.13 must not change A1.12 Golden values. The predecessor A1.12 result is generated in `outputs/a1_13/a1_12/` and is validated with the existing Golden checker before A1.13 is accepted.

## 3. What is and is not a sensitivity parameter

### Sensitivity parameters

Only assumptions that change the accessibility model are perturbed:

- walking speed
- maximum initial access walk time
- maximum stop-to-stop transfer walk time

### Evaluation dimensions, not assumptions

The following are not treated as tunable assumptions:

- departure time: all 16 A1.11 slots from 06:00 through 21:00 are evaluated
- population group: all / 65+ / 75+ / 85+ are all reported
- destination: hospital / emergency / general / welfare are all reported

This prevents demographic or destination selection from being used as a post-hoc way to obtain a preferred conclusion.

## 4. Pre-registered sensitivity cases

All seven cases are run. No case may be removed because its result is inconvenient.

| ID | Walking speed | Access walk max | Transfer walk max | Purpose |
|---|---:|---:|---:|---|
| `baseline` | 4.8 km/h | 20 min | 10 min | A1.12/A1.11 reference assumption |
| `walk_speed_3_6` | 3.6 km/h | 20 min | 10 min | 1.0 m/s walking sensitivity |
| `walk_speed_1_8` | 1.8 km/h | 20 min | 10 min | 0.5 m/s boundary sensitivity |
| `access_walk_10` | 4.8 km/h | 10 min | 10 min | tighter initial access constraint |
| `access_walk_30` | 4.8 km/h | 30 min | 10 min | wider initial access constraint |
| `transfer_walk_5` | 4.8 km/h | 20 min | 5 min | tighter transfer constraint |
| `transfer_walk_15` | 4.8 km/h | 20 min | 15 min | wider transfer constraint |

The cases use one-at-a-time perturbation. This keeps interpretation transparent. Combined worst-case assumptions are deliberately deferred unless a later evidence-based reason requires them.

## 5. Walking-time scaling

The OSM pedestrian graph uses a uniform 4.8 km/h walking speed. A1.13 therefore computes network shortest-path walk times once at the baseline speed and transforms them by the exact ratio:

`adjusted_minutes = baseline_minutes * 4.8 / sensitivity_speed_kmh`

Because all pedestrian edges use the same free walking speed, this scaling preserves the shortest-path ordering and is mathematically equivalent to recomputing the same graph with a different uniform speed. No Euclidean shortcut is introduced.

## 6. Criticality robustness

For each sensitivity case:

1. evaluate all 16 departure slots
2. compute baseline hospital accessibility
3. remove each still-boardable route independently
4. remove each still-boardable trip independently
5. calculate the existing A1.11 consequence metrics
6. aggregate each route/trip by its worst observed event across the day
7. rank candidates using the existing transparent order:
   - population with >1 minute increase, descending
   - population-weighted mean degradation, descending
   - stable ID, ascending

The baseline case defines the reference route and trip. A1.13 reports, without combining them into a score:

- reference candidate rank in every sensitivity case
- number of cases where it remains rank 1
- number of cases where it remains Top 3
- peak time and impact in every case
- cases where the rank or peak time changes

For Ozu, route Top 3 may be structurally weak evidence because only four routes are active. Therefore Top 1 stability is always shown alongside Top 3 stability.

## 7. Equity-direction robustness

At the 08:00 reference time, the existing clockwise-route D stress test is recomputed for all four destination classes under every sensitivity case.

For each destination and each of 65+ / 75+ / 85+, A1.13 evaluates two descriptive gaps versus all population:

- affected share >1 minute gap, percentage points
- mean travel-time change gap, minutes

Direction is classified as:

- `positive`: gap > 0.0005 at displayed 3-decimal precision
- `neutral`: absolute gap <= 0.0005
- `negative`: gap < -0.0005

A1.13 reports how many of the seven cases preserve the baseline direction and explicitly lists the cases that change direction. It does not call a positive gap statistically significant and does not create a vulnerability score.

## 8. Accessibility thresholds

30- and 60-minute reachability remain predecessor public indicators. A1.13 also records threshold losses directly from travel-time maps where useful, but threshold choice is treated as a reporting definition rather than a route-ranking driver. The existing A1.11 ranking rule is kept unchanged so that sensitivity analysis does not silently redefine “critical”.

## 9. Provenance and classification

- GTFS and official registries retain their existing A/B classifications.
- accessibility calculations remain C model results.
- route/trip outages remain D stress-test assumptions.
- sensitivity parameter values are D analytical assumptions.
- A1.13 records every case and its changed parameter in machine-readable output.

Sensitivity-case differences must not be described as uncertainty probabilities or confidence intervals.

## 10. Outputs

A1.13 produces:

- `summary.json` — A1.13 stage summary
- `robustness_summary.json` — concise stability findings and boundary cases
- `robustness_cases.json` — all pre-registered cases, case-level rankings, hourly top events and equity results
- `a1_12/` — full protected predecessor output used for Golden regression and site composition

## 11. UI contract

The Planning Canvas shows:

- baseline critical route/trip
- rank-by-case table
- Top 1 and Top 3 preservation counts
- equity direction preservation by destination/group
- explicit boundary conditions
- the exact seven assumptions

No single “Robustness Score” is displayed.

## 12. Release Gate

A1.13 is complete only when all of the following pass:

- all seven sensitivity cases are present and executed
- all 16 departure slots are evaluated for every case
- A1.12 predecessor Golden regression passes unchanged
- route and trip stability are persisted
- equity-direction stability is persisted for all four destinations and all three older age groups
- changed assumptions are persisted in provenance
- no composite robustness or vulnerability score is introduced
- unit tests cover scaling, aggregation and direction-stability logic
- pytest and Ruff pass
- official source probes pass
- generated A1.13 site smoke passes
- raw ZIP/XLS/XLSX are absent from the public site
