const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..", "..");
const target = process.argv[2] ? path.resolve(repoRoot, process.argv[2]) : path.join(repoRoot, "web");

for (const name of ["index.html", "app.js", "a1_10.css", "a1_10_runtime.js"]) {
  if (!fs.existsSync(path.join(target, name))) throw new Error("missing A1.10 UI artifact: " + name);
}

const html = fs.readFileSync(path.join(target, "index.html"), "utf8");
const app = fs.readFileSync(path.join(target, "app.js"), "utf8");
const css = fs.readFileSync(path.join(target, "a1_10.css"), "utf8");
const runtime = fs.readFileSync(path.join(target, "a1_10_runtime.js"), "utf8");

for (const marker of [
  "DESTINATIONS", "指定緊急避難場所", "指定一般避難所", "指定福祉避難所",
  "destination-selector", "setDestination", "renderDestinationLayer",
  "shelters.geojson", "shelter_population_access.geojson",
  "destination-synchronized"
]) {
  if (!app.includes(marker) && !runtime.includes(marker) && !css.includes(marker)) {
    throw new Error("missing A1.10 source contract marker: " + marker);
  }
}

for (const marker of [
  ".destination-grid", ".destination-choice", "min-height: 48px",
  "data-destination=\"emergency\"", "max-width: 900px", "max-width: 420px"
]) {
  if (!css.includes(marker)) throw new Error("missing A1.10 CSS contract: " + marker);
}

for (const marker of ["data-ui-stage", "dataset.destination", "MutationObserver", "aria-current"]) {
  if (!runtime.includes(marker)) throw new Error("missing A1.10 runtime accessibility contract: " + marker);
}

for (const forbidden of ["nominatim", "geocode(", "google.maps", "mapboxgl", "routeService", "fetchRoute"]) {
  if (app.toLowerCase().includes(forbidden.toLowerCase()) || runtime.toLowerCase().includes(forbidden.toLowerCase())) {
    throw new Error("A1.10 must not introduce client-side geocoding/routing: " + forbidden);
  }
}

const dataDir = path.join(target, "data");
if (fs.existsSync(path.join(dataDir, "summary.json"))) {
  const requiredData = [
    "summary.json", "manifest.json", "facilities.geojson", "population_access.geojson",
    "shelters.geojson", "shelter_accessibility.json", "shelter_population_access.geojson"
  ];
  for (const name of requiredData) {
    if (!fs.existsSync(path.join(dataDir, name))) throw new Error("missing generated A1.10 dependency: " + name);
  }
  if (!html.includes('href="a1_10.css"') || !html.includes('src="a1_10_runtime.js"')) {
    throw new Error("generated A1.10 assets are not linked from index.html");
  }
  if (!html.includes('data-ui-stage="A1.10"') || !html.includes('data-destination="hospital"')) {
    throw new Error("generated A1.10 body state contract missing");
  }

  const summary = JSON.parse(fs.readFileSync(path.join(dataDir, "summary.json"), "utf8"));
  const manifest = JSON.parse(fs.readFileSync(path.join(dataDir, "manifest.json"), "utf8"));
  const shelters = JSON.parse(fs.readFileSync(path.join(dataDir, "shelters.geojson"), "utf8"));
  const shelterAccess = JSON.parse(fs.readFileSync(path.join(dataDir, "shelter_accessibility.json"), "utf8"));
  const shelterMesh = JSON.parse(fs.readFileSync(path.join(dataDir, "shelter_population_access.geojson"), "utf8"));

  if (summary.stage !== "A1.9" || manifest.result_stage !== "A1.9") throw new Error("A1.10 must preserve A1.9 analysis result stage");
  if (manifest.ui_release_stage !== "A1.10") throw new Error("A1.10 UI release stage missing");
  for (const capability of [
    "destination-switcher", "shelter-map-layer", "destination-synchronized-metrics",
    "destination-synchronized-charts", "destination-provenance-popups"
  ]) {
    if (!manifest.ui_capabilities.includes(capability)) throw new Error("A1.10 capability missing: " + capability);
  }

  const byKind = { emergency: 0, general: 0, welfare: 0 };
  for (const feature of shelters.features || []) {
    const p = feature.properties || {};
    if (Object.prototype.hasOwnProperty.call(byKind, p.kind)) byKind[p.kind] += 1;
    if (!["exact", "name_equivalent", "parent_feature"].includes(p.location_match_quality)) {
      throw new Error("invalid shelter location quality in public layer");
    }
  }
  for (const kind of Object.keys(byKind)) {
    if (byKind[kind] !== summary.shelter_accessibility[kind].usable_destinations) {
      throw new Error("A1.10 destination layer count mismatch: " + kind);
    }
    if (!(byKind[kind] > 0)) throw new Error("A1.10 has no public destination for " + kind);
    if (!shelterAccess.by_kind || !shelterAccess.by_kind[kind]) {
      throw new Error("A1.9 shelter accessibility bundle missing " + kind);
    }
  }

  if (!Array.isArray(shelterMesh.features) || shelterMesh.features.length !== summary.population.zones_in_envelope) {
    throw new Error("A1.10 shelter population mesh mismatch");
  }
  const sample = (shelterMesh.features[0] || {}).properties || {};
  for (const kind of ["emergency", "general", "welfare"]) {
    for (const suffix of ["baseline_minutes", "disrupted_minutes", "delta_minutes"]) {
      if (!Object.prototype.hasOwnProperty.call(sample, kind + "_" + suffix)) {
        throw new Error("A1.10 synchronized mesh field missing: " + kind + "_" + suffix);
      }
    }
  }

  if (!app.includes("公式属性: 大洲市（A） / 位置: OpenStreetMap（B）")) {
    throw new Error("A1.10 shelter popup provenance missing");
  }
  if (!app.includes("親施設のOSM代表位置")) throw new Error("A1.10 parent_feature warning missing");
}

console.log("A1.10 destination-switcher smoke test passed for " + target);
