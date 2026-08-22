# Ehime Mobility Resilience Lab

## A0 Architecture Decision

Status: A0 foundation design

This document defines the technical boundary for the foundation stage. It does not implement road analysis, GTFS routing, Synthetic OD, traffic assignment, freight analysis, relief logistics, or the Phase B hazard adapter.

The formal product specification remains the authority for product scope and Decision Lock items:

- [SPECIFICATION.md](SPECIFICATION.md)

## 1. Architectural goals

The architecture shall:

1. Keep public web delivery independent from heavy analysis execution.
2. Make every public result traceable to data versions, model versions, parameters, and a Git commit.
3. Keep official observations, official-statistics transformations, model estimates, and user assumptions visibly distinct.
4. Allow a non-engineer operator to update approved datasets without replacing files in place.
5. Work without a paid map API, LLM API, or proprietary cloud service.
6. Keep Phase A fully usable without the Ehime earthquake damage-assumption GIS.
7. Make the first implementation reproducible in a clean checkout and in GitHub Actions.

## 2. Runtime layers

The system is divided into three layers. They share versioned contracts, but they do not share runtime responsibilities.

| Layer | Location | Responsibilities | Prohibited responsibilities |
| --- | --- | --- | --- |
| Public Layer | web/ and GitHub Pages | Map display, mode selection, preset scenario selection, precomputed result display, before/after comparison, provenance display, accessibility-friendly interaction | Heavy routing, traffic assignment, raw-data ingestion, credentials, administrative approval |
| Analysis Layer | src/ and scripts/ | Ingestion, validation, GTFS interpretation, network construction, Synthetic OD, assignment, freight and relief calculations, export of static artifacts | Serving credentials or an always-on API requirement for the public demo |
| Administration Layer | admin/ | Upload staging, validation reports, diff, preview, approval, active-version switch, archive, rollback | Direct overwrite of active data, exposure through the public Pages site |

The public site is intentionally static-first. A scenario that has not been computed by the analysis layer shall be shown as not computed; the browser shall not silently substitute a visually plausible estimate.

## 3. Data flow

The canonical flow is:

1. A source registry records publisher, dataset title, URL, reference date, download date, licence, checksum, and known limitations.
2. A dataset is received into a local or controlled staging area.
3. Format, schema, identifiers, geometry, CRS, and licence gates are validated.
4. A validated dataset receives an immutable dataset version.
5. The analysis layer produces versioned network, demand, accessibility, assignment, freight, relief, or scenario artifacts.
6. Each artifact receives a provenance manifest.
7. Only approved public-safe artifacts are exported to web/data.
8. GitHub Actions validates the repository and publishes web/ to GitHub Pages from the default branch.

Raw or restricted inputs are not copied to web/. Public artifacts must be sufficient for the public view but must not make a restricted source recoverable when redistribution is not allowed.

## 4. Repository boundaries

The target structure is:

| Path | Boundary |
| --- | --- |
| docs/ | Specification, evidence, design decisions, operational procedures, validation, and competition documentation |
| data/raw/ | Local acquisition area; ignored by default and never a place for unreviewed uploads |
| data/staging/ | Candidate versions before approval; ignored by default |
| data/processed/ | Analysis intermediates; ignored or release-specific |
| data/public/ | Public-safe release artifacts and metadata only |
| data/metadata/ | Dataset registry, schema versions, provenance contracts, and licence evidence |
| src/ | Reusable Python analysis packages; no web UI code |
| scripts/ | Explicit ingestion, validation, build, and export entry points |
| admin/ | Operator-facing update and approval tooling; not bundled into Pages |
| web/ | Static public application and small public assets |
| tests/ | Unit, integration, model, regression, and browser-test contracts |
| outputs/ | Reproducible local outputs; not an uncontrolled source-data store |

The A0 skeleton creates only foundation checks and a static Pages placeholder. A1 owns the first real network and transit implementation.

## 5. Technology selection

### 5.1 Selected direction

