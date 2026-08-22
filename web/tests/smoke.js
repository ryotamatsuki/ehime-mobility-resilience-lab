const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..", "..");
const target = process.argv[2] ? path.resolve(repoRoot, process.argv[2]) : path.join(repoRoot, "web");

for (const name of ["index.html", "app.js", "styles.css", "mobile.css"]) {
  if (!fs.existsSync(path.join(target, name))) throw new Error("missing frontend artifact: " + path.join(target, name));
}

const html = fs.readFileSync(path.join(target, "index.html"), "utf8");
const app = fs.readFileSync(path.join(target, "app.js"), "utf8");
const mobile = fs.readFileSync(path.join(target, "mobile.css"), "utf8");

const requiredMarkers = [
  "交通レジリエンス・プランニングキャンバス",
  "SCENARIO BUILDER",
  "Scenario A",
  "影響サマリー",
  "BEFORE / AFTER",
  "DISTRIBUTION",
  "RECOVERY",
  "distribution-chart",
  "population_access.geojson",
  "weightedCdf"
];
for (const marker of requiredMarkers) {
  if (!html.includes(marker) && !app.includes(marker)) throw new Error("missing planning-canvas marker: " + marker);
}

for (const stale of ["road56-stress-test", "国道56号区間停止チェック", "GTFS入力待ち"]) {
  if (html.includes(stale) || app.includes(stale)) throw new Error("stale A0 UI remains: " + stale);
}

for (const truthfulMarker of ["未計算", "disabled", "実被害予測", "D 停止仮定"]) {
  if (!html.includes(truthfulMarker) && !app.includes(truthfulMarker)) throw new Error("missing truthful-scope marker: " + truthfulMarker);
}

const mobileContracts = [
  'href="mobile.css"',
  "max-device-width: 900px",
  "flex-direction: column",
  ".builder-pane .future-section { display: none; }",
  "min-height: 48px",
  "order: 2",
  "order: 3"
];
for (const marker of mobileContracts) {
  if (!html.includes(marker) && !mobile.includes(marker)) throw new Error("missing A1.4 mobile contract: " + marker);
}
if (!html.includes("viewport-fit=cover")) throw new Error("mobile viewport safe-area contract missing");

const dataDir = path.join(target, "data");
const generatedSummary = path.join(dataDir, "summary.json");
if (fs.existsSync(generatedSummary)) {
  const required = ["summary.json", "manifest.json", "routes.geojson", "stops.geojson", "facilities.geojson", "population_access.geojson"];
  for (const name of required) {
    if (!fs.existsSync(path.join(dataDir, name))) throw new Error("missing generated A1 data: " + name);
  }
  const summary = JSON.parse(fs.readFileSync(generatedSummary, "utf8"));
  const manifest = JSON.parse(fs.readFileSync(path.join(dataDir, "manifest.json"), "utf8"));
  const population = JSON.parse(fs.readFileSync(path.join(dataDir, "population_access.geojson"), "utf8"));
  const stops = JSON.parse(fs.readFileSync(path.join(dataDir, "stops.geojson"), "utf8"));
  const facilities = JSON.parse(fs.readFileSync(path.join(dataDir, "facilities.geojson"), "utf8"));
  if (!["A1.1", "A1.5"].includes(summary.stage) || summary.status !== "computed" || summary.classification !== "C") throw new Error("invalid A1 summary contract");
  if (manifest.stage !== "A1.3" || manifest.status !== "computed") throw new Error("invalid A1.3 manifest contract");
  if (!Array.isArray(manifest.ui_capabilities) || !manifest.ui_capabilities.includes("three-pane-planning-canvas")) throw new Error("A1.3 UI capability contract missing");
  if (!manifest.ui_capabilities.includes("map-driven-scenario-selection")) throw new Error("map-driven scenario capability missing");
  if (stops.features.length !== summary.gtfs.stops) throw new Error("GTFS stop count mismatch");
  if (facilities.features.length !== summary.osm.hospital_destinations) throw new Error("hospital count mismatch");
  if (population.features.length !== summary.population.zones_in_envelope) throw new Error("population zone count mismatch");
  if (!(summary.impact.population_with_gt_1min_increase > 0)) throw new Error("stress test has no measurable travel-time impact");
  if (summary.stage === "A1.5") {
    if (!summary.official_registry || !(summary.official_registry.verified_osm_hospitals > 0)) throw new Error("A1.5 official verification summary missing");
    if (summary.official_registry.official_records_without_osm_match !== 0) throw new Error("official hospital coverage is incomplete");
    if (summary.official_registry.raw_workbook_published !== false) throw new Error("raw official workbook publication is forbidden");
    for (const feature of facilities.features) {
      const p = feature.properties || {};
      if (p.officially_verified !== true) throw new Error("unverified hospital leaked to public GeoJSON");
      for (const forbidden of ["official_id", "official_name", "address", "official_lat", "official_lon"]) {
        if (Object.prototype.hasOwnProperty.call(p, forbidden)) throw new Error("official raw attribute leaked: " + forbidden);
      }
    }
    if (!manifest.ui_capabilities.includes("official-hospital-verification-gate")) throw new Error("A1.5 UI provenance capability missing");
    if (!html.includes("病院照合：愛媛県公式台帳（A）")) throw new Error("A1.5 official verification label missing from generated UI");
    if (!app.includes("愛媛県公式台帳照合済み（A）")) throw new Error("A1.5 hospital popup provenance label missing");
  }
}

console.log("A1.5-compatible planning-canvas smoke test passed for " + target);
