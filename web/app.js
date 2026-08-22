/* Static-first public layer. Heavy recalculation remains in Python. */
(function () {
  "use strict";

  var state = {
    network: null,
    population: null,
    metrics: null,
    manifest: null,
    map: null,
    roadLayer: null,
    populationLayer: null,
    selectedLink: null,
    selectedFeature: null,
    mode: "PEOPLE",
    scenario: "road56-stress-test"
  };

  var modeCopy = {
    PEOPLE: "人口メッシュを分母に、指定リンク停止時の旅行時間変化を表示します。",
    TRANSIT: "GTFSの便・停留所・運行日を使う公共交通アクセシビリティ。現状は提供条件確認済みの外部入力待ちです。",
    TRAFFIC: "BPR静的配分とholdout検証の結果。県内詳細ODの公式入力が揃うまで、交通量は未計算です。",
    LOGISTICS: "貨物車、港湾、倉庫、工業地区の相対アクセシビリティ。企業在庫や完全なサプライチェーンは対象外です。",
    RELIEF: "備蓄・物資集積・防災拠点・避難所を結ぶ救援経路。公式位置入力が確認できるまで未計算です."
  };

  function get(id) { return document.getElementById(id); }
  function text(id, value) { get(id).textContent = value; }
  function formatNumber(value, digits) {
    if (value === null || value === undefined || !isFinite(Number(value))) return "—";
    return Number(value).toLocaleString("ja-JP", { maximumFractionDigits: digits || 0 });
  }
  function pct(value) { return isFinite(Number(value)) ? formatNumber(value, 1) + "%" : "—"; }

  function loadJson(name) {
    var primary = name === "network.geojson" ? "data/network.geojson.gz" : "data/" + name;
    return fetch(primary).then(function (response) {
      if (!response.ok) {
        if (name !== "network.geojson") throw new Error(name + " " + response.status);
        return fetch("data/network.geojson").then(function (fallback) {
          if (!fallback.ok) throw new Error(name + " " + fallback.status);
          return fallback.json();
        });
      }
      if (name !== "network.geojson") return response.json();
      if (!window.DecompressionStream) throw new Error("network.geojson.gz requires DecompressionStream");
      var compressed = response.body.pipeThrough(new DecompressionStream("gzip"));
      return new Response(compressed).json();
    });
  }

  function setError(error) {
    text("data-status", "公開成果物を読み込めません");
    get("data-status").className = "status status-warn";
    text("result-state", "エラー");
    get("result-state").className = "status status-warn";
    text("selection-note", "データ読み込みエラー: " + error.message + "。GitHub Pagesの相対パスと公開bundleを確認してください。");
  }

  function initializeMap() {
    if (!window.L) {
      get("map").innerHTML = '<div class="map-loading">地図ライブラリを読み込めません。公開成果物は下の指標と出典から確認できます。</div>';
      return;
    }
    state.map = L.map("map", { scrollWheelZoom: false }).setView([33.72, 132.8], 9);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "&copy; OpenStreetMap contributors"
    }).addTo(state.map);
    state.roadLayer = L.geoJSON(state.network, {
      style: function (feature) {
        var properties = feature.properties || {};
        var selected = state.selectedLink && properties.osm_way_id === state.selectedLink;
        return { color: selected ? "#ef4444" : (properties.highway === "trunk" ? "#175cd3" : "#4f86b9"), weight: selected ? 6 : 2, opacity: selected ? 1 : .62 };
      },
      onEachFeature: function (feature, layer) {
        layer.on({
          click: function () { selectLink(feature, layer); },
          mouseover: function () { layer.setStyle({ weight: 5 }); },
          mouseout: function () { state.roadLayer.resetStyle(layer); }
        });
        layer.bindTooltip((feature.properties.ref ? "国道・県道 " + feature.properties.ref + " " : "") + (feature.properties.name || "主要道路"));
      }
    }).addTo(state.map);
    state.populationLayer = L.geoJSON(state.population, {
      style: function () { return { color: "#f59e0b", weight: 1, fillColor: "#fbbf24", fillOpacity: .08 }; },
      onEachFeature: function (feature, layer) {
        var p = feature.properties || {};
        layer.bindTooltip((p.zone_id || "") + " / 2025人口 " + formatNumber(p.population_2025));
      }
    }).addTo(state.map);
    var bounds = state.roadLayer.getBounds();
    if (bounds.isValid()) state.map.fitBounds(bounds.pad(.05));
  }

  function selectLink(feature) {
    state.selectedFeature = feature;
    state.selectedLink = String((feature.properties || {}).osm_way_id || "");
    if (state.roadLayer) state.roadLayer.setStyle(function (item) {
      var selected = state.selectedLink && String((item.properties || {}).osm_way_id) === state.selectedLink;
      return { color: selected ? "#ef4444" : ((item.properties || {}).highway === "trunk" ? "#175cd3" : "#4f86b9"), weight: selected ? 6 : 2, opacity: selected ? 1 : .62 };
    });
    text("selection-note", "選択リンク: " + ((feature.properties || {}).ref || "道路") + " " + ((feature.properties || {}).name || "名称未確認") + "。これはD区分のユーザー仮定です。任意リンクの再計算結果は分析層で生成します。");
    text("result-state", "未計算");
    get("result-state").className = "status status-warn";
  }

  function renderMetrics(result) {
    var baseline = result.baseline || {};
    var after = result.after || {};
    var cards = [
      ["旅行時間増加ゾーン", formatNumber(after.zones_with_increased_travel_time), "C モデル推計"],
      ["旅行時間増加人口", formatNumber(after.population_with_increased_travel_time), "B人口 × Cネットワーク"],
      ["60分圏人口 Before", formatNumber(baseline.reachable_population_60min_before), "C 到達性"],
      ["60分圏人口 After", formatNumber(after.reachable_population_60min_after), "C 到達性"],
      ["Accessibility Loss", formatNumber(after.accessibility_loss_60min), "C 相対変化"],
      ["平均旅行時間差", formatNumber(after.average_travel_time_delta_minutes, 1) + " 分", "C 経路時間"]
    ];
    get("metric-grid").innerHTML = cards.map(function (card) {
      return '<div class="metric-card"><div class="metric-label">' + card[0] + '</div><div class="metric-value">' + card[1] + '</div><div class="metric-note">' + card[2] + '</div></div>';
    }).join("");
    var beforeValue = Number(baseline.reachable_population_60min_before || 0);
    var afterValue = Number(after.reachable_population_60min_after || 0);
    var maxValue = Math.max(beforeValue, afterValue, 1);
    get("before-bar").style.width = (beforeValue / maxValue * 100) + "%";
    get("after-bar").style.width = (afterValue / maxValue * 100) + "%";
    text("comparison-text", "60分圏人口: " + formatNumber(beforeValue) + " → " + formatNumber(afterValue) + "（" + formatNumber(after.accessibility_loss_60min) + "人の差、人口メッシュに基づく推計）");
    text("insight-title", result.link ? "影響リンク: " + (result.link.ref || "") + " " + (result.link.name || "名称未確認") : "選択シナリオの影響");
    text("insight-body", "選択リンク停止は、実被害の断定ではなく、指定ネットワーク条件でのC区分の比較です。");
  }

  function renderCritical(result) {
    var items = (result.critical_links || []).slice(0, 5);
    if (!items.length && result.link) items = [result.link];
    get("critical-list").innerHTML = items.map(function (item) {
      return "<li><button type=\"button\" data-link=\"" + (item.link_id || "") + "\">" + (item.ref || "道路") + " " + (item.name || "名称未確認") + "</button><br><span class=\"muted\">旅行時間増加人口 " + formatNumber(item.population_with_increased_travel_time) + "</span></li>";
    }).join("");
    Array.prototype.forEach.call(get("critical-list").querySelectorAll("button"), function (button) {
      button.addEventListener("click", function () {
        var found = state.network.features.find(function (feature) { return "osm-way-" + feature.properties.osm_way_id === button.dataset.link; });
        if (found) selectLink(found);
      });
    });
  }

  function renderProvenance(result) {
    var provenance = result.provenance || {};
    text("provenance", JSON.stringify({
      input_data_versions: provenance.input_data_versions || [],
      model_version: provenance.model_version || "not available",
      parameters: provenance.parameters || {},
      generated_at_utc: provenance.generated_at_utc || "not available",
      git_sha: provenance.git_sha || "not available",
      classification: result.classification || "C"
    }, null, 2));
    var limitations = (provenance.limitations || []).concat((state.manifest || {}).public_limitations || []);
    get("limitations").innerHTML = "<strong>Limitations</strong><ul>" + limitations.map(function (item) { return "<li>" + item + "</li>"; }).join("") + "</ul>";
  }

  function renderMode(mode) {
    state.mode = mode;
    Array.prototype.forEach.call(document.querySelectorAll(".mode-button"), function (button) {
      button.classList.toggle("active", button.dataset.mode === mode);
    });
    text("mode-summary", modeCopy[mode]);
    var data = state.metrics[mode.toLowerCase()] || {};
    if (data.status && data.status !== "computed") {
      text("result-state", "入力待ち");
      get("result-state").className = "status status-warn";
      text("insight-title", mode + " は未計算");
      text("insight-body", data.message || "必要な公開入力が未確認です。外部入力を追加してから再計算します。");
    } else {
      text("result-state", "計算済み");
      get("result-state").className = "status status-ok";
    }
  }

  function applyScenario(name) {
    state.scenario = name;
    var result = state.metrics;
    if (name !== "road56-stress-test") {
      text("scenario-description", "このレシピは、必要なGTFS・OD・施設入力が揃うまで未計算です。データ不存在とゼロ影響を混同しません。");
      text("result-state", "未計算");
      get("result-state").className = "status status-warn";
      text("comparison-text", "必要な入力データの状態を確認してください。");
      return;
    }
    text("scenario-description", "公開用に事前計算した道路Stress Testです。国道56号区間の完全停止をユーザー仮定として比較します。");
    renderMetrics(result);
    renderCritical(result);
    renderProvenance(result);
    renderMode(state.mode);
  }

  function recover() {
    state.selectedLink = null;
    if (state.roadLayer) state.roadLayer.setStyle(function (feature) {
      return { color: (feature.properties || {}).highway === "trunk" ? "#175cd3" : "#4f86b9", weight: 2, opacity: .62 };
    });
    text("selection-note", "復旧後：平常時ネットワークへ戻しました。Before / After比較のBeforeが復旧後状態です。");
    text("result-state", "復旧済み");
    get("result-state").className = "status status-ok";
  }

  function boot() {
    Promise.all([loadJson("network.geojson"), loadJson("population_zones.geojson"), loadJson("metrics.json"), loadJson("manifest.json")])
      .then(function (values) {
        state.network = values[0];
        state.population = values[1];
        state.metrics = values[2];
        state.manifest = values[3];
        text("data-status", "公開bundle読込済み");
        initializeMap();
        renderMetrics(state.metrics);
        renderCritical(state.metrics);
        renderProvenance(state.metrics);
        applyScenario("road56-stress-test");
      })
      .catch(setError);
    get("apply-scenario").addEventListener("click", function () { applyScenario(get("recipe").value); });
    get("recalculate").addEventListener("click", function () {
      text("result-state", "分析層で再計算");
      get("result-state").className = "status status-warn";
      text("selection-note", "最新データでの再計算を要求しました。GitHub Pagesでは重い計算を実行せず、分析層のresult_versionを待ちます。");
    });
    get("recover").addEventListener("click", recover);
    Array.prototype.forEach.call(document.querySelectorAll(".mode-button"), function (button) {
      button.addEventListener("click", function () { renderMode(button.dataset.mode); });
    });
  }

  document.addEventListener("DOMContentLoaded", boot);
}());
