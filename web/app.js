/* A1.3 planning canvas. Heavy routing is precomputed in Python; this file renders only verified A1.1 results. */
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
    scenario: "baseline",
    difference: false,
    selectedZone: null
  };

  function get(id) { return document.getElementById(id); }
  function text(id, value) { var node = get(id); if (node) node.textContent = value; }
  function finite(value) { return value !== null && value !== undefined && isFinite(Number(value)); }
  function number(value, digits) {
    if (!finite(value)) return "—";
    return Number(value).toLocaleString("ja-JP", { maximumFractionDigits: digits === undefined ? 0 : digits });
  }
  function pct(value) { return finite(value) ? number(value, 1) + "%" : "—"; }
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
  function scenarioIsDisrupted() { return state.scenario === "disrupted"; }
  function scenarioIsRecovery() { return state.scenario === "recovery"; }

  function setError(error) {
    text("selection-note", "データ読み込みエラー: " + error.message);
    text("impact-heading", "データを読み込めません");
    text("affected-population", "—");
    var map = get("map");
    if (map) map.innerHTML = '<div class="map-loading">公開成果物を読み込めません。GitHub ActionsのA1実データ生成結果を確認してください。</div>';
  }

  function disabledRouteIds() {
    return (state.summary && state.summary.scenario && state.summary.scenario.disabled_route_ids || []).map(String);
  }

  function routeIsTarget(feature) {
    return disabledRouteIds().indexOf(String((feature.properties || {}).route_id)) >= 0;
  }

  function routeStyle(feature) {
    if (scenarioIsDisrupted() && routeIsTarget(feature)) {
      return { color: "#c4322c", weight: 5, opacity: .9, dashArray: "9 6" };
    }
    return { color: "#1456d9", weight: 3.3, opacity: .82 };
  }

  function baselineColor(minutes) {
    if (!finite(minutes)) return "#64748b";
    if (Number(minutes) <= 30) return "#0f766e";
    if (Number(minutes) <= 60) return "#2563eb";
    if (Number(minutes) <= 90) return "#d97706";
    return "#b42318";
  }

  function deltaColor(delta) {
    if (!finite(delta)) return "#64748b";
    delta = Number(delta);
    if (delta > 10) return "#b42318";
    if (delta > 5) return "#dc6803";
    if (delta > 1) return "#f59e0b";
    if (delta > 0) return "#facc15";
    return "#94a3b8";
  }

  function populationColor(properties) {
    if (state.difference) return deltaColor(properties.delta_minutes);
    if (scenarioIsDisrupted()) return baselineColor(properties.disrupted_minutes);
    return baselineColor(properties.baseline_minutes);
  }

  function populationPopup(feature) {
    var p = feature.properties || {};
    var delta = finite(p.delta_minutes) ? Number(p.delta_minutes) : null;
    return "<strong>100m人口メッシュ " + escapeHtml(p.zone_id || "") + "</strong>" +
      "<br>人口: " + number(p.population, 1) + "人相当" +
      "<br>平常時: " + (finite(p.baseline_minutes) ? number(p.baseline_minutes, 1) + "分" : "到達不能") +
      "<br>Scenario A: " + (finite(p.disrupted_minutes) ? number(p.disrupted_minutes, 1) + "分" : "到達不能") +
      "<br><strong>差: " + (delta === null ? "—" : (delta >= 0 ? "+" : "") + number(delta, 1) + "分") + "</strong>" +
      "<br><small>C：モデル推計 / 人口はB区分</small>";
  }

  function selectZone(feature) {
    state.selectedZone = feature;
    var p = feature.properties || {};
    var delta = finite(p.delta_minutes) ? Number(p.delta_minutes) : null;
    text("selection-note", "メッシュ " + (p.zone_id || "") + "：" + number(p.population, 1) + "人相当、病院まで " + number(p.baseline_minutes, 1) + "分 → " + number(p.disrupted_minutes, 1) + "分（差 " + (delta !== null && delta >= 0 ? "+" : "") + number(delta, 1) + "分）");
    var card = get("selected-zone-card");
    if (card) {
      card.innerHTML = '<strong>メッシュ ' + escapeHtml(p.zone_id || "") + '</strong>' +
        '<div class="zone-metrics">' +
        '<div><span>人口</span><strong>' + number(p.population, 1) + '人相当</strong></div>' +
        '<div><span>所要時間差</span><strong>' + (delta !== null && delta >= 0 ? '+' : '') + number(delta, 1) + '分</strong></div>' +
        '<div><span>Baseline</span><strong>' + number(p.baseline_minutes, 1) + '分</strong></div>' +
        '<div><span>Scenario A</span><strong>' + number(p.disrupted_minutes, 1) + '分</strong></div>' +
        '</div>';
    }
  }

  function buildPopulationLayer() {
    if (!state.map || !state.population) return;
    if (state.layers.population && state.map.hasLayer(state.layers.population)) state.map.removeLayer(state.layers.population);
    state.layers.population = L.geoJSON(state.population, {
      pointToLayer: function (feature, latlng) {
        var p = feature.properties || {};
        var pop = Math.max(Number(p.population || 0), 0);
        var radius = Math.max(2.5, Math.min(8.5, 2 + Math.sqrt(pop) * .5));
        var color = populationColor(p);
        var noChange = state.difference && Number(p.delta_minutes || 0) <= 0;
        return L.circleMarker(latlng, {
          radius: radius,
          color: color,
          weight: .7,
          fillColor: color,
          fillOpacity: noChange ? .13 : .58
        });
      },
      onEachFeature: function (feature, layer) {
        layer.bindPopup(populationPopup(feature));
        layer.on("click", function () { selectZone(feature); });
      }
    }).addTo(state.map);
  }

  function bindRoutePopup(feature, layer) {
    var p = feature.properties || {};
    var isTarget = routeIsTarget(feature);
    var button = isTarget ? '<br><button type="button" class="popup-scenario-button">この系統を運休して比較</button>' : '';
    var note = isTarget ? 'A1.1で停止結果を計算済み' : 'この路線単独の停止結果は未計算';
    layer.bindPopup("<strong>" + escapeHtml(p.route_name || ("route " + p.route_id)) + "</strong>" +
      "<br>route_id: " + escapeHtml(p.route_id) +
      "<br>形状: " + escapeHtml(p.shape_source || "") +
      "<br><small>" + escapeHtml(note) + "</small>" + button);
    if (isTarget) {
      layer.on("popupopen", function (event) {
        var node = event.popup.getElement();
        var action = node && node.querySelector(".popup-scenario-button");
        if (action) action.addEventListener("click", function () { setScenario("disrupted", true); });
      });
    }
  }

  function initializeMap() {
    if (!window.L) throw new Error("Leafletを読み込めません");
    get("map").innerHTML = "";
    state.map = L.map("map", { scrollWheelZoom: false, zoomControl: true }).setView([33.51, 132.55], 12);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors"
    }).addTo(state.map);

    state.layers.routes = L.geoJSON(state.routes, {
      style: routeStyle,
      onEachFeature: bindRoutePopup
    }).addTo(state.map);

    state.layers.stops = L.geoJSON(state.stops, {
      pointToLayer: function (feature, latlng) {
        return L.circleMarker(latlng, { radius: 3, color: "#1552a8", weight: 1.3, fillColor: "#fff", fillOpacity: 1 });
      },
      onEachFeature: function (feature, layer) {
        var p = feature.properties || {};
        layer.bindTooltip(p.name || p.stop_id || "停留所", { direction: "top" });
      }
    }).addTo(state.map);

    state.layers.facilities = L.geoJSON(state.facilities, {
      pointToLayer: function (feature, latlng) {
        return L.circleMarker(latlng, { radius: 6.5, color: "#6431c9", weight: 2, fillColor: "#eee9ff", fillOpacity: .96 });
      },
      onEachFeature: function (feature, layer) {
        var p = feature.properties || {};
        layer.bindPopup("<strong>病院</strong><br>" + escapeHtml(p.name || "名称未登録") + "<br><small>OpenStreetMap amenity=hospital（B）</small>");
      }
    }).addTo(state.map);

    buildPopulationLayer();
    var bounds = state.layers.routes.getBounds();
    if (bounds.isValid()) state.map.fitBounds(bounds.pad(.13));
  }

  function weightedPopulation(deltaThreshold) {
    if (!state.population) return 0;
    return state.population.features.reduce(function (sum, feature) {
      var p = feature.properties || {};
      return sum + (finite(p.delta_minutes) && Number(p.delta_minutes) >= deltaThreshold ? Number(p.population || 0) : 0);
    }, 0);
  }

  function currentAccess() {
    return scenarioIsDisrupted() ? state.summary.disrupted : state.summary.baseline;
  }

  function updateScale() {
    var delta = state.difference;
    get("baseline-scale").hidden = delta;
    get("delta-scale").hidden = !delta;
    text("map-scale-title", delta ? "所要時間の変化（分）" : "病院までの所要時間（分）");
    get("scale-labels").innerHTML = delta
      ? "<span>0</span><span>+1</span><span>+5</span><span>+10</span><span>+10超</span>"
      : "<span>≤30</span><span>≤60</span><span>≤90</span><span>&gt;90</span>";
  }

  function updateScenarioTabs() {
    Array.prototype.forEach.call(document.querySelectorAll(".scenario-tab[data-scenario]"), function (button) {
      button.classList.toggle("active", button.dataset.scenario === state.scenario);
    });
    get("recovery-tab").classList.toggle("active", scenarioIsRecovery());
  }

  function updateBuilder() {
    var checked = scenarioIsDisrupted();
    get("clockwise-toggle").checked = checked;
    text("selected-transit-count", checked ? "選択中 1条件" : "選択中 0条件");
    text("selection-note", checked
      ? "右回り系統（route 11 / 21）を利用不能とするD区分Stress Testを表示しています。"
      : scenarioIsRecovery()
        ? "右回り系統を復旧し、Baselineと同じアクセス状態へ戻しています。"
        : "Baselineを表示しています。右回りを選ぶと、検証済みの停止シナリオへ切り替えます。");
  }

  function renderImpact() {
    var disrupted = scenarioIsDisrupted();
    var recovery = scenarioIsRecovery();
    var access = currentAccess();
    var impact = state.summary.impact || {};
    var total = Number(state.summary.population.population_in_envelope || 0);
    var affected = disrupted ? Number(impact.population_with_gt_1min_increase || 0) : 0;
    var p1 = disrupted ? weightedPopulation(1) : 0;
    var p5 = disrupted ? weightedPopulation(5) : 0;
    var p10 = disrupted ? weightedPopulation(10) : 0;
    var loss60 = disrupted ? Number(impact.accessibility_loss_60min_population || 0) : 0;
    var beforeMean = Number(state.summary.baseline.population_weighted_mean_minutes || 0);
    var afterMean = disrupted ? Number(state.summary.disrupted.population_weighted_mean_minutes || 0) : beforeMean;

    text("impact-heading", disrupted ? "このシナリオの影響（Baseline比較）" : recovery ? "Recovery：右回り復旧" : "平常時（Baseline）");
    text("affected-population", number(affected, 0) + "人");
    text("affected-share", "対象人口の" + pct(total ? affected / total * 100 : 0));
    text("reachable-60", number(access.reachable_60min, 0));
    text("unreachable-loss", number(loss60, 0));
    text("impact-1", number(p1, 0) + "人");
    text("impact-5", number(p5, 0) + "人");
    text("impact-10", number(p10, 0) + "人");
    text("mean-before", number(beforeMean, 1) + "分");
    text("mean-after", number(afterMean, 1) + "分");
    text("mean-delta", (afterMean - beforeMean >= 0 ? "+" : "") + number(afterMean - beforeMean, 2) + "分");
    text("stop-count", state.summary.gtfs.stops);
    text("hospital-count", state.summary.osm.hospital_destinations);
    text("route-count", state.summary.gtfs.routes);
    renderCritical(disrupted);
  }

  function affectedFeatures() {
    return (state.population.features || []).filter(function (feature) {
      return Number((feature.properties || {}).delta_minutes || 0) > 0;
    }).sort(function (a, b) {
      var ap = a.properties || {}, bp = b.properties || {};
      return Number(bp.population || 0) * Number(bp.delta_minutes || 0) - Number(ap.population || 0) * Number(ap.delta_minutes || 0);
    });
  }

  function renderCritical(disrupted) {
    var list = get("critical-list");
    if (!disrupted) {
      list.innerHTML = '<li>Scenario Aを選ぶと影響地域を順位表示します。</li>';
      return;
    }
    var features = affectedFeatures().slice(0, 5);
    if (!features.length) {
      list.innerHTML = '<li>旅行時間増加メッシュはありません。</li>';
      return;
    }
    list.innerHTML = features.map(function (feature, index) {
      var p = feature.properties || {};
      return '<li><button type="button" data-zone="' + escapeHtml(p.zone_id) + '">' + (index + 1) + '. メッシュ ' + escapeHtml(p.zone_id) + '</button>' +
        '<span class="rank-meta">' + number(p.population, 0) + '人 / +' + number(p.delta_minutes, 1) + '分</span></li>';
    }).join("");
    Array.prototype.forEach.call(list.querySelectorAll("button[data-zone]"), function (button) {
      button.addEventListener("click", function () {
        var feature = state.population.features.find(function (item) { return String((item.properties || {}).zone_id) === button.dataset.zone; });
        if (!feature) return;
        var c = feature.geometry.coordinates;
        state.map.setView([c[1], c[0]], 15);
        selectZone(feature);
      });
    });
  }

  function fitAffected() {
    var features = affectedFeatures();
    if (!features.length || !state.map) return;
    var latlngs = features.map(function (feature) { return [feature.geometry.coordinates[1], feature.geometry.coordinates[0]]; });
    state.map.fitBounds(L.latLngBounds(latlngs).pad(.15));
  }

  function renderProvenance() {
    var p = state.summary.provenance || {};
    text("provenance", JSON.stringify({
      input_data_versions: p.input_data_versions || [],
      model_version: p.model_version,
      scenario_id: p.scenario_id,
      parameters: p.parameters || {},
      generated_at_utc: p.generated_at_utc,
      git_sha: p.git_sha,
      classification: state.summary.classification
    }, null, 2));
    var seen = {};
    var limitations = (p.limitations || []).concat((state.manifest && state.manifest.public_limitations || [])).filter(function (item) {
      if (seen[item]) return false;
      seen[item] = true;
      return true;
    });
    get("limitations").innerHTML = "<strong>Limitations</strong><ul>" + limitations.map(function (item) { return "<li>" + escapeHtml(item) + "</li>"; }).join("") + "</ul>";
  }

  function setScenario(name, fromMap) {
    if (["baseline", "disrupted", "recovery"].indexOf(name) < 0) return;
    state.scenario = name;
    state.difference = name === "disrupted";
    get("difference-toggle").checked = state.difference;
    get("recovery-toggle").checked = name === "recovery";
    updateScenarioTabs();
    updateBuilder();
    updateScale();
    if (state.layers.routes) state.layers.routes.setStyle(routeStyle);
    buildPopulationLayer();
    renderImpact();
    renderRecovery();
    if (fromMap) text("selection-note", "地図上の計算済み対象路線からScenario Aへ切り替えました。");
  }

  function renderMiniMaps() {
    var features = state.population.features || [];
    if (!features.length) return;
    var xs = features.map(function (f) { return f.geometry.coordinates[0]; });
    var ys = features.map(function (f) { return f.geometry.coordinates[1]; });
    var minX = Math.min.apply(null, xs), maxX = Math.max.apply(null, xs);
    var minY = Math.min.apply(null, ys), maxY = Math.max.apply(null, ys);
    function project(feature) {
      var c = feature.geometry.coordinates;
      return [8 + (c[0] - minX) / Math.max(maxX - minX, .000001) * 164, 112 - (c[1] - minY) / Math.max(maxY - minY, .000001) * 104];
    }
    function draw(id, mode) {
      var svg = get(id);
      var html = '<rect x="0" y="0" width="180" height="120" fill="#f5f8fc"/>';
      features.forEach(function (feature) {
        var p = feature.properties || {};
        var xy = project(feature);
        var value = mode === "before" ? p.baseline_minutes : mode === "after" ? p.disrupted_minutes : p.delta_minutes;
        var color = mode === "delta" ? deltaColor(value) : baselineColor(value);
        var opacity = mode === "delta" && Number(value || 0) <= 0 ? .14 : .66;
        var radius = Math.max(1.1, Math.min(3.4, 1 + Math.sqrt(Math.max(Number(p.population || 0), 0)) * .15));
        html += '<circle cx="' + xy[0].toFixed(1) + '" cy="' + xy[1].toFixed(1) + '" r="' + radius.toFixed(1) + '" fill="' + color + '" fill-opacity="' + opacity + '"/>';
      });
      svg.innerHTML = html;
    }
    draw("mini-map-before", "before");
    draw("mini-map-delta", "delta");
    draw("mini-map-after", "after");
  }

  function weightedCdf(key, maxMinutes) {
    var features = state.population.features || [];
    var total = features.reduce(function (sum, f) { return sum + Number((f.properties || {}).population || 0); }, 0) || 1;
    var points = [];
    for (var minute = 0; minute <= maxMinutes; minute += 5) {
      var reached = features.reduce(function (sum, f) {
        var p = f.properties || {};
        return sum + (finite(p[key]) && Number(p[key]) <= minute ? Number(p.population || 0) : 0);
      }, 0);
      points.push([minute, reached / total * 100]);
    }
    return points;
  }

  function renderDistributionChart() {
    var svg = get("distribution-chart");
    var width = 520, height = 230, left = 42, right = 12, top = 12, bottom = 34;
    var plotW = width - left - right, plotH = height - top - bottom, maxMinutes = 120;
    function x(v) { return left + v / maxMinutes * plotW; }
    function y(v) { return top + (100 - v) / 100 * plotH; }
    function path(points) { return points.map(function (p, i) { return (i ? "L" : "M") + x(p[0]).toFixed(1) + "," + y(p[1]).toFixed(1); }).join(" "); }
    var html = '<rect width="520" height="230" fill="#fff"/>';
    [0, 25, 50, 75, 100].forEach(function (v) {
      html += '<line x1="' + left + '" y1="' + y(v) + '" x2="' + (width - right) + '" y2="' + y(v) + '" stroke="#e3e8ef" stroke-width="1"/>';
      html += '<text x="' + (left - 7) + '" y="' + (y(v) + 3) + '" text-anchor="end" fill="#718096" font-size="10">' + v + '%</text>';
    });
    [0, 30, 60, 90, 120].forEach(function (v) {
      html += '<line x1="' + x(v) + '" y1="' + top + '" x2="' + x(v) + '" y2="' + (height - bottom) + '" stroke="#eef1f5" stroke-width="1"/>';
      html += '<text x="' + x(v) + '" y="' + (height - 13) + '" text-anchor="middle" fill="#718096" font-size="10">' + v + '</text>';
    });
    html += '<path d="' + path(weightedCdf("baseline_minutes", maxMinutes)) + '" fill="none" stroke="#1456d9" stroke-width="3"/>';
    html += '<path d="' + path(weightedCdf("disrupted_minutes", maxMinutes)) + '" fill="none" stroke="#c4322c" stroke-width="3"/>';
    html += '<text x="' + (width / 2) + '" y="225" text-anchor="middle" fill="#667085" font-size="10">病院までの所要時間（分）</text>';
    svg.innerHTML = html;
  }

  function renderRecovery() {
    var affected = Number(state.summary.impact.population_with_gt_1min_increase || 0);
    var restored = scenarioIsRecovery() || get("recovery-toggle").checked;
    text("recovery-benefit", "復旧すると約" + number(affected, 0) + "人相当の1分超悪化が解消");
    text("recovery-before-value", number(affected, 0) + "人");
    text("recovery-after-value", restored ? "0人" : number(affected, 0) + "人");
    get("recovery-before-bar").style.width = "100%";
    get("recovery-after-bar").style.width = restored ? "0%" : "100%";
  }

  function renderMetadata() {
    var provenance = state.summary.provenance || {};
    text("meta-analysis-date", state.summary.analysis_date + " " + state.summary.departure_time);
    text("meta-model-version", provenance.model_version || "—");
    text("meta-feed-version", "v" + (state.summary.gtfs.feed_version || "—"));
    text("footer-model", "Model: " + (provenance.model_version || "—"));
    text("footer-git", "Git: " + String(provenance.git_sha || "—").slice(0, 8));
    text("map-coverage", state.manifest.coverage || "大洲市ぐるりんおおず停留所範囲周辺");
    text("clockwise-route-ids", "route " + disabledRouteIds().join(" / "));
    var names = state.summary.scenario.disabled_route_names || [];
    if (names.length) text("clockwise-label", names.join(" / "));
  }

  function openImpactPanel(id) {
    Array.prototype.forEach.call(document.querySelectorAll(".impact-tab"), function (button) {
      button.classList.toggle("active", button.dataset.panel === id);
    });
    Array.prototype.forEach.call(document.querySelectorAll(".impact-panel"), function (panel) {
      var active = panel.id === id;
      panel.hidden = !active;
      panel.classList.toggle("active", active);
    });
  }

  function bindControls() {
    Array.prototype.forEach.call(document.querySelectorAll(".scenario-tab[data-scenario]"), function (button) {
      button.addEventListener("click", function () { setScenario(button.dataset.scenario); });
    });
    get("recovery-tab").addEventListener("click", function () { setScenario("recovery"); });
    get("clockwise-toggle").addEventListener("change", function () {
      text("selected-transit-count", get("clockwise-toggle").checked ? "選択中 1条件" : "選択中 0条件");
    });
    get("run-analysis").addEventListener("click", function () { setScenario(get("clockwise-toggle").checked ? "disrupted" : "baseline"); });
    get("reset-analysis").addEventListener("click", function () { setScenario("baseline"); });
    get("difference-toggle").addEventListener("change", function () {
      state.difference = get("difference-toggle").checked;
      updateScale();
      buildPopulationLayer();
    });
    Array.prototype.forEach.call(document.querySelectorAll(".impact-tab"), function (button) {
      button.addEventListener("click", function () { openImpactPanel(button.dataset.panel); });
    });
    get("fit-affected").addEventListener("click", fitAffected);
    get("settings-action").addEventListener("click", function () {
      get("assumptions-panel").hidden = !get("assumptions-panel").hidden;
      if (!get("assumptions-panel").hidden) get("assumptions-panel").scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
    get("data-info-action").addEventListener("click", function () { openImpactPanel("report-panel"); get("report-panel").scrollIntoView({ behavior: "smooth", block: "nearest" }); });
    get("print-action").addEventListener("click", function () { window.print(); });
    get("report-print").addEventListener("click", function () { window.print(); });
    get("help-action").addEventListener("click", function () { if (get("help-dialog").showModal) get("help-dialog").showModal(); });
    get("share-action").addEventListener("click", function () {
      var payload = { title: document.title, text: "Ehime Mobility Resilience Lab", url: location.href };
      if (navigator.share) {
        navigator.share(payload).catch(function () {});
      } else if (navigator.clipboard) {
        navigator.clipboard.writeText(location.href).then(function () { text("selection-note", "現在のURLをクリップボードへコピーしました。"); });
      }
    });
    get("recovery-toggle").addEventListener("change", renderRecovery);
    get("apply-recovery").addEventListener("click", function () { setScenario(get("recovery-toggle").checked ? "recovery" : "disrupted"); });
    get("comparison-metric").addEventListener("change", function () {
      var delta = get("comparison-metric").value === "delta";
      state.difference = delta;
      get("difference-toggle").checked = delta;
      updateScale();
      buildPopulationLayer();
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
      if (state.summary.stage !== "A1.1") throw new Error("analysis stage contract mismatch");
      if (["A1.2", "A1.3"].indexOf(state.manifest.stage) < 0) throw new Error("public UI stage contract mismatch");
      initializeMap();
      renderMetadata();
      renderProvenance();
      renderMiniMaps();
      renderDistributionChart();
      bindControls();
      setScenario("baseline");
    }).catch(setError);
  }

  document.addEventListener("DOMContentLoaded", boot);
}());
