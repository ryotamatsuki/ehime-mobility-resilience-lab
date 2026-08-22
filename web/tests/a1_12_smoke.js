const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..", "..");
const target = process.argv[2] ? path.resolve(repoRoot, process.argv[2]) : path.join(repoRoot, "web");
for (const name of ["index.html", "app.js", "a1_12.css"]) {
  if (!fs.existsSync(path.join(target, name))) throw new Error("missing A1.12 artifact: " + name);
}
const html = fs.readFileSync(path.join(target, "index.html"), "utf8");
const app = fs.readFileSync(path.join(target, "app.js"), "utf8");
const css = fs.readFileSync(path.join(target, "a1_12.css"), "utf8");
if (!css.toLowerCase().includes("equity")) throw new Error("missing A1.12 equity CSS contract");
for (const forbidden of ["nominatim", "google.maps", "mapboxgl", "vulnerability_score", "compositeScore"]) {
  if ((app + html).toLowerCase().includes(forbidden.toLowerCase())) throw new Error("A1.12 forbidden marker: " + forbidden);
}

const dataDir = path.join(target, "data");
const equityPath = path.join(dataDir, "equity_summary.json");
if (fs.existsSync(equityPath)) {
  const summary = JSON.parse(fs.readFileSync(path.join(dataDir, "summary.json"), "utf8"));
  const manifest = JSON.parse(fs.readFileSync(path.join(dataDir, "manifest.json"), "utf8"));
  const equity = JSON.parse(fs.readFileSync(equityPath, "utf8"));
  const geo = JSON.parse(fs.readFileSync(path.join(dataDir, "vulnerable_population_access.geojson"), "utf8"));
  if (summary.stage !== "A1.12" || equity.stage !== "A1.12") throw new Error("A1.12 stage contract invalid");
  if (manifest.result_stage !== "A1.12" || manifest.ui_release_stage !== "A1.12") throw new Error("A1.12 manifest stage invalid");
  const groupIds = equity.groups.map(x => x.id);
  for (const id of ["all", "65plus", "75plus", "85plus"]) if (!groupIds.includes(id)) throw new Error("missing group " + id);
  for (const destination of ["hospital", "emergency", "general", "welfare"]) {
    const item = equity.destinations[destination];
    if (!item) throw new Error("missing destination " + destination);
    for (const group of groupIds) {
      const metrics = item.groups[group];
      const share = metrics.affected_share_gt1min_pct;
      if (share !== null && (share < -1e-9 || share > 100 + 1e-9)) throw new Error("invalid affected share");
    }
  }
  if (equity.interpretation.composite_score !== false) throw new Error("A1.12 must not create a composite score");
  if (!Array.isArray(geo.features) || geo.features.length !== summary.population.zones_in_envelope) throw new Error("A1.12 GeoJSON feature count mismatch");
  for (const feature of geo.features) {
    const p = feature.properties || {};
    if (!(p.population_85plus >= 0 && p.population_85plus <= p.population_75plus + 1e-6 && p.population_75plus <= p.population_65plus + 1e-6 && p.population_65plus <= p.population + 1e-6)) {
      throw new Error("age weights are not monotone");
    }
  }
  for (const capability of ["vulnerable-population-65plus", "vulnerable-population-75plus", "vulnerable-population-85plus", "equity-gap-metrics", "equity-public-geojson", "current-official-age-context"]) {
    if (!manifest.ui_capabilities.includes(capability)) throw new Error("missing capability " + capability);
  }
  if (!html.includes('data-ui-stage="A1.12"') || !html.includes("VULNERABLE POPULATION / EQUITY") || !html.includes("75歳以上") || !html.includes("85歳以上")) throw new Error("A1.12 generated UI missing");
  if (!app.includes('"A1.12"')) throw new Error("app does not accept A1.12");
}
console.log("A1.12 vulnerable-population/equity smoke passed for " + target);
