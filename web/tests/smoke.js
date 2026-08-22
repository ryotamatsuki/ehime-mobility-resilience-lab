const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const required = [
  "web/index.html",
  "web/app.js",
  "web/styles.css",
  "web/data/manifest.json",
  "web/data/network.geojson",
  "web/data/population_zones.geojson",
  "web/data/metrics.json"
];

for (const file of required) {
  if (!fs.existsSync(path.join(root, file))) {
    throw new Error("missing frontend artifact: " + file);
  }
}

const html = fs.readFileSync(path.join(root, "web/index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "web/app.js"), "utf8");
for (const marker of ["Scenario Builder", "PEOPLE", "TRANSIT", "TRAFFIC", "LOGISTICS", "RELIEF", "provenance"]) {
  if (!html.includes(marker) && !app.includes(marker)) {
    throw new Error("missing frontend marker: " + marker);
  }
}

const metrics = JSON.parse(fs.readFileSync(path.join(root, "web/data/metrics.json"), "utf8"));
if (metrics.classification !== "D" || !metrics.provenance || metrics.transit.status !== "external_input_required") {
  throw new Error("public metrics contract is missing classification, provenance, or GTFS state");
}

console.log("frontend smoke test passed");
