const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..", "..");
const target = process.argv[2] ? path.resolve(repoRoot, process.argv[2]) : path.join(repoRoot, "web");
for (const name of ["index.html", "app.js", "styles.css", "mobile.css"]) {
  if (!fs.existsSync(path.join(target, name))) throw new Error("missing frontend artifact: " + name);
}
const html = fs.readFileSync(path.join(target, "index.html"), "utf8");
const app = fs.readFileSync(path.join(target, "app.js"), "utf8");
const mobile = fs.readFileSync(path.join(target, "mobile.css"), "utf8");

for (const marker of ["交通レジリエンス・プランニングキャンバス","SCENARIO BUILDER","Scenario A","影響サマリー","BEFORE / AFTER","DISTRIBUTION","RECOVERY","distribution-chart","population_access.geojson","weightedCdf"]) {
  if (!html.includes(marker) && !app.includes(marker)) throw new Error("missing planning-canvas marker: " + marker);
}
for (const stale of ["road56-stress-test", "国道56号区間停止チェック", "GTFS入力待ち"]) {
  if (html.includes(stale) || app.includes(stale)) throw new Error("stale A0 UI remains: " + stale);
}
for (const truthfulMarker of ["未計算", "disabled", "実被害予測", "D 停止仮定"]) {
  if (!html.includes(truthfulMarker) && !app.includes(truthfulMarker)) throw new Error("missing truthful-scope marker: " + truthfulMarker);
}
for (const marker of ['href="mobile.css"',"max-device-width: 900px","flex-direction: column",".builder-pane .future-section { display: none; }","min-height: 48px","order: 2","order: 3"]) {
  if (!html.includes(marker) && !mobile.includes(marker)) throw new Error("missing A1.4 mobile contract: " + marker);
}
if (!html.includes("viewport-fit=cover")) throw new Error("mobile viewport safe-area contract missing");

const dataDir = path.join(target, "data");
const generatedSummary = path.join(dataDir, "summary.json");
if (fs.existsSync(generatedSummary)) {
  for (const name of ["summary.json","manifest.json","routes.geojson","stops.geojson","facilities.geojson","population_access.geojson"]) {
    if (!fs.existsSync(path.join(dataDir, name))) throw new Error("missing generated A1 data: " + name);
  }
  const summary = JSON.parse(fs.readFileSync(generatedSummary, "utf8"));
  const manifest = JSON.parse(fs.readFileSync(path.join(dataDir, "manifest.json"), "utf8"));
  const population = JSON.parse(fs.readFileSync(path.join(dataDir, "population_access.geojson"), "utf8"));
  const stops = JSON.parse(fs.readFileSync(path.join(dataDir, "stops.geojson"), "utf8"));
  const facilities = JSON.parse(fs.readFileSync(path.join(dataDir, "facilities.geojson"), "utf8"));
  if (!["A1.1","A1.5","A1.6","A1.7","A1.8"].includes(summary.stage) || summary.status !== "computed" || summary.classification !== "C") throw new Error("invalid A1 summary contract");
  if (manifest.stage !== "A1.3" || manifest.status !== "computed") throw new Error("invalid A1.3 manifest contract");
  if (!manifest.ui_capabilities.includes("three-pane-planning-canvas") || !manifest.ui_capabilities.includes("map-driven-scenario-selection")) throw new Error("core Planning Canvas capability missing");
  if (stops.features.length !== summary.gtfs.stops) throw new Error("GTFS stop count mismatch");
  if (facilities.features.length !== summary.osm.hospital_destinations) throw new Error("hospital count mismatch");
  if (population.features.length !== summary.population.zones_in_envelope) throw new Error("population zone count mismatch");
  if (!(summary.impact.population_with_gt_1min_increase > 0)) throw new Error("reference stress test has no measurable impact");

  if (["A1.5","A1.6","A1.7","A1.8"].includes(summary.stage)) {
    if (!summary.official_registry || !(summary.official_registry.verified_osm_hospitals > 0)) throw new Error("official verification summary missing");
    if (summary.official_registry.official_records_without_osm_match !== 0 || summary.official_registry.raw_workbook_published !== false) throw new Error("official hospital gate invalid");
    for (const feature of facilities.features) {
      const p = feature.properties || {};
      if (p.officially_verified !== true) throw new Error("unverified hospital leaked");
      for (const forbidden of ["official_id","official_name","address","official_lat","official_lon"]) if (Object.prototype.hasOwnProperty.call(p, forbidden)) throw new Error("official raw attribute leaked: " + forbidden);
    }
    if (!manifest.ui_capabilities.includes("official-hospital-verification-gate")) throw new Error("official verification capability missing");
    if (!html.includes("病院照合：愛媛県公式台帳（A）") || !app.includes("愛媛県公式台帳照合済み（A）")) throw new Error("official provenance label missing");
  }

  if (["A1.6","A1.7","A1.8"].includes(summary.stage)) {
    if (!summary.transfer_network || !(summary.transfer_network.directed_edges > 0)) throw new Error("walking transfer network missing");
    if (!manifest.ui_capabilities.includes("stop-to-stop-walking-transfer")) throw new Error("walking transfer capability missing");
    if (!html.includes("徒歩乗換") || !html.includes("道路NW 10分以内 + 1分")) throw new Error("transfer assumptions missing");
  }

  if (summary.stage === "A1.6") {
    if (summary.transfer_network.recursive_walking_transfer_chaining !== false) throw new Error("recursive walking transfer chaining enabled");
    if (!summary.same_input_no_transfer || !summary.transfer_model_effect) throw new Error("A1.6 comparison missing");
    if (!manifest.ui_capabilities.includes("same-input-no-transfer-model-comparison")) throw new Error("A1.6 comparison capability missing");
  }

  if (["A1.7","A1.8"].includes(summary.stage)) {
    const temporalPath = path.join(dataDir, "temporal_profile.json");
    if (!fs.existsSync(temporalPath)) throw new Error("temporal profile missing");
    const temporal = JSON.parse(fs.readFileSync(temporalPath, "utf8"));
    if (!summary.temporal_window || summary.temporal_window.slots !== 16 || !Array.isArray(temporal.rows) || temporal.rows.length !== 16) throw new Error("temporal profile invalid");
    if (!manifest.ui_capabilities.includes("full-day-temporal-resilience") || !manifest.ui_capabilities.includes("hourly-impact-profile")) throw new Error("temporal capability missing");
    if (!html.includes("TEMPORAL RESILIENCE") || !html.includes("終日の時間帯レジリエンス")) throw new Error("temporal UI missing");
  }

  if (summary.stage === "A1.8") {
    const criticalityPath = path.join(dataDir, "criticality.json");
    if (!fs.existsSync(criticalityPath)) throw new Error("criticality.json missing");
    const criticality = JSON.parse(fs.readFileSync(criticalityPath, "utf8"));
    if (!Array.isArray(criticality.route_ranking) || !criticality.route_ranking.length || !Array.isArray(criticality.trip_ranking) || !criticality.trip_ranking.length) throw new Error("criticality rankings empty");
    if (!manifest.ui_capabilities.includes("route-criticality-ranking") || !manifest.ui_capabilities.includes("trip-criticality-ranking")) throw new Error("criticality capabilities missing");
    if (!html.includes("SERVICE CRITICALITY") || !html.includes("路線 Top 3") || !html.includes("便 Top 3")) throw new Error("criticality UI missing");
  }
}
console.log("A1.8-compatible planning-canvas smoke test passed for " + target);
