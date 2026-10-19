/* Geek Motor · Sahne ve Sahne Yığını (GDevelop RuntimeScene + SceneStack mimarisinden esinlenildi)
   Kare sırası: zaman → nesne davranışları (PreEvents) → olay sayfası → davranışlar (PostEvents) → silinenler → çizim.
   SahneYigini: push (altındaki sahne yalnız çizilir), pop, replace; her an yalnızca üstteki sahne adımlanır. */
(function (root) {
  'use strict';
  var NS = root.GeekKosu = root.GeekKosu || {};
  var M = NS.motor = NS.motor || {};

  function ZamanYonetici() { this.olcek = 1; this.toplam = 0; this.gecen = 0; this.ham = 0; this.kare = 0; this.zamanlayicilar = {}; this.enBuyukDt = 0.1; }
  ZamanYonetici.prototype.guncelle = function (dt) {
    this.ham = Math.min(dt, this.enBuyukDt); this.gecen = this.ham * this.olcek; this.toplam += this.gecen; this.kare++;
  };

  function Sahne(ad, ayar) {
    ayar = ayar || {};
    this.ad = ad; this.zaman = new ZamanYonetici(); this.degiskenler = new M.DegiskenKabi('sahne:' + ad + ':');
    this.tween = new M.TweenYonetici(); this.olaylar = new M.OlaySayfasi();
    this.liste = []; this.adIndeks = {}; this.silinecek = []; this.katmanlar = {}; this.gecikmeler = []; this._gecikmeNo = 0;
    this.girdi = {}; this.efektler = null; this.yigin = null; this.yuklendi = false; this.durdu = false;
    this.ayar = ayar;
    this.onYukle = ayar.onYukle || null; this.onGir = ayar.onGir || null; this.onCik = ayar.onCik || null;
    this.onDuraklat = ayar.onDuraklat || null; this.onDevam = ayar.onDevam || null; this.onCiz = ayar.onCiz || null; this.onAdim = ayar.onAdim || null;
  }
  var P = Sahne.prototype;

  /* ---- katmanlar ---- */
  P.katmanEkle = function (ad, ayar) {
    var k = this.katmanlar[ad] = { ad: ad, gorunur: true, zaman: 1, kamera: { x: 0, y: 0, z: 0, yakin: 60 }, efektler: [], ayar: ayar || {} };
    return k;
  };
  P.katman = function (ad) { return this.katmanlar[ad] || null; };

  /* ---- nesne listesi ---- */
  P.nesneEkle = function (n) {
    n.sahne = this; this.liste.push(n);
    (this.adIndeks[n.ad] = this.adIndeks[n.ad] || []).push(n);
    return n;
  };
  P.nesneYarat = function (ad, ayar) { return this.nesneEkle(new M.Nesne(ad, ayar)); };
  P.nesneler = function (ad) { return ad ? (this.adIndeks[ad] || []).filter(function (n) { return !n.olu; }) : this.liste.filter(function (n) { return !n.olu; }); };
  P.etiketli = function (e) { return this.liste.filter(function (n) { return !n.olu && n.etiketVar(e); }); };
  P.enYakin = function (ad, x, y, z) {
    var en = null, ed = Infinity;
    this.nesneler(ad).forEach(function (n) { var dx = n.x - x, dy = n.y - (y || 0), dz = n.z - (z || 0), d = dx * dx + dy * dy + dz * dz; if (d < ed) { ed = d; en = n; } });
    return en;
  };
  P.nesneSil = function (n) { if (n.olu) return; n.olu = true; this.silinecek.push(n); };
  P._temizle = function () {
    if (!this.silinecek.length) return;
    var l = this.silinecek; this.silinecek = [];
    for (var i = 0; i < l.length; i++) {
      var n = l[i]; n._yokEt();
      var a = this.adIndeks[n.ad]; if (a) { var ix = a.indexOf(n); if (ix >= 0) a.splice(ix, 1); }
      var ix2 = this.liste.indexOf(n); if (ix2 >= 0) this.liste.splice(ix2, 1);
    }
  };

  /* ---- zamanlayıcı (GDevelop zamanlayıcısı): sn dolunca doğru döner; tekrar=true ise kendini sıfırlar ---- */
  P.zamanlayici = function (ad, sn, tekrar) {
    var z = this.zaman.zamanlayicilar;
    if (z[ad] === undefined) { z[ad] = 0; return false; }
    if (z[ad] >= sn) { if (tekrar) z[ad] -= sn; else z[ad] = -Infinity; return true; }
    return false;
  };
  P.zamanlayiciSifirla = function (ad) { delete this.zaman.zamanlayicilar[ad]; };
  P._zamanlayicilariIlerlet = function (dt) {
    var z = this.zaman.zamanlayicilar;
    for (var k in z) if (z[k] !== -Infinity) z[k] += dt;
  };

  /* ---- gecikme (GDevelop 'bekle' eylemi): sn sonra fn çalışır; sahne kapanınca/temizlenince iptal olur, sahne zaman ölçeğine uyar ---- */
  P.gecikme = function (sn, fn) { var id = ++this._gecikmeNo; this.gecikmeler.push({ id: id, kalan: sn, fn: fn }); return id; };
  P.gecikmeIptal = function (id) { this.gecikmeler = this.gecikmeler.filter(function (g) { return g.id !== id; }); };
  P.gecikmeleriTemizle = function () { this.gecikmeler = []; };
  P._gecikmeleriIlerlet = function (dt) {
    if (!this.gecikmeler.length) return;
    var hazir = [], kalan = [];
    this.gecikmeler.forEach(function (g) { g.kalan -= dt; (g.kalan <= 0 ? hazir : kalan).push(g); });
    this.gecikmeler = kalan;
    for (var i = 0; i < hazir.length; i++) { try { hazir[i].fn(this); } catch (e) { if (root.console) console.error(e); } }
  };

  /* ---- ana adım ---- */
  P.adim = function (dt) {
    if (this.durdu) return;
    this.zaman.guncelle(dt); var g = this.zaman.gecen;
    this._zamanlayicilariIlerlet(g);
    this.tween.adim(g); this._gecikmeleriIlerlet(g);
    var i, n, l = this.liste.slice();
    for (i = 0; i < l.length; i++) { n = l[i]; if (!n.olu) n.oncesi(this, g); }
    this.olaylar.kos(this);
    if (this.onAdim) this.onAdim(this, g);
    l = this.liste.slice();
    for (i = 0; i < l.length; i++) { n = l[i]; if (!n.olu) n.sonrasi(this, g); }
    this._temizle();
  };
  P.ciz = function (dt) { if (this.onCiz) this.onCiz(this, dt || 0); };
  P.temizle = function () {
    for (var i = 0; i < this.liste.length; i++) this.liste[i]._yokEt();
    this.liste = []; this.adIndeks = {}; this.silinecek = []; this.tween.hepsiniKaldir(); this.olaylar.sifirla(); this.zaman.zamanlayicilar = {}; this.gecikmeler = [];
  };

  /* ---- Sahne yığını ---- */
  function SahneYigini() { this.yigin = []; this.tanim = {}; }
  var Y = SahneYigini.prototype;
  Y.tanimla = function (ad, uretici) { this.tanim[ad] = uretici; return this; };
  Y._yarat = function (ad, arg) {
    var u = this.tanim[ad]; if (!u) throw new Error('Sahne tanımsız: ' + ad);
    var s = typeof u === 'function' ? u(arg) : new Sahne(ad, u);
    s.ad = s.ad || ad; s.yigin = this; return s;
  };
  Y.mevcut = function () { return this.yigin.length ? this.yigin[this.yigin.length - 1] : null; };
  Y.mevcutAd = function () { var m = this.mevcut(); return m ? m.ad : ''; };
  Y.adlar = function () { return this.yigin.map(function (s) { return s.ad; }); };
  Y.derinlik = function () { return this.yigin.length; };
  Y.var = function (ad) { return this.yigin.some(function (s) { return s.ad === ad; }); };
  Y.push = function (ad, arg) {
    var ust = this.mevcut(); if (ust) { ust.durdu = true; if (ust.onDuraklat) ust.onDuraklat(ust); }
    var s = this._yarat(ad, arg); this.yigin.push(s);
    if (!s.yuklendi) { s.yuklendi = true; if (s.onYukle) s.onYukle(s, arg); }
    if (s.onGir) s.onGir(s, arg);
    return s;
  };
  Y.pop = function (adet) {
    adet = adet || 1;
    for (var i = 0; i < adet && this.yigin.length; i++) {
      var s = this.yigin.pop(); if (s.onCik) s.onCik(s); s.temizle();
    }
    var ust = this.mevcut(); if (ust) { ust.durdu = false; if (ust.onDevam) ust.onDevam(ust); }
  };
  Y.replace = function (ad, arg, hepsiniTemizle) {
    if (hepsiniTemizle) { while (this.yigin.length) { var s0 = this.yigin.pop(); if (s0.onCik) s0.onCik(s0); s0.temizle(); } }
    else if (this.yigin.length) { var s1 = this.yigin.pop(); if (s1.onCik) s1.onCik(s1); s1.temizle(); }
    var s = this._yarat(ad, arg); this.yigin.push(s);
    if (!s.yuklendi) { s.yuklendi = true; if (s.onYukle) s.onYukle(s, arg); }
    if (s.onGir) s.onGir(s, arg);
    return s;
  };
  Y.adim = function (dt) { var s = this.mevcut(); if (s) s.adim(dt); };
  Y.ciz = function (dt) { for (var i = 0; i < this.yigin.length; i++) this.yigin[i].ciz(i === this.yigin.length - 1 ? dt : 0); };
  Y.temizle = function () { while (this.yigin.length) { var s = this.yigin.pop(); if (s.onCik) s.onCik(s); s.temizle(); } };

  M.Sahne = Sahne; M.SahneYigini = SahneYigini; M.ZamanYonetici = ZamanYonetici;
})(typeof window !== 'undefined' ? window : globalThis);
