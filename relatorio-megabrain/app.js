(function () {
  "use strict";

  var buttons = Array.prototype.slice.call(document.querySelectorAll("[data-panel-target]"));
  var panels = Array.prototype.slice.call(document.querySelectorAll("[data-panel]"));

  function panelName() {
    var requested = window.location.hash.replace(/^#\/?/, "");
    return panels.some(function (panel) { return panel.dataset.panel === requested; }) ? requested : "comecar";
  }

  function show(name, updateHash) {
    panels.forEach(function (panel) { panel.hidden = panel.dataset.panel !== name; });
    buttons.forEach(function (button) {
      button.setAttribute("aria-selected", String(button.dataset.panelTarget === name));
    });
    if (updateHash) window.history.replaceState(null, "", "#/" + name);
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  buttons.forEach(function (button) {
    button.addEventListener("click", function () { show(button.dataset.panelTarget, true); });
  });
  window.addEventListener("hashchange", function () { show(panelName(), false); });
  show(panelName(), false);
}());
