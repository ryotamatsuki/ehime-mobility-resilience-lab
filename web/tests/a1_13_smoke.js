const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..", "..");
const target = process.argv[2] ? path.resolve(repoRoot, process.argv[2]) : path.join(repoRoot, "web");
for (const name of ["index.html", "app.js", "a1_13.css"]) {
  if (!fs.existsSync(path.join(target, name))) throw new Error("missing A1.13 artifact: " + name);
}
const html = fs.readFileSync(path.join(target, "index.html"), "utf8");
const app = fs.readFileSync(path.join(target, "app.js"), "utf8");
const css = fs.readFileSync(path.join(target, "a1_13.css"), "utf8");
if (!css.toLowerCase().includes("robustness")) throw new Error("missing A1.13 robustness CSS contract");
for (const forbidden of ["robustness_score", "robustnessScore", "confidence_interval", "failure_probability"]) {
  if ((app + html).toLowerCase().includes(forbidden.toLowerCase())) throw new Error("A1.13 forbidden marker: " + forbidden);
}

const dataDir = path.join(target, "data");
const robustnessPath = path.join(dataDir, "robustness_summary.json");
if (fs.existsSync(robustnessPath)) {
  const summary = JSON.parse(fs.readFileSync(path.join(dataDir, "summary.json"), "utf8"));
  const manifest = JSON.parse(fs.readFileSync(path.join(dataDir, "manifest.json"), "utf8"));
  const robustness = JSON.parse(fs.readFileSync(robustnessPath, "utf8"));
  const cases = JSON.parse(fs.readFileSync(path.join(dataDir, "robustness_cases.json"), "utf8"));
  if (summary.stage !== "A1.13" || robustness.stage !== "A1.13" || cases.stage !== "A1.13") throw new Error("A1.13 stage contract invalid");
  if (manifest.result_stage !== "A1.13" || manifest.ui_release_stage !== "A1.13") throw new Error("A1.13 manifest stage invalid");
  if (robustness.composite_score !== false) throw new Error("A1.13 must not create a composite score");
  if (robustness.case_count !== 7 || robustness.slots_per_case !== 16 || robustness.case_slot_combinations !== 112) throw new Error("A1.13 case/time contract invalid");
  const expectedCases = ["baseline", "walk_speed_3_6", "walk_speed_1_8", "access_walk_10", "access_walk_30", "transfer_walk_5", "transfer_walk_15"];
  const actualCases = cases.case_registry.map(x => x.id);
  if (JSON.stringify(actualCases) !== JSON.stringify(expectedCases)) throw new Error("A1.13 sensitivity case registry changed");
  if (robustness.baseline_equivalence.status !== "PASS") throw new Error("A1.13 baseline equivalence failed");
  if (robustness.route_stability.case_count !== 7 || robustness.trip_stability.case_count !== 7) throw new Error("A1.13 ranking stability incomplete");
  for (const destination of ["hospital", "emergency", "general", "welfare"]) {
    for (const group of ["65plus", "75plus", "85plus"]) {
      const item = robustness.equity_direction_stability[destination][group];
      for (const metric of ["affected_share_gt1min_gap_pp", "mean_minutes_change_gap"]) {
        if (item[metric].case_count !== 7) throw new Error("A1.13 equity stability incomplete");
      }
    }
  }
  for (const capability of ["robustness-case-registry", "route-ranking-stability", "trip-ranking-stability", "equity-direction-stability", "robustness-boundary-conditions", "no-composite-robustness-score"]) {
    if (!manifest.ui_capabilities.includes(capability)) throw new Error("missing capability " + capability);
  }
  if (!html.includes('data-ui-stage="A1.13"') || !html.includes("ROBUSTNESS / UNCERTAINTY") || !html.includes('id="robustness-card"')) throw new Error("A1.13 generated UI missing");
  if (!app.includes("state.summary.stage !== state.manifest.result_stage")) throw new Error("app does not use manifest-driven result-stage validation");
}
console.log("A1.13 robustness/uncertainty smoke passed for " + target);