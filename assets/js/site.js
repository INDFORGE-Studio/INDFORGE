/* INDFORGE - Studio // Arma Reforger division — interactive layer.
   Every page is complete without this file: it only adds languages, search, copy and immersion. */
(function () {
  "use strict";
  var doc = document, root = doc.documentElement;
  var BASE = root.getAttribute("data-base") || "/INDFORGE/";
  var VER = root.getAttribute("data-v") || "0";
  var LANGS = Array.prototype.map.call(doc.querySelectorAll("#lang-menu [data-lang]"), function (b) { return b.getAttribute("data-lang"); });
  if (!LANGS.length) LANGS = ["en"];
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var dict = null;

  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }
  function sstore(k, v) { try { if (v === undefined) return sessionStorage.getItem(k); sessionStorage.setItem(k, v); } catch (e) { return null; } }
  function $(s, c) { return (c || doc).querySelector(s); }
  function $$(s, c) { return Array.prototype.slice.call((c || doc).querySelectorAll(s)); }
  function fmt(s, args) { if (!args) return s; for (var k in args) s = s.split("{" + k + "}").join(args[k]); return s; }
  function tr(key, fallback) { return (dict && dict[key] != null) ? dict[key] : fallback; }
  function plain(s) { var d = doc.createElement("div"); d.innerHTML = s; return d.textContent; }
  /* Plural form of a count key: base = other/many, base1 = one, base2 = few (Polish, Ukrainian: 2-4 except 12-14). */
  function pkey(base, n, d) {
    var c = "other";
    try { c = new Intl.PluralRules(root.getAttribute("lang") || "en").select(n); } catch (e) {}
    var k = c === "one" ? base + "1" : c === "few" ? base + "2" : base;
    return d && d[k] != null ? k : base;
  }

  /* ------------------------------------------------ i18n */
  function applyDict(lang, d) {
    dict = d;
    root.setAttribute("lang", lang);
    root.setAttribute("data-lang", lang);
    $$("[data-i18n]").forEach(function (el) {
      var key = el.getAttribute("data-i18n"), a = el.getAttribute("data-i18n-args"), pl = el.getAttribute("data-i18n-plural");
      if (pl && a) { try { key = pkey(pl, JSON.parse(a).n, d); } catch (e) {} }
      var s = d[key];
      if (s == null) return;
      if (a) { try { s = fmt(s, JSON.parse(a)); } catch (e) {} }
      if (el.tagName === "TITLE") { doc.title = plain(s) + (el.getAttribute("data-i18n-suffix") || ""); return; }
      if (el.innerHTML !== s) el.innerHTML = s;
    });
    $$("[data-i18n-attr]").forEach(function (el) {
      el.getAttribute("data-i18n-attr").split(";").forEach(function (pair) {
        var p = pair.split("="), s = d[p[1]];
        if (p.length === 2 && s != null) el.setAttribute(p[0], plain(s));
      });
    });
    var cur = $(".lang-cur"); if (cur) cur.textContent = lang.toUpperCase();
    $$(".lang-menu [data-lang]").forEach(function (b) { b.setAttribute("aria-checked", String(b.getAttribute("data-lang") === lang)); });
    root.classList.remove("i18n-wait");
    doc.dispatchEvent(new Event("ifg:lang")); // texts built by script (emblem title) follow the language
  }
  /* Pages with config tables also load the translated help texts (data-i18n-cfg = their version). */
  var CFGV = root.getAttribute("data-i18n-cfg");
  function loadPack(name, ver, cb) {
    var key = "ifg-i18n-" + name, c = store(key);
    if (c) { try { var o = JSON.parse(c); if (o.v === ver && o.d) { cb(o.d); return; } } catch (e) {} }
    fetch(BASE + "assets/i18n/" + name + ".json?v=" + ver, { credentials: "same-origin" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) { store(key, JSON.stringify({ v: ver, d: d })); cb(d); })
      .catch(function () { cb(null); });
  }
  function loadLang(lang, cb) {
    loadPack(lang, VER, function (d) {
      if (!d) { root.classList.remove("i18n-wait"); cb(null); return; }
      if (!CFGV) { cb(d); return; }
      loadPack("cfg-" + lang, CFGV, function (c) {
        if (c) for (var k in c) d[k] = c[k];
        cb(d);
      });
    });
  }
  function setLang(lang, save) {
    if (LANGS.indexOf(lang) < 0) lang = "en";
    if (save) store("ifg-lang", lang);
    loadLang(lang, function (d) {
      if (d) applyDict(lang, d); else if (lang !== "en") setLang("en", false);
      afterLang();
    });
  }

  /* ------------------------------------------------ language menu */
  function initLangMenu() {
    var btn = $(".lang-btn"), menu = $("#lang-menu");
    if (!btn || !menu) return;
    function open(v) {
      btn.setAttribute("aria-expanded", String(v)); menu.hidden = !v;
      if (v) { var c = $('[aria-checked="true"]', menu) || $("button", menu); c && c.focus(); }
    }
    btn.addEventListener("click", function (e) { e.stopPropagation(); open(menu.hidden); });
    menu.addEventListener("click", function (e) {
      var b = e.target.closest("[data-lang]"); if (!b) return;
      setLang(b.getAttribute("data-lang"), true); open(false); btn.focus();
      toast(tr("ui.lang_saved", "Language saved on this device."));
    });
    menu.addEventListener("keydown", function (e) {
      var items = $$("button", menu), i = items.indexOf(doc.activeElement);
      if (e.key === "ArrowDown") { e.preventDefault(); items[(i + 1) % items.length].focus(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); items[(i - 1 + items.length) % items.length].focus(); }
      else if (e.key === "Escape") { open(false); btn.focus(); }
      else if (e.key === "Tab") { open(false); }
    });
    doc.addEventListener("click", function (e) { if (!menu.hidden && !e.target.closest(".lang")) open(false); });
  }

  /* ------------------------------------------------ optics (display modes) */
  // Ambient layer of each optic: one canvas, a corner HUD and a click mark. Arma and the
  // national colours have none. Stops when the tab is hidden or the switch is off.
  var FX = { nvg: 1, thermal: 1, arctic: 1, desert: 1, forest: 1, red: 1, day: 1 };
  var DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  function fxOn() { return !root.classList.contains("fx-off"); }
  function makeFx() {
    var cv, ctx, hud, tl, br, torch, parts = [], raf = 0, last = 0, W = 0, Hh = 0, dpr = 1, kind = "", sweep = 0, sprite = null, hudRaf = 0, col = "", col2 = "", flies = [];
    var fine = window.matchMedia && matchMedia("(hover: hover) and (pointer: fine)").matches;
    function el(cls) { var d = doc.createElement("div"); d.className = cls; d.setAttribute("aria-hidden", "true"); d.hidden = true; doc.body.appendChild(d); return d; }
    function ensure() {
      if (cv) return;
      cv = doc.createElement("canvas"); cv.className = "fx-cv"; cv.setAttribute("aria-hidden", "true"); cv.hidden = true;
      doc.body.appendChild(cv); ctx = cv.getContext("2d");
      hud = el("fx-hud"); hud.innerHTML = '<span class="fx-tl"></span><span class="fx-br"></span>';
      tl = hud.firstChild; br = hud.lastChild;
      torch = el("fx-torch");
      window.addEventListener("resize", function () { if (kind) { size(); seed(); } }, { passive: true });
      window.addEventListener("scroll", function () { if (kind && !hudRaf) hudRaf = requestAnimationFrame(hudText); }, { passive: true });
      doc.addEventListener("visibilitychange", function () { if (doc.hidden) stop(); else if (kind) start(); });
      if (fine) doc.addEventListener("pointermove", function (e) {
        if (kind !== "red") return;
        torch.style.setProperty("--mx", e.clientX + "px"); torch.style.setProperty("--my", e.clientY + "px");
      }, { passive: true });
    }
    function rgbVar(n) { return getComputedStyle(root).getPropertyValue(n).trim() || "255, 255, 255"; }
    function size() {
      dpr = Math.min(window.devicePixelRatio || 1, 1.5); W = innerWidth; Hh = innerHeight;
      cv.width = Math.round(W * dpr); cv.height = Math.round(Hh * dpr); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    function rnd(a, b) { return a + Math.random() * (b - a); }
    function spawn(p, top) {
      if (kind === "arctic") { p.x = rnd(0, W); p.y = top ? rnd(-20, 0) : rnd(0, Hh); p.r = rnd(.6, 2.2); p.vy = .35 + p.r * .4; p.vx = rnd(.2, .6); p.ph = rnd(0, 6.3); p.a = rnd(.35, .85); }
      else if (kind === "desert") { p.x = top ? rnd(-30, -4) : rnd(0, W); p.y = Hh * Math.sqrt(Math.random()); /* sand blows low */ p.r = rnd(.6, 1.7); p.vx = rnd(.8, 2.6); p.vy = rnd(-.12, .12); p.ph = rnd(0, 6.3); p.tw = rnd(.6, 1.6); p.a = rnd(.18, .6); p.c = Math.random() < .7 ? 0 : 1; }
      else if (kind === "forest") { p.x = rnd(0, W); p.y = top ? rnd(-30, -8) : rnd(0, Hh); p.s = rnd(3, 7); p.rot = rnd(0, 6.3); p.vr = rnd(-.04, .04); p.vy = rnd(.3, .85); p.sw = rnd(.4, 1.2); p.ph = rnd(0, 6.3); p.a = rnd(.3, .65); p.c = Math.random() < .55 ? 0 : 1; }
      else if (kind === "thermal") { p.x = rnd(0, W); p.y = top ? Hh + rnd(0, 60) : rnd(0, Hh); p.r = rnd(10, 34); p.vy = -rnd(.15, .55); p.vx = rnd(-.1, .1); p.ph = rnd(0, 6.3); p.a = rnd(.05, .14); p.c = Math.random() < .7 ? 0 : 1; }
      else { p.x = rnd(0, W); p.y = rnd(0, Hh); p.r = rnd(.5, 1.5); p.vx = rnd(-.09, .09); p.vy = rnd(-.09, .09); p.ph = rnd(0, 6.3); p.a = rnd(.2, kind === "red" ? .4 : .7); }
      return p;
    }
    function seed() {
      var area = W * Hh, n = kind === "arctic" ? Math.min(120, area / 12000) : kind === "thermal" ? Math.min(28, area / 50000)
        : kind === "desert" ? Math.min(220, area / 7000) : kind === "forest" ? Math.min(40, area / 28000) : Math.min(90, area / 16000);
      if (kind === "red") n *= .5;
      parts = []; for (var i = 0; i < Math.round(n); i++) parts.push(spawn({}, false));
      flies = [];
      if (kind === "desert") for (i = 0; i < Math.round(Math.min(10, 3 + area / 220000)); i++) // drifting dust clouds
        flies.push({ x: rnd(-200, W), y: rnd(Hh * .15, Hh * 1.05), r: rnd(180, 420), vx: rnd(.25, .7), a: rnd(.05, .11), ph: rnd(0, 6.3) });
      if (kind === "forest") for (i = 0; i < Math.round(Math.min(14, area / 70000)); i++)
        flies.push({ x: rnd(0, W), y: rnd(Hh * .25, Hh), vx: rnd(-.3, .3), vy: rnd(-.2, .2), ph: rnd(0, 6.3), r: rnd(5, 9) });
    }
    function makeSprite(cols) {
      sprite = cols.map(function (c) {
        var s = doc.createElement("canvas"); s.width = s.height = 64; var x = s.getContext("2d");
        var gr = x.createRadialGradient(32, 32, 0, 32, 32, 32);
        gr.addColorStop(0, "rgba(" + c + ",1)"); gr.addColorStop(1, "rgba(" + c + ",0)");
        x.fillStyle = gr; x.fillRect(0, 0, 64, 64); return s;
      });
    }
    function frame(now) {
      raf = requestAnimationFrame(frame);
      var dt = Math.min(50, now - (last || now)) / 16.67; last = now;
      ctx.clearRect(0, 0, W, Hh);
      var t = now / 1000, i, p;
      if (kind === "thermal") {
        ctx.globalCompositeOperation = "lighter";
        for (i = 0; i < parts.length; i++) {
          p = parts[i]; p.y += p.vy * dt; p.x += (p.vx + Math.sin(t + p.ph) * .15) * dt;
          if (p.y < -p.r * 2) spawn(p, true);
          ctx.globalAlpha = p.a * (.7 + .3 * Math.sin(t * 1.5 + p.ph));
          ctx.drawImage(sprite[p.c], p.x - p.r, p.y - p.r, p.r * 2, p.r * 2);
        }
        ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over";
        return;
      }
      if (kind === "desert") {
        var gust = .75 + .35 * Math.sin(t * .45) + .25 * Math.max(0, Math.sin(t * 1.9 + 1)), haze = ctx.createLinearGradient(0, Hh * .45, 0, Hh);
        haze.addColorStop(0, "rgba(214, 178, 120, 0)"); haze.addColorStop(1, "rgba(214, 178, 120, " + (.07 + .05 * gust).toFixed(3) + ")");
        ctx.fillStyle = haze; ctx.fillRect(0, Hh * .45, W, Hh * .55);
        for (i = 0; i < flies.length; i++) { // dust clouds rolling with the wind
          p = flies[i]; p.x += p.vx * gust * dt;
          if (p.x - p.r > W) { p.x = -p.r; p.y = rnd(Hh * .15, Hh * 1.05); }
          ctx.globalAlpha = p.a * (.75 + .25 * Math.sin(t * .4 + p.ph)) * gust;
          ctx.drawImage(sprite[0], p.x - p.r, p.y - p.r * .55, p.r * 2, p.r * 1.1);
        }
        var grain = ["rgb(226, 196, 146)", "rgb(176, 138, 88)"];
        for (i = 0; i < parts.length; i++) { // sand grains: uneven, tumbling, in gusts
          p = parts[i]; p.x += p.vx * gust * dt; p.y += (p.vy + Math.sin(t * p.tw + p.ph) * .45) * dt;
          if (p.x > W + 6) spawn(p, true);
          ctx.globalAlpha = p.a * (.6 + .4 * Math.sin(t * 2.3 + p.ph)) * (.25 + .75 * Math.max(0, p.y) / Hh); ctx.fillStyle = grain[p.c];
          ctx.fillRect(p.x, p.y, p.r * (1 + gust * .8), p.r);
        }
        ctx.globalAlpha = 1;
        return;
      }
      if (kind === "forest") {
        var leaf = ["rgb(" + col + ")", "rgb(" + col2 + ")"];
        for (i = 0; i < parts.length; i++) {
          p = parts[i]; p.y += p.vy * dt; p.x += Math.sin(t * .9 + p.ph) * p.sw * dt; p.rot += p.vr * dt;
          if (p.y > Hh + 10) spawn(p, true);
          ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.rot + Math.sin(t + p.ph) * .5);
          ctx.globalAlpha = p.a; ctx.fillStyle = leaf[p.c];
          ctx.beginPath(); ctx.ellipse(0, 0, p.s, p.s * .42, 0, 0, 6.283); ctx.fill(); ctx.restore();
        }
        ctx.globalCompositeOperation = "lighter";
        for (i = 0; i < flies.length; i++) {
          p = flies[i]; p.x += (p.vx + Math.sin(t * .7 + p.ph) * .25) * dt; p.y += (p.vy + Math.cos(t * .6 + p.ph) * .2) * dt;
          if (p.x < 0) p.x = W; else if (p.x > W) p.x = 0;
          if (p.y < Hh * .2) p.y = Hh; else if (p.y > Hh) p.y = Hh * .2;
          ctx.globalAlpha = Math.max(0, Math.sin(t * 1.3 + p.ph)) * .9;
          ctx.drawImage(sprite[0], p.x - p.r, p.y - p.r, p.r * 2, p.r * 2);
        }
        ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over";
        return;
      }
      if (kind === "arctic") {
        var wind = .6 + .5 * Math.sin(t * .3);
        ctx.fillStyle = "rgb(228, 244, 255)";
        for (i = 0; i < parts.length; i++) {
          p = parts[i]; p.y += p.vy * dt; p.x += (p.vx * wind + Math.sin(t + p.ph) * .3) * dt;
          if (p.y > Hh + 4) spawn(p, true);
          if (p.x > W + 4) p.x = -4;
          ctx.globalAlpha = p.a; ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 6.283); ctx.fill();
        }
        ctx.globalAlpha = 1;
        return;
      }
      ctx.fillStyle = "rgb(" + col + ")";
      for (i = 0; i < parts.length; i++) {
        p = parts[i]; p.x += p.vx * dt; p.y += p.vy * dt;
        if (p.x < 0) p.x = W; else if (p.x > W) p.x = 0;
        if (p.y < 0) p.y = Hh; else if (p.y > Hh) p.y = 0;
        ctx.globalAlpha = p.a * (.55 + .45 * Math.sin(t * 3 + p.ph));
        ctx.fillRect(p.x, p.y, p.r, p.r);
      }
      ctx.globalAlpha = 1;
      if (kind === "nvg") {
        sweep = (sweep + 1.1 * dt) % (Hh + 160);
        var y = sweep - 80, g = ctx.createLinearGradient(0, y - 70, 0, y + 10);
        g.addColorStop(0, "rgba(" + col + ",0)"); g.addColorStop(.85, "rgba(" + col + ",.07)"); g.addColorStop(1, "rgba(" + col + ",0)");
        ctx.fillStyle = g; ctx.fillRect(0, y - 70, W, 80);
      }
    }
    function start() { if (!raf && kind && kind !== "day" && !doc.hidden) { last = 0; raf = requestAnimationFrame(frame); } }
    function stop() { if (raf) cancelAnimationFrame(raf); raf = 0; }
    function scrollFrac() { var m = doc.documentElement.scrollHeight - innerHeight; return m > 0 ? Math.min(1, Math.max(0, scrollY / m)) : 0; }
    function hdg() { var d = Math.round(42 + scrollFrac() * 318) % 360; return "HDG " + ("00" + d).slice(-3) + "° " + DIRS[Math.round(d / 45) % 8]; }
    function hudText() {
      hudRaf = 0; var f = scrollFrac();
      if (kind === "nvg") { tl.innerHTML = "NVG<i></i>GAIN 3"; br.textContent = hdg(); }
      else if (kind === "thermal") { tl.innerHTML = "IR<i></i>WHITE-HOT"; br.textContent = "T° " + (29 + f * 8).toFixed(1) + "°C"; }
      else if (kind === "arctic") { tl.innerHTML = "ARC<i></i>WIND " + (12 + Math.round(f * 9)) + " KT NW"; br.textContent = "T° −" + (16 + Math.round(f * 7)) + "°C"; }
      else if (kind === "desert") { tl.innerHTML = "DST<i></i>WIND " + (18 + Math.round(f * 14)) + " KT E"; br.textContent = "T° " + (41 + Math.round(f * 8)) + "°C"; }
      else if (kind === "forest") { tl.innerHTML = "FOR<i></i>CANOPY " + (88 - Math.round(f * 20)) + "%"; br.textContent = hdg(); }
      else if (kind === "red") { tl.innerHTML = "RED<i></i>LOW-LIGHT"; br.textContent = hdg(); }
    }
    function refresh() {
      var k = root.getAttribute("data-theme") || "";
      k = FX[k] && fxOn() ? k : "";
      if (!k && !cv) return;
      ensure(); stop(); kind = k;
      cv.hidden = !k || k === "day"; hud.hidden = !k || k === "day"; torch.hidden = !(k === "red" && fine);
      if (!k) { ctx.clearRect(0, 0, W, Hh); return; }
      if (k === "day") return;
      col = rgbVar("--amber-rgb"); col2 = rgbVar("--green-rgb");
      size(); if (k === "thermal") makeSprite([col, col2]); else if (k === "forest") makeSprite(["255, 222, 130"]); else if (k === "desert") makeSprite(["205, 168, 112"]);
      seed(); hudText(); start();
    }
    function hit(x, y) {
      var k = kind; if (!k) return;
      var label = k === "nvg" ? "RNG " + Math.round(rnd(120, 900)) + " m"
        : k === "thermal" ? "+" + rnd(31, 39).toFixed(1) + "°C"
        : k === "arctic" ? "−" + Math.round(rnd(8, 31)) + "°C"
        : k === "desert" ? "BRG " + ("00" + Math.round(rnd(0, 359))).slice(-3) + "°"
        : k === "forest" ? "WPT " + ("0" + Math.round(rnd(1, 24))).slice(-2)
        : k === "red" ? "PING " + ("00" + Math.round(rnd(0, 359))).slice(-3) + "°"
        : plain(tr("optic.stamp", "Read & approved"));
      var d = doc.createElement("div"); d.className = "fx-hit fx-" + k; d.setAttribute("aria-hidden", "true");
      d.style.left = x + "px"; d.style.top = y + "px";
      if (k === "day") d.style.setProperty("--rot", rnd(-12, 12).toFixed(1) + "deg");
      d.innerHTML = "<i></i><b></b>"; d.lastChild.textContent = label;
      doc.body.appendChild(d); setTimeout(function () { d.remove(); }, k === "day" ? 2700 : 1150);
    }
    doc.addEventListener("click", function (e) {
      if (!kind || e.detail === 0 || e.target.closest("input, textarea, select, .lang-menu, .pal")) return;
      hit(e.clientX, e.clientY);
    });
    return { refresh: refresh };
  }

  function initOptics() {
    var btn = $(".opt-btn"), menu = $("#opt-menu");
    if (!btn || !menu) return;
    var radios = $$("[data-optic]", menu), fxBtn = $("[data-fx]", menu), items = $$("button", menu);
    var meta = $('meta[name="theme-color"]'), fx = makeFx();
    function current() { return root.getAttribute("data-theme") || "arma"; }
    function sync() {
      var cur = current(), on = radios.filter(function (b) { return b.getAttribute("data-optic") === cur; })[0];
      radios.forEach(function (b) { b.setAttribute("aria-checked", String(b === on)); });
      if (fxBtn) fxBtn.setAttribute("aria-checked", String(fxOn()));
      $(".opt-cur", btn).textContent = on ? $(".opt-k", on).textContent : "ARM";
      var fsb = $(".fsb"), nm = on && $("[data-i18n]", on);
      if (fsb) fsb.title = nm ? plain(tr("optic.emblem", "INDFORGE emblem · {n}")).replace("{n}", nm.textContent) : "";
      if (meta) meta.setAttribute("content", getComputedStyle(root).getPropertyValue("--bg").trim() || "#06080a");
    }
    /* each group (styles, countries) in alphabetical order of its names in the chosen language, Arma first */
    function order() {
      var groups = [[]], lang = root.getAttribute("data-lang") || "en";
      var cmp = window.Intl && Intl.Collator ? new Intl.Collator(lang).compare : function (a, b) { return a.localeCompare(b); };
      $$("li", menu).forEach(function (li) {
        if (li.classList.contains("opt-h")) groups.push([]);
        else if ($("[data-optic]", li)) groups[groups.length - 1].push(li);
      });
      function name(li) { var n = $("[data-i18n]", li); return n ? n.textContent : ""; }
      function first(li) { return $("[data-optic]", li).getAttribute("data-optic") === "arma" ? 0 : 1; }
      groups.forEach(function (g) {
        if (!g.length) return;
        var end = g[g.length - 1].nextSibling, box = g[0].parentNode;
        g.slice().sort(function (a, b) { return first(a) - first(b) || cmp(name(a), name(b)); })
          .forEach(function (li) { box.insertBefore(li, end); });
      });
      items = $$("button", menu);
    }
    doc.addEventListener("ifg:lang", function () { order(); sync(); });
    function apply(o) {
      if (o === "arma") root.removeAttribute("data-theme"); else root.setAttribute("data-theme", o);
      store("ifg-optic", o); sync(); fx.refresh();
    }
    var live = null; // optic transition in progress
    function engage(o, from) {
      if (o === current()) return;
      var r = from.getBoundingClientRect(), anim = !reduce && fxOn();
      root.style.setProperty("--vx", Math.round(r.left + r.width / 2) + "px");
      root.style.setProperty("--vy", Math.round(r.top + r.height / 2) + "px");
      var label = plain(tr("optic." + o, o));
      if (!anim || !doc.startViewTransition) { apply(o); }
      else {
        root.classList.add("vt-optic");
        var vt = live = doc.startViewTransition(function () { apply(o); }); // a newer one skips this one
        vt.ready.catch(function () {}); vt.updateCallbackDone.catch(function () {});
        vt.finished.then(done, done);
      }
      if (anim) {
        var ring = doc.createElement("div"); ring.className = "optic-ring"; ring.setAttribute("aria-hidden", "true");
        doc.body.appendChild(ring); setTimeout(function () { ring.remove(); }, 800);
      }
      toast(fmt(tr("optic.on", "Optic engaged: {n}"), { n: label }));
      function done() { if (live === vt) { live = null; root.classList.remove("vt-optic"); } }
    }
    function toggleFx() {
      var on = !fxOn();
      root.classList.toggle("fx-off", !on); store("ifg-fx", on ? "on" : "off");
      sync(); fx.refresh();
      toast(plain(tr(on ? "optic.fx_on" : "optic.fx_off", on ? "Ambient effects on" : "Ambient effects off")));
    }
    function open(v) {
      btn.setAttribute("aria-expanded", String(v)); menu.hidden = !v;
      if (v) {
        $$("img[data-src]", menu).forEach(function (im) { im.src = im.getAttribute("data-src"); im.removeAttribute("data-src"); });
        var lb = $(".lang-btn"), lm = $("#lang-menu");
        if (lm && !lm.hidden) { lm.hidden = true; lb.setAttribute("aria-expanded", "false"); }
        var c = $('[data-optic][aria-checked="true"]', menu) || radios[0]; c && c.focus();
      }
    }
    btn.addEventListener("click", function (e) { e.stopPropagation(); open(menu.hidden); });
    menu.addEventListener("click", function (e) {
      if (e.target.closest("[data-fx]")) { toggleFx(); return; }
      var b = e.target.closest("[data-optic]"); if (!b) return;
      engage(b.getAttribute("data-optic"), b);
    });
    /* the menu stays open while styles are tried; with a mouse it closes once the pointer leaves it */
    var box = btn.closest(".opt") || menu, leave = 0;
    box.addEventListener("pointerleave", function (e) {
      if (e.pointerType !== "mouse" || menu.hidden) return;
      leave = setTimeout(function () { var f = menu.contains(doc.activeElement); open(false); if (f) btn.focus(); }, 300);
    });
    box.addEventListener("pointerenter", function () { clearTimeout(leave); });
    menu.addEventListener("keydown", function (e) {
      var i = items.indexOf(doc.activeElement);
      if (e.key === "ArrowDown") { e.preventDefault(); items[(i + 1) % items.length].focus(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); items[(i - 1 + items.length) % items.length].focus(); }
      else if (e.key === "Home") { e.preventDefault(); items[0].focus(); }
      else if (e.key === "End") { e.preventDefault(); items[items.length - 1].focus(); }
      else if (e.key === "Escape") { open(false); btn.focus(); }
      else if (e.key === "Tab") { open(false); }
    });
    doc.addEventListener("click", function (e) { if (!menu.hidden && !e.target.closest(".opt")) open(false); });
    var lb0 = $(".lang-btn"); if (lb0) lb0.addEventListener("click", function () { if (!menu.hidden) open(false); });
    order(); sync(); fx.refresh();
  }

  /* ------------------------------------------------ mobile menu */
  function initMenu() {
    var btn = $(".menu-btn"), nav = $("#nav");
    if (!btn || !nav) return;
    function set(v) {
      btn.setAttribute("aria-expanded", String(v)); nav.classList.toggle("open", v);
      doc.body.style.overflow = v ? "hidden" : "";
    }
    btn.addEventListener("click", function () { set(!nav.classList.contains("open")); });
    nav.addEventListener("click", function (e) { if (e.target.closest("a")) set(false); });
    doc.addEventListener("keydown", function (e) { if (e.key === "Escape" && nav.classList.contains("open")) { set(false); btn.focus(); } });
    window.addEventListener("resize", function () { if (innerWidth > 1279 && nav.classList.contains("open")) set(false); });
  }

  /* ------------------------------------------------ radio callsign: each visitor gets one, a click draws a new one */
  var CALLSIGNS = ["VIPER", "FALCON", "RAVEN", "WOLF", "GHOST", "HAWK", "COBRA", "TALON", "SABRE", "LANCER", "NOMAD", "RANGER",
    "SPECTRE", "ATLAS", "ORION", "HUNTER", "KESTREL", "OSPREY", "HORNET", "BADGER", "MUSTANG", "PHOENIX", "TITAN", "BISON",
    "LYNX", "GRIFFIN", "WARDEN", "SHADOW", "STORM", "ARROW", "MAGPIE", "TEMPEST"];
  function initCallsign() {
    var b = $(".csign"), v = b && $(".csign-v", b); if (!v) return;
    function draw() {
      var w = CALLSIGNS[Math.floor(Math.random() * CALLSIGNS.length)];
      return w + " " + (1 + Math.floor(Math.random() * 9)) + "-" + (1 + Math.floor(Math.random() * 9));
    }
    var cur = store("ifg-callsign");
    if (!cur || !/^[A-Z]+ [1-9]-[1-9]$/.test(cur)) { cur = draw(); store("ifg-callsign", cur); }
    v.textContent = cur;
    b.addEventListener("click", function () {
      var next = cur; while (next === cur) next = draw();
      cur = next; store("ifg-callsign", cur);
      toast(tr("ui.callsign_set", "New callsign: {c}").replace("{c}", cur));
      if (reduce) { v.textContent = cur; return; }
      var n = 0, A = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
      (function tick() { // radio static before the new callsign locks in
        n++;
        v.textContent = cur.split("").map(function (c, i) { return c === " " || c === "-" || i < n - 3 ? c : A[Math.floor(Math.random() * A.length)]; }).join("");
        if (n < cur.length + 4) setTimeout(tick, 35); else v.textContent = cur;
      })();
    });
  }

  /* ------------------------------------------------ toast & copy */
  var toastEl, toastT;
  function toast(msg, bad, ms) {
    if (!toastEl) { toastEl = doc.createElement("div"); toastEl.className = "toast"; toastEl.setAttribute("role", "status"); doc.body.appendChild(toastEl); }
    toastEl.textContent = plain(msg); toastEl.classList.toggle("bad", !!bad);
    void toastEl.offsetWidth; toastEl.classList.add("on");
    clearTimeout(toastT); toastT = setTimeout(function () { toastEl.classList.remove("on"); }, ms || 1800);
  }
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text).catch(function () { return legacyCopy(text); });
    return legacyCopy(text);
  }
  function legacyCopy(text) {
    return new Promise(function (ok, ko) {
      var ta = doc.createElement("textarea"); ta.value = text; ta.setAttribute("readonly", "");
      ta.style.position = "fixed"; ta.style.opacity = "0"; doc.body.appendChild(ta); ta.select();
      try { doc.execCommand("copy") ? ok() : ko(); } catch (e) { ko(e); } finally { ta.remove(); }
    });
  }
  function initCopy() {
    doc.addEventListener("click", function (e) {
      var b = e.target.closest(".copy, .srv-copy"); if (!b) return;
      var sel = b.getAttribute("data-copy"), text = b.getAttribute("data-copy-text");
      if (sel) { var src = $(sel); text = src ? src.textContent : ""; }
      if (!text) return;
      copyText(text).then(function () {
        b.classList.add("ok"); var l = $(".copy-lbl", b), old = l && l.innerHTML;
        if (l) l.textContent = plain(tr("ui.copied", "Copied"));
        var msg = b.getAttribute("data-copy-msg");
        toast(msg ? tr(msg, "Copied") : tr("ui.copied", "Copied"), false, msg ? 4200 : 0);
        setTimeout(function () { b.classList.remove("ok"); if (l) l.innerHTML = old; }, 1600);
      }, function () { toast(tr("ui.copy_fail", "Copy blocked: select the text by hand"), true); });
    });
  }

  /* ------------------------------------------------ live test server (home strip)
     Public reading from gamemonitoring.net: state, players, reading time. Nothing else is kept.
     No answer, a bad answer or an old reading leaves the static strip as it is. */
  function initLive() {
    var box = $(".srv[data-live]"); if (!box || !window.fetch || !window.JSON) return;
    var URL = "https://api.gamemonitoring.net/servers/" + encodeURIComponent(box.getAttribute("data-live"));
    var KEY = "ifg-srv", MAXAGE = 110000, last = null, busy = false, prevN = -1;
    var st = doc.createElement("span"); st.className = "srv-st"; st.hidden = true;
    $(".srv-l", box).appendChild(st);
    var live = doc.createElement("span"); live.className = "srv-live"; live.hidden = true;
    live.innerHTML = '<span class="srv-cnt" aria-hidden="true"><b></b><i>/</i><b></b></span>' +
      '<span class="srv-slots" aria-hidden="true"></span><span class="srv-age"></span><span class="srv-sr"></span>';
    var mid = $(".srv-mid", box); mid.insertBefore(live, $(".srv-meta", mid));
    var meta = $(".srv-meta", mid);
    var lbl = $(".srv-k", box);
    var cnt = $$(".srv-cnt b", live), slots = $(".srv-slots", live), age = $(".srv-age", live), sr = $(".srv-sr", live);

    function say(el, key, fb, args) {
      el.setAttribute("data-i18n", key);
      if (args) el.setAttribute("data-i18n-args", JSON.stringify(args)); else el.removeAttribute("data-i18n-args");
      el.innerHTML = fmt(tr(key, fb), args);
    }
    function two(n) { return n < 10 ? "0" + n : String(n); }
    function render(d) {
      var now = Date.now() / 1000;
      // an old reading, or a server dark for two days (moved, renamed): say nothing rather than something false
      var known = d && now - d.t < 1800 && (d.on || now - d.lo < 172800);
      if (!known) { box.classList.remove("srv-on", "srv-off"); st.hidden = live.hidden = true; if (meta) say(meta, "srv.meta", meta.textContent); if (lbl) say(lbl, "srv.h", lbl.textContent); return; }
      box.classList.toggle("srv-on", d.on); box.classList.toggle("srv-off", !d.on);
      if (meta) say(meta, d.on ? "srv.meta_live" : "srv.meta", meta.textContent); // the counter already gives the slots
      if (lbl) say(lbl, "srv.h_live", "Server"); // the badge says the rest
      say(st, d.on ? "srv.on" : "srv.off", d.on ? "ON-LINE" : "OFF-LINE"); st.hidden = false;
      if (!d.on) { live.hidden = true; prevN = -1; return; }
      cnt[0].textContent = two(d.n); cnt[1].textContent = two(d.max);
      if (slots.children.length !== d.max) { slots.innerHTML = new Array(d.max + 1).join("<i></i>"); prevN = -1; }
      Array.prototype.forEach.call(slots.children, function (s, i) {
        var f = i < d.n; if (f && !s.classList.contains("f") && prevN >= 0) { s.classList.add("nw"); s.style.animationDelay = (i - prevN) * 70 + "ms"; }
        s.classList.toggle("f", f);
      });
      if (prevN >= 0 && prevN !== d.n) { live.classList.remove("bump"); void live.offsetWidth; live.classList.add("bump"); }
      prevN = d.n;
      var m = Math.max(0, Math.round((now - d.t) / 60));
      if (m < 1) say(age, "srv.age0", "just now"); else say(age, "srv.age", "{n} min ago", { n: m });
      say(sr, "srv.players_a", "Players online: {n} of {max}", { n: d.n, max: d.max });
      live.title = plain(tr("srv.src", "Public reading: gamemonitoring.net"));
      live.hidden = false;
    }
    function keep(r) {
      if (!r || typeof r.numplayers !== "number" || typeof r.maxplayers !== "number") throw new Error("shape");
      var max = Math.min(64, Math.max(1, r.maxplayers | 0));
      return { on: r.status === true, n: Math.min(max, Math.max(0, r.numplayers | 0)), max: max,
        t: +r.last_update || 0, lo: +r.last_online || 0, at: Date.now() };
    }
    function pull() {
      if (doc.hidden || busy) return;
      var c = null; try { c = JSON.parse(sstore(KEY) || "null"); } catch (e) {}
      if (c && Date.now() - c.at < MAXAGE) { last = c; render(c); return; }
      busy = true;
      var ctl = window.AbortController ? new AbortController() : null;
      var to = setTimeout(function () { if (ctl) ctl.abort(); }, 6000);
      fetch(URL, { signal: ctl ? ctl.signal : undefined, credentials: "omit", referrerPolicy: "no-referrer", cache: "no-store" })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (j) { last = keep(j && j.response); sstore(KEY, JSON.stringify(last)); render(last); })
        .catch(function () { render(last); })
        .then(function () { clearTimeout(to); busy = false; });
    }
    pull();
    setInterval(pull, 30000);
    doc.addEventListener("visibilitychange", pull);
  }

  /* ------------------------------------------------ search palette */
  var idx = null, pal, palInput, palList, palSel = 0, palItems = [], lastFocus;
  function loadIndex() {
    if (idx) return Promise.resolve(idx);
    return fetch(BASE + "assets/search.json?v=" + VER).then(function (r) { return r.json(); }).then(function (d) { idx = d; return d; });
  }
  function norm(s) { return plain(String(s || "")).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, ""); }
  function buildPal() {
    pal = doc.createElement("div"); pal.className = "pal"; pal.hidden = true;
    pal.setAttribute("role", "dialog"); pal.setAttribute("aria-modal", "true"); pal.setAttribute("aria-label", plain(tr("nav.search", "Search")));
    pal.innerHTML = '<div class="pal-box"><label class="pal-field"><svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="M16 16l5 5"/></svg>' +
      '<input type="search" autocomplete="off" spellcheck="false" role="combobox" aria-expanded="true" aria-controls="pal-list" aria-autocomplete="list"></label>' +
      '<ul class="pal-list" id="pal-list" role="listbox"></ul><div class="pal-hint"></div></div>';
    doc.body.appendChild(pal);
    palInput = $("input", pal); palList = $(".pal-list", pal);
    $(".pal-field", pal).insertAdjacentElement("afterend", spBuild());
    palInput.addEventListener("input", renderPal);
    pal.addEventListener("click", function (e) { if (e.target === pal) closePal(); });
    pal.addEventListener("keydown", function (e) {
      var inField = e.target === palInput;
      if (e.key === "Escape") { e.preventDefault(); closePal(); }
      else if (e.key === "ArrowDown" && inField) { e.preventDefault(); selPal(palSel + 1); }
      else if (e.key === "ArrowUp" && inField) { e.preventDefault(); selPal(palSel - 1); }
      else if (e.key === "Enter" && inField) { var a = palItems[palSel]; if (a) { e.preventDefault(); a.click(); } }
      else if (e.key === "Tab") {
        // focus stays inside the dialog: the field, SPARKS' buttons and links, then the results
        var f = $$("input, button:not([hidden]), a[href]", pal).filter(function (x) { return x.offsetParent !== null; });
        var i = f.indexOf(doc.activeElement); e.preventDefault();
        (f[(i + (e.shiftKey ? -1 : 1) + f.length) % f.length] || palInput).focus();
      }
    });
  }
  function kindLabel(k) { return plain(tr("ui.k_" + k, k)); }
  function renderPal() {
    var q = norm(palInput.value).trim(), terms = q.split(/\s+/).filter(Boolean), out = [];
    (idx || []).forEach(function (it) {
      var title = it.tk ? plain(tr(it.t, it.t)) : it.t, sub = it.s ? plain(tr(it.s, "")) : "";
      var hay = norm(title + " " + sub + " " + (it.x || "") + " " + it.u);
      if (terms.every(function (t) { return hay.indexOf(t) >= 0; })) {
        var score = norm(title).indexOf(q) === 0 ? 0 : norm(title).indexOf(q) >= 0 ? 1 : 2;
        out.push({ it: it, title: title, sub: sub, score: score });
      }
    });
    if (q) out.sort(function (a, b) { return a.score - b.score; });
    out = out.slice(0, 40);
    palList.innerHTML = "";
    if (!out.length) { palList.innerHTML = '<li class="pal-empty">' + plain(tr("ui.search_empty", "No match on this frequency.")) + "</li>"; }
    out.forEach(function (o, i) {
      var li = doc.createElement("li"), a = doc.createElement("a");
      li.setAttribute("role", "none"); a.href = o.it.u; a.id = "pal-o" + i; a.setAttribute("role", "option");
      a.innerHTML = '<span class="pal-k"></span><span class="pal-t"></span><span class="pal-s"></span>';
      a.children[0].textContent = kindLabel(o.it.k); a.children[1].textContent = o.title; a.children[2].textContent = o.sub;
      a.addEventListener("mousemove", function () { if (palSel !== i) selPal(i); });
      a.addEventListener("click", function () { closePal(true); });
      li.appendChild(a); palList.appendChild(li);
    });
    palItems = $$("a", palList); selPal(0);
    spTyped(q, out.length > 0);
  }
  function selPal(i) {
    if (!palItems.length) return;
    palSel = (i + palItems.length) % palItems.length;
    palItems.forEach(function (a, j) { a.setAttribute("aria-selected", String(j === palSel)); });
    palInput.setAttribute("aria-activedescendant", palItems[palSel].id);
    palItems[palSel].scrollIntoView({ block: "nearest" });
  }
  function openPal() {
    if (!pal) buildPal();
    lastFocus = doc.activeElement;
    palInput.placeholder = plain(tr("ui.search_ph", "Type a mod, a page, a command…"));
    $(".pal-hint", pal).innerHTML = tr("ui.search_hint", "");
    pal.hidden = false; palInput.value = ""; palInput.focus();
    sp.stack = [{ name: "root", args: [] }]; sp.typed = false; spRender();
    loadIndex().then(function () { renderPal(); spRender(); }).catch(function () {});
  }
  function closePal(navigating) {
    if (!pal || pal.hidden) return;
    pal.hidden = true;
    if (!navigating && lastFocus && lastFocus.focus) lastFocus.focus();
  }
  function initSearch() {
    $$("[data-search]").forEach(function (b) { b.addEventListener("click", openPal); });
    doc.addEventListener("keydown", function (e) {
      var t = e.target, typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable);
      if ((e.key === "/" && !typing) || ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K"))) {
        if (pal && !pal.hidden) return;
        e.preventDefault(); openPal();
      }
    });
  }

  /* ------------------------------------------------ SPARKS: guided search assistant (inside the search palette)
     No server, no key, nothing sent anywhere: a small question tree written by hand, plus the site's own
     search index (assets/search.json) for the mod lists, families (c), Workshop links (w) and Tips (m). */
  var sp = { box: null, stack: [], typed: false };
  var SP_EXT = {
    host: "https://community.bistudio.com/wiki/Arma_Reforger:Server_Hosting",
    cfg: "https://community.bistudio.com/wiki/Arma_Reforger:Server_Config",
    mod: "https://community.bistudio.com/wiki/Category:Arma_Reforger/Modding",
    ws: "https://reforger.armaplatform.com/workshop"
  };
  var SP_FAM = ["indforge", "auc", "ctrp", "gear", "vehicles", "standby"];
  var SP_TIPS = ["conflict-pve", "forest", "enhanced-compositions", "rcd-wcs", "rcd-rhs", "solo-push-pull", "off-road-vehicles", "packs"];
  function spT(k, args) { return fmt(plain(tr("sparks." + k, "")), args); }
  function spMods(fam) { return (idx || []).filter(function (it) { return it.k === "mod" && (!fam || it.c === fam); }); }
  function spMod(slug) { var u = BASE + "workshop/" + slug + "/"; return spMods().filter(function (it) { return it.u === u; })[0]; }
  function spL(label, href, ext) { return { label: label, href: href, ext: !!ext }; }
  function spC(label, go) { return { label: label, go: go }; }
  /* Each step returns { say, chips, links }. */
  var SP = {
    root: function () {
      return { say: spT("q_root"), chips: [
        spC(spT("c_mods"), function () { spGo("family", "mods"); }),
        spC(spT("c_server"), function () { spGo("server"); }),
        spC(spT("c_play"), function () { spGo("play"); }),
        spC(spT("c_news"), function () { spGo("news"); }),
        spC(spT("c_team"), function () { spGo("team"); }),
        spC(spT("c_other"), function () { spGo("other"); })
      ] };
    },
    family: function (then) {
      var chips = SP_FAM.filter(function (f) { return spMods(f).length; }).map(function (f) {
        return spC(plain(tr("cat." + f, f)), function () { spGo("pick", f, then); });
      });
      chips.push(spC(spT("c_all"), function () { spGo("pick", "", then); }));
      return { say: spT("q_family"), chips: chips };
    },
    pick: function (fam, then) {
      return { say: spT("q_mod"), chips: spMods(fam).map(function (it) {
        return spC(it.t, function () { spGo(then === "deps" ? "deps" : "mod", it); });
      }) };
    },
    mod: function (it) {
      var slug = it.u.split("/").slice(-2)[0], links = [spL(spT("l_page"), it.u), spL(spT("l_deps"), it.u + "#deps")];
      if ((idx || []).some(function (x) { return x.m === slug; })) links.push(spL(spT("l_tips"), BASE + "tips/#" + slug));
      if (it.w) links.push(spL(spT("l_ws"), it.w, true));
      return { say: spT("a_mod", { name: it.t }), links: links };
    },
    deps: function (it) { return { say: spT("a_mod", { name: it.t }), links: [spL(spT("l_deps"), it.u + "#deps"), spL(spT("l_page"), it.u)] }; },
    server: function () {
      return { say: spT("q_server"), chips: [
        spC(spT("c_srv_new"), function () { spGo("srv", "new"); }),
        spC(spT("c_srv_cfg"), function () { spGo("srv", "cfg"); }),
        spC(spT("c_srv_cmd"), function () { spGo("srv", "cmd"); }),
        spC(spT("c_srv_deps"), function () { spGo("family", "deps"); }),
        spC(spT("c_srv_bug"), function () { spGo("srv", "bug"); })
      ] };
    },
    srv: function (w) {
      var A = BASE + "admins/#", ad = function (k) { return plain(tr("admins." + k, k)); };
      var L = {
        "new": [spL(ad("install"), A + "install"), spL(ad("json"), A + "json"), spL(ad("scen"), A + "scen"), spL(spT("ext_host"), SP_EXT.host, true)],
        cfg: [spL(ad("profile"), A + "profile"), spL(ad("cfg"), A + "cfg"), spL(spT("ext_cfg"), SP_EXT.cfg, true)],
        cmd: [spL(ad("cmds"), A + "cmds")],
        bug: [spL(ad("logs"), A + "logs"), spL(spT("ext_host"), SP_EXT.host, true)]
      };
      return { say: spT("a_srv_" + w), links: L[w] };
    },
    play: function () {
      return { say: spT("q_play"), chips: SP_TIPS.map(function (s) {
        var m = spMod(s);
        return spC(s === "packs" ? spT("c_packs") : (m ? m.t : s), function () { spGo("tips", s); });
      }) };
    },
    tips: function (s) {
      var m = spMod(s), links = (idx || []).filter(function (x) { return x.m === s; }).map(function (x) {
        return spL(plain(tr(x.t, x.t)), x.u);
      });
      return { say: spT("a_play", { name: s === "packs" ? spT("c_packs") : (m ? m.t : s) }), links: links };
    },
    news: function () { return { say: spT("a_news"), links: [spL(spT("l_news"), BASE + "news/"), spL(spT("l_road"), BASE + "roadmap/"), spL(spT("l_log"), BASE + "changelog/")] }; },
    team: function () { return { say: spT("a_team"), links: [spL(plain(tr("nav.about", "About us")), BASE + "about/")] }; },
    other: function () {
      if (palInput) setTimeout(function () { palInput.focus(); }, 0);
      return { say: spT("a_other"), links: [spL(spT("ext_ws"), SP_EXT.ws, true), spL(spT("ext_mod"), SP_EXT.mod, true), spL(spT("ext_host"), SP_EXT.host, true)] };
    }
  };
  var SP_INTENT = [["mods", function () { spGo("family", "mods"); }, "c_mods"], ["server", function () { spGo("server"); }, "c_server"],
    ["play", function () { spGo("play"); }, "c_play"], ["news", function () { spGo("news"); }, "c_news"], ["team", function () { spGo("team"); }, "c_team"]];
  function spGo(name) {
    var args = Array.prototype.slice.call(arguments, 1);
    sp.stack.push({ name: name, args: args });
    spRender(); if (name !== "other") spFocus();
  }
  /* The button just pressed is gone after a step: keep the keyboard focus inside the dialog. */
  function spFocus() { var f = $(".spk-chip, .spk-links a", sp.box) || palInput; sp.box.scrollTop = 0; if (f) f.focus({ preventScroll: true }); }
  function spBuild() {
    sp.box = doc.createElement("section"); sp.box.className = "spk";
    sp.box.setAttribute("aria-label", "SPARKS");
    sp.box.innerHTML = '<div class="spk-head"><span class="spk-av" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M3 15h13l2-3h3v3l-3 2v3H6v-3z"/><path d="M12 9l1.5-4M16 10l3-3M8 10L6 6.5" class="spk-sp"/></svg></span>' +
      '<span class="spk-id"><b>SPARKS</b><small></small></span><span class="spk-nav"><button type="button" class="spk-back"></button><button type="button" class="spk-new"></button></span></div>' +
      '<p class="spk-hello"></p><div class="spk-say" aria-live="polite"><p></p><div class="spk-chips"></div><ul class="spk-links"></ul></div>';
    $(".spk-back", sp.box).addEventListener("click", function () { if (sp.stack.length > 1) { sp.stack.pop(); spRender(); spFocus(); } });
    $(".spk-new", sp.box).addEventListener("click", function () { spReset(); palInput.focus(); });
    return sp.box;
  }
  function spShow(step) {
    var say = $(".spk-say p", sp.box), chips = $(".spk-chips", sp.box), links = $(".spk-links", sp.box);
    say.textContent = step.say || ""; chips.innerHTML = ""; links.innerHTML = "";
    (step.chips || []).forEach(function (c) {
      var b = doc.createElement("button"); b.type = "button"; b.className = "spk-chip"; b.textContent = c.label;
      b.addEventListener("click", c.go); chips.appendChild(b);
    });
    (step.links || []).forEach(function (l) {
      var li = doc.createElement("li"), a = doc.createElement("a");
      a.href = l.href; a.textContent = l.label;
      if (l.ext) {
        a.target = "_blank"; a.rel = "noopener noreferrer";
        var e = doc.createElement("span"); e.className = "spk-ext"; e.textContent = spT("ext"); a.appendChild(e);
      } else a.addEventListener("click", function () { closePal(true); });
      li.appendChild(a); links.appendChild(li);
    });
  }
  function spRender() {
    if (!sp.box) return;
    $(".spk-id small", sp.box).textContent = spT("role");
    $(".spk-hello", sp.box).textContent = spT("hello");
    $(".spk-back", sp.box).textContent = "← " + spT("back");
    $(".spk-new", sp.box).textContent = spT("restart");
    $(".spk-back", sp.box).hidden = sp.stack.length < 2;
    $(".spk-new", sp.box).hidden = sp.stack.length < 2 && !sp.typed;
    var top = sp.stack[sp.stack.length - 1] || { name: "root", args: [] };
    spShow(SP[top.name].apply(null, top.args));
  }
  function spReset() { sp.stack = [{ name: "root", args: [] }]; sp.typed = false; if (palInput) palInput.value = ""; if (pal && !pal.hidden) renderPal(); spRender(); }
  /* While the visitor types: guess the channel from the keywords of the current language (and English). */
  function spTyped(q, found) {
    if (!sp.box) return;
    if (!q) { if (sp.typed) { sp.typed = false; sp.stack = [{ name: "root", args: [] }]; spRender(); } return; }
    sp.typed = true; sp.stack = [{ name: "root", args: [] }];
    var terms = q.split(/\s+/).filter(function (t) { return t.length >= 3; });
    var hits = SP_INTENT.filter(function (x) {
      var kw = norm(tr("sparks.kw." + x[0], "")).split(/\s+/).filter(Boolean);
      return terms.some(function (t) { return kw.some(function (k) { return k.indexOf(t) === 0 || t.indexOf(k) === 0; }); });
    });
    var chips = (hits.length ? hits : SP_INTENT).map(function (x) { return spC(spT(x[2]), function () { palInput.value = ""; renderPal(); sp.typed = false; sp.stack = [{ name: "root", args: [] }]; x[1](); }); });
    if (found && !hits.length) { spRender(); $(".spk-say", sp.box).hidden = true; return; }
    $(".spk-say", sp.box).hidden = false;
    $(".spk-back", sp.box).hidden = true; $(".spk-new", sp.box).hidden = false;
    var step = { say: hits.length ? spT("guess") : spT("none"), chips: chips };
    if (!found) step.links = [spL(spT("ext_ws"), SP_EXT.ws, true), spL(spT("ext_mod"), SP_EXT.mod, true)];
    spShow(step);
  }

  /* ------------------------------------------------ boot sequence (home, once per session) */
  function boot() {
    if (reduce || root.getAttribute("data-page") !== "home" || sstore("ifg-boot")) return;
    sstore("ifg-boot", "1");
    var lines = [0, 1, 2, 3].map(function (i) { return plain(tr("ui.boot." + i, ["SECURE LINK ESTABLISHED", "DECRYPTING FIELD MANUAL", "LOADING ORDER OF BATTLE", "ALL STATIONS: READY"][i])); });
    var b = doc.createElement("div"); b.className = "boot"; b.setAttribute("aria-hidden", "true");
    b.innerHTML = '<div class="boot-in">' + lines.map(function (l, i) { return '<p style="animation-delay:' + (i * 230) + 'ms"></p>'; }).join("") +
      '<div class="boot-bar"><i></i></div><p class="boot-skip" style="animation-delay:0ms"></p></div>';
    $$("p", b).forEach(function (p, i) { p.textContent = i < lines.length ? lines[i] : plain(tr("ui.boot_skip", "Press any key")); });
    doc.body.appendChild(b);
    var done = false;
    function end() {
      if (done) return; done = true;
      b.classList.add("out"); setTimeout(function () { b.remove(); }, 400);
      doc.removeEventListener("keydown", end, true); scramble();
    }
    b.addEventListener("click", end); doc.addEventListener("keydown", end, true);
    setTimeout(end, 1250);
    return true;
  }

  /* ------------------------------------------------ text decode effect */
  var scrambled = false;
  function scramble() {
    if (reduce || scrambled) return; scrambled = true;
    var chars = "▓▒░█<>/\\|#%&@$*+=-_01ABCDEFGHJKLMNPRSTUVWXYZ";
    $$("[data-scramble]").forEach(function (el) {
      var html = el.innerHTML, text = el.textContent, n = text.length, start = performance.now(), dur = Math.min(700, 200 + n * 22);
      if (!n || n > 80) return;
      el.setAttribute("aria-label", text);
      function frame(now) {
        var p = Math.min(1, (now - start) / dur), shown = Math.floor(p * n), s = "";
        for (var i = 0; i < n; i++) {
          var c = text[i];
          s += (i < shown || c === " ") ? c : chars[(Math.random() * chars.length) | 0];
        }
        el.textContent = s;
        if (p < 1) requestAnimationFrame(frame); else { el.innerHTML = html; el.removeAttribute("aria-label"); }
      }
      requestAnimationFrame(frame);
    });
  }

  /* ------------------------------------------------ counters, reveal */
  function initCounters() {
    var els = $$("[data-count]"); if (!els.length || reduce || !("IntersectionObserver" in window)) return;
    var io = new IntersectionObserver(function (ents) {
      ents.forEach(function (en) {
        if (!en.isIntersecting) return; io.unobserve(en.target);
        var el = en.target, to = +el.getAttribute("data-count"), t0 = performance.now();
        (function step(now) {
          var p = Math.min(1, (now - t0) / 900), e = 1 - Math.pow(1 - p, 3);
          el.textContent = Math.round(to * e); if (p < 1) requestAnimationFrame(step);
        })(t0);
      });
    }, { threshold: .4 });
    els.forEach(function (el) { io.observe(el); });
  }
  function initReveal() {
    if (reduce || !("IntersectionObserver" in window)) return;
    var els = $$(".card, .feat li, .steps li, .stat, .dsec, .op, .leds li");
    var io = new IntersectionObserver(function (ents) {
      ents.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
    }, { rootMargin: "0px 0px -6% 0px" });
    var vh = innerHeight;
    els.forEach(function (el) {
      if (el.getBoundingClientRect().top < vh) return; // already on screen: no flash
      el.classList.add("rv"); io.observe(el);
    });
  }

  /* ------------------------------------------------ filters */
  /* Workshop page: one family and any of the checked Workshop tags; no sorting, the ORBAT order stays. */
  function initModFilter() {
    var box = $("#wsf"); if (!box) return;
    var cards = $$(".orbat .card"), groups = $$(".orbat-group"), fams = $$(".wsf-fam input", box), tags = $$(".wsf-tag input", box);
    var count = $("#wsf-n"), reset = $(".wsf-reset", box), empty = $(".wsf-empty");
    function has(el, attr, v) { return (" " + el.getAttribute(attr) + " ").indexOf(" " + v + " ") >= 0; }
    function setN(el, args) {
      if (!el) return;
      el.setAttribute("data-i18n-args", JSON.stringify(args));
      el.innerHTML = fmt(tr(el.getAttribute("data-i18n"), "{n} mods"), args);
    }
    function run() {
      var f = "all", on = [], n = 0;
      fams.forEach(function (x) { if (x.checked) f = x.value; });
      tags.forEach(function (x) { if (x.checked) on.push(x.value); });
      function inFam(c) { return f === "all" || has(c, "data-fam", f); }
      cards.forEach(function (c) {
        var ok = inFam(c) && (!on.length || on.some(function (v) { return has(c, "data-tags", v); }));
        c.hidden = !ok; if (ok) n++;
      });
      groups.forEach(function (g) {
        var v = $$(".card", g).filter(function (c) { return !c.hidden; }).length;
        g.hidden = !v; setN($(".orbat-n", g), { n: v });
      });
      tags.forEach(function (x) {
        var k = cards.filter(function (c) { return inFam(c) && has(c, "data-tags", x.value); }).length;
        x.parentNode.querySelector("i").textContent = k;
        x.disabled = !k && !x.checked;
      });
      setN(count, { n: n, t: cards.length });
      if (empty) empty.hidden = n > 0;
      reset.disabled = f === "all" && !on.length;
    }
    box.addEventListener("change", run);
    reset.addEventListener("click", function () {
      fams.forEach(function (x) { x.checked = x.value === "all"; });
      tags.forEach(function (x) { x.checked = false; });
      run(); fams[0].focus();
    });
    run();
  }
  function initCfgFilter() {
    var input = $("#cfg-filter"), count = $("#cfg-count"); if (!input) return;
    var boxes = $$(".cfg[id^='cfg-']"), t;
    function run() {
      var q = norm(input.value).trim(), total = 0;
      boxes.forEach(function (box) {
        var hits = 0, head = norm($("summary", box).textContent);
        $$("tbody tr", box).forEach(function (tr) {
          var ok = !q || head.indexOf(q) >= 0 || norm(tr.textContent).indexOf(q) >= 0;
          tr.hidden = !ok; if (ok) hits++;
        });
        box.hidden = q && !hits;
        if (q) box.open = hits > 0;
        total += hits;
      });
      count.textContent = q ? fmt(plain(tr(pkey("ui.rows", total, dict), "{n} settings")), { n: total }) : "";
    }
    input.addEventListener("input", function () { clearTimeout(t); t = setTimeout(run, 80); });
    if (location.hash.indexOf("#cfg-") === 0) { var target = $(location.hash); if (target && target.tagName === "DETAILS") target.open = true; }
    window.addEventListener("hashchange", function () { var tg = location.hash && $(location.hash); if (tg && tg.tagName === "DETAILS") tg.open = true; });
  }

  /* ------------------------------------------------ toc scrollspy */
  function initSpy() {
    var links = $$(".toc a[href^='#']"); if (!links.length || !("IntersectionObserver" in window)) return;
    var map = {};
    links.forEach(function (a) { var s = $(a.getAttribute("href")); if (s) map[s.id] = a; });
    var io = new IntersectionObserver(function (ents) {
      ents.forEach(function (en) {
        if (en.isIntersecting) { links.forEach(function (a) { a.classList.remove("on"); }); map[en.target.id] && map[en.target.id].classList.add("on"); }
      });
    }, { rootMargin: "-20% 0px -70% 0px" });
    Object.keys(map).forEach(function (id) { io.observe(doc.getElementById(id)); });
  }

  /* ------------------------------------------------ mini radar (header) */
  /* Like a real scope: the beam paints each contact where it stands when it passes,
     then the echo fades until the next turn while the contact keeps moving. */
  function initRadar() {
    var cv = $(".mradar canvas"); if (!cv || !cv.getContext) return;
    var ctx = cv.getContext("2d"), S = 34, C = S / 2, R = C - 2, TURN = 3600, TAU = Math.PI * 2;
    var dpr = Math.min(2, window.devicePixelRatio || 1);
    cv.width = cv.height = Math.round(S * dpr); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var g = "64, 200, 120", a = "255, 176, 0";
    function colors() {
      var cs = getComputedStyle(root);
      g = cs.getPropertyValue("--green-rgb").trim() || g; a = cs.getPropertyValue("--amber-rgb").trim() || a;
    }
    colors();
    function spawn(k, edge) {
      var ang = Math.random() * TAU, r = edge ? .97 : .2 + Math.random() * .7;
      var head = ang + Math.PI + (Math.random() - .5) * 1.6, sp = .02 + Math.random() * .035; // share of the radius per second
      k.x = Math.cos(ang) * r; k.y = Math.sin(ang) * r; k.vx = Math.cos(head) * sp; k.vy = Math.sin(head) * sp;
      k.px = k.x; k.py = k.y; k.seen = -1e9;
    }
    var ks = [];
    for (var i = 0; i < 6; i++) { var k = { hot: i === 0 }; spawn(k, false); ks.push(k); }
    function angOf(x, y) { var t = Math.atan2(y, x); return t < 0 ? t + TAU : t; }
    var last = performance.now(), drawn = 0, beam = 0;
    function draw(now, still) {
      var dt = Math.min(.1, (now - last) / 1000), nb = (now % TURN) / TURN * TAU; last = now;
      ctx.clearRect(0, 0, S, S);
      for (var j = 0; j < 14; j++) { // fading trail behind the beam
        ctx.beginPath(); ctx.moveTo(C, C); ctx.arc(C, C, R, nb - (j + 1) * .075, nb - j * .075); ctx.closePath();
        ctx.fillStyle = "rgba(" + g + "," + (.3 * (1 - j / 14)).toFixed(3) + ")"; ctx.fill();
      }
      ctx.strokeStyle = "rgba(" + g + ",.95)"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(C, C); ctx.lineTo(C + Math.cos(nb) * R, C + Math.sin(nb) * R); ctx.stroke();
      ks.forEach(function (k) {
        var ka;
        if (still) { ka = angOf(k.x, k.y); k.seen = now - ((nb - ka + TAU) % TAU) / TAU * TURN; }
        else {
          k.x += k.vx * dt; k.y += k.vy * dt;
          if (k.x * k.x + k.y * k.y > 1) spawn(k, true);
          ka = angOf(k.x, k.y);
          if (beam <= nb ? (ka > beam && ka <= nb) : (ka > beam || ka <= nb)) { k.px = k.x; k.py = k.y; k.seen = now; }
        }
        var o = 1 - (now - k.seen) / TURN; if (o <= 0) return;
        var col = "rgba(" + (k.hot ? a : g) + "," + o.toFixed(3) + ")";
        ctx.fillStyle = col; ctx.shadowColor = col; ctx.shadowBlur = 4;
        ctx.beginPath(); ctx.arc(C + k.px * R, C + k.py * R, k.hot ? 1.9 : 1.4, 0, TAU); ctx.fill();
        ctx.shadowBlur = 0;
      });
      beam = nb;
    }
    var running = false;
    function shown() { return cv.offsetWidth > 0; } // hidden on phones: no drawing at all
    function loop(now) {
      if (!running) return;
      if (!shown()) { running = false; return; }
      if (now - drawn > 30) { drawn = now; draw(now, false); } // about 30 frames a second is plenty
      requestAnimationFrame(loop);
    }
    function run() { // ambient effect: it follows the site's FX switch, like the optics
      if (!shown()) return;
      if (fxOn()) { if (!running) { running = true; last = performance.now(); requestAnimationFrame(loop); } }
      else { running = false; draw(performance.now(), true); }
    }
    addEventListener("resize", run, { passive: true });
    if ("MutationObserver" in window) new MutationObserver(function () { colors(); run(); }).observe(root, { attributes: true, attributeFilter: ["data-theme", "class"] });
    run();
  }

  /* ------------------------------------------------ back to top */
  function initTop() {
    var b = $(".totop"); if (!b) return;
    var on = false, tick = 0;
    function upd() {
      tick = 0; var v = scrollY > 480;
      if (v === on) return; on = v;
      b.classList.toggle("on", v); b.tabIndex = v ? 0 : -1; b.setAttribute("aria-hidden", String(!v));
    }
    addEventListener("scroll", function () { if (!tick) tick = requestAnimationFrame(upd); }, { passive: true });
    b.addEventListener("click", function () {
      scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
      var m = $("#main"); if (m) m.focus({ preventScroll: true });
    });
    upd();
  }

  /* ------------------------------------------------ 404: signal search (VHF scanner) and the SOS call */
  function initScan() {
    var box = $(".scan"); if (!box) return;
    var sec = box.closest(".e404"), cv = $(".scan-cv", box), ctx = cv && cv.getContext && cv.getContext("2d");
    var range = $(".scan-r", box), fOut = $(".scan-f b", box), st = $(".scan-st", box), bars = $$(".scan-m i", box), msg = $(".scan-msg", box);
    var sndBtn = $(".scan-snd", box), sndV = $(".scan-snd-v", box), fv = $(".e404-fv"), car = $(".e404-car");
    if (!ctx || !range) return;
    var N = 2319, F0 = 30, STEP = .025; // 30.000 to 87.975 MHz, 25 kHz channels
    function mhz(ch) { return F0 + ch * STEP; }
    function rint(a, b) { return a + Math.floor(Math.random() * (b - a + 1)); }
    var target = rint(80, N - 80), start;
    do { start = rint(0, N); } while (Math.abs(start - target) < 600);
    range.value = start;
    var t0 = performance.now(), locked = false, done = false, afc = false, afcT = 0, state = "";
    function dist() { return Math.abs(+range.value - target) * STEP; }
    function strength() { var s = Math.max(0, 1 - dist() / 7); return Math.pow(s, 1.6); }
    var ST = { search: ["e404.st_search", "Searching…"], weak: ["e404.st_weak", "Weak carrier"], strong: ["e404.st_strong", "Strong carrier"],
      afc: ["e404.st_afc", "AFC: locking on…"], lock: ["e404.st_lock", "Signal acquired"] };
    function setState(s) {
      if (s === state) return; state = s;
      box.setAttribute("data-state", s === "afc" || s === "lock" ? s : "search");
      st.textContent = plain(tr(ST[s][0], ST[s][1]));
    }
    function update() {
      var ch = +range.value, f = mhz(ch).toFixed(3), s = strength();
      fOut.textContent = f; range.setAttribute("aria-valuetext", f + " MHz");
      var lit = Math.round(s * 6);
      bars.forEach(function (b, i) { b.classList.toggle("on", i < lit); });
      if (locked && ch !== target) locked = false;
      if (!locked && !afc) setState(s > .75 ? "strong" : s > .3 ? "weak" : "search");
      audio();
      if (!running) draw(performance.now());
    }

    /* tuning: when the dial rests close to the carrier, the AFC pulls it onto the exact channel */
    function moved() {
      if (afc) afc = false;
      update(); clearTimeout(afcT); afcT = setTimeout(check, 450);
    }
    function check() {
      if (locked) return;
      var gap = target - +range.value;
      if (!gap) { lock(); return; }
      if (Math.abs(gap) * STEP > .5) return;
      afc = true; setState("afc");
      var from = +range.value, ts = performance.now(), dur = reduce ? 0 : 650;
      (function step(now) {
        if (!afc) return;
        var p = dur ? Math.min(1, (now - ts) / dur) : 1, e = 1 - Math.pow(1 - p, 3);
        range.value = Math.round(from + (target - from) * e); update();
        if (p < 1) requestAnimationFrame(step); else { afc = false; lock(); }
      })(ts);
    }
    function lock() {
      locked = true; setState("lock");
      if (sec) sec.classList.add("rx");
      if (fv) fv.textContent = mhz(target).toFixed(3);
      if (car) car.textContent = "CARRIER OK";
      morse("--.- ... .-..", 700); // QSL: received
      if (!done) { done = true; decode(); }
      update();
    }
    range.addEventListener("input", moved);
    function nudge(n) { range.value = Math.max(0, Math.min(N, +range.value + n)); moved(); }
    $$(".scan-b", box).forEach(function (b) {
      var dir = +b.getAttribute("data-step"), rep = 0, t = 0;
      function stop() { clearTimeout(t); clearInterval(rep); t = rep = 0; }
      b.addEventListener("pointerdown", function (e) {
        if (e.button) return; e.preventDefault(); nudge(dir);
        var n = 0; t = setTimeout(function () { rep = setInterval(function () { n++; nudge(dir * (n > 25 ? 8 : n > 10 ? 3 : 1)); }, 55); }, 320);
      });
      ["pointerup", "pointerleave", "pointercancel"].forEach(function (ev) { b.addEventListener(ev, stop); });
      b.addEventListener("click", function (e) { if (!e.detail) nudge(dir); }); // keyboard
    });
    $(".scan-scope", box).addEventListener("wheel", function (e) {
      e.preventDefault(); nudge((e.deltaY < 0 ? 1 : -1) * (e.shiftKey ? 1 : 4));
    }, { passive: false });

    /* the decrypted transmission */
    function lev(a, b) {
      var m = a.length, n = b.length, d = [], i, j;
      for (i = 0; i <= m; i++) d[i] = [i];
      for (j = 1; j <= n; j++) d[0][j] = j;
      for (i = 1; i <= m; i++) for (j = 1; j <= n; j++)
        d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      return d[m][n];
    }
    function nearest(list, path) {
      var seg = norm(path.split("/").filter(Boolean).pop() || "").replace(/\.html?$/, ""), best = null, home = null;
      list.forEach(function (it) {
        if (it.k !== "page" && it.k !== "mod") return;
        var name = it.tk ? plain(tr(it.t, it.t)) : it.t, slug = it.u.slice(BASE.length).split("/").filter(Boolean).pop() || "";
        if (!slug) { home = { u: it.u, n: name }; return; }
        if (!seg) return;
        var sc = lev(seg, slug) / Math.max(seg.length, slug.length);
        if (slug.indexOf(seg) >= 0 || seg.indexOf(slug) >= 0) sc = Math.min(sc, .2);
        if (!best || sc < best.sc) best = { sc: sc, u: it.u, n: name };
      });
      return best && best.sc <= .6 ? best : home || { u: BASE, n: plain(tr("nav.home", "HQ")) };
    }
    function secs(v) { var s = v.toFixed(1); return root.getAttribute("lang") === "fr" ? s.replace(".", ",") : s; }
    function decode() {
      var took = (performance.now() - t0) / 1000, prev = parseFloat(store("ifg-404-best")) || 0, rec = !prev || took < prev;
      if (rec) store("ifg-404-best", took.toFixed(1));
      var csv = $(".csign-v"), cs = store("ifg-callsign") || (csv && csv.textContent) || "OPERATOR";
      var path = location.pathname.indexOf(BASE) === 0 ? "/" + location.pathname.slice(BASE.length) : location.pathname;
      try { path = decodeURIComponent(path); } catch (e) {}
      if (path.length > 60) path = path.slice(0, 57) + "…";
      loadIndex().catch(function () { return []; }).then(function (list) {
        var near = nearest(list || [], path), joke = "e404.joke." + rint(0, 5);
        var lines = [
          { c: "rx-h", s: ">> RX " + mhz(target).toFixed(3) + " MHz · " + plain(tr("e404.rx", "Decrypted transmission")) },
          { s: fmt(plain(tr("e404.msg", "INDFORGE HQ to {cs}. The page “{path}” does not exist on this net.")), { cs: cs, path: path }) },
          { s: plain(tr("e404.near", "Nearest destination:")) + " ", a: near },
          { c: "rx-j", s: plain(tr(joke, "")) },
          { s: plain(tr("e404.out", "Out.")) },
          { c: "rx-t", s: fmt(plain(tr("e404.time", "Frequency found in {s} s.")), { s: secs(took) }) + " " +
            (rec && prev ? plain(tr("e404.newbest", "New record!")) : fmt(plain(tr("e404.best", "Best: {s} s.")), { s: secs(rec ? took : prev) })) }
        ];
        msg.hidden = false; msg.innerHTML = "";
        if (!reduce) msg.scrollIntoView({ block: "nearest", behavior: "smooth" });
        type(lines, 0);
      });
    }
    function type(lines, i) {
      if (i >= lines.length) return;
      var L = lines[i], p = doc.createElement("p"); if (L.c) p.className = L.c;
      msg.appendChild(p);
      function finish() {
        p.textContent = L.s;
        if (L.a) { var a = doc.createElement("a"); a.href = L.a.u; a.textContent = L.a.n; p.appendChild(a); }
        type(lines, i + 1);
      }
      if (reduce || !L.s) { finish(); return; }
      var n = 0;
      (function tick() {
        n += 2; p.textContent = L.s.slice(0, n) + (n < L.s.length ? "▌" : "");
        if (n < L.s.length) setTimeout(tick, 16); else setTimeout(finish, 120);
      })();
    }

    /* oscilloscope: noise that turns into a clean carrier, then keys "QSL" in Morse once locked */
    var W = 0, H = 0, col = {}, running = false, vis = true, drawn = 0, KEY = bits("--.- ... .-..");
    function bits(code) {
      var out = [];
      code.split("").forEach(function (c) {
        if (c === " ") { out.push(0, 0); return; }
        for (var k = 0; k < (c === "-" ? 3 : 1); k++) out.push(1);
        out.push(0);
      });
      return out.concat([0, 0, 0, 0]);
    }
    function size() {
      var dpr = Math.min(2, window.devicePixelRatio || 1);
      W = cv.clientWidth; H = cv.clientHeight; cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    function colors() {
      var cs = getComputedStyle(root);
      col.g = cs.getPropertyValue("--green-rgb").trim(); col.a = cs.getPropertyValue("--amber-rgb").trim(); col.l = cs.getPropertyValue("--line-rgb").trim();
    }
    function draw(now) {
      if (!W) return;
      var s = strength(), t = now / 1000, mid = H / 2, x, y, n = 0, i;
      ctx.clearRect(0, 0, W, H);
      ctx.strokeStyle = "rgba(" + col.l + ", .1)"; ctx.lineWidth = 1; ctx.beginPath();
      for (i = 1; i < 10; i++) { x = Math.round(W * i / 10) + .5; ctx.moveTo(x, 0); ctx.lineTo(x, H); }
      for (i = 1; i < 4; i++) { y = Math.round(H * i / 4) + .5; ctx.moveTo(0, y); ctx.lineTo(W, y); }
      ctx.stroke();
      var rgb = locked ? col.g : col.a, amp = H * .34 * s, noise = H * .4 * (1 - s * .93), wl = 26 + 70 * s, pts = [];
      for (x = 0; x <= W; x += 3) {
        n = n * .45 + (Math.random() * 2 - 1) * .55;
        var env = 1;
        if (locked) env = KEY[Math.floor((x + t * 90) / 14) % KEY.length] ? 1 : .08;
        pts.push(x, mid + Math.sin(x / wl * 6.283 - t * 7) * amp * env + n * noise);
      }
      [[3.5, .22], [1.4, .95]].forEach(function (pass) {
        ctx.strokeStyle = "rgba(" + rgb + ", " + pass[1] + ")"; ctx.lineWidth = pass[0]; ctx.beginPath();
        for (i = 0; i < pts.length; i += 2) { if (i) ctx.lineTo(pts[i], pts[i + 1]); else ctx.moveTo(pts[i], pts[i + 1]); }
        ctx.stroke();
      });
      var sx = (t * 140) % (W + 60) - 30, g = ctx.createLinearGradient(sx - 30, 0, sx + 30, 0); // sweep
      g.addColorStop(0, "rgba(" + rgb + ", 0)"); g.addColorStop(.5, "rgba(" + rgb + ", .07)"); g.addColorStop(1, "rgba(" + rgb + ", 0)");
      ctx.fillStyle = g; ctx.fillRect(sx - 30, 0, 60, H);
    }
    function loop(now) {
      if (!running) return;
      if (now - drawn > 33) { drawn = now; draw(now); }
      requestAnimationFrame(loop);
    }
    function run() {
      var want = fxOn() && vis && !doc.hidden;
      if (want && !running) { running = true; requestAnimationFrame(loop); }
      else if (!want) { running = false; draw(performance.now()); }
    }
    size(); colors(); update(); run();
    addEventListener("resize", function () { size(); if (!running) draw(performance.now()); });
    doc.addEventListener("visibilitychange", run);
    if ("IntersectionObserver" in window) new IntersectionObserver(function (e) { vis = e[0].isIntersecting; run(); }).observe(box);
    if ("MutationObserver" in window) new MutationObserver(function () { colors(); run(); }).observe(root, { attributes: true, attributeFilter: ["data-theme", "class"] });
    doc.addEventListener("ifg:lang", function () { var s = state; state = ""; setState(s); });

    /* sound, off until asked: hiss that clears up, a heterodyne whistle that drops as you close in */
    var ac = null, nG, tO, tG, on = false;
    function audioInit() {
      var AC = window.AudioContext || window.webkitAudioContext; if (!AC) return false;
      try {
        ac = new AC();
        var len = ac.sampleRate * 2, buf = ac.createBuffer(1, len, ac.sampleRate), d = buf.getChannelData(0), k;
        for (k = 0; k < len; k++) d[k] = Math.random() * 2 - 1;
        var src = ac.createBufferSource(), bp = ac.createBiquadFilter();
        src.buffer = buf; src.loop = true; bp.type = "bandpass"; bp.frequency.value = 1800; bp.Q.value = .6;
        nG = ac.createGain(); nG.gain.value = 0; src.connect(bp); bp.connect(nG); nG.connect(ac.destination); src.start();
        tO = ac.createOscillator(); tO.type = "sine"; tG = ac.createGain(); tG.gain.value = 0;
        tO.connect(tG); tG.connect(ac.destination); tO.start();
        return true;
      } catch (e) { ac = null; return false; }
    }
    function audio() {
      if (!on || !ac) return;
      var s = strength(), at = ac.currentTime;
      nG.gain.setTargetAtTime(locked ? .003 : .045 * (1 - s) + .005, at, .04);
      tO.frequency.setTargetAtTime(380 + Math.min(dist(), 7) * 160, at, .04);
      tG.gain.setTargetAtTime(locked || afc ? 0 : .045 * s * s, at, .04);
    }
    function morse(code, hz, unit) {
      if (!on || !ac) return;
      var o = ac.createOscillator(), g = ac.createGain(), at = ac.currentTime + .08, u = unit || .07;
      o.frequency.value = hz; g.gain.value = 0; o.connect(g); g.connect(ac.destination);
      code.split("").forEach(function (c) {
        if (c === " ") { at += u * 2; return; }
        var l = c === "-" ? 3 * u : u;
        g.gain.setTargetAtTime(.07, at, .004); g.gain.setTargetAtTime(0, at + l, .004); at += l + u;
      });
      o.start(); o.stop(at + .2);
    }
    sndBtn.addEventListener("click", function () {
      on = !on;
      if (on && !ac && !audioInit()) on = false;
      if (ac) { if (on) ac.resume(); else ac.suspend(); }
      sndBtn.setAttribute("aria-pressed", String(on)); sndV.textContent = on ? "ON" : "OFF";
      audio();
    });
    addEventListener("pagehide", function () { if (ac) ac.close(); });

    /* typing S O S anywhere on the page sends a distress call */
    var keys = "";
    doc.addEventListener("keydown", function (e) {
      if (e.ctrlKey || e.metaKey || e.altKey || /^(INPUT|TEXTAREA|SELECT)$/.test((e.target || {}).tagName || "")) return;
      if (!/^[a-z]$/i.test(e.key)) { keys = ""; return; }
      keys = (keys + e.key.toLowerCase()).slice(-3);
      if (keys === "sos") { keys = ""; sos(); }
    });
    var sosOn = false;
    function sos() {
      if (sosOn) return; sosOn = true;
      toast(tr("e404.sos", "Distress call received. Help is on its way: follow “Back to command”."));
      morse("... --- ...", 760, .12);
      if (!fxOn()) { setTimeout(function () { sosOn = false; }, 2500); return; } // ambient effect: follows the FX switch
      var fl = doc.createElement("div"), u = 250, at = 0; fl.className = "sos-fl"; doc.body.appendChild(fl);
      "... --- ...".split("").forEach(function (c) {
        if (c === " ") { at += u * 2; return; }
        var l = c === "-" ? 3 * u : u;
        setTimeout(function () { fl.classList.add("on"); }, at);
        setTimeout(function () { fl.classList.remove("on"); }, at + l);
        at += l + u;
      });
      setTimeout(function () { fl.remove(); sosOn = false; }, at + 300);
    }
  }

  /* ------------------------------------------------ home lists */
  /* The home lists show only the rows that fit; the clipped rows leave the Tab order. */
  function initHomeLists() {
    var lists = $$(".hl-list"); if (!lists.length) return;
    function fit() {
      lists.forEach(function (l) { $$("li", l).forEach(function (li) { li.style.visibility = li.offsetHeight ? "" : "hidden"; }); });
    }
    fit();
    if ("ResizeObserver" in window) lists.forEach(function (l) { new ResizeObserver(fit).observe(l); });
    else addEventListener("resize", fit);
  }

  /* ------------------------------------------------ prefetch fallback */
  function initPrefetch() {
    if (HTMLScriptElement.supports && HTMLScriptElement.supports("speculationrules")) return;
    var done = {};
    doc.addEventListener("pointerover", function (e) {
      var a = e.target.closest && e.target.closest("a[href^='" + BASE + "']"); if (!a) return;
      var u = a.href.split("#")[0]; if (done[u] || u === location.href.split("#")[0]) return;
      done[u] = 1; var l = doc.createElement("link"); l.rel = "prefetch"; l.href = u; doc.head.appendChild(l);
    }, { passive: true });
  }

  var started = false;
  function afterLang() {
    if (started) return; started = true;
    if (!boot()) scramble();
  }

  /* ------------------------------------------------ tips: role filter, learnt cards, field rank */
  function initTips() {
    var bar = $("#tipbar"); if (!bar) return;
    var KEY = "ifg-tips", RANKS = 8, got = {}, lastRank = -1;
    var cards = $$(".tip"), secs = $$(".tsec"), boxes = $$(".tip-ok input");
    var hide = $("#tip-hide"), reset = $("#tip-reset"), rank = $("#tip-rank"), meter = $("#tip-bar"), count = $("#tip-n"), empty = $(".tip-empty");
    try { JSON.parse(store(KEY) || "[]").forEach(function (k) { got[k] = 1; }); } catch (e) {}
    function save() { store(KEY, JSON.stringify(Object.keys(got))); }
    function role() { var r = $("input[name='tip-role']:checked", bar); return r ? r.value : "all"; }
    function run(pop) {
      var r = role(), all = 0, done = 0, shown = 0;
      cards.forEach(function (c) {
        var id = c.id.slice(2), d = !!got[id], mine = r === "all" || c.getAttribute("data-role") === r;
        c.classList.toggle("tip-done", d);
        c.hidden = !mine || (hide.checked && d);
        if (mine) { all++; if (d) done++; }
        if (!c.hidden) shown++;
      });
      secs.forEach(function (s) {
        var cs = $$(".tip", s), mine = cs.filter(function (c) { return r === "all" || c.getAttribute("data-role") === r; });
        var d = mine.filter(function (c) { return got[c.id.slice(2)]; }).length;
        s.hidden = !cs.some(function (c) { return !c.hidden; });
        s.style.setProperty("--sp", mine.length ? d / mine.length : 0);
        s.classList.toggle("full", mine.length > 0 && d === mine.length);
        var sn = $(".tsec-n", s); if (sn) sn.innerHTML = "<b>" + d + "</b> / " + mine.length;
        var a = $(".tipnav a[data-tsec='" + s.id + "']");
        if (a) {
          a.hidden = !mine.length;
          a.classList.toggle("full", mine.length > 0 && d === mine.length);
          $("i", a).textContent = d ? d + "/" + mine.length : mine.length;
        }
      });
      var p = all ? done / all : 0, k = Math.min(RANKS - 1, Math.floor(p * (RANKS - 1) + 1e-9));
      meter.style.setProperty("--p", p);
      rank.setAttribute("data-i18n", "tips.rank." + k);
      rank.innerHTML = tr("tips.rank." + k, rank.innerHTML);
      if (pop && k > lastRank && lastRank >= 0 && !reduce) {
        var w = rank.parentNode; w.classList.remove("up"); void w.offsetWidth; w.classList.add("up");
      }
      lastRank = k;
      count.setAttribute("data-i18n-args", JSON.stringify({ n: done, t: all }));
      count.innerHTML = fmt(tr("tips.prog", "{n} / {t}"), { n: done, t: all });
      if (empty) empty.hidden = shown > 0;
      reset.disabled = !Object.keys(got).length;
    }
    boxes.forEach(function (b) {
      b.checked = !!got[b.value];
      b.addEventListener("change", function () {
        if (b.checked) got[b.value] = 1; else delete got[b.value];
        save();
        var c = b.closest(".tip");
        if (b.checked && !reduce) { c.classList.remove("tip-pop"); void c.offsetWidth; c.classList.add("tip-pop"); }
        run(true);
      });
    });
    bar.addEventListener("change", function () { run(false); });
    reset.addEventListener("click", function () {
      got = {}; save();
      boxes.forEach(function (b) { b.checked = false; });
      run(false);
    });
    doc.addEventListener("ifg:lang", function () { run(false); });
    run(false);
    // the mod list follows the reading position, and stays in view on phones
    var links = $$(".tipnav a"), cur = $(".tip-cur", bar); if (!("IntersectionObserver" in window)) return;
    function show(s) {
      secs.forEach(function (x) { x.classList.toggle("on", x === s); });
      var img = $(".tsec-fig", s), code = $(".tsec-k .sec-code", s), h = $("h2", s);
      $(".tip-cur-img", cur).innerHTML = img ? img.innerHTML : "";
      $(".sec-code", cur).textContent = code ? code.textContent : "";
      $("b", cur).innerHTML = h ? h.innerHTML : "";
      cur.classList.remove("swap"); void cur.offsetWidth; cur.classList.add("swap");
    }
    var io = new IntersectionObserver(function (ents) {
      ents.forEach(function (en) {
        if (!en.isIntersecting) return;
        show(en.target);
        links.forEach(function (a) {
          var on = a.getAttribute("data-tsec") === en.target.id;
          a.classList.toggle("on", on);
          if (on && a.parentNode.scrollWidth > a.parentNode.clientWidth) a.parentNode.scrollLeft = a.offsetLeft - 12;
        });
      });
    }, { rootMargin: "-25% 0px -65% 0px" });
    secs.forEach(function (s) { io.observe(s); });
  }

  function init() {
    initLangMenu(); initOptics(); initMenu(); initCallsign(); initCopy(); initLive(); initSearch();
    initCounters(); initReveal(); initModFilter(); initCfgFilter(); initSpy(); initPrefetch(); initRadar(); initHomeLists(); initTop(); initScan(); initTips();
    var lang = root.getAttribute("data-lang") || "en";
    if (lang === "en") { applyCurrent(); afterLang(); loadLang("en", function (d) { if (d) dict = d; }); }
    else setLang(lang, false);
    if ("requestIdleCallback" in window) requestIdleCallback(function () { loadIndex().catch(function () {}); });
  }
  function applyCurrent() {
    var cur = $(".lang-cur"); if (cur) cur.textContent = "EN";
    $$(".lang-menu [data-lang]").forEach(function (b) { b.setAttribute("aria-checked", String(b.getAttribute("data-lang") === "en")); });
    root.classList.remove("i18n-wait");
  }

  if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", init); else init();
})();
