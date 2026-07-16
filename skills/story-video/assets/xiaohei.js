(function () {
  "use strict";

  globalThis.StoryVideo = globalThis.StoryVideo || {};
  var instanceCount = 0;

  function safeId(value) {
    var normalized = String(value === undefined ? "xiaohei" : value)
      .replace(/[^A-Za-z0-9_-]+/g, "-")
      .replace(/^-+|-+$/g, "");
    if (!normalized) normalized = "xiaohei";
    if (!/^[A-Za-z_]/.test(normalized)) normalized = "xh-" + normalized;
    return normalized;
  }

  function identity(id, view) {
    instanceCount += 1;
    var rootId = safeId(id) + "-" + instanceCount;
    return {
      rootId: rootId,
      filterId: rootId + "-" + view + "-rough",
    };
  }

  function roughFilter(id) {
    return '<filter id="' + id + '" x="-30%" y="-30%" width="160%" height="160%">' +
      '<feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves="2" seed="7" result="noise"/>' +
      '<feDisplacementMap in="SourceGraphic" in2="noise" scale="2.2"/>' +
      '</filter>';
  }

  function frontMarkup(id) {
    var ids = identity(id, "front");
    return '<svg id="' + ids.rootId + '" class="xh-front" viewBox="0 0 120 180" xmlns="http://www.w3.org/2000/svg" role="img">' +
      '<defs>' + roughFilter(ids.filterId) + '</defs>' +
      '<g class="xh-root" filter="url(#' + ids.filterId + ')">' +
      '<path class="xh-leg-l" d="M48 129 L43 164" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>' +
      '<path class="xh-leg-r" d="M72 129 L77 164" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>' +
      '<path class="xh-arm-l" d="M40 77 L22 119" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>' +
      '<path class="xh-arm-r" d="M80 77 L98 119" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>' +
      '<path class="xh-body" d="M38 67 Q60 51 82 67 L78 130 Q60 142 42 130 Z" fill="currentColor"/>' +
      '<circle class="xh-eye-l" cx="52" cy="84" r="4" fill="white"/>' +
      '<circle class="xh-eye-r" cx="68" cy="84" r="4" fill="white"/>' +
      '<text class="xh-thought" x="92" y="48" opacity="0">?</text>' +
      '</g></svg>';
  }

  function sideMarkup(id) {
    var ids = identity(id, "side");
    return '<svg id="' + ids.rootId + '" class="xh-side" viewBox="0 0 120 180" xmlns="http://www.w3.org/2000/svg" role="img">' +
      '<defs>' + roughFilter(ids.filterId) + '</defs>' +
      '<g class="xh-root" filter="url(#' + ids.filterId + ')">' +
      '<path class="xh-leg-b" d="M58 129 L46 164" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>' +
      '<path class="xh-leg-f" d="M68 129 L82 161" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>' +
      '<path class="xh-arm-b" d="M51 78 L35 119" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>' +
      '<path class="xh-arm-f" d="M70 78 L91 112" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>' +
      '<path class="xh-body" d="M43 67 Q65 51 79 69 L77 130 Q60 142 45 130 Z" fill="currentColor"/>' +
      '<circle class="xh-eye" cx="70" cy="83" r="4" fill="white"/>' +
      '<text class="xh-thought" x="92" y="48" opacity="0">?</text>' +
      '</g></svg>';
  }

  function resolveContainer(containerOrId) {
    var container = typeof containerOrId === "string"
      ? globalThis.document && globalThis.document.getElementById(containerOrId)
      : containerOrId;
    if (!container || typeof container.querySelector !== "function") {
      throw new Error("Xiaohei container was not found");
    }
    return container;
  }

  function inject(containerOrId, id, markupFactory) {
    var container = resolveContainer(containerOrId);
    var markup = markupFactory(id);
    var rootId = markup.match(/^<svg id="([^"]+)"/)[1];
    if (typeof container.insertAdjacentHTML === "function") {
      container.insertAdjacentHTML("beforeend", markup);
    } else {
      container.innerHTML = (container.innerHTML || "") + markup;
    }
    var svg = container.lastElementChild || container.querySelector('svg[id="' + rootId + '"]');
    if (!svg || typeof svg.querySelectorAll !== "function") throw new Error("Xiaohei SVG could not be inserted");
    if (globalThis.gsap && globalThis.gsap.utils && typeof globalThis.gsap.utils.selector === "function") {
      return globalThis.gsap.utils.selector(svg);
    }
    return function (selector) { return svg.querySelectorAll(selector); };
  }

  globalThis.StoryVideo.xiaohei = Object.freeze({
    frontMarkup: frontMarkup,
    sideMarkup: sideMarkup,
    spawn: function (containerOrId, id) {
      return inject(containerOrId, id, frontMarkup);
    },
    spawnSide: function (containerOrId, id) {
      return inject(containerOrId, id, sideMarkup);
    },
  });
}());
