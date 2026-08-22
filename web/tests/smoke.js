const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..", "..");
const target = process.argv[2] ? path.resolve(repoRoot, process.argv[2]) : path.join(repoRoot, "web");

for (const name of ["index.html", "app.js", "styles.css"]) {
  if (!fs.existsSync(path.join(target, name))) throw new Error("missing frontend artifact: " + path.join(target, name));
}

const html = fs.readFileSync(path.join(target, "index.html"), "utf8");
const app = fs.readFileSync(path.join(target, "app.js"), "utf8");
for (const marker of ["右回り停止", "病院Accessibility", "Provenance", "population_access.geojson", "scenario-button"]) {
  if (!html.includes(marker) && !app.includes(marker)) throw new Error("missing A1.2 marker: " + marker);
}
for (const stale of ["road56-stress-test", "国道56号区間停止チェック", "GTFS入力待ち"]) {
  if (html.includes(stale) || app.includes(stale)) throw new Error("stale A0 UI remains: " + stale);
}

const dataDir = path.join(target, "data");
if (fs.existsSync(dataDir)) {
  const required = ["summary.json", "manifest.json", "routes.geojson", "stops.geojson", "facilities.geojson", "population_access.geojson"];
  for (const name of required) {
    if (!fs.existsSync(path.join(dataDir, name))) throw new Error("missing generated A1.2 data: " + name);
  }
  const summary = JSON.parse(fs.readFileSync(path.join(dataDir, "summary.json"), "utf8"));
  const manifest = JSON.parse(fs.readFileSync(path.join(dataDir, "manifest.json"), "utf8"));
  const population = JSON.parse(fs.readFileSync(path.join(dataDir, "population_access.geojson"), "utf8"));
  const stops = JSON.parse(fs.readFileSync(path.join(dataDir, "stops.geojson"), "utf8"));
  const facilities = JSON.parse(fs.readFileSync(path.join(dataDir, "facilities.geojson"), "utf8"));
  if (summary.stage !== "A1.1" || summary.status !== "computed" || summary.classification !== "C") throw new Error("invalid A1.1 summary contract");
  if (manifest.stage !== "A1.2" || manifest.status !== "computed") throw new Error("invalid A1.2 manifest contract");
  if (stops.features.length !== summary.gtfs.stops) throw new Error("GTFS stop count mismatch");
  if (facilities.features.length !== summary.osm.hospital_destinations) throw new Error("hospital count mismatch");
  if (population.features.length !== summary.population.zones_in_envelope) throw new Error("population zone count mismatch");
  if (!(summary.impact.population_with_gt_1min_increase > 0)) throw new Error("stress test has no measurable travel-time impact");
}

console.log("A1.2 frontend smoke test passed for " + target);
