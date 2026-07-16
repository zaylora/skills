(function () {
  "use strict";

  globalThis.StoryVideo = globalThis.StoryVideo || {};

  function yoyoCycle(duration, desiredHalfCycle) {
    var total = Number(duration);
    var desired = Number(desiredHalfCycle);
    if (!Number.isFinite(total) || !Number.isFinite(desired) || total <= 0 || desired <= 0) {
      return { duration: 0, repeat: 1 };
    }
    var halfCycles = Math.max(2, Math.floor(total / desired));
    if (halfCycles % 2 === 1) halfCycles -= 1;
    return { duration: total / halfCycles, repeat: halfCycles - 1 };
  }

  function finiteRepeats(duration, cycle) {
    return yoyoCycle(duration, cycle).repeat;
  }

  function values(opts, defaultDuration) {
    var input = opts || {};
    return {
      at: input.at === undefined ? 0 : input.at,
      duration: Number.isFinite(input.duration) && input.duration > 0 ? input.duration : defaultDuration,
      distance: Number.isFinite(input.distance) ? input.distance : 24,
      direction: input.direction === "left" || Number(input.direction) < 0 ? -1 : 1,
    };
  }

  function targets(actor, part) {
    return typeof actor === "function" ? actor(part) : actor + " " + part;
  }

  function position(at, delta) {
    if (!delta) return at;
    if (typeof at === "number") return at + delta;
    var amount = Math.round(Math.abs(delta) * 1000) / 1000;
    return at + (delta < 0 ? "-=" : "+=") + amount;
  }

  function idle(tl, actor, opts) {
    var value = values(opts, 2);
    var breath = yoyoCycle(value.duration, 0.8);
    var blinkHalf = Math.min(0.08, value.duration * 0.05);
    var blinkAt = value.duration * 0.55;
    tl.to(targets(actor, ".xh-body"), {
      scaleY: 1.04,
      scaleX: 0.985,
      svgOrigin: "60 130",
      duration: breath.duration,
      ease: "sine.inOut",
      yoyo: true,
      repeat: breath.repeat,
    }, value.at);
    tl.fromTo(targets(actor, ".xh-eye-l, .xh-eye-r, .xh-eye"), { scaleY: 1 }, {
      scaleY: 0.1,
      svgOrigin: "60 84",
      duration: blinkHalf,
      ease: "power2.in",
    }, position(value.at, blinkAt));
    tl.to(targets(actor, ".xh-eye-l, .xh-eye-r, .xh-eye"), {
      scaleY: 1,
      svgOrigin: "60 84",
      duration: blinkHalf,
      ease: "power2.out",
    }, position(value.at, blinkAt + blinkHalf));
    return tl;
  }

  function blink(tl, actor, opts) {
    var value = values(opts, 0.24);
    var blinkCycle = yoyoCycle(value.duration, 0.08);
    tl.to(targets(actor, ".xh-eye-l, .xh-eye-r, .xh-eye"), {
      scaleY: 0.1,
      svgOrigin: "60 84",
      duration: blinkCycle.duration,
      ease: "power2.inOut",
      yoyo: true,
      repeat: blinkCycle.repeat,
    }, value.at);
    return tl;
  }

  function wave(tl, actor, opts) {
    var value = values(opts, 1.2);
    var waveCycle = yoyoCycle(value.duration, 0.3);
    tl.fromTo(targets(actor, ".xh-arm-r, .xh-arm-f"), {
      rotation: -145 * value.direction,
      svgOrigin: "80 78",
    }, {
      rotation: -110 * value.direction,
      svgOrigin: "80 78",
      duration: waveCycle.duration,
      ease: "sine.inOut",
      yoyo: true,
      repeat: waveCycle.repeat,
      immediateRender: false,
    }, value.at);
    tl.set(targets(actor, ".xh-arm-r, .xh-arm-f"), {
      rotation: 0,
      svgOrigin: "80 78",
    }, position(value.at, value.duration));
    return tl;
  }

  function walkCycle(tl, actor, opts) {
    var value = values(opts, 1.6);
    var stride = yoyoCycle(value.duration, 0.25);
    var bob = yoyoCycle(value.duration, 0.125);
    var hip = "60 129";
    var shoulder = "60 78";
    tl.to(targets(actor, ".xh-root"), {
      x: value.distance * value.direction,
      duration: value.duration,
      ease: "none",
    }, value.at);
    tl.fromTo(targets(actor, ".xh-leg-f, .xh-leg-l"), { rotation: 26 * value.direction, svgOrigin: hip }, {
      rotation: -26 * value.direction, svgOrigin: hip, duration: stride.duration,
      ease: "sine.inOut", yoyo: true, repeat: stride.repeat, immediateRender: false,
    }, value.at);
    tl.fromTo(targets(actor, ".xh-leg-b, .xh-leg-r"), { rotation: -26 * value.direction, svgOrigin: hip }, {
      rotation: 26 * value.direction, svgOrigin: hip, duration: stride.duration,
      ease: "sine.inOut", yoyo: true, repeat: stride.repeat, immediateRender: false,
    }, value.at);
    tl.fromTo(targets(actor, ".xh-arm-f, .xh-arm-r"), { rotation: -22 * value.direction, svgOrigin: shoulder }, {
      rotation: 22 * value.direction, svgOrigin: shoulder, duration: stride.duration,
      ease: "sine.inOut", yoyo: true, repeat: stride.repeat, immediateRender: false,
    }, value.at);
    tl.fromTo(targets(actor, ".xh-arm-b, .xh-arm-l"), { rotation: 22 * value.direction, svgOrigin: shoulder }, {
      rotation: -22 * value.direction, svgOrigin: shoulder, duration: stride.duration,
      ease: "sine.inOut", yoyo: true, repeat: stride.repeat, immediateRender: false,
    }, value.at);
    tl.to(targets(actor, ".xh-root"), {
      y: -4, duration: bob.duration, ease: "sine.inOut", yoyo: true, repeat: bob.repeat,
    }, value.at);
    var end = position(value.at, value.duration);
    tl.set(targets(actor, ".xh-leg-f, .xh-leg-l"), { rotation: 0, svgOrigin: hip }, end);
    tl.set(targets(actor, ".xh-leg-b, .xh-leg-r"), { rotation: 0, svgOrigin: hip }, end);
    tl.set(targets(actor, ".xh-arm-f, .xh-arm-r"), { rotation: 0, svgOrigin: shoulder }, end);
    tl.set(targets(actor, ".xh-arm-b, .xh-arm-l"), { rotation: 0, svgOrigin: shoulder }, end);
    tl.set(targets(actor, ".xh-root"), { y: 0 }, end);
    return tl;
  }

  function nod(tl, actor, opts) {
    var value = values(opts, 0.7);
    var nodCycle = yoyoCycle(value.duration, value.duration / 2);
    tl.to(targets(actor, ".xh-root"), {
      y: 9, duration: nodCycle.duration, ease: "power2.inOut", yoyo: true, repeat: nodCycle.repeat,
    }, value.at);
    tl.to(targets(actor, ".xh-body"), {
      scaleY: 0.9, svgOrigin: "60 130", duration: nodCycle.duration,
      ease: "power2.inOut", yoyo: true, repeat: nodCycle.repeat,
    }, value.at);
    return tl;
  }

  function jump(tl, actor, opts) {
    var value = values(opts, 0.8);
    var rise = value.duration * 0.42;
    var fall = value.duration * 0.4;
    var landing = value.duration - rise - fall;
    var landingCycle = yoyoCycle(landing, landing / 2);
    tl.to(targets(actor, ".xh-root"), {
      y: -Math.abs(value.distance), duration: rise, ease: "power2.out",
    }, value.at);
    tl.to(targets(actor, ".xh-root"), {
      y: 0, duration: fall, ease: "power2.in",
    }, position(value.at, rise));
    tl.fromTo(targets(actor, ".xh-body"), { scaleY: 1, scaleX: 1 }, {
      scaleY: 0.86, scaleX: 1.1, svgOrigin: "60 130", duration: landingCycle.duration,
      ease: "power2.inOut", yoyo: true, repeat: landingCycle.repeat,
    }, position(value.at, rise + fall));
    return tl;
  }

  function think(tl, actor, opts) {
    var value = values(opts, 1.1);
    tl.to(targets(actor, ".xh-arm-r, .xh-arm-f"), {
      rotation: -125 * value.direction, svgOrigin: "80 78", duration: value.duration * 0.55,
      ease: "power2.out",
    }, value.at);
    tl.to(targets(actor, ".xh-body"), {
      rotation: -6 * value.direction, x: -3 * value.direction, svgOrigin: "60 130",
      duration: value.duration, ease: "sine.inOut",
    }, value.at);
    tl.fromTo(targets(actor, ".xh-thought"), { autoAlpha: 0, y: 5, scale: 0.6 }, {
      autoAlpha: 1, y: 0, scale: 1, svgOrigin: "92 48", duration: value.duration * 0.6,
      ease: "back.out(2)",
    }, position(value.at, value.duration * 0.2));
    return tl;
  }

  function surprise(tl, actor, opts) {
    var value = values(opts, 0.5);
    var reaction = yoyoCycle(value.duration, value.duration / 2);
    tl.fromTo(targets(actor, ".xh-eye-l, .xh-eye-r, .xh-eye"), { scale: 1 }, {
      scale: 1.7, svgOrigin: "60 84", duration: reaction.duration,
      ease: "back.out(3)", yoyo: true, repeat: reaction.repeat,
    }, value.at);
    tl.fromTo(targets(actor, ".xh-arm-l, .xh-arm-b"), { rotation: 0 }, {
      rotation: 35, svgOrigin: "40 78", duration: reaction.duration,
      ease: "power2.out", yoyo: true, repeat: reaction.repeat,
    }, value.at);
    tl.fromTo(targets(actor, ".xh-arm-r, .xh-arm-f"), { rotation: 0 }, {
      rotation: -35, svgOrigin: "80 78", duration: reaction.duration,
      ease: "power2.out", yoyo: true, repeat: reaction.repeat,
    }, value.at);
    tl.fromTo(targets(actor, ".xh-root"), { y: 0 }, {
      y: -14, duration: reaction.duration, ease: "power2.out", yoyo: true, repeat: reaction.repeat,
    }, value.at);
    return tl;
  }

  var actions = {
    idle: idle,
    blink: blink,
    wave: wave,
    walk: walkCycle,
    walkCycle: walkCycle,
    nod: nod,
    jump: jump,
    think: think,
    surprise: surprise,
  };

  function dispatch(action, tl, actor, opts) {
    if (!Object.prototype.hasOwnProperty.call(actions, action)) throw new Error("Unknown action: " + action);
    return actions[action](tl, actor, opts);
  }

  globalThis.StoryVideo.microactions = Object.freeze({
    idle: idle,
    blink: blink,
    wave: wave,
    walkCycle: walkCycle,
    nod: nod,
    jump: jump,
    think: think,
    surprise: surprise,
    dispatch: dispatch,
    finiteRepeats: finiteRepeats,
  });
}());
