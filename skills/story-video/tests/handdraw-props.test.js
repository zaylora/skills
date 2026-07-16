const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const assetsDir = path.join(__dirname, "..", "assets");

function load(...names) {
  const context = vm.createContext({});
  for (const name of names) {
    const source = fs.readFileSync(path.join(assetsDir, name), "utf8");
    vm.runInContext(source, context, { filename: name });
  }
  return context.StoryVideo;
}

test("handdraw paths are stable for a seed and independent of call order", () => {
  const { handdraw } = load("handdraw.js");
  const opts = { seed: "stable", roughness: 1.4 };

  const first = handdraw.hLine(2, 4, 80, 42, opts);
  handdraw.hEllipse(20, 20, 12, 8, { seed: "unrelated" });
  const second = handdraw.hLine(2, 4, 80, 42, opts);

  assert.equal(first, second);
  assert.notEqual(first, handdraw.hLine(2, 4, 80, 42, { ...opts, seed: "other" }));
  assert.match(handdraw.hPoly([[0, 0], [12, 4], [4, 16]], opts), /^M/);
  assert.match(handdraw.hEllipse(20, 20, 12, 8, opts), /^M/);
});

test("handdraw handles zero-length lines without invalid numbers", () => {
  const { handdraw } = load("handdraw.js");
  const result = handdraw.hLine(5, 5, 5, 5, { seed: 7 });

  assert.match(result, /^M/);
  assert.doesNotMatch(result, /NaN|Infinity/);
});

test("handdraw rejects non-finite coordinates and survives finite overflow deltas", () => {
  const { handdraw } = load("handdraw.js");

  assert.throws(() => handdraw.hLine(0, 0, Infinity, 1), /finite/i);
  assert.throws(() => handdraw.hEllipse(0, NaN, 4, 4), /finite/i);
  assert.throws(() => handdraw.hPoly([[0, 0], [1, -Infinity]]), /finite/i);

  const extreme = handdraw.hLine(-Number.MAX_VALUE, 0, Number.MAX_VALUE, 1, { seed: "extreme" });
  assert.doesNotMatch(extreme, /NaN|Infinity/);
});

test("handdraw zero-radius ellipses are stable and normal ellipses stay slightly open", () => {
  const { handdraw } = load("handdraw.js");
  const point = handdraw.hEllipse(12, 14, 0, 8, { seed: "flat" });
  const ellipse = handdraw.hEllipse(20, 20, 12, 8, { seed: "open" });

  assert.equal(point, handdraw.hEllipse(12, 14, 0, 8, { seed: "flat" }));
  assert.match(point, /^M/);
  assert.doesNotMatch(point, /NaN|Infinity/);
  assert.doesNotMatch(ellipse, /Z\s*$/);
});

test("props exposes the exact frozen 32-item catalog", () => {
  const { props } = load("handdraw.js", "props.js");
  const expected = [
    "laptop", "coffee", "docs", "calendar", "phone", "printer", "badge", "chair",
    "conveyor", "funnel", "scale", "gate", "blackbox", "ladder", "pipe", "mailbox",
    "idea", "question", "excl", "sweat", "anger", "zzz", "boom", "up",
    "arrow", "fork", "loop", "check", "cross", "balance", "gear", "network",
  ];

  assert.deepEqual(Array.from(props.IDS), expected);
  assert.equal(Object.isFrozen(props.IDS), true);
  assert.deepEqual(Array.from(props.list()), expected);
});

test("every prop renders deterministic complete SVG with a handdraw path", () => {
  const { props } = load("handdraw.js", "props.js");
  const baseline = new Map(props.IDS.map((id) => [id, props.render(id, { seed: "catalog" })]));

  for (const id of [...props.IDS].reverse()) {
    const svg = props.render(id, { seed: "catalog" });
    assert.equal(svg, baseline.get(id));
    assert.match(svg, new RegExp(`^<svg[^>]*data-prop-id="${id}"[^>]*viewBox="[^"]+"`));
    assert.match(svg, /<path\b[^>]*d="M/);
    assert.match(svg, /<\/svg>$/);
  }
});

test("props have highly diverse path structures rather than seeded variants", () => {
  const { props } = load("handdraw.js", "props.js");
  const signatures = new Set(props.IDS.map((id) => {
    const svg = props.render(id, { seed: "structure" });
    const paths = Array.from(svg.matchAll(/<path\b[^>]*d="([^"]+)"/g), (match) => match[1]);
    return paths.map((d) => (d.match(/[A-Za-z]/g) || []).join("")).join("|");
  }));

  assert.ok(signatures.size >= 24, `expected at least 24 structural signatures, got ${signatures.size}`);
});

test("representative props expose recognizable named parts", () => {
  const { props } = load("handdraw.js", "props.js");
  const expectedParts = {
    laptop: ["screen", "base"],
    coffee: ["cup", "handle", "steam"],
    conveyor: ["belt", "roller", "item"],
    funnel: ["bowl", "stem"],
    idea: ["bulb", "base", "ray"],
    question: ["hook", "dot"],
    arrow: ["shaft", "head"],
    gear: ["outer", "hub", "tooth"],
  };

  for (const [id, parts] of Object.entries(expectedParts)) {
    const svg = props.render(id);
    for (const part of parts) assert.match(svg, new RegExp(`data-part="${part}(?:-|\")`), `${id}.${part}`);
  }
});

test("props rejects unknown ids clearly", () => {
  const { props } = load("handdraw.js", "props.js");
  assert.throws(() => props.render("missing"), /Unknown prop id: missing/);
});
