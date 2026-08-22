/* A1.2 static WebGIS. Heavy routing is precomputed in Python; this file only renders verified results. */
(function () {
  "use strict";

  var state = {
    summary: null,
    manifest: null,
    routes: null,
    stops: null,
    facilities: null,
    population: null,
    map: null,
    layers: {},
    scenario: "baseline"
  };

  function get(id) { return document.getElementById(id); }
  function text(id, value) { var node = get(id); if (node) node.textContent = value; }
  function number(value, digits) {
    if (value === null || value === undefined || !isFinite(Number(value))) return "—";
    return Number(value).toLocaleString("ja-JP", { maximumFractionDigits: digits === undefined ? 0 : digits });
  }
  function pct(value) { return isFinite(Number(value)) ? number(value, 1) + "%" : "—"; }
  function finite(value) { return value !== null && value !== undefined && isFinite(Number(value)); }
  function escapeHtml(value) {
    return String(value === null || value === undefined ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#039;");
  }
  function loadJson(name) {
    return fetch("data/" + name).then(function (response) {
      if (!response.ok) throw new Error(name + " HTTP " + response.status);
      return response.json();
    });
  }

  function setError(error) {
    text("data-status", "成果物を読み込めません");
    get("data-status").className = "status status-warn";
    text("result-state", "エラー");
    get("result-state").className = "status status-warn";
    text("selection-note", "データ読み込みエラー: " + error.message);
  }

  function routeStyle(feature) {
    var p = feature.properties || {};
    var stopped = (state.summary.scenario.disabled_route_ids || []).indexOf(String(p.route_id)) >= 0;
    if (state.scenario === "disrupted" && stopped) {
      return { color: "#b42318", weight: 5, opacity: 0.8, dashArray: "8 6" };
    }
    return { color: stopped ? "#7c3aed" : "#175cd3", weight: stopped ? 4 : 3, opacity: 0.82 };
  }

  function accessColor(properties) {
    if (state.scenario === "disrupted") {
      var delta = Number(properties.delta_minutes || 0);
      if (delta > 10) return "#b42318";
      if (delta > 5) return "#dc6803";
      if (delta > 1) return "#f59e0b";
      if (delta > 0) return "#facc15";
      return "#94a3b8";
    }
    var minutes = Number(properties.baseline_minutes);
    if (!isFinite(minutes)) return "#64748b";
    if (minutes <= 30) return "#0f766e";
    if (minutes <= 60) return "#2563eb";
    if (minutes <= 90) return "#d97706";
    return "#b42318";
  }

  function populationPopup(feature) {
    var p = feature.properties || {};
    return "<strong>100m人口メッシュ " + escapeHtml(p.zone_id || "") + "</strong>" +
      "<br>人口: " + number(p.population, 1) + "人相当" +
      "<br>平常時: " + (finite(p.baseline_minutes) ? number(p.baseline_minutes, 1) + "分" : "到達不能") +
      "<br>右回り停止: " + (finite(p.disrupted_minutes) ? number(p.disrupted_minutes, 1) + "分" : "到達不能") +
      "<br><strong>差: " + (finite(p.delta_minutes) ? "+" + number(p.delta_minutes, 1) + "分" : "—") + "</strong>" +
      "<br><small>C：モデル推計</small>";
  }

  function buildPopulationLayer() {
    if (state.layers.population && state.map.hasLayer(state.layers.population)) state.map.removeLayer(state.layers.population);
    state.layers.population = L.geoJSON(state.population, {
      pointToLayer: function (feature, latlng) {
        var p = feature.properties || {};
        var radius = Math.max(3, Math.min(9, 2.5 + Math.sqrt(Math.max(Number(p.population || 0), 0)) * 0.55));
        return L.circleMarker(latlng, {
          radius: radius,
          color: accessColor(p),
          weight: 1,
          fillColor: accessColor(p),
          fillOpacity: state.scenario === "disrupted" && Number(p.delta_minutes || 0) <= 0 ? 0.16 : 0.62
        });
      },
      onEachFeature: function (feature, layer) {
        layer.bindPopup(populationPopup(feature));
        layer.on("click", function () {
          var p = feature.properties || {};
          text("selection-note", "メッシュ " + (p.zone_id || "") + "：" + number(p.population, 1) + "人相当、病院まで " + number(p.baseline_minutes, 1) + "分 → " + number(p.disrupted_minutes, 1) + "分（差 +" + number(p.delta_minutes, 1) + "分）");
        });
      }
    });
    if (document.querySelector('[data-layer="population"]').checked) state.layers.population.addTo(state.map);
  }

  function initializeMap() {
    if (!window.L) throw new Error("Leafletを読み込めません");
    get("map").innerHTML = "";
    state.map = L.map("map", { scrollWheelZoom: false }).setView([33.51, 132.55], 12);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors"
    }).addTo(state.map);

    state.layers.routes = L.geoJSON(state.routes, {
      style: routeStyle,
      onEachFeature: function (feature, layer) {
        var p = feature.properties || {};
        var stopped = (state.summary.scenario.disabled_route_ids || []).indexOf(String(p.route_id)) >= 0;
        layer.bindPopup("<strong>" + escapeHtml(p.route_name || ("route " + p.route_id)) + "</strong><br>route_id: " + escapeHtml(p.route_id) + "<br>形状: " + escapeHtml(p.shape_source || "") + (stopped ? "<br><strong>D仮定：停止対象</strong>" : ""));
      }
    }).addTo(state.map);

    state.layers.stops = L.geoJSON(state.stops, {
      pointToLayer: function (feature, latlng) {
        return L.circleMarker(latlng, { radius: 3, color: "#0f3d91", weight: 1, fillColor: "#ffffff", fillOpacity: 1 });
      },
      onEachFeature: function (feature, layer) {
        var p = feature.properties || {};
        layer.bindTooltip(p.name || p.stop_id || "停留所");
      }
    }).addTo(state.map);

    state.layers.facilities = L.geoJSON(state.facilities, {
      pointToLayer: function (feature, latlng) {
        return L.circleMarker(latlng, { radius: 7, color: "#6d28d9", weight: 2, fillColor: "#ede9fe", fillOpacity: 0.95 });
      },
      onEachFeature: function (feature, layer) {
        var p = feature.properties || {};
        layer.bindPopup("<strong>病院</strong><br>" + escapeHtml(p.name || "名称未登録") + "<br><small>OSM amenity=hospital</small>");
      }
    }).addTo(state.map);

    buildPopulationLayer();
    var bounds = state.layers.routes.getBounds();
    if (bounds.isValid()) state.map.fitBounds(bounds.pad(0.14));
  }

  function renderMetrics() {
    var current = state.scenario === "baseline" ? state.summary.baseline : state.summary.disrupted;
    var impact = state.summary.impact || {};
    var cards;
    if (state.scenario === "baseline") {
      cards = [
        ["30分以内", pct(current.reachable_30min_pct), number(current.reachable_30min, 0) + "人相当"],
        ["60分以内", pct(current.reachable_60min_pct), number(current.reachable_60min, 0) + "人相当"],
        ["90分以内", pct(current.reachable_90min_pct), number(current.reachable_90min, 0) + "人相当"],
        ["平均所要時間", number(current.population_weighted_mean_minutes, 2) + "分", "人口加重平均"]
      ];
    } else {
      cards = [
        ["1分超悪化", number(impact.population_with_gt_1min_increase, 0) + "人", pct(impact.population_with_gt_1min_increase / state.summary.population.population_in_envelope * 100)],
        ["平均所要時間", "+" + number(impact.mean_minutes_change, 2) + "分", number(current.population_weighted_mean_minutes, 2) + "分"],
        ["30分以内", pct(current.reachable_30min_pct), "減少 " + number(impact.accessibility_loss_30min_population, 0) + "人"],
        ["60分以内", pct(current.reachable_60min_pct), "減少 " + number(impact.accessibility_loss_60min_population, 0) + "人"]
      ];
    }
    get("metric-grid").innerHTML = cards.map(function (card) {
      return '<div class="metric-card"><div class="metric-label">' + escapeHtml(card[0]) + '</div><div class="metric-value">' + escapeHtml(card[1]) + '</div><div class="metric-note">' + escapeHtml(card[2]) + '</div></div>';
    }).join("");

    var before = Number(state.summary.baseline.population_weighted_mean_minutes || 0);
    var after = Number(state.summary.disrupted.population_weighted_mean_minutes || 0);
    var max = Math.max(before, after, 1);
    get("before-bar").style.width = (before / max * 100) + "%";
    get("after-bar").style.width = (after / max * 100) + "%";
    text("comparison-text", "人口加重平均病院アクセス時間: " + number(before, 3) + "分 → " + number(after, 3) + "分（+" + number(after - before, 3) + "分）");
  }

  function renderCritical() {
    var features = (state.population.features || []).filter(function (feature) {
      return Number((feature.properties || {}).delta_minutes || 0) > 0;
    }).sort(function (a, b) {
      var ap = a.properties || {}, bp = b.properties || {};
      return Number(bp.population || 0) * Number(bp.delta_minutes || 0) - Number(ap.population || 0) * Number(ap.delta_minutes || 0);
    }).slice(0, 5);

    if (!features.length) {
      get("critical-list").innerHTML = "<li>1分未満の変化のみです。</li>";
      return;
    }
    get("critical-list").innerHTML = features.map(function (feature, index) {
      var p = feature.properties || {};
      return '<li><button type="button" data-zone="' + escapeHtml(p.zone_id) + '">メッシュ ' + escapeHtml(p.zone_id) + '</button><br><span class="muted">' + number(p.population, 1) + '人相当 / +' + number(p.delta_minutes, 1) + '分</span></li>';
    }).join("");

    Array.prototype.forEach.call(get("critical-list").querySelectorAll("button"), function (button) {
      button.addEventListener("click", function () {
        var feature = (state.population.features || []).find(function (item) { return String((item.properties || {}).zone_id) === button.dataset.zone; });
        if (!feature) return;
        var coordinates = feature.geometry.coordinates;
        state.map.setView([coordinates[1], coordinates[0]], 15);
        text("selection-note", "影響上位メッシュ " + button.dataset.zone + " へ移動しました。地図上の点をクリックすると詳細を確認できます。");
      });
    });
  }

  function renderProvenance() {
    var provenance = state.summary.provenance || {};
    text("provenance", JSON.stringify({
      input_data_versions: provenance.input_data_versions || [],
      model_version: provenance.model_version,
      scenario_id: provenance.scenario_id,
      parameters: provenance.parameters || {},
      generated_at_utc: provenance.generated_at_utc,
      git_sha: provenance.git_sha,
      classification: state.summary.classification
    }, null, 2));
    var seen = {};
    var limitations = (provenance.limitations || []).concat((state.manifest.public_limitations || [])).filter(function (item) {
      if (seen[item]) return false;
      seen[item] = true;
      return true;
    });
    get("limitations").innerHTML = "<strong>Limitations</strong><ul>" + limitations.map(function (item) { return "<li>" + escapeHtml(item) + "</li>"; }).join("") + "</ul>";
  }

  function setScenario(name) {
    state.scenario = name;
    Array.prototype.forEach.call(document.querySelectorAll(".scenario-button"), function (button) {
      button.classList.toggle("active", button.dataset.scenario === name);
    });
    var disrupted = name === "disrupted";
    text("map-title", disrupted ? "病院Accessibility — 右回り停止" : "病院Accessibility — 平常時");
    text("scenario-description", disrupted
      ? "D仮定：ぐるりんおおず右回り系統（route 11 / 21）を利用不能として、同じ2026年8月21日08:00出発条件で比較します。"
      : "2026年8月21日 08:00出発。ぐるりんおおず全路線が利用できる平常時を表示します。");
    text("result-state", disrupted ? "停止後を表示" : "平常時を表示");
    text("insight-title", disrupted ? "約" + number(state.summary.impact.population_with_gt_1min_increase, 0) + "人相当で1分超悪化" : "平常時の病院アクセスを基準にする");
    text("insight-body", disrupted
      ? "30分・60分圏人口は同じでも、連続的な所要時間では悪化が確認できます。閾値指標だけで影響ゼロと判断しません。"
      : "人口メッシュ、徒歩ネットワーク、GTFS時刻表を統合したBeforeです。右回り停止を選ぶと同じ入力版のAfterへ切り替わります。");
    if (state.layers.routes) state.layers.routes.setStyle(routeStyle);
    if (state.map && state.population) buildPopulationLayer();
    renderMetrics();
  }

  function bindControls() {
    Array.prototype.forEach.call(document.querySelectorAll(".scenario-button"), function (button) {
      button.addEventListener("click", function () { setScenario(button.dataset.scenario); });
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-layer]"), function (checkbox) {
      checkbox.addEventListener("change", function () {
        var layer = state.layers[checkbox.dataset.layer];
        if (!layer || !state.map) return;
        if (checkbox.checked) layer.addTo(state.map); else state.map.removeLayer(layer);
      });
    });
    get("recover").addEventListener("click", function () {
      setScenario("baseline");
      text("selection-note", "停止仮定を解除し、平常時へ戻しました。");
    });
  }

  function boot() {
    Promise.all([
      loadJson("summary.json"), loadJson("manifest.json"), loadJson("routes.geojson"),
      loadJson("stops.geojson"), loadJson("facilities.geojson"), loadJson("population_access.geojson")
    ]).then(function (values) {
      state.summary = values[0];
      state.manifest = values[1];
      state.routes = values[2];
      state.stops = values[3];
      state.facilities = values[4];
      state.population = values[5];
      if (state.summary.stage !== "A1.1" || state.manifest.stage !== "A1.2") throw new Error("stage contract mismatch");
      text("data-status", "実GTFS v" + (state.summary.gtfs.feed_version || "?") + " / " + number(state.summary.gtfs.stops) + "停留所");
      initializeMap();
      renderMetrics();
      renderCritical();
      renderProvenance();
      bindControls();
      setScenario("baseline");
    }).catch(setError);
  }

  document.addEventListener("DOMContentLoaded", boot);
}());
