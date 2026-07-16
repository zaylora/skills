const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const assetsDir = path.join(__dirname, "..", "assets");

function load(name, globals = {}) {
  const context = vm.createContext(globals);
  const source = fs.readFileSync(path.join(assetsDir, name), "utf8");
  vm.runInContext(source, context, { filename: name });
  return { api: context.StoryVideo, context };
}

function timeline() {
  const calls = [];
  const tl = { calls };
  for (const method of ["to", "fromTo", "set"]) {
    tl[method] = (...args) => {
      calls.push({ method, args });
      return tl;
    };
  }
  return tl;
}

function repeats(value, found = []) {
  if (!value || typeof value !== "object") return found;
  for (const [key, child] of Object.entries(value)) {
    if (key === "repeat") found.push(child);
    repeats(child, found);
  }
  return found;
}

function fakeMount() {
  return {
    children: [],
    lastElementChild: null,
    insertAdjacentHTML(position, markup) {
      assert.equal(position, "beforeend");
      const id = markup.match(/^<svg id="([^"]+)"/)[1];
      const svg = {
        id,
        markup,
        querySelectorAll(part) {
          return [{ owner: id, part }];
        },
      };
      this.children.push(svg);
      this.lastElementChild = svg;
    },
    querySelector(selector) {
      const id = selector.match(/id="([^"]+)"/);
      return id ? this.children.find((child) => child.id === id[1]) || null : null;
    },
  };
}

function actorSelector(part) {
  return { part };
}

function partOf(call) {
  return call.args[0] && call.args[0].part;
}

function varsOf(call) {
  return call.method === "fromTo" ? call.args[2] : call.args[1];
}

function hasCall(tl, part, property, predicate = () => true) {
  return tl.calls.some((call) => {
    const vars = varsOf(call) || {};
    return partOf(call) && partOf(call).includes(part) && property in vars && predicate(vars[property], vars);
  });
}

test("xiaohei front and side markup expose every named part and unique filters", () => {
  const { api } = load("xiaohei.js");
  const frontParts = ["xh-root", "xh-body", "xh-eye-l", "xh-eye-r", "xh-arm-l", "xh-arm-r", "xh-leg-l", "xh-leg-r"];
  const sideParts = ["xh-root", "xh-body", "xh-eye", "xh-arm-f", "xh-arm-b", "xh-leg-f", "xh-leg-b"];
  const frontA = api.xiaohei.frontMarkup("same id");
  const frontB = api.xiaohei.frontMarkup("same id");
  const side = api.xiaohei.sideMarkup("side");

  const rootA = frontA.match(/^<svg id="([^"]+)"/)[1];
  const rootB = frontB.match(/^<svg id="([^"]+)"/)[1];
  assert.match(rootA, /^same-id-/);
  assert.notEqual(rootA, rootB);
  for (const part of frontParts) assert.match(frontA, new RegExp(`class="[^"]*${part}`));
  for (const part of sideParts) assert.match(side, new RegExp(`class="[^"]*${part}`));

  const filterA = frontA.match(/<filter id="([^"]+)"/)[1];
  const filterB = frontB.match(/<filter id="([^"]+)"/)[1];
  assert.notEqual(filterA, filterB);
  assert.match(frontA, new RegExp(`filter="url\\(#${filterA}\\)"`));
});

test("xiaohei markup uses deterministic rough lines without drop shadows", () => {
  const { api } = load("xiaohei.js");
  const markups = [api.xiaohei.frontMarkup("rough"), api.xiaohei.sideMarkup("rough")];
  const filterIds = [];

  for (const markup of markups) {
    assert.doesNotMatch(markup, /feDropShadow|shadow/i);
    assert.match(markup, /<feTurbulence\b[^>]*seed="7"/);
    assert.match(markup, /<feDisplacementMap\b[^>]*scale="2\.2"/);
    const filterId = markup.match(/<filter id="([^"]+)"/)[1];
    assert.match(filterId, /-rough$/);
    filterIds.push(filterId);

    const limbWidths = Array.from(
      markup.matchAll(/<path class="xh-(?:arm|leg)-[^"]+"[^>]*stroke-width="([^"]+)"/g),
      (match) => match[1],
    );
    assert.equal(limbWidths.length, 4);
    assert.ok(limbWidths.every((width) => width === "2.2"));
  }

  assert.notEqual(filterIds[0], filterIds[1]);
});