| Concern | A0 decision | Reason |
| --- | --- | --- |
| Analysis language | Python 3.12 or newer supported release | Strong geospatial, tabular, scientific, and public-sector automation ecosystem; easy local and CI reproduction |
| Tabular processing | Pandas for compatibility, with Polars or DuckDB evaluated for large extracts | Preserve inspectability first; benchmark before introducing a second mandatory engine |
| Vector geospatial processing | GeoPandas, Shapely, and Pyogrio | Clear geometry semantics and common formats; Pyogrio is a suitable I/O path for larger vector files |
| Spatial SQL and profiling | DuckDB with Spatial extension as an optional analysis accelerator | Useful for reproducible SQL checks and columnar data; not required by the static web runtime |
| Road graph baseline | A transparent Python graph abstraction with NetworkX-compatible tests | Keeps shortest-path and disruption semantics inspectable; performance is measured before changing the abstraction |
| Transit accessibility | GTFS-JP parser plus a schedule-aware routing adapter; OpenTripPlanner is the primary integration candidate | GTFS supply and schedule semantics belong in the analysis layer, not in a browser mock |
| Traffic assignment | AequilibraE evaluation gate, with a validated transparent baseline available if integration is not suitable | Avoid committing to a solver before network, OD, licence, and calibration data are verified |
| Web language | TypeScript | Makes scenario, provenance, and result contracts explicit at the browser boundary |
| Web build | Vite or an equivalent static bundler selected at A1 lock | GitHub Pages needs static files; bundling keeps dependency versions and asset paths deterministic |
| Web map | MapLibre GL JS | Open-source WebGL rendering and vector-tile support are appropriate for growing public layers without a paid Mapbox runtime |
| Small A0 placeholder | Plain HTML and CSS with no runtime map dependency | Keeps this stage fast, offline-testable, and free of an accidental A1 implementation |
| Large static geodata | PMTiles or FlatGeobuf after benchmark; GeoJSON only for small previews and fixtures | Avoid shipping a large, monolithic GeoJSON file to every browser |
| Contracts | JSON Schema plus machine-readable provenance manifests | Enables CI checks, explainability, and stable handoff between Python and TypeScript |
| CI and deployment | GitHub Actions and GitHub Pages custom workflow | The repository is public and the public layer is static; deployment is auditable from commits |

### 5.2 Candidate technologies not selected as the default

| Candidate | A0 position |
| --- | --- |
| Leaflet | Good for a small map and a valid fallback, but MapLibre is preferred for the planned vector-tile and data-driven styling workload |
| deck.gl | Useful for high-volume visual layers, but it is an optional layer on top of MapLibre rather than the base map contract |
| r5py | Valuable for R5-based regional accessibility, but it adds a Java dependency and does not replace GTFS feed validation or the public artifact contract |
| A fully client-side routing engine | Rejected as the default because it would move reproducibility, compute cost, and data governance into an uncontrolled browser |
| A proprietary map SDK | Rejected by Decision Lock because the core product must work without a paid API |

These are architecture choices, not claims that every package has already been installed or validated against the final data. A1 must run a small feasibility spike before locking production dependencies.

## 6. Public Layer contract

The Pages application consumes only release artifacts with:

- an explicit schema version;
- a dataset classification of A, B, C, or D;
- source and attribution metadata;
- data and model version identifiers;
- generated-at timestamp;
- Git commit SHA;
- scenario definition and calculation status;
- confidence category with an explanation, not an unexplained numeric score.

The browser shall distinguish at least:

- computed result;
- not computed because required data is unavailable;
- not publishable because licence permission is unresolved;
- user assumption;
- model estimate;
- official observation or official statistic.

The public UI shall never label a stress-test result as predicted damage, actual isolation, actual traffic demand, or a real-time emergency instruction.

## 7. Analysis and artifact contracts

The analysis layer shall produce immutable, content-addressed or checksum-identified artifacts. Each result must be accompanied by:

| Field | Purpose |
| --- | --- |
| input_data_versions | Exact dataset versions used |
| model_version | Code and model contract version |
| scenario_id | Reproducible disruption definition |
| parameters | Capacity, speed, mode, time, and other assumptions |
| generated_at | Execution timestamp |
| git_sha | Source revision |
| data_classification | A, B, C, or D |
| coverage | Area, mode, and omitted-data statement |
| validation_status | Validation result and warnings |

Scenario calculations are batch outputs for the public site. Latest-data recalculation belongs to the Analysis and Administration Layers and must preserve the previous result version.

## 8. Phase B isolation

The Phase B hazard adapter is a separate future package and data boundary. Before an explicit licence gate passes:

- no Phase B source file is downloaded into the repository;
- no Phase B-derived geometry or raster is generated;
- no hazard attribute is joined to a road or transit link;
- no Phase B layer is displayed on Pages;
- no Phase B screenshot or derived GeoJSON is published.

The Phase A scenario interface accepts user-defined network conditions without knowing the source of a future hazard scenario. This keeps Phase A complete and makes a later adapter replaceable.

## 9. Security and data governance

