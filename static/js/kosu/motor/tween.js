/* Geek Motor · Tween yöneticisi (GDevelop TweenBehavior/TweenManager mimarisinden esinlenildi)
   Adlı tween'ler: ekle / cok (çok değerli) / duraklat / devam / durdur / kaldir / ilerleme / deger. Zaman kaynağı sahnenin zaman ölçeğine uyar. */
(function (root) {
  'use strict';
  var NS = root.GeekKosu = root.GeekKosu || {};
  var M = NS.motor = NS.motor || {};

  var PI = Math.PI;
  var kolaylik = {
    linear: function (t) { return t; },
    easeInQuad: function (t) { return t * t; },
    easeOutQuad: function (t) { return t * (2 - t); },
    easeInOutQuad: function (t) { return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t; },
    easeInCubic: function (t) { return t * t * t; },
    easeOutCubic: function (t) { var u = t - 1; return u * u * u + 1; },
    easeInOutCubic: function (t) { return t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1; },
    easeOutQuart: function (t) { var u = t - 1; return 1 - u * u * u * u; },
    easeOutExpo: function (t) { return t === 1 ? 1 : 1 - Math.pow(2, -10 * t); },
    easeInSine: function (t) { return 1 - Math.cos(t * PI / 2); },
    easeOutSine: function (t) { return Math.sin(t * PI / 2); },
    easeInOutSine: function (t) { return -(Math.cos(PI * t) - 1) / 2; },
    easeInBack: function (t) { var s = 1.70158; return t * t * ((s + 1) * t - s); },
    easeOutBack: function (t) { var s = 1.70158, u = t - 1; return u * u * ((s + 1) * u + s) + 1; },
    easeOutElastic: function (t) { if (t === 0 || t === 1) return t; return Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * (2 * PI / 3)) + 1; },
    easeOutBounce: function (t) {
      var n = 7.5625, d = 2.75;
      if (t < 1 / d) return n * t * t;
      if (t < 2 / d) return n * (t -= 1.5 / d) * t + 0.75;
      if (t < 2.5 / d) return n * (t -= 2.25 / d) * t + 0.9375;
      return n * (t -= 2.625 / d) * t + 0.984375;
    }
  };
  /* özel eğri: cubic-bezier(x1,y1,x2,y2) */
  function bezier(x1, y1, x2, y2) {
    function a(p1, p2) { return 1 - 3 * p2 + 3 * p1; }
    function b(p1, p2) { return 3 * p2 - 6 * p1; }
    function c(p1) { return 3 * p1; }
    function hesap(t, p1, p2) { return ((a(p1, p2) * t + b(p1, p2)) * t + c(p1)) * t; }
    return function (x) {
      if (x <= 0) return 0; if (x >= 1) return 1;
      var t = x;
      for (var i = 0; i < 8; i++) {
        var cx = hesap(t, x1, x2) - x;
        var d = (3 * a(x1, x2) * t + 2 * b(x1, x2)) * t + c(x1);
        if (Math.abs(cx) < 1e-5 || Math.abs(d) < 1e-6) break;
        t -= cx / d;
      }
      return hesap(Math.max(0, Math.min(1, t)), y1, y2);
    };
  }
  function kolaylikBul(ad) {
    if (typeof ad === 'function') return ad;
    return kolaylik[ad] || kolaylik.linear;
  }

  function TweenYonetici() { this.tweenler = {}; this.sira = []; }
  var P = TweenYonetici.prototype;

  function yarat(id, deger, sure, kol, onUpdate, onBitti) {
    return { id: id, deger: deger, sure: Math.max(1e-4, sure), gecen: 0, kol: kolaylikBul(kol), onUpdate: onUpdate || null, onBitti: onBitti || null,
      oynuyor: true, bitti: false, cur: null };
  }
  /* tek değer: from → to */
  P.ekle = function (id, from, to, sure, kol, onUpdate, onBitti) {
    return this._koy(yarat(id, [{ a: from, b: to }], sure, kol, onUpdate, onBitti));
  };
  /* çok değer: [{a,b}] veya {a:[..], b:[..]} → onUpdate(dizi) */
  P.cok = function (id, from, to, sure, kol, onUpdate, onBitti) {
    var d = []; for (var i = 0; i < from.length; i++) d.push({ a: from[i], b: to[i] });
    return this._koy(yarat(id, d, sure, kol, onUpdate, onBitti));
  };
  P._koy = function (tw) {
    tw.cur = tw.deger.map(function (d) { return d.a; });
    if (this.tweenler[tw.id]) this.sira.splice(this.sira.indexOf(this.tweenler[tw.id]), 1);
    this.tweenler[tw.id] = tw; this.sira.push(tw);
    if (tw.onUpdate) tw.onUpdate(tw.cur.length === 1 ? tw.cur[0] : tw.cur);
    return tw;
  };
  P.adim = function (dt) {
    var l = this.sira.slice();
    for (var i = 0; i < l.length; i++) {
      var tw = l[i]; if (!tw.oynuyor || tw.bitti) continue;
      tw.gecen += dt;
      var t = Math.min(1, tw.gecen / tw.sure), e = tw.kol(t);
      for (var k = 0; k < tw.deger.length; k++) tw.cur[k] = tw.deger[k].a + (tw.deger[k].b - tw.deger[k].a) * e;
      if (tw.onUpdate) tw.onUpdate(tw.cur.length === 1 ? tw.cur[0] : tw.cur);
      if (t >= 1) { tw.bitti = true; tw.oynuyor = false; if (tw.onBitti) tw.onBitti(tw); }
    }
    /* biten tweenler 'bitti' sorgusu için tutulur; aynı kimlikle yeniden eklenince üzerine yazılır */
  };
  P.var = function (id) { return !!this.tweenler[id]; };
  P.oynuyor = function (id) { var t = this.tweenler[id]; return !!t && t.oynuyor && !t.bitti; };
  P.bitti = function (id) { var t = this.tweenler[id]; return !!t && t.bitti; };
  P.duraklat = function (id) { var t = this.tweenler[id]; if (t && !t.bitti) t.oynuyor = false; };
  P.devam = function (id) { var t = this.tweenler[id]; if (t && !t.bitti) t.oynuyor = true; };
  P.durdur = function (id, hedefeGit) {
    var t = this.tweenler[id]; if (!t || t.bitti) return;
    t.oynuyor = false; t.bitti = true;
    if (hedefeGit) { for (var k = 0; k < t.deger.length; k++) t.cur[k] = t.deger[k].b; if (t.onUpdate) t.onUpdate(t.cur.length === 1 ? t.cur[0] : t.cur); }
  };
  P.kaldir = function (id) { var t = this.tweenler[id]; if (!t) return; this.sira.splice(this.sira.indexOf(t), 1); delete this.tweenler[id]; };
  P.hepsiniKaldir = function () { this.tweenler = {}; this.sira = []; };
  P.ilerleme = function (id) { var t = this.tweenler[id]; return t ? Math.min(1, t.gecen / t.sure) : 0; };
  P.deger = function (id) { var t = this.tweenler[id]; return t ? t.cur[0] : 0; };
  P.sayi = function () { return this.sira.length; };

  M.kolaylik = kolaylik; M.kolaylikBul = kolaylikBul; M.bezier = bezier; M.TweenYonetici = TweenYonetici;
})(typeof window !== 'undefined' ? window : globalThis);