test("xiaohei normalizes unsafe ids and spawn returns a scoped selector", () => {
  const mount = fakeMount();
  const document = { getElementById: (id) => (id === "mount" ? mount : null) };
  const { api } = load("xiaohei.js", { document });
  const unsafe = 'actor"><script>alert(1)</script>';
  const markup = api.xiaohei.frontMarkup(unsafe);

  assert.doesNotMatch(markup, /<script>/);
  assert.doesNotMatch(markup, /id="[^"]*[<>]/);

  const select = api.xiaohei.spawn("mount", unsafe);
  const selected = select(".xh-body")[0];
  assert.equal(selected.owner, mount.lastElementChild.id);
  assert.equal(selected.part, ".xh-body");
  assert.throws(() => api.xiaohei.spawn("missing"), /container/i);
});

test("xiaohei consecutive spawns with one base id remain instance-scoped", () => {
  const mount = fakeMount();
  const document = { getElementById: () => mount };
  const { api } = load("xiaohei.js", { document });

  const first = api.xiaohei.spawn("mount", "worker");
  const second = api.xiaohei.spawnSide("mount", "worker");
  assert.equal(mount.children.length, 2);
  assert.notEqual(mount.children[0].id, mount.children[1].id);
  assert.equal(first(".xh-body")[0].owner, mount.children[0].id);
  assert.equal(second(".xh-body")[0].owner, mount.children[1].id);
});

test("xiaohei prefers gsap selector scoped to the newly inserted svg", () => {
  const mount = fakeMount();
  const scopes = [];
  const gsap = { utils: { selector(scope) { scopes.push(scope); return (part) => ({ scope, part }); } } };
  const { api } = load("xiaohei.js", { document: { getElementById: () => mount }, gsap });

  const select = api.xiaohei.spawn("mount", "gsap-worker");
  assert.equal(scopes[0], mount.lastElementChild);
  assert.equal(select(".xh-eye").scope, mount.lastElementChild);
});

test("all microactions append synchronously to the supplied timeline", () => {
  const { api } = load("microactions.js");
  const actions = ["idle", "blink", "wave", "walkCycle", "nod", "jump", "think", "surprise"];

  for (const action of actions) {
    const tl = timeline();
    const returned = api.microactions[action](tl, actorSelector, {
      at: 1.25,
      duration: 2.4,
      direction: -1,
      distance: 60,
    });
    assert.equal(returned, tl, `${action} should return the supplied timeline`);
    assert.ok(tl.calls.length > 0, `${action} should append timeline calls`);
    assert.ok(tl.calls.every((call) => !String(call.args[0]).includes("actorSelector")), `${action} stringified actor`);
    assert.ok(tl.calls.every((call) => ["to", "fromTo", "set"].includes(call.method)));
    for (const repeat of repeats(tl.calls)) {
      assert.equal(Number.isFinite(repeat), true);
      assert.ok(repeat >= 0);
    }
  }
});

test("microactions target the required parts and visual properties", () => {
  const { api } = load("microactions.js");
  const expectations = {
    idle: [[".xh-body", "scaleY"], [".xh-eye", "scaleY"]],
    blink: [[".xh-eye", "scaleY"]],
    wave: [[".xh-arm-r", "rotation"]],
    walkCycle: [[".xh-leg-f", "rotation"], [".xh-leg-b", "rotation"], [".xh-arm-f", "rotation"], [".xh-arm-b", "rotation"], [".xh-root", "y"], [".xh-root", "x"]],
    nod: [[".xh-root", "y"], [".xh-body", "scaleY"]],
    jump: [[".xh-root", "y"], [".xh-body", "scaleY"]],
    think: [[".xh-arm-r", "rotation"], [".xh-body", "rotation"], [".xh-thought", "autoAlpha"]],
    surprise: [[".xh-eye", "scale"], [".xh-arm-l", "rotation"], [".xh-arm-r", "rotation"], [".xh-root", "y"]],
  };

  for (const [action, parts] of Object.entries(expectations)) {
    const tl = timeline();
    api.microactions[action](tl, actorSelector, { duration: 2, distance: 40 });
    for (const [part, property] of parts) {
      assert.ok(hasCall(tl, part, property), `${action} should animate ${part}.${property}`);
    }
  }
});

test("walk limbs are opposed and SVG joints use svgOrigin", () => {
  const { api } = load("microactions.js");
  const tl = timeline();
  api.microactions.walkCycle(tl, actorSelector, { duration: 2, direction: 1 });

  const frontLeg = tl.calls.find((call) => partOf(call) === ".xh-leg-f, .xh-leg-l");
  const backLeg = tl.calls.find((call) => partOf(call) === ".xh-leg-b, .xh-leg-r");
  assert.equal(frontLeg.method, "fromTo");
  assert.equal(backLeg.method, "fromTo");
  assert.equal(frontLeg.args[1].rotation, -backLeg.args[1].rotation);
  assert.ok(tl.calls.filter((call) => /arm|leg/.test(partOf(call) || "")).every((call) => varsOf(call).svgOrigin));
});

