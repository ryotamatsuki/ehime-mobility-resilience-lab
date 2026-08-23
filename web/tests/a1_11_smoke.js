const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..", "..");
const target = process.argv[2] ? path.resolve(repoRoot, process.argv[2]) : path.join(repoRoot, "web");
for (const name of ["index.html", "app.js", "a1_11.css", "a1_11_runtime.js"]) {
  if (!fs.existsSync(path.join(target, name))) throw new Error("missing A1.11 artifact: " + name);
}
const html = fs.readFileSync(path.join(target, "index.html"), "utf8");
const app = fs.readFileSync(path.join(target, "app.js"), "utf8");
const css = fs.readFileSync(path.join(target, "a1_11.css"), "utf8");
const runtime = fs.readFileSync(path.join(target, "a1_11_runtime.js"), "utf8");
for (const marker of ["time-dependent criticality", "time-criticality"]) {
  if (!app.toLowerCase().includes(marker.toLowerCase()) && !runtime.toLowerCase().includes(marker.toLowerCase()) && !css.toLowerCase().includes(marker.toLowerCase()) && !html.toLowerCase().includes(marker.toLowerCase())) {
    throw new Error("missing A1.11 source/UI marker: " + marker);
  }
}
for (const forbidden of ["nominatim", "google.maps", "mapboxgl", "fetchRoute", "routeService"]) {
  if ((app + runtime).toLowerCase().includes(forbidden.toLowerCase())) throw new Error("A1.11 introduced client routing/geocoding: " + forbidden);
}

const dataDir = path.join(target, "data");
const tdPath = path.join(dataDir, "time_dependent_criticality.json");
if (fs.existsSync(tdPath)) {
  const summary = JSON.parse(fs.readFileSync(path.join(dataDir, "summary.json"), "utf8"));
  const manifest = JSON.parse(fs.readFileSync(path.join(dataDir, "manifest.json"), "utf8"));
  const td = JSON.parse(fs.readFileSync(tdPath, "utf8"));
  const reference = JSON.parse(fs.readFileSync(path.join(dataDir, "criticality.json"), "utf8"));
  if (!["A1.11", "A1.12"].includes(summary.stage) || td.stage !== "A1.11") throw new Error("A1.11 capability stage contract invalid");
  if (manifest.result_stage !== summary.stage || manifest.ui_release_stage !== "A1.11") throw new Error("A1.11 manifest contract invalid");
  if (!Array.isArray(td.rows) || td.rows.length !== 16) throw new Error("A1.11 must have 16 hourly rows");
  const times = td.rows.map(r => r.departure_time);
  if (times[0] !== "06:00" || times[times.length - 1] !== "21:00") throw new Error("A1.11 time window invalid");
  const remaining = td.rows.map(r => Number(r.remaining_boardable_connections || 0));
  for (let i = 1; i < remaining.length; i++) if (remaining[i] > remaining[i - 1]) throw new Error("remaining connections must not increase over time");
  for (const row of td.rows) {
    if (!Array.isArray(row.route_ranking) || row.route_ranking.length !== summary.gtfs.active_routes) throw new Error("route ranking width mismatch at " + row.departure_time);
    if (!Array.isArray(row.trip_ranking) || row.trip_ranking.length !== summary.gtfs.active_trips) throw new Error("trip ranking width mismatch at " + row.departure_time);
    row.route_ranking.forEach((item, idx) => {
      if (item.rank !== idx + 1) throw new Error("route rank sequence invalid");
      if (item.evaluated === false && Number(item.impact.population_with_gt_1min_increase || 0) !== 0) throw new Error("skipped route has nonzero impact");
    });
    row.trip_ranking.forEach((item, idx) => {
      if (item.rank !== idx + 1) throw new Error("trip rank sequence invalid");
      if (item.evaluated === false && Number(item.impact.population_with_gt_1min_increase || 0) !== 0) throw new Error("skipped trip has nonzero impact");
    });
  }
  const at0800 = td.rows.find(r => r.departure_time === "08:00");
  if (!at0800) throw new Error("08:00 A1.11 row missing");
  if (at0800.route_ranking[0].id !== reference.route_ranking[0].id) throw new Error("08:00 top route regressed from A1.8");
  if (at0800.trip_ranking[0].id !== reference.trip_ranking[0].id) throw new Error("08:00 top trip regressed from A1.8");
  const meta = summary.time_dependent_criticality || {};
  if (meta.slots !== 16 || !(meta.total_route_evaluations > 0) || !(meta.total_trip_evaluations > 0)) throw new Error("A1.11 summary metadata invalid");
  if (!meta.peak_route_event || !meta.peak_trip_event) throw new Error("A1.11 peak event missing");
  for (const capability of ["time-dependent-route-criticality", "time-dependent-trip-criticality", "hourly-criticality-matrix", "criticality-peak-time"]) {
    if (!manifest.ui_capabilities.includes(capability)) throw new Error("A1.11 capability missing: " + capability);
  }
  if (!html.includes('data-ui-stage="A1.11"') || !html.includes("TIME × SERVICE CRITICALITY")) throw new Error("A1.11 generated UI marker missing");
  if (!app.includes("state.summary.stage !== state.manifest.result_stage")) throw new Error("Planning Canvas does not use manifest-driven result-stage validation");
}
console.log("A1.11 time-dependent criticality smoke passed for " + target);