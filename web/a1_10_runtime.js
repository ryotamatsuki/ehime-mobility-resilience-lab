/* A1.10 generated-site UI enhancer.
   CSS/runtime contract: destination-synchronized-metrics and destination-synchronized-charts.
   No routing or accessibility values are computed here. */
(function () {
  "use strict";

  var LABELS = {
    hospital: "病院",
    emergency: "指定緊急避難場所",
    general: "指定一般避難所",
    welfare: "指定福祉避難所"
  };

  function applyDestinationState(key) {
    if (!Object.prototype.hasOwnProperty.call(LABELS, key)) key = "hospital";
    document.body.dataset.destination = key;
    var selector = document.getElementById("destination-selector");
    if (selector) selector.dataset.a110Ready = "true";
    Array.prototype.forEach.call(document.querySelectorAll(".destination-choice"), function (label) {
      var input = label.querySelector('input[name="destination"]');
      if (!input) return;
      if (input.value === key && input.checked) label.setAttribute("aria-current", "true");
      else label.removeAttribute("aria-current");
    });
    var map = document.getElementById("map");
    if (map) map.setAttribute("aria-label", "大洲市交通レジリエンス分析地図：目的地 " + LABELS[key]);
  }

  function syncFromDom() {
    var checked = document.querySelector('input[name="destination"]:checked');
    applyDestinationState(checked ? checked.value : "hospital");
  }

  document.addEventListener("change", function (event) {
    var target = event.target;
    if (target && target.matches && target.matches('input[name="destination"]')) {
      window.setTimeout(syncFromDom, 0);
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    document.body.dataset.uiStage = "A1.10";
    syncFromDom();
    var observer = new MutationObserver(function () {
      if (document.getElementById("destination-selector")) syncFromDom();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  });
}());
