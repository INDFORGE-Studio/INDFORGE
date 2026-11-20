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

  /* ------------------------------------------------ i18n */
  function applyDict(lang, d) {
    dict = d;
    root.setAttribute("lang", lang);
    root.setAttribute("data-lang", lang);
    $$("[data-i18n]").forEach(function (el) {
      var key = el.getAttribute("data-i18n"), s = d[key];
      if (s == null) return;
      var a = el.getAttribute("data-i18n-args");
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
  var FX = { nvg: 1, thermal: 1, arctic: 1, red: 1, day: 1 };
  var DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  function fxOn() { return !root.classList.contains("fx-off"); }
  function makeFx() {
    var cv, ctx, hud, tl, br, torch, parts = [], raf = 0, last = 0, W = 0, Hh = 0, dpr = 1, kind = "", sweep = 0, sprite = null, hudRaf = 0;
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
      else if (kind === "thermal") { p.x = rnd(0, W); p.y = top ? Hh + rnd(0, 60) : rnd(0, Hh); p.r = rnd(10, 34); p.vy = -rnd(.15, .55); p.vx = rnd(-.1, .1); p.ph = rnd(0, 6.3); p.a = rnd(.05, .14); p.c = Math.random() < .7 ? 0 : 1; }
      else { p.x = rnd(0, W); p.y = rnd(0, Hh); p.r = rnd(.5, 1.5); p.vx = rnd(-.09, .09); p.vy = rnd(-.09, .09); p.ph = rnd(0, 6.3); p.a = rnd(.2, kind === "red" ? .4 : .7); }
      return p;
    }
    function seed() {
      var area = W * Hh, n = kind === "arctic" ? Math.min(120, area / 12000) : kind === "thermal" ? Math.min(28, area / 50000) : Math.min(90, area / 16000);
      if (kind === "red") n *= .5;
      parts = []; for (var i = 0; i < Math.round(n); i++) parts.push(spawn({}, false));
    }
    function makeSprite() {
      var a = rgbVar("--amber-rgb"), g = rgbVar("--green-rgb");
      sprite = [a, g].map(function (c) {
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
      var col = rgbVar("--amber-rgb"), t = now / 1000, i, p;
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
      size(); if (k === "thermal") makeSprite(); seed(); hudText(); start();
    }
    function hit(x, y) {
      var k = kind; if (!k) return;
      var label = k === "nvg" ? "RNG " + Math.round(rnd(120, 900)) + " m"
        : k === "thermal" ? "+" + rnd(31, 39).toFixed(1) + "°C"
        : k === "arctic" ? "−" + Math.round(rnd(8, 31)) + "°C"
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
      if (meta) meta.setAttribute("content", getComputedStyle(root).getPropertyValue("--bg").trim() || "#06080a");
    }
    function apply(o) {
      if (o === "arma") root.removeAttribute("data-theme"); else root.setAttribute("data-theme", o);
      store("ifg-optic", o); sync(); fx.refresh();
    }
    function engage(o, from) {
      if (o === current()) return;
      var r = from.getBoundingClientRect(), anim = !reduce && fxOn();
      root.style.setProperty("--vx", Math.round(r.left + r.width / 2) + "px");
      root.style.setProperty("--vy", Math.round(r.top + r.height / 2) + "px");
      var label = plain(tr("optic." + o, o));
      if (!anim || !doc.startViewTransition) { apply(o); }
      else {
        root.classList.add("vt-optic");
        var vt = doc.startViewTransition(function () { apply(o); });
        vt.ready.catch(function () {}); vt.finished.then(done, done);
      }
      if (anim) {
        var ring = doc.createElement("div"); ring.className = "optic-ring"; ring.setAttribute("aria-hidden", "true");
        doc.body.appendChild(ring); setTimeout(function () { ring.remove(); }, 800);
      }
      toast(fmt(tr("optic.on", "Optic engaged: {n}"), { n: label }));
      function done() { root.classList.remove("vt-optic"); }
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
        var lb = $(".lang-btn"), lm = $("#lang-menu");
        if (lm && !lm.hidden) { lm.hidden = true; lb.setAttribute("aria-expanded", "false"); }
        var c = $('[data-optic][aria-checked="true"]', menu) || radios[0]; c && c.focus();
      }
    }
    btn.addEventListener("click", function (e) { e.stopPropagation(); open(menu.hidden); });
    menu.addEventListener("click", function (e) {
      if (e.target.closest("[data-fx]")) { toggleFx(); return; }
      var b = e.target.closest("[data-optic]"); if (!b) return;
      open(false); btn.focus(); engage(b.getAttribute("data-optic"), btn);
    });
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
    sync(); fx.refresh();
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
    window.addEventListener("resize", function () { if (innerWidth > 1340 && nav.classList.contains("open")) set(false); });
  }

  /* ------------------------------------------------ Zulu clock */
  function initClock() {
    var el = $("#zulu"); if (!el) return;
    function pad(n) { return (n < 10 ? "0" : "") + n; }
    function tick() { var d = new Date(); el.textContent = pad(d.getUTCHours()) + ":" + pad(d.getUTCMinutes()) + ":" + pad(d.getUTCSeconds()) + "Z"; }
    tick();
    var id = setInterval(tick, 1000);
    doc.addEventListener("visibilitychange", function () { clearInterval(id); if (!doc.hidden) { tick(); id = setInterval(tick, 1000); } });
  }

  /* ------------------------------------------------ toast & copy */
  var toastEl, toastT;
  function toast(msg, bad) {
    if (!toastEl) { toastEl = doc.createElement("div"); toastEl.className = "toast"; toastEl.setAttribute("role", "status"); doc.body.appendChild(toastEl); }
    toastEl.textContent = plain(msg); toastEl.classList.toggle("bad", !!bad);
    void toastEl.offsetWidth; toastEl.classList.add("on");
    clearTimeout(toastT); toastT = setTimeout(function () { toastEl.classList.remove("on"); }, 1800);
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
      var b = e.target.closest(".copy"); if (!b) return;
      var sel = b.getAttribute("data-copy"), text = b.getAttribute("data-copy-text");
      if (sel) { var src = $(sel); text = src ? src.textContent : ""; }
      if (!text) return;
      copyText(text).then(function () {
        b.classList.add("ok"); var l = $(".copy-lbl", b), old = l && l.innerHTML;
        if (l) l.textContent = plain(tr("ui.copied", "Copied"));
        toast(tr("ui.copied", "Copied"));
        setTimeout(function () { b.classList.remove("ok"); if (l) l.innerHTML = old; }, 1600);
      }, function () { toast(tr("ui.copy_fail", "Copy blocked: select the text by hand"), true); });
    });
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
    palInput.addEventListener("input", renderPal);
    pal.addEventListener("click", function (e) { if (e.target === pal) closePal(); });
    pal.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { e.preventDefault(); closePal(); }
      else if (e.key === "ArrowDown") { e.preventDefault(); selPal(palSel + 1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); selPal(palSel - 1); }
      else if (e.key === "Enter") { var a = palItems[palSel]; if (a) { e.preventDefault(); a.click(); } }
      else if (e.key === "Tab") { e.preventDefault(); palInput.focus(); }
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
    loadIndex().then(renderPal).catch(function () {});
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
  function initModFilter() {
    var btns = $$(".fbtn"); if (!btns.length) return;
    btns.forEach(function (b) {
      b.addEventListener("click", function () {
        var f = b.getAttribute("data-filter");
        btns.forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
        $$(".orbat-group").forEach(function (g) { g.hidden = !(f === "all" || g.getAttribute("data-group") === f); });
      });
    });
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
      count.textContent = q ? fmt(plain(tr("ui.rows", "{n} settings")), { n: total }) : "";
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

  function init() {
    initLangMenu(); initOptics(); initMenu(); initClock(); initCopy(); initSearch();
    initCounters(); initReveal(); initModFilter(); initCfgFilter(); initSpy(); initPrefetch();
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
