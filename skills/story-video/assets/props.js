(function () {
  "use strict";

  globalThis.StoryVideo = globalThis.StoryVideo || {};
  var handdraw = globalThis.StoryVideo.handdraw;
  if (!handdraw) throw new Error("StoryVideo.handdraw must be loaded before props.js");

  var IDS = Object.freeze([
    "laptop", "coffee", "docs", "calendar", "phone", "printer", "badge", "chair",
    "conveyor", "funnel", "scale", "gate", "blackbox", "ladder", "pipe", "mailbox",
    "idea", "question", "excl", "sweat", "anger", "zzz", "boom", "up",
    "arrow", "fork", "loop", "check", "cross", "balance", "gear", "network",
  ]);

  var CATEGORY = Object.freeze(IDS.reduce(function (result, id, index) {
    result[id] = index < 8 ? "office" : index < 16 ? "process" : index < 24 ? "reaction" : "symbol";
    return result;
  }, {}));

  function builder(seed) {
    var index = 0;
    function options(part, extra) {
      return Object.assign({ seed: seed + ":" + part + ":" + index++, roughness: 0.9 }, extra);
    }
    return {
      line: function (part, x1, y1, x2, y2) {
        return { part: part, d: handdraw.hLine(x1, y1, x2, y2, options(part)) };
      },
      poly: function (part, points, closed) {
        return { part: part, d: handdraw.hPoly(points, options(part, { closed: closed !== false })) };
      },
      ellipse: function (part, cx, cy, rx, ry) {
        return { part: part, d: handdraw.hEllipse(cx, cy, rx, ry, options(part)) };
      },
    };
  }

  var RECIPES = {
    laptop: function (b) { return [b.poly("base", [[18, 64], [82, 64], [88, 70], [12, 70]]), b.poly("screen", [[24, 30], [76, 30], [76, 64], [24, 64]]), b.line("screen-line-1", 30, 38, 58, 38), b.line("screen-line-2", 30, 46, 66, 46), b.line("screen-line-3", 30, 54, 50, 54)]; },
    coffee: function (b) { return [b.poly("cup", [[26, 40], [30, 80], [64, 80], [68, 40]]), b.ellipse("rim", 47, 40, 21, 5), b.poly("handle", [[68, 48], [82, 50], [80, 66], [68, 64]], false), b.line("steam-1", 36, 24, 34, 16), b.line("steam-2", 47, 24, 45, 14), b.line("steam-3", 58, 24, 56, 16)]; },
    docs: function (b) { return [b.poly("stack-bottom", [[20, 74], [80, 74], [76, 84], [24, 84]]), b.poly("stack-middle", [[24, 60], [78, 58], [76, 74], [22, 72]]), b.poly("stack-top", [[28, 44], [74, 46], [76, 60], [26, 58]]), b.line("text", 34, 52, 60, 53)]; },
    calendar: function (b) { return [b.poly("page", [[22, 30], [78, 30], [78, 80], [22, 80]]), b.line("divider", 22, 44, 78, 44), b.line("ring-left", 38, 22, 38, 36), b.line("ring-right", 62, 22, 62, 36), b.poly("check", [[40, 58], [46, 64], [60, 50]], false)]; },
    phone: function (b) { return [b.ellipse("dial", 50, 50, 30, 30), b.ellipse("center", 50, 50, 12, 12), b.line("tick-top", 50, 20, 50, 10), b.line("tick-right", 72, 32, 80, 26), b.line("tick-left", 28, 32, 20, 26)]; },
    printer: function (b) { return [b.poly("body", [[22, 44], [78, 44], [78, 68], [22, 68]]), b.poly("paper-in", [[34, 30], [66, 30], [66, 44], [34, 44]]), b.poly("paper-out", [[34, 68], [66, 68], [66, 82], [34, 82]]), b.ellipse("status", 70, 52, 2.5, 2.5)]; },
    badge: function (b) { return [b.line("lanyard", 50, 12, 50, 30), b.poly("card", [[30, 30], [70, 30], [70, 84], [30, 84]]), b.ellipse("photo", 50, 44, 7, 7), b.line("name-1", 38, 60, 62, 60), b.line("name-2", 38, 70, 56, 70)]; },
    chair: function (b) { return [b.poly("back", [[34, 24], [62, 24], [60, 52], [36, 52]]), b.poly("seat", [[30, 52], [66, 52], [66, 60], [30, 60]]), b.line("leg-left", 36, 60, 32, 84), b.line("leg-right", 60, 60, 64, 84), b.line("leg-center", 48, 60, 48, 84)]; },
    conveyor: function (b) { return [b.ellipse("roller-left", 24, 56, 12, 12), b.ellipse("roller-right", 76, 56, 12, 12), b.line("belt-top", 24, 44, 76, 44), b.line("belt", 24, 68, 76, 68), b.poly("item", [[40, 30], [52, 30], [52, 44], [40, 44]])]; },
    funnel: function (b) { return [b.poly("bowl", [[18, 26], [82, 26], [56, 60], [56, 82], [44, 82], [44, 60]]), b.line("stem", 44, 60, 56, 60), b.line("filter-line", 30, 40, 70, 40)]; },
    scale: function (b) { return [b.line("stand", 50, 16, 50, 60), b.line("beam", 24, 30, 76, 30), b.poly("pan-left", [[24, 30], [14, 50], [34, 50]]), b.poly("pan-right", [[76, 30], [66, 50], [86, 50]]), b.poly("base", [[38, 60], [62, 60], [60, 68], [40, 68]])]; },
    gate: function (b) { return [b.line("post-left", 20, 84, 20, 30), b.line("post-right", 80, 84, 80, 30), b.line("header", 16, 30, 84, 30), b.poly("sign", [[30, 44], [70, 44], [70, 72], [30, 72]]), b.line("bar", 30, 58, 70, 58)]; },
    blackbox: function (b) { return [b.poly("box", [[24, 32], [76, 32], [76, 76], [24, 76]]), b.poly("mystery", [[38, 50], [44, 43], [50, 50], [56, 57], [62, 50]], false), b.ellipse("dot", 50, 64, 2, 2)]; },
    ladder: function (b) { return [b.line("rail-left", 34, 14, 28, 86), b.line("rail-right", 64, 14, 70, 86), b.line("rung-1", 31, 30, 67, 30), b.line("rung-2", 30, 46, 68, 46), b.line("rung-3", 30, 62, 69, 62), b.line("rung-4", 31, 78, 70, 78)]; },
    pipe: function (b) { return [b.poly("main", [[14, 36], [50, 36], [50, 72], [86, 72]], false), b.poly("branch", [[14, 52], [36, 52], [36, 86]], false), b.ellipse("outlet", 86, 72, 3, 3)]; },
    mailbox: function (b) { return [b.poly("box", [[28, 40], [72, 40], [72, 80], [28, 80]]), b.ellipse("top", 50, 40, 22, 10), b.line("flag", 50, 20, 50, 40), b.line("slot", 38, 52, 62, 52)]; },
    idea: function (b) { return [b.ellipse("bulb", 50, 40, 22, 22), b.line("base-1", 40, 58, 60, 58), b.line("base-2", 43, 66, 57, 66), b.line("base-3", 45, 74, 55, 74), b.line("ray-top", 50, 10, 50, 2), b.line("ray-left", 22, 20, 16, 14), b.line("ray-right", 78, 20, 84, 14)]; },
    question: function (b) { return [b.poly("hook", [[34, 36], [36, 22], [52, 18], [70, 26], [72, 40], [64, 51], [52, 56], [52, 66]], false), b.ellipse("dot", 52, 80, 2.6, 2.6)]; },
    excl: function (b) { return [b.line("stroke", 50, 16, 50, 60), b.ellipse("dot", 50, 76, 3, 3)]; },
    sweat: function (b) { return [b.poly("drop", [[50, 22], [40, 46], [32, 60], [36, 78], [50, 86], [64, 78], [68, 60], [60, 44]]), b.line("highlight", 44, 58, 42, 70)]; },
    anger: function (b) { return [b.poly("vein-left", [[24, 30], [32, 42], [26, 44]], false), b.poly("vein-center", [[44, 24], [50, 44], [42, 44]], false), b.poly("vein-right", [[68, 30], [60, 42], [68, 46]], false)]; },
    zzz: function (b) { return [b.poly("z-large", [[30, 58], [46, 58], [30, 74], [46, 74]], false), b.poly("z-small", [[54, 40], [68, 40], [54, 54], [68, 54]], false)]; },
    boom: function (b) { return [b.poly("burst", [[50, 10], [58, 30], [80, 24], [66, 42], [86, 54], [62, 54], [68, 78], [50, 62], [32, 78], [38, 54], [14, 54], [34, 42], [20, 24], [42, 30]]), b.line("center", 46, 46, 52, 46)]; },
    up: function (b) { return [b.line("shaft", 50, 82, 50, 20), b.poly("head", [[34, 36], [50, 20], [66, 36]], false)]; },
    arrow: function (b) { return [b.line("shaft", 12, 30, 100, 30), b.poly("head", [[82, 14], [104, 30], [82, 46]], false)]; },
    fork: function (b) { return [b.line("stem", 50, 84, 50, 52), b.line("branch-left", 50, 52, 26, 22), b.line("branch-right", 50, 52, 74, 22)]; },
    loop: function (b) { return [b.ellipse("loop", 50, 50, 30, 28), b.poly("head", [[62, 32], [80, 36], [76, 54]], false)]; },
    check: function (b) { return [b.poly("mark", [[18, 52], [42, 76], [84, 24]], false)]; },
    cross: function (b) { return [b.line("stroke-1", 26, 26, 74, 74), b.line("stroke-2", 74, 26, 26, 74)]; },
    balance: function (b) { return [b.line("stand", 50, 14, 50, 64), b.line("beam", 22, 30, 78, 30), b.ellipse("pan-left", 22, 40, 10, 4), b.ellipse("pan-right", 78, 40, 10, 4), b.poly("base", [[38, 64], [62, 64], [60, 70], [40, 70]])]; },
    gear: function (b) { return [b.ellipse("outer", 50, 50, 16, 16), b.ellipse("hub", 50, 50, 6, 6), b.line("tooth-top", 50, 30, 50, 22), b.line("tooth-bottom", 50, 70, 50, 78), b.line("tooth-left", 30, 50, 22, 50), b.line("tooth-right", 70, 50, 78, 50)]; },
    network: function (b) { return [b.ellipse("node-left", 24, 28, 7, 7), b.ellipse("node-right", 76, 28, 7, 7), b.ellipse("node-bottom", 50, 74, 7, 7), b.line("edge-left", 28, 33, 46, 68), b.line("edge-right", 72, 33, 54, 68), b.line("edge-top", 31, 28, 69, 28)]; },
  };

  function pathMarkup(path) {
    return '<path data-part="' + path.part + '" d="' + path.d + '"/>';
  }

  function render(id, opts) {
    if (!Object.prototype.hasOwnProperty.call(RECIPES, id)) throw new Error("Unknown prop id: " + id);
    var seed = String(opts && opts.seed !== undefined ? opts.seed : "story-video") + ":" + id;
    var paths = RECIPES[id](builder(seed));
    var viewBox = id === "arrow" ? "0 0 120 60" : "0 0 100 100";
    return '<svg data-prop-id="' + id + '" viewBox="' + viewBox + '" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">' +
      paths.map(pathMarkup).join("") + '</svg>';
  }

  globalThis.StoryVideo.props = Object.freeze({
    IDS: IDS,
    CATEGORY: CATEGORY,
    list: function () { return IDS.slice(); },
    render: render,
  });
}());
