/* Geek Oyun · ECS çekirdeği (Reia'nın GECS yapısından esinlenildi)
   Varlık = yalnızca bir kimlik + bileşen torbası. Bileşenler düz veri (C_*), mantık sistemlerde (*Sistemi).
   Gözlemciler (on/emit) simülasyonu arayüz ve efektlerden ayırır; istek kuyrukları (iste/tuket) sistemler arası köprüdür. */
(function (root) {
  'use strict';
  var NS = root.GeekKosu = root.GeekKosu || {};

  function Dunya(mod) {
    this.mod = mod || 'kosu';
    this.sonId = 0;
    this.varliklar = new Map();
    this.sistemler = [];
    this.dinleyici = {};
    this.kuyruklar = {};
    this.surum = 0;
    this.onbellek = {};
    this.zaman = 0;
    this.prefablar = {};
    this.durum = {};          // mod bazlı paylaşımlı durum (dalga, arena yarıçapı ...)
    this.rastgele = Math.random;
  }
  var P = Dunya.prototype;

  /* ---- varlıklar ---- */
  P.yarat = function (bilesenler, etiket) {
    var e = { id: ++this.sonId, c: {}, olu: false, etiket: etiket || '' };
    if (bilesenler) for (var k in bilesenler) e.c[k] = bilesenler[k];
    this.varliklar.set(e.id, e);
    this.surum++;
    this.emit('varlik_dogdu', e);
    return e;
  };
  P.ekle = function (e, ad, veri) { e.c[ad] = veri || {}; this.surum++; return e; };
  P.cikar = function (e, ad) { if (e.c[ad]) { delete e.c[ad]; this.surum++; } return e; };
  P.var = function (e, ad) { return !!(e && e.c[ad]); };
  P.yoket = function (e) {                      // anında yok etmez; kare sonunda temizlenir
    if (!e || e.olu) return;
    e.olu = true; this._silinecek = this._silinecek || []; this._silinecek.push(e);
  };
  P.temizle = function () {
    var l = this._silinecek;
    if (!l || !l.length) return;
    this._silinecek = [];
    for (var i = 0; i < l.length; i++) { this.emit('varlik_oldu', l[i]); this.varliklar.delete(l[i].id); }
    this.surum++;
  };
  P.al = function (id) { return this.varliklar.get(id) || null; };

  /* ---- sorgu (önbellekli) ---- */
  P.sorgu = function (adlar) {
    var anahtar = adlar.join('|'), o = this.onbellek[anahtar];
    if (o && o.surum === this.surum) return o.liste;
    var liste = [];
    this.varliklar.forEach(function (e) {
      if (e.olu) return;
      for (var i = 0; i < adlar.length; i++) if (!e.c[adlar[i]]) return;
      liste.push(e);
    });
    this.onbellek[anahtar] = { surum: this.surum, liste: liste };
    return liste;
  };

  /* ---- gözlemciler ---- */
  P.on = function (ad, fn) {
    (this.dinleyici[ad] = this.dinleyici[ad] || []).push(fn);
    var self = this;
    return function () { var l = self.dinleyici[ad]; var i = l.indexOf(fn); if (i >= 0) l.splice(i, 1); };
  };
  P.emit = function (ad, veri) {
    var l = this.dinleyici[ad];
    if (!l) return;
    l = l.slice();
    for (var i = 0; i < l.length; i++) { try { l[i](veri, this); } catch (e) { if (root.console) console.error('Gözlemci hatası [' + ad + ']', e); } }
  };

  /* ---- istek kuyrukları ---- */
  P.iste = function (ad, veri) { (this.kuyruklar[ad] = this.kuyruklar[ad] || []).push(veri); };
  P.tuket = function (ad) { var q = this.kuyruklar[ad]; if (!q || !q.length) return []; this.kuyruklar[ad] = []; return q; };

  /* ---- sistemler ---- */
  P.sistemEkle = function (ad, fn, oncelik) {
    this.sistemler.push({ ad: ad, fn: fn, oncelik: oncelik === undefined ? 50 : oncelik, acik: true });
    this.sistemler.sort(function (a, b) { return a.oncelik - b.oncelik; });
  };
  P.sistemAc = function (ad, acik) { this.sistemler.forEach(function (s) { if (s.ad === ad) s.acik = acik; }); };
  P.calistir = function (dt) {
    this.zaman += dt;
    for (var i = 0; i < this.sistemler.length; i++) {
      var s = this.sistemler[i];
      if (s.acik) s.fn(this, dt);
    }
    this.temizle();
  };

  /* ---- prefab ---- */
  P.prefab = function (ad, fn) { this.prefablar[ad] = fn; };
  P.olustur = function (ad, arg) {
    var f = this.prefablar[ad];
    if (!f) throw new Error('Prefab yok: ' + ad);
    return f(this, arg || {});
  };

  /* ---- yardımcılar ---- */
  NS.mesafe2 = function (a, b) { var dx = a.x - b.x, dz = a.z - b.z; return Math.sqrt(dx * dx + dz * dz); };
  NS.sinirla = function (v, a, b) { return v < a ? a : (v > b ? b : v); };
  NS.Dunya = Dunya;
  if (typeof module !== 'undefined' && module.exports) module.exports = NS;
})(typeof window !== 'undefined' ? window : globalThis);
