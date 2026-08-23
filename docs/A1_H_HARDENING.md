# A1.H — Architecture / Technical-Debt Hardening

## Purpose

A1.H is a **no-feature, no-model-change** maintenance stage inserted after A1.12.
Its purpose is to reduce regression risk before additional accessibility and
resilience analyses are added.

Reference production baseline:

- main SHA: `3077d922ed225356fb654c78414fd14bda05d236`
- released result stage: A1.12
- verified analysis zones: 1,840
- public result contract: all / 65+ / 75+ / 85+ × hospital / emergency / general / welfare

A1.H must not change the verified A1.12 accessibility/equity results. A data or
model-method change must be reviewed as a separate analytical stage rather than
being hidden inside a refactor.

## Hardening changes

### 1. Golden result contract

`tests/fixtures/a1_12_golden.json` freezes the pre-hardening A1.12 observable
contract for all four destination classes and all four population groups,
including:

- analysis-zone count and population totals
- current official citywide age-population context
- baseline 30/60-minute reachability
- >1 / >5 / >10 minute affected population and shares
- population-weighted baseline/disrupted mean travel time and change

`scripts/validate/check_a1_12_golden.py` compares a freshly generated A1.12 run
against that snapshot. The CI release gate fails on unexplained drift.

### 2. Result stage and UI capability are separate contracts

Earlier generated-site code temporarily rewrote `summary.stage` so an A1.12
result could impersonate A1.11, and A1.11 could impersonate A1.9. That pattern
was removed.

The generated site now preserves the real `manifest.result_stage` and composes
UI capabilities independently:

- A1.10 destination switcher
- A1.11 time-dependent criticality
- A1.12 vulnerable-population/equity UI

`web/app.js` validates `summary.stage === manifest.result_stage` instead of a
hard-coded list of known result stages.

### 3. Shared generated-site composition contract

`scripts/export_web/site_contract.py` centralizes repetitive mechanics:

- required-file validation
- CSS/JS asset injection
- `data-ui-stage` / destination metadata updates
- idempotent analytics-card insertion
- capability/artifact merging without result-stage mutation
- documentation copying

Unit tests cover stage replacement, idempotent insertion, capability/artifact
deduplication, and rejection of result-stage drift.

### 4. Static defect detection

CI now executes high-signal Ruff checks (`F` and Bugbear `B`) in addition to
pytest and compileall.

The initial audit found unused code and multiple implicit `zip()` truncation
sites. The contract is now explicit:

- OD target pairs and validation metric series use `strict=True`; a length
  mismatch is an error instead of silent truncation.
- adjacent geometry/sequence pairs intentionally use `strict=False`.
- unit tests verify OD and validation-series mismatch rejection.

### 5. A1.11 repeated-scan cleanup

A1.11 previously found each trip's first departure by rescanning the complete
connection list once per trip. Because connections are already departure-time
sorted, first departures are now captured in one pass with `setdefault`.
This changes complexity from repeated full scans to O(connections) and does not
change ranking or accessibility semantics.

### 6. One-build source snapshot

A1 stage entrypoints deliberately regenerate predecessor products as an
independent reproducibility/regression check. That design is retained rather
than replaced by a risky cross-stage mutable analysis context.

However, repeated identical public-data requests inside one Python process now
reuse the exact response bytes through a bounded process-local cache. Cache
identity includes URL, request body and timeout. It is never persisted between
runs. This provides two benefits:

- a single build cannot accidentally mix two versions of the same upstream
  resource if it changes during execution;
- repeated GTFS/population/registry/identical Overpass downloads are avoided.

A unit test verifies that only exact requests are reused.

### 7. CI / Pages separation

Pull requests run validation and generate/smoke-test the public site, but Pages
configuration/upload/deployment remains conditional on `refs/heads/main`.
The obsolete A1.12 feature-branch-specific push trigger was removed.

## Deliberately retained architecture

Historical `build_a1_*` entrypoints remain separate. They are executable stage
records and predecessor regression gates, not duplicate public APIs. A1.H does
not collapse them into one mutable mega-pipeline because that would increase
the blast radius of future model changes and make stage-level reproduction
harder.

Their network cost is bounded by the process-local exact-request cache. A future
architecture change may introduce immutable analysis contexts only if profiling
shows material compute cost and a dedicated equivalence test suite is added.

## Release gate

A1.H is mergeable only when all of the following pass on the final PR head:

1. pytest
2. Ruff `F,B`
3. A0 foundation / public-data contract / deterministic fixture
4. official source probes
5. fresh A1.12 real-data build
6. A1.12 analytical contract validation
7. full four-destination Golden regression
8. A1.11 capability regression with `summary.stage` remaining A1.12
9. generated A1.12 site smoke tests
10. raw ZIP/XLS/XLSX publication exclusion

No Golden value may be updated merely to make a refactor pass. A changed value
requires separate investigation and an explicit data/model-change review.
