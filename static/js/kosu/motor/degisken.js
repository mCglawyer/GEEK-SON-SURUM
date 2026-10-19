/* Geek Motor · Değişkenler (GDevelop Variable/VariablesContainer mimarisinden esinlenildi)
   Tür: sayi | metin | mantik | yapi (alt değişkenler) | dizi. Kalıcı olanlar localStorage'a yazılır. */
(function (root) {
  'use strict';
  var NS = root.GeekKosu = root.GeekKosu || {};
  var M = NS.motor = NS.motor || {};

  function Degisken(tur, deger) {
    this.tur = tur || 'sayi';
    this.kalici = false;
    this.v = deger !== undefined ? deger : (this.tur === 'sayi' ? 0 : this.tur === 'metin' ? '' : this.tur === 'mantik' ? false : null);
    this.cocuk = this.tur === 'yapi' ? {} : null;
    this.liste = this.tur === 'dizi' ? [] : null;
  }
  var P = Degisken.prototype;
  P.al = function () { return this.v; };
  P.ayarla = function (x) { this.v = x; return this; };
  P.ekle = function (n) { this.v = (+this.v || 0) + n; return this; };
  P.cikar = function (n) { return this.ekle(-n); };
  P.cocukAl = function (ad) {
    if (this.tur !== 'yapi') { this.tur = 'yapi'; this.cocuk = {}; }
    return this.cocuk[ad] || (this.cocuk[ad] = new Degisken('sayi'));
  };
  P.cocukVar = function (ad) { return !!(this.cocuk && this.cocuk[ad]); };
  P.cocukSil = function (ad) { if (this.cocuk) delete this.cocuk[ad]; };
  P.itele = function (x) {
    if (this.tur !== 'dizi') { this.tur = 'dizi'; this.liste = []; }
    this.liste.push(x instanceof Degisken ? x : new Degisken(typeof x === 'number' ? 'sayi' : typeof x === 'boolean' ? 'mantik' : 'metin', x));
    return this;
  };
  P.uzunluk = function () { return this.liste ? this.liste.length : (this.cocuk ? Object.keys(this.cocuk).length : 0); };
  P.json = function () {
    if (this.tur === 'yapi') { var o = {}; for (var k in this.cocuk) o[k] = this.cocuk[k].json(); return o; }
    if (this.tur === 'dizi') return this.liste.map(function (x) { return x.json(); });
    return this.v;
  };
  Degisken.dene = function (j) {
    if (Array.isArray(j)) { var d = new Degisken('dizi'); j.forEach(function (x) { d.itele(Degisken.dene(x)); }); return d; }
    if (j && typeof j === 'object') { var y = new Degisken('yapi'); for (var k in j) y.cocuk[k] = Degisken.dene(j[k]); return y; }
    return new Degisken(typeof j === 'number' ? 'sayi' : typeof j === 'boolean' ? 'mantik' : 'metin', j);
  };

  function DegiskenKabi(onek) { this.d = {}; this.onek = onek || 'geekmotor:'; }
  var K = DegiskenKabi.prototype;
  K.al = function (ad) { return this.d[ad] || (this.d[ad] = new Degisken('sayi')); };
  K.var = function (ad) { return !!this.d[ad]; };
  K.sil = function (ad) { delete this.d[ad]; };
  K.kalici = function (ad, evet) { this.al(ad).kalici = evet !== false; };
  K.kaydet = function () {
    try {
      var o = {}; for (var k in this.d) if (this.d[k].kalici) o[k] = this.d[k].json();
      root.localStorage.setItem(this.onek, JSON.stringify(o));
    } catch (e) {}
  };
  K.yukle = function () {
    try {
      var o = JSON.parse(root.localStorage.getItem(this.onek) || '{}');
      for (var k in o) { var dg = Degisken.dene(o[k]); dg.kalici = true; this.d[k] = dg; }
    } catch (e) {}
  };

  M.Degisken = Degisken; M.DegiskenKabi = DegiskenKabi;
})(typeof window !== 'undefined' ? window : globalThis);
