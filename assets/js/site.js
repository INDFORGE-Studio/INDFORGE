/* INDFORGE - Studio // Arma Reforger division — interactive layer.
   Every page is complete without this file: it only adds languages, search, copy and immersion. */
(function () {
  "use strict";
  var doc = document, root = doc.documentElement;
  var BASE = root.getAttribute("data-base") || "/INDFORGE/";
  var VER = root.getAttribute("data-v") || "0";
  var LANGS = ["en", "fr", "de", "es", "it", "pl", "uk"];
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
  function cacheKey(lang) { return "ifg-i18n-" + lang; }
  function loadLang(lang, cb) {
    var c = store(cacheKey(lang));
    if (c) { try { var o = JSON.parse(c); if (o.v === VER && o.d) { cb(o.d); return; } } catch (e) {} }
    fetch(BASE + "assets/i18n/" + lang + ".json?v=" + VER, { credentials: "same-origin" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) { store(cacheKey(lang), JSON.stringify({ v: VER, d: d })); cb(d); })
      .catch(function () { root.classList.remove("i18n-wait"); cb(null); });
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
    initLangMenu(); initMenu(); initClock(); initCopy(); initSearch();
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
