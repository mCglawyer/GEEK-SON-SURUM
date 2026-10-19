/* Geek Motor · Olay sayfası (GDevelop olay tablosu mantığı: koşullar → eylemler, bir kez, zamanlayıcı, alt olaylar)
   Kural = { kosul: fn | [fn..] (VE), eylem: fn(sahne), bir: true (koşul yeni doğru olduğunda 1 kez), alt: [kural..], ad } */
(function (root) {
  'use strict';
  var NS = root.GeekKosu = root.GeekKosu || {};
  var M = NS.motor = NS.motor || {};

  function OlaySayfasi() { this.kurallar = []; this._once = {}; this._sayac = 0; }
  var P = OlaySayfasi.prototype;
  P.ekle = function (kural) { kural._id = kural.ad || ('k' + (++this._sayac)); this.kurallar.push(kural); return this; };
  P.kos = function (sahne) { this._liste(this.kurallar, sahne); };
  P._liste = function (liste, sahne) {
    for (var i = 0; i < liste.length; i++) {
      var k = liste[i];
      if (k.aktif === false) continue;
      var dogru = true, ks = k.kosul;
      if (ks) { var a = Array.isArray(ks) ? ks : [ks]; for (var j = 0; j < a.length; j++) { if (!a[j](sahne, k)) { dogru = false; break; } } }
      if (k.bir) {
        var onceki = !!this._once[k._id]; this._once[k._id] = dogru;
        if (!dogru || onceki) { continue; }
      } else if (!dogru) continue;
      if (k.eylem) k.eylem(sahne, k);
      if (k.alt) this._liste(k.alt, sahne);
    }
  };
  P.sifirla = function () { this._once = {}; };

  /* yaygın koşullar */
  var O = {
    zamanlayici: function (ad, sn) { return function (sahne) { return sahne.zamanlayici(ad, sn); }; },
    her: function (sn) { var ad = 'her_' + Math.random().toString(36).slice(2); return function (sahne) { return sahne.zamanlayici(ad, sn, true); }; },
    degiskenEsit: function (ad, v) { return function (sahne) { return sahne.degiskenler.al(ad).al() === v; }; },
    degiskenBuyuk: function (ad, v) { return function (sahne) { return sahne.degiskenler.al(ad).al() > v; }; },
    nesneYok: function (ad) { return function (sahne) { return sahne.nesneler(ad).length === 0; }; },
    nesneSayisi: function (ad, f) { return function (sahne) { return f(sahne.nesneler(ad).length); }; },
    tus: function (kod) { return function (sahne) { return !!(sahne.girdi && sahne.girdi[kod]); }; },
    sahneSuresi: function (sn) { return function (sahne) { return sahne.zaman.toplam >= sn; }; }
  };
  M.OlaySayfasi = OlaySayfasi; M.olay = O;
})(typeof window !== 'undefined' ? window : globalThis);
