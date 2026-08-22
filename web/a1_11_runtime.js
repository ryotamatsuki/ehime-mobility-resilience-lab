/* A1.11 full-day service criticality renderer. */
(function () {
  "use strict";

  function esc(value) {
    return String(value === null || value === undefined ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#039;");
  }
  function number(value, digits) {
    if (value === null || value === undefined || !isFinite(Number(value))) return "—";
    return Number(value).toLocaleString("ja-JP", { maximumFractionDigits: digits === undefined ? 0 : digits });
  }
  function material(item) {
    return !!(item && item.impact && (
      Number(item.impact.population_with_gt_1min_increase || 0) > 0 ||
      Number(item.impact.mean_minutes_change || 0) > 0 ||
      Number(item.impact.accessibility_loss_30min_population || 0) > 0 ||
      Number(item.impact.accessibility_loss_60min_population || 0) > 0
    ));
  }
  function serviceLabel(item, trip) {
    if (!item) return "影響なし";
    if (trip) return (item.route_name || item.route_id || "") + " / " + (item.first_departure || "") + (item.trip_headsign ? " → " + item.trip_headsign : "");
    return item.route_name || item.id || "";
  }
  function impactCell(item, maxAffected) {
    if (!material(item)) return '<span class="time-criticality-zero">0人相当</span>';
    var affected = Number(item.impact.population_with_gt_1min_increase || 0);
    var width = maxAffected > 0 ? Math.max(2, Math.min(100, affected / maxAffected * 100)) : 0;
    return '<strong>' + number(affected, 0) + '人相当</strong>' +
      '<small> / +' + number(item.impact.mean_minutes_change || 0, 3) + '分</small>' +
      '<div class="time-criticality-bar" aria-hidden="true"><i style="--impact-width:' + width.toFixed(1) + '%"></i></div>';
  }
  function render(payload) {
    var rows = payload.rows || [];
    var body = document.getElementById("time-criticality-body");
    if (!body) return;
    var allItems = [];
    rows.forEach(function (row) {
      if (row.top_route) allItems.push(row.top_route);
      if (row.top_trip) allItems.push(row.top_trip);
    });
    var maxAffected = allItems.reduce(function (max, item) {
      return Math.max(max, Number((item.impact || {}).population_with_gt_1min_increase || 0));
    }, 0);
    body.innerHTML = rows.map(function (row) {
      return '<tr>' +
        '<td class="time-criticality-time">' + esc(row.departure_time) + '</td>' +
        '<td class="time-criticality-service">' + esc(serviceLabel(row.top_route, false)) + '</td>' +
        '<td class="time-criticality-impact">' + impactCell(row.top_route, maxAffected) + '</td>' +
        '<td class="time-criticality-service">' + esc(serviceLabel(row.top_trip, true)) + '</td>' +
        '<td class="time-criticality-impact">' + impactCell(row.top_trip, maxAffected) + '</td>' +
        '<td>' + number(row.remaining_trip_count || 0, 0) + '</td>' +
        '</tr>';
    }).join("");

    var meta = payload.time_window || {};
    var peakRoute = meta.peak_route_event;
    var peakTrip = meta.peak_trip_event;
    var routeNode = document.getElementById("time-criticality-peak-route");
    var tripNode = document.getElementById("time-criticality-peak-trip");
    var changeNode = document.getElementById("time-criticality-changes");
    if (routeNode) routeNode.innerHTML = peakRoute ? '<strong>' + esc(peakRoute.departure_time) + ' / ' + esc(serviceLabel(peakRoute, false)) + '</strong><small>' + number(peakRoute.impact.population_with_gt_1min_increase, 0) + '人相当、+' + number(peakRoute.impact.mean_minutes_change, 3) + '分</small>' : '<strong>影響なし</strong>';
    if (tripNode) tripNode.innerHTML = peakTrip ? '<strong>' + esc(peakTrip.departure_time) + ' / ' + esc(serviceLabel(peakTrip, true)) + '</strong><small>' + number(peakTrip.impact.population_with_gt_1min_increase, 0) + '人相当、+' + number(peakTrip.impact.mean_minutes_change, 3) + '分</small>' : '<strong>影響なし</strong>';
    if (changeNode) changeNode.innerHTML = '<strong>路線 ' + number(meta.top_route_changes || 0, 0) + '回 / 便 ' + number(meta.top_trip_changes || 0, 0) + '回</strong><small>時間帯で「最重要」が入れ替わった回数</small>';
    document.body.dataset.uiStage = "A1.11";
  }

  document.addEventListener("DOMContentLoaded", function () {
    fetch("data/time_dependent_criticality.json")
      .then(function (response) { if (!response.ok) throw new Error("HTTP " + response.status); return response.json(); })
      .then(render)
      .catch(function (error) {
        var body = document.getElementById("time-criticality-body");
        if (body) body.innerHTML = '<tr><td colspan="6">A1.11データを読み込めません: ' + esc(error.message) + '</td></tr>';
      });
  });
}());