1. No credential, API key, private upload, or admin secret may be bundled into web/.
2. Raw, candidate, and restricted datasets are ignored by default.
3. A file becomes public only after the data inventory and licence audit allow redistribution.
4. Upload validation must reject path traversal, symlink extraction, oversized archives, and unsupported formats before parsing.
5. Public critical-link results must state that they are scenario impacts under specified assumptions, not operational instructions.
6. External GTFS feeds requiring registration or additional terms are external inputs until their redistribution conditions are confirmed.
7. OSM-derived public data must include attribution and comply with the applicable ODbL obligations.

## 10. Performance budgets

The public layer is designed around the specification targets:

| Operation | Target | Architectural response |
| --- | --- | --- |
| Initial public load | Approximately 3 seconds on a normal connection | Small HTML shell, compressed static assets, no raw data fetch, lazy layer loading |
| Mode switch | Approximately 1 second for precomputed layers | Pre-indexed artifacts, stable layer identifiers, no recomputation in the browser |
| Preset scenario display | Approximately 2 seconds | Precomputed result manifests and compact summaries |
| Heavy analysis | Offline or controlled analysis runtime | Python batch jobs, explicit resource budget, provenance manifest |

Budgets are release criteria to measure, not guarantees to claim before browser tests exist.

## 11. CI and GitHub Pages design

The foundation workflow is defined in .github/workflows/ci.yml.

The workflow has two logical jobs:

1. build-and-check: checkout, Python setup, documentation/foundation checks, static-site assembly, and Pages artifact upload;
2. deploy: dependent on build-and-check, restricted to pushes to main, and deployed to the github-pages environment.

The deployment job requires the minimum Pages permissions documented by GitHub:

- contents: read;
- pages: write;
- id-token: write.

Pull requests run all checks and build the artifact but do not deploy. A push to main deploys the same artifact path after checks pass. A manual workflow dispatch is retained for operational recovery.

GitHub repository settings must select GitHub Actions as the Pages publishing source and protect the github-pages environment so only the default branch can deploy.

## 12. Testing strategy

A0 tests only foundations:

- required documents and links exist;
- prohibited Phase B paths are absent;
- the static site has an index document and no credentials;
- Python foundation scripts compile;
- the Pages build copies only the intended web directory;
- the workflow file is syntactically inspectable.

A1 adds real GTFS and road fixtures. A2 adds OD constraints. A3 adds assignment and holdout validation. A4 adds freight and relief. A5 adds upload/version/rollback tests. A6 adds browser, regression, performance, and release tests.

The first public release gate must not be inferred from a green A0 workflow. A green A0 workflow only proves that the foundation is structurally consistent.

## 13. A1 entry criteria

A1 may begin only after:

1. Data Inventory and Data License Inventory identify confirmed, conditional, unavailable, and blocked inputs.
2. GTFS coverage and redistribution conditions are recorded per feed, without assuming full Ehime coverage.
3. The road data public-release boundary is documented.
4. Population and facility source/version strategy is fixed.
5. The transit accessibility calculation contract is written and includes missing-shapes behavior.
6. Public result and provenance schemas are reviewed.
7. A0 QA has no unresolved blocker.
8. A1 work is started on a separate feature branch and does not modify the Phase B gate.

## 14. Open decisions for A1 review

The following are deliberately not hidden inside the A0 skeleton:

- final GTFS feed set and each feed's redistribution permission;
- whether OpenTripPlanner can ingest all selected GTFS-JP and ferry inputs;
- OSM extraction date, geographic clipping, and public derivative policy;
- PMTiles versus FlatGeobuf threshold after measuring the actual layer sizes;
- AequilibraE integration versus a transparent baseline for traffic assignment;
- final Python and Node dependency lock files;
- current facility datasets and their update ownership.

No unresolved item may be converted into a fabricated data source or an unstated assumption.

## 15. Evidence used for the A0 choices

The following primary sources were checked when selecting the foundation direction:

- [GitHub: Using custom workflows with GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [GitHub Actions checkout](https://github.com/actions/checkout)
- [GitHub Actions setup-python](https://github.com/actions/setup-python)
- [MapLibre GL JS documentation](https://maplibre.org/maplibre-gl-js/docs/)
- [OpenTripPlanner](https://www.opentripplanner.org/)
- [GeoPandas documentation](https://geopandas.org/en/stable/docs.html)
- [AequilibraE traffic assignment documentation](https://www.aequilibrae.com/docs/python/v1.4.2/traffic_assignment/assignment_procedures.html)
- [PMTiles browser documentation](https://pmtiles.io/typedoc/index.html)

These sources establish capability and integration direction. They do not replace the A1 feasibility tests against the actual Ehime datasets, licence conditions, and measured artifact sizes.
