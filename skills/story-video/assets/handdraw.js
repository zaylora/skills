(function () {
  "use strict";

  globalThis.StoryVideo = globalThis.StoryVideo || {};
  var MAX_COORD = 1e150;

  function coordinate(value, name) {
    var number = Number(value);
    if (!Number.isFinite(number)) throw new TypeError(name + " must be finite");
    return Math.max(-MAX_COORD, Math.min(MAX_COORD, number));
  }

  function hash(value) {
    var result = 2166136261;
    for (var i = 0; i < value.length; i += 1) {
      result ^= value.charCodeAt(i);
      result = Math.imul(result, 16777619);
    }
    return result >>> 0;
  }

  function seeded(seed) {
    var state = seed >>> 0;
    return function () {
      state += 0x6d2b79f5;
      var value = state;
      value = Math.imul(value ^ (value >>> 15), value | 1);
      value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
      return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
    };
  }

  function formatter(value) {
    var rounded = Math.round(value * 100) / 100;
    return String(Object.is(rounded, -0) ? 0 : rounded);
  }

  function randomFor(kind, values, opts) {
    var seed = opts && opts.seed !== undefined ? opts.seed : "story-video";
    return seeded(hash(kind + "|" + String(seed) + "|" + values.join(",")));
  }

  function hLine(x1, y1, x2, y2, opts) {
    x1 = coordinate(x1, "x1");
    y1 = coordinate(y1, "y1");
    x2 = coordinate(x2, "x2");
    y2 = coordinate(y2, "y2");
    var values = [x1, y1, x2, y2];
    var random = randomFor("line", values, opts);
    var roughness = opts && Number.isFinite(opts.roughness) ? opts.roughness : 1;
    var dx = x2 - x1;
    var dy = y2 - y1;
    var length = Math.hypot(dx, dy);

    if (length === 0) {
      return "M" + formatter(x1) + " " + formatter(y1) + " C" +
        formatter(x1) + " " + formatter(y1) + " " +
        formatter(x2) + " " + formatter(y2) + " " +
        formatter(x2) + " " + formatter(y2);
    }

    var nx = -dy / length;
    var ny = dx / length;
    var bend1 = (random() - 0.5) * 2 * roughness;
    var bend2 = (random() - 0.5) * 2 * roughness;
    var c1x = x1 + dx / 3 + nx * bend1;
    var c1y = y1 + dy / 3 + ny * bend1;
    var c2x = x1 + dx * 2 / 3 + nx * bend2;
    var c2y = y1 + dy * 2 / 3 + ny * bend2;

    return "M" + formatter(x1) + " " + formatter(y1) + " C" +
      formatter(c1x) + " " + formatter(c1y) + " " +
      formatter(c2x) + " " + formatter(c2y) + " " +
      formatter(x2) + " " + formatter(y2);
  }

  function hPoly(points, opts) {
    if (!points || points.length === 0) return "";
    points = points.map(function (point, index) {
      if (!point || point.length < 2) throw new TypeError("point " + index + " must contain finite x and y");
      return [coordinate(point[0], "point x"), coordinate(point[1], "point y")];
    });
    if (points.length === 1) {
      return hLine(points[0][0], points[0][1], points[0][0], points[0][1], opts);
    }

    var paths = [];
    var closed = !opts || opts.closed !== false;
    var segmentCount = closed ? points.length : points.length - 1;
    for (var i = 0; i < segmentCount; i += 1) {
      var from = points[i];
      var to = points[(i + 1) % points.length];
      var segmentOpts = Object.assign({}, opts, {
        seed: String(opts && opts.seed !== undefined ? opts.seed : "story-video") + ":poly:" + i,
      });
      paths.push(hLine(from[0], from[1], to[0], to[1], segmentOpts));
    }
    return paths.join(" ") + (closed ? " Z" : "");
  }

  function hEllipse(cx, cy, rx, ry, opts) {
    cx = coordinate(cx, "cx");
    cy = coordinate(cy, "cy");
    rx = Math.abs(coordinate(rx, "rx"));
    ry = Math.abs(coordinate(ry, "ry"));
    if (rx === 0 || ry === 0) return "M" + formatter(cx) + " " + formatter(cy);
    var random = randomFor("ellipse", [cx, cy, rx, ry], opts);
    var roughness = opts && Number.isFinite(opts.roughness) ? opts.roughness : 1;
    var points = [];
    var count = 14;
    var start = random() * 0.16;

    for (var i = 0; i <= count + 1; i += 1) {
      var angle = start + Math.PI * 2 * i / count;
      var jitter = (random() - 0.5) * roughness;
      points.push([
        cx + Math.cos(angle) * (rx + jitter),
        cy + Math.sin(angle) * (ry + jitter),
      ]);
    }

    return points.map(function (point, index) {
      return (index === 0 ? "M" : "L") + formatter(point[0]) + " " + formatter(point[1]);
    }).join(" ");
  }

  globalThis.StoryVideo.handdraw = Object.freeze({
    DEFAULT_STROKE_WIDTH: 2.2,
    hLine: hLine,
    hPoly: hPoly,
    hEllipse: hEllipse,
  });
}());
