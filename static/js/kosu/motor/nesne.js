/* Geek Motor · Nesne + Davranış (GDevelop RuntimeObject / RuntimeBehavior yaşam döngüsünden esinlenildi)
   Davranış: onCreated, doStepPreEvents(sahne, dt), doStepPostEvents(sahne, dt), onActivate, onDeActivate, onDestroy.
   Nesne: ad, konum (x,y,z), katman, etiketler, değişkenler, davranışlar, kendi tween yöneticisi; sahneye ad ile listelenir. */
(function (root) {
  'use strict';
  var NS = root.GeekKosu = root.GeekKosu || {};
  var M = NS.motor = NS.motor || {};

  function Davranis(sahip, ad, ayar) {
    this.sahip = sahip; this.ad = ad || this.constructor.tur || 'Davranis'; this.tur = this.constructor.tur || this.ad;
    this.aktif = true; this.ayar = ayar || {};
  }
  Davranis.prototype.onCreated = function () {};
  Davranis.prototype.doStepPreEvents = function () {};
  Davranis.prototype.doStepPostEvents = function () {};
  Davranis.prototype.onActivate = function () {};
  Davranis.prototype.onDeActivate = function () {};
  Davranis.prototype.onDestroy = function () {};
  Davranis.prototype.etkinlestir = function (evet) {
    evet = evet !== false;
    if (evet === this.aktif) return;
    this.aktif = evet; if (evet) this.onActivate(); else this.onDeActivate();
  };

  var kayit = {};
  Davranis.kaydet = function (tur, sinif) { sinif.tur = tur; kayit[tur] = sinif; return sinif; };
  Davranis.al = function (tur) { return kayit[tur] || null; };
  /* kolay alt sınıf: Davranis.turet('Ad', {onCreated(){}, doStepPreEvents(s, dt){}}) */
  Davranis.turet = function (tur, yontemler) {
    function D(sahip, ad, ayar) { Davranis.call(this, sahip, ad, ayar); }
    D.prototype = Object.create(Davranis.prototype); D.prototype.constructor = D;
    for (var k in yontemler) D.prototype[k] = yontemler[k];
    return Davranis.kaydet(tur, D);
  };

  var nesneSayac = 0;
  function Nesne(ad, ayar) {
    ayar = ayar || {};
    this.id = ++nesneSayac; this.ad = ad || 'Nesne'; this.x = ayar.x || 0; this.y = ayar.y || 0; this.z = ayar.z || 0;
    this.katman = ayar.katman || '';
    this.etiketler = ayar.etiketler ? ayar.etiketler.slice() : [];
    this.davranislar = []; this.davranisAd = {};
    this.degiskenler = new M.DegiskenKabi('nesne:' + this.id + ':'); this.tween = new M.TweenYonetici();
    this.sahne = null; this.olu = false; this.veri = ayar.veri || {};
    this.gorsel = ayar.gorsel || null;     // three.js Object3D veya DOM öğesi
  }
  var N = Nesne.prototype;
  N.davranisEkle = function (tur, ad, ayar) {
    var S = typeof tur === 'function' ? tur : Davranis.al(tur);
    if (!S) throw new Error('Davranış bulunamadı: ' + tur);
    var d = new S(this, ad || S.tur, ayar);
    this.davranislar.push(d); this.davranisAd[d.ad] = d;
    d.onCreated();
    return d;
  };
  N.davranis = function (ad) { return this.davranisAd[ad] || null; };
  N.davranisVar = function (ad) { return !!this.davranisAd[ad]; };
  N.etiketVar = function (e) { return this.etiketler.indexOf(e) >= 0; };
  N.konum = function (x, y, z) { this.x = x; if (y !== undefined) this.y = y; if (z !== undefined) this.z = z; return this; };
  N.mesafe = function (o) { var dx = this.x - o.x, dy = this.y - o.y, dz = this.z - o.z; return Math.sqrt(dx * dx + dy * dy + dz * dz); };
  N.oncesi = function (sahne, dt) {
    this.tween.adim(dt);
    for (var i = 0; i < this.davranislar.length; i++) { var d = this.davranislar[i]; if (d.aktif) d.doStepPreEvents(sahne, dt); }
  };
  N.sonrasi = function (sahne, dt) {
    for (var i = 0; i < this.davranislar.length; i++) { var d = this.davranislar[i]; if (d.aktif) d.doStepPostEvents(sahne, dt); }
  };
  N.yoket = function () { if (this.sahne) this.sahne.nesneSil(this); else this._yokEt(); };
  N._yokEt = function () {
    if (this.yokEdildi) return; this.yokEdildi = true; this.olu = true;
    for (var i = 0; i < this.davranislar.length; i++) { try { this.davranislar[i].onDestroy(); } catch (e) { if (root.console) console.error(e); } }
    if (this.onYok) this.onYok(this);
  };

  M.Davranis = Davranis; M.Nesne = Nesne;
})(typeof window !== 'undefined' ? window : globalThis);