test("wave and walk fromTo tweens defer immediate rendering", () => {
  const { api } = load("microactions.js");
  for (const action of ["wave", "walkCycle"]) {
    const tl = timeline();
    api.microactions[action](tl, actorSelector, { at: 2, duration: 2.4 });
    const fromTos = tl.calls.filter((call) => call.method === "fromTo");
    assert.ok(fromTos.length > 0);
    assert.ok(fromTos.every((call) => call.args[2].immediateRender === false), `${action} immediateRender`);
  }
});

test("wave and walk reset neutral parts exactly at numeric and label ends", () => {
  const { api } = load("microactions.js");
  const cases = [
    { at: 2, duration: 2.4, end: 4.4 },
    { at: "scene", duration: 2.4, end: "scene+=2.4" },
  ];

  for (const item of cases) {
    const waveTl = timeline();
    api.microactions.wave(waveTl, actorSelector, item);
    const waveReset = waveTl.calls.find((call) => call.method === "set" && partOf(call) === ".xh-arm-r, .xh-arm-f");
    assert.equal(waveReset.args[1].rotation, 0);
    assert.equal(waveReset.args[2], item.end);

    const walkTl = timeline();
    api.microactions.walkCycle(walkTl, actorSelector, item);
    const expected = [
      [".xh-leg-f, .xh-leg-l", "rotation"],
      [".xh-leg-b, .xh-leg-r", "rotation"],
      [".xh-arm-f, .xh-arm-r", "rotation"],
      [".xh-arm-b, .xh-arm-l", "rotation"],
      [".xh-root", "y"],
    ];
    for (const [part, property] of expected) {
      const reset = walkTl.calls.find((call) => call.method === "set" && partOf(call) === part && property in call.args[1]);
      assert.equal(reset.args[1][property], 0, `${part}.${property}`);
      assert.equal(reset.args[2], item.end, `${part} end`);
    }
  }
});

test("default yoyo loops span the requested duration and return to start", () => {
  const { api } = load("microactions.js");
  for (const action of ["idle", "blink", "wave", "walkCycle"]) {
    const tl = timeline();
    const duration = 2.4;
    api.microactions[action](tl, actorSelector, { duration });
    const loops = tl.calls.filter((call) => varsOf(call) && varsOf(call).yoyo);
    assert.ok(loops.length > 0, `${action} should contain a yoyo loop`);
    for (const call of loops) {
      const vars = varsOf(call);
      assert.equal(vars.repeat % 2, 1, `${action} repeat should be odd`);
      assert.ok(Math.abs(vars.duration * (vars.repeat + 1) - duration) < 1e-9, `${action} span`);
    }
  }
});

test("jump offsets numeric and label positions without concatenation bugs", () => {
  const { api } = load("microactions.js");
  const labelTl = timeline();
  api.microactions.jump(labelTl, actorSelector, { at: "intro", duration: 1 });
  const positions = labelTl.calls.map((call) => call.args[call.args.length - 1]);
  assert.ok(positions.includes("intro"));
  assert.ok(positions.some((position) => /^intro\+=0\./.test(position)));
  assert.ok(positions.every((position) => !/^intro\d/.test(position)));

  const numericTl = timeline();
  api.microactions.jump(numericTl, actorSelector, { at: 3, duration: 1 });
  assert.ok(numericTl.calls.some((call) => call.args[call.args.length - 1] > 3));
});

test("microactions uses finite cycles, SVG origins, and walk dispatch", () => {
  const { api } = load("microactions.js");
  assert.equal(api.microactions.finiteRepeats(5, 2), 1);
  assert.equal(api.microactions.finiteRepeats(0.5, 2), 1);

  const tl = timeline();
  api.microactions.dispatch("walk", tl, "#actor", { duration: 3, distance: 80 });
  assert.ok(tl.calls.length > 0);
  assert.ok(tl.calls.some((call) => typeof call.args[0] === "string" && call.args[0].startsWith("#actor ")));
  assert.ok(tl.calls.some((call) => call.args.some((arg) => arg && arg.svgOrigin)));
  assert.throws(() => api.microactions.dispatch("dance", tl, "#actor"), /Unknown action: dance/);
});

test("story-video assets contain no nondeterministic or asynchronous constructs", () => {
  for (const name of ["handdraw.js", "xiaohei.js", "microactions.js", "props.js"]) {
    const source = fs.readFileSync(path.join(assetsDir, name), "utf8");
    assert.doesNotMatch(source, /Math\.random|Date\.now|repeat\s*:\s*-1|setTimeout|\bPromise\b|\basync\b/, name);
  }
});
